# AI-hint: A2A FEDERATION publish/server surface extracted VERBATIM from server.py (refactor R11 federation wave).
# AI-doc: usr/share/doc/mios/manual/federation.md

from __future__ import annotations

import asyncio
import base64
import collections
import datetime
import hashlib
import json
import os
import time
import uuid
import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from mios_config import PORT, MCP_SERVER_PORT, _toml_section
import mios_capreg
import mios_interop
import mios_crl
import mios_a2a_principal as _a2a_pp

log = logging.getLogger("mios-agent-pipe")


app = None
_AGENT_REGISTRY: dict = {}
_VERB_CATALOG: dict = {}
_SCRATCHPADS: dict = {}
_agent_lane = None
_agent_skill_tags = None
_match_user_cfg = None
_cap_skills = None
_get_client = None
_API_REQUIRE_AUTH = False
_client_env_var = None
_passport_load_priv = None
_passport_canonical_json = None
_passport_kid = None
_passport_sign = None
_passport_verify = None
PASSPORT_ALGO = None
PASSPORT_ENABLE = None
PASSPORT_AGENT_NAME = None
_A2A_PEERS: dict = {}
_A2A_PEER_SKILLS: dict = {}
_A2A_PEERS_LOCK = None
_A2A_REPUTATION = None
_a2a_send_message_to_peer = None
_passport_load_public = None
_check_inbound_principal = None
_reload_membership = None
_MCP_POOL = None


def configure(*, app=None, agent_registry=None, verb_catalog=None,
              scratchpads=None, agent_lane=None, agent_skill_tags=None,
              match_user_cfg=None, cap_skills=None, get_client=None,
              api_require_auth=None, client_env_var=None,
              passport_load_priv=None, passport_canonical_json=None,
              passport_kid=None, passport_sign=None, passport_verify=None,
              passport_algo=None, passport_enable=None,
              passport_agent_name=None, a2a_peers=None, a2a_peer_skills=None,
              a2a_peers_lock=None, a2a_reputation=None,
              a2a_send_message_to_peer=None, passport_load_public=None,
              check_inbound_principal=None, reload_membership=None,
              mcp_pool=None) -> None:
    """Inject server.py's runtime deps. Mutable registries/catalogs/scratchpad
    (incl. the consumer-side _A2A_PEERS/_A2A_PEER_SKILLS) are injected BY
    REFERENCE so server-side mutation stays visible to the builders + context
    projection + the @app /v1/a2a/* route logic. server.py may call configure()
    more than once (a partial set per call) as each dep becomes defined."""
    g = globals()
    if mcp_pool is not None:
        g["_MCP_POOL"] = mcp_pool
    if app is not None:
        g["app"] = app
    if agent_registry is not None:
        g["_AGENT_REGISTRY"] = agent_registry
    if verb_catalog is not None:
        g["_VERB_CATALOG"] = verb_catalog
    if scratchpads is not None:
        g["_SCRATCHPADS"] = scratchpads
    if agent_lane is not None:
        g["_agent_lane"] = agent_lane
    if agent_skill_tags is not None:
        g["_agent_skill_tags"] = agent_skill_tags
    if match_user_cfg is not None:
        g["_match_user_cfg"] = match_user_cfg
    if cap_skills is not None:
        g["_cap_skills"] = cap_skills
    if get_client is not None:
        g["_get_client"] = get_client
    if api_require_auth is not None:
        g["_API_REQUIRE_AUTH"] = api_require_auth
    if client_env_var is not None:
        g["_client_env_var"] = client_env_var
    if passport_load_priv is not None:
        g["_passport_load_priv"] = passport_load_priv
    if passport_canonical_json is not None:
        g["_passport_canonical_json"] = passport_canonical_json
    if passport_kid is not None:
        g["_passport_kid"] = passport_kid
    if passport_sign is not None:
        g["_passport_sign"] = passport_sign
    if passport_verify is not None:
        g["_passport_verify"] = passport_verify
    if passport_algo is not None:
        g["PASSPORT_ALGO"] = passport_algo
    if passport_enable is not None:
        g["PASSPORT_ENABLE"] = passport_enable
    if passport_agent_name is not None:
        g["PASSPORT_AGENT_NAME"] = passport_agent_name
    if a2a_peers is not None:
        g["_A2A_PEERS"] = a2a_peers
    if a2a_peer_skills is not None:
        g["_A2A_PEER_SKILLS"] = a2a_peer_skills
    if a2a_peers_lock is not None:
        g["_A2A_PEERS_LOCK"] = a2a_peers_lock
    if a2a_reputation is not None:
        g["_A2A_REPUTATION"] = a2a_reputation
    if a2a_send_message_to_peer is not None:
        g["_a2a_send_message_to_peer"] = a2a_send_message_to_peer
    if passport_load_public is not None:
        g["_passport_load_public"] = passport_load_public
    if check_inbound_principal is not None:
        g["_check_inbound_principal"] = check_inbound_principal
    if reload_membership is not None:
        g["_reload_membership"] = reload_membership


A2A_PROTOCOL_VERSION = str(
    os.environ.get("MIOS_A2A_PROTOCOL_VERSION")
    or (_toml_section("a2a") or {}).get("protocol_version")
    or "1.0").strip()

_TS_SUBMITTED = "TASK_STATE_SUBMITTED"
_TS_WORKING = "TASK_STATE_WORKING"
_TS_COMPLETED = "TASK_STATE_COMPLETED"
_TS_FAILED = "TASK_STATE_FAILED"
_TS_CANCELED = "TASK_STATE_CANCELED"
_TS_REJECTED = "TASK_STATE_REJECTED"
_ROLE_USER = "ROLE_USER"
_ROLE_AGENT = "ROLE_AGENT"
_A2A_ROLE_TO_V1 = {"user": _ROLE_USER, "agent": _ROLE_AGENT}
_A2A_TEXT_MEDIA_TYPE = "text/plain"
_A2A_ERROR_DOMAIN = "a2a-protocol.org"
_A2A_ERRINFO_TYPE = "type.googleapis.com/google.rpc.ErrorInfo"


def _a2a_role_v1(role) -> str:
    """Normalise a Message role to its v1.0 token (liberal in / strict out)."""
    r = str(role or "").strip()
    return _A2A_ROLE_TO_V1.get(r.lower(), r if r.startswith("ROLE_") else _ROLE_USER)


def _a2a_text_part(text: str) -> dict:
    """A v1.0 A2A text Part: the `text` member (v1.0 discriminates Parts by which
    member is present, NOT by a `kind` tag) plus its mediaType. v0.3's `kind:"text"`
    is gone."""
    return {"text": str(text or ""), "mediaType": _A2A_TEXT_MEDIA_TYPE}


from mios_pipe.federation.agentcard_sign import (
    _JWS_ALG_EDDSA,
    _A2A_CARD_SIG_FIELD,
    _b64u,
    _b64u_decode,
    _jcs_canonicalize,
    _agent_card_signing_input,
    _agent_card_signature as _agent_card_signature_raw,
    _verify_agent_card_signature as _verify_agent_card_signature_raw,
)


def _agent_card_signature(card: dict) -> "Optional[dict]":
    return _agent_card_signature_raw(
        card,
        load_priv_fn=_passport_load_priv,
        kid_fn=_passport_kid,
    )


def _verify_agent_card_signature(card: dict, *, public_key=None) -> "tuple[Optional[bool], str]":
    return _verify_agent_card_signature_raw(
        card,
        public_key=public_key,
        load_pub_fn=_passport_load_public,
        passport_agent_name=PASSPORT_AGENT_NAME,
    )


