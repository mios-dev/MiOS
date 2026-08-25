#!/usr/bin/env bash
# AI-hint: bash The MISSING USB staging bridge -- stages every built immutable-MiOS artifact (oci-archive tar, Anaconda-bootc installer ISO, raw/qcow2/vhdx ...
# AI-doc: usr/share/doc/mios/manual/installation.md
set -euo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MIOS_ROOT:-$(cd "$SELF/.." && pwd)}"
BUILD="${MIOS_BUILD_DIR:-$ROOT/build}"
SSOT="$ROOT/usr/share/mios/mios.toml"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null || echo 0.3.0)"

_MIOS_REPO_ROOT="$ROOT/usr/share/mios"
if [[ -f "$SELF/mios-common.sh" ]]; then
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
        *) die "Unknown option: $1" ;;
    esac
done

REPO_LABEL="$(mios_ssot_value 'cat.repo_partition' 'label' 'MiOS-Repo')"
DATA_LABEL="$(mios_ssot_value 'cat.data_partition' 'label' 'MiOS-Data')"


render_loopback() {
    local tmpl="$ROOT/cat/loopback.cfg"
    if [[ -f "$tmpl" ]]; then
        sed -e "s/@@REPO_LABEL@@/${REPO_LABEL}/g" \
            -e "s/@@DATA_LABEL@@/${DATA_LABEL}/g" \
            "$tmpl"
    else
        die "Template $tmpl missing at cat/loopback.cfg"
    fi
}

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

stage_file() {
    local src="$1" dest="$2"
    if (( DRY_RUN )); then
        log_info "[dry-run] would stage $src -> $dest"
        return 0
    fi
    install -Dm0644 "$src" "$dest"
}

first_glob() {
    local g f
    for g in "$@"; do
        for f in $g; do
            [[ -f "$f" ]] && { printf '%s\n' "$f"; return 0; }
        done
    done
    return 0
}

log_phase "MiOS USB artifact stager"
REPO_MP="${MIOS_REPO_MP:-$(mnt_for_label "$REPO_LABEL")}"
DATA_MP="${MIOS_DATA_MP:-$(mnt_for_label "$DATA_LABEL")}"
[[ -z "$DATA_MP" ]] && DATA_MP="$REPO_MP"   # single-partition stick (degrade-open)
[[ -z "$REPO_MP" ]] && die "No '$REPO_LABEL' partition found"

log_info "ROOT=$ROOT  VERSION=$VERSION  BUILD=$BUILD"
log_info "$REPO_LABEL -> $REPO_MP"
log_info "$DATA_LABEL -> $DATA_MP"
(( DRY_RUN )) && log_warn "DRY-RUN: no changes will be written."

if [[ -f "$SSOT" ]]; then
    stage_file "$SSOT" "$REPO_MP/mios.toml"
    log_ok "staged brain: mios.toml"
else
    log_warn "vendor SSOT $SSOT missing -- brain mios.toml not staged"
fi
if (( DRY_RUN )); then
    log_info "[dry-run] would render loopback -> $REPO_MP/ventoy/mios-loopback.cfg and $DATA_MP/ventoy/ventoy_grub.cfg"
else
    mkdir -p "$REPO_MP/ventoy" "$DATA_MP/ventoy"
    render_loopback > "$REPO_MP/ventoy/mios-loopback.cfg"
    render_loopback > "$DATA_MP/ventoy/ventoy_grub.cfg"
fi
log_ok "staged boot menu: ventoy/mios-loopback.cfg and ventoy/ventoy_grub.cfg"

KS_SRC="$ROOT/usr/share/mios/ventoy/mios-oci-install.ks"
if [[ -f "$KS_SRC" ]]; then
    stage_file "$KS_SRC" "$REPO_MP/ventoy/mios-oci-install.ks"
    log_ok "staged Kickstart -> $REPO_MP/ventoy/mios-oci-install.ks"
else
    log_err "$KS_SRC missing -- Kickstart payload unavailable"
    exit 1
fi

SRC_TAR="$BUILD/oci-archive/mios-${VERSION}.tar"
if [[ -f "$SRC_TAR" ]]; then
    stage_file "$SRC_TAR" "$REPO_MP/mios-latest.tar"
    log_ok "staged oci-archive -> $REPO_MP/mios-latest.tar"
else
    log_err "$SRC_TAR missing -- run 'just oci-archive' (Path B / bootc install unavailable)"
    exit 1
fi

ISO_SRC="$(first_glob "$BUILD/iso/*.iso" "$BUILD/bootiso/*.iso" "$BUILD/usb-installer/*.iso")"
if [[ -n "$ISO_SRC" ]]; then
    stage_file "$ISO_SRC" "$DATA_MP/Live_Operating_Systems/MiOS.iso"
    log_ok "staged installer ISO -> $DATA_MP/Live_Operating_Systems/MiOS.iso"
else
    log_warn "no build/iso/*.iso -- run 'just iso' (Path A / immutable installer unavailable)"
fi

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

if (( DRY_RUN )); then
    log_ok "DRY-RUN complete -- no changes written."
else
    sync
    log_ok "DONE. Boot the USB -> 'Install MiOS (Immutable bootc Workstation & Agentic AI OS)'."
fi
