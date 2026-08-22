<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Provenance-taint + Semantic Firewall (lethal-trifecta...

Provenance-taint + Semantic Firewall (lethal-trifecta defense).

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

<!-- mios-src:93bab5862ce1 from usr/lib/mios/agent-pipe/mios_pipe/access/firewall.py:3-18 -->

### Inject server.py's SSOT-derived sets, the provenance flag...

Inject server.py's SSOT-derived sets, the provenance flag and the DB
    reader under their EXACT original server-side global names.

    Injected via ``is not None`` guards so a falsey-but-real value (False, an
    empty set) still overrides the placeholder; the sets/dict are shared by
    reference so server-side mutation stays visible.

<!-- mios-src:f5e7d99606f6 from usr/lib/mios/agent-pipe/mios_pipe/access/firewall.py:45-50 -->

### Return True if the URL points OUTSIDE the operator's own...

Return True if the URL points OUTSIDE the operator's own
    infrastructure (i.e. a taint source). Best-effort host parse;
    anything ambiguous defaults to External (fail-safe).

<!-- mios-src:236778cb0e43 from usr/lib/mios/agent-pipe/mios_pipe/access/firewall.py:66-68 -->
