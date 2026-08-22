<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Helper script to parse...

!/usr/bin/env python3
AI-hint: Helper script to parse mios.toml compliance options, dynamically construct an XCCDF tailoring file to skip specified rules, invoke oscap-im for scan/remediation, and execute mios-oscap-gate to enforce the build gate.
AI-related: /usr/share/mios/mios.toml, /usr/libexec/mios/mios-oscap-gate, Containerfile, oscap-im

<!-- mios-src:2ebb5b88c14a from usr/libexec/mios/oscap-scan.py:1-3 -->

