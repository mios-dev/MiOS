<!-- AI-hint: W10 Design — MiOS-Cat Live-USB-to-AI-Chat (bootc-live-squashfs). Grounded against: `C:\MiOS\docs\agy\impl-mios-cat-live-boot.md` (prior WinPE-stopgap research), `C:\mios-bootstrap\cat\MiOS-Cat.bat` (1428 lines, full read), `resources\ventoy\ventoy_grub.cfg`, `resources\ventoy\mios-kickstart.cfg
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->

# W10 Design — MiOS-Cat Live-USB-to-AI-Chat (bootc-live-squashfs)

Grounded against: `C:\MiOS\docs\agy\impl-mios-cat-live-boot.md` (prior WinPE-stopgap research), `C:\mios-bootstrap\cat\MiOS-Cat.bat` (1428 lines, full read), `resources\ventoy\ventoy_grub.cfg`, `resources\ventoy\mios-kickstart.cfg`, and the live `mios.toml` SSOT (`[ai]`, `[ai.vllm]`, `[cat]`, `[colors]`, `[laws]`, `usr\share\mios\cuda\Containerfile`, `config\artifacts\iso.toml`, `automation\build-mios.sh`). This is Phase 1 (design only) — no live-tree files were edited; this document is the contract downstream build-agent phases implement against.

---

## 0. The one governing call

Between **Fedora-Live+overlay** and **bootc-live-squashfs**: **bootc-live-squashfs wins**, and it's not close.

Fedora-Live+overlay means maintaining a second, parallel OS definition (its own kickstart/package list, its own drift surface) that gets "MiOS flavor" bolted on after the fact. That directly violates the SSOT law this whole codebase is organized around (`mios-ssot-operator-defined`, `[laws]` in `mios.toml`) — there would be two things claiming to be "MiOS" that can silently diverge. It also isn't what the task asked for: "boot the Ventoy USB → an **ephemeral MiOS** comes up." A Fedora-Live respin with MiOS overlaid on top is not MiOS; it's a lookalike.

bootc-live-squashfs derives the live media **directly from the same `localhost/mios:latest` bootc OCI image** that `bootc install` writes to disk for a real install. Same rootfs, same packages, same `mios.toml`-projected config, same AI stack lineage — just booted RAM-resident via `dmsquash-live` instead of installed. This is provably the tire/wheel framing in the task: blades (bootc image) = rim, and W10 is just another **workload profile** of that one rim, not a second rim. It also means the "chat with MiOS AI" demo is honest — the operator is talking to the actual OS, not a demo double.

Confirmed enabler already in the tree: `config\artifacts\iso.toml` line 7-8 states *"Source container image MUST include dracut-live + squashfs-tools... Containerfile installs these in v0.2.0."* The live-boot tooling is **already baked into the MiOS bootc image** for the (currently installer-only) ISO leg — it has just never been pointed at a `dmsquash-live` live target instead of an Anaconda kickstart target. W10 is the second consumer of tooling that already exists, not new infrastructure.

The prior WinPE research (`impl-mios-cat-live-boot.md`) is a legitimate, already-audited fallback (`MiOS-Cat Recovery` menu entry, existing WIM-servicing seam) — keep it, but it must **not** be the thing wired to the "Chat with MiOS AI" menu entry. That entry boots real MiOS.

---

## 1. Live-boot mechanism — bootc-live-squashfs

**Pipeline (new build leg, parallel to the existing `raw/iso/qcow2/vhd/wsl2` targets in `build-mios.ps1` / MiOS-DEV):**

1. Take the already-built `localhost/mios:latest` OCI image (same image `bootc install` consumes — no rebuild, no drift).
2. Export its rootfs: `podman create localhost/mios:latest` → `podman export | tar -C $rootfs -x` (or `skopeo copy`+`umoci unpack` if a running container is undesirable in the builder).
3. **Live-profile overlay** (applied only to this exported copy, never to the base image — keeps every real install lean): drop in the chat-serving binary + GGUF + the `mios-live-chat` client + a tty1 autologin unit (§3, §4). This is deliberately a build-time addition to the *live artifact*, not a new base-image package, because most real MiOS installs don't want a bundled GGUF baked permanently onto disk.
4. `mksquashfs $rootfs LiveOS/squashfs.img -comp zstd` (standard Fedora `dmsquash-live` layout: `/LiveOS/squashfs.img`).
5. Rebuild the image's own initramfs with dracut's `dmsquash-live` module added (`dracut --add dmsquash-live --add-drivers "…" initrd.img`), kernel args: `root=live:CDLABEL=MIOSLIVE rd.live.image rd.live.overlay.overlayfs=1 rd.live.ram=1 quiet`. `rd.live.ram=1` pulls the whole squashfs into RAM so the USB is unmount-safe after boot (mirrors the WinPE `X:` ramdisk property called out in the prior research).
6. Assemble `/EFI/BOOT/BOOTX64.EFI` (reuse the **same signed shim + MOK chain** already used for the real install ISO — do not stand up a second Secure Boot signing pipeline; per `mios-container-runtime-architecture` memory, MOK≠UKI, keep that distinction intact) + `/LiveOS/squashfs.img` + kernel/initrd into a standard bootable ISO via `xorriso` (BIOS+UEFI hybrid, matching how `Fedora-Server.iso` / `MiOS-Xbox.iso` already sit and chainload from Ventoy).
7. Output: `MiOS-Live-Chat.iso`. Record its sha256 as **SBOM/baked-manifest data** (ADR-0003) — never a hand-pinned value in `mios.toml`.

**New build config:** `config\artifacts\live-chat.toml` (sibling of `iso.toml`/`qcow2.toml`) — declares the live-profile package/file overlay list and dracut module args, kept separate from `iso.toml`'s Anaconda kickstart so the installer leg and the live leg never conflate (explicit non-goal call-out in the prior research, §2.6, still holds).

**New build script:** `automation\build\live-iso.sh` (sibling of `automation\build\rechunk.sh`) — implements steps 2-7, invoked by `build-mios.ps1`/MiOS-DEV as a new artifact target alongside the existing `raw/iso/qcow2/vhd/wsl2` matrix in `:build_all`.

**Staging into MiOS-Cat.bat:** `MiOS-Live-Chat.iso` lands in `Live_Operating_Systems\` exactly like `Fedora-Server.iso` and `MiOS-Xbox.iso` already do (copy-if-present / build-if-missing, same idiom as lines 1063 and 1246-1265) — no new staging mechanism, reuse the existing pattern.

---

## 2. Model choice + size — reuse the SSOT `bake_models` CSV, don't introduce a new pin

`mios.toml` `[ai]` already declares (line ~5783):

```
bake_models = "granite-4.1-8b.gguf=unsloth/granite-4.1-8b-GGUF:granite-4.1-8b-Q4_K_M.gguf,
               lfm2-700m.gguf=LiquidAI/LFM2-700M-GGUF:LFM2-700M-Q4_K_M.gguf,
               embeddinggemma-300m-qat-q8_0.gguf=…"
