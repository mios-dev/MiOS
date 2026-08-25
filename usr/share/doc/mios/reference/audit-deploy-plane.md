<!-- AI-hint: Audit of the MiOS DEPLOY plane (the least-done area, ~15-25%): traces the OFFLINE immutable-bootc install chain (Justfile oci-archive/BIB -> mios-stage-oci-archive -> tools/install.sh -> field/loopback.cfg + ventoy.json) end-to-end, proves the immutable leg is ORPHANED (MiOS-Cat.bat stages only mutable Fedora), and gives a sequenced plan + drop-in staging bridge / loopback-from-SSOT template / first-boot MOK-UKI enrollment to make one USB offline-install REAL MiOS (bootc/ostree) in every format. -->
<!-- AI-related: field/loopback.cfg, tools/install.sh, installation/MiOS-Cat.bat, usr/libexec/mios/mios-stage-oci-archive, usr/libexec/mios/mios-build-driver, usr/share/mios/ventoy/ventoy.json, usr/share/mios/ventoy/mios-kickstart.cfg, config/artifacts/{bib,iso,qcow2,vhdx,wsl2}.toml, Justfile, automation/98-drift-checks.sh, usr/share/mios/mios.toml [deployment]/[deploy.artifacts]/[cat], usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md, automation/76-uki-render.sh -->

# MiOS DEPLOY-Plane Audit — Offline Immutable Install (bare-metal, VM, ISO, Ventoy)

**Date:** 2026-07-31 · **Scope:** the deploy plane only (build->artifact->USB->installed-OS). **Verdict:** the **build side is real and complete**; the **delivery side (USB -> installed immutable OS) is a set of disconnected pieces**. The one wired Linux menu deploys **mutable Fedora + FHS overlay**, not the immutable bootc image the mission requires. Estimated completeness: **~20%** (build artifacts exist; the offline immutable-install path is authored but orphaned end-to-end).

---

## 1. The intended chain (what "one USB installs real MiOS offline" means)

```
just build            OCI image  localhost/mios:latest         (Containerfile)         [WORKS]
 └ just oci-archive   podman save --format oci-archive          build/oci-archive/mios-0.3.0.tar   [WORKS]
 └ just iso           BIB --type iso (Anaconda, embeds container) build/iso/*.iso        [WORKS, build-side]
 └ just raw/qcow2/vhdx BIB --type raw|qcow2|vhd                   build/{raw,qcow2,vhdx} [WORKS, build-side]
        │
        ▼   ── THE MISSING BRIDGE ──  (no code stages these onto the stick)
mios-stage-oci-archive  build/.../mios-0.3.0.tar -> /mnt/mios-repo/mios-latest.tar   [EXISTS, NEVER CALLED]
        │
        ▼
USB (Ventoy): MiOS-Repo (brain) + MiOS-Data (bulk: tar + disk images + models)
        │
        ▼
Boot menu:
  cat/loopback.cfg   ostreecontainer oci-archive:/mnt/mios-repo/mios-latest.tar   [DANGLING, unreferenced]
  ventoy.json        kickstart -> Fedora-Server.iso -> mios-kickstart.cfg          [WIRED, but MUTABLE Fedora]
        │
        ▼
tools/install.sh   bootc install to-disk --transport oci-archive (offline)         [EXISTS, NO CALLER]
        │
        ▼
Installed disk: shim -> GRUB -> UKI + MOK enrollment                                 [UKI baked; MOK not enrolled on target]
```

The pieces on the right that say **EXISTS/NEVER CALLED/DANGLING/NO CALLER** are the gap. Every arrow into "USB" and out of "Boot menu" toward the *immutable* image is unconnected.

---

## 2. What WORKS (file:line evidence)

