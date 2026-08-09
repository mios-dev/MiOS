<!-- AI-hint: W10 — MiOS-Cat Live-Chat: Flash-Tonight Landing Plan.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# W10 — MiOS-Cat Live-Chat: Flash-Tonight Landing Plan

**Mechanism (settled):** bootc-live-squashfs. The Ventoy USB chainloads `MiOS-Live-Chat.iso`, which boots the *same* `localhost/mios:latest` bootc OCi image `bootc install` would otherwise write to disk — RAM-resident via dracut `dmsquash-live` — overlaid with a bundled CPU llama-server + GGUF. tty1 is replaced entirely by a `User@mios>` chat REPL (no login, no shell reachable). Root cause of the earlier research doc's alternate (`llamafile.exe` injected into `MiOS_PE.wim`/WinPE) is rejected for landing: it boots WinPE, not MiOS, and doesn't satisfy "an ephemeral MiOS comes up."

Two prior build passes produced **overlapping/conflicting** implementations of the same server-side pieces (one self-contained in `live-iso.sh`, one split into `live-chat-fetch.sh` + `config/live-profile/*`), and two client implementations (bash vs. Python). This plan **de-duplicates** them into one canonical set — the alternates are listed at the bottom as *do-not-build* to avoid double maintenance.

---

## 1. Ownership split

| Layer | Owner | Repo |
|---|---|---|
| OS/image build pipeline (dracut/squashfs/xorriso, bundled server units, tty1 client, Justfile target) | **AGY** | `C:\MiOS` |
| USB staging / menu / installer UX (Ventoy grub entry, MiOS-Cat.bat build+stage routing, bat-facing SSOT aliases) | **Claude** | `C:\mios-bootstrap` |
| SSOT config (`[cat.live_chat]`) | **Both** — physically two separate files, no shared source (pre-existing 3×-mios.toml drift, see memory `mios-tech-debt-language`) | one block in each of `C:\MiOS\mios.toml` (+ mirror `usr\share\mios\mios.toml`) **and** `C:\mios-bootstrap\mios.toml` |

`C:\mios-bootstrap\cat\MiOS-Cat.bat` resolves `toml_path=%~dp0..\mios.toml` first (confirmed: `C:\mios-bootstrap\mios.toml` exists and is read before the `C:\MiOS\usr\share\mios\mios.toml` fallback) — so the bat-side SSOT edit is **not optional/cosmetic**, it's the file the installer actually loads.

Current live-tree state checked tonight: `C:\MiOS` has an unrelated uncommitted diff to `usr\share\mios\mios.toml` (`[cat]` block gaining `drivepath/medicatver/cache_path/...` — pre-existing, not part of this manifest, leave alone). `C:\mios-bootstrap` has an unrelated uncommitted diff to `cat\MiOS-Cat.bat` (Ventoy version-pin resolution — also pre-existing, leave alone). Neither touches `live_chat`. Nothing below has been applied to either tree.

---

## 2. File manifest (canonical — build these; alternates below are superseded)

### AGY / `C:\MiOS` (new)

| Path | Purpose |
|---|---|
| `automation/build/live-iso.sh` | The pipeline: resolve SSOT → stage model + llama-server binary → `podman create/cp/commit` overlay onto a throwaway tag (base image never mutated) → `dracut --add dmsquash-live` → `mksquashfs` → `xorriso` hybrid BIOS+UEFI ISO. |
| `config/artifacts/live-chat.toml` | Build-mechanics only (volume label, dracut modules/drivers, kernel-arg tail) — deliberately *not* operator SSOT. |
| `usr/share/mios/live-chat/overlay/usr/lib/systemd/system/mios-live-chat-server.service` | Server unit, `podman cp`'d verbatim into the staged rootfs. |
| `usr/share/mios/live-chat/overlay/usr/lib/systemd/system/multi-user.target.wants/mios-live-chat-server.service` | Enablement symlink (overlay is `cp`'d, not `systemctl enable`d). |
| `usr/share/mios/live-chat/overlay/usr/libexec/mios/mios-live-chat-server` | ExecStart wrapper — resolves `threads=0`→`nproc`. |
| `usr/share/mios/live-chat/overlay/usr/libexec/mios/mios-live-chat` | tty1's *only* process — bash+curl+jq REPL, `@`-verb allowlist, SSE stream to local `/v1/chat/completions`. **This is the canonical client** (picked over the Python variant below — already wired to `live-iso.sh`'s `podman cp $OVERLAY_ROOT`, zero extra plumbing). |
| `usr/share/mios/live-chat/overlay/etc/systemd/system/getty@tty1.service.d/override.conf` | Clears `ExecStart=`, replaces with the chat client; `Type=idle`. |
| `usr/share/mios/live-chat/overlay/etc/systemd/system/getty@tty{2..6}.service` → `/dev/null` | Defense-in-depth mask; serial-getty deliberately untouched (build/debug escape hatch). |

### AGY / `C:\MiOS` (edit)

