# AI-hint: Configures the DOCKER_HOST environment variable to point to the Podman remote socket path, enabling Docker-compatible CLI tools and agents to interact with the container engine.
# AI-related: mios-podman-ps.sh
#
# Export DOCKER_HOST only when podman actually reports a socket path. This file
# is sourced by every login shell, and the podman call is not always going to
# succeed: rootless podman cannot re-exec where user namespaces are unavailable
# (a dev container or Codespace running inside another container), failing with
# "cannot clone: Operation not permitted" / "cannot re-exec process".
#
# An unconditional command substitution printed that error on every login AND
# exported DOCKER_HOST="unix://" -- a scheme with an empty socket path, which is
# worse than leaving it unset: a docker-compatible client takes it as
# configuration and fails on it instead of falling back to its own default.
if command -v podman >/dev/null 2>&1; then
    _mios_podman_socket=$(podman info -f '{{.Host.RemoteSocket.Path}}' 2>/dev/null) || _mios_podman_socket=""
    if [ -n "$_mios_podman_socket" ]; then
        DOCKER_HOST="unix://$_mios_podman_socket"
        export DOCKER_HOST
    fi
    unset _mios_podman_socket
fi
