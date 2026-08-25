<!-- AI-hint: Specification for the Autonomous Epistemic Evolution and Continuous Learning Loop in MiOS. -->
<!-- AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md, usr/libexec/mios/mios-skill-synthesizer, usr/share/mios/postgres/schema-init.sql -->
# Autonomous Epistemic Evolution & Continuous Learning Loop

## 1. Overview

MiOS is designed to learn from its operational experiences, operator corrections, and successful execution traces. When an operator corrects an agent or verifies a complex workflow (the `/learn` workflow), the system extracts, distills, and permanently bakes this knowledge into future generations of the operating system image.

---

## 2. The Four-Stage Epistemic Loop

```
+-------------------------------------------------------------------+
| 1. Experience & Correction: Operator guidance or verified task    |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 2. Structured Distillation: Rule, Invariant, Anti-Pattern, Check  |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 3. Dual Persistence: PostgreSQL pgvector + /var/lib/mios/skills/  |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
| 4. Image Bake-in: /usr/share/doc/mios/ + Synthetic Model Tuning   |
+-------------------------------------------------------------------+
```

### Stage 1: Experience & Correction Trigger
When an operator corrects an agent's reasoning, resolves an FHS path conflict, or establishes a novel system pattern:
* The session conversation transcript is flagged for distillation.
* The agent identifies the root cause, the invalid assumption, and the corrective invariant.

### Stage 2: Structured Distillation
`usr/libexec/mios/mios-skill-synthesizer` distills the interaction into a standard epistemic artifact:
* **Rule / Invariant**: Concise normative statement (e.g. "Do not execute unshare without bwrap arguments").
* **Grounded Paths**: Concrete FHS file paths and line number references.
* **Anti-Pattern**: Explicit documentation of what was attempted and why it failed.
* **Verification Script**: Executable shell/Python command that asserts the invariant.

### Stage 3: Dual Persistence
* **Fast Semantic Recall**: Indexed into PostgreSQL `knowledge` and `fact_ledger` tables with `nomic-embed-text` vector embeddings for immediate cross-session retrieval.
* **File Template**: Written to `/var/lib/mios/ai/skills/<skill-name>/SKILL.md`.

### Stage 4: OCI Image Bake-in
During the next background image synthesis in `podman-MiOS-DEV` (ADR-0018):
* Distilled documentation is compiled into canonical markdown in `/usr/share/doc/mios/knowledge/`.
* Q&A reasoning pairs are synthesized by `mios-synthetic-qa` into `/var/lib/mios/ai/dataset/` for local fine-tuning of the `mios-opencode` coder model.