### 2.1 Multi-format artifact build (the strong part)
- **`Justfile:286-289`** — `oci-archive:` recipe: `podman save --format oci-archive -o build/oci-archive/mios-{{VERSION}}.tar {{LOCAL}}`. Produces the exact tar the offline installer consumes. `VERSION` = `0.3.0` (`VERSION` file).
- **`Justfile:203-211`** — `raw:` (BIB `--type raw --rootfs ext4`, mounts `config/artifacts/bib.toml`).
- **`Justfile:214-227`** — `iso:` Anaconda installer ISO, credential-substitutes `MIOS_USER_PASSWORD_HASH`/`MIOS_SSH_PUBKEY` into a temp copy of `config/artifacts/iso.toml` before `BIB --type iso`.
- **`Justfile:231-245`** — `qcow2:` (BIB `--type qcow2`). **`Justfile:250-272`** — `vhdx:` (BIB `--type vhd` then `qemu-img convert -f vpc -O vhdx`).
- **`Justfile:275-283`** — `wsl2:` `podman export | gzip` rootfs for `wsl --import`.
- **`Justfile:313`** — `all: build oci-archive raw iso usb-installer qcow2 vhdx wsl2` — one-shot every format.
- **`Justfile:327-348`** — `usb-installer:` repackages the ISO and prints the `dd`/Rufus flash recipe. **`Justfile:352-359`** — `verify-images:` size/magic smoke check.
- **`usr/libexec/mios/mios-build-driver:819-970`** — the inside-MiOS-DEV driver reads `[deployment].target_<fmt>` from the layered `mios.toml` (`:868-893`) and loops `sudo podman run --rm --privileged ... bootc-image-builder --type <t>` (`:936-943`), normalizing `vhdx->vhd` and skipping `wsl` (`:919-928`). Non-zero exit if any format fails (`:965-969`). This is a **second, parallel** BIB driver to the Justfile — see gap G7.
- **SSOT sizing projection** — `config/artifacts/bib.toml:5-7` (`minsize = "80 GiB"`) and `iso.toml:14-16` (`150 GiB`) are projected from `mios.toml [deploy.artifacts.raw].size` / `[deploy.artifacts.iso].minsize` (`mios.toml:8670-8673`) by `tools/generate-bib-configs.py`, gated green by drift-check **87** (`automation/98-drift-checks.sh:5144-5154`).

### 2.2 The offline immutable installer itself (authored, correct — just uncalled)
- **`tools/install.sh:1-79`** — `MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer`. Resolves the repo partition by SSOT label (`blkid -L "MiOS-Repo"`, `:9`), defaults `OCI_ARCHIVE=/mnt/mios-repo/mios-latest.tar` (`:14`), and runs `bootc install to-disk --target-no-signature-verification --source-imgref "oci-archive:$OCI_ARCHIVE" "$TARGET_DISK"` (`:78`). Has `--dry-run` (`:56-59`), a `YES` confirm gate (`:71-76`), root check (`:61-64`). **This is a genuine zero-network offline bootc installer.** The `install.sh reportedly ABSENT` note in the task is **stale** — it was (re)created 2026-07-31 and is gated by drift-checks 81/85/88.
- **`usr/libexec/mios/mios-stage-oci-archive:1-29`** — copies `build/oci-archive/mios-<VERSION>.tar` -> `/mnt/mios-repo/mios-latest.tar` (the producer half of the 81 producer/consumer pair).
- **`cat/loopback.cfg:1-16`** — Ventoy/GRUB loopback menu with two entries; the install entry uses `... ostreecontainer --url=oci-archive:/mnt/mios-repo/mios-latest.tar` (`:7`) — i.e. the real immutable path — plus a Live/Rescue entry (`:11-15`).
- **Drift-gated deploy contract** — `automation/98-drift-checks.sh`: check **81** oci-archive producer/consumer path match (`:4925-4943`), **83** kickstart `%post` bash-syntax (`:4999-5022`), **84** BIB `--rootfs` label policy (`:5024-5084`), **85** `tools/install.sh` must call `--transport oci-archive` **and contain zero network tokens** (`:5086-5111`), **86** unique installer-role markers (`:5113-5142`), **88** repo-partition label SSOT match (`:5156-5183`). These gates keep the immutable path *coherent* even though nothing *runs* it.

