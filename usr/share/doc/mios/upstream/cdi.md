<!-- AI-hint: Documentation for the Container Device Interface (CDI) specification, detailing how MiOS abstracts NVIDIA, AMD ROCm/KFD, and Intel iGPU passthrough into a unified, vendor-agnostic layer that container runtimes and the local inference lanes (mios-llm-light/heavy) consume to reach the GPU.
     AI-related: mios-gpu, mios-cdi-detect, mios-cdi-detect.service, mios-llm-light, mios-llm-light.container, nvidia-cdi-refresh.service -->
# Container Device Interface (CDI)

> The universal layer MiOS uses for NVIDIA, AMD ROCm/KFD, and Intel iGPU
> passthrough into containers. Vendor-generated specs live at `/run/cdi/`,
> admin overrides at `/etc/cdi/`; both directories are declared (LAW 2,
> NO-MKDIR-IN-VAR) in `usr/lib/tmpfiles.d/mios-gpu.conf`. Generation is driven
> by `mios-cdi-detect` (`/usr/libexec/mios/mios-cdi-detect`, run by
> `mios-cdi-detect.service`). Source: `usr/share/doc/mios/concepts/architecture.md`
> §Hardware acceleration.

## Purpose — why CDI matters to MiOS as a whole

MiOS is a single immutable bootc/OCI Fedora image that is *also* a local,
self-replicating agentic AI OS. The "agentic AI" half lives in containers (the
inference lanes, the agent gateways, the datastore), and those containers have
to reach the host GPU to be useful — that is where the model generation and
embeddings actually happen. CDI is the seam that makes that work across
heterogeneous hardware **without** baking a vendor into the image.

Because the image is hardware-agnostic and ships once for every host (gaming
desktop with an RTX 4090, an AMD APU laptop, an Intel iGPU mini-PC, or a WSL2
guest), MiOS cannot hard-code a GPU runtime hook. Instead the booted host
*describes* whatever GPU it has into a CDI spec, and any CDI-aware runtime
(podman) injects exactly the right device nodes, libraries, and env vars into a
container on request. The same `nvidia.com/gpu=all` reference that a maintainer
types into the `mios-llm-light` Quadlet resolves correctly whether the GPU is a
bare-metal NVIDIA card or a WSL2-exposed device — that portability is precisely
what lets one immutable image serve every host.

This is "Hardware delegation" (Pillar 2 in the architecture doc) in concrete
form: one CDI/VFIO plumbing layer feeds both the AI plane (a GPU passed *into* a
container) and the virtualization plane (a GPU passed *through* to a VFIO guest).

## Project

- Spec: <https://github.com/cncf-tags/container-device-interface>
- Status: vendor-agnostic CNCF tag; supersedes per-vendor runtime hooks

## Why CDI replaces vendor hooks

Pre-CDI, NVIDIA used `nvidia-container-runtime` as a special OCI hook, AMD used a
different hook, and Intel had no clean story. CDI lets the vendor declare what
their device exposes (kernel device nodes, libraries to bind-mount, env vars)
once, in a YAML/JSON spec, and any CDI-aware runtime (podman, containerd, CRI-O)
handles the rest. For an image that must run identically on three GPU vendors and
under WSL2, that single abstraction is the difference between one portable image
and a matrix of per-vendor builds.

## Spec example (NVIDIA, abridged)

```yaml
cdiVersion: 0.5.0
kind: nvidia.com/gpu
devices:
  - name: "0"
    containerEdits:
      deviceNodes:
        - path: /dev/nvidia0
        - path: /dev/nvidiactl
      mounts:
        - hostPath: /usr/lib64/libcuda.so.1
          containerPath: /usr/lib/x86_64-linux-gnu/libcuda.so.1
      env:
        - NVIDIA_VISIBLE_DEVICES=0
```

## MiOS detection and generation flow

CDI specs are regenerated on every boot — never baked — so the image stays
hardware-agnostic and the spec always matches the host it landed on.

1. **GPU detection.** `mios-gpu-detect` (bridged by `automation/34-gpu-detect.sh`,
   enabled via the systemd preset) blocks NVIDIA modules inside VMs, enables the
   hardware renderer on bare metal, and flags the RTX 50-series VFIO reset bug. It
   writes `/run/mios/gpu-passthrough.status`.
