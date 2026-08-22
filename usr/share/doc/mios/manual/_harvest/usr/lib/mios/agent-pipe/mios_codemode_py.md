<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_codemode -- pure helpers for WS-2 Code Mode (the AIOS...

mios_codemode -- pure helpers for WS-2 Code Mode (the AIOS Tool-Manager
"Code Mode" layer: instead of loading ~71 OpenAI function schemas into the
model's context every turn, the agent WRITES CODE that calls a small local tool
API; the code runs inside the EXISTING rootless podman coderun-sandbox and only
the FILTERED result returns -- the big token win).

Pure stdlib (no httpx / fastapi / podman / DB), in the sibling-module style of
mios_sched / mios_evict / mios_aci / mios_hitl, so it unit-tests in isolation
(test_mios_codemode.py). server.py owns the wiring (the SSOT flag, the
_exec_tool_calls branch, the broker proxy); the CLI (usr/libexec/mios/
mios-coderun-codemode) owns the actual podman exec. This module owns only the
reusable, side-effect-free decisions both of them need to agree on:

  * session id derivation (stable per conversation so a chat reuses one warm
    sandbox instead of churning a container per call),
  * the `podman exec` argv that dispatches a snippet into a running sandbox,
  * normalising the agent's tool-call arguments into a snippet request,
  * parsing / capping the sandbox's JSON result envelope,
  * the gating decision (Code Mode is DEFAULT-OFF + degrade-open).

Nothing here launches, writes, or touches the network -- that keeps the security-
sensitive surface (which the agent can drive) small and fully testable.

<!-- mios-src:394b3c922176 from usr/lib/mios/agent-pipe/mios_codemode.py:3-25 -->

### Validate + normalise an agent Code Mode tool-call into a...

Validate + normalise an agent Code Mode tool-call into a request dict.

    Returns (ok, payload). On success payload = {code, lang, timeout, net}. On
    failure payload = {"error": "<reason>"} so the caller returns a structured
    tool result the model can react to (no exceptions across the tool boundary).
    DEFAULT net=False (offline jail) -- the sandbox denies the network unless the
    agent opts in AND the deploy allows it.

<!-- mios-src:186c293eec36 from usr/lib/mios/agent-pipe/mios_codemode.py:94-100 -->

### Code Mode gating (DEFAULT-OFF): only on when...

Code Mode gating (DEFAULT-OFF): only on when [code_mode].enable is an
    explicit truthy value. Any missing/empty/garbage config -> off (degrade
    closed for a code-EXECUTION feature -- the one place we don't degrade open).

<!-- mios-src:80302a148fc9 from usr/lib/mios/agent-pipe/mios_codemode.py:124-126 -->

### The argv that dispatches a prepared snippet file into a...

The argv that dispatches a prepared snippet file into a RUNNING sandbox
    container via `podman exec -i`. The snippet is written to the bind-mounted
    workspace first (the caller does that I/O); here we only build the command
    that runs the right interpreter on it inside the jail.

    `init` (optional) is the in-container Landlock PID-1 wrapper
    (/usr/local/bin/exec-init per concepts/coderun-sandbox.md) -- when given, the
    interpreter is run THROUGH it for the per-process kernel boundary. Pure: this
    only assembles the list; it never runs anything.

<!-- mios-src:35e58aef566d from usr/lib/mios/agent-pipe/mios_codemode.py:142-150 -->
