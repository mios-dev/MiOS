#!/usr/bin/env bash
# AI-hint: W10 (MiOS-Cat zero-install live-USB-to-AI-chat) build leg. Sibling
# AI-related: config/artifacts/live-chat.toml, usr/share/mios/live-chat/overlay/,
set -euo pipefail

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="$(cd "$_self_dir/../.." && pwd)"

source "$_self_dir/../lib/common.sh" 2>/dev/null || {
    printf '[live-iso] WARN: automation/lib/common.sh unavailable -- skipping build\n' >&2
    exit 0
}

OUT_DIR="${1:-${ROOT}/output/live-chat}"
LOCAL_IMAGE="${MIOS_LOCAL_TAG:-localhost/mios:latest}"
CUDA_IMAGE="${MIOS_CUDA_TAG:-localhost/mios-cuda:latest}"
CONF="${ROOT}/config/artifacts/live-chat.toml"
OVERLAY_ROOT="${ROOT}/usr/share/mios/live-chat/overlay"
STAGED_TAG="localhost/mios-live-chat-staged:$$"
BUILD_CTR="mios-live-chat-build-$$"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/mios-live-iso.XXXXXX")"
cleanup() {
    local rc=$?
    podman rm -f "$BUILD_CTR" >/dev/null 2>&1 || true
    podman rmi -f "$STAGED_TAG" >/dev/null 2>&1 || true
    rm -rf "$WORK"
    exit "$rc"
}
trap cleanup EXIT

for bin in podman python3 curl sha256sum xorriso mkfs.vfat mcopy mmd; do
    command -v "$bin" >/dev/null 2>&1 || die "Live-iso: required tool '$bin' not on PATH"
done
podman image exists "$LOCAL_IMAGE" || die "Live-iso: $LOCAL_IMAGE not found"
podman image exists "$CUDA_IMAGE"  || die "Live-iso: $CUDA_IMAGE not found"
[[ -f "$CONF" ]] || die "Live-iso: missing $CONF"

log "Live-iso: resolving [cat.live_chat] SSOT from mios.toml"
_ssot="$(MIOS_TOML_ROOT="$ROOT" PYTHONPATH="${ROOT}/usr/lib/mios:${PYTHONPATH:-}" python3 - <<'PY'
import mios_toml as mt

def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"')

data = mt.load_merged()
lc = mt.section(data, "cat.live_chat")
llamacpp = mt.section(data, "llamacpp")

fields = {
    "LIVE_CHAT_ENABLED": lc.get("enabled", True),
    "LIVE_CHAT_MODEL": lc.get("model", "lfm2-700m"),
    "LIVE_CHAT_MODEL_FALLBACK": lc.get("model_fallback", ""),
    "LIVE_CHAT_PORT": lc.get("port", 8642),
    "LIVE_CHAT_CTX_SIZE": lc.get("ctx_size", 8192),
    "LIVE_CHAT_THREADS": lc.get("threads", 0),
    "LIVE_CHAT_ISO_NAME": lc.get("iso_name", "MiOS-Live-Chat.iso"),
    "LLAMACPP_BAKE_MODELS": llamacpp.get("bake_models", ""),
}
for k, v in fields.items():
    print(f'{k}="{esc(v)}"')

c = mt.colors(data)
print(f'LIVE_CHAT_COLOR_ACCENT="{esc(c["accent"])}"')
print(f'LIVE_CHAT_COLOR_SUCCESS="{esc(c["success"])}"')
print(f'LIVE_CHAT_COLOR_ERROR="{esc(c["error"])}"')
print(f'LIVE_CHAT_COLOR_MUTED="{esc(c["muted"])}"')
PY
)"
[[ -n "$_ssot" ]] || die "Live-iso: mios_toml.py resolved nothing"
eval "$_ssot"

LIVE_CHAT_ENABLED="$(printf '%s' "$LIVE_CHAT_ENABLED" | tr '[:upper:]' '[:lower:]')"
case "$LIVE_CHAT_ENABLED" in
    false|0|no|"") log "Live-iso: [cat.live_chat].enabled is off"; trap - EXIT; rm -rf "$WORK"; exit 0 ;;
esac

