<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### The push step sources tools/lib/userenv.sh, which defaults...

The push step sources tools/lib/userenv.sh, which defaults MIOS_VENDOR_TOML
to the ABSOLUTE /usr/share/mios/mios.toml -- on a self-hosted runner that
resolves the INSTALLED SSOT (or empty if MiOS isn't installed on the host),
NOT the checkout being built, so MIOS_IMAGE_NAME can come out empty/stale
and the push exits 1. Point it at the checked-out SSOT so it resolves the
version under build (parity with .github/workflows/mios-ci.yml).

<!-- mios-src:1328de9fd76a from .forgejo/workflows/build-mios.yml:17-22 -->

### Anonymous GHCR pulls hit "503 Egress is over the account...

Anonymous GHCR pulls hit "503 Egress is over the account limit"
mid-pull on big multi-layer base images like ublue-os/ucore-hci.
Authenticated pulls don't share the anonymous quota pool.
GHCR_USER + GHCR_TOKEN are already set in the runner's secret
store for the push step further down -- reusing them here costs
nothing and unblocks the FROM in Containerfile. Skipped silently
if the secrets aren't configured (build can still succeed if
GHCR's anonymous pool happens to have headroom that minute).

<!-- mios-src:9b1abfdb404e from .forgejo/workflows/build-mios.yml:132-139 -->

### Containerfile already runs `bootc container lint` as the...

Containerfile already runs `bootc container lint` as the final
build step (Architectural Law 4). This is a belt-and-suspenders
check: confirm the freshly-built image still carries the
required bootc labels before signaling the host watcher.

<!-- mios-src:147551906b1c from .forgejo/workflows/build-mios.yml:169-172 -->

### The host's mios-bootc-switch.path watches this file....

The host's mios-bootc-switch.path watches this file. Writing
the timestamp + image ref triggers mios-bootc-switch.service,
which validates the image exists in containers-storage and
runs `bootc switch --transport containers-storage <ref>`.
No reboot here; operator decides when to apply.

<!-- mios-src:c8be1fb9930b from .forgejo/workflows/build-mios.yml:188-192 -->
