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

---

## T-1047, the signature-policy gate, T-1046/T-1048 filed · status: partial

**Done since the last entry.** Two gates that did not check what they announced, plus the merge of
`origin/main` that moved under the branch mid-session.

- **T-1047 — the budget gate checked 9 of 128 keys and said "all".** `BUDGET_KEYS` in
  `tools/native/mios-aiplane-lint` was a hardcoded nine names; `[agent_pipe]` + `[dispatch]` hold
  **128** scalar leaves. Now enumerated from SSOT. Residue measured, not assumed: **119 of 128
  consumed, 9 dead**, itemised in `[drift.budget_keys].unconsumed` (shrink-only, ceiling 9).
  The search surface was also too narrow — it read `usr/lib/mios/agent-pipe` alone, and
  `[dispatch].gpu_profile` is read by `usr/libexec/mios/mios-swarm-pack-firstboot`. Widening the
  keys WITHOUT widening the search would have reported a load-bearing key dead. That correction is
  exactly what takes the residue from 10 to 9.
- **The container signature policy got the Law 8 half it never had.** `mios-gate signature-policy`
  (fifth check) regenerates `usr/lib/containers/policy.json` from `[security.sigstore]` and
  byte-diffs it. Wiring it in tripped `check_negatives_registered` (48 → 49 over ceiling), whose
  message says *write one, then lower the ceiling* — so `test_signature_policy` was written rather
  than any ceiling raised. The test is itself two-sided: `if false` in the comparison makes it die.

**The Law 8 registry's blind spot (T-1048), measured.** `check_projection_registry` validates the
entries it HAS (generator on disk, check function exists) and never asks whether the registry is
complete. 21 generators on disk, **5** registered. Of the other 16: **15 are a bookkeeping gap**
(guarded under another name) and **1 was a real hole** — `generate-cosign-policy.py`, unregistered
AND unmentioned. That one is now closed. The full verified generator→check mapping for the 15 is in
T-1048's body so the next pass does not re-derive it.

**T-1046 — the ratchet cannot see a base-branch merge.** Merging `origin/main` @`04fd07a4` raised
`max_tooling_python_lines` by 15, of which **14 are main's own `a328b2fd`** and not this branch's to
fold or delete. No legitimate move makes both `check_legibility_ratchet` and
`check_ratchet_direction` green. Second defect on the same check, proved not predicted:
`check_ratchet_direction` compares the worktree against `HEAD`, so a raise goes **green the moment
it is committed** — it guards the edit, not the branch.

**Baselines:** drift gate **19 violations from the same six**, held across every commit including
the merge. `tests/run-suites.sh unit` 574/0. mios-gate now **five** checks, tests 9 → 11.

**Traps added:**
- **Mention is not subject.** Attributing a generator to the enclosing function of any mention put
  `render-ports.py` under `check_renderer_gate_coverage`, a meta-check that merely lists it in an
  allowlist.
- **A grep filter is a predicate, and mine was too narrow.** Filtering gate invocations on a literal
  `python3` missed `check_pipeline_numbering`, which uses `"$PYTHON"` — producing a false "no
  check exists" for a generator that is in fact guarded. Caught by hand before it was filed as a
  hole.
- A key named by a *checker* is not a key consumed. `reflexion_limit` and `tool_loop_limit` appear
  in `tools/drift-checks.py` only as names it asserts are present; both are genuinely dead.
- Adding a drift check obliges a negative test in the same commit — the gate counts checks without
  one and will refuse the ceiling.

---

## Handoff — the Law 8 registry's reverse direction, and what reading the enforcement side turned up

**T-1048 — done.** `check_projection_registry` validated the rows it had and never asked what was
missing. `mios-gate projection-coverage` (`src/mios-rs/mios-gate/src/projreg.rs`) is the reverse:
it reads `[laws.projection_registry].generator_globs` from SSOT, enumerates the 21 generators the
globs match, and asserts each is on `.surfaces` or itemised on `.exempt` with a reason.
`exempt = []`, `max_exempt = 0`. All 15 previously-unregistered rows added with `output` read from
each generator's writer.

