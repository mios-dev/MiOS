<!-- AI-hint: Defines the isolated Podman/Landlock container that lets MiOS agents dry-run / test generated code before it touches the immutable host. Explains the defense-in-depth boundary (Quadlet user unit + exec-init Landlock + seccomp + cgroups), how it serves the Code Mode (run_python_tool_script) verb, and how it fits the whole MiOS agent stack. Distinct from the per-call bubblewrap `coderun`/`run_sandboxed_code` jail (mios-coderun / mios-sandbox-exec).
     AI-related: /etc/mios/containers/coderun-seccomp.json, /etc/mios/containers/coderun-sandbox/Dockerfile, /etc/mios/containers/coderun-sandbox/exec-init.c, /usr/libexec/mios/mios-coderun-session, /usr/share/containers/systemd/users/mios-coderun-sandbox@.container, /etc/mios/scripts/, /usr/share/mios/mios.toml, mios-coderun-session, mios-coderun-sandbox, mios-coderun-codemode, mios-find -->
# MiOS code-run sandbox — for dry-running / testing, NOT the agent runtime

## What this is and why it exists

MiOS is one system built two ways at once: an immutable, bootc/OCI Fedora
workstation (the whole OS ships as one container image you `bootc upgrade` like
a `git pull` and `bootc rollback` like a Ctrl-Z) that is *also* a local,
self-replicating agentic AI OS. Because the **repo root IS the deployed system
root**, when an agent generates a script and runs it, it is editing a live,
version-locked OS — there is no throwaway VM to mess up.

That is the tension this doc resolves. The MiOS agent stack (the agent-pipe
orchestrator on `:8640`, the MiOS-Hermes gateway on `:8642`, the local
inference lanes led by `mios-llm-light` on `:11450`, PostgreSQL+pgvector memory,
the MCP tool surface) runs as **direct host installs** by operator design — the
agents *are* the OS operating itself, so they live on the host root, not in a
container. But that same design means model-generated or untrusted code must
have a place to be *proven safe before it lands*. This sandbox is that place:
the disposable, kernel-hardened boundary an agent (or the operator) dispatches
**code** into to verify behaviour before it touches the immutable host.

**Architectural note (operator directive 2026-05-16):**
> "MiOS-Agents live on the local MiOS systems — Containers are for
> servers, applications, hosts, etc-etc (we will add proper
> sandboxing later (MiOS AI Agents ALWAYS install to the core
> system/host(s) root!!! Sandboxing can be later implemented with
> proper dry-running of code in these sandboxes or testing)".

So the boundary is sharp:

* **MiOS agents** (Hermes, sys-agent, opencode, the micro-LLMs behind
  `mios-llm-light`) run as direct host installs — `hermes-agent.service` is
  rootless on the host, never inside a container.
* **This sandbox** is the boundary for code DRY-RUNS / TESTS — when the operator
  or an agent wants to verify a generated script before it touches the live
  host, the code (not the agent) goes in here.

## Where it sits in the agent stack

This container is the execution backend for the **Code Mode** path — the
`run_python_tool_script` verb (`mios-coderun-codemode`), which lets an agent
write a Python snippet that orchestrates several MiOS verbs in one shot inside a
"rootless podman sandbox (no network, read-only, dropped caps)". Code Mode is
**default-off and degrades closed**: `mios.toml [code_mode] enable = false` is
the master gate, and code only runs when `enable = true` *and* the sandbox image
is present. The agent-pipe reads that gate directly.

It is distinct from the lighter, per-call **bubblewrap** jail behind the
`coderun` / `run_sandboxed_code` verb (`mios-coderun` → `mios-sandbox-exec`),
which runs a single short snippet in an ephemeral bwrap workspace and discards
it. Use the bwrap jail for a quick one-off; use **this** container boundary for
a longer-lived, per-session dry-run with snapshot/revert (build/migration/install
scripts, untrusted tooling). Both honour the same rule — no model-generated code
touches the host unsandboxed.

## Layers (defense-in-depth, when the sandbox IS used)

```
┌─────────────────────────────────────────────────────────────┐
│  caller (operator shell, or agent Code-Mode dry-run path)   │
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
│  Quadlet container (rootless podman, USER unit)             │ ← kernel boundary 2
│  -- Network=none                                            │
│  -- ReadOnly=true + tmpfs /tmp (1G) + tmpfs /work-upper (2G)│
│  -- DropCapability=ALL + NoNewPrivileges=true               │
│  -- SeccompProfile=/etc/mios/containers/coderun-seccomp.json│
│  -- PodmanArgs: --cpus=4 --memory=8g --pids-limit=1024      │
│       --ulimit nofile=4096 nproc=512 fsize=2GiB            │
│  -- UserNS=keep-id (container "root" = host invoker UID)    │
│  -- SecurityLabelType=container_t (per-instance MCS via :Z) │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  host kernel: SELinux enforcing, cgroups v2, unprivileged   │ ← system policy
│  userns enabled                                             │
└─────────────────────────────────────────────────────────────┘
```

If any single layer fails, the others hold. Note the two NPROC figures are two
different layers: the in-container `exec-init` rlimit caps a dispatched command
tree at NPROC=1024, while the Quadlet's outer `--ulimit nproc=512` caps the
whole container — both are intentional and accurate.

## Why it satisfies Architectural Law 6 (UNPRIVILEGED-QUADLETS)

Law 6 requires every Quadlet to declare `User=` / `Group=` and run
unprivileged. This unit sets `User=root` *with* `UserNS=keep-id`: the
container's "root" is mapped to whatever host UID the user unit runs as (the
`mios-ai` service account, provisioned with linger + a subuid/subgid range by
`mios-ai-firstboot`), **not** real uid 0. Inside-container root therefore has no
host privileges, and the whole defense-in-depth stack (`Network=none`,
`ReadOnly=true`, `DropCapability=ALL`, seccomp, Landlock) assumes that
container-root. Setting `User=` to anything else would break the keep-id
mapping; `root` here satisfies the Law-6 validator while preserving the
rootless-on-the-host posture. The image itself is built locally and pinned at
`localhost/mios-coderun-sandbox:latest`.

