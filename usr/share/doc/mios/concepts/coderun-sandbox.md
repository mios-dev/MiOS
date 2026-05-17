# MiOS code-run sandbox — for dry-running / testing, NOT the agent runtime

**Architectural note (operator directive 2026-05-16):**
> "MiOS-Agents live on the local MiOS systems — Containers are for
> servers, applications, hosts, etc-etc (we will add proper
> sandboxing later (MiOS AI Agents ALWAYS install to the core
> system/host(s) root!!! Sandboxing can be later implemented with
> proper dry-running of code in these sandboxes or testing)".

So:

* **MiOS agents** (Hermes, sys-agent, opencode, micro-LLMs) run as
  direct host installs — `hermes-agent.service` is rootless on the
  host, not in a container.
* **This sandbox** is the boundary for code DRY-RUNS / TESTS — when
  the operator or agent wants to verify a generated script before
  it touches the live host.

## Layers (defense-in-depth, when the sandbox IS used)

```
┌─────────────────────────────────────────────────────────────┐
│  caller (operator shell, or agent dry-run path)             │
│  -- dispatches into the sandbox via:                        │
│       podman exec -i mios-coderun-sandbox-<id> \            │
│           /usr/local/bin/exec-init <cmd>                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  exec-init (PID-1 of each dispatched command)               │ ← kernel boundary 1
│  -- Landlock ABI-aware: /work + /tmp rw; /usr /etc ro;      │
│       everything else denied                                │
│  -- PR_SET_NO_NEW_PRIVS                                     │
│  -- rlimits (AS=8GiB, NPROC=1024, NOFILE=4096, FSIZE=2GiB)  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  Quadlet container (rootless podman)                        │ ← kernel boundary 2
│  -- Network=none                                            │
│  -- ReadOnly=true + tmpfs /tmp + /work-upper                │
│  -- DropCapability=ALL + NoNewPrivileges=true               │
│  -- SeccompProfile=/etc/mios/containers/coderun-seccomp.json│
│  -- cgroups v2 (4 cpu, 8 GiB mem, 1024 pids)                │
│  -- UserNS=keep-id                                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  host kernel: SELinux enforcing, cgroups v2, unprivileged   │ ← system policy
│  userns enabled                                             │
└─────────────────────────────────────────────────────────────┘
```

## Files

| Path | Role |
|---|---|
| `/etc/containers/systemd/mios-coderun-sandbox@.container` | Quadlet template (per-run) |
| `/etc/mios/containers/coderun-seccomp.json` | Hardened seccomp allowlist |
| `/etc/mios/containers/coderun-sandbox/Dockerfile` | Alpine + ripgrep + git + python3 + nodejs + exec-init |
| `/etc/mios/containers/coderun-sandbox/exec-init.c` | In-container PID-1 Landlock wrapper |
| `/usr/libexec/mios/mios-coderun-session` | start/stop/snap/revert/status/list orchestrator |

## Build + start (one-time)

```bash
# 1. Build the sandbox image (~150 MB):
podman build -t localhost/mios-coderun-sandbox:latest \
    /etc/mios/containers/coderun-sandbox/

# 2. systemd knows about the Quadlet template after a reload:
systemctl --user daemon-reload

# 3. Start a code-run sandbox:
mios-coderun-session start <run-id>

# 4. Dispatch code into it:
podman exec -i mios-coderun-sandbox-<run-id> \
    /usr/local/bin/exec-init bash -lc "echo hello from sandbox"

# 5. Stop + GC old snapshots when done:
mios-coderun-session stop <run-id>
```

## When to use this sandbox

* The operator hands the agent a script and asks "what would this do
  if I ran it?" — agent dispatches into a coderun sandbox, captures
  stdout/stderr/exit, reports back.
* Agent generates a build / migration / install script and wants to
  verify it doesn't `rm -rf` something before running it on the host.
* CI-like dry-runs of operator-facing scripts before they land in
  `/etc/mios/scripts/`.
* Untrusted code (third-party, downloaded sample, model-generated
  unfamiliar tooling) — run it here first.

## When NOT to use it

* The agent's own runtime — agents install to host root by design.
  `hermes-agent.service` doesn't run inside this sandbox.
* Operator-confirmed actions where the host IS the target (mios-find,
  mios-windows launch, file edits in `/etc/mios/`, etc.) — those run
  on the host directly via the normal helpers.

## Operator-tunable paths

Both the workspace root + snapshot root resolve env-args-first then
fall back to `mios.toml [paths]`:

```toml
[paths]
coderun_workspace_root  = "/var/home/mios/coderuns"
coderun_snapshots_root  = "/var/home/mios/.coderun-snapshots"
```

Override per-host in `/etc/mios/mios.toml` or per-user in
`~/.config/mios/mios.toml`.
