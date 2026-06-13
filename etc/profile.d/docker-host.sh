# AI-hint: Configures the DOCKER_HOST environment variable to point to the Podman remote socket path, enabling Docker-compatible CLI tools and agents to interact with the container engine.
export DOCKER_HOST="unix://$(podman info -f "{{.Host.RemoteSocket.Path}}")"
