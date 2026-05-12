#!/usr/bin/env bash
# /usr/libexec/mios/mios-forgejo-runner-firstboot.sh
#
# Run `forgejo-runner register` once so /srv/mios/forge-runner/.runner
# exists before mios-forgejo-runner.service starts the daemon. v7+ no
# longer auto-registers from FORGEJO_RUNNER_REGISTRATION_TOKEN env --
# the daemon subcommand strictly requires .runner on disk.
#
# Idempotent: if .runner already present, exit 0 immediately.
set -euo pipefail

SENTINEL=/srv/mios/forge-runner/.runner
TOKEN_FILE=/etc/mios/forge/runner-token

if [[ -f "$SENTINEL" ]]; then
    echo "[runner-firstboot] $SENTINEL present; nothing to do"
    exit 0
fi

if [[ ! -r "$TOKEN_FILE" ]]; then
    echo "[runner-firstboot] $TOKEN_FILE missing; mios-forge-firstboot must run first"
    exit 0
fi

# shellcheck source=/dev/null
. "$TOKEN_FILE"

if [[ -z "${FORGEJO_RUNNER_REGISTRATION_TOKEN:-}" ]]; then
    echo "[runner-firstboot] token empty; cannot register"
    exit 0
fi

INSTANCE_URL="${FORGEJO_INSTANCE_URL:-http://localhost:3000/}"
RUNNER_NAME="${FORGEJO_RUNNER_NAME:-mios-self-hosted}"
RUNNER_LABELS="${FORGEJO_RUNNER_LABELS:-mios-self-hosted,podman,bootc,fedora-44}"
RUNNER_IMAGE="${MIOS_FORGE_RUNNER_IMAGE:-code.forgejo.org/forgejo/runner:7}"

install -d -m 0750 -o root -g root /srv/mios/forge-runner

echo "[runner-firstboot] registering $RUNNER_NAME against $INSTANCE_URL"
# --user 0:0 so the in-container forgejo-runner can write
# /data/.runner. The host /srv/mios/forge-runner is root-owned
# (Law-6 exception alongside ceph + k3s), and the daemon Quadlet
# also runs User=0, so root-owned .runner is the consistent
# ownership across register + daemon. Without --user 0:0 the
# image's default uid 1000 hits "permission denied" on the
# .runner write.
podman run --rm \
    -v /srv/mios/forge-runner:/data:Z \
    --network host \
    --user 0:0 \
    --entrypoint /bin/forgejo-runner \
    "$RUNNER_IMAGE" \
    register --no-interactive \
    --token "$FORGEJO_RUNNER_REGISTRATION_TOKEN" \
    --instance "$INSTANCE_URL" \
    --name "$RUNNER_NAME" \
    --labels "$RUNNER_LABELS"

if [[ -f "$SENTINEL" ]]; then
    echo "[runner-firstboot] registered; sentinel at $SENTINEL"
else
    echo "[runner-firstboot] register call returned 0 but $SENTINEL missing"
    exit 1
fi