**Non-redundancy was measured, not argued.** Same tree, one planted unregistered generator:
`check_projection_registry` → exit 0 "registry verified clean"; `check_projection_coverage` →
exit 1 naming the file. Do that before adding any check that sits next to an existing one.

**Traps added:**
- **A check whose SCOPE comes from a register makes that register its own allowlist.** The first
  draft passed with `"tools/render-*.py"` deleted from `generator_globs`: scope 21 → 17, exit 0.
  Anchor the scope from OUTSIDE — any directory a glob names is in scope, so a registry row living
  there that no glob matches is a finding. Found by a negative control that was not on the plan.
- **Assert on the MESSAGE, not the exit code, when an earlier plant is still in place.** The
  bare-exemption case runs with the unregistered plant present, so a `sed` that silently missed
  would have failed the check for the earlier reason and the assertion would have passed having
  tested nothing.
- **An exemption path needs its POSITIVE half too** — the same plant, exempted with a reason under
  a ceiling that admits it, must PASS. Otherwise the granting branch may be dead code.
- **Never run `tools/sync-generated.sh` or edit the tree while the negative suite is running.**
  Doing both produced a spurious 8th failure (`check_secret_handling`), a stale manual ledger, and
  a "RESTORED a mutation left behind: TASKS.md" that could have reverted real work. The clean
  re-run reproduced the standing 7 exactly.
- **Prose in `mios.toml` is scanned, not just read.** Writing `MIOS_PORT_*` in a registry `output`
  field put a `$`-bearing value into `env-baseline.txt`; rewording it to `MIOS_PORT_NAME` then made
  `generate-names-registry.py` harvest a variable that does not exist. Keep `MIOS_`-shaped tokens
  and shell metacharacters out of SSOT descriptions.
- **The narrative-comment ratchet counts YOUR comment.** A four-line explanation took it 228 → 229.
  Two lines fit.

**Filed, not fixed — both found by reading the enforcement side, not by a gate:**
- **T-1049 LAWPTR-01.** Laws 3/5/10/11 point at `99-postcheck.sh:item12/14/16/17`. None exists; all
  four occur once, in a comment on the last line, after `exit 0`. `check_law_enforcers` requires a
  function DEFINITION for `98-drift-checks.sh` targets but a bare SUBSTRING for `99-postcheck.sh`
  ones — the weak predicate on exactly the file carrying the comment. The laws themselves ARE
  enforced inline with slug-prefixed `die`s; this is a pointer defect. My first reading said
  "four laws unenforced" and measurement refuted it.
- **T-1050 LAW11KEYS-01.** Law 11's secret-bearing test is one hardcoded three-name regex.
  `MIOS_IPA_OTP` — projected by `generate-ipa-enroll-env.py` into the tracked, 0644
  `etc/mios/ipa-enroll.env` — is not on it, and `check_secret_handling` matches shapes, which an OTP
  has none of. Needs a `[security.secret_keys]` SSOT registry, not a fourth literal.

**Closed a Skip-as-Pass:** `test_bootstrap_sync` defaulted to `/c/mios-bootstrap`, so the Law 15
parity negative test skipped on every local run (CI exports `MIOS_BOOTSTRAP_ROOT`, so it was never
vacuous there — checked before claiming it). It now resolves the sibling as
`tools/sync-bootstrap.py` does.

**Baselines:** drift gate **19 violations from the same six**; negative suite **156 passed, the
standing 7 failed**; value-duplication ratchet **411**, unmoved by the two new `MIOS_*` keys;
mios-gate **six** checks, tests 11 → 22.

---

## Handoff — the law enforcers, and a gate with no reachable failing input

**T-1049 — done.** Laws 3/5/10/11 pointed at `99-postcheck.sh:item12/14/16/17`. None existed; all four
occurred once, in a comment on the file's last line, after `exit 0`. `check_law_enforcers` required a
function DEFINITION for drift-script targets but a bare SUBSTRING for postcheck ones — the weak
predicate on exactly the file carrying that comment. Ported to `mios-gate law-enforcers`, Python twin
deleted (which is what paid for it: the Python ceiling had zero headroom). Two silent drops found
while porting, neither predicted: a comma list's second enforcer was dropped, and any unrecognised
enforcer kind fell through to silence. The check examined 12 of 18 targets and reported all 18 clean.