def _build_agent_card() -> dict:
    """Render the A2A v1.0 AgentCard from MiOS SSOT (no hardcoded skills).

    Each mios.toml [agents.*] entry becomes one A2A skill: id=agent name,
    tags=its strengths, description from role+lane. This is exactly the
    data _pick_fanout_agents scores, now exposed in the open standard."""
    base = f"http://localhost:{PORT}"
    skills = []
    for name, cfg in _AGENT_REGISTRY.items():
        role = str(cfg.get("role", "general"))
        lane = _agent_lane(cfg)
        tags = _agent_skill_tags(cfg)
        desc_bits = [f"{role} agent on the {lane} inference lane"]
        if cfg.get("default"):
            desc_bits.append("primary/default orchestrator")
        if cfg.get("strengths"):
            desc_bits.append(
                "strengths: " + ", ".join(str(s) for s in cfg["strengths"]))
        skills.append({
            "id": name,
            "name": f"{name} ({role})",
            "description": "; ".join(desc_bits),
            "tags": tags,
            "inputModes": ["text/plain", "application/json"],
            "outputModes": ["text/plain"],
        })
    card: dict = {
        "name": os.environ.get("MIOS_A2A_AGENT_NAME", "MiOS AI"),
        "description": app.description,
        "version": app.version,
        "supportedInterfaces": [
            {"url": f"{base}/a2a", "protocolBinding": "JSONRPC",
             "protocolVersion": A2A_PROTOCOL_VERSION},
            {"url": f"{base}/v1", "protocolBinding": "OpenAI",
             "protocolVersion": A2A_PROTOCOL_VERSION},
        ],
        "provider": {
            "organization": "MiOS",
            "url": os.environ.get(
                "MIOS_REPO_URL", "https://github.com/mios-dev/MiOS"),
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": True,
        },
        "defaultInputModes": ["text/plain", "application/json", "image/png"],
        "defaultOutputModes": ["text/plain"],
        "skills": skills,
        "x-mios": {
            "openai_chat_completions": f"{base}/v1/chat/completions",
            "mcp_server": "mios-mcp-server (stdio JSON-RPC 2.0, spec "
                          "2025-06-18; tool catalog via this server's "
                          "/v1/verbs)",
            "verb_catalog_size": len(_VERB_CATALOG),
            "stateTransitionHistory": True,
            "contextSharing": True,
            "discovery": {
                "tools": f"{base}/v1/verbs",
                "tool_search": f"{base}/v1/tool-search",
                "a2a_skill_directory": f"{base}/a2a/skills",
                "capabilities": f"{base}/v1/capabilities",
                "capability_dag": f"{base}/v1/capabilities/dag",
                "context": f"{base}/a2a/contexts/{{contextId}}",
                "health": f"{base}/health",
            },
        },
    }
    _a2a_sec = (_toml_section("a2a") or {}).get("security") or {}
    card["securitySchemes"] = (
        _a2a_sec.get("schemes")
        if isinstance(_a2a_sec, dict) and isinstance(_a2a_sec.get("schemes"), dict)
        else {"bearer": {"httpAuthSecurityScheme": {
            "scheme": "bearer",
            "description": "MiOS shared API key or a per-caller key "
                           "(Authorization: Bearer <token>)."}}})
    if _API_REQUIRE_AUTH:
        card["security"] = [{k: []} for k in card["securitySchemes"]]
    _sig = _agent_card_signature(card)
    if _sig:
        card["signatures"] = [_sig]
    return card


AGENT_PASSPORT_VERSION = "0.1.0"


