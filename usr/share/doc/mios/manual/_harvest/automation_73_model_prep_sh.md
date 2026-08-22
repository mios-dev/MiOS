<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash MIOS_APPLY_CLASS=universal AI-hint: MiOS...

!/usr/bin/env bash
MIOS_APPLY_CLASS=universal
AI-hint: MiOS AI model-weight bake for BOTH local /v1 lanes -- llama.cpp GGUFs and the vLLM snapshot. Folded from 38-llamacpp-prep + 38-vllm-prep; each block is independently env-gated (MIOS_LLAMACPP_BAKE_MODELS / MIOS_VLLM_BAKE_MODEL), writes a disjoint SEED_DIR, and only appends to sbom/models.tsv.
AI-functions: (see blocks below)

<!-- mios-src:7fc6bf04d3ec from automation/73-model-prep.sh:1-4 -->

### AI-hint

AI-hint: Bakes GGUF weights into /usr/share/mios/llamacpp/models based on MIOS_LLAMACPP_BAKE_MODELS config to enable the offline mios-llm-light lane; agents use this to ensure local model availability.
AI-related: /usr/share/mios/llamacpp/models, mios-llm-light, mios-llm-light.container

<!-- mios-src:ee4421af5bf0 from automation/73-model-prep.sh:6-7 -->

