# AI-hint: VERB/RECIPE CATALOG loader + 3-projection SSOT source, extracted verbatim from server.py (refactor R2 leaf wave). Parses mios.toml [verbs.*]/[recipes.*] into the canonical catalogs (_load_verb_catalog / _load_recipe_catalog) and projects them three ways -- planner prose (_render_verb_catalog / _render_recipe_catalog), OpenAI/MCP function-tool schemas (_verb_to_openai_tool / _recipe_to_openai_tool), and the model_name/hidden_alias reverse map (_build_model_name_map -> _resolve_verb_key) -- plus the per-arg synonym projection (_verb_arg_synonyms_from_catalog / _load_verb_arg_synonyms) and the deterministic identity reply (_identity_answer). Config (CATALOG_FAIL_MODE) and the HOT server-owned globals _VERB_CATALOG / _MODEL_NAME_TO_VERB are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server); server.py keeps OWNERSHIP of those global assignments (it calls the re-imported builders) so the many existing configure(verb_catalog=_VERB_CATALOG) injections across siblings stay valid. _capability_grounding is imported directly from the mios_grounding sibling. server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). NO hardcoded topics/keywords -- everything re-derives from the live mios.toml SSOT.
# AI-related: ./server.py, ./mios_config.py, ./mios_grounding.py, ./test_mios_verbcatalog.py
# AI-functions: _load_verb_catalog, _verb_arg_synonyms_from_catalog, _render_verb_catalog, _identity_answer, _load_verb_arg_synonyms, _build_model_name_map, _resolve_verb_key, _load_recipe_catalog, _render_recipe_catalog, _recipe_to_openai_tool, _verb_to_openai_tool, configure
"""Verb/recipe catalog loader + the three-projection SSOT source.

Extracted verbatim from ``server.py``. Parses the ``mios.toml`` ``[verbs.*]`` and
``[recipes.*]`` sections into the canonical catalogs and projects them into the
planner prose block, the OpenAI/MCP function-tool schemas, and the model_name /
hidden_alias reverse map. Every function is moved byte-for-byte; ``server.py``
re-imports each under its original ``_``-prefixed name so the importable surface
is unchanged.

The HOT globals ``_VERB_CATALOG`` and ``_MODEL_NAME_TO_VERB`` are OWNED by
``server.py`` (it runs the assignments by calling the re-imported builders) and
injected here via :func:`configure` AFTER they are built, so the catalog readers
(``_resolve_verb_key``, ``_identity_answer``, ``_load_verb_arg_synonyms``) see the
live catalog. ``CATALOG_FAIL_MODE`` is injected before the first catalog build.
One-way module boundary: this module never imports ``server``.
"""

from __future__ import annotations

import logging
import os
import re

from mios_grounding import _capability_grounding

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --
# The HOT verb-catalog globals stay OWNED by server.py (it runs the assignments
# by calling the re-imported builders); they are injected here AFTER server builds
# them so the readers below see the live catalog. CATALOG_FAIL_MODE (the malformed-
# catalog fail-loud opt-in) is injected before the first build. These stay at their
# defaults until configure() is called, so a standalone import still succeeds.
_VERB_CATALOG: dict = {}
_MODEL_NAME_TO_VERB: dict = {}
CATALOG_FAIL_MODE = "warn"


_INJECTED = frozenset((
    "_VERB_CATALOG", "_MODEL_NAME_TO_VERB", "CATALOG_FAIL_MODE",
))


def configure(**deps) -> None:
    """Inject the server-owned catalog globals + config under their EXACT original
    names (one-way boundary). Called from ``server.py``: once early to inject
    ``CATALOG_FAIL_MODE`` before the first catalog build, then again after
    ``_VERB_CATALOG`` / ``_MODEL_NAME_TO_VERB`` are built. Partial injection is fine
    -- only the keys present in ``deps`` (and in ``_INJECTED``) are set."""
    g = globals()
    for _k, _v in deps.items():
        if _k in _INJECTED:
            g[_k] = _v


