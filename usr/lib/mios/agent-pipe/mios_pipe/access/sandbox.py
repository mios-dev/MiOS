# AI-hint: WS-A13 risk-tier dispatch-sandbox profile resolver. Pure-stdlib core that maps a verb's permission tier (read|write|interactive) to a Sandb...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_access_sandbox_py.md

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
