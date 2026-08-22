<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures fontconfig by symlinking the Geist font configuration from the available directory to the active directory to ensure persistent font styling across bootc redeployments.
AI-related: mios-fontconfig, mios-geist
/usr/lib/tmpfiles.d/mios-fontconfig.conf
Make the MiOS fontconfig overrides active by symlinking from
/etc/fonts/conf.d/ -> /usr/share/fontconfig/conf.avail/30-mios-geist.conf.
fontconfig only scans /etc/fonts/conf.d/ for active drop-ins; the
/usr/share/.../conf.avail/ location is "available but not enabled"
unless symlinked. L+ recreates the symlink on every boot so manual
/etc edits don't persist past a bootc redeploy.

<!-- mios-src:f82f97c499b0 from usr/lib/tmpfiles.d/mios-fontconfig.conf:1-9 -->

