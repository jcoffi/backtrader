#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
IBStore Headless OAuth Authentication Example

This example demonstrates how to use the migrated IBStore with ibind's OAuth 1.0a
authentication for completely headless operation - no IB Gateway/TWS required!

Key Benefits of Headless Operation:
1. No GUI components needed (no IB Gateway/TWS)
2. Fully automated trading without manual intervention
3. Direct connection to IB Web API using OAuth
4. Perfect for cloud deployments and automated systems
5. Session maintenance handled automatically

Prerequisites:
1. Install ibind with OAuth support: pip install ibind[oauth]
2. Set up OAuth credentials in IB self-service portal
3. Configure environment variables or OAuth config
"""

import os
import sys
from datetime import datetime, timedelta

# Add backtrader to path
sys.path.insert(0, '/workspace/backtrader')

import backtrader as bt
from backtrader.stores import ibstore


def setup_oauth_environment():
    """
    Set up OAuth environment variables for headless operation
    
    Note: In production, these should be set securely, not hardcoded!
    """
    print("Setting up OAuth environment for headless operation...")
    
    # These are example values - replace with your actual OAuth credentials
    oauth_config = {
        'IBIND_USE_OAUTH': 'True',
        'IBIND_ACCOUNT_ID': 'DU123456',  # Your paper/live account ID
        'IBIND_OAUTH1A_ACCESS_TOKEN': 'your_access_token_here',
        'IBIND_OAUTH1A_ACCESS_TOKEN_SECRET': 'your_access_token_secret_here',
        'IBIND_OAUTH1A_CONSUMER_KEY': 'your_consumer_key_here',
        'IBIND_OAUTH1A_ENCRYPTION_KEY_FP': '/path/to/your/encryption_key.pem',
        'IBIND_OAUTH1A_SIGNATURE_KEY_FP': '/path/to/your/signature_key.pem',
        'IBIND_OAUTH1A_DH_PRIME': 'your_dh_prime_hex_string_here'
    }
    
    # Set environment variables (for demo purposes)
    for key, value in oauth_config.items():
        os.environ[key] = value
        print(f"   {key}: {'*' * 20 if 'secret' in key.lower() or 'key' in key.lower() else value}")
    
    print("   OAuth environment configured!")
    return oauth_config


def demonstrate_headless_connection():
    """Demonstrate headless connection without IB Gateway/TWS"""
    print("=" * 60)
    print("Headless OAuth Connection (No IB Gateway/TWS Required)")
    print("=" * 60)
    
    # Create IBStore with OAuth enabled for headless operation
    store = ibstore.IBStore(
        # No host/port needed - connects directly to IB Web API
        use_oauth=True,
        enable_tickler=True,  # Automatically maintain OAuth session
        account_id='DU123456',  # Your account ID
        session_timeout=3600,  # 1 hour session timeout
        enhanced_error_handling=True,
        _debug=True
    )
    
    print("1. Attempting headless OAuth authentication...")
    try:
        # Enable OAuth authentication
        oauth_success = store.enable_oauth_authentication()
        
        if oauth_success:
            print("   [PASS] OAuth authentication successful!")
            print("   [PASS] Connected directly to IB Web API")
            print("   [PASS] No IB Gateway/TWS required")
            print("   [PASS] Session tickler started for automatic maintenance")
        else:
            print("   [FAIL] OAuth authentication failed")
            print("   (This is expected in demo without real credentials)")
            
    except Exception as e:
        print(f"   [FAIL] OAuth error: {e}")
        print("   (This is expected in demo without real credentials)")
    
    print("\n2. Testing headless market data access...")
    try:
        # Get market data snapshot without IB Gateway
        snapshot = store.get_market_data_snapshot(symbol='AAPL')
        
        if snapshot:
            print(f"   [PASS] Market data retrieved: {snapshot}")
        else:
            print("   [FAIL] Market data unavailable (expected without real OAuth)")
            
    except Exception as e:
        print(f"   [FAIL] Market data error: {e}")
    
    print("\n3. Testing headless account information...")
    try:
        # Get account performance without IB Gateway
        performance = store.get_account_performance()
        
        if performance:
            print(f"   [PASS] Account performance: {performance}")
        else:
            print("   [FAIL] Account data unavailable (expected without real OAuth)")
            
    except Exception as e:
        print(f"   [FAIL] Account data error: {e}")
    
    store.stop()


def demonstrate_headless_trading_strategy():
    """Demonstrate a complete headless trading strategy"""
    print("=" * 60)
    print("Headless Trading Strategy Example")
    print("=" * 60)
    
    class HeadlessStrategy(bt.Strategy):
        """Example strategy for headless trading"""
        
        def __init__(self):
            print("   [RESULTS] Headless strategy initialized")
            self.order = None
        
        def next(self):
            if not self.position and not self.order:
                print(f"   [GROWTH] Current price: {self.data.close[0]}")
                # Example: Buy signal (in real strategy, use your logic)
                print("    Placing buy order...")
                self.order = self.buy(size=100)
        
        def notify_order(self, order):
            if order.status in [order.Completed]:
                print(f"   [PASS] Order completed: {order.executed.size} @ {order.executed.price}")
            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                print(f"   [FAIL] Order failed: {order.status}")
            self.order = None
        
        def notify_trade(self, trade):
            if trade.isclosed:
                print(f"    Trade closed: PnL {trade.pnl:.2f}")
    
    print("1. Setting up headless Cerebro...")
    cerebro = bt.Cerebro()
    
    # Create headless store
    store = ibstore.IBStore(
        use_oauth=True,
        enable_tickler=True,
        account_id='DU123456',
        parallel_requests=True,
        cache_contract_details=True,
        _debug=False  # Reduce noise for strategy demo
    )
    
    # Add store to cerebro
    cerebro.addstore(store)
    
    print("2. Adding headless data feed...")
    # Add data feed (works without IB Gateway when OAuth is configured)
    data = store.getdata(
        dataname='AAPL-STK-SMART-USD',
        historical=True,
        fromdate=datetime.now() - timedelta(days=5),
        todate=datetime.now()
    )
    cerebro.adddata(data)
    
    print("3. Adding headless broker...")
    # Add broker (works without IB Gateway when OAuth is configured)
    broker = store.getbroker()
    cerebro.setbroker(broker)
    
    print("4. Adding headless strategy...")
    cerebro.addstrategy(HeadlessStrategy)
    
    print("5. Running headless strategy...")
    try:
        results = cerebro.run()
        print("   [PASS] Headless strategy completed successfully!")
        
        # In a real scenario with proper OAuth, this would execute trades
        print("   [RESULTS] Strategy would execute trades automatically")
        print("   [PROCESS] No manual intervention required")
        print("   [CLOUD]  Perfect for cloud deployment")
        
    except Exception as e:
        print(f"   [FAIL] Strategy execution failed: {e}")
        print("   (Expected without real IB connection)")
    
    store.stop()


def demonstrate_oauth_configuration():
    """Show different ways to configure OAuth"""
    print("=" * 60)
    print("OAuth Configuration Options")
    print("=" * 60)
    
    print("1. Environment Variables Method:")
    print("""
    # Set these environment variables for automatic OAuth setup
    export IBIND_USE_OAUTH=True
    export IBIND_ACCOUNT_ID=DU123456
    export IBIND_OAUTH1A_ACCESS_TOKEN=your_token
    export IBIND_OAUTH1A_ACCESS_TOKEN_SECRET=your_secret
    export IBIND_OAUTH1A_CONSUMER_KEY=your_key
    export IBIND_OAUTH1A_ENCRYPTION_KEY_FP=/path/to/encryption.pem
    export IBIND_OAUTH1A_SIGNATURE_KEY_FP=/path/to/signature.pem
    export IBIND_OAUTH1A_DH_PRIME=your_dh_prime_hex
    """)
    
    print("2. Direct Configuration Method:")
    print("""
    from ibind.oauth.oauth1a import OAuth1aConfig
    
    oauth_config = OAuth1aConfig(
        access_token='your_token',
        access_token_secret='your_secret',
        consumer_key='your_key',
        encryption_key_fp='/path/to/encryption.pem',
        signature_key_fp='/path/to/signature.pem',
        dh_prime='your_dh_prime_hex'
    )
    
    store = ibstore.IBStore(
        use_oauth=True,
        oauth_config=oauth_config,
        account_id='DU123456'
    )
    """)
    
    print("3. IBStore Enhanced Parameters:")
    print("""
    store = ibstore.IBStore(
        # OAuth Configuration
        use_oauth=True,                    # Enable OAuth authentication
        oauth_config=oauth_config,         # OAuth config object (optional)
        account_id='DU123456',            # Your account ID
        
        # Session Management
        enable_tickler=True,              # Auto-maintain OAuth session
        session_timeout=3600,             # Session timeout (seconds)
        
        # Enhanced Features
        parallel_requests=True,           # Parallel market data requests
        cache_contract_details=True,      # Cache for performance
        enhanced_error_handling=True,     # Better error reporting
        
        # Performance Tuning
        max_concurrent_requests=10,       # Max parallel requests
        rate_limit_delay=0.1,            # Rate limiting delay
        
        # WebSocket Features
        websocket_auto_reconnect=True,    # Auto-reconnect WebSocket
        market_data_channels=['MARKET_DATA', 'ORDERS', 'PNL']
    )
    """)


def main():
    """Main demonstration function"""
    print("IBStore Headless OAuth Authentication Demonstration")
    print("Fully Automated Trading Without IB Gateway/TWS")
    print("=" * 80)
    
    # Set up OAuth environment (demo only)
    setup_oauth_environment()
    print()
    
    # Demonstrate headless connection
    demonstrate_headless_connection()
    print()
    
    # Demonstrate headless trading
    demonstrate_headless_trading_strategy()
    print()
    
    # Show configuration options
    demonstrate_oauth_configuration()
    
    print("=" * 80)
    print("Headless Operation Summary")
    print("=" * 80)
    
    print("[PASS] Key Benefits:")
    print("   • No IB Gateway/TWS required - direct Web API connection")
    print("   • Fully automated operation with OAuth 1.0a authentication")
    print("   • Perfect for cloud deployments and headless servers")
    print("   • Automatic session maintenance with tickler")
    print("   • Enhanced error handling and reconnection")
    print("   • All IBStore features work in headless mode")
    
    print("\n[CONFIG] Setup Requirements:")
    print("   1. Install: pip install ibind[oauth]")
    print("   2. Configure OAuth credentials in IB self-service portal")
    print("   3. Set environment variables or OAuth config")
    print("   4. Enable use_oauth=True in IBStore")
    print("   5. No IB Gateway/TWS installation needed!")
    
    print("\n[START] Production Ready:")
    print("   • Deploy to any cloud platform")
    print("   • Run in Docker containers")
    print("   • Schedule with cron jobs")
    print("   • Integrate with CI/CD pipelines")
    print("   • Scale horizontally across multiple instances")
    
    print("\n[DOCS] Next Steps:")
    print("   1. Set up OAuth credentials with Interactive Brokers")
    print("   2. Test with paper trading account first")
    print("   3. Configure your trading strategies")
    print("   4. Deploy to your preferred cloud platform")
    print("   5. Monitor and scale as needed")
    
    print("\n[SUCCESS] Headless trading is now possible with IBStore + ibind!")


if __name__ == '__main__':
    main()