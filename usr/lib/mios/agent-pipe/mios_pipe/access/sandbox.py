# AI-hint: WS-A13 risk-tier dispatch-sandbox profile resolver. Pure-stdlib core that maps a verb's permission tier (read|write|interactive) to a Sandb...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_access_sandbox_py.md
"""mios_sandbox -- risk-tier dispatch sandbox profiles (WS-A13, the AIOS
Access-Manager confinement layer).

Pure stdlib. Every verb dispatch should run confined to the LEAST privilege its
risk tier needs; before WS-A13 there was no per-verb sandbox policy. This module
resolves a verb's permission tier -> a SandboxProfile (mechanism + workspace +
ro/net posture). It is deliberately FAIL-CLOSED: a security control must not
degrade-open, so an unknown tier (a typo, a new tier) maps to the STRICTEST
profile rather than 'none'. server.py runs the profile (bwrap/seccomp/podman +
the per-dispatch /var/lib/mios/ai/dispatch/<verbhash>-<uuid> workspace); this is
the testable decision.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Sequence

_TIER_PROFILE = {
    "read":        ("none",      False, False, True),
    "write":       ("workspace", True,  True,  True),
    "interactive": ("strict",    True,  True,  False),
}
_STRICT = ("strict", True, True, False)


class SandboxProfile:
    """The confinement a dispatch should run under."""

    __slots__ = ("tier", "mechanism", "workspace", "read_only_root", "network")

    def __init__(self, tier: str, mechanism: str, workspace: bool,
                 read_only_root: bool, network: bool) -> None:
        self.tier = str(tier)
        self.mechanism = str(mechanism)      # none | workspace | strict (server maps to bwrap/podman)
        self.workspace = bool(workspace)     # needs a per-dispatch writable dir
        self.read_only_root = bool(read_only_root)
        self.network = bool(network)

    @property
    def confined(self) -> bool:
        return self.mechanism != "none"

    def to_dict(self) -> dict:
        return {"tier": self.tier, "mechanism": self.mechanism,
                "workspace": self.workspace, "read_only_root": self.read_only_root,
                "network": self.network, "confined": self.confined}


def resolve_profile(permission_tier: str, *, explicit: Optional[str] = None,
                    tiers: Sequence[str] = ("read", "write", "interactive")) -> SandboxProfile:
    """Resolve the sandbox profile for a verb.

    `explicit` -- an [verbs.*].sandbox_profile override naming a tier-equivalent
    profile ("none"/"workspace"/"strict"); wins when set + recognised.
    Otherwise map `permission_tier` via the tier table. FAIL-CLOSED: an unknown
    tier (or unknown explicit) -> the STRICTEST profile, never 'none'."""
    if explicit:
        e = str(explicit).strip().lower()
        for tier, spec in _TIER_PROFILE.items():
            if e == spec[0] or e == tier:
                return SandboxProfile(tier, *spec)
        return SandboxProfile(f"explicit:{e}", *_STRICT)  # unknown override -> strict
    t = str(permission_tier or "").strip().lower()
    spec = _TIER_PROFILE.get(t)
    if spec is None:
        return SandboxProfile(t or "(none)", *_STRICT)
    return SandboxProfile(t, *spec)


def workspace_path(verb: str, uniq: str, *, base: str = "/var/lib/mios/ai/dispatch") -> str:
    """Per-dispatch writable workspace path: <base>/<verbhash>-<uniq>/. The verb
    is hashed (not embedded raw) so an odd verb name can't escape the base dir."""
    vh = hashlib.sha256(str(verb or "").encode()).hexdigest()[:12]
    safe_uniq = "".join(c for c in str(uniq or "") if c.isalnum() or c in "-_")[:36] or "0"
    return f"{base.rstrip('/')}/{vh}-{safe_uniq}"


def sandbox_exec_prefix(profile: "SandboxProfile", *,
                        workspace: Optional[str] = None,
                        level: str = "enforce",
                        exe: str = "mios-sandbox-exec") -> "list[str]":
    """The mios-sandbox-exec argv PREFIX (ending in '--') a confined profile maps
    to, or [] for an unconfined ('none') profile. server.py prepends this to a
    verb's broker command so a write/interactive verb runs under the MiOS sandbox
    CLI (which wraps bwrap with progressive --level + cgroup caps). `--level
    enforce` => read-only root + one writable workspace; `--net` is added ONLY when
    the tier permits egress (so 'strict' stays no-net). This is the testable policy
    half; server.py owns the workspace mkdir + the actual exec."""
    if not profile.confined:
        return []
    out = [exe, "--level", level]
    if profile.network:
        out.append("--net")
    if profile.workspace and workspace:
        out += ["--workspace", workspace]
    out.append("--")
    return out


def build_bwrap_argv(profile: "SandboxProfile", cmd: Sequence[str], *,
                     workspace: Optional[str] = None,
                     bwrap: str = "bwrap") -> "list[str]":
    """WS-A13 REFERENCE argv for a resolved SandboxProfile.

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
    `--` ends bwrap's options so the verb's own argv is never mis-parsed."""
    argv = list(cmd or [])
    if not profile.confined:
        return argv                               # 'none' tier -> run direct
    out = [bwrap, "--die-with-parent", "--new-session", "--unshare-all"]
    if profile.network:
        out.append("--share-net")
    out += (["--ro-bind", "/", "/"] if profile.read_only_root
            else ["--bind", "/", "/"])
    out += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    if profile.workspace and workspace:
        out += ["--bind", workspace, workspace, "--chdir", workspace]
    out.append("--")
    out += argv
    return out
