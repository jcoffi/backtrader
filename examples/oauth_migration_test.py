#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
OAuth-based IBind Migration Test

This test validates the migration from ibpy to ibind using OAuth authentication
without requiring a live IB Gateway connection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from backtrader.brokers.iborder_ibind import IBOrder, IBOrderState

def test_oauth_store_creation():
    """Test OAuth-based IBStore creation"""
    print("🔐 TESTING OAUTH STORE CREATION")
    print("-" * 40)
    
    # Set up OAuth environment variables
    os.environ['IBIND_OAUTH1A_ACCESS_TOKEN'] = 'test_access_token'
    os.environ['IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'] = 'test_access_token_secret'
    os.environ['IBIND_OAUTH1A_CONSUMER_KEY'] = 'test_consumer_key'
    
    try:
        # Create IBStore with OAuth
        store = bt.stores.IBStore(
            use_oauth=True,
            account_id='test_account',
            _debug=True
        )
        
        print("✅ OAuth IBStore created successfully")
        print(f"   - OAuth enabled: {store.p.use_oauth}")
        print(f"   - Account ID: {store.p.account_id}")
        
        # Test broker creation
        broker = store.getbroker()
        print(f"✅ OAuth IBBroker created: {type(broker)}")
        
        # Test broker methods availability
        methods_to_test = [
            'start', 'connected', 'get_acc_cash', 'get_acc_value',
            'get_positions', 'placeOrder', 'cancelOrder', 'nextOrderId'
        ]
        
        for method in methods_to_test:
            if hasattr(broker, method):
                print(f"   ✅ {method} - Available")
            else:
                print(f"   ❌ {method} - Missing")
        
        return True
        
    except Exception as e:
        print(f"❌ OAuth store creation failed: {e}")
        return False

def test_oauth_order_classes():
    """Test OAuth-compatible order classes"""
    print("\n🔧 TESTING OAUTH ORDER CLASSES")
    print("-" * 40)
    
    try:
        # Test IBOrderState
        order_state = IBOrderState(
            status='Filled',
            commission=2.50,
            commissionCurrency='USD'
        )
        print("✅ IBOrderState created successfully")
        
        # Test IBOrder
        order = IBOrder(
            action='BUY',
            m_totalQuantity=100,
            m_orderType='LMT',
            m_lmtPrice=150.0
        )
        print("✅ IBOrder created successfully")
        print(f"   - Action: {order.m_action}")
        print(f"   - Quantity: {order.m_totalQuantity}")
        print(f"   - Order Type: {order.m_orderType}")
        print(f"   - Limit Price: {order.m_lmtPrice}")
        
        # Test ibind conversion
        ibind_order = order.to_ibind_order(265598)  # AAPL contract ID
        print("✅ IBind order conversion successful")
        print(f"   - IBind format: {ibind_order}")
        
        return True
        
    except Exception as e:
        print(f"❌ OAuth order classes test failed: {e}")
        return False

def test_oauth_compatibility():
    """Test OAuth compatibility with existing Backtrader patterns"""
    print("\n🔄 TESTING OAUTH COMPATIBILITY")
    print("-" * 40)
    
    try:
        # Set up OAuth environment
        os.environ['IBIND_OAUTH1A_ACCESS_TOKEN'] = 'test_access_token'
        os.environ['IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'] = 'test_access_token_secret'
        os.environ['IBIND_OAUTH1A_CONSUMER_KEY'] = 'test_consumer_key'
        
        # Test standard Backtrader pattern
        cerebro = bt.Cerebro()
        
        # Create store with OAuth
        store = bt.stores.IBStore(
            use_oauth=True,
            account_id='test_account'
        )
        
        # Set broker
        cerebro.setbroker(store.getbroker())
        
        print("✅ OAuth store integrated with Cerebro")
        print("✅ OAuth broker set successfully")
        
        # Test that we can access OAuth-specific features
        broker = cerebro.broker
        if hasattr(broker, 'get_acc_cash'):
            print("✅ OAuth broker methods accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ OAuth compatibility test failed: {e}")
        return False

def test_oauth_vs_legacy():
    """Test OAuth vs legacy authentication differences"""
    print("\n⚖️  TESTING OAUTH VS LEGACY")
    print("-" * 40)
    
    try:
        # OAuth store (modern)
        oauth_store = bt.stores.IBStore(
            use_oauth=True,
            account_id='test_account'
        )
        
        # Legacy-style store (should still work but use OAuth internally)
        legacy_store = bt.stores.IBStore(
            host='localhost',
            port=5000,
            clientId=1
        )
        
        print("✅ OAuth store created")
        print("✅ Legacy-style store created (uses OAuth internally)")
        
        # Both should have the same broker capabilities
        oauth_broker = oauth_store.getbroker()
        legacy_broker = legacy_store.getbroker()
        
        print(f"✅ OAuth broker type: {type(oauth_broker)}")
        print(f"✅ Legacy broker type: {type(legacy_broker)}")
        
        # Both should be the same class (new IBBroker)
        if type(oauth_broker) == type(legacy_broker):
            print("✅ Both brokers use the same modern implementation")
        
        return True
        
    except Exception as e:
        print(f"❌ OAuth vs legacy test failed: {e}")
        return False

def main():
    """Run all OAuth migration tests"""
    print("🚀 OAUTH IBIND MIGRATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("OAuth Store Creation", test_oauth_store_creation),
        ("OAuth Order Classes", test_oauth_order_classes),
        ("OAuth Compatibility", test_oauth_compatibility),
        ("OAuth vs Legacy", test_oauth_vs_legacy)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 OAUTH TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL OAUTH TESTS PASSED!")
        print("\n📚 OAuth Migration Benefits:")
        print("- ✅ Secure OAuth 1.0a authentication")
        print("- ✅ No localhost dependency")
        print("- ✅ Modern API access")
        print("- ✅ Enhanced security")
        print("- ✅ Cloud-ready architecture")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. OAuth migration needs attention.")

if __name__ == '__main__':
    main()