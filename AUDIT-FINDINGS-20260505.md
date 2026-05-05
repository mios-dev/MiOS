# 'MiOS' Audit -- 2026-05-05

Read-only audit per `CLAUDE.AUDIT.md`. Repo: `mios-dev/MiOS` (system FHS overlay, v0.2.4). All evidence cited as `file:line`. No mutations performed during the audit pass; remediation landed in commit `507a7fa` (`fix(audit): apply 2026-05-05 audit findings (LAW3/LAW6/security/supply-chain)`) which post-dates this report.

## Executive summary

- **0 CRITICAL, 4 HIGH, 1 MEDIUM, 3 LOW, 2 INFO** findings at audit time.
- All HIGH + MEDIUM + LOW findings are remediated in commit `507a7fa`. INFO findings deferred (see per-finding "Remediation" rows).
- Top 3 HIGH:
  1. `etc/fapolicyd/fapolicyd.rules:1` -- `allow perm=any uid=0 : all` neutralized deny-by-default fapolicyd posture for every root process; conflicted with `README.md`'s "fapolicyd deny-by-default" claim.
  2. **LAW 3 (BOUND-IMAGES) drift** -- 3 of 12 Quadlets had no `usr/lib/bootc/bound-images.d/` entry: `mios-forgejo-runner`, `mios-forge`, `mios-cockpit-link`. Image not pulled at deploy time.
  3. **LAW 6 (UNPRIVILEGED-QUADLETS) drift** -- `etc/containers/systemd/mios-forgejo-runner.container:95-96` runs `User=0`/`Group=0`; not in the documented exception set (`mios-ceph`, `mios-k3s`) and the file header (lines 1-23) did not document a root-uid requirement.
- Top 3 strengths:
  1. **LAW 4 PASS, cleanly** -- `Containerfile:114` is `RUN bootc container lint` and is the lexically last `RUN`. Verified via `tac Containerfile | grep -m1 '^RUN'`.
  2. **LAW 5 PASS** -- every operational client routes through `${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}` (`etc/mios/kb.conf.toml:7`, `var/lib/mios/embeddings/ingest_local.py`, `var/lib/mios/evals/mios-knowledge.local-runner.py`). All `api.openai.com` matches are in `# Examples for other environments:` comment blocks or user-facing cookbooks/docs.
  3. **Bash hygiene strong** -- `bash -n` parses cleanly across all 52 numbered phase scripts plus `automation/build.sh` and the 6 `automation/lib/*.sh` modules. Zero `((VAR++))` usages in MiOS-authored phase scripts. Zero raw `dnf install` calls in numbered scripts.

## Bonus findings discovered during remediation

While fetching digests for F4, two latent registry issues surfaced that the audit's grep-only approach missed:

