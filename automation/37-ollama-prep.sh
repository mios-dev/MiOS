#!/bin/bash
# 37-ollama-prep: DEPRECATED -- replaced by mios-ollama-firstboot.service.
#
# This script tried to embed the default LLM model set into
# /var/lib/ollama at build time, but bootc's image-commit step runs a
# /var cleanup that removes everything except /var/{tmp,cache} (per
# Architectural Law 2 -- NO-MKDIR-IN-VAR; /var is a mutable host
# surface, not part of the immutable composefs layer). The pulled
# models therefore never survive into the deployed image.
#
# The work has moved to a runtime first-boot service that pulls the
# default models AFTER the deploy, into the persistent /var/lib/ollama:
#
#   usr/lib/systemd/system/mios-ollama-firstboot.service
#   usr/libexec/mios/ollama-firstboot.sh
#
# That service is sentinel-guarded (/var/lib/mios/.ollama-firstboot-
# done) so it runs once per deploy, and the models survive
# 'bootc upgrade' / 'bootc rollback' as ordinary /var state.
#
# The script is kept as an explicit no-op stub (rather than deleted)
# so existing CONTAINERFILE_SCRIPTS references in automation/build.sh
# don't break. Future cleanups can drop both this file and that
# reference together.
set -euo pipefail
echo "[37-ollama-prep] deprecated -- model pull happens at first boot via mios-ollama-firstboot.service"
exit 0
