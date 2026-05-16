# /etc/mios/containers/agent-sandbox/Dockerfile
#
# Per-session MiOS agent exec sandbox image. Built locally with:
#   podman build -t localhost/mios-agent-sandbox:latest \
#       /etc/mios/containers/agent-sandbox/
#
# Per FS+OS Control guide §15. Alpine base for small image size + musl
# (the compiled exec-init.c is static-linked against musl). The
# sandbox image is a SHELL + CODER toolkit, NOT an OS -- the agent
# runs commands inside it via `podman exec`, so the container's PID 1
# is the long-running exec-init listener (or just a `sleep infinity`
# during initial wiring).
#
# What the agent has access to inside:
#   bash, coreutils, ripgrep, fd-find, git, python3 + pip, nodejs + npm,
#   make, gcc, jq, curl (off by default via Network=none), the
#   compiled /usr/local/bin/exec-init for Landlock-restricting child
#   commands.
#
# What the sandbox CANNOT do:
#   network (Quadlet Network=none + seccomp socket(AF_INET) ERRNO),
#   write outside /work or /tmp (Landlock from exec-init),
#   any escalation syscall (hardened seccomp profile),
#   keep_state across sessions (--rm + tmpfs /tmp + tmpfs upper).

FROM docker.io/library/alpine:3.20 AS build

# Build the exec-init landlock+rlimits wrapper.
# musl + static linking -> single self-contained ELF, no libc.so
# dependency drift between alpine versions.
RUN apk add --no-cache build-base linux-headers
COPY exec-init.c /build/exec-init.c
RUN gcc -static -Wall -Wextra -O2 -o /build/exec-init /build/exec-init.c \
    && strip /build/exec-init

FROM docker.io/library/alpine:3.20

# Runtime toolkit. Kept minimal -- agent loads more on demand via
# `apk add` inside its own session if needed (the package metadata
# is read-only via the Landlock /etc /usr ro mounts; apk writes to
# /var which we leave rw inside the sandbox tmpfs).
RUN apk add --no-cache \
        bash coreutils \
        ripgrep fd \
        git git-lfs \
        python3 py3-pip py3-virtualenv \
        nodejs npm \
        make gcc musl-dev linux-headers \
        jq curl wget \
        file procps-ng htop \
        openssh-client \
    && rm -rf /var/cache/apk/*

# Install the compiled exec-init wrapper. Agents inside the sandbox
# launch commands via:
#   exec-init <cmd> [args...]
# which applies the Landlock domain (allow /work + /tmp rw, /usr +
# /etc ro, deny everything else) before exec'ing the command. PID 1
# of the container itself doesn't need to run inside the Landlock
# domain; only the agent's spawned commands do.
COPY --from=build /build/exec-init /usr/local/bin/exec-init
RUN chmod 0755 /usr/local/bin/exec-init

# Workspace + scratch -- bind-mounted from the host by the Quadlet.
RUN mkdir -p /work /work-upper && chmod 0755 /work /work-upper

# Default cmd: long-sleep so the container stays alive for `podman
# exec` from the agent. The Quadlet's Exec= overrides this if the
# operator wants a different listener (e.g. a unix-socket-listening
# `exec-server`).
CMD ["/bin/sleep", "infinity"]
