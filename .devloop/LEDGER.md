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

---

## 2026-09-16 (later) · dev-loop v5 adopted; T-1022 closed · status: partial

**Baseline moved.** The drift gate is now **19 violations from SIX checks**, not 20 from seven.
`check_secret_handling` is green. Any future session comparing against "20 from seven" is using a
stale number.

**Done:** dev-loop v5.0.0 adopted (docs/DOD.md, this ledger, explicit-path staging, pre-commit
secrets scan). T-1022 closed as a false positive -- the two flagged files hold PEM *templates*,
not keys, and the check was matching a keyword rather than the property. Research report filed at
`docs/design/agentic-dev-scaffolding.md`; T-1029 and T-1030 filed from it.

**Next:** T-1018 stages 4..18. A background workflow is auditing all fourteen remaining stages'
Rust renderers in parallel; its map supersedes the provisional group order in the T-1018 body.

**Unverified:** still no bake. Every T-1018 conversion is proved by offline output diffing only.

**Traps this session walked into, so the next one does not:**
- `exit=$?` after a PIPE reports the pipe's status, not the command's. A negative control reported
  "exit=0" that way looks like a pass. Capture the exit inside a function.
- A heredoc that builds a regex with backslashes doubles them. Write the literal with `chr(92)` or
  a real file write, then GREP THE RESULT before trusting it.
- The tooling-Python ratchet has zero slack by design: adding any Python line requires removing
  one. Put rationale in the commit message, not in an eleven-line comment.


---

## 2026-09-16 (later still) · T-1031 + T-1032 — the gate was not running the build's Python · status: partial

**The single most important line in this ledger.** Until commit `0b803b65`, `automation/98-drift-checks.sh`
ran every one of the 209 checks on a **cached copy of a different Python interpreter** than
`sync-generated.sh`, `just`, CI and anything you type by hand. The copy lived at
`${TEMP:-/tmp}/mios-py-bin/python3`, was created once and never invalidated. On this host it was
Python **3.13.12**, dated the previous day; the system interpreter was **3.11.15**. Fixed: the shim
is Windows-only now (it no-ops wherever a real `python3` resolves) and is never cached.

**Consequence for anyone reading older sessions:** a gate result recorded before `0b803b65` was
produced by an interpreter nobody chose and nothing logged. It agrees with the corrected one on
today's tree — 19 violations, six checks, measured both ways — but that is luck.

**Baseline unchanged:** **19 violations from six checks**. `check_doc_refs_resolve` 11,
`check_docs_ratchet` 3, `check_unit_dependency_closure` 2, `check_db_seed_coverage` 1,
`check_module_test_coverage` 1, `check_no_duplicate_value_key` 1.

**Done:** T-1022 (secret-handling false positive, predicate narrowed to header+body), T-1031
(`tools/render-globals.py` did not parse below py3.12, which broke `sync-generated.sh` at step 2/6
and took the four downstream projections with it), T-1032 (the interpreter shim).

**Next:** T-1018 stages 4..18, pending the renderer-audit workflow's map.

**Traps this session walked into, so the next one does not:**
- **Reproducing a check's command in your shell is not reproducing the check.** A file that exits 1
  under `python3` gave rc=0 through the gate, and a commit message went out asserting the opposite
  before that was caught. Run it *through the harness*, or you are measuring a different subject.
- A pre-commit secrets scan that matches a bare `-----BEGIN ... KEY-----` flags **the source line of
  the regex that looks for keys**. Require the base64 body. The scanner used here lives in the
  session scratchpad and is validated against six controls; the durable version is
  `drift-checks.py secret-handling`, which now has the same predicate.
- `git add` of a derived file before `sync-generated.sh` completes stages a half-regenerated tree.
  Run the spine to exit 0 first, then stage explicit paths.
- Shrink-only ratchets with slack are not neutral: `shell_lines=38431/39903`, `ps_lines=22607/22618`,
  `tracked_files=3288/3344` all sit BELOW their ceilings. A ceiling above its measurement is
  accepted debt nobody is paying down — fold into T-1013/T-1021.

**Unverified:** still no bake. Every T-1018 conversion is proved by offline output diffing only.

---

## 2026-09-16 (evening) · the renderer audit landed; five live defects fixed · status: partial

**Baseline unchanged all session: 19 violations from six checks.** `check_doc_refs_resolve` 11,
`check_docs_ratchet` 3, `check_unit_dependency_closure` 2, `check_db_seed_coverage` 1,
`check_module_test_coverage` 1, `check_no_duplicate_value_key` 1. Every commit below held it
count-for-count.

