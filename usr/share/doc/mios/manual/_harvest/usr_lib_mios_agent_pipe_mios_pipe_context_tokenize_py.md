<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A5 tokenizer seam for the agent-pipe. Centralizes the scattered "len // 4" token estimate behind ONE pluggable interface -- count_text / count_messages / truncate_to_tokens / backend_name -- so context-fit sizing, the OpenAI usage estimate, and history/block truncation all measure tokens THE SAME WAY and an accurate tokenizer can replace the heuristic via set_backend (when one is provisioned) without touching call sites. The default backend is the established ~4-chars/token heuristic -- a DELIBERATE offline-safe default (the agent-pipe carries no tokenizer dependency), not a placeholder: behaviour is byte-identical until a better backend is configured. server.py selects the backend from the [ai].tokenizer_backend SSOT; this module owns the measurement.
AI-related: ./server.py, ./mios_ctxpack.py, ./mios_compact.py, ./test_mios_tokenize.py, /usr/share/mios/mios.toml
AI-functions: count_text, count_messages, truncate_to_tokens, backend_name, set_backend, make_backend, _usage_estimate, class HeuristicBackend, class TiktokenBackend, class HFTokenizerBackend

<!-- mios-src:680abbe12ef8 from usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py:1-3 -->

