# AI-hint: WS-A13 risk-tier dispatch-sandbox profile resolver. Pure-stdlib core that maps a verb's permission tier (read|write|interactive) to a SandboxProfile -- the confinement (mechanism + writable workspace + read-only/network posture) the dispatch chokepoint should run the verb under. read -> none (pure info), write -> a per-dispatch writable workspace with the rest read-only, interactive -> the strictest isolation (bwrap/podman, no net). FAIL-CLOSED (security-sensitive, NOT degrade-open): an unknown/missing tier resolves to the STRICTEST profile, never 'none'. server.py owns the actual confinement (bwrap/seccomp/podman) + the workspace tmpfiles; this module owns only the deterministic policy so it unit-tests in isolation.
# AI-related: ./server.py, ./mios_pdp.py, /usr/share/mios/mios.toml, /var/lib/mios/ai/dispatch, ./test_mios_sandbox.py
# AI-functions: resolve_profile, workspace_path, class SandboxProfile
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

# tier -> (mechanism, writable_workspace, read_only_root, network)
# read        : pure info verb -> no sandbox needed.
# write       : may touch the fs -> a per-dispatch writable workspace, rest RO.
# interactive : highest risk -> strict isolation, no network.
_TIER_PROFILE = {
    "read":        ("none",      False, False, True),
    "write":       ("workspace", True,  True,  True),
    "interactive": ("strict",    True,  True,  False),
}
# The strictest profile -- the fail-closed target for an unknown tier.
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
        # Unknown/missing tier -> fail CLOSED to the strictest confinement.
        return SandboxProfile(t or "(none)", *_STRICT)
    return SandboxProfile(t, *spec)


def workspace_path(verb: str, uniq: str, *, base: str = "/var/lib/mios/ai/dispatch") -> str:
    """Per-dispatch writable workspace path: <base>/<verbhash>-<uniq>/. The verb
    is hashed (not embedded raw) so an odd verb name can't escape the base dir."""
    vh = hashlib.sha256(str(verb or "").encode()).hexdigest()[:12]
    safe_uniq = "".join(c for c in str(uniq or "") if c.isalnum() or c in "-_")[:36] or "0"
    return f"{base.rstrip('/')}/{vh}-{safe_uniq}"
