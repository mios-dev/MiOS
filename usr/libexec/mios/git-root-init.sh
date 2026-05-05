#!/usr/bin/env bash
# /usr/libexec/mios/git-root-init.sh
#
# Initialize the deployed root `/` as a git working tree of the local
# Forgejo `mios.git` mirror. Runs once via mios-git-root-init.service
# after mios-forge-firstboot.service has created the admin user and
# the operator's mios.git repo on the local Forgejo instance.
#
# Architecture invariant (mios_root_git memory): the deployed `/` IS a
# git working tree. Operators edit files at FHS paths, `git commit`,
# push to localhost:3000, the Forgejo Runner builds a new OCI image,
# and `bootc switch` swaps to it on the next boot. Without /.git
# present, the loop is broken -- the operator can't `git diff /` to
# see what diverged from the deployed image.
#
# What this script does:
#   1. Skip if /.git already present (idempotent; sentinel-free).
#   2. Wait for the local Forgejo to respond on http://localhost:3000/
#      (up to 60s). Forgejo bootstrap can take 30-45s on first boot.
#   3. Probe whether the operator's mios.git repo exists at
#      http://localhost:3000/<user>/mios.git. If absent, skip and
#      log -- operator initializes via the Forgejo web UI or CLI.
#   4. `git -C / init -b main`
#   5. `git -C / remote add origin http://localhost:3000/<user>/mios.git`
#   6. `git -C / fetch origin main` -- pull the upstream tree.
#   7. `git -C / reset --soft FETCH_HEAD` -- adopt the FETCH_HEAD as
#      HEAD without touching the working tree (the deployed files
#      already match the image; `reset --soft` only updates the index
#      so `git status` shows no changes).
#
# After this runs, `git status` at / works, `git diff` shows operator
# edits since deploy, and `git push` against localhost:3000 triggers
# the Forgejo Runner build.

set -euo pipefail

# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh 2>/dev/null || true
: "${MIOS_VAR_DIR:=/var/lib/mios}"

_log() {
    logger -t mios-git-root-init "$*" 2>/dev/null || true
    echo "[git-root-init] $*" >&2
}

# Idempotent: /.git is the sentinel.
if [[ -d /.git ]]; then
    _log "/.git already present; nothing to do"
    exit 0
fi

# Resolve the operator's username (drives the Forgejo repo path).
MIOS_USER="${MIOS_USER:-mios}"
if [[ -r /etc/mios/install.env ]]; then
    # shellcheck disable=SC1091
    set -a; source /etc/mios/install.env 2>/dev/null || true; set +a
fi
MIOS_USER="${MIOS_USER:-mios}"

FORGE_URL="${MIOS_FORGE_URL:-http://localhost:3000}"
REPO_URL="${FORGE_URL}/${MIOS_USER}/mios.git"

# Wait for Forgejo to be up. mios-forge.service can take 30-45s for
# the first SQLite-DB write after a fresh container start.
_log "waiting for Forgejo at ${FORGE_URL} ..."
for _ in $(seq 1 60); do
    if curl -fsS --max-time 2 -o /dev/null "${FORGE_URL}/api/v1/version" 2>/dev/null; then
        _log "Forgejo reachable"
        break
    fi
    sleep 2
done
if ! curl -fsS --max-time 2 -o /dev/null "${FORGE_URL}/api/v1/version" 2>/dev/null; then
    _log "Forgejo never came up; skipping git-root-init"
    exit 0
fi

# Probe whether the mios.git repo exists. If not, the operator hasn't
# created it yet -- skip; they'll init via web UI / git push.
if ! curl -fsS --max-time 2 -o /dev/null "${REPO_URL}/info/refs?service=git-upload-pack" 2>/dev/null; then
    _log "${REPO_URL} not yet present; create it on Forgejo first, then re-run"
    exit 0
fi

# Init / as a git tree without disturbing the deployed working tree.
_log "git init / + remote add origin ${REPO_URL}"
git -C / init -b main
git -C / config core.fileMode false   # prevent perm-noise on read-only composefs
git -C / config core.autocrlf false
git -C / config user.email "${MIOS_USER}@$(hostname).local"
git -C / config user.name "${MIOS_USER}"
git -C / remote add origin "${REPO_URL}"

_log "fetching origin main ..."
if git -C / fetch --depth=1 origin main 2>&1 | logger -t mios-git-root-init; then
    # Adopt FETCH_HEAD as HEAD without rewriting the working tree.
    # `reset --soft` only moves the branch pointer + index; the on-disk
    # files (which already match the image build) stay put. `git status`
    # then shows whatever the operator has edited since deploy.
    git -C / reset --soft FETCH_HEAD
    _log "/.git initialized; HEAD = $(git -C / rev-parse HEAD)"
else
    _log "fetch failed; /.git left unset"
    exit 1
fi
