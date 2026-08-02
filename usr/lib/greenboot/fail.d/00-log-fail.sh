#!/usr/bin/bash
# AI-hint: Logs specific systemctl failures and timestamps to /var/log/greenboot.fail during a greenboot failure event to provide diagnostic data before the automated rollback reboot occurs.

LOG_FILE="/var/log/greenboot.fail"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "" >> "$LOG_FILE"
echo "Active Health Check Failures:" >> "$LOG_FILE"

systemctl --failed >> "$LOG_FILE"

echo "Triggering rollback reboot" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

sync
