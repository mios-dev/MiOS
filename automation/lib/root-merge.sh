#!/usr/bin/env bash
# AI-hint: Canonical "Git = $ROOT" root-merge -- makes a target root ($MIOS_ROOT, default /) a
# first-class SELF-UPDATING git work tree of mios.git (git init + fetch + reset --hard FETCH_HEAD
# + upstream wiring so `git -C $ROOT pull` works on Day-N+). ONE implementation shared by the FHS
# bare-metal install (build-mios.sh Total Root Merge), the WSL dev-VM overlay (build-mios.ps1),
# and the OCI bake (where it is a no-op: the tree is already materialized at $ROOT). Idempotent;
# set -e safe; the caller decides the confirm-gate. This is the heart of the deploy unification.
# AI-functions: mios_root_merge
# AI-related: build-mios.sh, build-mios.ps1, automation/build.sh, automation/mios-apply, usr/lib/mios/userenv.sh
#
# Usage:   mios_root_merge <root> <repo-url-or-local-path> <branch>
#          "/ IS $ROOT": the deployed root becomes the SAME git tree the drift-gate resolves
#          ($ROOT = $(cd automation/.. ) = /), and it self-updates via `git -C $root pull`.
# Self-test:  bash automation/lib/root-merge.sh --selftest [tmpdir]   # merges this repo into a
#             throwaway root and asserts .git + tracked files + upstream wiring. Never touches /.

mios_root_merge() {
    local root="${1:-/}"
    local repo="${2:-}"
    local branch="${3:-main}"

    [[ -n "$root" ]] || { echo "[root-merge] FATAL: empty root" >&2; return 2; }
    [[ -n "$repo" ]] || { echo "[root-merge] FATAL: empty repo/source" >&2; return 2; }

    # A Windows-authored tree merged onto a Linux root: never rewrite line endings, and mark
    # the (root-owned) root a safe.directory so git 2.35+ does not refuse "dubious ownership".
    git config --global --add safe.directory "$root" 2>/dev/null || true
    git config --global --add safe.directory '*'      2>/dev/null || true

    # 1. Initialize <root> as a git work tree (idempotent). ${root%/}/.git resolves correctly
    #    for "/" (-> /.git) and for "/tmp/x" (-> /tmp/x/.git).
    if [[ ! -d "${root%/}/.git" ]]; then
        git init "$root" >/dev/null || { echo "[root-merge] FATAL: git init $root failed" >&2; return 1; }
    fi
    if git -C "$root" remote get-url origin >/dev/null 2>&1; then
        git -C "$root" remote set-url origin "$repo"
    else
        git -C "$root" remote add origin "$repo"
    fi
    git -C "$root" config core.autocrlf false 2>/dev/null || true

    # 2. Fetch the branch (shallow) + reset the work tree to it. `reset --hard` only touches
    #    TRACKED files, so untracked host state (/var, generated projections) survives.
    local fetch_err
    if ! fetch_err="$(git -C "$root" fetch --depth=1 origin "$branch" 2>&1)"; then
        echo "[root-merge] FATAL: fetch $branch from $repo failed: $fetch_err" >&2
        return 1
    fi
    if ! git -C "$root" reset --hard FETCH_HEAD >/dev/null 2>&1; then
        echo "[root-merge] FATAL: reset --hard FETCH_HEAD failed" >&2
        return 1
    fi

    # 3. "/ IS $ROOT": make it SELF-UPDATING. fetch+reset leaves HEAD on git-init's default
    #    branch with NO upstream, so a bare `git pull` errors "no tracking information".
    #    checkout -B (no working-tree change) + the two config lines wire the branch upstream
    #    so `git -C $root pull --ff-only` fast-forwards mios.git on Day-N+.
    git -C "$root" checkout -B "$branch" >/dev/null 2>&1 || true
    git -C "$root" config "branch.${branch}.remote" origin
    git -C "$root" config "branch.${branch}.merge"  "refs/heads/${branch}"

    # 4. Restore the executable bit on MiOS script trees. mios.git is authored on Windows where
    #    core.filemode is off, so a fresh checkout lands libexec/bin scripts 0644 -> systemd
    #    ExecStart 203/EXECs "Permission denied". Data files (py/json/yaml/md) stay untouched.
    if [[ -d "${root%/}/usr/libexec/mios" ]]; then
        chmod -R +x "${root%/}/usr/libexec/mios/" 2>/dev/null || true
    fi
    find "${root%/}/usr/lib/mios" -type f \( -name "*.sh" -o -name "mios-*" \) \
        ! -name "*.py" ! -name "*.json" ! -name "*.yaml" ! -name "*.md" \
        -exec chmod +x {} + 2>/dev/null || true
    find "${root%/}/usr/bin" "${root%/}/usr/local/bin" -maxdepth 1 -name "mios-*" -type f \
        -exec chmod +x {} + 2>/dev/null || true

    return 0
}

# Standalone self-test -- merges THIS repo (resolved from the script location) into a throwaway
# root, asserts the invariants, and cleans up. Never touches / and never pushes.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
      --selftest)
        set -uo pipefail
        _src_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # automation/lib/../.. = repo root
        _tmp="${2:-/tmp/mios-rootmerge-selftest.$$}"
        rm -rf "$_tmp"; mkdir -p "$_tmp"
        _branch="$(git -C "$_src_root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
        echo "[selftest] merge $_src_root/.git ($_branch) -> $_tmp"
        _ok=1
        mios_root_merge "$_tmp" "$_src_root/.git" "$_branch" || _ok=0
        echo "--- asserts ---"
        [[ -d "$_tmp/.git" ]]                  && echo "  OK   .git materialized"          || { echo "  FAIL no .git"; _ok=0; }
        [[ -f "$_tmp/automation/build.sh" ]]   && echo "  OK   tracked file present"       || { echo "  FAIL tracked file missing"; _ok=0; }
        _up="$(git -C "$_tmp" config --get "branch.${_branch}.remote" 2>/dev/null || true)"
        [[ "$_up" == "origin" ]]               && echo "  OK   upstream wired (git pull works)" || { echo "  FAIL upstream=$_up"; _ok=0; }
        _hd="$(git -C "$_tmp" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
        [[ "$_hd" == "$_branch" ]]             && echo "  OK   HEAD on $_branch"           || { echo "  FAIL HEAD=$_hd"; _ok=0; }
        rm -rf "$_tmp"
        [[ $_ok -eq 1 ]] && { echo "SELFTEST: PASS"; exit 0; } || { echo "SELFTEST: FAIL"; exit 1; }
        ;;
      *)
        echo "root-merge.sh is a sourced library. Run 'bash $0 --selftest' to self-test." >&2
        exit 2 ;;
    esac
fi
