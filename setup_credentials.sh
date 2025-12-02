#!/bin/bash
#
# Secure credential setup for automated trading analysis
#

set -e

echo "=========================================="
echo "Secure Credential Setup"
echo "=========================================="
echo ""

# Get Gmail app password securely
echo "Gmail Configuration:"
echo "  Email: perjohandanders@gmail.com"
echo ""
echo -n "Enter Gmail App Password (16 characters, input hidden): "
read -s GMAIL_PASSWORD
echo ""

if [ -z "$GMAIL_PASSWORD" ]; then
    echo "Error: Gmail password cannot be empty"
    exit 1
fi

# Backup existing config if it exists
if [ -f config.json ]; then
    cp config.json config.json.backup
    echo "✓ Backed up existing config.json to config.json.backup"
fi

# Create new config.json
cat > config.json <<EOCONFIG
{
  "email": {
    "sender": "perjohandanders@gmail.com",
    "password": "$GMAIL_PASSWORD",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
  }
}
EOCONFIG

# Set secure permissions
chmod 600 config.json

echo ""
echo "✓ config.json created with secure permissions (600)"
echo ""
echo "Alert Recipients:"
echo "  - Per Edstrom: 737-400-1329, perjohandanders@gmail.com"
echo "  - Jenna Edstrom: 737-400-2720, jenna.edstrom@gmail.com"
echo ""
echo "Note: SMS alerts via Twilio are disabled (not configured)."
echo "      Only email alerts will be sent."
echo ""
echo "To add Twilio later:"
echo "  1. Sign up at https://www.twilio.com/try-twilio"
echo "  2. Add 'twilio' section to config.json with credentials"
echo ""
echo "Next step: Test the system"
echo "  python auto_daily_analysis.py"
echo ""

