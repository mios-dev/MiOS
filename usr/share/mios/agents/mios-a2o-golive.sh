#!/usr/bin/env bash
# One command for the OPERATOR to actuate the four human-gated A2O switches.
# You run this — Claude cannot (auto-mode classifier + Architectural Laws reserve
# these for the human): it builds+launches the super-container, opens the
# Gemini(agy) login, and prints how to enable the auto-approve operator and bake
# Phase-B into the immutable image.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

echo "== [1/4] build + launch mios-agents super-container =="
bash "$here/mios-agents-dev.sh"

echo
echo "== [2/4] Gemini(agy) login — complete the Google sign-in, then quit (Ctrl-C) =="
podman exec -it mios-agents-dev agy || true

echo
echo "== [3/4] auto-approve operator (optional) =="
echo "   Dispatch with AUTO on so the operator runs tools unattended (safe: confined to the container):"
echo "     echo 'PROMPT' | podman exec -i -e MIOS_A2O_AUTO=1 mios-agents-dev mios-a2o dispatch task1 agy /mnt/mios-root"

echo
echo "== [4/4] bake Phase-B into the immutable image =="
echo "   Follow usr/share/mios/agents/ACTIVATION.md (mios.toml stanza + bound-images), then: just build"

echo
echo "== smoke-test the live Gemini operator now =="
echo "   echo 'List the 5 largest files under /mnt/mios-root/usr and explain each' \\"
echo "     | podman exec -i mios-agents-dev mios-a2o dispatch smoke agy /mnt/mios-root"
echo "   podman exec -it mios-agents-dev mios-a2o status"
echo "   podman exec -it mios-agents-dev mios-a2o tail smoke"
