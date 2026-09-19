#!/usr/bin/env bash
# cloud-fedora-setup.sh — give an Anthropic-hosted cloud environment a real
# Fedora userspace.
#
# WHERE THIS RUNS
#   Paste the whole file into the "Setup script" field of a cloud environment
#   (claude.ai/code -> environment selector -> Add cloud environment). It is
#   kept here so the pasted copy has a versioned, syntax-checked source.
#
# WHY A CONTAINER AND NOT A BASE IMAGE
#   Anthropic-hosted cloud sessions run a fixed Ubuntu 24.04 x86_64 VM, and
#   "replacing the base image entirely isn't supported yet"
#   (code.claude.com/docs/en/cloud-environments#installed-tools). Docker IS
#   pre-installed, and after this script finishes the platform snapshots the
#   filesystem and reuses it for every later session — so an image built here
#   is already on disk next time and costs nothing at startup. A container is
#   therefore the only supported way to get Fedora, and a cheap one.
#
# WHAT YOU GET
#   /usr/local/bin/fedora — run anything in Fedora, same paths, same $PWD:
#       fedora                  # interactive Fedora shell
#       fedora dnf install -y … # Fedora package management
#       fedora cargo build      # build against Fedora's toolchain
#
# SETUP-SCRIPT CONTRACT (docs: cloud-environments#script-requirements)
#   Runs as root. Must exit 0 — a non-zero exit fails the whole session. Must
#   finish inside ~5 minutes or the environment cache won't build. So: no
#   `set -e`, every step guarded, and an unconditional `exit 0` at the end.
#   A failed provision degrades to a plain Ubuntu session with a log line, it
#   never blocks the session.
#
# TUNABLES (set them as environment variables on the same cloud environment)
#   FEDORA_VERSION    Fedora release to base on          (default 44)
#   FEDORA_PACKAGES   package set baked into the image   (default below)
#   FEDORA_IMAGE      derived image tag                  (default dev-loop-fedora:$FEDORA_VERSION)
#   FEDORA_REBUILD=1  force a rebuild even if the image is already cached
#
# ALSO USABLE WITHOUT THE SETUP-SCRIPT FIELD
#   `--wrapper-only` installs /usr/local/bin/fedora and skips the pull+build,
#   so a SessionStart hook can install it in well under a second and the first
#   `fedora …` call builds the image on demand. Use that when an environment
#   dialog offers no Setup script field, or to keep session startup instant.

set -u

FEDORA_VERSION="${FEDORA_VERSION:-44}"
FEDORA_IMAGE="${FEDORA_IMAGE:-dev-loop-fedora:${FEDORA_VERSION}}"
FEDORA_BASE="registry.fedoraproject.org/fedora:${FEDORA_VERSION}"
FEDORA_CONTAINER="${FEDORA_CONTAINER:-fedora}"
BUILD_CTX=/opt/dev-loop-fedora
SELF=$(cd "$(dirname "$0")" 2>/dev/null && pwd)/$(basename "$0")
WRAPPER_ONLY=0
[ "${1:-}" = "--wrapper-only" ] && WRAPPER_ONLY=1

# Kept close to .devcontainer/Dockerfile so a cloud session and the devcontainer
# present the same Fedora. install_weak_deps=False keeps the build inside budget.
FEDORA_PACKAGES="${FEDORA_PACKAGES:-git tmux jq curl wget ripgrep python3 python3-pip nodejs npm gcc gcc-c++ make procps-ng util-linux shadow-utils sudo which hostname tar gzip unzip zip findutils diffutils patch openssl dbus-daemon dbus-tools gnome-keyring libsecret}"

log() { printf '[fedora-env] %s\n' "$*"; }

# --- 1. the Docker daemon -----------------------------------------------------
# Present but not started: the environment cache restores files, never running
# processes, so this is also what /usr/local/bin/fedora does on a cold session.
ensure_dockerd() {
    docker info >/dev/null 2>&1 && return 0
    command -v dockerd >/dev/null 2>&1 || { log "dockerd is not installed — cannot provision Fedora"; return 1; }
    log "starting dockerd"
    ( dockerd >/var/log/dev-loop-dockerd.log 2>&1 & ) >/dev/null 2>&1
    i=0
    while [ "$i" -lt 45 ]; do
        docker info >/dev/null 2>&1 && return 0
        i=$((i + 1)); sleep 1
    done
    log "dockerd did not come up in 45s (see /var/log/dev-loop-dockerd.log)"
    return 1
}

# --- 2. the egress proxy's CA -------------------------------------------------
# Cloud sessions reach the network through a TLS-terminating proxy, so a
# container that doesn't trust its CA fails every https fetch with
# "self-signed certificate in certificate chain". Bake the CA into the image's
# trust store rather than turning verification off anywhere.
find_ca_bundle() {
    for c in "${FEDORA_CA_BUNDLE:-}" "${SSL_CERT_FILE:-}" "${CURL_CA_BUNDLE:-}" \
             /root/.ccr/ca-bundle.crt /etc/ssl/certs/ca-certificates.crt; do
        [ -n "$c" ] && [ -f "$c" ] && { printf '%s' "$c"; return 0; }
    done
    return 1
}

