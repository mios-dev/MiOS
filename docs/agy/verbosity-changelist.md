<!-- AI-hint: MiOS Automation — Log-Message Verbosity Audit (Consolidated, Apply-Ready). Scope: 67 findings across 40 pipeline scripts under `C:\MiOS\automation` (+ `automation/lib`). Every proposal is technology-grounded English; `current` strings are preserved verbatim for `sed`/Edit application.
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# MiOS Automation — Log-Message Verbosity Audit (Consolidated, Apply-Ready)

Scope: 67 findings across 40 pipeline scripts under `C:\MiOS\automation` (+ `automation/lib`). Every proposal is technology-grounded English; `current` strings are preserved verbatim for `sed`/Edit application.

---

## 1. Summary

### Recurring fluff / hype words to purge pipeline-wide

| Token / pattern | Instances | Files |
|---|---|---|
| `successfully` | 5 | 20-fapolicyd-trust:24, 35-gpu-passthrough:57, 54-bake-hyprland:153, 55-bake-quickshell:121, 56-bake-surfer:109 |
| `complete` / `Done.` banner (no artifact named) | 7 | 14-generate-quadlets:41, 16-render-ports:50, 20-services:47, 26-grd:15, 35-gpu-pv-shim:73, 39-desktop-polish:43 (+ `installed` banner 13-ceph-k3s:124) |
| `BAKED IN` (all-caps emphasis) | 2 | 52-bake-kvmfr:121, 53-bake-lookingglass-client:130 |
| `... drift detected` (parenthetical restating `_violation`) | 3 | 38-drift-checks:1328, :1390, :1489 |
| marketing adjective (`pure build-up`, `Universal Dark Theme`, `Final desktop polish`) | 4 | 10-gnome:31, 30-locale-theme:21, 39-desktop-polish:20 & :43 |
| decorative `!` | 1 | 35-gpu-pv-shim:40 |

Purge list for a pipeline-wide lint rule: **successfully, complete/Done (bare), BAKED IN, "drift detected" after `_violation`, pure build-up, Universal, Final polish, trailing `!`.**

### Most common inaccuracy classes (25 `inaccurate` findings)

1. **"Action verb" for work the script does not do** — announces `Configuring/Setting/Enabling/Disabling` when the file only `echo`s and the real delivery is a `system_files` overlay, a `90-mios.preset`, or a `kargs.d/*.toml`. Dominant class (11): 10-gnome:42, 10-gnome:48, 18-apply-boot-fixes:54, 19-k3s-selinux:5, 20-services:39, 26-grd:6, 34-gpu-detect:10, 34-gpu-detect:15, 98-boot-config:14, install-fhs:59, install:58.
2. **Unconditional success on a conditional/skippable path** — asserts an artifact a guard may have skipped (5): 11-hardware:94 (NVIDIA_PRESENT=0), 13-ceph-k3s:124 (K3s download/checksum skips), 40-flatpak-bake:156 (`|| true` makes FAILED unreachable), build-mios:549 (venv guarded by `command -v python3`), 98-boot-config:40 (timeout value never read).
3. **Mislabeled unit/artifact set** — header names a narrower or different set than the loop touches (4): 44-podman-machine-compat:36 (enables sshd + qemu-guest-agent), 45-nvidia-cdi-refresh:32 (also nvidia-persistenced), 55-quickshell:64 ("panels" = one Config.qml), 30-locale-theme:92 ("all toolkits").
4. **One specific cause asserted where code cannot distinguish** (2): 37-selinux:167 (any `checkmodule`/`semodule_package` non-zero), 01-repos:92 ("warnings" = failed dnf transaction).
5. **Contradicts adjacent comment/config** (remainder): install-bootstrap:176 ("non-destructive" vs `rsync -aH` with no `--ignore-existing`), 38-drift-checks:1800/:1802 (claims `userenv.sh` verification the body never runs), 20-services:47 ("v1.4" vs CHANGELOG v1.3).

### Count table by verdict

| Verdict | Count |
|---|---|
| inaccurate | 25 |
| vague | 27 |
| fluff | 12 |
| redundant | 3 |
| **Total** | **67** |

---

## 2. Highest-value fixes

