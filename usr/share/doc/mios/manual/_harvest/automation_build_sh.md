<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: This script is the primary build runner...

!/bin/bash
AI-hint: This script is the primary build runner for MiOS, managing the build lifecycle by parsing `mios.toml` configurations, enforcing environment constraints, and rendering a TTY-safe ASCII progress UI for the build process.
AI-related: /etc/mios/mios.toml, /usr/share/mios/mios.toml, mios-bootstrap, mios-build, mios-step, packagekit.service
AI-functions: _pad, _hline, _row, _progress_bar, _step_header, _step_result, _section_header, _progress_frame, _fail_report, _warn_report, _final_summary

<!-- mios-src:3a7c439788e2 from automation/build.sh:1-4 -->

