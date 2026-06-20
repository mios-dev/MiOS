<!-- AI-hint: MiOS k3s manifests -- how the generated/ k8s manifests are produced from the pod SSOT (WS-7 #61), how to regenerate, and the k3s adaptation caveats before they can deploy. -->

# MiOS → k3s manifests (pods-as-SSOT, WS-7)

The workload SSOT for MiOS is the **Quadlet** unit set in
`usr/share/containers/systemd/*.container` (Architectural Law 3 / bound-images).
This directory projects those workloads to **k3s/Kubernetes** so the cluster path
cannot silently drift from the pod path.

## `generated/`

One manifest per MiOS workload, produced by
[`tools/generate-k3s-manifests.sh`](../../../../tools/generate-k3s-manifests.sh):

- **Standalone containers** (most MiOS services — `Network=host`, rootful, one
  container per Quadlet) → one `Pod` manifest each.
- **Pods** (e.g. `mios-webtools`, a 5-container pod) → one manifest for the whole
  pod, generated from the pod (podman requires this — its member containers
  cannot be generated individually).

The mapping is produced by `podman kube generate` (podman's own canonical
container→k8s converter) rather than a hand-rolled Quadlet→k8s mapper, so the
field translation is podman-authored and correct. The generator strips the
volatile fields (`creationTimestamp`, the multi-mount `bind-mount-options`
annotation, the podman-version comment) so output is **deterministic** —
re-running on the same pods yields byte-identical files (verified across 3 runs).

> This is a **host/VM runtime** generator: it reads the *live* pods, so it runs on
> a machine where the MiOS stack is up (not in the OCI build, which has no running
> pods). Regenerate after changing a Quadlet, then commit the result.

```bash
# on a host/VM running the MiOS stack
tools/generate-k3s-manifests.sh
git add usr/share/mios/k3s/generated && git commit
```

## Status: generated, not yet deployed (inert)

These manifests are a faithful **starting point**, not turnkey k3s specs. MiOS
workloads use host networking, CDI GPU, rootful podman, and hostPath bind-mounts,
which need k3s-specific wiring before they deploy:

| MiOS trait | k3s adaptation still needed |
|---|---|
| `Network=host` | `hostNetwork: true` (+ resolve host-port conflicts) |
| CDI GPU (NVIDIA/ROCm/iGPU) | a GPU device plugin + `resources.limits` |
| hostPath bind-mounts (`/var/lib/mios/...`) | `PersistentVolume`/`PVC` or explicit `hostPath` |
| rootful + SELinux `:Z` relabel | `securityContext` / SELinux options per cluster |

They stay **inert until the k3s lane is enabled** (`[k3s]` in `mios.toml`); nothing
here deploys anything on its own. Completing the per-trait adaptation above is the
remaining WS-7 work.