# --- 3. build context ---------------------------------------------------------
# Repos are pinned to dl.fedoraproject.org instead of the default metalink.
# A metalink hands dnf a different third-party mirror hostname on every run,
# which no network allowlist can cover; dl.fedoraproject.org is the canonical
# master and is one stable host to allow. GPG checking stays on.
write_build_context() {
    mkdir -p "$BUILD_CTX/repos" "$BUILD_CTX/ca" || return 1

    cat > "$BUILD_CTX/repos/fedora.repo" <<'REPO'
[fedora]
name=Fedora $releasever - $basearch
baseurl=https://dl.fedoraproject.org/pub/fedora/linux/releases/$releasever/Everything/$basearch/os/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch
skip_if_unavailable=False
REPO

    cat > "$BUILD_CTX/repos/fedora-updates.repo" <<'REPO'
[updates]
name=Fedora $releasever - $basearch - Updates
baseurl=https://dl.fedoraproject.org/pub/fedora/linux/updates/$releasever/Everything/$basearch/
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch
skip_if_unavailable=False
REPO

    ca_line=""
    if ca=$(find_ca_bundle); then
        cp "$ca" "$BUILD_CTX/ca/egress-proxy-ca.crt" 2>/dev/null &&
            ca_line='COPY ca/egress-proxy-ca.crt /etc/pki/ca-trust/source/anchors/egress-proxy-ca.crt'
        log "trusting egress CA from $ca"
    else
        log "no egress CA bundle found — continuing with the image's own trust store"
    fi

    # --disablerepo='*' pins the build to exactly the two repos above, so
    # whatever else the base image ships (codec repos and friends) can never
    # pull the build toward a host the allowlist doesn't cover.
    cat > "$BUILD_CTX/Dockerfile" <<DOCKERFILE
ARG FEDORA_BASE=${FEDORA_BASE}
FROM \${FEDORA_BASE}
COPY repos/ /etc/yum.repos.d/
${ca_line}
RUN update-ca-trust extract || true
# The minimal Fedora image ships no /etc/pki/tls/certs/ca-bundle.crt compat
# symlink, so anything hardcoding that classic path fails to load any CA.
RUN mkdir -p /etc/pki/tls/certs \\
    && ln -sf /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem /etc/pki/tls/certs/ca-bundle.crt
RUN dnf -y --disablerepo='*' --enablerepo=fedora --enablerepo=updates \\
        --setopt=install_weak_deps=False install ${FEDORA_PACKAGES} \\
    && dnf clean all
DOCKERFILE
}

# --- 4. the wrapper -----------------------------------------------------------
# Self-healing on purpose: it starts dockerd and the container itself, so it
# works in every later session even though only files survive the snapshot.
install_wrapper() {
    # Write-then-rename, never write in place: this script can be invoked BY
    # the wrapper (on-demand build), and bash reads a script incrementally by
    # byte offset — truncating and rewriting the file a shell is executing
    # makes it resume mid-line on shifted offsets. A rename swaps the directory
    # entry and leaves the running shell's open inode untouched.
    tmp=/usr/local/bin/.fedora.$$
    cat > "$tmp" <<'WRAPPER'
#!/usr/bin/env bash
# Run a command inside this environment's Fedora userspace.
#   fedora                 interactive Fedora shell
#   fedora <cmd> [args…]   run <cmd> in Fedora
# Host paths are bind-mounted at the SAME absolute path and $PWD is preserved,
# so a path means the same thing on both sides.
set -u

IMAGE="${FEDORA_IMAGE:-dev-loop-fedora:${FEDORA_VERSION:-44}}"
CONTAINER="${FEDORA_CONTAINER:-fedora}"
SETUP_SCRIPT="__SETUP_SCRIPT__"

die() { printf 'fedora: %s\n' "$*" >&2; exit 1; }

ensure_dockerd() {
    docker info >/dev/null 2>&1 && return 0
    command -v dockerd >/dev/null 2>&1 || die "dockerd is not installed"
    ( dockerd >/var/log/dev-loop-dockerd.log 2>&1 & ) >/dev/null 2>&1
    i=0
    while [ "$i" -lt 45 ]; do
        docker info >/dev/null 2>&1 && return 0
        i=$((i + 1)); sleep 1
    done
    die "dockerd did not start (see /var/log/dev-loop-dockerd.log)"
}

run_args() {
    # --network host: the egress proxy listens on the VM's 127.0.0.1, which a
    # bridged container cannot reach.
    printf '%s\n' --network host
    for d in /home /root /workspace /srv /opt/dev-loop-fedora; do
        [ -d "$d" ] && printf '%s\n%s\n' -v "$d:$d"
    done
    for v in HTTPS_PROXY https_proxy NO_PROXY no_proxy HTTP_PROXY http_proxy; do
        [ -n "${!v:-}" ] && printf '%s\n%s\n' -e "$v=${!v}"
    done
    # Fedora's own trust store, where update-ca-trust puts the egress CA at build
    # time. Use the extracted bundle, not the /etc/pki/tls/certs/ca-bundle.crt
    # compat path: it is the file update-ca-trust actually writes.
    for v in SSL_CERT_FILE CURL_CA_BUNDLE REQUESTS_CA_BUNDLE NODE_EXTRA_CA_CERTS; do
        printf '%s\n%s\n' -e "$v=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    done
}

ensure_image() {
    docker image inspect "$IMAGE" >/dev/null 2>&1 && return 0
    # FEDORA_NO_AUTOBUILD guards the recursion: the setup script verifies itself
    # by calling this wrapper, and a failed build must not bounce the two off
    # each other forever.
    [ "${FEDORA_NO_AUTOBUILD:-0}" = 1 ] &&
        die "image $IMAGE is missing and the build did not produce it (see /var/log/dev-loop-fedora-build.log)"
    [ -r "$SETUP_SCRIPT" ] || die "image $IMAGE is missing — re-run $SETUP_SCRIPT"
    printf 'fedora: first use — building %s, about a minute…\n' "$IMAGE" >&2
    FEDORA_NO_AUTOBUILD=1 bash "$SETUP_SCRIPT" >&2
    docker image inspect "$IMAGE" >/dev/null 2>&1 ||
        die "build failed (see /var/log/dev-loop-fedora-build.log)"
}

ensure_container() {
    state=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null) || state=""
    case "$state" in
        running) return 0 ;;
        "")
            mapfile -t args < <(run_args)
            docker run -d --name "$CONTAINER" "${args[@]}" "$IMAGE" sleep infinity >/dev/null ||
                die "could not start the Fedora container"
            ;;
        *) docker start "$CONTAINER" >/dev/null || die "could not restart $CONTAINER" ;;
    esac
}

