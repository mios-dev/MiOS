# 'MiOS' v0.2.0 - Linux Build Targets
# Requires: podman, just
# Usage: just build | just iso | just all
#
# By invoking any 'just' target you acknowledge AGREEMENTS.md
# (Apache-2.0 main + bundled-component licenses in LICENSES.md +
# attribution in CREDITS.md). 'MiOS' is a research project (pronounced
# 'MyOS'; generative, seed-script-derived). Set MIOS_AGREEMENT_BANNER=quiet
# to silence the per-script banners that appear during build.

# Load user environment from XDG-compliant configuration
# This sources $HOME/.config/mios/*.toml files and exports MIOS_* variables
_load_env := `bash -c 'source ./tools/lib/userenv.sh 2>/dev/null || true'`
_agreement_banner := `bash -c '
case "${MIOS_AGREEMENT_BANNER:-}" in
    quiet|silent|off|0|false|FALSE) ;;
    *)
        cat >&2 <<__EOF__
[mios] just build target invoked. AGREEMENTS.md acknowledged
       (Apache-2.0 + LICENSES.md + CREDITS.md). Research project
       (pronounced MyOS; generative, seed-script-derived).
__EOF__
        ;;
esac
true'`

MIOS_REGISTRY_DEFAULT := "ghcr.io/MiOS-DEV/mios" # @verb:GET_REGISTRY
IMAGE_NAME := env_var_or_default("MIOS_IMAGE_NAME", MIOS_REGISTRY_DEFAULT) # @verb:GET_IMAGE
MIOS_VAR_VERSION := "v0.2.0" # @verb:GET_VERSION
VERSION := `cat VERSION 2>/dev/null || echo {{MIOS_VAR_VERSION}}`
LOCAL := env_var_or_default("MIOS_LOCAL_TAG", "localhost/mios:latest") # @verb:SET_LOCAL
MIOS_IMG_BIB := "quay.io/centos-bootc/bootc-image-builder:latest" # @verb:GET_BIB
BIB := env_var_or_default("MIOS_BIB_IMAGE", MIOS_IMG_BIB)

# Run preflight system check
preflight:
    @chmod +x tools/preflight.sh
    @./tools/preflight.sh

# Show current flight status and variable mappings
flight-status:
    @chmod +x tools/flight-control.sh
    @./tools/flight-control.sh

# Unified initialization (Mode 2: User-space)
init:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# System-wide deployment (Mode 1: FHS system install)
deploy:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# Live ISO Initiation (Mode 0: Overlay onto root)
live-init:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# bootc container lint -- runs against the locally built image.
# The Containerfile already runs `bootc container lint` as its final RUN, so
# `just build` is itself a lint gate. This target re-runs lint on demand.
lint:
    podman run --rm --entrypoint /usr/bin/bootc {{LOCAL}} container lint

# Build OCI image locally
build: preflight flight-status
    podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} .
    @echo "[OK] Built: {{LOCAL}}"

# Build OCI image with unified logging
build-logged: artifact
    @mkdir -p logs
    @LOG_FILE="logs/build-$(date -u +%Y%m%dT%H%M%SZ).log"
    @echo "---" | tee -a "${LOG_FILE}"
    @echo "[START] CHECKPOINT: Starting 'MiOS' build..." | tee -a "${LOG_FILE}"
    @echo "Unified log will be available at: ${LOG_FILE}" | tee -a "${LOG_FILE}"
    @echo "---" | tee -a "${LOG_FILE}"
    @set -o pipefail; podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} . 2>&1 | tee -a "${LOG_FILE}"
    @echo "---" | tee -a "${LOG_FILE}"
    @echo "[OK] CHECKPOINT: 'MiOS' build complete." | tee -a "${LOG_FILE}"
    @echo "Unified log available at: ${LOG_FILE}" | tee -a "${LOG_FILE}"
    @echo "---"

# Build OCI image with verbose output (no redirection)
build-verbose: artifact
    podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} .

