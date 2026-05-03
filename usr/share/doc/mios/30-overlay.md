# Repo Overlay — Repo Root === System Root

> Source: `README.md`, `ARCHITECTURE.md` §Filesystem-layout,
> `Containerfile` (`ctx` scratch stage), `INDEX.md` §1.

The 'MiOS' repo's root **is** the deployed system root. There is **no
`system_files/` directory** — that was a v1 KB fabrication. The `ctx`
scratch stage in `Containerfile` does:

```dockerfile
COPY automation/ /ctx/automation/
COPY usr/        /ctx/usr/
COPY etc/        /ctx/etc/
```

…and then `automation/08-system-files-overlay.sh` (which runs
pre-pipeline from `Containerfile`) lays these onto `/`.

## Per-directory FHS disposition

| Path | FHS character | bootc disposition | Source-of-truth in repo |
| --- | --- | --- | --- |
| `/usr` | Read-only, shareable (FHS 3.0) | Immutable composefs mount; change = new OCI image | `usr/` overlaid by `automation/08-system-files-overlay.sh` |
| `/etc` | Host-specific config | 3-way merge overlay; admin edits survive upgrades | `etc/` |
| `/var` | Mutable, persistent | Fully writable; never replaced on upgrade | Declared via `usr/lib/tmpfiles.d/mios*.conf` (LAW 2: NO-MKDIR-IN-VAR) |
| `/srv` | Data served by the system | Persistent; AI model weights, Ceph data | Declared via `usr/lib/tmpfiles.d/mios.conf` |
| `/run` | Ephemeral runtime | tmpfs; cleared at boot; never in image layers | — |
| `/home` | User homes | Persistent via `/var/home/<user>` + symlink | `usr/lib/sysusers.d/`, dotfiles staged via `/etc/skel` |

## Where to put what

| Artifact type | Repo path |
| --- | --- |
| systemd unit (vendor) | `usr/lib/systemd/system/<name>.service` |
| systemd unit (host-overridable) | `etc/systemd/system/<name>.service` |
| systemd preset | `usr/lib/systemd/system-preset/90-mios.preset` |
| Quadlet (vendor) | `usr/share/containers/systemd/<name>.container` |
| Quadlet (host-overridable) | `etc/containers/systemd/<name>.container` |
| Kernel kargs | `usr/lib/bootc/kargs.d/NN-name.toml` |
| Sysctl (vendor) | `usr/lib/sysctl.d/99-mios-hardening.conf` |
| Sysctl override | `/etc/sysctl.d/<name>.conf` |
| tmpfiles | `usr/lib/tmpfiles.d/mios*.conf` |
| sysusers | `usr/lib/sysusers.d/` |
| modprobe | `etc/modprobe.d/<name>.conf` (admin) or `usr/lib/modprobe.d/` (vendor) |
| dnf repo | `etc/yum.repos.d/<name>.repo` (upstream-contract location, exception to LAW 1) |
| SELinux modules | `usr/share/selinux/packages/mios/<name>.te` |
| Polkit rules | `usr/share/polkit-1/rules.d/` |
| AI prompt (canonical) | `usr/share/mios/ai/system.md` |
| AI prompt (host override) | `etc/mios/ai/system-prompt.md` |
| AI models catalog | `usr/share/mios/ai/v1/models.json` |
| AI MCP registry | `usr/share/mios/ai/v1/mcp.json` |
| Profile (vendor) | `usr/share/mios/profile.toml` |
| Profile (host override) | `etc/mios/profile.toml` |

## Build-time vs runtime

- **Build-time writes to `/var/`** are forbidden (LAW 2). The only
  exceptions are bind-mounted dnf cache directories, which buildkit
  doesn't bake into layers.
- **Per-user homes** are seeded via `/etc/skel/` at build, then populated
  by `systemd-sysusers` at first boot. The overlay step at
  `automation/08-system-files-overlay.sh:49-67` does this.
- The `Containerfile`'s post-overlay cleanup at the end of the main RUN
  enforces this:

  ```bash
  find /var -mindepth 1 -maxdepth 1 ! -name tmp ! -name cache -exec rm -rf {} +
  find /run -mindepth 1 -maxdepth 1 ! -name secrets -exec rm -rf {} +
  ```

## Three-layer config overlay

Every MiOS-aware config (profile.toml, env, AI prompts, sysctl, etc.) has
a three-layer overlay:

1. `~/.config/mios/<name>` — per-user (highest precedence)
2. `/etc/mios/<name>` — host/admin
3. `/usr/share/mios/<name>` — vendor defaults (lowest, immutable)

Resolved by `/etc/profile.d/mios-env.sh` for env files; by the `mios` CLI
clients for profile.toml; by the agent loader for system prompts.
