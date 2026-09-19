# SCOPE Staged Code Review Rubric & Assurance Gate

**Review Target:** `[Branch name, commit SHA, or PR ID]`  
**Reviewer / Engine:** `scripts/review.py` (SCOPE Protocol)  
**Assurance Framework:** Staged Code Oversight with Proportional Escalation (SCOPE)  

---

## 1. The SCOPE Multi-Stage Review Architecture

```
+---------------------------------------------------------------------------------------------------+
|                               The SCOPE Code Oversight Pipeline                                   |
|                                                                                                   |
|  [Stage 1: Agent Review]     --> Automated static/AST audit, secret scans, injection, test checks  |
|                                  (Scales contextual checks; zero human accountability)             |
|                                                                                                   |
|  [Stage 2: Developer Review] --> Steering developer inspects diff, audits unprompted decisions,   |
|                                  evaluates Agent-Dev Loop size, and accepts work as their own     |
|                                                                                                   |
|  [Stage 3: Peer Review]      --> Proportional escalation based on Understanding Need & Risk;       |
|                                  independent challenge, architectural review, shared mental model |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Stage 1: Agent Review (Automated Baseline)

- [ ] **Security & Credential Scanning:** Zero unencrypted API keys, bearer tokens, private keys, or passwords.
- [ ] **Injection Surface Audit:** Zero unsanitized `shell=True`, raw string concatenations in OS executions, or unquoted variables.
- [ ] **Hygiene & Dead Code:** Zero leftover debug prints (`console.log`, `print()`, `pdb.set_trace`) or orphaned stubs.
- [ ] **Test Assertion Integrity:** Zero empty assertions (`pass` in test methods without assertions, `assert True`).
- [ ] **Tree Hygiene:** Zero blanket staging (`git add -A` or `git add .`). Explicit file paths only.

---

## 3. Stage 2: Steering Developer Review & Agent-Dev Loop

- [ ] **Agent-Dev Loop Sizing:** Change set is within cognitive comprehension limits (≤ 600 lines / ≤ 20 files).
- [ ] **Intent Alignment:** Implementation solves the requested problem without unintended feature creep.
- [ ] **Unprompted Decision Audit:** Steering developer has identified, scrutinized, and documented all decisions the agent made autonomously.
- [ ] **Two-Sided Verification:** Verified that positive control passes and negative control fails strictly for the expected defect.
- [ ] **Acceptance of Ownership:** Steering developer officially accepts responsibility for the code.

---

## 4. Stage 3: Peer Review & Proportional Escalation

### 4.1 Escalation Dimension Evaluation

1. **Understanding Need (How much shared understanding is required?):**
   - `LOW`: Local, familiar, isolated change.
   - `MEDIUM`: Cross-subsystem touchpoints, new patterns, or library adoptions.
   - `HIGH`: Architectural shift, public interface migration, or fundamental mental model change.

2. **Change Risk (What happens if the change is wrong?):**
   - `LOW`: Minimal blast radius, immediate local reversibility.
   - `MEDIUM`: User-facing behavior, performance impact, or operational dependencies.
   - `HIGH`: Security critical, auth/crypto, financial, or irreversible database schema alterations.

3. **Established Assurance (What confidence has already been justified?):**
   - `STRONG`: Robust two-sided test suite, passing agent audit, manifest hash verified, clean git tree.
   - `MODERATE`: Standard unit tests passing, clean agent audit.
   - `WEAK`: Missing test coverage or unaddressed agent findings (triggers Escalate Down).

### 4.2 Proportional Review Actions

- **Tier 1 (Standard):** Fast-track asynchronous review. Peer verifies rationale and accepts steering developer sign-off.
- **Tier 2 (Proportional):** Asynchronous challenge. Peer probes unprompted decisions, edge cases, and interface touchpoints.
- **Tier 3 (Deep Oversight):** Synchronous walkthrough. Mandatory specialist consultation (Security/Architecture), cross-team consensus.
- **Escalate Down to Dev:** Reject PR from peer review; return to Developer Review to shrink scope or add missing evidence.

---

## 5. Findings & Sign-Off Ledger

| Finding ID | Severity | Location | Dimension | Description & Required Remediation |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | `[BLOCKER]` | `src/auth.py:42` | `SECURITY` | Unencrypted bearer token in default parameter. Move to env. |
| **F2** | `[WARNING]` | `src/worker.py:118` | `HYGIENE` | Leftover print debugging in retry loop. |

**Final Sign-Off:**
- **Steering Developer:** `[Name / Date]` (Accepted)
- **Peer Reviewer:** `[Name / Date]` (`[APPROVED | REVISE]`)