def _load_verb_catalog() -> dict:
    """Parse mios.toml [verbs.*] sections into the canonical verb
    catalog. Each entry: {section, sig, desc, tier, permission, params:
    {<arg>: {type, desc, aliases, enum, default}}}. SSOT for the planner
    prompt + the arg-synonym dispatcher + (future) MCP tools/list."""
    global _DB_UNREACHABLE
    cat: dict = {}
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        verbs = data.get("verbs") or {}
        defaults = verbs.get("_defaults") or {}
        if isinstance(verbs, dict):
            for vname, vcfg in verbs.items():
                if vname == "_defaults":
                    continue
                if not isinstance(vcfg, dict):
                    continue
                merged_vcfg = defaults.copy()
                merged_vcfg.update(vcfg)
                vcfg = merged_vcfg
                # Reject entries lacking `section` -- the [verbs.*]
                # namespace is shared with the mios-html configurator
                # (build/config/dash/ai/dev/...) which uses the same
                # TOML key for UI button definitions. agent-pipe owns
                # only the entries that carry the agent-verb shape.
                if "section" not in vcfg:
                    continue
                cat[vname] = {
                    "section":    str(vcfg.get("section", "Misc")),
                    "sig":        str(vcfg.get("sig", "")),
                    "desc":       str(vcfg.get("desc", "")),
                    "tier":       str(vcfg.get("tier", "common")),
                    "permission": str(vcfg.get("permission", "read")),
                    "params":     vcfg.get("params") or {},
                    # SSOT command template (P3): when present, the dispatch
                    # builder renders THIS instead of a hardcoded branch.
                    "cmd":        str(vcfg.get("cmd", "") or ""),
                    # Per-verb result cap (SSOT): inventory/discovery verbs
                    # legitimately return LONG lists (mios_apps' full app+game
                    # inventory is ~27KB) that the default READ_TOOL_ENRICH_CHARS
                    # (1500) truncated -- dropping the games section entirely
                    # ("list ALL my games" returned 2/11).
                    # 0 -> use the default cap.
                    "max_result_chars": int(vcfg.get("max_result_chars", 0) or 0),
                    # P1 PA-Tool : optional MODEL-FACING name alias. The
                    # model sees `model_name` (a lexically-unambiguous, pretraining-
                    # familiar name) while the internal KEY (vname) stays canonical for
                    # dispatch/recipes/A2A/routing. Empty -> the model sees the key.
                    # Resolved back to the key via _MODEL_NAME_TO_VERB / _resolve_verb_key.
                    "model_name": str(vcfg.get("model_name", "") or "").strip(),
                    # P1 TDWA: synthetic example user-queries appended to the verb's
                    # retrieval EMBEDDING text (NOT shown to the model) to sharpen the
                    # cosine tool selection. Embedded by _ensure_verb_embeddings.
                    "examples": [str(x).strip() for x in (vcfg.get("examples") or [])
                                 if str(x).strip()],
                    # P1: legacy deadweight (e.g. the flatpak_/winget_ verbs superseded
                    # by `pkg`). Dropped from the model-facing surface (_worker_tools_*)
                    # but still PARSED + dispatchable so any in-flight caller keeps working.
                    "hidden": bool(vcfg.get("hidden", False)),
                    # Old verb names this verb ABSORBED during consolidation. Each
                    # resolves to this key via _resolve_verb_key (back-compat for
                    # in-flight chains, DAG/skill step bodies, and MCP/A2A callers) but
                    # NEVER renders on the model / MCP / A2A surface (it is neither a verb
                    # key nor a model_name). This lets a redundant verb block be DELETED
                    # outright while its old name still dispatches. No hardcoded keywords.
                    "hidden_aliases": [str(x).strip()
                                       for x in (vcfg.get("hidden_aliases") or [])
                                       if str(x).strip()],
                    # WS-A7 Tool-Manager serialization (SSOT, both optional):
                    #   parallel_limit -- max concurrent dispatches of THIS verb
                    #     (>=1; e.g. 1 = strictly single-flight). 0/absent = unbounded.
                    #   conflict_group -- named mutual-exclusion set: all verbs
                    #     sharing the group run one-at-a-time (e.g. open_app /
                    #     focus_window / pc_type all contend for the one foreground
                    #     window + keyboard, so a fan-out must not interleave them).
                    "parallel_limit": int(vcfg.get("parallel_limit", 0) or 0),
                    "conflict_group": str(vcfg.get("conflict_group", "") or "").strip(),
                }
    except Exception as e:
        log.warning("verb catalog load failed: %s", e)
        if CATALOG_FAIL_MODE == "fail":   # WS-A1 fail-loud (opt-in)
            raise

    db_auth = False
    try:
        import sys
        if "/usr/lib/mios" not in sys.path:
            sys.path.insert(0, "/usr/lib/mios")
        import mios_db_config
        db_auth = mios_db_config.is_db_authoritative()
    except Exception:
        pass

    import copy
    pure_toml_cat = copy.deepcopy(cat)

    # ── Database Overlay & Localization (T-126) ──
    if db_auth and not _DB_UNREACHABLE:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from mios_pipe.memory.pg import pg_config
            cfg = pg_config()
            conn_str = (f"postgresql://{cfg['user']}:{cfg['password']}"
                        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}")
            
            locale = os.environ.get("MIOS_LOCALE") or os.environ.get("LANG", "en")
            lang = locale.split("_")[0].split(".")[0].lower()
            
            with psycopg.connect(conn_str, connect_timeout=2) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute("SELECT * FROM verb;")
                    rows = cur.fetchall()
                    for r in rows:
                        vname = r["name"]
                        if not r["is_active"]:
                            cat.pop(vname, None)
                            continue
                        
                        sig = r["sig"]
                        desc = r["desc_default"]
                        tier = r["tier"]
                        permission = r["permission"]
                        cmd = r["cmd"] or ""
                        params = r["params"] or {}
                        
                        i18n = r["i18n"] or {}
                        if lang in i18n:
                            lang_data = i18n[lang]
                            if "desc" in lang_data:
                                desc = lang_data["desc"]
                            if "params" in lang_data:
                                lang_params = lang_data["params"]
                                for arg, arg_cfg in params.items():
                                    if isinstance(arg_cfg, dict) and arg in lang_params:
                                        arg_cfg["desc"] = lang_params[arg]
                                        
                        if vname in cat:
                            cat[vname].update({
                                "sig": sig,
                                "desc": desc,
                                "tier": tier,
                                "permission": permission,
                                "cmd": cmd,
                                "params": params
                            })
                        else:
                            cat[vname] = {
                                "section": "Misc",
                                "sig": sig,
                                "desc": desc,
                                "tier": tier,
                                "permission": permission,
                                "params": params,
                                "cmd": cmd,
                                "max_result_chars": 0,
                                "model_name": "",
                                "examples": [],
                                "hidden": False,
                                "hidden_aliases": [],
                                "parallel_limit": 0,
                                "conflict_group": "",
                            }
        except Exception as db_err:
            _DB_UNREACHABLE = True
            log.debug("Database verb catalog overlay failed (using TOML baseline): %s", db_err)

    # ── Database Authority Sentinel & Shadow-Compare ──
    try:
        db_cat = _load_verb_catalog_from_db()
        
        if db_auth:
            if db_cat:
                return db_cat
            # Else fall-open to TOML
            return cat
        else:
            if db_cat:
                if not _compare_catalogs(pure_toml_cat, db_cat):
                    import mios_db_config
                    mios_db_config.DIVERGENCES += 1
                    log.warning("Verb catalog divergence detected between TOML/Overlay and DB")
    except Exception as sentinel_err:
        log.debug("sentinel check or shadow-compare failed: %s", sentinel_err)

    return cat