resolve_model_entry() { # $1 = short key (e.g. "lfm2-700m") -> prints "dest\trepo\tfile"
    local key="$1" entry dest rest repo file
    IFS=',' read -ra _entries <<< "$LLAMACPP_BAKE_MODELS"
    for entry in "${_entries[@]}"; do
        entry="$(printf '%s' "$entry" | tr -d '[:space:]')"
        [[ -z "$entry" ]] && continue
        dest="${entry%%=*}"
        rest="${entry#*=}"
        [[ "${dest%.gguf}" == "$key" ]] || continue
        repo="${rest%%:*}"
        file="${rest#*:}"
        printf '%s\t%s\t%s\n' "$dest" "$repo" "$file"
        return 0
    done
    return 1
}

PRIMARY_ENTRY="$(resolve_model_entry "$LIVE_CHAT_MODEL")" \
    || die "Live-iso: [cat.live_chat].model = '${LIVE_CHAT_MODEL}' has no matching entry in [llamacpp].bake_models"
IFS=$'\t' read -r PRIMARY_DEST PRIMARY_REPO PRIMARY_FILE <<< "$PRIMARY_ENTRY"

FALLBACK_DEST="" FALLBACK_REPO="" FALLBACK_FILE=""
if [[ -n "$LIVE_CHAT_MODEL_FALLBACK" ]]; then
    if FALLBACK_ENTRY="$(resolve_model_entry "$LIVE_CHAT_MODEL_FALLBACK")"; then
        IFS=$'\t' read -r FALLBACK_DEST FALLBACK_REPO FALLBACK_FILE <<< "$FALLBACK_ENTRY"
    else
        warn "Live-iso: model_fallback '${LIVE_CHAT_MODEL_FALLBACK}' not in bake_models"
    fi
fi

lc_get() { # $1=key $2=default
    local v
    v="$(grep -E "^[[:space:]]*${1}[[:space:]]*=" "$CONF" | head -1 | sed -E 's/^[^=]*=[[:space:]]*//')"
    v="${v%\"}"; v="${v#\"}"
    printf '%s' "${v:-$2}"
}
VOLUME_LABEL="$(lc_get volume_label MIOSLIVE)"
DRACUT_MODULES="$(lc_get dracut_modules dmsquash-live)"
DRACUT_DRIVERS="$(lc_get dracut_drivers "ahci nvme sd_mod usb_storage uas xhci_hcd ehci_hcd sdhci_pci virtio_blk virtio_scsi virtio_net e1000e r8169 iwlwifi")"
KERNEL_ARGS_EXTRA="$(lc_get kernel_args_extra "quiet rd.live.overlay.overlayfs=1 rd.live.ram=1 enforcing=0")"

mkdir -p "$OUT_DIR" "${WORK}/models" "${WORK}/iso" "${WORK}/out"

stage_model() { # $1=dest $2=repo $3=file
    local dest="$1" repo="$2" file="$3" out="${WORK}/models/${1}"
    [[ -s "$out" ]] && return 0
    log "Live-iso: staging ${dest}"
    if podman run --rm --entrypoint cat "$LOCAL_IMAGE" "/usr/share/mios/llamacpp/models/${dest}" > "${out}.part" 2>/dev/null \
       && [[ -s "${out}.part" ]]; then
        mv -f "${out}.part" "$out"
        log "Live-iso: ${dest} reused from baked ${LOCAL_IMAGE} image"
        record_version "live-chat:${dest}" "baked" "${LOCAL_IMAGE}"
        return 0
    fi
    rm -f "${out}.part"
    local url="https://huggingface.co/${repo}/resolve/main/${file}"
    log "Live-iso: ${dest} not baked in the base image"
    curl -fL -C - --retry 3 --max-time 1800 -o "${out}.part" "$url" && [[ -s "${out}.part" ]] \
        || die "Live-iso: failed to obtain ${dest}"
    mv -f "${out}.part" "$out"
    record_version "live-chat:${dest}" "${repo}:${file}" "$url"
}
stage_model "$PRIMARY_DEST" "$PRIMARY_REPO" "$PRIMARY_FILE"
[[ -n "$FALLBACK_DEST" ]] && stage_model "$FALLBACK_DEST" "$FALLBACK_REPO" "$FALLBACK_FILE"

