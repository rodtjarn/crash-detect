# Quick Start Guide

## 1. Configure Credentials (5 minutes)

```bash
# Copy template
cp config.json.template config.json

# Edit with your credentials
nano config.json
```

**Gmail Setup**:
- Enable 2FA: https://myaccount.google.com/security
- Create app password: https://myaccount.google.com/apppasswords
- Use app password in config.json (not regular password)

**Twilio Setup** (optional for SMS):
- Sign up: https://www.twilio.com/try-twilio
- Get credentials from dashboard
- Free trial includes $15 credit

## 2. Test Manually (2 minutes)

```bash
# Activate virtual environment
source venv/bin/activate

# Run test
python auto_daily_analysis.py
```

Expected output: Current QQQ analysis with buy signal check

## 3. Install Automation (5 minutes)

```bash
# Run setup with sudo
sudo ./setup_auto_trading_schedule.sh
```

Choose **Yes** when prompted for RTC wake setup.

## 4. Verify Installation (1 minute)

```bash
# Check timer is active
systemctl status trading-analysis.timer

# View scheduled times
systemctl list-timers | grep trading
```

You should see next run scheduled for 3:00 PM ET on next trading day.

## Done!

Your system will now:
- ✅ Wake at 3:00 PM ET on trading days
- ✅ Check QQQ for 5% dip opportunities
- ✅ Send email/SMS alerts to Per and Jenna
- ✅ Shutdown automatically after analysis
- ✅ Cost: ~$0.30/month in electricity

## Manual Commands

```bash
# Run analysis now (will shutdown!)
sudo systemctl start trading-analysis.service

# View recent logs
journalctl -u trading-analysis.service -n 50

# Disable auto-run
sudo systemctl disable trading-analysis.timer
```

## Tracking Your Purchases

Update `last_purchase.txt` when you make a purchase:

```bash
# Example: Bought QQQ at $450.00
echo "450.00" > last_purchase.txt
```

This helps the system calculate 5% drawdowns from your actual last purchase.

## Full Documentation

See **AUTO_TRADING_SETUP.md** for:
- Detailed troubleshooting
- Security notes
- Cost breakdown
- System behavior details
- Uninstall instructions

## Support

Alert recipients:
- Per Edstrom: 737-400-1329, perjohandanders@gmail.com  
- Jenna Edstrom: 737-400-2720, jenna.edstrom@gmail.com

Strategy: Linear progression ($10K, $20K, $30K...), 5% triggers, $300K annual cap

Backtest results: $720K invested → $12.4M (15.29% annualized, $17.22 per dollar)
