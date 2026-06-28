# AI-hint: WS-A10 certificate/token revocation list (CRL). Pure-stdlib revocation set: load revoked token-ids / principal-ids from a list (or a caller-tokens.json revoked[] block), check is_revoked(tid) at verify time, and revoke()/restore() at runtime. The agent-pipe's A2A caller-key gate (mios_a2a._caller_key_revoked) consults is_revoked so a compromised/retired credential is refused even before expiry. Pure (no fs/network -- the caller loads the source) so it unit-tests on the host.
# AI-related: ./mios_a2a.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_crl.py
# AI-functions: revoke, restore, is_revoked, load, merge, ids, class CRL
"""mios_crl -- token/cert revocation list (WS-A10, the AIOS edge revocation layer).

Pure stdlib. A small, explicit revocation set the principal verifier consults so
a credential can be killed BEFORE it expires (a compromised token, a retired
peer). The operator/SSOT owns the source list; this holds it + answers
is_revoked. Membership is O(1); empty CRL == nothing revoked (the no-op default)."""

from __future__ import annotations

from typing import Iterable, Set


class CRL:
    """An in-memory revocation set keyed by token-id / principal-id."""

    def __init__(self, revoked: Iterable[str] = ()) -> None:
        self._revoked: Set[str] = {str(x).strip() for x in (revoked or []) if str(x).strip()}

    def is_revoked(self, tid: str) -> bool:
        return str(tid or "").strip() in self._revoked

    def revoke(self, tid: str) -> None:
        t = str(tid or "").strip()
        if t:
            self._revoked.add(t)

    def restore(self, tid: str) -> None:
        self._revoked.discard(str(tid or "").strip())

    def merge(self, other: Iterable[str]) -> None:
        """Union in more revoked ids (e.g. a refreshed CRL from disk)."""
        for x in (other or []):
            self.revoke(x)

    def ids(self) -> list:
        return sorted(self._revoked)

    def __len__(self) -> int:
        return len(self._revoked)

    @classmethod
    def load(cls, source) -> "CRL":
        """Build a CRL from a list, or a dict carrying a `revoked` list (the
        caller-tokens.json shape). Anything else -> an empty CRL (degrade-open
        on a malformed source: a broken CRL must not block every caller)."""
        if isinstance(source, dict):
            return cls(source.get("revoked") or [])
        if isinstance(source, (list, tuple, set)):
            return cls(source)
        return cls()
