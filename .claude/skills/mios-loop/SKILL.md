---
name: mios-loop
description: The MiOS working loop — upstream research, append roadmap/tasks, write instructions for every dev agent, implement, double-check, push, monitor CI, debug, repeat. Use when working on the MiOS repo (mios.git / mios-bootstrap.git) on ANY task: fixing CI, appending TASKS.md/ROADMAP.md/AGY-TASKS.md, editing mios.toml, running the drift-gate, compacting files, or porting to Rust. Carries the verification discipline, the house schemas, the environment traps and the standing operator directives so a fresh session works like an experienced one.
---

# The MiOS loop

You are working on **MiOS** — an immutable bootc/OCI Fedora workstation that is also a
self-hosted agentic AI OS. **The repo root IS the deployed system root**: `usr/`, `etc/`,
`srv/`, `var/` land at exactly those paths on a booted host. Editing a file here edits the OS.

Read `CLAUDE.md` and `AGENTS.md` at the repo root first — they carry the sixteen architectural
laws and the repo contract. This skill carries the *method*: how to work here without shipping
something broken or chasing a failure that was never real.

## The loop

1. **Research upstream** — targeted to what you are actually implementing or what CI is failing on.
2. **Append the roadmap and task lists** in the house schemas (below).
3. **Write instructions for the other dev agents** (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md` in
   *both* repos; `AGY-TASKS.md` for the Gemini lane).
4. **Implement.**
5. **Double-check** — see *Verify, don't believe*. This is the step that matters.
6. **Push**, then **monitor CI**, **debug**, and go back to 1.

**Ask the operator at every step.** Use `AskUserQuestion` whenever two readings would lead to
materially different work. The operator has repeatedly corrected architecture mid-flight, and
each correction was load-bearing — asking early is cheaper than rewriting a landed task.

## Verify, don't believe

The **#1 MiOS defect class is a check that is structurally incapable of failing.** Assume you
are about to add another one. Real examples, all found in-tree:

- `mios-unit-gen --check` printed PASS without comparing anything. Once repaired: 66/66 units drifted.
- A golden-master test diffed the tree against a *copy of itself*.
- `check_bake_ref_defaults` printed its **success line** on the skip path.
- A bake-smoke check iterated an empty list and printed OK.

**Rules that follow:**

- **Exit 0 is not proof.** A command killed by a timeout can still report success through a
  pipeline. After any generator or renderer, *spot-check the content* — not the exit code.
  (A corpus re-render once reported success while changing nothing; only comparing a file's
  claimed line numbers against the actual file caught it.)
- **A negative test must fail for the RIGHT reason.** Plant a violation, confirm the gate
  catches *that specific thing*, then remove it. A gate that fails for an unrelated reason is
  not evidence your fix works.
- **Counts and self-reports are not proof.** "N checks passed" says nothing about whether any
  of them could have failed.
- **Silence is not success.** If a monitor or filter would stay quiet through a crash, widen it.

## Is this failure even real? — the false-positive catalogue

Before fixing anything the local gate reports, rule these out. Each has cost a real session:

| Symptom | Cause | Test |
|---|---|---|
| A gate silently passes in a worktree | `.git` is a **FILE** in a linked worktree; guards written `[[ -d "$ROOT/.git" ]]` trip | `ls -la <root>/.git` — file or dir? Prefer `git -C "$ROOT" rev-parse --git-dir` |
| Lint flags a line the tree already fixed | It scanned a **stale temp copy** (e.g. a leftover `/tmp/miosci`) | `stat` the file it named; compare to the tree's actual content |
| SSOT-projection checks "drift" locally | The machine's **stale installed MiOS** is read by any check using absolute paths (`/usr`, `/etc`, `~/.config`) | Only trust `$ROOT`-relative checks locally; trust CI for projection checks |
| ~7 negatives fail "after restoration" | The gate was **already failing on the unmutated tree**; every post-restore re-run inherits it. The suite even warns "a later failure may be a consequence of an earlier one" | Fix the first real failure, then re-run |

**Trust locally:** negatives, gate-index, BIB, names-registry, shellcheck, resolver-twin.
**Trust CI for:** SSOT-projection (dotfiles/theme, ipa-enroll, uki-cmdline, cockpit, bake-plan).

## Environment traps (Windows host + WSL)

- **`cd /c/MiOS` on every Bash call.** The working directory does not reliably persist.
- **`$var` dies through two shells.** `wsl -d podman-MiOS-DEV -- bash -c '...$t...'` loses the
  variable in loops — it prints blanks and every branch looks OK, a *fake pass*. Put loops in a
  **script file**.
- **Git Bash rewrites `/mnt/...`** into `C:/Program Files/Git/mnt/...`. Use `MSYS_NO_PATHCONV=1`.
- **Windows Python can't open `/c/...` paths** — use `C:/...`.
- **Heredocs with heavy quoting break.** Write the payload to a scratch file, then splice it.
- **Builds run inside `podman-MiOS-DEV`, never on the Windows host.** Rust toolchain lives
  there (`cargo audit`/`cargo nextest` need a **login** shell — they're in `~/.cargo/bin`).
- There is **no `rustup` binary**; the RPM ships only `rustup-init`. CI's
  `rustup component add clippy rustfmt || true` works only because Fedora RPMs already provide them.

## House schemas — get these right or the gates reject you

**`TASKS.md`** — every task appears **twice** and a parity gate compares them:
- a table row: `| T-NNN | PN | status | Domain | Title |`
- a detail section: `## T-NNN -- Title (WS-X | PN | size)` with `**Goal:** **What+How:** **Where:**
  **Done When:** **Why:** **Dep:** **Status:** | **Domain:** | **Who:**`
- The table status and the detail `**Status:**` head token **must match**.
- Verify: `python3 tools/check-tasks-status-parity.py`

**`AGY-TASKS.md`** (the Gemini AGY lane) — ids ≥ `[tasks].schema_from` need **all** of:
`Goal, What+How, Where, Verify, Do NOT, Done When, Why, Dep`.
`Verify` must be an exact command whose failure is the proof. `Do NOT` names the dodge that
would satisfy the task falsely (raising a ceiling, editing an accepted-list).
Verify: `python3 tools/check-task-schema.py` and `tools/check-agy-tasks.py`

**`ROADMAP.md`** — each workstream carries an HTML-comment metadata block
(`id, title, theme, status, priority, laws, ssot_keys, adr, deps, acceptance`).
**`ssot_keys` must already exist in `mios.toml`** — the index gate rejects keys a task merely
*proposes* to create. Regenerate with `python3 tools/roadmap-index.py` (it is idempotent).

**`usr/share/mios/mios.toml`** — the SSOT. It has been truncated and pushed before, breaking CI.
**Always** verify after editing: line count changed by exactly what you intended, **and**
`tomllib.load()` parses it.

## Generated artefacts

Anything derived from the SSOT is drift-gated (Law 8). After changing source, run
`bash ./tools/sync-generated.sh` (~5 min) and commit what it regenerates.

**Adding or deleting a tracked file is itself a change to a generated artefact.** `ROADMAP.md`
carries a generated "Tracked files" count, so committing one new file without re-rendering
fails CI at the very first step. `python3 tools/roadmap-index.py` is the fast path when that
is all you changed.

**The manual corpus (`usr/share/mios/reference/manual-corpus.tsv`) indexes comment blocks by
LINE NUMBER**, across `.py`, `.rs`, `.toml` and more — but **not** `.md`. Reformatting *any*
source file invalidates it. This has broken CI twice. Never run `cargo fmt` or a bulk edit
while the corpus census is running.

It is **not** vestigial: `check_docs_ratchet` consumes its narrative verdicts and enforces a
ceiling (`[docs].max_unmigrated_narrative`), so the corpus is the input to a live gate, not a
ledger kept fresh for its own sake.

## Commit and push

- **Stage explicit paths. Never `git add -A`** — the tree is shared with the AGY agent.
- Never strip `@sha256` pins from generated Quadlets with a broad add.
- **Law 15 (DOUBLE-REPO-TRIPLE-CHECK):** check **both** `mios.git` and `mios-bootstrap.git`
  before changing a shared surface, and update both or justify the divergence.
- Commit messages are **prose that explains the reasoning and the evidence** — what was
  broken, how you know, why this fix and not the other one. Not a bullet list of files.
- Confirm before: `git push` (unless the operator has standing authorisation), `bootc switch`,
  `dnf install`, `rm -rf`, `git reset --hard`.

## Monitoring CI

Arm a persistent `Monitor` that emits on **every terminal state**, not just failure:

```
gh run list --workflow=mios-ci.yml --branch main --limit 6 --json databaseId,status,conclusion,displayTitle \
  --jq '.[] | select(.status=="completed") | "run \(.databaseId) \(.conclusion|ascii_upcase): \(.displayTitle[0:60])"'
```
Seed the snapshot first, then emit only *new* completions.

`mios-ci` tiers run in this order, and each one hides everything behind it:
`Generated artifacts match the SSOT` → `Static analysis` → `Behavioural suite` →
`Rust format, lint and tests` → `Drift-gate tier` → then `build` and `smoke-test`.
**The Rust step runs under `bash -e`**, so its first failing command hides the rest. Expect to fix one tier and immediately discover the next
had never run. Both Rust workspaces are checked: `src/mios-rs` **and** `tools/native`.

## Standing operator directives

- **Everything derives from `mios.toml`**, defined by the deploying operator. No hand-maintained
  or divergent config anywhere.
- **All ports and addresses FLOAT to SSOT.** There are **no** canonical port *values* — only
  canonical *keys*. Never write a port literal; never verify a port by its number.
- **Only the AI plane is Python.** Everything else becomes **minimal Rust binaries**, shaped as
  a **few multi-call binaries** (the `miosd` `argv[0]` pattern), not one per tool.
- **"Canned" = hardened templates** an AI generates the next tool *from* (Law 16), not merely a
  conformance gate.
- **Schemas are OpenAI format**, everywhere.
- **Naming is domain-then-function** — `net/route.py`, `storage/provision.py`. No redundant
  `mios_` prefix inside `usr/lib/mios/`.
- **"Lossless" means behaviour only — paths are free**, provided every consumer is fixed in the
  same change and the gates prove it.
- **Blades:** MiOS-Metal + MiOS-Edge + MiOS-KVM (PiKVM) are three Blades that exist inherently.
  Target the **minimum device count (1-2)** first — MiOS must deploy from a single source
  regardless. Hardware-facing roles live on the Blade and are unclaimable by a NIC-less guest.
- **Merge work properly:** real `git merge --no-ff` and `git branch -d`, never content-copy plus
  a force-delete. The graph must show the merge.

## When you find a defect

Prefer **fixing the cause** over registering the symptom. A drift register or an accepted-hazard
list exists to hold *deliberate* debt; putting a fresh defect in one converts a failing test
into a silent trap. The example to remember: a unit shipped with sandboxing its SSOT
declaration lacked, so the renderer would have *stripped* the hardening. Registering that drift
would have turned the gate green and left the trap armed.
