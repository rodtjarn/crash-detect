#!/usr/bin/env python3
"""
Automated Daily Dip-Buying Analysis with ML
Runs 1 hour before market close, uses ML model to detect opportunities,
and sends alerts with recommended investment amounts.
"""

import yfinance as yf
import smtplib
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ml_crash_detector import MLCrashDetector

# Alert recipients
ALERTS = {
    'per': {
        'phone': '7374001329',
        'email': 'perjohananders@gmail.com'
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
    """Analyze current QQQ conditions using ML model"""
    try:
        # Load ML model
        detector = MLCrashDetector()
        detector.load_model('ml_crash_model.pkl')

        # Fetch data for ML analysis (1 year for features)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        qqq_data = yf.download('QQQ', start=start_date, end=end_date, progress=False)

        if qqq_data.empty or len(qqq_data) < 200:
            return None

        # Prepare data for ML
        data = pd.DataFrame()
        data['close'] = qqq_data['Close']
        data['high'] = qqq_data['High']
        data['low'] = qqq_data['Low']
        data['volume'] = qqq_data['Volume']

        # Fetch VIX
        vix_data = yf.download('^VIX', start=start_date, end=end_date, progress=False)
        data['vix'] = vix_data['Close']
        data = data.dropna()

        # Calculate ML features
        data = detector.calculate_technical_indicators(data)
        data = data.dropna(subset=detector.feature_names)

        if len(data) == 0:
            return None

        # Get latest values
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest

        current_price = float(latest['close'])
        prev_price = float(prev['close'])
        daily_change = ((current_price - prev_price) / prev_price) * 100

        # Get ML prediction
        features = np.array([[latest[col] for col in detector.feature_names]])
        prediction = detector.model.predict(features)[0]
        probability = detector.model.predict_proba(features)[0, 1]

        # Get drawdowns
        drawdown = float(latest['drawdown'])
        drawdown_30d = float(latest['drawdown_60d'])  # Using 60d as proxy

        # Check last purchase
        last_purchase_price = get_last_purchase_price()
        if last_purchase_price:
            drawdown_from_last = ((current_price - last_purchase_price) / last_purchase_price) * 100
        else:
            drawdown_from_last = None

        # Calculate recommended investment (if signal)
        investment_recommendation = None
        if probability >= 0.5:
            # Base percentage from probability (5-20%)
            prob_factor = (probability - 0.5) * 2
            base_pct = 0.05 + (prob_factor * 0.15)

            # Drawdown multiplier (1x to 3x)
            drawdown_magnitude = abs(drawdown)
            drawdown_multiplier = 1 + (drawdown_magnitude - 0.05) / 0.10
            drawdown_multiplier = np.clip(drawdown_multiplier, 1.0, 3.0)

            # Investment percentage (max 25%)
            investment_pct = min(base_pct * drawdown_multiplier, 0.25)

            investment_recommendation = {
                'percentage': investment_pct * 100,
                'amount_250k': int(250000 * investment_pct / 1000) * 1000,  # Round to nearest $1k
                'confidence': probability * 100
            }

        return {
            'current_price': current_price,
            'daily_change': daily_change,
            'drawdown_from_ath': drawdown * 100,
            'drawdown_30d': drawdown_30d * 100,
            'drawdown_from_last': drawdown_from_last,
            'last_purchase_price': last_purchase_price,
            'ml_probability': probability * 100,
            'ml_prediction': prediction,
            'vix': float(latest['vix']),
            'rsi': float(latest['rsi']),
            'investment_recommendation': investment_recommendation
        }

    except Exception as e:
        print(f"Error in ML analysis: {e}")
        return None


def load_portfolio():
    """Load portfolio tracking data"""
    try:
        with open('portfolio.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Initialize empty portfolio
        return {
            'initial_capital': 250000,
            'purchases': []
        }


def save_portfolio(portfolio):
    """Save portfolio tracking data"""
    with open('portfolio.json', 'w') as f:
        json.dump(portfolio, f, indent=2)


def calculate_portfolio_value(portfolio, current_price):
    """Calculate current portfolio value and metrics"""
    if not portfolio['purchases']:
        return None

    total_shares = sum(p['shares'] for p in portfolio['purchases'])
    total_invested = sum(p['investment'] for p in portfolio['purchases'])
    initial_capital = portfolio['initial_capital']
    cash_remaining = initial_capital - total_invested

    shares_value = total_shares * current_price
    total_value = shares_value + cash_remaining

    total_gain = total_value - initial_capital
    total_return_pct = (total_gain / initial_capital) * 100

    return {
        'total_shares': total_shares,
        'total_invested': total_invested,
        'cash_remaining': cash_remaining,
        'shares_value': shares_value,
        'total_value': total_value,
        'total_gain': total_gain,
        'total_return_pct': total_return_pct,
        'num_purchases': len(portfolio['purchases']),
        'avg_purchase_price': total_invested / total_shares if total_shares > 0 else 0
    }


def get_last_purchase_price():
    """Get the last purchase price from portfolio"""
    portfolio = load_portfolio()
    if portfolio['purchases']:
        return portfolio['purchases'][-1]['price']
    return None


def check_buy_signal(conditions):
    """Determine if ML model detects a buy signal"""
    if not conditions:
        return False, "Unable to fetch market data", None

    # ML model decision (probability >= 50%)
    ml_prob = conditions['ml_probability']

    if ml_prob >= 70:
        return True, f"Strong ML signal ({ml_prob:.1f}% confidence)", "STRONG"
    elif ml_prob >= 50:
        return True, f"Moderate ML signal ({ml_prob:.1f}% confidence)", "MODERATE"
    else:
        return False, f"No ML signal (only {ml_prob:.1f}% confidence)", None


def send_email_alert(config, subject, message):
    """Send email alert to both recipients"""
    if not config:
        print("Cannot send email: config not loaded")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = config['email']['sender_email']
        msg['To'] = ', '.join([ALERTS['per']['email'], ALERTS['jenna']['email']])
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        # Connect to SMTP server
        server = smtplib.SMTP(config['email']['smtp_server'], config['email']['smtp_port'])
        server.starttls()
        server.login(config['email']['sender_email'], config['email']['sender_password'])

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

            # Use messaging service if available, otherwise use phone number
            send_params = {
                'body': message,
                'to': to_number
            }

            if 'messaging_service_sid' in config['twilio']:
                send_params['messaging_service_sid'] = config['twilio']['messaging_service_sid']
            else:
                send_params['from_'] = config['twilio']['phone_number']

            sms = client.messages.create(**send_params)
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

    # Load portfolio and calculate current value
    portfolio = load_portfolio()
    portfolio_metrics = calculate_portfolio_value(portfolio, conditions['current_price'])

    print(f"\nQQQ Current Price: ${conditions['current_price']:.2f}")
    print(f"Daily Change: {conditions['daily_change']:+.2f}%")
    print(f"Drawdown from ATH: {conditions['drawdown_from_ath']:.2f}%")
    print(f"ML Buy Probability: {conditions['ml_probability']:.1f}%")
    print(f"VIX: {conditions['vix']:.1f}")
    print(f"RSI: {conditions['rsi']:.1f}")

    if portfolio_metrics:
        print(f"\n💼 PORTFOLIO STATUS:")
        print(f"Total Value: ${portfolio_metrics['total_value']:,.0f}")
        print(f"Total Gain/Loss: ${portfolio_metrics['total_gain']:+,.0f} ({portfolio_metrics['total_return_pct']:+.2f}%)")
        print(f"Purchases: {portfolio_metrics['num_purchases']}")
        print(f"Total Shares: {portfolio_metrics['total_shares']:.2f}")
        print(f"Cash Remaining: ${portfolio_metrics['cash_remaining']:,.0f}")
    elif conditions['last_purchase_price']:
        print(f"Last Purchase Price: ${conditions['last_purchase_price']:.2f}")
        print(f"Drawdown from last purchase: {conditions['drawdown_from_last']:+.2f}%")
    else:
        print("No previous purchases tracked")

    # Check for buy signal
    has_signal, reason, signal_strength = check_buy_signal(conditions)

    print(f"\n{'='*80}")
    if has_signal:
        print(f"🚨 BUY SIGNAL DETECTED: {reason}")
        print("="*80)

        # Prepare alert message
        emoji = "🟢" if signal_strength == "STRONG" else "🟡"
        subject = f"{emoji} ML BUY SIGNAL: {reason}"

        email_body = f"""
ML-DETECTED BUYING OPPORTUNITY
{'='*70}

{reason}

📊 MARKET CONDITIONS:
- QQQ Price: ${conditions['current_price']:.2f}
- Daily Change: {conditions['daily_change']:+.2f}%
- Drawdown from ATH: {conditions['drawdown_from_ath']:.2f}%
- VIX (Fear): {conditions['vix']:.1f}
- RSI (Momentum): {conditions['rsi']:.1f}

🤖 ML ANALYSIS:
- Buy Probability: {conditions['ml_probability']:.1f}%
- Signal Strength: {signal_strength}
"""

        if conditions['investment_recommendation']:
            rec = conditions['investment_recommendation']
            email_body += f"""
💰 INVESTMENT RECOMMENDATION:
- Suggested Amount: ${rec['amount_250k']:,} (from $250k portfolio)
- Percentage: {rec['percentage']:.1f}%
- Confidence: {rec['confidence']:.1f}%
"""

        # Add portfolio status
        if portfolio_metrics:
            email_body += f"""
💼 YOUR PORTFOLIO STATUS:
- Total Value: ${portfolio_metrics['total_value']:,.0f}
- Total Gain/Loss: ${portfolio_metrics['total_gain']:+,.0f} ({portfolio_metrics['total_return_pct']:+.2f}%)
- Total Shares Owned: {portfolio_metrics['total_shares']:.2f} QQQ
- Average Cost: ${portfolio_metrics['avg_purchase_price']:.2f}/share
- Current Price: ${conditions['current_price']:.2f}/share
- Cash Remaining: ${portfolio_metrics['cash_remaining']:,.0f}
- Number of Purchases: {portfolio_metrics['num_purchases']}
"""
        elif conditions['last_purchase_price']:
            email_body += f"""
📈 PURCHASE HISTORY:
- Last Purchase: ${conditions['last_purchase_price']:.2f}
- From Last Buy: {conditions['drawdown_from_last']:+.2f}%
"""
        else:
            email_body += """
💼 PORTFOLIO STATUS:
- No purchases yet (monitoring mode)
"""

        email_body += f"""
{'='*70}

📋 STRATEGY PERFORMANCE (Backtested):
- Average Return: +312.80% over 10 years
- Win Rate vs Weekly DCA: 90%
- Outperformance vs DCA: +58.30% average

Execute trade manually via Schwab if appropriate.
Analysis run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}
"""

        sms_body = f"{emoji} ML BUY: {conditions['ml_probability']:.0f}% confidence. QQQ ${conditions['current_price']:.2f}. Recommend ${conditions['investment_recommendation']['amount_250k']:,} ({conditions['investment_recommendation']['percentage']:.0f}%). Review Schwab."

        # Send alerts
        print("\nSending email alerts...")
        send_email_alert(config, subject, email_body)

    else:
        print(f"✓ No action needed: {reason}")
        print("="*80)

        # Send daily summary email (no SMS for no-action days)
        subject = f"📊 QQQ Daily Summary - No ML Signal ({datetime.now().strftime('%Y-%m-%d')})"

        email_body = f"""
QQQ DAILY MARKET SUMMARY
{'='*70}

Status: {reason}

📊 MARKET CONDITIONS:
- QQQ Price: ${conditions['current_price']:.2f}
- Daily Change: {conditions['daily_change']:+.2f}%
- Drawdown from ATH: {conditions['drawdown_from_ath']:.2f}%
- VIX (Fear): {conditions['vix']:.1f}
- RSI (Momentum): {conditions['rsi']:.1f}

🤖 ML ANALYSIS:
- Buy Probability: {conditions['ml_probability']:.1f}% (threshold: 50%)
- Model Prediction: HOLD
"""

        # Add portfolio status to daily summary
        if portfolio_metrics:
            email_body += f"""
💼 YOUR PORTFOLIO STATUS:
- Total Value: ${portfolio_metrics['total_value']:,.0f}
- Total Gain/Loss: ${portfolio_metrics['total_gain']:+,.0f} ({portfolio_metrics['total_return_pct']:+.2f}%)
- Total Shares Owned: {portfolio_metrics['total_shares']:.2f} QQQ
- Average Cost: ${portfolio_metrics['avg_purchase_price']:.2f}/share
- Current Price: ${conditions['current_price']:.2f}/share
- Cash Remaining: ${portfolio_metrics['cash_remaining']:,.0f}
- Number of Purchases: {portfolio_metrics['num_purchases']}
"""
        elif conditions['last_purchase_price']:
            email_body += f"""
📈 PURCHASE HISTORY:
- Last Purchase: ${conditions['last_purchase_price']:.2f}
- From Last Buy: {conditions['drawdown_from_last']:+.2f}%
"""
        else:
            email_body += """
💼 PORTFOLIO STATUS:
- No purchases yet (monitoring mode)
"""

        email_body += f"""
{'='*70}

ML model is monitoring for:
- Significant market dips (typically 5-10%+ drawdowns)
- Technical indicator alignment
- Historical patterns suggesting recovery

Expected signal frequency: ~1.65 per year
Strategy average return: +312.80% over 10 years (backtested)

Analysis run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}
"""

        print("\nSending daily summary email...")
        send_email_alert(config, subject, email_body)

    print("\n✓ Analysis complete\n")


if __name__ == '__main__':
    main()
