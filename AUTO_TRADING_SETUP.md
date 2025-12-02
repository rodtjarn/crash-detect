# Automated Daily Trading Analysis Setup

This guide walks you through setting up automated daily analysis for the QQQ dip-buying strategy on Arch Linux.

## What This Does

- **Automatically wakes** your Arch Linux system at 3:00 PM ET (1 hour before market close)
- **Runs analysis** to check if QQQ meets buy signal criteria
- **Sends alerts** via email and SMS if opportunity detected
- **Shuts down** automatically after completion
- **Power cost**: ~$0.30/month (only on ~5 minutes per trading day)

## Prerequisites

1. **Python virtual environment** with required packages:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install yfinance pandas twilio
   ```

2. **Gmail App Password** (for email alerts):
   - Enable 2FA on your Gmail account
   - Generate app password at: https://myaccount.google.com/apppasswords
   - Use this app password (not your regular Gmail password)

3. **Twilio Account** (for SMS alerts):
   - Sign up at: https://www.twilio.com/try-twilio
   - Get your Account SID, Auth Token, and phone number
   - Note: Free trial includes $15 credit (~500 SMS messages)

## Step 1: Configure Credentials

1. Copy the template:
   ```bash
   cp config.json.template config.json
   ```

2. Edit `config.json` with your credentials:
   ```bash
   nano config.json
   ```

3. Fill in:
   - **email.sender**: Your Gmail address
   - **email.password**: Gmail app password (16 characters, no spaces)
   - **twilio.account_sid**: From Twilio dashboard
   - **twilio.auth_token**: From Twilio dashboard
   - **twilio.phone_number**: Your Twilio number (format: +1XXXXXXXXXX)

4. Save and protect the file:
   ```bash
   chmod 600 config.json
   ```

## Step 2: Test Manually

Before setting up automation, test that everything works:

```bash
# Activate virtual environment
source venv/bin/activate

# Run manual test
python auto_daily_analysis.py
```

You should see output like:
```
================================================================================
DAILY DIP-BUYING ANALYSIS - 2025-12-02 15:00:00
================================================================================

Analyzing current market conditions...

QQQ Current Price: $XXX.XX
Daily Change: +X.XX%
Drawdown from 30-day high: -X.XX%
No previous purchase tracked

================================================================================
✓ No action needed: No buying opportunity detected
================================================================================

✓ Analysis complete
```

If there's a buy signal, you'll see alerts being sent.

## Step 3: Install Automated System

Run the setup script with sudo:

```bash
sudo ./setup_auto_trading_schedule.sh
```

This will:
1. Create systemd service for running analysis
2. Create systemd timer for weekday execution at 3:00 PM ET
3. Optionally set up RTC wake for automatic boot from shutdown

When prompted about RTC wake setup:
- Choose **Yes** for fully automatic operation (recommended)
- Choose **No** if you prefer manual wake setup

## Step 4: Verify Installation

Check that the timer is active:
```bash
systemctl status trading-analysis.timer
```

List all scheduled times:
```bash
systemctl list-timers
```

You should see `trading-analysis.timer` scheduled for weekdays at 3:00 PM ET.

## Step 5: Test Automatic Execution

Test the service manually:
```bash
sudo systemctl start trading-analysis.service
```

Check the logs:
```bash
journalctl -u trading-analysis.service -n 50
```

**Note**: The service will shutdown your system after running. Make sure you've saved all work before testing!

## Strategy Parameters

The system monitors QQQ for these conditions:

- **Buy Signal Triggers**:
  - Single-day drop ≥ 5%, OR
  - Price drops ≥ 5% below last purchase

- **Buy Amounts** (linear progression):
  - 1st buy: $10,000
  - 2nd buy: $20,000
  - 3rd buy: $30,000
  - 4th buy: $40,000
  - And so on...

- **Annual Cap**: $300,000 with smart sizing
- **Reset**: When price recovers 5% above last $10K purchase

## Alert Recipients

Alerts are sent to:
- **Per Edstrom**: 737-400-1329, perjohandanders@gmail.com
- **Jenna Edstrom**: 737-400-2720, jenna.edstrom@gmail.com

## Tracking Last Purchase

The system tracks your last purchase price in `last_purchase.txt`. To update it manually:

```bash
# Set last purchase price to $450.00
echo "450.00" > last_purchase.txt
```

This helps the system calculate drawdowns from your actual last purchase.

## Manual Commands

```bash
# Check timer status
systemctl status trading-analysis.timer

