#!/bin/bash
set -e

# Pass environment variables to cron
env | grep -E '^(SLACK_|OREF_|ALERT_|NIGHT_|LOG_)' > /etc/environment

# Run initial collection on startup
echo "Running initial alert collection..."
python -m manager_alert collect

echo "Starting crond..."
exec crond -n
