# MiOS hwcaps — x86-64 microarchitecture optimization

> Status: configurable, default off (`[hwcaps].level = "v1"`).
> SSOT: `[hwcaps]` table in `/usr/share/mios/mios.toml`.

## What this is

Modern x86-64 CPUs implement instruction-set extensions (SSE3, AVX, AVX2,
AVX-512, BMI, FMA, …) that didn't exist in the original AMD64 ISA. Software
compiled with `-march=x86-64` (the baseline) cannot use those extensions
even on capable hardware — the compiler is forbidden from emitting the
relevant opcodes.

Fedora ships **glibc-hwcaps** subpackages that supply alternative
`/usr/lib64/glibc-hwcaps/x86-64-vN/<lib>.so` files compiled against the
higher microarch ABIs. The dynamic linker (`ld.so`) auto-selects them at
process start when the host CPU advertises the matching capability bits
via `AT_HWCAP` / `AT_HWCAP2` in the auxiliary vector. No application
changes; transparent perf uplift.

## Microarchitecture levels

The x86-64 psABI committee defined four levels:

| Level | ISA bits added | Hardware floor |
|-------|----------------|----------------|
| **v1** | baseline AMD64 (CMOV, CX8, FPU, FXSR, MMX, SCE, SSE, SSE2) | every x86-64 CPU since 2003 |
| **v2** | SSE3 + SSSE3 + SSE4.1 + SSE4.2 + POPCNT | Intel Nehalem 2008+, AMD Barcelona 2007+ |
| **v3** | AVX + AVX2 + BMI1 + BMI2 + FMA + F16C + LZCNT + MOVBE | Intel Haswell 2013+, AMD Excavator 2015+, **AMD Zen 1 2017+** |
| **v4** | AVX-512 (foundation + DQ + CD + BW + VL) | Intel Skylake-X 2017+, Ice Lake 2019+, **AMD Zen 4 2022+** |

### AMD Zen mapping

| AMD generation | Family | Highest hwcaps level |
|---|---|---|
| Zen 1 (Ryzen 1000) | 2017 | v3 |
| Zen+ (Ryzen 2000) | 2018 | v3 |
| Zen 2 (Ryzen 3000) | 2019 | v3 |
| Zen 3 (Ryzen 5000) | 2020 | v3 |
| Zen 4 (Ryzen 7000) | 2022 | **v4** |
| Zen 5 (Ryzen 9000) | 2024 | **v4** (full AVX-512 width, not the half-width path Zen 4 had) |

The dev-host the `mios.toml` `[hwcaps]` table was designed against is a
Ryzen 9 9950X3D (Zen 5) → both v3 and v4 are valid choices. v4 is the
maximum.

## What MiOS does today (Day-N current)

`automation/lib/packages.sh` reads `[hwcaps].level` and adds the matching
section (`glibc-hwcaps-v3` or `glibc-hwcaps-v4`) to the dnf install list
when the level is `v3` or `v4`. Empty / `v1` skips both sections — the
image stays universal and slightly smaller.

```toml
[hwcaps]
level = "v3"   # or "v4" on Zen 4 / Zen 5 / Ice Lake+ hosts
```

The relevant Fedora packages (`glibc-hwcaps-x86-64-v3`,
`glibc-hwcaps-x86-64-v4`) MAY not be present in every Fedora release —
upstream packaging has been uneven. `--skip-unavailable` + `--skip-broken`
in the dnf install handles the gap silently.

When the packages do install, every glibc-aware process automatically
benefits — no application changes, no environment variables, no recompile.

## Storage cost

| Component | Approx. size |
|-----------|-----:|
| `glibc-hwcaps-x86-64-v3` | ~12 MB |
| `glibc-hwcaps-x86-64-v4` | ~14 MB |
| Both | ~26 MB combined |

Per-glibc-update churn is real but bounded — the hwcaps subpackages
re-ship on every glibc bump. Within a build, both v3 and v4 can coexist;
ld.so picks the highest level the CPU supports.

## Runtime cost

Zero on the hot path. `ld.so` resolves the loader once per process at
`execve()` time. After resolution there's no branching, no dispatching;
the picked `.so` IS the `.so` for the lifetime of the process.

## Native-rebuild track (Day-N+1, currently `[hwcaps].native_rebuild = false`)

