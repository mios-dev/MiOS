# MiOS Build-Stack Audit — 2026-05-01

**Auditor:** Claude Code (model: claude-sonnet-4-6)
**Scope:** mios@2a5561c3c5461698c5681f45fffbd5c6848325c0, mios-bootstrap@N/A (single repo)
**Methodology:** CLAUDE.AUDIT.md framework
**Total findings:** 26 (3 CRITICAL, 7 HIGH, 9 MEDIUM, 5 LOW, 2 INFO)

---

## Executive Summary

The MiOS v0.2.0 build stack is a technically ambitious, well-structured bootc image with a strong security posture in its kernel hardening, SELinux policies, greenboot integration, and composefs-verity enforcement. However, three critical defects undermine build integrity: (1) `bootc container lint` runs in a separate RUN layer after `ostree container commit`, meaning lint findings cannot prevent a committed image; (2) `42-cosign-policy.sh` downloads a URL that identifies as `v0.2.0` — a string that does not correspond to any real cosign release and will 404 at build time; and (3) `mios-k3s.container` ships a hardcoded plaintext cluster token baked permanently into the image. Seven high-severity findings cover the non-fatal CI smoke test, floating base image tag, missing GPG validation on Fedora repo metadata, unverified binary downloads for aichat/Bibata cursor, the k3s-selinux repo cloned at HEAD without commit pinning, and the `99-postcheck.sh` double-invocation ordering bug. The stack is production-class in its architectural intent but requires targeted remediation before it can be considered release-ready.

---

## Findings by Severity

| ID | Severity | Category | File:Line | One-line summary |
|---|---|---|---|---|
| F-01 | CRITICAL | Build Correctness | `Containerfile:57-58` | `bootc container lint` runs after `ostree container commit` — lint cannot block a committed image |
| F-02 | CRITICAL | Supply Chain | `automation/42-cosign-policy.sh:20` | cosign fallback downloads `v0.2.0` — not a real cosign release; will 404, leaving cosign unverified |
| F-03 | CRITICAL | Security Posture | `etc/containers/systemd/mios-k3s.container:13` | Hardcoded `K3S_TOKEN=mios-cluster-secret` baked into image — all deployments share a known secret |
| F-04 | HIGH | Supply Chain | `Containerfile:2` | Base image uses floating tag `ucore-hci:stable-nvidia` — not pinned to digest; non-reproducible builds |
| F-05 | HIGH | Supply Chain | `automation/01-repos.sh:31-44` | Fedora 44 repo added with `gpgcheck=0` and `repo_gpgcheck=0` — no RPM signature validation |
| F-06 | HIGH | Supply Chain | `automation/37-aichat.sh:36-41` | aichat and aichat-ng binaries downloaded without sha256 verification |
| F-07 | HIGH | Supply Chain | `automation/19-k3s-selinux.sh:13` | k3s-selinux policy cloned at HEAD without commit hash — untrusted supply chain |
| F-08 | HIGH | Supply Chain | `automation/10-gnome.sh:96` | Bibata cursor downloaded without sha256 verification |
| F-09 | HIGH | Build Correctness | `automation/build.sh:187-191` + glob | `99-postcheck.sh` invoked twice: via glob loop AND explicitly in `build.sh:189` |
| F-10 | HIGH | Build Correctness | `automation/99-cleanup.sh:48` + `Containerfile:57` | `ostree container commit` runs twice: in `99-cleanup.sh` and in the Containerfile |
| F-11 | HIGH | CI | `.github/workflows/mios-ci.yml:91` | Smoke test is non-fatal (`\|\| echo 'WARN: smoke build failed'`) — broken PRs merge silently |
| F-12 | MEDIUM | Supply Chain | `etc/containers/systemd/mios-ceph.container:10` | Ceph container uses `quay.io/ceph/ceph:latest` — mutable tag, no digest pin |
| F-13 | MEDIUM | Architectural Law | `etc/containers/systemd/mios-k3s.container:12` | K3s quadlet runs `Privileged=true` — violates UNPRIVILEGED-EXECUTION architectural law |
| F-14 | MEDIUM | Architectural Law | `etc/containers/systemd/mios-k3s.container` + `mios-ceph.container` | `mios-k3s.container` and `mios-ceph.container` have no `User=` directive — run as root inside Podman |
| F-15 | MEDIUM | Build Correctness | `automation/49-finalize.sh:29` | `49-finalize.sh` calls `dnf5 clean all` directly, bypassing `$DNF_BIN` abstraction |
| F-16 | MEDIUM | Build Correctness | `automation/90-generate-sbom.sh:18` | `90-generate-sbom.sh` calls `dnf install -y syft` directly, bypassing `$DNF_BIN` |
| F-17 | MEDIUM | Reproducibility | `automation/90-generate-sbom.sh:25` | SBOM filename includes `date +%Y%m%dT%H%M%SZ` timestamp — breaks bit-for-bit reproducibility |
| F-18 | MEDIUM | Bash Hygiene | Multiple files | Six library files exist in triplicate (`automation/`, `automation/lib/`, `automation/lib_*.sh`) — divergence risk |
| F-19 | MEDIUM | Bash Hygiene | `automation/common.sh` et al. | Six library/helper scripts missing `set -euo pipefail` |
| F-20 | MEDIUM | Security Posture | `usr/share/pki/containers/` | Directory is empty — `policy.json` references keys absent from the overlay |
| F-21 | LOW | Documentation | `automation/42-cosign-policy.sh:8,17` | Comment says "pinned to v2.x" but code downloads `v0.2.0` — contradictory inline documentation |
| F-22 | LOW | Documentation | `image-versions.yml:13` | `ucore_hci_stable_nvidia_digest` contains a malformed SHA256 (invalid hex) |
| F-23 | LOW | Documentation | `image-versions.yml:22` | `image_builder_cli_digest` is all zeros — Renovate has not populated it |
| F-24 | LOW | Build Correctness | `Containerfile:43` + `PACKAGES.md:75` | `kernel-devel` installed twice: in Containerfile and via `packages-kernel` in PACKAGES.md |
| F-25 | LOW | Architectural Law | `automation/08-system-files-overlay.sh:56` | `mkdir -p /var/home` at build time — deviation from STATELESS-VAR law |
| F-26 | INFO | Security Posture | `usr/lib/bootc/kargs.d/01-mios-hardening.toml` | `init_on_alloc=1` and `init_on_free=1` commented out but SECURITY.md claims them active |

