#!/usr/bin/env bash
# automation/lib/paths.sh — FHS path constants for MiOS.
# Source via common.sh; safe to source multiple times (idempotent).
# Override any constant from the environment before sourcing.

# /usr/* — read-only image surface
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LOG_DIR:=${MIOS_USR_DIR}/logs}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"

# /etc/* — admin-override surface
: "${MIOS_ETC_DIR:=/etc/mios}"

# /var/* — runtime mutable
: "${MIOS_VAR_DIR:=/var/lib/mios}"
: "${MIOS_MEMORY_DIR:=${MIOS_VAR_DIR}/memory}"
: "${MIOS_SCRATCH_DIR:=${MIOS_VAR_DIR}/scratch}"

# Build artefacts (resolved at end of build.sh)
: "${MIOS_BUILD_LOG:=${MIOS_LOG_DIR}/mios-build.log}"
: "${MIOS_BUILD_CHAIN_LOG:=${MIOS_LOG_DIR}/mios-build-chain.log}"
: "${MIOS_VERSION_MANIFEST_FINAL:=${MIOS_LOG_DIR}/mios-build-versions.tsv}"

export MIOS_USR_DIR MIOS_LOG_DIR MIOS_LIBEXEC_DIR MIOS_SHARE_DIR
export MIOS_ETC_DIR
export MIOS_VAR_DIR MIOS_MEMORY_DIR MIOS_SCRATCH_DIR
export MIOS_BUILD_LOG MIOS_BUILD_CHAIN_LOG MIOS_VERSION_MANIFEST_FINAL