**The 29-agent renderer audit returned** and is committed at
`docs/design/miosd-renderer-parity-audit.md`. Read its **coverage gaps** before building any
conversion gate from it: no auditor ran a real `podman build`, no SELinux-enforcing host existed,
and several stages were replayed through harnesses. Its **refuted claims** section is the most
useful part — every refutation was a harness artifact, never a fabricated observation.

**The sequencing rule is now evidence-backed.** `ENV PATH=/usr/libexec/mios:$PATH` would arm the
latent Rust defects in stages 75, 33, 34, 40, 51, 49, 88, 01 and 05 **in one bake**. Do not do it.
Convert per stage. Revised order: `build.sh` driver → 75 (done) → 76 → 33 → 34 → 01 → 85 → 49 →
88 → 44 → 40+51 as one commit → 05 → the hollow-check gate.

**Done since the last entry:** T-1022, T-1031, T-1032, T-1033, T-1018 stage 4 (75-kargs),
the audit filing (T-1034..T-1041), T-1034 (partial), T-1039, T-1038 (partial).

**What the conversions keep finding.** Four stages converted, four real defects, every one
invisible for as long as the dispatch has been dead:
- `35-render-ports` — TOML comments became env var names, one carrying a backtick pair (Law 10).
- `42-chrony-render` — a multi-line array unreadable by line scan, silently substituting
  hardcoded `time.cloudflare.com` / `time.google.com` (Law 7).
- `43-nut-render` — byte-identical, but rendered four default files from a nonexistent manifest.
- `75-kargs-render` — **deleted `rd.driver.pre=vfio-pci` and `kvm-intel.nested=1` from the kernel
  command line**, exit 0, under a header claiming SSOT provenance.

**Traps this session walked into, so the next one does not:**
- **`$?` after a pipe reports the pipe's status.** Written down in this ledger this morning, walked
  into again this evening (I read `bake-budget` as exit 0 when it correctly returns 1). Capture the
  status in a variable on the same line, or inside a function.
- **Sourcing a shell library inside a pipeline puts it in a SUBSHELL** and every variable it sets is
  lost. This is how "2641 of 2655 `MIOS_*` are never exported" became a finding in the audit, and
  how I reproduced it a second time. `source X | head` measures nothing.
- **Reproducing a check's command in your shell is not reproducing the check.** The drift gate runs
  its own interpreter and its own environment; run it through the harness.
- **Touching `automation/build.sh` promotes it to lint-shell's warning tier**, which surfaces nine
  pre-existing shellcheck findings. Budget for them or do not touch the file.
- **Ceilings above their measurement are findings.** Both new gates treat slack as a violation.

**Unverified, still:** no bake has been run, by anyone, at any point. Every conversion is proved by
offline output diffing and negative controls only.

---

## 2026-09-16 (late) · the bake's own gate was reporting 55 passes it never computed · status: partial

**Read this before trusting any `miosd drift-check` output from before `5d66f508`.** 54 of 77
`Check::run` impls took `_ctx`, never read the tree, and returned a constant `Verdict::Pass` with
a message claiming verification. Pointed at a directory that does not exist the suite reported
**"55 passed"**. `Containerfile:103` runs it at every bake. They now say
`Verdict::Skip("NOT IMPLEMENTED: ...")` and are registered shrink-only at `[drift.unimplemented]`,
gated by `mios-gate drift-stubs`.

**What the native suite actually verifies: 18 things, not 73.** Real tree now reads
`18 passed, 1 failed, 55 skipped`.

**That one failure is real and was invisible** — `check_backfill_coverage: Table 'system_logs' has
'emb vector' but is not in PK_MAP or _BACKFILL_EXEMPT`, failing at every bake under fifty-five
claims that could not fail. Filed T-1042. And exactly one check still passes against a
nonexistent root (`check_pipeline_numbering` calls an empty set dense) — filed T-1043 as the
template for auditing the other 20 ctx-reading checks.

**CI gave its first clean verdict of the session** on `f4424e50`: 9 of 10 steps green, only the
drift-gate tier failing, with **7 negative-test failures, down from the baseline 8**. Every one is
`check_X failed on the unmutated tree` for the six standing-red checks. Nothing new is ours.

**Gate baseline: still 19 violations from six checks**, count-for-count, across all 14 commits.

**Three shrink-only registers now exist and all three treat a ceiling above its measurement as a
violation:** `[build.tool_dispatch]` (14), `[build.phases].unregistered` (1),
`[drift.unimplemented]` (54), plus `[security.credential_literals]` which now pins VALUES not keys.

