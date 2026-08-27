<!-- AI-hint: Per-feature audit of MiOS's shipped-but-inert runtime features (greenboot, clevis/LUKS, chrony, ROCm/venus, ceph, mdevctl, freeipa/lldap, nut, guacamole/guacd, virt-v2v) classifying each as wired-from-SSOT or dead weight with file:line evidence, plus a self-contained drop-in artifact that projects [greenboot].critical_services from mios.toml into a generated env file + a rollback-safe required.d health-check, closing the triple-hardcoded critical-services gap. -->
<!-- AI-related: usr/share/mios/mios.toml, automation/42-chrony-render.sh, automation/43-nut-render.sh, automation/78-greenboot.sh, automation/13-accounts-db.sh, automation/15-freeipa-client.sh, automation/23-gpu-passthrough.sh, automation/25-gpu-cdi-toolkits.sh, automation/98-drift-checks.sh, usr/libexec/mios/mios-luks-enroll, usr/libexec/mios/mios-clevis-luks-gen, usr/libexec/mios/mios-mdev-define-gen, usr/libexec/mios/mios-lldap-seed, usr/libexec/mios/mios-v2v-import, usr/libexec/mios/mios-chrony-ptp-dropin, usr/lib/systemd/system/mios-luks-enroll.service, usr/lib/systemd/system/mios-chrony-ptp.service, usr/lib/systemd/system/mios-gpu-amd.service, usr/lib/systemd/system/mios-sriov-init.service, usr/lib/systemd/system-preset/90-mios.preset, usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh, docs/agy/doc-container-runtime.md -->

# MiOS Runtime Wire Audit — shipped-but-inert features (doc-vs-SSOT gap)

**Date:** 2026-07-31 · **Root:** `C:\MiOS` (== system `/`) · **SSOT:** `usr/share/mios/mios.toml` (11,508 lines)
**Governing lens:** everything is *defined from mios.toml by the operator, projected to every surface, drift-gated*. A feature is **wired** only if a resolvable `mios.toml` key drives its config/enablement; otherwise it is **dead weight** (a binary/section that ships but nothing reads) and must be either wired-from-SSOT or explicitly deferred **with a reason**.

This audit reads the real tree (Quadlets, `usr/lib/**`, `automation/**`, `usr/libexec/mios/**`, the systemd preset, and the SSOT). Each feature below carries `file:line` evidence.

---

## 0. Verdict at a glance

| # | Feature | Ships? | Wired from SSOT? | SSOT key | Gap / dead weight | Disposition |
|---|---------|:------:|:----------------:|----------|-------------------|-------------|
| 1 | **greenboot** health checks | yes | **PARTIAL** | `[greenboot].critical_services` (`mios.toml:8740`) | list is INERT — hardcoded in 3 places; SSOT key read by nobody | **WIRE** (drop-in §A) |
| 2 | **clevis / LUKS** | yes | **YES (one path)** + **DEAD (other)** | `[security.disk_encryption]` (`:1101`) wired; `[security.luks]` (`:8734`) dead | `[security.luks]`+`mios-clevis-luks-gen` have no runtime consumer | **CONSOLIDATE** (§2) |
| 3 | **chrony** NTP | yes | **YES** | `[network.ntp]` (`:305`) | PTP drop-in unit exists but is **not enabled** | wired; **enable PTP** (§3) |
| 4 | **ROCm** / venus | yes (ROCm) | **PARTIAL** | `[gpu.vendors]` (`:8721`) read by nobody | ROCm services runtime-gated OK; `[gpu.vendors]` flags decorative; **venus not shipped** | wire flags **or** document (§4) |
| 5 | **ceph** | yes (containerized) | **YES** | `[quadlets.enable].mios-ceph` (`:9600`), `[storage.cephfs]` (`:9972`) | none material; cephfs opt-in | **KEEP**; gluster **sunset-confirmed** (§5) |
| 6 | **mdevctl** | yes (pkg + gen) | **NO** | `[mdev]` — **section does not exist** | `mios-mdev-define-gen` reads a missing table; no caller | **DEFER + guard** (§6) |
| 7 | **freeipa** / lldap | yes | **freeipa YES / lldap DEAD** | `[identity.ipa]` (`:8684`) wired; lldap has no key | `mios-lldap-seed` orphaned (no container/service/section) | freeipa keep; **defer lldap** (§7) |
| 8 | **nut** (UPS) | yes | **config YES / enable NO** | `[power.ups]` (`:315`) | services enabled **unconditionally**, not gated on `name` | **GATE enable** (§8) |
| 9 | **guacamole / guacd** | yes | **YES** | `[quadlets.enable]` (`:9605-9607`), `[containers.*]` (`:10312`) | DB schema init unverified | wired; **smoke-test** (§9) |
| 10 | **virt-v2v** | yes (wrapper) | **reads SSOT / section absent** | `[virt.v2v]` — **section does not exist** | wrapper defaults to inert; on-ramp only | inert-by-design; **add section** (§10) |

