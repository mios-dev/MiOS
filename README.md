# 'MiOS'

An immutable, container-image-shaped Linux workstation that boots like an OS,
upgrades like a `git pull`, and rolls back like a Ctrl-Z. It's Fedora
underneath, with a curated stack on top for people who actually use their
machines for AI, virtualization, and clusters — not just spreadsheets.

The default ref:

```
ghcr.io/mios-dev/mios:latest
```

If you've got a Fedora-bootc-compatible host (or a Hyper-V VHDX, ISO, qcow2,
or WSL2 distro you can run), you can be on 'MiOS' in the time it takes the
network to pull the image.

---

## Why bother

A normal distro evolves like a Jenga tower: every package update is a small
prayer, every clean reinstall is a weekend. 'MiOS' is the opposite — the
whole OS is one OCI image. You upgrade it the way you'd upgrade a container.
If something breaks, `bootc rollback` and you're back where you started, with
no "I sure hope `dnf` finishes" in the middle.

What you actually get out of the box:

- **GNOME 50 on Wayland** (the desktop), plus Phosh as a tablet-style
  fallback for portrait / RDP scenarios.
- **NVIDIA + AMD ROCm + Intel iGPU**, all wired up via CDI so containers can
  see the hardware without you fighting `--device` flags.
- **KVM/QEMU + libvirt + Looking Glass B7** baked into the image, with
  VFIO-PCI passthrough kargs already staged. Hand a discrete GPU to a
  Windows VM and game on it.
- **k3s + Ceph** for when you want to grow the box into a one-node cluster
  without re-imaging.
- **Local AI surface**, OpenAI-compatible at `http://localhost:8080/v1`. Every
  agent and tool on the system targets that one endpoint, so your Cursor,
  Cline, Gemini, and Claude Code installs all talk to the same brain.
- **Real security defaults**: SELinux enforcing, fapolicyd deny-by-default,
  USBGuard, CrowdSec sovereign-mode IPS, kernel-lockdown integrity, MOK-
  signed kernel modules. Not the security-theater kind.

---

## The 30-second elevator pitch for engineers

It's [Universal Blue's `ucore-hci`](https://github.com/ublue-os/ucore) (which
is itself Fedora CoreOS + uCore + HCI tooling) plus a deliberate workstation
layer on top. The whole image is `bootc`-managed — meaning `/usr` is a
read-only composefs mount, `/etc` gets a 3-way merge across upgrades, and
`/var` survives everything. New release? `bootc upgrade`. Bad release?
`bootc rollback`. No more "the package manager left my system in a state."

Think of it as a workstation flavor of CoreOS / Silverblue with the
hyperconverged bits of Talos / openSUSE MicroOS, except it's still a
day-to-day desktop you can ship code from.

---

## Try it

### Already on a Fedora-bootc-compatible host

```bash
bootc switch ghcr.io/mios-dev/mios:latest
sudo systemctl reboot
```

### From scratch, on Windows

```powershell
# One-liner from PowerShell (admin):
irm https://raw.githubusercontent.com/MiOS-DEV/MiOS/main/Get-MiOS.ps1 | iex
```

That clones the repo, runs the preflight check, then hands you off to the
local builder. You'll be prompted for a username, password, and hostname.
The Windows installer drops the result as a WSL2 distro, a Hyper-V VHDX, an
Anaconda installer ISO, and a qcow2 — pick whichever fits.

### From scratch, on Linux

```bash
git clone https://github.com/mios-dev/MiOS.git && cd MiOS
just preflight
just build
just iso       # or: just raw / just qcow2 / just vhdx / just wsl2
```

`just --list` shows every target. `Justfile` is the source of truth for the
Linux side; `mios-build-local.ps1` is the Windows equivalent.

---

## How it's actually structured

Most distros hide their layout behind a package manager. 'MiOS' doesn't — the
**repo root is the deployed system root**. Browse `usr/`, `etc/`, `srv/`,
`var/` here in GitHub and you're looking at exactly where those files land
on a booted system. There's no `system_files/` indirection, no Ansible
playbook materializing things into place. What you see is what gets baked.

The build pipeline is just a `Containerfile` that runs every script in
`automation/[NN]-*.sh` in numeric order. Each script does one thing
(install packages, configure SELinux, render the UKI, generate CDI specs,
etc.) and the numeric prefix encodes execution order. Add a new step? Drop
a new `45-myfeature.sh` next to its peers.