### 2a. `inaccurate` — fact-check failures that mislead operators (fix first)

| file:line | current | proposed | code-evidence |
|---|---|---|---|
| 01-repos.sh:92 | `[01-repos] NOTE: Pre-upgrade had warnings, continuing...` | `[01-repos] NOTE: dnf upgrade of systemd/glibc/dbus-broker/filesystem returned non-zero; continuing` | Block lines 90-93 fires only on dnf non-zero exit (failed transaction), not "warnings". |
| 10-gnome.sh:42 | `echo "[10-gnome] Disabling localsearch/tracker indexing (keep package, hide autostart)..."` | `echo "[10-gnome] localsearch/tracker indexing disabled via static autostart override files in the usr/share/xdg/autostart/ overlay (package retained)"` | No command between echo (42) and next section (44); comment (40) says disabling is done by overlay files. |
| 10-gnome.sh:48 | `echo "[10-gnome] Setting Qt Adwaita environment variables (managed via overlay)..."` | `echo "[10-gnome] Qt Adwaita theming provided by usr/lib/environment.d/60-mios-qt-adwaita.conf overlay"` | No env var is set here; comment (47) names the overlay file. |
| 11-hardware.sh:94 | `echo "[11-hardware] GPU stack complete. Mesa + AMD ROCm + Intel + NVIDIA (ucore / akmod rebuild)."` | `echo "[11-hardware] GPU stack complete: Mesa + AMD ROCm + Intel installed; NVIDIA kmod present=$NVIDIA_PRESENT (0 = image ships without NVIDIA acceleration)."` | Lines 73-79 handle NVIDIA_PRESENT=0 where no NVIDIA kmod ships; line asserts NVIDIA unconditionally. |
| 13-ceph-k3s.sh:124 | `echo "[13-ceph-k3s] Ceph + K3s stack installed."` | `echo "[13-ceph-k3s] Ceph client + cephadm installed; K3s binary install per tag ${K3S_TAG:-none} (see status above)."` | K3s install skipped at line 52 (version unset), 102 (checksum), 106 (download fail). |
| 18-apply-boot-fixes.sh:54 | `echo "==> Service gating drop-ins active via overlay"` | `echo "==> OCI/WSL2 service gating: no action here; ConditionVirtualization drop-ins ship in the system_files overlay"` | Section 6 (51-54) is comments + this echo only; nothing activates. |
| 19-k3s-selinux.sh:5 | `echo "==> Compiling and Installing K3s SELinux Policy for Fedora 44..."` | `echo "==> Compiling K3s SELinux policy (k3s.pp) for Fedora 44 and staging it in /usr/share/selinux/packages/mios/..."` | Lines 59-63 comment "instead of installing... we ship the compiled policy"; only `install -m 0644 k3s.pp` (63); line 68 says "staged". |
| 20-services.sh:39 | `echo "[20-services] WSL2/Container skip drop-ins active via overlay"` | `echo "[20-services] WSL2/OCI service-skip drop-ins delivered via system_files overlay (not by this step)"` | No install/activate command; comment (38) says they ship via overlay. |
| 26-gnome-remote-desktop.sh:6 | `echo "[26-grd] Configuring GNOME Remote Desktop (GNOME 50)"` | `echo "[26-grd] Masking xrdp.service and xrdp-sesman.service; GNOME Remote Desktop enablement via 90-mios.preset"` | Only command is `systemctl mask xrdp.service xrdp-sesman.service` (9); GRD enable via preset/overlay (11-13). |
| 30-locale-theme.sh:92 | `echo "[30-locale-theme] Dark theme configured for all toolkits."` | `echo "[30-locale-theme] Applied system Flatpak dark/cursor overrides, compiled 90-mios.gschema.override, ran dconf update."` | Step only sets Flatpak overrides (49-66), compiles gschema (76), dconf update (82); GTK/Qt/Electron via overlays. |
| 34-gpu-detect.sh:10 | `echo "[34-gpu-detect] Configuring GPU auto-detect service..."` | `echo "[34-gpu-detect] gpu-detect unit + /usr/libexec/mios/gpu-detect supplied by system_files overlay; this step performs no configuration."` | Body is only echoes (12-13 say unit/script come from overlay + preset). |
| 34-gpu-detect.sh:15 | `echo "[34-gpu-detect] GPU detection service enabled."` | `echo "[34-gpu-detect] gpu-detect.service enablement delivered via usr/lib/systemd/system-preset/90-mios.preset (not enabled by this script)."` | Script never enables the unit; comment (13) attributes enablement to preset. |
| 37-selinux.sh:167 | `echo "[37-selinux] mios_${name}: SKIPPED (type missing in current policy)"` | `echo "[37-selinux] mios_${name}: SKIPPED (checkmodule or semodule_package failed -- e.g. a required SELinux type is absent from the current policy)"` | else branch fires on any non-zero from checkmodule (161) OR semodule_package (162); cause not verified. |
| 38-drift-checks.sh:1800 | `echo "[38-drift-checks]   (30) names registry matches generate-names-registry.py and userenv.sh maps cleanly"` | `echo "[38-drift-checks]   (30) usr/share/mios/names.generated.txt + referenced_names.txt match a fresh tools/generate-names-registry.py run"` | Body (1737-1798) only diffs the two generated files; never reads userenv.sh. |
| 38-drift-checks.sh:1802 | `_violation "naming registry drift / userenv translation table violation (flatten check 30)"` | `_violation "usr/share/mios/names.generated.txt or referenced_names.txt is STALE vs tools/generate-names-registry.py -- regenerate with python3 tools/generate-names-registry.py (flatten check 30)"` | Check inspects no userenv table; only failure is stale generated files. |
| 40-flatpak-bake.sh:156 | `log "[40-flatpak-bake] bake complete: ${INSTALLED} installed, ${FAILED} deferred to first boot"` | `log "[40-flatpak-bake] bake complete: ${INSTALLED} refs attempted, ${FAILED} reported non-zero"` | Lines 146-149 `flatpak install ... \| grep ... \|\| true` always succeeds; FAILED else branch unreachable, INSTALLED counts failures too. |
| 44-podman-machine-compat.sh:36 | `log "Enabling Podman Machine and cloud-init services..."` | `log "Symlinking sshd.service, podman.socket, qemu-guest-agent.service, cloud-init.service, cloud-final.service into multi-user.target.wants"` | Loop (37-42) also enables sshd + qemu-guest-agent, which are neither podman-machine nor cloud-init units. |
| 45-nvidia-cdi-refresh.sh:32 | `log "Enabling NVIDIA CDI units..."` | `log "Symlinking nvidia-cdi-refresh.path, nvidia-cdi-refresh.service, nvidia-persistenced.service into multi-user.target.wants"` | Loop (33-37) also enables nvidia-persistenced.service (persistence daemon, not CDI). |
| 55-bake-quickshell.sh:64 | `echo "[55-bake-quickshell] Writing default quickshell panels..."` | `echo "[55-bake-quickshell] Writing default panel /usr/share/mios/quickshell/Config.qml..."` | Heredoc (66-119) writes one file Config.qml with a single PanelWindow. |
| 98-boot-config.sh:14 | `echo "[98-boot-config] Configuring plymouth disable via kernel cmdline..."` | `echo "[98-boot-config] Verified /usr/lib/bootc/kargs.d/10-mios-console.toml present (plymouth disable via kernel cmdline)."` | if (13) only tests `-f .../10-mios-console.toml`; comment (5) says disable is in the kargs TOML. |
| 98-boot-config.sh:40 | `echo "[98-boot-config]   NM-wait-online: 10s timeout (was 90s)"` | `echo "[98-boot-config]   NM-wait-online: timeout set by overlay drop-in (value not read or verified by this script)"` | Script never reads/sets the timeout (34 defers to overlay); "10s/90s" is unverified. |
| build-mios.sh:549 | `âœ" Python virtual environment created` | `âœ" Python virtual environment created at .local/share/mios/venv (skipped if python3 absent)` | venv guarded by `command -v python3`; failure is non-fatal `log_warn` (440-443). |
| install-bootstrap.sh:176 | `log_info "Applying non-destructive FHS overlay from staging area..."` | `log_info "Rsyncing usr/etc/var/srv from ${MIOS_STAGE} into / (rsync -aH, overwrites on content diff)"` | rsync (180) is `rsync -aH --info=stats1` with no `--ignore-existing`; existing host files ARE overwritten. |
| install-fhs.sh:59 | `echo "[INFO] Enabling 'MiOS' services (Quadlets pulled in via systemd preset)"` | `echo "[INFO] Quadlet .container units laid down under /etc/containers/systemd; systemd generator instantiates them on next daemon-reload/boot"` | No `systemctl enable`/preset follows; 56-61 are daemon-reload + echoes only. |
| install.sh:58 | `echo "[INFO] Enabling 'MiOS' services (Quadlets pulled in via systemd preset)"` | `echo "[INFO] Quadlet .container units laid down under /etc/containers/systemd; systemd generator instantiates them on next daemon-reload/boot"` | No enable/preset invocation follows; 55-61 are daemon-reload + echoes. |