def _canonical_json(obj) -> bytes:
    """Canonical JSON for signing: sorted keys at every depth, no whitespace,
    UTF-8 -- deterministic bytes for cross-implementation Ed25519 verification."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _build_agent_passport() -> dict:
    """Render the Open Agent Passport (v0.1.0) from MiOS SSOT, Ed25519-signed when
    a private key is configured ([agent_passport].signing_key_path or
    MIOS_AGENT_PASSPORT_KEY); otherwise unsigned + flagged. No hardcoded identity
    -- every value flows from [agent_passport]/[identity] with MiOS defaults."""
    ap = _toml_section("agent_passport") or {}
    ident = _toml_section("identity") or {}
    base = f"http://localhost:{PORT}"
    domain = str(os.environ.get("MIOS_PUBLIC_DOMAIN") or ap.get("domain") or (_toml_section("a2a") or {}).get("public_domain") or "localhost")
    agent_id = str((_toml_section("ai") or {}).get("agent_model") or "MiOS AI")
    cur = str(ap.get("spend_currency") or "USD")
    now = int(time.time())
    ttl_days = int(ap.get("validity_days", 90))
    doc = {
        "version": AGENT_PASSPORT_VERSION,
        "issuer": {
            "domain": domain,
            "legalName": str(ap.get("legal_name") or ident.get("org") or "MiOS"),
            "displayName": str(ap.get("display_name") or "MiOS AI"),
            "logo": str(ap.get("logo") or f"https://{domain}/favicon.svg"),
            "signingKeyDns": str(ap.get("signing_key_dns") or f"_agent-passport.{domain}"),
            "contact": {
                "email": str(ap.get("contact_email") or ident.get("email") or f"admin@{domain}"),
                "url": str(ap.get("contact_url") or f"https://{domain}"),
            },
        },
        "agent": {
            "id": f"{domain}:{agent_id}",
            "displayName": agent_id,
            "purpose": str(ap.get("purpose")
                           or "Local agentic operating-system assistant (MiOS)."),
            "model": agent_id,
            "endpoints": {"rest": f"{base}/v1", "a2a": f"{base}/a2a"},
        },
        "authority": {
            "scope": list(ap.get("scope") or ["assist.local", "tools.invoke", "web.search"]),
            "spendCeiling": {
                "amount": float(ap.get("spend_ceiling_amount", 0)),
                "currency": cur,
                "perEngagement": bool(ap.get("spend_per_engagement", True)),
            },
            "humanInLoop": {
                "above": {"amount": float(ap.get("hitl_above_amount", 0)), "currency": cur},
                "escalation": str(ap.get("escalation") or ident.get("email")
                                  or f"admin@{domain}"),
                "slaHours": int(ap.get("sla_hours", 24)),
            },
            "decisionAudit": str(ap.get("decision_audit") or f"{base}/a2a/contexts/{{id}}"),
            "termsUrl": str(ap.get("terms_url") or f"https://{domain}/terms"),
        },
        "counterparties": {"openTo": str(ap.get("open_to") or "allowlist")},
        "compliance": {
            "dataClassification": str(ap.get("data_classification") or "local-only"),
            "regions": list(ap.get("regions") or ["US"]),
            "subprocessors": list(ap.get("subprocessors") or []),
            "humanReviewLog": bool(ap.get("human_review_log", True)),
        },
        "issuedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "expiresAt": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime(now + ttl_days * 86400)),
        "signature": {"alg": "ed25519",
                      "keyId": str(ap.get("key_id") or "mios-ap-1"), "value": ""},
    }
    revurl = ap.get("revocation_list_url")
    if revurl:
        doc["revocationListUrl"] = str(revurl)
    keypath = (os.environ.get("MIOS_AGENT_PASSPORT_KEY")
               or str(ap.get("signing_key_path") or ""))
    signed = False
    if keypath and os.path.isfile(keypath):
        try:
            import base64
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey)
            from cryptography.hazmat.primitives import serialization
            raw = open(keypath, "rb").read()
            try:
                key = serialization.load_pem_private_key(raw, password=None)
            except Exception:
                key = Ed25519PrivateKey.from_private_bytes(raw[-32:])
            sig = key.sign(_canonical_json(doc))
            doc["signature"]["value"] = base64.urlsafe_b64encode(sig).decode().rstrip("=")
            signed = True
        except Exception as e:
            log.warning("agent-passport signing failed: %s", e)
    if not signed:
        doc["x-mios-unsigned"] = (
            "UNSIGNED: provision an Ed25519 key via [agent_passport].signing_key_path "
            "(or MIOS_AGENT_PASSPORT_KEY) and publish the DNS TXT at signingKeyDns "
            "(v=ap1; kid=<keyId>; alg=ed25519; pk=<base64url-public-key>) to make this "
            "passport verifiable. The document is schema-valid as-is.")
    return doc


AGNTCY_OASF_SCHEMA_VERSION = "0.7.0"


def _build_agntcy_manifest() -> dict:
    """Render the MiOS agent in OASF shape. SSOT-derived (no hardcoded
    features); skills come from _AGENT_REGISTRY [[mios.toml [agents.*]]],
    tools come from _VERB_CATALOG, protocols from the live A2A/MCP surfaces.
 'true ACP/A2A/MCP + AGNTCY layer'."""
    card = _build_agent_card()
    base = f"http://localhost:{PORT}"
    features = []
    for sk in (card.get("skills") or []):
        tags = list(sk.get("tags") or [])
        features.append({
            "name": sk.get("id"),
            "display_name": sk.get("name"),
            "description": sk.get("description"),
            "category": (tags[0] if tags else "general"),
            "tags": tags,
            "input_modes": sk.get("inputModes") or [],
            "output_modes": sk.get("outputModes") or [],
        })
    resources = []
    for vname, vcfg in (_VERB_CATALOG or {}).items():
        if not isinstance(vcfg, dict):
            continue
        if str(vcfg.get("tier", "")).lower() == "rare":
            continue
        resources.append({
            "name": vname,
            "kind": "tool",
            "section": vcfg.get("section"),
            "description": vcfg.get("desc"),
            "permission": vcfg.get("permission", "read"),
        })
    return {
        "$schema": ("https://github.com/agntcy/oasf/blob/main/"
                    f"schema/v{AGNTCY_OASF_SCHEMA_VERSION}/agent.json"),
        "oasf_version": AGNTCY_OASF_SCHEMA_VERSION,
        "id": os.environ.get("MIOS_AGNTCY_AGENT_ID",
                             "agent.mios.local-mios"),
        "name": card.get("name"),
        "description": card.get("description"),
        "version": card.get("version"),
        "vendor": "MiOS",
        "homepage": (card.get("provider") or {}).get("url"),
        "license": os.environ.get("MIOS_AGNTCY_LICENSE", "MIT"),
        "protocols": [
            {
                "name": "A2A",
                "version": A2A_PROTOCOL_VERSION,
                "endpoints": {
                    "agent_card": f"{base}/.well-known/agent-card.json",
                    "task_rpc":   f"{base}/a2a",
                    "context":    f"{base}/a2a/contexts/{{contextId}}",
                    "peers":      f"{base}/v1/a2a/peers",
                    "skills":     f"{base}/v1/a2a/skills",
                    "dispatch":   f"{base}/v1/a2a/dispatch",
                },
            },
            {
                "name": "MCP",
                "version": "2025-06-18",
                "transport": "streamable-http",
                "endpoints": {
                    "server":     f"http://127.0.0.1:{MCP_SERVER_PORT}/",
                    "clients":    f"{base}/v1/mcp/clients",
                    "tools":      f"{base}/v1/mcp/tools",
                    "dispatch":   f"{base}/v1/mcp/dispatch",
                },
            },
            {
                "name": "OpenAI",
                "version": "v1",
                "endpoints": {
                    "chat_completions":
                        f"{base}/v1/chat/completions",
                    "verbs":      f"{base}/v1/verbs",
                    "tool_search": f"{base}/v1/tool-search",
                },
            },
        ],
        "capabilities": {
            "streaming": (card.get("capabilities") or {}).get("streaming", False),
            "tool_use": True,
            "shared_context": (card.get("x-mios") or {})
                              .get("contextSharing", False),
            "federated_discovery": True,   # P1.1+P1.2 client halves are live
            "agent_to_agent_delegation": True,  # P2.2 a2a_delegate verb
            "push_notifications": (card.get("capabilities") or {})
                                  .get("pushNotifications", False),
        },
        "features": features,
        "resources": resources,
        "x-mios": {
            "source": "agent-pipe SSOT (mios.toml [agents.*] + [verbs.*])",
            "verb_catalog_size": len(_VERB_CATALOG or {}),
            "agents_in_registry": len(_AGENT_REGISTRY or {}),
        },
    }


async def a2a_skill_directory_logic() -> JSONResponse:
    """Logic for GET /a2a/skills (server.py keeps the thin @app route)."""
    try:
        try:
            _, _ucfg = _match_user_cfg()
        except Exception:  # noqa: BLE001
            _ucfg = {}
        ceiling = str((_ucfg or {}).get("max_permission") or "interactive")
        recipes = _toml_section("recipes") or {}
        skills = _cap_skills()
        man = mios_capreg.build_capability_manifest(
            _VERB_CATALOG, recipes, ceiling=ceiling, skills=skills)
        out = []
        for c in man:
            kind, nm = c.get("kind"), c.get("name")
            if kind == "verb":
                spec = _VERB_CATALOG.get(nm) or {}
            elif kind == "recipe":
                spec = recipes.get(nm) or {}
            else:
                spec = skills.get(nm) or {}
            out.append(mios_interop.to_a2a_skill(nm, spec, kind))
        if _MCP_POOL is not None:
            for t in _MCP_POOL.get_tools():
                out.append(mios_interop.to_a2a_skill(t["name"], t, "mcp"))
        return JSONResponse({"object": "mios.a2a.skill_directory",
                             "ceiling": ceiling, "count": len(out),
                             "skills": out})
    except Exception as e:  # noqa: BLE001 -- never 500 the surface
        return JSONResponse({"object": "mios.a2a.skill_directory",
                             "error": str(e), "skills": []})



def _a2a_messages_for(key: str) -> list:
    dq = _SCRATCHPADS.get(key)
    if not dq:
        return []
    msgs = []
    for e in dq:
        ts = e.get("ts", 0.0)
        agent = e.get("agent", "?")
        msgs.append({
            "role": _ROLE_AGENT,
            "messageId": f"msg_{int(ts * 1000)}_{agent}",
            "contextId": key,
            "taskId": agent,
            "parts": [_a2a_text_part(e.get("note", ""))],
            "metadata": {
                "agent": agent,
                "lane": e.get("lane", "") or "",
                "phase": e.get("phase", "") or "",
                "ts": ts,
            },
        })
    return msgs


def _a2a_context(ctx_id: str) -> dict:
    """A2A/ACP-shaped shared inter-agent context for a conversation: the
    contextId + the agent Message history other agents read for continuity."""
    return {
        "contextId": ctx_id,
        "protocolVersion": A2A_PROTOCOL_VERSION,
        "messages": _a2a_messages_for(ctx_id),
    }



def _principal_mode() -> str:
    raw = str(os.environ.get(
        "MIOS_A2A_PRINCIPAL_MODE",
        str((_toml_section("agent_passport") or {}).get("principal_mode", "off")))
        ).strip().lower()
    if raw in {"require", "enforce", "1", "true", "yes"}:
        return "enforce"
    if raw == "verify":
        return "verify"
    return "off"


_A2A_PRINCIPAL_MODE = _principal_mode()
_A2A_PRINCIPAL_REQUIRE = _A2A_PRINCIPAL_MODE == "enforce"


def _a2a_principal_audit(outcome: str, reason: str, claims) -> None:
    """FED-G6 verify-tier audit: emit ONE structured (JSON) record for a principal
    check that verify-mode lets pass but enforce-mode would reject -- so an operator
    can watch what enforcing WOULD block before flipping the gate. Best-effort: an
    audit failure must never block the request it is only observing."""
    try:
        c = claims if isinstance(claims, dict) else {}
        log.warning("a2a-principal-audit %s", json.dumps(
            {"event": "a2a.principal.verify", "mode": "verify",
             "outcome": outcome, "reason": reason,
             "agent": c.get("agent"), "principal": c.get("principal")},
            sort_keys=True))
    except Exception:  # noqa: BLE001 -- audit must never block the request
        pass


def _a2a_principal_metadata(text: str, peer_id: str,
                           context_id: Optional[str]) -> Optional[dict]:
    """{'claims':…, 'passport':envelope|None} to attach as message.metadata
    ['mios_principal'], or None when the passport system is disabled. Thin wrapper
    over mios_a2a_principal (pure logic) with the live principal + sign fn."""
    if not PASSPORT_ENABLE:
        return None
    env = _client_env_var.get()
    env = env if isinstance(env, dict) else {}
    principal = str(env.get("user_name") or env.get("user_email") or "").strip()
    return _a2a_pp.build_metadata(PASSPORT_AGENT_NAME, principal, peer_id,
                                  context_id, text, _passport_sign)


_CRL_PATH = os.environ.get("MIOS_CRL_PATH", "/usr/share/mios/ai/v1/crl.json")
_CRL_CACHE: dict = {"mtime": -1.0, "crl": None}


def _load_crl() -> "mios_crl.CRL":
    """WS-A10 principal/cert revocation list, loaded from MIOS_CRL_PATH (a JSON
    list or {"revoked":[...]}) + cached by mtime. INERT BY DEFAULT: no CRL file
    -> an empty CRL (nothing revoked), so the revocation check is a no-op until an
    operator publishes a CRL. Degrade-open."""
    try:
        st = os.stat(_CRL_PATH)
        if _CRL_CACHE["crl"] is None or st.st_mtime != _CRL_CACHE["mtime"]:
            with open(_CRL_PATH, encoding="utf-8") as fh:
                _CRL_CACHE["crl"] = mios_crl.CRL.load(json.load(fh))
            _CRL_CACHE["mtime"] = st.st_mtime
        return _CRL_CACHE["crl"]
    except Exception:  # noqa: BLE001 -- missing/unreadable -> empty CRL (inert)
        return _CRL_CACHE["crl"] if _CRL_CACHE["crl"] is not None else mios_crl.CRL()



def _crl_fingerprint(token: str) -> str:
    """Stable, NON-SECRET id for a caller key: sha256 of the bearer token. The CRL
    stores this fingerprint rather than the raw token, and the inbound gate hashes a
    presented token the same way to test membership -- so a key is revocable without
    persisting the credential itself."""
    return "sha256:" + hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _crl_reload() -> "mios_crl.CRL":
    """Force a re-read of the CRL from disk, BYPASSING the mtime cache. Used right
    after a write so a freshly-revoked id is live on the very next check even when the
    filesystem's mtime resolution is too coarse to register the change."""
    _CRL_CACHE["mtime"] = -1.0
    return _load_crl()


