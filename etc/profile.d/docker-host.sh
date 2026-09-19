# AI-hint: Configures the DOCKER_HOST environment variable to point to the Podman remote socket path, enabling Docker-compatible CLI tools and agents to interact with the container engine.
# AI-related: mios-podman-ps.sh
# shellcheck shell=bash
# Export only when podman reports a path. Rootless podman cannot re-exec where
# user namespaces are unavailable (a container inside a container), and an
# unconditional substitution both printed that error on every login and
# exported "unix://" -- an empty socket path a docker client fails on instead
# of falling back to its own default.
if command -v podman >/dev/null 2>&1; then
    _mios_sock=$(podman info -f '{{.Host.RemoteSocket.Path}}' 2>/dev/null) || _mios_sock=""
    [ -n "$_mios_sock" ] && export DOCKER_HOST="unix://$_mios_sock"
    unset _mios_sock
fi
