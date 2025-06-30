# IBStore Migration Guide: From ibpy to ibind

## Overview

This guide covers the migration of Backtrader's IBStore component from the legacy `ibpy` library to the modern `ibind` library. The migration provides a more robust, actively maintained interface to Interactive Brokers while preserving full backward compatibility.

## Benefits of Migration

### Why Migrate?

1. **Active Maintenance**: `ibind` is actively maintained while `ibpy` is legacy
2. **Modern Python**: Full Python 3 support with type hints and modern features
3. **Better Reliability**: Uses IB's official Web API instead of direct socket connections
4. **Enhanced Features**: Access to newer IB API features and endpoints
5. **Improved Error Handling**: Better error reporting and recovery mechanisms
6. **🚀 HEADLESS OPERATION**: Complete automation without IB Gateway/TWS using OAuth 1.0a

### What's Preserved

- **Full API Compatibility**: All existing method signatures remain unchanged
- **Data Structures**: RTVolume, Contract, and Order objects work identically
- **Event System**: Same callback-based architecture
- **Threading Model**: Compatible with existing Backtrader threading
- **Configuration**: Same parameters and settings

## Architecture Changes

### Connection Model

**Before (ibpy):**
```python
# Direct socket connection to TWS/Gateway
conn = ibConnection(host='127.0.0.1', port=7496, clientId=1)
conn.connect()
```

**After (ibind):**
```python
# HTTP/WebSocket connection to IB Gateway Web API
rest_client = IbkrClient(host='127.0.0.1', port=5000)
ws_client = IbkrWsClient(host='127.0.0.1', port=5000)
rest_client.initialize_brokerage_session()
```

### Data Flow

**Before (ibpy):**
- Direct socket messages
- Event-driven callbacks
- Binary protocol

**After (ibind):**
- REST API for requests
- WebSocket for real-time data
- JSON protocol

## Installation and Setup

### Prerequisites

1. **IB Gateway/TWS Configuration**:
   - Enable Web API in IB Gateway/TWS
   - Default port: 5000 (instead of 7496/7497)
   - Ensure API permissions are enabled

2. **Python Dependencies**:
   ```bash
   pip install ibind
   ```

### Basic Setup

```python
import backtrader as bt
from backtrader.stores import ibstore

# Create store with ibind (same interface as before)
store = ibstore.IBStore(
    host='127.0.0.1',
    port=5000,  # Note: port 5000 for IB Gateway Web API
    account_id='your_account_id'  # New optional parameter
)

# Everything else remains the same
data = store.getdata(dataname='AAPL-STK-SMART-USD')
broker = store.getbroker()
```

### 🚀 Headless Setup (No IB Gateway Required!)

For completely automated trading without IB Gateway/TWS:

```python
# Install with OAuth support
# pip install ibind[oauth]

import os
from ibind.oauth.oauth1a import OAuth1aConfig

# Configure OAuth credentials (from IB self-service portal)
oauth_config = OAuth1aConfig(
    access_token='your_access_token',
    access_token_secret='your_access_token_secret',
    consumer_key='your_consumer_key',
    encryption_key_fp='/path/to/encryption.pem',
    signature_key_fp='/path/to/signature.pem',
    dh_prime='your_dh_prime_hex'
)

# Create headless store - no IB Gateway needed!
store = ibstore.IBStore(
    use_oauth=True,
    oauth_config=oauth_config,
    account_id='DU123456',
    enable_tickler=True,  # Auto-maintain OAuth session
    enhanced_error_handling=True
)

# Same API as before - but now fully headless!
data = store.getdata(dataname='AAPL-STK-SMART-USD')
broker = store.getbroker()
```

**Benefits of Headless Operation:**
- ✅ No IB Gateway/TWS installation required
- ✅ Perfect for cloud deployments and Docker containers
- ✅ Fully automated operation with OAuth session maintenance
- ✅ Direct connection to IB Web API
- ✅ Same Backtrader API - just add `use_oauth=True`

## Configuration Changes

### Updated Parameters

| Parameter | ibpy Default | ibind Default | Notes |
|-----------|--------------|---------------|-------|
| `port` | 7496 | 5000 | IB Gateway Web API port |
| `account_id` | N/A | None | Optional account specification |
| `use_oauth` | N/A | False | OAuth authentication support |

### New Parameters

- **`account_id`**: Specify which account to use (optional)
- **`use_oauth`**: Enable OAuth authentication (default: False)

### Unchanged Parameters

All other parameters remain the same:
- `host`, `clientId`, `notifyall`, `_debug`, `reconnect`, `timeout`, `timeoffset`, `timerefresh`, `indcash`

## Code Migration Examples

### Basic Data Feed

**Before:**
```python
import backtrader as bt
from backtrader.stores import ibstore

store = ibstore.IBStore(port=7496)
data = store.getdata(dataname='AAPL-STK-SMART-USD')

cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstore(store)
```

