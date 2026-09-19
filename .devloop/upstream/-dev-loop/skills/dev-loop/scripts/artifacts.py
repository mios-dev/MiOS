#!/usr/bin/env python3
"""
artifacts.py — canonical autonomous-development artifacts (stdlib only).

  scaffold  [--root .] [--dry-run]        create any missing canonical files from assets/templates/ (never overwrites)
  bridges   [--root .]                    create thin pointer files (CLAUDE.md @AGENTS.md, GEMINI.md, .agents/rules, copilot, cursor, opencode)
  tasks     render   [--root .]           .devloop/tasks.jsonl -> TASKS.md (human view; grouped by epic; - [ ] boxes)
  tasks     validate [--root .]           ids unique, status vocabulary, depends_on resolvable, no cycles, done ⇒ evidence present
  tasks     set <id> <status> [--evidence TEXT] [--root .]
  tasks     add --id T-00N --title ... [--epic ID] [--goal ID] [--depends a,b] [--ac "..."] [--positive CMD --negative CMD --expect RE]
  tasks     next [--root .]               ids that are open with all depends_on done (what a fresh session should pick up)
  tasks     lane <id> [--root .]          print a lane object (v2 schema) for this task, ready to drop into lanes.json
  adr       new "<title>" [--root .]      next NNNN-title.md in docs/decisions from the MADR 4.0 template, status: proposed
  trailer   <id>                           print the commit trailer line for a task
  strip-frontmatter <SKILL.md>             keep only the six agentskills.io frontmatter keys (used when installing into non-Claude harnesses)

Vocabularies (also enforced by `tasks validate`):
  task.status  open | in_progress | blocked | done | cancelled      task.type  task | epic | bug
  goal.status  active | at_risk | met | dropped                    adr.status proposed | accepted | deprecated | superseded
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TPL = HERE.parent / "assets" / "templates"
TASK_STATUS = ["open", "in_progress", "blocked", "done", "cancelled"]
TASK_TYPE = ["task", "epic", "bug"]
CANON = {  # target path -> template
    "AGENTS.md": "AGENTS.md", "docs/GOALS.md": "GOALS.md", "docs/ROADMAP.md": "ROADMAP.md", "docs/DOD.md": "DOD.md",
    "CHECKLISTS.md": "CHECKLISTS.md", "CHANGELOG.md": "CHANGELOG.md", ".devloop/tasks.jsonl": "tasks.jsonl", ".devloop/LEDGER.md": "LEDGER.md",
}
BRIDGES = {
    "CLAUDE.md": "@AGENTS.md\n\n<!-- Claude-specific additions below; the constitution lives in AGENTS.md -->\n",
    "GEMINI.md": "Follow `AGENTS.md` (the project constitution). Gemini/Antigravity-specific additions below.\n",
    ".agents/rules/00-agents.md": "---\ntrigger: always_on\n---\nFollow `AGENTS.md` at the repository root; it is the project constitution. Run engineering work through the `dev-loop` skill.\n",
    ".github/copilot-instructions.md": "Follow `AGENTS.md` at the repository root (project constitution). Run engineering work through the `dev-loop` skill (`/dev-loop`).\n",
    ".cursor/rules/agents.mdc": "---\ndescription: Project constitution pointer\nalwaysApply: true\n---\nFollow `AGENTS.md` at the repository root. Run engineering work through the `dev-loop` skill.\n",
}


def die(m, c=1):
    print(m, file=sys.stderr); sys.exit(c)


def load_tasks(root: Path) -> list[dict]:
    p = root / ".devloop" / "tasks.jsonl"
    if not p.exists(): return []
    out = []
    for n, line in enumerate(p.read_text("utf-8").splitlines(), 1):
        if line.strip():
            try: out.append(json.loads(line))
            except json.JSONDecodeError as e: die(f"tasks.jsonl line {n}: {e}")
    return out


def save_tasks(root: Path, tasks: list[dict]) -> None:
    p = root / ".devloop" / "tasks.jsonl"; p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), "utf-8")
    tmp.replace(p)  # atomic


# ---------------------------------------------------------------- scaffold / bridges
def cmd_scaffold(a):
    root = Path(a.root).resolve(); made = []
    for rel, tpl in CANON.items():
        dst = root / rel
        if dst.exists(): continue
        made.append(rel)
        if not a.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text((TPL / tpl).read_text("utf-8"), "utf-8")
    (root / "docs" / "decisions").mkdir(parents=True, exist_ok=True) if not a.dry_run else None
    (root / "docs" / "runbooks").mkdir(parents=True, exist_ok=True) if not a.dry_run else None
    print(("would create: " if a.dry_run else "created: ") + (", ".join(made) or "nothing (all present)"))
    if made and not a.dry_run: print("fill the <placeholders> in AGENTS.md / GOALS.md before relying on them; then `artifacts.py tasks render`.")


def cmd_bridges(a):
    root = Path(a.root).resolve(); made = []
    for rel, body in BRIDGES.items():
        dst = root / rel
        if dst.exists():
            if rel == "CLAUDE.md" and "@AGENTS.md" not in dst.read_text("utf-8"):
                print("CLAUDE.md exists without `@AGENTS.md` — add it as the first line so the constitution is imported.")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(body, "utf-8"); made.append(rel)
    print("bridges created: " + (", ".join(made) or "none (all present)"))


# ---------------------------------------------------------------- tasks
def validate(tasks: list[dict]) -> list[str]:
    errs = []; ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)): errs.append("duplicate ids")
    for t in tasks:
        i = t.get("id", "?")
        if not re.match(r"^[A-Z]+-\d+$", str(i)): errs.append(f"{i}: id must look like T-001")
        if t.get("status") not in TASK_STATUS: errs.append(f"{i}: status {t.get('status')!r} not in {TASK_STATUS}")
        if t.get("type", "task") not in TASK_TYPE: errs.append(f"{i}: type {t.get('type')!r} not in {TASK_TYPE}")
        for d in t.get("depends_on", []):
            if d not in ids: errs.append(f"{i}: depends_on unknown {d}")
        if t.get("epic") and t["epic"] not in ids: errs.append(f"{i}: epic unknown {t['epic']}")
        if t.get("status") == "done" and not t.get("verification_evidence"):
            errs.append(f"{i}: done without verification_evidence (SKILL §6 — 'done' needs both controls cited)")
    # cycles
    deps = {t["id"]: set(t.get("depends_on", [])) for t in tasks if "id" in t}; done = set()
    while deps:
        ready = [k for k, v in deps.items() if v <= done]
        if not ready: errs.append(f"depends_on cycle among {sorted(deps)}"); break
        done |= set(ready); [deps.pop(k) for k in ready]
    return errs


def cmd_tasks(a):
    root = Path(a.root).resolve(); tasks = load_tasks(root)
    if a.op == "validate":
        errs = validate(tasks)
        die("tasks.jsonl invalid:\n  " + "\n  ".join(errs)) if errs else print(f"tasks.jsonl ok: {len(tasks)} tasks")
    elif a.op == "render":
        errs = validate(tasks)
        if errs: die("refusing to render invalid tasks.jsonl:\n  " + "\n  ".join(errs))
        box = {"done": "x", "cancelled": "-"}
        lines = ["# TASKS", "", "_Rendered from `.devloop/tasks.jsonl` — edit the JSONL (or `artifacts.py tasks set/add`), then `artifacts.py tasks render`. Do not hand-edit this file._", ""]
        epics = [t for t in tasks if t.get("type") == "epic"]; by_epic = {}
        for t in tasks:
            if t.get("type") != "epic": by_epic.setdefault(t.get("epic") or "_none", []).append(t)
        def line(t):
            b = box.get(t["status"], " "); dep = f" ← {', '.join(t['depends_on'])}" if t.get("depends_on") else ""
            own = f" @{t['owner']}" if t.get("owner") else ""; st = "" if t["status"] in ("open", "done") else f" **[{t['status']}]**"
            return f"- [{b}] **{t['id']}** {t['title']}{st}{own}{dep}"
        for e in epics:
            lines += [f"## {e['id']} · {e['title']} · `{e['status']}`" + (f" · goal {e['goal']}" if e.get("goal") else ""), ""]
            lines += [line(t) for t in by_epic.get(e["id"], [])] + [""]
        if by_epic.get("_none"):
            lines += ["## Unassigned", ""] + [line(t) for t in by_epic["_none"]] + [""]
        n_done = sum(t["status"] == "done" for t in tasks); lines += [f"_{n_done}/{len(tasks)} done · {time.strftime('%Y-%m-%d')}_", ""]
        (root / "TASKS.md").write_text("\n".join(lines), "utf-8"); print(f"TASKS.md rendered ({len(tasks)} tasks)")
    elif a.op == "set":
        t = next((t for t in tasks if t["id"] == a.id), None) or die(f"no task {a.id}")
        if a.status not in TASK_STATUS: die(f"status must be one of {TASK_STATUS}")
        if a.status == "done" and not (a.evidence or t.get("verification_evidence")): die("done requires --evidence (both controls, exact commands)")
        t["status"] = a.status
        if a.evidence: t["verification_evidence"] = a.evidence
        t["updated"] = time.strftime("%Y-%m-%d")
        save_tasks(root, tasks); print(f"{a.id} -> {a.status}")
    elif a.op == "add":
        if any(t["id"] == a.id for t in tasks): die(f"{a.id} exists")
        t = {"id": a.id, "type": a.type, "title": a.title, "status": "open", "owner": a.owner or "", "epic": a.epic or "", "goal": a.goal or "",
             "depends_on": [d for d in (a.depends or "").split(",") if d], "acceptance_criteria": a.ac or [],
             "verification": {k: v for k, v in (("positive_cmd", a.positive), ("negative_control_cmd", a.negative), ("negative_expect", a.expect)) if v},
             "verification_evidence": "", "links": [], "notes": "", "created": time.strftime("%Y-%m-%d")}
        tasks.append(t); errs = validate(tasks)
        if errs: die("would make tasks.jsonl invalid:\n  " + "\n  ".join(errs))
        save_tasks(root, tasks); print(f"added {a.id}")
    elif a.op == "next":
        done = {t["id"] for t in tasks if t["status"] in ("done", "cancelled")}
        ready = [t for t in tasks if t["status"] == "open" and t.get("type") != "epic" and set(t.get("depends_on", [])) <= done]
        print("\n".join(f"{t['id']}  {t['title']}" for t in ready) or "(nothing ready — check blocked/in_progress tasks and the ledger)")
    elif a.op == "lane":
        t = next((t for t in tasks if t["id"] == a.id), None) or die(f"no task {a.id}")
        v = t.get("verification", {})
        lane = {"id": re.sub(r"[^a-z0-9_-]", "-", t["id"].lower()), "task_id": t["id"], "objective": t["title"] + ("\nAcceptance: " + "; ".join(t["acceptance_criteria"]) if t.get("acceptance_criteria") else ""),
                "owned_paths": ["<fill: exclusive globs>"], "positive_cmd": v.get("positive_cmd", "<fill>"),
                "negative_control_cmd": v.get("negative_control_cmd", "<fill>"), "negative_expect": v.get("negative_expect", "<fill>"),
                "depends_on": [re.sub(r"[^a-z0-9_-]", "-", d.lower()) for d in t.get("depends_on", [])]}
        print(json.dumps(lane, indent=2))


def cmd_adr(a):
    root = Path(a.root).resolve(); d = root / "docs" / "decisions"; d.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in d.glob("*.md") if (m := re.match(r"^(\d{4})-", p.name))]
    n = max(nums, default=0) + 1; slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:60]
    dst = d / f"{n:04d}-{slug}.md"
    dst.write_text((TPL / "adr.md").read_text("utf-8").replace("{date}", time.strftime("%Y-%m-%d")).replace("{title}", a.title), "utf-8")
    print(f"{dst}  (status: proposed — a human flips it to accepted; agents never self-accept)")


SPEC_KEYS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")


def cmd_strip(a):
    """Reduce a SKILL.md's frontmatter to the six agentskills.io keys (Claude Code extensions such as context/agent/argument-hint are dropped)."""
    p = Path(a.path); s = p.read_text("utf-8")
    if not s.startswith("---"): die(f"{p}: no frontmatter")
    head, _, body = s[3:].partition("\n---")
    keep, cur, dropped = [], None, []
    for line in head.splitlines():
        if line and not line[0].isspace() and ":" in line:
            cur = line.split(":", 1)[0].strip(); (keep if cur in SPEC_KEYS else dropped).append(line)
        elif cur in SPEC_KEYS: keep.append(line)
    p.write_text("---\n" + "\n".join(k for k in keep if k.strip()) + "\n---" + body, "utf-8")
    print(f"{p}: dropped {[d.split(':')[0] for d in dropped if d.strip()]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("scaffold"); p.add_argument("--root", default="."); p.add_argument("--dry-run", action="store_true"); p.set_defaults(f=cmd_scaffold)
    p = sp.add_parser("bridges"); p.add_argument("--root", default="."); p.set_defaults(f=cmd_bridges)
    p = sp.add_parser("tasks"); p.add_argument("op", choices=["render", "validate", "set", "add", "next", "lane"]); p.add_argument("id", nargs="?"); p.add_argument("status", nargs="?")
    p.add_argument("--root", default="."); p.add_argument("--evidence"); p.add_argument("--id", dest="id_flag"); p.add_argument("--title"); p.add_argument("--type", default="task", choices=TASK_TYPE)
    p.add_argument("--owner"); p.add_argument("--epic"); p.add_argument("--goal"); p.add_argument("--depends"); p.add_argument("--ac", action="append")
    p.add_argument("--positive"); p.add_argument("--negative"); p.add_argument("--expect"); p.set_defaults(f=cmd_tasks)
    p = sp.add_parser("adr"); p.add_argument("op", choices=["new"]); p.add_argument("title"); p.add_argument("--root", default="."); p.set_defaults(f=cmd_adr)
    p = sp.add_parser("trailer"); p.add_argument("id"); p.set_defaults(f=lambda a: print(f"Task-Id: {a.id}"))
    p = sp.add_parser("strip-frontmatter"); p.add_argument("path"); p.set_defaults(f=cmd_strip)
    a = ap.parse_args()
    if a.cmd == "tasks":
        if a.op == "add": a.id = a.id_flag or a.id or die("--id required")
        if a.op in ("set", "lane") and not a.id: die("task id required")
        if a.op == "set" and not a.status: die("status required")
        if a.op == "add" and not a.title: die("--title required")
    a.f(a)


if __name__ == "__main__":
    main()