---

## Detailed Findings

---

### F-01 — CRITICAL | Build Correctness | `Containerfile:57-58`

**Evidence:**
```
Containerfile:57: RUN rm -rf /ctx && ostree container commit
Containerfile:58: RUN bootc container lint
```

**Defect:** `bootc container lint` is placed in its own `RUN` layer *after* `ostree container commit`. Each `RUN` in a Containerfile is a separate layer. `ostree container commit` finalizes the OSTree metadata for the image. Any lint failure in the following `RUN` layer would fail the lint layer, but the commit has already been made. Lint is also validating a different layer state than the one that was committed (the `/ctx` deletion happened in the prior `RUN`). The correct architecture is lint-then-commit, not commit-then-lint.

**Recommendation:** Merge `bootc container lint` into the same `RUN` block as `ostree container commit`, before the commit call:
```dockerfile
RUN rm -rf /ctx && bootc container lint && ostree container commit
```

---

### F-02 — CRITICAL | Supply Chain | `automation/42-cosign-policy.sh:19-20`

**Evidence:**
```bash
log "  downloading cosign v0.2.0 static binary..."
scurl "https://github.com/sigstore/cosign/releases/download/v0.2.0/cosign-linux-amd64" -o /usr/local/bin/cosign
```
Comment on line 17: `# 1. Install cosign binary (pinned to v2.x for rpm-ostree compatibility)`

**Defect:** The URL references cosign `v0.2.0` — a string that is the MiOS project version, not a cosign release version. Real cosign release numbering starts at v1.x (the first cosign release was v1.0.0). The URL `sigstore/cosign/releases/download/v0.2.0/cosign-linux-amd64` will return a 404. The comment on line 17 says "v2.x" while code uses "v0.2.0" — a copy-paste of the MiOS version string. No checksum verification is present. The `if ! command -v cosign` guard means this fallback only triggers if the DNF-installed cosign (from `packages-containers`) is absent; if the DNF install succeeded, the bug is silently bypassed. If it didn't, an empty or error-page binary is placed at `/usr/local/bin/cosign`.

**Recommendation:** Replace with the actual current cosign release URL (e.g., `v2.4.0`) and add sha256 verification using the official cosign checksums file. Preferably, remove the fallback entirely and rely on DNF.

---

### F-03 — CRITICAL | Security Posture | `etc/containers/systemd/mios-k3s.container:13`

**Evidence:**
```ini
Environment=K3S_TOKEN=mios-cluster-secret
```

**Defect:** A hardcoded cluster authentication token is baked into the OCI image at build time. Every deployed system shares the same well-known K3s token `mios-cluster-secret`. This token: (1) is inspectable by anyone with image pull access via `podman inspect`, (2) is identical across all deployments enabling lateral movement between K3s clusters, (3) is in a public GitHub repository. Any attacker who can pull the image or access the repository immediately knows the K3s cluster secret.

**Recommendation:** Remove `Environment=K3S_TOKEN=` from the quadlet. Generate a random token at first-boot via a `ConditionPathExists=!/etc/rancher/k3s/token` oneshot service, or inject at install time via a secrets mechanism (e.g., systemd credentials, cloud-init user-data).

---

### F-04 — HIGH | Supply Chain | `Containerfile:2`

**Evidence:**
```dockerfile
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia
```

**Defect:** The base image uses the floating tag `stable-nvidia`. Every build may pull a different upstream image. `image-versions.yml` documents a SHA256 digest but states "USAGE: This file is reference documentation — the Containerfile now uses digests" — but the Containerfile does NOT use a digest. Renovate is mentioned but only updates `image-versions.yml`, not the Containerfile ARG. The documented digest in `image-versions.yml:13` is also malformed (see F-22).

**Recommendation:** Pin the Containerfile ARG to a validated digest:
```dockerfile
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia@sha256:<valid-64-hex-digest>
```
Configure Renovate's `fileMatch` to update the Containerfile ARG directly.

---

### F-05 — HIGH | Supply Chain | `automation/01-repos.sh:31-44`

**Evidence:**
```ini
[fedora-44]
...
repo_gpgcheck=0
gpgcheck=0
```

