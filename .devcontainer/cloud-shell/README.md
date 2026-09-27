<!-- AI-hint: How to install and launch the portable MiOS Dev Container from Google Cloud Shell and Oracle Cloud Shell, which do not apply devcontainer.json on their own. -->
# MiOS Cloud Shell bootstrap

GitHub Codespaces automatically consumes `.devcontainer/devcontainer.json` and
runs its lifecycle commands. Google Cloud Shell and Oracle Cloud Shell do not
automatically apply a repository Dev Container configuration when a repository
is opened, so install the portable launcher once from the MiOS checkout:

```bash
bash .devcontainer/cloud-shell/bootstrap.sh install
```

Open a new shell, then run:

```bash
mios-cloud-shell up
```

The launcher installs `@devcontainers/cli` beneath persistent
`$HOME/.local`. On Oracle Cloud Shell it starts the rootless Podman API socket
and exposes it through `DOCKER_HOST` for the Dev Containers CLI. On Google
Cloud Shell it uses the preinstalled Docker engine. Both routes select the
portable `.devcontainer/devcontainer.json` profile.

Use the privileged `.devcontainer/artifact-builder/devcontainer.json` only on
a trusted, self-managed builder host. Cloud Shell providers do not promise the
privileges needed for `bootc-image-builder` disk artifacts.
