# AI-hint: Pure prompt text-block formatters lifted verbatim from server.py AI-related: server.py, mios_fanout.py, mios_swarm.py, mios_daemons.py A...
# AI-doc: usr/share/doc/mios/manual/context.md
"""Pure, stateless prompt text-block formatters (strangler-fig extraction)."""

from __future__ import annotations

import json

def _council_role_lens(name: str, cfg: dict) -> str:
    role = str(cfg.get("role", "")).strip().lower()
    strengths = [str(s).strip() for s in (cfg.get("strengths") or [])
                 if str(s).strip()]
    if not role and not strengths:
        return ""
    bits = []
    if role:
        bits.append(f"the {role} lens")
    if strengths:
        bits.append("strengths: " + ", ".join(strengths))
    angle = "; ".join(bits)
    return (
        f"You are agent '{name}' participating in a MULTI-AGENT COUNCIL as "
        f"{angle}. Other agents are answering the same question from their "
        "own angles in parallel; a synthesiser merges all takes. Your job: "
        "focus on what YOUR lens cares about most -- do not try to cover "
        "everything. Be concise, give one decisive angle-specific take, do "
        "not restate the question, do not preface with role labels."
    )

def _format_satisfaction_block(rows: list[dict]) -> str:
    if not rows:
        return ""
    parts = [
        "Recent satisfaction verdicts from mios-daemon "
        "(MOST AUTHORITATIVE ground truth -- daemon AND-folds raw "
        "signals across multiple sources):"
    ]
    for row in rows:
        kind = row.get("kind", "")
        summary = (row.get("summary") or "")[:120]
        marker = "✓ satisfied" if kind == "user_query_satisfied" else "✗ UNSATISFIED"
        parts.append(f"  {marker}: {summary}")
        payload = row.get("payload") or {}
        if kind == "user_query_unsatisfied":
            reason = payload.get("reason")
            failed = payload.get("failed_tools") or []
            if reason:
                parts.append(f"    reason: {reason}")
            for f in failed[:3]:
                parts.append(
                    f"    failed: {f.get('tool')} exit={f.get('exit_code')} "
                    f"err={(f.get('stderr_preview') or '')[:80]}"
                )
        wau = payload.get("write_action_unmet")
        if isinstance(wau, dict) and wau.get("hinted"):
            parts.append(
                "    NOTE: the plan intended a side-effecting action ("
                + ", ".join(str(h) for h in wau["hinted"][:4])
                + ") but NO such action actually ran this turn -- do NOT claim "
                "it was done; state plainly that it was not performed.")
    return "\n".join(parts)

def _format_tool_history(rows: list[dict]) -> str:
    if not rows:
        return ""
    parts = ["Tool history (chronological; CHECK THIS BEFORE WRITING):"]
    for i, row in enumerate(rows, 1):
        tool = row.get("tool", "?")
        args = row.get("args") or {}
        ok = row.get("success")
        exit_code = row.get("exit_code")
        preview = (row.get("result_preview") or "")[:300]
        ok_label = "ok" if ok else (
            f"FAILED (exit={exit_code})" if ok is False else "?")
        parts.append(
            f"  [{i}] {tool}({json.dumps(args, default=str)[:120]}) "
            f"-> {ok_label}"
        )
        if preview.strip():
            parts.append(f"      result: {preview}")
    return "\n".join(parts)

def _build_agent_hint(refined: dict, target_name: str) -> str:
    intent = str(refined.get("intent") or "").strip()
    outcome = str(refined.get("intended_outcome") or "").strip()
    refined_text = str(refined.get("refined_text") or "").strip()
    tools = refined.get("hint_tools") or []
    skills = refined.get("hint_skills") or []
    lines = [
        "# MiOS-Agent refined plan (consume + act; do NOT echo to user)",
        f"target_agent: {target_name}",
    ]
    if intent:
        lines.append(f"intent: {intent}")
    if outcome:
        lines.append(f"intended_outcome: {outcome}")
    if refined_text:
        lines.append(f"refined_query: {refined_text[:400]}")
    if tools:
        lines.append("hint_tools: " + ", ".join(str(t) for t in tools[:8]))
    if skills:
        lines.append("hint_skills: " + ", ".join(str(s) for s in skills[:8]))
    lines.append(
        "tool_access: GLOBAL -- the hints above are SUGGESTIONS, not limits "
        "(see the agent contract). Acting REQUIRES a real tool_call.")
    cards = refined.get("tool_cards") or []
    if isinstance(cards, list) and cards:
        lines.append("tool_cards:")
        for i, c in enumerate(cards[:8]):
            if not isinstance(c, dict):
                continue
            tool = str(c.get("tool") or "").strip()
            why = str(c.get("why") or "").strip()[:160]
            succ = str(c.get("success_predicate") or "").strip()[:160]
            consumed = c.get("output_used_by") or []
            args_hint = c.get("args_hint")
            line = f"  - [{i}] tool={tool}"
            if args_hint:
                try:
                    line += f" args={json.dumps(args_hint, separators=(',', ':'))[:200]}"
                except (TypeError, ValueError):
                    pass
            if why:
                line += f" why={why}"
            if succ:
                line += f" success={succ}"
            if consumed:
                line += f" output_used_by={consumed}"
            lines.append(line)
    return "\n".join(lines)

def _multi_task_preamble(queued: list[dict],
                         active_idx: int = 0) -> str:
    """Render a short user-facing preamble surfacing what's in the
    queue. Goes at the TOP of the polished reply so the operator
    sees the queue state up front (and the polished response for
    the active task comes immediately below)."""
    if not queued or len(queued) < 2:
        return ""
    active = queued[active_idx]
    others = [t for i, t in enumerate(queued) if i != active_idx]
    lines = [
        f"**Queued {len(queued)} tasks from your message.**",
        f"Starting now: _{active.get('title','(untitled)')}_",
        "",
        "Queued for follow-up (run `mios continue` or just say "
        "'next task'):",
    ]
    for t in others:
        lines.append(f"  - {t.get('title','(untitled)')}")
    lines.append("")
    return "\n".join(lines)