def _crl_persist_revoke(ids) -> int:
    """Append revocation ids to the CRL file (_CRL_PATH) in the {"revoked":[...]} shape
    mios_crl.CRL.load reads, atomically, then HOT-RELOAD. Idempotent (set union);
    returns how many ids were newly added. Creates the parent dir if absent. Raises
    OSError when the store is unwritable (the caller maps that to an error response)."""
    want = [str(x).strip() for x in (ids or []) if str(x).strip()]
    if not want:
        return 0
    existing: list = []
    try:
        with open(_CRL_PATH, encoding="utf-8") as fh:
            cur = json.load(fh)
        if isinstance(cur, dict):
            existing = list(cur.get("revoked") or [])
        elif isinstance(cur, (list, tuple)):
            existing = list(cur)
    except (OSError, ValueError):
        existing = []                     # missing/empty/corrupt -> start a fresh set
    existing = [str(x) for x in existing]
    merged = list(dict.fromkeys(existing + want))      # order-stable union
    added = len(merged) - len(dict.fromkeys(existing))
    os.makedirs(os.path.dirname(_CRL_PATH) or ".", exist_ok=True)
    tmp = _CRL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"revoked": merged}, fh)
    os.replace(tmp, _CRL_PATH)            # atomic publish
    _crl_reload()                         # cache-bust so the next check sees it
    return added


def _caller_key_revoked(token, entry=None) -> bool:
    try:
        crl = _load_crl()
        if len(crl) == 0:                 # inert default -> nothing revoked, fast path
            return False
        cands = []
        t = str(token or "").strip()
        if t:
            cands.append(_crl_fingerprint(t))
        if isinstance(entry, dict):
            for k in ("id", "kid", "fingerprint", "principal"):
                v = entry.get(k)
                if v:
                    cands.append(str(v))
        return any(crl.is_revoked(c) for c in cands)
    except Exception:  # noqa: BLE001 -- degrade-open
        return False


def _revoke_ids_from_body(body) -> list:
    """The CRL id(s) a revoke request names. A raw `token` is converted to its
    (non-secret) fingerprint; an explicit id/fingerprint/kid/principal is taken
    verbatim. These map onto how _load_caller_keys keys a caller (token->fingerprint)
    and how the CRL already matches a principal/agent id."""
    if not isinstance(body, dict):
        return []
    ids: list = []
    tok = str(body.get("token") or "").strip()
    if tok:
        ids.append(_crl_fingerprint(tok))
    for k in ("id", "fingerprint", "kid", "principal"):
        v = body.get(k)
        if v and str(v).strip():
            ids.append(str(v).strip())
    return list(dict.fromkeys(ids))       # de-dup, order-stable


async def caller_key_revoke_logic(request) -> JSONResponse:
    _tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    if _check_inbound_principal is None or _check_inbound_principal(_tok) is None:
        return JSONResponse(
            content={"error": {"message": "unauthorized",
                               "type": "invalid_request_error"}}, status_code=401)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(content={"error": "invalid json"}, status_code=400)
    ids = _revoke_ids_from_body(body)
    if not ids:
        return JSONResponse(
            content={"error": "missing key identifier "
                              "(token|id|fingerprint|kid|principal)"}, status_code=400)
    try:
        added = _crl_persist_revoke(ids)
    except OSError as e:
        return JSONResponse(
            content={"error": f"CRL store not writable: {e}"}, status_code=500)
    return JSONResponse(content={"object": "mios.crl.revoke", "revoked": ids,
                                 "added": added, "crl_size": len(_load_crl())})


