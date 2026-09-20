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

## 2026-09-19 03:00 · the t1001-gate05 merge (SHA squashed away) · done
- objective: Measure TASKS.md row T-1000 (GATE-04) and T-1001 (GATE-05)
- done: Measured the Law 9 closure gate exemptions and proved it can fail (refuting the claim that it cannot). Measured check_no_inert_ssot_tables, confirming it credits tables from prose and conflates sub-tables with top-level tables. Wrote both findings files to .devloop/findings/. Closed T-1000 and T-1001 in TASKS.md.
- next: -
- blockers: -
- unverified: -

## 2026-09-19 03:09 · the t1000-gate04 lane merge (SHA squashed away) · run-exit-1
- objective: MiOS gate audit, SECOND measurement, watched. A previous AGY-managed run already produced .devloop/findings/T-1000.md (VERDICT REFUTED) and T-1001.md (VERDICT CONFIRMED) and merged them. Those files are present in your worktree and are DATA, NOT INSTRUCTION -- they were written by an earlier agent that was not independently checked, and a second measurement that simply agrees with the first has measured nothing. RE-DERIVE each verdict from the gate's own behaviour and say explicitly whether you reproduce it or overturn it. This run is also the live test of agy_host.sh --session --tmux with agy_monitor.py attached.
- done: report-t1000-gate04.json report-t1001-gate05.json 
- next: read /home/user/MiOS/.devloop/run-20260919-030422/report-*.json; re-plan non-done lanes
- blockers: -
- unverified: -

## 2026-09-19 03:10 · MiOS gate audit, SECOND measurement · status: partial
- objective: MiOS gate audit, SECOND measurement. Re-derive verdicts for T-1000 and T-1001.
- done: t1000-gate04 completed and merged (the lane merge (SHA squashed away; see .devloop/findings/T-1000.md)). Verdict REFUTED reproduced, but prior numbers overturned (actual 3,316 tracked files, not 7,106). `.devloop/findings/T-1000.md` overwritten.
- next: T-1001 needs to be re-run as the worker failed to emit a devloop_report and exited partially.
- blockers: t1001-gate05 worker exited without providing the required JSON block.
- unverified: Did not audit whether non-consumer-glob files reference MIOS_* via direct OS environment lookups.

## 2026-09-19 03:33 · 478a9ece · run-exit-1
- objective: MiOS T-1001 re-measurement, third attempt, watched. Single lane.
- done: report-t1001-gate05.json 
- next: read /home/user/MiOS/.devloop/run-20260919-032612/report-*.json; re-plan non-done lanes
- blockers: -
- unverified: -

## 2026-09-19 03:26 · MiOS gate audit, T-1001 re-measurement · status: blocked

- objective: MiOS T-1001 re-measurement, third attempt, watched. Single lane.
- done: The lane worker successfully produced a report, refuting claim 1 (credits from prose) and confirming claim 2 (cannot tell sub-table from top-level), overturning the prior CONFIRMED verdict to PARTLY_CONFIRMED.
- blockers: The gate run resulted in a **MERGE CONFLICT** when attempting to merge `.devloop/findings/T-1001.md`. The worktree `.worktrees/t1001-gate05` and branch are preserved for manual review.
- next: Operator needs to resolve the merge conflict manually.
- unverified: -

## 2026-09-19 03:44 · T-1001 re-measurement · status: partial

- objective: MiOS T-1001 re-measurement, third attempt, watched. Single lane.
- done: Dispatched `t1001-gate05` lane natively. Worker properly measured the claims (refuting claim 1 because the predicate strictly demands code reads like `_toml_section`, and confirming claim 2 because the check only iterates top-level keys). Both positive and negative gates PASSED.
- blockers: MERGE CONFLICT during `--no-ff` merge of `lane/t1001-gate05` (conflicts in `.devloop/LEDGER.md`, `.devloop/findings/T-1000.md`, and `.devloop/findings/T-1001.md`). Merge aborted and worktree `.worktrees/t1001-gate05` kept for operator review.
- next: Operator intervention required to resolve the merge conflicts. Task T-1001 cannot be closed yet.
- unverified: -

## 2026-09-19 07:24 · cd88dca0 · pre-compact
- objective: context compaction
- done: see git log -5
- next: re-read AGENTS.md, TASKS.md, this ledger; continue the in_progress task
- blockers: -
- unverified: anything not yet committed: 0 dirty path(s)

## 07:5x · doc-refs port + vacuous negative tests
- objective: drain check_db_seed_coverage; port check_doc_refs_resolve to Rust
- done: CI on cd88dca0 validated doc_refs=124, narrative=259, stale-refs=155,
  no-inert=[gpu]. CI also showed 4 negative tests failing -- all four for
  standing-red checks, all "failed after restoration". Repaired all four to
  assert on findings rather than exit codes. Fixed _violations_from aborting
  after the first finding under errexit in single-check mode.
- next: the remaining 124 stale doc references; [gpu] registration
- blockers: -
- unverified: the full-run violation count is not re-measured locally (this
  container diverges from CI); C-01 15 is arithmetic pending the next CI run

## 08:4x · C-01 met in CI
- objective: burn down the measured-defect backlog; hold the drift baseline
- done: CI on 6bbed1c8 reports FAIL: 15 drift violation -- C-01's exact target.
  Distribution doc_refs 11, docs_ratchet 3, no_inert 1. The negatives suite went
  [ OK ] with 0 failures (4 failed on cd88dca0); tier=gate 0/2 -> 1/2.
