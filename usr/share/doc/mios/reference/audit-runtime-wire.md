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

**Wired.** Ceph runs as a container, not host daemons: `[quadlets.enable].mios-ceph = true` (`mios.toml:9600`) renders `usr/share/containers/systemd/mios-ceph.container` (a member of `[pods.mios-system]`), while the **host** MON/OSD units are explicitly disabled (`90-mios.preset:252-253` `disable ceph-mon@.service` / `ceph-osd@.service`). `ceph-bootstrap.service` is enabled via `automation/41-services.sh:27` + `automation/36-ceph-k3s.sh`. CephFS is a distinct, **opt-in** SSOT surface: `[storage.cephfs].enable = false` (`mios.toml:9972`), with `mios-cephfs-provision` (`:9999` `provision_script`), the firstboot mounter `automation/firstboot/mios-cephfs-mount-setup.sh:52`, and the non-fatal greenboot observer `etc/greenboot/check/wanted.d/55-mios-cephfs.sh` (gated on `MIOS_CEPHFS_ENABLE`, `:13`). **Correctly wired-from-SSOT; inert until the operator flips `enable`.**

**Decision (ceph vs gluster).** Gluster is **already gone**: no `gluster*` package, unit, or config anywhere in `automation/` or `usr/`; the only mention is `98-drift-checks.sh:3473` which *rejects re-introduction* of `glusterfs*`. Ceph is the surviving, wired storage plane. **Keep ceph (containerized + opt-in CephFS); gluster stays sunset** — no action beyond confirming the drift guard.

---

## 6. mdevctl (DEAD generator — no `[mdev]` section, no caller)

`usr/libexec/mios/mios-mdev-define-gen` reads `mios.toml [mdev]` and writes `/etc/mdevctl.d/*.json` (`:6-7`). **There is no `[mdev]` section in `mios.toml`** (grep confirms only the `mdevctl` package at `:7335`, kept "for legitimate SR-IOV/mdev inventory; NOT a vGPU path"). And **nothing calls the generator**: the `mios-sriov-init.service` AI-hint *claims* it "generates persistent mediated devices … via mios-mdev-define-gen," but the actual `usr/libexec/mios/mios-sriov-init` reads `/etc/mios/sriov.conf` (`:26`) and never invokes the generator. So `mios-mdev-define-gen` is fully orphaned: a missing SSOT table + zero callers. (This is consistent with the hard architectural truth in memory: driver-free GPU *fractioning* is impossible → whole-GPU-per-guest; mdev is SR-IOV/vendor-mediated inventory only.)

> **Disposition — defer with a guard, don't silently keep.** Either (a) delete `mios-mdev-define-gen` and drop the false "mdev" clause from `mios-sriov-init.service`'s AI-hint; **or** (b) if persistent VF mediated-device definitions are genuinely on the roadmap, add a real `[mdev]` section (list of `{parent, mdev_type, uuid}`) and invoke the generator from `mios-sriov-init` **after** VF creation. Until (b) lands, the generator reading a non-existent table is dead weight — it currently `exit 0`s harmlessly but misrepresents capability.

---

## 7. freeipa (WIRED) / lldap (DEAD orphan)

**freeipa — wired.** `automation/15-freeipa-client.sh` installs `freeipa-client`+`sssd` (`:24`), verifies the SSSD file-cap regression (`:26-45`), **renders `/etc/mios/ipa-enroll.env` from `[identity.ipa]` via `tools/generate-ipa-enroll-env.py`** (`:56-64`), and enables the `ConditionPathExists`-gated `mios-freeipa-enroll.service` (`:67`). `[identity.ipa]` (`mios.toml:8684-8690`, `enabled=false`, realm/server/domain/principal/otp) is the SSOT face. **Correctly wired-from-SSOT; inert by default** (the enroll oneshot no-ops while `/etc/ipa/default.conf` is absent and the env carries placeholder OTP).

