#!/usr/bin/env bash
# AI-hint: bash Defines and exports core MiOS filesystem constants (USR, ETC, VAR, LOG, BUILD) as environment variables to standardize directory paths for automatio...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_lib_paths_sh.md

: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LOG_DIR:=${MIOS_USR_DIR}/logs}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"

: "${MIOS_ETC_DIR:=/etc/mios}"

: "${MIOS_VAR_DIR:=/var/lib/mios}"
: "${MIOS_MEMORY_DIR:=${MIOS_VAR_DIR}/memory}"
: "${MIOS_SCRATCH_DIR:=${MIOS_VAR_DIR}/scratch}"

: "${MIOS_BUILD_LOG:=${MIOS_LOG_DIR}/mios-build.log}"
: "${MIOS_BUILD_CHAIN_LOG:=${MIOS_LOG_DIR}/mios-build-chain.log}"
: "${MIOS_VERSION_MANIFEST_FINAL:=${MIOS_LOG_DIR}/mios-build-versions.tsv}"

export MIOS_USR_DIR MIOS_LOG_DIR MIOS_LIBEXEC_DIR MIOS_SHARE_DIR
export MIOS_ETC_DIR
export MIOS_VAR_DIR MIOS_MEMORY_DIR MIOS_SCRATCH_DIR
export MIOS_BUILD_LOG MIOS_BUILD_CHAIN_LOG MIOS_VERSION_MANIFEST_FINAL
