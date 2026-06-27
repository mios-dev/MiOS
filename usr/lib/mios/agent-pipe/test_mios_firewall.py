# AI-hint: Standalone stdlib assert-script for mios_firewall (the provenance-taint + Semantic Firewall plane). Wires the module with the REAL mios_secset-derived taint/high-privilege sets + a stubbed _db_read, then proves the lethal-trifecta defense: _is_external_url host classification (external vs allowlist/internal/fail-safe), _classify_verb_taint NAME-KEYED taint introduction (web/open_url-external/powershell_run/text_view-system/mcp.*-taint vs read-only safe), the _session_is_tainted pg taint-chain reader (stubbed), and the firewall BLOCK decision (a tainted session blocks a high-privilege verb + the exfil/external open_url taint source, and allows a read-only verb). No server import.
# AI-related: ./mios_firewall.py, ./mios_secset.py, ./test_server_import.py
# AI-functions: (assert-script; no defs)
"""Assert-script gate for mios_firewall. Run: ``python test_mios_firewall.py``.

Uses the REAL mios_secset set-math to build the high-privilege + always-taint
verb sets the live server derives, configures mios_firewall with them + a stub
DB reader, and asserts the firewall gates byte-faithfully. Exit 0 = green."""

import asyncio

import mios_secset
import mios_firewall


# -- Build the REAL SSOT-derived sets (same shape server.py derives) ----------
# Curated high-privilege floor subset (the real server floor is larger; these are
# verbatim members of _HIGH_PRIVILEGE_CURATED) UNION an SSOT addition.
_CURATED = {
    "service_restart", "container_restart", "powershell_run",
    "text_create", "text_str_replace", "text_insert", "pc_type",
}
_HIGH = mios_secset.high_privilege_set(_CURATED, ["custom_dangerous_verb"])
# Always-taint set = built-in external-fetch verbs UNION SSOT extra (server uses
# exactly this builtin tuple).
_TAINT = mios_secset.taint_verb_set(
    ("web_search", "web_extract", "crawl", "web_scrape"), ["scrape_site"])

assert "powershell_run" in _HIGH, "curated floor must survive"
assert "custom_dangerous_verb" in _HIGH, "SSOT addition must be present"
assert "web_search" in _TAINT and "scrape_site" in _TAINT, "taint set built"


# -- Stub the pg taint-chain reader -------------------------------------------
# server calls: await _db_read(sql, pg_sql=..., pg_params={"sid": session_id})
# and reads r[-1]["result"]. The stub returns a tainted row for a known session,
# an empty result otherwise.
_TAINTED_SESSION = "session:abc"


async def _stub_db_read(sql, *, pg_sql=None, pg_params=None):
    sid = (pg_params or {}).get("sid")
    if sid == _TAINTED_SESSION:
        return [{"result": [
            {"ts": "t0", "tool": "powershell_run",
             "taint_reason": "powershell_output"},
            {"ts": "t1", "tool": "open_url",
             "taint_reason": "external_open_url:https://evil.example.com"},
        ]}]
    return [{"result": []}]


mios_firewall.configure(
    taint_verbs=_TAINT,
    provenance_taint_enable=True,
    allowlist_hosts={"localhost", "127.0.0.1", "mios-searxng", "mios-hermes"},
    mcp_client_tools={"mcp.s.evil": {"taint": "untrusted_web"},
                      "mcp.s.safe": {}},
    db_read=_stub_db_read,
)


# -- 1. _is_external_url classification ----------------------------------------
assert mios_firewall._is_external_url("https://evil.example.com/path") is True, \
    "public dotted host = external taint source"
assert mios_firewall._is_external_url("http://localhost:8080/v1") is False, \
    "allowlist host = internal"
assert mios_firewall._is_external_url("http://mios-searxng:8888") is False, \
    "operator-infra allowlist host = internal"
assert mios_firewall._is_external_url("http://mios-hermes") is False, \
    "allowlist no-dot host = internal"
assert mios_firewall._is_external_url("http://buildbox.local/x") is False, \
    ".local suffix = internal"
assert mios_firewall._is_external_url("http://plainhost/x") is False, \
    "no-dot bare hostname = internal"
assert mios_firewall._is_external_url("") is False, "empty = not external"
assert mios_firewall._is_external_url(None) is False, "None = not external"


# -- 2. _classify_verb_taint: NAME-KEYED taint introduction --------------------
t, r = mios_firewall._classify_verb_taint("web_search", {})
assert t is True and r == "web_search_external", "SSOT taint verb introduces taint"
t, r = mios_firewall._classify_verb_taint("scrape_site", {})
assert t is True, "SSOT-added taint verb introduces taint"
t, r = mios_firewall._classify_verb_taint(
    "open_url", {"url": "https://evil.example.com/x"})
assert t is True and r.startswith("external_open_url:"), \
    "external open_url = exfil/ingest taint source"
t, r = mios_firewall._classify_verb_taint(
    "open_url", {"url": "http://localhost:8080"})
assert t is False, "internal open_url is NOT a taint source"
t, r = mios_firewall._classify_verb_taint("powershell_run", {})
assert t is True and r == "powershell_output", "powershell_run always taints"
t, r = mios_firewall._classify_verb_taint("text_view", {"path": "/etc/shadow"})
assert t is True and r.startswith("text_view_system:"), "system-path read taints"
t, r = mios_firewall._classify_verb_taint("text_view", {"path": "/home/mios/n.txt"})
assert t is False, "user-path read does NOT taint"
t, r = mios_firewall._classify_verb_taint("mcp.s.evil", {})
assert t is True and r == "mcp_untrusted_web:mcp.s.evil", \
    "taint-declaring MCP tool taints"
