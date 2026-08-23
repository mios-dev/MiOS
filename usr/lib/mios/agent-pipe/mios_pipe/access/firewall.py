# AI-hint: Provenance-taint + Semantic Firewall plane extracted verbatim from server.py (refactor R7 wave).
# AI-doc: usr/share/doc/mios/manual/access.md

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger("mios-agent-pipe")



_TAINT_VERBS: set = set()
PROVENANCE_TAINT_ENABLE = False
_ALLOWLIST_HOSTS: set = set()
_MCP_CLIENT_TOOLS: dict = {}
_db_read = None
_TEXT_VIEW_TAINT_PREFIXES: tuple = (
    "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/dev/",
    "/mnt/c/Windows/", "/mnt/c/Program Files/",
    "/mnt/c/Program Files (x86)/",
)
_INTERNAL_TLD_SUFFIXES: tuple = (".local", ".lan", ".internal")


def configure(*, taint_verbs=None, provenance_taint_enable=None,
              allowlist_hosts=None, mcp_client_tools=None, db_read=None,
              text_view_taint_prefixes=None, internal_tld_suffixes=None) -> None:
    global _TAINT_VERBS, PROVENANCE_TAINT_ENABLE, _ALLOWLIST_HOSTS
    global _MCP_CLIENT_TOOLS, _db_read
    global _TEXT_VIEW_TAINT_PREFIXES, _INTERNAL_TLD_SUFFIXES
    if taint_verbs is not None: _TAINT_VERBS = taint_verbs
    if provenance_taint_enable is not None: PROVENANCE_TAINT_ENABLE = provenance_taint_enable
    if allowlist_hosts is not None: _ALLOWLIST_HOSTS = allowlist_hosts
    if mcp_client_tools is not None: _MCP_CLIENT_TOOLS = mcp_client_tools
    if db_read is not None: _db_read = db_read
    if text_view_taint_prefixes is not None:
        _TEXT_VIEW_TAINT_PREFIXES = tuple(text_view_taint_prefixes)
    if internal_tld_suffixes is not None:
        _INTERNAL_TLD_SUFFIXES = tuple(internal_tld_suffixes)


def _is_external_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        if host in _ALLOWLIST_HOSTS:
            return False
        if _INTERNAL_TLD_SUFFIXES and host.endswith(tuple(_INTERNAL_TLD_SUFFIXES)):
            return False
        if "." not in host:
            return False
        return True
    except Exception:
        return True  # fail-safe: ambiguous = treat as external


def _classify_verb_taint(tool: str, args: dict) -> tuple[bool, str]:
    """Decide whether a verb's OWN execution introduces taint.
    Returns (tainted, reason)."""
    if PROVENANCE_TAINT_ENABLE and tool in _TAINT_VERBS:   # WS-A14 SSOT-derived
        return True, f"{tool}_external"
    if tool == "open_url":
        url = str((args or {}).get("url", ""))
        if _is_external_url(url):
            return True, f"external_open_url:{url[:80]}"
    if tool == "powershell_run":
        return True, "powershell_output"
    if tool == "text_view":
        path = str((args or {}).get("path", ""))
        for prefix in _TEXT_VIEW_TAINT_PREFIXES:
            if path.startswith(prefix):
                return True, f"text_view_system:{prefix}"
    if tool.startswith("mcp."):
        _mt = str((_MCP_CLIENT_TOOLS.get(tool) or {}).get("taint") or "").strip()
        if _mt:
            return True, f"mcp_{_mt}:{tool}"
    return False, ""


async def _session_is_tainted(session_id: Optional[str]) -> tuple[bool, str]:
    """Look up whether the session has ANY prior tainted tool_call.
    Returns (tainted, reason_chain) where reason_chain summarises
    the upstream taint sources for the firewall event."""
    if not session_id:
        return False, ""
    sql = (
        f"SELECT ts, tool, taint_reason FROM tool_call "
        f"WHERE session = {session_id} AND tainted = true "
        f"ORDER BY ts ASC LIMIT 5;"
    )
    r = await _db_read(sql, pg_sql=(
        "SELECT ts, tool, taint_reason FROM tool_call "
        "WHERE session_id = %(sid)s AND tainted = true "
        "ORDER BY ts ASC LIMIT 5"), pg_params={"sid": session_id})
    if not r:
        return False, ""
    rows = (r[-1] or {}).get("result") or []
    if not rows:
        return False, ""
    chain = "; ".join(
        f"{row.get('tool','?')}:{row.get('taint_reason','')}"
        for row in rows
    )
    return True, chain[:300]
