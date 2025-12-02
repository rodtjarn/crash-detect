#!/usr/bin/env python3
"""
Automated Daily Dip-Buying Analysis
Runs 1 hour before market close, analyzes current conditions,
and sends alerts if buying opportunity exists.
"""

import yfinance as yf
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Alert recipients
ALERTS = {
    'per': {
        'phone': '7374001329',
        'email': 'perjohandanders@gmail.com'
    },
    'jenna': {
        'phone': '7374002720',
        'email': 'jenna.edstrom@gmail.com'
    }
}


def load_config():
    """Load email/SMS configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found")
        return None


def get_current_conditions():
    """Analyze current QQQ conditions"""
    # Fetch recent data (90 days for context)
    qqq = yf.download('QQQ', period='90d', progress=False, auto_adjust=True)

    if qqq.empty:
        return None

    # Extract scalar values (handle MultiIndex columns from yfinance)
    close_series = qqq['Close']
    current_price = close_series.iloc[-1].item() if hasattr(close_series.iloc[-1], 'item') else float(close_series.iloc[-1])
    prev_price = close_series.iloc[-2].item() if hasattr(close_series.iloc[-2], 'item') else float(close_series.iloc[-2])

    # Calculate daily change
    daily_change = ((current_price - prev_price) / prev_price) * 100

    # Get recent high (30 days)
    max_val = qqq['Close'].tail(30).max()
    recent_high = max_val.item() if hasattr(max_val, 'item') else float(max_val)
    drawdown_from_high = ((current_price - recent_high) / recent_high) * 100

    # Check last purchase price from our tracking file
    last_purchase_price = get_last_purchase_price()

    if last_purchase_price:
        drawdown_from_last = ((current_price - last_purchase_price) / last_purchase_price) * 100
    else:
        drawdown_from_last = None

    return {
        'current_price': current_price,
        'daily_change': daily_change,
        'drawdown_from_high': drawdown_from_high,
        'drawdown_from_last': drawdown_from_last,
        'last_purchase_price': last_purchase_price
    }


def get_last_purchase_price():
    """Get the last purchase price from tracking file"""
    try:
        with open('last_purchase.txt', 'r') as f:
            return float(f.read().strip())
    except FileNotFoundError:
        return None


def check_buy_signal(conditions):
    """Determine if conditions warrant a buy signal"""
    if not conditions:
        return False, "Unable to fetch market data"

    # Check for 5% single-day drop
    if conditions['daily_change'] <= -5.0:
        return True, f"Single-day drop: {conditions['daily_change']:.1f}%"

    # Check for 5% drawdown from last purchase
    if conditions['drawdown_from_last'] and conditions['drawdown_from_last'] <= -5.0:
        return True, f"5% below last purchase: {conditions['drawdown_from_last']:.1f}%"

    # No signal
    return False, "No buying opportunity detected"


def send_email_alert(config, subject, message):
    """Send email alert to both recipients"""
    if not config:
        print("Cannot send email: config not loaded")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = config['email']['sender']
        msg['To'] = ', '.join([ALERTS['per']['email'], ALERTS['jenna']['email']])
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        # Connect to SMTP server
        server = smtplib.SMTP(config['email']['smtp_server'], config['email']['smtp_port'])
        server.starttls()
        server.login(config['email']['sender'], config['email']['password'])

        server.send_message(msg)
        server.quit()

        print("✓ Email alerts sent successfully")
        return True

    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def send_sms_alert(config, message):
    """Send SMS alert via Twilio"""
    if not config or 'twilio' not in config:
        print("Cannot send SMS: Twilio not configured")
        return False

    try:
        from twilio.rest import Client

        client = Client(
            config['twilio']['account_sid'],
            config['twilio']['auth_token']
        )

        # Send to both phones
        for person, info in ALERTS.items():
            to_number = f"+1{info['phone']}"
            sms = client.messages.create(
                body=message,
                from_=config['twilio']['phone_number'],
                to=to_number
            )
            print(f"✓ SMS sent to {person}: {sms.sid}")

        return True

    except ImportError:
        print("✗ Twilio not installed (pip install twilio)")
        return False
    except Exception as e:
        print(f"✗ SMS failed: {e}")
        return False


def main():
    """Main execution"""
    print("="*80)
    print(f"DAILY DIP-BUYING ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Load configuration
    config = load_config()

    # Get current market conditions
    print("\nAnalyzing current market conditions...")
    conditions = get_current_conditions()

    if not conditions:
        print("✗ Failed to fetch market data")
        return

    print(f"\nQQQ Current Price: ${conditions['current_price']:.2f}")
    print(f"Daily Change: {conditions['daily_change']:+.2f}%")
    print(f"Drawdown from 30-day high: {conditions['drawdown_from_high']:.2f}%")

    if conditions['last_purchase_price']:
        print(f"Last Purchase Price: ${conditions['last_purchase_price']:.2f}")
        print(f"Drawdown from last purchase: {conditions['drawdown_from_last']:+.2f}%")
    else:
        print("No previous purchase tracked")

    # Check for buy signal
    has_signal, reason = check_buy_signal(conditions)

    print(f"\n{'='*80}")
    if has_signal:
        print(f"🚨 BUY SIGNAL DETECTED: {reason}")
        print("="*80)

        # Prepare alert message
        subject = f"🚨 QQQ Dip-Buying Opportunity - {reason}"

        email_body = f"""
QQQ DIP-BUYING OPPORTUNITY DETECTED

Trigger: {reason}

Current Conditions:
- QQQ Price: ${conditions['current_price']:.2f}
- Daily Change: {conditions['daily_change']:+.2f}%
- 30-day Drawdown: {conditions['drawdown_from_high']:.2f}%
"""

        if conditions['last_purchase_price']:
            email_body += f"- Last Purchase: ${conditions['last_purchase_price']:.2f}\n"
            email_body += f"- From Last Buy: {conditions['drawdown_from_last']:+.2f}%\n"

        email_body += f"""
Strategy Parameters:
- Linear progression: $10K, $20K, $30K, $40K...
- Annual cap: $300,000
- Smart sizing enabled

Review the opportunity and execute trade manually via Schwab if appropriate.

Analysis run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}
"""

        sms_body = f"QQQ BUY SIGNAL: {reason}. Price: ${conditions['current_price']:.2f}, Change: {conditions['daily_change']:+.1f}%. Review & trade via Schwab."

        # Send alerts
        print("\nSending alerts...")
        send_email_alert(config, subject, email_body)
        send_sms_alert(config, sms_body)

    else:
        print(f"✓ No action needed: {reason}")
        print("="*80)

    print("\n✓ Analysis complete\n")


if __name__ == '__main__':
    main()