**Defect:** The Fedora 44 repository is added with both `gpgcheck=0` (disables RPM signature verification) and `repo_gpgcheck=0` (disables repository metadata signature verification). Every RPM installed from this repo is accepted without cryptographic verification. Combined with metalink HTTP-redirect chains, this creates a MITM attack surface during the build.

**Recommendation:** Enable `gpgcheck=1` and `repo_gpgcheck=1`. Import the Fedora 44 GPG key before adding the repo:
```bash
rpm --import https://getfedora.org/static/fedora.gpg
```
Then set `gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64` in the repo definition.

---

### F-06 — HIGH | Supply Chain | `automation/37-aichat.sh:36-41`

**Evidence:**
```bash
scurl -L -o /tmp/aichat.tar.gz "https://github.com/sigoden/aichat/releases/download/${AICHAT_TAG}/..."
tar -xzf /tmp/aichat.tar.gz -C /usr/bin/ aichat
```
No sha256sum verification step present.

**Defect:** The aichat and aichat-ng binaries are downloaded and installed directly to `/usr/bin/` without integrity verification. A compromised release, tag hijack, or MITM attack during build results in an arbitrary binary in the system path.

**Recommendation:** Download the `.sha256` sidecar file from the GitHub release and verify:
```bash
scurl -L -o /tmp/aichat.tar.gz.sha256 "${AICHAT_URL}.sha256"
sha256sum -c /tmp/aichat.tar.gz.sha256
```

---

### F-07 — HIGH | Supply Chain | `automation/19-k3s-selinux.sh:13`

**Evidence:**
```bash
git clone --depth 1 https://github.com/k3s-io/k3s-selinux.git /tmp/k3s-selinux
```

**Defect:** The k3s-selinux SELinux policy is cloned at the branch HEAD with no specific commit hash or tag checkout. Any push to the upstream repository changes what policy is compiled into the image. The compiled `.pp` file is installed to `/usr/share/selinux/packages/mios/k3s.pp` without verification.

**Recommendation:** Pin to a specific commit hash using `git checkout <sha>` after clone, or vendor the specific `.te` source file into the repository directly to eliminate the runtime network dependency.

---

### F-08 — HIGH | Supply Chain | `automation/10-gnome.sh:96`

**Evidence:**
```bash
if scurl -fSL --retry 3 --retry-delay 5 "$BIBATA_URL" -o /tmp/bibata.tar.xz; then
    if tar -xf /tmp/bibata.tar.xz -C /usr/share/icons/; then
```
No sha256 verification between download and extraction.

**Defect:** The Bibata cursor theme tarball is extracted to `/usr/share/icons/` without checksum verification. A compromised GitHub release or MITM attack during build could result in arbitrary files extracted into the icon tree.

**Recommendation:** Verify against the SHA256 published alongside the GitHub release before extracting.

---

### F-09 — HIGH | Build Correctness | `automation/build.sh:62-90` + `automation/build.sh:187-191`

**Evidence:**
```bash
# In the numbered script loop (runs 99-postcheck.sh as part of glob):
for script in "$SCRIPT_DIR"/[0-9][0-9]-*.sh; do
    bash "$script"
done
# After the loop, explicit second invocation:
if [[ -f "${SCRIPT_DIR}/99-postcheck.sh" ]]; then
    bash "${SCRIPT_DIR}/99-postcheck.sh"
fi
```
`99-postcheck.sh` is NOT in `CONTAINERFILE_SCRIPTS` skip list.

**Defect:** `99-postcheck.sh` executes twice per build: once in the glob loop (it matches `[0-9][0-9]-*.sh`) and once explicitly in the post-loop validation block. Additionally, `99-cleanup.sh` (which runs before `99-postcheck.sh` alphabetically in the loop) calls `ostree container commit` — making all validation happen after the image is committed.

**Recommendation:** Add `99-postcheck.sh` to the `CONTAINERFILE_SCRIPTS` skip list so it only runs via the explicit post-loop invocation. Move `ostree container commit` out of `99-cleanup.sh` entirely.

---

### F-10 — HIGH | Build Correctness | `automation/99-cleanup.sh:48` + `Containerfile:57`

**Evidence:**
```bash
# automation/99-cleanup.sh:47-48:
echo "[99-cleanup] Running ostree container commit..."
ostree container commit 2>&1 || true

# Containerfile:57:
RUN rm -rf /ctx && ostree container commit
```

**Defect:** `ostree container commit` is called inside `build.sh`'s mega-RUN block (via `99-cleanup.sh`) and then called again explicitly in the Containerfile after the mega-RUN block. Running `ostree container commit` twice may produce incorrect layer metadata or undefined behavior. The first commit (in 99-cleanup.sh) happens before postcheck validation completes.

**Recommendation:** Remove `ostree container commit` from `99-cleanup.sh`. The Containerfile is the sole authoritative commit point.

---

### F-11 — HIGH | CI | `.github/workflows/mios-ci.yml:91`

**Evidence:**
```yaml
podman build -t mios:smoke -f Containerfile . || echo 'WARN: smoke build failed (non-fatal in PR)'
```

**Defect:** The smoke test job is explicitly non-fatal. A PR that completely breaks the build will show a green check on `smoke-test` and be mergeable. The `smoke-test` job only runs on PRs; the full `build` job runs only on pushes/tags. This means the full build is never tested before merge.

**Recommendation:** Remove the `|| echo '...'` to make the smoke build fatal. Consider running the full build on PRs with `push: false`.