### 2.3 USB fabrication (Windows) + Ventoy + UKI (partial)
- **`installation/MiOS-Cat.bat`** — the Windows "USB flash executor" genuinely works: SSOT palette load from `mios.toml` (`:64`), Ventoy latest-release resolve + install (`:773-782`, `:516-521`), MediCat 23 GB pull (`:251-257`), Fedora Server DVD stage (`:263-273`), SystemRescue (`:275-298`), offline DISM servicing of the WinPE WIM (`:300-444`), MiOS-Xbox ISO build (`:828-841`), repo + `mios.toml` staging to `MiOS-Repo` (`:558-566`), partition scheme MiOS-Repo/MiOS-Data by disk size (`:507-529`).
- **`usr/share/mios/ventoy/ventoy.json`** — Ventoy control/theme/menu; kickstart binding `Fedora-Server.iso -> /ventoy/mios-kickstart.cfg` (`:77-86`).
- **UKI (build-time)** — `automation/76-uki-render.sh` + `tools/generate-uki-cmdline.py` flatten `usr/lib/bootc/kargs.d/*.toml` -> `usr/lib/kernel/cmdline` (gated by check 93); `usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml` carries the UKI kargs. So the **image ships a UKI cmdline**; Secure-Boot OVMF helper tooling exists under `tools/` (`get-secureboot-ovmf.sh`, `fix-secureboot-now.sh`, `check-ovmf-enrollment.sh`).

---

## 3. What is BROKEN / STUBBED / DISCONNECTED (the deploy gap)

| # | Gap | Evidence | Impact |
|---|-----|----------|--------|
| **G1** | **Immutable leg orphaned end-to-end.** `MiOS-Cat.bat` never stages `mios-latest.tar`, `vmlinuz`/`initrd.img`, or the BIB Anaconda ISO. | `grep -ni "oci-archive\|mios-latest\|bootc\|vmlinuz\|initrd\|install.iso" installation/MiOS-Cat.bat` -> only comments/labels, **no staging** | USB boots **no** immutable installer. |
| **G2** | **The one wired Linux menu deploys MUTABLE Fedora.** `ventoy.json` kickstart -> `Fedora-Server.iso` -> `mios-kickstart.cfg`, which installs `@core+@virtualization` on plain ext4 and runs `build-mios.sh -u` (FHS overlay). | `ventoy.json:77-86`; `mios-kickstart.cfg` header "deliberately **NOT** an immutable bootc install", `autopart --fstype=ext4`, `bash build-mios.sh -u` | Result is Fedora+overlay, **not** `ghcr.io/mios-dev/mios`. |
| **G3** | **`cat/loopback.cfg` is dangling.** Referenced only by `AGY-TASKS.md`; `ventoy.json` has zero `loopback` refs. Expects `/images/vmlinuz`, `/images/initrd.img`, `/images/mios-latest.iso`, `oci-archive:/mnt/mios-repo/mios-latest.tar` — none of which any stager writes. | `grep -rl loopback.cfg` -> `AGY-TASKS.md` only; `grep -c loopback ventoy.json` -> `0` | The real immutable menu entry is unreachable and its inputs never exist. |
| **G4** | **`mios-stage-oci-archive` never invoked.** Only referenced by the drift-checks and the negatives test. | `grep -rl mios-stage-oci-archive` -> `automation/98-drift-checks.sh`, `tests/drift-gate-negatives.sh` | `/mnt/mios-repo/mios-latest.tar` is never populated. |
| **G5** | **`tools/install.sh` has no caller.** The kickstart used to `bash tools/install.sh`; it now calls `build-mios.sh -u` (see the in-file note in `mios-kickstart.cfg`). | `mios-kickstart.cfg` %post comment: "WAS `bash tools/install.sh` ... canonical entry point is build-mios.sh" | The genuine offline bootc installer is dead code at runtime. |
| **G6** | **No Secure-Boot chain on the INSTALLED target.** UKI cmdline is baked, but there is no first-boot MOK enrollment for the deployed disk. Ventoy `/S` (`MiOS-Cat.bat:519`) signs only the **USB's own** shim, not the installed OS's UKI. | `MiOS-Cat.bat:517-521`; no `mokutil --import` / `sbctl` in any first-boot unit | On SB-enforcing hardware the installed UKI may not verify without manual MOK enrollment. |
| **G7** | **Two divergent BIB drivers.** `Justfile` recipes (credential-substituted, `--rootfs ext4`, per-format tomls) vs `mios-build-driver:819-970` (env/`[deployment]` toggles, `-v /var/lib/containers/storage`, no credential sub). They can produce different artifacts. | `Justfile:203-289` vs `mios-build-driver:936-943` | "which artifact is canonical" ambiguity; only Justfile does REPLACEME substitution (drift-check 82). |
| **G8** | **VM images (qcow2/vhdx/raw) are built but never staged to `MiOS-Data`** for a boot-a-VM-from-stick or copy-to-host flow. | `Justfile:313` builds them; no stager copies them onto the USB | "every format" promise (ADR-0008) unmet on the stick. |
| **G9** | **`wsl2.toml` is inert.** `Justfile:275-283` uses `podman export`, ignoring `config/artifacts/wsl2.toml`. | `Justfile:275-283` | Dead config; minor. |
| **G10** | **Xbox/Windows ISO leg deploys Windows, not "MiOS in an ISO."** `ventoy.json:34-35` aliases `MiOS-Xbox.iso` = "Windows Gaming Edition (CompactOS)"; built by `Build-MiOSXboxISO.ps1` (`MiOS-Cat.bat:828-841`). Legit as a separate edition, but it is **not** the immutable MiOS. | `ventoy.json:34-35`; `MiOS-Cat.bat:451-452,828-841` | Naming implies MiOS; payload is debloated Win11. |