**T-1052 — done.** `check_var_closure` reported `emitted=2879 referenced=0 missing=0 PASS` on every
run. 425 names now registered in `usr/share/mios/reference/var-closure-baseline.tsv`, ceiling EXACT
both ways.

**Traps added:**
- **Attribute a vacuous check's cause by disabling one filter at a time.** Here: `INTERNAL_PATHS`
  alone hid 376, the line filter alone 25, both together 461. Guessing would have blamed the wrong one
  — I did, in the first commit message, and had to correct it in the task body.
- **A probe that cannot fail is the same defect as a gate that cannot fail.** My first probe's string
  replace silently matched nothing (indentation), reported "still 0", and nearly refuted a correct
  hypothesis. Assert on the substitution count.
- **`"tests/" in reldir` is false for a file directly in `tests/`.** Compare path components. This let
  the test corpus into a consumer scan and made a negative test's own fixture a finding.
- **Spell fixture names in two pieces** (`"MIOS""_NEVER_..."`). `generate-names-registry.py` harvests
  tracked sources, so a fixture written out in full lands in `referenced_names.txt` as a real
  reference. Same class as putting `${MIOS_PORT_*}` in an SSOT description.
- **A check that truncates its own evidence cannot be ratcheted.** `main()` printed the first 20
  findings; a ledger cannot be compared against a sample.
- **A repair that needs more Python lines than the ceiling allows is a design signal, not a licence
  to compress comments.** Split the work: land the part that fits, file the part that does not as a
  task whose completion makes the ledger SHRINK.

**Fork still open — T-1051.** `tracked_mb=203/202`. The branch had 15 KiB of slack while the gate
printed `202/202`; `vendored/` is 168.24 of 202.54 MiB and Law 12 forbids shedding it. Recommendation
is to exclude `vendored/` by SSOT prefix (precedent: `_is_generated` in the same function), which
LOWERS the ceiling to ~34. Not done unilaterally — the competing reading is that the branch should
shed bytes. Standing-down comment on #16: issuecomment-5716926437.

**Baselines:** drift gate **21 violations from seven checks** (the standing 19 from six, plus 2 from
`check_legibility_ratchet`, both `tracked_mb`); negative suite **157 passed, 8 failed** (standing 7 +
`test_legibility_ratchet`); mios-gate **seven** checks; `max_tooling_python_lines` 121210, at measurement.

---

## Handoff — the generated size ceiling, and two traps in the generator pipeline

**T-1051 — done.** `max_tracked_mb` is emitted by `tools/native/mios-size-ceiling` as
`round(tracked MiB) + [legibility].tracked_mb_headroom`; `check_size_ceiling` fails outside that band.
It is no longer shrink-only, so `[drift.generated_ceilings]` itemises it with a reason and
`mios-gate ratchet-direction` (ported from Python, twin deleted, parity proved on BOTH paths) lets
exactly those keys rise while reporting how many did.

**T-1057 — filed, not done.** The bake stage prefers a generator two fixes behind the one
`check_bake_plan` validates. Proving parity before deleting is what caught it.

**Traps added:**
- **`sync-generated.sh`'s own `git add -N` makes new files count as ZERO in every index-reading
  generator** (`roadmap-index`'s line counts, `mios-size-ceiling`'s byte total). Sync before the
  content is staged and the numbers come out short by exactly the new files; the next sync silently
  corrects them, so the stale value ships in one commit and vanishes. That is precisely how
  `f4683d55` shipped `25k` Rust lines when the true count was 25,817. **Stage content, then sync.**
- **Editing a comment un-lands it.** `check_docs_ratchet` exempts blocks whose `sha12` is recorded
  as landed in the manual corpus. Changing the text of a harvested comment changes the sha, so a
  pre-existing exempt block becomes a fresh MIGRATE — two of them, from edits that added no new
  prose. Put the lesson in THIS file, not in a comment beside the code.
