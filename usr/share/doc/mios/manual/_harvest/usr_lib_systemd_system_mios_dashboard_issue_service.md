<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit that executes mios-dashboard-render_issue.sh to populate /etc/issue.d/30-mios.issue, ensuring the MiOS system status is rendered on all getty login prompts.
AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, mios-dashboard-render_issue, mios-dashboard-render-issue, mios-dashboard-issue, mios-dashboard-issue.timer, console-login-helper-messages.service, multi-user.target, getty.target, local-fs.target
/usr/lib/systemd/system/mios-dashboard-issue.service
Render the MiOS dashboard into /etc/issue.d/30-mios.issue so the
system state is shown on every getty BEFORE the login prompt.

Runs once at boot (after multi-user.target so all Quadlets have
attempted to start) and is also pulled by mios-dashboard-issue.timer
every 5 minutes for state freshness.

Ordered Before= the getty units so the very first console that
opens already has the rendered snippet visible.

<!-- mios-src:9a8e921263ad from usr/lib/systemd/system/mios-dashboard-issue.service:1-12 -->

