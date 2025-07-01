# OAuth Setup Microagent

**Task**: Set up OAuth 1.0a authentication for Interactive Brokers integration with Backtrader using ibind library.

**Context**: User needs to configure OAuth credentials for secure API access to Interactive Brokers without password-based authentication.

**Goal**: Complete OAuth setup with environment variables, key files, and validation testing.

### 1. Obtain OAuth Credentials from IBKR

Contact Interactive Brokers to obtain your OAuth 1.0a credentials:

```
Required Credentials:
- OAuth Access Token
- OAuth Access Token Secret
- OAuth Consumer Key
- Diffie-Hellman Prime
- Encryption Key File (.pem)
- Signature Key File (.pem)
- Account ID
```

### 2. Install Required Dependencies

```bash
pip install ibind[oauth] backtrader cryptography
```

### 3. Set Environment Variables

Create secure environment variables for your OAuth credentials:

```bash
# OAuth Tokens
export IBKR_OAUTH_ACCESS_TOKEN="your_access_token_here"
export IBKR_OAUTH_ACCESS_TOKEN_SECRET="your_access_token_secret_here"
export IBKR_OAUTH_CONSUMER_KEY="your_consumer_key_here"

# Diffie-Hellman Prime (hex string)
export IBKR_OAUTH_DH_PRIME="your_dh_prime_hex_string"

# Key File Paths
export IBKR_OAUTH_ENCRYPTION_KEY_FP="/path/to/your/encryption_key.pem"
export IBKR_OAUTH_SIGNATURE_KEY_FP="/path/to/your/signature_key.pem"

# Account Information
export IBKR_ACCOUNT_ID="your_account_id"
```

### 4. Secure Key File Setup

Ensure your PEM key files have proper permissions:

```bash
# Set secure permissions (owner read/write only)
chmod 600 /path/to/your/encryption_key.pem
chmod 600 /path/to/your/signature_key.pem

# Verify permissions
ls -la /path/to/your/*.pem
# Should show: -rw------- (600 permissions)
```

### 5. Validate OAuth Setup

Run the validation test script:

```bash
python .openhands/microagents/test_oauth_setup.py
```

Expected output for successful setup:
```
🚀 Starting OAuth Setup Validation
==================================================
Environment Variables............ ✅ PASSED
Key Files........................ ✅ PASSED
IBind Import..................... ✅ PASSED
Backtrader Import................ ✅ PASSED
OAuth Config..................... ✅ PASSED
OAuth Store...................... ✅ PASSED

Overall: 6/6 tests passed

🎉 ALL TESTS PASSED!
Your OAuth setup is ready for live trading!
```

### 6. Basic Usage Example

```python
import backtrader as bt
import os

# Create OAuth-enabled store
store = bt.stores.IBStore(
    use_oauth=True,
    account_id=os.environ['IBKR_ACCOUNT_ID'],
    _debug=True  # Enable debug logging
)

# Get broker instance
broker = store.getbroker()

# Create and run strategy
cerebro = bt.Cerebro()
cerebro.setbroker(broker)
# Add your strategy here
cerebro.run()
```

### 7. Production Deployment

#### Docker Example

```dockerfile
FROM python:3.9-slim

# Install dependencies
RUN pip install backtrader ibind[oauth] cryptography

# Copy key files with secure permissions
COPY --chmod=600 encryption_key.pem /app/keys/
COPY --chmod=600 signature_key.pem /app/keys/

# Set environment variables
ENV IBKR_OAUTH_ENCRYPTION_KEY_FP=/app/keys/encryption_key.pem
ENV IBKR_OAUTH_SIGNATURE_KEY_FP=/app/keys/signature_key.pem

# Copy application
COPY . /app
WORKDIR /app

CMD ["python", "your_trading_script.py"]
```

