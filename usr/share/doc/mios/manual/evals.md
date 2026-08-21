<!-- AI-hint: Manual pages distilled from the source comments of evals, sanitized, each passage anchored to the comment it came from. -->

# evals

### mios-knowledge.local-runner.py — Run the MiOS Knowledge...

mios-knowledge.local-runner.py — Run the MiOS Knowledge eval against any
OpenAI-compatible /v1/chat/completions endpoint.

Mirrors the testing_criteria from mios-knowledge.eval.json:
  - string_check (ilike): the candidate's answer must mention `must_mention`
  - score_model: an LLM grader rates 0.0 / 0.5 / 1.0 (cloud or local)

Day-0 compatible. Set MIOS_AI_ENDPOINT to:
  http://localhost:8642/v1   (MiOS llm-light — canonical)
  http://localhost:11434/v1  (Ollama)
  http://localhost:8000/v1   (vLLM)
  http://localhost:1234/v1   (LM Studio)
  http://localhost:4000/v1   (LiteLLM — use this for routing to vendor clouds)

LAW 5 — UNIFIED-AI-REDIRECTS: vendor cloud endpoints (api.openai.com,
api.anthropic.com, etc.) must not be used directly. Route through LiteLLM
at http://localhost:4000/v1 with provider routing if cloud grading is required.

Usage:
  pip install httpx
  python3 mios-knowledge.local-runner.py \
    --endpoint $MIOS_AI_ENDPOINT \
    --model $MIOS_AI_MODEL \
    --eval ./mios-knowledge.eval.json \
    --dataset ./dataset.jsonl \
    [--grader-endpoint $MIOS_AI_ENDPOINT] \
    [--grader-model $MIOS_AI_MODEL] \
    [--system-prompt /etc/mios/system-prompts/mios-engineer.md] \
    [--limit N] \
    [--report report.json]

<!-- mios-src:ca342d0ce1e0 from var/lib/mios/evals/mios-knowledge.local-runner.py:5-36 -->