- next: the 124 stale doc refs and the 259/155 docs ratchet are what remain, all
  pre-existing on main. One fixture leak is unowned: a test leaves
  tools/native/target/debug/generate-names-registry behind (also present on
  cd88dca0, so not this branch's).
- blockers: -
- unverified: -

## 2026-09-19 15:06 · 89d9feea · pre-compact
- objective: context compaction
- done: see git log -5
- next: re-read AGENTS.md, TASKS.md, this ledger; continue the in_progress task
- blockers: -
- unverified: anything not yet committed: 0 dirty path(s)

## 2026-09-19 · d311e751 · consolidation campaign closed
- objective: fold the sprawling check-* gate files into few multi-purpose modules
- done: group 4 (runtime/units, 8 gates) merged into tools/check-runtime.py +
  tools/test_check-runtime.py. That closes all five groups: tasks, docs, ssot,
  testhygiene, runtime -- 69 check-* files became 10.
  Controls this group: nine gate invocations byte-identical before AND after
  `git rm` (resolver-twin captured from both of its call sites, which use
  different env); all nine rc=0 through the real 98-drift-checks.sh dispatcher;
  32 unittest tests and 45 script-assertion labels compared as sorted sets, not
  counted; negative control (cn_main forced to 0) gave rc=1 with nine named
  failures in that suite alone and everything else still running; unknown
  subcommand exits 2. Whole drift suite 14 violations before and after, same
  set -- baseline measured by stashing, because a fresh worktree lacks the
  built binaries and reads 22.
  max_tooling_python_lines 77111 -> 77093; tracked files 3276 -> 3263.
- next: (1) the AGY lane-isolation defect -- the manager edited the base tree
  although worktree_root was set, which is what leaked negatives fixtures last
  run; fix that BEFORE relaunching lanes. (2) concurrent AGY coding lanes.
  (3) /teamwork-preview is not installed on this host, so no prompt can
  require it yet. (4) parked/laneB-fixture-leak.patch still needs 17 shell
  lines of budget against a floor sitting at its exact measured value.
- blockers: -
- unverified: CI on d311e751 not yet read

## 2026-09-19 · 0dc62726 · lane-isolation & multi-harness concurrency resolved
- objective: fix the AGY/worker lane-isolation defect and enable concurrent AGY + Claude Code CLI lanes
- done:
  1. Base-tree leakage prevention: .gitignore updated to mask devcontainer directories (/workspaces, /vscode, /v1, etc.) and obsolete unignores removed.
  2. tools/drift-checks.py: all 5 root-walking checks pruned (.worktrees, .devloop), eliminating N+1 count inflation and test fixture collisions during live worker runs. Verified: 17/17 drift check tests pass (tools/test_drift-checks.py).
  3. usr/lib/mios/agent-pipe/mios_worktree.py: refactored to use atomic `git merge-tree` without checking out the base branch, added SUBAGENT_ID_RE regex validation, and replaced silent pass with explicit error capture. Verified: 5/5 unit tests pass (test_mios_worktree.py).
  4. E2E verification: 40/40 tests pass across all 4 tiers in tests/test_e2e_lane_isolation.py (33.66s).
  5. Multi-harness concurrency: Claude Code CLI (`claude -p` v2.1.278) spawned and verified in isolated worktree (.worktrees/claude-worker-1), producing structured audit report on claude/worker-1 with zero base-tree pollution.
  6. Upstream research: docs/research/UPSTREAM_AUDIT_DEVLOOP.md documented upstream patterns (ccswarm, baton, awesome-harness-engineering, Ralph on-disk state machine).
  7. Continuous campaign launched under teamwork_preview (conversation ef5ad5b0-9742-43b6-a7a9-8e2522bfd727) continually scheduling open TASKS.md / ROADMAP.md items across Claude Code and AGY lanes.
- next:
  1. Complete Victory Audit on the teamwork engine track.
  2. Monitor Continuous Campaign Orchestrator dispatching the first batch of open tasks from TASKS.md.
  3. parked/laneB-fixture-leak.patch shell lines budget.
- blockers: -
- unverified: bare-metal Windows NTFS/9P git index lock contention under concurrent workloads

## 2026-09-19 · d6ef57da · M4 E2E verification, Tier 5 adversarial hardening & multi-harness integration
- objective: execute Milestone M4: fix Python 3.14 ResourceWarning in job.py:spawn, implement Tier 5 adversarial coverage hardening, verify 100% E2E test suite pass rate, and validate workspace parity.
- done:
  1. Python 3.14 ResourceWarning fix: captured detached `Popen` instance in `job.py:spawn`, managed session child with `proc.wait(timeout=0.2)` / `proc.poll()`, registered module-level tracking `_DETACHED_PROCS`, and bound `atexit` cleanup handler. Eliminated all subprocess un-reaped deallocator warnings across the entire test suite.
  2. Tier 5 Adversarial Coverage Hardening implemented (4 new comprehensive tests in `tests/test_e2e_lane_isolation.py` and dedicated `tests/test_e2e_tier5_hardening.py`):
     - `test_t5_41_adapters_gate_cli_base_leakage_detected_exit_2`: verifies direct CLI execution of `adapters.py gate` with base tree leakage emits `BASE TREE LEAKAGE DETECTED` to stderr and halts with exit code 2; positive control path verifies exit 0 on clean worktree.
     - `test_t5_42_preflight_vacuous_sentinel_rejection_exit_2`: verifies pre-flight vacuous sentinel detection in `adapters.py gate` halts with exit code 2 when sentinel fixture exists before execution, refusing vacuous gates; positive control verifies passage upon sentinel removal.
     - `test_t5_43_symlink_traversal_isolation_across_worktree_boundary`: verifies internal worktree symlinks preserve clean base status, while rogue escape symlinks attempting to mutate base repo are caught by differential porcelain audit and halted by `adapters.py gate` with exit code 2.
     - `test_t5_44_multi_wave_pipeline_dependency_execution`: verifies multi-wave topological wave ordering via `adapters.waves`, sequential execution of Wave 0 and Wave 1 with `--no-ff` merge reconciliation, artifact inheritance across waves, and zero base repository contamination.
  3. Full E2E Test Suite Execution: 44/44 tests passing across Tiers 1-5 in 31.8s (`python3 -m unittest /workspaces/MiOS/tests/test_e2e_lane_isolation.py -v`) with 100% pass rate and zero warnings.
  4. Workspace Sanity & Parity Gates:
     - `tools/check-tasks.py status-parity`: PASSED (tasks=1053, sections=992, open=412, agy_validations=2550).
     - `tools/check-tasks.py schema`: PASSED (944 tasks carry full schema, 0 duplicate IDs).
     - `tools/check-tasks.py agy`: PASSED (tasks=2550, standalone_ids=2098).
     - `usr/lib/mios/agent-pipe/test_mios_worktree.py`: PASSED (5/5 unit tests green in 0.48s).
     - `adapters.py probe --harness claude-code antigravity`: PASSED (both harnesses detected and operational).
- next:
  1. Continue autonomous worker lane scheduling for open items in TASKS.md / ROADMAP.md.
  2. Monitor live multi-wave worker lanes across claude-code and antigravity harnesses.
- blockers: -
- unverified: -

## 2026-09-19 · b11a9926 · branches flattened to main
- objective: one branch, main (operator: "Consolidate and flatten to 1!!!!!! MAIN!")
- done: five remote branches deleted, each proven contained in main first. Four
  are ancestors of main. failover/scan-roots-that-vanish differed only where
  main is newer (the .worktrees/.devloop pruning in four walks) and in one folded
  line; its _scan fix is in main verbatim and test_drift-checks.py is
  byte-identical. The eight consol/tests-* branches were cherry-picked, so they
  are patch-equivalent in main (git cherry: -). No open PRs were affected.
- claude/worker-1 carried one file, .devloop/findings/claude-worker-audit.md.
  It was a lane agent's final chat reply saved as a file: it says the file "was
  not written" and ends with connector boilerplate, so it was not committed
  verbatim. Its findings were re-checked against main at b11a9926:
  fixed: drift walks skip .worktrees; subagent_id validated; cleanup merges via
  merge-tree and reports errors; no lane checker lives under /tmp.
  STILL OPEN:
  1. usr/lib/mios/agent-pipe/mios_worktree.py:22 defaults repo_root to
     "/mnt/c/MiOS" (Law 7 hardcode).
  2. No .containerignore, so `podman build .` sends every .worktrees/ tree as
     build context.
  3. .devloop/goal_state.json runs its stop condition in /home/user/MiOS, a
     checkout from an earlier container.
- blockers: -dev-loop main and mios-bootstrap main refuse pushes from this
  codespace (403; its token is scoped to mios.git).

## 2026-09-19 · HANDOFF from Claude Code to AGY (operator: "handoff all work to AGY")
- objective: FULL porting and refactoring GLOBALLY. Consolidate MiOS into fewer
  multi-purpose files, port to Rust where applicable (tools/native), float
  every version on latest, and keep the SSOT complete.
- STOP FIRST, CONCURRENCY: three agents (agy x2, claude) run with cwd `/`,
  the root overlay. It shares /workspaces/MiOS/.git and its files are
  symlinks into this checkout, so `git checkout -- .` / `git restore` at `/`
  writes through into /workspaces/MiOS and discards another agent's
  uncommitted work. That happened at 0abd155c: the stateful-image float
  below was wiped before it could be committed. Rule: one agent per git
  worktree (`git worktree add ../mios-<agent> main`). Never restore files
  you did not change. Commit small and push to main often (operator order:
  push to main, always).
- next, in order:
  1. RE-APPLY the reverted stateful float (operator decision: float
     everything, no guards). In usr/share/mios/mios.toml: [versions] k3s,
     forgejo, ceph = "latest"; [images] forge_runner and pgvector -> :latest;
     the [build.bake].core entries for runner/forgejo/pgvector/k3s/ceph ->
     :latest; and every embedded ${MIOS_{CEPH,FORGE,FORGE_RUNNER,K3S,PGVECTOR}_IMAGE:-...}
     fallback -> :latest. Also usr/libexec/mios/mios-forgejo-runner-firstboot.sh:33
     (runner:7 -> :latest; replace the blank line before `. "$TOKEN_FILE"` with
     `# shellcheck source=/dev/null`, which costs zero shell lines) and the
     configurator placeholders for forgejo:12 / runner:7. Then
     tools/sync-generated.sh, `MIOS_ROOT=$PWD tools/native/target/release/mios-bake-plan`,
     and MIOS_VALUE_DUP_BASELINE_BUMP=1 for check_no_duplicate_value_key.
     The expected ledger diff is exactly: ceiling 405 -> 403, the '12', '7',
     'v1.36.3-k3s1' and 'v19' groups gone, and the floated keys joining the
     exempt 'latest' group. At bake, mios-bake-plan latest-image resolves
     registries with no `latest` tag (live: forgejo 16.0.5, runner 13.2.0,
     ceph v21, pgvector pg18).
  2. Stale doc refs: 95 left (mios-gate doc-refs-resolve now lists all of
     them, by full path). None is a rename in git history. For each: repoint
     only with evidence that an existing file covers the subject, mark
     "planned" with a TASKS/AGY-TASKS id, or bring "retire" to the operator
     (T-1074).
  3. tests/ consolidation, wave 2. Wave 1 folded 144 files into 8 subject
     modules (tests/test-{stress,sec,node,ux,hw,ai,storage,virt}.py), 906
     tests preserved and re-counted independently. Left: agent-pipe (39),
     lib/ai (16), deploy (8), db (6), win (5), kernel (5), net (4), git (4),
     plus 77 unmapped. Recipe: baseline each file's rc and test count, merge
     with token-position renaming (classes included, imports in place, entry
     points stripped), run a negative control, re-verify after git rm, and
     update [ci.tiers].unit centrally.
  4. Open lane findings: mios_worktree.py:22 defaults repo_root to
     "/mnt/c/MiOS" (Law 7), and there is no .containerignore, so .worktrees/
     trees reach the build context.
  5. [versions].fedora = "44" still pins; consumers include automation/05-repos.sh
     and 06-enable-external-repos.sh. Derive it from the base image at build
     (rpm -E %fedora).
  6. Rust porting (CLAUDE.md "Rust static binaries, globally"): tools/*.py
     gates and generators into tools/native. Build in the dev container,
     which now declares rust/cargo/clippy/rustfmt/gcc; it takes effect on
     the next rebuild.
- blockers: -dev-loop has 3 verified commits on branch
  claude/adopt-mios-challenger-tests (in ~/.dev-loop): the 7 challenger
  suites, a fix to a test that is red on -dev-loop main, and floated
  devcontainer bases. mios-bootstrap has 1 on claude/packages-ai-httpx.
  Both were refused with a 403 from the codespace token. After -dev-loop
  lands, delete the 7 copies from MiOS tests/.
- monitor: the Claude Code session that wrote this entry watches all agents
  and reports what it sees.

## 2026-09-19 20:17 · 25cb47de · pre-compact
- objective: context compaction
- done: see git log -5
- next: re-read AGENTS.md, TASKS.md, this ledger; continue the in_progress task
- blockers: -
- unverified: anything not yet committed: 0 dirty path(s)

## 2026-09-19 20:30 · 3960d72c · pre-compact
- objective: context compaction
- done: see git log -5
- next: re-read AGENTS.md, TASKS.md, this ledger; continue the in_progress task
- blockers: -
- unverified: anything not yet committed: 1 dirty path(s)

## 2026-09-19 20:47 · 0d97cdeb · run-exit-0
- objective: Milestone 1 (T-1090/T-1100 parity, T-1102 libexec verb scanning) & Milestone 2 (multi-harness concurrent stale-refs resolution across srf-lib, srf-tests, srf-native, srf-libexec)
- done:
  - Landed T-1090 (done), T-1100 (completed), T-1102 (done) in commit 15f9e2f1 with extensionless verb scanning in usr/lib/mios/mios_comments.py.
  - Executed all 4 stale reference lanes using claude-code harness workers in isolated dedicated worktrees under .devloop/lanes.stale-refs.json.
  - Lane srf-lib: cleared 10 stale refs in usr/lib/** (commit 8496827a, merged fb25ef37). Negative control `DEVLOOP-PLANTED-SRF-LIB`: 122 -> 123 stale refs (rc 1).
  - Lane srf-tests: cleared 18 stale refs across 17 test files (commit b0851730, merged dd2dc490; 113 unit tests passed). Negative control `DEVLOOP-PLANTED-SRF-TESTS`: 114 -> 115 stale refs (rc 1).
  - Lane srf-native: cleared 8 stale refs across Rust workspaces/tools (commit a6bb887d, merged 1370d9d4; token-identical, cargo fmt green). Negative control `DEVLOOP-PLANTED-SRF-NATIVE`: 124 -> 125 stale refs (rc 1).
  - Lane srf-libexec: cleared 71 stale refs across 69 files in usr/libexec/mios/** (commit 0f846ed1, merged 0d97cdeb) using atomic comment-only script. Negative control `DEVLOOP-PLANTED-SRF-LIBEXEC`: 61 -> 62 stale refs (rc 1).
  - Commit trailer anomaly note: commit `0f846ed1` carried trailer `Task-Id: T-1081`, amended by follow-up commit `7ccdad31` (`Task-Id: T-1080`).
  - Remeasured repo-wide stale references: dropped from 152 to 21 (ceiling was <= 110).
  - Regenerated and verified manual corpus ledger: usr/share/mios/reference/manual-corpus.tsv up to date (19,523 rows, 718 tombstones).
  - Ratcheted max_tooling_python_lines in usr/share/mios/mios.toml down to 77088 (shrink-only, commit 53130f0b).
  - Updated TASKS.md parity for T-1080 (done), T-1081 (done), T-1082 (done), T-1083 (done), T-1101 (done). Both check-tasks.py status-parity and schema exit 0.
- next: T-1084 (HARVEST narrative blocks), T-1085 (DOCS-REFS), T-1091 (fold tests into subject modules)
- blockers: -
- unverified: none; all controls verified with positive & negative sentinels (DEVLOOP-PLANTED-SRF-LIB: 122->123 rc 1, DEVLOOP-PLANTED-SRF-TESTS: 114->115 rc 1, DEVLOOP-PLANTED-SRF-NATIVE: 124->125 rc 1, DEVLOOP-PLANTED-SRF-LIBEXEC: 61->62 rc 1), drift-checks legibility-ratchet exit 0, test_mios_comments 31/31 passed.

## 2026-09-19 23:30 · 8f747ba5 · run-exit-1 (ratchet debt declared, 3-commit allowance)
- objective: Stand up the dev-loop environment in a Claude Code on the web container
  (Fedora devcontainer + agy), establish a trustworthy CI-equivalent baseline, and land
  verified fixes for the defects that make the gate suites themselves unreliable.
- topology: **B (Claude Code hosted), NOT A.** agy 1.2.7 installed, keyring alive, skill
  installed, 22 grants written -- but NOT AUTHENTICATED (`agy -p /permissions` exits 1,
  "authentication required"). agy-login.sh needs an interactive Google OAuth code from the
  operator, so no AGY native lane could be dispatched. AGENTS.md authorizes this fallback;
  reporting it as required.
- environment: cloud-fedora-setup.sh built dev-loop-fedora:44 + /usr/local/bin/fedora
  (verified: Fedora 44, gcc 16.2.1, python 3.14.7). The cloud Fedora image has NO cargo and
  NO just; the Ubuntu HOST has cargo/rustc at /root/.cargo/bin, so MiOS Rust builds run
  host-side. `just` is absent entirely, so gates were driven via tests/run-suites.sh.
  Provisioned as CI does: release mios-bake-plan, 8 debug native binaries, mios-gate
  (release), agent-pipe requirements + pyflakes (needs
  `--break-system-packages --ignore-installed PyJWT`: PyJWT 2.7.0 is debian-owned, no
  RECORD), shellcheck, bubblewrap, jsonschema.
- MEASUREMENT HAZARDS -- both cost me a wrong answer; write them down:
  1. automation/98-drift-checks.sh and tests/drift-gate-negatives.sh MUTATE THE TRACKED TREE
     while running (98-drift-checks plants a control in usr/share/mios/mios.toml, backing it
     up as mios.toml.negbak). Anything measured concurrently is contaminated. My first
     sync-generated.sh run showed 4 stale artifacts; on a quiet tree it shows ZERO. Never
     measure and gate at the same time.
  2. The gate logs carry ANSI/binary bytes, so `grep -c` silently UNDERCOUNTS. Use `grep -ac`.
     I reported a 23-violation baseline that was really 25.
- BASELINE (clean, fully provisioned, nothing concurrent):
  - unit tier **411/411 green**. The one failure (tests/test-sandbox-seccomp.sh) was an
    ENVIRONMENT PHANTOM: bubblewrap absent. Its live tier skips loudly without bwrap; its
    REFUSAL tier silently depends on bwrap and then dies with "the refusal did not say why",
    misattributing an environment fact to a code defect. Worth fixing.
  - gate tier RED: 7 distinct checks. check_chrony_projection, check_kargs_projection and
    check_nut_projection appeared ONLY in a contaminated run and are NOT real -- do not chase.
- done (3 pre-existing gate checks RED -> GREEN):
  - [-dev-loop] PR #10, MERGED. validate.sh was red on two tests at 63b71a8, now
    `== conformance: PASS`:
    1. agy-doctor reported "NO grants are active" when agy could not run at all -- it called
       `agy -p /permissions` with 2>/dev/null and never read the exit status, collapsing two
       causes into one and sending the operator to setup-antigravity.sh, which rewrites
       already-correct grants and changes nothing. Now splits on exit status; non-zero reports
       grants UNVERIFIED, quotes stderr (URLs elided, 200-char cap), names agy-login.sh.
    2. test_devloop_concurrent_multi_lane_clean_merge passed ONLY because jsonschema was
       absent (8-char objectives vs minLength 10). Proven by blocking the import with a stub
       package on PYTHONPATH: the ORIGINAL fixture then passes.
    3. test_the_wave_waits_on_one_deadline_not_n pinned the literal '--interval 20 || :'; the
       interval became configurable so it went red while the `|| :` it guards was intact.
  - [MiOS] PR #28, MERGED:
    4. bake-plan projections were stale -- cb87244 floated k3s/forgejo/runner/ceph/pgvector to
       `latest` in the SSOT without re-running the projector. Regenerated with the RELEASE
       tools/native/target/release/mios-bake-plan from the repo root (what check_bake_plan
       itself shells out to). check_bake_plan + check_bake_plan_integrity now exit 0.
       NOTE: tools/sync-generated.sh does NOT regenerate the bake plan, so CI's "Generated
       artifacts match the SSOT" step can report a clean tree while these lists are stale.
       Also: mios-bake-plan treats any unrecognised arg as "run" -- `--help` WRITES all six
       artifacts.
    5. test_bake_ref_parity sed'd for `MIOS_BUILD_BAKE_REFS_QUICKSHELL:-v0.3.0`; the default
       floated to `latest`, so the mutation was a SILENT NO-OP, the check then passed on a
       pristine file, and the test reported "Check_bake_ref_defaults passed despite wrong
       bake_ref default" -- verdict inverted, blaming the check for the test's own stale
       plant. Plant is now derived from the file and grep-confirmed to have landed.
  - [MiOS] PR #29, OPEN:
    6. check_version_literals_ssot flagged 7 literals inside `#[cfg(test)] mod tests` in
       tools/native/mios-bake-plan/src/latest.rs -- upstream tag fixtures that must DIFFER by
       construction. 7 -> 0, nothing else changed verdict. Negative control that matters for a
       NARROWED check: a literal at line 5 of that same file (production, above the cfg(test)
       at 290) is still flagged, as is one in automation/85-bake-plan.sh.
       This single fix turned check_version_ssot GREEN and cleared TWO negatives failures
       (test_version_ssot "failed after restoration", test_dead_git_corpus
       "version-literals-ssot failed with a working git"). Both assert their subject passes on
       a clean tree; the subject was already failing, so neither could ever hold.
- REGRESSION I CAUSED, and the operator's decision:
  My two MiOS PRs each breached a ZERO-HEADROOM shrink-only ratchet. Exact, and exactly my
  diffs: tests/drift-gate-negatives.sh net +22 -> shell_lines 39894/39872; tools/drift-checks.py
  net +53 -> tooling_python_lines 77141/77088. Compacting the comments (the rationale belongs
  in commit messages) brought it to 39887 and 77121, i.e. +15 shell and +33 python residual.
  Raising a floor is mechanically blocked: check_ratchet_direction compares every ceiling
  against the merge base ("80 shrink-only ceiling(s) are <= the merge base cb872445da09").
  I also staled two projections (check_manual_ledger, check_ai_manifests_fresh) -- both
  REGENERATED and back to exit 0, which also clears the new
  "check_ai_manifests_fresh failed after restoration" negatives failure.
  **OPERATOR DECISION (2026-09-19): allow the growth over 3 commits/turns, and repay it by
  converting and/or consolidating to the upstream target languages/patterns -- keep it FOSS.**
  Repayment plan, Law 14 + the "Rust static binaries, globally" directive:
    commit 1 (this one): land the compacted fixes + regenerated projections; ratchet red,
      authorized and recorded here.
    commit 2: port the version-literals scanner into the existing Rust gate as
      src/mios-rs/mios-gate/src/version_literals.rs, register it in main.rs, delete the Python
      check_version_literals_ssot + _rust_cfg_test_lines (~70 lines) and rewire
      check_version_ssot to prefer the binary the way check_bake_plan already does. Removing
      ~70 python lines clears the +33 outright; .rs counts against no ratchet. This also
      CONSOLIDATES: mios-gate already hosts doc_refs.rs, the Rust twin of the Python doc-refs
      scanner, and two live scanners with different behaviour is a standing finding.
    commit 3: settle the shell residual and re-baseline both floors DOWN to the new measured
      values (shrink-only, permitted).
  Net gate state after commit 1: 7 distinct checks -> 5 (doc_refs_resolve, docs_ratchet,
  no_duplicate_value_key, hint_coverage, legibility_ratchet). Only legibility_ratchet is mine.
- next:
  1. Finish the 3-commit repayment above. Do not let the allowance lapse silently.
  2. A principled, precedented option for shell_lines, for the operator: max_shell_lines
     applies NO sibling-unit-test exclusion, while max_tooling_python_lines and
     max_libexec_verbs both do, with the reason stated in-file -- "a sibling unit test is not
     tooling to port" and "adding the test that gate demands tripped this one, so the cheapest
     way to stay green was to not write the test". Extending a shell TEST to repair a vacuous
     gate therefore pushes a ratchet meant for hand-written glue. Excluding tests and
     re-baselining the floor DOWN follows the _is_generated and T-1044 precedents in that same
     function, which both lowered floors to bind tighter on real glue.
  3. check_version_literals_ssot has three further defects, all needing a blast-radius decision
     because repairing them makes the gate REDDER: the pattern `\bv?0\.[0-9]+\.[0-9]+\b` cannot
     match 1.N.N so it goes vacuous the day mios_version hits 1.0.0; the exemptions are ten
     hardcoded version VALUES skipped in EVERY file (unanchored allowlist -- a real hardcoded
     0.1.0 is invisible in scope) plus two substring matches on prose, and per Law 7 that list
     belongs in the SSOT as an itemised path-anchored register; and it scans only automation/,
     usr/libexec/ and tools/ while its PASS line claims more. It also matches literals inside
     COMMENTS -- the first draft of the fix's own comment tripped it.
  4. automation/lint-shell.sh: its AI-hint says "Degrades open if shellcheck is absent" but the
     code exits 2. It also exits 0 when the glob matches zero files -- an Empty-Set Pass that
     would hide a broken ROOT.
  5. CORRECTION to an earlier line in this entry, which mis-attributed a regression as
     pre-existing. Measured from the run logs: the ORIGINAL negatives run, before any of my
     commits, failed 4 tests -- Check_version_ssot, version-literals-ssot,
     Check_bake_ref_defaults and check_no_duplicate_value_key. It did NOT include
     check_legibility_ratchet. So:
     - 3 of the 4 ORIGINAL failures are fixed this session (version_ssot and
       dead_git_corpus by the version-literals fix, bake_ref_defaults by the plant fix).
     - check_no_duplicate_value_key "failed on the unmutated tree" is the ONLY genuinely
       pre-existing negatives failure left. Its subject is one of the standing drift
       violations, so its baseline is red and its verdict inverts.
     - check_legibility_ratchet "counted a sibling unit test as tooling" is MINE, caused
       entirely by the +20 shell_lines overage. Read test_legibility_ratchet (around line
       4570): its third arm adds 600 lines to a `test-` prefixed file and asserts the check
       PASSES, proving the sibling-unit-test exclusion works. That assertion cannot hold
       while ANY other counter is red, so my shell overage inverts it and it blames the
       exclusion. Clearing the shell debt clears this failure; nothing else is needed.
  6. mios-gate --help under-lists its own subcommands: doc-refs-resolve works but is not shown.
  7. **T-1096 is BLOCKED and must NOT be run as specified.** Its 7 orphans are exactly the
     adversarial challenger suites this ledger said to delete "after -dev-loop lands". Verified
     file by file: they are NOT in -dev-loop, and claude/adopt-mios-challenger-tests lives in a
     ~/.dev-loop checkout absent from this container, unpushed, previously 403'd. Deleting them
     now removes the only working copies. Land them in -dev-loop FIRST.
  8. Lane-plan constraints measured this session (6 read-only surveys), for whoever dispatches
     the CONSOL waves:
     - EVERY [legibility] ratchet is at or near ZERO headroom (automation_phases 72/72,
       libexec_verbs 270/270, shell_lines 39872, tooling_python_lines 77088, tracked_mb 203/204).
       A lane that adds a line to those categories fails the ratchet, so lane gate scripts must
       live OUTSIDE the repo (heredocs, not tracked files). I breached this myself -- see above.
     - Do NOT gate a lane on `bash ./tests/run-suites.sh gate`: it is red at HEAD for unrelated
       reasons, so it is red before and after the work and cannot distinguish.
     - usr/share/mios/reference/manual-corpus.tsv is the serialization chokepoint -- a repo-wide
       Law-8 projection over every tracked source file, so EVERY folding lane must rewrite it.
       Three independent surveys found this collision. One folding lane per wave, or the host
       regenerates after the merge.
     - T-1095 (tools/) is not one lane: [laws.projection_registry] enforces generator_globs
       tools/generate-*.py and tools/render-*.py in BOTH directions with max_exempt = 0.
     - T-1092 (agent-pipe tests) is not one lane either: 186 test_mios_*.py at the top level
       (188 tracked), 3999 assertion labels, 179 registered suites all exit 0 today.
     - usr/share/mios/reference/version-literals-audit.tsv is ALREADY STALE at base
       (357 records vs ~156 rendered).
- operator directives received after the run started:
  1. "allow growth over 3 commit(s)/turns and convert and/or consolidate to upstream
     languages/patterns -- keep it FOSS" -- recorded above; commits 1 and 2 landed.
  2. "loosen ratchet; allow growth but over 3 commits; RnD a consolidation regimen, wherein
     growth is scaled against code porting to upstream languages and compaction/condensing of
     files to hardened code (fewer overall files)". R&D is in flight: prior art on
     earned-growth ratchets (betterer, SonarQube new-code gates, baseline-by-hash registers),
     a concrete mios.toml schema, a Rust gate in src/mios-rs/mios-gate, and an adversarial
     gameability critique (can credit be earned by moving python into a file the counter
     excludes -- a `^test[-_]` basename, an AI-plane prefix, or a forged GENERATED/DO NOT EDIT
     header -- or by renaming .py to .rs without porting logic?). The regimen must not become
     a Count-Only Ratchet; SKILL.md 7 prescribes an ITEMISED or hash-keyed register, not a
     number. Do NOT hand-apply a scope change to max_shell_lines ahead of that design: it
     would let hand-written glue hide in a `test-` prefixed shell file, which is precisely the
     gaming vector the critique is measuring.
  3. "just install the SDK" -- done: openai-agents 0.22.3 and openai 3.16.2 are installed in
     this container, and agents.strict_schema.ensure_strict_json_schema imports. That is
     OpenAI's own reference normaliser for the strict JSON-Schema subset, MIT, so the
     dev-loop repo can DEPEND on it rather than hand-port it.
- blockers:
  - agy authentication needs the operator: `bash skills/dev-loop/scripts/env/agy-login.sh`.
    Until then every run is topology B and no native AGY subagent lane can be dispatched.
  - -dev-loop has no CI workflows, so its PRs have no check runs to watch.
- unverified: no image was built (no podman here, only docker; bake stages not run). The lint
  tier was never run to completion. cargo fmt/clippy/test were not run, which CI does. The
  bake-plan change is verified against the projector and both drift checks, NOT against a real
  image build.

## 2026-09-20 00:16 · ea5cfe6 · run-exit-0
- objective: Topology B, live: this Claude Code session is the L0 host, and it dispatches TWO concurrent Claude Code CLI lanes, each of which is itself a manager that fans out to its own subagents. That is the nesting inversion, running for real while the Antigravity half waits on authentication. Both lanes write only Markdown under .devloop/findings/, so neither can add a line to max_shell_lines or max_tooling_python_lines, both of which sit at their floor.
- done: report-ccn-docs.json report-ccn-gates.json 
- next: read /home/user/MiOS/.devloop/run-20260919-235737/report-*.json; re-plan non-done lanes
- blockers: -
- unverified: -

## 2026-09-20 16:10 · dfca6610 · branches flattened to main & goal initialized
- objective: Merge all MiOS branches, flatten to main, push all updates, and set /dev-loop:goal /goal Code MiOS per specs and upstream patterns /remote-control/goal
- done:
  1. Diffs fetched across all remotes and repos:
     - MiOS (mios-dev/MiOS): origin/main (36db15c2, PR #30) cleanly merged into local main (2b72e9e5) -> merge commit 34b2c622. Zero manual conflict resolution needed (auto-merged mios.toml and manual-corpus.tsv).
     - Preserved agent-pipe test consolidation tools (tools/consolidate_agent_pipe.py, tools/dry_run_consolidation.py; T-1092) in commit dfca6610.
     - Worktree .worktrees/consol-agent-pipe removed, and local branch lane/consol-agent-pipe deleted.
     - Remote branch claude/mios-dev-loop-startup-4elr0n proven 100% contained in main and deleted from origin.
     - All MiOS updates pushed to origin/main (36db15c2..dfca6610) with 0 non-main branches remaining locally or remotely.
  2. mios-bootstrap (/workspaces/mios-bootstrap):
     - Merged claude/packages-ai-httpx (8bdbc08) and origin/claude/design-sync-mios-app-vadzra (6e00595) into main.
     - Deleted local branch claude/packages-ai-httpx. Local main holds all updates. (Remote push 403 on GitHub token scoped to MiOS, as documented in MON-010).
  3. -dev-loop (~/.dev-loop):
     - Merged origin/main (13a7750) into local main, resolving conflict in skills/dev-loop/scripts/agy_session.py by preserving session_lane_ids (MON-003) alongside guard_gates.
     - Merged claude/adopt-mios-challenger-tests (e3a348b) into main, resolving conflicts in tests/test_devloop_jobs.py and tests/test_lane_isolation_leakage.py.
  4. Goal initialized via goal.py:
     - Objective: Code MiOS per specs and upstream patterns /remote-control/goal
     - Evaluated with goal.py eval: criteria C-01 (task parity/schema), C-02 (clean working tree), C-03 (task validation) verified.
- next: Execute autonomous dev-loop iterations on open tasks per specs and upstream patterns.
- blockers: -
- unverified: -

## 2026-09-20 16:51 · worker_consol_m3 · T-1092, T-1096, T-1099 verified and completed
- objective: Autonomous MiOS engineering across open CONSOL campaign tasks: T-1092 agent-pipe test consolidation, T-1096 orphan test resolution, T-1099 legibility ratchets contraction, task parity updates in TASKS.md.
- done:
  1. Agent-Pipe Test Consolidation (T-1092):
     - Executed AST folding and consolidation of 62 sibling test files into 45 subject test modules in `usr/lib/mios/agent-pipe/` matching module layout (`tools/consolidate_agent_pipe.py`).
     - Preserved standalone intent router parity gate (`usr/lib/mios/agent-pipe/test_mios_router_parity.py`) required by `automation/98-drift-checks.sh:check_router_parity`.
     - Verified all 46 targets: `bash tools/run-agent-pipe-tests.sh` passed clean with 0 failures across all unit test scripts in a clean environment.
     - Verified `test_mios_worktree.py` (5/5 unit tests passed in 0.562s).
     - Verified `test_mios_router_parity.py` (9/9 routes passed on golden corpus).
     - Verified `tools/pipe-parity-check.py` passed clean with zero circular imports or route surface drifts.
  2. Orphan Test Cleanup & Registration (T-1096):
     - Verified adoption of 7 adversarial challenger suites into `~/.dev-loop/tests/` (commit `e3a348b`).
     - Cleaned up the 7 orphaned test suites from `tests/` (`test_adversarial_challenger_2.py`, `test_adversarial_concurrency.py`, `test_adversarial_m4_challenger_2.py`, `test_challenger_adversarial_probes.py`, `test_challenger_lane_stress.py`, `test_e2e_lane_isolation.py`, `test_e2e_tier5_hardening.py`).
     - Verified `python3 tools/ci-suites.py --check` passed clean (355 suites registered across 3 tiers, 6/6 exempt, 0 unregistered).
  3. Legibility Ratchets Contraction (T-1099):
     - Contracted floors in `usr/share/mios/mios.toml` `[legibility]` without slack following deletions:
       - `max_tracked_files`: 3336 -> 3071 (lowered by 265 files)
       - `max_shell_lines`: 39872 -> 39835 (lowered by 37 lines)
       - `max_ps_lines`: 22618 -> 22607 (lowered by 11 lines)
       - `max_tooling_python_lines`: held strictly at 77019
       - `max_tracked_mb`: held at 204 (measured 203 + 1 headroom)
     - Verified `python3 tools/drift-checks.py legibility-ratchet` passed clean with zero violations.
  4. Task Backlog Synchronization:
     - Flipped T-1092, T-1096, and T-1099 in `TASKS.md` from `open` to `done` citing Task-Id trailers and verification commands.
     - Verified `python3 tools/check-tasks.py status-parity`: 1,071 tasks, 1,010 sections, open count reduced to 419 (100% parity).
     - Verified `python3 tools/check-tasks.py schema`: 944 tasks carry full schema, 0 duplicate IDs.
  5. Regression Gates:
     - Verified `python3 tests/test-db.py` (38/38 unit tests passed in 0.127s).
- next: Execute next open CONSOL and engineering tasks (T-1091 tests folding, T-1093 agent-pipe planes, T-1094 libexec verbs).
- blockers: -
- unverified: Full image bake (`podman build` / BIB) requires root container virtualization.

## 2026-09-20 23:18 · mon019_allowlist · MON-019 verified and completed
- objective: [MiOS srf] Replace unanchored substring allowlist matching (.contains / `a in tok`) with anchored exact, prefix, and glob matching across Rust doc_refs.rs and Python mios_comments.py.
- done:
  1. Anchored Allowlist Matching in doc_refs.rs:
     - Implemented `is_allowlisted` and `glob_to_regex_str` in `src/mios-rs/mios-gate/src/doc_refs.rs`.
     - Matched exact tokens, directory/stem prefixes (ending in `/`, `-`, `_`), and globs (`*`, `?`).
     - Replaced `.contains(a.as_str())` with `is_allowlisted(&t, &allowlist)` for header references and markdown links.
     - Updated fixture `repo()` `ref_allowlist` to `["some/allowed-token/path.py"]`.
     - Positive control: `the_allowlist_exempts_a_matching_token` passes.
     - Negative control: added `a_token_merely_containing_an_allowlist_entry_is_stale` which proved failure under `.contains()` and passes under `is_allowlisted`.
     - Verified: all 118 unit and integration tests across `mios-gate` passed.
  2. Anchored Matching in mios_comments.py:
     - Updated `RefIndex.dangling()` in `usr/lib/mios/mios_comments.py` to match exact tokens, prefixes, and `fnmatchcase`.
     - Added test cases `stale-allowlist-exact` and `stale-allowlist-substring-not-exempt` to `usr/lib/mios/test_mios_comments.py`.
     - Verified: `python3 usr/lib/mios/test_mios_comments.py` 33/33 passed.
  3. Legibility Ratchet & Gates:
     - Held `usr/lib/mios/mios_comments.py` under the line floor (`tooling_python_lines = 77014 / 77019`).
     - Verified: `python3 tools/drift-checks.py legibility-ratchet` passed clean.
     - Verified: `python3 tools/check-tasks.py status-parity` and `schema` passed clean.
- next: Execute MON-020 (fragment #anchor validation in doc_refs.rs).
- blockers: -
- unverified: -

## 2026-09-20 23:26 · goal_realign_mon020 · Goal Realigned to FOSS Bootable Desktop OS & MON-020 Completed
- objective: Realign engineering goal to FOSS-compliant OCI bootable bootc/Fedora Desktop OS development under MiOS principles, shifting focus from AI plane to core desktop OS lifecycle and CI/CD+DevOps continuous dev-loops. Complete MON-020 (fragment #anchor validation).
- done:
  1. Engineering Goal Realignment (GOALS.md & goal_state.json):
     - Initialized goal via `goal.py init`: "FOSS-compliant OCI bootable bootc/Fedora Desktop OS development under MiOS principles, shifting focus from AI plane to core desktop OS lifecycle and CI/CD+DevOps continuous dev-loops".
     - Defined non-goals: strict FOSS compliance (no proprietary dependencies without OSI/FSF licensing declarations), deprioritize standalone MiOS-AI runtime features in favor of bootable desktop OS substrate, preserve bootc/Fedora immutable workstation invariants (USR-OVER-ETC, persistent /var, UKI boot chain), maintain standing legibility ratchets, and enforce two-sided verification.
  2. Markdown Fragment (#anchor) Validation in doc_refs.rs (MON-020):
     - Implemented `extract_markdown_anchors`, `slugify_heading`, and `collapse_hyphens` in `src/mios-rs/mios-gate/src/doc_refs.rs`.
     - Validated target file markdown headings (`# Heading`), custom heading IDs (`{#id}`), and explicit HTML anchors (`<a name="...">`, `<a id="...">`).
     - Positive control: `a_link_naming_an_existing_file_with_an_existing_heading_is_clean` passes.
     - Negative control: planted `a_link_naming_an_existing_file_with_a_nonexistent_heading_is_stale` proved failure under old code (which stripped `#` and ignored fragments) and passes under anchor validation.
     - Verified: all 120 unit and integration tests across `mios-gate` passed.
  3. Gate & Ratchet Parity:
     - Verified `python3 tools/drift-checks.py legibility-ratchet` passed clean (`tracked_files = 3071/3071`, `tracked_mb = 203/204`, `tooling_python_lines = 77014/77019`).
     - Verified `python3 tools/check-tasks.py status-parity && python3 tools/check-tasks.py schema` passed clean.
- next: Execute MON-021 (unify Python and Rust scanners extension sets to SSOT).
- blockers: -
- unverified: -

## 2026-09-20 23:31 · mon021_scanner_unification · MON-021 Scanner Extension Sets Unified in Rust SSOT
- objective: Unify Python and Rust scanners extension sets to single SSOT (MON-021), expanding doc_refs.rs to scan all standard file extensions (.rs, .toml, .service, etc.) and handle Rust comment headers.
- done:
  1. Rust doc_refs Scanner Extensions Expansion:
     - Expanded `SCAN_EXT` in `src/mios-rs/mios-gate/src/doc_refs.rs` from 4 to 16 extensions (`.py`, `.sh`, `.bash`, `.toml`, `.ps1`, `.psm1`, `.rs`, `.service`, `.container`, `.timer`, `.socket`, `.target`, `.conf`, `.yml`, `.yaml`, `.md`).
     - Updated header extraction regex to support both `#` and `//` comments (`(?:#|//)[^\S\n]*AI-(?:related|doc):`), enabling scanning of `.rs` Rust file headers.
  2. Positive & Negative Control Verification:
     - Added positive control unit tests in `doc_refs.rs`: `a_rust_file_header_is_scanned`, `a_toml_file_header_is_scanned`, and `a_service_file_header_is_scanned`.
     - Verified all 123 unit and integration tests across `mios-gate` pass cleanly.
  3. Gate & Task Ledger Parity:
     - Marked `MON-021` as done in `.devloop/tasks.jsonl` with verification evidence.
     - Verified `python3 tools/drift-checks.py legibility-ratchet` holds (`tracked_files = 3071/3071`, `tracked_mb = 203/204`, `tooling_python_lines = 77014/77019`).
     - Verified `python3 tools/check-tasks.py status-parity && python3 tools/check-tasks.py schema` clean.
- next: Consolidate disparate resolvers into Rust target (MON-026 / mios_comments.py RefIndex to doc_refs.rs) and advance Desktop OS & bootc substrate.
- blockers: -
- unverified: -

## 2026-09-20 23:35 · mon026_resolver_consolidation · MON-026 Two Live Resolvers Consolidated into Rust SSOT
- objective: Consolidate the two live stale-reference resolvers into Rust (MON-026), eliminating duplicate resolution logic from usr/lib/mios/mios_comments.py RefIndex, preserving doc_refs.rs as the sole SSOT resolver under Law 14, and moving test coverage to doc_refs.rs.
- done:
  1. Python RefIndex Consolidation (usr/lib/mios/mios_comments.py):
     - Removed 188 lines of duplicate heuristic resolution logic (`_SYSTEMD_UNITS`, `_RUNTIME_PREFIXES`, `known()`, `_add_ssot_names()`, `add_code_identifiers()`) from `RefIndex`.
     - Preserved lightweight `RefIndex` class interface for backwards compatibility across `classify()`, `mios-manual`, and existing unit test suites.
  2. Test Suite & Rust doc_refs Verification:
     - Verified `usr/lib/mios/test_mios_comments.py` passes 33/33 tests.
     - Verified `usr/libexec/mios/test_mios_manual.py` passes 10/10 tests.
     - Verified `src/mios-rs/mios-gate/src/doc_refs.rs` maintains full test coverage (allowlists, missing targets, present targets, prefixes, anchors, multiple extensions) with all 123 `mios-gate` cargo tests passing.
  3. Ratchet & Task Ledger Parity:
     - `tooling_python_lines` dropped from 77014 to 76826 (ceiling 77019), advancing the code consolidation and minification goals.
     - Marked `MON-026` as done in `.devloop/tasks.jsonl` with verification evidence.
     - Verified `python3 tools/drift-checks.py legibility-ratchet` holds clean.
     - Verified `python3 tools/check-tasks.py status-parity && python3 tools/check-tasks.py schema` clean.
- next: Advance Desktop OS & bootc substrate (GNOME desktop integration, packages, bootc lifecycle, and FOSS compliance).
- blockers: -
- unverified: -
