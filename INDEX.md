# 'MiOS' System Interface -- v0.2.2

Single source of truth for 'MiOS' architectural laws and the OpenAI-compatible
API surface. Sourced from `Containerfile`, `automation/`, `usr/lib/bootc/`,
`usr/share/mios/ai/v1/`, and the upstream specs cited inline.

## 1. System profile

'MiOS' is an immutable, bootc-managed Linux workstation OS distributed as an
OCI image. Source: `README.md`, `Containerfile`. Image:
`ghcr.io/mios-dev/mios:latest`.

## 2. API surface (OpenAI-compatible)

All system agents target the local proxy at `http://localhost:8080/v1`,
served by the `mios-ai.container` Quadlet (LocalAI runtime). The
endpoints below follow the OpenAI public API spec
(<https://platform.openai.com/docs/api-reference>) verb-for-verb;
`x-mios.*` rows are MiOS extensions, clearly namespaced so strict
OpenAI clients can ignore them.

| Path | Method | Served by | Spec |
|---|---|---|---|
| `/v1/chat/completions` | POST | LocalAI runtime | <https://platform.openai.com/docs/api-reference/chat> |
| `/v1/responses` | POST | LocalAI runtime | <https://platform.openai.com/docs/api-reference/responses> |
| `/v1/embeddings` | POST | LocalAI runtime | <https://platform.openai.com/docs/api-reference/embeddings> |
| `/v1/models` | GET | `usr/share/mios/ai/v1/models.json` | <https://platform.openai.com/docs/api-reference/models/list> |
| `/v1/audio/{transcriptions,speech}` | POST | LocalAI runtime (when configured) | <https://platform.openai.com/docs/api-reference/audio> |
| `x-mios:/v1/mcp` | GET | `usr/share/mios/ai/v1/mcp.json` | <https://modelcontextprotocol.io/specification> |

`/v1/mcp` is a MiOS extension (not part of the OpenAI public API). The
canonical OpenAI route to invoke an MCP server is
`POST /v1/responses` with `tools=[{"type": "mcp", "server_url": ...}]`;
the manifest at `/v1/mcp` is what MiOS agents read to populate that
`tools` array. The `x-mios:` prefix is a documentation marker only --
the served URL is `/v1/mcp`.

### 2a. Default model set

| Slot | Default | Quant | Disk | Resident | Notes |
|---|---|---|---|---|---|
| chat / code | `qwen2.5-coder:7b` | Q4_K_M | ~4.7 GB | ~5-6 GB | Apache 2.0; 128K context; HumanEval ~88%; multi-language including bash, PowerShell, Containerfiles, systemd units, TOML |
| embeddings | `nomic-embed-text` (v1.5) | Q4 | ~270 MB | <1 GB | Apache 2.0; 768-dim; 8192-token context; OpenAI `/v1/embeddings`-shape via LocalAI |

Sized for the 12 GB system-RAM baseline (CPU-only inference, ~8 GB
available to the model). Build-baked into
`/usr/share/ollama/models` (immutable composefs surface) by
`automation/37-ollama-prep.sh`; first-boot service
(`mios-ollama-firstboot.service`) hardlink-copies the seed into
`/var/lib/ollama/models` (the writable `OLLAMA_MODELS` path).

Override the build-time set with `MIOS_OLLAMA_BAKE_MODELS=<csv>` (e.g.
`"qwen2.5-coder:14b,nomic-embed-text"` for 24 GB+ profiles). Override
the runtime selection by editing `[ai].model` / `[ai].embed_model` in
`/etc/mios/mios.toml` (host) or `~/.config/mios/mios.toml` (per-user)
and restarting `mios-ollama.service`. The `[ai]` section in
`usr/share/mios/mios.toml` documents the alternates considered and
their resource cost.

## 3. Architectural laws (enforced; non-negotiable)

| # | Law | Enforced by |
|---|---|---|
| 1 | **USR-OVER-ETC** -- static config in `/usr/lib/<component>.d/`; `/etc/` is admin-override only. Exceptions documented per-file (e.g., `/etc/yum.repos.d/`, `/etc/nvidia-container-toolkit/` -- upstream-contract surfaces). | `automation/`, `usr/lib/`, `etc/` |
| 2 | **NO-MKDIR-IN-VAR** -- every `/var/` path declared via `usr/lib/tmpfiles.d/*.conf`. | `usr/lib/tmpfiles.d/mios*.conf` |
| 3 | **BOUND-IMAGES** -- every Quadlet image symlinked into `/usr/lib/bootc/bound-images.d/`. Binder loop: `automation/08-system-files-overlay.sh:74-86`. | `usr/lib/bootc/bound-images.d/` |
| 4 | **BOOTC-CONTAINER-LINT** -- final RUN of `Containerfile`. | `Containerfile` (last `RUN`) |
| 5 | **UNIFIED-AI-REDIRECTS** -- every OpenAI-API-shaped client resolves through one canonical surface: `MIOS_AI_ENDPOINT` (default `http://localhost:8080/v1`, the OpenAI-SDK `base_url` slot), `MIOS_AI_MODEL` (default model id), `MIOS_AI_KEY` (api key, empty for the local proxy). No vendor-hardcoded URLs. | `/etc/profile.d/mios-env.sh`, `usr/bin/mios`, `usr/bin/mios-env`, `etc/mios/ai/` |
| 6 | **UNPRIVILEGED-QUADLETS** -- every Quadlet declares `User=`, `Group=`, `Delegate=yes`. Documented exceptions: `mios-ceph` and `mios-k3s` declare `User=root`/`Group=root` because Ceph/K3s require uid 0 (see file headers). | `etc/containers/systemd/`, `usr/share/containers/systemd/` |

## 4. Profile + environment resolution

Both the user profile (TOML) and runtime environment (env-style) follow a
three-layer overlay. Higher layers supersede lower layers field-by-field.

**Profile layers** (read by `mios-bootstrap/install.sh:load_profile_defaults`
and at runtime by `mios` CLI clients):

1. `~/.config/mios/profile.toml` -- per-user override (highest precedence;
   seeded into every uid≥1000 home from `/etc/skel/.config/mios/profile.toml`)
2. `/etc/mios/profile.toml` -- host/admin override (shipped by `mios-bootstrap`)
3. `/usr/share/mios/profile.toml` -- vendor defaults (shipped by `mios.git`,
   immutable, USR-OVER-ETC)

**Environment layers** (resolved by `/etc/profile.d/mios-env.sh` at
login; later sources override earlier values, so this list runs from
**lowest** precedence to **highest**):

1. `/usr/share/mios/env.defaults` -- vendor defaults (lowest)
2. `~/.env.mios` -- legacy per-user (deprecated; honored only when no
   admin/host/current source supplies the same key)
3. `/etc/mios/env.d/*.env` -- admin/distro drop-ins (alphabetical)
4. `/etc/mios/install.env` -- host identity, written by bootstrap
5. `~/.config/mios/env` -- canonical per-user override (highest)

The CLI `/usr/bin/mios-env` prints the resolved surface (`--explain`
shows which layer supplied each key).

**Build-time variables** read by `Justfile`:

| Variable | Scope | Purpose |
|---|---|---|
| `MIOS_AI_KEY` / `MIOS_AI_MODEL` / `MIOS_AI_ENDPOINT` | AI | Resolution per LAW 5; defaults in `usr/share/mios/env.defaults`. |
| `MIOS_BASE_IMAGE` | build | OCI base image (default `ghcr.io/ublue-os/ucore-hci:stable-nvidia`, `Justfile:45`). |
| `MIOS_LOCAL_TAG` | build | Local image tag (default `localhost/mios:latest`, `Justfile:13`). |
| `MIOS_USER` / `MIOS_HOSTNAME` | build | Default account/hostname baked into the image (`Containerfile:26-27`). |
| `MIOS_FLATPAKS` | build | Comma-separated Flatpak refs (`Containerfile:28`). |

## 5. Defaults policy

Every boolean feature flag in `usr/share/mios/profile.toml` and
`/etc/mios/profile.toml` ships **`true`**. The system never disables a
component via static config -- when a component is incompatible with the
host (wrong virtualization layer, missing required path, missing
hardware), systemd `Condition*` directives in the corresponding
Quadlet/service unit short-circuit it at boot/pre-boot and the unit
silently no-ops. Operators can still set any flag to `false` to
force-disable a component even when it would otherwise run.

Active gating (referenced in `etc/containers/systemd/` and
`usr/share/containers/systemd/`):

| Unit | Condition | Skips on |
|---|---|---|
| `mios-ai` | `ConditionPathIsDirectory=/etc/mios/ai` | bootstrap incomplete |
| `mios-ceph` | `ConditionPathExists=/etc/ceph/ceph.conf`, `!container` | Ceph not configured, nested |
| `mios-k3s` | `!wsl`, `!container` | WSL2, nested containers |
| `crowdsec-dashboard` | `ConditionPathExists=/etc/crowdsec/config.yaml` | CrowdSec not configured |
| `cloudws-guacamole`, `guacd`, `guacamole-postgres` | `!container` | nested containers |
| `cloudws-pxe-hub` | `!wsl`, `!container` | virtualized hosts without routable LAN |
| `mios-gpu-{nvidia,amd,intel,status}` | `ConditionPathExists=/dev/...`, `!container`, `!wsl` (Intel) | no matching GPU device |
| `ollama` | none | always runs (CPU fallback) |
| `mios-forge` | `ConditionPathIsDirectory=/etc/mios/forge`, `!container` | bootstrap incomplete, nested |
| `mios-forge-firstboot` | `ConditionPathExists=/etc/mios/install.env`, `!sentinel`, `!container` | install.env absent, already ran, nested |
| `mios-cockpit-link` | `ConditionPathExists=/usr/lib/systemd/system/cockpit.socket`, `!container` | Podman Desktop UI shim that publishes :19090 → host :9090 so the Cockpit web console is clickable from the container view; skipped when cockpit isn't installed |

## 5b. Service access surface (LAN-reachable by default)

Every 'MiOS' service binds `0.0.0.0` on its listening port so the same
deployment is reachable from
- `127.0.0.1` / `::1` (local loopback)
- the host LAN IP (remote-LAN access on bare-metal, Hyper-V VM, or
  WSL2 with `networkingMode=mirrored`)
- Podman bridge / `cni0` / `virbr0` (sibling-container access on
  `mios.network` and the libvirt bridge)

Container Quadlets use `PublishPort=0.0.0.0:HOST:CONTAINER` (Podman's
default already binds 0.0.0.0; the explicit prefix makes the contract
auditable). Apps inside containers that take an explicit listen
address get `Environment=ADDRESS=0.0.0.0:PORT` (LocalAI),
`OLLAMA_HOST=0.0.0.0:11434` (Ollama), or
`FORGEJO__server__HTTP_ADDR=0.0.0.0` (Forgejo). Cockpit on the host
listens via `cockpit.socket` whose default `ListenStream=9090` already
binds the wildcard address.

Firewalld is the actual gate. Default zone is `drop`; the ports below
are opened by `automation/25-firewall-ports.sh` (build-time) and
`automation/33-firewall.sh` (runtime mios-firewall-init):

| Port  | Proto | Service | Notes |
|---|---|---|---|
| 22    | tcp | sshd          | host service |
| 2222  | tcp | mios-forge    | git+ssh (non-22 to coexist with sshd) |
| 3000  | tcp | mios-forge    | Forgejo HTTP web UI |
| 3389  | tcp | RDP           | GNOME Remote Desktop / xRDP |
| 6443  | tcp | k3s           | Kubernetes API |
| 8080  | tcp | mios-ai       | LocalAI /v1 (Architectural Law 5) |
| 8090  | tcp | mios-guacamole| Browser desktop (mapped from container 8080) |
| 8443  | tcp | mios-ceph     | Ceph dashboard |
| 9090  | tcp | cockpit       | host web console |
| 11434 | tcp | ollama        | alternate local LLM backend |
| 19090 | tcp | mios-cockpit-link | Podman Desktop discovery shim → 9090 |

Internal-only services (no `PublishPort`, reachable only from the
`mios.network` bridge): `guacamole-postgres` (5432), `guacd` (4822),
`crowdsec-dashboard` (LAPI 8080 sibling-only), `mios-pxe-hub`.

## 6. Global pipeline phases

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

## 7. Cross-references

- Build pipeline architecture: `CLAUDE.md`, `automation/build.sh`.
- Filesystem and hardware layout: `ARCHITECTURE.md`.
- Security posture and hardening kargs: `SECURITY.md`, `usr/lib/bootc/kargs.d/`.
- Build modes (CI, Linux, Windows, self-build): `SELF-BUILD.md`.
- Contribution conventions: `CONTRIBUTING.md`.
- Component licenses: `LICENSES.md`.
