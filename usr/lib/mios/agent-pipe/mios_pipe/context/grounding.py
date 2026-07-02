# AI-hint: Per-turn ENV-GROUNDING subsystem extracted verbatim from server.py (refactor R2 leaf wave). Builds the native system-role <env> grounding block the agent-pipe orchestrator threads into EVERY grounded prompt (refine/synthesis/polish/swarm/council/native-loop): the structured _env_block() <env> key:value view + the prose helpers _identity_guard (non-negotiable local-only identity), _arch_grounding (self-architecture), _temporal_grounding (date/time from the client locale), _client_grounding (location/locale/cwd/surface), _capability_grounding (live tool-surface summary), and _client_env (normalise the OWUI-forwarded metadata.variables into a flat env dict). _env_grounding() composes them. Config (_toml_section) imported from mios_config; the per-request _client_env_var ContextVar and the _current_date_str helper that STAY in server.py are dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff). NO hardcoded topics/keywords -- capability lines re-derive from the live verb catalog.
# AI-related: ./server.py, ./mios_config.py, ./test_mios_grounding.py
# AI-functions: _capability_grounding, _temporal_grounding, _get_os_info, _host_timezone, _client_grounding, _identity_guard, _arch_grounding, _env_block, _env_grounding, _principal_bind_mode, _bound_account, _client_env, configure
"""Per-turn environment-grounding block builders (native <env> system block).

Extracted verbatim from ``server.py``. Assembles the system-role grounding block
from host facts + config + the forwarded client/invocation environment. Every
function is moved byte-for-byte; ``server.py`` re-imports each under its original
``_``-prefixed name so the module's importable surface is unchanged.

Config constants come from ``mios_config``; the per-request ``_client_env_var``
ContextVar and the ``_current_date_str`` helper (both stay in ``server.py``) are
injected via :func:`configure` (one-way module boundary -- this module never
imports ``server``).
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import time
from typing import Any, Optional

from mios_config import _toml_section

log = logging.getLogger("mios-agent-pipe")


# -- Dependency-injection seam --
# The grounding helpers read the per-request client/session context from
# server.py's _client_env_var ContextVar and the current date via its
# _current_date_str() helper. server.py calls configure() with those AFTER
# they are defined (one-way boundary: this module never imports server).
# They stay None until then; every consumer runs at request time so a
# standalone ``import mios_grounding`` still succeeds.
_client_env_var = None
_current_date_str = None
# V2 verified-principal binding: server.py's bearer-token -> scoped-principal
# resolver, injected via configure(). None (default / tests) -> binding degrades
# open (the owner falls back to the forwarded body/header user). One-way boundary:
# mios_grounding never imports server.
_check_inbound_principal = None


def configure(*, client_env_var=None, current_date_str=None,
              check_inbound_principal=None) -> None:
    """Inject the server.py runtime refs the grounding cluster calls back into."""
    global _client_env_var, _current_date_str, _check_inbound_principal
    if client_env_var is not None:
        _client_env_var = client_env_var
    if current_date_str is not None:
        _current_date_str = current_date_str
    if check_inbound_principal is not None:
        _check_inbound_principal = check_inbound_principal


NATIVE_LOOP_CAPABILITY_PER_SECTION = int(
    os.environ.get("MIOS_NATIVE_LOOP_CAPABILITY_PER_SECTION", "6") or 6)


def _capability_grounding(cat: dict) -> str:
    """A COMPACT live capability summary for identity grounding: one line per
    catalog section listing the real verb names (from _VERB_CATALOG, i.e. the
    mios.toml [verbs.*] SSOT). The model then answers "what can you do?" from its
    ACTUAL tool surface instead of inventing capabilities. Names only + capped
    per section to keep the system block (and the RadixAttention stable prefix)
    short. Rare-tier verbs are omitted -- still dispatchable, just not advertised.
    No hardcoded English: re-derived from the catalog on every load."""
    if not cat:
        return ""
    sections: "dict[str, list[str]]" = {}
    order: list = []
    for vname, vcfg in cat.items():
        if not isinstance(vcfg, dict) or vcfg.get("tier") == "rare":
            continue
        name = vcfg.get("model_name") or vname
        sec = vcfg.get("section", "Misc")
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        if name not in sections[sec]:
            sections[sec].append(name)
    if not order:
        return ""
    cap = NATIVE_LOOP_CAPABILITY_PER_SECTION
    lines = []
    for sec in order:
        names = sections[sec]
        shown = ", ".join(names[:cap])
        if len(names) > cap:
            shown += f", +{len(names) - cap} more"
        lines.append(f"- {sec}: {shown}")
    return ("YOUR ACTUAL CAPABILITIES (this system's live tool catalog -- the real "
            "tools you can call right now). When asked who you are or what you can "
            "do, describe yourself from THIS list; never claim a capability that is "
            "not here, and do NOT invent example commands, languages, libraries, "
            "file types, or parameter values that are not shown -- name the "
            "capabilities only:\n" + "\n".join(lines))


def _temporal_grounding() -> str:
    """One system-message block giving the agents the current date/time.

    The micros have no clock. Without this, relative dates ("tomorrow",
    "this weekend") were resolved by guessing off whatever dates appeared
    in retrieved text -- operator-flagged: "what's tomorrow at Anime North"
    came back as TODAY's date and three other dates across one answer.
    This grounds the orchestrator's OWN system prompts (refine / polish /
    dispatch); it is NOT a pre_llm_call env-inject into the user message.

    Timezone/date/time come from the USER's Open WebUI client context when
    the pipe forwarded it (metadata.variables: CURRENT_TIMEZONE / CURRENT_DATE
    / CURRENT_TIME / CURRENT_WEEKDAY), so "today"/"tomorrow" match the
    OPERATOR's wall clock, not the server's (the VM is often UTC). Falls back
    to the process-local clock when no client context is present (Discord, raw
 API). "use detected environment details -- locations,
    timezones, locale, time"."""
    env = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
    tz_name = (env.get("timezone") or "").strip()
    now_dt = None
    if tz_name:
        try:                                  # IANA tz from the client (e.g. America/Chicago)
            from zoneinfo import ZoneInfo
            now_dt = datetime.datetime.now(ZoneInfo(tz_name))
        except Exception:
            now_dt = None
    if now_dt is None:
        now_dt = datetime.datetime.now().astimezone()
    tomorrow_dt = now_dt + datetime.timedelta(days=1)
    # Prefer the client's OWN rendered strings (authoritative for the user's
    # locale) where present; compute the rest from the resolved clock.
    weekday = (env.get("weekday") or now_dt.strftime("%A")).strip()
    date_s = (env.get("date") or now_dt.strftime("%Y-%m-%d")).strip()
    time_s = (env.get("time") or now_dt.strftime("%H:%M")).strip()
    tz_show = tz_name or (now_dt.strftime("%Z") or "")
    src = ("the user's Open WebUI client locale/timezone"
           if (tz_name or env.get("date") or env.get("time")) else "the server clock")
    return (
        "Temporal grounding (resolve every relative date/time against THIS, "
        f"never against dates found in retrieved text or training data; from {src}):\n"
        f"  - Today is {weekday}, {date_s}.\n"
        f"  - Tomorrow is {tomorrow_dt.strftime('%A, %Y-%m-%d')}.\n"
        f"  - Current local time: {time_s}{(' ' + tz_show) if tz_show else ''}."
    )


