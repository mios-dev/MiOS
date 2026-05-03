# Container Device Interface (CDI)

> Used by 'MiOS' as the universal layer for NVIDIA, AMD ROCm/KFD, and
> Intel iGPU passthrough into containers. Specs at `/var/run/cdi/`,
> admin overrides at `/etc/cdi/`, declared in
> `usr/lib/tmpfiles.d/mios-gpu.conf`. Source:
> `ARCHITECTURE.md` §Hardware-acceleration.

## Project

- Spec: <https://github.com/cncf-tags/container-device-interface>
- Status: vendor-agnostic CNCF tag; supersedes per-vendor runtime hooks

## Why CDI replaces vendor hooks

Pre-CDI, NVIDIA used `nvidia-container-runtime` as a special OCI hook,
AMD used a different hook, and Intel had no clean story. CDI lets the
vendor declare what their device exposes (kernel modules, device nodes,
libs to bind-mount, env vars) once, in YAML, and any CDI-aware runtime
(podman, containerd, CRI-O) handles the rest.

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

## 'MiOS' detection flow

1. `automation/34-gpu-detect.sh` runs at first boot, writes
   `/run/mios/gpu-passthrough.status`
2. A systemd one-shot calls `nvidia-ctk cdi generate
   --output=/var/run/cdi/nvidia.yaml` on hosts with NVIDIA hardware
3. Admin overrides land in `/etc/cdi/` (per-host pinning, e.g.
   "GPU 0 is reserved for the LLM workload, GPU 1 for VFIO passthrough")
4. `usr/lib/tmpfiles.d/mios-gpu.conf` ensures `/var/run/cdi/` and
   `/etc/cdi/` exist on every boot (LAW 2 NO-MKDIR-IN-VAR)

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

The same device IDs are visible to LocalAI's Quadlet spec at
`etc/containers/systemd/mios-ai.container`, which assigns the host's
preferred GPU to the inference workload.

## Cross-refs

- `usr/share/doc/mios/upstream/nvidia.md`
- `usr/share/doc/mios/upstream/looking-glass-kvmfr.md`
- `usr/share/doc/mios/40-kargs.md` (VFIO kargs)