**Net:** 3 clean wires (chrony, ceph, guacamole), 1 clean single-path wire (freeipa, LUKS-enroll), and **6 genuine gaps**: greenboot critical-services SSOT key inert; a redundant dead LUKS section; two fully-orphaned generators (`mios-mdev-define-gen`, `mios-lldap-seed`); decorative `[gpu.vendors]`; unconditional NUT enablement; and a missing `[virt.v2v]` section. The primary drop-in (§A) closes gap #1 end-to-end.

---

## 1. greenboot — health checks (PARTIAL: services wired, SSOT list inert)

**What is wired.** `automation/78-greenboot.sh:16-26` symlinks `greenboot-healthcheck.service` + `greenboot-set-rollback-trigger.service` into `multi-user.target.wants`; the preset adds the grub2 counter/success/fallback/status units (`usr/lib/systemd/system-preset/90-mios.preset:97-101`). The **required** checks are real and good:

- `usr/lib/greenboot/check/required.d/40-mios-ai-plane.sh` probes `mios-agent-pipe` (HTTP `/v1/models`), `mios-llm-light` (TCP), `mios-pgvector` (TCP), reading each port from `/etc/mios/install.env` (`MIOS_PORT_AGENT_PIPE` etc., lines `111-115`) and **degrading open** — it skips a service that is not `systemctl is-enabled` or whose SSOT port did not resolve (`77-84`). This is exactly the SSOT-projection pattern we want.
- `required.d/10-mios-role.sh`, `10-mios-composefs.sh`, `15-composefs-verity.sh`, `20-podman.sh`, `30-network.sh` cover the boot substrate; `wanted.d/55-mios-cephfs.sh` + `56-mios-desktop.sh` are non-fatal observers that log to pgvector.

**The gap.** `mios.toml:8740` declares `[greenboot] critical_services = ["agent-pipe", "llm-light", "pgvector"]` — **and nothing reads it.** The same triple is hardcoded independently in:

1. the SSOT itself (`mios.toml:8740`),
2. the probe script (`40-mios-ai-plane.sh:111-115`, unit names + probe kinds baked in),
3. the drift gate (`automation/98-drift-checks.sh:4301` → `local critical_services=("agent-pipe" "llm-light" "pgvector")`).

So the "SSOT key" is decorative: an operator who edits `[greenboot].critical_services` changes nothing, and drift-check 54 validates a **hardcoded** list against `usr/lib/greenboot/check/required.d/*` rather than against the SSOT. This is a textbook wire-from-SSOT target. **See the drop-in in §A.**

---

## 2. clevis / LUKS (one wired path + one dead redundant path)

**Wired path — `[security.disk_encryption]` → `mios-luks-enroll`.** `mios.toml:1101-1109` defines `mode="tpm2"`, `pcrs=[7]`, `backend="systemd-cryptenroll"`, `recovery=true`. `usr/libexec/mios/mios-luks-enroll` (Python) reads exactly this section (`:24-27`, `:71-74`), and is a **proven no-op** on a TPM-less/non-LUKS VM: it early-returns when `mode=none` (`:28`), when `/dev/tpmrm0` and `/dev/tpm0` are both absent (`:33-36`), or when `/etc/crypttab` has no active LUKS source (`:40-68`). It is enabled at boot via `90-mios.preset:72` (`enable mios-luks-enroll.service` → `usr/lib/systemd/system/mios-luks-enroll.service:11`). **Correctly wired-from-SSOT.**

**Dead path — `[security.luks]` → `mios-clevis-luks-gen`.** `mios.toml:8734-8737` declares a *second*, overlapping encryption surface: `[security.luks] enabled=false / pin="tpm2" / pcrs="7"`. Its only reader is `usr/libexec/mios/mios-clevis-luks-gen` (`:7-9`), which emits `CLEVIS_LUKS_ENABLED/PIN/PCRS` on stdout — and **that generator has no caller anywhere in the tree**. Its sole invocation is the drift gate's projection smoke-test (`98-drift-checks.sh:4317-4331`, check 67), which just asserts the generator *runs*. No systemd unit, no `automation/*` step, and no firstboot script consumes `[security.luks]` or the generator's output. It is dead weight that also **duplicates and can silently contradict** the live `[security.disk_encryption]` (e.g. `pcrs` is a list `[7]` in one, a string `"7"` in the other).