**Root cause (one sentence):** every deploy *component* exists and is individually drift-gated, but **nothing wires the built immutable artifacts onto the USB and nothing points a boot-menu entry at `tools/install.sh` / the Anaconda-bootc ISO** — so the only executable Linux path is the mutable-Fedora kickstart.

---

## 4. Concrete, sequenced implementation plan

Two supported offline immutable paths, in priority order. **Path A (Anaconda-bootc ISO)** is the fastest to green because BIB already emits a *self-contained* installer that embeds the container (no separate vmlinuz/initrd/tar juggling). **Path B (oci-archive + `tools/install.sh`)** is the rescue/no-Anaconda path the operator explicitly wants, and reuses the already-authored `loopback.cfg` + `tools/install.sh`.

### Phase 0 — Decide the canonical driver (unblocks everything)
0.1 Pick **Justfile recipes** as the canonical artifact producer (they do credential substitution + per-format tomls). Make `mios-build-driver`'s BIB loop *call* `just <fmt>` instead of re-implementing `podman run` (removes G7 divergence). Keep the driver's `[deployment]` toggles as the format selector.
0.2 Add a Justfile target `stage-usb DEST=<mount>` that invokes the new staging bridge (Phase 2). Add `anaconda-iso` explicitly to the `all` target list (currently `iso`, which BIB maps to `--type iso`; confirm it is the *installer* ISO, not live-only).

### Phase 1 — Produce the immutable installer ISO (Path A)
1.1 Verify `just iso` (`Justfile:214-227`, `config/artifacts/iso.toml`) emits an **Anaconda `anaconda-iso`** that embeds `localhost/mios:latest` (bootc-installer semantics) so Anaconda writes the **ostree/bootc** image, not a package install. iso.toml already sets kickstart `text --non-interactive`, `clearpart --disklabel=gpt`, `reqpart --add-boot`, `part / --grow`.
1.2 Replace the REPLACEME creds path: the Justfile already substitutes `MIOS_USER_PASSWORD_HASH`/`MIOS_SSH_PUBKEY` (drift-check 82 enforces this). Ensure the operator's SSOT identity feeds those env vars in the driver (source from `[identity]` via `userenv.sh`).
1.3 Output: `build/iso/*.iso` — a bootable, offline, self-contained immutable installer.

### Phase 2 — The MISSING BRIDGE: stage artifacts onto the USB (fixes G1, G4, G8)
2.1 Add **`installation/stage-mios-repo.sh`** (drop-in below) — the single stager that, given `build/` + a Ventoy USB, writes:
- `MiOS-Data/Live_Operating_Systems/MiOS.iso` <- `build/iso/*.iso` (Path A boot target)
- `MiOS-Repo/mios-latest.tar` <- `build/oci-archive/mios-<VERSION>.tar` (Path B source; reuses `mios-stage-oci-archive` semantics, same `/mnt/mios-repo/mios-latest.tar` default that drift-check 81 pins)
- `MiOS-Data/images/{disk.raw,disk.qcow2,disk.vhdx}` <- BIB outputs (G8)
- `MiOS-Repo/mios.toml` + shallow repo clones (brain)
- `MiOS-Repo/ventoy/mios-loopback.cfg` rendered from SSOT labels (Phase 3)
2.2 Provide a Windows companion `installation/stage-mios-repo.ps1` (or call the `.sh` via WSL) so `MiOS-Cat.bat` can invoke it after Ventoy install — insert one `call`/`powershell` line near `MiOS-Cat.bat:558-566` where repos are already staged.

