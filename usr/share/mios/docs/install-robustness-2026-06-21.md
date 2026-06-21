<!-- AI-hint: Install-robustness audit + fix register (2026-06-21). Two multi-agent audits (C:\MiOS build/firstboot/AI-plane: 9 confirmed/3 blockers; C:\mios-bootstrap Windows entry: 27 confirmed/4 blockers) for "irm|iex installs flawlessly on every hardware config + MiOS AI operational". Records the 16 fixes shipped this session (commits 0cd9f4b/497b917 in mios.git; d2c580c/39a98ba/eb7379a/bb60eba in mios-bootstrap.git) + the prioritized REMAINING backlog with file:line + fix. Companion to aios-capability-gap-register-2026-06-21.md.
     AI-related: ../mios.toml, ../../../../usr/libexec/mios/mios-gpu-passthrough, ./aios-capability-gap-register-2026-06-21.md -->
# MiOS install robustness — audit + fix register (2026-06-21)

Two adversarially-verified multi-agent audits of the `irm|iex` install across the
hardware/config matrix (NVIDIA / ROCm / Intel iGPU / CPU-only; WSL2 vs bare-metal;
fresh Windows box; no-WSL / no-virt / no-podman / non-admin / flaky-net):

- **C:\MiOS** (build pipeline + firstboot + AI plane): 42 surfaced → **9 confirmed (3 blockers)**.
- **C:\mios-bootstrap** (Windows entry: Get-MiOS/bootstrap/build-mios): 39 surfaced → **27 confirmed (4 blockers)**.

The real flow (corrected): `irm … Get-MiOS.ps1 | iex` does **not** reboot the
Windows host — it elevates, verifies Git/Podman, fresh-clones mios-bootstrap, and
runs `bootstrap.ps1` (dev-VM + Windows integration; OCI build is a later opt-in).
`bootc switch`+reboot live only in the bare-metal **target** deploy path.

## Fixed this session (16) — all PowerShell parse-validated, all bash `-n` clean

### mios.git (C:\MiOS) — commits 0cd9f4b, 497b917
| # | Sev | Fix |
|---|---|---|
| coverage gate | blocker | `mios-ai-hint-coverage` skips gitignored files → repo-root `just drift-gate`/CI/build.sh no longer abort on local scratch (untagged 13→3) |
| GPU device wiring | blocker | `mios-gpu-passthrough` now reconciles the brain lanes (llm-light/worker/heavy) + emits an `AddDevice=` RESET before the **detected** vendor → non-NVIDIA hosts stop hard-failing on the baked `nvidia.com/gpu=all` (safe-on-NVIDIA) |
| preflight PS7 id | blocker | `Vendor.PowerShell` → `Microsoft.PowerShell` + surface `$LASTEXITCODE` |
| repos GPG | high | `01-repos.sh` fedora-gpg-keys install `--skip-unavailable \|\| warn` (no-egress no longer fatal) |
| WSL2 distro detect | high | `install.ps1` force UTF-16 decode + exact match (re-install no longer fails "already exists") |
| WSL2 NVIDIA CDI | high | `mios-cdi-detect` defers to upstream nvidia-cdi-refresh only on bare-metal; WSL2 always generates the spec |
| VM GPU passthrough | med | `gpu-detect` probes for a real NVIDIA device before blacklisting (VFIO/SR-IOV VMs keep their GPU) |

### mios-bootstrap.git — commits d2c580c, 39a98ba, eb7379a, bb60eba
| # | Sev | Fix |
|---|---|---|
| disk shrink (B1/B4) | blocker | `Initialize-DataDisk` CLAMPs to the largest fittable size down to `[bootstrap.host_storage].min_shrink_mb` (64 GB) instead of an untrappable `exit 1`; `throw` (trappable) only if even the floor won't fit |
| virtualization (B2) | blocker | `build-mios.ps1` Phase-0 VT-x/AMD-V (`VirtualizationFirmwareEnabled`+`HypervisorPresent`) preflight → clean "enable in BIOS" remediation instead of cryptic HCS 0x80370102 |
| no-WSL reboot (B3) | blocker | flag `$script:WslJustInstalled` + HALT after Phase 0 with an idempotent "reboot then re-run" banner (was falling through to a cryptic podman fail) |
| build-success mask | high | generated `mios build` captures the OCI driver's `$LASTEXITCODE` → reports real failure ("MiOS AI will NOT be operational…") instead of false success |
| AI-plane smoke | high | `post-bootstrap-smoke.sh` §9: bounded-retry `:11450/v1/models` (P0) + `:8640` front door (P1) — the actual "MiOS AI is operational" check |
| smoke wiring | high | the generated `mios build` now RUNS the smoke in MiOS-DEV after a successful build (it was never invoked) |
| clone retry | high | `Get-MiOS.ps1` fresh-clone retries 3× (2/5/10s backoff) instead of aborting the whole install on one network blip |

## Remaining backlog (prioritized) — mios-bootstrap, mostly resilience/polish

**High:**
- **Version pinning**: bootstrap builds against the floating tip of mios.git. Add `[bootstrap].mios_ref`/`bootstrap_ref` (default `main`), thread through build-mios.ps1 (~8574/8639) for reproducible installs.
- **build-mios.ps1 fetch retry** (flaky-net): the `irm … build-mios.ps1` fetch + the in-WSL re-clone (4862) + the Windows mios.git fetch (8574/8639) lack retry — wrap in the same 3× backoff.
- **no-winget Git fallback**: a failed/partial winget Git install is swallowed; report per-package exit + direct-download fallback for Git.Git / Microsoft.WSL.
- **non-admin log loss**: `install.ps1` / `install-host-tools.ps1` hardcode `M:\` for log + btop + toml lookup; derive from the resolved `$MiosInstallDir` (`%LOCALAPPDATA%\MiOS` in non-admin mode).
- **first `mios build` driver fallback**: if the `M:\` driver copy isn't readable, curl the canonical driver (mirror the menu-path fallback).
- **smoke on dev-VM**: the bootc/os-release P0 checks fail inside MiOS-DEV (not a deployed bootc host) — detect the WSL dev-VM and downgrade those to P1.

**Med:** `.wslconfig` written with a UTF-8 BOM (write BOM-free); `mios-gui-watch.ps1` unbounded poll w/o single-instance mutex (`Global\MiOS-GuiWatch`); `identity.env.example` dead vs mios.toml SSOT (delete or source it); CLAUDE.md model table drift vs mios.toml `[ai]`; `seed-merge` ROOT_FILES references missing files; `bootstrap.sh` curl no `--retry`; dev-distro health re-run (`wsl --exec true` + `podman machine inspect`); `install-host-tools.ps1` hard `throw` on winget pkg failure + no download checksum/retry.

### C:\MiOS — deferred (needs hardware)
- **#4 CPU-only**: `mios-llm-light.yaml` forces `-ngl 999` on the `llama-swap:cuda` image. The `-ngl 0` cpu-node lane is the working CPU fallback, but a hardware-driven image/ngl selection for a GPU-less PRIMARY needs CPU hardware to verify — build-mechanism follow-up.

## Install + verify
```powershell
irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex
# then, after `mios build` (it now auto-runs the smoke):
mios smoke      # re-checks AI plane (:11450 /v1/models, :8640) + parity
```