### 2b. Worst fluff (banner noise that hides the actual artifact)

The five `successfully` banners and two `BAKED IN` banners are the highest-value fluff to purge because each sits at the end of a bake step and, once reworded, becomes the only place the produced artifact path is stated.

| file:line | current | proposed |
|---|---|---|
| 54-bake-hyprland.sh:153 | `echo "[54-bake-hyprland] Baseline configuration written successfully."` | `echo "[54-bake-hyprland] Wrote /usr/share/mios/hyprland/hyprland.conf (MIOS_COLOR_ACCENT/INFO/MUTED tokens substituted from mios.toml [colors])."` |
| 55-bake-quickshell.sh:121 | `echo "[55-bake-quickshell] Quickshell successfully compiled and deployed."` | `echo "[55-bake-quickshell] Installed /usr/bin/quickshell and wrote /usr/share/mios/quickshell/Config.qml."` |
| 56-bake-surfer.sh:109 | `echo "[56-bake-surfer] Custom webshell built successfully."` | `echo "[56-bake-surfer] Installed /usr/lib/mios/webshell/ and symlinked /usr/bin/mios-webshell."` |
| 35-gpu-passthrough.sh:57 | `log "GPU passthrough services enabled successfully"` | `log "GPU passthrough units symlinked into multi-user.target.wants"` |
| 20-fapolicyd-trust.sh:24 | `echo "==> fapolicyd configured successfully."` | `echo "==> Set trust = file,rpmdb in fapolicyd.conf and enabled fapolicyd.service."` |
| 52-bake-kvmfr.sh:121 | `log "kvmfr kmod BAKED IN"` | `log "kvmfr.ko installed under /usr/lib/modules/$KVER/extra/kvmfr/"` |
| 53-bake-lookingglass-client.sh:130 | `log "Looking Glass client BAKED IN"` | `log "looking-glass-client installed at /usr/bin/looking-glass-client"` |
| 10-gnome.sh:31 | `echo "[10-gnome] Installing GNOME 50 desktop (pure build-up)..."` | `echo "[10-gnome] Installing GNOME 50 packages from mios.toml [packages.gnome]..."` |
| 30-locale-theme.sh:21 | `echo "  'MiOS' ${MIOS_VERSION:-} -- Universal Dark Theme"` | `echo "  'MiOS' ${MIOS_VERSION:-} -- locale + dark theme (dconf/GTK/Qt/Flatpak)"` |
| 39-desktop-polish.sh:20 | `echo "[39-desktop-polish] Final desktop polish..."` | `echo "[39-desktop-polish] staging profile.d/mios-motd.sh terminal MOTD; desktop entries delivered by 08-system-files overlay"` |
| 39-desktop-polish.sh:43 | `echo "[39-desktop-polish] Desktop polish complete."` | `echo "[39-desktop-polish] MOTD/desktop-entry overlay delivery reported"` |

