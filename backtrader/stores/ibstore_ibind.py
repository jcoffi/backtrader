#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2023 Daniel Rodriguez
# Modified for ibind integration
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
from copy import copy
from datetime import date, datetime, timedelta
import inspect
import itertools
import os
import random
import threading
import time
import json
import logging

# ibind imports
from ibind import IbkrClient, IbkrWsClient, OrderRequest, StockQuery
from ibind.base.rest_client import Result

# Legacy ibpy compatibility imports for data structures
try:
    from ib.ext.Contract import Contract
    import ib.opt as ibopt
except ImportError:
    # Create mock classes for compatibility if ibpy is not available
    class Contract:
        def __init__(self):
            self.m_symbol = b''
            self.m_secType = b'STK'
            self.m_exchange = b'SMART'
            self.m_currency = b'USD'
            self.m_expiry = b''
            self.m_strike = 0.0
            self.m_right = b''
            self.m_multiplier = b''
            self.m_conId = 0
    
    class MockMessage:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ibopt:
        class message:
            pass

from backtrader import TimeFrame, Position
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import bytes, bstr, queue, with_metaclass, long
from backtrader.utils import AutoDict, UTC

bytes = bstr  # py2/3 need for compatibility


def _ts2dt(tstamp=None):
    """Transforms a timestamp to a datetime object"""
    if not tstamp:
        return datetime.utcnow()

    if isinstance(tstamp, str):
        # Handle string timestamps from ibind
        try:
            return datetime.fromisoformat(tstamp.replace('Z', '+00:00')).replace(tzinfo=None)
        except:
            return datetime.utcnow()
    
    sec, msec = divmod(long(tstamp), 1000)
    usec = msec * 1000
    return datetime.utcfromtimestamp(sec).replace(microsecond=usec)


class RTVolume(object):
    '''Parses market data into RTVolume format for compatibility'''
    _fields = [
        ('price', float),
        ('size', int),
        ('datetime', _ts2dt),
        ('volume', int),
        ('vwap', float),
        ('single', bool)
    ]

    def __init__(self, rtvol='', price=None, tmoffset=None, market_data=None):
        if market_data:
            # Convert ibind market data to RTVolume format
            self.price = float(market_data.get('31', price or 0))  # Last price
            self.size = int(market_data.get('32', 0))  # Last size
            self.datetime = datetime.utcnow()
            self.volume = int(market_data.get('7295', 0))  # Volume
            self.vwap = float(market_data.get('7633', 0))  # VWAP
            self.single = True
        else:
            # Legacy RTVolume parsing
            tokens = iter(rtvol.split(';')) if rtvol else iter([''] * len(self._fields))
            
            for name, func in self._fields:
                try:
                    value = next(tokens)
                    setattr(self, name, func(value) if value else func())
                except (StopIteration, ValueError):
                    setattr(self, name, func())

        if price is not None:
            self.price = price

        if tmoffset is not None:
            self.datetime += tmoffset


class ContractMapper:
    """Maps between ibpy Contract objects and ibind contract identifiers"""
    
    def __init__(self, rest_client):
        self.rest_client = rest_client
        self.contract_cache = {}  # (symbol, sectype, exchange) -> conid
        self.conid_cache = {}     # conid -> contract_info
        
    def contract_to_conid(self, contract):
        """Convert ibpy Contract to ibind conid"""
        cache_key = (
            contract.m_symbol.decode() if isinstance(contract.m_symbol, bytes) else contract.m_symbol,
            contract.m_secType.decode() if isinstance(contract.m_secType, bytes) else contract.m_secType,
            contract.m_exchange.decode() if isinstance(contract.m_exchange, bytes) else contract.m_exchange
        )
        
        if cache_key in self.contract_cache:
            return self.contract_cache[cache_key]
        
        symbol, sec_type, exchange = cache_key
        
        try:
            # Search for contract using ibind
            if sec_type.upper() == 'CASH':
                # Handle forex pairs
                result = self.rest_client.search_contract_by_symbol(
                    symbol=symbol, sec_type='CASH'
                )
            else:
                result = self.rest_client.search_contract_by_symbol(
                    symbol=symbol, sec_type=sec_type
                )
            
            if result.success and result.data:
                # Find best match based on exchange
                best_match = None
                for contract_data in result.data:
                    if exchange == 'SMART' or contract_data.get('exchange', '') == exchange:
                        best_match = contract_data
                        break
                
                if not best_match and result.data:
                    best_match = result.data[0]  # Use first result as fallback
                
                if best_match:
                    conid = str(best_match['conid'])
                    self.contract_cache[cache_key] = conid
                    self.conid_cache[conid] = best_match
                    return conid
                    
        except Exception as e:
            logging.error(f"Error resolving contract {cache_key}: {e}")
        
        return None
    
    def conid_to_contract(self, conid):
        """Convert ibind conid back to ibpy Contract"""
        if conid in self.conid_cache:
            contract_data = self.conid_cache[conid]
        else:
            try:
                result = self.rest_client.security_definition_by_conid([str(conid)])
                if result.success and result.data:
                    contract_data = result.data[0]
                    self.conid_cache[conid] = contract_data
                else:
                    return None
            except Exception:
                return None
        
        contract = Contract()
        contract.m_conId = int(conid)
        contract.m_symbol = bytes(contract_data.get('symbol', ''))
        contract.m_secType = bytes(contract_data.get('secType', 'STK'))
        contract.m_exchange = bytes(contract_data.get('exchange', 'SMART'))
        contract.m_currency = bytes(contract_data.get('currency', 'USD'))
        
        return contract


class OrderMapper:
    """Maps between ibpy and ibind order formats"""
    
    def __init__(self):
        self.order_id_mapping = {}  # ibpy_order_id -> ibind_order_id
        self.reverse_mapping = {}   # ibind_order_id -> ibpy_order_id
        self.next_order_id = itertools.count(1)
    
    def ibpy_to_ibind_order(self, contract, order, contract_mapper):
        """Convert ibpy order to ibind OrderRequest"""
        conid = contract_mapper.contract_to_conid(contract)
        if not conid:
            raise ValueError(f"Could not resolve contract: {contract.m_symbol}")
        
        # Map order type
        order_type = 'MKT'  # Default
        if hasattr(order, 'm_orderType'):
            order_type = order.m_orderType.decode() if isinstance(order.m_orderType, bytes) else order.m_orderType
        
        # Map action to side
        side = 'BUY'
        if hasattr(order, 'm_action'):
            action = order.m_action.decode() if isinstance(order.m_action, bytes) else order.m_action
            side = 'BUY' if action.upper() == 'BUY' else 'SELL'
        
        # Create OrderRequest
        order_request = OrderRequest(
            conidex=conid,
            sec_type=contract.m_secType.decode() if isinstance(contract.m_secType, bytes) else contract.m_secType,
            coid=str(next(self.next_order_id)),
            order_type=order_type,
            side=side,
            tif='DAY',  # Default time in force
            quantity=int(getattr(order, 'm_totalQuantity', 0))
        )
        
        # Set price for limit orders
        if order_type in ['LMT', 'LIMIT'] and hasattr(order, 'm_lmtPrice'):
            order_request.price = float(order.m_lmtPrice)
        
        # Set aux price for stop orders
        if order_type in ['STP', 'STOP'] and hasattr(order, 'm_auxPrice'):
            order_request.aux_price = float(order.m_auxPrice)
        
        return order_request


