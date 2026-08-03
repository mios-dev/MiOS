#!/usr/bin/env bash
set -euo pipefail

log() { printf '[test-firstboot-prestage] %s\n' "$*"; }
die() { printf '[test-firstboot-prestage] ERROR: %s\n' "$*" >&2; exit 1; }

tmp_dir="$(mktemp -d /tmp/firstboot-prestage-test.XXXXXX)"
trap 'rm -rf "$tmp_dir"' EXIT

stub_bin="${tmp_dir}/bin"
mkdir -p "$stub_bin"
pull_log="${tmp_dir}/pulls.log"

cat << 'EOF' > "${stub_bin}/podman"
if [[ "$*" == *"image exists"* ]]; then
    exit 1
elif [[ "$*" == *"pull"* ]]; then
    img="${!#}"
    echo "$img" >> "${MIOS_TEST_PULL_LOG}"
    if [[ "$img" == *"fail"* ]]; then
        exit 1
    fi
    exit 0
fi
exit 0
EOF
chmod +x "${stub_bin}/podman"

export PATH="${stub_bin}:${PATH}"
export MIOS_TEST_PULL_LOG="$pull_log"

fblist="${tmp_dir}/firstboot.list"
cat << 'EOF' > "$fblist"
docker.io/vllm/vllm-openai:latest
docker.io/lmsysorg/sglang-fail:latest
EOF

log "Testing firstboot prestage with stub podman "

FBLIST="$fblist" STORE="${tmp_dir}/store" bash -c '
    FBLIST="'"$fblist"'"
    STORE="'"${tmp_dir}/store"'"
    if [ -f "$FBLIST" ] && command -v podman >/dev/null 2>&1; then
        while IFS= read -r fb_img; do
            fb_img="$(echo "$fb_img" | sed "s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//")"
            [ -z "$fb_img" ] && continue
            if podman --root "$STORE" image exists "$fb_img" 2>/dev/null; then
                continue
            fi
            _fb_pulled=0
            for _fb_try in 1 2 3; do
                if podman --root "$STORE" pull "$fb_img" >/dev/null 2>&1; then
                    _fb_pulled=1
                    break
                fi
            done
        done < "$FBLIST"
    fi
'

if [[ ! -f "$pull_log" ]]; then
    die "Pull log was not created"
fi

pull_count="$(wc -l < "$pull_log" | tr -d ' ')"
if [[ "$pull_count" -lt 2 ]]; then
    die "Expected at least 2 pull attempts across the images, got $pull_count"
fi

log "Firstboot prestage test passed clean"