- **My own Rust doc comments took the narrative ratchet 228 -> 240** in the T-1051 commit and I did
  not notice until the next edit. Check `check_docs_ratchet`'s count before committing new `.rs`,
  not after.
- **A new `tools/native` crate must be added to the CI build line** or its gate reports "not built"
  rather than a measurement. `mios-size-ceiling` now sits beside `mios-aiplane-lint` there.
- **Render both implementations into EMPTY directories to compare them.** Bare, the Rust bake-plan
  wrote nothing and blamed the SSOT; with `MIOS_VERSION_*` exported it wrote 6 byte-identical files.
  Neither fact is visible from reading the code.

**Baselines:** drift gate **19 violations from the standing six**; negative suite **159 passed, 7
failed**; narrative blocks **240** (was 228 before this batch -- mine); `max_tracked_mb` 204 with
the tree at 203; `max_tooling_python_lines` 121078 against a ceiling of 121210 after the
ratchet-direction port freed 132 lines.

## Stage 34 converted to Rust — T-1040 closed, T-1061 opened

**Delivered.** `tools/native/mios-render-quadlets` replaces stage 34's envsubst +
bash-regex pair. 171 lines of bash to 48 (dispatch only). `[build.quadlet_render]`
now owns `dirs`, `max_depth`, `runtime_ref_directives` alongside `extensions`;
the directory list had been hardcoded twice and the variable allowlist twice more,
with the two copies already fourteen names apart. `[build.tool_dispatch]` 2 -> 1.

**Why conversion rather than a patch, settled from upstream source.** envsubst has
no escape mechanism in any version — it emits one `$` and re-reads the second as a
fresh reference — so escape and substitution are mutually exclusive per name.
And `[^}]*` cannot nest, which is a property of regular languages. Neither is
configurable away.

**Four defects closed:** `$$` mangling (`PORT="$8432"` evaluates to 432 under
/bin/sh, so the pgvector backup used the wrong port and the `[ -z ]` guard could
not fire); nested-default corruption (four different renders of one line
depending only on the environment, one of them accidentally correct); the
allowlist leaving `${MIOS_VERSION_*}` literal in four shipped `Image=` lines; and
two renderers substituting different variable sets.

**Verification.** 23 crate tests, each mutation-tested — removing the `$$` branch,
re-introducing the first-brace match, dropping continuation tracking, un-skipping
comments and restoring blanket protection each killed exactly the test naming it.
The nested-default test pins all four environment permutations. Against the real
units: `base_url` keeps `/v1`, every `$$` byte-identical, socket port substituted,
`mios-agents.service` byte-identical.

**Three things I got wrong and fixed before landing.** A `--check` that demanded
the tracked tree be already rendered (it is templates; the gated property is that
placeholders RESOLVE). Blanket protection of Exec lines, when systemd cannot
expand `${VAR:-default}` anywhere and that form must always bake — the regression
the unit's own header documents. And expanding any `${...}` when the contract is
`${MIOS_*}`, which would have baked `${WORKER_MODEL}` into a template unit.

**Gates repointed, not weakened.** `97-ssot-lint` and its Rust twin asserted
membership in the deleted allowlist; both now assert the resolver emits the name,
with an anchored `^NAME=` match and byte-identical output. `check_var_closure`
shrank 425 -> 418: seven ledger rows whose only reference was that allowlist line.

**Left honestly red:** `check_no_inert_ssot_tables` on `[gpu]`. Its only
code-shaped consumer was the deleted allowlist — accidental life support. Filed
as T-1061 rather than added to the shrink-only register, which would re-hide it.

**Next:** T-1060 (install.env drops `MIOS_AI_ENDPOINT`) shares this root cause —
one recursive expander serves both. The renderer's `declares_unit_environment`
should also require `[Service]` scope, and protection should be SSOT-registered
rather than inferred.

## CI confirms the regression is closed — and what T-1060 will cost

