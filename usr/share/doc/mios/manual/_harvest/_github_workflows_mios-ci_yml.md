<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### In-repo build

In-repo build: MiOS owns the Containerfile and Justfile, so CI builds
straight from the repository tree -- no cross-repo fetch.

Parity with .forgejo/workflows/build-mios.yml: both pipelines use
`podman build` (NOT docker/build-push-action) so the OCI manifests,
layer digests, labels, and provenance match bit-for-bit between the
self-hosted Forgejo Runner closure and the GitHub Actions cloud
closure. An operator pulling ghcr.io/mios-dev/mios:latest gets the
same image whether the runner was forgejo-side or github-side.

<!-- mios-src:dc685a024553 from .github/workflows/mios-ci.yml:5-13 -->

### GitHub Actions and the self-hosted Forgejo runner are...

GitHub Actions and the self-hosted Forgejo runner are EQUAL, bit-for-bit
build/publish environments (build LOCAL-first on MiOS-DEV; default registry is
GHCR when credentials are present, else the local/Forgejo registry). PUBLISH
gates whether THIS (GitHub) runner also BAKES the bound images + pushes/signs.
It is 'false' ONLY because a standard ubuntu-24.04 runner (~66GB /mnt) cannot
yet hold the ~60GB baked store -- a CAPACITY gate, NOT a demotion of GitHub.
While false, GitHub still fully build+lint validates; the baked image is
produced by a runner that CAN bake (local MiOS-DEV, or the 707GB Forgejo
runner, .forgejo/workflows/build-mios.yml) and published to the default
registry. Flip to 'true' once a GitHub runner can hold the full image (a
large-disk runner, or after the MiOS-Sys consolidation shrinks the bake) so
GitHub bakes + pushes + signs as a full equal.

ENABLED: the ~47GB GPU-engine whales (vLLM ~25GB + SGLang ~22GB)
are now the FIRSTBOOT tier (mios.toml [build.bake].firstboot_tokens) --
evicted from the bake (generate-bake-plan.py -> plan.d/firstboot.list) and
pulled at first boot, not baked. That drops peak build disk from ~60GB to
~20-25GB, which fits a standard ubuntu-24.04 runner, so GitHub now bakes the
core AI + service images, rechunks, pushes, and cosign-signs as a full equal.

<!-- mios-src:c90f747b0a61 from .github/workflows/mios-ci.yml:30-48 -->

### The agent-pipe runtime deps ship in the baked image's agent...

The agent-pipe runtime deps ship in the baked image's agent venv, but
the drift-gate runs BEFORE the OCI bake so there is no venv here. The
module shims resolve mios_* -> mios_pipe.* which import fastapi/httpx at
module load; install those light, pip-resolvable deps so the hermetic
logic tests can import. The build job re-runs the FULL suite in the venv.
ubuntu-24.04's system python is PEP-668 externally-managed, so a plain
pip install errors; fall back to --break-system-packages on the
ephemeral runner. Best-effort (|| true): a missing dep just re-surfaces
as a test import error below, not a silent skip.

<!-- mios-src:6b7280f004e5 from .github/workflows/mios-ci.yml:196-204 -->

### Skip tests that cannot run in a fast, DB-less, venv-less...

Skip tests that cannot run in a fast, DB-less, venv-less drift-gate:
  * live-pgvector DB-integration (config_audit/redact/vector) -- mirrors
    the automation/build.sh _DB_INTEGRATION_TESTS skip.
  * a heavy agent dep not installed in the fast gate (smolagents ->
    gateway_agent/gateway_queue/admission; the mcp SDK -> mcp_pool).
  * an executable bit git does not preserve on the runner
    (bench_harness spawns /usr/libexec/mios/mios-bench).
ALL of these are exercised in the venv-backed build-job test gate.

<!-- mios-src:9084b8acca81 from .github/workflows/mios-ci.yml:208-215 -->

### The publish steps (compute-tags / login) source...

The publish steps (compute-tags / login) source tools/lib/userenv.sh, which
defaults MIOS_VENDOR_TOML to the ABSOLUTE /usr/share/mios/mios.toml -- a path
that exists only INSIDE the built image, never on the runner host. Without
this, MIOS_IMAGE_NAME resolves empty and those steps `exit 1`
("MIOS_IMAGE_NAME is empty"), failing the first PUBLISH=true run at push.
Point it at the checked-out SSOT so it resolves ghcr.io/mios-dev/mios. Host-
side only -- the in-container build sets its own MIOS_TOML (Containerfile).

<!-- mios-src:0e4256b66c2a from .github/workflows/mios-ci.yml:255-261 -->

### runroot + graphroot are REQUIRED (a [storage] table with...