---

## 3. Full changelist (per file, by line — apply as old→new)

### automation/00-materialize-build-ctx.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 21 | vague | `[00-materialize-build-ctx] build_catalog_authoritative=true. Running database materialization...` | `[00-materialize-build-ctx] build_catalog_authoritative=true; running /usr/libexec/mios/materialize-build-ctx.py to materialize build-context files into ${MIOS_BUILD_CTX}` |

### automation/01-repos.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 92 | inaccurate | `[01-repos] NOTE: Pre-upgrade had warnings, continuing...` | `[01-repos] NOTE: dnf upgrade of systemd/glibc/dbus-broker/filesystem returned non-zero; continuing` |
| 126 | vague | `[01-repos] Verifying core package versions...` | `[01-repos] Querying installed versions of systemd glibc dbus-broker filesystem via rpm -q` |

### automation/10-gnome.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 31 | fluff | `echo "[10-gnome] Installing GNOME 50 desktop (pure build-up)..."` | `echo "[10-gnome] Installing GNOME 50 packages from mios.toml [packages.gnome]..."` |
| 42 | inaccurate | `echo "[10-gnome] Disabling localsearch/tracker indexing (keep package, hide autostart)..."` | `echo "[10-gnome] localsearch/tracker indexing disabled via static autostart override files in the usr/share/xdg/autostart/ overlay (package retained)"` |
| 48 | inaccurate | `echo "[10-gnome] Setting Qt Adwaita environment variables (managed via overlay)..."` | `echo "[10-gnome] Qt Adwaita theming provided by usr/lib/environment.d/60-mios-qt-adwaita.conf overlay"` |