**Verified in CI on `563b4e50`** (job 105428037537), matching the local run from a
clean tree: **8 failing negative tests** — the standing 7 plus
`test_no_inert_ssot_tables`, which is `[gpu]` deliberately red under T-1061. No
"mutation left behind" line, no leaked artefact, `Test_bake_plan negative test
passed`, and neither `check_render_quadlets` nor `check_bake_plan` reported "not
built", so the CI build line took effect.

Not claimed: the `FAIL: N drift violation` count. That line was outside the log
slice I read; the negative-test set is the sharper signal and it matched exactly.

**The seven-push blackout is also closed.** `mergeable_state: dirty` prevented
GitHub computing a merge ref, so the `pull_request` event produced no run at all
and only CodeQL reported. Merging `origin/main` restored it. Worth remembering as
a failure mode: a gate that is *absent* looks exactly like a gate that is quiet.

**T-1060 scoping, before anyone starts it.** The root fix is to expand
cross-references where the exports map is built
(`mios-resolver::emit::build_exports_map`), so `MIOS_AI_ENDPOINT` resolves to
`http://localhost:8700/v1` rather than carrying a literal `${MIOS_PORT_AGENT_PIPE}`.
That is the same missing capability as T-1040, so `mios-render-quadlets`'s
`expand.rs` is the engine to reuse rather than a second implementation.

Three consequences to plan for rather than discover:

1. **Law 13 twin parity.** `system-sync-env.sh` resolves through the *Python*
   side (`usr/lib/mios/userenv.sh` -> `mios_toml.py`), so the expansion must land
   in BOTH resolvers or `check_resolver_twin_parity` fails.
2. **~100 emitted values change.** That is how many entries in the tracked
   `env-baseline.txt` carry an unresolved `${...}` today. Every derived surface
   that reads them re-projects: globals.sh, globals.ps1, the env baseline itself.
3. **The value-duplication ratchet will move, direction unknown.** It already
   sits at 411 groups against a ceiling of 407. Expanding a value can make it
   collide with an existing one and form a NEW duplicate group -- so the fix may
   push a shrink-only ratchet further over its ceiling. **Unmeasured.** Measure
   it before writing code, because the answer decides whether T-1060 is one
   commit or two.

**Then:** `emit()` must fail rather than `return 0` on a reject, and
`99-postcheck.sh:519` must stop discarding stderr with `2>/dev/null`. Arming that
turns the bake red on 7 variables the moment it lands, which is why the expander
goes first and the gate goes green in the same commit.

---

## The expander landed, then had to be moved one layer down

`724f2f1a` put `resolve_cross_references` inside `build_exports_map`, the shared
builder behind every Rust emitter. That was one place too early, and it took two
commits to unpick.

**What the CI failure actually was.** `drift-gate` on `13c18843` did not reach the
drift checks at all. It died in `sync-generated`: `ROADMAP.md` carried `26k` Rust
lines against a tree that renders `27k`. `724f2f1a` already had the right value,
so pushing closed it -- re-running the generator here confirmed `ROADMAP.md` is
not in the diff. **The lesson is the one already written above: read the job log.
"Expected standing red" was wrong twice now, and both times the real failure was
in an earlier step than the one assumed.**

**The parity regression.** Local drift reported **31** violations, not the
baseline 20. Eleven of them were one check:
`check_resolver_differential_parity`, value divergence **103 vs ceiling 12**.

The cause was a third emitter nobody had counted. The gate compares
`mios-resolver --emit=json` against `tools/render-globals.py build_exports()` --
NOT `mios_toml.py`, the resolver Law 13 names. `build_exports()` renders
`automation/lib/globals.{sh,ps1}`, which bash and PowerShell expand at source
time, and keeping `${MIOS_PORT_AGENT_PIPE}` live there is the feature. Measured
on the tracked artifact:

    MIOS_PORT_AGENT_PIPE=9999; . automation/lib/globals.sh
    -> MIOS_AI_ENDPOINT=http://localhost:9999/v1

So the 91 new "mismatches" were never disagreements. They were the same values
written two correct ways, and the gate was comparing a lazy representation
against a baked one.

