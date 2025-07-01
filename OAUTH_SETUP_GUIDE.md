# OAuth Setup Guide for IBind Migration

## Overview

This guide explains how to set up OAuth authentication for the migrated IBStore/IBBroker components that now use `ibind` instead of the legacy `ibpy` library.

## Benefits of OAuth Authentication

[PASS] **Enhanced Security**: OAuth 1.0a provides secure authentication without storing passwords  
[PASS] **No Local Gateway**: No need to run IB Gateway or TWS locally  
[PASS] **Cloud Ready**: Works in cloud environments and containers  
[PASS] **Modern API**: Access to IBKR's latest REST API features  
[PASS] **Better Performance**: More efficient than legacy socket connections  

## Prerequisites

1. **Interactive Brokers Account**: You need an active IBKR account
2. **OAuth Credentials**: Obtain OAuth credentials from IBKR
3. **Python Environment**: Python 3.7+ with `ibind[oauth]` installed

## OAuth Credential Setup

### Step 1: Obtain OAuth Credentials from IBKR

Contact Interactive Brokers to obtain your OAuth 1.0a credentials:

- **Access Token**: Your OAuth access token
- **Access Token Secret**: Your OAuth access token secret  
- **Consumer Key**: Your OAuth consumer key
- **DH Prime**: Diffie-Hellman prime for encryption
- **Encryption Key**: File path to your encryption key
- **Signature Key**: File path to your signature key
- **Account ID**: Your IBKR account ID

### Step 2: Set Environment Variables

Set the following environment variables with your OAuth credentials:

```bash
# Required OAuth credentials
export IBKR_OAUTH_ACCESS_TOKEN="your_access_token"
export IBKR_OAUTH_ACCESS_TOKEN_SECRET="your_access_token_secret"
export IBKR_OAUTH_CONSUMER_KEY="your_consumer_key"
export IBKR_OAUTH_DH_PRIME="your_dh_prime"
export IBKR_OAUTH_ENCRYPTION_KEY_FP="/path/to/encryption_key.pem"
export IBKR_OAUTH_SIGNATURE_KEY_FP="/path/to/signature_key.pem"
export IBKR_ACCOUNT_ID="your_account_id"
```

### Step 3: Verify Setup

Run the OAuth test to verify your setup:

```bash
cd /path/to/backtrader
python examples/real_oauth_test.py
```

## Usage Examples

### Basic OAuth Store Creation

```python
import backtrader as bt

# Create OAuth-enabled store
store = bt.stores.IBStore(
    use_oauth=True,
    account_id='your_account_id',
    _debug=True  # Enable debug logging
)

# Get broker
broker = store.getbroker()

# Start connection
broker.start()
```

### Complete Trading Strategy

```python
import backtrader as bt
import datetime

class MyStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(self.data, period=20)
    
    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy(size=100)
        else:
            if self.data.close[0] < self.sma[0]:
                self.sell(size=100)

# Set up OAuth environment variables first
import os
os.environ['IBKR_OAUTH_ACCESS_TOKEN'] = 'your_token'
os.environ['IBKR_OAUTH_ACCESS_TOKEN_SECRET'] = 'your_secret'
# ... set other variables

# Create cerebro
cerebro = bt.Cerebro()

# Add strategy
cerebro.addstrategy(MyStrategy)

# Create OAuth store
store = bt.stores.IBStore(
    use_oauth=True,
    account_id='your_account_id'
)

# Set broker
cerebro.setbroker(store.getbroker())

# Add data feed
data = store.getdata(
    dataname='AAPL',
    timeframe=bt.TimeFrame.Minutes,
    compression=1
)
cerebro.adddata(data)

# Run strategy
cerebro.run()
```

### Data Feed Only

```python
import backtrader as bt

# Create OAuth store
store = bt.stores.IBStore(
    use_oauth=True,
    account_id='your_account_id'
)

# Create data feed
data = store.getdata(
    dataname='AAPL',
    timeframe=bt.TimeFrame.Minutes,
    compression=5,
    historical=True,
    fromdate=datetime.datetime.now() - datetime.timedelta(days=1)
)

# Use with cerebro
cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.run()
```

## Security Best Practices

### Environment Variables
- [PASS] Always use environment variables for credentials
- [PASS] Never store credentials in code or version control
- [PASS] Use secure methods to set environment variables in production

### File Permissions
```bash
# Secure your key files
chmod 600 /path/to/encryption_key.pem
chmod 600 /path/to/signature_key.pem
```

### Production Deployment
```bash
# Use secure environment variable injection
docker run -e IBKR_OAUTH_ACCESS_TOKEN="$IBKR_OAUTH_ACCESS_TOKEN" \
           -e IBKR_OAUTH_ACCESS_TOKEN_SECRET="$IBKR_OAUTH_ACCESS_TOKEN_SECRET" \
           your_trading_app
```

## Troubleshooting

### Common Issues

#### 1. Missing OAuth Parameters
```
Error: OAuth1aConfig is missing required parameters
```
**Solution**: Ensure all required environment variables are set

#### 2. Invalid Credentials
```
Error: Authentication failed
```
**Solution**: Verify your OAuth credentials with IBKR

#### 3. Network Issues
```
Error: Connection refused
```
**Solution**: Check internet connection and firewall settings

#### 4. Key File Issues
```
Error: Cannot read key file
```
**Solution**: Verify file paths and permissions

### Debug Mode

Enable debug logging for troubleshooting:

```python
store = bt.stores.IBStore(
    use_oauth=True,
    account_id='your_account_id',
    _debug=True  # Enable debug output
)
```

### Test Connection

Use the provided test scripts:

```bash
# Test OAuth structure
python examples/oauth_migration_test.py

# Test with real credentials
python examples/real_oauth_test.py

# Full migration test
python examples/complete_ibpy_migration_test.py
```

## Migration from Legacy

### Before (ibpy)
```python
# Old way with IB Gateway
store = bt.stores.IBStore(
    host='localhost',
    port=7497,
    clientId=1
)
```

### After (ibind + OAuth)
```python
# New way with OAuth
store = bt.stores.IBStore(
    use_oauth=True,
    account_id='your_account_id'
)
```

### Backward Compatibility

The new implementation maintains backward compatibility:

```python
# This still works but uses OAuth internally
store = bt.stores.IBStore(
    host='localhost',  # Ignored when OAuth is available
    port=7497,         # Ignored when OAuth is available
    clientId=1         # Ignored when OAuth is available
)
```

## Support

For issues with:
- **OAuth Setup**: Contact Interactive Brokers support
- **ibind Library**: Check [ibind documentation](https://github.com/Voyz/ibind)
- **Backtrader Integration**: Check this migration guide and test scripts

## Additional Resources

- [IBKR OAuth Documentation](https://www.interactivebrokers.com/api)
- [ibind Library](https://github.com/Voyz/ibind)
- [Backtrader Documentation](https://www.backtrader.com/)
- [Migration Guide](IBPY_TO_IBIND_MIGRATION_GUIDE.md)