for f in "${WORK}"/models/*; do
    sha256sum "$f" >> "${OUT_DIR}/$(basename "${LIVE_CHAT_ISO_NAME%.iso}").sbom.sha256"
done

log "Live-iso: extracting llama-server from ${CUDA_IMAGE}"
podman run --rm --entrypoint cat "$CUDA_IMAGE" /usr/bin/llama-server > "${WORK}/llama-server" \
    && [[ -s "${WORK}/llama-server" ]] || die "Live-iso: could not extract /usr/bin/llama-server from ${CUDA_IMAGE}"
chmod 0755 "${WORK}/llama-server"

cat > "${WORK}/live-chat.conf" <<EOF
LIVE_CHAT_MODEL_PATH=/usr/share/mios/live-chat/models/${PRIMARY_DEST}
LIVE_CHAT_MODEL_NAME=${LIVE_CHAT_MODEL}
LIVE_CHAT_FALLBACK_MODEL_PATH=${FALLBACK_DEST:+/usr/share/mios/live-chat/models/${FALLBACK_DEST}}
LIVE_CHAT_FALLBACK_MODEL_NAME=${LIVE_CHAT_MODEL_FALLBACK}
LIVE_CHAT_PORT=${LIVE_CHAT_PORT}
LIVE_CHAT_CTX_SIZE=${LIVE_CHAT_CTX_SIZE}
LIVE_CHAT_THREADS=${LIVE_CHAT_THREADS}
LIVE_CHAT_ENDPOINT=http://127.0.0.1:${LIVE_CHAT_PORT}/v1
LIVE_CHAT_COLOR_ACCENT=${LIVE_CHAT_COLOR_ACCENT}
LIVE_CHAT_COLOR_SUCCESS=${LIVE_CHAT_COLOR_SUCCESS}
LIVE_CHAT_COLOR_ERROR=${LIVE_CHAT_COLOR_ERROR}
LIVE_CHAT_COLOR_MUTED=${LIVE_CHAT_COLOR_MUTED}
EOF

log "Live-iso: staging live-only overlay onto a throwaway copy of ${LOCAL_IMAGE}"
podman create --name "$BUILD_CTR" --entrypoint '["true"]' "$LOCAL_IMAGE" >/dev/null

podman cp "${WORK}/llama-server" "${BUILD_CTR}:/usr/libexec/mios/llama-server"
podman cp "${WORK}/live-chat.conf" "${BUILD_CTR}:/etc/mios/live-chat.conf"
for f in "${WORK}"/models/*; do
    podman cp "$f" "${BUILD_CTR}:/usr/share/mios/live-chat/models/$(basename "$f")"
done
podman cp "${OVERLAY_ROOT}/." "${BUILD_CTR}:/"

podman commit --quiet "$BUILD_CTR" "$STAGED_TAG" >/dev/null
podman rm -f "$BUILD_CTR" >/dev/null
log "Live-iso: staged image ${STAGED_TAG} ready"

log "Live-iso: regenerating dmsquash-live initramfs + squashing rootfs"
sudo podman run --rm --privileged \
    -v "${WORK}/out:/live-out:Z" \
    -e DRACUT_MODULES="$DRACUT_MODULES" \
    -e DRACUT_DRIVERS="$DRACUT_DRIVERS" \
    "$STAGED_TAG" bash -euo pipefail -c '
        kver="$(basename "$(ls -d /usr/lib/modules/*/ 2>/dev/null | sort -V | tail -1)")"
        [[ -n "$kver" ]] || { echo "No /usr/lib/modules/<kver> found in staged image" >&2; exit 1; }
        echo "[live-iso/ctr] kernel version: ${kver}"

        mkdir -p /live-out/LiveOS
        dracut --force --no-hostonly \
            --add "$DRACUT_MODULES" \
            --add-drivers "$DRACUT_DRIVERS" \
            "/live-out/initrd.img" "$kver"

        cp -a "/usr/lib/modules/${kver}/vmlinuz" /live-out/vmlinuz

        echo "[live-iso/ctr] mksquashfs"
        mksquashfs / /live-out/LiveOS/squashfs.img \
            -comp zstd -Xcompression-level 15 -no-progress \
            -e proc sys dev run tmp live-out
    '

log "Live-iso: assembling hybrid BIOS+UEFI ISO"
mkdir -p "${WORK}/iso/LiveOS" "${WORK}/iso/EFI/BOOT" "${WORK}/iso/images"
cp "${WORK}/out/LiveOS/squashfs.img" "${WORK}/iso/LiveOS/squashfs.img"
cp "${WORK}/out/vmlinuz"             "${WORK}/iso/vmlinuz"
cp "${WORK}/out/initrd.img"          "${WORK}/iso/initrd.img"

