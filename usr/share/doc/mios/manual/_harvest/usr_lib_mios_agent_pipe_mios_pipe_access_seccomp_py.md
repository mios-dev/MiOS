<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: T-230 seccomp filter builder for the risk-tier dispatch sandbox. bwrap was already exec'd for opted-in verbs and really did confine the filesystem and the network -- `Seccomp: 0` in the confined process was the half that was missing, so a verb could still call mount, ptrace, keyctl or bpf inside its jail. Assembles a classic-BPF seccomp program in pure stdlib (no libseccomp): validate the audit arch, then compare the syscall number against the SSOT denylist and return EPERM (or kill) on a hit, ALLOW otherwise. The syscall NUMBER table is kernel ABI, not policy -- the sibling test re-derives it from the host's own asm/unistd headers so a transcription error cannot ship. An architecture with no verified table refuses to build a filter rather than returning an empty one: a filter that denies nothing is worse than no filter, because it reads as protection.
AI-related: ./sandbox.py, /usr/libexec/mios/mios-seccomp-filter, /usr/libexec/mios/mios-sandbox-exec, /usr/share/mios/mios.toml, ./test_mios_seccomp.py, usr/share/doc/mios/manual/ch62-sandbox-seccomp.md
AI-functions: audit_arch, syscall_numbers, resolve_denylist, build_filter, class SeccompUnsupported

<!-- mios-src:b5e57a5cc511 from usr/lib/mios/agent-pipe/mios_pipe/access/seccomp.py:1-3 -->

