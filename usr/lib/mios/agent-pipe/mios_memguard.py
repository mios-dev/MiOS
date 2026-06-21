# AI-hint: WS-MEM-VALIDATE write-time memory-poisoning guard (OWASP ASI08, the PURE half). Scans a candidate durable-memory fact (a knowledge Q/A about to be persisted) for poisoning indicators -- embedded prompt-injection imperatives ("ignore previous instructions", role-tag injection), dangerous code-exec patterns (os.system / rm -rf / curl|sh / <script>), and URLs -- and classifies severity (high = injection/dangerous-code, low = url/code-fence only). validate_for_store(mode) applies policy: off (no-op) | log (scan+flag, never blocks) | strip (neutralize URLs/code-fences in the stored text) | reject (drop a high-severity fact). FAIL-OPEN by design: a scanner error never blocks a store (it just stores unflagged) -- the guard hardens the memory store WITHOUT becoming a new way to lose the user's answer. server.py owns wiring this before _store_knowledge_task writes + the SSOT mode; this is the deterministic, testable policy in the mios_pdp/mios_sandbox sibling style.
# AI-related: ./server.py, ./mios_pdp.py, /usr/share/mios/mios.toml, ./test_mios_memguard.py
# AI-functions: scan_fact, validate_for_store, _neutralize
"""mios_memguard -- write-time memory-poisoning validation (WS-MEM-VALIDATE, OWASP ASI08).

A durable-memory store (the knowledge Q/A append) is an injection vector: text
persisted today is RECALLED later and folded into a future turn's context, where
an embedded imperative ("ignore previous instructions...") or a code/exfil
payload can steer the model. MiOS already verdict-gates storage (an UNSATISFIED
turn is not stored), but a SATISFIED answer can still carry poisoned content.

This module is the PURE detector + policy:
  * scan_fact()        -- regex indicators -> {flags, severity, has_*}.
  * validate_for_store(mode) -- off | log | strip | reject.

FAIL-OPEN: a scanner exception never blocks a store (the memory guard must not
become a new way to drop the user's own answer). server.py owns the wiring + the
SSOT mode; this is the deterministic, unit-testable policy.
"""
from __future__ import annotations

import re
from typing import List

# Severity levels (ascending).
NONE = "none"
LOW = "low"
HIGH = "high"

# Prompt-injection imperatives: text that, when later recalled, reads as an
# instruction to the model. These are the core ASI08 risk -> HIGH.
_INJECTION = [re.compile(p, re.IGNORECASE) for p in (
    r"ignore\s+(all\s+|the\s+|your\s+|any\s+)?(previous|prior|above|earlier|preceding)\s+"
    r"(instructions?|prompts?|messages?|context|rules?)",
    r"disregard\s+(all\s+|the\s+|your\s+|any\s+)?(previous|prior|instructions?|system|rules?)",
    r"forget\s+(everything|all|your\s+(instructions?|rules?|prompt))",
    r"\bnew\s+(instructions?|rules?|system\s+prompt)\s*[:\-]",
    r"you\s+are\s+now\s+(a|an|the)\b",
    r"\bsystem\s+prompt\b\s*[:\-]?",
    r"act\s+as\s+(if\s+)?(a|an|the|though)\b",
    r"\boverride\b[^.\n]{0,40}\b(instructions?|rules?|system|safety)\b",
    r"</?\s*(system|instruction|assistant|tool)\s*>",          # role-tag injection
)]

# Dangerous code-exec / exfil payloads -> HIGH.
_DANGER_CODE = [re.compile(p, re.IGNORECASE) for p in (
    r"<\s*script\b",
    r"\bos\.system\s*\(",
    r"\bsubprocess\.(Popen|run|call|check_output)\b",
    r"\beval\s*\(", r"\bexec\s*\(",
    r"\brm\s+-rf\b",
    r"\bcurl\b[^\n|]*\|\s*(ba|z|fi)?sh\b",                     # curl ... | sh
    r"\bwget\b[^\n|]*\|\s*(ba|z|fi)?sh\b",
)]

# Lower-signal indicators (common in legit answers) -> LOW (informational).
_URL = re.compile(r"\bhttps?://[^\s)>\]\"']+", re.IGNORECASE)
_CODE_FENCE = re.compile(r"```")


def scan_fact(text: str) -> dict:
    """Scan a candidate durable-memory fact for poisoning indicators. Returns
    {flags: [str], severity: none|low|high, has_injection, has_danger_code,
    has_url, has_code_fence}. Pure + deterministic. HIGH iff an injection
    imperative OR a dangerous code/exfil pattern is present; LOW iff only a URL /
    code fence; else NONE."""
    s = str(text or "")
    flags: List[str] = []
    inj = next((p.pattern for p in _INJECTION if p.search(s)), None)
    if inj:
        flags.append(f"injection:{inj[:48]}")
    dng = next((p.pattern for p in _DANGER_CODE if p.search(s)), None)
    if dng:
        flags.append(f"danger_code:{dng[:48]}")
    has_url = bool(_URL.search(s))
    has_fence = bool(_CODE_FENCE.search(s))
    if has_url:
        flags.append("url")
    if has_fence:
        flags.append("code_fence")
    severity = HIGH if (inj or dng) else (LOW if (has_url or has_fence) else NONE)
    return {"flags": flags, "severity": severity,
            "has_injection": bool(inj), "has_danger_code": bool(dng),
            "has_url": has_url, "has_code_fence": has_fence}


def _neutralize(text: str) -> str:
    """Defang a fact for 'strip' mode: redact URLs + fence the prose so recalled
    content can't act as a live link or code block. Conservative + reversible-ish
    (keeps the words, removes the executable/clickable shape)."""
    out = _URL.sub("[url removed]", str(text or ""))
    out = out.replace("```", "ʼʼʼ")        # neutralize code-fence markers (look-alike)
    return out


def validate_for_store(text: str, *, mode: str = "off") -> dict:
    """Apply the WS-MEM-VALIDATE policy to a candidate fact. Returns
    {ok, store_text, flags, severity}:
      off    -> always ok, text unchanged (no-op; zero behaviour change).
      log    -> always ok, text unchanged, flags/severity reported (the caller
                emits an audit event when flagged) -- observe-only.
      strip  -> always ok, store_text is the NEUTRALIZED text when flagged.
      reject -> ok=False ONLY on HIGH severity (drop the poisoned fact); LOW/none
                store unchanged.
    FAIL-OPEN: any scanner error -> ok=True, text unchanged (never lose a store)."""
    m = str(mode or "off").strip().lower()
    if m not in ("log", "strip", "reject"):
        return {"ok": True, "store_text": text, "flags": [], "severity": NONE}
    try:
        rep = scan_fact(text)
    except Exception:  # noqa: BLE001 -- fail-open: a guard bug never blocks a store
        return {"ok": True, "store_text": text, "flags": [], "severity": NONE}
    sev, flags = rep["severity"], rep["flags"]
    if m == "reject":
        return {"ok": sev != HIGH, "store_text": text, "flags": flags, "severity": sev}
    if m == "strip":
        st = _neutralize(text) if sev != NONE else text
        return {"ok": True, "store_text": st, "flags": flags, "severity": sev}
    # log
    return {"ok": True, "store_text": text, "flags": flags, "severity": sev}
