<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Forgejo CI workflow that automates the OCI image build via podman, tags it with version/timestamp/SHA, and triggers the host's bootc switch to stage the new image for the next boot.
AI-related: /etc/mios/install.env, mios-forgejo-runner, mios-bootc-switch, mios-self-hosted, mios-dev, mios-bootc-switch.service, localhost:3000
.forgejo/workflows/build-mios.yml
Self-replication loop: triggered by `git push http://localhost:3000/<admin>/mios`,
this workflow runs in the mios-forgejo-runner Quadlet, builds a new OCI
image via `podman build` against /Containerfile, and signals the host's
mios-bootc-switch.path watcher to stage the new image for next boot.

Privilege boundary:
  - Runner container (Privileged=true, documented exception): does
    `podman build` and writes the build-output sentinel.
  - Host (mios-bootc-switch.service triggered by mios-bootc-switch.path):
    reads the sentinel, runs `bootc switch --transport containers-storage`.
  - The runner has NO access to /usr/bin/bootc; the split is intentional.

Storage: the runner shares /var/lib/containers/storage with the host
(Volume= in the Quadlet). After `podman build` produces
`localhost/mios:latest`, the image is visible to host bootc directly.

<!-- mios-src:a58a0dbdcdd6 from .forgejo/workflows/build-mios.yml:1-18 -->

