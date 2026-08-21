<!-- AI-hint: Manual pages distilled from the source comments of users, sanitized, each passage anchored to the comment it came from. -->

# users

### usr/share/containers/systemd/users/mios-coderun-sandbox@.con...

/usr/share/containers/systemd/users/mios-coderun-sandbox@.container

CODE-RUN sandbox (Quadlet, templated). NOT the agent runtime --
MiOS agents (Hermes, sys-agent, opencode, micro-LLMs) ALWAYS install
directly to the host root per operator architecture. This container
is the dry-run / code-test boundary that the agent (or operator)
dispatches CODE into when they want to verify behavior before
touching the host -- e.g. "run this generated build script in a
disposable namespace and report exit code + stdout".

USER-SCOPE Quadlet (operator 2026-06-12): this unit is started via
`systemctl --user start mios-coderun-sandbox@<id>.service` by
mios-coderun-session, and it uses %t (XDG_RUNTIME_DIR) + WantedBy=
default.target -- i.e. it is a USER unit. It MUST live under a user
Quadlet search path (here: /usr/share/containers/systemd/users/) so the
podman USER generator emits it; when it was in the SYSTEM path
(/usr/share|/etc/containers/systemd/) only a SYSTEM unit was generated
and `systemctl --user` reported "unit not found" -> run_sandboxed_code
failed with a sandbox/permission error. The mios-ai service account also
needs linger + a subuid/subgid range (UserNS=keep-id) -- both provisioned
by mios-ai-firstboot.

Operator directive 2026-05-16: "MiOS-Agents live on the local MiOS
systems -- Containers are for servers, applications, hosts, etc-etc
(we will add proper sandboxing later (MiOS AI Agents ALWAYS install
to the core system/host(s) root!!! Sandboxing can be later
implemented with proper dry-running of code in these sandboxes or
testing)".

Start a dry-run sandbox with:

  systemctl --user start mios-coderun-sandbox@<run-id>.service

Dispatch code into it:

  podman exec -i mios-coderun-sandbox-<run-id> \
      /usr/local/bin/exec-init <cmd>

The exec-init wrapper applies the per-process Landlock domain;
the Quadlet provides namespace + seccomp + cgroup + network deny.
Defense in depth: if any single layer fails, the others hold.

<!-- mios-src:7d690d27ea3e from usr/share/containers/systemd/users/mios-coderun-sandbox@.container:4-44 -->

### UNPRIVILEGED-QUADLETS (Law 6). UserNS=keep-id already pins...

UNPRIVILEGED-QUADLETS (Law 6). UserNS=keep-id already pins the
container "root" to whatever UID the unit runs as -- but the
postcheck Law-6 validator REQUIRES an explicit User= directive on
every Quadlet (no exceptions outside the documented allowlist:
mios-ceph, mios-k3s). Set User=root because:
  * the sandbox spawns container PID-1 as "root" inside the user
    namespace (which keep-id maps to the host invoker, NOT real
    uid 0); the inside-container root has NO host privileges
  * the sandbox's whole defense-in-depth (Network=none, ReadOnly,
    DropCapability=ALL, seccomp, Landlock) assumes container-root
  * setting it to anything else breaks the keep-id mapping
This satisfies the Law-6 grep while preserving the sandbox's
rootless-on-the-host posture.

<!-- mios-src:ab8897f7752a from usr/share/containers/systemd/users/mios-coderun-sandbox@.container:53-65 -->

### UserNS=keep-id: container "root" is the host UID running...

UserNS=keep-id: container "root" is the host UID running this unit.
Files written to bind-mounted /work appear as the operator's UID
on the host -- no chown dance after the run.

<!-- mios-src:84720888223c from usr/share/containers/systemd/users/mios-coderun-sandbox@.container:68-70 -->

### Workspace bind mount, with per-instance SELinux label (:Z)....

Workspace bind mount, with per-instance SELinux label (:Z). The
path is template-substituted: %i is the systemd instance specifier,
used as both the run id AND the workspace directory name under
/var/home/mios/coderuns/. (Operators wanting a different layout
edit this Volume= line; future iteration reads from mios.toml
[paths.coderun_workspace_root] per TOML-first invariant.)

<!-- mios-src:c573a84bad78 from usr/share/containers/systemd/users/mios-coderun-sandbox@.container:109-114 -->
