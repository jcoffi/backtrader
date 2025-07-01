#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
IBStore OAuth Configuration Example

This file shows how to set up OAuth authentication for IBStore.
Copy this file and modify with your actual credentials.

SECURITY WARNING: Never commit this file with real credentials to version control!
"""

import os
from pathlib import Path

# =============================================================================
# CONFIGURATION - MODIFY THESE VALUES
# =============================================================================

# Your IB Account ID (e.g., 'U12345678')
ACCOUNT_ID = 'U12345678'  # Replace with your actual account ID

# Path to your OAuth credential files
CREDENTIALS_DIR = Path.home() / '.ib_credentials'  # Modify this path

# OAuth credentials - Replace with your actual values
ACCESS_TOKEN = 'your_access_token_here'
ACCESS_TOKEN_SECRET = 'your_access_token_secret_here'
CONSUMER_KEY = 'your_consumer_key_here'

# DH Prime value (provided by IB during OAuth setup)
DH_PRIME = 'your_dh_prime_value_here'

# =============================================================================
# OAUTH CONFIGURATION
# =============================================================================

OAUTH_CONFIG = {
    'IBIND_USE_OAUTH': 'True',
    'IBIND_ACCOUNT_ID': ACCOUNT_ID,
    'IBIND_OAUTH1A_ACCESS_TOKEN': ACCESS_TOKEN,
    'IBIND_OAUTH1A_ACCESS_TOKEN_SECRET': ACCESS_TOKEN_SECRET,
    'IBIND_OAUTH1A_CONSUMER_KEY': CONSUMER_KEY,
    'IBIND_OAUTH1A_ENCRYPTION_KEY_FP': str(CREDENTIALS_DIR / 'private_encryption.pem'),
    'IBIND_OAUTH1A_SIGNATURE_KEY_FP': str(CREDENTIALS_DIR / 'private_signature.pem'),
    'IBIND_OAUTH1A_DH_PRIME': DH_PRIME
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def setup_oauth():
    """
    Set up OAuth environment variables for IBStore
    
    Call this function before creating IBStore instances:
    
    from ibstore_oauth_config import setup_oauth
    setup_oauth()
    """
    for key, value in OAUTH_CONFIG.items():
        os.environ[key] = value
    print("✅ OAuth environment variables configured")

def load_credentials_from_files():
    """
    Load credentials from secure files instead of hardcoding them
    
    Expected file structure:
    ~/.ib_credentials/
    ├── private_encryption.pem
    ├── private_signature.pem
    ├── accesstoken.txt      # access_token on line 1, secret on line 2
    └── consumerkey.txt      # consumer_key
    """
    try:
        # Load access token and secret
        with open(CREDENTIALS_DIR / 'accesstoken.txt', 'r') as f:
            lines = f.read().strip().split('\n')
            access_token = lines[0]
            access_token_secret = lines[1] if len(lines) > 1 else lines[0]
        
        # Load consumer key
        with open(CREDENTIALS_DIR / 'consumerkey.txt', 'r') as f:
            consumer_key = f.read().strip()
        
        # Update configuration
        OAUTH_CONFIG.update({
            'IBIND_OAUTH1A_ACCESS_TOKEN': access_token,
            'IBIND_OAUTH1A_ACCESS_TOKEN_SECRET': access_token_secret,
            'IBIND_OAUTH1A_CONSUMER_KEY': consumer_key,
        })
        
        print("✅ Credentials loaded from files")
        return True
        
    except FileNotFoundError as e:
        print(f"❌ Credential file not found: {e}")
        print("Please ensure your credential files are in the correct location")
        return False
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        return False

def setup_oauth_from_files():
    """
    Load credentials from files and set up OAuth environment
    
    This is the recommended approach for production use.
    """
    if load_credentials_from_files():
        setup_oauth()
        return True
    return False

def verify_oauth_setup():
    """
    Verify that OAuth is properly configured
    
    Returns True if all required environment variables are set
    """
    required_vars = [
        'IBIND_USE_OAUTH',
        'IBIND_ACCOUNT_ID',
        'IBIND_OAUTH1A_ACCESS_TOKEN',
        'IBIND_OAUTH1A_ACCESS_TOKEN_SECRET',
        'IBIND_OAUTH1A_CONSUMER_KEY',
        'IBIND_OAUTH1A_ENCRYPTION_KEY_FP',
        'IBIND_OAUTH1A_SIGNATURE_KEY_FP',
        'IBIND_OAUTH1A_DH_PRIME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing OAuth environment variables: {missing_vars}")
        return False
    else:
        print("✅ All OAuth environment variables are set")
        return True

# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    print("IBStore OAuth Configuration Example")
    print("=" * 50)
    
    # Method 1: Use hardcoded credentials (for testing only)
    print("\n1. Setting up OAuth with hardcoded credentials...")
    setup_oauth()
    verify_oauth_setup()
    
    # Method 2: Load from files (recommended for production)
    print("\n2. Setting up OAuth from credential files...")
    if setup_oauth_from_files():
        verify_oauth_setup()
    
    print("\n" + "=" * 50)
    print("Configuration complete!")
    print("\nNext steps:")
    print("1. Import this module in your trading scripts")
    print("2. Call setup_oauth() or setup_oauth_from_files()")
    print("3. Create IBStore with use_oauth=True")
    print("\nExample:")
    print("  from ibstore_oauth_config import setup_oauth")
    print("  from backtrader.stores import ibstore")
    print("  ")
    print("  setup_oauth()")
    print("  store = ibstore.IBStore(use_oauth=True, account_id='U12345678')")