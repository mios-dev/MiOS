# AI-hint: Pure Jensen-Shannon divergence monitor over agent-plane verdict/intent/score histograms (CONS-02).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_observability_drift_monitor_py.md
"""Jensen-Shannon drift monitor (CONS-02). Bounded 0..1 divergence against a
frozen baseline; rationale in usr/share/doc/mios/manual/ch53-drift-monitoring.md"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Optional

__all__ = ["histogram", "jensen_shannon", "compare", "is_alerting"]


def histogram(samples: Iterable) -> dict:
    """Count labels into a normalized distribution summing to 1.0.
    Empty input returns {} -- an absent window is not a uniform one."""
    counts: dict = {}
    total = 0
    for s in samples:
        key = str(s)
        counts[key] = counts.get(key, 0) + 1
        total += 1
    if not total:
        return {}
    return {k: v / total for k, v in counts.items()}


def _normalize(dist: Mapping[str, float]) -> dict:
    total = 0.0
    clean: dict = {}
    for k, v in dist.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f != f or f in (float("inf"), float("-inf")) or f < 0.0:
            continue
        clean[str(k)] = f
        total += f
    if total <= 0.0:
        return {}
    return {k: v / total for k, v in clean.items()}


def jensen_shannon(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    """Jensen-Shannon divergence between two label distributions, log base 2,
    so the result is bounded 0.0 (identical) .. 1.0 (disjoint support)."""
    pn = _normalize(p)
    qn = _normalize(q)
    if not pn or not qn:
        return 0.0
    keys = set(pn) | set(qn)
    div = 0.0
    for k in keys:
        pk = pn.get(k, 0.0)
        qk = qn.get(k, 0.0)
        mk = 0.5 * (pk + qk)
        if mk <= 0.0:
            continue
        if pk > 0.0:
            div += 0.5 * pk * math.log2(pk / mk)
        if qk > 0.0:
            div += 0.5 * qk * math.log2(qk / mk)
    # Float error can push an identical pair a hair below zero or a disjoint
    # pair a hair above one; the caller compares against a threshold, so clamp.
    return min(1.0, max(0.0, div))


def compare(
    baseline: Mapping[str, Mapping[str, float]],
    live: Mapping[str, Mapping[str, float]],
    *,
    threshold: float = 0.2,
    min_samples: int = 0,
    live_counts: Optional[Mapping[str, int]] = None,
) -> dict:
    """Score every named axis at once -> {axes, max_divergence, max_axis,
    alerting}. Thin or one-sided axes report compared=False; see ch53."""
    counts = live_counts or {}
    axes: dict = {}
    worst = 0.0
    worst_axis = ""
    alerting = False
    for name in sorted(set(baseline) | set(live)):
        b = baseline.get(name) or {}
        l = live.get(name) or {}
        thin = int(counts.get(name, min_samples)) < int(min_samples)
        compared = bool(b) and bool(l) and not thin
        div = jensen_shannon(b, l) if compared else 0.0
        axis_alert = compared and div >= float(threshold)
        axes[name] = {"divergence": div, "alerting": axis_alert,
                      "compared": compared}
        if compared and div > worst:
            worst, worst_axis = div, name
        alerting = alerting or axis_alert
    return {"axes": axes, "max_divergence": worst, "max_axis": worst_axis,
            "alerting": alerting, "threshold": float(threshold)}


def is_alerting(report: Mapping) -> bool:
    """True when any compared axis crossed the threshold. Tolerates a partial
    or malformed report by answering False -- an alarm must not fire on noise."""
    try:
        return bool(report.get("alerting"))
    except AttributeError:
        return False
