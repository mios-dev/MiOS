#!/usr/bin/env bash
# AI-hint: Defines and exports standard FHS path constants for MiOS components (logs, libexec, share, etc.) to ensure consistent directory resolution across system scripts and binaries.
# AI-related: /usr/lib/mios/paths.sh

: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LOG_DIR:=${MIOS_USR_DIR}/logs}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"

: "${MIOS_ETC_DIR:=/etc/mios}"

: "${MIOS_VAR_DIR:=/var/lib/mios}"
: "${MIOS_MEMORY_DIR:=${MIOS_VAR_DIR}/memory}"
: "${MIOS_SCRATCH_DIR:=${MIOS_VAR_DIR}/scratch}"

export MIOS_USR_DIR MIOS_LOG_DIR MIOS_LIBEXEC_DIR MIOS_SHARE_DIR
export MIOS_ETC_DIR
export MIOS_VAR_DIR MIOS_MEMORY_DIR MIOS_SCRATCH_DIR