If you want to know what makes a package show up in the image, check
[`usr/share/mios/PACKAGES.md`](usr/share/mios/PACKAGES.md) — it's the single
source of truth, parsed at build time. Want to know what kernel arguments
ship? They're in [`usr/lib/bootc/kargs.d/`](usr/lib/bootc/kargs.d/).

---

## The user-facing knobs

The whole user side is one file:

```
~/.config/mios/mios.toml
```

That's where you set your preferred username, hostname, base image, AI
model, Flatpaks to install at first boot, and any free-form environment
variables you want exported on login. Everything else inherits from the
vendor defaults at `/usr/share/mios/env.defaults`.

```toml
[user]
name     = "you"
hostname = "you-laptop"

[ai]
model = "qwen2.5-coder:14b"

[flatpaks]
install = [
  "com.spotify.Client",
  "org.mozilla.firefox",
]

[env]
EDITOR = "nvim"
```

Run `just init-user-space` to seed it from the vendor template; `just edit`
to open it in `$EDITOR`; `just show-env` to see the resolved values.

---

## The architectural laws (the boring but load-bearing bits)

These are the rules every contribution has to obey. They're enforced by
build-time lint and by `automation/99-postcheck.sh`:

1. **USR-OVER-ETC** — static config lives in `/usr/lib/<component>.d/`.
   `/etc/` is for admin overrides only.
2. **NO-MKDIR-IN-VAR** — every `/var/` path is declared via
   `usr/lib/tmpfiles.d/*.conf`. Never written at build time.
3. **BOUND-IMAGES** — every Quadlet image is symlinked into
   `/usr/lib/bootc/bound-images.d/` so it ships *with* the host.
4. **BOOTC-CONTAINER-LINT** — every build ends with `bootc container lint`.
   Fail the lint, fail the build.
5. **UNIFIED-AI-REDIRECTS** — every agent and tool targets `MIOS_AI_ENDPOINT`
   (`http://localhost:8080/v1`). No vendor-hardcoded URLs.
6. **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`,
   `Delegate=yes`. Documented exceptions: `mios-ceph` and `mios-k3s`
   (rationale in their headers).

If you want the deeper dive: [`INDEX.md`](INDEX.md) is the architectural
contract, [`ARCHITECTURE.md`](ARCHITECTURE.md) is the layout, and
[`ENGINEERING.md`](ENGINEERING.md) is the build-pipeline rules.

---

## Where things live

| Document | What's in it |
|---|---|
| [`INDEX.md`](INDEX.md) | Architectural laws + API surface (the contract). |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Filesystem and hardware layout. |
| [`ENGINEERING.md`](ENGINEERING.md) | Build pipeline + shell conventions. |
| [`SECURITY.md`](SECURITY.md) | Hardening kargs and posture. |
| [`SELF-BUILD.md`](SELF-BUILD.md) | Build modes (CI, Linux, Windows, self-build). |
| [`DEPLOY.md`](DEPLOY.md) | bootc + Day-2 lifecycle. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution conventions. |
| [`API.md`](API.md) | OpenAI-compatible AI surface. |
| [`SOURCES.md`](SOURCES.md) | Every external reference, every upstream link. |

For LLMs and AI agents arriving at the repo:
[`llms.txt`](llms.txt) and [`llms-full.txt`](llms-full.txt) are the
machine-readable index. [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md),
and [`GEMINI.md`](GEMINI.md) are the per-tool entry points. They all
ultimately defer to `/usr/share/mios/ai/system.md` once the OS is running.

---

## Status

'MiOS' is in active development at `v0.2.x`. The build pipeline is stable,
the image lints clean against `bootc container lint`, and the WSL2 + ISO
paths are battle-tested through several weeks of daily-driving. The bare-
metal install path works but expects you to know what `bootc switch` does
before you run it.

Open issues + roadmap live on the GitHub side. PRs welcome — read
[`CONTRIBUTING.md`](CONTRIBUTING.md) before you push.

---

## License

Apache-2.0. Component licenses for every shipped piece are catalogued in
[`LICENSES.md`](LICENSES.md).

The `'MiOS'` name (capitalized) is a project mark; lowercase `mios` (used in
file paths, package names, env-var prefixes, etc.) is the technical
identifier and free of that constraint.