**lldap — dead weight.** `usr/libexec/mios/mios-lldap-seed` ships, but a full-tree search finds **no lldap container, no `.container`/`.pod` quadlet, no systemd unit, and no `[lldap]`/lldap key in `mios.toml`** — the seeder has nothing to seed. The "lldap-over-Postgres cross-platform SSOT face" is still aspirational (per the PostgresOS memory: assemble from FOSS bricks). Today it is an orphaned binary.

> **Disposition — defer lldap with a reason.** Keep `mios-lldap-seed` only if the lldap container lands **this** cycle; otherwise move it out of the shipped `libexec` (or clearly mark it staged/unwired) so "every shipped binary is wired-or-documented" holds. Documented reason: lldap is the intended DB-driven directory face but no lldap service is deployed yet; `[identity.ipa]`+SSSD is the currently-wired identity path. `docs/agy/doc-postgresos-accounts.md` is the tracking doc.

---

## 8. nut — UPS (config WIRED; service enablement NOT gated)

**Wired config.** `automation/43-nut-render.sh:29-112` reads `[power.ups]` (`mios.toml:315-319`: `name/driver/port/desc`) and renders `/etc/ups/{nut,ups,upsd,upsmon}.conf`. When `name=""` (the default, `mios.toml:316` "Set name = '' to disable NUT (boots inert)") it writes `MODE=none` and empty driver/monitor stanzas (`:54-57`). Good SSOT projection.

**Gap — services are enabled unconditionally.** `90-mios.preset:51-52` does `enable nut-server.service` **and** `enable nut-monitor.service` regardless of `[power.ups].name`. With `MODE=none` and no `ups.conf` entry, `nut-server`/`upsd` starts with nothing to serve and `upsmon` has no `MONITOR` line — the units churn/fail on every boot of the default (UPS-less) image, contradicting "boots inert." **Fix:** gate enablement on the SSOT — either render a `.preset`/wants-symlink decision from `MIOS_UPS_NAME` in `43-nut-render.sh` (enable only when non-empty), or add `ConditionFileNotEmpty=/etc/ups/ups.conf`-style guards. Config is SSOT-driven; make **enablement** SSOT-driven too.

---

## 9. guacamole / guacd (WIRED; needs a DB-schema smoke-test)

**Wired.** `[quadlets.enable] mios-guacamole = true` / `mios-guacd = true` (`mios.toml:9605-9607`) render `usr/share/containers/systemd/mios-guacamole.container` + `mios-guacd.container`, both members of `[pods.mios-system]`. Container env is SSOT-projected (`[containers.mios-guacamole.Container]`, `mios.toml:10312-10331`): `POSTGRESQL_*` from `MIOS_PORT_PGVECTOR`/`MIOS_PG_{DB,USER,PASS}` + `EnvironmentFile=/etc/mios/install.env`; guacd hostname/port and `MIOS_GUACAMOLE_IMAGE`/`MIOS_GUACD_IMAGE`/`*_UID`/`*_GID` all resolve from SSOT. The web port is `[ports].guacamole_web = 8080` (`:7922`), published + surfaced in the Portal (`:8936`, `:8961-8963`). `After=/Wants=mios-pgvector.service` (`:10336-10337`) orders it behind the datastore. **Wired-from-SSOT.**

> **Smoke gap.** Guacamole needs its **schema** (`guacamole_db`) loaded into the pgvector Postgres before login works (`initdb.sql` from `guacamole/guacamole`), and it points at `POSTGRESQL_DATABASE=${MIOS_PG_DB:-mios}` — the shared `mios` DB. No schema-init step was found for the guac tables. **Action:** add a one-shot (firstboot or an `ExecStartPre` in a seed unit) that applies the Guacamole schema idempotently, then verify `GET http://localhost:8080/guacamole/` returns the login page. This is a wiring completeness item, not a dead-weight finding.

---

## 10. virt-v2v (wrapper reads SSOT; `[virt.v2v]` section absent → inert by design)

