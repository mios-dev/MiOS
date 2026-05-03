#!/usr/bin/env bash
# /usr/lib/mios/paths.sh — runtime FHS path constants for MiOS.
# Shipped in the image; sourced by /usr/libexec/mios/* and /usr/bin/mios*.
# Idempotent. Override any constant from the environment before sourcing.
#
# Mirror of automation/lib/paths.sh (which is build-time only and not shipped).
# Keep these two files aligned when adding constants.

# /usr/* — read-only composefs surface
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LOG_DIR:=${MIOS_USR_DIR}/logs}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"

# /etc/* — admin-override surface (3-way merged on bootc upgrade)
: "${MIOS_ETC_DIR:=/etc/mios}"

# /var/* — runtime mutable (declared via tmpfiles.d, never written at build)
: "${MIOS_VAR_DIR:=/var/lib/mios}"
: "${MIOS_MEMORY_DIR:=${MIOS_VAR_DIR}/memory}"
: "${MIOS_SCRATCH_DIR:=${MIOS_VAR_DIR}/scratch}"

export MIOS_USR_DIR MIOS_LOG_DIR MIOS_LIBEXEC_DIR MIOS_SHARE_DIR
export MIOS_ETC_DIR
export MIOS_VAR_DIR MIOS_MEMORY_DIR MIOS_SCRATCH_DIR
