#!/usr/bin/env bash
# AI-hint: The MISSING USB staging bridge -- stages every built immutable-MiOS artifact (oci-archive tar, Anaconda-bootc installer ISO, raw/qcow2/vhdx disk images, the mios.toml brain) onto a MiOS-Cat-prepared Ventoy USB (MiOS-Repo + MiOS-Data), resolving partition labels from mios.toml [cat.*] via the shared mios-common.sh resolver, and renders the from-SSOT loopback boot menu so one USB offline-installs the REAL bootc image. Zero-network; idempotent; degrade-open on single-partition sticks. Companion/caller-restorer for tools/install.sh + usr/libexec/mios/mios-stage-oci-archive.
# AI-related: installation/mios-common.sh, tools/install.sh, usr/libexec/mios/mios-stage-oci-archive, cat/loopback.cfg, usr/share/mios/ventoy/ventoy.json, Justfile, usr/share/mios/mios.toml [cat.repo_partition]/[cat.data_partition]/[deploy.artifacts]
# MIOS_INSTALLER_ROLE=usb-artifact-stager
set -euo pipefail

# ============================================================================
# Paths -- resolved relative to THIS script so it works from any CWD/symlink.
# ============================================================================
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MIOS_ROOT:-$(cd "$SELF/.." && pwd)}"
BUILD="${MIOS_BUILD_DIR:-$ROOT/build}"
SSOT="$ROOT/usr/share/mios/mios.toml"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null || echo 0.3.0)"

# ============================================================================
# Shared library -- ONE layered SSOT resolver (mios_ssot_value: user > host >
# vendor, same order as usr/lib/mios/mios_toml.py) + the [colors]-themed logger.
# Point _MIOS_REPO_ROOT at the vendor SSOT dir so `${_MIOS_REPO_ROOT}/mios.toml`
# resolves to THIS checkout's usr/share/mios/mios.toml as the repo-local layer.
# Degrade-open: if mios-common.sh is absent (bare stick copy), define minimal
# fallbacks so the stager still runs with the canonical labels.
# ============================================================================
_MIOS_REPO_ROOT="$ROOT/usr/share/mios"
if [[ -f "$SELF/mios-common.sh" ]]; then
    # shellcheck source=installation/mios-common.sh
    . "$SELF/mios-common.sh"