_DB_UNREACHABLE = False


def _load_verb_catalog_from_db() -> dict:
    global _DB_UNREACHABLE
    if _DB_UNREACHABLE:
        return {}
    import json
    cat: dict = {}
    try:
        import psycopg
        from psycopg.rows import dict_row
        from mios_pipe.memory.pg import pg_config
        cfg = pg_config()
        conn_str = (f"postgresql://{cfg['user']}:{cfg['password']}"
                    f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}")
        
        locale = os.environ.get("MIOS_LOCALE") or os.environ.get("LANG", "en")
        lang = locale.split("_")[0].split(".")[0].lower()
        
        defaults = {}
        with psycopg.connect(conn_str, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT value FROM config_kv
                    WHERE scope = 'verbs' AND key = '_defaults' AND layer = 0;
                    """
                )
                def_row = cur.fetchone()
                if def_row:
                    defaults = def_row[0]
                    if isinstance(defaults, str):
                        try:
                            defaults = json.loads(defaults)
                        except Exception:
                            defaults = {}

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM verb ORDER BY name;")
                rows = cur.fetchall()
                for r in rows:
                    vname = r["name"]
                    if not r["is_active"]:
                        continue
                    if not r.get("section"):
                        continue
                    
                    vcfg = defaults.copy()
                    sig = r.get("sig")
                    desc = r.get("desc_default")
                    tier = r.get("tier")
                    permission = r.get("permission")
                    cmd = r.get("cmd")
                    params = r.get("params")
                    section = r.get("section")
                    examples = r.get("examples")
                    model_name = r.get("model_name")
                    hidden = r.get("hidden")
                    aliases = r.get("aliases")
                    conflict_group = r.get("conflict_group")
                    parallel_limit = r.get("parallel_limit")
                    max_result_chars = r.get("max_result_chars")
                    
                    # Localization (T-126)
                    i18n = r.get("i18n") or {}
                    if lang in i18n:
                        lang_data = i18n[lang]
                        if "desc" in lang_data:
                            desc = lang_data["desc"]
                        if "params" in lang_data:
                            lang_params = lang_data["params"]
                            for arg, arg_cfg in (params or {}).items():
                                if isinstance(arg_cfg, dict) and arg in lang_params:
                                    arg_cfg["desc"] = lang_params[arg]

                    vcfg.update({
                        "section":    str(section or "Misc"),
                        "sig":        str(sig or ""),
                        "desc":       str(desc or ""),
                        "tier":       str(tier or "common"),
                        "permission": str(permission or "read"),
                        "params":     params or {},
                        "cmd":        str(cmd or ""),
                        "max_result_chars": int(max_result_chars or 0),
                        "model_name": str(model_name or "").strip(),
                        "examples": [str(x).strip() for x in (examples or [])
                                     if str(x).strip()],
                        "hidden": bool(hidden),
                        "hidden_aliases": [str(x).strip()
                                           for x in (aliases or [])
                                           if str(x).strip()],
                        "parallel_limit": int(parallel_limit or 0),
                        "conflict_group": str(conflict_group or "").strip(),
                    })
                    cat[vname] = vcfg
    except Exception as e:
        _DB_UNREACHABLE = True
        log.debug("Failed to load verb catalog from DB: %s", e)
        return {}
    return cat


def _normalize_verb_catalog_entry(vcfg: dict) -> dict:
    import copy
    v = copy.deepcopy(vcfg)
    for key in ("sig", "desc", "cmd", "section", "model_name", "conflict_group"):
        val = v.get(key)
        if val == "" or val is None:
            v[key] = None
        else:
            v[key] = str(val).strip()
    for key in ("examples", "hidden_aliases", "aliases"):
        val = v.get(key)
        if not val:
            v[key] = None
        else:
            v[key] = [str(x).strip() for x in val if str(x).strip()]
            if not v[key]:
                v[key] = None
    if "params" in v:
        if not v["params"]:
            v["params"] = None
    v["hidden"] = bool(v.get("hidden"))
    v["parallel_limit"] = int(v.get("parallel_limit") or 0)
    v["max_result_chars"] = int(v.get("max_result_chars") or 0)
    if "aliases" in v:
        v["hidden_aliases"] = v.pop("aliases")
    return v


def _compare_catalogs(toml_cat: dict, db_cat: dict) -> bool:
    for vname in set(toml_cat.keys()) | set(db_cat.keys()):
        if vname not in toml_cat:
            log.warning("Verb '%s' exists in DB but not in TOML", vname)
            return False
        if vname not in db_cat:
            log.warning("Verb '%s' exists in TOML but not in DB", vname)
            return False
        toml_v = _normalize_verb_catalog_entry(toml_cat[vname])
        db_v = _normalize_verb_catalog_entry(db_cat[vname])
        if toml_v != db_v:
            log.warning("Verb '%s' differences: TOML=%s, DB=%s", vname, toml_v, db_v)
            return False
    return True


def _verb_arg_synonyms_from_catalog(cat: dict) -> dict:
    """Project verb catalog's per-arg `aliases` lists into the legacy
    {verb: {arg: [alias,...]}} shape `_arg_with_synonyms` consumes.
    Single SSOT (catalog) -- no separate [verbs.<name>.synonyms] block."""
    syn: dict = {}
    for vname, vcfg in cat.items():
        params = vcfg.get("params") or {}
        if not isinstance(params, dict):
            continue
        for argname, argcfg in params.items():
            if not isinstance(argcfg, dict):
                continue
            aliases = argcfg.get("aliases") or []
            if aliases:
                syn.setdefault(vname, {})[str(argname)] = [str(a) for a in aliases]
    return syn


def _render_verb_catalog(cat: dict, include_rare: bool = True) -> str:
    """Render the verb catalog as the prose block the planner consumes.
    Sections grouped + ordered by first-seen order. Verbs tagged
    tier='rare' are HIDDEN by default -- they remain dispatchable for
    in-flight chains but don't burn planner tokens. Set include_rare=
    True for a full audit."""
    sections: dict[str, list[str]] = {}
    order: list[str] = []
    for vname, vcfg in cat.items():
        if not include_rare and vcfg.get("tier") == "rare":
            continue
        sec = vcfg.get("section", "Misc")
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        sig = vcfg.get("sig", "")
        desc = vcfg.get("desc", "")
        line = f"  {vname}({sig})".ljust(48) + f"-- {desc}"
        sections[sec].append(line)
    parts: list[str] = []
    for sec in order:
        parts.append(f"  -- {sec} --")
        parts.extend(sections[sec])
        parts.append("")
    return "\n".join(parts).rstrip()


def _identity_answer() -> str:
    """Deterministic reply to "who are you / what can you do", built from the LIVE
 capability catalog + a generic persona intro (the 14B
    confabulated its identity from the literal model name -- "Zabbix agent",
    "Mio's Pizza" -- and varied wildly run to run, because a small model cannot be
    trusted to self-describe). Composed deterministically, like the `remember`
    handler. All specifics come from _VERB_CATALOG (the mios.toml [verbs.*] SSOT),
    so the reply is accurate AND baked: a freshly-imaged Day-0 agent describes
    itself correctly with zero chat history. Returns '' if no catalog is loaded."""
    cap = _capability_grounding(_VERB_CATALOG)
    if not cap:
        return ""
    body = cap.split(":\n", 1)[1].strip() if ":\n" in cap else ""
    intro = ("I'm **MiOS-Agent**, the local AI assistant built into MiOS. I'm not "
             "just a chatbot: I run on a local model and can act on this system "
             "through a live tool surface, and I answer from real tool results, the "
             "web, and facts you've asked me to remember -- not guesswork.")
    if not body:
        return intro
    return (intro + "\n\nHere's my actual capability surface on this system, by "
            "area:\n\n" + body + "\n\nJust ask in plain English and I'll pick the "
            "right tools to do it.")


def _load_verb_arg_synonyms() -> dict:
    """Compat shim -- existing callers still hit this name."""
    return _verb_arg_synonyms_from_catalog(_VERB_CATALOG)


def _build_model_name_map(cat: dict) -> dict:
    """P1 PA-Tool reverse map {model_name -> canonical verb key} for every verb that
    declares a model_name alias. The model emits tool_calls under the alias; dispatch +
    the permission gate + the tier/selection lookups resolve it back to the key. A
    collision (alias == a real verb key, or two verbs claim the same alias) is logged and
    the offending alias dropped -- real keys always win, so a bad alias degrades to the
    key being shown, never to a mis-dispatch."""
    rev: dict = {}
    keys = set(cat.keys())
    collisions: list[str] = []
    for vname, vcfg in cat.items():
        mn = str((vcfg or {}).get("model_name", "") or "").strip()
        if not mn or mn == vname:
            continue
        if mn in keys:
            collisions.append(f"alias {mn!r} (verb {vname!r}) == a real verb key")
            log.error("ALIAS-COLLISION: model_name %r (verb %r) collides with a real "
                      "verb key -- alias ignored", mn, vname)
            continue
        if mn in rev:
            collisions.append(f"alias {mn!r} claimed by both {rev[mn]!r} and {vname!r}")
            log.error("ALIAS-COLLISION: model_name %r duplicated (%r vs %r) -- keeping "
                      "first; %r is DROPPED from the model-facing surface", mn, rev[mn],
                      vname, vname)
            continue
        rev[mn] = vname
    # Fold each verb's hidden_aliases (old names it ABSORBED during consolidation) into
    # the SAME reverse map so they resolve to the keeper -- back-compat for in-flight
    # chains, DAG/skill step bodies, and MCP/A2A callers -- without ever appearing on the
    # model/MCP/A2A surface (they are neither verb keys nor model_names, so no renderer
    # emits them). Same guards: an alias equal to a real key, or already claimed, is
    # dropped + logged. This is what lets a redundant verb block be DELETED losslessly.
    for vname, vcfg in cat.items():
        for al in ((vcfg or {}).get("hidden_aliases") or []):
            al = str(al).strip()
            if not al or al == vname:
                continue
            if al in keys:
                collisions.append(f"hidden_alias {al!r} (verb {vname!r}) == a real verb key")
                log.error("ALIAS-COLLISION: hidden_alias %r (verb %r) == a real verb "
                          "key -- ignored", al, vname)
                continue
            if al in rev and rev[al] != vname:
                collisions.append(
                    f"hidden_alias {al!r} claimed by both {rev[al]!r} and {vname!r}")
                log.error("ALIAS-COLLISION: hidden_alias %r duplicated (%r vs %r) -- "
                          "keeping first", al, rev[al], vname)
                continue
            rev[al] = vname
    # A dropped alias SILENTLY hides a verb from the model -- exactly the failure a
    # verb-merge campaign (model_name aliasing the old keys to a consolidated verb) can
    # introduce. Make it loud by default; a HARD gate under MIOS_STRICT_VERB_ALIASES=1
    # (set in CI / the build) fails fast so a bad merge never ships, WITHOUT ever
    # bricking a production agent-pipe start (degrade-open: real keys still dispatch).
    if collisions:
        log.error("ALIAS-COLLISION: %d model_name collision(s) -- %s",
                  len(collisions), "; ".join(collisions))
        if str(os.environ.get("MIOS_STRICT_VERB_ALIASES", "")).strip().lower() \
                in {"1", "true", "yes"}:
            raise RuntimeError(
                f"verb model_name alias collisions ({len(collisions)}): "
                + "; ".join(collisions))
    return rev


def _resolve_verb_key(name: str) -> str:
    """Map a model-facing tool name (possibly a P1 model_name alias) back to its
    canonical verb key. Identity for names that are already keys or unknown. Cheap +
    idempotent -- safe to call on an already-resolved key."""
    if not name:
        return name
    if name in _VERB_CATALOG:
        return name
    return _MODEL_NAME_TO_VERB.get(name, name)


def _load_recipe_catalog() -> dict:
    """Parse mios.toml [recipes.*] -> {name: {description, args, permission}}.
    SSOT for the os_recipe verb. Rendered into the planner prompt so EVERY
    recipe is natively discoverable by every agent -- no recipe names baked
 in code ("ALL agents know to use these functions";
    "no hardcodes unless modelfile/docs"). Add a [recipes.*] block in TOML
    and it appears here + in every consumer automatically (self-iterating)."""
    out: dict = {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return out
    toml_path = os.environ.get("MIOS_TOML", "/usr/share/mios/mios.toml")
    for p in (toml_path, "/etc/mios/mios.toml"):  # /etc overlay wins
        try:
            with open(p, "rb") as f:
                recs = (tomllib.load(f).get("recipes") or {})
        except tomllib.TOMLDecodeError:
            # WS-A1: a MALFORMED toml is a real SSOT defect -> fail-loud when
            # opted in; otherwise skip this file (degrade, today's behaviour).
            if CATALOG_FAIL_MODE == "fail":
                raise
            continue
        except OSError:
            continue  # absent /etc overlay is normal -> always skip
        for name, cfg in recs.items():
            if isinstance(cfg, dict):
                out[name] = {
                    "description": str(cfg.get("description", "")),
                    "args": list(cfg.get("args") or []),
                    "permission": str(cfg.get("permission", "read")),
                }
    return out


def _render_recipe_catalog(rec: dict) -> str:
    if not rec:
        return ""
    lines = ["  -- OS recipes (run via os_recipe(name=..., params={...})) --"]
    for name, cfg in rec.items():
        args = ",".join(cfg.get("args") or [])
        perm = cfg.get("permission", "read")
        tag = "" if perm == "read" else f" [{perm}]"
        lines.append(f"  {name}({args})".ljust(34)
                     + f"-- {cfg.get('description', '')}{tag}")
    return "\n".join(lines)


def _recipe_to_openai_tool(name: str, cfg: dict) -> dict:
    """Render one [recipes.*] entry as an OpenAI function-tool schema --
    the SAME `{type:function, function:{name,description,parameters}}` shape
    as _verb_to_openai_tool / _skill_to_openai_tool. The function name is
    mangled to `mios_recipe__<name>` so a relay (mios-mcp-server) can route a
    returned tool_call back through the opaque `os_recipe` verb -- strip the
    prefix, then POST /v1/dispatch {tool:'os_recipe', args:{name, params}}.
    Recipe args are free-form per [recipes.*].args (SSOT in mios.toml); every
    arg is exposed as a string property, plus an optional `os` selector (some
    recipes branch on the target OS). No arg is marked required -- recipes
    fill sensible defaults, and the os_recipe verb tolerates a partial
    params map. Discover here, execute via os_recipe at /v1/dispatch."""
    # OpenAI STRICT mode (audit P1): recipe args are all OPTIONAL, but
    # strict mode requires additionalProperties:false AND every property in
    # `required` -- so an optional arg is expressed as NULLABLE (["string","null"]),
    # the model emits null to skip it, and os_recipe fills the default. Mirrors
    # _verb_to_openai_tool. (Was additionalProperties:true + required:[] -> not
    # strict-mode-valid, silently degraded constrained decoding for mios_recipe__*.)
    args_raw = cfg.get("args") or []
    props: dict = {}
    if isinstance(args_raw, dict):
        for argname, argcfg in args_raw.items():
            if isinstance(argcfg, dict):
                spec = {
                    "type": [argcfg.get("type", "string"), "null"],
                    "description": argcfg.get("desc") or argcfg.get("description") or f"value for {argname}"
                }
                if "enum" in argcfg:
                    spec["enum"] = list(argcfg["enum"]) + [None]
                props[argname] = spec
            else:
                props[argname] = {
                    "type": ["string", "null"],
                    "description": f"value for {argname}",
                }
    else:
        for argname in args_raw:
            if not isinstance(argname, str) or not argname:
                continue
            props[argname] = {
                "type": ["string", "null"],
                "description": f"value for {argname}",
            }
    if "os" not in props:
        props["os"] = {
            "type": ["string", "null"],
            "description": "target OS selector (optional; defaults to host)",
        }
    return {
        "type": "function",
        "function": {
            "name": f"mios_recipe__{re.sub(r'[^A-Za-z0-9_]', '_', name)}",
            "description": cfg.get("description", "") or f"MiOS OS recipe {name}",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": list(props.keys()),
                "additionalProperties": False,
            },
        },
        # Routing/UX hints (x- namespaced; ignored by strict OpenAI clients).
        "x-mios-recipe": name,
        "x-mios-permission": cfg.get("permission", "read"),
    }


def _verb_to_openai_tool(vname: str, vcfg: dict) -> dict:
    """Render one [verbs.*] entry as an OpenAI function-tool schema --
    the SAME `{type:function, function:{name,description,parameters}}`
    shape Hermes/OpenCode already consume from /skills/openai-tools (see
    _skill_to_openai_tool). Tool name == the bare verb name, so a returned
    tool_call executes verbatim via POST /v1/dispatch {tool, args} (the
    launcher-broker path the MCP server also uses). No name mangling ->
    discover here, execute there, one contract."""
    props: dict = {}
    required: list[str] = []
    for argname, argcfg in (vcfg.get("params") or {}).items():
        if not isinstance(argcfg, dict):
            continue
        _t = argcfg.get("type", "string")
        spec: dict = {"description": argcfg.get("desc", "")}
        if argcfg.get("enum"):
            spec["enum"] = list(argcfg["enum"])
        # OpenAI strict mode (Tier-1): EVERY property must be in `required`. An
        # OPTIONAL param (has a default) becomes nullable -- the model emits null to
        # "skip" it, dispatch_mios_verb drops null, and the cmd-template default
        # applies. No `default` key (unsupported under strict). Required params keep
        # their plain type.
        if "default" in argcfg:
            spec["type"] = [_t, "null"]
            if "enum" in spec:
                spec["enum"] = spec["enum"] + [None]
        else:
            spec["type"] = _t
        required.append(argname)
        props[argname] = spec
    # P1 PA-Tool: the MODEL sees the model_name alias (unambiguous, pretraining-familiar)
    # if one is declared; otherwise the bare key. The canonical key still rides x-mios-verb
    # and dispatch resolves the alias back via _resolve_verb_key -> discover-as-alias,
    # execute-as-key, one contract.
    _facing = str(vcfg.get("model_name", "") or "").strip() or vname
    return {
        "type": "function",
        "function": {
            "name": _facing,
            "description": vcfg.get("desc", ""),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
                "additionalProperties": False,
            },
        },
        # Routing/UX hints (x- namespaced; ignored by strict OpenAI clients).
        "x-mios-verb": vname,
        "x-mios-permission": vcfg.get("permission", "read"),
        "x-mios-section": vcfg.get("section", ""),
    }
