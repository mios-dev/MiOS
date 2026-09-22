# FOSS OCI Compliant DevContainer for MiOS Agent Harness
#
# Base image is digest-pinned (not just tag-pinned) for reproducibility: the
# `fedora-minimal:42` tag can move, the digest cannot. Refresh the pin
# deliberately by re-querying the registry, e.g.:
#   curl -s "https://registry.fedoraproject.org/v2/fedora-minimal/manifests/42" \
#     -H "Accept: application/vnd.oci.image.index.v1+json" -D - -o /dev/null \
#     | grep -i docker-content-digest
FROM registry.fedoraproject.org/fedora-minimal:42@sha256:09a2061e2cfb85ac8e7fa7f2234d0ace6ad4f2b7dfdf0f257c90405e4f07577d

LABEL org.opencontainers.image.title="MiOS DevContainer Agent Harness" \
      org.opencontainers.image.description="Embedded agentic harness for MiOS + MiOS-AI autonomous build pipeline" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN microdnf install -y \
    git bash curl jq tar gzip procps-ng shadow-utils \
    python3 python3-pip python3-pyyaml python3-cffi \
    && microdnf clean all

# Configure unprivileged non-root operator user
RUN useradd -m -u 1000 -s /bin/bash spark \
    && mkdir -p /var/lib/mios /var/cache/mios /etc/mios \
    && chown -R spark:spark /var/lib/mios /var/cache/mios /etc/mios

USER spark
WORKDIR /workspace
ENTRYPOINT ["/bin/bash"]
