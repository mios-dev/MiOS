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
podman run --rm \
    -v /srv/mios/forge-runner:/data:Z \
    --network host \
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
