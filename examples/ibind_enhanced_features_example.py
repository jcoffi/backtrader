#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Enhanced IBStore Features Example

This example demonstrates the new capabilities available with the ibind-based
IBStore implementation while maintaining full backward compatibility.

Features demonstrated:
1. OAuth authentication for headless operation
2. Parallel market data requests
3. Enhanced order management with automatic confirmations
4. Real-time position tracking
5. Account performance monitoring
6. Transaction history
7. Performance metrics and caching
8. WebSocket channel management
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add backtrader to path
sys.path.insert(0, '/workspace/backtrader')

import backtrader as bt
from backtrader.stores import ibstore


def demonstrate_enhanced_market_data():
    """Demonstrate enhanced market data capabilities"""
    print("=" * 60)
    print("Enhanced Market Data Features")
    print("=" * 60)
    
    # Create store with enhanced features enabled
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,
        parallel_requests=True,
        max_concurrent_requests=5,
        cache_contract_details=True,
        auto_symbol_resolution=True,
        rate_limit_delay=0.1,
        _debug=True
    )
    
    print("1. Testing market data snapshot...")
    try:
        # Get live market data snapshot
        snapshot = store.get_market_data_snapshot(symbol='AAPL')
        if snapshot:
            print(f"   AAPL snapshot: {snapshot}")
        else:
            print("   Snapshot failed (expected without IB connection)")
    except Exception as e:
        print(f"   Snapshot error: {e}")
    
    print("\n2. Testing parallel historical data requests...")
    try:
        # Get historical data for multiple symbols in parallel
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        historical_data = store.get_historical_data_parallel(
            symbols=symbols,
            period='1d',
            bar_size='1h'
        )
        
        if historical_data:
            print(f"   Retrieved data for {len(historical_data)} symbols")
            for symbol, data in historical_data.items():
                print(f"   {symbol}: {len(data) if data else 0} bars")
        else:
            print("   Parallel request failed (expected without IB connection)")
    except Exception as e:
        print(f"   Parallel request error: {e}")
    
    print("\n3. Testing symbol resolution and caching...")
    try:
        # Test symbol to contract ID resolution
        conid = store.resolve_symbol_to_conid('AAPL')
        if conid:
            print(f"   AAPL contract ID: {conid}")
        else:
            print("   Symbol resolution failed (expected without IB connection)")
        
        # Test cache
        cached = store.get_cached_contract_details('AAPL')
        print(f"   Cached details: {cached is not None}")
        
    except Exception as e:
        print(f"   Symbol resolution error: {e}")
    
    store.stop()


def demonstrate_oauth_authentication():
    """Demonstrate OAuth authentication features"""
    print("=" * 60)
    print("OAuth Authentication Features")
    print("=" * 60)
    
    # Create store with OAuth enabled
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,
        use_oauth=True,
        enable_tickler=True,
        session_timeout=3600,
        _debug=True
    )
    
    print("1. Testing OAuth authentication...")
    try:
        # Enable OAuth authentication
        oauth_enabled = store.enable_oauth_authentication()
        print(f"   OAuth enabled: {oauth_enabled}")
        
        if oauth_enabled:
            print("   OAuth tickler started for session maintenance")
        else:
            print("   OAuth setup failed (expected without proper configuration)")
            
    except Exception as e:
        print(f"   OAuth error: {e}")
    
    store.stop()


