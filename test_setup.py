#!/usr/bin/env python3
"""
Test Script for Trading Alert System
Verifies that all dependencies are installed and configuration is correct
"""

import sys

def test_imports():
    """Test that all required packages can be imported"""
    
    print("Testing Python package imports...")
    print("-" * 50)
    
    packages = {
        'yfinance': 'yfinance',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'hmmlearn': 'hmmlearn.hmm',
        'sklearn': 'scikit-learn'
    }
    
    failed = []
    
    for name, import_name in packages.items():
        try:
            if name == 'hmmlearn':
                from hmmlearn.hmm import GaussianHMM
            elif name == 'yfinance':
                import yfinance as yf
            elif name == 'pandas':
                import pandas as pd
            elif name == 'numpy':
                import numpy as np
            elif name == 'sklearn':
                import sklearn
            
            print(f"✓ {name:15} OK")
        except ImportError as e:
            print(f"✗ {name:15} FAILED - {e}")
            failed.append(name)
    
    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("\nInstall with:")
        print("  pip install yfinance pandas numpy hmmlearn scikit-learn")
        return False
    else:
        print("\n✓ All required packages installed!")
        return True

def test_optional_imports():
    """Test optional packages"""
    
    print("\nTesting optional packages...")
    print("-" * 50)
    
    try:
        from twilio.rest import Client
        print("✓ twilio         OK (SMS alerts available)")
    except ImportError:
        print("○ twilio         Not installed (SMS alerts disabled)")
        print("  Install with: pip install twilio")

def test_config():
    """Test configuration file"""
    
    print("\nTesting configuration...")
    print("-" * 50)
    
    import json
    import os
    
    if not os.path.exists('config.json'):
        print("✗ config.json not found")
        print("  Copy config.json.template to config.json")
        return False
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        print("✓ config.json exists and is valid JSON")
        
        # Check email config
        if config['email']['enabled']:
            if 'your_email@gmail.com' in config['email']['sender_email']:
                print("⚠ Email: Not configured (using template values)")
            else:
                print("✓ Email: Configured")
        else:
            print("○ Email: Disabled")
        
        # Check SMS config
        if config['sms']['enabled']:
            if 'YOUR_TWILIO' in config['sms']['twilio_account_sid']:
                print("⚠ SMS: Enabled but not configured")
            else:
                print("✓ SMS: Configured")
        else:
            print("○ SMS: Disabled")
        
        return True
        
    except Exception as e:
        print(f"✗ Error reading config.json: {e}")
        return False

def test_data_fetch():
    """Test fetching market data"""
    
    print("\nTesting data fetch...")
    print("-" * 50)
    
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print("Fetching sample data from Yahoo Finance...")
        data = yf.download('^GSPC', start=start_date, end=end_date, progress=False)
        
        if len(data) > 0:
            print(f"✓ Successfully fetched {len(data)} days of data")
            print(f"  Latest close: ${float(data['Close'].iloc[-1]):.2f}")
            return True
        else:
            print("✗ No data returned")
            return False
            
    except Exception as e:
        print(f"✗ Error fetching data: {e}")
        return False

def test_email_config():
    """Test email configuration (without sending)"""
    
    print("\nTesting email configuration...")
    print("-" * 50)
    
    try:
        import json
        import smtplib
        
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        if not config['email']['enabled']:
            print("○ Email alerts disabled in config")
            return True
        
        email_cfg = config['email']
        
        if 'your_email' in email_cfg['sender_email']:
            print("⚠ Email not configured (using template)")
            return False
        
        print(f"  Server: {email_cfg['smtp_server']}:{email_cfg['smtp_port']}")
        print(f"  From: {email_cfg['sender_email']}")
        print(f"  To: {email_cfg['recipient_email']}")
        
        # Try to connect (don't login or send)
        try:
            server = smtplib.SMTP(email_cfg['smtp_server'], 
                                email_cfg['smtp_port'], timeout=5)
            server.starttls()
            server.quit()
            print("✓ SMTP server reachable")
            print("\n  Note: Email credentials not tested")
            print("  Run the main script to test actual sending")
            return True
        except Exception as e:
            print(f"✗ Cannot reach SMTP server: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         TRADING ALERT SYSTEM - SETUP TEST                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    results = []
    
    results.append(("Imports", test_imports()))
    test_optional_imports()
    results.append(("Config", test_config()))
    results.append(("Data Fetch", test_data_fetch()))
    results.append(("Email Config", test_email_config()))
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20} {status}")
    
    all_pass = all(r[1] for r in results)
    
    if all_pass:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("  1. Edit config.json with your email settings")
        print("  2. Run: python trading_alert_system.py")
    else:
        print("\n✗ Some tests failed")
        print("\nPlease fix the issues above before running the main script")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