ensure_dockerd
# Before ensure_container, never after: an on-demand build runs the setup
# script, which verifies itself through this same wrapper and may create the
# container — so any container state read earlier would already be stale.
ensure_image
ensure_container

workdir=$PWD
case $workdir in
    /home/*|/root|/root/*|/workspace/*|/srv/*) ;;
    *) workdir=/ ;;
esac

exec_flags=(-i -w "$workdir")
[ -t 0 ] && [ -t 1 ] && exec_flags+=(-t)

if [ "$#" -eq 0 ]; then
    exec docker exec "${exec_flags[@]}" "$CONTAINER" bash -l
fi
exec docker exec "${exec_flags[@]}" "$CONTAINER" "$@"
WRAPPER
    sed -i "s#__SETUP_SCRIPT__#${SELF}#" "$tmp" || { rm -f "$tmp"; return 1; }
    chmod 0755 "$tmp" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" /usr/local/bin/fedora
}

# --- main ---------------------------------------------------------------------
main() {
    if [ "$WRAPPER_ONLY" = 1 ]; then
        install_wrapper && log "installed /usr/local/bin/fedora (builds $FEDORA_IMAGE on first use)" ||
            log "could not install /usr/local/bin/fedora"
        return 0
    fi

    ensure_dockerd || { log "skipping Fedora provisioning"; return 0; }

    if [ "${FEDORA_REBUILD:-0}" != "1" ] && docker image inspect "$FEDORA_IMAGE" >/dev/null 2>&1; then
        log "$FEDORA_IMAGE already present — skipping build"
    else
        write_build_context || { log "could not write the build context"; return 0; }
        log "pulling $FEDORA_BASE"
        docker pull "$FEDORA_BASE" >/dev/null 2>&1 || { log "pull failed — is registry.fedoraproject.org allowed by this environment's network policy?"; return 0; }
        log "building $FEDORA_IMAGE"
        # --network host so the build itself reaches the proxy on 127.0.0.1.
        if ! docker build --network host \
                --build-arg "FEDORA_BASE=$FEDORA_BASE" \
                -t "$FEDORA_IMAGE" "$BUILD_CTX" >/var/log/dev-loop-fedora-build.log 2>&1; then
            log "build failed — tail of /var/log/dev-loop-fedora-build.log:"
            tail -n 15 /var/log/dev-loop-fedora-build.log 2>/dev/null
            return 0
        fi
    fi

    if [ "${FEDORA_NO_AUTOBUILD:-0}" = 1 ]; then
        log "invoked by the wrapper — leaving /usr/local/bin/fedora as it is"
    else
        install_wrapper || { log "could not install /usr/local/bin/fedora"; return 0; }
    fi

    if ver=$(/usr/local/bin/fedora cat /etc/fedora-release 2>/dev/null); then
        log "ready: $ver — run 'fedora <command>' or 'fedora' for a shell"
    else
        log "image built but the wrapper could not start a container"
    fi
}

main
exit 0