---

### F-12 — MEDIUM | Supply Chain | `etc/containers/systemd/mios-ceph.container:10`

**Evidence:**
```ini
Image=quay.io/ceph/ceph:latest
```

**Defect:** The Ceph container uses the `latest` mutable tag with no digest pinning. Different deployments may pull different Ceph versions, breaking cluster consistency. The other containers use version tags (`v2.20.0`, `v1.32.1-k3s1`) but none use digests.

**Recommendation:** Pin all quadlet images to immutable digests. Manage updates via Renovate.

---

### F-13 — MEDIUM | Architectural Law (UNPRIVILEGED-EXECUTION) | `etc/containers/systemd/mios-k3s.container:12`

**Evidence:**
```ini
Privileged=true
```
`ENGINEERING.md`: "All sidecar containers execute as unprivileged service accounts."
`INDEX.md` Operational Invariants: "UNPRIVILEGED-EXECUTION: All agent containers execute without root privileges."

**Defect:** `mios-k3s.container` runs with `Privileged=true`, giving K3s full host capabilities. This violates the documented architectural invariant.

**Recommendation:** Document the K3s exception explicitly in ARCHITECTURE.md with rationale, or replace `Privileged=true` with specific capability grants (e.g., `AddCapability=NET_ADMIN,SYS_ADMIN,NET_RAW,...`).

---

### F-14 — MEDIUM | Architectural Law (UNPRIVILEGED-EXECUTION) | `etc/containers/systemd/mios-k3s.container` + `mios-ceph.container`

**Evidence:**
```
mios-k3s.container: no User= directive (grep -c 'User=' → 0)
mios-ceph.container: no User= directive (grep -c 'User=' → 0)
mios-ai.container: User=mios-ai (compliant)
```

**Defect:** Two of three quadlets run as root (uid 0) inside Podman. In conjunction with `Privileged=true` for K3s, this is maximum privilege escalation. Ceph also runs as root with no capability restrictions.

**Recommendation:** Add `User=ceph` and appropriate capabilities to `mios-ceph.container`. For `mios-k3s.container`, assess whether a non-root user is feasible; if not, document the exception.

---

### F-15 — MEDIUM | Build Correctness | `automation/49-finalize.sh:29`

**Evidence:**
```bash
dnf5 clean all || true
```

**Defect:** Direct `dnf5` invocation bypasses the `$DNF_BIN` abstraction from `lib/common.sh`. On systems where `dnf5` is unavailable (only `dnf` present), this silently fails (`|| true`) and the cache is not cleaned.

**Recommendation:** Replace with `$DNF_BIN "${DNF_SETOPT[@]}" clean all`.

---

### F-16 — MEDIUM | Build Correctness | `automation/90-generate-sbom.sh:18`

**Evidence:**
```bash
dnf install -y syft || {
```

**Defect:** Direct `dnf install` invocation bypasses `$DNF_BIN` and omits `$DNF_SETOPT` (`install_weak_deps=False`). This may install unwanted weak dependencies and breaks on non-dnf5 environments.

**Recommendation:** Replace with `$DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" syft`.

---

### F-17 — MEDIUM | Reproducibility | `automation/90-generate-sbom.sh:25`

**Evidence:**
```bash
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
--file "${ARTIFACT_DIR}/mios-sbom-${VERSION}-${TIMESTAMP}.cyclonedx.json"
```

**Defect:** SBOM filename embeds wall-clock timestamp. Two builds of the same source tree produce different SBOM file paths. The timestamped file is baked into the image layer, making layers non-reproducible.

**Recommendation:** Use a fixed filename `mios-sbom-${VERSION}.cyclonedx.json` or derive the timestamp from `SOURCE_DATE_EPOCH` for deterministic builds.

---

### F-18 — MEDIUM | Bash Hygiene | Multiple files

**Evidence:**
```
/automation/common.sh       (diff vs lib/common.sh → IDENTICAL)
/automation/lib_common.sh   (diff vs lib/common.sh → IDENTICAL)
/automation/masking.sh      (present alongside lib/masking.sh)
/automation/lib_masking.sh  (present alongside lib/masking.sh)
/automation/packages.sh     (present alongside lib/packages.sh)
/automation/lib_packages.sh (present alongside lib/packages.sh)
```

**Defect:** Six library files exist in triplicate. Currently identical, they will diverge silently when one copy is edited. Any future fix to `lib/common.sh` not mirrored to `common.sh` and `lib_common.sh` will apply inconsistently.

**Recommendation:** Delete the legacy root-level copies. Update any scripts that source them to use `lib/common.sh`, `lib/masking.sh`, `lib/packages.sh`.

---

### F-19 — MEDIUM | Bash Hygiene | `automation/common.sh`, `automation/lib_common.sh`, `automation/masking.sh`, `automation/lib_masking.sh`, `automation/packages.sh`, `automation/lib_packages.sh`

**Evidence:** `grep -L 'set -euo pipefail' /automation/*.sh` returns all six library files listed above.

**Defect:** Library scripts missing `set -euo pipefail`. Harmless when sourced by a calling script that has the guard, but dangerous when run standalone.

**Recommendation:** Add `set -euo pipefail` to each library file header.

---

### F-20 — MEDIUM | Security Posture | `usr/share/pki/containers/`

