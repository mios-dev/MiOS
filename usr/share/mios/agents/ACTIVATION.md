# mios-agents — Architect→Operator (A2O) super-container

One image = **code-server** (browser IDE / glass wall) + **tmux** war room +
**Claude Code CLI** + **agy** (Antigravity CLI → Gemini) + the **`mios-a2o`**
muxer. Claude scaffolds; an operator engine finishes the last 20% inside a tmux
session; humans watch/steer via the code-server terminal (same container, same
tmux socket). Credentials are **mounted/entered at runtime — never baked**.

Files in this dir:
- `Containerfile` — the image source (base = code-server; adds tmux/Claude/agy/harness).
- `mios-a2o` — the engine-aware war-room muxer (`dispatch|status|tail|capture|send|repl|doctor|selftest`).
- `mios-agents-dev.sh` — DEV build+run helper (rootless podman, IDE on `:8801`).
- `mios-forge-mirror.sh` — Forgejo pull-mirror of the GitHub repo (owner/port from SSOT).

## DEV validation (do this first — you launch it)

```bash
bash usr/share/mios/agents/mios-agents-dev.sh          # build + run in MiOS-DEV
podman exec -it mios-agents-dev agy                    # sign in the Gemini operator
# IDE: http://localhost:8801 (pw = mios) → terminal runs `mios-a2o`
```

## Phase B — bake into the immutable image

> Follows the existing local-image precedent (`localhost/mios-crawl4ai-slim`,
> `localhost/mios-firecrawl`, `localhost/mios-coderun-sandbox`). Everything below
> is SSOT/Law-compliant; run `just build` to bake, then deploy via bootc.

**1. Port registry** — add to the `MIOS_PORT_*` block in `usr/share/mios/mios.toml`
(don't hardcode 8801 elsewhere; Law 7):
```toml
MIOS_PORT_AGENTS = 8801
```

**2. Container SSOT** — add to `usr/share/mios/mios.toml` (schema mirrors
`[containers.mios-code-server.*]`; Law 6 → `User/Group/Delegate`; NO-HARDCODE →
registry port, SSOT password, no literal user/URL):
```toml
[containers.mios-agents.Container]
ContainerName = "mios-agents"
Image = "localhost/mios-agents:latest"
Pod = "mios-webtools.pod"
EnvironmentFile = "/etc/mios/install.env"
Environment = [
  "MIOS_A2O_ENGINE=agy",
  "MIOS_A2O_WORK=/mnt/mios-root",
  "PASSWORD=${MIOS_DEFAULT_PASSWORD:-mios}",
]
Exec = "--bind-addr 0.0.0.0:${MIOS_PORT_AGENTS:-8801} /mnt/mios-root"
User = "0"
Group = "0"
SecurityLabelDisable = "true"
Volume = [
  "/var/lib/mios/agents:/home/coder",
  "/:/mnt/mios-root:rw,rslave",
]
Label = [
  "org.opencontainers.image.title=mios-agents",
  "io.podman_desktop.openInBrowser=http://localhost:${MIOS_PORT_AGENTS:-8801}/",
]

[containers.mios-agents.Install]
WantedBy = "multi-user.target default.target"

[containers.mios-agents.Service]
Delegate = "yes"
Restart = "on-failure"
RestartSec = "10s"
TimeoutStartSec = "600s"

[containers.mios-agents.Unit]
After = "network-online.target mios-code-server.service"
Description = "'MiOS' A2O agents (Claude CLI + agy/Gemini + tmux war room)"
Wants = "network-online.target"
```

**3. Pod membership** — add `"mios-agents"` to `[pods.mios-webtools].members`.

**4. `/var` path** (Law 2 — no build-time mkdir) — declare in
`usr/lib/tmpfiles.d/mios.conf`:
```
d /var/lib/mios/agents 0750 1000 1000 -
```

**5. Image build + bound-images** (Law 3) — build `localhost/mios-agents:latest`
from `usr/share/mios/agents/Containerfile` in the same pipeline step that builds
the other `localhost/mios-*` images (see `automation/build-mios.sh`), and add the
bound-images symlink so it's baked into `/usr/lib/containers/storage`:
```
usr/lib/bootc/bound-images.d/mios-agents.image -> /usr/share/mios/agents/Containerfile-built ref
```
(Mirror exactly how `mios-crawl4ai-slim` / `mios-firecrawl` are wired — same
build hook, same symlink convention.)

**6. Regenerate + build:**
```bash
python tools/generate-pod-quadlets.py       # emits usr/share/containers/systemd/mios-agents.container
just build                                  # bakes the image; runs bootc container lint (Law 4)
```

## Credentials (runtime, never baked)
- **agy (Gemini):** `podman exec -it mios-agents agy` → interactive OAuth (you reserve this).
- **Claude:** mount `~/.claude/.credentials.json` as a podman secret, or `podman exec -it mios-agents claude` → `/login`.
- **Auto-approve operator:** dispatch with `MIOS_A2O_AUTO=1` (adds `--dangerously-skip-permissions`) — safe *because* it's confined to this container. Requires your explicit authorization.
