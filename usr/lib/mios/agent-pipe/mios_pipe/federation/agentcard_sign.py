# AI-hint: Pure A2A AgentCard JWS/JCS signing and verification module.
# AI-related: mios_pipe/federation/a2a.py, test_mios_agentcard_sign.py
"""Pure A2A v1.0 AgentCard JWS signature and RFC-8785 JCS canonicalization helpers."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("mios-agent-pipe")

# -- A2A v1.0 AgentCard JWS signature (RFC-7515 over RFC-8785 JCS) -------------
_JWS_ALG_EDDSA = "EdDSA"
_A2A_CARD_SIG_FIELD = "signatures"


def _b64u(b: bytes) -> str:
    """RFC-7515 §2 BASE64URL: URL-safe base64, padding stripped."""
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    """Inverse of :func:`_b64u`: restore the stripped RFC-7515 BASE64URL padding
    before decoding back to bytes."""
    raw = str(s or "")
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def _jcs_canonicalize(obj: Any) -> bytes:
    """RFC-8785 (JSON Canonicalization Scheme) bytes for ``obj``: object members
    sorted by key, no insignificant whitespace, UTF-8 with non-ASCII emitted
    LITERALLY."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _agent_card_signing_input(protected_b64: str, card: dict) -> bytes:
    """RFC-7515 §5.1 JWS Signing Input for a DETACHED AgentCard signature:
    ``ASCII(BASE64URL(protected) || '.' || BASE64URL(JCS(card minus signatures)))``."""
    payload = {k: v for k, v in (card or {}).items() if k != _A2A_CARD_SIG_FIELD}
    return (protected_b64 + "." + _b64u(_jcs_canonicalize(payload))).encode("ascii")


def _agent_card_signature(card: dict, *, load_priv_fn=None, kid_fn=None) -> Optional[dict]:
    """FED-G4 / U3: an A2A v1.0 AgentCard JWS signature (RFC-7515 over RFC-8785 JCS).
    A DETACHED JWS over the JCS-canonical card (minus ``signatures``)."""
    try:
        if load_priv_fn is None or kid_fn is None:
            # Sibling import fallback for production wiring
            from mios_pipe.identity.principal import _passport_load_priv, _passport_kid
            load_priv_fn = _passport_load_priv
            kid_fn = _passport_kid

        priv = load_priv_fn()
        if not priv:
            return None
        protected_b64 = _b64u(_jcs_canonicalize(
            {"alg": _JWS_ALG_EDDSA, "kid": kid_fn()}))
        sig = priv.sign(_agent_card_signing_input(protected_b64, card))
        return {"protected": protected_b64, "signature": _b64u(sig)}
    except Exception as e:  # noqa: BLE001 -- degrade-open
        log.debug("agent-card JWS signature skipped: %s", e)
        return None


def _verify_agent_card_signature(card: dict, *, public_key=None, load_pub_fn=None, passport_agent_name="MiOS Operator") -> Tuple[Optional[bool], str]:
    """Receive-side of :func:`_agent_card_signature`: verify an A2A v1.0 AgentCard
    JWS signature (RFC-7515 over RFC-8785 JCS)."""
    sigs = card.get(_A2A_CARD_SIG_FIELD) if isinstance(card, dict) else None
    if not isinstance(sigs, list) or not sigs:
        return None, "unsigned"
    entry = sigs[0] if isinstance(sigs[0], dict) else {}
    protected_b64 = entry.get("protected")
    sig_b64 = entry.get("signature")
    if not protected_b64 or not sig_b64:
        return False, "malformed_signature"
    try:
        header = json.loads(_b64u_decode(protected_b64))
    except Exception:  # noqa: BLE001
        return False, "bad_protected_header"
    alg = header.get("alg") if isinstance(header, dict) else None
    if alg != _JWS_ALG_EDDSA:
        return False, f"unsupported_alg:{alg}"
    pub = public_key
    if pub is None:
        if load_pub_fn is None:
            try:
                from mios_pipe.identity.principal import _passport_load_public
                load_pub_fn = _passport_load_public
            except Exception:
                pass
        if load_pub_fn is not None:
            pub = load_pub_fn(passport_agent_name)

    if pub is None:
        return False, "no_public_key"
    try:
        from cryptography.exceptions import InvalidSignature
        pub.verify(_b64u_decode(sig_b64),
                   _agent_card_signing_input(protected_b64, card))
        return True, "ok"
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception as e:  # noqa: BLE001
        return False, f"verify_error:{e}"
