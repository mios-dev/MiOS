<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Portable drive LUKS2 FIDO2 /...

!/usr/bin/env python3
AI-hint: Portable drive LUKS2 FIDO2 / CTAP2 token enrollment helper using systemd-cryptenroll.
AI-related: tests/test-sec.py, usr/libexec/mios/mios-luks-enroll, usr/share/mios/mios.toml
AI-functions: Fido2EnrollEngine, Fido2Token, LuksKeyslot, EnrollmentResult, StatusResult, main

<!-- mios-src:8bb1c95f475e from usr/libexec/mios/sec/fido2_enroll.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Greenboot post-bake health...

!/usr/bin/env python3
AI-hint: Greenboot post-bake health gate validating service initialization with automated rollback and diff quarantine on regressions.
AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md, tests/test-sec.py
AI-functions: GreenbootGateEngine, atomic_write_json, main

<!-- mios-src:2aa29acce323 from usr/libexec/mios/sec/greenboot_gate.py:1-4 -->

### !/usr/bin/env python3 AI-hint: Automated zero-downtime...

!/usr/bin/env python3
AI-hint: Automated zero-downtime LUKS2 and dm-crypt encryption key rotation for Ceph OSDs and secure partitions.
AI-related: usr/lib/systemd/system/mios-luks-rotate.service, usr/lib/systemd/system/mios-luks-rotate.timer, tests/test-sec.py, usr/share/mios/mios.toml
AI-functions: LUKSDevice, LUKSRotationEngine, main

<!-- mios-src:c6b986f6f9a2 from usr/libexec/mios/sec/mios-luks-rotate:1-4 -->