`usr/libexec/mios/mios-v2v-import` resolves `config["virt"]["v2v"]` (`:53`) → `enabled/output_storage/output_network/output_format`, and is **inert by default**: it prints the planned `virt-v2v -o libvirt …` command and exits when `enabled` is false or on `--dry-run` (`:66-79`), and degrades open when the `virt-v2v` binary is absent (`:81-84`). Drift-check parity guards the wrapper (`98-drift-checks.sh:6002-6004`). It is a **CLI on-ramp, not a service** — inert-by-design is correct.

**Nit — the SSOT section is missing.** `mios.toml` has **no `[virt.v2v]` (nor any `[virt]`) section**, so the wrapper always falls to Python defaults. For SSOT completeness (operator can pre-set the target pool/network/format) add:

```toml
[virt.v2v]
enabled        = false      # on-ramp; flip true to run a live import
output_storage = "default"  # libvirt storage pool
output_network = "default"  # libvirt network
output_format  = "qcow2"    # qcow2 | raw
```

---

## Cross-cutting corrections (record these)

- **venus ≠ CUDA** — venus is Vulkan/graphics transport; CUDA-in-microVM needs real vfio. venus is **not shipped** as runtime; doc-only (`docs/agy/doc-container-runtime.md:45`).
- **gluster sunset** — confirmed absent; only the anti-reintroduction guard remains (`98-drift-checks.sh:3473`). Ceph is the wired storage plane.
- **MOK ≠ UKI** — `[uki].verity_uki_build=false` builds an unsigned, uninstalled artifact; MOK enrollment signs modules, not the UKI boot chain (§2).
- **/var persists** — bootc composefs seals `/usr`; `/var` **persists across `bootc` updates**. Stateful dirs already live there: `/var/lib/mios/role.active` (`required.d/10-mios-role.sh:10`), `/var/lib/chrony/drift` (`42-chrony-render.sh:71`), `/var/lib/ceph`, `/var/lib/ipa-client` (freeipa tmpfiles). No feature above stores state under `/usr` or a tmpfs `/var`. The greenboot generated env in the drop-in below writes to `/etc/mios/` (config, persisted) — not runtime state.

---

## A. Drop-in artifact — wire `[greenboot].critical_services` from SSOT

Closes gap #1 end-to-end: the critical-services list becomes **operator-defined in `mios.toml`, projected to a generated env file, consumed by a rollback-safe required.d check, and drift-gated against the SSOT** — eliminating the three independent hardcodes. It reuses the proven degrade-open probe idiom from `40-mios-ai-plane.sh` (skip when a unit is not `is-enabled` or its SSOT port did not resolve → a config glitch never rolls the OS back).

### A.1 SSOT enrichment — `usr/share/mios/mios.toml`

Keep the existing list; add an optional per-service probe override so the HTTP `/v1/models` liveness of the agent-pipe is preserved while everything else defaults to a bounded TCP connect:

```toml
[greenboot]
# Critical services whose post-boot readiness gates the deployment. After
# GREENBOOT_MAX_BOOT_ATTEMPTS consecutive failures, bootc rolls back. Each is
# probed ONLY when `systemctl is-enabled` says it is wanted on this role AND its
# SSOT port (MIOS_PORT_<NAME>, from /etc/mios/install.env) resolved -- degrade-open.
# Unit name is derived as mios-<name>.service; port var as MIOS_PORT_<NAME-UPPERCASED>.
critical_services = ["agent-pipe", "llm-light", "pgvector"]

# Optional per-service probe override. Default probe = bounded TCP connect.
# kind="http" requires an HTTP status < 500 at `path` (a 4xx still proves the
# listener is serving, matching the agent-pipe's own liveness convention).
[greenboot.probe.agent-pipe]
kind = "http"
path = "/v1/models"
```

### A.2 Generator — `usr/libexec/mios/mios-greenboot-critical-gen`

Projects the SSOT into a shell-sourceable env file. (Mode `0755`; drift-check 5 requires the AI-hint header.)