**Four decisions are with the operator** and are blocking, not optional: registering
`55-native-build.sh` (or dropping its `/usr/bin` symlink); stage 34's acceptance test inverting
because the Rust path is the correct one; the 44-port three-spelling collapse that
`naming-unification.md` already decided and nobody executed; and which of the two shipping
bake-plan implementations owns stage 85.

**Trap added:** `$?` after a pipe reports the pipe's status — walked into for the THIRD time today,
on `mios-gate` output. It is in this ledger twice now. Capture the status without a pipe.

---

## 2026-09-17 · the AI plane had no local test coverage all session · status: partial

**Do this first, before any AI-plane change.** CI does not invoke suites directly — it calls
`tests/run-suites.sh`. So should you. Running `tests/test-*.py` by hand gives 42 spurious
failures from PYTHONPATH alone.

```bash
python3 -m pip install --ignore-installed PyJWT -r usr/lib/mios/agent-pipe/requirements.txt pyflakes
apt-get install -y bubblewrap
bash tests/run-suites.sh lint   # 6 passed, 0 failed
bash tests/run-suites.sh unit   # 574 passed, 0 failed   <-- matches CI exactly
```

**Why it matters, concretely.** Without those dependencies 50 of the 184 agent-pipe suites fail on
`ModuleNotFoundError`. Earlier today I read that correctly as an environment gap and moved past it
— and then shipped `KeyError: 'system_logs'` in `embed_backfill.py`, which CI caught. Diagnosing a
gap honestly is not the same as closing it. It is closed now; the whole unit tier runs here.

**Baselines, all re-measured today:**
- drift gate: **19 violations from six checks** (was 20 from seven)
- negative suite: **7 failures**, each a consequence of a standing-red check
- `miosd drift-check --root .`: **20 passed, 0 failed, 54 skipped** — and **0 passed** against both
  a nonexistent root and a present-but-empty one
- `tests/run-suites.sh unit`: **574 passed, 0 failed**

**Four shrink-only registers now exist, and every one treats a ceiling above its measurement as a
violation:** `[build.tool_dispatch]` 14, `[build.phases].unregistered` 1, `[drift.unimplemented]`
54, and `[security.credential_literals]` which pins VALUES not keys.

**Traps, cumulative — the first two bit more than once each:**
- `$?` after a pipe reports the pipe's status. Three times today.
- Sourcing a shell library inside a pipeline puts it in a SUBSHELL; every variable it sets is lost.
- **Reproducing a command in your shell is not reproducing the check.** The gate runs its own
  interpreter and environment.
- **A predicate that tests the wrong property passes its own tests.** The stub detector went
  through three versions — parameter name, then `ctx.root` mentioned, then an actual read — and
  each earlier one was green on its own suite. Test the checker, not just with it.
- A helper named `regen_and_diff` did not diff. Read a helper before reusing it.
- Touching `automation/build.sh` promotes it to lint-shell's warning tier and surfaces nine
  pre-existing findings. Budget for them or leave the file alone.

---

## T-1018 stages 5-8 · status: partial

**Done since the last entry.** The negative suite's own vacuous test, then four stage conversions.

- `tests/drift-gate-negatives.sh::test_resolver_differential_parity` hid the FIRST of four
  resolver binaries and `break`ed, while the check it tests walks all four. On a tree with both a
  release and a debug build the check found the debug one, so the "no binary under
  REQUIRE_TOOLS=1" refusal had never executed. Unanchored allowlist, inside the suite that exists
  to catch unanchored allowlists. It also now declines to claim a proof when
  `/usr/libexec/mios/mios-resolver` or `/usr/bin/mios-resolver` exists, since those are outside the
  tree and not the test's to move.
- **Stage 5, `automation/build.sh`** — the orchestrator. Three defects, compounding: the dispatch
  never resolved; `MIOS_ROOT` defaulted to `"."` so miosd read the registry against the caller's
  cwd; and `PhaseRegistry::load_from_toml` swallowed every failure and returned a hardcoded
  SIX-phase default at exit 0. Together those would have produced a six-of-seventy-one-phase image
  reporting BUILD COMPLETE. The registry now returns `Result` with a variant per failure.
- **Stage 6, `76-uki-render`** — and the four subcommands behind it. `render-uki-cmdline`,
  `generate-quadlets`, `cosign-policy` and `bake-plan` each carried the same five lines: a
  cwd-relative script path, and an else-branch printing "... up to date." and returning Ok without
  opening the artefact. Collapsed into one `run_repo_generator` that resolves against MIOS_ROOT and
  errors when the generator is absent.
