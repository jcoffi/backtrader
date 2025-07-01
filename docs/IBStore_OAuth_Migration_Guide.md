# IBStore OAuth 1.0a Migration Guide

## Overview

The IBStore component in Backtrader has been successfully migrated from the legacy `ibpy` library to the modern `ibind` library with OAuth 1.0a authentication. This guide will help you migrate your existing code and set up OAuth authentication with Interactive Brokers.

## [START] Quick Start

### 1. Install Dependencies

```bash
pip install ibind[oauth]
```

### 2. Set Up OAuth Credentials

You'll need to obtain OAuth credentials from Interactive Brokers. Follow the [IB OAuth Setup Guide](#oauth-setup-with-interactive-brokers) below.

### 3. Update Your Code

**Before (legacy ibpy):**
```python
from backtrader.stores import ibstore

store = ibstore.IBStore(
    host='127.0.0.1',
    port=7497,
    clientId=1
)
```

**After (modern ibind with OAuth):**
```python
import os
from backtrader.stores import ibstore

# Set OAuth environment variables
os.environ['IBIND_USE_OAUTH'] = 'True'
os.environ['IBIND_ACCOUNT_ID'] = 'your_account_id'
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN'] = 'your_access_token'
os.environ['IBIND_OAUTH1A_ACCESS_TOKEN_SECRET'] = 'your_access_token_secret'
os.environ['IBIND_OAUTH1A_CONSUMER_KEY'] = 'your_consumer_key'
os.environ['IBIND_OAUTH1A_ENCRYPTION_KEY_FP'] = '/path/to/private_encryption.pem'
os.environ['IBIND_OAUTH1A_SIGNATURE_KEY_FP'] = '/path/to/private_signature.pem'
os.environ['IBIND_OAUTH1A_DH_PRIME'] = 'your_dh_prime'

store = ibstore.IBStore(
    use_oauth=True,
    account_id='your_account_id',
    _debug=True  # Optional: enable debug logging
)
```

## [SUMMARY] OAuth Setup with Interactive Brokers

### Step 1: Generate OAuth Credentials

1. **Log into IB Client Portal**
   - Go to https://www.interactivebrokers.com/
   - Log in to your account

2. **Navigate to API Settings**
   - Go to Settings → API → OAuth
   - Click "Create OAuth Application"

3. **Generate Keys**
   - Create a new OAuth application
   - Download the following files:
     - `private_encryption.pem` (encryption key)
     - `private_signature.pem` (signature key)
     - Consumer key (text string)

4. **Generate Access Token**
   - Follow IB's OAuth flow to generate access token and secret
   - Save these securely

### Step 2: Organize Your Credentials

Create a secure directory structure:
```
/your/secure/path/
├── private_encryption.pem
├── private_signature.pem
├── accesstoken.txt          # Contains access_token on first line, secret on second
├── consumerkey.txt          # Contains consumer key
└── config.py               # Your configuration file
```

### Step 3: Create Configuration File

**config.py:**
```python
import os

# OAuth Configuration
OAUTH_CONFIG = {
    'IBIND_USE_OAUTH': 'True',
    'IBIND_ACCOUNT_ID': 'U12345678',  # Your IB account ID
    'IBIND_OAUTH1A_ACCESS_TOKEN': 'your_access_token_here',
    'IBIND_OAUTH1A_ACCESS_TOKEN_SECRET': 'your_access_token_secret_here',
    'IBIND_OAUTH1A_CONSUMER_KEY': 'your_consumer_key_here',
    'IBIND_OAUTH1A_ENCRYPTION_KEY_FP': '/path/to/private_encryption.pem',
    'IBIND_OAUTH1A_SIGNATURE_KEY_FP': '/path/to/private_signature.pem',
    'IBIND_OAUTH1A_DH_PRIME': 'your_dh_prime_value'
}

def setup_oauth():
    """Set up OAuth environment variables"""
    for key, value in OAUTH_CONFIG.items():
        os.environ[key] = value
```

## [CODE] Usage Examples