_CACHED_OS_INFO: "Optional[str]" = None


def _get_os_info() -> str:
    """Detailed host OS information, parsed and cached once to prevent latency."""
    global _CACHED_OS_INFO
    if _CACHED_OS_INFO is not None:
        return _CACHED_OS_INFO

    distro = ""
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break
    except Exception:
        pass

    kernel = ""
    arch = ""
    try:
        import subprocess
        res = subprocess.run(["uname", "-rm"], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0 and res.stdout:
            parts = res.stdout.split()
            if parts:
                kernel = parts[0]
            if len(parts) > 1:
                arch = parts[1]
    except Exception:
        pass

    is_wsl = False
    try:
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r", encoding="utf-8") as f:
                ver = f.read().lower()
            if "microsoft" in ver or "wsl" in ver:
                is_wsl = True
    except Exception:
        pass

    windows_host = ""
    if is_wsl:
        mw = None
        for path in ("/usr/libexec/mios/mios-windows", "/usr/local/bin/mios-windows"):
            if os.path.exists(path):
                mw = path
                break
        if mw:
            try:
                import subprocess
                res = subprocess.run([
                    mw, "ps",
                    "try { $o=Get-CimInstance Win32_OperatingSystem; "
                    "\"$($o.Caption) $($o.Version)\" } catch { '' }",
                ], capture_output=True, text=True, timeout=5.0)
                if res.returncode == 0 and res.stdout:
                    cap = res.stdout.replace("\r", "")
                    cap = next((ln.strip() for ln in reversed(cap.splitlines()) if ln.strip()), "")
                    if cap and "windows" in cap.lower():
                        windows_host = cap
            except Exception:
                pass

    parts = []
    if distro:
        parts.append(distro)
    if kernel:
        parts.append(f"kernel {kernel}")
    if arch:
        parts.append(arch)
    if is_wsl:
        parts.append("WSL2")
    if windows_host:
        parts.append(f"host: {windows_host}")

    _CACHED_OS_INFO = ", ".join(parts) if parts else "Linux"
    return _CACHED_OS_INFO


_HOST_TZ: "Optional[str]" = None


def _host_timezone() -> str:
    """The host's IANA timezone (e.g. 'America/New_York') -- a REAL, always-
    available env detail (read once from /etc/localtime). Used as the coarse
    locale-of-last-resort for 'local' / 'near me' asks when no precise user
    location was forwarded or configured, so the agent grounds to the right
 REGION instead of fabricating unrelated cities (OWUI on
    phone answered 'local weather' for five random US cities, observing no env)."""
    global _HOST_TZ
    if _HOST_TZ is not None:
        return _HOST_TZ
    tz = ""
    try:
        p = os.readlink("/etc/localtime")
        if "zoneinfo/" in p:
            tz = p.split("zoneinfo/", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass
    if not tz:
        tz = (os.environ.get("TZ") or "").strip()
    _HOST_TZ = tz
    return tz


def _client_grounding() -> str:
    """Client/session grounding -- the user's REAL location + locale forwarded
    by the OWUI pipe (metadata.variables: USER_LOCATION / USER_LANGUAGE /
    USER_NAME). Like _temporal_grounding it grounds the orchestrator's OWN
    system prompts (refine / swarm / council / polish); NOT a pre_llm_call
    user-message inject. Returns '' when the client sent nothing (Discord, raw
 API, location-sharing off) so nothing is fabricated.
    "OWUI provides entire environment details ... USE them in the pipeline";
    the location is what lets 'near me' resolve instead of a placeholder."""
    env = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
    loc = (env.get("location") or "").strip()
    lang = (env.get("language") or "").strip()
    name = (env.get("user_name") or "").strip()
    lines: list = []
    # Invocation environment -- WHERE this turn is being spoken to from. Each
    # surface forwards what it knows: cwd (the @/mios CLI's working directory),
    # surface tag (cli/owui/discord/desktop), host/os of the invoking machine
    # ("MiOS AI should be aware of every environment it's
    # invoked in"). Emitted independently of location so a CLI turn with no OWUI
    # geo still grounds its folder/surface.
    surface = (env.get("surface") or "").strip()
    cwd = (env.get("cwd") or "").strip()
    host = (env.get("host") or "").strip()
    os_s = (env.get("os") or "").strip()
    _inv: list = []
    if surface:
        _inv.append(f"invoked via the {surface} surface")
    if host:
        _inv.append(f"on host {host}" + (f" ({os_s})" if os_s else ""))
    if cwd:
        _inv.append(f"the user's current working directory is {cwd}")
    if _inv:
        lines.append(
            "  - Invocation context: " + "; ".join(_inv) + ". Resolve relative "
            "paths and 'here' / 'this folder' / 'current directory' against the "
            "cwd; tailor OS-specific actions to the host/os. This is the LIVE "
            "per-invocation environment -- report the working directory / surface "
            "ONLY from THIS context, NEVER from memory, recall, or a prior session.")
    else:
        # No invocation env forwarded this turn (e.g. a surface with no folder
        # context). cwd/surface are LIVE per-invocation facts -- the agent must NOT
        # answer them from a recalled/stored value ('what
        # folder are we in' returned a STALE test cwd from prior recorded context).
        lines.append(
            "  - No working-directory / surface context was forwarded this turn. "
            "If asked where you are / what folder this is, say you cannot determine "
            "it for THIS turn -- do NOT recall, guess, or report a cwd/surface from "
            "memory or a prior session.")
    # Location resolution CHAIN (OWUI on a phone answered
    # "local weather" with five random US cities -- it observed NO location). In
    # order: (1) the client-forwarded geo; else (2) the configured MiOS home
    # location [identity].location; else (3) the host system timezone's REGION (a
    # real, always-available env detail) as a coarse locale. Only when NONE exists
    # do we punt -- and NEVER by fabricating a list of unrelated cities.
    loc_src = "Open WebUI client"
    if not loc:
        _cfg_loc = str((_toml_section("identity") or {}).get("location") or "").strip()
        if _cfg_loc:
            loc = _cfg_loc
            loc_src = "the configured MiOS home location ([identity].location)"
    if loc:
        lines.append(
            f"  - User location ({loc_src}): {loc}. Resolve 'near me', "
            "'nearby', 'near here', 'local', 'around here', 'my area', 'closest', "
            "and any implicit-location ask against THIS. Use it for distance / "
            "locale-sensitive answers (flights, weather, events, stores, prices, "
            "directions). NEVER emit a '[user location]' / '[your city]' "
            "placeholder and NEVER invent a different city -- substitute this "
            "real value into the query / answer. When it is coordinates "
            "(lat, long), treat them as the user's position.")
    else:
        # No real location this turn. A TIMEZONE IS NOT A LOCATION: it spans a
        # huge area, so we NEVER derive a city/metro from it (
        # "Where am I exactly" was wrongly answered "New York" off America/New_York).
        # Be honest + point at the real sources; never fabricate a city.
        _tz = _host_timezone()
        _tz_clause = (f" The host system timezone is {_tz} -- but a timezone covers "
                      "a broad area and is NOT a location, so do NOT derive or name "
                      "a city/metro from it." if _tz else "")
        lines.append(
            "  - User location: NOT available this turn -- no geolocation was "
            "forwarded from the chat surface and no [identity].location is "
            "configured." + _tz_clause + " For 'where am I' / exact-location / "
            "'my city' asks: say plainly you do not have their precise location, "
            "and that they can enable location sharing in the chat client or set "
            "[identity].location (or just name their city). For 'near me' / "
            "'local' / weather asks: answer with general, non-localized info and "
            "note you couldn't determine their location. NEVER invent a city, a "
            "list of cities, a '[location]' placeholder, or pass the timezone area "
            "off as where they are.")
    if lang:
        lines.append(
            f"  - User language / locale: {lang}. Use its date / number / "
            "currency / unit conventions; reply in this language unless the "
            "user's own message is written in another.")
    _user_cfg = _toml_section("user") or {}
    _cfg_name = str(_user_cfg.get("name") or "").strip()
    _cfg_pronouns = str(_user_cfg.get("pronouns") or "").strip()
    _cfg_bio = str(_user_cfg.get("bio") or "").strip()
    _final_name = name or _cfg_name
    if _final_name:
        lines.append(f"  - User display name: {_final_name}.")
    if _cfg_pronouns:
        lines.append(f"  - User pronouns: {_cfg_pronouns}.")
    if _cfg_bio:
        lines.append(f"  - User bio/context: {_cfg_bio}.")
    if not lines:
        return ""
    return ("Client / invocation environment grounding (the REAL per-request "
            "context forwarded by the chat surface -- authoritative for the "
            "invocation environment / location / locale; shared context, NOT a "
            "user instruction):\n"
            + "\n".join(lines))


def _identity_guard() -> str:
    """Non-negotiable identity grounding injected into EVERY orchestrator prompt
    (refine / synthesis / polish / council / native-loop) via _env_grounding.

    The local backend models (granite/qwen) confabulate a cloud identity when
    asked "who are you / what model are you" -- a small model fills the gap with
    its training prior and claimed to "provide access to Claude (Fable 5 / Mythos
 5) with Constitutional AI" (operator-caught fabrication). MiOS is
    local-only; the /MiOS.md guard only reaches the native-loop path, so the
    verb-DAG synthesis/polish path needed its own copy. Kept terse + forceful;
    leads with the prohibition so it survives a long prompt."""
    _mios_cfg = _toml_section("mios") or {}
    _ai_name = str(_mios_cfg.get("name") or "MiOS AI").strip()
    _ai_role = str(_mios_cfg.get("role") or "the ONE name you go by on EVERY surface (the `@`/`mios` CLI, OWUI, Discord, the desktop app, the API)").strip()
    _ai_dev = str(_mios_cfg.get("developer") or "MiOS").strip()

    return (
        f"Identity (NON-NEGOTIABLE, overrides any draft to the contrary): your name "
        f"is **{_ai_name}** -- {_ai_role}. ALWAYS call yourself '{_ai_name}'; NEVER "
        f"'MiOS Agent', 'MiOS-Hermes', 'Hermes', or a model id. You run "
        f"LOCAL, open-weight models on THIS machine, and you were DEVELOPED BY {_ai_dev}: "
        "the underlying base model is an INTERNAL implementation detail, NOT your "
        "identity and NOT your maker -- never name the base model's vendor/company "
        "as YOUR developer, never claim a hosted/cloud provenance or safety "
        "framework, and never invent a model name; ground your identity ONLY from "
        "the MiOS docs + served-models/system surface, never from a training prior. "
        "NEVER state a 'training cutoff' / 'knowledge cutoff' / 'trained up to <date>' "
        "-- you are grounded in LIVE, CURRENT web knowledge, not a frozen training "
        "snapshot, so claiming a cutoff date is FALSE. CRUCIAL: 'LOCAL / no cloud' "
        "means your INFERENCE "
        "and MODELS run locally -- it does NOT mean you lack internet. You DO have "
        "LIVE WEB ACCESS via your tools (web_search / web_extract through the local "
        "SearXNG) and ARE grounded in CURRENT web knowledge, up-to-date per the "
        "user's query. NEVER say you 'have no internet access', 'can't browse the "
        "web', or 'only know my training data' -- that DENIES a real capability. If "
        "a draft claims a cloud MODEL, OR denies web access / claims training-data-"
        "only, that is FALSE -- correct it. MiOS = LOCAL inference + LIVE web."
    )


def _arch_grounding() -> str:
    """Concise SELF-ARCHITECTURE grounding (#65) so the agent answers 'how are you
    built / which model / what's the orchestrator' from FACT, not a guess -- it
    hallucinated its own stack before (e.g. 'the orchestrator is Hermes', stale).
    Folds the key system.md facts in (system.md is not otherwise injected at
    runtime). Kept short to bound per-turn token cost."""
    return (
        "What MiOS IS (ground any 'what is MiOS / MiOS?' answer on THIS host and its "
        "on-disk docs, NEVER from a training prior): MiOS is THIS system -- an "
        "immutable, container-image-shaped (bootc/OCI) Fedora workstation that is "
        "ALSO a complete LOCAL agentic AI operating system; the same image ships the "
        "GNOME/Wayland desktop AND the whole AI stack (local inference lanes, a "
        "multi-agent pipeline, pgvector memory). This is the ONLY MiOS you describe; "
        "read /MiOS.md, /usr/share/mios/ai/ and /usr/share/doc/mios/ (you have full "
        "filesystem access) to ground it. If a draft describes some other 'MiOS' "
        "product from training data, that is FALSE -- correct it from these docs. "
        "Self-architecture (ground any 'how are you built / which model / what's the "
        "orchestrator' answer on THIS, never guess): you are MiOS AI, served by the "
        "agent-pipe orchestrator (:8640, model id 'MiOS AI') -- the front door that "
        "refines, routes, "
        "fans out across a council/DAG, and polishes. LOCAL inference lanes behind it: "
        "mios-llm-light (:11450 — everyday models + embeddings + a vision VLM) + the "
        "heavy lane mios-llm-heavy (:11441, SGLang). MiOS-Hermes (:8642) is a tool-loop "
        "WORKER the pipe fronts, NOT the orchestrator. Memory = pgvector; web_search = "
        "local SearXNG. Hardware: AMD Ryzen 9 9950X3D + NVIDIA RTX 4090. "
        "You have FULL read access to THIS machine's filesystem AND the authoritative "
        "MiOS documentation on it (/MiOS.md, /usr/share/mios/ai/, /usr/share/doc/mios/, "
        "plus knowledge_search over the indexed MiOS docs). For ANY question about "
        "MiOS, its components, or your own capabilities, ground the answer in those "
        "REAL on-disk docs (read them with your file tools / knowledge_search) -- "
        "MiOS facts are KNOWABLE from this machine, so NEVER answer them from a "
        "training-data guess."
    )


def _env_block() -> str:
    """A fixed-shape, parseable <env> block of the LIVE per-turn environment
 (research a small ~8B model reads structured key:value far more
    reliably than the prose helpers, which it routinely overrides). This is the
    CANONICAL 'every prompt env-grounded natively' mechanism -- a SYSTEM-role block
    refreshed each turn, NOT a pre_llm_call user-message inject (that is the banned
    hack). Values are LIVE this turn from the forwarded invocation env + host facts;
    an undetermined key is OMITTED (never fabricated). cwd/surface/location come
    ONLY from this turn's context, never recall. Reuses the SAME getters +
    location-chain as _client_grounding so the structured + prose views agree."""
    env = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
    rows: list = []
    rows.append(("current_date", _current_date_str()))
    _tz = _host_timezone()
    if _tz:
        rows.append(("timezone", _tz))
    for _ek, _ok in (("surface", "surface"), ("host", "host"),
                     ("cwd", "cwd"), ("user_name", "user"), ("language", "language")):
        _v = str(env.get(_ek) or "").strip()
        if _v:
            rows.append((_ok, _v))
    # os details: prefer server-probed OS (cached/detailed) and merge client platform if separate
    _client_os = str(env.get("os") or "").strip()
    _server_os = _get_os_info()
    if _client_os and _client_os.lower() not in _server_os.lower():
        _os_v = f"{_server_os} (client: {_client_os})"
    else:
        _os_v = _server_os or _client_os
    if _os_v:
        rows.append(("os", _os_v))
    # location chain (client-forwarded geo -> configured [identity].location),
    # with provenance, MIRRORING _client_grounding so the two views never disagree.
    # We DELIBERATELY do NOT downgrade the host timezone into a `location`: a tz
    # area (e.g. America/New_York) spans a third of a country and is NOT the
    # user's city -- claiming its principal metro is a fabrication (operator
    # "Where am I exactly" was wrongly answered "New York"). `location`
    # is emitted ONLY from a real source; the honest "unknown" path lives in
    # _client_grounding's directives (the timezone fact stays in the `timezone` row).
    _loc = str(env.get("location") or "").strip()
    _src = "client"
    if not _loc:
        _cfg = str((_toml_section("identity") or {}).get("location") or "").strip()
        if _cfg:
            _loc, _src = _cfg, "configured"
    if _loc:
        rows.append(("location", _loc))
        rows.append(("location_source", _src))
    else:
        # EXPLICIT unknown (NOT omitted): an 8B model otherwise fills the gap by
        # inferring a city from the `timezone` row above (it
        # kept answering "New York" off America/New_York). Granite obeys the
        # structured key:value block far more reliably than prose, so the hard
        # guard lives HERE, in the env block itself.
        rows.append(("location",
                     "UNKNOWN -- not shared this turn. The timezone is NOT a "
                     "location: do NOT infer or name any city/region from it. "
                     "Ask the user for their city or use [identity].location."))
    if not rows:
        return ""
    body = "\n".join(f"  {k}: {v}" for k, v in rows)
    return ("<env>  # LIVE environment for THIS turn -- report cwd / surface / "
            "location ONLY from here, never from memory or a prior turn\n"
            + body + "\n</env>")


def _env_grounding() -> str:
    """Identity guard + self-architecture + temporal + client-environment grounding
    for the orchestrator's OWN system prompts (refine / synthesis / polish / swarm /
    council / native-loop). Single helper so every grounded prompt site threads the
    identity + arch + forwarded OWUI environment (time, timezone, location, locale,
 name) in one place. Leads with a STRUCTURED <env> block (research
    parseable key:value for small models) followed by the detailed prose guidance +
    anti-fabrication rules -- the prose is kept so nothing regresses."""
    e = _env_block()
    g = _identity_guard()
    a = _arch_grounding()
    t = _temporal_grounding()
    c = _client_grounding()
    anti_stale = (
        "WARNING: Avoid stale information! If the query asks about current events, "
        "today's topics, this week, or recent occurrences, do NOT rely on your training "
        "data. You MUST execute active web search queries to verify and pull live, "
        "accurate facts. Strictly prevent any stale grounding or assumptions.\n"
        "STRICT VERSION GROUNDING RULE: Do NOT guess, assume, or append specific version numbers, "
        "release versions, or hardware specifications (e.g. '4', '5', '6', '2026') unless they "
        "are explicitly requested by the user or present in the chat history. Keep generic brand "
        "or product names (e.g. 'forza horizon' or 'photoshop') EXACTLY as requested so the "
        "system's local resolver can match against the actual installed local inventory."
    )
    return (e + "\n" if e else "") + g + "\n" + a + "\n" + t + "\n" + anti_stale + ("\n" + c if c else "")


_OWUI_VAR_KEYS = (
    "user_location", "location", "current_timezone", "timezone",
    "current_date", "current_time", "current_datetime", "current_weekday",
    "user_language", "language", "locale", "user_name", "user_email",
    # Invocation-environment keys (every chat surface forwards what it knows so
    # the agent is aware of WHERE it is being spoken to from --
    # "MiOS AI should be aware of every environment it's invoked in"). cwd = the
    # @/mios CLI's working directory; surface = which front-end (cli/owui/discord/
    # desktop); host/os = the invoking machine.
    "cwd", "surface", "origin", "host", "os", "shell",
)
# OWUI's absent-value sentinels (getPromptVariables emits 'Unknown'); drop
# them so a missing fact never overrides a real one or grounds as junk.
_ENV_SENTINELS = frozenset({"", "unknown", "none", "null", "n/a", "undefined"})

# The SSOT-defined principal-binding states (validation set, NOT a decision gate);
# mirrors the sibling rls_mode / principal_mode enums. Anything outside this set
# degrades to the safe 'off' default. See mios.toml [security].principal_bind_mode.
_PRINCIPAL_BIND_MODES = frozenset({"off", "verify", "enforce"})


def _principal_bind_mode() -> str:
    """V2 verified-principal binding mode from SSOT [security].principal_bind_mode
    (env MIOS_PRINCIPAL_BIND_MODE wins). Returns one of off/verify/enforce; an
    unrecognised value degrades to 'off' (the safe, byte-identical default). Read
    per call so a live mios.toml edit takes effect, like the sibling rls_mode knob."""
    try:
        mode = str(os.environ.get("MIOS_PRINCIPAL_BIND_MODE")
                   or (_toml_section("security") or {}).get("principal_bind_mode", "off")
                   ).strip().lower()
        return mode if mode in _PRINCIPAL_BIND_MODES else "off"
    except Exception:  # noqa: BLE001 -- degrade-open: never break env assembly
        return "off"


def _bound_account(headers: Optional[Any]) -> "Optional[str]":
    """Resolve THIS request's bearer token to the account/owner identity BOUND to its
    caller-key, or None when there is no token / no mapping / the resolver was not
    injected (degrade-open). The canonical shared + ingress keys resolve to the
    full-trust operator principal, which carries NO bound account -> None here, so a
    trusted gateway (OWUI) keeps speaking for its forwarded per-user identity. The
    per-key binding is the optional `account` (alias `owner`) field on the caller-key
    entry (see mios.toml [security].principal_bind_mode)."""
    try:
        if not (_check_inbound_principal and headers is not None
                and hasattr(headers, "get")):
            return None
        tok = str(headers.get("authorization") or "").removeprefix("Bearer ").strip()
        if not tok:
            return None
        princ = _check_inbound_principal(tok)
        if not isinstance(princ, dict):
            return None
        acct = str(princ.get("account") or princ.get("owner") or "").strip()
        return acct or None
    except Exception:  # noqa: BLE001 -- degrade-open: binding must never break a turn
        return None


def _client_env(body: dict, headers: Optional[Any] = None) -> dict:
    """Normalise the per-request client/session context the OWUI pipe forwards.

    Primary source is metadata.variables (OWUI's own convention; keys carry
    the {{ }} braces, e.g. "{{USER_LOCATION}}"). We also accept a top-level
    `variables` dict and directly-placed known keys (non-OWUI callers), plus
    the standard OpenAI `user` field as a last-resort display name. Returns a
    flat dict {location, timezone, date, time, datetime, weekday, language,
    user_name, user_email} with empty strings for anything not provided."""
    if not isinstance(body, dict):
        return {}
    meta = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    raw: dict = {}
    # Braced-key variable dicts (OWUI metadata.variables; also tolerate one at
    # body top level for direct callers).
    for cand in (meta.get("variables"), body.get("variables")):
        if isinstance(cand, dict):
            for k, v in cand.items():
                if isinstance(k, str):
                    raw.setdefault(k, v)
    # Directly-placed known keys on metadata/body (non-OWUI shapes).
    for cand in (meta, body):
        if isinstance(cand, dict):
            for k in _OWUI_VAR_KEYS:
                if k in cand:
                    raw.setdefault(k, cand[k])
    norm: dict = {}
    for k, v in raw.items():
        if not isinstance(k, str) or v is None:
            continue
        kk = k.strip().strip("{}").strip().lower()
        if not kk:
            continue
        sv = str(v).strip()
        if sv.lower() in _ENV_SENTINELS:
            continue
        norm.setdefault(kk, sv)
    out = {
        "location":  norm.get("user_location") or norm.get("location") or "",
        "timezone":  norm.get("current_timezone") or norm.get("timezone") or "",
        "date":      norm.get("current_date") or "",
        "time":      norm.get("current_time") or "",
        "datetime":  norm.get("current_datetime") or "",
        "weekday":   norm.get("current_weekday") or "",
        "language":  (norm.get("user_language") or norm.get("language")
                      or norm.get("locale") or ""),
        "user_name": norm.get("user_name") or "",
        "user_email": norm.get("user_email") or "",
        # Invocation environment (where the turn is being spoken to from).
        "cwd":       norm.get("cwd") or "",
        "surface":   norm.get("surface") or norm.get("origin") or "",
        "host":      norm.get("host") or "",
        "os":        norm.get("os") or "",
        "shell":     norm.get("shell") or "",
    }
    # Retain EVERY env detail the surface forwards ("OWUI
    # exposes DOZENS of env details, MiOS AI uses them"): keep the canonical
    # aliases above AND pass through any other normalized key so the allow-list
    # never silently drops a forwarded fact. setdefault never clobbers a canonical
    # key; _client_grounding renders the named ones, the rest are available.
    for _k, _v in norm.items():
        out.setdefault(_k, _v)
    if not out["user_name"]:
        u = body.get("user")
        if isinstance(u, str) and u.strip():
            out["user_name"] = u.strip()

    # Look up user details in webui.db if we have email or user_id
    email = ""
    uid = ""
    if headers and hasattr(headers, "get"):
        email = (headers.get("x-openwebui-user-email") or "").strip()
        uid = (headers.get("x-openwebui-user-id") or "").strip()
    if not email:
        email = out.get("user_email") or ""
    if not uid:
        uid = norm.get("user_id") or ""
    if email or uid:
        owui_db = os.environ.get("MIOS_OWUI_DB", "/var/lib/mios/open-webui/webui.db")
        if os.path.isfile(owui_db):
            try:
                import sqlite3
                c = sqlite3.connect(f"file:{owui_db}?mode=ro", uri=True, timeout=10.0)
                c.row_factory = sqlite3.Row
                row = None
                if uid:
                    row = c.execute("SELECT timezone, info, settings, name, email FROM user WHERE id = ? LIMIT 1;", (uid,)).fetchone()
                if not row and email:
                    row = c.execute("SELECT timezone, info, settings, name, email FROM user WHERE email = ? LIMIT 1;", (email,)).fetchone()
                c.close()
                if row:
                    if row["timezone"] and not out.get("timezone"):
                        out["timezone"] = str(row["timezone"])
                    if row["name"] and not out.get("user_name"):
                        out["user_name"] = str(row["name"])
                    if row["email"] and not out.get("user_email"):
                        out["user_email"] = str(row["email"])
                    if row["info"]:
                        try:
                            info = json.loads(row["info"])
                            if isinstance(info, dict) and not out.get("location") and info.get("location"):
                                out["location"] = str(info["location"]).strip()
                        except Exception:
                            pass
                    if row["settings"]:
                        try:
                            settings = json.loads(row["settings"])
                            if isinstance(settings, dict) and not out.get("location"):
                                loc = settings.get("location") or settings.get("ui", {}).get("location")
                                if loc:
                                    out["location"] = str(loc).strip()
                        except Exception:
                            pass
            except Exception:
                pass
    # CONNECTION-MODEL PATH : when OWUI drives a direct
    # connection model (NOT the pipe), it substitutes the live geo into the SYSTEM
    # MESSAGE TEXT (the model's {{USER_LOCATION}} prompt), NOT into
    # metadata.variables -- so the loops above find nothing and 'near me'/weather
    # fall back to "ask for your city". Recover it from the resolved system
    # message(s) so the connection path grounds too. Anchored on the SSOT prompt
    # wording ("location is <value>"); requires an alphanumeric value and rejects a
    # leftover "{{" or a stripped "location is ." -- best-effort, never throws.
    if not out["location"]:
        try:
            for _m in (body.get("messages") or []):
                if not (isinstance(_m, dict) and _m.get("role") == "system"):
                    continue
                _sys = _m.get("content")
                if not isinstance(_sys, str) or not _sys:
                    continue
                # Match both the prose form ("...location is <v>.") and the
                # labelled form the mios-agent.md env block uses ("User location:
                # <v>" / "location = <v>"), value bounded by newline or sentence end.
                _mt = re.search(r"location\s*(?:is|[:=])\s*(.+?)(?:\n|\.\s|\.$|$)",
                                _sys, re.I)
                if _mt:
                    _rec = _mt.group(1).strip().rstrip(".").strip()
                    if ("{{" not in _rec and re.search(r"[0-9A-Za-z]", _rec)
                            and _rec.lower() not in _ENV_SENTINELS):
                        out["location"] = _rec
                        break
        except Exception:  # noqa: BLE001 -- recovery is best-effort
            pass
    # Diagnostic: surface EXACTLY what the chat surface forwarded for location, so
    # an "I enabled location but it still doesn't know where I am" report is
    # debuggable from the journal. Logs the forwarded var
    # keys + the resolved location/timezone, never the full payload.
    try:
        _hdr_email = ""
        if headers is not None and hasattr(headers, "get"):
            _hdr_email = headers.get("x-openwebui-user-email") or ""
        log.info("client_env: fwd_var_keys=%s hdr_email=%r -> location=%r timezone=%r",
                 sorted(raw.keys())[:30], _hdr_email,
                 out.get("location"), out.get("timezone"))
    except Exception:  # noqa: BLE001
        pass
    # ── V2 verified-principal binding (default OFF -> byte-identical) ──────────
    # Downstream owner row-scoping (owner_user) derives from user_name/user_email,
    # both spoofable by a direct caller (body `user` / x-openwebui-user-* headers).
    # When [security].principal_bind_mode is verify/enforce, reconcile that owner
    # against the AUTHENTICATED caller-key's bound account. This is the LAST mutation
    # so it has the final say over the webui.db / OWUI-forwarded values. 'off' (the
    # default) does NOTHING -> the returned env dict is byte-identical to today.
    # DEGRADE-OPEN: no token / unbound key / any error -> the forwarded value stands.
    _bind_mode = _principal_bind_mode()
    if _bind_mode != "off":
        try:
            _claimed = (out.get("user_name") or out.get("user_email") or "").strip()
            _bound = _bound_account(headers)
            if _bound:
                if _bind_mode == "enforce":
                    # The token-bound account is the sole owner identity; the
                    # spoofable claim is overridden so display + every owner_user
                    # derivation (knowledge / agent_memory / a2a / policy) agree.
                    out["user_name"] = _bound
                    out["user_email"] = ""
                elif _bound != _claimed:  # verify: observe + audit, value unchanged
                    log.warning(
                        "principal-bind mismatch (mode=verify): claimed=%r "
                        "token-bound=%r -- using claimed (observe mode)",
                        _claimed, _bound)
        except Exception:  # noqa: BLE001 -- degrade-open: never break a turn
            pass
    return out


def _current_year() -> str:
    """Current 4-digit year. Prefers the USER's client date (the env-detected
    value the OWUI pipe forwarded) so a query anchors to the OPERATOR's NOW,
    falling back to the live system clock. NEVER hardcode the year (operator
 "use env detect for current values for all AI functions / fall
    back to embedding the current year")."""
    env = _client_env_var.get() if isinstance(_client_env_var.get(), dict) else {}
    for _src in (env.get("date"), env.get("datetime")):
        m = re.match(r"\s*(\d{4})", str(_src or ""))
        if m:
            return m.group(1)
    return str(time.localtime().tm_year)