def _a2a_verify_principal(in_msg: dict) -> "tuple[Optional[bool], str, dict]":
    md = in_msg.get("metadata") if isinstance(in_msg, dict) else None
    verdict, reason, claims = _a2a_pp.verify(
        md, _a2a_text_from_message(in_msg), _passport_verify)
    if verdict and isinstance(claims, dict):
        try:
            crl = _load_crl()
            for _pid in (claims.get("principal"), claims.get("agent")):
                if _pid and crl.is_revoked(str(_pid)):
                    return (False, f"revoked principal: {_pid}", claims)
        except Exception:  # noqa: BLE001 -- degrade-open: a CRL bug never blocks
            pass
    return verdict, reason, claims



_A2A_TASKS: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
_A2A_TASKS_LOCK = asyncio.Lock()
_A2A_TASKS_MAX = int(os.environ.get("MIOS_A2A_TASKS_MAX", "512"))
_A2A_TERMINAL = {_TS_COMPLETED, _TS_FAILED, _TS_CANCELED, _TS_REJECTED}

_A2A_ERR_TASK_NOT_FOUND = -32001
_A2A_ERR_TASK_NOT_CANCELABLE = -32002
_A2A_ERR_UNSUPPORTED_OP = -32004
_A2A_REASON_TASK_NOT_FOUND = "TASK_NOT_FOUND"
_A2A_REASON_TASK_NOT_CANCELABLE = "TASK_NOT_CANCELABLE"
_A2A_REASON_UNSUPPORTED_OP = "UNSUPPORTED_OPERATION"
_A2A_REASON_INVALID_ARGUMENT = "INVALID_ARGUMENT"


def _a2a_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _a2a_text_from_message(msg: dict) -> str:
    """Concatenate the text of a Message's text Parts. LIBERAL on input: accepts a
    v1.0 Part (the `text` member present, discriminated by member presence -- no
    `kind` tag) AND a v0.3 Part (an explicit kind/type == 'text'). A Part that
    explicitly declares a NON-text kind/type is skipped even if some text rides
    along."""
    if not isinstance(msg, dict):
        return ""
    out: list = []
    for p in (msg.get("parts") or []):
        if not isinstance(p, dict):
            continue
        disc = p.get("kind") or p.get("type")
        t = p.get("text")
        if disc == "text" or (disc is None and isinstance(t, str) and t):
            if t:
                out.append(str(t))
    return "\n".join(out)


def _a2a_make_task(context_id: str, in_msg: dict) -> dict:
    """Create a fresh Task in state=TASK_STATE_SUBMITTED with the inbound Message in
    history; mint a contextId/messageId/taskId if absent. The stored inbound
    message's role is normalised to its v1.0 token (liberal in / strict out); v1.0
    Task/Message carry no `kind` discriminator."""
    task_id = str(uuid.uuid4())
    ctx = (context_id or in_msg.get("contextId") or "").strip() or str(uuid.uuid4())
    in_msg = dict(in_msg or {})
    in_msg["role"] = _a2a_role_v1(in_msg.get("role"))
    in_msg.setdefault("messageId", str(uuid.uuid4()))
    in_msg["contextId"] = ctx
    in_msg["taskId"] = task_id
    return {
        "id": task_id,
        "contextId": ctx,
        "status": {"state": _TS_SUBMITTED, "timestamp": _a2a_now()},
        "history": [in_msg],
        "artifacts": [],
    }


async def _a2a_task_record(task: dict) -> None:
    """Insert/refresh a Task in the LRU store; evict oldest beyond cap."""
    tid = task.get("id")
    if not tid:
        return
    async with _A2A_TASKS_LOCK:
        _A2A_TASKS[tid] = task
        _A2A_TASKS.move_to_end(tid)
        while len(_A2A_TASKS) > _A2A_TASKS_MAX:
            _A2A_TASKS.popitem(last=False)



_A2A_PUSH_CONFIGS: dict = {}            # task_id -> {cfg_id: {url, token, …}}
_A2A_PUSH_LOCK = asyncio.Lock()


def _a2a_make_push_cfg_id() -> str:
    return uuid.uuid4().hex


