# MiOS standing goal

Operator objective (verbatim, 2026-10-07; re-anchored 2026-10-08):

> port all platforms shell scripts to rust static binaries for both linux and windows for MiOS;
> code and target containerfile(s) feed from SSOT--edited from mios.html--renders selections from
> file--overlays MiOS git root to root FHS--irm|iex web invoke bootstrap; monitor, debug,
> code--reinstall--ALL until MIOS IS COMPLETED ON CODE AND BOOTSTRAPS/INSTALLS/BUILDS/AND CAN SELF
> HOST/SELF BUILD--all required dependencies, packages etc-etc render from a user defined SSOT FILE

Amendment (operator, 2026-10-08): fold everything into **static Rust binaries** and **minimize the
number of disparate binaries**. Organize code as a few larger **MiOS-MODULES** (multi-call binaries
that own a whole domain) for a more controlled environment. Minimize global directories: prefer
**shallow trees** from MiOS's `.git`/ROOT.

A command finishing is not completion. Each condition below needs a positive control (the check
passes on the real tree or system) and a negative control (a planted defect makes it fail).

## Stopping conditions

| ID | Condition | Evidence that closes it |
|----|-----------|-------------------------|
| SC-1 | **No scripts on product paths.** Every build, install, runtime and bootstrap path runs a static Rust binary. Shell, PowerShell and Python survive only as declared thin shims or as AI-plane model or runtime bindings. Both are listed in a shrink-only SSOT register. | Register count is 0 outside the allowed classes; a drift gate fails on any new unregistered script |
| SC-2 | **Few, static binaries.** Linux artifacts are fully static. Windows artifacts link the CRT statically. Functionality is grouped into MiOS-MODULES (multi-call binaries) rather than one binary per tool. | Static-linkage audit is green for both targets; binary count ≤ an SSOT ceiling that only goes down |
| SC-3 | **SSOT renders everything.** Containerfiles, package sets, install, build, runtime and Windows/Linux variants all derive from layered `mios.toml` (vendor → host → user). | `mios-gen sync --root . && git diff --exit-code` clean; `miosd drift-check` reports PASS for every check with 0 FAIL and 0 MISSING |
| SC-4 | **mios.html is the editor.** Edits in `usr/share/mios/configurator/mios.html` round-trip losslessly into the user SSOT layer, and SSOT changes render back. | Round-trip test with a planted lossy edit (negative) |
| SC-5 | **Overlay.** The image overlays the MiOS git root onto `/` (FHS), and `/` remains a git work tree. | `git -C / status` works in an installed image; drift gates prove the overlay mapping |
| SC-6 | **Literal bootstrap.** Running `irm <Get-MiOS.ps1 URL> \| iex` on Windows performs the full install → build → runtime path with no manual step. | Executed run log, green end to end |
| SC-7 | **Self-host and self-build.** An installed MiOS rebuilds its own OCI image from its own SSOT, through `bootc container lint`. | `mios build` on MiOS reaches lint green |
| SC-8 | **CI green on both publishers.** drift-gate, build, smoke-test and CodeQL (no high or critical alerts) pass on `main`. | GitHub and Forgejo run URLs |
| SC-9 | **Shallow tree.** Fewer top-level entries and directories, and less depth, under the repo root. Each move is lossless, with every consumer updated and gates proving it. | The counts below decrease and never regress (ratchet) |

### Baseline (2026-10-08, PR #61 head + recovered work)
- tracked: 344 `.sh`, 73 `.ps1`/`.psm1`, 947 `.py`, 243 `.rs`
- `usr/{bin,libexec}` extensionless entrypoints: 125 shell, 157 Python
- Rust crates: 32 in `tools/native`, 6 in `src/mios-rs`; about 40 installed binaries
- tree: 3833 tracked files, 85 top-level entries, 668 directories, directory depth 9, file depth 10
  (deepest: `tools/mios-portal-app/app/src/main/java/io/mios/portal/`)
- drift: 15 checks MISSING (ports in progress)

## Milestones
- **M0, current:** recover Codex thread 01a116b2 (unified build console, native dashboard, Windows
  tmux profile, native drift checks) and push PR #61 with drift-gate green (0 MISSING) and the
  CodeQL highs fixed. Then merge to main per the operator's earlier authorization.
- **M1:** run the literal Windows `irm | iex` bootstrap through to a full SSOT-derived install and build (SC-6).
- **M2:** MiOS-MODULES consolidation plan. Map the ~40 binaries into domain modules (for example
  build, ssot or gen, gate or drift, runtime or agent, install), extending `miosd`'s multi-call pattern.
  Set the SSOT binary-count ceiling.
- **M3:** script-port burn-down by domain, ratcheted per SC-1.
- **M4:** mios.html ↔ SSOT round trip (SC-4).
- **M5:** self-build on installed MiOS (SC-7). Shallow-tree moves (SC-9) land throughout, never as one big rename.

## Non-goals and blast radius
- Do not rewrite history or force-push shared branches. Do not use `git add -A`; other agents share this tree.
- Do not touch other agents' worktrees or branches except to preserve and integrate their work.
- Do not delete legacy files without first proving they are unreferenced. "Dead" files have proven load-bearing before.
- Changes to shared SSOT surfaces must update both `mios.git` and `mios-bootstrap.git` (Law 15).
- Do not weaken a gate to make it pass. Honest red beats lying green.