**Evidence:**
```
$ ls /usr/share/pki/containers/
(empty — no output)
```
`/usr/lib/containers/policy.json` references:
```json
"keyPath": "/usr/share/pki/containers/mios-cosign.pub"
"keyPath": "/usr/share/pki/containers/ublue-os.pub"
"rekorPublicKeyPath": "/usr/share/pki/containers/rekor.pub"
```

**Defect:** The signing policy references keys in `/usr/share/pki/containers/` that are absent. `42-cosign-policy.sh` attempts to install them from `${SYSFILES}/usr/share/pki/containers/` but skips silently if the source path is empty. With a default-reject policy and missing keys, `bootc upgrade` will fail signature verification for all images including `ghcr.io/mios-dev/mios`.

**Recommendation:** Commit the actual public keys (`mios-cosign.pub`, `ublue-os.pub`, `ublue-cosign.pub`, `fulcio_v1.crt.pem`, `rekor.pub`) to the repository under `usr/share/pki/containers/`. Add a postcheck assertion that these files exist in the built image.

---

### F-21 — LOW | Documentation | `automation/42-cosign-policy.sh:8,17`

**Evidence:**
```bash
# Line 8: Note: we pin to v0.2.0 because v3 breaks rpm-ostree bundle format (OCI 1.1).
# Line 17: # 1. Install cosign binary (pinned to v2.x for rpm-ostree compatibility)
```

**Defect:** Lines 8 and 17 contradict each other — one says `v0.2.0`, the other says `v2.x`. The underlying URL is incorrect regardless (see F-02).

**Recommendation:** After fixing F-02, update comments to accurately reflect the pinned version and rationale.

---

### F-22 — LOW | Documentation | `image-versions.yml:13`

**Evidence:**
```yaml
ucore_hci_stable_nvidia_digest: sha256:3f4474648ab2835bdb8a29f1afe8805de96a32bc0.1.1345ecf485a395aa1d1d
```

**Defect:** Contains `.1.1` sequence — not valid hexadecimal. A valid SHA256 digest is exactly 64 lowercase hex characters. This digest cannot be used for image pinning.

**Recommendation:** Populate with the actual current digest of `ghcr.io/ublue-os/ucore-hci:stable-nvidia` and configure Renovate to auto-update both this file and the Containerfile ARG.

---

### F-23 — LOW | Documentation | `image-versions.yml:22`

**Evidence:**
```yaml
image_builder_cli_digest: sha256:0000000000000000000000000000000000000000000000000000000000000000
```

**Defect:** Zeroed digest — Renovate has not been configured or run for this entry.

**Recommendation:** Either remove this entry if `image-builder-cli` is not in active use, or configure Renovate and populate the digest.

---

### F-24 — LOW | Build Correctness | `Containerfile:43` + `usr/share/mios/PACKAGES.md:75`

**Evidence:**
```
Containerfile:43:     kernel-devel; \
PACKAGES.md:75: kernel-devel
```

**Defect:** `kernel-devel` is installed in the Containerfile's explicit `dnf install` block AND listed in PACKAGES.md `packages-kernel` (installed by `02-kernel.sh`). DNF handles duplicates gracefully but this creates maintenance confusion.

**Recommendation:** Remove `kernel-devel` from the Containerfile's explicit install block. Rely solely on PACKAGES.md `packages-kernel`.

---

### F-25 — LOW | Architectural Law | `automation/08-system-files-overlay.sh:56`

**Evidence:**
```bash
mkdir -p /var/home
```

**Defect:** `mkdir -p /var/home` creates a directory under `/var` at build time. ARCHITECTURE.md: "Build-time overlays into /var are architectural violations. All /var state must be declared via `tmpfiles.d`." The `tmpfiles.d` files do declare `d /var/home` entries, partially mitigating this.

**Recommendation:** Remove the `mkdir -p /var/home` from the overlay script. The `tmpfiles.d` declarations will create the directory on first boot. Add a comment if the mkdir is required for the tar overlay to succeed before tmpfiles processes.

---

### F-26 — INFO | Security Posture | `usr/lib/bootc/kargs.d/01-mios-hardening.toml`

**Evidence:**
```toml
# "init_on_alloc=1",
# "init_on_free=1",
# "page_alloc.shuffle=1",
```
`SECURITY.md` documents these as active parameters with override instructions.

**Defect:** Three documented-as-active memory hardening parameters are commented out. The kargs file provides CUDA/NVIDIA interference as rationale. SECURITY.md does not reflect this exception.

**Recommendation:** Update `SECURITY.md` to note these three parameters are intentionally disabled due to CUDA/NVIDIA interference, with a reference to the kargs file.

---

## Section §4.1 — Architectural Law Compliance

**Status:** 3 findings, 3 passes

- PASS **USR-OVER-ETC:** No `COPY ... /etc/` in Containerfile. Checked: `grep -rn "COPY.*\b/etc/" Containerfile automation/` — no violations.
- FAIL **NO-MKDIR-IN-VAR:** `automation/08-system-files-overlay.sh:56` — `mkdir -p /var/home` at build time (F-25).
- PASS **BOUND-IMAGES:** `08-system-files-overlay.sh:66-77` implements LBI logic. Note: production quadlets live in `/etc/containers/systemd/`; the LBI source path `/usr/share/containers/systemd/` is empty. This means bound-images pre-pull does not fire for deployed quadlets (design tension but not a strict law violation at build time).
- FAIL **BOOTC-CONTAINER-LINT:** `Containerfile:57-58` — lint runs after commit in a separate RUN layer (F-01).
- PASS **UNIFIED-AI-REDIRECTS:** No external `openai.com` or `anthropic.com` endpoints in MiOS system files. AI traffic routes through `http://localhost:8080/v1` (LocalAI). Grep hits are all in third-party Python packages (`/usr/local/lib/python3.12/dist-packages/vertexai/`).
- FAIL **UNPRIVILEGED-QUADLETS:** `mios-k3s.container:12` — `Privileged=true`, no `User=` (F-13, F-14). `mios-ceph.container` — no `User=` (F-14). Only `mios-ai.container` is compliant.

