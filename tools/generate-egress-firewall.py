#!/usr/bin/env python3
# AI-hint: Generate the agent OUTBOUND egress nftables ruleset (#54 zero-trust federation).
# AI-related: usr/share/mios/security, usr/share/mios/mios.toml, usr/lib/systemd/system/mios-agent-pipe.service, tools/generate-k3s-manifests.sh
# AI-functions: agent_user, build_ruleset, main
#   Renders usr/share/mios/security/egress.nft from mios.toml [security.egress]
#   (mode + allow) and the agent-pipe service User= (SSOT, not hardcoded). The
#   ruleset is UID-scoped to the agent so it constrains ONLY the agent's external
#   egress -- loopback, tailnet, the local WSL gateway and the operator allowlist
#   are always permitted; everything else for that user is logged (audit) or
#   dropped (enforce). The OPERATOR applies it with `nft -f` -- this only
#   generates the artifact (default mode=off -> a no-op ruleset).
"""Generate the MiOS agent egress firewall (#54).

Zero-trust federation calls for an OUTBOUND firewall: a compromised or misled
agent must not be able to exfiltrate to arbitrary internet hosts. The correct
layer for that is the OS (nftables), scoped to the agent's uid -- an app-level
hook would be incomplete (httpx clients are constructed ad-hoc throughout the
orchestrator). This emits that ruleset from SSOT; the operator applies it.

It is uid-scoped, so it does not disturb other users: `web_search` keeps working
because the agent reaches searxng over loopback, and searxng (a different uid)
reaches the internet.
"""
from __future__ import annotations

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
TOML = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")
OUT = os.environ.get("MIOS_EGRESS_OUT") or os.path.join(
    ROOT, "usr/share/mios/security/egress.nft")
SERVICE = os.path.join(ROOT, "usr/lib/systemd/system/mios-agent-pipe.service")


def agent_user() -> str:
    """The agent-pipe service user (SSOT = its unit's User=); env override; default."""
    u = os.environ.get("MIOS_AGENT_USER")
    if u:
        return u.strip()
    try:
        for ln in open(SERVICE, encoding="utf-8"):
            if ln.startswith("User="):
                return ln.split("=", 1)[1].strip()
    except OSError:
        pass
    return "mios-ai"


def build_ruleset(mode: str, allow: "list[str]", user: str) -> str:
    if mode == "enforce":
        final = '        log prefix "mios-egress-drop " drop'
        note = "ENFORCE: the agent's non-allowed external egress is logged + DROPPED."
    elif mode == "audit":
        final = '        log prefix "mios-egress-audit " accept'
        note = "AUDIT: the agent's external egress is LOGGED then accepted (observe only)."
    else:
        mode = "off"
        final = "        accept   # mode=off -> no-op even if applied"
        note = "OFF: informational ruleset; applying it changes nothing."

    allow_rules = ""
    v4 = sorted(a for a in allow if ":" not in a)
    v6 = sorted(a for a in allow if ":" in a)
    if v4:
        allow_rules += f'        ip daddr {{ {", ".join(v4)} }} accept\n'
    if v6:
        allow_rules += f'        ip6 daddr {{ {", ".join(v6)} }} accept\n'

    return f"""# AI-hint: GENERATED nftables egress firewall for the MiOS agent (#54). DO NOT EDIT -- regenerate via tools/generate-egress-firewall.py. {note}
# Apply (operator step): nft -f usr/share/mios/security/egress.nft   |   Remove: nft delete table inet mios_egress
# mode={mode}  agent-user={user}  always-allowed: loopback + tailnet 100.64.0.0/10 + WSL gateway 172.16.0.0/12 + [security.egress].allow
table inet mios_egress {{
    chain output {{
        type filter hook output priority filter; policy accept;
        meta skuid != "{user}" accept
        oifname "lo" accept
        ip daddr 127.0.0.0/8 accept
        ip6 daddr ::1 accept
        ip daddr 100.64.0.0/10 accept
        ip daddr 172.16.0.0/12 accept
{allow_rules}{final}
    }}
}}
"""


def main() -> int:
    with open(TOML, "rb") as f:
        d = tomllib.load(f)
    eg = ((d.get("security") or {}).get("egress")) or {}
    mode = str(eg.get("mode", "off")).strip().lower()
    allow = [str(a).strip() for a in (eg.get("allow") or []) if str(a).strip()]
    user = agent_user()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_ruleset(mode, allow, user))
    print(f"[egress-fw] wrote {OUT} (mode={mode}, user={user}, allow={len(allow)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
