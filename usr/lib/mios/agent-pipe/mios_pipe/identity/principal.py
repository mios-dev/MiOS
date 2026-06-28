# AI-hint: Pure A2A signed-delegation-principal helpers (#60 WS-6). Builds + verifies. Also HOSTS the low-level agent-passport Ed25519 crypto (canonical op-hash + sign/verify + keypair load/cache, moved verbatim from server.py) that the signed-principal contract here consumes through the injected sign_fn/verify_fn; server.py keeps the surface-pinned PASSPORT_* config consts and injects them via configure(). Still server.py-free (one-way DI boundary) and unit-testable in isolation; cryptography is imported lazily inside the helpers so a host without python3-cryptography still imports the module.
# AI-related: server.py, mios_hitl, mios-passport, /usr/share/mios/mios.toml
# AI-functions: text_digest, build_claims, build_metadata, verify, configure, _passport_canonical_json, _passport_op_hash, _passport_load_priv, _passport_kid, _passport_load_public, _passport_sign, _passport_verify
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

import base64
import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Optional, Tuple

log = logging.getLogger("mios-agent-pipe")

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


# -- Agent-passport Ed25519 crypto (moved VERBATIM from server.py) -----------
# The low-level agent-passport credential the signed-principal contract above
# (build_metadata / verify) consumes through its injected sign_fn/verify_fn:
# deterministic op-hash canonicalisation, Ed25519 sign/verify, and keypair load +
# caching. Moved here so the crypto and the claim shape live together. server.py
# keeps the PASSPORT_* config consts (surface-pinned there) and injects them via
# configure(); the cluster's private cache state moves with it. One-way boundary:
# this module never imports server. cryptography is imported lazily inside the
# helpers so a host without python3-cryptography still imports the module (sign
# calls then degrade to None).
PASSPORT_ENABLE = None
PASSPORT_ALGO = None
PASSPORT_KEY_DIR = None
PASSPORT_AGENT_NAME = None

_passport_priv = None  # cached private key object
_passport_pub_cache: dict[str, Any] = {}
_passport_load_attempted = False


def configure(*, passport_enable=None, passport_algo=None, passport_key_dir=None,
              passport_agent_name=None) -> None:
    """Inject server.py's surface-pinned PASSPORT_* config consts under their EXACT
    original names. An unset keyword leaves the prior binding; the guard is
    ``is not None`` so a real falsey value (PASSPORT_ENABLE=False) still overrides
    the placeholder."""
    global PASSPORT_ENABLE, PASSPORT_ALGO, PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME
    if passport_enable is not None:
        PASSPORT_ENABLE = passport_enable
    if passport_algo is not None:
        PASSPORT_ALGO = passport_algo
    if passport_key_dir is not None:
        PASSPORT_KEY_DIR = passport_key_dir
    if passport_agent_name is not None:
        PASSPORT_AGENT_NAME = passport_agent_name


def _passport_canonical_json(obj) -> str:
    """Deterministic JSON encoding -- matches the mios-passport CLI
    exactly so a signature emitted by one path is verifiable by
    the other."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str)


def _passport_op_hash(table: str, fields: dict) -> str:
    """SHA-256 of `table:canonical-json(fields-minus-passport)`.
    Identical algorithm to mios-passport CLI's op_hash so the two
    sides agree on what's being signed."""
    import hashlib
    payload = dict(fields or {})
    payload.pop("passport", None)
    canon = f"{table}:{_passport_canonical_json(payload)}"
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _passport_load_priv():
    """Best-effort load of this service's Ed25519 private key.
    Returns the key object on success; sets _passport_priv to a
    sentinel False on failure so we don't retry repeatedly."""
    global _passport_priv, _passport_load_attempted
    if _passport_load_attempted:
        return _passport_priv if _passport_priv else None
    _passport_load_attempted = True
    if not PASSPORT_ENABLE:
        _passport_priv = False
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        path = os.path.join(
            PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME, "private.key")
        with open(path, "rb") as f:
            _passport_priv = serialization.load_pem_private_key(
                f.read(), password=None)
        log.info(
            "passport: loaded private key for %s from %s",
            PASSPORT_AGENT_NAME, path)
        return _passport_priv
    except FileNotFoundError:
        log.warning(
            "passport: no private key at %s for agent %s -- "
            "writes will be unsigned until "
            "`mios-passport provision` runs",
            os.path.join(PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME,
                         "private.key"),
            PASSPORT_AGENT_NAME)
        _passport_priv = False
        return None
    except Exception as e:
        log.warning("passport: failed to load private key: %s", e)
        _passport_priv = False
        return None


