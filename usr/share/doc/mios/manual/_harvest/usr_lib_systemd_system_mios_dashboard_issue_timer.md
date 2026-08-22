<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd timer that triggers mios-dashboard-issue.service every 5 minutes to refresh the /etc/issue.d/ banner with real-time Quadlet status updates like service flapping and endpoint reachability.
AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, mios-dashboard-issue, mios-dashboard-render-issue, mios-dashboard-issue.service, timers.target
/usr/lib/systemd/system/mios-dashboard-issue.timer
Refresh the /etc/issue.d/ dashboard snippet every 5 minutes so
Quadlet state changes (services flapping, endpoint reachability
coming and going) reach the pre-login banner without operator
intervention.

<!-- mios-src:67aa7401acb1 from usr/lib/systemd/system/mios-dashboard-issue.timer:1-7 -->