### automation/11-hardware.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 94 | inaccurate | `echo "[11-hardware] GPU stack complete. Mesa + AMD ROCm + Intel + NVIDIA (ucore / akmod rebuild)."` | `echo "[11-hardware] GPU stack complete: Mesa + AMD ROCm + Intel installed; NVIDIA kmod present=$NVIDIA_PRESENT (0 = image ships without NVIDIA acceleration)."` |

### automation/13-ceph-k3s.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 124 | inaccurate | `echo "[13-ceph-k3s] Ceph + K3s stack installed."` | `echo "[13-ceph-k3s] Ceph client + cephadm installed; K3s binary install per tag ${K3S_TAG:-none} (see status above)."` |

### automation/14-generate-quadlets.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 41 | vague | `echo "[14-generate-quadlets] Done."` | `echo "[14-generate-quadlets] Quadlets generated into ${OUT_DIR}."` |

### automation/16-render-ports.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 50 | vague | `echo "[16-render-ports] Done."` | `echo "[16-render-ports] Wrote MIOS_PORT_* to $ENV_FILE (stack_id*10000 offset applied, port 53 excluded)."` |

### automation/18-apply-boot-fixes.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 12 | vague | `echo "==> Applying 'MiOS' system service fixes..."` | `echo "==> Restoring +x on /usr/libexec/mios and /usr/bin/mios-* binaries, setting /etc/usbguard/*.conf to 0600, and running systemd-sysusers for systemd-resolve..."` |
| 54 | inaccurate | `echo "==> Service gating drop-ins active via overlay"` | `echo "==> OCI/WSL2 service gating: no action here; ConditionVirtualization drop-ins ship in the system_files overlay"` |

### automation/19-k3s-selinux.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 5 | inaccurate | `echo "==> Compiling and Installing K3s SELinux Policy for Fedora 44..."` | `echo "==> Compiling K3s SELinux policy (k3s.pp) for Fedora 44 and staging it in /usr/share/selinux/packages/mios/..."` |

### automation/20-fapolicyd-trust.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 6 | vague | `echo "==> Configuring fapolicyd for fs-verity/ComposeFS..."` | `echo "==> Setting fapolicyd trust backend to 'file,rpmdb' in /usr/lib and /etc fapolicyd.conf..."` |
| 24 | fluff | `echo "==> fapolicyd configured successfully."` | `echo "==> Set trust = file,rpmdb in fapolicyd.conf and enabled fapolicyd.service."` |

### automation/20-services.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 39 | inaccurate | `echo "[20-services] WSL2/Container skip drop-ins active via overlay"` | `echo "[20-services] WSL2/OCI service-skip drop-ins delivered via system_files overlay (not by this step)"` |
| 47 | vague | `echo "[20-services] Service configuration baseline complete. v1.4"` | `echo "[20-services] chmod 644 applied to unit files; TuneD profile set to throughput-performance"` |

