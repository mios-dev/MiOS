# AI-hint: Redaction utilities for secrets and PII (AGY-8).
# Sanitizes input strings before they are written to persistent storage or federated.
import re

# Redaction patterns
API_KEY_PATTERNS = [
    # OpenAI, HF, Anthropic, generic Bearer tokens, etc.
    re.compile(r"\b(sk-[a-zA-Z0-9]{32,})\b"),
    re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{32,})\b"),
    re.compile(r"\b(hf_[a-zA-Z0-9]{34,})\b"),
    re.compile(r"\b(ghp_[a-zA-Z0-9]{36,})\b"),
    # General Bearer token / auth header content
    re.compile(r"\b(Bearer\s+[a-zA-Z0-9-._~+/]+=*)\b", re.IGNORECASE),
]

EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")

# MIOS_* environment variable secrets / passwords
MIOS_SECRET_PATTERN = re.compile(r"\b(MIOS_[A-Z0-9_]*(?:PASS|SECRET|KEY|TOKEN|AUTH))\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)

def redact(text: str) -> tuple[str, bool]:
    """Sanitizes text by replacing secrets, PII, and MIOS_* variables with [REDACTED].
    Returns (redacted_text, is_redacted)."""
    if not isinstance(text, str) or not text:
        return text, False

    original = text
    redacted = False

    # 1. API Keys
    for pattern in API_KEY_PATTERNS:
        new_text, count = pattern.subn("[REDACTED_API_KEY]", text)
        if count > 0:
            text = new_text
            redacted = True

    # 2. Emails
    text, count = EMAIL_PATTERN.subn("[REDACTED_EMAIL]", text)
    if count > 0:
        redacted = True

    # 3. MIOS_* secrets
    text, count = MIOS_SECRET_PATTERN.subn(r"\1=[REDACTED_SECRET]", text)
    if count > 0:
        redacted = True

    return text, redacted