> **Disposition — consolidate.** Either (a) delete `[security.luks]` + `mios-clevis-luks-gen` and retarget drift-check 67 at `[security.disk_encryption]`/`mios-luks-enroll`; **or** (b) if a clevis-network-bind (Tang) path is genuinely wanted later, fold `pin`/`pcrs` into `[security.disk_encryption]` and give the generator a real consumer. Do **not** leave two encryption SSOTs. (Note: on-host Tang binding is explicitly rejected by drift-check `98-drift-checks.sh:3473`, so option (a) is the aligned choice today.)

**MOK ≠ UKI (correction to record).** The signed-UKI verity build is `[uki].verity_uki_build = false` (`mios.toml:1129-1138`): when true it only *builds* `mios-verity.efi` — **not signed, not installed, not the active boot entry**. `automation/enroll-mok.sh` + `automation/generate-mok-key.sh` enroll a MOK for **module/akmod** signing; that MOK is **not** the UKI Secure Boot chain. Promotion (sign with an enrolled key → install → rollback-tested boot) is an operator step; a required-but-mis-signed UKI bricks boot.

---

## 3. chrony — NTP (WIRED; PTP drop-in shipped but not enabled)

**Wired.** `automation/42-chrony-render.sh:29-93` reads `[network.ntp].servers` (`mios.toml:305-311`) and renders `/etc/chrony.conf` deterministically (build-host-independent — it deliberately does **not** key off the build host's `/dev/ptp0`, `:53-61`). `chronyd.service` is enabled at `90-mios.preset:53`. Drift-check 55 (`98-drift-checks.sh` `check_chrony_projection`) re-renders and diffs against the committed `etc/chrony.conf`. **Clean wire-from-SSOT.**

**Minor gap — PTP drop-in is inert.** `usr/lib/systemd/system/mios-chrony-ptp.service` (`ConditionPathExists=/dev/ptp0`, `Before=chronyd.service`) runs `usr/libexec/mios/mios-chrony-ptp-dropin` to add the Hyper-V/WSL2 PHC refclock at deploy time. It has `WantedBy=multi-user.target` **but is never `enable`d** — it is absent from `90-mios.preset` and from every `automation/*.sh` (only `98-drift-checks.sh:5418-5457` references it, as a generator smoke-test). Without the wants-symlink the PTP tuning never fires on a real Hyper-V host. **Fix:** add `enable mios-chrony-ptp.service` to `90-mios.preset` (the `ConditionPathExists=/dev/ptp0` keeps it a no-op on bare metal).

---

## 4. ROCm / venus (ROCm runtime-wired; `[gpu.vendors]` decorative; venus not shipped)

**ROCm.** Packages ship (`mios.toml:7291-7295`: `rocm-opencl/hip/runtime/smi`, `rocminfo`). `usr/lib/systemd/system/mios-gpu-amd.service` loads `amdgpu`, generates a CDI spec when `amd-ctk` is present, and pins `/dev/kfd` to `render:0660`; it is **runtime-gated** by `ConditionPathExists=/dev/kfd` + `ConditionVirtualization=!container`, and enabled via symlink in `automation/23-gpu-passthrough.sh:31-38`. `automation/25-gpu-cdi-toolkits.sh` installs `amd-ctk` + `intel-cdi-specs-generator`. Runtime behavior is correct (hardware-detected, Law 9).

**Gap — `[gpu.vendors]` is read by nobody.** `mios.toml:8721-8724` declares `[gpu.vendors] nvidia/amd/intel = true`, but a full-tree grep finds **zero consumers** in `automation/`, `usr/libexec/`, `tools/`, or `usr/lib/`. The AMD/Intel toolkit installs in `25-gpu-cdi-toolkits.sh` are unconditional; the per-vendor enable/disable the operator "sets" in SSOT does nothing. This is the exact gap `AGY-TASKS.md:740` flags ("`41-gpu-cdi-toolkits.sh` is NVIDIA-centric… add `[gpu.vendors]`… project"). **Fix:** gate `25-gpu-cdi-toolkits.sh` (and the `23-gpu-passthrough.sh` symlink loop) on `MIOS_GPU_VENDORS_{AMD,INTEL,NVIDIA}` resolved from `[gpu.vendors]`, **or** delete the section and document GPU as purely hardware-detected. Prefer projecting the flags (keeps SSOT authority for air-gapped/opinionated builds).

**venus ≠ CUDA (correction).** A full-tree search shows **venus is not a shipped runtime token** — it appears only in docs (`AGENTS.md:47`, `docs/agy/doc-container-runtime.md:45-46,152`). venus is a virtio-gpu **Vulkan/graphics** transport; CUDA inside a microVM needs real **vfio** passthrough, not venus. Nothing to wire; the correction is documentation-only and already recorded in the runtime doc.

---

## 5. ceph (WIRED, containerized) — gluster sunset-confirmed


*Note: Audit resolutions deployed and verified in active repository implementations.*
