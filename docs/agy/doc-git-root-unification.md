<!-- AI-hint: Git = $ROOT: one overlay mechanism, one installer. title: "Git = $ROOT — Unify CI/CD bake ≡ bare-metal/dev deploy + fold the installers" status: planned owner: claude-lane created: 2026-07-25 ---
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
---
title: "Git = $ROOT — Unify CI/CD bake ≡ bare-metal/dev deploy + fold the installers"
status: planned
owner: claude-lane
created: 2026-07-25
---

# Git = $ROOT: one overlay mechanism, one installer

## North star (operator)
> "CI/CD pipelines and bare-metal deploys are functionally the EXACT SAME; the bare-metal
> deploy is based off the CI/CD building process. MiOS is a git tree overlaid on a Linux
> FHS root tree — they are one and the same; **Git = $ROOT**; MiOS is the systems on top."
> "UNIFY THE SEEDING/OVERLAYING MECHANISM … and unify the installer(s) at the same time
> (same code, same touch-patterns — do both at once)."

## Ground truth (from the three deep-maps)

There are **three** separately-coded "apply MiOS to `/`" mechanisms doing the same job:

| Mechanism | File | How it puts the tree at `/` | Runs `automation/*` stages? |
|---|---|---|---|
| **CI/CD bake** | `Containerfile` → `automation/build.sh` | `01-system-files-overlay.sh` **tar-pipes** `usr/`+`etc/`+skel onto `/` from read-only `/ctx`; `.git` shipped only into throwaway `/tmp/build` for the drift gate | **all 69** |
| **Bare-metal (FHS)** | `mios-bootstrap/build-mios.sh:1062-1090` | **`git init /` + fetch + `reset --hard FETCH_HEAD`** (+ `checkout -B main` + upstream config → `git -C / pull` self-updates) | a few (`15-render-quadlets`, sysusers/tmpfiles) |
| **Dev-VM (WSL/podman)** | `build-mios.ps1:3688-3723` (`Invoke-MiosQuadletOverlay`) | **same `git init /` + reset** inside the VM | some canonical (`09-fonts`,`15-render-quadlets`,`38-oh-my-posh`,`install-ai-clis`) **+ re-implements the rest in bash-in-PowerShell** |
| dumb overlay | `MiOS/tools/mios-overlay.sh` | `tar`-copies `usr/etc/var/home`, no stages | none (Justfile init/deploy/live-init call this) |

**Key insight:** bare-metal and dev-VM **already** realize `Git = $ROOT` (git-worktree at `/`); only the CI bake still `cp`/tars from `ctx` — and it already ships `.git`. So convergence is a *short reach*, not a rewrite. The dev-VM only re-implements the bake because its base is podman-**machine-os** (raw FCOS), not the MiOS image. The rows already sharing `automation/*.sh` prove the model works.

### Duplication to collapse (seed → canonical stage)
- Bibata cursor: `build-mios.ps1:9849-9925` ⇄ `automation/10-gnome.sh:59-95` (MANDATORY, identical fetch)
- dconf: `build-mios.ps1:9820-9847` ⇄ `automation/30-locale-theme.sh:82`
- home-owner + `LANG=C.utf8`: `build-mios.ps1:9944-9967` ⇄ `30-locale-theme` + `31-user`
- pkg layering (hand-rolled awk-TOML + rpm-ostree): `build-mios.ps1:4350-4600` ⇄ `install_packages_strict` + `lib/packages.sh:217-277`
- GNOME flatpak/sudoers/passwords: `build-mios.ps1:4129-4348` → new `dev-only` stage
- terminal/btop/profile.d bridge: `build-mios.ps1:9690-9818` → `08-system-files-overlay` (wsl-dev guard)
- **AI-CLIs (`install-ai-clis.sh`) has NO bake stage — a genuine gap, not just dup.**