### Basic Historical Data (Backtesting)

```python
import backtrader as bt
from backtrader.stores import ibstore
from config import setup_oauth

# Set up OAuth
setup_oauth()

# Create strategy
class MyStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy()
        elif len(self.data) > 10:
            self.sell()

# Create Cerebro engine
cerebro = bt.Cerebro()

# Create IBStore with OAuth
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True
)

# Add data feed
data = store.getdata(
    dataname='AAPL',
    sectype='STK',
    exchange='SMART',
    currency='USD',
    timeframe=bt.TimeFrame.Minutes,
    compression=1,
    historical=True,
    fromdate=datetime.datetime.now() - datetime.timedelta(days=5),
    todate=datetime.datetime.now()
)

cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
```

### Live Market Data

```python
from backtrader.stores import ibstore
from config import setup_oauth

# Set up OAuth
setup_oauth()

# Create IBStore
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True
)

# Get live market data snapshot
snapshot = store.get_market_data_snapshot('AAPL')
if snapshot and 'AAPL' in snapshot:
    data = snapshot['AAPL']
    print(f"AAPL Live Data:")
    print(f"  Last: ${data.get('last', 'N/A'):.2f}")
    print(f"  Bid:  ${data.get('bid', 'N/A'):.2f}")
    print(f"  Ask:  ${data.get('ask', 'N/A'):.2f}")

store.stop()
```

### Live Trading Strategy

```python
import backtrader as bt
from backtrader.stores import ibstore
from config import setup_oauth

class LiveTradingStrategy(bt.Strategy):
    def next(self):
        # Simple momentum strategy
        if self.data.close[0] > self.data.close[-1]:
            if not self.position:
                self.buy(size=100)
        elif self.data.close[0] < self.data.close[-1]:
            if self.position:
                self.sell(size=100)

# Set up OAuth
setup_oauth()

# Create Cerebro for live trading
cerebro = bt.Cerebro()

# Create IBStore
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True
)

# Add live data feed
data = store.getdata(
    dataname='AAPL',
    sectype='STK',
    exchange='SMART',
    currency='USD',
    timeframe=bt.TimeFrame.Minutes,
    compression=1,
    historical=False  # Live data
)

cerebro.adddata(data)
cerebro.addstrategy(LiveTradingStrategy)
cerebro.run()
```

## [CONFIG] Configuration Options

### IBStore Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_oauth` | bool | False | Enable OAuth authentication |
| `account_id` | str | None | IB account ID (required for OAuth) |
| `_debug` | bool | False | Enable debug logging |
| `auto_symbol_resolution` | bool | True | Automatically resolve symbols to contract IDs |
| `cache_contract_details` | bool | True | Cache contract details for performance |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IBIND_USE_OAUTH` | Yes | Set to 'True' to enable OAuth |
| `IBIND_ACCOUNT_ID` | Yes | Your IB account ID |
| `IBIND_OAUTH1A_ACCESS_TOKEN` | Yes | OAuth access token |
| `IBIND_OAUTH1A_ACCESS_TOKEN_SECRET` | Yes | OAuth access token secret |
| `IBIND_OAUTH1A_CONSUMER_KEY` | Yes | OAuth consumer key |
| `IBIND_OAUTH1A_ENCRYPTION_KEY_FP` | Yes | Path to encryption key file |
| `IBIND_OAUTH1A_SIGNATURE_KEY_FP` | Yes | Path to signature key file |
| `IBIND_OAUTH1A_DH_PRIME` | Yes | Diffie-Hellman prime value |

## [SECURE] Security Best Practices

### 1. Secure Credential Storage

- **Never commit credentials to version control**
- Store credentials in environment variables or secure configuration files
- Use file permissions to restrict access (chmod 600)
- Consider using a secrets management system for production

### 2. Environment Variables

```bash
# Set in your shell profile or use a .env file
export IBIND_USE_OAUTH=True
export IBIND_ACCOUNT_ID=U12345678
export IBIND_OAUTH1A_ACCESS_TOKEN=your_token
# ... other variables
```

### 3. Configuration File Security

```python
# config.py - Keep this file secure!
import os
from pathlib import Path

