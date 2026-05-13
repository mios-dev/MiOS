<!-- FHS: /usr/share/mios/docs/day-n/SELF-REPLICATION.md -->

# Day-1 → Day-N: The Self-Replication Loop

## Day-1: First Self-Built MiOS

MiOS-DEV's running state IS the build input. The Justfile target
`build` calls ~48 phase scripts in sequence. The output is a bootc
OCI image that, when booted, is functionally identical to the
MiOS-DEV that produced it (modulo machine-local state in `/etc` and
`/var`).

## Day-N: Continuous Loop

Each generation builds the next. The build is reproducible to the
extent that:

- The base ucore-hci tag (`stable-nvidia`) is pinned by digest in
  the Containerfile.
- All package versions come from a snapshotted Fedora Rawhide mirror
  (recorded in `etc/mios/rawhide-snapshot.toml`).
- The Justfile is committed; phase script SHAs are recorded in the
  manifest.

## Generation Tagging

```
ghcr.io/mios-dev/mios:gen-<N>
ghcr.io/mios-dev/mios:latest    # = gen-<N> for the latest signed gen
```

`bootc upgrade` always points at `:latest`. Specific generations are
referenced by digest for rollback.

## What "Self-Replicating" Excludes

- Machine-local state (`/etc`, `/var`, `/var/home/*`) does not carry
  over — by design (bootc semantics).
- The Containerfile must be cleanly buildable from a stock ucore-hci
  base; MiOS doesn't "embed" itself in the new image except as
  source files in `/usr/share/mios/src/` (a committed snapshot).

## The Day-N loop in five commands

```sh
# 1. Pull or refresh the canonical mios source view.
mios repo use main
git fetch --all && git rebase origin/main

# 2. Run all invariants. Refuses to continue on any failure.
mios doctor

# 3. Build the next image. Justfile drives ~48 phase scripts.
mios build              # -> out/mios-<gen>.oci-archive

# 4. Sign and push.
just sign push          # cosign keyless via OIDC

# 5. Upgrade the running MiOS-DEV to its own output.
sudo bootc upgrade
sudo systemctl reboot
```

After reboot, the now-newer MiOS-DEV is ready to build the *next*
next gen. The loop has no terminus.

## Reproducibility ledger

Each generation publishes alongside its image:

- `mios-<gen>.containerfile-digest`  — sha256 of the Containerfile.
- `mios-<gen>.packages-lock`         — pinned NVRs.
- `mios-<gen>.kargs-effective`       — merged kargs.d output.
- `mios-<gen>.invariants-passed`     — `mios doctor` JSON report.
- `mios-<gen>.cosign.sig` + `.cert`  — cosign keyless artifacts.

A second host, given identical inputs, MUST produce a bit-identical
ostree commit (modulo timestamps in metadata). Drift is treated as a
build bug.