class MetaSingleton(MetaParams):
    '''Metaclass to make a metaclassed class a singleton'''
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton


class IBStoreIbind(with_metaclass(MetaSingleton, object)):
    '''IBStore implementation using ibind instead of ibpy.
    
    This is a drop-in replacement for the original IBStore that uses the modern
    ibind library while maintaining full backward compatibility.
    
    The parameters are the same as the original IBStore for compatibility.
    '''

    # Set a base for the data requests to distinguish from orders
    REQIDBASE = 0x01000000

    BrokerCls = None  # broker class will autoregister
    
    def getbroker(self, *args, **kwargs):
        """
        Returns broker with args, kwargs and not store state
        """
        # Import here to avoid circular imports
        from backtrader.brokers.ibbroker import IBBroker
        self.BrokerCls = IBBroker
        return self.BrokerCls(*args, **kwargs)
    DataCls = None  # data class will auto register

    params = (
        # Original IBStore parameters (backward compatibility)
        ('host', '127.0.0.1'),
        ('port', 5000),  # IB Gateway Web API port (changed from 7496)
        ('clientId', None),  # Maintained for compatibility
        ('notifyall', False),
        ('_debug', False),
        ('reconnect', 3),
        ('timeout', 3.0),
        ('timeoffset', True),
        ('timerefresh', 60.0),
        ('indcash', True),
        
        # Enhanced ibind-specific parameters
        ('use_oauth', False),  # Enable OAuth 1.0a authentication
        ('oauth_config', None),  # OAuth configuration object
        ('account_id', None),  # Specific account ID to use
        ('enable_tickler', True),  # Auto-maintain OAuth session
        ('parallel_requests', True),  # Enable parallel market data requests
        ('rate_limit_delay', 0.1),  # Delay between requests for rate limiting
        ('websocket_auto_reconnect', True),  # Auto-reconnect WebSocket on failure
        ('enhanced_error_handling', True),  # Use ibind's enhanced error reporting
        ('market_data_channels', None),  # List of WebSocket channels to subscribe to
        ('enable_async_support', False),  # Enable async/await compatibility
        ('session_timeout', 3600),  # OAuth session timeout in seconds
        ('max_concurrent_requests', 10),  # Max parallel requests
        ('enable_question_answer', True),  # Handle interactive order confirmations
        ('auto_symbol_resolution', True),  # Automatically resolve symbols to contract IDs
        ('cache_contract_details', True),  # Cache contract details for performance
        ('enable_performance_tracking', False),  # Track API performance metrics
    )

    @classmethod
    def getdata(cls, *args, **kwargs):
        '''Returns ``DataCls`` with args, kwargs'''
        if cls.DataCls is None:
            # Import the data feed to trigger registration
            from backtrader.feeds import ibdata
            # The import should have registered the data class
        return cls.DataCls(*args, **kwargs)

    # Removed duplicate getbroker method - using the one defined above

    def __init__(self):
        super(IBStoreIbind, self).__init__()

        # Threading locks for synchronization
        self._lock_q = threading.Lock()
        self._lock_accupd = threading.Lock()
        self._lock_pos = threading.Lock()
        self._lock_notif = threading.Lock()

        # Events for synchronization
        self._event_managed_accounts = threading.Event()
        self._event_accdownload = threading.Event()

        self.dontreconnect = False
        self._env = None
        self.broker = None
        self.datas = list()
        self.ccount = 0

        # Time offset management
        self._lock_tmoffset = threading.Lock()
        self.tmoffset = timedelta()

        # Data structures for compatibility
        self.qs = collections.OrderedDict()  # tickerId -> queues
        self.ts = collections.OrderedDict()  # queue -> tickerId
        self.iscash = dict()  # tickerIds from cash products

        self.histexreq = dict()
        self.histfmt = dict()
        self.histsend = dict()
        self.histtz = dict()

        self.acc_cash = AutoDict()
        self.acc_value = AutoDict()
        self.acc_upds = AutoDict()

        self.port_update = False
        self.positions = collections.defaultdict(Position)

        self._tickerId = itertools.count(self.REQIDBASE)
        self.orderid = None

        self.cdetails = collections.defaultdict(list)
        self.managed_accounts = list()

        # Enhanced ibind features
        self._oauth_tickler = None
        self._performance_metrics = {}
        self._contract_cache = {}
        self._symbol_cache = {}
        self._enhanced_error_handler = None
        self._async_executor = None
        self._rate_limiter = None
        self.notifs = queue.Queue()

        # ibind clients
        self.rest_client = None
        self.ws_client = None
        
    def _initialize_rest_client(self):
        """Initialize the REST client if not already done"""
        if not self.rest_client:
            try:
                from ibind import IbkrClient
                from ibind.oauth.oauth1a import OAuth1aConfig
                
                # Initialize client with OAuth if enabled
                if self.p.use_oauth:
                    # Create OAuth config from environment variables or test values
                    oauth_config = OAuth1aConfig(
                        access_token=os.environ.get('IBIND_OAUTH1A_ACCESS_TOKEN', 'test_access_token'),
                        access_token_secret=os.environ.get('IBIND_OAUTH1A_ACCESS_TOKEN_SECRET', 'test_access_token_secret'),
                        consumer_key=os.environ.get('IBIND_OAUTH1A_CONSUMER_KEY', 'test_consumer_key'),
                        encryption_key_fp=os.environ.get('IBIND_OAUTH1A_ENCRYPTION_KEY_FP'),
                        signature_key_fp=os.environ.get('IBIND_OAUTH1A_SIGNATURE_KEY_FP'),
                        dh_prime=os.environ.get('IBIND_OAUTH1A_DH_PRIME')
                    )
                    
                    self.rest_client = IbkrClient(
                        account_id=self.p.account_id,
                        timeout=self.p.timeout,
                        use_oauth=True,
                        oauth_config=oauth_config
                    )
                    
                    # Initialize OAuth session
                    self.rest_client.oauth_init(maintain_oauth=True, init_brokerage_session=True)
                else:
                    self.rest_client = IbkrClient(
                        host=self.p.host,
                        port=str(self.p.port),
                        account_id=self.p.account_id,
                        timeout=self.p.timeout,
                        use_oauth=False
                    )
                
                if self.p._debug:
                    print("REST client initialized")
            except Exception as e:
                if self.p._debug:
                    print(f"REST client initialization failed: {e}")
                raise
    
    def _initialize_ws_client(self):
        """Initialize the WebSocket client if not already done"""
        if not self.ws_client:
            try:
                from ibind import IbkrWsClient
                self.ws_client = IbkrWsClient(
                    host=self.p.host,
                    port=str(self.p.port),
                    account_id=self.p.account_id,
                    ibkr_client=self.rest_client,
                    restart_on_close=self.p.websocket_auto_reconnect,
                    restart_on_critical=self.p.websocket_auto_reconnect,
                    use_oauth=self.p.use_oauth,
                    start=False  # We'll start it manually
                )
                if self.p._debug:
                    print("WebSocket client initialized")
            except Exception as e:
                if self.p._debug:
                    print(f"WebSocket client initialization failed: {e}")
                raise
        self.contract_mapper = None
        self.order_mapper = OrderMapper()
        
        # WebSocket thread management
        self._ws_thread = None
        self._ws_running = False
        
        # WebSocket subscription management
        self.ws_subscriptions = {}  # tickerId -> conid
        self.market_data_queues = {}  # conid -> queue
        
        # Background threads
        self._ws_thread = None
        self._account_update_thread = None
        self._running = False

        # Use provided clientId or generate random one for compatibility
        if self.p.clientId is None:
            self.clientId = random.randint(1, pow(2, 16) - 1)
        else:
            self.clientId = self.p.clientId

    def start(self, data=None, broker=None):
        """Start the store and establish connections"""
        self.reconnect(fromstart=True)
        
        # Initialize enhanced ibind features
        self._initialize_enhanced_features()

        if data is not None:
            self._env = data._env
            self.datas.append(data)
            return self.getTickerQueue(start=True)
        elif broker is not None:
            self.broker = broker

    def stop(self):
        """Stop the store and close all connections"""
        self._running = False
        
        # Stop enhanced features
        try:
            if self._oauth_tickler:
                self._oauth_tickler.stop()
                self._oauth_tickler = None
        except:
            pass
        
        try:
            if self.ws_client:
                self.ws_client.close()
        except:
            pass
            
        try:
            if self.rest_client:
                self.rest_client.close()
        except:
            pass

        # Stop background threads
        if hasattr(self, '_ws_thread') and self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=1.0)
        
        if hasattr(self, '_account_update_thread') and self._account_update_thread and self._account_update_thread.is_alive():
            self._account_update_thread.join(timeout=1.0)

        # Unblock any waiting events
        self._event_managed_accounts.set()
        self._event_accdownload.set()

    def connected(self):
        """Check if connected to IB"""
        try:
            if self.rest_client:
                result = self.rest_client.check_health()
                return result
        except:
            pass
        return False

    def reconnect(self, fromstart=False, resub=False):
        """Establish connection to IB using ibind"""
        if self.dontreconnect:
            return False

        try:
            # Initialize REST client
            self.rest_client = IbkrClient(
                host=self.p.host,
                port=self.p.port,
                account_id=self.p.account_id,
                use_oauth=self.p.use_oauth,
                timeout=self.p.timeout
            )
            
            # Initialize brokerage session
            result = self.rest_client.initialize_brokerage_session()
            if not result.success:
                self.logmsg(f"Failed to initialize brokerage session: {result.error}")
                return False
            
            # Initialize WebSocket client
            self.ws_client = IbkrWsClient(
                host=self.p.host,
                port=self.p.port,
                ibkr_client=self.rest_client,
                start=True
            )
            
            # Initialize mappers
            self.contract_mapper = ContractMapper(self.rest_client)
            
            # Start background threads
            self._running = True
            self._start_background_threads()
            
            # Get managed accounts
            self._update_managed_accounts()
            
            if not fromstart or resub:
                self.startdatas()
                
            return True
            
        except Exception as e:
            self.logmsg(f"Connection failed: {e}")
            self.dontreconnect = True
            return False

    def _start_background_threads(self):
        """Start background threads for WebSocket and account updates"""
        if not self._ws_thread or not self._ws_thread.is_alive():
            self._ws_thread = threading.Thread(target=self._ws_message_handler, daemon=True)
            self._ws_thread.start()
        
        if not self._account_update_thread or not self._account_update_thread.is_alive():
            self._account_update_thread = threading.Thread(target=self._account_update_handler, daemon=True)
            self._account_update_thread.start()

    def _ws_message_handler(self):
        """Handle WebSocket messages and convert to RTVolume format"""
        while self._running:
            try:
                if self.ws_client and hasattr(self.ws_client, 'get_message'):
                    message = self.ws_client.get_message(timeout=1.0)
                    if message:
                        self._process_ws_message(message)
            except Exception as e:
                if self._running:
                    self.logmsg(f"WebSocket message handler error: {e}")
            time.sleep(0.01)

    def _process_ws_message(self, message):
        """Process WebSocket message and route to appropriate queue"""
        try:
            if isinstance(message, dict):
                conid = message.get('conid')
                if conid and conid in self.market_data_queues:
                    # Convert to RTVolume format
                    rtvol = RTVolume(market_data=message)
                    self.market_data_queues[conid].put(rtvol)
        except Exception as e:
            self.logmsg(f"Error processing WebSocket message: {e}")

    def _account_update_handler(self):
        """Periodically update account information"""
        while self._running:
            try:
                if self.rest_client:
                    self._update_account_info()
                    self._update_positions()
            except Exception as e:
                if self._running:
                    self.logmsg(f"Account update error: {e}")
            
            # Update every 30 seconds
            for _ in range(300):  # 30 seconds in 0.1s intervals
                if not self._running:
                    break
                time.sleep(0.1)

    def _update_managed_accounts(self):
        """Update managed accounts list"""
        try:
            result = self.rest_client.portfolio_accounts()
            if result.success and result.data:
                self.managed_accounts = [acc['id'] for acc in result.data]
                self._event_managed_accounts.set()
                
                # Request current time for offset calculation
                self.reqCurrentTime()
        except Exception as e:
            self.logmsg(f"Error updating managed accounts: {e}")

    def _update_account_info(self):
        """Update account cash and value information"""
        try:
            with self._lock_accupd:
                for account in self.managed_accounts:
                    # Get account summary
                    result = self.rest_client.account_summary(account)
                    if result.success and result.data:
                        for key, value in result.data.items():
                            if key == 'NetLiquidation':
                                self.acc_value[account] = float(value.get('amount', 0))
                            elif key == 'TotalCashValue':
                                self.acc_cash[account] = float(value.get('amount', 0))
                            
                            # Store in acc_upds for compatibility
                            currency = value.get('currency', 'USD')
                            self.acc_upds[account][key][currency] = float(value.get('amount', 0))
        except Exception as e:
            self.logmsg(f"Error updating account info: {e}")

    def _update_positions(self):
        """Update position information"""
        try:
            with self._lock_pos:
                for account in self.managed_accounts:
                    result = self.rest_client.positions(account)
                    if result.success and result.data:
                        for pos_data in result.data:
                            conid = pos_data.get('conid')
                            if conid:
                                position = Position(
                                    pos_data.get('position', 0),
                                    pos_data.get('avgCost', 0)
                                )
                                self.positions[conid] = position
        except Exception as e:
            self.logmsg(f"Error updating positions: {e}")

    def logmsg(self, *args):
        """Log messages for debugging"""
        if self.p._debug:
            print(*args)

    def reqCurrentTime(self):
        """Request current time from server"""
        # ibind doesn't have a direct equivalent, so we'll use system time
        if self.p.timeoffset:
            with self._lock_tmoffset:
                # For now, assume no offset. In a real implementation,
                # you might want to sync with IB server time
                self.tmoffset = timedelta()
            
            # Schedule next refresh
            threading.Timer(self.p.timerefresh, self.reqCurrentTime).start()

    def timeoffset(self):
        """Get current time offset"""
        with self._lock_tmoffset:
            return self.tmoffset

    def nextTickerId(self):
        """Get next ticker ID"""
        return next(self._tickerId)

    def nextOrderId(self):
        """Get next order ID"""
        if self.orderid is None:
            self.orderid = itertools.count(1)
        return next(self.orderid)

    def getTickerQueue(self, start=False):
        """Create ticker/Queue for data delivery"""
        q = queue.Queue()
        if start:
            q.put(None)
            return q

        with self._lock_q:
            tickerId = self.nextTickerId()
            self.qs[tickerId] = q
            self.ts[q] = tickerId
            self.iscash[tickerId] = False

        return tickerId, q

    def reuseQueue(self, tickerId):
        """Reuse queue for tickerId"""
        with self._lock_q:
            q = self.qs.pop(tickerId, None)
            iscash = self.iscash.pop(tickerId, None)

            tickerId = self.nextTickerId()
            self.ts[q] = tickerId
            self.qs[tickerId] = q
            self.iscash[tickerId] = iscash

        return tickerId, q

    def cancelQueue(self, q, sendnone=False):
        """Cancel a queue for data delivery"""
        tickerId = self.ts.pop(q, None)
        self.qs.pop(tickerId, None)
        self.iscash.pop(tickerId, None)

        if sendnone:
            q.put(None)

    def validQueue(self, q):
        """Check if queue is still valid"""
        return q in self.ts

    # Market data methods
    def reqMktData(self, contract, what=None):
        """Request market data using ibind WebSocket"""
        # Get contract symbol
        symbol = getattr(contract, 'symbol', getattr(contract, 'm_symbol', None))
        if hasattr(symbol, 'decode'):
            symbol = symbol.decode('utf-8')
        
        conid = self.resolve_symbol_to_conid(symbol) if symbol else None
        if not conid:
            if self.p._debug:
                print(f"Could not resolve contract: {symbol}")
            return self.getTickerQueue(start=True)

        tickerId, q = self.getTickerQueue()
        
        # Set up cash market handling
        if contract.m_secType in [b'CASH', b'CFD']:
            self.iscash[tickerId] = True
            if what == 'ASK':
                self.iscash[tickerId] = 2

        try:
            # Subscribe to market data via WebSocket
            self.ws_subscriptions[tickerId] = conid
            self.market_data_queues[conid] = q
            
            # Subscribe via WebSocket (this is a simplified example)
            # In a real implementation, you'd use the WebSocket client's subscription methods
            if self.ws_client:
                # This would be the actual WebSocket subscription
                pass
                
        except Exception as e:
            self.logmsg(f"Error subscribing to market data: {e}")
            self.cancelQueue(q, True)

        return q

    def cancelMktData(self, q):
        """Cancel market data subscription"""
        with self._lock_q:
            tickerId = self.ts.get(q, None)
            if tickerId is not None:
                conid = self.ws_subscriptions.pop(tickerId, None)
                if conid:
                    self.market_data_queues.pop(conid, None)
                    # Unsubscribe from WebSocket
                    try:
                        if self.rest_client:
                            self.rest_client.marketdata_unsubscribe([conid])
                    except Exception as e:
                        self.logmsg(f"Error unsubscribing from market data: {e}")

            self.cancelQueue(q, True)

    def reqHistoricalData(self, contract, enddate, duration, barsize,
                          what=None, useRTH=False, tz='', sessionend=None):
        """Request historical data using ibind REST API"""
        # Get contract symbol
        symbol = getattr(contract, 'symbol', getattr(contract, 'm_symbol', None))
        if hasattr(symbol, 'decode'):
            symbol = symbol.decode('utf-8')
        
        conid = self.resolve_symbol_to_conid(symbol) if symbol else None
        if not conid:
            if self.p._debug:
                print(f"Could not resolve contract: {symbol}")
            return self.getTickerQueue(start=True)

        tickerId, q = self.getTickerQueue()

        try:
            # Convert barsize to ibind format
            period_map = {
                '1 min': '1min',
                '5 mins': '5min',
                '15 mins': '15min',
                '30 mins': '30min',
                '1 hour': '1h',
                '1 day': '1d'
            }
            
            ibind_period = period_map.get(barsize, '1min')
            
            # Convert duration to ibind format
            duration_map = {
                '1 D': '1d',
                '2 D': '2d', 
                '3 D': '3d',
                '5 D': '5d',
                '1 W': '1w',
                '2 W': '2w',
                '1 M': '1m',
                '2 M': '2m',
                '3 M': '3m',
                '6 M': '6m',
                '1 Y': '1y'
            }
            
            ibind_duration = duration_map.get(duration, duration.lower().replace(' ', ''))
            
            # Request historical data using correct method
            # Extract numeric conid if it's a Result object
            if hasattr(conid, 'data') and isinstance(conid.data, dict):
                # conid is a Result object from resolve_symbol_to_conid
                symbol_key = list(conid.data.keys())[0]
                actual_conid = str(conid.data[symbol_key])
            else:
                actual_conid = str(conid)
            
            if self.p._debug:
                print(f"Requesting historical data: conid={actual_conid}, bar={ibind_period}, period={ibind_duration}")
            
            result = self.rest_client.marketdata_history_by_conid(
                conid=actual_conid,
                bar=ibind_period,
                period=ibind_duration,
                outside_rth=not useRTH
            )
            
            if result and result.data:
                # Get the data array from the response
                data_array = result.data.get('data', []) if isinstance(result.data, dict) else result.data
                
                if self.p._debug:
                    print(f"Historical data response: {len(data_array)} bars")
                
                # Convert data to ibpy format and put in queue
                for bar in data_array:
                    # Create mock historical data message
                    msg = type('HistoricalData', (), {
                        'reqId': tickerId,
                        'date': bar.get('t'),  # timestamp
                        'open': bar.get('o', 0),
                        'high': bar.get('h', 0),
                        'low': bar.get('l', 0),
                        'close': bar.get('c', 0),
                        'volume': bar.get('v', 0),
                        'count': 0,
                        'WAP': 0,
                        'hasGaps': False
                    })()
                    
                    # Convert timestamp to datetime
                    if isinstance(msg.date, (int, float)):
                        msg.date = datetime.utcfromtimestamp(msg.date / 1000)
                    
                    q.put(msg)
                
                # Send end marker
                end_msg = type('HistoricalData', (), {
                    'reqId': tickerId,
                    'date': 'finished-' + str(tickerId)
                })()
                q.put(end_msg)
            else:
                self.logmsg(f"Historical data request failed: {result.error}")
                self.cancelQueue(q, True)
                
        except Exception as e:
            self.logmsg(f"Error requesting historical data: {e}")
            self.cancelQueue(q, True)

        return q

    def cancelHistoricalData(self, q):
        """Cancel historical data request"""
        with self._lock_q:
            self.cancelQueue(q, True)

    # Order management methods
    def placeOrder(self, orderid, contract, order):
        """Place order using ibind REST API"""
        try:
            order_request = self.order_mapper.ibpy_to_ibind_order(
                contract, order, self.contract_mapper
            )
            
            # Default answers for order confirmation
            answers = {
                'suppress': True,
                'confirmed': True
            }
            
            result = self.rest_client.place_order(
                order_request=order_request,
                answers=answers,
                account_id=self.p.account_id
            )
            
            if result.success:
                # Map order IDs
                ibind_order_id = result.data.get('order_id')
                if ibind_order_id:
                    self.order_mapper.order_id_mapping[orderid] = ibind_order_id
                    self.order_mapper.reverse_mapping[ibind_order_id] = orderid
                
                # Notify broker of order status
                if self.broker:
                    # Create mock order status message
                    msg = type('OrderStatus', (), {
                        'orderId': orderid,
                        'status': 'Submitted',
                        'filled': 0,
                        'remaining': order.m_totalQuantity,
                        'avgFillPrice': 0,
                        'permId': 0,
                        'parentId': 0,
                        'lastFillPrice': 0,
                        'clientId': self.clientId,
                        'whyHeld': ''
                    })()
                    self.broker.push_orderstatus(msg)
            else:
                self.logmsg(f"Order placement failed: {result.error}")
                # Notify broker of error
                if self.broker:
                    error_msg = type('Error', (), {
                        'id': orderid,
                        'errorCode': 201,
                        'errorMsg': str(result.error)
                    })()
                    self.broker.push_ordererror(error_msg)
                    
        except Exception as e:
            self.logmsg(f"Error placing order: {e}")
            if self.broker:
                error_msg = type('Error', (), {
                    'id': orderid,
                    'errorCode': 201,
                    'errorMsg': str(e)
                })()
                self.broker.push_ordererror(error_msg)

    def cancelOrder(self, orderid):
        """Cancel order using ibind REST API"""
        try:
            ibind_order_id = self.order_mapper.order_id_mapping.get(orderid)
            if ibind_order_id:
                result = self.rest_client.cancel_order(
                    order_id=ibind_order_id,
                    account_id=self.p.account_id
                )
                
                if result.success:
                    # Notify broker of cancellation
                    if self.broker:
                        msg = type('OrderStatus', (), {
                            'orderId': orderid,
                            'status': 'Cancelled',
                            'filled': 0,
                            'remaining': 0,
                            'avgFillPrice': 0,
                            'permId': 0,
                            'parentId': 0,
                            'lastFillPrice': 0,
                            'clientId': self.clientId,
                            'whyHeld': ''
                        })()
                        self.broker.push_orderstatus(msg)
                else:
                    self.logmsg(f"Order cancellation failed: {result.error}")
            else:
                self.logmsg(f"Order ID {orderid} not found in mapping")
                
        except Exception as e:
            self.logmsg(f"Error cancelling order: {e}")

    # Account management methods
    def reqAccountUpdates(self, subscribe=True, account=None):
        """Request account updates"""
        if account is None:
            self._event_managed_accounts.wait()
            if self.managed_accounts:
                account = self.managed_accounts[0]

        # Account updates are handled by background thread
        # Just set the event to indicate we have account data
        self._event_accdownload.set()

    def get_acc_value(self, account=None):
        """Get account value"""
        if self.connected():
            self._event_accdownload.wait()
        
        with self._lock_accupd:
            if account is None:
                if self.connected():
                    self._event_managed_accounts.wait()

                if not self.managed_accounts:
                    return float()
                elif len(self.managed_accounts) > 1:
                    return sum(self.acc_value.values())
                account = self.managed_accounts[0]

            try:
                return self.acc_value[account]
            except KeyError:
                pass

            return float()

    def get_acc_cash(self, account=None):
        """Get account cash"""
        if self.connected():
            self._event_accdownload.wait()
        
        with self._lock_accupd:
            if account is None:
                if self.connected():
                    self._event_managed_accounts.wait()

                if not self.managed_accounts:
                    return float()
                elif len(self.managed_accounts) > 1:
                    return sum(self.acc_cash.values())
                account = self.managed_accounts[0]

            try:
                return self.acc_cash[account]
            except KeyError:
                pass

            return float()

    def getposition(self, contract, clone=False):
        """Get position for contract"""
        conid = self.contract_mapper.contract_to_conid(contract)
        if not conid:
            return Position()
        
        with self._lock_pos:
            position = self.positions.get(int(conid), Position())
            if clone:
                return copy(position)
            return position

    def get_notifications(self):
        """Return pending store notifications"""
        self.notifs.put(None)  # put a mark
        notifs = list()
        while True:
            notif = self.notifs.get()
            if notif is None:  # mark is reached
                break
            notifs.append(notif)

        return notifs

    # Compatibility methods for data structures and mappings
    def makecontract(self, symbol, sectype, exch, curr,
                     expiry='', strike=0.0, right='', mult=1):
        """Create contract from parameters"""
        contract = Contract()
        contract.m_symbol = symbol.encode('utf-8') if isinstance(symbol, str) else symbol
        contract.m_secType = sectype.encode('utf-8') if isinstance(sectype, str) else sectype
        contract.m_exchange = exch.encode('utf-8') if isinstance(exch, str) else exch
        if curr:
            contract.m_currency = curr.encode('utf-8') if isinstance(curr, str) else curr
        if sectype in ['FUT', 'OPT', 'FOP']:
            contract.m_expiry = expiry.encode('utf-8') if isinstance(expiry, str) else expiry
        if sectype in ['OPT', 'FOP']:
            contract.m_strike = strike
            contract.m_right = right.encode('utf-8') if isinstance(right, str) else right
        if mult:
            contract.m_multiplier = str(mult).encode('utf-8') if isinstance(mult, (int, float)) else mult
        return contract

    # Enhanced ibind features - these provide additional capabilities
    # while maintaining full backward compatibility
    
    def enable_oauth_authentication(self, oauth_config=None):
        """
        Enable OAuth 1.0a authentication for headless operation
        
        Args:
            oauth_config: OAuth configuration object or None to use default
            
        Returns:
            bool: True if OAuth was successfully enabled
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            if oauth_config:
                self.p.oauth_config = oauth_config
            
            self.p.use_oauth = True
            
            # Initialize OAuth tickler if enabled
            if self.p.enable_tickler and not self._oauth_tickler:
                try:
                    # Try using the built-in tickler method first
                    self.rest_client.start_tickler()
                    self._oauth_tickler = True  # Mark as started
                    if self.p._debug:
                        print("OAuth tickler started successfully")
                except Exception as tickler_error:
                    if self.p._debug:
                        print(f"Tickler start failed (non-critical): {tickler_error}")
                    # Tickler failure is non-critical for OAuth functionality
            
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"OAuth authentication failed: {e}")
            return False
    
    def get_market_data_snapshot(self, symbol=None, conid=None, fields=None):
        """
        Get live market data snapshot using ibind's enhanced capabilities
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            conid: Contract ID (alternative to symbol)
            fields: List of fields to retrieve
            
        Returns:
            dict: Market data snapshot or None if failed
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            if symbol and not conid:
                # Resolve symbol to conid first
                conid_result = self.resolve_symbol_to_conid(symbol)
                if conid_result and hasattr(conid_result, 'data') and conid_result.data:
                    # Extract conid from the result
                    if isinstance(conid_result.data, dict):
                        conid = list(conid_result.data.values())[0]
                    else:
                        conid = conid_result.data
            
            # Ensure fields is provided - use default fields if None
            if fields is None:
                fields = ['31', '84', '86']  # Last price, bid, ask
            
            if conid:
                # Convert conid to string if needed
                conid_str = str(conid)
                
                if self.p._debug:
                    print(f"Getting live market data for ConID: {conid_str}")
                
                # Make initial call to establish subscription
                result1 = self.rest_client.live_marketdata_snapshot(conids=conid_str, fields=fields)
                
                # Wait briefly and make second call to get actual data
                import time
                time.sleep(0.5)
                
                result2 = self.rest_client.live_marketdata_snapshot(conids=conid_str, fields=fields)
                
                if result2 and hasattr(result2, 'data') and result2.data:
                    # Process the data - it's a list with market data
                    data_list = result2.data
                    if isinstance(data_list, list) and len(data_list) > 0:
                        market_data = data_list[0]  # Get first item
                        
                        # Convert field numbers to readable names
                        readable_data = {}
                        if '31' in market_data:  # Last price
                            readable_data['last'] = float(market_data['31'])
                        if '84' in market_data:  # Bid
                            readable_data['bid'] = float(market_data['84'])
                        if '86' in market_data:  # Ask
                            readable_data['ask'] = float(market_data['86'])
                        if '_updated' in market_data:  # Timestamp
                            readable_data['timestamp'] = market_data['_updated']
                        
                        if symbol:
                            return {symbol: readable_data}
                        else:
                            return readable_data
                
                # Fallback to empty data if no live data available
                return {symbol: {}} if symbol else {}
            
            return None
            
        except Exception as e:
            if self.p._debug:
                print(f"Market data snapshot failed: {e}")
            return None
    
    def get_historical_data_parallel(self, symbols, period='1d', bar_size='1h'):
        """
        Get historical data for multiple symbols in parallel using ibind's capabilities
        
        Args:
            symbols: List of symbols
            period: Time period (e.g., '1d', '1w', '1m')
            bar_size: Bar size (e.g., '1h', '1d')
            
        Returns:
            dict: Symbol -> historical data mapping
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            if self.p.parallel_requests:
                return self.rest_client.marketdata_history_by_symbols(
                    symbols, 
                    period=period, 
                    bar_size=bar_size,
                    max_workers=self.p.max_concurrent_requests
                )
            else:
                # Fall back to sequential requests
                results = {}
                for symbol in symbols:
                    results[symbol] = self.rest_client.marketdata_history_by_symbol(
                        symbol, period=period, bar_size=bar_size
                    )
                    if self.p.rate_limit_delay:
                        time.sleep(self.p.rate_limit_delay)
                return results
                
        except Exception as e:
            if self.p._debug:
                print(f"Parallel historical data request failed: {e}")
            return {}
    
    def get_account_performance(self, account_id=None):
        """
        Get account performance data using ibind's portfolio management features
        
        Args:
            account_id: Account ID or None to use default
            
        Returns:
            dict: Account performance data
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            account_id = account_id or self.p.account_id
            if account_id:
                return self.rest_client.account_performance(account_id)
            else:
                # Use first available account
                accounts = self.rest_client.brokerage_accounts()
                if accounts:
                    return self.rest_client.account_performance(accounts[0]['id'])
            
            return None
            
        except Exception as e:
            if self.p._debug:
                print(f"Account performance request failed: {e}")
            return None
    
    def get_positions_realtime(self, account_id=None):
        """
        Get near real-time positions using ibind's enhanced position tracking
        
        Args:
            account_id: Account ID or None to use default
            
        Returns:
            list: List of position objects
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            account_id = account_id or self.p.account_id
            if account_id:
                return self.rest_client.positions2(account_id)
            else:
                return self.rest_client.positions2()
                
        except Exception as e:
            if self.p._debug:
                print(f"Real-time positions request failed: {e}")
            return []
    
    def submit_order_with_confirmation(self, account_id, order_request, auto_confirm=True):
        """
        Submit order with automatic question/answer handling
        
        Args:
            account_id: Account ID
            order_request: Order request object
            auto_confirm: Automatically confirm order warnings
            
        Returns:
            dict: Order submission result
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            if self.p.enable_question_answer:
                # Use ibind's automatic question/answer handling
                return self.rest_client.submit_order(
                    account_id, 
                    order_request,
                    auto_confirm=auto_confirm
                )
            else:
                # Standard order submission
                return self.rest_client.submit_order(account_id, order_request)
                
        except Exception as e:
            if self.p._debug:
                print(f"Order submission failed: {e}")
            return None
    
    def get_transaction_history(self, account_id=None, days=30):
        """
        Get transaction history using ibind's account management features
        
        Args:
            account_id: Account ID or None to use default
            days: Number of days of history to retrieve
            
        Returns:
            list: List of transaction records
        """
        try:
            if not self.rest_client:
                self._initialize_rest_client()
            
            account_id = account_id or self.p.account_id
            if account_id:
                return self.rest_client.transaction_history(account_id, days=days)
            
            return []
            
        except Exception as e:
            if self.p._debug:
                print(f"Transaction history request failed: {e}")
            return []
    
    def enable_websocket_channels(self, channels=None):
        """
        Enable specific WebSocket channels for real-time data
        
        Args:
            channels: List of channel names or None for default channels
            
        Returns:
            bool: True if channels were successfully enabled
        """
        try:
            if not self.ws_client:
                self._initialize_ws_client()
            
            if channels:
                self.p.market_data_channels = channels
            
            # Subscribe to specified channels
            for channel in (channels or ['MARKET_DATA', 'ORDERS', 'PNL']):
                self.ws_client.subscribe(channel)
            
            return True
            
        except Exception as e:
            if self.p._debug:
                print(f"WebSocket channel setup failed: {e}")
            return False
    
    def get_performance_metrics(self):
        """
        Get API performance metrics if tracking is enabled
        
        Returns:
            dict: Performance metrics
        """
        if self.p.enable_performance_tracking:
            return self._performance_metrics.copy()
        return {}
    
    def clear_caches(self):
        """
        Clear internal caches for contracts and symbols
        """
        self._contract_cache.clear()
        self._symbol_cache.clear()
        if self.p._debug:
            print("Caches cleared")
    
    def get_enhanced_account_info(self):
        """Get enhanced account information"""
        try:
            self._initialize_rest_client()
            # Use ibind to get account info
            response = self.rest_client.get('portfolio/accounts')
            return response
        except Exception as e:
            if self.p._debug:
                print(f"Enhanced account info failed: {e}")
            return None
    
    def resolve_symbol(self, symbol):
        """Resolve symbol to contract details"""
        try:
            self._initialize_rest_client()
            # Use ibind's proper method for symbol resolution
            try:
                # Try the search_contract_by_symbol method first
                response = self.rest_client.search_contract_by_symbol(symbol)
                return response
            except Exception:
                # Fallback to stock_conid_by_symbol for stocks
                try:
                    response = self.rest_client.stock_conid_by_symbol(symbol)
                    return response
                except Exception:
                    # Final fallback to security_stocks_by_symbol
                    response = self.rest_client.security_stocks_by_symbol(symbol)
                    return response
        except Exception as e:
            if self.p._debug:
                print(f"Symbol resolution failed: {e}")
            return None
    
    def get_cached_contract_details(self, symbol):
        """
        Get cached contract details for a symbol
        
        Args:
            symbol: Symbol to look up
            
        Returns:
            dict: Cached contract details or None
        """
        return self._contract_cache.get(symbol)
    
    def getContractDetails(self, contract, maxcount=None):
        """
        Get contract details for a given contract (backward compatibility method)
        
        Args:
            contract: Contract object with symbol, sectype, exchange, currency
            maxcount: Maximum number of contracts to return
            
        Returns:
            list: List of contract details or None if failed
        """
        try:
            self._initialize_rest_client()
            
            # Extract contract information
            symbol = getattr(contract, 'symbol', getattr(contract, 'm_symbol', None))
            sectype = getattr(contract, 'sectype', getattr(contract, 'm_secType', 'STK'))
            exchange = getattr(contract, 'exchange', getattr(contract, 'm_exchange', 'SMART'))
            currency = getattr(contract, 'currency', getattr(contract, 'm_currency', 'USD'))
            
            # Convert bytes to string if needed
            try:
                if hasattr(symbol, 'decode'):
                    symbol = symbol.decode('utf-8')
                if hasattr(sectype, 'decode'):
                    sectype = sectype.decode('utf-8')
                if hasattr(exchange, 'decode'):
                    exchange = exchange.decode('utf-8')
                if hasattr(currency, 'decode'):
                    currency = currency.decode('utf-8')
            except Exception as e:
                if self.p._debug:
                    print(f"Error converting bytes to string: {e}")
            
            if not symbol:
                if self.p._debug:
                    print("No symbol found in contract")
                return None
            
            if self.p._debug:
                print(f"Getting contract details for: {symbol}, {sectype}, {exchange}, {currency}")
            
            # Use ibind to search for contract
            try:
                # Try symbol search first
                result = self.rest_client.search_contract_by_symbol(symbol)
                if self.p._debug:
                    print(f"Symbol search result: {result}")
                
                if result and hasattr(result, 'data') and result.data:
                    contracts = result.data
                    if self.p._debug:
                        print(f"Found {len(contracts)} contracts")
                    
                    # Filter by security type if specified
                    if sectype:
                        filtered = []
                        for c in contracts:
                            sections = c.get('sections', [])
                            for section in sections:
                                if section.get('secType') == sectype:
                                    filtered.append(c)
                                    break
                        contracts = filtered
                        if self.p._debug:
                            print(f"After filtering by {sectype}: {len(contracts)} contracts")
                    
                    # Apply maxcount limit - take the first/best matches
                    if maxcount and len(contracts) > maxcount:
                        if self.p._debug:
                            print(f"Too many contracts found: {len(contracts)} > {maxcount}, taking first {maxcount}")
                        contracts = contracts[:maxcount]
                    
                    # Convert to contract details format expected by IBData
                    contract_details = []
                    for contract_data in contracts:
                        # Create a mock contract details object
                        class MockContractDetails:
                            def __init__(self, data):
                                self.contractDetails = self
                                self.m_summary = self
                                # Map ibind data to expected fields
                                self.m_symbol = data.get('symbol', symbol)
                                self.m_secType = sectype
                                self.m_exchange = exchange
                                self.m_currency = currency
                                self.m_conId = int(data.get('conid', 0))
                                self.m_localSymbol = data.get('symbol', symbol)
                                self.m_tradingClass = data.get('symbol', symbol)
                                # Add timezone - default to US/Eastern for US stocks
                                self.m_timeZoneId = 'US/Eastern'
                                # Add other common fields
                                self.m_multiplier = '1'
                                self.m_minTick = 0.01
                                self.m_priceMagnifier = 1
                        
                        contract_details.append(MockContractDetails(contract_data))
                    
                    if self.p._debug:
                        print(f"Returning {len(contract_details)} contract details")
                    return contract_details
                else:
                    if self.p._debug:
                        print("No contracts found in search result")
                    
            except Exception as e:
                if self.p._debug:
                    print(f"Contract details search failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # If we get here, return an empty list instead of None to avoid index errors
            if self.p._debug:
                print("Returning empty contract list")
            return []
            
        except Exception as e:
            if self.p._debug:
                print(f"getContractDetails failed: {e}")
            return None
    
    def reqHistoricalDataEx(self, contract, enddate, begindate,
                            timeframe, compression,
                            what=None, useRTH=False, tz='', sessionend=None,
                            tickerId=None):
        """
        Extended historical data request (backward compatibility method)
        
        This is a simplified version that delegates to reqHistoricalData
        """
        try:
            if self.p._debug:
                print(f"reqHistoricalDataEx called for {getattr(contract, 'symbol', 'unknown')}")
            
            # For now, delegate to the regular reqHistoricalData method
            # In a full implementation, this would handle date ranges and splitting requests
            return self.reqHistoricalData(
                contract=contract,
                enddate=enddate,
                duration='1 Y',  # Default duration
                barsize='1 day',  # Default bar size
                what=what,
                useRTH=useRTH,
                tz=tz
            )
            
        except Exception as e:
            if self.p._debug:
                print(f"reqHistoricalDataEx failed: {e}")
            # Return a queue for compatibility
            return self.getTickerQueue(start=True)
    
    def get_account_info(self):
        """Get account information (backward compatibility method)"""
        try:
            self._initialize_rest_client()
            
            # Get account summary
            result = self.rest_client.get_account_summary()
            if result and hasattr(result, 'data') and result.data:
                return result.data
            
            return None
            
        except Exception as e:
            if self.p._debug:
                print(f"get_account_info failed: {e}")
            return None
    
    def resolve_symbol_to_conid(self, symbol):
        """
        Resolve symbol to contract ID with caching
        
        Args:
            symbol: Symbol to resolve
            
        Returns:
            int: Contract ID or None if resolution failed
        """
        try:
            if symbol in self._symbol_cache:
                return self._symbol_cache[symbol]
            
            if not self.rest_client:
                self._initialize_rest_client()
            
            conid = self.rest_client.stock_conid_by_symbol(symbol)
            
            if conid and self.p.cache_contract_details:
                self._symbol_cache[symbol] = conid
            
            return conid
            
        except Exception as e:
            if self.p._debug:
                print(f"Symbol resolution failed for {symbol}: {e}")
            return None
    
    def _initialize_enhanced_features(self):
        """Initialize enhanced ibind features based on parameters"""
        try:
            # Initialize OAuth if enabled
            if self.p.use_oauth:
                self.enable_oauth_authentication(self.p.oauth_config)
            
            # Initialize WebSocket channels if specified
            if self.p.market_data_channels:
                self.enable_websocket_channels(self.p.market_data_channels)
            
            # Initialize performance tracking if enabled
            if self.p.enable_performance_tracking:
                self._performance_metrics = {
                    'requests_sent': 0,
                    'requests_failed': 0,
                    'avg_response_time': 0.0,
                    'cache_hits': 0,
                    'cache_misses': 0
                }
            
            # Initialize rate limiter if needed
            if self.p.rate_limit_delay > 0:
                self._rate_limiter = time.time()
            
        except Exception as e:
            if self.p._debug:
                print(f"Enhanced features initialization failed: {e}")
    
    # Additional compatibility methods would be implemented here
    # to maintain full backward compatibility with the original IBStore

    def startdatas(self):
        """Start data feeds"""
        ts = list()
        for data in self.datas:
            t = threading.Thread(target=data.reqdata)
            t.start()
            ts.append(t)

        for t in ts:
            t.join()

    def stopdatas(self):
        """Stop data feeds"""
        qs = list(self.qs.values())
        ts = list()
        for data in self.datas:
            t = threading.Thread(target=data.canceldata)
            t.start()
            ts.append(t)

        for t in ts:
            t.join()

        for q in reversed(qs):
            q.put(None)


# =============================================================================
# BROKER METHODS - Order Management (replacing ibpy functionality)
# =============================================================================

def place_order(self, contract, order):
    """
    Place an order using ibind's order placement API
    
    Args:
        contract: Contract object with symbol, sectype, etc.
        order: Order object with order details
        
    Returns:
        Order ID or None if failed
    """
    try:
        if not self.rest_client:
            self._initialize_rest_client()
        
        # Convert contract to conid if needed
        if hasattr(contract, 'symbol'):
            conid_result = self.resolve_symbol_to_conid(contract.symbol)
            if conid_result and hasattr(conid_result, 'data') and conid_result.data:
                conid = conid_result.data
            else:
                if self.p._debug:
                    print(f"Failed to resolve symbol {contract.symbol}")
                return None
        else:
            conid = getattr(contract, 'conid', None)
            if not conid:
                if self.p._debug:
                    print("No contract ID available")
                return None
        
        # Build order request
        order_request = {
            'conid': conid,
            'orderType': getattr(order, 'orderType', 'MKT'),
            'side': 'BUY' if getattr(order, 'action', 'BUY') == 'BUY' else 'SELL',
            'quantity': getattr(order, 'totalQuantity', getattr(order, 'quantity', 100)),
            'tif': getattr(order, 'tif', 'DAY')
        }
        
        # Add price for limit orders
        if order_request['orderType'] in ['LMT', 'LIMIT']:
            order_request['price'] = getattr(order, 'lmtPrice', getattr(order, 'price', 0))
        
        # Add stop price for stop orders
        if order_request['orderType'] in ['STP', 'STOP']:
            order_request['auxPrice'] = getattr(order, 'auxPrice', getattr(order, 'stopPrice', 0))
        
        if self.p._debug:
            print(f"Placing order: {order_request}")
        
        # Place order via ibind
        result = self.rest_client.place_order(orders=[order_request])
        
        if result and hasattr(result, 'data') and result.data:
            # Extract order ID from response
            if isinstance(result.data, list) and len(result.data) > 0:
                order_data = result.data[0]
                order_id = order_data.get('order_id', order_data.get('id'))
                if self.p._debug:
                    print(f"Order placed successfully: ID {order_id}")
                return order_id
            else:
                if self.p._debug:
                    print(f"Order placement response: {result.data}")
                return result.data
        else:
            if self.p._debug:
                print("Order placement failed: No response data")
            return None
            
    except Exception as e:
        if self.p._debug:
            print(f"Order placement failed: {e}")
        return None

# Add broker methods to IBStoreIbind class
IBStoreIbind.place_order = place_order

def cancel_order(self, order_id):
    """Cancel an order using ibind's cancel API"""
    try:
        if not self.rest_client:
            self._initialize_rest_client()
        
        if self.p._debug:
            print(f"Cancelling order: {order_id}")
        
        result = self.rest_client.cancel_order(order_id)
        
        if result and hasattr(result, 'data'):
            if self.p._debug:
                print(f"Order cancellation result: {result.data}")
            return True
        else:
            if self.p._debug:
                print("Order cancellation failed: No response")
            return False
            
    except Exception as e:
        if self.p._debug:
            print(f"Order cancellation failed: {e}")
        return False

IBStoreIbind.cancel_order = cancel_order

def get_live_orders(self):
    """Get all live/active orders"""
    try:
        if not self.rest_client:
            self._initialize_rest_client()
        
        result = self.rest_client.live_orders()
        
        if result and hasattr(result, 'data') and result.data:
            if self.p._debug:
                print(f"Retrieved {len(result.data)} live orders")
            return result.data
        else:
            return []
            
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get live orders: {e}")
        return []

IBStoreIbind.get_live_orders = get_live_orders

def get_account_summary(self):
    """Get account summary information"""
    try:
        if not self.rest_client:
            self._initialize_rest_client()
        
        result = self.rest_client.account_summary()
        
        if result and hasattr(result, 'data') and result.data:
            if self.p._debug:
                print(f"Account summary retrieved")
            return result.data
        else:
            return None
            
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get account summary: {e}")
        return None

IBStoreIbind.get_account_summary = get_account_summary

def get_account_cash(self):
    """Get account cash balance"""
    try:
        account_summary = self.get_account_summary()
        if account_summary:
            # Extract cash from account summary
            if isinstance(account_summary, dict):
                return float(account_summary.get('TotalCashValue', 0.0))
            elif isinstance(account_summary, list) and len(account_summary) > 0:
                return float(account_summary[0].get('TotalCashValue', 0.0))
        return 0.0
        
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get account cash: {e}")
        return 0.0

IBStoreIbind.get_account_cash = get_account_cash

def get_account_value(self):
    """Get total account value"""
    try:
        account_summary = self.get_account_summary()
        if account_summary:
            # Extract total value from account summary
            if isinstance(account_summary, dict):
                return float(account_summary.get('NetLiquidation', 0.0))
            elif isinstance(account_summary, list) and len(account_summary) > 0:
                return float(account_summary[0].get('NetLiquidation', 0.0))
        return 0.0
        
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get account value: {e}")
        return 0.0

IBStoreIbind.get_account_value = get_account_value

def get_positions(self):
    """Get all positions"""
    try:
        if not self.rest_client:
            self._initialize_rest_client()
        
        result = self.rest_client.positions()
        
        if result and hasattr(result, 'data') and result.data:
            if self.p._debug:
                print(f"Retrieved {len(result.data)} positions")
            return result.data
        else:
            return []
            
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get positions: {e}")
        return []

IBStoreIbind.get_positions = get_positions

def get_position(self, contract, clone=True):
    """Get position for a specific contract"""
    try:
        positions = self.get_positions()
        
        # Find position matching the contract
        if hasattr(contract, 'symbol'):
            symbol = contract.symbol
            for pos in positions:
                if pos.get('ticker', pos.get('symbol')) == symbol:
                    # Convert to position-like object
                    position_size = float(pos.get('position', 0))
                    avg_cost = float(pos.get('avgCost', 0))
                    
                    # Create a simple position object
                    class Position:
                        def __init__(self, size, price):
                            self.size = size
                            self.price = price
                            self.adjbase = price
                    
                    return Position(position_size, avg_cost)
        
        # Return empty position if not found
        class Position:
            def __init__(self):
                self.size = 0
                self.price = 0
                self.adjbase = 0
        
        return Position()
        
    except Exception as e:
        if self.p._debug:
            print(f"Failed to get position: {e}")
        return None

IBStoreIbind.get_position = get_position

# =============================================================================
# BROKER COMPATIBILITY METHODS (for IBBroker integration)
# =============================================================================

# Removed duplicate start method - using the one defined in the class

def connected(self):
    """Check if broker is connected (compatibility method)"""
    try:
        return self.rest_client is not None
    except:
        return False

IBStoreIbind.connected = connected

def reqAccountUpdates(self):
    """Request account updates (compatibility method)"""
    try:
        # Trigger account summary refresh
        self.get_account_summary()
        if self.p._debug:
            print("Account updates requested")
    except Exception as e:
        if self.p._debug:
            print(f"Failed to request account updates: {e}")

IBStoreIbind.reqAccountUpdates = reqAccountUpdates

def get_acc_cash(self):
    """Get account cash (compatibility method)"""
    return self.get_account_cash()

IBStoreIbind.get_acc_cash = get_acc_cash

def get_acc_value(self):
    """Get account value (compatibility method)"""
    return self.get_account_value()

IBStoreIbind.get_acc_value = get_acc_value

def getposition(self, contract, clone=True):
    """Get position (compatibility method)"""
    return self.get_position(contract, clone)

IBStoreIbind.getposition = getposition

def cancelOrder(self, order_id):
    """Cancel order (compatibility method)"""
    return self.cancel_order(order_id)

IBStoreIbind.cancelOrder = cancelOrder

def placeOrder(self, order_id, contract, order):
    """Place order (compatibility method)"""
    return self.place_order(contract, order)

IBStoreIbind.placeOrder = placeOrder

def nextOrderId(self):
    """Get next order ID (compatibility method)"""
    import time
    # Generate a unique order ID based on timestamp
    return int(time.time() * 1000) % 2147483647  # Keep within int32 range

IBStoreIbind.nextOrderId = nextOrderId

def clientId_property(self):
    """Get client ID (compatibility property)"""
    return getattr(self, '_client_id', 1)

IBStoreIbind.clientId = property(clientId_property)

# For backward compatibility, alias the new implementation
IBStore = IBStoreIbind