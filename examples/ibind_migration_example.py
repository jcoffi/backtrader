#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
IBStore Migration Example: From ibpy to ibind

This example demonstrates how to use the new ibind-based IBStore
implementation as a drop-in replacement for the legacy ibpy version.

The example shows:
1. Basic setup and configuration
2. Data feed creation
3. Strategy implementation
4. Backward compatibility features

Note: This example can run without IB Gateway for demonstration purposes.
"""

import sys
import os
from datetime import datetime, timedelta

# Add backtrader to path if running from examples directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import backtrader as bt
from backtrader.stores import ibstore


def demonstrate_basic_usage():
    """Demonstrate basic usage of the migrated IBStore"""
    print("=" * 60)
    print("Basic IBStore Usage with ibind")
    print("=" * 60)
    
    print("1. Creating IBStore...")
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,  # IB Gateway Web API port (changed from 7496)
        clientId=1,
        account_id=None,  # Optional: specify account
        _debug=True
    )
    
    print(f"   Store type: {type(store)}")
    print(f"   Host: {store.p.host}")
    print(f"   Port: {store.p.port}")
    print(f"   Client ID: {store.clientId}")
    
    print("\n2. Creating contract...")
    contract = store.makecontract(
        symbol='AAPL',
        sectype='STK',
        exch='SMART',
        curr='USD'
    )
    
    print(f"   Symbol: {contract.m_symbol.decode()}")
    print(f"   Security Type: {contract.m_secType.decode()}")
    print(f"   Exchange: {contract.m_exchange.decode()}")
    print(f"   Currency: {contract.m_currency.decode()}")
    
    print("\n3. Testing queue management...")
    tickerId, q = store.getTickerQueue()
    print(f"   Ticker ID: {tickerId}")
    print(f"   Queue type: {type(q)}")
    print(f"   Queue valid: {store.validQueue(q)}")
    
    store.cancelQueue(q)
    print(f"   Queue valid after cancel: {store.validQueue(q)}")
    
    print("\n4. Testing RTVolume data structure...")
    # Test with new market data format (from ibind)
    market_data = {
        '31': '150.25',  # Last price
        '32': '100',     # Last size
        '7295': '1000000',  # Volume
        '7633': '150.20'    # VWAP
    }
    
    rtvol = ibstore.RTVolume(market_data=market_data)
    print(f"   Price: {rtvol.price}")
    print(f"   Size: {rtvol.size}")
    print(f"   Volume: {rtvol.volume}")
    print(f"   VWAP: {rtvol.vwap}")
    print(f"   DateTime: {rtvol.datetime}")
    
    # Test with legacy format (backward compatibility)
    rtvol_legacy = ibstore.RTVolume('150.25;100;1234567890000;1000000;150.20;1')
    print(f"   Legacy format price: {rtvol_legacy.price}")
    
    store.stop()
    print("   Store stopped successfully")


def demonstrate_data_feed():
    """Demonstrate data feed creation"""
    print("\n" + "=" * 60)
    print("Data Feed Creation")
    print("=" * 60)
    
    store = ibstore.IBStore(port=5000)
    
    print("1. Creating historical data feed...")
    try:
        data = store.getdata(
            dataname='AAPL-STK-SMART-USD',
            historical=True,
            fromdate=datetime.now() - timedelta(days=30),
            todate=datetime.now(),
            timeframe=bt.TimeFrame.Days,
            compression=1
        )
        
        print(f"   Data feed type: {type(data)}")
        print(f"   Data name: {data.p.dataname}")
        print(f"   Historical: {data.p.historical}")
        print(f"   Timeframe: {data.p.timeframe}")
        print(f"   Compression: {data.p.compression}")
        
    except Exception as e:
        print(f"   Data feed creation failed: {e}")
        print("   This is expected without IB Gateway connection")
    
    print("\n2. Creating live data feed...")
    try:
        live_data = store.getdata(
            dataname='AAPL-STK-SMART-USD',
            historical=False,
            timeframe=bt.TimeFrame.Seconds,
            compression=30
        )
        
        print(f"   Live data type: {type(live_data)}")
        print(f"   Historical: {live_data.p.historical}")
        
    except Exception as e:
        print(f"   Live data creation failed: {e}")
        print("   This is expected without IB Gateway connection")


def demonstrate_strategy_integration():
    """Demonstrate strategy integration"""
    print("\n" + "=" * 60)
    print("Strategy Integration")
    print("=" * 60)
    
    class SimpleStrategy(bt.Strategy):
        def log(self, txt):
            print(f"   Strategy: {txt}")
        
        def __init__(self):
            self.log("Strategy initialized")
        
        def notify_data(self, data, status):
            self.log(f"Data status: {data._getstatusname(status)}")
        
        def notify_store(self, msg, *args, **kwargs):
            self.log(f"Store notification: {msg}")
        
        def next(self):
            if len(self.data) > 0:
                self.log(f"Close price: {self.data.close[0]:.2f}")
    
    print("1. Creating Cerebro with IBStore...")
    cerebro = bt.Cerebro()
    
    store = ibstore.IBStore(port=5000, _debug=False)
    cerebro.addstore(store)
    
    print("2. Adding strategy...")
    cerebro.addstrategy(SimpleStrategy)
    
    print("3. Adding data feed...")
    try:
        data = store.getdata(
            dataname='AAPL-STK-SMART-USD',
            historical=True,
            fromdate=datetime.now() - timedelta(days=5),
            todate=datetime.now()
        )
        cerebro.adddata(data)
        
        print("4. Setting up broker...")
        cerebro.broker.setcash(100000.0)
        
        print("5. Running strategy...")
        print("   (This will fail without IB connection, which is expected)")
        
        try:
            cerebro.run()
        except Exception as e:
            print(f"   Strategy run failed: {e}")
            print("   This is expected without IB Gateway")
            
    except Exception as e:
        print(f"   Setup failed: {e}")


def show_migration_checklist():
    """Show migration checklist"""
    print("\n" + "=" * 60)
    print("Migration Checklist")
    print("=" * 60)
    
    print("✅ Code Changes Required:")
    print("   - Change port from 7496 to 5000")
    print("   - Install ibind: pip install ibind")
    print("   - Enable IB Gateway Web API")
    print("   - Optional: add account_id parameter")
    
    print("\n✅ What Stays the Same:")
    print("   - All method signatures")
    print("   - Data structures (RTVolume, Contract)")
    print("   - Event callbacks")
    print("   - Strategy code")
    print("   - Cerebro integration")
    
    print("\n✅ New Features Available:")
    print("   - OAuth authentication")
    print("   - Better error handling")
    print("   - Modern Python features")
    print("   - Active maintenance")
    
    print("\n✅ Backward Compatibility:")
    print("   - Set BACKTRADER_USE_IBIND=false to use legacy ibpy")
    print("   - Automatic fallback if ibind not available")
    print("   - Same configuration parameters")


def show_before_after_comparison():
    """Show before/after code comparison"""
    print("\n" + "=" * 60)
    print("Before/After Code Comparison")
    print("=" * 60)
    
    print("BEFORE (ibpy):")
    print("```python")
    print("store = ibstore.IBStore(")
    print("    host='127.0.0.1',")
    print("    port=7496,  # TWS/Gateway port")
    print("    clientId=1")
    print(")")
    print("```")
    
    print("\nAFTER (ibind):")
    print("```python")
    print("store = ibstore.IBStore(")
    print("    host='127.0.0.1',")
    print("    port=5000,  # IB Gateway Web API port")
    print("    clientId=1,")
    print("    account_id='DU123456'  # Optional")
    print(")")
    print("```")
    
    print("\nEverything else remains exactly the same!")


if __name__ == '__main__':
    print("IBStore Migration Demonstration")
    print("From ibpy to ibind - Maintaining Full Backward Compatibility")
    
    # Run demonstrations
    demonstrate_basic_usage()
    demonstrate_data_feed()
    demonstrate_strategy_integration()
    show_migration_checklist()
    show_before_after_comparison()
    
    print("\n" + "=" * 60)
    print("Demonstration completed!")
    print("\nNext steps:")
    print("1. Review IBIND_MIGRATION_GUIDE.md for detailed instructions")
    print("2. Test with your existing strategies")
    print("3. Update IB Gateway configuration")
    print("4. Enjoy the benefits of modern, maintained code!")
    print("=" * 60)