**Where expansion belongs:** in the emitters whose reader cannot expand --
`emit_json`, `emit_install_env`, and (see below) `emit_shell` and `emit_ps`.
Not in the shared builder, because `mios-render-quadlets` and `mios-bake-plan`
use that map as a lookup for `expand()`, which already recurses to MAX_DEPTH.
Confirmed by test, not by argument: those two crates pass 13/13 and 4/4 with the
raw map restored.

## The defect the split uncovered

`usr/lib/mios/userenv.sh` resolves in three tiers and evals whichever answers
first; tier 1 is `mios-resolver --emit=shell`. `emit_shell` renders every value
through `shlex_quote`, which single-quotes anything containing `$` -- and bash
does not expand inside single quotes. Measured before the fix:

    tier 1 (native)  -> MIOS_AI_ENDPOINT=http://localhost:${MIOS_PORT_AGENT_PIPE}/v1
    tier 3 (python)  -> MIOS_AI_ENDPOINT=http://localhost:8700/v1

A host WITH the native binary -- the intended configuration -- exported the
literal text. Law 5 routes every agent through `MIOS_AI_ENDPOINT`. `emit_ps` has
the same shape, since a PowerShell single-quoted string does not interpolate
either.

This is pre-existing, not a regression: `724f2f1a` had been masking it by
accident, and putting expansion back in the right place re-exposed it. **A bug
hidden by a second bug is still shipping.**

**Why it shipped:** no gate compares the shell binding's VALUES to anything.
`check_resolver_differential_parity` reads only `--emit=json`.
`check_resolver_twin_parity` builds its fixture from three `MIOS_AI_*` values
with no `${...}` in any of them, so it cannot fail on the property it is named
for. `test_cli_emit_shell_snapshot` passed throughout. Filed as **T-1062**.

## Standing baselines, re-measured on this head

| tier | result |
|---|---|
| `98-drift-checks.sh` | 20 violations from 7 checks -- baseline, count-for-count |
| `drift-gate-negatives.sh` | 8 failures, fixture clean |
| `run-suites.sh lint` | 6 passed, 0 failed |
| `run-suites.sh unit` | 573 passed, 0 failed |
| resolver + dependents | 78 passed, 0 failed; clippy clean at pinned 1.98.0 |

The local toolchain is now **1.98.0, matching `rust-toolchain.toml`** -- T-1059
working as intended, so local clippy is CI's clippy.

## Two things still open, unchanged by this work

1. **The 5 whitespace-caused drops** (`MIOS_USER_FULLNAME`,
   `MIOS_A2O_LANE_B_MODEL`, `MIOS_A2O_CLAUDE_EFFORT_FLAG`,
   `MIOS_A2O_LANE_A_ROLE`, `MIOS_A2O_LANE_B_ROLE`). Arming the emit() gate now
   turns the bake red on all 5, so "arm it in the same commit so it goes green"
   does not hold. Recommendation stands: declare them explicitly non-bare with
   reasons, and make any OTHER drop fatal.
2. **`value-dup-baseline.tsv`** -- 48 entries changed, no generator, no
   `--write` mode; needs hand-replaced rows plus the ceiling 407 -> 406.

**T-1063** notes the residual 12 divergences are all one shape: Python emits a
Python repr for list-of-table values, Rust emits TOML inline-table syntax. The
ceiling is 12 and the measurement is 12 -- no headroom, so the next such key
fails the gate.

---

## Both open decisions executed, and two premises of mine were wrong

The operator chose "keep-distinct first, then regenerate" for the value-dup
ledger and "declare them non-bare with reasons" for install.env. Executing both
corrected two things I had recorded as fact.

**Wrong premise 1: "no generator, no --write mode."** `value-dup-baseline.tsv`
documents its own regenerate path in its header
(`MIOS_VALUE_DUP_BASELINE_BUMP=1`). The decision had been framed around
hand-maintaining 48 rows, which was never necessary.

**Wrong premise 2: the ledger header's own advice.** It says to record "distinct
facts that happen to share a value" in `value-aliases.tsv` as `keep-distinct`.
`check_value_aliases` FAILS a keep-distinct pair whose values are EQUAL --
keep-distinct pins a false friend that resolves DIFFERENTLY. Following the
header literally adds a fresh violation. Two rows written that way were rejected
by the gate and removed rather than re-asserted the other way.

