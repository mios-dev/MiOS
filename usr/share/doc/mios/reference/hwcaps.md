<!-- AI-hint: Documentation for x86-64 microarchitecture optimization levels (v1-v4) used to determine which glibc-hwcaps packages to include in the build via the [hwcaps] table in mios.toml; explains the transparent per-process perf uplift the loader gives MiOS's hot path (inference lanes, media, hashing), the storage/runtime tradeoffs, and the future native-rebuild track.
     AI-related: /usr/share/mios/mios.toml, /etc/mios/mios.toml, automation/lib/packages.sh, mios-rebuild, /usr/share/doc/mios/reference/bootc-comparison.md -->
# MiOS hwcaps — x86-64 microarchitecture optimization

> Status: configurable, default off (`[hwcaps].level = "v1"`).
> SSOT: `[hwcaps]` table in `/usr/share/mios/mios.toml`.
> Audience: operators and build engineers tuning image performance for a known CPU.

## Why this exists (purpose within MiOS)

MiOS is one image built two ways at once: an immutable, bootc/OCI-shaped Fedora
workstation *and* a local, self-replicating agentic AI OS. The same image that
ships GNOME/Wayland, GPU wiring (NVIDIA + ROCm + iGPU via CDI), KVM/libvirt
passthrough, and a one-node k3s+Ceph path also runs a full local inference and
agent stack — the `mios-llm-light` primary lane (:11450, llama.cpp behind the
`llama-swap` proxy, serving everyday models, the `mios-opencode` coder model, and
`nomic-embed-text` embeddings), the gated heavy GPU lanes (`mios-llm-heavy` SGLang
:11441, `mios-llm-heavy-alt` vLLM :11440), the agent-pipe orchestrator, and a
PostgreSQL+pgvector agent memory.

Much of that workload is SIMD-heavy: BLAS and numeric kernels under inference,
`libvips`/`ffmpeg` media transcoding, blake3 hashing, JSON/YAML parsing. The
default `-march=x86-64` baseline leaves the newer instruction-set extensions on
modern CPUs unused. **hwcaps is the cheapest lever MiOS has to recover that
performance: a transparent, per-process perf uplift with no application changes
and zero runtime branching.** Because MiOS is a single rebuildable OCI image, the
choice is made once at build time (via one SSOT key) and then reproduced
identically on every host that pulls the ref — fitting the same build-pipeline →
image → bootc-lifecycle discipline as everything else in the system.

This doc explains what the mechanism is, how MiOS uses it today, the storage and
runtime costs, and the future **native-rebuild track** for the hot-path packages
Fedora doesn't multi-build.

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

These libraries are **purely additive** — they never replace the baseline v1
`.so` files. Older or cross-arch binaries keep working, and a CPU that lacks the
capability bits simply falls back to the baseline path.

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
when the level is `v3` or `v4`. The default shipped in the vendor
`mios.toml` is `v1`, which skips both sections — the image stays universal
and slightly smaller, with the widest CPU compatibility.

```toml
[hwcaps]
level = "v1"                     # vendor default; set "v3"/"v4" on capable hosts
ld_so_hwcaps_autoselect = true   # let ld.so pick the highest supported .so at exec
native_rebuild = false           # future track (see below)
```

`ld_so_hwcaps_autoselect = true` is the default: it lets `ld.so` select the
highest level the CPU supports at process start. Setting it `false` forces the
baseline-only paths even when v3/v4 `.so` files are present — it exists for
benchmarking and regression isolation, not normal operation.

The relevant Fedora packages (`glibc-hwcaps-x86-64-v3`,
`glibc-hwcaps-x86-64-v4`) MAY not be present in every Fedora release —
upstream packaging cadence has been uneven. `--skip-unavailable` +
`--skip-broken` in the dnf install handles the gap silently, so a missing
subpackage degrades to baseline rather than failing the build.

When the packages do install, every glibc-aware process automatically
benefits — no application changes, no environment variables, no recompile.
On the MiOS hot path that means the inference lanes, media transcoding, and
hashing pick up the uplift for free.

## Storage cost

| Component | Approx. size |
|-----------|-----:|
| `glibc-hwcaps-x86-64-v3` | ~12 MB |
| `glibc-hwcaps-x86-64-v4` | ~14 MB |
| Both | ~26 MB combined |

Per-glibc-update churn is real but bounded — the hwcaps subpackages
re-ship on every glibc bump. Within a build, both v3 and v4 can coexist;
`ld.so` picks the highest level the CPU supports.

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

1. Spin up a `mock` chroot (or COPR) with the matching CFLAGS / RUSTFLAGS.
2. Iterate the hot-path package set (proposed `[hwcaps].native_rebuild_packages`).
3. Pull each upstream srpm.
4. Rebuild against `-march=znver{4|5}` or `-march=x86-64-v{3|4}`.
5. Drop the rebuilt RPMs into `/var/lib/mios/rebuilds/` and
   `dnf install --setopt=allow_vendor_change` them on top of the
   Fedora baseline.
6. Snapshot the result so it's deterministic and auditable.

Open questions before native-rebuild flips on:

- **Signing**: rebuilt RPMs need their own signing key. Either reuse the
  MiOS MOK or mint a separate `mios-rebuild` key with a documented trust
  delegation. Fits LAW 4 (BOOTC-CONTAINER-LINT) / sealed-image-track adjacent
  thinking — the same key would later gate the `[security].composefs_mode`
  verity boot path.
- **CI**: rebuilds blow up CI build time by 2-4x. Probably need a
  dedicated `mios-rebuild` Forgejo Runner with cached `mock` chroots.
- **Storage**: ~200 MB for the rebuilt RPMs cached under `/var/lib/mios/`
  (declared via tmpfiles per LAW 2 — never `mkdir`-ed at build time).
- **Auditability**: each rebuild gets an SBOM entry tagged
  `mios-rebuild:znver5` so downstream cross-compile / cross-arch users
  see exactly which RPMs are vendor-baseline vs MiOS-rebuilt.

## How operators opt in

For glibc-hwcaps (Day-N, ready now), edit the SSOT and rebuild:

```toml
# /etc/mios/mios.toml  (admin override layer)
[hwcaps]
level = "v3"   # or "v4" on Zen 4 / Zen 5 / Ice Lake+ hosts

[packages]
sections = [..., "glibc-hwcaps-v3"]   # add to your existing list
```

Then `sudo just build` (or trigger CI). The image rebuilds with the matching
hwcaps subpackage; on next boot, `ld.so --list-diagnostics | grep hwcap`
shows the loader picked it up. Because the choice lives in `mios.toml`, it
flows through the same three-layer override (per-user `~/.config/mios/` <
host `/etc/mios/` < vendor `/usr/share/mios/`) as every other tunable, and
the rebuilt image is reproduced identically on every host that pulls the ref.

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
rebuild.sh` (TBD; the `native_rebuild_packages` key is not yet defined in the
vendor `mios.toml`). Postcheck rule LAW 4 candidate extension: validate that
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
- `/usr/share/mios/mios.toml` — `[hwcaps]` table SSOT (and the parallel
  `[packages.glibc-hwcaps-v3]` / `[packages.glibc-hwcaps-v4]` sections)
- `/usr/share/doc/mios/reference/bootc-comparison.md` — the sealed-image gap
  is adjacent: hwcaps + sealed-image are both "transparent uplift / hardening"
  tracks that share the eventual `mios-rebuild` signing key