KARGS="root=live:CDLABEL=${VOLUME_LABEL} rd.live.image rd.live.dir=LiveOS rd.live.squashimg=squashfs.img ${KERNEL_ARGS_EXTRA} console=tty0"

SHIM_SRC="$(find /boot/efi/EFI -maxdepth 1 -iname 'shimx64.efi' -print -quit 2>/dev/null || true)"
if [[ -n "$SHIM_SRC" ]]; then
    VENDOR_DIR="$(dirname "$SHIM_SRC")"
    GRUB_SRC="$(find "$VENDOR_DIR" -maxdepth 1 -iname 'grubx64.efi' -print -quit 2>/dev/null || true)"
    MM_SRC="$(find "$VENDOR_DIR" -maxdepth 1 -iname 'mmx64.efi' -print -quit 2>/dev/null || true)"
    [[ -n "$GRUB_SRC" ]] || die "Live-iso: found $SHIM_SRC but no grubx64.efi beside it in $VENDOR_DIR"
    log "Live-iso: reusing this host's signed shim/grub from $VENDOR_DIR"
    cp "$SHIM_SRC" "${WORK}/iso/EFI/BOOT/BOOTX64.EFI"
    cp "$GRUB_SRC" "${WORK}/iso/EFI/BOOT/grubx64.efi"
    [[ -n "$MM_SRC" ]] && cp "$MM_SRC" "${WORK}/iso/EFI/BOOT/mmx64.efi"
    USE_SIGNED_SHIM=1
else
    warn "Live-iso: no shim-x64/grub2-efi-x64 found on this build host under /boot/efi/EFI"
    command -v grub2-mkrescue >/dev/null 2>&1 || die "Live-iso: neither a host shim NOR grub2-mkrescue is available"
    USE_SIGNED_SHIM=0
fi

cat > "${WORK}/iso/EFI/BOOT/grub.cfg" <<EOF
set timeout=3
insmod all_video
insmod gfxterm
menuentry "MiOS Live Chat" {
    linux /vmlinuz ${KARGS}
    initrd /initrd.img
}
EOF

EFIBOOT_IMG="${WORK}/iso/images/efiboot.img"
truncate -s 8M "$EFIBOOT_IMG"
mkfs.vfat -n MIOS_EFI "$EFIBOOT_IMG" >/dev/null
mmd -i "$EFIBOOT_IMG" ::EFI ::EFI/BOOT
mcopy -i "$EFIBOOT_IMG" "${WORK}/iso/EFI/BOOT/"* ::EFI/BOOT/

ISO_PATH="${OUT_DIR}/${LIVE_CHAT_ISO_NAME}"
rm -f "$ISO_PATH"
if [[ "$USE_SIGNED_SHIM" -eq 1 ]]; then
    ISOHDPFX="$(find /usr/share/syslinux /usr/lib/syslinux -iname 'isohdpfx.bin' -print -quit 2>/dev/null || true)"
    xorriso_bios_args=()
    if [[ -n "$ISOHDPFX" ]]; then
        xorriso_bios_args=(-isohybrid-mbr "$ISOHDPFX")
    else
        warn "Live-iso: isohdpfx.bin not found"
    fi
    xorriso -as mkisofs \
        -V "$VOLUME_LABEL" \
        -o "$ISO_PATH" \
        -eltorito-alt-boot \
        -e images/efiboot.img -no-emul-boot \
        "${xorriso_bios_args[@]}" \
        -isohybrid-gpt-basdat \
        -r -J -joliet-long \
        "${WORK}/iso"
else
    grub2-mkrescue -o "$ISO_PATH" "${WORK}/iso" -- -V "$VOLUME_LABEL"
fi
[[ -s "$ISO_PATH" ]] || die "Live-iso: ISO assembly produced no output at $ISO_PATH"

sha256sum "$ISO_PATH" | tee "${ISO_PATH}.sha256"
record_version "live-chat-iso" "$LIVE_CHAT_MODEL" "$ISO_PATH"
log "Live-iso: done"
log "Live-iso: stage into MiOS-Cat via Live_Operating_Systems\\${LIVE_CHAT_ISO_NAME}"
exit 0
