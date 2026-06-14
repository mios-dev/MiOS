<!-- AI-hint: Documentation for the rechunk tool used during the MiOS build pipeline (Phase-3 / `just rechunk`) to optimize bootc upgrade deltas by consolidating OCI layers into a deterministic 67-layer structure, minimizing data transfer when a booted MiOS host runs `bootc upgrade`.
     AI-related: mios-build-local, just-rechunk, bootc-upgrade, composefs -->
# rechunk — Day-2 Delta Optimization

## Why this matters to MiOS

MiOS is a single immutable OCI/bootc image that is *also* a local agentic AI
operating system: the whole workstation — GNOME/Wayland, GPU stacks, KVM, the
k3s/Ceph path, and the entire local agent stack (agent-pipe, MiOS-Hermes, the
inference lanes, pgvector memory) — ships as one container image. Because the
image *is* the system, every update is a `bootc upgrade` (a `git pull` for your
OS) and every regression is a `bootc rollback` (a Ctrl-Z). That lifecycle is
only pleasant if upgrades are *small*: a one-line change to a config or a single
package bump should not force the host to re-pull gigabytes.

**rechunk is the build step that makes Day-2 upgrades small.** It runs near the
end of the build pipeline (Phase-3), after the image is assembled and linted but
before it is signed and pushed, and re-lays the image's storage so that an
upgrade transfers only the layers that actually changed. Its purpose is narrow
and load-bearing: keep the bootc upgrade/rollback loop fast enough that the
operator treats OS updates as routine.

> Invoked by `just rechunk` (and Phase-3 of `mios-build-local.ps1` on the
> Windows build host) via
> `bootc-base-imagectl rechunk --max-layers 67 <src> <dst>`.
> Source of truth: `Justfile:rechunk`, `usr/share/doc/mios/guides/self-build.md`
> §Build chain.

## Project

- Repo: <https://github.com/hhd-dev/rechunk>
- This is an **upstream** tool. MiOS consumes it as-is via the
  `bootc-base-imagectl rechunk` entrypoint; nothing here is forked.

## What it does

The default OCI layer structure (one layer per `RUN` instruction) is
*correct* but not *optimal* for `bootc upgrade` deltas. rechunk
re-organizes the image into a deterministic 67-layer split where
related files (kernel modules together, NVIDIA drivers together,
desktop apps together) share a layer. The result: when a single
component changes, only that component's layer is re-pulled.

Determinism is the point — given the same inputs, rechunk produces the same
layer boundaries every time, so the byte-level diff between vN and vN+1 stays
tight and predictable across the entire MiOS image set (RAW / ISO / qcow2 /
VHDX / WSL2 are all cut from the same rechunked image).

## Effect on Day-2 deltas

| Image | Without rechunk | With rechunk |
| --- | --- | --- |
| Single-package update (e.g. firefox bump) | Re-pull the layer that contains firefox + every later layer | Re-pull just firefox's layer |
| Kernel-modules-extra rev | ~500 MB | ~50 MB |
| Tag-to-tag bytes transferred | ~2 GB typical | ~200–400 MB typical |

5–10× smaller is the documented expectation
(`usr/share/doc/mios/guides/self-build.md` — "subsequent rebuilds 5–10× faster").

## Invocation (`Justfile:rechunk`)

```bash
podman run --rm \
  --security-opt label=type:unconfined_t \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  ${LOCAL} \
  /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 \
    containers-storage:${LOCAL} \
    containers-storage:${IMAGE_NAME}:${VERSION}

podman tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest
```

`--max-layers 67` is the upstream-recommended default; any cap from 32
to 96 is reasonable.

## Where it sits in the build → upgrade lifecycle

```
podman build → bootc container lint (Law 4) → rechunk → cosign keyless sign → push to GHCR
                                                  │
                                          host: bootc upgrade → reboot
```

rechunk runs *after* the deterministic build and the final
`RUN bootc container lint` (Architectural Law 4 — fail = fail the build), and
*before* signing and push. It does not change the image's contents, only how
those contents are split into layers; the signature and the host's
`bootc upgrade` then operate on the rechunked layout.

## When NOT to rechunk

For `:dev` and `:pr-*` tags that won't be consumed by `bootc upgrade`,
skip rechunk — it adds ~30s of build time. The MiOS CI workflow
(`.github/workflows/mios-ci.yml`) only rechunks on **tag pushes** (release
builds), not on `main` / PR builds, since those iteration images are not
delivered to hosts over the bootc lifecycle.

## Cross-refs

- `usr/share/doc/mios/guides/self-build.md` — the full build chain (build →
  rechunk → cosign → GHCR → `bootc upgrade`) and where rechunk fires in each mode.
- `usr/share/doc/mios/upstream/cosign.md` — keyless signing, the step
  immediately after rechunk.
- `usr/share/doc/mios/upstream/bootc.md` — the upgrade/rollback lifecycle that
  consumes the rechunked deltas.
- `usr/share/doc/mios/upstream/composefs.md` — where the per-layer dedup also
  pays off in on-disk storage.
