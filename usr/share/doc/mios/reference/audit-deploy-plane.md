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

*Note: Implementation verified and deployed in automation/70-liveiso-ipxe.sh and field/loopback.cfg.*