- **Stage 7, `33-generate-quadlets`** — dispatch only; both legs exec the same generator.
- **Stage 8, `01-system-files-overlay`** — Law 3. The Rust `overlay-bind-images` used `read_dir` at
  depth 1 where the bash globs `*/` too, so `users/mios-coderun-sandbox@.container` was never
  bound: an image that would not have shipped with the host. Its `firstboot_tokens` read was also a
  line scan that would have yielded an EMPTY token set on a reflowed array, and an empty set binds
  everything including the two heavy GPU lanes the register exists to keep out. Both fixed;
  symlink failures no longer swallowed. A `--qdir` override was added because with the paths
  hardcoded there was no way to test the bind without writing to `/usr/share` on the test host.

`[build.tool_dispatch].max_unreachable` **14 → 10**, one per conversion, each refused by the gate
before I lowered it. `[build.phases].unregistered` is now **empty** (ceiling 0).

**55-native-build.sh was registered, and the register's premise was wrong.** It was held off
`[build.phases].list` because registering it would create `/usr/bin/miosd` and arm every gate above
ordinal 55. But the stage guards its whole body on `command -v cargo`, no `[packages]` section
installs a Rust toolchain, and no phase installs one — so in a bake it warns and does nothing. The
image's binaries come from the Containerfile's `rust-builder` stage. The symlink has never been
created. Registering it arms nothing, and since selection went through the glob (which already
included 55) it changes no phase count: the converted driver selects the same 68 scripts in the
same order.

**Next: stage 34 is a genuine fork — do not flip its dispatch.** The audit's note that "the Rust
path is correct and byte-parity would ship a broken image" does not survive measurement:

- 24 of the 48 distinct `${MIOS_*}` placeholders in the shipped corpus are NOT on 34's allowlist.
- That allowlist is the build-time/runtime boundary, not an oversight.
  `usr/lib/systemd/system/mios-agents.service` carries its own comment saying its ExecStart uses
  plain `${VAR}` so **systemd** expands it at runtime from `Environment=` plus
  `EnvironmentFile=-/etc/mios/install.env` — the mios.toml→env SSOT bridge.
- `miosd render-quadlets` has no allowlist. Containerfile line 99 exports `MIOS_AI_MODEL` and
  `MIOS_AI_EMBED_MODEL` for the bake; both appear as `${MIOS_AI_MODEL:-...}` in
  `etc/mios/kb.conf.toml` and `usr/share/mios/kb/manifest.json`, both inside 34's walk. The Rust
  path would freeze them at bake and sever the override.
- It also differs in ways unrelated to the allowlist: `read_dir` depth 1 vs `find -maxdepth 2`, no
  extension filter, no `mios-llm-heavy` multi-LoRA case, `let _ = fs::write` swallowing failures,
  no `chmod 0644`.

**Remaining order:** 85 (also forked — two shipping bake-plan implementations, `run_bake_plan`
shelling out to Python beside a native `src/mios-rs/miosd/src/bake_plan.rs`), 49, 88, 44 (blocked
on T-1040), 40+51 as one commit, 05, then the hollow-check gate. 49, 88, 40, 51 and 05 are not
forked.

**Baselines, unchanged across all four conversions:** drift gate **19 violations from six checks**,
count-for-count; `tests/run-suites.sh unit` **574 passed, 0 failed**; mios-gate four green; cargo
clippy `--all-targets` and `cargo fmt` clean.

**Unverified:** still no bake. Every conversion is proved by offline diffing and by two-sided
controls, not by a real build.

**Traps added today:**
- The corpus ledger goes stale the moment you edit a commented file, and `cargo fmt` counts —
  re-run `tools/sync-generated.sh` AFTER the last edit or `check_manual_ledger` fails and the
  baseline reads 20 instead of 19. Cost three gate runs.
- A comment of 60+ words is classified MIGRATE by the corpus lexer, and
  `[docs].max_unmigrated_narrative` is 0. Say it in fewer words rather than harvesting a
  test-local note into the manual.
- Absolute paths hardcoded inside a checker mean the checker cannot be tested without mutating the
  host. Give it an override and the two-sided control becomes possible.

---

## T-1018 stages 9-14 · status: the unforked conversions are done

**Register: `[build.tool_dispatch].max_unreachable` 14 → 3 this session.** Every conversion
lowered it by its own count, and every one of those lowerings was refused by the gate before I
made it — the ceiling-above-measurement rule works.