### Installer skeleton (fold target)
- `install.sh` (root, both repos) = legacy redirector → `build-mios.sh`. `install.sh` ≡ `install-fhs.sh` **byte-identical** (live drift).
- `bootstrap.sh` (root) = redirector + curl fallback.
- `build-mios.sh` = FHS Total Root Merge (the Linux install engine).
- `installation/mios-install.sh` (515L) = Linux dispatcher (fedora→build-mios.sh, live/flash→MiOS-Cat.sh, build/update→host bins, xbox/oci/seed→Windows guidance). **No Linux consumer today** — only the `.ps1` twin is wired (Get-MiOS).
- `installation/mios-common.{sh,ps1}` = shared contract (logger/SSOT/elevation/repo-fetch).
- `tools/install.sh` (MiOS only) = offline `bootc install to-disk` from OCI archive.
- `cat/MiOS-Cat.sh` = vendored MediCat (Ventoy+USB), zero MiOS logic.
- `build-mios.ps1` = Windows host provisioning + (today) the dev-VM seeds. **Two copies diverge** (Law-15 violation).
- Enforcement precedent: every installer carries `# MIOS_INSTALLER_ROLE=`; `automation/98-drift-checks.sh:3770-3783` fails the build on missing/duplicate. **This is the hook to extend.**

## Target architecture

### One mechanism: `automation/mios-apply`
A thin entrypoint (installed `/usr/libexec/mios/mios-apply`) parameterized by:
- `MIOS_SUBSTRATE ∈ { oci-bake, bootc-live, wsl-dev, fhs-host }`
- `MIOS_ROOT` (default `/`; `/tmp/build` in the bake)

It: (1) **materializes git=$ROOT** via shared `lib/root-merge.sh` (extract of `build-mios.ps1:3628-3733`; no-op when `oci-bake` since the tree is already at $ROOT); (2) **selects stages** by a new per-stage header `# MIOS_APPLY_CLASS=<universal|bake-only|boot-only|dev-only|hardware-gated>`; (3) **runs them** through build.sh's existing loop (`build.sh:293-329`) extracted to `lib/stage-runner.sh`; (4) runs post-checks (99-postcheck/38-ssot-lint/38-drift-checks) in every substrate.

`build.sh` shrinks to: `exec env MIOS_SUBSTRATE=oci-bake MIOS_ROOT="${CTX:-/}" mios-apply "$@"` — **Containerfile:121 never changes**; the bake stays bit-identical.

### Substrate adapters (`automation/lib/adapters/*.sh`, ~30-80 lines each; 3 hooks)
`adapter_pre()`, `adapter_pkg_install <section>`, `adapter_finalize()`:
- `oci-bake`: writable `/usr`; `dnf5 install`; finalize = ostree commit + bootc lint + bound-image bake (**stay in Containerfile**).
- `bootc-live`: `rpm-ostree usroverlay`; `rpm-ostree install --idempotent`; deploy via `bootc switch`/`tools/install.sh`.
- `wsl-dev`: `nsenter` into systemd PID; `rpm-ostree`/`dnf` on mutable machine-os.
- `fhs-host`: mutable Fedora; `dnf install`.

The dnf-vs-rpm-ostree choice moves into `lib/packages.sh` behind `case "$MIOS_SUBSTRATE"`.

### Stage classification (drives everything)
- `universal` (all substrates): 08, 09, 10, 14, 15, 16, 17, 20-services, 30, 31, 32, 34-sshd, 36-tools, 37-flatpak-env, 38-oh-my-posh, 38-ssot-lint, 41-dropin-fanout, install-ai-clis.
- `bake-only` (oci-bake): 02, 05, 18, 22-kargs, 23-uki, 36-akmod, 39-oscap, 40-composefs, 42-cosign, 43-uupd, 46-greenboot, 47-hardening, 90-sbom, 91-strip, 98-boot, 99-cleanup, 52-56 bakes; + Containerfile ostree-commit/bootc-lint.
- `boot-only` (oci-bake + fhs-host w/ bootloader): kargs/boot subset a non-bootc FHS host legitimately needs.
- `dev-only` (wsl-dev): new `60-wsl-dev-desktop.sh` (flatpak/sudoers/passwords), wsl.conf writer.
- `hardware-gated` (any w/ HW): 11, 12, 34-gpu, 35-gpu-*, 41-gpu-cdi, 45-nvidia-cdi (already detect-guarded).

