# rechunk — Day-2 Delta Optimization

> Used by `just rechunk` (and the `mios-build-local.ps1` Phase-3) via
> `bootc-base-imagectl rechunk --max-layers 67 <src> <dst>`.
> Source: `Justfile:rechunk`, `usr/share/doc/mios/guides/self-build.md` §Build-chain.

## Project

- Repo: <https://github.com/hhd-dev/rechunk>

## What it does

The default OCI layer structure (one layer per `RUN` instruction) is
*correct* but not *optimal* for `bootc upgrade` deltas. rechunk
re-organizes the image into a deterministic 67-layer split where
related files (kernel modules together, NVIDIA drivers together,
desktop apps together) share a layer. The result: when a single
component changes, only that component's layer is re-pulled.

## Effect on Day-2 deltas

| Image | Without rechunk | With rechunk |
| --- | --- | --- |
| Single-package update (e.g. firefox bump) | Re-pull the layer that contains firefox + every later layer | Re-pull just firefox's layer |
| Kernel-modules-extra rev | ~500 MB | ~50 MB |
| Tag-to-tag bytes transferred | ~2 GB typical | ~200–400 MB typical |

5–10× smaller is the documented expectation (`usr/share/doc/mios/guides/self-build.md`).

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

## When NOT to rechunk

For `:dev` and `:pr-*` tags that won't be consumed by `bootc upgrade`,
skip rechunk — it adds ~30s of build time. The MiOS CI workflow only
rechunks on tag pushes (release builds), not on `main` PR builds.

## Cross-refs

- `usr/share/doc/mios/60-ci-signing.md`
- `usr/share/doc/mios/50-orchestrators.md`
- `usr/share/doc/mios/upstream/composefs.md` (where the per-layer dedup actually pays off in storage too)
