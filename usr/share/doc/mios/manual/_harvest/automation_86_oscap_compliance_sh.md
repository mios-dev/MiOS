<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=bake-only AI-hint...

!/usr/bin/env bash
MIOS_APPLY_CLASS=bake-only
AI-hint: BOOT-02 OpenSCAP scan-only build gate. Reads [compliance] from mios.toml; when enabled=true it runs `oscap xccdf eval` against an SSG datastream (explicit [compliance].datastream, else ssg-<os-release ID>-ds.xml located from the installed scap-security-guide RPM) under the configured profile, bakes the ARF + HTML reports into [compliance].report_path (in /usr, not /var), then defers the pass/fail verdict to mios-oscap-gate (counts FAILED rules at/above [compliance].severity_gate). DEFAULT OFF + degrade-open: disabled => exits 0 (complete no-op). Scan-only -- openscap-scanner + scap-security-guide are already in [packages.security]; remediation (oscap-im) is intentionally NOT wired. Runs in build.sh numeric order, before the Containerfile's final `bootc container lint`.
AI-related: ../usr/libexec/mios/mios-oscap-gate, lib/packages.sh, lib/common.sh, ../usr/share/mios/mios.toml, build.sh, oscap

<!-- mios-src:bd0fff0b1115 from automation/86-oscap-compliance.sh:1-4 -->

