#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
IBStore OAuth Example - Complete Usage Demonstration

This example shows how to use the new OAuth-enabled IBStore for both
backtesting (historical data) and live trading (real-time data).

Prerequisites:
1. Install ibind: pip install ibind[oauth]
2. Set up OAuth credentials with Interactive Brokers
3. Configure ibstore_oauth_config.py with your credentials
"""

import datetime
import backtrader as bt
from backtrader.stores import ibstore

# Import OAuth configuration
try:
    from ibstore_oauth_config import setup_oauth_from_files, verify_oauth_setup
except ImportError:
    print("[FAIL] Please copy and configure ibstore_oauth_config.py first!")
    exit(1)

# =============================================================================
# TRADING STRATEGY EXAMPLE
# =============================================================================

class SimpleStrategy(bt.Strategy):
    """
    Simple example strategy for demonstration
    """
    
    params = (
        ('period', 20),  # Moving average period
        ('debug', True), # Print debug information
    )
    
    def __init__(self):
        # Create moving average indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.period
        )
        
        # Track orders
        self.order = None
        self.bar_count = 0
    
    def next(self):
        self.bar_count += 1
        
        if self.params.debug and self.bar_count <= 5:
            print(f"Bar {self.bar_count}: "
                  f"Date={self.data.datetime.date(0)} "
                  f"Close=${self.data.close[0]:.2f} "
                  f"SMA=${self.sma[0]:.2f}")
        
        # Skip if we have a pending order
        if self.order:
            return
        
        # Simple strategy: buy when price > SMA, sell when price < SMA
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.order = self.buy(size=100)
                if self.params.debug:
                    print(f" BUY signal: Price ${self.data.close[0]:.2f} > SMA ${self.sma[0]:.2f}")
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.sell(size=100)
                if self.params.debug:
                    print(f" SELL signal: Price ${self.data.close[0]:.2f} < SMA ${self.sma[0]:.2f}")
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"[PASS] BUY executed: ${order.executed.price:.2f}")
            else:
                print(f"[PASS] SELL executed: ${order.executed.price:.2f}")
        
        self.order = None

# =============================================================================
# EXAMPLE FUNCTIONS
# =============================================================================

def test_oauth_connection():
    """Test OAuth connection and basic functionality"""
    print("[TEST] Testing OAuth Connection")
    print("=" * 50)
    
    # Set up OAuth
    if not setup_oauth_from_files():
        print("[FAIL] OAuth setup failed")
        return False
    
    if not verify_oauth_setup():
        print("[FAIL] OAuth verification failed")
        return False
    
    try:
        # Create IBStore
        store = ibstore.IBStore(
            use_oauth=True,
            account_id='U12345678',  # Replace with your account ID
            _debug=True
        )
        
        # Test symbol resolution
        print("\n[CHECK] Testing symbol resolution...")
        result = store.resolve_symbol_to_conid('AAPL')
        if result and hasattr(result, 'data') and result.data:
            print(f"[PASS] AAPL resolved to ConID: {result.data}")
        else:
            print("[FAIL] Symbol resolution failed")
            return False
        
        # Test live market data
        print("\n Testing live market data...")
        snapshot = store.get_market_data_snapshot('AAPL')
        if snapshot and 'AAPL' in snapshot and snapshot['AAPL']:
            data = snapshot['AAPL']
            print(f"[PASS] AAPL Live Data:")
            print(f"   Last: ${data.get('last', 'N/A'):.2f}")
            print(f"   Bid:  ${data.get('bid', 'N/A'):.2f}")
            print(f"   Ask:  ${data.get('ask', 'N/A'):.2f}")
        else:
            print("[WARNING]  Live data not available (market may be closed)")
        
        store.stop()
        print("\n[PASS] OAuth connection test successful!")
        return True
        
    except Exception as e:
        print(f"[FAIL] OAuth connection test failed: {e}")
        return False

def run_backtest_example():
    """Run a backtest using historical data"""
    print("\n[RESULTS] Running Backtest Example")
    print("=" * 50)
    
    # Set up OAuth
    if not setup_oauth_from_files():
        return False
    
    try:
        # Create Cerebro engine
        cerebro = bt.Cerebro()
        
        # Create IBStore
        store = ibstore.IBStore(
            use_oauth=True,
            account_id='U12345678',  # Replace with your account ID
            _debug=True
        )
        
        # Add historical data feed
        data = store.getdata(
            dataname='AAPL',
            sectype='STK',
            exchange='SMART',
            currency='USD',
            timeframe=bt.TimeFrame.Minutes,
            compression=5,  # 5-minute bars
            historical=True,
            fromdate=datetime.datetime.now() - datetime.timedelta(days=2),
            todate=datetime.datetime.now()
        )
        
        cerebro.adddata(data)
        cerebro.addstrategy(SimpleStrategy, debug=True)
        
        # Set initial cash
        cerebro.broker.setcash(100000.0)
        initial_value = cerebro.broker.getvalue()
        
        print(f" Starting portfolio value: ${initial_value:.2f}")
        
        # Run backtest
        results = cerebro.run()
        
        final_value = cerebro.broker.getvalue()
        profit = final_value - initial_value
        
        print(f" Final portfolio value: ${final_value:.2f}")
        print(f"[GROWTH] Total profit/loss: ${profit:.2f}")
        
        if profit > 0:
            print("[PASS] Backtest completed successfully with profit!")
        else:
            print("[WARNING]  Backtest completed with loss")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Backtest failed: {e}")
        return False

def run_live_data_example():
    """Demonstrate live data functionality"""
    print("\n Live Data Example")
    print("=" * 50)
    
    # Set up OAuth
    if not setup_oauth_from_files():
        return False
    
    try:
        # Create IBStore
        store = ibstore.IBStore(
            use_oauth=True,
            account_id='U12345678',  # Replace with your account ID
            _debug=True
        )
        
        # Test multiple symbols
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
        
        print("Getting live market data for multiple symbols...")
        
        for symbol in symbols:
            print(f"\n[RESULTS] {symbol}:")
            
            # Get live snapshot
            snapshot = store.get_market_data_snapshot(symbol)
            
            if snapshot and symbol in snapshot and snapshot[symbol]:
                data = snapshot[symbol]
                last = data.get('last', 'N/A')
                bid = data.get('bid', 'N/A')
                ask = data.get('ask', 'N/A')
                
                if last != 'N/A':
                    spread = ask - bid if (bid != 'N/A' and ask != 'N/A') else 'N/A'
                    print(f"   Last: ${last:.2f}")
                    print(f"   Bid:  ${bid:.2f}")
                    print(f"   Ask:  ${ask:.2f}")
                    print(f"   Spread: ${spread:.2f}" if spread != 'N/A' else "   Spread: N/A")
                else:
                    print("   No live data available")
            else:
                print("   Failed to get market data")
        
        store.stop()
        print("\n[PASS] Live data example completed!")
        return True
        
    except Exception as e:
        print(f"[FAIL] Live data example failed: {e}")
        return False

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function - run all examples"""
    print("[START] IBStore OAuth Example")
    print("=" * 60)
    print("This example demonstrates the new OAuth-enabled IBStore")
    print("for both backtesting and live trading with Interactive Brokers")
    print("=" * 60)
    
    # Test 1: OAuth connection
    if not test_oauth_connection():
        print("\n[FAIL] OAuth connection failed. Please check your configuration.")
        return
    
    # Test 2: Backtest with historical data
    if not run_backtest_example():
        print("\n[FAIL] Backtest example failed.")
        return
    
    # Test 3: Live data demonstration
    if not run_live_data_example():
        print("\n[WARNING]  Live data example had issues (market may be closed)")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] IBStore OAuth Example Completed!")
    print("=" * 60)
    print("\n[PASS] Key achievements:")
    print("   - OAuth authentication working")
    print("   - Historical data retrieval for backtesting")
    print("   - Live market data access")
    print("   - Symbol resolution and contract details")
    print("\n[START] Your IBStore is ready for both backtesting and live trading!")
    print("\nNext steps:")
    print("   1. Modify the strategy for your trading logic")
    print("   2. Test with your preferred symbols")
    print("   3. Configure risk management parameters")
    print("   4. Deploy for live trading (with proper testing!)")

if __name__ == '__main__':
    main()