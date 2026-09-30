<!-- AI-hint: MiOS architectural documentation: mios-unit-gen.
     AI-related: mios-unit-gen -->

# mios-unit-gen

One Rust component renders systemd units and the related deployment projections.
`src/lib.rs` owns rendering and comparison; the CLI and `miosd` use that library.

## Systemd units

`mios-unit-gen --list` lists declared units. `--render UNIT` emits one unit.
`--check` compares `[units.*]` with `usr/lib/systemd/system/`, enforcing the
shrink-only `[unit_projection].drift` register. Tests render from the SSOT;
there is no golden copy of the shipped unit tree to refresh.

## Deployment projections

| Mode | Source | Output |
|---|---|---|
| `blade-dropins` | `[blade.requires]` | Capability conditions, k3s selectors and tolerations, and Pacemaker rules in `usr/share/mios/dropins/` |
| `blade-karg` | `[blade].type` and `[blade.archetypes]` | `usr/lib/bootc/kargs.d/05-mios-blade.toml` |
| `uki-cmdline` | Ordered `usr/lib/bootc/kargs.d/*.toml` | `usr/lib/kernel/cmdline` |

Each mode accepts `--root DIR` and `--check`; check mode never writes.
`--toml FILE` selects an independent SSOT input for the blade modes.
`--list-projections` advertises supported modes so callers can reject stale binaries.
Run `uki-cmdline` after every karg producer. Invalid input fails before output is
written. The selectors retain every capability and the location rules retain
their conjunctions. The projection owns only the files it renders, leaving
other service drop-ins in their existing locations.

## Build and verify

Run inside `podman-MiOS-DEV` from `tools/native`:

```bash
cargo build -p mios-unit-gen
cargo test -p mios-unit-gen
```
