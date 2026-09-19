# -dev-loop Hardening Patch Series & Git Bundle

This directory contains the verified commits for `https://github.com/mios-dev/-dev-loop.git` to ensure all development progress is preserved in the main repository:

## Included Artifacts
1. **`dev-loop-hardening.bundle`**: Complete Git bundle containing commits `eeecc6a` and `7a373d9` on branch `feature/lane-isolation-concurrency-hardening`.
2. **`0001-fix-dev-loop-harden-worktree-isolation-base-tree-lea.patch`**: Commit `eeecc6a` (Strict worktree isolation, base tree leakage detection, index lock backoff & eviction, Claude Code CLI & AGY concurrency, and 12-test test suite).
3. **`0002-fix-adapters-fix-relative-worktree-parts-filtering-i.patch`**: Commit `7a373d9` (Fix relative worktree parts filtering in sentinel vacuous check).

## How to Apply to `-dev-loop` and Create PR

### Option A: From any machine with write access using the Git bundle
```bash
git clone https://github.com/mios-dev/-dev-loop.git
cd -dev-loop
git fetch /path/to/dev-loop-hardening.bundle HEAD:feature/lane-isolation-concurrency-hardening
git checkout feature/lane-isolation-concurrency-hardening
git push -u origin feature/lane-isolation-concurrency-hardening
```
Then open the PR:
https://github.com/mios-dev/-dev-loop/compare/main...feature/lane-isolation-concurrency-hardening

### Option B: Push directly from Codespace using a Personal Access Token (PAT)
```bash
git -C ~/.dev-loop push https://<PAT>@github.com/mios-dev/-dev-loop.git feature/lane-isolation-concurrency-hardening
```
Then visit https://github.com/mios-dev/-dev-loop/compare to open the Pull Request.

### Option C: Applying formatted patches
```bash
cd /path/to/-dev-loop
git checkout -b feature/lane-isolation-concurrency-hardening
git am /path/to/0001-*.patch
git am /path/to/0002-*.patch
git push -u origin feature/lane-isolation-concurrency-hardening
```