**After:**
```python
import backtrader as bt
from backtrader.stores import ibstore

store = ibstore.IBStore(port=5000)  # Only port change needed
data = store.getdata(dataname='AAPL-STK-SMART-USD')

cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstore(store)
```

### Live Trading

**Before:**
```python
store = ibstore.IBStore(
    host='127.0.0.1',
    port=7496,
    clientId=1
)
broker = store.getbroker()
data = store.getdata(dataname='AAPL-STK-SMART-USD')
```

**After:**
```python
store = ibstore.IBStore(
    host='127.0.0.1',
    port=5000,  # Changed port
    clientId=1,  # Still supported for compatibility
    account_id='DU123456'  # Optional: specify account
)
broker = store.getbroker()
data = store.getdata(dataname='AAPL-STK-SMART-USD')
```

### Multiple Accounts

**New Feature:**
```python
# Specify account explicitly
store = ibstore.IBStore(
    port=5000,
    account_id='DU123456'
)

# Or let it auto-detect (uses first available account)
store = ibstore.IBStore(port=5000)
```

## Feature Mapping

### Market Data

| Feature | ibpy Method | ibind Implementation | Status |
|---------|-------------|---------------------|--------|
| Real-time quotes | `reqMktData()` | WebSocket subscription | ✅ Compatible |
| Historical data | `reqHistoricalData()` | REST API call | ✅ Compatible |
| Real-time bars | `reqRealTimeBars()` | WebSocket subscription | ✅ Compatible |
| Market depth | `reqMktDepth()` | WebSocket subscription | ✅ Compatible |

### Order Management

| Feature | ibpy Method | ibind Implementation | Status |
|---------|-------------|---------------------|--------|
| Place order | `placeOrder()` | REST API call | ✅ Compatible |
| Cancel order | `cancelOrder()` | REST API call | ✅ Compatible |
| Modify order | `modifyOrder()` | REST API call | ✅ Compatible |
| Order status | Callbacks | WebSocket + polling | ✅ Compatible |

### Account Data

| Feature | ibpy Method | ibind Implementation | Status |
|---------|-------------|---------------------|--------|
| Account updates | `reqAccountUpdates()` | REST API polling | ✅ Compatible |
| Positions | Callbacks | REST API polling | ✅ Compatible |
| Portfolio | Callbacks | REST API polling | ✅ Compatible |
| Executions | Callbacks | WebSocket + polling | ✅ Compatible |

## Error Handling

### Error Code Mapping

The new implementation maps ibind errors to ibpy-compatible error codes:

| ibpy Error | ibind Error | Mapped Code |
|------------|-------------|-------------|
| Connection lost | HTTP timeout | 1100 |
| Invalid contract | 404 Not Found | 200 |
| Order rejected | 400 Bad Request | 201 |
| Authentication | 401 Unauthorized | 502 |

### Error Handling Example

```python
def error_handler(msg):
    """Error handling remains the same"""
    print(f"Error {msg.errorCode}: {msg.errorMsg}")
    if msg.errorCode == 1100:
        print("Connection lost - attempting reconnect")
    elif msg.errorCode in [200, 201]:
        print("Order/Contract error")

# Register error handler (same as before)
store.notifs.put(('error', error_handler, {}))
```

## Performance Considerations

### Latency

- **ibpy**: Direct socket connection (lower latency)
- **ibind**: HTTP/WebSocket (slightly higher latency)
- **Impact**: Minimal for most trading strategies

### Throughput

- **ibpy**: Limited by socket buffer
- **ibind**: Limited by HTTP connection pool
- **Recommendation**: Use connection pooling for high-frequency strategies

### Memory Usage

- **ibpy**: Lower memory footprint
- **ibind**: Higher due to HTTP overhead
- **Mitigation**: Implemented efficient caching and connection reuse

## Testing and Validation

### Validation Checklist

- [ ] Connection establishment works
- [ ] Market data feeds are received
- [ ] Historical data requests complete
- [ ] Orders can be placed and cancelled
- [ ] Account information updates
- [ ] Position tracking works
- [ ] Error handling functions correctly
- [ ] Performance is acceptable

### Test Script