# View recent logs
journalctl -u trading-analysis.service -n 50

# Follow logs in real-time (during manual test)
journalctl -u trading-analysis.service -f

# Run analysis manually (will shutdown after!)
sudo systemctl start trading-analysis.service

# Disable auto-run
sudo systemctl disable trading-analysis.timer

# Re-enable auto-run
sudo systemctl enable trading-analysis.timer
sudo systemctl start trading-analysis.timer
```

## Manual RTC Wake (Alternative to Automatic)

If you chose not to set up automatic RTC wake, you can set it manually before each shutdown:

```bash
# Wake tomorrow at 3:00 PM
sudo rtcwake -m off -l -t $(date -d 'tomorrow 15:00' +%s)

# Wake today at 3:00 PM (if before 3 PM)
sudo rtcwake -m off -l -t $(date -d 'today 15:00' +%s)
```

## Troubleshooting

### No alerts received
1. Check config.json credentials are correct
2. Verify Gmail app password (not regular password)
3. Check Twilio account has credits
4. Review logs: `journalctl -u trading-analysis.service -n 50`

### System not waking automatically
1. Check RTC wake service: `systemctl status rtc-wake-trading.service`
2. Verify BIOS supports RTC wake (check BIOS settings)
3. Test manual RTC wake: `sudo rtcwake -m no -l -t $(date -d 'tomorrow 15:00' +%s)`
4. Check system logs after wake: `journalctl -b -n 100`

### Timer not running
1. Check timer is enabled: `systemctl is-enabled trading-analysis.timer`
2. Start timer: `sudo systemctl start trading-analysis.timer`
3. Check for errors: `systemctl status trading-analysis.timer`

### Email sending fails
- Gmail: Ensure 2FA is enabled and using app password
- Check SMTP server/port are correct for your provider
- Test with `telnet smtp.gmail.com 587`

### SMS sending fails
- Verify Twilio credentials in config.json
- Check Twilio account has credits
- Ensure phone number format: +1XXXXXXXXXX
- Install twilio package: `pip install twilio`

## Cost Breakdown

- **Power consumption**: ~5 minutes/day = ~$0.30/month
  - Assumes typical desktop at 100W, $0.12/kWh
  - 5 min × 20 trading days × 100W × $0.12/kWh = $0.30

- **Twilio SMS**: ~$0.0075 per message
  - ~3 signals per year × 2 recipients = 6 messages/year = $0.05/year

**Total cost**: ~$3.60/year

## Security Notes

1. **config.json** contains sensitive credentials - never commit to git
2. File permissions should be 600 (owner read/write only)
3. Gmail app passwords can be revoked at any time
4. Twilio credentials can be regenerated if compromised

## System Behavior

**On Trading Days (Mon-Fri)**:
- 3:00 PM ET: System wakes from shutdown
- 3:00-3:03 PM: Fetch market data and analyze
- 3:03-3:05 PM: Send alerts if buy signal detected
- 3:05 PM: System shuts down automatically
- Before shutdown: Sets next wake time for 3:00 PM ET

**On Weekends/Holidays**:
- System remains off
- No scheduled wakes
- Manual boot works normally

## Expected Signal Frequency

Based on 20-year backtest:
- **Total signals**: 26 buys over 20 years
- **Average frequency**: ~1.3 buys per year
- **Concentrated in crashes**: 9 buys in 2008, 2 buys in 2009, etc.

Most trading days will result in "No action needed" messages (no alerts sent).

## Performance Metrics (20-year backtest)

- **Total invested**: $720,000
- **Final value**: $12,397,999
- **Annualized return**: 15.29%
- **Return per $1 invested**: $17.22
- **Total buys**: 26
- **Skipped opportunities**: 10 (all in late 2008 when cap was hit)

## Uninstalling

To remove the automated system:

```bash
# Disable and stop timer
sudo systemctl disable trading-analysis.timer
sudo systemctl stop trading-analysis.timer

# Remove systemd files
sudo rm /etc/systemd/system/trading-analysis.service
sudo rm /etc/systemd/system/trading-analysis.timer
sudo rm /etc/systemd/system/rtc-wake-trading.service
sudo rm /usr/local/bin/set-next-trading-wake

# Reload systemd
sudo systemctl daemon-reload
```

## Support

For issues with:
- **Strategy logic**: Review optimized_price_reset.py
- **Automation setup**: Check setup_auto_trading_schedule.sh
- **Daily analysis**: Review auto_daily_analysis.py
- **System logs**: `journalctl -u trading-analysis.service`