### automation/23-uki-render.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 5 | vague | `echo "==> Preparing Unified Kernel Image (UKI) configuration..."` | `echo "==> Rendering kernel cmdline from bootc kargs.d/*.toml into /usr/lib/kernel/cmdline for the UKI..."` |

### automation/26-gnome-remote-desktop.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 6 | inaccurate | `echo "[26-grd] Configuring GNOME Remote Desktop (GNOME 50)"` | `echo "[26-grd] Masking xrdp.service and xrdp-sesman.service; GNOME Remote Desktop enablement via 90-mios.preset"` |
| 15 | vague | `echo "[26-grd] complete."` | `echo "[26-grd] xrdp.service and xrdp-sesman.service masked"` |

### automation/30-locale-theme.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 21 | fluff | `echo "  'MiOS' ${MIOS_VERSION:-} -- Universal Dark Theme"` | `echo "  'MiOS' ${MIOS_VERSION:-} -- locale + dark theme (dconf/GTK/Qt/Flatpak)"` |
| 25 | vague | `echo "[30-locale-theme] Using /etc/skel/.bashrc from overlay..."` | `echo "[30-locale-theme] /etc/skel/.bashrc provided by usr/share/skel overlay (no action here)."` |
| 29 | vague | `echo "[30-locale-theme] Using GTK3 theme from overlay..."` | `echo "[30-locale-theme] GTK3 theme provided by etc/gtk-3.0/settings.ini overlay (no action here)."` |
| 33 | vague | `echo "[30-locale-theme] Using GTK4 theme from overlay..."` | `echo "[30-locale-theme] GTK4 theme provided by etc/gtk-4.0/settings.ini overlay (no action here)."` |
| 37 | vague | `echo "[30-locale-theme] Using environment.d from overlay..."` | `echo "[30-locale-theme] Toolkit env vars provided by etc/environment.d/ overlay (no action here)."` |
| 92 | inaccurate | `echo "[30-locale-theme] Dark theme configured for all toolkits."` | `echo "[30-locale-theme] Applied system Flatpak dark/cursor overrides, compiled 90-mios.gschema.override, ran dconf update."` |

### automation/34-gpu-detect.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 10 | inaccurate | `echo "[34-gpu-detect] Configuring GPU auto-detect service..."` | `echo "[34-gpu-detect] gpu-detect unit + /usr/libexec/mios/gpu-detect supplied by system_files overlay; this step performs no configuration."` |
| 15 | inaccurate | `echo "[34-gpu-detect] GPU detection service enabled."` | `echo "[34-gpu-detect] gpu-detect.service enablement delivered via usr/lib/systemd/system-preset/90-mios.preset (not enabled by this script)."` |

### automation/35-gpu-passthrough.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 57 | fluff | `log "GPU passthrough services enabled successfully"` | `log "GPU passthrough units symlinked into multi-user.target.wants"` |

### automation/35-gpu-pv-shim.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 40 | fluff | `log "Hyper-V dxgkrnl detected!"` | `log "/dev/dxg present (Hyper-V dxgkrnl)"` |
| 73 | vague | `log "GPU-PV shim integration complete."` | `log "GPU-PV shim installed: /usr/lib/wsl/{lib,drivers}, ld.so.conf.d/mios-gpu-pv.conf, mios-gpu-pv-detect.service enabled"` |

### automation/35-init-service.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 10 | vague | `log "Enabling unified system initialization..."` | `log "Symlinking mios-role.service, mios-podman-gc.timer, mios-webtools-firstboot.service into multi-user.target.wants"` |
| 29 | vague | `log "Initialization system services enabled."` | `log "mios-role/podman-gc/webtools-firstboot units enabled via multi-user.target.wants symlinks"` |

### automation/37-selinux.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 167 | inaccurate | `echo "[37-selinux] mios_${name}: SKIPPED (type missing in current policy)"` | `echo "[37-selinux] mios_${name}: SKIPPED (checkmodule or semodule_package failed -- e.g. a required SELinux type is absent from the current policy)"` |