The hwcaps mechanism only covers libraries that Fedora packagers chose to
multi-build. For the rest of MiOS's hot path (kernel, openssl, zstd,
ffmpeg, mesa-vulkan-drivers, the video / image / inference stack), getting
v3/v4 perf requires recompiling them ourselves with `-march=x86-64-v3` or
`-march=x86-64-v4` (or AMD-specific `-march=znver3` / `-march=znver4` /
`-march=znver5` for the dev-host CPU family).

This is the **native-rebuild track**. When `[hwcaps].native_rebuild = true`,
a future `automation/45-hwcaps-rebuild.sh` would:

1. Spin up a `mock` chroot with the matching CFLAGS / RUSTFLAGS.
2. Iterate the hot-path package set declared in
   `[hwcaps].native_rebuild_packages`.
3. Pull each upstream srpm.
4. Rebuild against `-march=znver{4|5}` or `-march=x86-64-v{3|4}`.
5. Drop the rebuilt RPMs into `/var/lib/mios/rebuilds/` and
   `dnf install --setopt=allow_vendor_change` them on top of the
   Fedora baseline.
6. Snapshot the result so it's deterministic and auditable.

Open questions before native-rebuild flips on:

- **Signing**: rebuilt RPMs need their own signing key. Either reuse the
  MiOS MOK or mint a separate `mios-rebuild` key with a documented trust
  delegation. Fits LAW 4 / sealed-image-track adjacent thinking.
- **CI**: rebuilds blow up CI build time by 2-4x. Probably need a
  dedicated `mios-rebuild` Forgejo Runner with cached `mock` chroots.
- **Storage**: ~200 MB for the rebuilt RPMs cached under `/var/lib/mios/`.
  Already accounted for in [Audit 5 — bound-images.d coverage].
- **Auditability**: each rebuild gets an SBOM entry tagged
  `mios-rebuild:znver5` so downstream cross-compile / cross-arch users
  see exactly which RPMs are vendor-baseline vs MiOS-rebuilt.

## How operators opt in

For glibc-hwcaps (Day-N, ready now):

```toml
# /etc/mios/mios.toml
[hwcaps]
level = "v3"   # or "v4"

[packages]
sections = [..., "glibc-hwcaps-v3"]   # add to your existing list
```

Then `sudo just build` (or trigger CI). Image rebuilds with the matching
hwcaps subpackage; on next boot, `ld.so --list-diagnostics | grep hwcap`
shows the loader picked it up.

For native-rebuild (Day-N+1, future):

```toml
[hwcaps]
level = "v4"
native_rebuild = true
native_rebuild_packages = [
    "kernel",
    "openssl",
    "zstd",
    "ffmpeg",
    "mesa-vulkan-drivers",
]
```

Build infrastructure for native-rebuild ships with `automation/45-hwcaps-
rebuild.sh` (TBD). Postcheck rule LAW 7 candidate: validate that
declared rebuild targets are reproducible (rebuild twice from the same
srpm, byte-compare).

## Verification on a running host

```bash
# Did the hwcaps loader pick a higher level?
ld.so --list-diagnostics 2>/dev/null | grep -E '(hwcap|x86_64-v[234])' | head

# Which subpackage is installed?
rpm -q glibc-hwcaps-x86-64-v3 glibc-hwcaps-x86-64-v4 2>&1 | grep -v 'not installed'

# CPU's actual highest supported level (informational):
ld.so --help | grep -A2 'subdirectories of glibc-hwcaps' | tail -5
```

## See also

- [psABI x86-64 microarchitecture levels](https://gitlab.com/x86-psABIs/x86-64-ABI)
- [Fedora Change: Glibc Hardware Capabilities for x86-64](https://fedoraproject.org/wiki/Changes/Glibc_x86-64-v3)
  (rejected for F39; subpackages still ship in Fedora as opt-in)
- [secureblue x86-64-v3 derivative](https://github.com/secureblue/secureblue) —
  one of the few projects shipping a -v3 image variant; useful reference
  for the native-rebuild track
- `/usr/share/mios/mios.toml` — `[hwcaps]` table SSOT
- `/usr/share/doc/mios/reference/bootc-comparison.md` — gap #1 (sealed
  images) is adjacent: hwcaps + sealed-image both are "transparent
  uplift" tracks