---

## Section §4.2 — Build Correctness

**Status:** 5 findings, 3 passes

- PASS **Phase ordering:** 48 scripts execute in numeric-then-alpha glob order. Critical dependencies respected (13 before 19, 02 before 52, etc.).
- FAIL **Skip list:** `99-postcheck.sh` missing from skip list — double invocation (F-09).
- FAIL **Double ostree commit:** `99-cleanup.sh:48` + `Containerfile:57` (F-10).
- FAIL **Direct dnf invocations:** `49-finalize.sh:29` and `90-generate-sbom.sh:18` bypass `$DNF_BIN` (F-15, F-16).
- PASS **Build-arg consumption:** `MIOS_USER` in `31-user.sh:22`; `MIOS_HOSTNAME` in `32-hostname.sh:18`; `MIOS_FLATPAKS` in `Containerfile:44-45`. All consumed.
- PASS **DNF weak deps:** `install_weak_deps=False` correctly written to dnf.conf by `01-repos.sh:13`. `$DNF_SETOPT` carries `--setopt=install_weak_deps=False` for all DNF invocations.
- FAIL **Duplicate package install:** `kernel-devel` in Containerfile and PACKAGES.md (F-24).

---

## Section §4.3 — Bash Hygiene

**Status:** 1 finding, 4 passes

- FAIL **set -euo pipefail missing:** Six library/helper files (F-19). All 48 numbered scripts have it.
- PASS **Arithmetic safety:** No `((VAR++))` patterns found. `build.sh` changelog confirms: "Safe arithmetic: VAR=$((VAR + 1)) not ((VAR++))".
- PASS **Hard-coded versions:** Only `42-cosign-policy.sh:20` has a hard-coded version (`v0.2.0`) — already captured as F-02. Aichat fallback versions are appropriately guarded.
- PASS **install_weakdeps footgun:** No deprecated dnf4 `install_weakdeps` form found. Correct `install_weak_deps=False` used consistently.
- PASS **set+e/RC=$?/set-e pattern:** `52-bake-kvmfr.sh` correctly implements the guard pattern around every external command call.

---

## Section §4.4 — Supply Chain Integrity

**Status:** 5 findings, 3 passes

- FAIL **Base image pinning:** Floating tag in Containerfile (F-04).
- FAIL **Quadlet image pinning:** `mios-ceph.container` uses `latest` (F-12). Others use version tags but no digests.
- PASS **K3s sha256 check:** `13-ceph-k3s.sh:56` — `sha256sum -c` verification before K3s binary installation. Correct pattern.
- FAIL **Cosign fallback URL:** `42-cosign-policy.sh:20` downloads an invalid cosign release URL (F-02).
- FAIL **Unverified downloads:** aichat (F-06), Bibata cursor (F-08), k3s-selinux at HEAD (F-07). Geist font also `git clone`'d without commit pinning (`10-gnome.sh:53`).
- FAIL **GPG verification:** Fedora 44 repos with `gpgcheck=0` (F-05).
- PASS **CI signing:** `mios-ci.yml` uses `sigstore/cosign-installer@v3` with `id-token: write` for keyless signing. Provenance and SBOM generation enabled. Signing gated on non-PR events.
- PASS **policy.json structure:** Default-reject with explicit allow lists for MiOS, ublue-os, Fedora, Red Hat. Well-structured. Key absence captured as F-20.

---

## Section §4.5 — Security Posture

**Status:** 2 findings, 8 passes

- PASS **Kernel kargs:** 14 kargs files, comprehensive hardening: `slab_nomerge`, `pti=on`, `vsyscall=none`, `lockdown=confidentiality` (overridden to `integrity` for NVIDIA MOK), `spectre_v2`, `spectre_bhi`, `spec_store_bypass_disable`, `l1tf`, `gather_data_sampling`, `tsx=off`, `slub_debug=FZ`, `page_poison=1`, `debugfs=off`, `oops=panic`, `iommu.strict=1`, `iommu=force`. RTX 50 VFIO workaround present.
- PASS **Sysctl hardening:** `99-mios-hardening.conf` covers kernel pointer restriction, dmesg restriction, ptrace scope (level 2), BPF hardening, TCP protections, filesystem protections.
- PASS **SELinux modules:** 21 custom policy modules in `37-selinux.sh`. Skip-not-fail pattern correct.
- PASS **fapolicyd:** `90-mios-deny.rules` deny-by-default for `/var/home/`, `/home/`, `/run/media/`, `/mnt/`.
- PASS **Firewall:** `33-firewall.sh:15` — `firewall-cmd --set-default-zone=drop`. Default-deny confirmed.
- PASS **Greenboot:** 5 required health checks + 4 wanted checks. Composefs verity check (`15-composefs-verity.sh`) is particularly strong.
- PASS **Composefs verity:** `usr/lib/ostree/prepare-root.conf` — `enabled = verity`. Strongest composefs mode.
- PASS **RTX 50 VFIO reset:** `13-rtx50-vfio-workaround.toml` — `vfio_pci.disable_idle_d3=1` present. Build validation also checks for this.
- FAIL **PKI keys absent:** `/usr/share/pki/containers/` empty — signing policy will fail at verification time (F-20).
- INFO **SECURITY.md discrepancy:** `init_on_alloc=1`, `init_on_free=1`, `page_alloc.shuffle=1` documented as active but commented out in kargs (F-26).