# Embed the most recent build log into the image
embed-log:
    @echo "[START] Finding most recent build log..."
    @LOG_FILE=$$(ls -t logs/build-*.log 2>/dev/null | head -n 1)
    @if [ -z "$${LOG_FILE}" ]; then \
        echo "[FAIL] No build logs found in logs/. Run 'just build-logged' first."; \
        exit 1; \
    fi
    @echo "  Found: $${LOG_FILE}"
    @echo "[START] Creating temporary Containerfile to embed log..."
    @echo "FROM {{LOCAL}}" > /tmp/Containerfile.embed
    @echo "COPY --chown=root:root $${LOG_FILE} /usr/share/mios/build-logs/latest-build.log" >> /tmp/Containerfile.embed
    @echo "[START] Building image with embedded log..."
    @set -o pipefail; podman build --no-cache -f /tmp/Containerfile.embed -t localhost/mios:latest-with-log .
    @rm /tmp/Containerfile.embed
    @echo "---"
    @echo "[OK] Success! New image created: localhost/mios:latest-with-log"
    @echo "   Embedded log is at: /usr/share/mios/build-logs/latest-build.log"
    @echo "---"

# Refresh all AI manifests, UKB, and Wiki documentation
artifact:
    ./automation/ai-bootstrap.sh
    @echo "[OK] Artifacts, UKB, and Wiki refreshed."

# Build OCI image on Cloud (using remote context)
cloud-build:
    @echo "Configure cloud-build with your cloud provider CLI"
    @echo "Example: podman build --remote -t {{IMAGE_NAME}}:{{VERSION}} ."
    @echo "[OK] Cloud Build target (customize for your cloud provider)"

# Rechunk for optimal Day-2 updates (5-10x smaller deltas)
rechunk: build
    podman run --rm \
        --security-opt label=type:unconfined_t \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        {{LOCAL}} \
        /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 containers-storage:{{LOCAL}} containers-storage:{{IMAGE_NAME}}:{{VERSION}}
    podman tag {{IMAGE_NAME}}:{{VERSION}} {{IMAGE_NAME}}:latest
    @echo "[OK] Rechunked: {{IMAGE_NAME}}:{{VERSION}}"

# Generate RAW bootable disk image (80 GiB root)
raw: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/bib.toml:/config.toml:ro \
        {{BIB}} build --type raw --rootfs ext4 {{LOCAL}}
    @echo "[OK] RAW image in output/"

# Generate Anaconda installer ISO
# FIX v0.2.0: ONLY mount iso.toml (includes minsize). Do NOT also mount bib config.
# BIB crashes with: "found config.json and also config.toml"
iso: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/iso.toml:/config.toml:ro \
        {{BIB}} build --type iso --rootfs ext4 {{LOCAL}}
    @echo "[OK] ISO image in output/"

# Generate QEMU qcow2 disk image
# Substitutes MIOS_USER_PASSWORD_HASH and MIOS_SSH_PUBKEY from env before invoking BIB.
qcow2: build
    mkdir -p output
    @if [ -z "${MIOS_USER_PASSWORD_HASH:-}" ]; then echo "[FAIL] Set MIOS_USER_PASSWORD_HASH (openssl passwd -6 'yourpass')"; exit 1; fi
    @TMPTOML="$(mktemp /tmp/mios-qcow2-XXXXXX.toml)" && \
        sed -e "s|\$6\$REPLACEME_WITH_SHA512_HASH\$REPLACEME|${MIOS_USER_PASSWORD_HASH}|g" \
            -e "s|AAAA_REPLACE_WITH_REAL_PUBKEY|${MIOS_SSH_PUBKEY:-}|g" \
            ./config/artifacts/qcow2.toml > "$$TMPTOML" && \
        sudo podman run --rm -it --privileged \
            --security-opt label=type:unconfined_t \
            -v ./output:/output \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            -v "$$TMPTOML":/config.toml:ro \
            {{BIB}} build --type qcow2 --rootfs ext4 {{LOCAL}}; \
        rm -f "$$TMPTOML"
    @echo "[OK] QCOW2 image in output/"