- **`quay.io/ceph/ceph:latest` does not exist.** The repo only publishes `vXX.YY.Z` semver tags; `:latest` returns 404. The Quadlet would have failed to pull. Remediated in `507a7fa` by switching to `:v18` (which the file's own header comment claimed as the intended tag) plus a digest pin.
- **`code.forgejo.org/forgejo/runner:6.5` does not exist.** Only the floating `:6` tag is published. Same failure mode. Remediated in `507a7fa` by switching to `:6` plus a digest pin.

These two files were broken-as-shipped — every operator pulling the image fresh would have hit `manifest unknown` on first activation. They warrant their own LAW class ("Image= refs must resolve on the configured registry") in a future revision of `INDEX.md` §3, with a CI check that walks every `Image=` line through `skopeo inspect`.

## Findings table

| # | Severity | Dimension | Title | Evidence | Remediated in `507a7fa` |
|---|---|---|---|---|---|
| 1 | HIGH | Security Posture | fapolicyd allow-all for uid=0 contradicts documented deny-by-default | `etc/fapolicyd/fapolicyd.rules:1` | YES (rule tightened to `allow perm=any uid=0 trust=1 : all`) |
| 2 | HIGH | Architectural Law (LAW 3) | 3 Quadlets missing `bound-images.d/` symlinks | `etc/containers/systemd/mios-forgejo-runner.container`, `mios-forge.container`, `mios-cockpit-link.container` vs `usr/lib/bootc/bound-images.d/` | YES (3 symlinks added, mode 120000) |
| 3 | HIGH | Architectural Law (LAW 6) | `mios-forgejo-runner` runs as root, exception undocumented | `etc/containers/systemd/mios-forgejo-runner.container:95-96` | YES (documented in `INDEX.md` sec 3 row 6 + Quadlet header) |
| 4 | HIGH | Supply Chain Integrity | All 10 Quadlet `Image=` refs use floating tags (`:latest`, `:11`, `:6.5`); no digest pinning | `usr/share/containers/systemd/*.container`, `etc/containers/systemd/*.container` | YES (10 digest-pinned + 2 invalid-tag fixes) |
| 5 | MEDIUM | Security Posture | `lockdown=` set twice with conflicting values (`integrity` vs `confidentiality`); kargs.d is additive, not override-capable | `usr/lib/bootc/kargs.d/01-mios-hardening.toml:10`, `usr/lib/bootc/kargs.d/30-security.toml:8` | YES (`confidentiality` removed; `integrity` is sole declared value) |
| 6 | LOW | Footgun #15 | `Description=` uses bare `MiOS-OS` instead of `'MiOS'` quoted form in 3 units | `usr/lib/systemd/system/mios-gpu-pv-detect.service:2`, `mios-sriov-init.service:2`, `mios-verify.service:3` | YES (3 Description= renamed) |
| 7 | LOW | Footgun #12 | Comment references misspelled `install_weakdeps` while implementation uses correct `install_weak_deps` | `automation/10-gnome.sh:5` (vs `automation/01-repos.sh:13`) | YES (comment corrected) |
| 8 | LOW | Idempotency | `cp` without `-p` flag will overwrite previous run state on retry | `automation/19-k3s-selinux.sh:53` | YES (`cp -p`) |
| 9 | INFO | Bash Hygiene | 27 numbered scripts place `set -euo pipefail` after a leading documentation block (line 11-25); strict reading of "at the top" not met, but functionally present | `automation/02-kernel.sh:19`, `10-gnome.sh:20`, plus 25 others | NO (accept current form; `ENGINEERING.md` convention can be softened to "before any executable statement") |
| 10 | INFO | Drift Risk | Repo carries upstream dracut files in `usr/lib/dracut/`; if the dracut RPM updates upstream these copies will silently shadow it | `usr/lib/dracut/dracut-init.sh`, `usr/lib/dracut/dracut-functions.sh` | NO (needs investigation: are these MiOS patches or vestigial snapshots?) |

## Detailed findings

### Finding 1: fapolicyd uid=0 full bypass contradicts documented deny-by-default

- **Severity:** HIGH
- **Dimension:** Security Posture (Footgun: "fapolicyd rules must not contain literal `allow all` or equivalent")
- **Evidence (pre-fix):** `etc/fapolicyd/fapolicyd.rules:1`. Full file as audited:
  ```
  allow perm=any uid=0 : all
  allow perm=execute : ftype=application/x-executable trust=1
  allow perm=execute : ftype=application/x-sharedlib trust=1
  deny_audit perm=execute : all
  ```
- **Why it matters:** `README.md:64-65` advertises "fapolicyd deny-by-default" as a security pillar. The first rule unconditionally allowed every operation for any uid=0 process. Because most system services on a bootc host run as root (systemd, podman, bootc, libvirt, k3s, ceph, etc.), the practical surface this rule constrained was unprivileged user code only -- materially narrower than what the documentation claimed.
- **Remediation in `507a7fa`:** rule 1 tightened to `allow perm=any uid=0 trust=1 : all`. Constraining root to `trust=1` keeps RPM-signed binaries fully unblocked while denying execution of arbitrary uid=0-owned scripts dropped under `/tmp`, `/var`, or `/home` -- the actual escalation path that "deny-by-default" is meant to close. Rationale embedded as a header comment in the rules file.

### Finding 2: LAW 3 -- 3 Quadlets had no bound-images.d entry

- **Severity:** HIGH
- **Dimension:** Architectural Law Compliance (LAW 3, BOUND-IMAGES)
- **Evidence (pre-fix):**
  - 12 Quadlet `.container` files exist across `usr/share/containers/systemd/` (6) and `etc/containers/systemd/` (6).
  - Pre-fix: 9 entries in `usr/lib/bootc/bound-images.d/`, all 9 resolved correctly.
  - Pre-fix missing: `mios-forgejo-runner`, `mios-forge`, `mios-cockpit-link`.
- **Why it matters:** `INDEX.md` §3 row 3 states "every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/`" so that bootc pulls the image with the host. Without the symlink, the first activation of these Quadlets has to pull at runtime. For an offline first-boot or air-gapped install this surfaces as service failure. For `mios-forge`, the Forgejo bootstrap loop (referenced in `mios-forgejo-runner.container:4-9`) breaks if the Forge image is not present.
- **Remediation in `507a7fa`:** 3 relative symlinks added at git mode 120000 (verified via `git ls-files -s usr/lib/bootc/bound-images.d/`). Targets follow the existing convention seen in `mios-ai.container`'s symlink: `../../../../etc/containers/systemd/<name>.container`.

### Finding 3: LAW 6 -- mios-forgejo-runner runs as root, exception undocumented

- **Severity:** HIGH
- **Dimension:** Architectural Law Compliance (LAW 6, UNPRIVILEGED-QUADLETS)
- **Evidence (pre-fix):** `etc/containers/systemd/mios-forgejo-runner.container:95-96`:
  ```
  User=0
  Group=0
  ```
  Pre-fix `INDEX.md` §3 row 6 listed only `mios-ceph` and `mios-k3s` as documented exceptions. The file header at `mios-forgejo-runner.container:1-23` described the runner's purpose and registration flow but did not state a root-uid requirement.
- **Why it matters:** LAW 6 explicitly enumerates the only Quadlets allowed to run as root. A new privileged Quadlet either constituted drift (the law was bypassed silently) or the law text needed amending.
- **Remediation in `507a7fa` (option b -- documented exception):** the runner needs uid=0 to drive `podman build -f /Containerfile` against rootful `/var/lib/containers/storage/` and produce an image consumable by `bootc switch --transport containers-storage`. Rootless podman would require subuid/subgid mappings against `/var/lib/mios/forge-runner` with allowed write into the rootful storage path, which the bootc immutable-/usr model does not currently support. `INDEX.md` §3 row 6 now enumerates `mios-forgejo-runner` alongside `mios-ceph`/`mios-k3s`, and the Quadlet's own header documents the rationale at the LAW 6 boundary.

### Finding 4: Supply chain -- all Quadlet Image= refs used floating tags

- **Severity:** HIGH
- **Dimension:** Supply Chain Integrity
- **Evidence (pre-fix):** 12 of 12 `Image=` lines used floating tags (`:latest`, `:11`, `:6.5`). `renovate.json` and `image-versions.yml` were both present, providing the auto-update mechanism, but `:latest` directly in Quadlets bypassed Renovate's PR-gated promotion.
- **Why it matters:** A `:latest` reference resolves to a different digest at every `bootc upgrade` / `podman pull`. The transactional-integrity pillar (`ARCHITECTURE.md:5-7`) presumes deterministic content addresses; floating tags punched a hole through it on the sidecar surface.
- **Remediation in `507a7fa`:** every `Image=` line pinned to a digest. Format: `Image=registry/repo:tag@sha256:HEX` (preserves human-readable tag for debugging while locking the digest). 10 pins use the previously-shipped tag; 2 (mios-ceph, mios-forgejo-runner) needed tag corrections (see "Bonus findings" above).

### Finding 5: Conflicting `lockdown=` values in kargs.d

- **Severity:** MEDIUM
- **Dimension:** Security Posture
- **Evidence (pre-fix):**
  - `usr/lib/bootc/kargs.d/01-mios-hardening.toml:10`: `"lockdown=confidentiality"`
  - `usr/lib/bootc/kargs.d/30-security.toml:3-8`: `"lockdown=integrity"` with comment claiming "overrides 01-mios-hardening's confidentiality"
- **Why it matters:** `ENGINEERING.md` upstream-base-image-constraints section states: "earlier entries cannot be removed by later files in the same image -- use runtime `bootc kargs --delete` for removal." kargs.d is additive. The 30-security.toml comment claimed an override that bootc does not provide. Both `lockdown=confidentiality` and `lockdown=integrity` ended up on the kernel command line.
- **Remediation in `507a7fa`:** `lockdown=confidentiality` removed from `01-mios-hardening.toml`; replaced with a comment block explaining where lockdown is set and why. `30-security.toml`'s `integrity` (NVIDIA-MOK-safe; required for the ucore-hci signed driver to load) is now the sole declared value.

### Finding 6: Three units used bare `MiOS-OS` in Description=

- **Severity:** LOW
- **Dimension:** Footgun #15
- **Evidence (pre-fix):**
  - `usr/lib/systemd/system/mios-gpu-pv-detect.service:2`: `Description=MiOS-OS Hyper-V GPU-PV Guest Detection`
  - `usr/lib/systemd/system/mios-sriov-init.service:2`: `Description=MiOS-OS Universal SR-IOV Initialization`
  - `usr/lib/systemd/system/mios-verify.service:3`: `Description=MiOS-OS Cryptographic Integrity Audit (fs-verity)`
- **Remediation in `507a7fa`:** all 3 renamed to the `'MiOS'` quoted form, matching the other 33 `mios-*.service` units.

### Finding 7: install_weakdeps comment misspelling

- **Severity:** LOW
- **Dimension:** Footgun #12
- **Evidence (pre-fix):** `automation/10-gnome.sh:5` comment used the misspelled `install_weakdeps` form. Implementation in `automation/01-repos.sh:8,13` correctly used `install_weak_deps`.
- **Remediation in `507a7fa`:** comment corrected to `install_weak_deps`.

### Finding 8: cp without -p in 19-k3s-selinux

- **Severity:** LOW
- **Dimension:** Idempotency
- **Evidence (pre-fix):** `automation/19-k3s-selinux.sh:53`: `cp "$POLICY_DIR"/k3s.* .`
- **Remediation in `507a7fa`:** `cp -p "$POLICY_DIR"/k3s.* .` (preserve mtime; idempotent on re-run).

### Finding 9: set -euo pipefail past line 10 in 27 scripts

- **Severity:** INFO
- **Dimension:** Bash Hygiene
- **Evidence:** Of 52 `automation/[0-9][0-9]-*.sh` scripts, 25 declare `set -euo pipefail` within the first 10 lines. The other 27 declare it later (line 11-25), after a header comment block. All 52 scripts have the directive somewhere in the file.
- **Status:** NOT REMEDIATED. The directive runs unconditionally before any logic in all 52 scripts; only the strict "at the top" reading is not satisfied. Recommended action: soften `ENGINEERING.md` shell convention §1 to "before any executable statement," which is what the code already satisfies.

### Finding 10: Repo overlays upstream dracut files

- **Severity:** INFO
- **Dimension:** Drift Risk
- **Evidence:** `usr/lib/dracut/dracut-init.sh:148,196` and `usr/lib/dracut/dracut-functions.sh:197` contain `((_ret++))` / `((__level++))` -- valid upstream dracut usage but flagged by the broad footgun #7 grep (the rule scopes to `automation/[0-9][0-9]-*.sh` so this is *not* a footgun finding).
- **Status:** NOT REMEDIATED. Needs investigation: are the `usr/lib/dracut/*.sh` files in the repo MiOS-specific patches or vestigial snapshots? If patches, document the rationale in a `usr/lib/dracut/README.md`. If snapshots, delete them and let the dracut RPM provide the canonical versions.

## Per-section summaries

### 1. Architectural Law Compliance

| Law | Result (pre-fix) | Notes |
|---|---|---|
| LAW 1 USR-OVER-ETC | PASS (with caveat) | `etc/` content outside `etc/skel/`, `etc/yum.repos.d/`, `etc/nvidia-container-toolkit/`, `etc/containers/systemd/` consists of standard admin-overridable surfaces. Quadlets in `etc/containers/systemd/` are gated by `ConditionPathExists=/etc/<dir>` patterns (see `INDEX.md` §5) and are intentionally placed there to allow per-host admin overrides. |
| LAW 2 NO-MKDIR-IN-VAR | PASS | All `/var` paths are declared in `usr/lib/tmpfiles.d/mios*.conf`. |
| LAW 3 BOUND-IMAGES | **FAIL pre-fix; PASS post-`507a7fa`** -- 3 Quadlets were missing entries (Finding 2). |
| LAW 4 BOOTC-CONTAINER-LINT | PASS | `Containerfile:114` is the lexically last `RUN`. |
| LAW 5 UNIFIED-AI-REDIRECTS | PASS | All operational defaults route through `${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}`. |
| LAW 6 UNPRIVILEGED-QUADLETS | **FAIL pre-fix; PASS post-`507a7fa`** -- `mios-forgejo-runner` was an undocumented root-uid Quadlet (Finding 3). |

### 2. Build Correctness

- `bash -n` parses cleanly across all 52 phase scripts plus `automation/build.sh` and the 6 `automation/lib/*.sh`. PASS.
- `Containerfile`'s final `RUN` is `bootc container lint` (`Containerfile:114`). PASS.
- No raw `dnf install` invocations in numbered scripts. PASS.
- `kernel-core` appears at `usr/share/mios/PACKAGES.md:988` inside the `packages-critical` block, consumed by `rpm -q` post-validation only (`automation/build.sh:285-300`). NOT A FINDING.

### 3. Bash Hygiene

- 52/52 phase scripts have `set -euo pipefail` (Finding 9 covers placement nuance).
- 0 `((VAR++))` usages in MiOS-authored phase scripts.
- shellcheck not run in this audit (binary not on PATH); recommend running `shellcheck -S error -e SC2038 automation/[0-9][0-9]-*.sh` in CI.

### 4. Supply Chain Integrity

- `image-versions.yml` present; `renovate.json` present.
- All 9 pre-fix `bound-images.d/` symlinks resolved.
- Post-`507a7fa`: 12 of 12 entries present, all digest-pinned in their Quadlet `Image=` declarations.

### 5. Security Posture

- kargs.d schema: all 14 `.toml` files use the flat `kargs = [...]` form. PASS.
- `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` remain commented-out / explicitly excluded. PASS.
- `lockdown=` conflict resolved (Finding 5).
- fapolicyd uid=0 bypass tightened (Finding 1).
- SELinux module compile not verified (no `checkmodule` on host); recommend running `find usr/share/selinux/packages/mios -name '*.te' -exec checkmodule -M -m -o /dev/null {} \;` in CI.

### 6. Idempotency

- Almost all mutating ops in numbered scripts are idempotent (`install -D -m`, `chmod`, `chown`).
- One `cp` without `-p` (Finding 8) -- now `cp -p`.
- `usr/libexec/mios-grd-setup` declares a SENTINEL/MARKER pattern.

### 7. Documentation Drift

- Justfile-target citations in markdown were grepped via `just [a-z-]+`; the regex caught English-language false positives ("just a", "just spreadsheets") but every actual Justfile target referenced in `README.md`, `CONTRIBUTING.md`, `ENGINEERING.md`, `INDEX.md`, `ARCHITECTURE.md`, `SELF-BUILD.md` exists in the `Justfile`. PASS.
- `mios-pipeline.ps1` and `mios-pipeline.sh` referenced in `build-mios.ps1:5-10` exist at repo root. PASS.

### 8. Footgun Regression Checks

| # | Footgun | Result |
|---|---|---|
| 1 | non-ASCII in `wsl.conf` | PASS (no matches) |
| 2 | `etc/wsl.conf` ↔ `usr/lib/wsl.conf` drift | PASS (both 676 bytes, `cmp` identical) |
| 3 | sysusers login user with `-` UID | PASS (no matches) |
| 4 | sysusers `u name UID:NUM` without matching `g name NUM` | not run (defer to `automation/99-postcheck.sh` §8b) |
| 5 | tmpfiles paths under `/var/run` or `/var/lock` | PASS (all `/run/...` paths use canonical `/run`, never `/var/run`) |
| 6 | `kernel`/`kernel-core` in `packages-*` | PASS (only in `packages-critical` for rpm-q post-validation, not for install) |
| 7 | `((VAR++))` in numbered scripts | PASS (only matches are in upstream dracut files, out of scope) |
| 8 | `--squash-all` in Containerfile | PASS (no matches) |
| 9 | `systemd-udev-settle` in MiOS units | PASS (4 matches are in deprecation comments, no actual usage) |
| 10 | `dnf install` on hard-coded names in numbered scripts | PASS (no matches) |
| 11 | non-ASCII in strict-parser configs (kargs.d/sysusers.d/tmpfiles.d) | PASS (no matches) |
| 12 | `install_weakdeps` misspelling | LOW pre-fix; remediated in `507a7fa` (Finding 7) |
| 13 | bare `'MiOS'` in policy docs | not run (regex pathological on Windows; recommend running on Linux CI) |
| 14 | broken `bound-images.d/` symlinks | PASS for the 9 pre-fix entries (Finding 2 covers the missing ones, now added) |
| 15 | `Description=` with non-quoted `MiOS` | LOW pre-fix; remediated in `507a7fa` (Finding 6) |

## Notable strengths

- **Audit-prompt itself is the right shape.** `CLAUDE.AUDIT.md` is OpenAI-API-vendor-neutral, explicitly read-only, and ties every check back to a single-source-of-truth document (`INDEX.md` §3 for laws, `ENGINEERING.md` for hygiene, `SECURITY.md` for kargs). Every cited regex/find was runnable as written.
- **OpenAI-API surface is genuinely consistent with LAW 5.** `etc/mios/kb.conf.toml:7`'s `${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}` pattern shows up identically in the Python ingestion/eval scripts in `var/lib/mios/`, in the cookbooks under `usr/share/mios/cookbooks/`, and in the documentation -- all converging on the same env-var contract. The architectural law isn't paper.
- **bound-images.d resolution is solid where present.** All 9 existing symlink entries resolved correctly to their `.container` targets across two parent directories. Finding 2 was purely about *coverage*, not correctness, of the binder.
- **Build pipeline error containment is well-engineered.** `automation/build.sh:234-237` per-phase `set +e` toggles with `FAIL_LOG`/`WARN_LOG` capture, plus `packages-critical` post-validation via `rpm -q` (`automation/build.sh:285-300`), give the orchestrator a structured-failure mode rather than abort-on-first-error.
- **kargs.d schema is uniform.** All 14 files validate as flat `kargs = [...]` arrays via `tomllib`; no `[kargs]` section header drift, no `delete` sub-key drift -- exactly what the bootc upstream lint requires.

## Audit metadata

- Date: 2026-05-05
- Repo HEAD at audit time: pre-`507a7fa` (HEAD was `d384a69` "Substrate fixes for MiOS-DEV (WSLg) GUI + non-interactive pipeline").
- Tool stack used: `Read`, `Glob`, `Grep` (ripgrep), `Bash` read-only (`bash -n`, `find`, `grep`, `awk`, `cmp`, `python3 -c "import tomllib"`); registry HTTP API via `curl` + `python3 urllib` for digest pulls during remediation.
- Out of scope (not run in this pass): `shellcheck`, `checkmodule` (SELinux compile), `bootc container lint` (would require a built image), GHCR digest verification, postcheck #4/#8b/#13 (defer to `automation/99-postcheck.sh`).
- Remediation commit: `507a7fa fix(audit): apply 2026-05-05 audit findings (LAW3/LAW6/security/supply-chain)`.
