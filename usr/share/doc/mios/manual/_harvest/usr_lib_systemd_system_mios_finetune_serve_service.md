<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit to host the fine-tuned refiner model as an OpenAI /v1-compatible endpoint on port 11438, allowing the agent-pipe to swap between the high-quality transformer-served adapter and the faster llama.cpp path.
AI-related: /usr/libexec/mios/mios-finetune-serve, mios-finetune-serve, network-online.target, multi-user.target
'MiOS' fine-tune serve -- serves the trained role adapter (base + LoRA) as an
OpenAI /v1 endpoint so the fine-tuned refiner can be adopted/A-B'd
in the agent-pipe. OPT-IN: NOT enabled by default (the transformers-served 2B is
correct but slower than the GGUF lane on the hot path; enable to evaluate, or once
llama.cpp gains Qwen3-Next LoRA switch production to the fast adapter-on-GGUF path).
  systemctl enable --now mios-finetune-serve.service
Pair with a pipe drop-in pointing MIOS_REFINE_ENDPOINT at this server.

<!-- mios-src:943428dc6a55 from usr/lib/systemd/system/mios-finetune-serve.service:1-9 -->