# Generate Hyper-V VHDX disk image
# BIB emits VPC (.vhd); we convert to .vhdx via qemu-img.
# Substitutes MIOS_USER_PASSWORD_HASH and MIOS_SSH_PUBKEY from env before invoking BIB.
vhdx: build
    mkdir -p output
    @if [ -z "${MIOS_USER_PASSWORD_HASH:-}" ]; then echo "[FAIL] Set MIOS_USER_PASSWORD_HASH (openssl passwd -6 'yourpass')"; exit 1; fi
    @TMPTOML="$(mktemp /tmp/mios-vhdx-XXXXXX.toml)" && \
        sed -e "s|\$6\$REPLACEME_WITH_SHA512_HASH\$REPLACEME|${MIOS_USER_PASSWORD_HASH}|g" \
            -e "s|AAAA_REPLACE_WITH_REAL_PUBKEY|${MIOS_SSH_PUBKEY:-}|g" \
            ./config/artifacts/vhdx.toml > "$$TMPTOML" && \
        sudo podman run --rm -it --privileged \
            --security-opt label=type:unconfined_t \
            -v ./output:/output \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            -v "$$TMPTOML":/config.toml:ro \
            {{BIB}} build --type vhd --rootfs ext4 {{LOCAL}}; \
        rm -f "$$TMPTOML"
    @if command -v qemu-img >/dev/null 2>&1 && ls output/*.vhd >/dev/null 2>&1; then \
        for vhd in output/*.vhd; do \
            vhdx="$${vhd%.vhd}.vhdx"; \
            qemu-img convert -f vpc -O vhdx "$$vhd" "$$vhdx" && rm -f "$$vhd" && echo "[OK] Converted: $$vhdx"; \
        done; \
    else \
        echo "[WARN] qemu-img not found or no .vhd produced -- .vhd retained in output/"; \
    fi
    @echo "[OK] VHDX image in output/"

# Generate WSL2 tar.gz for wsl --import
wsl2: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/wsl2.toml:/config.toml:ro \
        {{BIB}} build --type wsl2 {{LOCAL}}
    @echo "[OK] WSL2 image in output/ -- import with: wsl --import 'MiOS' ./mios output/disk.wsl2"


# Log artifacts to MiOS-bootstrap repository (Linux FS native)
log-bootstrap:
    @echo "[START] Logging artifacts to MiOS-bootstrap repository (Linux FS native)..."
    ./tools/log-to-bootstrap.sh
    @echo "[OK] Artifacts logged to bootstrap repository"

# Complete build with bootstrap logging (recommended for releases)
build-and-log: build-logged
    @echo "[START] Running bootstrap artifact logging (Linux FS native)..."
    ./tools/log-to-bootstrap.sh
    @echo "[OK] Build complete with artifacts logged to bootstrap"

# Full pipeline: build  rechunk  log to bootstrap (Linux FS native)
all-bootstrap: build rechunk log-bootstrap
    @echo "[OK] Full pipeline complete (build  rechunk  bootstrap Linux FS native)"

# Generate SBOM for the local image
sbom:
    @echo "[START] Generating SBOM for {{LOCAL}}..."
    @mkdir -p artifacts/sbom
    podman run --rm \
        -v ./artifacts/sbom:/out \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        anchore/syft:latest scan {{LOCAL}} -o cyclonedx-json > artifacts/sbom/mios-sbom.json
    @echo "[OK] SBOM generated: artifacts/sbom/mios-sbom.json"

# ============================================================================
# User-Space Management
# ============================================================================

# Initialize user-space configuration (seeds ~/.config/mios/mios.toml).
init-user-space:
    @./tools/init-user-space.sh

# Re-initialize user-space (overwrite mios.toml with vendor template).
reinit-user-space:
    @./tools/init-user-space.sh --force

# Show user-space configuration paths
show-user-space:
    @echo "'MiOS' User-Space Directories:"
    @echo "  Config:  ${XDG_CONFIG_HOME:-$HOME/.config}/mios/"
    @echo "  Data:    ${XDG_DATA_HOME:-$HOME/.local/share}/mios/"
    @echo "  Cache:   ${XDG_CACHE_HOME:-$HOME/.cache}/mios/"
    @echo "  State:   ${XDG_STATE_HOME:-$HOME/.local/state}/mios/"
    @echo "  Runtime: ${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mios/"
    @echo ""
    @echo "Configuration:"
    @if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios.toml" ]; then \
        echo "  [OK] mios.toml"; \
    else \
        echo "  [FAIL] mios.toml (run: just init)"; \
    fi
    @for f in env.toml images.toml build.toml flatpaks.list; do \
        if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/mios/$f" ]; then \
            echo "  [legacy] $f -- migrate via: just init"; \
        fi; \
    done

# Show loaded environment variables
show-env:
    @echo "'MiOS' Environment Variables:"
    @source ./tools/lib/userenv.sh && env | grep '^MIOS_' | sort | sed 's/^/  /'

# Edit the unified user configuration (mios.toml).
edit:
    @CFG="${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios.toml"; \
        if [ ! -f "$CFG" ]; then \
            echo "[FAIL] $CFG not found. Run: just init"; exit 1; \
        fi; \
        ${EDITOR:-vim} "$CFG"