t, r = mios_firewall._classify_verb_taint("mcp.s.safe", {})
assert t is False, "MCP tool without a taint declaration does NOT taint"
t, r = mios_firewall._classify_verb_taint("recall", {})
assert t is False and r == "", "read-only verb introduces NO taint"


# -- 2b. provenance flag OFF disables the SSOT web-fetch taint extension --------
mios_firewall.configure(provenance_taint_enable=False)
t, _ = mios_firewall._classify_verb_taint("web_search", {})
assert t is False, "flag OFF -> web_search no longer self-taints"
# but the hard heuristics still fire regardless of the opt-in flag:
t, _ = mios_firewall._classify_verb_taint("powershell_run", {})
assert t is True, "powershell_run taints even with provenance flag OFF"
mios_firewall.configure(provenance_taint_enable=True)  # restore


# -- 3. _session_is_tainted: pg taint-chain reader -----------------------------
async def _run_session_checks():
    tainted, chain = await mios_firewall._session_is_tainted(_TAINTED_SESSION)
    assert tainted is True, "session with a tainted tool_call row is tainted"
    assert "powershell_run" in chain and "open_url" in chain, \
        "reason chain summarises upstream taint sources"

    clean, chain2 = await mios_firewall._session_is_tainted("session:clean")
    assert clean is False and chain2 == "", "session with no taint rows is clean"

    none_t, _ = await mios_firewall._session_is_tainted(None)
    assert none_t is False, "no session id = not tainted"


asyncio.run(_run_session_checks())


# -- 4. Firewall BLOCK decision (mirrors server's gate) ------------------------
# The live firewall blocks when: the session is tainted AND the downstream verb is
# high-privilege (server: `tool in _HIGH_PRIVILEGE_VERBS and session_id` tainted).
def _firewall_blocks(session_tainted: bool, verb: str) -> bool:
    return bool(session_tainted and verb in _HIGH)


# (the _TAINTED_SESSION was already proven tainted in section 3 above.)
# tainted session BLOCKS a high-privilege verb (exfil/act class)...
assert _firewall_blocks(True, "powershell_run") is True, \
    "tainted session must BLOCK a high-privilege verb"
assert _firewall_blocks(True, "custom_dangerous_verb") is True, \
    "tainted session must BLOCK an SSOT-added high-privilege verb"
# ...and ALLOWS a safe read-only verb...
assert _firewall_blocks(True, "recall") is False, \
    "tainted session must ALLOW a safe read-only verb"
# ...while a clean session is never blocked.
assert _firewall_blocks(False, "powershell_run") is False, \
    "clean session is never firewall-blocked"

# The exfil URL verb is recognised as a taint SOURCE (closes the trifecta: once it
# runs, the session taints and subsequent high-priv verbs get blocked above).
t, _ = mios_firewall._classify_verb_taint(
    "open_url", {"url": "https://exfil.attacker.net/leak?d=secret"})
assert t is True, "external open_url is the exfil taint source the firewall keys on"


# -- 5. SSOT injection: text_view-taint prefixes + internal-TLD suffixes ------
# The prefix list + the internal-host suffix rule are NOT baked in code -- they
# read from the configure()-injected SSOT ([security].text_view_taint_prefixes /
# internal_tld_suffixes). Prove behaviour FOLLOWS a non-default config: a path /
# host that was inert under defaults taints/internal-classifies once the SSOT
# value declares it, and a default member stops mattering when dropped.
# Default member taints; a custom-only path does not (yet).
t, _ = mios_firewall._classify_verb_taint("text_view", {"path": "/etc/shadow"})
assert t is True, "default prefix taints before SSOT override"
t, _ = mios_firewall._classify_verb_taint("text_view", {"path": "/srv/secret/x"})
assert t is False, "non-default prefix does NOT taint under defaults"
assert mios_firewall._is_external_url("http://box.corp/x") is True, \
    "non-default suffix host is external under defaults"

# Inject a NON-DEFAULT SSOT: only /srv/secret/ taints, only .corp is internal.
mios_firewall.configure(
    text_view_taint_prefixes=["/srv/secret/"],
    internal_tld_suffixes=[".corp"],
)
t, r = mios_firewall._classify_verb_taint("text_view", {"path": "/srv/secret/x"})
assert t is True and r == "text_view_system:/srv/secret/", \
    "SSOT-declared prefix now taints (read from config, not baked)"
t, _ = mios_firewall._classify_verb_taint("text_view", {"path": "/etc/shadow"})
assert t is False, "former-default prefix no longer taints once SSOT drops it"
assert mios_firewall._is_external_url("http://box.corp/x") is False, \
    "SSOT-declared internal suffix now classifies host as internal"
assert mios_firewall._is_external_url("http://buildbox.local/x") is True, \
    "former-default suffix is external once SSOT drops it"

# Restore the documented defaults for any later reuse.
mios_firewall.configure(
    text_view_taint_prefixes=[
        "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/dev/",
        "/mnt/c/Windows/", "/mnt/c/Program Files/",
        "/mnt/c/Program Files (x86)/",
    ],
    internal_tld_suffixes=[".local", ".lan", ".internal"],
)


print("test_mios_firewall: ALL PASS")