---

## Section §4.6 — Idempotency & Reproducibility

**Status:** 2 findings, 4 passes

- PASS **Multi-stage build:** `FROM scratch AS ctx` / `COPY --from=ctx /ctx /ctx` — correct build context isolation.
- PASS **Cache mounts:** `--mount=type=cache,dst=/var/cache/libdnf5,sharing=locked` and `/var/cache/dnf` on the main RUN.
- PASS **Cleanup:** `Containerfile:52-53`, `99-cleanup.sh`, and `build.sh:205-211` perform comprehensive cleanup.
- FAIL **SBOM timestamp:** Non-reproducible filename (F-17).
- PASS **Script idempotency (31-user, 33-firewall, 10-gnome, 46-greenboot):** All checked scripts use idempotency guards (`getent passwd`, `--if-not-exists`, `[[ -f ... ]]`, `ln -sf`). `46-greenboot.sh` safely uses `[[ -f "/usr/lib/systemd/system/${unit}" ]]` before enabling.
- FAIL **Build determinism:** `90-generate-sbom.sh:25` uses wall-clock `date` for SBOM filename. `49-finalize.sh` also embeds `date` in `/etc/mios/version` (minor, acceptable for metadata).

---

## Section §4.7 — Documentation Drift

**Status:** 1 finding, 4 passes

- PASS **PACKAGES.md categories vs scripts:** All categories invoked by scripts exist in PACKAGES.md. No orphaned calls found.
- PASS **Phase script inventory:** 48 numbered scripts present. ARCHITECTURE.md and ENGINEERING.md are high-level only — no script inventory to cross-reference.
- PASS **VERSION consistency:** `VERSION`=`0.2.0`, Containerfile label `v0.2.0`, `build.sh` header `v0.2.0`. Consistent.
- FAIL **GTK_THEME FG-5:** `usr/lib/environment.d/70-mios-theme.conf:2` sets `GTK_THEME=adw-gtk3-dark`. The Engineering Reference warns "Never set GTK_THEME=Adwaita:dark". The value `adw-gtk3-dark` IS the correct adw-gtk3 compatibility theme for GTK3 apps and is distinct from `Adwaita:dark`. `50-mios.conf` correctly documents NOT setting GTK_THEME for GTK4/libadwaita. This is technically correct but the two environment files could confuse future maintainers.
- PASS **Stale refs in source:** CloudWS/Kabuki94 references are in `MiOS-Engineering-Reference.md` as historical migration notes, not in active build scripts.

---

## Section §4.8 — Footgun Regression Checks

| Check | Status | Evidence |
|---|---|---|
| FG-1: `install_weakdeps` (dnf4) | PASS | Not used anywhere; correct `install_weak_deps` used |
| FG-2: F44 filesystem posttrans | PASS | `01-repos.sh:49` pre-upgrades `filesystem`, `systemd`, `glibc`, `dbus-broker` before distro-sync |
| FG-3: ucore-hci akmod guard | PASS | `36-akmod-guards.sh` installs ExecCondition drop-ins for 7 NVIDIA units with correct regex |
| FG-4: malcontent | PASS | `malcontent-control`, `malcontent-pam`, `malcontent-tools` in `packages-bloat`; `malcontent-libs` retained |
| FG-5: GTK_THEME | NOTE | `70-mios-theme.conf:2` sets `GTK_THEME=adw-gtk3-dark` (correct for GTK3; GTK4/libadwaita path correctly separated in `50-mios.conf`) |
| FG-6: bash arithmetic `++` | PASS | Not found in any numbered automation script |
| FG-7: BIB config format | PASS | No `config.json`/`config.toml` BIB references in Justfile or build scripts |
| FG-8: BIB --squash-all | PASS | Not present in any workflow or build script |
| FG-9: xdm_t context | PASS | `37-selinux.sh:85-88,116-118` — `xdm_t` used correctly in fapolicyd/GDM SELinux modules |
| FG-10: cosign version | CRITICAL | `42-cosign-policy.sh:20` — `v0.2.0` URL is not a valid cosign release (F-02) |
| FG-11: WSL2 nftables | PASS | `iptables-legacy` in `packages-security` with explanatory WSL2 rationale comment |
| FG-12: wsl --list | PASS | `mios-build-local.ps1` not found in repo |
| FG-13: RTX 50 VFIO reset | PASS | `13-rtx50-vfio-workaround.toml` — `vfio_pci.disable_idle_d3=1` confirmed present |
| FG-14: SELinux skip-not-fail | PASS | `37-selinux.sh:164-167` — failed modules increment counter and log SKIPPED; do not abort |
| FG-15: NVIDIA CT CVE | PASS | `99-postcheck.sh:75-76` — `die` if NCT < 1.18; enforces minimum version |

