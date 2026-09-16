<!-- AI-hint: Handoff notes between MiOS working sessions, newest last. A fresh session reads the last entry, TASKS.md and git log -10 before doing anything. -->
<!-- AI-related: docs/DOD.md, TASKS.md, docs/design/operating-agreement.md -->
# MiOS ledger (handoff notes; newest last)

Each session appends one entry before it ends or compacts: status, done, next, blockers,
unverified. State lives on disk, not in a context window.

---

## 2026-09-16 · T-1018 stage conversions · status: partial

**Context that is not obvious from the tree.** Sixteen build stages dispatched to the Rust binary
with `command -v miosd`, a PATH lookup that cannot resolve at bake time — miosd installs to
`/usr/libexec/mios`, which nothing puts on PATH. So the Rust branch has never executed in a real
build and every bake silently used the bash fallback. Converting them one at a time, each proving
byte-parity before the fallback is deleted.

**Done:** 3 of 18 gates. `35-render-ports`, `42-chrony-render`, `43-nut-render`. Register
`[build.tool_dispatch].max_unreachable` 18 → 15.

**All three had real defects in the never-executed Rust path:**
- `render-ports` — a line scan, not a TOML parse, so comments containing `=` became environment
  variable names in `install.env`, one carrying a backtick pair that `bash source` reads as
  command substitution (Law 10).
- `render-chrony` — the same scan could not read a multi-line array, so `[network.ntp].servers`
  parsed empty and it SILENTLY substituted hardcoded `time.cloudflare.com` / `time.google.com`
  (Law 7), under a header claiming it was generated from SSOT.
- `render-nut` — byte-identical output, but `unwrap_or_default()` meant a nonexistent manifest
  rendered four default config files and exited 0.

**Next:** the conversion order is groups A–E (see the T-1018 body in `TASKS.md`). A background
audit of all fourteen remaining stages is running; its map supersedes the provisional order.

**Blockers:** none. The operator confirmed CI red is acceptable until all stages are done.

**Unverified:** no bake has been run. Every conversion is proved by offline output diffing, not by
a real build. The operator will run bakes and a CI bake job is planned (T-1028).

**Watch out for:** the `mios-resolver` binary must be built before a local gate run means anything
— `check_resolver_differential_parity` exits 0 when it is absent. That skip hid a real failure
this session until CI caught it.
