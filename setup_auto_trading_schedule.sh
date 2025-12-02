#!/bin/bash
#
# Arch Linux Auto-Wake Setup for Daily Trading Analysis
# Sets up automatic system wake at 3:00 PM ET (1 hour before market close)
# Runs analysis, sends alerts, and shuts down
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
ANALYSIS_SCRIPT="$SCRIPT_DIR/auto_daily_analysis.py"
SERVICE_NAME="trading-analysis"

echo "=========================================="
echo "Auto-Trading Analysis Setup (Arch Linux)"
echo "=========================================="
echo ""

# Check if running as root for system setup
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo for system setup"
    echo "Usage: sudo ./setup_auto_trading_schedule.sh"
    exit 1
fi

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please create venv first: python -m venv venv"
    exit 1
fi

# Create systemd service for running analysis on boot
echo "Creating systemd service..."
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Daily Trading Analysis
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$(logname)
WorkingDirectory=$SCRIPT_DIR
ExecStart=$VENV_PATH/bin/python $ANALYSIS_SCRIPT
StandardOutput=journal
StandardError=journal

# Shutdown after completion
ExecStartPost=/usr/bin/systemctl poweroff

[Install]
WantedBy=multi-user.target
EOF

# Create systemd timer for weekdays at 3:00 PM ET
echo "Creating systemd timer for weekday execution..."
cat > /etc/systemd/system/${SERVICE_NAME}.timer <<EOF
[Unit]
Description=Daily Trading Analysis Timer (3 PM ET weekdays)

[Timer]
# Run at 3:00 PM ET (20:00 UTC / 8:00 PM UTC depending on DST)
# During EDT (Mar-Nov): 3 PM EDT = 7 PM UTC (19:00)
# During EST (Nov-Mar): 3 PM EST = 8 PM UTC (20:00)
OnCalendar=Mon,Tue,Wed,Thu,Fri 19:00:00
OnCalendar=Mon,Tue,Wed,Thu,Fri 20:00:00

Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start the timer
echo "Enabling systemd timer..."
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}.timer
systemctl start ${SERVICE_NAME}.timer

echo ""
echo "✓ Systemd service and timer created successfully!"
echo ""
echo "=========================================="
echo "RTC Wake Setup"
echo "=========================================="
echo ""
echo "For automatic wake from shutdown/suspend, you have two options:"
echo ""
echo "Option 1: Manual RTC wake (simpler, run before each shutdown)"
echo "  Run this command to set next wake time:"
echo "  sudo rtcwake -m off -l -t \$(date -d 'tomorrow 15:00' +%s)"
echo ""
echo "Option 2: Automatic RTC wake script (more complex, needs BIOS support)"
echo "  Create a shutdown hook that automatically sets next wake time"
echo ""
read -p "Do you want to set up automatic RTC wake? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating RTC wake script..."

    cat > /usr/local/bin/set-next-trading-wake <<'EOF'
#!/bin/bash
# Calculate next trading day at 3 PM ET

current_date=$(date +%Y-%m-%d)
current_hour=$(date +%H)

# If it's before 3 PM, wake today at 3 PM, otherwise tomorrow
if [ $current_hour -lt 15 ]; then
    wake_date="$current_date 15:00"
else
    wake_date=$(date -d "tomorrow" +%Y-%m-%d)" 15:00"
fi

# Convert to Unix timestamp
wake_timestamp=$(date -d "$wake_date" +%s)

# Set RTC wake alarm
rtcwake -m no -l -t $wake_timestamp

echo "RTC wake alarm set for: $wake_date"
logger "Trading analysis: RTC wake set for $wake_date"
EOF

    chmod +x /usr/local/bin/set-next-trading-wake

    # Create shutdown hook
    cat > /etc/systemd/system/rtc-wake-trading.service <<EOF
[Unit]
Description=Set RTC wake for next trading analysis
DefaultDependencies=no
Before=shutdown.target reboot.target halt.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/set-next-trading-wake

[Install]
WantedBy=halt.target poweroff.target
EOF

    systemctl daemon-reload
    systemctl enable rtc-wake-trading.service

    echo "✓ Automatic RTC wake configured!"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Analysis runs weekdays at 3:00 PM ET"
echo "  - Sends alerts to:"
echo "      Per: 737-400-1329, perjohandanders@gmail.com"
echo "      Jenna: 737-400-2720, jenna.edstrom@gmail.com"
echo "  - System shuts down automatically after analysis"
echo ""
echo "Commands:"
echo "  - Check timer status: systemctl status ${SERVICE_NAME}.timer"
echo "  - Check service logs: journalctl -u ${SERVICE_NAME}.service"
echo "  - List scheduled times: systemctl list-timers"
echo "  - Run analysis manually: sudo systemctl start ${SERVICE_NAME}.service"
echo "  - Disable auto-run: sudo systemctl disable ${SERVICE_NAME}.timer"
echo ""
echo "Next Steps:"
echo "  1. Ensure config.json has email/SMS credentials"
echo "  2. Test manually: sudo systemctl start ${SERVICE_NAME}.service"
echo "  3. Check logs: journalctl -u ${SERVICE_NAME}.service -f"
echo ""
echo "Power savings: System will only be on ~5 minutes/day = ~\$0.30/month"
echo ""