**Converted:** `automation/build.sh` (5), `76-uki-render` (6), `33-generate-quadlets` (7),
`01-system-files-overlay` (8), `49-cosign-policy` (9), `88-finalize` (10), `40-fapolicyd-trust` +
`51-hardening` (11-12), `05-repos` (13), and `98-drift-checks`'s `mios-aiplane-lint` gate (14).

**The pattern that held across all of them.** Every dead Rust branch had a second defect behind the
dead gate, and in most cases the second defect was worse than the gate:

- `build.sh` — a hardcoded SIX-phase registry returned at exit 0 on any failure to read SSOT.
- `76`, `33`, `49`, `85` — four copies of an else-branch printing "... up to date." for an artefact
  it had never opened, from a cwd-relative script path.
- `01` — `read_dir` at depth 1 where the bash globs `*/` too, so one shipping Quadlet would never
  have been bound (Law 3); plus a `firstboot_tokens` line scan that yields an empty set on a
  reflowed array, and an empty set binds the two ~47GB GPU lanes the register exists to exclude.
- `49`'s generator — `except Exception: pass` around the SSOT read, defaulting to
  `insecureAcceptEverything`; and a `--check` comparing parsed JSON, which is exactly blind to the
  compact-vs-indented drift that was actually there.
- `88` — `if !p.exists() || ver == "unknown" { return Ok(()) }` under a stage that logged a
  successful projection on the strength of the exit code.
- `40`/`51` — every write `let _ = ...` followed by an unconditional "enabled <unit>".
- `05` — `if fedora_version.is_empty() { "44" }`, a release number beside
  `[versions].fedora = 44`, free to drift.

**Testability was the recurring blocker, three times.** `overlay-bind-images`, `harden` and
`render-repos` each hardcoded absolute system paths, so exercising them meant writing to
`/usr/share`, `/usr/lib/fapolicyd` or `/etc/yum.repos.d` on the machine running the test. Each got
one optional argument (`--qdir`, `--root`, `--vendored-dir`) defaulting to the system path — no
bake behaviour change, and the two-sided control becomes possible. **If a checker cannot be
checked, that is the first thing to fix.**

**Three files remain on the register and none is a plain conversion:**

1. **34-render-quadlets** — the bash allowlist IS the build-time/runtime boundary (measurements in
   the stage-7 commit). Operator decision.
2. **44-firewall-ports** — blocked on T-1040.
3. **85-bake-plan** — two shipping implementations: `src/mios-rs/miosd/src/bake_plan.rs` (native)
   beside `run_bake_plan` (shells out to `tools/generate-bake-plan.py`). Which owns the stage is
   the operator's call.

**Two new findings, filed not fixed** (each would move the gate baseline, so each needs its own
commit and gate run):

- **`check_agent_pipe_budgets` is vacuous in the direction it announces.** `BUDGET_KEYS` in
  `tools/native/mios-aiplane-lint` is a hardcoded list of nine names; the lint walks that list,
  never the `[agent_pipe]` table. A planted unconsumed key passes both the Rust and the Python leg
  at rc=0. Also a registry of operator-tunable names in Rust source rather than SSOT (Law 7).
- **`check_var_closure` is an empty-set pass on Law 9.** It reports
  `emitted=2874 referenced=0 missing=0` under the same `MIOS_ROOT` the gate passes it — the
  referenced set is empty, so "referenced ⊆ emitted" holds trivially, while
  `usr/share/mios/referenced_names.txt` sits in the tree with thousands of entries something else
  produces.

**Also fixed:** `usr/lib/containers/policy.json` is now regenerated by `tools/sync-generated.sh`
(step 4e). It is a Law 8 surface that had neither half of the law — no regenerate step and no drift
check. The missing check belongs in `mios-gate` (Rust, and the Python ratchet has no room).

**Baselines, unchanged across all nine commits:** drift gate **19 violations from six checks**,
count-for-count; mios-gate four green; `cargo clippy --all-targets` and `cargo fmt` clean.

**Unverified:** still no bake. Every conversion is proved by offline diffing and two-sided
controls.

**Traps added:**
- `$?` after a pipe reports the pipe's status. Hit again this session, in a `--check` probe.
- `cargo fmt` rewrites source and therefore stales the corpus ledger — run `sync-generated.sh`
  after it, not before.
- `git diff` on `automation/manifest.json` or `tools/manifest.json` dumps megabytes: they embed
  full file contents. Diff `--stat` only.
- A generator's writer and its `--check` can disagree. Compare bytes, or the check is blind to
  exactly the drift it is there to find.