runroot + graphroot are REQUIRED (a [storage] table with only `driver`
makes `podman system reset` abort with "runroot must be set"). Put
graphroot on /mnt -- the GHA runner's LARGE ephemeral disk (~65GB+
free) vs / (~21GB even after jlumbroso frees ~30GB). The MiOS image
bakes 21 large bound-images (~50GB incl AI lanes); committing that
layer on / exhausts the disk and the layer copy's pipe closes ("io:
read/write on closed pipe", exit 125,). runroot stays on
tmpfs /run (small runtime state only). install-robustness.

<!-- mios-src:9565dcccef24 from .github/workflows/mios-ci.yml:307-314 -->

### The GHA runner ships a pre-seeded containers store whose...

The GHA runner ships a pre-seeded containers store whose libpod DB
may record an empty/foreign graph driver. `podman system reset`
reads that DB FIRST and aborts with 'database graph driver "" does
not match our graph driver "overlay"' BEFORE it can wipe. Remove
the stale store (rootful + rootless) so reset starts from a clean
slate, then make reset itself non-fatal (install-robustness
).

<!-- mios-src:32d6ab8c2bce from .github/workflows/mios-ci.yml:316-322 -->

### GitHub-hosted ubuntu-24.04 runners ship with ~14 GB free on...

GitHub-hosted ubuntu-24.04 runners ship with ~14 GB free on
/. The MiOS Containerfile bakes 16+ container images into
/usr/lib/containers/storage at OCI build time
(BOUND-IMAGES law -- runtime pulls are bugs), and the bake
blew through the runner's free space mid-pull at the 16th
image (open-webui's NotoSansSC font blob, ~30 MB) on
. jlumbroso/free-disk-space reclaims ~30 GB by
removing pre-installed Android SDK, .NET, GHC, Haskell,
CodeQL, large /opt entries, etc. -- none of which the OCI
build needs. Forgejo's self-hosted runner has plenty of
disk and skips this; keeping the steps in parity here
matters less than building successfully.

<!-- mios-src:b896b941f929 from .github/workflows/mios-ci.yml:328-339 -->

### Anonymous GHCR pulls hit "503 Egress is over the account...

Anonymous GHCR pulls hit "503 Egress is over the account limit"
mid-pull on big multi-layer images like ublue-os/ucore-hci
(~70 blobs, all anonymous-quota-counted). Authenticated pulls
don't share the anonymous pool, so logging in even with the
auto-provided GITHUB_TOKEN (which has GHCR read on public
images) bypasses the rate limit. Operator-confirmed CI failure
Containerfile FROM ghcr.io/ublue-os/ucore-hci died
at blob 67/70 with the anonymous-quota error.

<!-- mios-src:488fc6bcd3a7 from .github/workflows/mios-ci.yml:351-358 -->

### sudo

sudo: rootful podman avoids the user-namespace UID exhaustion
that breaks the bound-images bake step. The bake's inner
`podman --root /usr/lib/containers/storage pull` unpacks
images that contain files owned by high-numbered system
GIDs (e.g. /etc/gshadow gid=42); rootless podman remaps via
/etc/subuid + /etc/subgid which the GHA runner user has only
65k entries for, and the chown then fails with "lchown
/etc/gshadow: invalid argument" -- "potentially insufficient
UIDs or GIDs available in user namespace". Rootful podman
has full UID range and skips the remap. Operator-confirmed
CI failure (qdrant + 13 other bound images failed
with this exact error mid-bake).
TMPDIR on /mnt too -- buildah's commit scratch must not spill onto
the small / (install-robustness).
When PUBLISH=false this GitHub build+lint VALIDATES only: a standard
ubuntu-24.04 runner (~66GB /mnt) cannot hold the ~60GB baked
bound-images store -- one buildah commit overruns it (exit 125 /
"closed pipe"). GitHub and Forgejo are EQUALS; this is a capacity gate,
not a demotion. The baked image comes from a runner that CAN bake
(local MiOS-DEV first, or the 707GB Forgejo runner) and lands in the
default registry (GHCR when creds are present, else local/Forgejo). Set
PUBLISH='true' (env, top of file) so GitHub bakes+pushes too once it can
hold the full image (large-disk runner, or after MiOS-Sys shrinks it).
--device /dev/fuse + --cap-add all + seccomp/apparmor unconfined: the bake
RUNs (57-mios-sys-build.sh, mios-bake-group) run podman-in-podman to build
localhost/mios-sys|-cuda and pull the bound sidecars into the additional
store -- and the mios-sys build is itself multi-stage with its own RUN
steps (go-builder), so it is TRIPLE-nested. Nested podman needs: /dev/fuse
(native overlay-on-overlay is blocked -> fuse-overlayfs fallback, "cannot
mount: No such file or directory") AND enough capability for crun to set
up each RUN container -- CAP_SYS_RESOURCE for setrlimit(RLIMIT_NOFILE)
("Operation not permitted"), CAP_SYS_ADMIN for mount/namespaces, etc. The
Forgejo runner never hits any of this: its Quadlet is Privileged=true.
Match that privileged env with --cap-add all + unconfined confinement.
57-mios-sys-build.sh passes the same down to ITS nested podman build.
BUILD-TIME only (RUN instructions) -- the produced image carries nothing.
DISK FIT: the graphroot lives on /mnt (Configure-storage step). buildah
writes ~2-3x the layer diff to TMPDIR during each RUN commit, so keeping
TMPDIR on /mnt too competes with the store on ONE volume -> exit-125
"storing blob ... write" (ENOSPC) on the 57-mios-sys-build commit. Put the
commit temp on the jlumbroso-freed / instead, so the amplification spreads
across both large disks (/mnt store + / temp), each holding ~1x.

<!-- mios-src:feb6b6ba127c from .github/workflows/mios-ci.yml:381-422 -->

### Improved rechunking for smaller Day-2 deltas. PREFER...

Improved rechunking for smaller Day-2 deltas. PREFER rpm-ostree's
`compose build-chunked-oci --format-version=2`: format-version 2 writes
explicit per-layer parent dirs -> DETERMINISTIC layer hashes, so layers
that don't change keep identical digests across builds and bootc-upgrade
ships a minimal delta (vs the wrapper's default). Runs the image's own
rpm-ostree. FALLBACK chain: build-chunked-oci -> bootc-base-imagectl
rechunk (the wrapper; --max-layers, no format-version) -> un-rechunked.
Each rechunk is a LOSSLESS re-layering (content byte-identical), so a
missing tool/flag only costs delta efficiency, never the publish.
The bind-mount maps the runner's ACTUAL rootful graphroot
(/mnt/containers-storage -- relocated off the small / in "Configure host
podman storage") onto the container's DEFAULT c/storage path so the inner
rpm-ostree/bootc reads the just-built image and writes -rechunked back to
the same store the host push reads. Mounting /var/lib/containers/storage
(podman's default) mounted an EMPTY dir -- the store was rm -rf'd + moved
to /mnt -- so every rechunk silently degraded to un-rechunked.

<!-- mios-src:6ec74752970a from .github/workflows/mios-ci.yml:469-484 -->

### cosign writes each .sig artifact to the registry as the...

cosign writes each .sig artifact to the registry as the RUNNER user (no
sudo). The earlier `sudo podman login` steps wrote creds to ROOT's
auth.json, which cosign (non-root) never sees -> the signature push is
denied ("unauthorized"). Give cosign its OWN login to the same registry
host (derived from the SSOT MIOS_IMAGE_NAME, parity with the push-login
step) before signing. Keyless OIDC still provides the signing identity;
this only authorizes the registry WRITE.

<!-- mios-src:617b0a013ef0 from .github/workflows/mios-ci.yml:592-598 -->

### runroot + graphroot are REQUIRED (a [storage] table with...

runroot + graphroot are REQUIRED (a [storage] table with only `driver`
makes `podman system reset` abort with "runroot must be set"). Put
graphroot on /mnt -- the GHA runner's LARGE ephemeral disk (~65GB+
free) vs / (~21GB even after jlumbroso frees ~30GB). The MiOS image
bakes 21 large bound-images (~50GB incl AI lanes); committing that
layer on / exhausts the disk and the layer copy's pipe closes ("io:
read/write on closed pipe", exit 125,). runroot stays on
tmpfs /run (small runtime state only). install-robustness.

<!-- mios-src:9565dcccef24 from .github/workflows/mios-ci.yml:624-631 -->

### The GHA runner ships a pre-seeded containers store whose...

The GHA runner ships a pre-seeded containers store whose libpod DB
may record an empty/foreign graph driver. `podman system reset`
reads that DB FIRST and aborts with 'database graph driver "" does
not match our graph driver "overlay"' BEFORE it can wipe. Remove
the stale store (rootful + rootless) so reset starts from a clean
slate, then make reset itself non-fatal (install-robustness
).

<!-- mios-src:32d6ab8c2bce from .github/workflows/mios-ci.yml:633-639 -->

### sudo

sudo: rootful podman avoids user-namespace UID exhaustion in
the bake step (same fix as the main build step above).
PR-only smoke: skip the disk-heavy bound-images bake (see build job).
--device/--cap-add/--seccomp: 57-mios-sys-build.sh runs podman-in-podman
(nested fuse-overlayfs) even with MIOS_BAKE_BOUND_IMAGES=0, so the smoke
build needs the same nested-storage privileges as the main build above.

<!-- mios-src:c5329a266c25 from .github/workflows/mios-ci.yml:666-671 -->