2. **Multi-vendor CDI generation.** `mios-cdi-detect`
   (`/usr/libexec/mios/mios-cdi-detect`, run by `mios-cdi-detect.service`, ordered
   `Before=nvidia-cdi-refresh.service`) probes every GPU vendor present and writes
   the matching spec(s) into `/run/cdi/`. All branches are best-effort: a missing
   vendor toolkit makes that branch a no-op rather than failing the boot. Vendor
   coverage:
   - **NVIDIA** via `nvidia-ctk` (NVIDIA Container Toolkit) →
     `/run/cdi/nvidia.yaml` (or `/run/cdi/nvidia-wsl.yaml` under WSL2). NVIDIA's
     own `nvidia-cdi-refresh.service` also keeps `/run/cdi/nvidia.yaml` fresh,
     reading `/etc/nvidia-container-toolkit/cdi-refresh.env` (seeded by
     `mios-gpu.conf` with `CDI_OUTPUT_PATH=/run/cdi/nvidia.yaml`).
   - **AMD** via `amd-ctk` (AMD Container Toolkit) → `/run/cdi/amd.json` (AMD
     emits JSON, not YAML).
   - **Intel** via `intel-cdi-specs-generator`
     (`/usr/libexec/mios/intel-cdi-specs-generator`, fetched best-effort by
     `automation/41-gpu-cdi-toolkits.sh`) → `/run/cdi/intel.yaml`.
   - **WSL2 iGPUs.** AMD APUs and Intel iGPUs are exposed under WSL2 via
     `/dev/dxg` (not `/dev/kfd` or `renderD*`); for those, `mios-cdi-detect`
     writes a hand-rolled `wsl2-<vendor>.yaml` spec instead of relying on the
     Linux-side vendor toolkit. A status snapshot lands at
     `/run/mios/cdi-detect.status`.
3. **Admin overrides** land in `/etc/cdi/` (per-host pinning — e.g. "GPU 0 is
   reserved for the inference lane, GPU 1 for VFIO passthrough"). `/etc/cdi/`
   wins over the auto-generated `/run/cdi/` spec, in keeping with LAW 1
   (USR-OVER-ETC: `/etc/` is the admin-override surface).
4. **Directory declaration.** `usr/lib/tmpfiles.d/mios-gpu.conf` ensures
   `/run/cdi/`, `/run/mios/`, `/etc/cdi/`, and the NVIDIA toolkit's
   `/etc/nvidia-container-toolkit/` exist on every boot (LAW 2, NO-MKDIR-IN-VAR).

> Path note: specs go in `/run/cdi/`, not `/var/run/cdi/`. On bootc/Fedora
> `/var/run` is a symlink to `/run`, and `systemd-tmpfiles` rejects the legacy
> alias ("Line references path below /var/run") — so MiOS declares `/run` directly.

## Using a CDI device

```bash
# Podman
podman run --rm --device nvidia.com/gpu=all <image> nvidia-smi
podman run --rm --device nvidia.com/gpu=0 <image> nvidia-smi   # specific GPU

# AMD ROCm
podman run --rm --device amd.com/gpu=all <image> rocminfo

# Intel iGPU
podman run --rm --device intel.com/gpu=card0 <image> intel_gpu_top
```

The same vendor-prefixed device IDs are what the inference-lane Quadlets request.
`mios-llm-light` — the **primary** local inference engine (llama.cpp behind the
`llama-swap` proxy image on `:11450`, which also serves embeddings via
`nomic-embed-text`) — declares it directly in
`usr/share/containers/systemd/mios-llm-light.container`:

```ini
[Container]
AddDevice=nvidia.com/gpu=all
```

That one CDI reference is what lets `llama-server` offload to CUDA inside the
container; the heavy GPU lanes (`mios-llm-heavy`, SGLang on `:11441`;
`mios-llm-heavy-alt`, vLLM) consume the same CDI surface when enabled. From
there the generation/embeddings produced over the GPU flow up the AI plane —
agent-pipe (`:8640`) orchestration, MiOS-Hermes (`:8642`) tool-loop, and
pgvector (`:5432`) memory — so CDI is the bottom rung of the whole agentic stack.

## Cross-refs

- `usr/share/doc/mios/upstream/nvidia.md` — NVIDIA Container Toolkit + driver path
- `usr/share/doc/mios/upstream/looking-glass-kvmfr.md` — the VFIO-passthrough sibling of GPU delegation
- `usr/share/doc/mios/concepts/architecture.md` §Hardware acceleration / §Hardware delegation
