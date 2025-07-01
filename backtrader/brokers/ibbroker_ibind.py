#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2023 Daniel Rodriguez
# Migrated from ibpy to ibind for better maintainability and modern Python support
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

from copy import copy
from datetime import date, datetime, timedelta
import threading
import uuid

# Import our new ibind-based order classes instead of ibpy
from .iborder_ibind import IBOrder, IBOrderState

from backtrader.feed import DataBase
from backtrader import (TimeFrame, num2date, date2num, BrokerBase,
                        Order, OrderBase, OrderData)
from backtrader.utils.py3 import bytes, bstr, with_metaclass, queue, MAXFLOAT
from backtrader.metabase import MetaParams
from backtrader.comminfo import CommInfoBase
from backtrader.position import Position
from backtrader.stores import ibstore
from backtrader.utils import AutoDict, AutoOrderedDict
from backtrader.comminfo import CommInfoBase

bytes = bstr  # py2/3 compatibility


class IBBroker(with_metaclass(MetaParams, BrokerBase)):
    '''
    Broker implementation for Interactive Brokers using ibind instead of ibpy.
    
    This broker integrates with the new IBStore implementation that uses
    ibind for OAuth-based authentication and modern API access.
    '''

    params = (
        ('use_positions', True),  # use IB reported positions
        ('_debug', False),  # enable debug output
    )

    def __init__(self, **kwargs):
        super(IBBroker, self).__init__()

        self.ib = ibstore.IBStore(**kwargs)  # Use the new ibind-based store

        self.startingcash = self.cash = 0.0
        self.startingvalue = self.value = 0.0
        self.positions = AutoDict()
        self.orderid = None
        self.notifs = queue.Queue()  # holds orders which are notified

        self.opending = AutoDict()  # pending transmission
        self.brackets = AutoDict()  # confirmed brackets

        self.orderbyid = AutoDict()  # orders by order id
        self.executions = AutoDict()  # notified executions

        self.ordstatus = AutoDict()  # orders by status
        self.ordstatus[Order.Submitted] = AutoDict()
        self.ordstatus[Order.Accepted] = AutoDict()
        self.ordstatus[Order.Partial] = AutoDict()
        self.ordstatus[Order.Completed] = AutoDict()
        self.ordstatus[Order.Canceled] = AutoDict()
        self.ordstatus[Order.Expired] = AutoDict()
        self.ordstatus[Order.Rejected] = AutoDict()

    def start(self):
        super(IBBroker, self).start()
        self.ib.start(broker=self)

        if self.ib.connected():
            self.ib.reqAccountUpdates()
            self.startingcash = self.cash = self.ib.get_acc_cash()
            self.startingvalue = self.value = self.ib.get_acc_value()

    def stop(self):
        super(IBBroker, self).stop()
        self.ib.stop()

    def getcash(self):
        # This call cannot block if no answer is available from ib
        self.cash = self.ib.get_acc_cash()
        return self.cash

    def getvalue(self, datas=None):
        self.value = self.ib.get_acc_value()
        return self.value

    def getposition(self, data, clone=True):
        # return self.o.position
        return self.ib.getposition(data.tradecontract, clone=clone)

    def orderstatus(self, order):
        try:
            o = self.orderbyid[order.ref]
        except KeyError:
            o = order

        return o.status

    def _submit(self, oref, transmit, parent):
        try:
            order = self.opending.pop(oref)
        except KeyError:
            order = self.orderbyid[oref]
            transmit = True

        order.m_transmit = transmit
        order.m_parentId = parent
        order.m_orderId = oref

        # Use the new ibind-based order placement
        self.ib.placeOrder(order.m_orderId, order.data.tradecontract, order)

        if not transmit:
            self.opending[order.m_parentId] = order

        return order

    def _cancel(self, order):
        # Use the new ibind-based order cancellation
        self.ib.cancelOrder(order.m_orderId)

    def cancel(self, order):
        if order.status == Order.Cancelled:
            return
        return self._cancel(order)

    def buy(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            parent=None, transmit=True,
            **kwargs):

        order = self.createorder(owner, data, size, price, plimit,
                                exectype, valid, oco, parent, transmit,
                                tradeid, **kwargs)

        order.addinfo(**kwargs)
        order.m_action = 'BUY'
        return self.submit(order)

    def sell(self, owner, data, size, price=None, plimit=None,
             exectype=None, valid=None, tradeid=0, oco=None,
             trailamount=None, trailpercent=None,
             parent=None, transmit=True,
             **kwargs):

        order = self.createorder(owner, data, size, price, plimit,
                                exectype, valid, oco, parent, transmit,
                                tradeid, **kwargs)

        order.addinfo(**kwargs)
        order.m_action = 'SELL'
        return self.submit(order)

    def createorder(self, owner, data, size, price, plimit, exectype, valid,
                    oco, parent, transmit, tradeid, **kwargs):

        order = IBOrder(action=None, **kwargs)
        order.owner = owner
        order.data = data
        order.size = size
        order.price = price
        order.pricelimit = plimit

        # Map Backtrader order types to IB order types
        if exectype is None:
            exectype = Order.Market

        if exectype == Order.Market:
            order.m_orderType = 'MKT'
        elif exectype == Order.Limit:
            order.m_orderType = 'LMT'
            order.m_lmtPrice = price
        elif exectype == Order.Stop:
            order.m_orderType = 'STP'
            order.m_auxPrice = price
        elif exectype == Order.StopLimit:
            order.m_orderType = 'STP LMT'
            order.m_lmtPrice = plimit
            order.m_auxPrice = price

        order.m_totalQuantity = abs(size)
        order.m_lmtPrice = order.m_lmtPrice or 0.0
        order.m_auxPrice = order.m_auxPrice or 0.0

        # Set time in force
        if valid is None:
            order.m_tif = 'DAY'
        elif isinstance(valid, datetime):
            order.m_tif = 'GTD'
            order.m_goodTillDate = valid.strftime('%Y%m%d %H:%M:%S')
        elif valid == Order.DAY:
            order.m_tif = 'DAY'
        elif valid == Order.GTC:
            order.m_tif = 'GTC'

        # Set order IDs
        order.m_clientId = self.ib.clientId
        order.m_orderId = self.ib.nextOrderId()

        # Store order reference
        order.ref = order.m_orderId
        self.orderbyid[order.ref] = order

        return order

    def submit(self, order):
        if order.oco:
            self._bracketize(order, buy=order.isbuy())
            return order

        order.submit(self)
        self.notifs.put(order.clone())

        if order.transmit:
            return self._submit(order.ref, order.transmit, order.parent)

        # Keep the order in pending queue
        self.opending[order.ref] = order
        return order

    def _bracketize(self, order, buy):
        # Bracket order implementation
        # This is a simplified version - full implementation would handle
        # complex bracket scenarios
        porder = order.parent
        if porder is None:
            # Main order
            order.addinfo(oco=order.oco)
            order.transmit = False
            porder = self._submit(order.ref, False, None)
            
            # Create stop loss order
            if hasattr(order, 'stopprice') and order.stopprice:
                stop_order = self.createorder(
                    order.owner, order.data, -order.size,
                    order.stopprice, None, Order.Stop,
                    None, None, porder, False, 0
                )
                stop_order.m_action = 'SELL' if buy else 'BUY'
                stop_order.m_parentId = porder.m_orderId
                self._submit(stop_order.ref, False, porder.m_orderId)
            
            # Create take profit order
            if hasattr(order, 'limitprice') and order.limitprice:
                limit_order = self.createorder(
                    order.owner, order.data, -order.size,
                    order.limitprice, None, Order.Limit,
                    None, None, porder, True, 0  # Transmit the last order
                )
                limit_order.m_action = 'SELL' if buy else 'BUY'
                limit_order.m_parentId = porder.m_orderId
                self._submit(limit_order.ref, True, porder.m_orderId)

        return order

    def next(self):
        while True:
            try:
                msg = self.notifs.get(False)
            except queue.Empty:
                return None

            if msg is None:
                return None

            order = msg

            # Process order status updates
            if hasattr(order, 'status'):
                if order.status == Order.Submitted:
                    order.submit()
                elif order.status == Order.Accepted:
                    order.accept()
                elif order.status == Order.Partial:
                    order.partial()
                elif order.status == Order.Completed:
                    order.complete()
                elif order.status == Order.Canceled:
                    order.cancel()
                elif order.status == Order.Expired:
                    order.expire()
                elif order.status == Order.Rejected:
                    order.reject()

            self.notify(order)

    def notify(self, order):
        self.notifs.put(order.clone())

    # Event handlers for IB callbacks (these would be called by the store)
    def push_orderstatus(self, msg):
        """Handle order status updates from IB"""
        try:
            order = self.orderbyid[msg.orderId]
            
            # Map IB status to Backtrader status
            status_map = {
                'Submitted': Order.Submitted,
                'PreSubmitted': Order.Submitted,
                'PendingSubmit': Order.Submitted,
                'Filled': Order.Completed,
                'PartiallyFilled': Order.Partial,
                'Cancelled': Order.Canceled,
                'PendingCancel': Order.Canceled,
                'Rejected': Order.Rejected,
                'Inactive': Order.Rejected,
            }
            
            bt_status = status_map.get(msg.status, Order.Rejected)
            order.status = bt_status
            
            # Update order state
            if hasattr(msg, 'filled'):
                order.executed.size = msg.filled
            if hasattr(msg, 'remaining'):
                order.executed.remsize = msg.remaining
            if hasattr(msg, 'avgFillPrice'):
                order.executed.price = msg.avgFillPrice
            if hasattr(msg, 'commission'):
                order.executed.comm = msg.commission
            
            self.notify(order)
            
        except KeyError:
            # Order not found - might be from a different session
            pass

    def push_execution(self, msg):
        """Handle execution reports from IB"""
        try:
            order = self.orderbyid[msg.orderId]
            
            # Update execution details
            if hasattr(msg, 'shares'):
                order.executed.size += msg.shares
            if hasattr(msg, 'price'):
                order.executed.price = msg.price
            if hasattr(msg, 'commission'):
                order.executed.comm += msg.commission
            
            # Calculate remaining size
            order.executed.remsize = order.size - order.executed.size
            
            # Determine order status
            if order.executed.remsize <= 0:
                order.status = Order.Completed
            else:
                order.status = Order.Partial
            
            self.notify(order)
            
        except KeyError:
            # Order not found
            pass

    def push_commissionreport(self, msg):
        """Handle commission reports from IB"""
        try:
            # Find order by execution ID
            for order in self.orderbyid.values():
                if hasattr(msg, 'execId') and hasattr(order, 'execId'):
                    if order.execId == msg.execId:
                        if hasattr(msg, 'commission'):
                            order.executed.comm = msg.commission
                        if hasattr(msg, 'currency'):
                            order.executed.commcurrency = msg.currency
                        self.notify(order)
                        break
        except:
            pass

    def push_portupdate(self, msg):
        """Handle portfolio updates from IB"""
        # Update account values
        if hasattr(msg, 'key') and hasattr(msg, 'value'):
            if msg.key == 'TotalCashValue':
                self.cash = float(msg.value)
            elif msg.key == 'NetLiquidation':
                self.value = float(msg.value)

    def push_posupdate(self, msg):
        """Handle position updates from IB"""
        # Update position information
        # This would be called when position data is received from IB
        pass

    def push_accountupdate(self, msg):
        """Handle account updates from IB"""
        # Update account information
        if hasattr(msg, 'key') and hasattr(msg, 'value'):
            if msg.key == 'TotalCashValue':
                self.cash = float(msg.value)
            elif msg.key == 'NetLiquidation':
                self.value = float(msg.value)


# For backward compatibility
IBBrokerIbind = IBBroker