def _redact_payload(val: Any) -> Any:
    try:
        from mios_pipe.redact import redact
        if isinstance(val, str):
            r, _ = redact(val)
            return r
        elif isinstance(val, dict):
            return {k: _redact_payload(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_redact_payload(v) for v in val]
    except Exception:
        pass
    return val


async def _a2a_fire_push_notifications(task: dict) -> None:
    """POST the Task envelope to every webhook registered for this task_id.
    Best-effort: each webhook POST runs in its own try/except so one bad
    consumer never blocks the others or the task itself. Called by
    _a2a_dispatch_send at every state transition."""
    tid = str(task.get("id") or "")
    if not tid:
        return
    async with _A2A_PUSH_LOCK:
        cfgs = list((_A2A_PUSH_CONFIGS.get(tid) or {}).values())
    if not cfgs:
        return
    
    task_redacted = _redact_payload(task)
    
    client = await _get_client()
    for cfg in cfgs:
        url = str(cfg.get("url") or "").strip()
        if not url:
            continue
        headers = {"Content-Type": "application/json"}
        tok = str(cfg.get("token") or "").strip()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        try:
            await client.post(url, json=task_redacted, headers=headers, timeout=10.0)
        except Exception as e:  # noqa: BLE001
            log.warning("a2a push notification to %s failed: %s", url, e)


async def _a2a_dispatch_send(task: dict) -> dict:
    text = _a2a_text_from_message((task.get("history") or [{}])[0])
    task["status"] = {"state": _TS_WORKING, "timestamp": _a2a_now()}
    await _a2a_task_record(task)
    await _a2a_fire_push_notifications(task)
    body = {
        "model": os.environ.get("MIOS_A2A_DEFAULT_MODEL", "MiOS AI"),
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "metadata": {"chat_id": task.get("contextId") or task["id"]},
    }

    def _agent_msg(answer: str) -> dict:
        return {"role": _ROLE_AGENT, "messageId": str(uuid.uuid4()),
                "contextId": task.get("contextId") or "",
                "taskId": task.get("id") or "", "parts": [_a2a_text_part(answer)]}

    try:
        client = await _get_client()
        r = await client.post(
            f"http://127.0.0.1:{PORT}/v1/chat/completions",
            json=body,
            timeout=httpx.Timeout(connect=5.0, read=600.0,
                                  write=10.0, pool=10.0),
        )
        if r.status_code != 200:
            task["status"] = {
                "state": _TS_FAILED, "timestamp": _a2a_now(),
                "message": _agent_msg(f"chat backend {r.status_code}")}
        else:
            data = r.json()
            answer = (((data.get("choices") or [{}])[0].get("message") or {})
                      .get("content") or "")
            task.setdefault("history", []).append(_agent_msg(answer))
            task.setdefault("artifacts", []).append({
                "artifactId": str(uuid.uuid4()),
                "name": "response",
                "parts": [_a2a_text_part(answer)],
            })
            task["status"] = {"state": _TS_COMPLETED, "timestamp": _a2a_now()}
    except Exception as e:  # noqa: BLE001 -- any failure -> task failed
        log.warning("a2a message/send failed: %s", e)
        task["status"] = {
            "state": _TS_FAILED, "timestamp": _a2a_now(),
            "message": _agent_msg(f"a2a dispatch error: {e}")}
    await _a2a_task_record(task)
    await _a2a_fire_push_notifications(task)
    return task


def _a2a_rpc_ok(mid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _a2a_rpc_err(mid, code: int, message: str, data=None,
                 *, reason=None, metadata=None) -> dict:
    """A JSON-RPC 2.0 error in A2A v1.0 shape (§9.5): the standard numeric
    `code` + `message`, and `data` as an ARRAY of typed detail objects (ProtoJSON
    `Any`, each carrying an `@type`). When `reason` is given a google.rpc.ErrorInfo
    detail is attached (reason + domain + optional metadata); an explicit `data`
    overrides. A bare error (no reason/data) stays a valid minimal JSON-RPC error."""
    e: dict = {"code": code, "message": message}
    if data is not None:
        e["data"] = data
    elif reason is not None:
        info = {"@type": _A2A_ERRINFO_TYPE, "reason": reason,
                "domain": _A2A_ERROR_DOMAIN}
        if metadata:
            info["metadata"] = {k: str(v) for k, v in metadata.items()}
        e["data"] = [info]
    return {"jsonrpc": "2.0", "id": mid, "error": e}


async def _a2a_jsonrpc_dispatch(msg: dict) -> dict:
    mid = msg.get("id")
    method = str(msg.get("method") or "")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

    if method in ("message/send", "message:send", "SendMessage"):
        in_msg = params.get("message") or {}
        if not isinstance(in_msg, dict):
            return _a2a_rpc_err(mid, -32602, "params.message must be an object",
                                reason=_A2A_REASON_INVALID_ARGUMENT)
        if not _a2a_text_from_message(in_msg):
            return _a2a_rpc_err(mid, -32602,
                                "params.message has no text Parts",
                                reason=_A2A_REASON_INVALID_ARGUMENT)
        _pv, _preason, _pclaims = _a2a_verify_principal(in_msg)
        if _pv is True:
            log.info("a2a inbound: principal verified (agent=%s on behalf of %s)",
                     _pclaims.get("agent") or "?", _pclaims.get("principal") or "-")
        elif _pv is False:
            log.warning("a2a inbound: principal verify FAILED (%s)", _preason)
            if _A2A_PRINCIPAL_MODE == "verify":      # audit the failure, allow through
                _a2a_principal_audit("verify_failed", _preason, _pclaims)
            elif _A2A_PRINCIPAL_REQUIRE:
                return _a2a_rpc_err(mid, -32600,
                                    f"signed principal required: {_preason}")
        else:                                        # _pv is None -> no principal block
            if _A2A_PRINCIPAL_MODE == "verify":      # audit the absence, allow through
                _a2a_principal_audit("absent", _preason or "absent", _pclaims)
            elif _A2A_PRINCIPAL_REQUIRE:
                return _a2a_rpc_err(mid, -32600, "signed principal required: absent")
        task = _a2a_make_task(in_msg.get("contextId") or "", in_msg)
        await _a2a_task_record(task)
        task = await _a2a_dispatch_send(task)
        return _a2a_rpc_ok(mid, {"task": task})

    if method in ("tasks/get", "GetTask"):
        tid = str(params.get("id") or "").strip()
        if not tid:
            return _a2a_rpc_err(mid, -32602, "missing task id",
                                reason=_A2A_REASON_INVALID_ARGUMENT)
        async with _A2A_TASKS_LOCK:
            t = _A2A_TASKS.get(tid)
            if t is not None:
                _A2A_TASKS.move_to_end(tid)
        if t is None:
            return _a2a_rpc_err(mid, _A2A_ERR_TASK_NOT_FOUND, "task not found",
                                reason=_A2A_REASON_TASK_NOT_FOUND,
                                metadata={"taskId": tid})
        try:
            hl = int(params.get("historyLength") or 0)
        except (TypeError, ValueError):
            hl = 0
        if hl > 0 and isinstance(t.get("history"), list):
            t = dict(t); t["history"] = t["history"][-hl:]
        return _a2a_rpc_ok(mid, t)

    if method in ("tasks/cancel", "CancelTask"):
        tid = str(params.get("id") or "").strip()
        if not tid:
            return _a2a_rpc_err(mid, -32602, "missing task id",
                                reason=_A2A_REASON_INVALID_ARGUMENT)
        async with _A2A_TASKS_LOCK:
            t = _A2A_TASKS.get(tid)
            if t is None:
                return _a2a_rpc_err(mid, _A2A_ERR_TASK_NOT_FOUND,
                                    "task not found",
                                    reason=_A2A_REASON_TASK_NOT_FOUND,
                                    metadata={"taskId": tid})
            state = ((t.get("status") or {}).get("state") or "")
            if state in _A2A_TERMINAL:
                if state != _TS_CANCELED:
                    return _a2a_rpc_err(mid, _A2A_ERR_TASK_NOT_CANCELABLE,
                                        f"task already {state}",
                                        reason=_A2A_REASON_TASK_NOT_CANCELABLE,
                                        metadata={"taskId": tid, "state": state})
            else:
                t["status"] = {"state": _TS_CANCELED, "timestamp": _a2a_now()}
                await _a2a_fire_push_notifications(t)
        return _a2a_rpc_ok(mid, t)

    if method in ("tasks/list", "ListTasks"):
        ctx = str(params.get("contextId") or "").strip()
        try:
            page_size = int(params.get("pageSize") or 50)
        except (TypeError, ValueError):
            page_size = 50
        page_size = max(1, min(page_size, 200))
        async with _A2A_TASKS_LOCK:
            items = list(_A2A_TASKS.values())
        if ctx:
            items = [t for t in items if t.get("contextId") == ctx]
        total = len(items)
        items = list(reversed(items))[:page_size]
        return _a2a_rpc_ok(mid, {"tasks": items, "nextPageToken": "",
                                 "pageSize": page_size, "totalSize": total})

    if method in ("tasks/pushNotificationConfig/set",
                  "tasks.pushNotificationConfig.set",
                  "SetTaskPushNotificationConfig",
                  "CreateTaskPushNotificationConfig"):
        tid = str(params.get("taskId")
                  or params.get("id") or "").strip()
        pcfg = params.get("pushNotificationConfig") or params.get("config")
        if not tid:
            return _a2a_rpc_err(mid, -32602, "missing taskId")
        if not isinstance(pcfg, dict) or not pcfg.get("url"):
            return _a2a_rpc_err(mid, -32602,
                                "pushNotificationConfig.url required")
        async with _A2A_TASKS_LOCK:
            if tid not in _A2A_TASKS:
                return _a2a_rpc_err(mid, _A2A_ERR_TASK_NOT_FOUND,
                                    "task not found")
        cfg_id = str(pcfg.get("id") or _a2a_make_push_cfg_id())
        entry = {
            "id":             cfg_id,
            "url":            str(pcfg.get("url")),
            "token":          pcfg.get("token"),
            "authentication": pcfg.get("authentication"),
        }
        async with _A2A_PUSH_LOCK:
            _A2A_PUSH_CONFIGS.setdefault(tid, {})[cfg_id] = entry
        return _a2a_rpc_ok(mid, {"taskId": tid,
                                 "pushNotificationConfig": entry})

    if method in ("tasks/pushNotificationConfig/get",
                  "tasks.pushNotificationConfig.get",
                  "GetTaskPushNotificationConfig"):
        tid = str(params.get("taskId")
                  or params.get("id") or "").strip()
        cfg_id = str(params.get("pushNotificationConfigId")
                     or params.get("configId") or "").strip()
        if not tid or not cfg_id:
            return _a2a_rpc_err(mid, -32602,
                                "taskId + pushNotificationConfigId required")
        async with _A2A_PUSH_LOCK:
            entry = (_A2A_PUSH_CONFIGS.get(tid) or {}).get(cfg_id)
        if not entry:
            return _a2a_rpc_err(mid, _A2A_ERR_TASK_NOT_FOUND,
                                "push config not found")
        return _a2a_rpc_ok(mid, {"taskId": tid,
                                 "pushNotificationConfig": entry})

    if method in ("tasks/pushNotificationConfig/list",
                  "tasks.pushNotificationConfig.list",
                  "ListTaskPushNotificationConfig"):
        tid = str(params.get("taskId")
                  or params.get("id") or "").strip()
        if not tid:
            return _a2a_rpc_err(mid, -32602, "taskId required")
        async with _A2A_PUSH_LOCK:
            entries = list((_A2A_PUSH_CONFIGS.get(tid) or {}).values())
        return _a2a_rpc_ok(mid, {"taskId": tid,
                                 "pushNotificationConfigs": entries})

    if method in ("tasks/pushNotificationConfig/delete",
                  "tasks.pushNotificationConfig.delete",
                  "DeleteTaskPushNotificationConfig"):
        tid = str(params.get("taskId")
                  or params.get("id") or "").strip()
        cfg_id = str(params.get("pushNotificationConfigId")
                     or params.get("configId") or "").strip()
        if not tid or not cfg_id:
            return _a2a_rpc_err(mid, -32602,
                                "taskId + pushNotificationConfigId required")
        async with _A2A_PUSH_LOCK:
            bucket = _A2A_PUSH_CONFIGS.get(tid) or {}
            removed = bucket.pop(cfg_id, None) is not None
            if not bucket:
                _A2A_PUSH_CONFIGS.pop(tid, None)
        return _a2a_rpc_ok(mid, {"taskId": tid,
                                 "deleted": bool(removed)})

    if method in ("message/stream", "tasks/resubscribe", "SubscribeToTask"):
        return _a2a_rpc_err(mid, _A2A_ERR_UNSUPPORTED_OP,
                            f"{method} not supported (no resubscribe token bus)",
                            reason=_A2A_REASON_UNSUPPORTED_OP)

    return _a2a_rpc_err(mid, -32601, f"unknown method: {method}")


_A2A_STREAM_ENABLED = os.environ.get("MIOS_A2A_STREAM", "1") != "0"


def _a2a_sse(mid, result=None, error=None) -> bytes:
    """One A2A JSON-RPC-over-SSE frame (data: <json>\\n\\n)."""
    payload = {"jsonrpc": "2.0", "id": mid}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return ("data: " + json.dumps(payload) + "\n\n").encode("utf-8")


async def _a2a_stream_response(msg: dict) -> StreamingResponse:
    mid = msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    in_msg = params.get("message") if isinstance(params.get("message"), dict) else None

    async def _gen():
        try:
            if not in_msg or not _a2a_text_from_message(in_msg):
                yield _a2a_sse(mid, error={
                    "code": -32602, "message": "params.message has no text Parts",
                    "data": [{"@type": _A2A_ERRINFO_TYPE,
                              "reason": _A2A_REASON_INVALID_ARGUMENT,
                              "domain": _A2A_ERROR_DOMAIN}]})
                return
            task = _a2a_make_task(in_msg.get("contextId") or "", in_msg)
            await _a2a_task_record(task)
            _w = dict(task)
            _w["status"] = {"state": _TS_WORKING, "timestamp": _a2a_now()}
            yield _a2a_sse(mid, {"task": _w})           # StreamResponse: Task payload
            done = await _a2a_dispatch_send(task)
            yield _a2a_sse(mid, {"task": done})         # final Task frame (stream then closes)
        except Exception as e:  # noqa: BLE001 -- never crash the stream
            yield _a2a_sse(mid, error={"code": -32603, "message": str(e)[:160]})

    return StreamingResponse(_gen(), media_type="text/event-stream")



async def a2a_jsonrpc_logic(request) -> JSONResponse:
    """POST /a2a JSON-RPC 2.0 entry-point logic. Routes message/send, tasks/get,
    tasks/cancel, tasks/list (streaming + push tracked separately, returned as the
    spec UnsupportedOperation error). message/stream is intercepted to SSE before
    the dict/batch dispatch."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(
            _a2a_rpc_err(None, -32700, "parse error"), status_code=400)
    if (_A2A_STREAM_ENABLED and isinstance(body, dict)
            and str(body.get("method") or "") == "message/stream"):
        return await _a2a_stream_response(body)
    if isinstance(body, list):           # JSON-RPC batch
        out: list = []
        for m in body:
            if isinstance(m, dict):
                out.append(await _a2a_jsonrpc_dispatch(m))
        return JSONResponse(out)
    if not isinstance(body, dict):
        return JSONResponse(
            _a2a_rpc_err(None, -32600, "invalid request"), status_code=400)
    return JSONResponse(await _a2a_jsonrpc_dispatch(body))


async def a2a_skills_list_logic() -> JSONResponse:
    """GET /v1/a2a/skills logic: the federated skill catalog -- every skill any
    ready peer declared, with the peer(s) that publish it. Reads the live
    consumer-side _A2A_PEER_SKILLS/_A2A_PEERS under the shared lock."""
    async with _A2A_PEERS_LOCK:
        skills = []
        for sid, peer_ids in _A2A_PEER_SKILLS.items():
            entries = []
            for pid in peer_ids:
                peer = _A2A_PEERS.get(pid) or {}
                match = next((s for s in (peer.get("skills") or [])
                              if s.get("id") == sid), None)
                entries.append({
                    "peer_id": pid,
                    "name": (match or {}).get("name"),
                    "description": (match or {}).get("description"),
                    "tags": (match or {}).get("tags") or [],
                })
            skills.append({"id": sid, "peers": entries})
    return JSONResponse({"object": "mios.a2a.skills", "skills": skills})


async def a2a_dispatch_logic(request) -> JSONResponse:
    """POST /v1/a2a/dispatch logic: forward a message to a chosen A2A peer.
    Body: {peer_id?, skill?, text|message, contextId?}. If peer_id missing but
    skill given, picks the most reliable ready peer that advertises that skill.
    Returns the spec Task envelope."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid json"}, status_code=400)
    peer_id = str(body.get("peer_id") or "").strip() or None
    skill = str(body.get("skill") or "").strip() or None
    context_id = str(body.get("contextId")
                     or body.get("context_id") or "").strip() or None
    text = body.get("text")
    if not text and isinstance(body.get("message"), dict):
        parts = (body["message"].get("parts") or [])
        text = "".join(str(p.get("text") or "") for p in parts
                       if isinstance(p, dict))
    text = str(text or "").strip()
    if not text:
        return JSONResponse({"error": "missing 'text' or 'message'"},
                            status_code=400)
    if not peer_id and skill:
        async with _A2A_PEERS_LOCK:
            candidates = list(_A2A_PEER_SKILLS.get(skill) or [])
            ready = [pid for pid in candidates
                     if (_A2A_PEERS.get(pid) or {}).get("status") == "ready"]
        ranked = _A2A_REPUTATION.rank(ready)
        if ranked:
            peer_id = ranked[0]
    if not peer_id:
        return JSONResponse(
            {"error": "no peer matched (provide peer_id or skill)"},
            status_code=404)
    return JSONResponse(await _a2a_send_message_to_peer(
        peer_id, text, context_id=context_id))