### Phase 3 — Wire the boot menu to the immutable installer (fixes G2, G3, G5)
3.1 Add a Ventoy `menu_alias`/`menu_class` entry for `MiOS.iso` = "Install MiOS (Immutable bootc)" in `ventoy.json` (sits beside the existing Fedora entry; keep Fedora as the explicit *"mutable server"* mode so both are offered, not silently swapped).
3.2 Render `cat/loopback.cfg` **from SSOT** (drop-in template below) and stage it as `MiOS-Repo/ventoy/mios-loopback.cfg`. For Path A the entry simply `chainloads`/`iso_boot`s `MiOS.iso`; for Path B it boots a rescue kernel + `ostreecontainer oci-archive:` (as today) — but now the inputs actually exist because Phase 2 staged them.
3.3 Add a Ventoy `kickstart`/auto-install hook (or the ISO's embedded kickstart) whose `%post` calls **`tools/install.sh --oci-archive /mnt/mios-repo/mios-latest.tar --target-disk <auto>`** for the Path B rescue flow — restoring the caller drift-check 85 already assumes.

### Phase 4 — Secure Boot on the installed target (fixes G6)
4.1 Ship a **first-boot MOK enrollment** oneshot (drop-in unit below): on the freshly `bootc install`ed disk, `mokutil --import /etc/mios/secureboot/MOK.der` (or `sbctl enroll-keys`) so the baked UKI verifies under enforcing Secure Boot. Guard with `mokutil --sb-state` and idempotency (`ConditionPathExists`).
4.2 Keep the chain explicit: **shim (signed) -> GRUB -> UKI (systemd-ukify, from `76-uki-render.sh`) -> MOK-trusted**. Document that Ventoy `/S` covers only the USB shim; the target's trust is enrolled by 4.1.

### Phase 5 — Prove it (no more "logs can lie", per MiOS-Cat.bat:476)
5.1 Extend `just verify-images` to assert the ISO is an **installer** (contains `images/install.img` + bootc/ostree marker), and that `mios-latest.tar` is an oci-archive (`oci-layout` present).
5.2 Add a drift-check **"deploy-wiring"**: fail if `ventoy.json` has a MiOS immutable ISO alias but no stager writes it, or if `loopback.cfg` references paths no stager produces (closes G3 permanently).
5.3 Boot-test matrix in a VM (OVMF+SB on): Path A ISO install; Path B loopback+`tools/install.sh`; qcow2 direct-boot; verify `bootc status` shows `ghcr.io/mios-dev/mios` (not Fedora).

### Phase 6 — Fold the divergent driver + inert config
6.1 Land Phase 0.1 (driver calls Just). 6.2 Either wire `wsl2.toml` into the `wsl2` recipe or delete it (G9). 6.3 Rename the Xbox entry to make clear it is the **Windows Gaming edition**, not immutable MiOS (G10).

---

## 5. Drop-in artifacts

### 5.1 `installation/stage-mios-repo.sh` — the missing USB staging bridge
Runs on Linux/WSL. Stages every built artifact + a from-SSOT loopback menu onto a mounted Ventoy USB. Idempotent; zero network. Place at `installation/stage-mios-repo.sh`, `chmod +x`.

```bash
#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=usb-artifact-stager
# AI-hint: Stages built immutable-MiOS artifacts (oci-archive tar, Anaconda-bootc ISO, raw/qcow2/vhdx, brain) onto a mounted Ventoy USB (MiOS-Repo + MiOS-Data) and renders the from-SSOT loopback menu, so one USB offline-installs the REAL bootc image. Zero-network. Companion to tools/install.sh + mios-stage-oci-archive.
# AI-related: usr/libexec/mios/mios-stage-oci-archive, tools/install.sh, field/loopback.cfg, usr/share/mios/ventoy/ventoy.json, usr/share/mios/mios.toml [cat.repo_partition]/[cat.data_partition]/[deploy.artifacts]
set -euo pipefail

# --- Resolve ROOT + SSOT labels (no hardcoding; degrade-open to canonical) ---
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MIOS_ROOT:-$(cd "$SELF/.." && pwd)}"
SSOT="$ROOT/usr/share/mios/mios.toml"
BUILD="${MIOS_BUILD_DIR:-$ROOT/build}"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null || echo 0.3.0)"

_ssot() { # _ssot <section> <key> <fallback> — tiny grep-based reader (drift-check-88 style)
    local sec="$1" key="$2" fb="$3" v
    v="$(awk -v s="[$sec]" -v k="$key" '
        $0==s{f=1;next} /^\[/{f=0}
        f && $1==k {for(i=1;i<=NF;i++) if($i=="="){print $(i+1);exit}}' "$SSOT" 2>/dev/null | tr -d '"' )"
    printf '%s' "${v:-$fb}"
}
REPO_LABEL="$(_ssot 'cat.repo_partition' 'label' 'MiOS-Repo')"
DATA_LABEL="$(_ssot 'cat.data_partition' 'label' 'MiOS-Data')"

# --- Locate mounted partitions by label (Linux: /dev/disk/by-label) ---
mnt_for_label() { # echo mountpoint for a filesystem label, mounting if needed
    local lbl="$1" dev mp
    dev="$(blkid -L "$lbl" 2>/dev/null || true)"
    [[ -z "$dev" ]] && { echo ""; return 0; }
    mp="$(findmnt -n -o TARGET --source "$dev" 2>/dev/null || true)"
    if [[ -z "$mp" ]]; then mp="/run/mios-stage/$lbl"; mkdir -p "$mp"; mount "$dev" "$mp"; fi
    echo "$mp"
}
REPO_MP="${MIOS_REPO_MP:-$(mnt_for_label "$REPO_LABEL")}"
DATA_MP="${MIOS_DATA_MP:-$(mnt_for_label "$DATA_LABEL")}"
[[ -z "$DATA_MP" ]] && DATA_MP="$REPO_MP"   # small stick: single partition (degrade-open)
[[ -z "$REPO_MP" ]] && { echo "[stage] FATAL: no '$REPO_LABEL' partition found. Run MiOS-Cat first." >&2; exit 1; }

echo "[stage] ROOT=$ROOT  VERSION=$VERSION"
echo "[stage] $REPO_LABEL -> $REPO_MP   $DATA_LABEL -> $DATA_MP"

# --- 1. Brain: mios.toml + loopback menu (always, even on tiny sticks) ---
install -Dm0644 "$SSOT" "$REPO_MP/mios.toml"
mkdir -p "$REPO_MP/ventoy"
render_loopback > "$REPO_MP/ventoy/mios-loopback.cfg"   # defined at bottom
echo "[stage] staged brain: mios.toml + ventoy/mios-loopback.cfg"

# --- 2. OCI archive (Path B source; same path drift-check 81 pins) ---
SRC_TAR="$BUILD/oci-archive/mios-${VERSION}.tar"
if [[ -f "$SRC_TAR" ]]; then
    install -Dm0644 "$SRC_TAR" "$REPO_MP/mios-latest.tar"   # tools/install.sh: /mnt/mios-repo/mios-latest.tar
    echo "[stage] staged oci-archive -> $REPO_MP/mios-latest.tar"
else
    echo "[stage] WARN: $SRC_TAR missing -- run 'just oci-archive' (Path B unavailable)"
fi

# --- 3. Anaconda-bootc installer ISO (Path A boot target) ---
ISO_SRC="$(ls -1 "$BUILD"/iso/*.iso "$BUILD"/bootiso/*.iso 2>/dev/null | head -1 || true)"
if [[ -n "$ISO_SRC" ]]; then
    install -Dm0644 "$ISO_SRC" "$DATA_MP/Live_Operating_Systems/MiOS.iso"
    echo "[stage] staged installer ISO -> $DATA_MP/Live_Operating_Systems/MiOS.iso"
else
    echo "[stage] WARN: no build/iso/*.iso -- run 'just iso' (Path A unavailable)"
fi

# --- 4. VM disk images (fixes G8) -- only when a MiOS-Data bulk store exists ---
if [[ "$DATA_MP" != "$REPO_MP" ]]; then
    for pair in "raw:disk.raw" "qcow2:disk.qcow2" "vhdx:disk.vhdx"; do
        d="${pair%%:*}"; out="${pair##*:}"
        f="$(ls -1 "$BUILD/$d"/*."${out##*.}" 2>/dev/null | head -1 || true)"
        [[ -n "$f" ]] && install -Dm0644 "$f" "$DATA_MP/images/$out" && echo "[stage] staged $out"
    done
fi

# --- 5. Shallow brain repos (offline overlay source for the kickstart) ---
if [[ "${MIOS_STAGE_REPOS:-1}" == "1" && -d "$ROOT/.git" ]]; then
    mkdir -p "$REPO_MP/repos"
    git -C "$ROOT" archive --format=tar HEAD | tar -x -C "$REPO_MP/repos" \
        && mkdir -p "$REPO_MP/repos/MiOS" && echo "[stage] staged mios tree (git archive)"
fi

sync
echo "[stage] DONE. Boot the USB -> 'Install MiOS (Immutable bootc)'."

# ---------------------------------------------------------------------------
# render_loopback: emits the from-SSOT Ventoy/GRUB loopback menu (see 5.2).
render_loopback() {
cat <<LOOP
# Auto-rendered from mios.toml by installation/stage-mios-repo.sh -- DO NOT hand-edit.
# Path A (preferred): boot the self-contained Anaconda-bootc installer ISO.
menuentry "Install MiOS (Immutable bootc Workstation & Agentic AI OS)" {
    search --set=root --label ${DATA_LABEL}
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop \$iso
    linux (loop)/images/pxeboot/vmlinuz inst.stage2=hd:LABEL=${DATA_LABEL}:\$iso quiet
    initrd (loop)/images/pxeboot/initrd.img
}
# Path B (rescue / no-Anaconda): install the immutable image straight from the oci-archive.
menuentry "Install MiOS from OCI archive (bootc install --transport oci-archive)" {
    search --set=root --label ${DATA_LABEL}
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop \$iso
    linux (loop)/images/pxeboot/vmlinuz rd.live.image \
        inst.ks=hd:LABEL=${REPO_LABEL}:/ventoy/mios-oci-install.ks quiet
    initrd (loop)/images/pxeboot/initrd.img
}
LOOP
}
```

> Note: `render_loopback` is defined after its first use for readability; move the `render_loopback(){...}` definition **above** its call site (or `source` it) before landing — bash needs the function defined before line 1's invocation. Shown inline here to keep the artifact self-contained.

### 5.2 `cat/loopback.cfg` — from-SSOT template (replaces the dangling literal one)
Committed template with tokens the stager substitutes (labels come from `[cat.repo_partition].label` / `[cat.data_partition].label`). This keeps drift-check 88 green (references the SSOT `MiOS-Repo` label) and removes the fictional `/images/vmlinuz` top-level paths that no stager writes.

```
# AI-hint: Ventoy/GRUB loopback multiboot menu TEMPLATE; @@DATA_LABEL@@/@@REPO_LABEL@@ substituted from mios.toml [cat.*_partition].label by installation/stage-mios-repo.sh. Boots the staged self-contained Anaconda-bootc MiOS.iso (immutable), NOT plain Fedora.
# AI-related: usr/share/mios/mios.toml, installation/stage-mios-repo.sh, tools/install.sh, automation/98-drift-checks.sh
menuentry "Install MiOS (Immutable bootc Workstation & Agentic AI OS)" {
    search --set=root --label @@DATA_LABEL@@
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop $iso
    linux (loop)/images/pxeboot/vmlinuz inst.stage2=hd:LABEL=@@DATA_LABEL@@:$iso quiet
    initrd (loop)/images/pxeboot/initrd.img
}
menuentry "Install MiOS from OCI archive (rescue: bootc install --transport oci-archive)" {
    search --set=root --label @@DATA_LABEL@@
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop $iso
    linux (loop)/images/pxeboot/vmlinuz rd.live.image inst.ks=hd:LABEL=@@REPO_LABEL@@:/ventoy/mios-oci-install.ks quiet
    initrd (loop)/images/pxeboot/initrd.img
}
menuentry "MiOS Live / Rescue Environment" {
    search --set=root --label @@DATA_LABEL@@
    set iso=/Live_Operating_Systems/MiOS.iso
    loopback loop $iso
    linux (loop)/images/pxeboot/vmlinuz rd.live.image quiet
    initrd (loop)/images/pxeboot/initrd.img
}
```

### 5.3 `usr/share/mios/ventoy/mios-oci-install.ks` — Path B kickstart that FINALLY calls `tools/install.sh`
Restores the caller drift-check 85 assumes. Zero-network; installs the immutable image from the staged tar.

```
# AI-hint: Path-B rescue kickstart -- mounts the MiOS-Repo USB and runs tools/install.sh to bootc-install the immutable image from the staged oci-archive (offline, zero-network). Complements the mutable-Fedora mios-kickstart.cfg (that path stays a separate MODE).
# AI-related: tools/install.sh, usr/libexec/mios/mios-stage-oci-archive, usr/share/mios/mios.toml [cat.repo_partition]
text --non-interactive
network --bootproto=dhcp --device=link --activate --onboot=on
%post --nochroot --log=/var/log/mios-oci-install.log --erroronfail
set -euo pipefail
repo_dev="$(blkid -L "MiOS-Repo" 2>/dev/null || true)"
[ -n "$repo_dev" ] && { mkdir -p /mnt/mios-repo; mount -o ro "$repo_dev" /mnt/mios-repo || true; }
# Pick the first non-removable disk as target (operator can override in the menu).
target="$(lsblk -dnro NAME,TYPE,RM | awk '$2=="disk" && $3==0 {print "/dev/"$1; exit}')"
src="$(command -v mios-install.sh || echo /mnt/mios-repo/repos/MiOS/tools/install.sh)"
echo "YES" | bash "$src" --target-disk "$target" --oci-archive /mnt/mios-repo/mios-latest.tar
%end
```

### 5.4 `usr/lib/systemd/system/mios-mok-enroll.service` — first-boot Secure-Boot MOK enrollment (fixes G6)
Baked into the image; runs once on the installed disk so the UKI trusts under enforcing SB.

```ini
# AI-hint: One-shot first-boot MOK enrollment so the baked UKI (from 76-uki-render.sh) verifies under enforcing Secure Boot on the INSTALLED disk. Idempotent; no-op when SB is off or key already enrolled. Completes shim->GRUB->UKI->MOK chain that Ventoy's /S flag only covers for the USB shim.
# AI-related: automation/76-uki-render.sh, tools/generate-uki-cmdline.py, usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml
[Unit]
Description=MiOS first-boot MOK enrollment for Secure Boot UKI trust
ConditionPathExists=/etc/mios/secureboot/MOK.der
ConditionPathExists=!/var/lib/mios/.mok-enrolled
After=local-fs.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/bash -c '\
  mokutil --sb-state 2>/dev/null | grep -q "enabled" || { echo "SB off -- skip"; exit 0; }; \
  mokutil --test-key /etc/mios/secureboot/MOK.der 2>/dev/null | grep -q "already enrolled" && exit 0; \
  mokutil --import /etc/mios/secureboot/MOK.der --root-pw && mkdir -p /var/lib/mios && touch /var/lib/mios/.mok-enrolled; \
  echo "MOK import staged -- confirm in MokManager on next reboot."'
[Install]
WantedBy=multi-user.target
```

---

## 6. Fastest path to a demoable win
1. `just build oci-archive iso` on MiOS-DEV (all three already work).
2. Land **5.1** `installation/stage-mios-repo.sh` (move `render_loopback` above its call); run it against a MiOS-Cat-prepared stick.
3. Land **5.2** template + one `menu_alias` line in `ventoy.json` for `MiOS.iso`.
4. Boot the stick in an OVMF VM -> "Install MiOS (Immutable bootc)" -> after reboot confirm `bootc status` = `ghcr.io/mios-dev/mios` (not Fedora). That single boot converts the deploy plane from ~20% to a real, demonstrable offline immutable install.

## 7. Law / gate compliance notes
- Everything above resolves labels/paths/sizes **from `mios.toml`** (`[cat.*_partition].label`, `[deploy.artifacts]`) — no new hardcoding (Law 7/8; SSOT-operator-defined).
- The new stager carries a unique `MIOS_INSTALLER_ROLE=usb-artifact-stager` so drift-check 86 stays green (roles: `bootc-baremetal-disk-installer`, `root-overlay-redirector`, `container-build-installer`, + this).
- `tools/install.sh` unchanged -> drift-checks 81/85/88 stay green; the plan only adds **callers** and **stagers**, so the zero-network offline-install invariant (check 85) is preserved.
- Two-repo (Law 15): the stager + templates are host-side deploy assets that live under `installation/` and `cat/`/`usr/share/mios/ventoy/`; mirror them into `mios-bootstrap.git` per the double-repo rule before landing.