### Installer fold (same pass — the entrypoints of the above)
- `build-mios.sh` becomes the **one canonical Linux entry**: fold `mios-install.sh`'s target dispatch (fedora/bootc/live/flash/build/update/config) into it; delete the `mios-install.sh → build-mios.sh` chain. `build-mios.sh` targets call `mios-apply` with the right substrate.
- Delete redirector shims `install.sh` + `bootstrap.sh`; repoint the documented `curl … | bash` / `irm … | iex` URLs to `build-mios.sh`. `install.sh`/`install-fhs.sh` dedup first (Phase 0).
- Reconcile the **two divergent `build-mios.ps1`** copies to byte-identical (Law-15); after the fold its Linux-mutation bash is gone (only host provisioning remains).
- **Keep**: `Get-MiOS.ps1` (canonical Windows door), `tools/install.sh` (offline), `cat/*` (USB), `automation/*` doc-bundled copies.
- **5 judgment calls**: (G1) keep vs delete legacy `/install.sh` URL — plan: delete + repoint (preserve one thin redirector only if operator wants the bookmark); (G2) register `build-mios.sh` in check-86 as `canonical-linux-entry`; (G3) keep `require_root` hard-exit (no mios-common dep) vs inline self-sudo — plan: keep hard-exit; (G4) `flash`/`live` graceful-die in MiOS repo (no `cat/`); (G5) leave Windows guided `.ps1` dispatcher (asymmetry intentional).

## Phased task plan (execute at xhigh; each phase ends green on `just drift-gate`)

**Phase 0 — freeze baseline (no behavior change)**
1. Capture green oracles: current publish bake (drift-fix run) green; `just drift-gate` clean; the successful `Reinstall-MiOSDEV.ps1 -Go`. Record `build.sh` `_final_summary` step list.
2. Dedup `automation/install.sh` → one-line `exec install-fhs.sh` (byte-identical today). Zero-risk.

**Phase 1 — classification + enforcement (no behavior change)**
3. Add `# MIOS_APPLY_CLASS=` header to every `automation/[0-9][0-9]-*.sh` per the table. Pure comments.
4. Extend `automation/98-drift-checks.sh` (clone the `MIOS_INSTALLER_ROLE` check): "every numbered stage declares exactly one MIOS_APPLY_CLASS" + a `tests/drift-gate-negatives.sh` case. Invariant lands **before** code depends on it.

**Phase 2 — shared engine (behind the wrapper; bake unchanged)**
5. Extract `lib/stage-runner.sh` from `build.sh:204-329`; `build.sh` sources + `run_stages`. Byte-diff the summary vs Phase 0.
6. Extract `lib/root-merge.sh` from `build-mios.ps1:3628-3733`; unit-test against `$ROOT=/tmp/mios-rootmerge-test`.
7. Add `automation/mios-apply` (substrate/root → root-merge → class-filter → stage-runner → post-checks); install via `usr/` overlay.
8. Add `lib/adapters/{oci-bake,bootc-live,wsl-dev,fhs-host}.sh`; move pkg-backend switch into `lib/packages.sh`.
9. Reduce `build.sh` to `exec … MIOS_SUBSTRATE=oci-bake mios-apply`. **Gate:** full bake-log diff + `bootc container lint` identical to Phase 0. Highest risk — branch + verify.

