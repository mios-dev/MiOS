# AI-hint: WS-A10 certificate/token revocation list (CRL). Pure-stdlib revocation set: load revoked token-ids / principal-ids from a list (or a caller-t...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_identity_crl_py.md

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