fi
if ! declare -F mios_ssot_value >/dev/null 2>&1; then
    mios_ssot_value() { # SECTION KEY [DEFAULT] -- tiny fallback reader over the vendor SSOT
        local section="$1" key="$2" default="${3:-}" v
        v="$(awk -v section="$section" -v key="$key" '
            /^[[:space:]]*\[/ { h=$0; gsub(/^[[:space:]]*\[|\][[:space:]]*$/,"",h); insec=(h==section); next }
            insec && $0 ~ ("^[[:space:]]*" key "[[:space:]]*=") {
                line=$0
                if (match(line, /"[^"]*"/)) { print substr(line, RSTART+1, RLENGTH-2); exit }
                sub(/^[^=]*=[[:space:]]*/,"",line); sub(/[[:space:]]+#.*$/,"",line); sub(/[[:space:]]+$/,"",line)
                print line; exit
            }' "$SSOT" 2>/dev/null || true)"
        printf '%s\n' "${v:-$default}"
    }
fi
if ! declare -F log_info >/dev/null 2>&1; then
    log_info()  { printf '[INFO] %s\n' "$*"; }
    log_ok()    { printf '[ OK ] %s\n' "$*"; }
    log_warn()  { printf '[WARN] %s\n' "$*" >&2; }
    log_err()   { printf '[ERR ] %s\n' "$*" >&2; }
    log_phase() { printf '\n== %s ==\n\n' "$*"; }
    die()       { log_err "$*"; exit 1; }
fi

# ============================================================================
# CLI
# ============================================================================
DRY_RUN=0
usage() {
    cat <<EOF
Usage: $0 [options]

Stages built MiOS artifacts from build/ onto a MiOS-Cat-prepared Ventoy USB.
Partition labels come from mios.toml [cat.repo_partition]/[cat.data_partition].

Options:
  --dry-run           Print the staging plan; make no changes (no mount/copy).
  --help              Show this help.

Environment overrides:
  MIOS_ROOT           Repo root (default: parent of this script).
  MIOS_BUILD_DIR      Build output dir  (default: \$MIOS_ROOT/build).
  MIOS_REPO_MP        Pre-mounted MiOS-Repo mountpoint (skip label lookup).
  MIOS_DATA_MP        Pre-mounted MiOS-Data mountpoint (skip label lookup).
  MIOS_STAGE_REPOS=0  Skip staging the shallow git brain (default: 1).
EOF
    exit 0
}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --help|-h) usage ;;
        *) die "Unknown option: $1 (see --help)" ;;
    esac
done

# ============================================================================
# SSOT labels -- resolved from [cat.*] (no hardcoding; canonical fallbacks).
# ============================================================================
REPO_LABEL="$(mios_ssot_value 'cat.repo_partition' 'label' 'MiOS-Repo')"
DATA_LABEL="$(mios_ssot_value 'cat.data_partition' 'label' 'MiOS-Data')"

# ============================================================================
# Helpers -- ALL defined BEFORE their call sites (render_loopback in particular:
# the deploy-plane audit flagged the draft that called it before definition).
# ============================================================================

# render_loopback: emit the from-SSOT Ventoy/GRUB loopback menu. Labels are
# expanded from bash; GRUB's own $iso is escaped (\$) so it survives the heredoc.
# Boots the staged self-contained Anaconda-bootc MiOS.iso (immutable), NOT Fedora.
render_loopback() {
    cat <<LOOP
# Auto-rendered from mios.toml by installation/stage-mios-repo.sh -- DO NOT hand-edit.
# Labels resolved from [cat.repo_partition].label / [cat.data_partition].label.
# Path A (preferred): boot the self-contained Anaconda-bootc installer ISO.
menuentry "Install MiOS (Immutable bootc Workstation & Agentic AI OS)" {
    search --set=root --label ${DATA_LABEL}
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop \$iso
    linux (loop)/images/pxeboot/vmlinuz inst.stage2=hd:LABEL=${DATA_LABEL}:\$iso quiet
    initrd (loop)/images/pxeboot/initrd.img
}
# Path B (rescue / no-Anaconda): install the immutable image from the staged oci-archive.
menuentry "Install MiOS from OCI archive (rescue: bootc install --transport oci-archive)" {
    search --set=root --label ${DATA_LABEL}
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop \$iso
    linux (loop)/images/pxeboot/vmlinuz rd.live.image inst.ks=hd:LABEL=${REPO_LABEL}:/ventoy/mios-oci-install.ks quiet
    initrd (loop)/images/pxeboot/initrd.img
}
menuentry "MiOS Live / Rescue Environment" {
    search --set=root --label ${DATA_LABEL}
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop \$iso
    linux (loop)/images/pxeboot/vmlinuz rd.live.image quiet
    initrd (loop)/images/pxeboot/initrd.img
}
LOOP
}

# mnt_for_label: echo the mountpoint for a filesystem label, mounting it under
# /run/mios-stage/<label> if it is present but not mounted. Empty if not found.
mnt_for_label() {
    local lbl="$1" dev mp
    command -v blkid >/dev/null 2>&1 || { printf ''; return 0; }
    dev="$(blkid -L "$lbl" 2>/dev/null || true)"
    [[ -z "$dev" ]] && { printf ''; return 0; }
    mp="$(findmnt -n -o TARGET --source "$dev" 2>/dev/null | head -1 || true)"
    if [[ -z "$mp" ]]; then
        mp="/run/mios-stage/$lbl"
        if (( DRY_RUN )); then
            log_info "[dry-run] would mount $dev -> $mp"
        else
            mkdir -p "$mp"; mount "$dev" "$mp" || { printf ''; return 0; }
        fi
    fi
    printf '%s\n' "$mp"
}

# stage_file SRC DEST -- idempotent 0644 install with a dry-run echo.
stage_file() {
    local src="$1" dest="$2"
    if (( DRY_RUN )); then
        log_info "[dry-run] would stage $src -> $dest"
        return 0
    fi
    install -Dm0644 "$src" "$dest"
}

# first_glob PATTERN... -- echo the first existing file across the given globs.
first_glob() {
    local g f
    for g in "$@"; do
        for f in $g; do
            [[ -f "$f" ]] && { printf '%s\n' "$f"; return 0; }
        done
    done
    return 0
}

# ============================================================================
# Locate the target partitions (label -> mountpoint). Degrade-open: a small
# single-partition stick has no MiOS-Data, so bulk artifacts fold onto MiOS-Repo.
# ============================================================================
log_phase "MiOS USB artifact stager"
REPO_MP="${MIOS_REPO_MP:-$(mnt_for_label "$REPO_LABEL")}"
DATA_MP="${MIOS_DATA_MP:-$(mnt_for_label "$DATA_LABEL")}"
[[ -z "$DATA_MP" ]] && DATA_MP="$REPO_MP"   # single-partition stick (degrade-open)
[[ -z "$REPO_MP" ]] && die "no '$REPO_LABEL' partition found -- run MiOS-Cat to prepare the USB first."

log_info "ROOT=$ROOT  VERSION=$VERSION  BUILD=$BUILD"
log_info "$REPO_LABEL -> $REPO_MP"
log_info "$DATA_LABEL -> $DATA_MP"
(( DRY_RUN )) && log_warn "DRY-RUN: no changes will be written."

# ============================================================================
# 1. Brain: mios.toml SSOT + the from-SSOT loopback menu (always, even tiny sticks)
# ============================================================================
if [[ -f "$SSOT" ]]; then
    stage_file "$SSOT" "$REPO_MP/mios.toml"
    log_ok "staged brain: mios.toml"
else
    log_warn "vendor SSOT $SSOT missing -- brain mios.toml not staged"
fi
if (( DRY_RUN )); then
    log_info "[dry-run] would render loopback -> $REPO_MP/ventoy/mios-loopback.cfg"
else
    mkdir -p "$REPO_MP/ventoy"
    render_loopback > "$REPO_MP/ventoy/mios-loopback.cfg"
fi
log_ok "staged boot menu: ventoy/mios-loopback.cfg"

# ============================================================================
# 2. OCI archive (Path B source) -- same /mios-latest.tar name tools/install.sh
#    + mios-stage-oci-archive default to, and drift-check 81 pins.
# ============================================================================
SRC_TAR="$BUILD/oci-archive/mios-${VERSION}.tar"
if [[ -f "$SRC_TAR" ]]; then
    stage_file "$SRC_TAR" "$REPO_MP/mios-latest.tar"
    log_ok "staged oci-archive -> $REPO_MP/mios-latest.tar"
else
    log_warn "$SRC_TAR missing -- run 'just oci-archive' (Path B / bootc install unavailable)"
fi

# ============================================================================
# 3. Anaconda-bootc installer ISO (Path A boot target) -- 'just iso' output.
# ============================================================================
ISO_SRC="$(first_glob "$BUILD/iso/*.iso" "$BUILD/bootiso/*.iso" "$BUILD/usb-installer/*.iso")"
if [[ -n "$ISO_SRC" ]]; then
    stage_file "$ISO_SRC" "$DATA_MP/Live_Operating_Systems/MiOS.iso"
    log_ok "staged installer ISO -> $DATA_MP/Live_Operating_Systems/MiOS.iso"
else
    log_warn "no build/iso/*.iso -- run 'just iso' (Path A / immutable installer unavailable)"
fi

# ============================================================================
# 4. VM disk images (raw/qcow2/vhdx) -- only when a real MiOS-Data bulk store
#    exists (a copy-to-host / boot-a-VM-from-stick flow); skipped on tiny sticks.
# ============================================================================
if [[ "$DATA_MP" != "$REPO_MP" ]]; then
    for pair in "raw:disk.raw:*.raw" "qcow2:disk.qcow2:*.qcow2" "vhdx:disk.vhdx:*.vhdx" "vhdx:disk.vhd:*.vhd"; do
        subdir="${pair%%:*}"; rest="${pair#*:}"; out="${rest%%:*}"; glob="${rest#*:}"
        f="$(first_glob "$BUILD/$subdir/$glob")"
        if [[ -n "$f" ]]; then
            stage_file "$f" "$DATA_MP/images/$out"
            log_ok "staged VM image -> $DATA_MP/images/$out"
        fi
    done
else
    log_info "single-partition stick -- skipping bulk VM disk images (no $DATA_LABEL)."
fi

# ============================================================================
# 5. Shallow git brain (offline overlay source for the kickstart) -- opt-out.
# ============================================================================
if [[ "${MIOS_STAGE_REPOS:-1}" == "1" && -d "$ROOT/.git" ]] && command -v git >/dev/null 2>&1; then
    if (( DRY_RUN )); then
        log_info "[dry-run] would stage git archive HEAD -> $REPO_MP/repos/MiOS"
    else
        mkdir -p "$REPO_MP/repos/MiOS"
        git -C "$ROOT" archive --format=tar HEAD | tar -x -C "$REPO_MP/repos/MiOS"
        log_ok "staged MiOS tree (git archive HEAD) -> $REPO_MP/repos/MiOS"
    fi
else
    log_info "shallow git brain skipped (MIOS_STAGE_REPOS=0 or not a git checkout)."
fi

# ============================================================================
# Flush and report.
# ============================================================================
if (( DRY_RUN )); then
    log_ok "DRY-RUN complete -- no changes written."
else
    sync
    log_ok "DONE. Boot the USB -> 'Install MiOS (Immutable bootc Workstation & Agentic AI OS)'."
fi