# Use absolute paths
CREDS_DIR = Path.home() / '.ib_credentials'

def load_credentials():
    """Load credentials from secure files"""
    with open(CREDS_DIR / 'accesstoken.txt', 'r') as f:
        lines = f.read().strip().split('\n')
        access_token = lines[0]
        access_token_secret = lines[1] if len(lines) > 1 else lines[0]
    
    with open(CREDS_DIR / 'consumerkey.txt', 'r') as f:
        consumer_key = f.read().strip()
    
    return {
        'access_token': access_token,
        'access_token_secret': access_token_secret,
        'consumer_key': consumer_key
    }
```

## [ALERT] Migration Checklist

### Breaking Changes

- [ ] **Authentication Method**: OAuth 1.0a required instead of username/password
- [ ] **Dependencies**: Install `ibind[oauth]` instead of `ibpy`
- [ ] **Configuration**: Set up OAuth environment variables
- [ ] **Connection**: No more TWS/Gateway connection required

### Code Updates Required

- [ ] Update import statements (no changes needed)
- [ ] Add OAuth configuration
- [ ] Update IBStore initialization parameters
- [ ] Test historical data functionality
- [ ] Test live data functionality
- [ ] Update error handling for OAuth-specific errors

### Compatibility

- [ ] **API Methods**: All existing IBStore methods maintained
- [ ] **Data Formats**: Same OHLCV data structure
- [ ] **Timeframes**: All existing timeframes supported
- [ ] **Strategies**: No strategy code changes required

## [DEBUG] Troubleshooting

### Common Issues

**1. OAuth Authentication Failed**
```
Error: OAuth1aConfig is missing required parameters
```
**Solution**: Ensure all OAuth environment variables are set correctly.

**2. No Market Data Received**
```
Market data snapshot: {'AAPL': {}}
```
**Solution**: 
- Check if markets are open
- Verify you have market data permissions
- Try making two consecutive calls (subscription pattern)

**3. Symbol Resolution Failed**
```
Symbol resolution failed for MSFT: 'NoneType' object has no attribute 'request'
```
**Solution**: Ensure REST client is properly initialized and OAuth is working.

**4. Historical Data Empty**
```
No historical data received
```
**Solution**:
- Check your market data permissions
- Verify the symbol exists and is tradeable
- Check date ranges (don't request future dates)

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True  # Enable detailed logging
)
```

### Testing Your Setup

Use this simple test to verify your OAuth setup:

```python
from backtrader.stores import ibstore
from config import setup_oauth

# Set up OAuth
setup_oauth()

# Test connection
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True
)

# Test symbol resolution
result = store.resolve_symbol_to_conid('AAPL')
if result and hasattr(result, 'data') and result.data:
    print("[PASS] OAuth setup successful!")
    print(f"AAPL ConID: {result.data}")
else:
    print("[FAIL] OAuth setup failed")

store.stop()
```

## [DOCS] Additional Resources

- [Interactive Brokers OAuth Documentation](https://www.interactivebrokers.com/api/doc/oauth.html)
- [ibind Library Documentation](https://github.com/Voyz/ibind)
- [Backtrader Documentation](https://www.backtrader.com/docu/)

## [HELP] Support

If you encounter issues:

1. **Check the troubleshooting section above**
2. **Enable debug mode** to get detailed logs
3. **Verify your OAuth credentials** with IB
4. **Test with the simple verification script**
5. **Check IB's API status** and your account permissions

## [BULLSEYE] Summary

The IBStore OAuth migration provides:

- [PASS] **Enhanced Security**: OAuth 1.0a authentication
- [PASS] **Modern API**: Uses IB's latest REST API
- [PASS] **Better Performance**: Active maintenance and optimization
- [PASS] **Full Compatibility**: Same interface, enhanced functionality
- [PASS] **Future-Proof**: Compatible with IB's roadmap

**Ready for both backtesting and live trading with real Interactive Brokers market data!**