```

`[cat].models` even cross-references this CSV as the models source for the USB already ("see `[ai].bake_models` + `[ai.vllm].bake_model`"). **W10 must not introduce a third model pin.** Decision:

- **Default live-chat model: `lfm2-700m.gguf` (~500-700 MB Q4_K_M).** It's already SSOT-pinned, tiny enough to fit on *any* USB stick regardless of `[cat.data_partition].min_disk_gb` gating (that 512 GB gate exists for the bulk `MiOS-Data` partition and must not be a precondition for the live-chat demo to work), and fast enough on bare CPU for an interactive tty demo on unknown/weak hardware.
- **Operator step-up: `granite-4.1-8b.gguf` (~4.9 GB Q4_K_M)** — the same model that already serves as MiOS's real always-on CPU lane (`mios-cpu-node` Quadlet, `Exec` line at `mios.toml:10012`). Selecting this gives closer answer-quality parity with the installed OS at the cost of USB space and CPU tokens/sec. Exposed as an SSOT toggle, not a hardcoded swap.
- Both are copied from the same HF refs already in `bake_models` — the live-iso build script parses that CSV rather than hardcoding either filename, so a future bake_models edit propagates automatically (Law: SSOT-operator-defined).

New SSOT block (`[cat.live_chat]`, sibling of the existing `[cat.repo_partition]` / `[cat.data_partition]`):

```toml
[cat.live_chat]
enabled        = true
model          = "lfm2-700m"        # short key into [ai].bake_models
model_fallback = "granite-4.1-8b"   # operator step-up, same CSV
port           = 8642               # = MIOS_AI_ENDPOINT (mios-ai-endpoint-canonical)
ctx_size       = 8192
threads        = 0                  # 0 = auto nproc at boot
iso_name       = "MiOS-Live-Chat.iso"
```

---

## 3. Serving binary — bare `llama-server`, deliberately decoupled from the Quadlet/`mios-ai.pod` stack

The full-OS AI stack (`mios-cpu-node`, `mios-ai.pod`) runs `llama-server` **inside** the `mios-cuda` sidecar container (`usr\share\mios\cuda\Containerfile:31`), orchestrated by Podman/Quadlet. That's the right shape for an always-on installed host; it is the *wrong* shape for a RAM-resident live boot — pulling/mounting a whole container image plus a pod plus Quadlet unit generation adds startup latency and failure surface for zero benefit in an ephemeral, single-purpose session.

**Decision:** the live profile ships the same `llama-server` binary (copied straight out of the `mios-cuda` Containerfile's `llamaswap-src` build stage as a build artifact — no new upstream pin) as a **plain host-level systemd unit**, not a Quadlet/container:

```ini
# /usr/lib/systemd/system/mios-live-chat-server.service  (live-profile overlay only)
[Unit]
Description=MiOS live-boot AI chat server (ephemeral, CPU-only)
After=local-fs.target

