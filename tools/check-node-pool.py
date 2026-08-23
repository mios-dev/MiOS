#!/usr/bin/env python3
# AI-hint: Drift gate for the fan-out pool. [nodes.*] is dispatched by capacity behind per-lane and per-endpoint semaphores, so a node that repeats another...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: every node in the fan-out pool is a distinct, reachable, honest lane."""

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"


def nodes(data: dict) -> dict:
    """{name: cfg} for every declared compute node."""
    return {str(k): v for k, v in (data.get("nodes") or {}).items()
            if isinstance(v, dict)}


def lane_vocabulary(data: dict) -> set:
    """Legal lane names, read from [dispatch].lane_priority -- the one place the
    scheduler's buckets are declared."""
    raw = str((data.get("dispatch") or {}).get("lane_priority") or "")
    out = set()
    for part in raw.split(","):
        name = part.split(":", 1)[0].strip()
        if name and not name.startswith("_"):
            out.add(name)
    return out


def blades(data: dict) -> set:
    return {str(k) for k in (data.get("blades") or {})}


def _ep(cfg: dict) -> str:
    return str(cfg.get("endpoint") or "").rstrip("/")


def aliases(data: dict) -> list:
    """Two nodes with the same (endpoint, model, lane) are one backend twice."""
    seen, viol = {}, []
    for name, cfg in sorted(nodes(data).items()):
        ep = _ep(cfg)
        if not ep:
            continue  # an empty endpoint is a declared-inert placeholder
        key = (ep, str(cfg.get("model") or ""), str(cfg.get("lane") or ""))
        if key in seen:
            viol.append("[nodes].%s duplicates [nodes].%s exactly (%s) -- the "
                        "fan-out counts one backend as two lanes"
                        % (name, seen[key], key[0]))
        else:
            seen[key] = name
    return viol


def lane_conflicts(data: dict) -> list:
    """One endpoint cannot be two lanes: the semaphore bucket would be split."""
    by_ep, viol = {}, []
    for name, cfg in sorted(nodes(data).items()):
        ep = _ep(cfg)
        if ep:
            by_ep.setdefault(ep, []).append((name, str(cfg.get("lane") or "")))
    for ep, entries in sorted(by_ep.items()):
        lanes = {lane for _, lane in entries}
        if len(lanes) > 1:
            viol.append("endpoint %s is declared as %s by %s -- one endpoint, "
                        "one lane" % (ep, "/".join(sorted(lanes)),
                                      ", ".join(n for n, _ in entries)))
    return viol


def illegal_lanes(data: dict) -> list:
    vocab, viol = lane_vocabulary(data), []
    if not vocab:
        return ["[dispatch].lane_priority declares no lanes -- the gate would "
                "pass vacuously"]
    for name, cfg in sorted(nodes(data).items()):
        lane = str(cfg.get("lane") or "").strip()
        if lane and lane not in vocab:
            viol.append("[nodes].%s declares lane '%s', which [dispatch]."
                        "lane_priority does not budget (legal: %s)"
                        % (name, lane, ", ".join(sorted(vocab))))
    return viol


def orphan_blades(data: dict) -> list:
    """A node MAY omit `blade` -- it then belongs to the local blade, whose name
    comes from [identity].hostname. Naming one that does not exist is the error."""
    known, viol = blades(data), []
    for name, cfg in sorted(nodes(data).items()):
        blade = str(cfg.get("blade") or "").strip()
        if blade and blade not in known:
            viol.append("[nodes].%s names blade '%s', which [blades] does not "
                        "declare" % (name, blade))
    return viol


_LOCAL = re.compile(r"://(?:localhost|127\.0\.0\.1):(\d+)")


def unmovable_endpoints(data: dict) -> list:
    """A local endpoint with a baked port cannot be repointed at a blade."""
    viol = []
    for name, cfg in sorted(nodes(data).items()):
        ep = _ep(cfg)
        for m in _LOCAL.finditer(ep):
            viol.append("[nodes].%s bakes port %s into its endpoint -- an "
                        "/etc/mios overlay cannot move it, so the node can never "
                        "be offloaded" % (name, m.group(1)))
    return viol


def classify(data: dict) -> list:
    if not nodes(data):
        return ["[nodes] declares no compute node -- the gate would pass "
                "vacuously over an empty pool"]
    return (aliases(data) + lane_conflicts(data) + illegal_lanes(data)
            + orphan_blades(data) + unmovable_endpoints(data))


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-node-pool: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = classify(data)
    if viol:
        for v in viol:
            print("check_node_pool: %s" % v, file=sys.stderr)
        return 1

    n = nodes(data)
    live = {_ep(c) for c in n.values() if _ep(c)}
    print("[check-node-pool] %d node(s) over %d distinct endpoint(s); lanes %s; "
          "%d declared inert" % (len(n), len(live),
                                 "/".join(sorted(lane_vocabulary(data))),
                                 sum(1 for c in n.values() if not _ep(c))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
