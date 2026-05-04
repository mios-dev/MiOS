#!/usr/bin/env python3
"""
mios-knowledge.local-runner.py — Run the MiOS Knowledge eval against any
OpenAI-compatible /v1/chat/completions endpoint.

Mirrors the testing_criteria from mios-knowledge.eval.json:
  - string_check (ilike): the candidate's answer must mention `must_mention`
  - score_model: an LLM grader rates 0.0 / 0.5 / 1.0 (cloud or local)

Day-0 compatible. Set MIOS_AI_ENDPOINT to:
  http://localhost:8080/v1   (MiOS LocalAI — canonical)
  http://localhost:11434/v1  (Ollama)
  http://localhost:8000/v1   (vLLM)
  http://localhost:1234/v1   (LM Studio)
  http://localhost:4000/v1   (LiteLLM)
  https://api.openai.com/v1  (OpenAI cloud)

Usage:
  pip install httpx
  python3 mios-knowledge.local-runner.py \\
    --endpoint $MIOS_AI_ENDPOINT \\
    --model $MIOS_AI_MODEL \\
    --eval ./mios-knowledge.eval.json \\
    --dataset ./dataset.jsonl \\
    [--grader-endpoint $MIOS_AI_ENDPOINT] \\
    [--grader-model $MIOS_AI_MODEL] \\
    [--system-prompt /etc/mios/system-prompts/mios-engineer.md] \\
    [--limit N] \\
    [--report report.json]
"""
from __future__ import annotations
import argparse, json, os, sys, re, statistics, time
from pathlib import Path

try:
    import httpx
except ImportError:
    sys.exit("pip install httpx")


def chat(endpoint: str, key: str, model: str, messages: list[dict],
         response_format: dict | None = None) -> str:
    """Single non-streaming call. Returns assistant text."""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {"model": model, "messages": messages, "temperature": 0.0}
    if response_format:
        body["response_format"] = response_format
    r = httpx.post(f"{endpoint.rstrip('/')}/chat/completions",
                   headers=headers, json=body, timeout=180.0)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def grade_string_check(output_text: str, must_mention: str) -> bool:
    """ilike — case-insensitive substring."""
    return must_mention.lower() in (output_text or "").lower()


def grade_score_model(grader_endpoint: str, grader_key: str, grader_model: str,
                      item: dict, output_text: str) -> tuple[float, str]:
    """o3-style grader. Returns (score, reason)."""
    try:
        raw = chat(
            grader_endpoint, grader_key, grader_model,
            messages=[
                {"role": "system",
                 "content": ("You are grading MiOS engineering answers. "
                             "Score 1.0 = factually correct AND cites the right MiOS "
                             "file/upstream doc; 0.5 = correct but missing citation; "
                             "0.0 = incorrect or hallucinated. "
                             "Reply with JSON only: {\"score\": <float>, \"reason\": \"<terse>\"}")},
                {"role": "user",
                 "content": (f"Question: {item['question']}\n"
                             f"Expected reference: {item['reference']}\n"
                             f"Must mention: {item['must_mention']}\n"
                             f"Candidate answer: {output_text}")},
            ],
            response_format={"type": "json_object"},
        )
        # Some local servers ignore json_object — best-effort extract
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        obj = json.loads(m.group(0)) if m else {"score": 0.0, "reason": "ungradable"}
        return float(obj.get("score", 0.0)), str(obj.get("reason", ""))
    except Exception as e:
        return 0.0, f"grader-error: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default=os.environ.get("MIOS_AI_ENDPOINT", "http://localhost:8080/v1"))
    ap.add_argument("--key",      default=os.environ.get("MIOS_AI_KEY", ""))
    ap.add_argument("--model",    default=os.environ.get("MIOS_AI_MODEL", "gpt-4o-mini"))
    ap.add_argument("--grader-endpoint", default=None)
    ap.add_argument("--grader-key",      default=None)
    ap.add_argument("--grader-model",    default=None)
    ap.add_argument("--eval",     default="./mios-knowledge.eval.json")
    ap.add_argument("--dataset",  default="./dataset.jsonl")
    ap.add_argument("--system-prompt", default=None,
                    help="Path to a Markdown system prompt; defaults to a built-in mios-engineer.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    # Default grader = same as candidate
    grader_endpoint = args.grader_endpoint or args.endpoint
    grader_key      = args.grader_key      or args.key
    grader_model    = args.grader_model    or args.model

    # System prompt
    if args.system_prompt and Path(args.system_prompt).exists():
        system = Path(args.system_prompt).read_text()
    else:
        system = ("You are MiOS-Engineer. Cite MiOS files (e.g. INDEX.md, ENGINEERING.md, "
                  "SECURITY.md, Containerfile, Justfile, usr/lib/bootc/kargs.d/00-mios.toml, "
                  "usr/share/mios/PACKAGES.md) when stating facts. Refuse to fabricate.")

    items = [json.loads(l) for l in Path(args.dataset).read_text().splitlines() if l.strip()]
    if args.limit:
        items = items[:args.limit]

    print(f"Endpoint: {args.endpoint}  model: {args.model}")
    print(f"Grader:   {grader_endpoint}  model: {grader_model}")
    print(f"Items:    {len(items)}\n")

    results = []
    for i, item in enumerate(items, 1):
        t0 = time.time()
        try:
            answer = chat(args.endpoint, args.key, args.model,
                          messages=[{"role": "system", "content": system},
                                    {"role": "user", "content": item["question"]}])
        except Exception as e:
            answer = f"<<ERROR: {e}>>"

        passed_string = grade_string_check(answer, item["must_mention"])
        score, reason = grade_score_model(grader_endpoint, grader_key, grader_model,
                                          item, answer)
        passed_overall = passed_string and score >= 0.7

        elapsed = time.time() - t0
        marker = "✅" if passed_overall else "❌"
        print(f"{marker} [{i:>3}/{len(items)}] {item['topic']:<12} "
              f"string={passed_string!s:<5} score={score:.2f}  ({elapsed:.1f}s)  "
              f"{item['question'][:70]}")
        results.append({
            **item,
            "answer": answer,
            "string_check_passed": passed_string,
            "score_model_score": score,
            "score_model_reason": reason,
            "passed_overall": passed_overall,
            "elapsed_s": round(elapsed, 2),
        })

    n = len(results)
    n_pass = sum(r["passed_overall"] for r in results)
    avg = statistics.mean(r["score_model_score"] for r in results) if results else 0.0
    print(f"\n=== Summary ===")
    print(f"Pass rate:  {n_pass}/{n} = {100*n_pass/max(n,1):.1f}%")
    print(f"Avg score:  {avg:.2f}")
    print(f"Topics:")
    by_topic = {}
    for r in results:
        by_topic.setdefault(r["topic"], []).append(r["passed_overall"])
    for t, passes in sorted(by_topic.items()):
        print(f"  {t:<12} {sum(passes)}/{len(passes)}")

    if args.report:
        Path(args.report).write_text(json.dumps({
            "endpoint": args.endpoint, "model": args.model,
            "grader_endpoint": grader_endpoint, "grader_model": grader_model,
            "n_total": n, "n_pass": n_pass, "avg_score": avg,
            "results": results,
        }, indent=2))
        print(f"Report written: {args.report}")

    sys.exit(0 if n_pass == n else 1)


if __name__ == "__main__":
    main()