#### Kubernetes Secret Example

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: ibkr-oauth-credentials
type: Opaque
stringData:
  IBKR_OAUTH_ACCESS_TOKEN: "your_access_token"
  IBKR_OAUTH_ACCESS_TOKEN_SECRET: "your_secret"
  IBKR_OAUTH_CONSUMER_KEY: "your_consumer_key"
  IBKR_OAUTH_DH_PRIME: "your_dh_prime"
  IBKR_ACCOUNT_ID: "your_account_id"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ibkr-key-files
data:
  encryption_key.pem: |
    -----BEGIN PRIVATE KEY-----
    your_encryption_key_content
    -----END PRIVATE KEY-----
  signature_key.pem: |
    -----BEGIN PRIVATE KEY-----
    your_signature_key_content
    -----END PRIVATE KEY-----
```

### 8. Troubleshooting

#### Common Issues

**Environment Variables Not Set**
```bash
# Check if variables are set
env | grep IBKR_OAUTH
```

**Key File Permission Issues**
```bash
# Fix permissions
chmod 600 /path/to/key/files/*.pem
```

**Import Errors**
```bash
# Install with OAuth support
pip install ibind[oauth]
```

**Connection Issues**
```python
# Enable debug logging
store = bt.stores.IBStore(use_oauth=True, _debug=True)
```

#### Validation Failures

If validation tests fail:

1. **Check Environment Variables**: Ensure all 7 required variables are set
2. **Verify Key Files**: Confirm PEM files exist and have correct permissions
3. **Test Credentials**: Validate credentials with IBKR directly
4. **Check Network**: Ensure access to `https://api.ibkr.com`

### 9. Security Best Practices

#### Credential Management
- Never hardcode credentials in source code
- Use environment variables or secure secret management
- Rotate credentials regularly
- Monitor access logs

#### Key File Security
- Store PEM files with 600 permissions (owner read/write only)
- Use secure file systems (encrypted storage)
- Backup keys securely
- Never commit keys to version control

#### Production Security
- Use container secrets for deployment
- Implement proper access controls
- Monitor authentication attempts
- Use secure communication channels

### 10. Advanced Configuration

#### Custom OAuth Configuration

```python
from ibind.support.oauth_config import OAuth1aConfig
import backtrader as bt

# Create custom OAuth config
oauth_config = OAuth1aConfig(
    access_token=os.environ['IBKR_OAUTH_ACCESS_TOKEN'],
    access_token_secret=os.environ['IBKR_OAUTH_ACCESS_TOKEN_SECRET'],
    consumer_key=os.environ['IBKR_OAUTH_CONSUMER_KEY'],
    dh_prime=os.environ['IBKR_OAUTH_DH_PRIME'],
    encryption_key_fp=os.environ['IBKR_OAUTH_ENCRYPTION_KEY_FP'],
    signature_key_fp=os.environ['IBKR_OAUTH_SIGNATURE_KEY_FP']
)

# Use with store
store = bt.stores.IBStore(oauth_config=oauth_config)
```

#### Multiple Account Support

```python
# Account 1
store1 = bt.stores.IBStore(
    use_oauth=True,
    account_id='account_1_id'
)

# Account 2 (different credentials)
store2 = bt.stores.IBStore(
    use_oauth=True,
    account_id='account_2_id',
    oauth_config=custom_oauth_config_2
)
```

### 11. Migration from Legacy Authentication

If migrating from password-based authentication:

#### Before (Legacy)
```python
store = bt.stores.IBStore(
    host='localhost',
    port=7497,
    clientId=1
)
```

#### After (OAuth)
```python
store = bt.stores.IBStore(
    use_oauth=True,
    account_id=os.environ['IBKR_ACCOUNT_ID']
)
```

#### Migration Checklist
- [ ] Obtain OAuth credentials from IBKR
- [ ] Set up environment variables
- [ ] Configure key files with proper permissions
- [ ] Run validation tests
- [ ] Update application code
- [ ] Test with paper trading first
- [ ] Deploy to production

This microagent provides complete OAuth setup guidance for the IBPy to IBind migration, ensuring secure and reliable authentication for Interactive Brokers integration with Backtrader.