---

## §5.9 — Out-of-Scope Observations

1. **Home directory leak risk:** `Containerfile:7` — `COPY home/ /ctx/home/`. The `/home/` directory at the repo root contains the builder's user home (`corey_dl_taylor`). If this is the live filesystem root (not a dedicated repo checkout), personal home directory files may be included in the build context. Verify that the repo's `home/` subtree contains only MiOS skeleton content.

2. **Large artifact files in repo root:** `files1.zip`, `files.zip`, `FOUND-THE-FILES.tar`, `MiOS-Build-Scripts.md`, `MiOS-Build-Stack.tar.gz`, `llms-full.txt`, `llms.txt`, `MiOS-FULL-Build-Stack.md`, `MiOS-SBOM.csv` are in the repo root. These inflate `docker build` context transfer. Add to `.dockerignore`.

3. **`COSIGN_EXPERIMENTAL=1` in CI:** Used with `sigstore/cosign-installer@v3` which installs cosign v2.x. `COSIGN_EXPERIMENTAL` was deprecated in v2.x (replaced by `--yes`). Current builds likely still work but emit deprecation warnings.

4. **Duplicate script prefix numbers:** Prefixes `20`, `35`, `36`, `37`, `99` each have 2-4 sibling scripts. Bash glob expansion within a prefix is alphabetical, creating implicit ordering (e.g., `20-fapolicyd-trust.sh` before `20-services.sh`). Acceptable currently but makes phase ordering non-obvious.

5. **CI smoke test uses `podman` on GitHub Actions:** GitHub-hosted Ubuntu runners (`ubuntu-24.04`) do not ship Podman by default. The smoke test may fail for infrastructure reasons, obscuring real failures from the `|| echo WARN` behavior (though this is moot given F-11's recommendation to make it fatal).

6. **`99-cleanup.sh:48` ostree commit labeled "CRITICAL":** The comment says this commit "finalizes OSTree layer metadata" but it is superseded by the Containerfile's explicit commit. The label "CRITICAL" is misleading.

---

## §5.10 — Audit Methodology Notes

**Tools used:** bash, grep, find, sort, diff. shellcheck not installed; no static analysis possible.

**Files read fully:** `Containerfile`, `automation/build.sh`, `automation/lib/common.sh`, `automation/lib/packages.sh`, `automation/01-repos.sh`, `automation/08-system-files-overlay.sh`, `automation/10-gnome.sh`, `automation/13-ceph-k3s.sh`, `automation/19-k3s-selinux.sh`, `automation/31-user.sh`, `automation/33-firewall.sh`, `automation/36-akmod-guards.sh`, `automation/37-selinux.sh`, `automation/42-cosign-policy.sh`, `automation/46-greenboot.sh`, `automation/49-finalize.sh`, `automation/52-bake-kvmfr.sh`, `automation/99-cleanup.sh`, `automation/99-postcheck.sh`, `INDEX.md`, `ARCHITECTURE.md`, `ENGINEERING.md`, `SECURITY.md`, `image-versions.yml`, `usr/share/mios/PACKAGES.md`, `.github/workflows/mios-ci.yml`, all three quadlet container files, all 14 kargs.d files, `usr/lib/sysctl.d/99-mios-hardening.conf`, `usr/lib/containers/policy.json`, `usr/lib/ostree/prepare-root.conf`, `usr/lib/fapolicyd/rules.d/90-mios-deny.rules`.

**Checks run:** All 15 footgun regression checks executed. All 8 audit dimensions evaluated. All specified grep/find/diff commands run.

**Limitations:** Static analysis only; no build execution. No runtime verification of SELinux compilation, DNF resolution, container networking, or first-boot behavior.

---

## Notable Strengths

1. **`automation/52-bake-kvmfr.sh`** — Exemplary `set +e`/`RC=$?`/`set -e` guard pattern around every external command. Detailed, user-actionable warning messages. Correct graceful degradation to IVSHMEM-only mode.

2. **`automation/37-selinux.sh`** — 21 custom SELinux policy modules with correct skip-not-fail pattern. In-tree policy compilation. Covers GDM, fapolicyd, accountsd, homed, k3s, kvmfr, coreos boot — comprehensive real-world coverage.

3. **`usr/lib/ostree/prepare-root.conf`** — `enabled = verity` composefs mode — the strongest available integrity enforcement. Most comparable images use `enabled = yes` (without verity signatures).

4. **Greenboot integration** (`46-greenboot.sh`, `usr/lib/greenboot/check/required.d/`) — 5 required health checks including a dedicated composefs verity check (`15-composefs-verity.sh`). Above-average greenboot coverage.

5. **`automation/13-ceph-k3s.sh:56`** — `sha256sum -c` verification of K3s binary before installation. One of the few external downloads with proper integrity verification in the build.

6. **`automation/build.sh`** — The `set +e`/`SCRIPT_EXIT`/`set -e` wrapper with aggregated failure tracking (not abort-on-first-failure) produces a comprehensive failure summary and correctly exits non-zero on any script failure.

7. **`automation/lib/packages.sh`** — Clean three-tier API: `install_packages` (soft), `install_packages_strict` (hard), `install_packages_optional` (section-aware). Consistent `$DNF_BIN`/`$DNF_SETOPT` usage across all three.
