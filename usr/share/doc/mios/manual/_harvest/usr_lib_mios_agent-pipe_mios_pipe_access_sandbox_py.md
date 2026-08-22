<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_sandbox -- risk-tier dispatch sandbox profiles...

mios_sandbox -- risk-tier dispatch sandbox profiles (WS-A13, the AIOS
Access-Manager confinement layer).

Pure stdlib. Every verb dispatch should run confined to the LEAST privilege its
risk tier needs; before WS-A13 there was no per-verb sandbox policy. This module
resolves a verb's permission tier -> a SandboxProfile (mechanism + workspace +
ro/net posture). It is deliberately FAIL-CLOSED: a security control must not
degrade-open, so an unknown tier (a typo, a new tier) maps to the STRICTEST
profile rather than 'none'. server.py runs the profile (bwrap/seccomp/podman +
the per-dispatch /var/lib/mios/ai/dispatch/<verbhash>-<uuid> workspace); this is
the testable decision.

<!-- mios-src:e45dd7beb84a from usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py:3-14 -->

### Resolve the sandbox profile for a verb. `explicit` -- an...

Resolve the sandbox profile for a verb.

    `explicit` -- an [verbs.*].sandbox_profile override naming a tier-equivalent
    profile ("none"/"workspace"/"strict"); wins when set + recognised.
    Otherwise map `permission_tier` via the tier table. FAIL-CLOSED: an unknown
    tier (or unknown explicit) -> the STRICTEST profile, never 'none'.

<!-- mios-src:55b5de7a0118 from usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py:54-59 -->

### The mios-sandbox-exec argv PREFIX (ending in '--') a...

The mios-sandbox-exec argv PREFIX (ending in '--') a confined profile maps
    to, or [] for an unconfined ('none') profile. server.py prepends this to a
    verb's broker command so a write/interactive verb runs under the MiOS sandbox
    CLI (which wraps bwrap with progressive --level + cgroup caps). `--level
    enforce` => read-only root + one writable workspace; `--net` is added ONLY when
    the tier permits egress (so 'strict' stays no-net). This is the testable policy
    half; server.py owns the workspace mkdir + the actual exec.

<!-- mios-src:d8830dfbc1b1 from usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py:85-91 -->

### WS-A13 REFERENCE argv for a resolved SandboxProfile. NOT...

WS-A13 REFERENCE argv for a resolved SandboxProfile.

    NOT what runs. The executor is `usr/libexec/mios/mios-seccomp-filter` +
    `usr/libexec/mios/mios-sandbox-exec`, which builds its own flag set (narrower
    namespace unsharing, plus --cap-drop ALL and the T-230 --seccomp filter this
    function does not model). Read the wrapper, not this, for what a confined
    verb actually gets; reconciling the two is T-309. `cmd` is the verb's argv.
    Flags verified against bubblewrap docs (ArchWiki Bubblewrap/Examples):

      mechanism 'none'  -> NO wrapper: returns cmd unchanged (run direct).
      confined          -> bwrap --die-with-parent --new-session --unshare-all
                           [--share-net IFF profile.network] (no --share-net =>
                           --unshare-all already dropped the net namespace = no net),
                           --ro-bind / /  (read_only_root) | --bind / /  (else),
                           --proc /proc --dev /dev --tmpfs /tmp,
                           [--bind WS WS --chdir WS  IFF workspace given], -- CMD...

    --unshare-all isolates every namespace; --share-net re-adds only networking
    for tiers that need it. Later binds override earlier ones, so --ro-bind / /
    then --bind WS WS yields a read-only root with one writable workspace. The
    `--` ends bwrap's options so the verb's own argv is never mis-parsed.

<!-- mios-src:d0ba2b5efdbb from usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py:106-126 -->