def _passport_kid() -> str:
    """Read this service's current kid. Defaults to <agent>-v1."""
    path = os.path.join(PASSPORT_KEY_DIR, PASSPORT_AGENT_NAME, "kid")
    try:
        with open(path) as f:
            kid = f.read().strip()
        return kid or f"{PASSPORT_AGENT_NAME}-v1"
    except Exception:
        return f"{PASSPORT_AGENT_NAME}-v1"


def _passport_load_public(agent: str):
    """Resolve an agent's public key. Filesystem first; the
    agent_keypair row as the offline fallback so a verifier
    without filesystem access can still validate."""
    if agent in _passport_pub_cache:
        return _passport_pub_cache[agent]
    try:
        from cryptography.hazmat.primitives import serialization
        path = os.path.join(PASSPORT_KEY_DIR, agent, "public.key")
        with open(path, "rb") as f:
            key = serialization.load_pem_public_key(f.read())
        _passport_pub_cache[agent] = key
        return key
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning("passport: pub key load failed for %s: %s", agent, e)
    return None


def _passport_sign(table: str, fields: dict) -> Optional[dict]:
    """Return a passport envelope for a (table, fields) write, or
    None if signing is disabled / no key available. The envelope is
    safe to attach as `fields["passport"]` -- the op_hash is
    computed over `fields` WITHOUT the passport key (which would be
    circular), so the recipient re-derives the same hash."""
    if not PASSPORT_ENABLE:
        return None
    priv = _passport_load_priv()
    if not priv:
        return None
    try:
        h = _passport_op_hash(table, fields)
        nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        msg = f"{PASSPORT_AGENT_NAME}\n{ts}\n{nonce}\n{h}".encode("utf-8")
        sig = priv.sign(msg)
        return {
            "agent": PASSPORT_AGENT_NAME,
            "ts": ts,
            "nonce": nonce,
            "op_hash": h,
            "alg": PASSPORT_ALGO,
            "kid": _passport_kid(),
            "sig": base64.b64encode(sig).decode("ascii"),
        }
    except Exception as e:
        log.warning("passport: sign failed for %s: %s", table, e)
        return None


def _passport_verify(envelope: dict,
                     payload_for_hash: Optional[tuple] = None
                     ) -> tuple[bool, str]:
    """Verify a passport envelope. (table, fields) tuple in
    payload_for_hash binds the op_hash check. Same algorithm as
    mios-passport's verify_envelope."""
    if not isinstance(envelope, dict):
        return False, "envelope_not_dict"
    agent = envelope.get("agent")
    ts = envelope.get("ts")
    nonce = envelope.get("nonce")
    declared_hash = envelope.get("op_hash")
    sig_b64 = envelope.get("sig")
    alg = envelope.get("alg", "ed25519")
    if not all([agent, ts, nonce, declared_hash, sig_b64]):
        return False, "envelope_missing_field"
    if alg != "ed25519":
        return False, f"unsupported_alg:{alg}"
    if payload_for_hash is not None:
        table, fields = payload_for_hash
        recomputed = _passport_op_hash(table, fields)
        if recomputed != declared_hash:
            return False, "op_hash_mismatch"
    pub = _passport_load_public(agent)
    if pub is None:
        return False, f"no_public_key:{agent}"
    try:
        from cryptography.exceptions import InvalidSignature
        pub.verify(
            base64.b64decode(sig_b64),
            f"{agent}\n{ts}\n{nonce}\n{declared_hash}".encode("utf-8"),
        )
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception as e:
        return False, f"verify_error:{e}"
    return True, "ok"
