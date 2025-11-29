# Detect Crash - Trading Alert System

Automated severe market crash detection system that alerts you via email when all 4 critical indicators align.

## What It Does

Monitors the stock market and sends email alerts **only during severe crashes** when:
- VIX > 30 (extreme fear)
- Put/Call Ratio > 1.2 (high panic)
- Fractal Dimension < 1.15 (realistic threshold)
- Markov State = Crisis (market in crisis mode)

**Tested Performance:**
- ✅ Caught COVID crash on March 16, 2020 (VIX 82.69)
- ✅ Triggered 1 day before absolute bottom
- ✅ Only 1 signal in 2025 (April 7) - no false alarms

## Files

- `trading_alert_system.py` - Main detection script
- `config.json` - Email credentials and thresholds
- `setup_linux_autorun.sh` - Auto-boot setup for Arch Linux
- `test_setup.py` - Verify dependencies and configuration
- `CLAUDE.md` - Detailed technical documentation

## Quick Start (Arch Linux)

### 1. Install Dependencies

```bash
sudo pacman -S python python-pip
pip install yfinance pandas numpy hmmlearn scikit-learn
```

### 2. Configure Email

Edit `config.json`:
```json
{
  "email": {
    "sender_email": "your_email@gmail.com",
    "sender_password": "your_gmail_app_password",
    "recipient_email": "your_email@gmail.com"
  }
}
```

**Gmail App Password:** https://myaccount.google.com/apppasswords

### 3. Test Setup

```bash
python test_setup.py
```

### 4. Run Manually

```bash
python trading_alert_system.py
```

## Auto-Boot Setup (Arch Linux)

**Boot → Analyze → Shutdown automatically at 3:00 PM ET daily**

### Requirements:
1. RTC Wake enabled in BIOS (check "Power Management" settings)
2. systemd (standard on Arch)

### Installation:

```bash
./setup_linux_autorun.sh
```

This configures:
- ✅ System boots at 3:00 PM ET on weekdays (1hr before market close)
- ✅ Script runs automatically
- ✅ Computer shuts down after completion
- ✅ Next wake time set before shutdown
- ✅ Skips weekends automatically

**Power consumption:** ~$0.30/month (computer off 23+ hours/day)

### Manual Commands:

```bash
# Test without shutdown
python trading_alert_system.py

# Set next wake time
./set_rtc_wake.sh

# Check logs
tail -f trading_alert.log

# View service status
systemctl status trading-alert.service
```

## Configuration

### Thresholds (Severe Crashes Only)

Current settings in `config.json`:
```json
{
  "thresholds": {
    "fractal_max": 1.15,     // Realistic (COVID = 1.067)
    "vix_min": 30,           // Severe fear only
    "put_call_min": 1.2,     // High panic
    "markov_state": "Crisis" // Full crisis mode
  }
}
```

**These thresholds are optimized to catch only severe crashes with minimal false alarms.**

## How It Works

### Market Hours
- US Stock Market: 9:30 AM - 4:00 PM ET
- Script runs: 3:00 PM ET (1 hour before close)
- Allows time for signal analysis before market close

### RTC Wake (BIOS Level)
1. Computer is completely off (not sleep/hibernation)
2. BIOS RTC alarm triggers at scheduled time
3. Computer boots automatically
4. systemd runs trading-alert.service
5. Script analyzes market and sends email if conditions met
6. System sets next wake time and shuts down

**No GRUB configuration needed** - wake happens at BIOS level before bootloader.

## Dual Boot Notes

Since you're dual-booting Windows/Linux:
- RTC wake works fine with dual boot
- Linux controls boot (GRUB default)
- Windows partition unaffected
- BIOS wakes to Linux automatically

## Expected Alerts

**Frequency:** 1-3 alerts per year during severe market conditions

**Recent Example (2025):**
- Signal: April 7, 2025
- S&P 500: $5,062
- VIX: 46.98
- Market bottom: Next day at $4,983 (-1.6%)

## Troubleshooting

### RTC Wake Not Working

1. Check BIOS support:
```bash
cat /sys/class/rtc/rtc0/wakealarm
```

2. Enable in BIOS:
- Enter BIOS (DEL/F2/F12 at boot)
- Find "Power Management" or "ACPI Configuration"
- Enable "RTC Wake" or "Wake on RTC Alarm"

3. Set wake time manually:
```bash
./set_rtc_wake.sh
```

### Email Not Sending

1. Verify Gmail app password (not regular password)
2. Check spam folder
3. Run test: `python test_setup.py`

### Dependencies Missing

```bash
pip install --upgrade yfinance pandas numpy hmmlearn scikit-learn
```

## License

Educational purposes only. Not financial advice. Trading involves risk.

## Support

See `CLAUDE.md` for detailed technical documentation and architecture.
# crash-detect
