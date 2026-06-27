# AI-hint: Pure prompt text-block formatters lifted verbatim from server.py
#   (strangler-fig extraction). Each turns a small data structure into a
#   prompt-injectable string with NO server state, NO network, NO DB -- args +
#   stdlib only, so they are trivially unit-isolated: _council_role_lens (the
#   per-secondary diversity lens for a council, SSOT role+strengths derived),
#   _format_satisfaction_block (daemon satisfaction verdicts incl. the P5
#   write-action-unmet anti-fabrication note), and _format_tool_history (the
#   chronological tool-call ledger the writer must check before claiming done).
# AI-related: server.py, mios_fanout.py, mios_swarm.py, mios_daemons.py
# AI-functions: _council_role_lens, _format_satisfaction_block, _format_tool_history, _build_agent_hint, _multi_task_preamble
"""Pure, stateless prompt text-block formatters (strangler-fig extraction)."""

from __future__ import annotations

import json


def _council_role_lens(name: str, cfg: dict) -> str:
    """P2.1 ("council not fan-out"): per-secondary role
    lens prompt so a council DOES NOT send the same prompt to N models. Each
    secondary gets a small system message identifying its angle (its role +
    declared strengths from mios.toml [agents.*]) so the council answers from
    DIVERSE perspectives instead of duplicating one answer N times. SSOT-
    derived (no hardcoded per-agent text); empty when the agent has neither
    a role nor strengths -- harmless fall-back to identical-prompt mode."""
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
        # Structural action-claim flag (P5): surfaced for ANY verdict (a turn
        # can be "satisfied" by an answer yet still have skipped a planned
        # side-effecting action). Gives polish's INVOKED-TOOL CHECK an explicit,
        # authoritative signal not to let a fabricated "done" stand.
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
    """Render a compact system-message prefix from a refined plan.
    Injected at the head of `messages` when proxying to a sub-
    agent so the agent receives MiOS-Agent's intent + suggested
    tools/skills/outcome -- NOT as free-form prose, but as a
    structured marker block the agent's own system prompt can
    parse.

    Format kept tight (~150-250 tokens) so even a 4K-context
    micro-model has plenty of room for the conversation itself.
    """
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
    # GLOBAL tool access ("all agents have all access to
    # all tools/skills/recipes globally"). The hints above are SUGGESTIONS,
    # not limits -- state it explicitly so an agent never assumes it's scoped
    # to the hinted subset. Compact (no full-catalog dump -- keeps the micro
    # context budget) + reinforces act-don't-narrate.
    # Capability/behaviour rules (global tool access, live internet, no
    # disclaim/fabricate, delegation) now live in the overlay agent-contract
    # .md presented as the LEAD system message at every hop -- not duplicated
    # here. This block carries only the per-plan hints. Keep one terse pointer
    # so the hinted-subset is never misread as a limit.
    lines.append(
        "tool_access: GLOBAL -- the hints above are SUGGESTIONS, not limits "
        "(see the agent contract). Acting REQUIRES a real tool_call.")
    # Per-step tool cards (ReWOO + MCP-style annotations). Carries
    # the WHY + the success predicate INTO the sub-agent so it
    # doesn't have to re-derive the plan. Cap at 8 cards so we
    # stay under ~250 tokens total even for rich plans.
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
                # Render compactly; sub-agent re-parses as JSON.
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
