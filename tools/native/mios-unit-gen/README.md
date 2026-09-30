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
| `cockpit` | `[cockpit]` | `etc/cockpit/cockpit.conf` |
| `ipa-enroll` | `[identity.ipa]` | `etc/mios/ipa-enroll.env` |

Each mode accepts `--root DIR` and `--check`; check mode never writes.
`--toml FILE` selects an independent SSOT input for every TOML-backed mode.
`--list-projections` advertises supported modes so callers can reject stale binaries.
Run `uki-cmdline` after every karg producer. Invalid input fails before output is
written. The selectors retain every capability and the location rules retain
their conjunctions. The projection owns only the files it renders, leaving
other service drop-ins in their existing locations.

Service configuration reads the explicit defaults already present in the vendor
SSOT. Missing keys and wrong types fail before replacing an output; the renderer
does not invent a second set of defaults after a parse failure. FreeIPA values
are quoted for the Bash consumer, with shell expansion characters escaped and
control characters rejected. The OTP key is a variable name pointing to the
separate credential file; the projection carries no credential value.
Quoting follows the [Bash double-quote contract](https://www.gnu.org/software/bash/manual/html_node/Double-Quotes.html).

## Build and verify

Run inside `podman-MiOS-DEV` from `tools/native`:

```bash
cargo build -p mios-unit-gen
cargo test -p mios-unit-gen
```
