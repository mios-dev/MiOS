# AI-hint: Provenance-taint + Semantic Firewall plane extracted verbatim from server.py (refactor R7 wave). Lethal-trifecta defense: a session that ingested EXTERNAL/untrusted content (external open_url, powershell_run output, system-path text_view, taint-declaring MCP tools, or the SSOT-opt-in web-fetch verbs) gets its tool_call rows tainted, and _session_is_tainted lets the caller's firewall BLOCK downstream high-privilege + exfiltration verbs in the same session. Holds _is_external_url (allowlist-host classifier, fail-safe External), _classify_verb_taint (per-verb taint introducer; NAME-KEYED on _TAINT_VERBS + the open_url/powershell_run/text_view/mcp.* heuristics) and _session_is_tainted (the pg taint-chain reader). SECURITY-CRITICAL: every verb key, heuristic and set-membership is moved byte-for-byte -- a silent gate-disable is the worst regression. The SSOT-derived _TAINT_VERBS set, the PROVENANCE_TAINT_ENABLE flag, the _ALLOWLIST_HOSTS host set, the _MCP_CLIENT_TOOLS registry and the _db_read pg reader are dependency-INJECTED via configure() (one-way boundary -- mios_firewall NEVER imports server). server.py re-imports every name under its EXACT original alias so the importable surface stays byte-identical.
# AI-related: ./server.py, ./mios_secset.py, ./mios_pdp.py, ./mios_policy.py, ./test_mios_firewall.py
# AI-functions: _is_external_url, _classify_verb_taint, _session_is_tainted, configure
"""Provenance-taint + Semantic Firewall (lethal-trifecta defense).

Extracted verbatim from ``server.py``. A session that has ingested external /
untrusted content is BLOCKED (by the caller, using ``_session_is_tainted``) from
high-privilege + exfiltration verbs. The three moved functions are unchanged;
``server.py`` re-imports each under its original alias so the public surface is
byte-identical.

SECURITY-CRITICAL: the gates are NAME-KEYED on verb keys. Nothing is renamed and
no set is inlined -- the SSOT-derived always-taint verb set (``_TAINT_VERBS``,
built from ``mios_secset.taint_verb_set`` in server.py), the ``PROVENANCE_TAINT_ENABLE``
opt-in flag, the operator-infrastructure ``_ALLOWLIST_HOSTS`` host set, the
``_MCP_CLIENT_TOOLS`` registry and the ``_db_read`` pg taint-chain
reader are all dependency-injected via :func:`configure` (one-way module
boundary -- this module never imports ``server``).
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --------------------------------------
# server.py calls configure() with the SSOT-derived taint verb set, the
# provenance-taint opt-in flag, the allowlist-host set, the live MCP client-tool
# registry and the DB taint-chain reader AFTER every one is defined (the latest,
# _MCP_CLIENT_TOOLS, is defined well below the firewall functions). They stay at
# their documented defaults until injected; every consumer that reads them runs
# at request time so a standalone ``import mios_firewall`` still succeeds. The
# sets/dicts are injected BY REFERENCE (server assigns each exactly once and
# never rebinds), so the shared object stays live.

# SSOT-derived always-taint verb set (server: mios_secset.taint_verb_set(...) of
# the external-fetch verbs UNION [security].taint_verbs). NEVER inlined here.
_TAINT_VERBS: set = set()
# AIOS gap8 provenance/taint firewall opt-in flag (default OFF; server-derived
# from MIOS_SECURITY_PROVENANCE_TAINT / [security].provenance_taint).
PROVENANCE_TAINT_ENABLE = False
# operator-own-infrastructure host set (server: env CSV or compiled defaults).
_ALLOWLIST_HOSTS: set = set()
# live "mcp.<sid>.<tool>" -> tool metadata registry (carries per-tool taint=...).
_MCP_CLIENT_TOOLS: dict = {}
# pg taint-chain reader (server._db_read; async). None until injected.
_db_read = None
# System-path prefixes whose text_view READ taints the session (content the agent
# did not author). SSOT [security].text_view_taint_prefixes -- the SAME write-
# protected prefix set mios-text-edit enforces, so a tainting read and a denied
# write stay in lock-step. The tuple below is the documented vendor default and
# MUST match that SSOT seed; server.py injects the live value via configure().
_TEXT_VIEW_TAINT_PREFIXES: tuple = (
    "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/dev/",
    "/mnt/c/Windows/", "/mnt/c/Program Files/",
    "/mnt/c/Program Files (x86)/",
)
# Host suffixes treated as the operator's OWN (internal) infrastructure -- a URL
# whose host ends with one of these is NOT a taint source. SSOT
# [security].internal_tld_suffixes; the tuple below is the documented vendor
# default and MUST match that seed (injected live via configure()).
_INTERNAL_TLD_SUFFIXES: tuple = (".local", ".lan", ".internal")


def configure(*, taint_verbs=None, provenance_taint_enable=None,
              allowlist_hosts=None, mcp_client_tools=None, db_read=None,
              text_view_taint_prefixes=None, internal_tld_suffixes=None) -> None:
    """Inject server.py's SSOT-derived sets, the provenance flag and the DB
    reader under their EXACT original server-side global names.

    Injected via ``is not None`` guards so a falsey-but-real value (False, an
    empty set) still overrides the placeholder; the sets/dict are shared by
    reference so server-side mutation stays visible."""
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
    """Return True if the URL points OUTSIDE the operator's own
    infrastructure (i.e. a taint source). Best-effort host parse;
    anything ambiguous defaults to External (fail-safe)."""
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return False
        if host in _ALLOWLIST_HOSTS:
            return False
        # Treat the SSOT internal-TLD suffixes + plain hostnames (no dots) as
        # internal (operator-own infrastructure, not a taint source).
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
    # powershell_run output reflects Windows-side execution state
    # the agent didn't author -- treat as taint so subsequent high-
    # privilege verbs in the same session get firewall-checked.
    if tool == "powershell_run":
        return True, "powershell_output"
    # text_view of a system path (or any path under the write-
    # denied prefixes) reads content the agent didn't author, so
    # downstream high-priv verbs should be firewall-gated. The
    # denied-prefix list is the SAME SSOT one mios-text-edit uses
    # for write protection (injected via configure(), default in
    # sync), so the agent-pipe never shells out to look it up.
    if tool == "text_view":
        path = str((args or {}).get("path", ""))
        for prefix in _TEXT_VIEW_TAINT_PREFIXES:
            if path.startswith(prefix):
                return True, f"text_view_system:{prefix}"
    # P6 : an external MCP tool from a server that declares a taint
    # (e.g. Playwright taint=untrusted_web loads attacker-controllable HTML) taints the
    # session, so the Semantic Firewall then refuses downstream high-privilege / exfil
    # verbs -- closes the lethal trifecta for untrusted-web MCP servers.
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
    # The legacy backend requires ORDER BY fields to be in the SELECT
    # projection -- include `ts` even though we don't use it past the
    # ordering (parse error otherwise: "Missing order idiom `ts` in
    # statement selection").
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