[Service]
ExecStart=/usr/libexec/mios/llama-server \
  --model /usr/share/mios/live-chat/model.gguf \
  --host 127.0.0.1 --port 8642 \
  --ctx-size 8192 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --parallel 1 --n-gpu-layers 0 --jinja \
  --alias mios-live-chat
Restart=on-failure
RestartSec=2s

[Install]
WantedBy=multi-user.target
```

Flags deliberately mirror the real `mios-cpu-node` Exec line (`mios.toml:10012`) minus container/Quadlet plumbing — `--n-gpu-layers 0` unconditionally, since a live boot on unidentified hardware cannot assume a working GPU driver stack.

**Port: `127.0.0.1:8642`**, the canonical `MIOS_AI_ENDPOINT` (`mios-ai-endpoint-canonical` memory). This is an intentional simplification specific to the live/ephemeral profile: in the full install, `:8642` is Hermes fronting multiple backends; in the live session nothing else is running, so `llama-server` binds the canonical port directly. Same address every `/v1` client already expects — no new port to add to the `[security.nohc_allowlist]`.

---

## 4. tty0 chat client — bash+curl REPL, no shell escape, no sudo

Zero new binary, matching the "sudo-disabled / immutable" contract literally rather than just cosmetically: the tty1 getty's `ExecStart` is **replaced** by the chat client itself, so there is never a bare shell to escape to.

```ini
# systemd override, live-profile overlay only
# /etc/systemd/system/getty@tty1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/usr/libexec/mios/mios-live-chat --tty %I
Type=idle
```

`mios-live-chat` (bash + `curl` + `jq`, both already on any Fedora-derived rootfs — no new dependency, matching the PowerShell-REPL "zero extra binaries" reasoning from the prior WinPE research, ported to Linux):

- Waits on `curl -fsS http://127.0.0.1:8642/health` before printing the first prompt (same ordering gotcha the prior research flagged for WinPE — applies identically here).
- Prompt: `User@mios> ` (per the task's literal TTY-prompt spec).
- Lines starting with `@` are intercepted client-side as **whitelisted SSOT-toggle verbs**, never shelled out:
  - `@model` — show/switch between staged models (`lfm2-700m` ↔ `granite-4.1-8b`, only if the fallback was staged onto the ISO).
  - `@endpoint` — print the active `/v1` base + port (from `[cat.live_chat]`).
  - `@theme` — re-emit the `[colors]` ANSI palette (same tokens the WinPE console-color registry injection already uses, ported to a `vconsole`/tput init).
  - `@help` — list verbs.
  - `@reboot` / `@poweroff` — the *only* system actions, explicitly whitelisted `systemctl` calls. No `@sh`, no `@sudo`, no arbitrary exec — that is the sudo-disabled/immutable boundary, enforced by the client's verb allowlist rather than by trusting `sudo` to be absent.
- Everything else is POSTed to `http://127.0.0.1:8642/v1/chat/completions` and streamed back.

Immutability is structural, not policy: the rootfs is a read-only composefs image; `rd.live.overlay.overlayfs=1` gives writes an ephemeral RAM overlay that's discarded on reboot; the live user has no `wheel` membership and no shell is reachable from tty1 at all.

---

## 5. Ventoy entry — same idiom, new default

Add as the **first** entry in `resources\ventoy\ventoy_grub.cfg`, under the existing `DEPLOY` block's pattern (`search --file` guard so it's invisible unless actually staged — matches every other entry in the file, e.g. lines 25-30, 32-37):

```
if search --file --set=root /Live_Operating_Systems/MiOS-Live-Chat.iso; then
menuentry "0. Chat with MiOS AI        [ live -- no install, no changes to this machine ]" --class linux {
    search --set=root --file /Live_Operating_Systems/MiOS-Live-Chat.iso
    chainloader /Live_Operating_Systems/MiOS-Live-Chat.iso
}
fi
```

