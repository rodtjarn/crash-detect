# Arch Linux Installation Guide

Quick installation guide for Arch Linux systems.

## Pre-Installation (Your Arch Machine)

### 1. Check RTC Wake Support

```bash
# Check if RTC wake is available
cat /sys/class/rtc/rtc0/wakealarm

# Should show a number or empty (not an error)
```

### 2. Enable RTC Wake in BIOS

**Reboot and enter BIOS** (usually DEL, F2, or F12):
1. Find **Power Management** or **ACPI Configuration**
2. Enable **"RTC Wake"** or **"Wake on RTC Alarm"**
3. Save and exit

## Installation

### 1. Install Python Dependencies

```bash
sudo pacman -S python python-pip

pip install yfinance pandas numpy hmmlearn scikit-learn
# OR
pip install -r requirements.txt
```

### 2. Configure Email

```bash
# Copy template
cp config.json.template config.json

# Edit with your credentials
nano config.json
# OR
vim config.json
```

**Gmail Setup:**
1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use the 16-character app password (NOT your regular password)

### 3. Test Configuration

```bash
python test_setup.py
```

Should show:
- ✓ All packages installed
- ✓ Email configured
- ✓ Data fetch working

### 4. Test Manual Run

```bash
python trading_alert_system.py
```

You should see current market indicators and whether any signal is active.

## Auto-Boot Setup (Optional but Recommended)

**Enables: Boot at 3PM ET → Analyze → Shutdown → Repeat**

```bash
# Run the setup script
./setup_linux_autorun.sh
```

This installs:
- systemd service: `trading-alert.service`
- Shutdown hook: `set-next-wake.service`
- Wake scheduler: `set_rtc_wake.sh`

### What It Does:

1. **3:00 PM ET every weekday**: Computer boots via RTC wake
2. **Auto-runs**: Script executes, analyzes market, sends email if signal
3. **Auto-shutdown**: System powers off after completion
4. **Sets next wake**: Before shutdown, schedules next weekday wake
5. **Skips weekends**: Automatically calculates next trading day

### Power Consumption:

- Running: ~50W for 2-3 minutes/day
- Shutdown: ~1-2W the rest of the time
- **Total: ~$0.30/month**

## Manual Commands

```bash
# Test the service (will shutdown!)
sudo systemctl start trading-alert.service

# Set wake time manually
./set_rtc_wake.sh

# Check when next wake is scheduled
cat /sys/class/rtc/rtc0/wakealarm | xargs -I {} date -d @{}

# View logs
tail -f trading_alert.log
tail -f wake_schedule.log

# Check service status
systemctl status trading-alert.service
systemctl status set-next-wake.service

# Disable auto-boot
sudo systemctl disable trading-alert.service
sudo systemctl disable set-next-wake.service
```

## Dual Boot Notes

Your setup: Linux (Arch) controls boot via GRUB, Windows on separate drive.

**RTC Wake behavior:**
- ✅ Works perfectly with dual boot
- ✅ Always boots to default (Arch via GRUB)
- ✅ Windows unaffected
- ✅ No GRUB configuration needed

**If GRUB timeout is set:**
- BIOS wakes → GRUB countdown → Boots default (Arch)
- Set GRUB_TIMEOUT=0 in `/etc/default/grub` for instant boot (optional)

## Troubleshooting

### RTC Wake Not Working

**Check BIOS setting:**
```bash
# Try setting a test wake for 2 minutes from now
echo 0 | sudo tee /sys/class/rtc/rtc0/wakealarm
echo $(($(date +%s) + 120)) | sudo tee /sys/class/rtc/rtc0/wakealarm

# Shutdown and wait
sudo shutdown -h now
```

Computer should boot in ~2 minutes.

**Common issues:**
- BIOS setting not enabled → Enter BIOS and enable RTC Wake
- Secure Boot interfering → Disable Secure Boot (optional)
- Fast Boot enabled → Disable Fast Boot in BIOS

### Service Not Running

```bash
# Check service status
systemctl status trading-alert.service

# View full logs
journalctl -u trading-alert.service -n 50

# Test manually
python trading_alert_system.py
```

### Email Not Sending

1. Verify Gmail app password (not regular password)
2. Check spam folder
3. Test SMTP manually:
```bash
python test_setup.py
```

### Wake Time Wrong

RTC uses UTC. Script automatically converts 3PM ET to UTC (20:00).

During DST changes, wake time may be off by 1 hour. This auto-corrects after first run.

## Uninstall

```bash
# Disable services
sudo systemctl disable trading-alert.service
sudo systemctl disable set-next-wake.service

# Remove service files
sudo rm /etc/systemd/system/trading-alert.service
sudo rm /etc/systemd/system/set-next-wake.service

# Reload systemd
sudo systemctl daemon-reload

# Clear RTC wake
echo 0 | sudo tee /sys/class/rtc/rtc0/wakealarm

# Remove project (optional)
rm -rf ~/detect_crash
```

## Directory Structure

```
detect_crash/
├── trading_alert_system.py    # Main script
├── config.json                 # Your credentials (not in git)
├── config.json.template        # Template
├── setup_linux_autorun.sh      # Auto-boot installer
├── set_rtc_wake.sh            # Wake scheduler (created by setup)
├── test_setup.py              # Verification script
├── requirements.txt            # Python dependencies
├── README.md                   # General docs
├── CLAUDE.md                   # Technical docs
├── INSTALL_ARCH.md            # This file
├── trading_alert.log          # Runtime logs (created on first run)
└── wake_schedule.log          # Wake schedule log (created by setup)
```

## Support

- **Technical details**: See `CLAUDE.md`
- **General usage**: See `README.md`
- **Test setup**: Run `python test_setup.py`
