<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: The mios-llm-light model map -- maps OpenAI /v1-compatible model tags to llama-server configs, enabling multi-model auto-swapping, KV-cache paging via slot-save-paths, and embeddings for the MiOS agent stack. Served via the upstream llama-swap proxy image.
AI-related: /usr/share/mios/llamacpp/mios-llm-light.yaml, mios-llm-light, mios-agent, mios-agent-cpu, mios-hermes, mios-hermes-cpu, mios-daemon-agent, mios-opencode, mios-igpu, mios-heavy, mios-reasoner-cpu
/usr/share/mios/llamacpp/mios-llm-light.yaml
mios-llm-light model map -- MiOS's primary llama.cpp multi-model lane (WS-10).
The upstream llama-swap proxy launches/swaps a `llama-server` per requested model
behind one OpenAI /v1 endpoint, restoring on-demand multi-model auto-swap for llama.cpp.

Each chat model carries --parallel 1 + --slot-save-path so it lands on a single
deterministic slot and the agent-pipe's _kv_paging (POST /slots/{id}?action=
save|restore) can checkpoint/restore that conversation's KV to disk -- the
AIOS Context Manager, fleet-wide (a swap-only backend can't). The embed model runs
a --embedding llama-server so /v1/embeddings replaces the legacy embed lane.

KV-cache SERVING flags are DOCUMENTED canonically in mios.toml [ai.kv] -- distinct
from the agent-pipe's runtime [dispatch].kv_* paging knobs. NOTE: this yaml is NOT
auto-rendered from [ai.kv]; each lane `cmd` below carries the --slot-save-path
literal DIRECTLY and is kept in sync with [ai.kv] + tmpfiles BY HAND:
  * [ai.kv].slot_save_path documents the --slot-save-path written into every chat
    lane below (keep in sync with usr/lib/tmpfiles.d/mios-llamacpp.conf).
  * [ai.kv].swa_full, when true, appends --swa-full to SWA (sliding-window-
    attention) lanes ONLY, so the full window is retained for correct KV
    checkpoint/restore. The current chat brains (granite4.1:8b, lfm2:700m) are
    HYBRID/RECURRENT, NOT SWA -- --swa-full is MOOT for them and is deliberately
    ABSENT from their cmd below. Append it only when adding a Gemma/Qwen3-SWA lane.
    For hybrid/recurrent KV checkpoint-restore correctness the real lever is the
    llama.cpp BUILD VERSION (track a recent validated llama-swap image pin), not
    this flag.

!! TEMPLATE -- VERIFY before enabling (cannot be validated offline):
  * the ${PORT} substitution + `cmd`/`proxy`/`ttl` keys match your llama-swap
    version's schema (see github.com/mostlygeek/llama-swap README);
  * the llama-server binary path inside the image (here /app/llama-server);
  * the GGUF filenames exist under /models (provisioned by the bake step);
  * --n-gpu-layers / --ctx-size sized to the shared 4090's free VRAM.
Model NAMES should match the model tags the agent-pipe already dispatches
(granite4.1:8b, lfm2:700m, nomic-embed-text, ...) so the lane is a drop-in.

<!-- mios-src:e71875003128 from usr/share/mios/llamacpp/mios-llm-light.yaml:1-36 -->