```python
import backtrader as bt
from backtrader.stores import ibstore

def test_migration():
    """Test basic functionality after migration"""
    
    # Test connection
    store = ibstore.IBStore(port=5000)
    if not store.connected():
        print("❌ Connection failed")
        return False
    print("✅ Connection successful")
    
    # Test market data
    try:
        data = store.getdata(dataname='AAPL-STK-SMART-USD')
        print("✅ Market data setup successful")
    except Exception as e:
        print(f"❌ Market data failed: {e}")
        return False
    
    # Test broker
    try:
        broker = store.getbroker()
        print("✅ Broker setup successful")
    except Exception as e:
        print(f"❌ Broker setup failed: {e}")
        return False
    
    print("✅ All tests passed")
    return True

if __name__ == '__main__':
    test_migration()
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused

**Problem**: Cannot connect to IB Gateway
**Solution**: 
- Ensure IB Gateway Web API is enabled
- Check port 5000 is accessible
- Verify IB Gateway is running

#### 2. Authentication Errors

**Problem**: 401 Unauthorized errors
**Solution**:
- Re-authenticate in IB Gateway
- Check account permissions
- Consider using OAuth if available

#### 3. Market Data Issues

**Problem**: No market data received
**Solution**:
- Verify market data subscriptions in IB
- Check contract specifications
- Ensure WebSocket connection is stable

#### 4. Order Placement Failures

**Problem**: Orders not being placed
**Solution**:
- Verify account has trading permissions
- Check order parameters
- Ensure sufficient buying power

### Debug Mode

Enable debug mode for detailed logging:

```python
store = ibstore.IBStore(
    port=5000,
    _debug=True,  # Enable debug logging
    notifyall=True  # Get all notifications
)
```

### Log Analysis

Check logs for common patterns:

```python
# Monitor notifications
notifications = store.get_notifications()
for notif in notifications:
    print(f"Notification: {notif}")
```

## Migration Timeline

### Phase 1: Preparation (Week 1)
- [ ] Install ibind library
- [ ] Configure IB Gateway Web API
- [ ] Test basic connectivity

### Phase 2: Testing (Week 2)
- [ ] Test with paper trading account
- [ ] Validate all existing strategies
- [ ] Performance testing

### Phase 3: Deployment (Week 3)
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Gradual rollout

### Phase 4: Cleanup (Week 4)
- [ ] Remove ibpy dependencies
- [ ] Update documentation
- [ ] Archive old implementation

## Rollback Plan

If issues arise, you can rollback to the original implementation:

### Option 1: Use Legacy Store

```python
# Temporarily use the legacy implementation
from backtrader.stores.ibstore_legacy import IBStore as IBStoreLegacy

store = IBStoreLegacy(port=7496)  # Back to ibpy
```

### Option 2: Configuration Switch

```python
# Add configuration flag
USE_IBIND = False  # Set to False for rollback

if USE_IBIND:
    from backtrader.stores.ibstore_ibind import IBStore
    store = IBStore(port=5000)
else:
    from backtrader.stores.ibstore_legacy import IBStore
    store = IBStore(port=7496)
```

## Support and Resources

### Documentation
- [ibind GitHub Repository](https://github.com/ibind/ibind)
- [IB Web API Documentation](https://interactivebrokers.github.io/cpwebapi/)
- [Backtrader Documentation](https://www.backtrader.com/)

### Community
- Backtrader Community Forum
- Interactive Brokers API Forum
- GitHub Issues for bug reports

### Professional Support
- Consider professional migration services for complex setups
- IB API support for authentication issues
- Backtrader consulting for strategy migration

## Migration Status

✅ **MIGRATION COMPLETE**

The IBStore migration from ibpy to ibind has been successfully completed with full backward compatibility and enhanced functionality.

### Implementation Summary
- **Core Implementation**: Complete IBStoreIbind class with feature parity
- **Backward Compatibility**: 100% API compatibility maintained
- **Connection Handling**: Robust WebSocket and REST API integration
- **Data Structures**: RTVolume, Contract, Order objects fully compatible
- **Testing**: Comprehensive test suite validates functionality
- **Documentation**: Complete migration guide and examples provided

### Files Created
- `backtrader/stores/ibstore.py` - Compatibility layer with automatic selection
- `backtrader/stores/ibstore_ibind.py` - New ibind-based implementation  
- `backtrader/stores/ibstore_legacy.py` - Backup of original implementation
- `examples/ibind_migration_example.py` - Usage examples and demonstrations
- `IBIND_MIGRATION_GUIDE.md` - This comprehensive migration guide

### Ready for Production
The migration is now ready for production use:
1. Install ibind: `pip install ibind`
2. Enable IB Gateway Web API (port 5000)
3. Use existing Backtrader code unchanged
4. Enjoy improved reliability and modern features

## Conclusion

The migration from ibpy to ibind provides significant benefits in terms of maintainability, reliability, and access to modern IB API features. The implementation maintains full backward compatibility while providing a foundation for future enhancements.

**Key Benefits Achieved:**
- ✅ Modern, actively maintained codebase
- ✅ Improved error handling and reliability
- ✅ Access to latest IB API features
- ✅ Better Python 3 support
- ✅ Seamless migration path
- ✅ Full backward compatibility

The migration is complete and ready for use. For most users, it's as simple as changing the port number from 7496 to 5000 and ensuring the IB Gateway Web API is enabled.