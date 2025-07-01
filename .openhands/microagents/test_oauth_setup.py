#!/usr/bin/env python3
"""
OAuth Setup Test Script for IBind Migration

This script validates OAuth 1.0a configuration for the IBPy to IBind migration.
Run this script to verify your OAuth setup before using Backtrader with IBind.

Usage:
    python test_oauth_setup.py

Environment Variables Required:
    IBKR_OAUTH_ACCESS_TOKEN
    IBKR_OAUTH_ACCESS_TOKEN_SECRET
    IBKR_OAUTH_CONSUMER_KEY
    IBKR_OAUTH_DH_PRIME
    IBKR_OAUTH_ENCRYPTION_KEY_FP
    IBKR_OAUTH_SIGNATURE_KEY_FP
    IBKR_ACCOUNT_ID
"""

import os
import sys
from pathlib import Path

def check_environment_variables():
    """Check if all required OAuth environment variables are set"""
    print("[CHECK] Checking OAuth environment variables...")
    
    required_vars = [
        'IBKR_OAUTH_ACCESS_TOKEN',
        'IBKR_OAUTH_ACCESS_TOKEN_SECRET', 
        'IBKR_OAUTH_CONSUMER_KEY',
        'IBKR_OAUTH_DH_PRIME',
        'IBKR_OAUTH_ENCRYPTION_KEY_FP',
        'IBKR_OAUTH_SIGNATURE_KEY_FP',
        'IBKR_ACCOUNT_ID'
    ]
    
    missing = []
    present = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing.append(var)
        else:
            present.append(var)
            # Show partial value for verification (mask sensitive data)
            if 'TOKEN' in var or 'SECRET' in var or 'KEY' in var:
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"  [PASS] {var}: {display_value}")
    
    if missing:
        print(f"\n[FAIL] Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        return False
    
    print(f"\n[PASS] All {len(present)} environment variables are set")
    return True

def check_key_files():
    """Check if OAuth key files exist and have proper permissions"""
    print("\n[CHECK] Checking OAuth key files...")
    
    encryption_key_path = os.environ.get('IBKR_OAUTH_ENCRYPTION_KEY_FP')
    signature_key_path = os.environ.get('IBKR_OAUTH_SIGNATURE_KEY_FP')
    
    if not encryption_key_path or not signature_key_path:
        print("[FAIL] Key file paths not set in environment variables")
        return False
    
    files_to_check = [
        ('Encryption Key', encryption_key_path),
        ('Signature Key', signature_key_path)
    ]
    
    all_good = True
    
    for name, path in files_to_check:
        file_path = Path(path)
        
        if not file_path.exists():
            print(f"[FAIL] {name} file not found: {path}")
            all_good = False
            continue
            
        if not file_path.is_file():
            print(f"[FAIL] {name} path is not a file: {path}")
            all_good = False
            continue
            
        # Check permissions (should be 600 or similar)
        stat = file_path.stat()
        permissions = oct(stat.st_mode)[-3:]
        
        if permissions not in ['600', '400', '640']:
            print(f"[WARNING]  {name} file permissions may be too open: {permissions} (recommended: 600)")
        else:
            print(f"[PASS] {name} file found with secure permissions: {permissions}")
            
        # Check if file is readable
        try:
            with open(file_path, 'r') as f:
                content = f.read(100)  # Read first 100 chars
                if 'BEGIN' in content and 'KEY' in content:
                    print(f"[PASS] {name} file appears to be a valid PEM file")
                else:
                    print(f"[WARNING]  {name} file may not be a valid PEM file")
        except Exception as e:
            print(f"[FAIL] Cannot read {name} file: {e}")
            all_good = False
    
    return all_good

def test_ibind_import():
    """Test if ibind library can be imported with OAuth support"""
    print("\n[CHECK] Testing ibind library import...")
    
    try:
        import ibind
        print("[PASS] ibind library imported successfully")
        
        # Check if OAuth components are available
        try:
            from ibind.client.ibind_client import IBind
            print("[PASS] IBind client available")
        except ImportError as e:
            print(f"[FAIL] IBind client import failed: {e}")
            return False
            
        try:
            from ibind.support.oauth_config import OAuth1aConfig
            print("[PASS] OAuth1aConfig available")
        except ImportError as e:
            print(f"[FAIL] OAuth1aConfig import failed: {e}")
            print("[TIP] Try: pip install ibind[oauth]")
            return False
            
        return True
        
    except ImportError as e:
        print(f"[FAIL] ibind library not found: {e}")
        print("[TIP] Try: pip install ibind[oauth]")
        return False

def test_backtrader_import():
    """Test if backtrader can be imported"""
    print("\n[CHECK] Testing backtrader import...")
    
    try:
        import backtrader as bt
        print("[PASS] backtrader imported successfully")
        
        # Check if IBStore is available
        try:
            store_class = bt.stores.IBStore
            print("[PASS] IBStore class available")
            return True
        except AttributeError as e:
            print(f"[FAIL] IBStore not found in backtrader: {e}")
            return False
            
    except ImportError as e:
        print(f"[FAIL] backtrader library not found: {e}")
        print("[TIP] Try: pip install backtrader")
        return False

def test_oauth_store_creation():
    """Test creating an OAuth-enabled IBStore"""
    print("\n[CHECK] Testing OAuth store creation...")
    
    try:
        import backtrader as bt
        
        account_id = os.environ.get('IBKR_ACCOUNT_ID')
        
        # Create OAuth-enabled store
        store = bt.stores.IBStore(
            use_oauth=True,
            account_id=account_id,
            _debug=True
        )
        
        print("[PASS] OAuth IBStore created successfully")
        
        # Test broker creation
        try:
            broker = store.getbroker()
            print("[PASS] OAuth broker created successfully")
            
            # Test if broker has required methods
            required_methods = ['connected', 'get_acc_cash', 'get_acc_value', 'placeOrder']
            for method in required_methods:
                if hasattr(broker, method):
                    print(f"[PASS] Broker method '{method}' available")
                else:
                    print(f"[WARNING]  Broker method '{method}' not found")
            
            return True
            
        except Exception as e:
            print(f"[FAIL] Broker creation failed: {e}")
            return False
            
    except Exception as e:
        print(f"[FAIL] OAuth store creation failed: {e}")
        return False

def test_oauth_config_creation():
    """Test creating OAuth configuration directly"""
    print("\n[CHECK] Testing OAuth configuration creation...")
    
    try:
        from ibind.support.oauth_config import OAuth1aConfig
        
        config = OAuth1aConfig(
            access_token=os.environ['IBKR_OAUTH_ACCESS_TOKEN'],
            access_token_secret=os.environ['IBKR_OAUTH_ACCESS_TOKEN_SECRET'],
            consumer_key=os.environ['IBKR_OAUTH_CONSUMER_KEY'],
            dh_prime=os.environ['IBKR_OAUTH_DH_PRIME'],
            encryption_key_fp=os.environ['IBKR_OAUTH_ENCRYPTION_KEY_FP'],
            signature_key_fp=os.environ['IBKR_OAUTH_SIGNATURE_KEY_FP']
        )
        
        print("[PASS] OAuth1aConfig created successfully")
        
        # Test if config has required attributes
        required_attrs = ['access_token', 'consumer_key', 'dh_prime']
        for attr in required_attrs:
            if hasattr(config, attr):
                print(f"[PASS] Config attribute '{attr}' available")
            else:
                print(f"[FAIL] Config attribute '{attr}' missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"[FAIL] OAuth configuration creation failed: {e}")
        return False

def run_comprehensive_test():
    """Run all OAuth setup tests"""
    print("[START] Starting OAuth Setup Validation")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", check_environment_variables),
        ("Key Files", check_key_files),
        ("IBind Import", test_ibind_import),
        ("Backtrader Import", test_backtrader_import),
        ("OAuth Config", test_oauth_config_creation),
        ("OAuth Store", test_oauth_store_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[FAIL] {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("[RESULTS] OAuth Setup Test Results")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("Your OAuth setup is ready for live trading!")
        return True
    else:
        print(f"\n[WARNING]  {total - passed} tests failed")
        print("Please fix the issues above before proceeding.")
        return False

def print_setup_help():
    """Print help for OAuth setup"""
    print("\n[TIP] OAuth Setup Help")
    print("=" * 30)
    print("""
To set up OAuth for IBind migration:

1. Obtain OAuth credentials from Interactive Brokers
2. Set environment variables:
   export IBKR_OAUTH_ACCESS_TOKEN="your_token"
   export IBKR_OAUTH_ACCESS_TOKEN_SECRET="your_secret"
   export IBKR_OAUTH_CONSUMER_KEY="your_key"
   export IBKR_OAUTH_DH_PRIME="your_dh_prime_hex"
   export IBKR_OAUTH_ENCRYPTION_KEY_FP="/path/to/encryption.pem"
   export IBKR_OAUTH_SIGNATURE_KEY_FP="/path/to/signature.pem"
   export IBKR_ACCOUNT_ID="your_account"

3. Install required packages:
   pip install ibind[oauth] backtrader cryptography

4. Run this test script again

For detailed instructions, see: .openhands/microagents/oauth_setup_microagent.md
""")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_setup_help()
        sys.exit(0)
    
    success = run_comprehensive_test()
    
    if not success:
        print_setup_help()
        sys.exit(1)
    
    print("\n[BULLSEYE] Next Steps:")
    print("- Your OAuth setup is validated and ready")
    print("- You can now use Backtrader with IBind OAuth")
    print("- See examples/ directory for usage examples")
    print("- Start with paper trading before going live")