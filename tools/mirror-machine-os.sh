#!/bin/bash
# AI-hint: Mirrors the container images (not the podman-machine disk images) of [image].machine_os_repo:machine_os_tag into [image].machine_os_mirror, digest-identical, so builders that cannot parse the disk-image artifacts (Codespaces) pull the same MiOS base.
# AI-related: /usr/share/mios/templates/bash, usr/share/mios/mios.toml, .github/workflows/machine-os-mirror.yml
# AI-functions: main

set -euo pipefail

main() {
    local root="${1:-.}"
    local get="$root/usr/libexec/mios/mios-toml-get"
    local repo tag mirror
    repo="$(python3 "$get" image machine_os_repo)"
    tag="$(python3 "$get" image machine_os_tag)"
    mirror="${2:-$(python3 "$get" image machine_os_mirror)}"
    local src="$repo:$tag" dst="$mirror:$tag" list="localhost/mios-machine-os-mirror:$tag"

    # The upstream index also carries the podman-machine disk images (annotated
    # disktype); MiOS-DEV boots those from upstream, so only images are mirrored.
    local -a digests
    mapfile -t digests < <(skopeo inspect --raw "docker://$src" \
        | jq -r '.manifests[] | select(.annotations.disktype == null) | .digest')
    if [ "${#digests[@]}" -eq 0 ]; then
        echo "[mirror-machine-os] $src lists no container images" >&2
        exit 1
    fi

    podman manifest rm "$list" >/dev/null 2>&1 || true
    podman manifest create "$list" >/dev/null
    local d
    for d in "${digests[@]}"; do
        podman manifest add "$list" "docker://$repo@$d" >/dev/null
    done
    podman manifest push --all "$list" "docker://$dst"
    podman manifest rm "$list" >/dev/null

    # The mirror must hold exactly the upstream image manifests, by digest.
    local want got
    want="$(printf '%s\n' "${digests[@]}" | sort)"
    got="$(skopeo inspect --raw "docker://$dst" | jq -r '.manifests[].digest' | sort)"
    if [ "$got" != "$want" ]; then
        printf '[mirror-machine-os] %s differs from %s\nwant:\n%s\ngot:\n%s\n' "$dst" "$src" "$want" "$got" >&2
        exit 1
    fi
    echo "[mirror-machine-os] $dst: ${#digests[@]} container image(s), digest-identical to $src"
}

main "$@"
