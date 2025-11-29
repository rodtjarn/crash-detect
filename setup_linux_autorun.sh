#!/bin/bash
# Linux Auto-Boot Trading Alert Setup
# This configures the system to boot, run trading alerts, then shutdown

echo "=================================="
echo "Linux Trading Alert Auto-Boot Setup"
echo "=================================="
echo ""

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Creating systemd service..."

# Create the systemd service file
sudo tee /etc/systemd/system/trading-alert.service > /dev/null <<EOF
[Unit]
Description=Trading Alert System - Run and Shutdown
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/trading_alert_system.py
ExecStartPost=/bin/sleep 30
ExecStartPost=/sbin/shutdown -h now
StandardOutput=append:$SCRIPT_DIR/trading_alert.log
StandardError=append:$SCRIPT_DIR/trading_alert.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file created"

# Enable the service
sudo systemctl enable trading-alert.service
echo "✓ Service enabled (will run on every boot)"

# Create the wake scheduler script
cat > $SCRIPT_DIR/set_rtc_wake.sh <<'WAKESCRIPT'
#!/bin/bash
# Set RTC wake timer for next trading day at 3:00 PM ET (1 hour before market close)

# 3:00 PM ET = 20:00 UTC (winter) or 19:00 UTC (summer with DST)
# Using 20:00 UTC as base time

# Get current date/time
NOW=$(date +%s)

# Calculate next weekday 3:00 PM ET (20:00 UTC)
TOMORROW=$(date -d "tomorrow 20:00" +%s)
DAY_OF_WEEK=$(date -d "@$TOMORROW" +%u)

# If tomorrow is Saturday (6) or Sunday (7), find next Monday
if [ $DAY_OF_WEEK -eq 6 ]; then
    # Saturday, wake on Monday
    WAKE_TIME=$(date -d "next Monday 20:00" +%s)
elif [ $DAY_OF_WEEK -eq 7 ]; then
    # Sunday, wake on Monday
    WAKE_TIME=$(date -d "next Monday 20:00" +%s)
else
    # Weekday, wake tomorrow
    WAKE_TIME=$TOMORROW
fi

# Clear existing RTC wake alarm
echo 0 | sudo tee /sys/class/rtc/rtc0/wakealarm > /dev/null

# Set new wake time
echo $WAKE_TIME | sudo tee /sys/class/rtc/rtc0/wakealarm > /dev/null

WAKE_DATE=$(date -d "@$WAKE_TIME" '+%Y-%m-%d %H:%M:%S')
echo "✓ RTC wake alarm set for: $WAKE_DATE (3:00 PM ET - 1hr before market close)"
WAKESCRIPT

chmod +x $SCRIPT_DIR/set_rtc_wake.sh

echo "✓ Wake scheduler created"

# Create a shutdown hook to set next wake time
sudo tee /etc/systemd/system/set-next-wake.service > /dev/null <<EOF
[Unit]
Description=Set RTC Wake Timer Before Shutdown
DefaultDependencies=no
Before=shutdown.target reboot.target halt.target

[Service]
Type=oneshot
ExecStart=$SCRIPT_DIR/set_rtc_wake.sh
StandardOutput=append:$SCRIPT_DIR/wake_schedule.log

[Install]
WantedBy=shutdown.target
EOF

sudo systemctl enable set-next-wake.service
echo "✓ Wake scheduler enabled (sets alarm before shutdown)"

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "How it works:"
echo "  1. Computer wakes at 3:00 PM ET on weekdays (1hr before market close)"
echo "  2. Trading alert script runs automatically"
echo "  3. Computer shuts down after completion"
echo "  4. Next wake time is set before shutdown"
echo ""
echo "To test manually:"
echo "  sudo systemctl start trading-alert.service"
echo ""
echo "To check logs:"
echo "  tail -f $SCRIPT_DIR/trading_alert.log"
echo ""
echo "To set wake time manually:"
echo "  $SCRIPT_DIR/set_rtc_wake.sh"
echo ""
echo "IMPORTANT: Make sure RTC Wake is enabled in BIOS!"
echo ""
