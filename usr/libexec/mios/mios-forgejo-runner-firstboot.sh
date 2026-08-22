#!/usr/bin/env bash
# AI-hint: bash Run `forgejo-runner register` once so /srv/mios/forge-runner/.runner AI-related: /usr/libexec/mios/mios-forgejo-runner-fir...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_libexec_mios_mios_forgejo_runner_firstboot_sh.md
set -euo pipefail

SENTINEL=/srv/mios/forge-runner/.runner
TOKEN_FILE=/etc/mios/forge/runner-token

if command -v miosd >/dev/null 2>&1; then
    miosd build-if-missing forgejo-runner
fi

if [[ -f "$SENTINEL" ]]; then
    echo "[runner-firstboot] $SENTINEL present; nothing to do"
    exit 0
fi

if [[ ! -r "$TOKEN_FILE" ]]; then
    echo "[runner-firstboot] $TOKEN_FILE missing; mios-forge-firstboot must run first"
    exit 0
fi

. "$TOKEN_FILE"

if [[ -z "${FORGEJO_RUNNER_REGISTRATION_TOKEN:-}" ]]; then
    echo "[runner-firstboot] token empty; cannot register"
    exit 0
fi

INSTANCE_URL="${FORGEJO_INSTANCE_URL:-http://localhost:3000/}"
RUNNER_NAME="${FORGEJO_RUNNER_NAME:-mios-self-hosted}"
RUNNER_LABELS="${FORGEJO_RUNNER_LABELS:-mios-self-hosted,podman,bootc,fedora-${FEDORA_VERSION:-44}}"
RUNNER_IMAGE="${MIOS_FORGE_RUNNER_IMAGE:-code.forgejo.org/forgejo/runner:7}"

install -d -m 0750 -o root -g root /srv/mios/forge-runner

FORGE_NET=$(podman inspect mios-forge \
    --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null \
    | awk '{print $1}')
if [[ "$FORGE_NET" == "host" || -z "$FORGE_NET" ]]; then
    NET_ARG=(--network host)
else
    NET_ARG=(--network "$FORGE_NET")
fi
echo "[runner-firstboot] forge network: ${FORGE_NET:-host}; register net: ${NET_ARG[*]}"

echo "[runner-firstboot] registering $RUNNER_NAME against $INSTANCE_URL"
podman run --rm \
    -v /srv/mios/forge-runner:/data:Z \
    "${NET_ARG[@]}" \
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
