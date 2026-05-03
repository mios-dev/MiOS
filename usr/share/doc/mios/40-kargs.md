# Kernel Arguments -- `usr/lib/bootc/kargs.d/`

> Source: `ENGINEERING.md` §Kargs-format, `SECURITY.md` §Kernel-boot-parameters,
> bootc upstream docs at `bootc.dev/bootc/building/kernel-arguments.html`.

## Format (LAW-enforced)

Files at `usr/lib/bootc/kargs.d/*.toml` use a flat top-level array:

```toml
kargs = ["init_on_alloc=1", "lockdown=integrity"]

# Optional architecture filter:
match-architectures = ["x86_64"]
```

**No `[kargs]` section header. No `delete` sub-key.** `bootc container
lint` rejects anything else. Files are processed lexicographically;
**earlier entries cannot be removed by later files in the same image** --
use runtime `bootc kargs --delete` for removal.

## 'MiOS' hardening kargs (00-mios.toml)

| Parameter | Active? | Purpose | Override |
| --- | :-: | --- | --- |
| `slab_nomerge` | [ok] | Prevent slab cache merging (heap isolation) | Higher-priority kargs.d file |
| `init_on_alloc=1` |  | DISABLED -- causes CUDA memory init failures | Higher-priority file (CPU-only builds only) |
| `init_on_free=1` |  | DISABLED -- same CUDA incompatibility | Higher-priority file |
| `page_alloc.shuffle=1` |  | DISABLED -- NVIDIA driver instability | Higher-priority file |
| `randomize_kstack_offset=on` | [ok] | Per-syscall kernel stack randomization | `=off` |
| `pti=on` | [ok] | Page Table Isolation (Meltdown) | `=off` (not recommended) |
| `vsyscall=none` | [ok] | Disable legacy vsyscall table | `=emulate` |
| `iommu=pt` | [ok] | IOMMU passthrough for VFIO | Required for GPU passthrough |
| `amd_iommu=on` / `intel_iommu=on` | [ok] | Enable IOMMU | Required for VFIO |
| `nvidia-drm.modeset=1` | [ok] | NVIDIA DRM modesetting (Wayland) | Required for GNOME Wayland |
| `lockdown=integrity` | [ok] | Kernel lockdown integrity mode | Remove to allow unsigned modules |
| `spectre_v2=on` | [ok] | Spectre v2 mitigation | Performance cost ~2-5% |
| `spec_store_bypass_disable=on` | [ok] | Spectre v4 SSB mitigation | ~1-2% |
| `l1tf=full,force` | [ok] | L1TF mitigation | Affects HyperThreading |
| `gather_data_sampling=force` | [ok] | GDS/Downfall mitigation | Intel-specific |

**Note**: 'MiOS' uses `lockdown=integrity` (NOT `confidentiality`). The v1
KB had this wrong.

## Day-2 changes

- **Image-time** (preferred): drop a higher-priority TOML, rebuild,
  `bootc upgrade`. Lexicographic precedence means `99-myhost.toml` wins
  over `00-mios.toml`.
- **Runtime**: `sudo bootc kargs edit` opens an editor on the active
  cmdline; `sudo bootc kargs --append` and `--delete` for one-shot edits.
  These persist across upgrades because they're stored as machine-local
  state separate from the image's `kargs.d`.

## VFIO GPU passthrough kargs

For VFIO passthrough to a guest VM, supplement with:

```toml
kargs = [
  "intel_iommu=on",      # or "amd_iommu=on"
  "iommu=pt",
  "vfio-pci.ids=10de:2204,10de:1aef"   # vendor:device -- runtime-detected by automation/34-gpu-detect.sh
]
```

Bind via `etc/modprobe.d/vfio.conf`:

```
options vfio-pci ids=10de:2204,10de:1aef
softdep nvidia pre: vfio-pci
softdep nouveau pre: vfio-pci
```

## CPU isolation for VM workloads

```toml
kargs = [
  "isolcpus=2-7",
  "nohz_full=2-7",
  "rcu_nocbs=2-7"
]
```

Drop these in a dedicated higher-priority file (e.g.
`50-mios-cpu-isolation.toml`) so a non-passthrough host can override
with `99-disable-isolation.toml`.

## Hyper-V Plymouth fix

On Hyper-V Gen2 with `hyperv_fb`, Plymouth animations cause a visible
boot hang. Drop `usr/lib/bootc/kargs.d/05-mios-plymouth.toml`:

```toml
kargs = ["plymouth.enable=0", "rd.plymouth=0"]
match-architectures = ["x86_64"]
```

## FIPS

```toml
# usr/lib/bootc/kargs.d/01-mios-fips.toml
kargs = ["fips=1"]
```

Plus bake `update-crypto-policies --no-reload --set FIPS` and
`crypto-policies-scripts` into the image (`packages-base` already
includes the latter).

## Verifying

```bash
sudo bootc status --format=json | jq '.spec.bootOrder, .status.booted.kargs'
cat /proc/cmdline
ls /usr/lib/bootc/kargs.d/
```

The `mios_kargs_validate` function tool (defined in
`/usr/lib/mios/tools/responses-api/mios_kargs_validate.json`) can
validate a TOML fragment for schema compliance before you commit it.
