<!-- AI-hint: The numbered build pipeline and the Law-6 root Quadlet exceptions, both derived from mios.toml so they cannot go stale. -->

# The build pipeline

<!-- MIOS-GEN:boilerplate:what-mios-is -->
MiOS is one thing built two ways at once: an immutable, `bootc`/OCI-shaped
Fedora workstation -- the whole OS is a single container image, so `bootc
upgrade` behaves like a `git pull` and `bootc rollback` like a Ctrl-Z -- that
is *also* a local, self-hosted, agentic AI operating system.

<!-- derived from usr/share/mios/mios.toml [docs.boilerplate].what-mios-is -->
<!-- /MIOS-GEN:boilerplate:what-mios-is -->

The image is built by a single `Containerfile` that runs every script in
`automation/NN-*.sh` in numeric order. Each script does one thing; the numeric
prefix *is* the execution order. To add a build step you drop a new file next to
its peers — there is no central dispatcher to thread it through.

Two columns below are worth reading carefully:

- **Fatal** — whether a non-zero exit from that phase stops the bake. A
  non-fatal phase is allowed to fail on a host that cannot satisfy it (no GPU,
  no network) without failing the image.
- **Applies** — `containerfile` phases are invoked directly by the
  `Containerfile`; the rest run through `automation/build.sh`.

<!-- MIOS-GEN:pipeline -->
| # | Phase | Script | Fatal | Applies |
|---|---|---|---|---|

<!-- derived from usr/share/mios/mios.toml [build.phases].list (0 phases) -->
<!-- /MIOS-GEN:pipeline -->

## Root Quadlet exceptions (Law 6)

Law 6 (UNPRIVILEGED-QUADLETS) requires every Quadlet to declare `User=`,
`Group=` and `Delegate=yes`. The units below are the sanctioned exceptions,
almost all because the upstream image they run insists on uid 0. The list is
registry data, not prose: it is derived from the SSOT, so a unit cannot quietly
join it by editing a doc.

<!-- MIOS-GEN:root-exceptions -->
| Quadlet | Runs as root because |
|---|---|

<!-- derived from usr/share/mios/mios.toml [security.privileged_quadlets].root -->
<!-- /MIOS-GEN:root-exceptions -->

## Cross-refs

- `usr/share/doc/mios/reference/ports-and-laws.md` — the port allocations and the full law registry.
- `usr/share/doc/mios/guides/engineering.md` — the build-pipeline and shell rules in prose.
- `automation/98-drift-checks.sh` — the fitness functions each law is enforced by.
