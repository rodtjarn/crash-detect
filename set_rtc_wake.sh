#!/bin/bash
# Set RTC wake timer for next trading day at 2:00 PM CST / 3:00 PM ET (1 hour before market close)

# 2:00 PM CST = 3:00 PM ET = 20:00 UTC (winter) or 19:00 UTC (summer with DST)
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
echo "✓ RTC wake alarm set for: $WAKE_DATE (2:00 PM CST / 3:00 PM ET - 1hr before market close)"
