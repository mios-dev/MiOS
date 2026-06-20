#!/usr/bin/env bash
# AI-hint: Generate k3s/k8s manifests from the live MiOS pods (pods-as-SSOT, WS-7 #61).
# AI-related: usr/share/mios/k3s, usr/share/containers/systemd, usr/share/mios/mios.toml, tools/generate-ai-manifest.py
# AI-functions: _emit_header, main
#   Uses `podman kube generate` (podman's canonical container->k8s converter) so
#   the mapping is podman-AUTHORED, not hand-rolled, then writes DETERMINISTIC
#   YAML (strips the volatile creationTimestamp, bind-mount-options annotation,
#   and podman-version line) under
#   usr/share/mios/k3s/generated/ -- one manifest per mios-* pod, each carrying a
#   self-documenting AI-hint header. Read-only wrt podman. Run on a host/VM where
#   the mios pods exist; commit the result like any generated artifact.
# ----------------------------------------------------------------------------
# WHY: the Quadlets in usr/share/containers/systemd are the workload SSOT. This
# projects them to k3s so the cluster path can't drift from the pod path. podman
# has no quadlet->kube step, but the running pods ARE the quadlets instantiated,
# so `podman kube generate` is the faithful, version-correct bridge.
#
# k3s ADAPTATION CAVEAT (documented, not hidden): MiOS workloads use Network=host,
# rootful podman, CDI GPU, and hostPath bind-mounts. The generated manifests are a
# faithful STARTING POINT; host-network / GPU / privileged services still need
# k3s-specific wiring (hostNetwork:true, a GPU device plugin, PV/PVC) before they
# deploy. They are INERT until the [k3s] lane is enabled -- this script only
# produces the artifacts, it deploys nothing.
#
# Reproducible: same pods -> byte-identical output (the volatile fields --
# creationTimestamp, the non-deterministic bind-mount-options annotation that
# podman emits for multi-bind-mount containers, and the "Created with podman-X"
# line -- are stripped). Verified identical across 3 consecutive runs. NB: this is
# a HOST/VM runtime generator (it reads live pods), so unlike the build-time
# manifest generators it does not run in the OCI build gate.
# ----------------------------------------------------------------------------
set -euo pipefail

ROOT="${MIOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${MIOS_K3S_OUT:-$ROOT/usr/share/mios/k3s/generated}"
NAME_FILTER="${MIOS_K3S_FILTER:-^mios-}"
PODMAN="${PODMAN:-podman}"

_emit_header() {
    # Deterministic AI-hint header so generated manifests stay agent-readable AND
    # satisfy the AI-hint coverage gate without polluting the k8s spec (# = YAML
    # comment, ignored by kubectl).
    local name="$1"
    printf '# AI-hint: GENERATED k3s/k8s manifest for the MiOS %s pod (pods-as-SSOT, WS-7). DO NOT EDIT -- regenerate via tools/generate-k3s-manifests.sh. Inert until the [k3s] lane is enabled; host-net/GPU/bind-mount services need k3s adaptation first.\n' "$name"
    printf '# AI-related: tools/generate-k3s-manifests.sh, %s.container, usr/share/mios/k3s/README.md\n' "$name"
}

main() {
    if ! "$PODMAN" kube generate --help >/dev/null 2>&1; then
        echo "[generate-k3s] podman kube generate unavailable -- aborting" >&2
        return 1
    fi
    mkdir -p "$OUT_DIR"
    # Targets = mios-* PODS (a pod's members must be generated from the POD, not
    # each container -- podman errors otherwise) + mios-* STANDALONE containers
    # (those with an empty Pod field). This captures every workload exactly once.
    local pods=() standalone=() targets=()
    mapfile -t pods < <("$PODMAN" pod ps --format '{{.Name}}' 2>/dev/null \
        | grep -E "$NAME_FILTER" | sort -u || true)
    mapfile -t standalone < <("$PODMAN" ps -a --format '{{.Names}}|{{.Pod}}' 2>/dev/null \
        | grep -E "$NAME_FILTER" | grep -E '\|$' | sed 's/|$//' | sort -u || true)
    targets=("${pods[@]}" "${standalone[@]}")
    if [[ "${#targets[@]}" -eq 0 ]]; then
        echo "[generate-k3s] no pods/containers match $NAME_FILTER" >&2
        return 0
    fi
    local n out raw generated=0
    for n in "${targets[@]}"; do
        [[ -n "$n" ]] || continue
        out="$OUT_DIR/${n}.yaml"
        # Capture first (|| true) so a container that must be generated via its
        # pod -- or any kube-generate failure -- never aborts the run under set -e.
        raw="$("$PODMAN" kube generate "$n" 2>/dev/null || true)"
        if printf '%s\n' "$raw" | grep -qE '^apiVersion:'; then
            {
                _emit_header "$n"
                printf '%s\n' "$raw" \
                    | grep -vE '^[[:space:]]*creationTimestamp:' \
                    | grep -vE '^[[:space:]]*bind-mount-options:' \
                    | grep -vE '^# Created with podman' || true
            } > "$out"
            generated=$((generated + 1))
            echo "[generate-k3s]   $out"
        else
            echo "[generate-k3s]   SKIP $n (no manifest from kube generate)" >&2
        fi
    done
    echo "[generate-k3s] wrote $generated manifest(s) to $OUT_DIR"
    return 0
}

main "$@"
