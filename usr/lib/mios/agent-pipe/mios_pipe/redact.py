# AI-hint: Redaction utilities for secrets and PII.
import re

API_KEY_PATTERNS = [
    re.compile(r"\b(sk-[a-zA-Z0-9]{32,})\b"),
    re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{32,})\b"),
    re.compile(r"\b(hf_[a-zA-Z0-9]{34,})\b"),
    re.compile(r"\b(ghp_[a-zA-Z0-9]{36,})\b"),
    re.compile(r"\b(Bearer\s+[a-zA-Z0-9-._~+/]+=*)\b", re.IGNORECASE),
]

EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# MIOS_* environment variable secrets / passwords
MIOS_SECRET_PATTERN = re.compile(r"\b(MIOS_[A-Z0-9_]*(?:PASS|SECRET|KEY|TOKEN|AUTH))\s*=\s*['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE)

def redact(text: str) -> tuple[str, bool]:
    """Sanitizes text by replacing secrets, PII, and MIOS_* variables with [REDACTED].
    Returns (redacted_text, is_redacted)."""
    if not isinstance(text, str) or not text:
        return text, False

    original = text
    redacted = False

    for pattern in API_KEY_PATTERNS:
        new_text, count = pattern.subn("[REDACTED_API_KEY]", text)
        if count > 0:
            text = new_text
            redacted = True

    text, count = EMAIL_PATTERN.subn("[REDACTED_EMAIL]", text)
    if count > 0:
        redacted = True

    text, count = MIOS_SECRET_PATTERN.subn(r"\1=[REDACTED_SECRET]", text)
    if count > 0:
        redacted = True

    return text, redacted
