<!-- AI-hint: Manual pages distilled from the source comments of containers, sanitized, each passage anchored to the comment it came from. -->

# containers

### runroot / graphroot intentionally OMITTED. Why...

runroot / graphroot intentionally OMITTED.

Why: containers/storage's resolution chain reads /etc/containers/
storage.conf for ALL users (root and non-root). When this file
explicitly sets runroot=/run/containers/storage and
graphroot=/var/lib/containers/storage, NON-ROOT podman invocations
inherit those paths and fail at startup:

    WARN[0000] RunRoot is pointing to a path (/run/containers/storage)
               which is not writable. Most likely podman will fail.:
               permission denied
    Error: cannot evaluate symlinks on DB run root path
               "/run/containers/storage": lstat /run/containers/storage:
               permission denied

(visible at every `wsl -d podman-MiOS-DEV` entry on 2026-05-06 paste
until this fix). The default `user` (UID 1000) and the mios user can
only write rootless paths. Letting podman default per-UID gives:
  * root          : /run/containers/storage + /var/lib/containers/storage
                    (the same paths this file used to set explicitly)
  * non-root user : $XDG_RUNTIME_DIR/containers + ~/.local/share/containers/storage
                    (rootless, writable by the user)

Operators who want to override either path do so in their per-user
~/.config/containers/storage.conf -- /etc wins for fields that ARE
set here, but absent fields fall through to per-UID defaults.

<!-- mios-src:d812e6153920 from etc/containers/storage.conf:34-59 -->

### usr/lib/containers/storage is the logically-bound-image...

/usr/lib/containers/storage is the logically-bound-image store. The
OCI build (Containerfile) skopeo-copies every Quadlet's Image= into
it (ARCHITECTURAL LAW 3 -- BOUND-IMAGES); it lives in immutable /usr
so it survives the build's /var cleanup. Listing it here as a
read-only additional store is what lets `bootc install` AND the
running system resolve bound images with ZERO runtime pulls --
without it, BIB/osbuild's bootc.install-to-filesystem stage fails
every deployment artifact with "resolving bound image ...: does not
resolve to an image ID" (operator-confirmed 2026-05-14).

<!-- mios-src:34c4596b5b8f from etc/containers/storage.conf:62-70 -->

### Logically-bound-image store baked into immutable /usr by...

Logically-bound-image store baked into immutable /usr by the OCI
build (see /etc/containers/storage.conf for the full rationale --
ARCHITECTURAL LAW 3, BOUND-IMAGES). Kept in sync with the /etc layer.

<!-- mios-src:f54abcc3a832 from usr/share/containers/storage.conf:33-35 -->
