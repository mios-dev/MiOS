<!-- AI-hint: Manual pages distilled from the source comments of ai, sanitized, each passage anchored to the comment it came from. -->

# ai

### Autonomous Self-Healing Code Remediation Agent (T-382 /...

Autonomous Self-Healing Code Remediation Agent (T-382 / AGY-1980)

Listens for and detects systemd unit failure events, harvests recent journald error logs,
formulates structured root cause diagnoses, enforces circuit breaker rate limiting
(max 3 restarts / 15m), strictly protects immutable `/usr` partitions (Architectural Law 1),
applies safe `/etc` configuration patches and `/var` repairs, and logs RCA records
to `/var/log/mios/self-heal.log`.

<!-- mios-src:06486356871f from usr/libexec/mios/ai/self_heal.py:4-12 -->

### Enforces Architectural Law 1 (USR-OVER-ETC) & bootc...

Enforces Architectural Law 1 (USR-OVER-ETC) & bootc immutability.
    Strictly forbids modifications to /usr and ensures all mutations are
    scoped to /etc overrides, /var runtime storage, or transient /tmp paths.

<!-- mios-src:4a3daad55758 from usr/libexec/mios/ai/self_heal.py:191-195 -->

### Formulates structured root cause diagnosis from failure...

Formulates structured root cause diagnosis from failure event and journal logs.

<!-- mios-src:5a5c0476a80a from usr/libexec/mios/ai/self_heal.py:351-353 -->

### Synthetic Training Q&A Data Pipeline (T-383 / AGY-1981)...

Synthetic Training Q&A Data Pipeline (T-383 / AGY-1981)

Harvests architectural chapters, user guides, manual pages, and ADRs from `/usr/share/doc/mios/`
and `cat/`, performs hierarchical markdown parsing with context preservation, synthesizes
multi-turn reasoning and domain-specific Q&A pairs for `mios-opencode` fine-tuning,
enforces secret/token redaction (Rule 14), and emits JSONL datasets to `/var/lib/mios/ai/dataset/`.

<!-- mios-src:749518f59c11 from usr/libexec/mios/ai/synthetic_qa.py:4-11 -->