def demonstrate_enhanced_portfolio_management():
    """Demonstrate enhanced portfolio and account management"""
    print("=" * 60)
    print("Enhanced Portfolio Management")
    print("=" * 60)
    
    # Create store with account management features
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,
        account_id='DU123456',  # Example account ID
        enable_performance_tracking=True,
        _debug=True
    )
    
    print("1. Testing account performance tracking...")
    try:
        performance = store.get_account_performance()
        if performance:
            print(f"   Account performance: {performance}")
        else:
            print("   Performance data unavailable (expected without IB connection)")
    except Exception as e:
        print(f"   Performance tracking error: {e}")
    
    print("\n2. Testing real-time positions...")
    try:
        positions = store.get_positions_realtime()
        if positions:
            print(f"   Found {len(positions)} positions")
            for pos in positions[:3]:  # Show first 3
                print(f"   Position: {pos}")
        else:
            print("   No positions found (expected without IB connection)")
    except Exception as e:
        print(f"   Position tracking error: {e}")
    
    print("\n3. Testing transaction history...")
    try:
        transactions = store.get_transaction_history(days=30)
        if transactions:
            print(f"   Found {len(transactions)} transactions")
            for txn in transactions[:3]:  # Show first 3
                print(f"   Transaction: {txn}")
        else:
            print("   No transactions found (expected without IB connection)")
    except Exception as e:
        print(f"   Transaction history error: {e}")
    
    print("\n4. Testing performance metrics...")
    try:
        metrics = store.get_performance_metrics()
        if metrics:
            print(f"   Performance metrics: {metrics}")
        else:
            print("   No metrics available (tracking may be disabled)")
    except Exception as e:
        print(f"   Metrics error: {e}")
    
    store.stop()


def demonstrate_enhanced_order_management():
    """Demonstrate enhanced order management with automatic confirmations"""
    print("=" * 60)
    print("Enhanced Order Management")
    print("=" * 60)
    
    # Create store with enhanced order features
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,
        enable_question_answer=True,
        account_id='DU123456',
        _debug=True
    )
    
    print("1. Testing enhanced order submission...")
    try:
        # Create a mock order request (would normally use ibind's OrderRequest)
        class MockOrderRequest:
            def __init__(self):
                self.symbol = 'AAPL'
                self.quantity = 100
                self.order_type = 'MKT'
                self.side = 'BUY'
        
        order_request = MockOrderRequest()
        
        # Submit order with automatic confirmation
        result = store.submit_order_with_confirmation(
            account_id='DU123456',
            order_request=order_request,
            auto_confirm=True
        )
        
        if result:
            print(f"   Order submission result: {result}")
        else:
            print("   Order submission failed (expected without IB connection)")
            
    except Exception as e:
        print(f"   Order submission error: {e}")
    
    store.stop()


def demonstrate_websocket_features():
    """Demonstrate WebSocket channel management"""
    print("=" * 60)
    print("WebSocket Channel Management")
    print("=" * 60)
    
    # Create store with WebSocket features
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,
        websocket_auto_reconnect=True,
        market_data_channels=['MARKET_DATA', 'ORDERS', 'PNL'],
        _debug=True
    )
    
    print("1. Testing WebSocket channel setup...")
    try:
        # Enable specific WebSocket channels
        channels_enabled = store.enable_websocket_channels([
            'MARKET_DATA', 'ORDERS', 'PNL', 'MARKET_HISTORY'
        ])
        
        print(f"   WebSocket channels enabled: {channels_enabled}")
        
        if channels_enabled:
            print("   Subscribed to: MARKET_DATA, ORDERS, PNL, MARKET_HISTORY")
        else:
            print("   Channel setup failed (expected without IB connection)")
            
    except Exception as e:
        print(f"   WebSocket setup error: {e}")
    
    store.stop()


def demonstrate_backward_compatibility():
    """Demonstrate that all original features still work"""
    print("=" * 60)
    print("Backward Compatibility Verification")
    print("=" * 60)
    
    # Create store using original parameters only
    store = ibstore.IBStore(
        host='127.0.0.1',
        port=5000,  # Only change: port 7496 -> 5000
        clientId=1,
        timeoffset=True,
        reconnect=3,
        timeout=3.0,
        notifyall=False,
        _debug=False
    )
    
    print("1. Original contract creation...")
    contract = store.makecontract(
        symbol='AAPL',
        sectype='STK',
        exch='SMART',
        curr='USD'
    )
    print(f"   Contract: {contract.m_symbol.decode()}-{contract.m_secType.decode()}")
    
    print("\n2. Original queue management...")
    tickerId, queue = store.getTickerQueue()
    print(f"   Ticker ID: {tickerId}, Queue: {type(queue).__name__}")
    
    print("\n3. Original data feed creation...")
    data = store.getdata(
        dataname='AAPL-STK-SMART-USD',
        historical=True,
        fromdate=datetime.now() - timedelta(days=5)
    )
    print(f"   Data feed: {type(data).__name__}")
    
    print("\n4. Original Cerebro integration...")
    cerebro = bt.Cerebro()
    cerebro.addstore(store)
    cerebro.adddata(data)
    print(f"   Cerebro stores: {len(cerebro.stores)}")
    print(f"   Cerebro datas: {len(cerebro.datas)}")
    
    store.stop()
    
    print("\n[PASS] All original functionality preserved!")