```bash
#!/usr/bin/env bash
# AI-hint: Projects mios.toml [greenboot].critical_services (+ optional [greenboot.probe.<svc>]) into /etc/mios/greenboot-critical.env so the required.d critical-service health-check is SSOT-driven instead of hardcoded.
# AI-related: usr/share/mios/mios.toml, usr/lib/greenboot/check/required.d/41-mios-critical-services.sh, /etc/mios/greenboot-critical.env, automation/78-greenboot.sh
set -euo pipefail

TOML="${MIOS_TOML:-/usr/share/mios/mios.toml}"
OUT="${MIOS_GREENBOOT_CRITICAL_ENV:-/etc/mios/greenboot-critical.env}"

[[ -f "$TOML" ]] || { echo "[greenboot-critical-gen] $TOML absent -- no-op." >&2; exit 0; }
command -v python3 >/dev/null 2>&1 || { echo "[greenboot-critical-gen] python3 missing -- no-op." >&2; exit 0; }

install -d -m 0755 "$(dirname "$OUT")"
python3 - "$TOML" "$OUT" <<'PY'
import sys, tomllib, re
toml_path, out_path = sys.argv[1], sys.argv[2]
with open(toml_path, "rb") as f:
    cfg = tomllib.load(f)
gb = cfg.get("greenboot", {})
services = gb.get("critical_services", []) or []
probes = gb.get("probe", {}) or {}

def mangle(name: str) -> str:
    # "agent-pipe" -> "AGENT_PIPE" (matches MIOS_PORT_* naming in install.env)
    return re.sub(r"[^A-Za-z0-9]", "_", name).upper()

lines = [
    "# AI-hint: GENERATED from mios.toml [greenboot] by mios-greenboot-critical-gen. DO NOT EDIT.",
    "# AI-related: usr/share/mios/mios.toml, usr/lib/greenboot/check/required.d/41-mios-critical-services.sh",
    'MIOS_GREENBOOT_CRITICAL_SERVICES="%s"' % " ".join(str(s) for s in services),
]
for s in services:
    m = mangle(str(s))
    p = probes.get(str(s), {}) if isinstance(probes, dict) else {}
    kind = str(p.get("kind", "tcp"))
    path = str(p.get("path", ""))
    lines.append('MIOS_GB_PROBE_%s_KIND="%s"' % (m, kind))
    if path:
        lines.append('MIOS_GB_PROBE_%s_PATH="%s"' % (m, path))
with open(out_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("[greenboot-critical-gen] wrote %d critical service(s) to %s" % (len(services), out_path))
PY
```

### A.3 Required check — `usr/lib/greenboot/check/required.d/41-mios-critical-services.sh`

SSOT-driven generalization of the hardcoded probe (mode `0755`). It supersedes the baked triple in `40-mios-ai-plane.sh:109-119`; once landed, reduce `40` to source this list (or retire `40` in favor of `41`).

