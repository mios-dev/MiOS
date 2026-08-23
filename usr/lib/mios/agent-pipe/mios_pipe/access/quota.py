# AI-hint: WS-6 per-user quota + rate-limit core. Pure-stdlib tracker modelled on the LiteLLM per-key budget + RPM pattern: each user gets a sliding-win...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_access_quota_py.md

from __future__ import annotations

import collections
from typing import Deque, Dict, Tuple


class QuotaVerdict:
    __slots__ = ("allowed", "reason", "rpm_used", "spent")

    def __init__(self, allowed: bool, reason: str = "", rpm_used: int = 0,
                 spent: float = 0.0) -> None:
        self.allowed = bool(allowed)
        self.reason = str(reason)
        self.rpm_used = int(rpm_used)
        self.spent = float(spent)

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason,
                "rpm_used": self.rpm_used, "spent": round(self.spent, 4)}


class QuotaTracker:
    """Per-user sliding-window RPM + per-window cost budget.

    rpm_limit    -- max requests per `window_s` (<=0 = unlimited).
    daily_budget -- max cost per `budget_window_s` (<=0 = unlimited).
    """

    def __init__(self, rpm_limit: int = 0, daily_budget: float = 0.0,
                 *, window_s: float = 60.0, budget_window_s: float = 86400.0) -> None:
        self.rpm_limit = int(rpm_limit)
        self.daily_budget = float(daily_budget)
        self.window_s = max(1.0, float(window_s))
        self.budget_window_s = max(1.0, float(budget_window_s))
        self._reqs: Dict[str, Deque[float]] = {}
        self._spend: Dict[str, list] = {}   # user -> [window_start, spent]

    def _rpm_used(self, user: str, now: float) -> int:
        dq = self._reqs.get(user)
        if not dq:
            return 0
        cutoff = now - self.window_s
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq)

    def spent(self, user: str, now: float) -> float:
        w = self._spend.get(user)
        if not w:
            return 0.0
        if now - w[0] >= self.budget_window_s:   # window rolled over -> reset
            return 0.0
        return float(w[1])

    def check(self, user: str, now: float, *, cost: float = 0.0) -> QuotaVerdict:
        """Allow/deny one request for `user` at `now` (and record it if allowed).
        Fail-closed on the configured limits; unlimited dimensions always pass."""
        u = str(user or "")
        if not u:
            return QuotaVerdict(True, "no principal -> unlimited")   # single-user
        used = self._rpm_used(u, now)
        if self.rpm_limit > 0 and used >= self.rpm_limit:
            return QuotaVerdict(False, f"rate limit: {used}/{self.rpm_limit} req per "
                                f"{int(self.window_s)}s", used, self.spent(u, now))
        cur_spent = self.spent(u, now)
        if self.daily_budget > 0 and (cur_spent + max(0.0, cost)) > self.daily_budget:
            return QuotaVerdict(False, f"budget exceeded: {cur_spent:.4f}+{cost:.4f} > "
                                f"{self.daily_budget}", used, cur_spent)
        self._reqs.setdefault(u, collections.deque()).append(float(now))
        w = self._spend.get(u)
        if not w or (now - w[0]) >= self.budget_window_s:
            self._spend[u] = [float(now), max(0.0, float(cost))]
        else:
            w[1] += max(0.0, float(cost))
        return QuotaVerdict(True, "", used + 1, self.spent(u, now))

    def reset(self, user: str) -> None:
        self._reqs.pop(str(user), None)
        self._spend.pop(str(user), None)

    def snapshot(self, user: str) -> dict:
        """A principal's durable ledger: budget window + spend.

        The RPM deque is deliberately not carried. Manual ch60."""
        u = str(user or "")
        w = self._spend.get(u)
        if not w:
            return {"principal": u, "window_start": 0.0, "spent": 0.0}
        return {"principal": u, "window_start": float(w[0]), "spent": float(w[1])}

    def restore(self, user: str, window_start: float, spent: float,
                now: float) -> bool:
        """Re-seat a persisted budget window.

        False (restoring nothing) once the window has rolled over. Manual ch60."""
        u = str(user or "")
        try:
            ws, sp = float(window_start), float(spent)
        except (TypeError, ValueError):
            return False
        if u == "" or ws <= 0 or sp <= 0:
            return False
        if (float(now) - ws) >= self.budget_window_s:
            return False
        self._spend[u] = [ws, sp]
        return True
