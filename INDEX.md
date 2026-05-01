# MiOS System Interface — v0.2.0

Single source of truth for MiOS architectural laws and the OpenAI-compatible
API surface. Sourced from `Containerfile`, `automation/`, `usr/lib/bootc/`,
`usr/share/mios/ai/v1/`, and the upstream specs cited inline.

## 1. System profile

MiOS is an immutable, bootc-managed Linux workstation OS distributed as an
OCI image. Source: `README.md`, `Containerfile`. Image:
`ghcr.io/mios-dev/mios:latest`.

## 2. API surface (OpenAI-compatible)

All system agents target the local proxy at `http://localhost:8080/v1`,
served by the LocalAI Quadlet at `etc/containers/systemd/mios-ai.container`.

| Path | Method | Manifest |
|---|---|---|
| `/v1/chat/completions` | POST | LocalAI runtime |
| `/v1/models` | GET | `usr/share/mios/ai/v1/models.json` |
| `/v1/mcp` | filesystem | `usr/share/mios/ai/v1/mcp.json` |

Spec: <https://platform.openai.com/docs/api-reference>.

## 3. Architectural laws (enforced; non-negotiable)

| # | Law | Enforced by |
|---|---|---|
| 1 | **USR-OVER-ETC** — static config in `/usr/lib/<component>.d/`; `/etc/` is admin-override only. Exceptions documented per-file (e.g., `/etc/yum.repos.d/`, `/etc/nvidia-container-toolkit/` — upstream-contract surfaces). | `automation/`, `usr/lib/`, `etc/` |
| 2 | **NO-MKDIR-IN-VAR** — every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`. | `usr/lib/tmpfiles.d/mios*.conf` |
| 3 | **BOUND-IMAGES** — every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/`. Binder loop: `automation/08-system-files-overlay.sh:74-86`. | `usr/lib/bootc/bound-images.d/` |
| 4 | **BOOTC-CONTAINER-LINT** — final RUN of `Containerfile`. | `Containerfile` (last `RUN`) |
| 5 | **UNIFIED-AI-REDIRECTS** — `MIOS_AI_KEY`, `MIOS_AI_MODEL`, `MIOS_AI_ENDPOINT` → `http://localhost:8080/v1`. No vendor URLs. | `usr/bin/mios`, `etc/mios/ai/` |
| 6 | **UNPRIVILEGED-QUADLETS** — every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented exceptions: `mios-ceph` and `mios-k3s` declare `User=root`/`Group=root` because Ceph/K3s require uid 0 (see file headers). | `etc/containers/systemd/`, `usr/share/containers/systemd/` |

## 4. Environment contract

| Variable | Scope | Purpose |
|---|---|---|
| `MIOS_AI_KEY` | AI | Local inference key (default empty for unauthenticated localhost). |
| `MIOS_AI_MODEL` | AI | Target model id resolved via `usr/share/mios/ai/v1/models.json`. |
| `MIOS_AI_ENDPOINT` | AI | API base URL. Default `http://localhost:8080/v1`. |
| `MIOS_BASE_IMAGE` | build | OCI base image (default `ghcr.io/ublue-os/ucore-hci:stable-nvidia`, `Justfile:45`). |
| `MIOS_LOCAL_TAG` | build | Local image tag (default `localhost/mios:latest`, `Justfile:13`). |
| `MIOS_USER` / `MIOS_HOSTNAME` | build | Default account/hostname baked into the image (`Containerfile:26-27`). |
| `MIOS_FLATPAKS` | build | Comma-separated Flatpak refs (`Containerfile:28`). |

## 5. Global pipeline phases

The end-to-end bootstrap → install pipeline is partitioned into five phases
shared across both repos:

| Phase | Owner repo | Purpose |
|---|---|---|
| Phase-0 | `mios-bootstrap` | Preflight, profile load, identity capture |
| Phase-1 | `mios-bootstrap` | Total Root Merge (clone `mios.git` into `/`, overlay bootstrap) |
| Phase-2 | `mios` | Build (Containerfile + `automation/[0-9][0-9]-*.sh` sub-phases, OR dnf install on FHS) |
| Phase-3 | both | sysusers/tmpfiles/services + user create + per-user `~/.config/mios/{profile.toml,system-prompt.md}` staging |
| Phase-4 | `mios-bootstrap` | Reboot |

The user profile card at `etc/mios/profile.toml` (host) and
`~/.config/mios/profile.toml` (per-user) is read in Phase-0 to seed defaults
and re-written/staged in Phase-3.

## 6. Cross-references

- Build pipeline architecture: `CLAUDE.md`, `automation/build.sh`.
- Filesystem and hardware layout: `ARCHITECTURE.md`.
- Security posture and hardening kargs: `SECURITY.md`, `usr/lib/bootc/kargs.d/`.
- Build modes (CI, Linux, Windows, self-build): `SELF-BUILD.md`.
- Contribution conventions: `CONTRIBUTING.md`.
- Component licenses: `LICENSES.md`.
