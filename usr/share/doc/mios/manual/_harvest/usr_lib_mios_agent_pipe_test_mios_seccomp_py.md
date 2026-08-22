<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_pipe.access.seccomp (T-230). The load-bearing case is the ABI cross-check: the committed x86_64 syscall-number table is re-derived from the host's own asm/unistd_64.h whenever those headers exist, so a transcription error -- which would silently deny the WRONG syscall -- cannot ship. Also pins the shape of the emitted classic-BPF program (arch check first, and an arch MISMATCH must fall through to DENY rather than ALLOW, the classic 32-on-64 bypass), the refusals that keep a useless filter from looking like protection (unknown architecture, empty denylist, a chain longer than the uint8 jump range), and that an operator's SSOT list can only EXTEND the baseline floor, never shrink it.
AI-related: ./mios_pipe/access/seccomp.py, /usr/libexec/mios/mios-seccomp-filter, /usr/libexec/mios/mios-sandbox-exec, /usr/share/mios/mios.toml
AI-functions: check, t_table_matches_kernel_abi, t_denylist, t_program_shape, t_refusals, main

<!-- mios-src:edb69ea59a02 from usr/lib/mios/agent-pipe/test_mios_seccomp.py:1-4 -->

