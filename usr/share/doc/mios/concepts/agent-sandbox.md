# MiOS agent exec sandbox — defense-in-depth boundary

Per the FS+OS Control guide §15 "What I'd actually build first": a
per-session container that the agent dispatches commands into,
combining four independent boundaries so any one layer's failure is
caught by the others.

## Layers (top-to-bottom)

```
┌─────────────────────────────────────────────────────────────┐
│  agent runtime (Hermes / opencode)                          │
│  -- plugin permission gate, prompt rules, refusal patterns  │ ← UX policy
│  -- talks to sandbox via:  podman exec -i mios-agent-       │
│       sandbox-<session-id> /usr/local/bin/exec-init <cmd>   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  exec-init (PID-1 of each agent command in the sandbox)     │ ← kernel boundary 1
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
│  -- SeccompProfile=/etc/mios/containers/agent-seccomp.json  │
│  -- cgroups v2 (4 cpu, 8 GiB mem, 1024 pids)                │
│  -- UserNS=keep-id (container "root" = host operator UID)   │
│  -- :Z-labeled project bind mount                           │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│  host kernel: SELinux enforcing, cgroups v2, user.max_user_ │ ← system policy
│  namespaces enabled (Fedora 42 default), unprivileged userns│
└─────────────────────────────────────────────────────────────┘
```

## Files

| Path | Role |
|---|---|
| `/etc/containers/systemd/mios-agent-sandbox@.container` | Quadlet template (per-session) |
| `/etc/mios/containers/agent-seccomp.json` | Hardened seccomp allowlist |
| `/etc/mios/containers/agent-sandbox/Dockerfile` | Alpine + ripgrep + git + python3 + nodejs + exec-init |
| `/etc/mios/containers/agent-sandbox/exec-init.c` | In-container PID-1 Landlock wrapper |
| `/usr/libexec/mios/mios-agent-session` | start/stop/snap/revert/status/list session helper |

## Build + start (one-time)

```bash
# 1. Build the sandbox image (~150 MB):
podman build -t localhost/mios-agent-sandbox:latest \
    /etc/mios/containers/agent-sandbox/

# 2. systemd-user knows about the Quadlet template after a reload:
systemctl --user daemon-reload

# 3. Start a session sandbox:
mios-agent-session start abc123-session-id

# 4. The agent now dispatches commands via:
podman exec -i mios-agent-sandbox-abc123-session-id \
    /usr/local/bin/exec-init bash -lc "echo hello from sandbox"

# 5. Stop + GC old snapshots when done:
mios-agent-session stop abc123-session-id
```

## Integration from Hermes / opencode

The hardened `bash` tool wrapper (per the guide §16) becomes:

```
async def execute(args, ctx):
    await ctx.permission_gate.ask(kind="exec", pattern=args.command, ...)
    container = f"mios-agent-sandbox-{ctx.session_id}"
    proc = await asyncio.create_subprocess_exec(
        "podman", "exec", "-i", container,
        "/usr/local/bin/exec-init", "/bin/bash", "-lc", args.command,
        stdout=PIPE, stderr=PIPE)
    ...
```

The agent's plugin-level permission gate is the UX layer; the
container + Landlock + seccomp is the kernel boundary. If the model
talks past the permission gate (bad LLM behaviour) OR the gate has a
bug, the kernel still says no.

## Operator-tunable paths

Both the project root + snapshot root resolve env-args-first then
fall back to `mios.toml [paths]` per the operator TOML-first
invariant:

```
[paths]
agent_projects_root  = "/var/home/mios/projects"
agent_snapshots_root = "/var/home/mios/.agent-snapshots"
```

Override per-host in `/etc/mios/mios.toml` or per-user in
`~/.config/mios/mios.toml`.

## What this does NOT yet include

* TCP egress allowlist via pasta + nftables (Network=none is total deny)
* btrfs subvolume conversion of `/var/home/mios/projects/` (snapshots
  only work when the project root happens to be on btrfs already;
  otherwise falls back to git stash)
* Landlock audit log integration (kernel 6.15+; Fedora 43 territory)
* eBPF-LSM host-wide policies
* The actual hermes / opencode tool wrapper -- this PR ships the
  sandbox infrastructure; the tool wrapper lands as a follow-up
  alongside the agent that calls it.

## Verification

```bash
# Sandbox cannot reach the network:
mios-agent-session start test
podman exec -i mios-agent-sandbox-test /usr/local/bin/exec-init \
    /bin/sh -c "ping -c 1 1.1.1.1"   # fails: socket(AF_INET)=ENOSYS

# Sandbox cannot write outside /work + /tmp:
podman exec -i mios-agent-sandbox-test /usr/local/bin/exec-init \
    /bin/sh -c "touch /etc/foo"      # fails: EACCES via Landlock

# Sandbox cannot ptrace anything:
podman exec -i mios-agent-sandbox-test /usr/local/bin/exec-init \
    strace ls /work                  # fails: ptrace=ENOSYS

mios-agent-session stop test
```