```bash
#!/usr/bin/bash
# AI-hint: greenboot required check that verifies every mios.toml [greenboot].critical_services unit answered after boot, using SSOT ports from /etc/mios/install.env and the projected /etc/mios/greenboot-critical.env; degrades open (skips not-enabled or port-unresolved services) so only a genuine outage triggers bootc rollback.
# AI-related: /etc/mios/greenboot-critical.env, /etc/mios/install.env, usr/libexec/mios/mios-greenboot-critical-gen, usr/share/mios/mios.toml
set -euo pipefail

TIMEOUT=60; POLL=3; PROBE_TIMEOUT=3; HOST=127.0.0.1
log()  { echo "[mios-greenboot] $*"; }
fail() { echo "[mios-greenboot] $*" >&2; }

# Source SSOT-derived env (degrade-open on any glitch: a config bridge hiccup
# must never roll the OS back).
_src() { [[ -r "$1" ]] && { set +u; set -a; . "$1" 2>/dev/null || true; set +a; set -u; }; }
_src /etc/mios/install.env
_src /etc/mios/greenboot-critical.env

_tcp_up()  { local h="$1" p="$2"; timeout "$PROBE_TIMEOUT" bash -c "exec 3<>/dev/tcp/${h}/${p}" 2>/dev/null; }
_http_up() {
    local h="$1" p="$2" path="$3" code
    command -v curl >/dev/null 2>&1 || { _tcp_up "$h" "$p"; return; }
    code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$PROBE_TIMEOUT" "http://${h}:${p}${path}" 2>/dev/null || true)"
    case "$code" in [1-4][0-9][0-9]) return 0 ;; *) return 1 ;; esac
}

check_service() {
    local unit="$1" port="$2" kind="$3" path="${4:-}" deadline
    if ! systemctl is-enabled --quiet "$unit" 2>/dev/null; then log "${unit} not enabled here -- skip."; return 0; fi
    if [[ -z "$port" ]]; then log "${unit}: SSOT port unresolved -- skip (no hardcoded fallback)."; return 0; fi
    log "${unit}: probing ${kind} ${HOST}:${port}${path} (up to ${TIMEOUT}s)..."
    deadline=$(( $(date +%s) + TIMEOUT ))
    while true; do
        if [[ "$kind" == "http" ]]; then _http_up "$HOST" "$port" "$path" && { log "${unit}: healthy."; return 0; }
        else _tcp_up "$HOST" "$port" && { log "${unit}: healthy."; return 0; }; fi
        [[ $(date +%s) -ge $deadline ]] && { fail "FAIL: ${unit} did not answer within ${TIMEOUT}s."; return 1; }
        sleep "$POLL"
    done
}

# No SSOT list => nothing to assert (degrade-open, not a false rollback).
if [[ -z "${MIOS_GREENBOOT_CRITICAL_SERVICES:-}" ]]; then
    log "no [greenboot].critical_services projected -- skipping."
    exit 0
fi

rc=0
for svc in $MIOS_GREENBOOT_CRITICAL_SERVICES; do
    m="$(printf '%s' "$svc" | tr '[:lower:]-' '[:upper:]_')"      # agent-pipe -> AGENT_PIPE
    unit="mios-${svc}.service"
    port_var="MIOS_PORT_${m}";  port="${!port_var:-}"
    kind_var="MIOS_GB_PROBE_${m}_KIND"; kind="${!kind_var:-tcp}"
    path_var="MIOS_GB_PROBE_${m}_PATH"; path="${!path_var:-}"
    check_service "$unit" "$port" "$kind" "$path" || rc=1
done
[[ "$rc" -eq 0 ]] && log "critical services healthy (all enabled ones answered)."
exit "$rc"
```

### A.4 Build wiring — `automation/78-greenboot.sh`

Run the generator at build so `/etc/mios/greenboot-critical.env` is baked, and make the new check executable. Append after the existing `chmod +x` block (`78-greenboot.sh:30-33`):

```bash
# Project [greenboot].critical_services -> /etc/mios/greenboot-critical.env (SSOT).
if [[ -x /usr/libexec/mios/mios-greenboot-critical-gen ]]; then
    MIOS_TOML="${MIOS_TOML:-/usr/share/mios/mios.toml}" \
        /usr/libexec/mios/mios-greenboot-critical-gen || mios_warn "greenboot-critical projection failed (non-fatal)"
fi
chmod +x /usr/lib/greenboot/check/required.d/41-mios-critical-services.sh 2>/dev/null || true
```

(Re-render at firstboot is free: fold `mios-greenboot-critical-gen` into whatever `mios-sync-*` refreshes `/etc/mios/install.env`, so an operator `mios.toml` edit reprojects without a rebuild.)

### A.5 Drift-gate fix — `automation/98-drift-checks.sh:4294-4315`

Replace the hardcoded triple with the SSOT list so check 54 validates against `mios.toml`, not a copy:

