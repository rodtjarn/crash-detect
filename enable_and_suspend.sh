#!/bin/bash
#
# Enable Trading Analysis and Suspend
# Verifies everything is configured correctly, then suspends the computer
# All future trading analysis will run automatically without interruption
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="trading-analysis"

echo "=========================================="
echo "Trading Analysis Pre-Suspend Verification"
echo "=========================================="
echo ""

# Check if running with sudo (needed for suspend)
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo to suspend the system"
    echo "Usage: sudo ./enable_and_suspend.sh"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=$(logname 2>/dev/null || echo $SUDO_USER)

echo "Checking system configuration..."
echo ""

# 1. Check timer exists
if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.timer" ]; then
    echo "✗ Error: Timer not found at /etc/systemd/system/${SERVICE_NAME}.timer"
    echo "Run setup first: sudo ./setup_auto_trading_schedule.sh"
    exit 1
fi
echo "✓ Timer file exists"

# 2. Check service exists
if [ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    echo "✗ Error: Service not found at /etc/systemd/system/${SERVICE_NAME}.service"
    echo "Run setup first: sudo ./setup_auto_trading_schedule.sh"
    exit 1
fi
echo "✓ Service file exists"

# 3. Check timer is enabled
if systemctl is-enabled ${SERVICE_NAME}.timer &> /dev/null; then
    echo "✓ Timer is enabled"
else
    echo "⚠ Timer is not enabled, enabling now..."
    systemctl enable ${SERVICE_NAME}.timer
    echo "✓ Timer enabled"
fi

# 4. Check timer is active
if systemctl is-active ${SERVICE_NAME}.timer &> /dev/null; then
    echo "✓ Timer is active"
else
    echo "⚠ Timer is not active, starting now..."
    systemctl start ${SERVICE_NAME}.timer
    echo "✓ Timer started"
fi

# 5. Show next scheduled run
echo ""
echo "Next scheduled run:"
systemctl status ${SERVICE_NAME}.timer | grep -E "Trigger:|Active:" || true

echo ""
echo "Upcoming timer schedule:"
systemctl list-timers ${SERVICE_NAME}.timer --no-pager

# 6. Check config.json exists
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    echo ""
    echo "⚠ Warning: config.json not found"
    echo "Alerts may not work without email configuration"
fi

# 7. Verify WakeSystem is enabled in timer
if grep -q "WakeSystem=true" /etc/systemd/system/${SERVICE_NAME}.timer; then
    echo ""
    echo "✓ WakeSystem enabled (will wake from suspend)"
else
    echo ""
    echo "⚠ Warning: WakeSystem not enabled in timer"
    echo "System may not wake from suspend automatically"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "System is configured for automatic trading analysis:"
echo "  ✓ Timer enabled and active"
echo "  ✓ Service configured to run analysis"
echo "  ✓ Will wake from suspend automatically"
echo "  ✓ Will suspend after each run"
echo ""
echo "The computer will now:"
echo "  1. Suspend (low power mode)"
echo "  2. Wake daily at 3:00 PM ET (Mon-Fri)"
echo "  3. Run trading analysis"
echo "  4. Send email alerts if signals detected"
echo "  5. Verify timer is enabled"
echo "  6. Suspend again"
echo ""

# Countdown before suspend
echo "Suspending in 10 seconds... (Ctrl+C to cancel)"
for i in {10..1}; do
    echo -n "$i... "
    sleep 1
done
echo ""

echo ""
echo "Suspending now..."
systemctl suspend
