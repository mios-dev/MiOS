# SCOPE Staged Code Review Specification (`/review`, `/rv`)

The Staged Code Review engine enforces quality, security, and architectural oversight based on the **SCOPE** assurance model (Dr. Michaela Greiler, August 2026).

---

## 1. What is SCOPE?

**SCOPE** stands for **Staged Code Oversight with Proportional Escalation**.

Traditional peer review assumes human code production capacity roughly matches peer review capacity. In agentic programming, agent generation throughput is orders of magnitude higher, creating severe review bottlenecks, cognitive debt, and the risk of rubber-stamping.

SCOPE solves this by:
1. Shifting the primary detailed implementation review to the **Steering Developer** who directs the agent.
2. Establishing a dedicated **Agent Review** automation layer that scales contextual checks.
3. Reserving **Peer Review** for independent challenge, architectural assessment, and shared team mental models.
4. Dynamically tuning oversight depth through **Proportional Escalation**.

---

## 2. The 3 Review Stages

```
                  +-----------------------------------+
                  |      Stage 1: Agent Review        |
                  | Static / AST / Security Checks    |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |    Stage 2: Developer Review      |
                  | Mental Model & Unprompted Audit   |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |       Stage 3: Peer Review        |
                  | Proportional Escalation Challenge |
                  +-----------------------------------+
```

### Stage 1: Agent Review (Contextual Automation Layer)
- **Role:** Executes automated static and AST analysis on git diffs before humans spend cognitive energy.
- **Checks:** Credentials/tokens, destructive commands, shell injection risks, corrupted path escapes, debug residue, skip-as-pass test anti-patterns, and blanket git staging.
- **Boundary:** **Zero Accountability**. Agents provide findings and evidence, but cannot assume responsibility for code correctness.

### Stage 2: Developer Review (Steering Developer Ownership)
- **Role:** The developer directing or adopting the agent reviews the implementation.
- **Agent-Dev Loop Sizing:** Sized so the developer maintains an accurate mental model (≤ 600 lines / ≤ 20 files). If overwhelmed, the loop is too large and must be decomposed.
- **Directives:** Identify unprompted agent choices, verify that tests test real invariants rather than echo hallucinations, and officially accept the work as their own.

### Stage 3: Peer Review (Independent Challenge & Shared Ownership)
- **Role:** Independent peers review the work to challenge assumptions, assess cross-system blast radius, and build shared team understanding.
- **Depth:** Proportional, not repetitive. Peers do not duplicate the developer's line-by-line inspection.

---

## 3. Proportional Escalation Dimensions

Oversight depth is calculated from:
1. **Understanding Need (Low / Medium / High):** How much shared understanding is required across the team?
2. **Change Risk (Low / Medium / High):** What happens if the change is wrong?
3. **Established Assurance (Weak / Moderate / Strong):** What justified confidence exists from tests, two-sided validation, and agent audits?

### Escalation Tiers:
- **Tier 1 (Standard):** Fast-track review for low-risk, local changes with strong assurance.
- **Tier 2 (Proportional):** Asynchronous challenge of core decisions and interface touchpoints for medium-risk changes.
- **Tier 3 (Deep Oversight):** Synchronous walkthrough and specialist sign-off for high-risk or high-understanding changes.
- **Escalate Down to Dev:** Rejection of change back to Developer Review if assurance is weak or change size is unmanageable.

---

## 4. The Oversight Record

Stored in `OVERSIGHT_RECORD.md` and `.devloop/scope_review_<timestamp>.json`. Captures the living trace of the oversight conversation across all three stages.

---

## 5. CLI Reference

```bash
# Audit staged changes
python3 scripts/review.py --staged

# Audit a specific commit, range, or branch
python3 scripts/review.py HEAD
python3 scripts/review.py origin/main..HEAD

# Scaffold a fresh OVERSIGHT_RECORD.md
python3 scripts/review.py --init
```
