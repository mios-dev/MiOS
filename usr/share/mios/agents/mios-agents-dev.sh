#!/usr/bin/env bash
# Build + run the mios-agents DEV super-container in MiOS-DEV (rootless podman).
# YOU run this — Claude does not live-launch. Creds are mounted from your host so
# agy/claude logins persist and are shared with the host.
set -euo pipefail
cd "$(dirname "$0")"
IMG=localhost/mios-agents:dev
NAME=mios-agents-dev
PORT="${MIOS_AGENTS_PORT:-8801}"          # browser IDE (8801 avoids mios-code-server:8800)
PASS="${MIOS_AGENTS_PASSWORD:-mios}"

echo ">> building $IMG"
podman build --network=host -t "$IMG" -f Containerfile .

echo ">> (re)starting $NAME on :$PORT"
podman rm -f "$NAME" 2>/dev/null || true

mounts=(-v /:/mnt/mios-root:rw,rslave)
[ -d "$HOME/.gemini" ]      && mounts+=(-v "$HOME/.gemini":/home/coder/.gemini:rw)
[ -d "$HOME/.claude" ]      && mounts+=(-v "$HOME/.claude":/home/coder/.claude:rw)
[ -f "$HOME/.claude.json" ] && mounts+=(-v "$HOME/.claude.json":/home/coder/.claude.json:rw)

podman run -d --name "$NAME" --userns=keep-id \
  -e PASSWORD="$PASS" \
  -p "$PORT:8080" \
  "${mounts[@]}" \
  -w /mnt/mios-root \
  "$IMG" \
  --bind-addr 0.0.0.0:8080 /mnt/mios-root

cat <<EOF

mios-agents-dev up.
  IDE:          http://localhost:$PORT   (password: $PASS)
  Gemini login: podman exec -it $NAME agy       # sign in to Antigravity/Gemini
  Claude login: podman exec -it $NAME claude    # sign in to Claude (if needed)
  Doctor:       podman exec -it $NAME mios-a2o doctor
  War room:     podman exec -it $NAME tmux attach -t mios-a2o
  Dispatch:     echo 'PROMPT' | podman exec -i $NAME mios-a2o dispatch demo agy
  Monitor:      podman exec -it $NAME mios-a2o status
EOF