| Path | Change |
|---|---|
| `mios.toml` (+ mirror `usr/share/mios/mios.toml`) | Insert `[cat.live_chat]` after `[cat.data_partition]` — canonical nested keys (`enabled`, `model`, `model_fallback`, `port`, `ctx_size`, `threads`, `iso_name`) **plus** flat bat-loader aliases (`live_chat_enabled`, `live_chat_model`, `live_chat_fallback`, `live_chat_port`, `live_chat_ctx`, `live_chat_iso_name`) in the same block — one schema serves both `mios_toml.py` (section-aware) and `MiOS-Cat.bat`'s regex-flat loader without collision. |
| `Justfile` | New `live-chat-iso: build` recipe (sibling of `wsl2:`, same "BIB has no matching `--type`" shape); fold into `all:`. |

### Claude / `C:\mios-bootstrap` (edit)

| Path | Change |
|---|---|
| `mios.toml` | Same `[cat.live_chat]` block as above (independent file, no shared source with `C:\MiOS`'s copy). |
| `cat\resources\ventoy\ventoy_grub.cfg` | New media-guarded `if search --file --set=root /Live_Operating_Systems/MiOS-Live-Chat.iso` menu entry, placed **first** (de-facto unattended-boot default): `"0. Chat with MiOS AI [ live -- no install, no changes to this machine ]"`. |
| `cat\MiOS-Cat.bat` | 11 targeted hunks (not a rewrite): live-chat default vars; extend the PowerShell SSOT `$map`; `:menu`/`:sub_build` add a 3rd build option; new `:build_live_chat_iso` label (drives `build-mios.ps1` with `MIOS_BUILD_LIVE_CHAT=1`); `:build_all` gains the artifact + env-var gate; `:manual_about`/`:start_install` summary mentions; new staging block (copy-if-present / build-if-missing, degrade-open, `search --file`-guarded so a missing ISO just hides the menu row, never blocks the rest of the USB build); README mention; new `:resolve_live_chat_iso` helper (cache → MiOS-DEV UNC output → not-found). |

### Superseded — do **not** build tonight (redundant with the manifest above)

- `automation/build/live-chat-fetch.sh` + `config/live-profile/*` (duplicate server-side staging/units under different names — `live-iso.sh` already does this inline).
- `config/artifacts/live-chat-overlay/usr/libexec/mios/mios-live-chat` (Python client variant) + its `getty@tty1` override — keep as a documented alternate only if the bash+curl+jq client proves too fragile; don't maintain both.

---

## 3. Build + stage order (tonight)

1. **AGY, `C:\MiOS`:** land the `[cat.live_chat]` mios.toml edit (both copies) + `Justfile` recipe first — everything downstream reads this.
2. **AGY, `C:\MiOS`:** land `config/artifacts/live-chat.toml` + the `usr/share/mios/live-chat/overlay/` tree (`chmod 0755` on the two libexec scripts and the wrapper; create the two symlinks — `multi-user.target.wants/...` and the 5 masked `getty@ttyN.service` — on a Linux checkout; Windows filesystem symlinks aren't required for the Windows-side repo).
3. **AGY, `C:\MiOS`:** land `automation/build/live-iso.sh` (`chmod 0755`).
4. **Preflight on the Linux/MiOS-DEV builder:** `podman image exists localhost/mios:latest` (run `just build` first if not) and `podman image exists localhost/mios-cuda:latest`. **Before trusting the extracted binary**, run `ldd /usr/bin/llama-server` inside the `mios-cuda` image — see Risk #1 below; this determines whether step 5 needs a source swap.
5. **Run the build:** `just live-chat-iso` → produces `output/live-chat/MiOS-Live-Chat.iso` + `.sha256`. First run downloads the pinned `LiquidAI/LFM2-700M-GGUF` Q4_K_M if it isn't already baked into `localhost/mios:latest`; expect 10–25 min once the OCI image itself is already built. `mksquashfs` is the slow step.
6. **Stage the ISO** to wherever `MiOS-Cat.bat`'s `:resolve_live_chat_iso` looks (cache dir `%stage_dir%\MiOS-Live-Chat.iso`, or the MiOS-DEV build-output UNC path it already checks) — no manual copy needed if the build ran on the same box the batch script's helper resolves against.
7. **Claude, `C:\mios-bootstrap`:** land the `mios.toml` block, `ventoy_grub.cfg`, and the 11 `MiOS-Cat.bat` hunks.
8. **Run `MiOS-Cat.bat` → Stage USB** on a real target drive: it copies `Fedora-Server.iso`/kickstart as today, then the new staging block finds/copies `MiOS-Live-Chat.iso` (builds it via `build-mios.ps1 -Unattended` with `MIOS_BUILD_LIVE_CHAT=1` only if missing — degrade-open, never blocks the rest of the USB), and `xcopy`'s the updated `ventoy_grub.cfg` (existing step, no new copy logic needed there).
9. **Smoke test** per §5 below on real hardware before calling it landed.

---

## 4. Size budget

| Item | Estimate | Note |
|---|---|---|
| `lfm2-700m.gguf` (LiquidAI/LFM2-700M-GGUF, Q4_K_M) — default model | ~400–500 MB | Fits any stick; SBOM sha256 recorded per ADR-0003, never hand-pinned. |
| `granite-4.1-8b.gguf` Q4_K_M — optional operator step-up | ~4.5–5 GB | Off by default (`include_fallback=false` equivalent); only bake if RAM budget below allows. |
| `llama-server` binary | tens of MB if statically resolvable; **unknown/at-risk** if it drags in dynamically-linked CUDA runtime `.so`s (mios-cuda's binary is sourced from an upstream CUDA-enabled image, not built CPU-only in-repo) | **Verify with `ldd` before staging — see Risk #1.** |
| Base MiOS squashfs (Fedora-derived, `zstd` compressed) | not measured tonight — confirm via `podman images localhost/mios:latest` at build time; treat 2–5 GB compressed as a working assumption | Same rootfs as a real install, so it's already whatever `[image]`'s package list costs today. |
| **Total ISO, default config** | roughly 3–6 GB | Fits comfortably alongside Fedora-Server.iso + MediCat on any 32 GB+ Ventoy stick. |
| **Total ISO, with step-up model baked** | roughly 8–11 GB | Only if `include_fallback` is turned on. |
| RAM to boot (default model, `rd.live.ram=1` pulls the whole squashfs into RAM) | comfortable on 4 GB, safe on 8 GB+ | KV cache at `ctx_size=8192`, `q4_0` K/V ≈ under 1.5 GB combined with the runtime working set. |
| RAM with step-up model selected | 12 GB+ recommended | Matches the existing `[ai.host_thresholds].mid_ram_gb=12` tier already used for comparable-size models on the installed OS. |

---

## 5. Exact "boot USB → chat" demo steps

1. Insert the Ventoy USB, boot the target machine, select it as the boot device (UEFI menu / F12 / F11 depending on OEM).
2. Ventoy's own menu appears → select the staged `MiOS-Live-Chat.iso` (it's the boot device Ventoy chainloads).
3. GRUB2 menu (`ventoy_grub.cfg`) appears, 3-second timeout, entry **`0. Chat with MiOS AI [ live -- no install, no changes to this machine ]`** is first/default — press Enter or wait out the timeout.
4. Kernel + `dmsquash-live` initrd boot the squashfs RAM-resident; systemd reaches `multi-user.target`; `mios-live-chat-server.service` starts `llama-server --model .../lfm2-700m.gguf --host 127.0.0.1 --port 8642 --n-gpu-layers 0 ...`.
5. tty1's `getty@tty1` override skips login entirely and execs `mios-live-chat` directly — the screen shows the MiOS banner (SSOT `[colors]` palette), then `Waiting for the local model server...` with dots until `/health` on `127.0.0.1:8642` responds.
6. Prompt lands on:
   ```
   User@mios> 
   ```
7. Type a normal message (no `@` prefix) → Enter → response streams token-by-token under `mios>`.
8. Try `@help` → lists the whitelisted verb set (`@help`, `@model`, `@endpoint`, `@theme`, `@reboot`, `@poweroff`) — confirms no shell is reachable.
9. Try `@endpoint` → prints `http://127.0.0.1:8642/v1`, proving it's genuinely serving OpenAI `/v1`.
10. `@reboot` (or physically power off) → RAM overlay discarded, machine returns to exactly its prior state — nothing was installed, no disk was touched.

---

## 6. Risks flagged for tonight (don't block landing, but verify before declaring "done")

1. **Highest-priority:** confirm `llama-server` extracted from `localhost/mios-cuda:latest` actually runs standalone with no GPU/CUDA driver present (`ldd` check on the builder; boot-test on real "unknown demo hardware," not just the builder VM). If it hard-requires `libcudart`/`libcublas` at load time rather than lazily `dlopen`-ing the CUDA backend, swap the binary source in `live-iso.sh` step 5 for a genuine CPU-only llama.cpp release build instead of extracting from the CUDA sidecar.
2. Secure Boot signing reuses the *build host's own* shim/grub trust chain; if the demo machine enforces Secure Boot and the build host has neither a signed shim nor a MOK the demo machine already trusts, the unsigned `grub2-mkrescue` fallback path needs Secure Boot disabled on the demo machine or a MOK enrolled ahead of time.
3. `MiOS-Cat.bat` cannot build the ISO itself (no Linux/podman toolchain assumed on a bare Windows install host) — `:build_live_chat_iso` shells out to `build-mios.ps1 -Unattended` with the new `MIOS_BUILD_LIVE_CHAT=1` env hook, which the MiOS-DEV-side `mios-build-driver` does not yet recognize (same pre-existing gap as `MIOS_SKIP_BIB`, not new tonight) — the actual squashfs/ISO assembly must run via `just live-chat-iso` on the Linux/MiOS-DEV builder directly at least once before `:resolve_live_chat_iso`'s cache/UNC lookup has anything to find.
4. `enforcing=0` is set in the live kernel args (the freshly-overlaid chat binaries carry no relabeled SELinux policy for the RW tmpfs layer) — acceptable for a single-purpose, no-inbound-network, discard-on-reboot demo session; must never leak into any real install leg's kargs.