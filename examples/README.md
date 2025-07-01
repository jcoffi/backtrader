# IBStore OAuth Examples

This directory contains examples and configuration files for using the new OAuth-enabled IBStore with Interactive Brokers.

## Files

### Configuration
- **`ibstore_oauth_config.py`** - OAuth configuration template and helper functions
- **`README.md`** - This file

### Examples
- **`ibstore_oauth_example.py`** - Complete usage demonstration

## Quick Start

### 1. Set Up OAuth Credentials

First, obtain OAuth credentials from Interactive Brokers:

1. Log into IB Client Portal
2. Go to Settings → API → OAuth
3. Create a new OAuth application
4. Download the encryption and signature key files
5. Generate access token and consumer key

### 2. Configure OAuth

Copy and modify the configuration file:

```bash
cp ibstore_oauth_config.py my_config.py
```

Edit `my_config.py` with your actual credentials:

```python
# Your IB Account ID
ACCOUNT_ID = 'U12345678'  # Replace with your actual account ID

# OAuth credentials
ACCESS_TOKEN = 'your_access_token_here'
ACCESS_TOKEN_SECRET = 'your_access_token_secret_here'
CONSUMER_KEY = 'your_consumer_key_here'
DH_PRIME = 'your_dh_prime_value_here'

# Path to credential files
CREDENTIALS_DIR = Path.home() / '.ib_credentials'
```

### 3. Organize Credential Files

Create a secure directory structure:

```
~/.ib_credentials/
├── private_encryption.pem
├── private_signature.pem
├── accesstoken.txt          # access_token on line 1, secret on line 2
└── consumerkey.txt          # consumer_key
```

### 4. Run the Example

```bash
python ibstore_oauth_example.py
```

## Example Usage

### Basic Setup

```python
from ibstore_oauth_config import setup_oauth_from_files
from backtrader.stores import ibstore

# Set up OAuth
setup_oauth_from_files()

# Create IBStore
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True
)
```

### Historical Data (Backtesting)

```python
import backtrader as bt
import datetime

# Create data feed
data = store.getdata(
    dataname='AAPL',
    sectype='STK',
    exchange='SMART',
    currency='USD',
    timeframe=bt.TimeFrame.Minutes,
    compression=5,
    historical=True,
    fromdate=datetime.datetime.now() - datetime.timedelta(days=5),
    todate=datetime.datetime.now()
)

# Run backtest
cerebro = bt.Cerebro()
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)
cerebro.run()
```

### Live Market Data

```python
# Get live market data snapshot
snapshot = store.get_market_data_snapshot('AAPL')
if snapshot and 'AAPL' in snapshot:
    data = snapshot['AAPL']
    print(f"Last: ${data.get('last', 'N/A'):.2f}")
    print(f"Bid:  ${data.get('bid', 'N/A'):.2f}")
    print(f"Ask:  ${data.get('ask', 'N/A'):.2f}")
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit credentials to version control**
2. **Use file permissions to protect credential files** (`chmod 600`)
3. **Store credentials in environment variables for production**
4. **Use the file-based credential loading for better security**

## Troubleshooting

### Common Issues

**OAuth Authentication Failed**
- Verify all environment variables are set
- Check that credential files exist and are readable
- Ensure OAuth credentials are valid and not expired

**No Market Data**
- Check if markets are open
- Verify you have market data permissions with IB
- Try the two-call pattern for live data subscriptions

**Symbol Resolution Failed**
- Ensure the symbol exists and is tradeable
- Check the security type (STK, OPT, FUT, etc.)
- Verify exchange and currency parameters

### Debug Mode

Enable debug logging for troubleshooting:

```python
store = ibstore.IBStore(
    use_oauth=True,
    account_id='U12345678',
    _debug=True  # Enable detailed logging
)
```

### Test Your Setup

Use the verification function:

```python
from ibstore_oauth_config import verify_oauth_setup

if verify_oauth_setup():
    print("✅ OAuth setup is correct")
else:
    print("❌ OAuth setup has issues")
```

## Support

For additional help:

1. Check the main documentation: `../docs/IBStore_OAuth_Migration_Guide.md`
2. Review the troubleshooting section in the migration guide
3. Enable debug mode for detailed error messages
4. Verify your IB account permissions and API access

## Migration from Legacy IBStore

If you're migrating from the old ibpy-based IBStore:

1. **Install new dependencies**: `pip install ibind[oauth]`
2. **Set up OAuth credentials** (no more TWS/Gateway needed)
3. **Update initialization**: Add `use_oauth=True` and `account_id`
4. **Test thoroughly**: Both historical and live data functionality

The API remains the same, so your existing strategies should work without modification!