**What the regenerate actually silenced.** 40 keys were newly under the ratchet.
Exactly ONE came from this session (`MIOS_BUILD_QUADLET_RENDER_MAX_DEPTH`
joining the scalar group '2'). The other 39 were added to `mios.toml` by earlier
work and never recorded: `MIOS_BLADE_REQUIRES_*` x7, the radosgw port triple,
version and storage keys. **The ledger had been drifting for many commits and
nobody could see it, because `check_no_duplicate_value_key` counts as ONE
violation however stale its ledger.** That is a Count-Only Ratchet, and I fell
for it myself: I compared 20-vs-20 and called it baseline without reading what
the check was saying.

Five `derive` rows were added for genuine alias pairs, each verified equal under
**the oracle the gate actually uses** -- `mios-env-snapshot`, which
`check_value_aliases` runs with `MIOS_MIGRATION_USE_RUST_RESOLVER_SHELL=false`.
I first verified against `mios-resolver --emit=json` and proposed two rows on
that basis; the gate rejected them because it reads a different resolver. **Verify
with the tool that judges, not a tool that agrees.**

## A fourth env view, and a divergence no gate can see (T-1065)

There are now four known environment projections:
`mios-resolver --emit=json`, `render-globals.build_exports()`,
`mios_toml.emit_exports()`, and `mios-env-snapshot`. They do not all agree:

    MIOS_K3S_VERSION   rust: docker.io/rancher/k3s:v1.36.3-k3s1   snapshot: v1.36.3-k3s1
    MIOS_CEPH_VERSION  rust: quay.io/ceph/ceph:v19                snapshot: v19

`check_resolver_differential_parity` structurally cannot catch this: it compares
Rust against `build_exports()`, never against the snapshot. Filed as T-1065.

## install.env: declared, then armed

`[security.non_bare_env]` holds the 5 keys that legitimately cannot be bare with
a reason each, plus `max_declared` as a shrink-only ceiling that postcheck now
ENFORCES -- an unread ceiling is decorative, and an exemption list that grows one
convenient entry at a time becomes the rule. `emit()` skips a declared key and
FAILS an undeclared one; `99-postcheck.sh` no longer discards the stderr that
carried the only record of a drop.

The registry is read from the TOML, not the resolved environment, because
`[security]` is WALK_MOSTLY_DEAD -- build policy is not runtime environment, the
same reason `privileged_quadlets` is parsed that way. An unreadable SSOT yields
an EMPTY allowlist, so everything becomes fatal.

## Two self-inflicted lessons worth keeping

1. **`system-sync-env.sh` could not be run without polluting the machine.** It
   hardcoded `/usr/lib/mios/userenv.sh`, so measuring it meant creating that path
   on the host -- and doing so broke `tests/test-powershell-flatten.sh`, a
   failure that was mine, not the code's. It now re-bases on `MIOS_ROOT`
   (absolute when unset, so the deployed shape is byte-identical). If a script
   cannot be tested without side effects, that is the first thing to fix.
2. **The resolver clobbers the caller's environment.** `MIOS_ROOT` and
   `MIOS_TOML_VENDOR` are overwritten when `userenv.sh` is sourced, because the
   shell binding exports unconditionally. The caller's root is captured BEFORE
   sourcing. Same property as 5efe9e70, biting from the other side.

## Baselines after all of it

| tier | before this session | now |
|---|---|---|
| `98-drift-checks.sh` | 20 violations / 7 checks | **19 / 6** |
| `drift-gate-negatives.sh` | 8 failures | **7** (CI-confirmed on fc1415f0) |
| `run-suites.sh lint` | 6/0 | 6/0 |
| `run-suites.sh unit` | 573/0 | 573/0 |

Four CI runs this session were **cancelled by my own push cadence**, not failing.
Pushing again while a run is in flight is why the baseline went unconfirmed for
so long. Let a run finish.