### automation/38-drift-checks.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 1328 | redundant | `_violation "bootstrap mios.toml [ports] table diverges from main repository mios.toml (drift detected)"` | `_violation "bootstrap mios.toml [ports] table diverges from main repository mios.toml"` |
| 1390 | redundant | `_violation "some [agent_pipe] keys do not have code consumers inside the agent-pipe codebase (T-108 drift detected)"` | `_violation "some [agent_pipe] keys have no code consumer in the agent-pipe codebase (T-108)"` |
| 1489 | redundant | `_violation "bare port literals detected in execution paths (T-121/T-125 drift detected)"` | `_violation "bare port literals in execution paths (T-121/T-125)"` |
| 1800 | inaccurate | `echo "[38-drift-checks]   (30) names registry matches generate-names-registry.py and userenv.sh maps cleanly"` | `echo "[38-drift-checks]   (30) usr/share/mios/names.generated.txt + referenced_names.txt match a fresh tools/generate-names-registry.py run"` |
| 1802 | inaccurate | `_violation "naming registry drift / userenv translation table violation (flatten check 30)"` | `_violation "usr/share/mios/names.generated.txt or referenced_names.txt is STALE vs tools/generate-names-registry.py -- regenerate with python3 tools/generate-names-registry.py (flatten check 30)"` |

### automation/38-vm-gating.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 21 | vague | `echo "[38-vm-gating] Configuring VM-specific service gating..."` | `echo "[38-vm-gating] chmod cockpit.socket.d/listen.conf, append hv_sock to modules-load.d/mios.conf, enable mios-hyperv-enhanced.service"` |

### automation/39-desktop-polish.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 20 | fluff | `echo "[39-desktop-polish] Final desktop polish..."` | `echo "[39-desktop-polish] staging profile.d/mios-motd.sh terminal MOTD; desktop entries delivered by 08-system-files overlay"` |
| 43 | fluff | `echo "[39-desktop-polish] Desktop polish complete."` | `echo "[39-desktop-polish] MOTD/desktop-entry overlay delivery reported"` |

### automation/40-flatpak-bake.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 156 | inaccurate | `log "[40-flatpak-bake] bake complete: ${INSTALLED} installed, ${FAILED} deferred to first boot"` | `log "[40-flatpak-bake] bake complete: ${INSTALLED} refs attempted, ${FAILED} reported non-zero"` |

### automation/44-podman-machine-compat.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 36 | inaccurate | `log "Enabling Podman Machine and cloud-init services..."` | `log "Symlinking sshd.service, podman.socket, qemu-guest-agent.service, cloud-init.service, cloud-final.service into multi-user.target.wants"` |

### automation/45-nvidia-cdi-refresh.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 32 | inaccurate | `log "Enabling NVIDIA CDI units..."` | `log "Symlinking nvidia-cdi-refresh.path, nvidia-cdi-refresh.service, nvidia-persistenced.service into multi-user.target.wants"` |

### automation/50-enable-log-copy-service.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 7 | vague | `log "Enabling 'MiOS' build log copy service..."` | `log "symlinking mios-copy-build-log.service into ${WANTS}"` |

### automation/52-bake-kvmfr.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 121 | fluff | `log "kvmfr kmod BAKED IN"` | `log "kvmfr.ko installed under /usr/lib/modules/$KVER/extra/kvmfr/"` |

### automation/53-bake-lookingglass-client.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 130 | fluff | `log "Looking Glass client BAKED IN"` | `log "looking-glass-client installed at /usr/bin/looking-glass-client"` |

### automation/54-bake-hyprland.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 153 | fluff | `echo "[54-bake-hyprland] Baseline configuration written successfully."` | `echo "[54-bake-hyprland] Wrote /usr/share/mios/hyprland/hyprland.conf (MIOS_COLOR_ACCENT/INFO/MUTED tokens substituted from mios.toml [colors])."` |

### automation/55-bake-quickshell.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 64 | inaccurate | `echo "[55-bake-quickshell] Writing default quickshell panels..."` | `echo "[55-bake-quickshell] Writing default panel /usr/share/mios/quickshell/Config.qml..."` |
| 121 | fluff | `echo "[55-bake-quickshell] Quickshell successfully compiled and deployed."` | `echo "[55-bake-quickshell] Installed /usr/bin/quickshell and wrote /usr/share/mios/quickshell/Config.qml."` |

