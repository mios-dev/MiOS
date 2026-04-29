<!-- 🌐 MiOS Artifact | Proprietor: MiOS Project | https://github.com/mios-project/mios -->
# 🌐 MiOS
```json:knowledge
{
  "summary": "> **Proprietor:** MiOS Project",
  "logic_type": "documentation",
  "tags": [
    "MiOS",
    "knowledge"
  ],
  "relations": {
    "depends_on": [
      ".env.mios"
    ],
    "impacts": []
  }
}
```
> **Proprietor:** MiOS Project
> **Infrastructure:** Self-Building Infrastructure (Personal Property)
> **License:** Licensed as personal property to MiOS Project
> **Source Reference:** MiOS-Core-v0.1.1
---

# MiOS v0.1.1 release — complete implementation plan

**Bottom line:** The CI break is a `/usr/local` symlink collision inherited from the Fedora-CoreOS / ucore lineage; fix it by targeting `/var/usrlocal` directly (that's what the symlink points to) and eliminate the `cp -a` trailing-slash gotcha entirely. Of the three defensive audit fixes, the cleanest shape for v0.1.1 is to ship a full replacement `automation/05-enable-external-repos.sh` (no RPM Fusion, `dnf` not `dnf5`, array-form `DNF_SETOPT`) and turn `push-to-github.ps1` into a 5-line deprecation shim that exec's `push-v0.1.1.ps1`. DNF_SETOPT becomes a bash array sourced from a new `automation/lib/common.sh`, applied to every `dnf install/remove/swap/group install` call site. The three highest-ROI outstanding items — cosign keyless (Item A), bootc-image-builder artifacts (Item B), and akmod ExecCondition guards (Item C) — are all deliverable in this release with exact file contents, no further research required. One material research surprise: **ublue-os bluefin/bazzite use keyed cosign signing, not keyless**, so the keyless pattern is modeled on travier/cosign-test and the Sigstore CI quickstart, which are the authoritative keyless references for containers/image-based verification.

Everything below is copy-pasteable. File paths are given in both repo form (`automation/foo.sh`) and flatpack form (`scripts__foo.sh`) so you can generate the flatpack mechanically.

---

## 1. The `/usr/local` CI failure, root cause, and chosen fix

**Hypothesis confirmed.** On ucore-hci / Fedora-CoreOS-lineage bootc images, `/usr/local` is a symbolic link to `/var/usrlocal` (the long-standing OSTree convention: `/usr` is immutable, `/var` is runtime-mutable, so a writable `/usr/local` must be a symlink into `/var`). bootc upstream has since diverged and recommends regular-directory `/usr/local` for **base** images, but derived images in the ublue/ucore stack still ship the symlink. `cp -a /ctx/usr/local/. /usr/local/` fails with `cannot create directory '/usr/local/': File exists` because the trailing slash forces `cp` to treat the target as a directory name to create — which collides with the existing symlink target.

**Evaluation of fix patterns:**

| Pattern | Verdict |
|---|---|
| `tar --dereference` / `tar -h` | Works for reading but doesn't change the fact that the target is a symlink; source side, not relevant |
| **Target `/var/usrlocal` directly** | **Chosen.** Matches the semantic the symlink is expressing, single-line fix, idempotent, works whether `/usr/local` is a symlink (ucore/ublue lineage) or a real directory (pure Fedora bootc base) because we first create `/var/usrlocal` |
| Remove symlink, cp, restore | Fragile, violates base-image invariants |
| `cp -aL --no-target-directory` | Brittle and hard to reason about under `set -e` |
| `rsync -a` | Adds a build-time dep (rsync not guaranteed on ucore-hci) |
| `/usr/share/factory/var/usrlocal` with tmpfiles.d | bootc-correct for runtime population, but overkill for build-time overlay; retain as a follow-up if `bootc container lint` flags `/var` writes |

**Downstream risk assessment:** writing to `/var` during container build has Docker-`VOLUME`-like semantics — it is copied only at **install** time, not on `bootc upgrade`. For `/var/usrlocal` this is acceptable because MiOS's overlay only seeds developer conveniences (wrapper scripts, local binaries), and users who need those files to evolve across upgrades can move them under `/usr/local/bin` only if `/usr/local` is later re-made a real directory. Flagged as a v2.2 consideration; not a v0.1.1 blocker.

**Recommended snippet** (replaces the failing RUN block in the Containerfile):

```dockerfile
RUN set -euo pipefail; \
    # Stage 1: overlay everything EXCEPT /usr/local (which is a symlink to
    # /var/usrlocal on ucore/bootc images; cp -a into it trips over the link).
    if [ -d /ctx/system_files ]; then \
        tar -C /ctx/system_files -cf - --exclude='./usr/local' . \
          | tar -C / -xf -; \
    fi; \
    # Stage 2: overlay /usr/local content by writing through the symlink into
    # /var/usrlocal. Create the target directory first in case the base image
    # ships the symlink without the dir populated.
    if [ -d /ctx/usr/local ]; then \
        mkdir -p /var/usrlocal; \
        tar -C /ctx/usr/local -cf - . \
          | tar -C /var/usrlocal -xf -; \
    fi; \
    echo "[overlay] system_files applied (2-stage, /var/usrlocal aware)"
```

Rationale for `tar | tar` rather than `cp -a` even for stage 2: identical semantics for permissions/ownership/timestamps, no trailing-slash ambiguity, and resilient to future additions of extended attributes (tar `--xattrs --acls` can be added without changing shape).

---

## 2. DNF_SETOPT activation across all numbered scripts

**Decision: bash array form.** String word-splitting (`dnf $DNF_SETOPT install …`) is fragile under `set -u` and ShellCheck SC2086. Inline (`dnf --setopt=install_weak_deps=False …`) is ublue-os's literal style but DRY-violating. The array pattern is strictly safer, adds future flags in one place, and is what every mature bash codebase converges on.

**New file `automation/lib/common.sh`** (create if absent; merge additively if present):

```bash
#!/usr/bin/env bash
# automation/lib/common.sh — shared helpers for MiOS build scripts.
# Safe to source multiple times.

# --- Logging ------------------------------------------------------------
log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# --- dnf flags ----------------------------------------------------------
# Defense-in-depth: /etc/dnf/dnf.conf also carries install_weak_deps=False,
# but passing it on every invocation guarantees behaviour even if a script
# or transaction overrides the global default (see dnf5 issue #2241).
# Array form so elements are one-argv-each under `set -u` and future flags
# can be added without re-escaping.
DNF_SETOPT=(--setopt=install_weak_deps=False)
export DNF_SETOPT_STR="${DNF_SETOPT[*]}"   # for debug/visibility only
```

**Modification to `automation/build.sh`:** keep the existing export so backward compatibility is preserved; add `source "$(dirname "$0")/lib/common.sh"` at the top after `set -euo pipefail`, and remove any line that re-assigns `DNF_SETOPT` as a string.

**Conversion pattern** for every numbered script that calls dnf (sourced from common.sh at the top, then):

```bash
dnf "${DNF_SETOPT[@]}" -y install foo bar
dnf "${DNF_SETOPT[@]}" -y remove  firefox
dnf "${DNF_SETOPT[@]}" -y swap    mesa-va-drivers mesa-va-drivers-freeworld
dnf "${DNF_SETOPT[@]}" -y group install @virtualization
```

**Scripts requiring edit** (exhaustive list for a typical ublue-pattern build):

| Script | dnf calls to adapt |
|---|---|
| `automation/01-repos.sh` | RPM Fusion free/nonfree release RPM install URLs |
| `automation/05-enable-external-repos.sh` | full replacement — see §3 |
| `automation/10-core-packages.sh` (or wherever PACKAGES.md is consumed) | main install loop |
| `automation/11-nvidia.sh` (if present) | akmod-nvidia, nvidia-driver-cuda |
| `automation/12-container-tools.sh` (if present) | docker-ce family |
| `automation/13-dev-tools.sh` (if present) | code, gh, tailscale, 1password |
| `automation/14-virtualization.sh` (if present) | libvirt, qemu-kvm |
| `automation/15-desktop-apps.sh` (if present) | Legacy-Cloud-chrome, fonts |
| `automation/16-swaps.sh` (if present) | ffmpeg/mesa-freeworld swaps |
| `automation/17-cleanup.sh` (or equivalent) | dnf remove of firefox/gnome-software-rpm-ostree/podman-docker |
| `automation/lib/packages.sh` | the dnf-call wrapper around PACKAGES.md entries |

**Auditing command** to verify 100% coverage after the edit (run in CI as a shellcheck-adjacent gate):

```bash
! grep -rnE '^\s*dnf (install|remove|swap|group)' automation/ \
  | grep -v '"${DNF_SETOPT\[@\]}"'
```

(Exits 0 iff every dnf-mutating call includes the array expansion.)

---

## 3. Full replacement `automation/05-enable-external-repos.sh`

Design: no RPM Fusion (01 handles it), `dnf` not `dnf5`, `${DNF_SETOPT[@]}` on every mutating call, idempotent per-repo guard, fails fast. Includes Terra, VS Code, 1Password, Tailscale, Docker CE, Cloud Chrome — the six repos defensible for a developer workstation bootc. COPRs and aggressive privacy browsers (Brave, Mullvad, etc.) are deferred to Flatpak per ublue best-practice.

```bash
#!/usr/bin/env bash
# automation/05-enable-external-repos.sh
# Enable external DNF repositories for MiOS (Fedora 44).
# Idempotent; fails fast; uses $DNF_SETOPT array from automation/lib/common.sh.
# RPM Fusion is intentionally NOT handled here — see 01-repos.sh.
#
# v0.1.1 CHANGES:
#   - removed redundant/broken RPM Fusion install block (was using
#     `rpm -E %fedora` which yielded 41/43 from the base image and
#     overrode 01-repos.sh's explicit F44 pin).
#   - replaced dnf5 with dnf throughout (consistency with 01-repos.sh
#     and lib/packages.sh; on F44 `dnf` is dnf5 via symlink).
#   - adopted ${DNF_SETOPT[@]} for every mutating invocation.

set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

REPO_DIR=/etc/yum.repos.d

#######################################################################
# 1. Terra (Fyralabs) — patched WINE/Mesa/misc packages missing from
#    Fedora and RPM Fusion. Use the subatomic .repo dropin (safe for
#    bootc builds; no scriptlets). Leave enabled=1 from upstream file.
#######################################################################
if [ ! -f "${REPO_DIR}/terra.repo" ]; then
    log "enabling Terra repo (fyralabs)"
    curl -fsSL \
        https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo \
        -o "${REPO_DIR}/terra.repo"
else
    log "Terra repo already present — skipping"
fi

#######################################################################
# 2. Visual Studio Code (Microsoft)
#######################################################################
if [ ! -f "${REPO_DIR}/vscode.repo" ]; then
    log "enabling VS Code repo (Microsoft)"
    rpm --import https://packages.microsoft.com/keys/microsoft.asc
    cat > "${REPO_DIR}/vscode.repo" <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
else
    log "VS Code repo already present — skipping"
fi

#######################################################################
# 3. 1Password
#######################################################################
if [ ! -f "${REPO_DIR}/1password.repo" ]; then
    log "enabling 1Password repo"
    rpm --import https://downloads.1password.com/linux/keys/1password.asc
    cat > "${REPO_DIR}/1password.repo" <<'EOF'
[1password]
name=1Password Stable Channel
baseurl=https://downloads.1password.com/linux/rpm/stable/$basearch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://downloads.1password.com/linux/keys/1password.asc
EOF
else
    log "1Password repo already present — skipping"
fi

#######################################################################
# 4. Tailscale
#######################################################################
if [ ! -f "${REPO_DIR}/tailscale.repo" ]; then
    log "enabling Tailscale repo"
    dnf "${DNF_SETOPT[@]}" -y config-manager addrepo \
        --overwrite \
        --from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo
else
    log "Tailscale repo already present — skipping"
fi

#######################################################################
# 5. Docker CE — required when podman-docker is removed; dev workflow
#    uses real Docker. Keep repo enabled=1; tight package pins live in
#    the install script, not here.
#######################################################################
if [ ! -f "${REPO_DIR}/docker-ce.repo" ]; then
    log "enabling Docker CE repo"
    dnf "${DNF_SETOPT[@]}" -y config-manager addrepo \
        --overwrite \
        --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
else
    log "Docker CE repo already present — skipping"
fi

#######################################################################
# 6. Cloud Chrome
#######################################################################
if [ ! -f "${REPO_DIR}/Legacy-Cloud-chrome.repo" ]; then
    log "enabling Cloud Chrome repo"
    rpm --import https://dl.Legacy-Cloud.com/linux/linux_signing_key.pub
    cat > "${REPO_DIR}/Legacy-Cloud-chrome.repo" <<'EOF'
[Legacy-Cloud-chrome]
name=Legacy-Cloud-chrome
baseurl=https://dl.Legacy-Cloud.com/linux/chrome/rpm/stable/$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl.Legacy-Cloud.com/linux/linux_signing_key.pub
EOF
else
    log "Cloud Chrome repo already present — skipping"
fi

log "external repos enabled; refreshing metadata"
dnf "${DNF_SETOPT[@]}" -y makecache

log "05-enable-external-repos.sh complete"
```

---

## 4. `push-to-github.ps1` — deprecation shim, not a patch

**Decision: replace with a shim.** Patching fixes the bug but leaves two scripts-of-record with drifting behaviour; hard-deleting breaks muscle memory and doc references. The 5-line shim preserves the filename and filepath references while routing all execution through the v0.1.1/v0.1.1 script that already uses `git commit -F $msgFile`. Plan is to remove the shim in v0.1.1 (noted in CHANGELOG).

**Full replacement `push-to-github.ps1`:**

```powershell
# push-to-github.ps1 — DEPRECATED as of v0.1.1; will be removed in v0.1.1.
# Forwards to push-v0.1.1.ps1 (which uses `git commit -F $msgFile` and
# correctly handles multi-word commit messages; the old body here had
# `git commit -m $msg` which unquote-split on spaces).
Write-Warning "push-to-github.ps1 is deprecated as of v0.1.1."
Write-Warning "Forwarding to push-v0.1.1.ps1 — please update your references."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $scriptDir 'push-v0.1.1.ps1') @args
exit $LASTEXITCODE
```

---

## 5. Outstanding Item A — cosign keyless end-to-end

**Reality check:** ublue-os bluefin/bazzite actually use **keyed** signing with a `COSIGN_PRIVATE_KEY` secret and a `cosign.pub` file checked into the repo — not keyless. The keyless reference implementation most relevant to a Fedora-bootc + containers/image stack is **travier/cosign-test** (Tim Siosm at Red Hat); pattern tracks the Sigstore CI quickstart. We adopt that.

### 5a. Full `.github/workflows/build-test.yml`

```yaml
name: build-test
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

env:
  IMAGE_REGISTRY: ghcr.io
  IMAGE_NAME: mios-project/mios
  IMAGE_BASE: {{MIOS_BASE_IMAGE}}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions:
  contents: read
  packages: write
  id-token: write   # required for Fulcio keyless OIDC exchange

jobs:
  build:
    name: build-sign-push
    runs-on: ubuntu-24.04
    steps:
      - name: Free runner disk
        run: |
          sudo rm -rf /opt/hostedtoolcache /usr/share/dotnet \
                      /usr/local/lib/android /opt/ghc
          df -h

      - name: Checkout
        uses: actions/checkout@v5
        with:
          fetch-depth: 1

      - name: Install cosign
        uses: sigstore/cosign-installer@v0.1.1

      - name: Log in to GHCR
        uses: redhat-actions/podman-login@v1
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build container image with buildah
        id: build
        uses: redhat-actions/buildah-build@v2
        with:
          image: ${{ env.IMAGE_NAME }}
          tags: latest ${{ github.sha }}
          containerfiles: ./Containerfile
          layers: false
          oci: true
          extra-args: |
            --build-arg=BASE_IMAGE=${{ env.IMAGE_BASE }}

      - name: bootc container lint
        run: |
          sudo podman run --rm --entrypoint /usr/bin/bootc \
            "${{ steps.build.outputs.image-with-tag }}" \
            container lint --fatal-warnings

      - name: Push image (capture digest)
        id: push
        run: |
          set -euo pipefail
          IMG="${IMAGE_REGISTRY}/${IMAGE_NAME}"
          buildah push --digestfile=digest.txt \
            "${{ steps.build.outputs.image-with-tag }}" \
            "docker://${IMG}:latest"
          buildah push \
            "${{ steps.build.outputs.image-with-tag }}" \
            "docker://${IMG}:${GITHUB_SHA}"
          DIGEST="$(cat digest.txt)"
          echo "digest=${DIGEST}" >> "$GITHUB_OUTPUT"
          echo "image=${IMG}"     >> "$GITHUB_OUTPUT"
          echo "Pushed ${IMG}@${DIGEST}"

      - name: Sign image with cosign (keyless, Fulcio OIDC)
        if: github.event_name != 'pull_request'
        env:
          DIGEST: ${{ steps.push.outputs.digest }}
          IMAGE:  ${{ steps.push.outputs.image }}
        run: cosign sign --yes "${IMAGE}@${DIGEST}"

      - name: Verify signature (keyless)
        if: github.event_name != 'pull_request'
        env:
          DIGEST: ${{ steps.push.outputs.digest }}
          IMAGE:  ${{ steps.push.outputs.image }}
        run: |
          cosign verify \
            --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
            --certificate-identity-regexp="^https://github\.com/${GITHUB_REPOSITORY}/\.github/workflows/.+@refs/heads/main$" \
            "${IMAGE}@${DIGEST}"
```

### 5b. `/etc/containers/policy.json` (shipped in-image via ``)

```json
{
    "default": [
        { "type": "reject" }
    ],
    "transports": {
        "docker": {
            "ghcr.io/mios-project/mios": [
                {
                    "type": "sigstoreSigned",
                    "fulcio": {
                        "caPath": "/etc/pki/containers/fulcio_v1.crt.pem",
                        "oidcIssuer": "https://token.actions.githubusercontent.com",
                        "subjectEmail": "https://github.com/mios-project/mios/.github/workflows/build-test.yml@refs/heads/main"
                    },
                    "rekorPublicKeyPath": "/etc/pki/containers/rekor.pub",
                    "signedIdentity": { "type": "matchRepository" }
                }
            ],
            "ghcr.io/ublue-os": [
                {
                    "type": "sigstoreSigned",
                    "keyPath": "/etc/pki/containers/ublue-os.pub",
                    "signedIdentity": { "type": "matchRepository" }
                }
            ],
            "registry.access.redhat.com": [
                { "type": "signedBy", "keyType": "GPGKeys",
                  "keyPath": "/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release" }
            ],
            "registry.redhat.io": [
                { "type": "signedBy", "keyType": "GPGKeys",
                  "keyPath": "/etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release" }
            ]
        },
        "docker-daemon": {
            "": [ { "type": "insecureAcceptAnything" } ]
        }
    }
}
```

### 5c. `/etc/containers/registries.d/ghcr.io-kabuki94.yaml`

```yaml
docker:
  ghcr.io/kabuki94:
    use-sigstore-attachments: true
```

Without this entry, `containers/image` does not look for cosign `.sig` attachments and verification silently fails even though `cosign verify` on the runner succeeds. This is a known footgun (rpm-ostree #4272).

### 5d. `automation/37-cosign-policy.sh`

```bash
#!/usr/bin/env bash
# automation/37-cosign-policy.sh
# Install cosign keyless verification policy + sigstore trust roots.
# Runs inside the Containerfile build, after 36-akmod-guards.sh.
#
# Prereq: the Containerfile must COPY these files into /ctx before this
# script runs:
#   etc/containers/policy.json
#   etc/containers/registries.d/ghcr.io-kabuki94.yaml
#   sigstore/fulcio_v1.crt.pem   (from sigstore/root-signing)
#   sigstore/rekor.pub           (from sigstore/root-signing)
#   sigstore/ublue-os.pub        (from ublue-os/main cosign.pub)

set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "37-cosign-policy: installing sigstore trust roots + policy.json"

install -d -m 0755 /etc/pki/containers
install -m 0644 /ctx/sigstore/fulcio_v1.crt.pem \
    /etc/pki/containers/fulcio_v1.crt.pem
install -m 0644 /ctx/sigstore/rekor.pub \
    /etc/pki/containers/rekor.pub
install -m 0644 /ctx/sigstore/ublue-os.pub \
    /etc/pki/containers/ublue-os.pub

install -d -m 0755 /etc/containers
install -m 0644 /ctx/etc/containers/policy.json \
    /etc/containers/policy.json

install -d -m 0755 /etc/containers/registries.d
install -m 0644 /ctx/etc/containers/registries.d/ghcr.io-kabuki94.yaml \
    /etc/containers/registries.d/ghcr.io-kabuki94.yaml

if command -v restorecon >/dev/null 2>&1; then
    restorecon -RF /etc/pki/containers \
                   /etc/containers/policy.json \
                   /etc/containers/registries.d || true
fi

if command -v jq >/dev/null 2>&1; then
    jq -e . /etc/containers/policy.json >/dev/null \
        || die "policy.json failed jq parse"
fi

log "37-cosign-policy: done"
```

**Cosign gotchas to note in CHANGELOG:**
- `id-token: write` permission is mandatory; missing it silently breaks keyless.
- `sigstore/cosign-installer@v0.1.1` is required for cosign v3+; the v3.x installer cannot install cosign v3.
- `COSIGN_EXPERIMENTAL` is obsolete since cosign 2.0 — do not set it.
- `bootc upgrade` does not yet expose `--enforce-container-sigpolicy` (bootc-dev/bootc#528); we rely on `default: reject` in policy.json so any un-rulified registry is refused.
- PRs from forks cannot sign (no `id-token` write) — `if: github.event_name != 'pull_request'` gates the sign/verify steps.

---

## 6. Outstanding Item B — bootc-image-builder artifacts

### 6a. `bib-configs/qcow2.toml`

```toml
# bib-configs/qcow2.toml
# Target: local libvirt/QEMU smoke-test of ghcr.io/mios-project/mios:latest

[[customizations.user]]
name     = "mios"
password = "$6$REPLACEME_WITH_SHA512_HASH$REPLACEME"
key      = "ssh-ed25519 AAAA_REPLACE_WITH_REAL_PUBKEY mios@operator"
groups   = ["wheel"]

[customizations.kernel]
append = "nvidia-drm.modeset=1 rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nvidia_drm.fbdev=1"

[[customizations.filesystem]]
mountpoint = "/"
minsize    = "150 GiB"

[[customizations.filesystem]]
mountpoint = "/var/home"
minsize    = "20 GiB"
```

### 6b. `bib-configs/vhdx.toml`

```toml
# bib-configs/vhdx.toml
# Target: Hyper-V on Windows host ("MiOS-2" bare metal + Win11 + RTX 4090)
# BIB --type vhd emits VPC/.vhd; CI post-converts to .vhdx via qemu-img.

[[customizations.user]]
name     = "mios"
password = "$6$REPLACEME_WITH_SHA512_HASH$REPLACEME"
key      = "ssh-ed25519 AAAA_REPLACE_WITH_REAL_PUBKEY mios@operator"
groups   = ["wheel"]

[customizations.kernel]
append = "nvidia-drm.modeset=1 rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nvidia_drm.fbdev=1"

[[customizations.filesystem]]
mountpoint = "/"
minsize    = "150 GiB"

[[customizations.filesystem]]
mountpoint = "/var/home"
minsize    = "20 GiB"
```

### 6c. `bib-configs/iso.toml`

```toml
# bib-configs/iso.toml
# Target: Anaconda unattended installer ISO for bare-metal install onto MiOS-1.
# NOTE: BIB #528 — [customizations.user] is ignored when kickstart is present.
#       User is defined IN the kickstart below.
# NOTE: source container image MUST include dracut-live + squashfs-tools,
#       or this build leg will fail. Add them in the Containerfile before release.

[customizations.kernel]
append = "nvidia-drm.modeset=1 rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nvidia_drm.fbdev=1"

[[customizations.filesystem]]
mountpoint = "/"
minsize    = "150 GiB"

[customizations.installer.modules]
disable = ["org.fedoraproject.Anaconda.Modules.Users"]

[customizations.installer.kickstart]
contents = """
text --non-interactive
lang en_US.UTF-8
keyboard us
timezone --utc UTC

network --bootproto=dhcp --device=link --activate --onboot=on

zerombr
clearpart --all --initlabel --disklabel=gpt
reqpart --add-boot
part / --grow --fstype xfs

user --name=mios --groups=wheel --iscrypted --password=$6$REPLACEME_WITH_SHA512_HASH$REPLACEME
sshkey --username=mios "ssh-ed25519 AAAA_REPLACE_WITH_REAL_PUBKEY mios@operator"

reboot --eject
"""
```

### 6d. `.github/workflows/build-artifacts.yml`

```yaml
# .github/workflows/build-artifacts.yml
# Matrix build of QCOW2 / VHDX / ISO via bootc-image-builder.
# EXPENSIVE (20-40 min per leg on ubuntu-24.04) — triggers: dispatch + weekly + post-build success.

name: build-artifacts

on:
  workflow_dispatch:
    inputs:
      image-tag:
        description: "Tag of ghcr.io/mios-project/mios to convert"
        required: false
        default: "latest"
  schedule:
    - cron: "0 5 * * 0"
  workflow_run:
    workflows: ["build-test"]
    types: [completed]
    branches: [main]

permissions:
  contents: read
  packages: read

env:
  IMAGE: ghcr.io/mios-project/mios
  BIB_IMAGE: quay.io/centos-bootc/bootc-image-builder:latest
  ROOTFS: ext4

jobs:
  build-artifact:
    if: ${{ github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-24.04
    timeout-minutes: 90
    strategy:
      fail-fast: false
      matrix:
        include:
          - artifact: qcow2
            bib-type: qcow2
            config:   bib-configs/qcow2.toml
            out-subdir: qcow2
            out-file:   disk.qcow2
          - artifact: vhdx
            bib-type: vhd
            config:   bib-configs/vhdx.toml
            out-subdir: vpc
            out-file:   disk.vhd
          - artifact: iso
            bib-type: anaconda-iso
            config:   bib-configs/iso.toml
            out-subdir: bootiso
            out-file:   install.iso

    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Free runner disk space (~40 GB)
        uses: jlumbroso/free-disk-space@main
        with:
          tool-cache: true
          android: true
          dotnet: true
          haskell: true
          large-packages: true
          swap-storage: true

      - name: Install qemu-utils (for VHDX post-convert)
        if: matrix.artifact == 'vhdx'
        run: sudo apt-get update && sudo apt-get install -y qemu-utils

      - name: Resolve image ref
        id: tag
        run: |
          TAG="${{ github.event.inputs.image-tag || 'latest' }}"
          echo "IMAGE_REF=${{ env.IMAGE }}:${TAG}" >> "$GITHUB_OUTPUT"

      - name: Log in to GHCR
        uses: redhat-actions/podman-login@v1
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Pull bootc image into local storage
        run: sudo podman pull "${{ steps.tag.outputs.IMAGE_REF }}"

      - name: Build with bootc-image-builder
        run: |
          mkdir -p output
          sudo podman run \
            --rm \
            --privileged \
            --pull=newer \
            --security-opt label=type:unconfined_t \
            -v "${{ github.workspace }}/${{ matrix.config }}:/config.toml:ro" \
            -v "${{ github.workspace }}/output:/output" \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            "${{ env.BIB_IMAGE }}" \
            --type "${{ matrix.bib-type }}" \
            --rootfs "${{ env.ROOTFS }}" \
            --use-librepo=True \
            --chown "$(id -u):$(id -g)" \
            "${{ steps.tag.outputs.IMAGE_REF }}"

      - name: Convert VHD -> VHDX (Hyper-V native)
        if: matrix.artifact == 'vhdx'
        run: |
          qemu-img convert -p -f vpc -O vhdx -o subformat=dynamic \
            "output/vpc/disk.vhd" "output/mios.vhdx"
          ls -lh output/mios.vhdx

      - name: Compute artifact path
        id: path
        run: |
          if [ "${{ matrix.artifact }}" = "vhdx" ]; then
            echo "ARTIFACT_PATH=output/mios.vhdx" >> "$GITHUB_OUTPUT"
          else
            echo "ARTIFACT_PATH=output/${{ matrix.out-subdir }}/${{ matrix.out-file }}" >> "$GITHUB_OUTPUT"
          fi

      - name: Checksum
        run: |
          cd "$(dirname ${{ steps.path.outputs.ARTIFACT_PATH }})"
          sha256sum "$(basename ${{ steps.path.outputs.ARTIFACT_PATH }})" \
            > "$(basename ${{ steps.path.outputs.ARTIFACT_PATH }}).sha256"

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: mios-${{ matrix.artifact }}
          path: |
            ${{ steps.path.outputs.ARTIFACT_PATH }}
            ${{ steps.path.outputs.ARTIFACT_PATH }}.sha256
          if-no-files-found: error
          retention-days: 14
          compression-level: 0
```

**BIB gotchas:** `--rootfs` is mandatory for Fedora-derived images (not CentOS); `--local` is obsolete — just bind-mount `/var/lib/containers/storage`; BIB `--type vhd` emits VPC `.vhd`, not native `.vhdx` (hence the `qemu-img convert` step); ISO builds require `dracut-live` + `squashfs-tools` in the source container; ubuntu-24.04 runners need the `free-disk-space` action to fit a 150 GiB sparse image.

---

## 7. Outstanding Item C — akmod ExecCondition guards

**Services to guard** (nvidia-cdi-refresh already done in v0.1.1, nvidia-fallback intentionally excluded — its existing `After=akmods.service` + negative `ConditionPathExists` is the anti-guard):

- `nvidia-persistenced.service`
- `nvidia-powerd.service`
- `nvidia-suspend.service`
- `nvidia-resume.service`
- `nvidia-hibernate.service`
- `nvidia-suspend-then-hibernate.service`

**kvmfr is excluded** from drop-in scope — Looking Glass ships no system-level systemd service; kvmfr is loaded via `/etc/modules-load.d/kvmfr.conf`. If a future MiOS release adds a boot-time modprobe wrapper unit, guard it with the kvmfr-specific regex noted in §7b.

### 7a. ExecCondition regex: widen beyond upstream #1395

The `^kernel/drivers/` anchor from NVIDIA issue #1395 misses akmod-built modules, which install under `/lib/modules/$(uname -r)/extra/nvidia/`. For RPM-Fusion-akmod lineage (which ucore-hci:stable-nvidia uses), we adopt a widened regex that matches both layouts and handles `.ko.xz`/`.ko.zst` compression:

```
grep -Eq '(^|/)nvidia\.ko(\.[xz]z|\.zst)?:' /lib/modules/$(uname -r)/modules.dep
```

Recommend backporting the same widening to v0.1.1's `nvidia-cdi-refresh` drop-in in the same v0.1.1 release for consistency (one extra file in the flatpack: `/usr/lib/systemd/system/nvidia-cdi-refresh.service.d/10-mios-akmod-guard.conf`).

### 7b. Drop-in content (identical across the 6 services + cdi-refresh backport)

`/usr/lib/systemd/system/<svc>.service.d/10-mios-akmod-guard.conf`:

```ini
# MiOS v0.1.1 akmod-guard
# Skip unit if akmods has not yet registered the nvidia kernel module
# for the currently running kernel. Pattern tolerates:
#   - kernel/drivers/... paths (negativo17 packaging)
#   - extra/nvidia/...   paths (RPM Fusion akmod packaging)
#   - .ko, .ko.xz, .ko.zst compressed variants
# ExecCondition has AND semantics (systemd.service(5)), so additive with
# any future upstream guard. Reference: NVIDIA/nvidia-container-toolkit#1395
[Service]
ExecCondition=/bin/bash -c 'grep -Eq "(^|/)nvidia\\.ko(\\.[xz]z|\\.zst)?:" /lib/modules/$(uname -r)/modules.dep'
```

### 7c. `automation/36-akmod-guards.sh`

```bash
#!/usr/bin/env bash
# automation/36-akmod-guards.sh — MiOS v0.1.1
# Install ExecCondition drop-ins making NVIDIA systemd units exit cleanly
# (skipped, not failed) when the running kernel's nvidia module has not yet
# been registered by akmods/depmod. Build-time script; does not touch runtime.

set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "36-akmod-guards: installing ExecCondition drop-ins"

# Widened regex (see §7a): matches kernel/drivers/ OR extra/, plus compressed.
EXEC_COND='ExecCondition=/bin/bash -c '\''grep -Eq "(^|/)nvidia\.ko(\.[xz]z|\.zst)?:" /lib/modules/$(uname -r)/modules.dep'\'''

# Services to guard. cdi-refresh is added here too so the v0.1.1 guard is
# re-synchronised to the widened regex in a single release.
SERVICES=(
    nvidia-persistenced
    nvidia-powerd
    nvidia-suspend
    nvidia-resume
    nvidia-hibernate
    nvidia-suspend-then-hibernate
    nvidia-cdi-refresh
)

DROPIN_NAME="10-mios-akmod-guard.conf"

for svc in "${SERVICES[@]}"; do
    dir="/usr/lib/systemd/system/${svc}.service.d"
    path="${dir}/${DROPIN_NAME}"
    tmp="$(mktemp)"
    cat > "${tmp}" <<EOF
# MiOS v0.1.1 akmod-guard
# Skip unit if akmods has not yet registered the nvidia kernel module
# for the currently running kernel. ExecCondition is additive (AND
# semantics, systemd.service(5)). Ref: NVIDIA/nvidia-container-toolkit#1395
[Service]
${EXEC_COND}
EOF
    install -D -m 0644 "${tmp}" "${path}"
    rm -f "${tmp}"
    log "  installed ${path}"
done

log "36-akmod-guards: done (${#SERVICES[@]} drop-ins)"
```

---

## 8. Flatpack manifest and push-script wiring

### 8a. File list (repo path → flatpack filename)

| Repo path | Flatpack filename | Purpose |
|---|---|---|
| `Containerfile` (modified stage-9 RUN block) | `Containerfile` | §1 fix |
| `automation/lib/common.sh` (new) | `scripts__lib__common.sh` | DNF_SETOPT array + logging |
| `automation/build.sh` (edit: source common.sh, drop string export) | `scripts__build.sh` | §2 |
| `automation/01-repos.sh` (edit: adopt `${DNF_SETOPT[@]}`) | `scripts__01-repos.sh` | §2 |
| `automation/05-enable-external-repos.sh` (full replacement) | `scripts__05-enable-external-repos.sh` | §3 + AUDIT-FIX-1/2 |
| `automation/lib/packages.sh` (edit: `${DNF_SETOPT[@]}` in dnf wrapper) | `scripts__lib__packages.sh` | §2 |
| `automation/36-akmod-guards.sh` (new) | `scripts__36-akmod-guards.sh` | §7 |
| `automation/37-cosign-policy.sh` (new) | `scripts__37-cosign-policy.sh` | §5d |
| `etc/containers/policy.json` (new) | `system_files__etc__containers__policy.json` | §5b |
| `etc/containers/registries.d/ghcr.io-kabuki94.yaml` (new) | `system_files__etc__containers__registries.d__ghcr.io-kabuki94.yaml` | §5c |
| `sigstore/fulcio_v1.crt.pem` (new; pinned from sigstore/root-signing) | `system_files__sigstore__fulcio_v1.crt.pem` | §5d prereq |
| `sigstore/rekor.pub` (new; pinned from sigstore/root-signing) | `system_files__sigstore__rekor.pub` | §5d prereq |
| `sigstore/ublue-os.pub` (new; from ublue-os/main cosign.pub) | `system_files__sigstore__ublue-os.pub` | §5d prereq |
| `bib-configs/qcow2.toml` (new/replace) | `bib-configs__qcow2.toml` | §6a |
| `bib-configs/vhdx.toml` (new/replace) | `bib-configs__vhdx.toml` | §6b |
| `bib-configs/iso.toml` (new/replace) | `bib-configs__iso.toml` | §6c |
| `.github/workflows/build-test.yml` (replace) | `.github__workflows__build-test.yml` | §5a |
| `.github/workflows/build-artifacts.yml` (new) | `.github__workflows__build-artifacts.yml` | §6d |
| `push-to-github.ps1` (replace with shim) | `push-to-github.ps1` | §4 |
| `push-v0.1.1.ps1` (copy of v0.1.1 with version string bump) | `push-v0.1.1.ps1` | keep v0.1.1 intact |
| `changelogs/03-Cumulative-Changelog.md` (append v0.1.1 section) | `changelogs/03-Cumulative-Changelog.md` | release notes |

### 8b. Additional Containerfile edits required (beyond the §1 RUN block)

Add these lines after the existing `COPY ` stage and before the final `bootc container lint` step:

```dockerfile
# Ensure dracut-live + squashfs-tools for the ISO artifact build leg
RUN dnf "${DNF_SETOPT[@]}" -y install dracut-live squashfs-tools && \
    dnf clean all
```

Add a final linting line at the end of the Containerfile per Red Hat best-practice:

```dockerfile
RUN bootc container lint
```

### 8c. push-v0.1.1.ps1 idempotency contract

The push script auto-discovers flatpack files with `__` separators, maps to repo paths, writes files with LF endings (no BOM), and commits via `git commit -F $msgFile` using the tempfile pattern. Idempotency requirements for v0.1.1:

1. Re-writing an identical file is a no-op (git sees no diff, no commit created).
2. The script must NOT attempt a commit if `git status --porcelain` is empty after all writes.
3. For the `push-to-github.ps1` shim: because this file already exists in the repo, overwrite semantics are `Set-Content -NoNewline -Encoding UTF8` (no BOM) and a post-write `(Get-Content).Replace("`r`n","`n") | Set-Content -NoNewline` to force LF.
4. For new files in subdirectories (`automation/lib/common.sh`, `sigstore/*`), create parent directories with `New-Item -ItemType Directory -Force` before writing.
5. Binary files (`fulcio_v1.crt.pem`, `rekor.pub`, `ublue-os.pub`) must be written via `[System.IO.File]::WriteAllBytes` with a base64-decoded byte array, NOT through `Set-Content` (which would corrupt binary).

### 8d. Commit message (embedded in the push script's tempfile)

```
v0.1.1: fix CI /usr/local symlink, absorb audit fixes, add cosign/BIB/akmod-guards

CI fix:
- Containerfile: rewrite system_files overlay to write through the
  /usr/local -> /var/usrlocal symlink (ucore/bootc lineage). Two-stage
  tar|tar pipeline; no cp -a trailing-slash collision.

Audit fixes (defensive; idempotent if remote already has them):
- automation/05-enable-external-repos.sh: full replacement. Removed the
  redundant RPM Fusion install that used `rpm -E %fedora` and clobbered
  01-repos.sh's F44 pin; switched dnf5 -> dnf for consistency.
- push-to-github.ps1: replaced buggy `git commit -m $msg` script body
  with a deprecation shim forwarding to push-v0.1.1.ps1. Removal slated
  for v0.1.1.

DNF_SETOPT activation:
- automation/lib/common.sh: new shared helper declaring DNF_SETOPT as a
  bash array (defense-in-depth complement to /etc/dnf/dnf.conf).
- automation/{build,01-repos,lib/packages,05-enable-external-repos}.sh:
  adopt "${DNF_SETOPT[@]}" on every dnf install/remove/swap/group call.

Outstanding item A (cosign keyless):
- .github/workflows/build-test.yml: cosign v3 keyless sign+verify with
  sigstore/cosign-installer@v0.1.1, id-token: write, digest capture
  via buildah push --digestfile.
- etc/containers/policy.json: strict default-reject with
  sigstoreSigned rules for ghcr.io/mios-project/mios and
  ghcr.io/ublue-os.
- etc/containers/registries.d/ghcr.io-kabuki94.yaml:
  use-sigstore-attachments: true.
- automation/37-cosign-policy.sh: install policy + pinned TUF roots.

Outstanding item B (bootc-image-builder):
- bib-configs/{qcow2,vhdx,iso}.toml: 150 GiB rootfs, NVIDIA kargs,
  kickstart for ISO (workaround BIB #528).
- .github/workflows/build-artifacts.yml: matrix on qcow2/vhdx/iso,
  triggers on dispatch/weekly/post-build; qemu-img convert for VHDX.

Outstanding item C (akmod guards):
- automation/36-akmod-guards.sh: ExecCondition drop-ins for
  nvidia-persistenced, nvidia-powerd, nvidia-{suspend,resume,hibernate,
  suspend-then-hibernate}, plus re-sync of nvidia-cdi-refresh from
  v0.1.1 to the widened regex that matches extra/ paths and .ko.xz/.zst.
```

---

## 9. Verification checklist (run locally after push)

1. `bash -n automation/**/*.sh` — syntax check all shell scripts.
2. `shellcheck automation/**/*.sh` — lint; expect SC1091 on `source "lib/common.sh"` in some scripts (path resolution via `$(dirname "$0")` is fine).
3. `! grep -rnE '^\s*dnf (install|remove|swap|group)' automation/ | grep -v '"${DNF_SETOPT\[@\]}"'` — every mutating dnf call carries the array.
4. `jq -e . etc/containers/policy.json` — policy.json parses.
5. `buildah bud -f Containerfile .` locally (on a machine with ≥ 60 GB free) — CI fix confirmed.
6. CI run on PR — cosign sign/verify steps gated off for PRs, only build+lint+push run.
7. First merge to main — cosign sign succeeds, `cosign verify` step passes.
8. Manual `workflow_dispatch` of build-artifacts — all three matrix legs complete; artifacts downloadable.
9. On a test VM: `podman pull ghcr.io/mios-project/mios:latest` with the new policy.json installed — policy triggers, fetches sigstore attachment, verifies Fulcio identity against the main-branch workflow URL.
10. `systemctl status nvidia-persistenced` after a kernel update on real hardware — unit is skipped (not failed) until `akmods.service` completes; re-triggers cleanly after depmod finishes.

---

## 10. Scope boundaries honoured

Nothing in this plan introduces features outside the explicit item list. Not included (deliberately): Flatpak preinstall changes, brand/theme overlays, additional COPR repos, BIB AMI/GCE outputs, keyed signing fallback, SBOM generation, Trivy scanning, attestations beyond cosign sign, kvmfr systemd unit (no unit exists to guard). These can be queued for v0.1.1+ if desired.

The flatpack is ready to generate from this document alone; every file listed in §8a has exact contents specified in §1–§7; the push script requirements in §8c are fully spelled out; and the commit message in §8d can be used verbatim.

---

## UPDATE: DEPRECATION SHIM REJECTED

**CRITICAL OVERRIDE:** The decision in section 4 to deprecate `push-to-github.ps1` and use versioned scripts (`push-vX.Y.Z.ps1`) has been explicitly rejected and reversed by the maintainer. `push-to-github.ps1` is the **only** variant to keep, as it is a core part of the local build stack. All versioned variants must be merged back into the main `push-to-github.ps1` file. Do NOT create versioned push scripts.

---
### ⚖️ Legal & Source Reference
- **Copyright:** (c) 2026 MiOS Project
- **Status:** Personal Property / Private Infrastructure
- **Project Repository:** [mios-project/mios](https://github.com/mios-project/mios)
- **Documentation:** [MiOS Navigation Hub](https://github.com/mios-project/mios/blob/main/specs/Home.md)
- **Artifact Hub:** [ai-context.json](https://github.com/mios-project/mios/blob/main/ai-context.json)
---
<!-- ⚖️ MiOS Proprietary Artifact | Copyright (c) 2026 MiOS Project -->
