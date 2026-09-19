# Upstream Research Specification (`/research`, `/rs`, `/websearch`, `/s`)

The Upstream Research suite automates truth-finding, upstream dependency diffing, and live documentation discovery to ground all autonomous engineering decisions before altering code.

---

## 1. Commands & Aliases

| Command | Short Alias | Primary Function |
| :--- | :--- | :--- |
| **`/websearch`** | **`/s`** | Real-time documentation queries, API parameter lookups, and error triage. |
| **`/research`** | **`/rs`** | Upstream git diff analysis across commit SHAs/tags, breaking changes, and deprecation audits. |

---

## 2. Upstream Research Protocol (Stage 1 of Dev Loop)

Before modifying code or contracts:

1. **Verify Truth Before Refactoring:** Never guess API signatures or assume deprecation timelines. Run `/websearch` or `/s` to inspect canonical release notes.
2. **Upstream Tag & Digest Auditing:** When bumping dependencies, run `/research <base_tag> <new_tag>`. Inspect deleted interfaces, renamed constants, and breaking schema changes.
3. **Template Scaffolding:** Run `python3 scripts/research.py template <spike|upstream|eval>` to instantiate formal research briefs.
4. **Generate Research Brief:** The research engine produces `UPSTREAM_BRIEF.md` and logs JSON telemetry in `.devloop/`, creating an auditable paper trail.