**Phase 3 — cut bare-metal/live to the engine + installer fold**
10. Rewrite `tools/mios-overlay.sh` → `exec MIOS_SUBSTRATE=bootc-live mios-apply` (keep tar as fhs-host fallback for non-git checkouts). Justfile init/deploy/live-init now run real `universal` stages (capability upgrade: bare metal finally gets bibata/dconf/quadlet-render).
11. Fold `mios-install.sh` dispatch into `build-mios.sh` (one Linux entry); delete `install.sh`+`bootstrap.sh` shims; repoint URLs; register build-mios.sh in check-86 (G2); dedup the two `build-mios.ps1`. Verify shellcheck + drift-gate installer-role/family checks green.

**Phase 4 — fold dev-VM seeds one at a time (reinstall green after each)**
12. Packages: delete awk-TOML `parse_pkgs` (`build-mios.ps1:4350-4600`) → `install_packages_strict` via wsl-dev adapter.
13. Bibata: delete `:9849-9925` → `10-gnome.sh` under wsl-dev.
14. dconf + locale/home: delete `:9820-9847`,`:9944-9967` → `30-locale-theme`+`31-user`.
15. Desktop/flatpak/sudoers/passwords: move `:4129-4348` → new `60-wsl-dev-desktop.sh` (dev-only).
16. terminal/btop bridge: delete `:9690-9818` → `08-system-files-overlay` (wsl-dev guard).
17. Collapse `Invoke-MiosQuadletOverlay` (`:3479-4600`) → ensure git tree at `/` (root-merge.sh) then `wsl … sudo env MIOS_SUBSTRATE=wsl-dev mios-apply`. After this **no MiOS-mutation bash lives in PowerShell**. Re-run `Reinstall-MiOSDEV.ps1 -Go` + dashboard smoke after each fold.

**Phase 5 — lock the unification**
18. `automation/98-drift-checks.sh` no-reimplementation gate: fail if `build-mios.ps1` has MiOS-mutation markers (`rpm-ostree install`/`dconf update`/`Bibata`/`chpasswd`/`flatpak install`) outside a provisioning allowlist.
19. Parity check: `mios-apply --list-stages` per substrate diffed in drift-gate — `universal` set identical across substrates.
20. SSOT: record the 4 substrates + class table in `mios.toml` so the configurator surfaces them.

## Invariants (must NOT break) + verification
- INV-1 working bake (`Containerfile:121`→build.sh→ostree-commit+bootc-lint, Law 4): Phase 2 keeps build.sh a bit-identical wrapper; gate = full build-log diff + lint at step 9; branch it.
- INV-2 working reinstall (`Reinstall-MiOSDEV.ps1 -Go`): fold one seed per commit; never delete a seed until its stage covers it live.
- INV-3 git=$ROOT (".git IS /"): root-merge.sh is a verbatim extract; `reset --hard` touches only tracked files; readonly self-test guards idempotency.
- INV-4 bake-only never runs live: the MIOS_APPLY_CLASS filter + drift enforcement (step 4) fail an unclassified stage before it can run anywhere.
- INV-5 package SSOT: step 12 deletes the PowerShell fork; step 18 forbids its return.
- INV-6 drift-gate green throughout: `just drift-gate` is the continuous oracle; new checks (4,18,19) land before the code they guard.
- Risk: rpm-ostree vs dnf on live bootc → `--idempotent --allow-inactive`, defer activation to `bootc switch`. Risk: CRLF from Windows tree → root-merge.sh inherits `autocrlf false` + `sed 's/\r$//'` + `+x` restore.

## Law 15 (both repos)
Shared surfaces touched: `build-mios.sh`, `installation/mios-common.sh`, `build-mios.ps1`, `install.sh`, `bootstrap.sh`, `mios-install.sh`. Every edit lands byte-identical in `C:\MiOS` + `C:\mios-bootstrap`; `automation/`, `tools/`, drift-gate, `Containerfile` are mios.git-only.