async def passport_verify_logic(request) -> JSONResponse:
    """POST /passport/verify logic: structured (ok, reason) verdict over a posted
    passport envelope (optionally op-hash-bound to a (table, fields) payload),
    without holding the signer's private key."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(
            content={"error": "invalid JSON body"}, status_code=400)
    envelope = body.get("envelope")
    if not isinstance(envelope, dict):
        return JSONResponse(
            content={"error": "envelope object required"},
            status_code=400)
    payload_for_hash = None
    table = body.get("table")
    fields = body.get("fields")
    if table and isinstance(fields, dict):
        payload_for_hash = (str(table), fields)
    ok, reason = _passport_verify(envelope, payload_for_hash)
    return JSONResponse(content={
        "ok": ok,
        "reason": reason,
        "agent": envelope.get("agent"),
        "kid": envelope.get("kid"),
        "alg": envelope.get("alg"),
    })


async def passport_public_key_logic(agent: str = "") -> JSONResponse:
    """GET /passport/public-key logic: return the requested agent's public PEM
    (defaults to this service's own identity). Lets external integrators bootstrap
    verification without filesystem access."""
    target = (agent or PASSPORT_AGENT_NAME).strip()
    pub = _passport_load_public(target)
    if pub is None:
        return JSONResponse(
            content={"error": f"no public key for {target}"},
            status_code=404)
    from cryptography.hazmat.primitives import serialization
    pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return JSONResponse(content={
        "agent": target,
        "alg": PASSPORT_ALGO,
        "public_key_pem": pem,
    })


a2a_router = APIRouter()


@a2a_router.get("/a2a/skills")
async def a2a_skill_directory(request: Request) -> JSONResponse:
    return await a2a_skill_directory_logic()


@a2a_router.get("/a2a/contexts/{context_id}")
async def a2a_context_get(context_id: str) -> JSONResponse:
    return JSONResponse(_a2a_context(context_id))


@a2a_router.get("/v1/contexts/{context_id}")
async def a2a_context_get_v1(context_id: str) -> JSONResponse:
    """/v1 convenience alias for the A2A shared context."""
    return JSONResponse(_a2a_context(context_id))


@a2a_router.post("/a2a")
async def a2a_jsonrpc(request: Request) -> JSONResponse:
    """A2A JSON-RPC 2.0 entry point. Routes message/send, tasks/get,
    tasks/cancel, tasks/list (streaming + push tracked separately as P2.2 /
    P3.3, returned as the spec UnsupportedOperation error). LOCAL-ONLY by
    binding, matching the rest of the A2A surface; tailnet exposure deferred
    until an auth gate ships. Routes to a2a_jsonrpc_logic (same module)."""
    return await a2a_jsonrpc_logic(request)


@a2a_router.post("/a2a/jsonrpc")
async def a2a_jsonrpc_alias(request: Request) -> JSONResponse:
    """Explicit alias for clients that expect the conventional /a2a/jsonrpc
    path. Delegates to the same dispatcher."""
    return await a2a_jsonrpc(request)


@a2a_router.post("/a2a/peers/reload")
async def a2a_peers_reload(request: Request) -> JSONResponse:
    """FED-G3: explicit hot-reload of agent/node/peer membership. Always credential-
    gated (a control-plane mutation), independent of the global api_require_auth flag."""
    _tok = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    if _check_inbound_principal(_tok) is None:
        return JSONResponse(
            content={"error": {"message": "unauthorized", "type": "invalid_request_error"}},
            status_code=401)
    out = await _reload_membership(reason="api")
    return JSONResponse(content={"object": "mios.membership.reload", **out})


@a2a_router.post("/v1/admin/keys/revoke")
async def caller_key_revoke(request: Request) -> JSONResponse:
    """FED-G8: revoke a caller key -- append its id to the CRL + hot-reload so the
    credential is refused immediately, no restart. ADMIN: credential-gated like
    peers/reload, independent of the global api_require_auth flag. Calls
    caller_key_revoke_logic (same module)."""
    return await caller_key_revoke_logic(request)




@a2a_router.get("/.well-known/agent-card.json")
async def a2a_agent_card() -> JSONResponse:
    """A2A AgentCard at the spec well-known path."""
    return JSONResponse(_build_agent_card())


@a2a_router.get("/.well-known/agent.json")
async def a2a_agent_card_legacy() -> JSONResponse:
    """Legacy A2A well-known path (pre-0.3 clients)."""
    return JSONResponse(_build_agent_card())


@a2a_router.get("/.well-known/agent-passport.json")
async def agent_passport() -> JSONResponse:
    """Open Agent Passport: verifiable issuer-signed agent IDENTITY +
    AUTHORITY at the spec well-known path. Native standard; complements the A2A
    AgentCard (capabilities) at /.well-known/agent-card.json."""
    return JSONResponse(_build_agent_passport())


@a2a_router.get("/.well-known/agntcy-manifest.json")
async def agntcy_manifest_wellknown() -> JSONResponse:
    """AGNTCY OASF manifest at the conventional well-known path so a
    discovery directory can scrape this MiOS instance the same way A2A
    clients scrape the agent card."""
    return JSONResponse(_build_agntcy_manifest())


@a2a_router.get("/v1/a2a/peers")
async def a2a_peers_list() -> JSONResponse:
    """Inspect the consumer-side A2A client. Every external peer's status +
    skills_count + protocolVersion + agent_name -- the proof the registry
    was read and cards were fetched. Reads the same live consumer-side peer
    registry + reputation configure() injects for the dispatch/skills logic."""
    async with _A2A_PEERS_LOCK:
        peers = []
        for v in _A2A_PEERS.values():
            peers.append({
                "id": v.get("id"),
                "url": v.get("url"),
                "label": v.get("label"),
                "status": v.get("status"),
                "protocolVersion": v.get("protocolVersion"),
                "agent_name": v.get("agent_name"),
                "skills_count": len(v.get("skills") or []),
                "error": v.get("error"),
            })
    return JSONResponse({"object": "mios.a2a.peers", "peers": peers,
                         "reputation": _A2A_REPUTATION.snapshot()})  # #54


@a2a_router.get("/v1/a2a/skills")
async def a2a_skills_list() -> JSONResponse:
    """Federated skill catalog: every skill any ready peer declared, with the
    peer(s) that publish it. Routing layer for capability-based dispatch. Calls
    a2a_skills_list_logic (same module)."""
    return await a2a_skills_list_logic()


@a2a_router.post("/v1/a2a/dispatch")
async def a2a_dispatch(request: Request) -> JSONResponse:
    """Forward a message to a chosen A2A peer.
    Body: {peer_id?, skill?, text|message, contextId?}.
    If peer_id missing but skill given, picks the first ready peer that
    advertises that skill. Returns the spec Task envelope. Calls
    a2a_dispatch_logic (same module)."""
    return await a2a_dispatch_logic(request)


@a2a_router.post("/passport/verify")
async def passport_verify(request: Request) -> JSONResponse:
    """Cross-agent verification: any agent POSTs {envelope, payload?} and gets a
    structured (ok, reason) response without holding the signer's private key.
    Calls passport_verify_logic (same module)."""
    return await passport_verify_logic(request)


@a2a_router.get("/passport/public-key")
async def passport_public_key(agent: str = "") -> JSONResponse:
    """Return the requested agent's public PEM. Defaults to this
    service's own agent identity. Lets external integrators
    bootstrap verification without filesystem access. Calls
    passport_public_key_logic (same module)."""
    return await passport_public_key_logic(agent)


@a2a_router.get("/v1/agent-card")
async def a2a_agent_card_alias() -> JSONResponse:
    """Convenience alias under /v1 for clients that don't probe
    the well-known path."""
    return JSONResponse(_build_agent_card())


@a2a_router.get("/v1/agntcy/manifest")
async def agntcy_manifest_v1() -> JSONResponse:
    """/v1 alias for the AGNTCY OASF manifest."""
    return JSONResponse(_build_agntcy_manifest())
