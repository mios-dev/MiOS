# AI-hint: Pure A2A signed-delegation-principal helpers (#60 WS-6). Builds + verifies
# AI-related: server.py, mios_hitl, mios-passport, /usr/share/mios/mios.toml
# AI-functions: text_digest, build_claims, build_metadata, verify
#   the signed "principal" block that MiOS AI attaches to an outbound A2A
#   delegation (who is acting, on whose behalf, to whom, about what), and the
#   receive-side verification that binds the delivered instruction text to the
#   signature. Dependency-INJECTED: the caller passes the agent-passport
#   sign_fn/verify_fn (Ed25519) + the acting agent/principal, so this module is
#   server.py-free and unit-testable in isolation (test_mios_a2a_passport.py).
"""Pure helpers for the #60 WS-6 signed delegation principal (A2A).

Why a sibling module: the crypto primitives (Ed25519 sign/verify) and the request
principal live in server.py, but the CLAIM SHAPE + the text-binding + the
metadata routing are deterministic logic that should be tested without importing
the orchestrator. The caller injects sign_fn(table, fields)->envelope|None and
verify_fn(envelope, (table, fields))->(ok, reason); this module supplies the
contract those two sides must agree on.

Rides A2A's message.metadata extension point under the key "mios_principal", so a
non-MiOS peer simply ignores it. Degrade-open: with no key the claims still ride
along but unsigned (passport=None), and the verifier reports "unsigned".
"""
from __future__ import annotations

import hashlib
from typing import Callable, Optional, Tuple

# The op_hash "table" the two sides agree to sign over. Kept here so send + verify
# can never disagree on it.
TABLE = "a2a_delegation"
METADATA_KEY = "mios_principal"


def text_digest(text) -> str:
    """SHA-256 hex of the delegated instruction text -- binds the signature to the
    exact instruction so a man-in-the-middle cannot swap the task."""
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def build_claims(agent, principal, peer_id, context_id, text) -> dict:
    """The signed-over claim set: who is acting (agent), on whose behalf
    (principal; "" = autonomous), to whom (peer), in which context, about what
    (text digest)."""
    return {
        "agent": str(agent or ""),
        "principal": str(principal or ""),
        "peer": str(peer_id or ""),
        "context": str(context_id or ""),
        "text_sha256": text_digest(text),
    }


def build_metadata(agent, principal, peer_id, context_id, text,
                   sign_fn: Callable[[str, dict], Optional[dict]]) -> dict:
    """{'claims':…, 'passport':envelope|None}. The passport is None when no key is
    provisioned -- intentional (unsigned but still attributable)."""
    claims = build_claims(agent, principal, peer_id, context_id, text)
    return {"claims": claims, "passport": sign_fn(TABLE, claims)}


def verify(metadata: Optional[dict], delivered_text,
           verify_fn: Callable[[dict, Tuple[str, dict]], Tuple[bool, str]]
           ) -> "Tuple[Optional[bool], str, dict]":
    """Receive-side check. Returns (verdict, reason, claims):
      verdict None  -> no principal block present (legacy / non-MiOS peer)
      verdict False -> tampered text, unsigned, or bad signature
      verdict True  -> signature valid AND the delivered text matches the claim
    The text-digest check runs BEFORE signature verification, so a swapped
    instruction fails even when carrying an otherwise-valid envelope."""
    block = (metadata or {}).get(METADATA_KEY) if isinstance(metadata, dict) else None
    if not isinstance(block, dict):
        return None, "absent", {}
    claims = block.get("claims") if isinstance(block.get("claims"), dict) else {}
    passport = block.get("passport")
    if claims.get("text_sha256") != text_digest(delivered_text):
        return False, "text_digest_mismatch", claims
    if not isinstance(passport, dict):
        return False, "unsigned", claims
    ok, reason = verify_fn(passport, (TABLE, claims))
    return ok, reason, claims