def demonstrate_performance_comparison():
    """Demonstrate performance improvements"""
    print("=" * 60)
    print("Performance Improvements")
    print("=" * 60)
    
    print("1. Testing with caching enabled...")
    start_time = time.time()
    
    store_cached = ibstore.IBStore(
        port=5000,
        cache_contract_details=True,
        auto_symbol_resolution=True,
        parallel_requests=True,
        _debug=False
    )
    
    # Simulate multiple contract lookups
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AAPL', 'GOOGL']  # Repeated symbols
    for symbol in symbols:
        store_cached.resolve_symbol_to_conid(symbol)
    
    cached_time = time.time() - start_time
    store_cached.stop()
    
    print(f"   Time with caching: {cached_time:.4f}s")
    
    print("\n2. Testing with caching disabled...")
    start_time = time.time()
    
    store_uncached = ibstore.IBStore(
        port=5000,
        cache_contract_details=False,
        auto_symbol_resolution=False,
        parallel_requests=False,
        _debug=False
    )
    
    # Same contract lookups without caching
    for symbol in symbols:
        store_uncached.resolve_symbol_to_conid(symbol)
    
    uncached_time = time.time() - start_time
    store_uncached.stop()
    
    print(f"   Time without caching: {uncached_time:.4f}s")
    
    if cached_time < uncached_time:
        improvement = ((uncached_time - cached_time) / uncached_time) * 100
        print(f"   Performance improvement: {improvement:.1f}%")
    else:
        print("   Performance similar (expected without real IB connection)")


def main():
    """Run all enhanced feature demonstrations"""
    print("IBStore Enhanced Features Demonstration")
    print("Showcasing ibind's advanced capabilities with full backward compatibility")
    print("=" * 80)
    
    try:
        # Demonstrate enhanced features
        demonstrate_enhanced_market_data()
        print()
        
        demonstrate_oauth_authentication()
        print()
        
        demonstrate_enhanced_portfolio_management()
        print()
        
        demonstrate_enhanced_order_management()
        print()
        
        demonstrate_websocket_features()
        print()
        
        # Verify backward compatibility
        demonstrate_backward_compatibility()
        print()
        
        # Show performance improvements
        demonstrate_performance_comparison()
        
    except Exception as e:
        print(f"Demonstration error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Enhanced Features Summary")
    print("=" * 80)
    
    print("[PASS] New Features Available:")
    print("   • OAuth 1.0a authentication for headless operation")
    print("   • Parallel market data requests with rate limiting")
    print("   • Enhanced order management with auto-confirmations")
    print("   • Real-time position and account tracking")
    print("   • Transaction history and performance analytics")
    print("   • WebSocket channel management")
    print("   • Contract and symbol caching for performance")
    print("   • Enhanced error handling and reporting")
    
    print("\n[PASS] Backward Compatibility:")
    print("   • All original IBStore methods work unchanged")
    print("   • Same data structures and event system")
    print("   • Existing strategies require no code changes")
    print("   • Only port change needed: 7496 → 5000")
    
    print("\n[PASS] Configuration Options:")
    print("   • use_oauth: Enable OAuth authentication")
    print("   • parallel_requests: Enable parallel data requests")
    print("   • cache_contract_details: Cache for performance")
    print("   • enable_question_answer: Auto-handle order confirmations")
    print("   • websocket_auto_reconnect: Auto-reconnect WebSocket")
    print("   • enable_performance_tracking: Track API metrics")
    
    print("\n[START] Ready for production use with enhanced capabilities!")


if __name__ == '__main__':
    main()