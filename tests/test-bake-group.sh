#!/usr/bin/env bash
set -euo pipefail

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="$(cd "$_self_dir/.." && pwd)"

log() { printf '[test-bake-group] %s\n' "$*"; }
die() { printf '[test-bake-group] ERROR: %s\n' "$*" >&2; exit 1; }

tmp_dir="$(mktemp -d /tmp/bake-group-test.XXXXXX)"
trap 'rm -rf "$tmp_dir"' EXIT

# mios-bake-group defaults STORE to /usr/lib/containers/storage, which a
# runner cannot create. The tool already honours an override, so point it
# at the fixture directory rather than requiring root.
export STORE="${tmp_dir}/containers/storage"
mkdir -p "$STORE"

stub_bin="${tmp_dir}/bin"
mkdir -p "$stub_bin"
pull_log="${tmp_dir}/pulls.log"

cat << 'EOF' > "${stub_bin}/podman"
if [[ "$*" == *"pull"* ]]; then
    img="${!#}"
    echo "$img" >> "${MIOS_TEST_PULL_LOG}"
    exit 0
elif [[ "$*" == *"image inspect"* ]]; then
    echo '{"Digest": "sha256:1234567890abcdef"}'
    exit 0
fi
exit 0
EOF
chmod +x "${stub_bin}/podman"

export PATH="${stub_bin}:${PATH}"
export MIOS_TEST_PULL_LOG="$pull_log"

log "Case 1: MIOS_BAKE_BOUND_IMAGES=0 short-circuit"
out="$(MIOS_BAKE_BOUND_IMAGES=0 bash "${ROOT}/usr/libexec/mios/mios-bake-group" sys)"
if [[ "$out" != *"SKIP bound-images bake"* ]]; then
    die "Case 1 failed: output did not contain SKIP message: $out"
fi
if [[ -f "$pull_log" && -s "$pull_log" ]]; then
    die "Case 1 failed: stub podman pulled images despite MIOS_BAKE_BOUND_IMAGES=0"
fi
log "Case 1 passed"

log "Case 2: group .list with N images -> N stub pulls + bound-images.tsv entries"
plan_dir="${tmp_dir}/plan.d"
mkdir -p "$plan_dir"
cat << 'EOF' > "${plan_dir}/01-testgroup.list"
docker.io/library/alpine:latest
docker.io/library/ubuntu:latest
EOF

sbom_dir="${tmp_dir}/sbom"
mkdir -p "$sbom_dir"

rm -f "$pull_log"
MIOS_PLAN_DIR="$plan_dir" \
STORE="${tmp_dir}/store" \
SCRATCH="${tmp_dir}/scratch" \
SBOM_DIR="$sbom_dir" \
bash "${ROOT}/usr/libexec/mios/mios-bake-group" testgroup

pull_count=0
if [[ -f "$pull_log" ]]; then
    pull_count="$(wc -l < "$pull_log" | tr -d ' ')"
fi

if [[ "$pull_count" -ne 2 ]]; then
    die "Case 2 failed: expected 2 pulls, got $pull_count"
fi

if [[ ! -f "${sbom_dir}/bound-images.tsv" ]]; then
    die "Case 2 failed: bound-images.tsv was not created"
fi

tsv_rows="$(grep -c "docker.io/library/" "${sbom_dir}/bound-images.tsv" || true)"
if [[ "$tsv_rows" -ne 2 ]]; then
    die "Case 2 failed: expected 2 rows in bound-images.tsv, got $tsv_rows"
fi
log "Case 2 passed"

log "Case 3: firstboot-token image never appears in group .list files"
fb_file="${ROOT}/usr/lib/mios/bake/plan.d/firstboot.list"
if [[ -f "$fb_file" ]]; then
    while IFS= read -r fb_img; do
        [[ -z "$fb_img" ]] && continue
        for gf in "${ROOT}/usr/lib/mios/bake/plan.d/"[0-9]*-[a-z]*.list; do
            [[ -f "$gf" ]] || continue
            if grep -qF "$fb_img" "$gf"; then
                die "Case 3 failed: firstboot image $fb_img found in group list $gf"
            fi
        done
    done < "$fb_file"
fi
log "Case 3 passed"

log "Case 4: localhost/ ref in a pull group fails fast with zero pulls"
cat << 'EOF' > "${plan_dir}/02-badgroup.list"
localhost/mios-testonly:latest
docker.io/library/alpine:latest
EOF

rm -f "$pull_log"
set +e
out="$(MIOS_PLAN_DIR="$plan_dir" \
    STORE="${tmp_dir}/store" \
    SCRATCH="${tmp_dir}/scratch" \
    SBOM_DIR="$sbom_dir" \
    bash "${ROOT}/usr/libexec/mios/mios-bake-group" badgroup 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    die "Case 4 failed: bake-group succeeded on a plan containing a localhost/ ref"
fi
if [[ "$out" != *"locally-built image localhost/mios-testonly:latest"* ]]; then
    die "Case 4 failed: missing fail-fast diagnostic in output: $out"
fi
if [[ -f "$pull_log" && -s "$pull_log" ]]; then
    die "Case 4 failed: pulls were attempted despite localhost/ ref in the plan"
fi
log "Case 4 passed"

log "All mios-bake-group unit tests passed"