Placed before the existing "Deploy MiOS Linux" entry so it's the de-facto default on an unattended boot. The existing "MiOS-Cat Recovery [ Mini Windows PE ]" entry (line 51-57) stays as-is and is **not** repurposed for AI chat — keeps the live-chat leg and the WinPE recovery leg un-conflated, same separation-of-concerns the prior research already insisted on for install-vs-live.

---

## 6. Staging plan (what MiOS-Cat.bat must do — for the next build-agent phase)

1. New build target `live-chat-iso` added to `build-mios.ps1` / MiOS-DEV's artifact matrix (alongside `raw/iso/qcow2/vhd/wsl2`), driven by `automation\build\live-iso.sh` + `config\artifacts\live-chat.toml` (§1).
2. `MiOS-Cat.bat`: in `:sub_build` / `:build_all`, add `MiOS-Live-Chat.iso` to the artifact list already copied out of `/var/lib/mios/build/output` — same code shape as the existing Xbox-ISO copy (line ~1256).
3. In the staging pipeline (near the Fedora-ISO copy at line 1063 and the resources xcopy at line 984), copy `MiOS-Live-Chat.iso` → `%drivepath%:\Live_Operating_Systems\MiOS-Live-Chat.iso`, guarded the same "exists → skip, else build/fetch" way `fedora_file` already is (lines 946-959) — reuse the pattern, don't invent a new one.
4. Add `[cat.live_chat]` to `mios.toml` (§2) and thread it through the existing SSOT-loader pass in `MiOS-Cat.bat` (lines 41-53) the same way `drivepath`/`medicatver`/`cache_path`/palette keys already load — add `live_chat_model`, `live_chat_port`, `live_chat_iso_name` to the PowerShell `$map` there.
5. Add the grub entry (§5) to `resources\ventoy\ventoy_grub.cfg` — this ships via the existing `xcopy "%maindir%\resources\ventoy" "%drivepath%:\ventoy\"` step (line 984), no new copy step needed.
6. `sha256` of `MiOS-Live-Chat.iso` recorded as build/SBOM manifest data (ADR-0003) alongside the other artifact hashes — never written into `mios.toml` as a hand pin.

**Explicitly out of scope for the build agents this phase governs:** touching the live tree directly (this was a design-only pass), the WinPE stopgap fixes already fully specified in `impl-mios-cat-live-boot.md` Deliverables 1 & 3 (those stand independently and should still land — the "Chat" entry point is new, the WinPE blockers are pre-existing bugs), and LFM2's exact license text (LiquidAI's "LFM Open License," not plain Apache-2.0 — flag for a build-agent to verify redistribution terms before the ISO ships, does not block design).

---

## Summary table

| Axis | Decision | Why |
|---|---|---|
| Live mechanism | **bootc-live-squashfs** from `localhost/mios:latest` | Same OCI image as real installs; `dracut-live`+`squashfs-tools` already baked in (`iso.toml:7-8`); avoids a second OS definition (SSOT law) |
| Model | **`lfm2-700m.gguf`** default (~600 MB), **`granite-4.1-8b.gguf`** operator step-up (~4.9 GB) | Both already SSOT-pinned in `[ai].bake_models` — zero new pins; small default fits any stick + fast on unknown CPU |
| Serving | Bare `llama-server` systemd unit, `127.0.0.1:8642` (=`MIOS_AI_ENDPOINT`), `--n-gpu-layers 0` | Decoupled from the heavy Quadlet/`mios-ai.pod`/container stack; same binary lineage, no pod/pull latency in a RAM boot |
| Chat client | `mios-live-chat` bash+curl REPL replacing tty1's getty `ExecStart` | Zero new binaries; no shell ever reachable → structural sudo-disabled/immutable, not policy-based; `@`-prefixed whitelisted SSOT-toggle verbs only |
| Staging | New `live-chat-iso` build target → `Live_Operating_Systems\MiOS-Live-Chat.iso`, staged/grub-wired via the exact existing Fedora/Xbox-ISO idiom | Reuses every existing MiOS-Cat.bat pattern; no new mechanism invented |

Files a downstream build-agent phase will need to create/edit (none touched in this design pass): `config\artifacts\live-chat.toml`, `automation\build\live-iso.sh`, `mios.toml` `[cat.live_chat]` block, `resources\ventoy\ventoy_grub.cfg` (new entry), `MiOS-Cat.bat` (SSOT-map + staging-copy lines), a live-profile package/file overlay list for `llama-server` + the chosen GGUF + `mios-live-chat` + the tty1 override unit.
