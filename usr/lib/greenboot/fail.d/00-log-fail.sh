#!/usr/bin/bash
# Greenboot failure logging script
# Capture and log failure reason before rollback

LOG_FILE="/var/log/greenboot.fail"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

echo "--- Greenboot Failure Detected at $TIMESTAMP ---" >> "$LOG_FILE"
echo "Active Health Check Failures:" >> "$LOG_FILE"

# List failing services or health checks if possible
systemctl --failed >> "$LOG_FILE"

echo "Triggering rollback reboot..." >> "$LOG_FILE"
echo "-----------------------------------------------" >> "$LOG_FILE"

# Ensure log is written to disk
sync
