<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Configures the DOCKER_HOST environment variable to point to the Podman remote socket path, enabling Docker-compatible CLI tools and agents to interact with the container engine.
AI-related: mios-podman-ps.sh
shellcheck shell=bash
Export only when podman reports a path. Rootless podman cannot re-exec where
user namespaces are unavailable (a container inside a container), and an
unconditional substitution both printed that error on every login and
exported "unix://" -- an empty socket path a docker client fails on instead
of falling back to its own default.

<!-- mios-src:5ef41dcb9a80 from etc/profile.d/docker-host.sh:1-8 -->