### automation/56-bake-surfer.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 109 | fluff | `echo "[56-bake-surfer] Custom webshell built successfully."` | `echo "[56-bake-surfer] Installed /usr/lib/mios/webshell/ and symlinked /usr/bin/mios-webshell."` |

### automation/98-boot-config.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 14 | inaccurate | `echo "[98-boot-config] Configuring plymouth disable via kernel cmdline..."` | `echo "[98-boot-config] Verified /usr/lib/bootc/kargs.d/10-mios-console.toml present (plymouth disable via kernel cmdline)."` |
| 34 | vague | `echo "[98-boot-config] NetworkManager-wait-online timeout delivered via overlay."` | `echo "[98-boot-config] NetworkManager-wait-online-service.d timeout drop-in supplied by the image overlay (not set by this script)."` |
| 40 | inaccurate | `echo "[98-boot-config]   NM-wait-online: 10s timeout (was 90s)"` | `echo "[98-boot-config]   NM-wait-online: timeout set by overlay drop-in (value not read or verified by this script)"` |

### automation/ai-bootstrap.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 55 | vague | `echo "[ai-bootstrap] Persisting environment state..."` | `echo "[ai-bootstrap] Refreshing environment configs and dotfiles via tools/refresh-env.py..."` |
| 65 | vague | `echo "[ai-bootstrap] Seeding latest 'MiOS' context for initialized agents..."` | `echo "[ai-bootstrap] Copying artifacts/repo-rag-snapshot.json.gz into .ai/foundation/shared-tmp/ and agents/research/..."` |

### automation/build-mios.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 547 | vague | `âœ" User account created with full permissions` | `âœ" User account created in groups wheel,libvirt,kvm,video,render,input,dialout with NOPASSWD sudoers drop-in` |
| 549 | inaccurate | `âœ" Python virtual environment created` | `âœ" Python virtual environment created at .local/share/mios/venv (skipped if python3 absent)` |
| 550 | vague | `âœ" System configuration installed` | `âœ" /etc templates merged via rsync --ignore-existing` |

### automation/install-bootstrap.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 117 | vague | `log_phase "'MiOS' Bootstrap Installer (Full Build Mode)"` | `log_phase "'MiOS' Bootstrap Installer (clone repo + install full [packages.*] manifest + FHS overlay)"` |
| 176 | inaccurate | `log_info "Applying non-destructive FHS overlay from staging area..."` | `log_info "Rsyncing usr/etc/var/srv from ${MIOS_STAGE} into / (rsync -aH, overwrites on content diff)"` |

### automation/install-fhs.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 59 | inaccurate | `echo "[INFO] Enabling 'MiOS' services (Quadlets pulled in via systemd preset)"` | `echo "[INFO] Quadlet .container units laid down under /etc/containers/systemd; systemd generator instantiates them on next daemon-reload/boot"` |

### automation/install.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 58 | inaccurate | `echo "[INFO] Enabling 'MiOS' services (Quadlets pulled in via systemd preset)"` | `echo "[INFO] Quadlet .container units laid down under /etc/containers/systemd; systemd generator instantiates them on next daemon-reload/boot"` |

### automation/lib/generate-packages.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 32 | vague | `echo "[generate-packages] package_registry ON -- materializing the registry..."` | `echo "[generate-packages] package_registry ON -- running mios-registry generate to write ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml + registry.json..."` |

### automation/lib/ws7-uki-fapolicyd-build.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 129 | vague | `log "[ws7] fapolicyd observe posture installed. fapolicyd will LOG, never block."` | `log "[ws7] wrote fapolicyd permissive=1 config to /etc/fapolicyd/fapolicyd.conf; fapolicyd logs matches, does not deny"` |

### automation/lint-shell.sh
| line | verdict | current | proposed |
|---|---|---|---|
| 86 | vague | `echo "[lint-shell] PASS: all shell scripts conform to safety rules."` | `echo "[lint-shell] PASS: shellcheck reports no error-level issues repo-wide and no warning-level issues in modified/new scripts."` |

---

Apply note: `build-mios.sh` lines 547/549/550 carry the mojibake check-glyph prefix `âœ"` in the source; the `current` strings above reproduce it byte-for-byte so the edits match verbatim. Fixing that encoding is out of scope for this verbosity pass.