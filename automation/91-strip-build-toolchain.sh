#!/bin/bash
# 'MiOS' v0.2.2 -- 91-strip-build-toolchain
#
# Removes the build toolchain (compilers, build-system headers) from the
# image after every build-phase that needs them has finished. Runs after
# 90-generate-sbom.sh (so the SBOM still records what was used to build
# the image) and before 99-cleanup.sh / 99-postcheck.sh.
#
# Why: a deployed MiOS host carrying gcc/g++/cmake/golang is unnecessary
# attack surface for any process that obtains a shell. Per the project
# invariant (VM | Container | Flatpak only), runtime application code
# does not compile on the host -- it ships in containers/Flatpaks/VMs
# that bring their own toolchains where needed.
#
# Block parsed from PACKAGES.md `packages-build-toolchain`. The strip is
# best-effort: a missing package is fine (host already lean), but a
# failed dnf transaction is logged loud since it leaves the toolchain in
# place.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/packages.sh
source "${SCRIPT_DIR}/lib/packages.sh"

log "[91-strip-build-toolchain] Resolving build-toolchain package list..."
TOOLCHAIN_STR="$(get_packages "build-toolchain")"

if [[ -z "${TOOLCHAIN_STR// /}" ]]; then
    warn "[91-strip-build-toolchain] No packages found in 'build-toolchain' block; nothing to strip."
    exit 0
fi

log "[91-strip-build-toolchain] Removing: ${TOOLCHAIN_STR}"
# --noautoremove keeps system libs that the toolchain pulled but other
# runtime packages also depend on (libstdc++, libgcc); we only want to
# remove the toolchain itself, not cascade-delete shared libraries.
# shellcheck disable=SC2086 # word-splitting is intentional
$DNF_BIN "${DNF_SETOPT[@]}" remove -y --noautoremove $TOOLCHAIN_STR 2>&1 \
    | grep -E '^\s*(Removing|Error|Warning|Nothing)' || true

# Verification: assert no compiler binary is left in PATH. If any survive,
# 99-postcheck will surface it as an image-quality regression.
log "[91-strip-build-toolchain] Verifying toolchain removal..."
LEFT=()
for bin in gcc g++ cc cmake make go; do
    if command -v "$bin" >/dev/null 2>&1; then
        LEFT+=("$bin -> $(command -v "$bin")")
    fi
done
if [[ ${#LEFT[@]} -gt 0 ]]; then
    warn "[91-strip-build-toolchain] Toolchain binaries still in PATH:"
    for entry in "${LEFT[@]}"; do warn "  ${entry}"; done
    warn "[91-strip-build-toolchain] These were pulled in by another package's dependencies; review build-toolchain block."
else
    log "[91-strip-build-toolchain] [ok] No compiler/build-system binaries remain in PATH."
fi

log "[91-strip-build-toolchain] Build toolchain stripped."
