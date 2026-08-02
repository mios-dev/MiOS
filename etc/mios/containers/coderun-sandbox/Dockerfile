# AI-hint: Defines the Dockerfile for the coderun-sandbox container, providing a restricted, Landlock-hardened environment with a pre-built toolchain (gcc, python, node) for agents to execute untrusted code safely.
# AI-related: /etc/mios/containers/coderun-sandbox/Dockerfile, /etc/mios/containers/coderun-sandbox/, mios-coderun-sandbox

FROM docker.io/library/alpine:3.20 AS build

RUN apk add --no-cache build-base linux-headers
COPY exec-init.c /build/exec-init.c
RUN gcc -static -Wall -Wextra -O2 -o /build/exec-init /build/exec-init.c \
    && strip /build/exec-init

FROM docker.io/library/alpine:3.20

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

COPY --from=build /build/exec-init /usr/local/bin/exec-init
RUN chmod 0755 /usr/local/bin/exec-init

RUN mkdir -p /work /work-upper && chmod 0755 /work /work-upper

ENV MIOS_CODEMODE_SOCKET=/run/coderun.sock
ENV PYTHONPATH=/usr/local/lib/mios
COPY mios_tools.py /usr/local/lib/mios/mios_tools.py

CMD ["/bin/sleep", "infinity"]