```bash
check_greenboot() {
    echo "[38-drift-checks]   (54) greenboot health-coverage check"
    local gb_dir="$ROOT/usr/lib/greenboot/check/required.d"
    [[ -d "$gb_dir" ]] || { _fail "(54) greenboot required.d ($gb_dir) missing"; return; }

    # SSOT is the authority -- read [greenboot].critical_services, do NOT hardcode.
    local -a critical_services
    mapfile -t critical_services < <(python3 - "$ROOT/usr/share/mios/mios.toml" <<'PY'
import sys, tomllib
d = tomllib.load(open(sys.argv[1], "rb"))
for s in d.get("greenboot", {}).get("critical_services", []) or []:
    print(s)
PY
)
    local s f script_found
    for s in "${critical_services[@]}"; do
        script_found=0
        for f in "$gb_dir"/*; do
            [[ -f "$f" ]] && grep -q "$s" "$f" 2>/dev/null && { script_found=1; break; }
        done
        [[ "$script_found" -eq 0 ]] && _fail "(54) greenboot missing health-check coverage for critical service: $s"
    done
}
```

With `41-mios-critical-services.sh` present, `grep -q "$s"` matches the generalized loop's comments/derivation; more robustly the gate can assert the generated `/etc/mios/greenboot-critical.env` (or the generator's output) contains each `$s`.

### A.6 Verify (on MiOS-DEV / a Linux worktree)

```bash
# 1. Projection is correct:
MIOS_TOML=usr/share/mios/mios.toml MIOS_GREENBOOT_CRITICAL_ENV=/tmp/gb.env \
  usr/libexec/mios/mios-greenboot-critical-gen && cat /tmp/gb.env
#   -> MIOS_GREENBOOT_CRITICAL_SERVICES="agent-pipe llm-light pgvector"
#      MIOS_GB_PROBE_AGENT_PIPE_KIND="http"  MIOS_GB_PROBE_AGENT_PIPE_PATH="/v1/models"  ...

# 2. Check is a clean no-op with no env (degrade-open):
bash usr/lib/greenboot/check/required.d/41-mios-critical-services.sh; echo "rc=$?"   # rc=0

# 3. Drift gate reads SSOT, not a hardcode:
bash -c 'ROOT=. ; source automation/98-drift-checks.sh; check_greenboot'

# 4. End-to-end on the VM: edit [greenboot].critical_services, rebuild, then
#    `systemctl start greenboot-healthcheck` and confirm the new service is probed.
```

---

## B. Sequenced remediation plan

1. **Land drop-in §A** (greenboot critical-services SSOT wire) — generator + `41-*` check + `78-greenboot.sh` hook + drift-fix. Lowest-risk, highest-signal; removes 3 hardcodes. *(Per Law 15: mirror any shared SSOT change into `mios-bootstrap.git`'s `mios.toml` too.)*
2. **§8 NUT enablement gate** — enable `nut-server`/`nut-monitor` only when `[power.ups].name != ""` (render the decision in `43-nut-render.sh`, drop the unconditional `enable` at `90-mios.preset:51-52`). Stops per-boot churn on the default UPS-less image.
3. **§3 chrony PTP** — add `enable mios-chrony-ptp.service` to `90-mios.preset` (Condition-gated, no-op on bare metal).
4. **§2 LUKS consolidation** — delete `[security.luks]` + `mios-clevis-luks-gen`, retarget drift-check 67 at `[security.disk_encryption]`/`mios-luks-enroll`. Removes the second encryption SSOT.
5. **§4 `[gpu.vendors]`** — gate `25-gpu-cdi-toolkits.sh` + the `23-gpu-passthrough.sh` symlink loop on `MIOS_GPU_VENDORS_*`, or delete the section and document GPU as hardware-detected.
6. **§6 mdevctl + §7 lldap** — decide per feature: wire (add `[mdev]` / land the lldap container) or **remove the orphaned generator** and record the deferral. No silent dead binaries.
7. **§9 guacamole schema** + **§10 `[virt.v2v]` section** — completeness items; add the schema-init one-shot and the SSOT section.

**Definition of done (mirrors AGY-TASKS §834):** every shipped binary/unit is *SSOT-driven + smoke-verified*, **or** its deferral is documented with a reason. After steps 1–7, the only intentionally-inert surfaces are the operator-gated ones (`[identity.ipa].enabled=false`, `[storage.cephfs].enable=false`, `[power.ups].name=""`, `[virt.v2v].enabled=false`, `[security.disk_encryption]` no-op on TPM-less) — inert **by SSOT default**, not by dead wiring.