## Files

| Path | Role |
|---|---|
| `/usr/share/containers/systemd/users/mios-coderun-sandbox@.container` | Quadlet template (per-run); **USER** unit — must live under a *user* Quadlet search path so the podman user generator emits it |
| `/etc/mios/containers/coderun-seccomp.json` | Hardened seccomp allowlist (AF_UNIX-only sockets; `clone3`/escalation syscalls → ENOSYS) |
| `/etc/mios/containers/coderun-sandbox/Dockerfile` | Alpine 3.20 + ripgrep + fd + git + python3 + nodejs + gcc/make + static-musl `exec-init` |
| `/etc/mios/containers/coderun-sandbox/exec-init.c` | In-container PID-1 Landlock + rlimits wrapper |
| `/usr/libexec/mios/mios-coderun-session` | start/stop/snap/revert/status/list orchestrator (btrfs-snapshot or git-stash isolation) |

> **Why a USER unit (operator 2026-06-12):** the sandbox is started via
> `systemctl --user start mios-coderun-sandbox@<id>.service` and uses `%t`
> (`XDG_RUNTIME_DIR`) + `WantedBy=default.target`. When the template lived in a
> SYSTEM search path (`/usr/share` or `/etc/containers/systemd/`) only a SYSTEM
> unit was generated and `systemctl --user` reported "unit not found", so
> `run_python_tool_script` failed with a sandbox/permission error. It must live
> under the **user** search path shown above.

## Build + start (one-time)

```bash
# 1. Build the sandbox image (~150 MB):
podman build -t localhost/mios-coderun-sandbox:latest \
    /etc/mios/containers/coderun-sandbox/

# 2. Let the podman USER generator pick up the Quadlet template:
systemctl --user daemon-reload

# 3. Start a per-session code-run sandbox (also snapshots the project root):
mios-coderun-session start <run-id>
#   (wraps: systemctl --user start mios-coderun-sandbox@<run-id>.service)

# 4. Dispatch code into it via the Landlock wrapper:
podman exec -i mios-coderun-sandbox-<run-id> \
    /usr/local/bin/exec-init bash -lc "echo hello from sandbox"

# 5. Stop + GC old snapshots when done:
mios-coderun-session stop <run-id>
```

`mios-coderun-session` keys everything off one opaque `<run-id>` (the agent's
session uuid/hash): it threads through the Quadlet instance name (`%i`), the
project subdir under the workspace root, and the snapshot path. On `start` it
snapshots the project root (btrfs subvolume snapshot when available, git-stash
fallback otherwise); `revert` restores it; `stop` bounds snapshot retention.

## When to use this sandbox

* The operator hands the agent a script and asks "what would this do if I ran
  it?" — the agent dispatches into a coderun sandbox, captures
  stdout/stderr/exit, reports back.
* The agent generates a build / migration / install script and wants to verify
  it doesn't `rm -rf` something before running it on the host.
* An agent uses **Code Mode** (`run_python_tool_script`) to glue several MiOS
  verbs together with loops/logic — that snippet executes here.
* CI-like dry-runs of operator-facing scripts before they land in
  `/etc/mios/scripts/`.
* Untrusted code (third-party, downloaded sample, model-generated unfamiliar
  tooling) — run it here first.

## When NOT to use it

* The agent's own runtime — agents install to host root by design.
  `hermes-agent.service` and the inference lanes do **not** run inside this
  sandbox.
* Operator-confirmed actions where the host IS the target (mios-find,
  mios-windows launch, file edits in `/etc/mios/`, etc.) — those run on the host
  directly via the normal helpers.
* A single trivial one-off snippet with no session/snapshot need — that is the
  lighter bubblewrap `run_sandboxed_code` path, not this container.

## Operator-tunable paths

Both the workspace root + snapshot root resolve env-args-first, then fall back to
`mios.toml [paths]` (the configuration SSOT), then a compiled default —
matching the rest of the MiOS helper fleet ("no hardcoded anything"):

```toml
[paths]
coderun_workspace_root  = "/var/home/mios/coderuns"           # podman coderun-sandbox /work bind root (shared by Code Mode + coderun-session)
coderun_snapshots_root  = "/var/home/mios/.coderun-snapshots" # coderun-session snapshot root
```

Override per-host in `/etc/mios/mios.toml` or per-user in
`~/.config/mios/mios.toml`; the vendor SSOT is `/usr/share/mios/mios.toml`.
