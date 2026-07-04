#!/usr/bin/env bash
# Build + run the mios-agents DEV war-room from THIS repo and bring mios-frontier
# online on :8801 in the target composition (Sonnet-5 orchestrator + Opus-4.8 /
# Gemini-Flash-3.5 lanes). YOU run this.
#
# WSL fact this encodes: a /mnt/c (drvfs/9p) bind-mount is NOT writable from inside
# a podman container (rootless OR rootful) -- the agents could read but never EDIT
# the repo. So the war-room works on a NATIVE ext4 replica (writable) synced to
# GitHub (origin). Seed once from the repo (captures uncommitted edits), then it is
# git-managed -- re-runs rebuild+restart WITHOUT clobbering the workspace.
set -euo pipefail
cd "$(dirname "$0")"                              # usr/share/mios/agents
REPO_SRC="$(cd ../../../.. && pwd)"               # repo root
IMG=localhost/mios-agents:dev
NAME=mios-agents-dev
PORT="${MIOS_AGENTS_PORT:-8800}"                  # IDE port (takes over the mios-agents endpoint)
PASS="${MIOS_AGENTS_PASSWORD:-mios}"
WORK="${MIOS_FRONTIER_WORKSPACE:-$HOME/MiOS}"     # NATIVE ext4 workspace (container-writable)

echo ">> build $IMG from the repo (rootful storage -- the run is rootful --network=host)"
sudo podman build --network=host -t "$IMG" -f Containerfile .

if [ ! -e "$WORK/.git" ]; then
  echo ">> seed native workspace $WORK from $REPO_SRC (one-time; includes uncommitted edits + git origin)"
  mkdir -p "$WORK"
  rsync -a \
    --exclude="__pycache__" --exclude="*.pyc" --exclude="node_modules" --exclude=".venv" \
    --exclude="output/" --exclude="*.tar" --exclude="*.tar.gz" --exclude="*.qcow2" \
    --exclude="*.iso" --exclude="*.vhdx" --exclude="*.raw" --exclude="*.wsl" \
    "$REPO_SRC"/ "$WORK"/
else
  echo ">> native workspace $WORK exists (git-managed) -- leaving its contents. Sync via mios-frontier-sync."
fi
# The container's coder maps to a uid != the workspace owner (WSL userns quirk);
# make the native workspace writable by any container uid (dev workspace).
chmod -R a+rwX "$WORK"

# Serve the IDE via ROOTFUL --network=host (rootless -p forwarding is unreliable
# under WSL, and --network=host conflicts with --userns=keep-id). Root also writes
# the native workspace cleanly. Stop the stale systemd service so it frees the port.
echo ">> (re)start $NAME on :$PORT (rootful --network=host)"
sudo systemctl stop mios-agents 2>/dev/null || true
sudo podman rm -f "$NAME" 2>/dev/null || true; podman rm -f "$NAME" 2>/dev/null || true
sudo chmod -R a+rwX "$WORK"
mounts=(-v "$WORK":/mnt/mios-root:rw)
[ -d "$HOME/.gemini" ]      && mounts+=(-v "$HOME/.gemini":/home/coder/.gemini:rw)
[ -d "$HOME/.claude" ]      && mounts+=(-v "$HOME/.claude":/home/coder/.claude:rw)
[ -f "$HOME/.claude.json" ] && mounts+=(-v "$HOME/.claude.json":/home/coder/.claude.json:rw)
sudo podman run -d --name "$NAME" --network=host -e PASSWORD="$PASS" \
  "${mounts[@]}" "$IMG" --bind-addr "0.0.0.0:$PORT" /mnt/mios-root

cat <<EOF

mios-agents-dev up -- war-room on a NATIVE writable workspace synced to GitHub.
  IDE:          http://localhost:$PORT   (password: $PASS)
  Workspace:    $WORK   (origin: $(git -C "$WORK" remote get-url origin 2>/dev/null || echo '?'))
  Gemini login: sudo podman exec -it $NAME agy
  Claude login: sudo podman exec -it $NAME claude
  Doctor:       sudo podman exec -it $NAME mios-a2o doctor
  WAR ROOM:     sudo podman exec -it $NAME mios-frontier
  Sync:         sudo podman exec -it $NAME mios-frontier-sync push|pull   (<-> GitHub origin)
EOF
