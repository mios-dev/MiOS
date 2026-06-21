# AI-hint: WS-A10 verified-caller principal core. Pure-stdlib (hmac/hashlib) scoped-token mint+verify so the agent-pipe edge can bind a VERIFIED caller identity (principal + scopes + expiry) instead of trusting a surface-claimed user_name. issue_token signs {sub,scopes,iat,exp,tid} with a shared secret; verify_token does a constant-time signature check + expiry + required-scope + revocation (CRL) check, returning (ok, claims|reason). This is the token half of edge principal binding; the inbound ASGI auth middleware + the caller-tokens store + mTLS are the server.py/VM half. No deps so it unit-tests on the host.
# AI-related: ./mios_crl.py, ./mios_a2a_principal.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_principal.py
# AI-functions: issue_token, verify_token, token_id, _b64u, _b64u_decode
"""mios_principal -- verified-caller scoped tokens (WS-A10, the AIOS edge
Access-Manager identity layer).

Pure stdlib. A scoped token is a signed bearer credential: a base64url JSON
claim set ({sub, scopes, iat, exp, tid}) + an HMAC-SHA256 signature over it. The
edge mints one per caller and verifies it on each dispatch, so authorization
keys off a CRYPTOGRAPHICALLY-VERIFIED principal + scopes rather than an
unauthenticated surface claim. Revocation is delegated to a CRL (mios_crl) via
the `revoked` predicate. (ed25519/mTLS is the heavier transport-auth layer;
this HMAC token is the portable, dependency-free application credential.)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Callable, Iterable, Optional, Tuple


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def token_id(sub: str, iat: int) -> str:
    """A stable token id (for CRL revocation) -- digest of subject+issue-time."""
    return hashlib.sha256(f"{sub}|{iat}".encode()).hexdigest()[:16]


def issue_token(principal: str, scopes: Iterable[str], *, secret: str,
                ttl_s: int = 3600, now: float = 0.0, tid: str = "") -> str:
    """Mint a signed scoped token `<payload>.<sig>`. `now` is epoch seconds
    (pass the real clock at the call site -> this stays pure/deterministic)."""
    iat = int(now)
    claims = {
        "sub": str(principal),
        "scopes": sorted({str(s).strip() for s in (scopes or []) if str(s).strip()}),
        "iat": iat,
        "exp": iat + max(1, int(ttl_s)),
        "tid": str(tid) or token_id(str(principal), iat),
    }
    payload = _b64u(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64u(hmac.new(str(secret).encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_token(token: str, *, secret: str, now: float = 0.0,
                 required_scope: Optional[str] = None,
                 revoked: Optional[Callable[[str], bool]] = None
                 ) -> Tuple[bool, object]:
    """Verify a scoped token. Returns (True, claims) or (False, reason).
    Checks, in order: shape, HMAC signature (constant-time), expiry, revocation
    (the CRL predicate), and the required scope. Fail-closed on any miss."""
    try:
        payload, _, sig = str(token or "").partition(".")
        if not payload or not sig:
            return False, "malformed token"
        expect = _b64u(hmac.new(str(secret).encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expect):
            return False, "bad signature"
        claims = json.loads(_b64u_decode(payload).decode("utf-8"))
        if not isinstance(claims, dict):
            return False, "bad claims"
        if int(now) >= int(claims.get("exp", 0)):
            return False, "expired"
        tid = str(claims.get("tid") or "")
        if revoked is not None and tid and revoked(tid):
            return False, "revoked"
        if required_scope is not None:
            scopes = set(claims.get("scopes") or [])
            if str(required_scope) not in scopes:
                return False, f"missing scope '{required_scope}'"
        return True, claims
    except Exception as e:  # noqa: BLE001 -- any parse/crypto error is a fail-closed deny
        return False, f"verify error: {type(e).__name__}"
