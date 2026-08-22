<!-- AI-hint: Chapter 10: Local Inference Lanes and llama.cpp. Covers how llama-swap handles hot swapping and KV paging on the `llm_light` port. Maps GPU context management, prompt template bindings, and model formats. Documents model map configuration file and resource optimization strategies. -->

# Chapter 10: Local Inference Lanes and llama.cpp

> Part IV: Detailed Inference & Execution Layers of the [MiOS manual](../manual.md).

This chapter covers the documentation for **Local Inference Lanes and llama.cpp** under MiOS.

### <a name="10_llama_swap_proxy_architecture"></a>10.Llama Swap Proxy Architecture: Llama-Swap Proxy Architecture

> Path Reference: `/usr/share/doc/mios/manual.md#10_llama_swap_proxy_architecture`

#### Overview

The llama-swap proxy manages model requests on the `llm_light` port, serving as the single entry point for light inference tasks.

## Routing Logic
1. **Model Swap**: Swaps the underlying `llama-server` process on-demand to match the requested model name.
2. **Context Saving**: Pages the KV context of inactive conversations to disk using `--slot-save-path`.
3. **KV Restoring**: Reloads KV pages on subsequent requests via `POST /slots/{id}` calls.
4. **Performance**: Reduces memory use by ensuring only active models remain resident in VRAM/RAM.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="10_embedded_inference_setup"></a>10.Embedded Inference Setup: Embedded Inference Setup

> Path Reference: `/usr/share/doc/mios/manual.md#10_embedded_inference_setup`

#### Overview

Embedded inference on MiOS uses optimized GGUF format weights to enable local execution on GPU or CPU.

## Setup Details
- **Context Size**: Standardized context boundaries are mapped dynamically in [38-llamacpp-prep.sh](automation/38-llamacpp-prep.sh).
- **Embeddings**: An embedding-configured llama-server runs in parallel to handle vector queries.
- **Safety**: Uses static model limits and resource controls to prevent container memory limit crashes.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.

---

### <a name="10_model_map_and_hot_swapping"></a>10.Model Map and Hot Swapping: Model Map and Hot Swapping

> Path Reference: `/usr/share/doc/mios/manual.md#10_model_map_and_hot_swapping`

#### Overview

Models are mapped in [mios-llm-light.yaml](usr/share/mios/llamacpp/mios-llm-light.yaml), defining served model aliases and parameters.

## Configuration
- **Model Keys**: Mapping `granite4.1:8b` (default chat), `nomic-embed-text` (embeddings), and `mios-opencode` (coding model).
- **Auto-swap Gating**: llama-swap monitors inbound request headers to spin down idle processes and start target weights.

#### System References

- Relevant configurations: `mios.toml`
- Runtime services: ``MIOS_AI_ENDPOINT``

#### Guidelines & Best Practices

1. Adhere to the Architectural Laws of MiOS at all times.
2. All configurations should be resolved using the three-layer override structure.
3. System state updates must be atomic and verified before reboot.
