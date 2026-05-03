# API.md

> Canonical OpenAI-API-compatible reference for MiOS.
>
> **Scope:** This document specifies the full OpenAI public API surface that
> 'MiOS' targets via `MIOS_AI_ENDPOINT=http://localhost:8080/v1`
> (Architectural Law 5: UNIFIED-AI-REDIRECTS). Implementation is provided by
> the `mios-ai.container` Quadlet running LocalAI; per-endpoint *served*
> status is **unverified** in the current codebase — verify against the
> deployed LocalAI build with `GET /v1/models` and the per-endpoint probes
> below before relying on any specific endpoint in production.
>
> **Source of truth for the spec:** OpenAI's published reference at
> <https://platform.openai.com/docs/api-reference>. This document tracks
> that surface; when MiOS's served set diverges (e.g., audio/image endpoints
> may not be implemented by LocalAI), the divergence is noted in the
> [Compatibility Matrix](#compatibility-matrix), not by omitting the spec.

## Conventions

### Base URL
```
http://localhost:8080/v1   # in-image
http://<host>:8080/v1      # cross-host
```
The endpoint binds to localhost via `etc/containers/systemd/mios-ai.container` (`PublishPort=8080:8080`). All clients (CLI tools, the `mios` agent, IDE plugins) MUST resolve through `MIOS_AI_ENDPOINT` — vendor-hardcoded URLs are a Law-5 violation and fail audit.

### Authentication
OpenAI's protocol expects `Authorization: Bearer <token>` on every request. LocalAI (and other OpenAI-compatible servers) accept any non-empty token by default. 'MiOS' deployments SHOULD set a non-trivial bearer in `etc/containers/systemd/mios-ai.container.d/auth.conf` or via `Environment=API_KEY=...` and require it via reverse-proxy gating; the spec below assumes the token is supplied even when it is currently a no-op.

```
Authorization: Bearer ${MIOS_AI_API_KEY}
Content-Type:  application/json
```

### Versioning
All paths under `/v1`. Newer surfaces (Responses API, Realtime) are also `/v1`. Beta/admin surfaces require additional headers — noted per-endpoint.

### Pagination
List endpoints accept `limit` (default 20, max 100), `order` (`asc`|`desc`), `after`, `before`. Responses include `data[]`, `first_id`, `last_id`, `has_more`.

### Errors
Standard error envelope:
```json
{
  "error": {
    "message": "string",
    "type":    "invalid_request_error | authentication_error | rate_limit_error | api_error | tools_error",
    "param":   "string | null",
    "code":    "string | null"
  }
}
```
HTTP 4xx/5xx mirror REST conventions. Streamed errors arrive as `event: error` SSE frames.

### Streaming
Endpoints supporting `stream: true` emit Server-Sent Events with `data:` lines terminated by `data: [DONE]`. Realtime uses WebSocket (or WebRTC for audio).

## Compatibility Matrix

`'MiOS' Status` values:
- `Unverified` — endpoint defined in this spec but not yet probed against the deployed LocalAI image. Default for the current build.
- `Served` — confirmed reachable and protocol-conformant.
- `Proxied` — request is forwarded to an upstream that may or may not be MiOS-resident.
- `Unsupported` — definitively not implemented by the current LocalAI build; client SHOULD short-circuit.

| Group | Endpoint | 'MiOS' Status |
|---|---|---|
| Models | `GET /v1/models`, `GET /v1/models/{model}`, `DELETE /v1/models/{model}` | Unverified |
| Chat | `POST /v1/chat/completions` | Unverified |
| Completions (legacy) | `POST /v1/completions` | Unverified |
| Responses | `POST /v1/responses`, `GET /v1/responses/{id}`, `DELETE /v1/responses/{id}`, `GET /v1/responses/{id}/input_items` | Unverified |
| Embeddings | `POST /v1/embeddings` | Unverified |
| Audio | `POST /v1/audio/transcriptions`, `POST /v1/audio/translations`, `POST /v1/audio/speech` | Unverified |
| Images | `POST /v1/images/generations`, `POST /v1/images/edits`, `POST /v1/images/variations` | Unverified |
| Files | `POST /v1/files`, `GET /v1/files`, `GET /v1/files/{id}`, `DELETE /v1/files/{id}`, `GET /v1/files/{id}/content` | Unverified |
| Uploads | `POST /v1/uploads`, `POST /v1/uploads/{id}/parts`, `POST /v1/uploads/{id}/complete`, `POST /v1/uploads/{id}/cancel` | Unverified |
| Vector Stores | `POST/GET/DELETE /v1/vector_stores`, `…/{id}` | Unverified |
| VS Files | `POST/GET/DELETE /v1/vector_stores/{id}/files[/{file_id}]` | Unverified |
| VS File Batches | `POST/GET /v1/vector_stores/{id}/file_batches[/{batch_id}]`, `…/cancel`, `…/files` | Unverified |
| Assistants | `POST/GET/DELETE /v1/assistants[/{id}]` | Unverified |
| Threads | `POST/GET/DELETE /v1/threads[/{id}]` | Unverified |
| Messages | `POST/GET/DELETE /v1/threads/{tid}/messages[/{mid}]` | Unverified |
| Runs | `POST/GET /v1/threads/{tid}/runs[/{rid}]`, `…/cancel`, `…/submit_tool_outputs` | Unverified |
| Run Steps | `GET /v1/threads/{tid}/runs/{rid}/steps[/{sid}]` | Unverified |
| Batches | `POST/GET /v1/batches[/{id}]`, `…/cancel` | Unverified |
| Fine-tuning | `POST/GET /v1/fine_tuning/jobs[/{id}]`, `…/cancel`, `…/events`, `…/checkpoints` | Unverified |
| Moderations | `POST /v1/moderations` | Unverified |
| Realtime | `WS /v1/realtime`, `POST /v1/realtime/sessions` | Unverified |
| Admin | `/v1/organization/*` | Unsupported (single-tenant deployment) |

To probe live: `curl -fsS -H "Authorization: Bearer $MIOS_AI_API_KEY" "$MIOS_AI_ENDPOINT/models" | jq '.data[].id'`. If that returns model IDs, chat/embeddings are typically also live.

---

## Models

### `GET /v1/models`
List models the deployment can serve. LocalAI advertises models declared under `/srv/ai/models/*.yaml`.

Response:
```json
{
  "object": "list",
  "data": [
    { "id": "string", "object": "model", "created": 0, "owned_by": "string" }
  ]
}
```

### `GET /v1/models/{model}`
Single-model lookup.

### `DELETE /v1/models/{model}`
Remove a fine-tuned/uploaded model. Base/system models cannot be deleted.

---

## Chat Completions

### `POST /v1/chat/completions`
Primary text-generation endpoint. Supports tool/function calling, JSON mode, vision (`image_url` parts), audio (`input_audio` parts), and SSE streaming.

Request:
```jsonc
{
  "model":            "string",                  // required
  "messages":         [Message, ...],            // required
  "max_completion_tokens": 0,                    // newer; replaces max_tokens for o-series
  "max_tokens":       0,                         // legacy; still accepted
  "temperature":      1.0,                       // 0–2
  "top_p":            1.0,
  "n":                1,
  "stream":           false,
  "stream_options":   { "include_usage": false },
  "stop":             "string | string[]",
  "presence_penalty":  0.0,
  "frequency_penalty": 0.0,
  "logit_bias":       { "tokenId": -100 },
  "logprobs":         false,
  "top_logprobs":     0,
  "user":             "string",
  "tools":            [Tool, ...],
  "tool_choice":      "none | auto | required | { type: 'function', function: { name } }",
  "parallel_tool_calls": true,
  "response_format":  { "type": "text | json_object | json_schema",
                        "json_schema": { "name": "...", "strict": true, "schema": { … } } },
  "seed":             0,
  "service_tier":     "auto | default",
  "store":            false,
  "metadata":         { "key": "value" },
  "reasoning_effort": "low | medium | high"     // o-series
}
```

`Message` shape:
```jsonc
{
  "role":      "system | developer | user | assistant | tool",
  "content":   "string | ContentPart[]",
  "name":      "string",                         // optional
  "tool_calls":[ ToolCall ],                     // assistant only
  "tool_call_id":"string"                        // tool only
}
```

`ContentPart` shapes: `{type:"text",text}`, `{type:"image_url",image_url:{url,detail}}`, `{type:"input_audio",input_audio:{data,format}}`, `{type:"file",file:{file_id|file_data|filename}}`.

`Tool` (function-calling):
```json
{ "type":"function",
  "function":{ "name":"string", "description":"string",
               "parameters":{ /* JSON Schema */ },
               "strict": true } }
```

Response (non-stream):
```jsonc
{
  "id":"chatcmpl-…", "object":"chat.completion", "created":0, "model":"string",
  "choices":[
    { "index":0,
      "message":{ "role":"assistant", "content":"string|null", "tool_calls":[…], "refusal":null },
      "logprobs":null,
      "finish_reason":"stop|length|tool_calls|content_filter|function_call" }
  ],
  "usage":{ "prompt_tokens":0,"completion_tokens":0,"total_tokens":0,
            "completion_tokens_details":{"reasoning_tokens":0} },
  "system_fingerprint":"string"
}
```

Streaming: SSE with `chat.completion.chunk` objects whose `choices[0].delta` carries incremental `content`/`tool_calls` deltas; final frame is `data: [DONE]`.

Probe:
```bash
curl -fsS -H "Authorization: Bearer $MIOS_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4.1","messages":[{"role":"user","content":"ping"}]}' \
  "$MIOS_AI_ENDPOINT/chat/completions"
```

---

## Completions (Legacy)

### `POST /v1/completions`
Single-prompt text generation. Retained for legacy compatibility; new code SHOULD use `/chat/completions` or `/responses`.

Request: `{ model, prompt, max_tokens, temperature, top_p, n, stream, logprobs, echo, stop, presence_penalty, frequency_penalty, best_of, logit_bias, user, suffix }`.

Response: `{ id, object:"text_completion", created, model, choices:[{ text, index, logprobs, finish_reason }], usage }`.

---

## Responses

The Responses API unifies chat, tool-use, vision, file/image inputs, and stateful conversations into one endpoint. Newer than `/chat/completions`; SHOULD be the default for new 'MiOS' agent code.

### `POST /v1/responses`
Request:
```jsonc
{
  "model": "string",
  "input": "string | InputItem[]",                 // text or structured items
  "instructions": "string",                        // system-style preamble
  "previous_response_id": "string",                // chain prior turn for state reuse
  "tools": [ Tool, ... ],                          // function | file_search | web_search_preview | computer_use | …
  "tool_choice": "auto | none | required | { … }",
  "parallel_tool_calls": true,
  "stream": false,
  "stream_options": { "include_obfuscation": false },
  "include": [ "file_search_call.results", "message.input_image.image_url",
               "computer_call_output.output.image_url",
               "reasoning.encrypted_content" ],
  "max_output_tokens": 0,
  "temperature": 1.0,
  "top_p": 1.0,
  "metadata": { "key":"value" },
  "store": true,
  "background": false,
  "reasoning": { "effort":"low|medium|high", "summary":"auto|concise|detailed" },
  "text": { "format":{ "type":"text|json_schema|json_object", "json_schema":{ … } } },
  "truncation": "auto | disabled",
  "service_tier": "auto | default | flex"
}
```

`InputItem` types: `message`, `file_search_call`, `function_call`, `function_call_output`, `computer_call`, `computer_call_output`, `web_search_call`, `reasoning`, `input_image`, `input_file`.

Response:
```jsonc
{
  "id":"resp_…", "object":"response", "created_at":0, "model":"string",
  "status":"completed | in_progress | incomplete | failed | cancelled",
  "output":[ /* ordered list of output items: messages, tool calls, reasoning */ ],
  "output_text":"string",                          // convenience flatten
  "usage":{ "input_tokens":0,"output_tokens":0,"total_tokens":0,
            "input_tokens_details":{"cached_tokens":0},
            "output_tokens_details":{"reasoning_tokens":0} },
  "incomplete_details": null,
  "error": null,
  "metadata": { … },
  "previous_response_id": null,
  "parallel_tool_calls": true,
  "store": true
}
```

### `GET /v1/responses/{response_id}`
Fetch a stored Response.

### `DELETE /v1/responses/{response_id}`
Delete a stored Response.

### `GET /v1/responses/{response_id}/input_items`
Paginated list of input items the Response was created with.

### `POST /v1/responses/{response_id}/cancel`
Cancel a `background:true` Response in progress.

---

## Embeddings

### `POST /v1/embeddings`
Generate dense vectors.

Request:
```json
{
  "model": "string",
  "input": "string | string[] | int[] | int[][]",
  "encoding_format": "float | base64",
  "dimensions": 0,
  "user": "string"
}
```
Response:
```json
{ "object":"list",
  "data":[{ "object":"embedding","index":0,"embedding":[0.0, …] }],
  "model":"string",
  "usage":{ "prompt_tokens":0,"total_tokens":0 } }
```

'MiOS' cross-ref: `var/lib/mios/embeddings/chunks.jsonl` is produced in the embedding format LocalAI returns; the ingestion pipeline reads from this endpoint.

---

## Audio

### `POST /v1/audio/transcriptions`
Multipart form. Fields: `file` (audio binary), `model`, `language`, `prompt`, `response_format` (`json | text | srt | vtt | verbose_json`), `temperature`, `timestamp_granularities[]` (`word | segment`).

Response (`json` default): `{ "text": "string" }`. Verbose: includes `segments[]` with `start`, `end`, `text`, `tokens`, `avg_logprob`, `compression_ratio`, `no_speech_prob`.

### `POST /v1/audio/translations`
Same shape as transcriptions; output is English regardless of input language.

### `POST /v1/audio/speech`
Request:
```json
{
  "model":"string", "voice":"alloy|echo|fable|onyx|nova|shimmer|coral|ash|ballad|sage|verse|...",
  "input":"string", "response_format":"mp3|opus|aac|flac|wav|pcm",
  "speed":1.0, "instructions":"string"
}
```
Response: binary audio stream of the requested format. Streaming via `Transfer-Encoding: chunked`.

---

## Images

### `POST /v1/images/generations`
Request:
```json
{
  "model":"string", "prompt":"string",
  "n":1, "size":"auto|256x256|512x512|1024x1024|1024x1536|1536x1024|1792x1024|1024x1792",
  "quality":"auto|standard|hd|low|medium|high",
  "background":"auto|transparent|opaque",
  "moderation":"auto|low",
  "output_format":"png|jpeg|webp",
  "output_compression":0,
  "response_format":"url|b64_json",
  "style":"vivid|natural",
  "user":"string"
}
```
Response: `{ "created":0, "data":[ { "url"|"b64_json", "revised_prompt" } ] }`.

### `POST /v1/images/edits`
Multipart. `image` (PNG, ≤4MB, square for some models), optional `mask`, `prompt`, plus the generation params above.

### `POST /v1/images/variations`
Multipart. `image`, `model`, `n`, `size`, `response_format`.

---

## Files

### `POST /v1/files`
Multipart form. `file` (any binary), `purpose` (`assistants | batch | fine-tune | vision | user_data | evals`).

Response: `File` object — `{ id, object:"file", bytes, created_at, filename, purpose, status, expires_at, status_details }`.

### `GET /v1/files`
Query: `purpose`, `limit`, `order`, `after`. Returns paginated `File[]`.

### `GET /v1/files/{file_id}`
Single-file metadata.

### `DELETE /v1/files/{file_id}`
Delete an uploaded file. Returns `{ id, object:"file", deleted:true }`.

### `GET /v1/files/{file_id}/content`
Download the file body. `Content-Type` reflects original.

---

## Uploads

Multi-part upload protocol for files larger than the single-shot 512MB ceiling. Use when ingesting model weights, datasets, or large eval artifacts.

### `POST /v1/uploads`
`{ purpose, filename, bytes, mime_type }` → `Upload { id, status:"pending", expires_at }`.

### `POST /v1/uploads/{upload_id}/parts`
Multipart with `data` field; max 64MB/part, max 250 parts. Response: `UploadPart { id, upload_id, created_at }`.

### `POST /v1/uploads/{upload_id}/complete`
`{ part_ids: ["..."], md5: "..." }` → finalized `Upload` containing a `file` field referencing the assembled `File`.

### `POST /v1/uploads/{upload_id}/cancel`
Abort and free server-side state.

---

## Vector Stores

### `POST /v1/vector_stores`
`{ name, file_ids[], expires_after:{anchor:"last_active_at",days}, chunking_strategy:{type:"auto|static",static:{max_chunk_size_tokens,chunk_overlap_tokens}}, metadata }`. Response: `VectorStore`.

### `GET /v1/vector_stores`
Paginated `VectorStore[]`.

### `GET /v1/vector_stores/{vector_store_id}`
Single-store fetch.

### `POST /v1/vector_stores/{vector_store_id}`
Mutable fields: `name`, `expires_after`, `metadata`.

### `DELETE /v1/vector_stores/{vector_store_id}`
Delete.

`VectorStore` shape: `{ id, object:"vector_store", created_at, name, usage_bytes, file_counts:{ in_progress, completed, failed, cancelled, total }, status:"expired|in_progress|completed", expires_after, expires_at, last_active_at, metadata }`.

### Vector-store search
`POST /v1/vector_stores/{vector_store_id}/search`
`{ query, max_num_results, filters:{ … }, ranking_options:{ ranker:"auto|default-2024-11-15", score_threshold } }` → `{ object:"vector_store.search_results.page", search_query, data:[ { file_id, filename, score, attributes, content:[ { type:"text", text } ] } ], has_more, next_page }`.

---

## Vector Store Files

### `POST /v1/vector_stores/{vector_store_id}/files`
Attach an uploaded `File` to the store. `{ file_id, chunking_strategy, attributes }`. Response: `VectorStoreFile`.

### `GET /v1/vector_stores/{vector_store_id}/files`
List with filter `?filter=in_progress|completed|failed|cancelled`.

### `GET /v1/vector_stores/{vector_store_id}/files/{file_id}`
Single-file status + chunking details.

### `POST /v1/vector_stores/{vector_store_id}/files/{file_id}`
Update mutable `attributes`.

### `DELETE /v1/vector_stores/{vector_store_id}/files/{file_id}`
Detach (does NOT delete the underlying `File`).

### `GET /v1/vector_stores/{vector_store_id}/files/{file_id}/content`
Stream the parsed/chunked text content the store indexed.

---

## Vector Store File Batches

### `POST /v1/vector_stores/{vector_store_id}/file_batches`
`{ file_ids[], attributes, chunking_strategy }` → `VectorStoreFileBatch { id, status, file_counts, … }`.

### `GET /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}`
Status fetch.

### `POST /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel`
Cancel an in-progress batch.

### `GET /v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/files`
Paginated `VectorStoreFile[]` for the batch.

---

## Assistants

### `POST /v1/assistants`
Request:
```jsonc
{
  "model":"string",
  "name":"string","description":"string","instructions":"string",
  "tools":[ {"type":"code_interpreter"}, {"type":"file_search","file_search":{ … }},
            {"type":"function","function":{ … }} ],
  "tool_resources":{ "code_interpreter":{ "file_ids":[…] },
                     "file_search":{ "vector_store_ids":[…] } },
  "metadata":{ … }, "temperature":1.0, "top_p":1.0,
  "response_format":"auto | { type:'text|json_object|json_schema', … }",
  "reasoning_effort":"low|medium|high"
}
```

### `GET /v1/assistants` / `GET /v1/assistants/{id}` / `POST /v1/assistants/{id}` / `DELETE /v1/assistants/{id}`
Standard list / fetch / modify / delete.

---

## Threads

### `POST /v1/threads`
`{ messages[], tool_resources, metadata }` → `Thread`.

### `GET /v1/threads/{thread_id}` / `POST /v1/threads/{thread_id}` / `DELETE /v1/threads/{thread_id}`
Fetch / modify / delete.

---

## Messages

### `POST /v1/threads/{thread_id}/messages`
`{ role:"user|assistant", content:"string|ContentPart[]", attachments:[{file_id,tools:[…]}], metadata }` → `Message`.

### `GET /v1/threads/{thread_id}/messages` / `GET /v1/threads/{thread_id}/messages/{message_id}` / `POST …` / `DELETE …`
List / fetch / modify (metadata only) / delete.

---

## Runs

### `POST /v1/threads/{thread_id}/runs`
Trigger an assistant turn against a thread.
```jsonc
{
  "assistant_id":"string",
  "model":"string",                             // override
  "instructions":"string",                      // override
  "additional_instructions":"string",
  "additional_messages":[ Message ],
  "tools":[ Tool ],                             // override
  "metadata":{ … },
  "temperature":1.0, "top_p":1.0,
  "stream":false,
  "max_prompt_tokens":0, "max_completion_tokens":0,
  "truncation_strategy":{ "type":"auto|last_messages","last_messages":0 },
  "tool_choice":"auto|none|required|{ type:'function',function:{name} }",
  "parallel_tool_calls":true,
  "response_format":"auto | { … }",
  "reasoning_effort":"low|medium|high"
}
```
Response: `Run` (status: `queued | in_progress | requires_action | cancelling | cancelled | failed | completed | incomplete | expired`).

### `POST /v1/threads/runs`
Create-thread-and-run combined op. Body merges thread-create and run-create.

### `GET /v1/threads/{thread_id}/runs` / `GET …/{run_id}` / `POST …/{run_id}` (metadata)
Standard.

### `POST /v1/threads/{thread_id}/runs/{run_id}/cancel`
Cancel.

### `POST /v1/threads/{thread_id}/runs/{run_id}/submit_tool_outputs`
Reply to `requires_action.submit_tool_outputs`. `{ tool_outputs:[{ tool_call_id, output }], stream }`.

---

## Run Steps

### `GET /v1/threads/{thread_id}/runs/{run_id}/steps`
Paginated `RunStep[]`.

### `GET /v1/threads/{thread_id}/runs/{run_id}/steps/{step_id}`
Single step. `step_details` discriminated by `type`: `message_creation` or `tool_calls` (each tool call typed: `code_interpreter`, `file_search`, `function`).

---

## Batches

Asynchronous bulk request execution. Inputs/outputs are JSONL `File`s.

### `POST /v1/batches`
```json
{
  "input_file_id":"file_…",
  "endpoint":"/v1/chat/completions | /v1/embeddings | /v1/responses | /v1/completions",
  "completion_window":"24h",
  "metadata":{ … }
}
```
Response: `Batch { id, object:"batch", endpoint, errors, input_file_id, completion_window, status:"validating|failed|in_progress|finalizing|completed|expired|cancelling|cancelled", output_file_id, error_file_id, created_at, in_progress_at, expires_at, finalizing_at, completed_at, failed_at, expired_at, cancelling_at, cancelled_at, request_counts:{ total, completed, failed }, metadata }`.

### `GET /v1/batches/{batch_id}` / `GET /v1/batches`
Status / list.

### `POST /v1/batches/{batch_id}/cancel`
Cancel; status transitions through `cancelling` → `cancelled`.

'MiOS' cross-ref: `srv/mios/api/batch.requests.jsonl` is the canonical input format — one JSON object per line, each `{ custom_id, method, url, body }`.

---

## Fine-tuning

### `POST /v1/fine_tuning/jobs`
```jsonc
{
  "model":"string", "training_file":"file_…", "validation_file":"file_…",
  "method":{ "type":"supervised | dpo | reinforcement",
             "supervised":{ "hyperparameters":{ "n_epochs":"auto|int",
                "batch_size":"auto|int", "learning_rate_multiplier":"auto|number" } },
             "dpo":{ "hyperparameters":{ "beta":"auto|number", … } },
             "reinforcement":{ "hyperparameters":{ … }, "grader":{ … } } },
  "suffix":"string", "seed":0,
  "integrations":[ { "type":"wandb", "wandb":{ "project","name","entity","tags":[] } } ],
  "metadata":{ … }
}
```
Response: `FineTuningJob`.

### `GET /v1/fine_tuning/jobs` / `GET …/{id}`
List / fetch. Status: `validating_files | queued | running | succeeded | failed | cancelled`.

### `POST /v1/fine_tuning/jobs/{id}/cancel`
Cancel.

### `GET /v1/fine_tuning/jobs/{id}/events`
Paginated `FineTuningJobEvent[]` (`object:"fine_tuning.job.event"`).

### `GET /v1/fine_tuning/jobs/{id}/checkpoints`
Paginated `FineTuningJobCheckpoint[]` — references intermediate models that can be used as `model` in a chat-completions request.

### `POST /v1/fine_tuning/checkpoints/{permission_id}/permissions` (Admin)
Grant per-checkpoint sharing. Out of scope for single-tenant MiOS.

'MiOS' cross-ref: `var/lib/mios/training/sft.jsonl` (supervised) and `var/lib/mios/training/dpo.jsonl` (preference) follow the formats this endpoint expects.

---

## Moderations

### `POST /v1/moderations`
```json
{ "model":"omni-moderation-latest|text-moderation-latest", "input":"string | string[] | InputItem[]" }
```
Response: `{ id, model, results:[ { flagged, categories:{ … }, category_scores:{ … }, category_applied_input_types:{ … } } ] }`.

---

## Realtime

### `WS /v1/realtime?model=…`
Bidirectional WebSocket for low-latency speech-to-speech and text-to-speech sessions. Client sends/receives event-typed JSON envelopes; audio frames are base64 PCM16 over `input_audio_buffer.append`. Major event types:

- Client → server: `session.update`, `input_audio_buffer.{append,commit,clear}`, `conversation.item.{create,truncate,delete}`, `response.{create,cancel}`.
- Server → client: `session.{created,updated}`, `input_audio_buffer.{committed,cleared,speech_started,speech_stopped}`, `conversation.item.{created,input_audio_transcription.{completed,failed},truncated,deleted}`, `response.{created,done,output_item.{added,done},content_part.{added,done},text.{delta,done},audio_transcript.{delta,done},audio.{delta,done},function_call_arguments.{delta,done}}`, `rate_limits.updated`, `error`.

### `POST /v1/realtime/sessions`
Mint an ephemeral client token (`client_secret.value`) for browser-side WebRTC connections without exposing `MIOS_AI_API_KEY`. Body mirrors the `session.update` shape. Response includes `client_secret.expires_at`.

### `POST /v1/realtime/transcription_sessions`
Same pattern, scoped to transcription-only sessions.

---

## Admin / Organization

`/v1/organization/*` covers user/project/api-key administration, audit logs, costs, and usage. **'MiOS' Status: Unsupported** — single-tenant deployment; auth is enforced at the reverse-proxy layer. If multi-tenant becomes a goal, document the chosen subset in a follow-up `ADMIN.md`.

---

## Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `invalid_request_error` | 400 | Malformed body, unknown field, bad enum value. |
| `authentication_error` | 401 | Missing/invalid `Authorization` header. |
| `permission_error` | 403 | Token lacks scope; deployment policy block. |
| `not_found_error` | 404 | Unknown id (file, model, response, etc.). |
| `conflict_error` | 409 | Concurrent-modification conflict on a stateful object. |
| `unprocessable_entity_error` | 422 | Schema-valid but logically rejected. |
| `rate_limit_error` | 429 | TPM/RPM/quota exceeded. Retry with backoff. |
| `api_error` | 500 | Transient server fault. |
| `bad_gateway_error` | 502 | Upstream model unavailable. |
| `service_unavailable_error` | 503 | Capacity exhaustion. |
| `gateway_timeout_error` | 504 | Generation exceeded wall-clock budget. |

Streamed errors arrive as `event: error` SSE frames with the same envelope.

---

## Rate Limits

OpenAI advertises `x-ratelimit-{limit,remaining,reset}-{requests,tokens}` headers. LocalAI's behavior depends on configuration; 'MiOS' deployments SHOULD enforce limits at the reverse-proxy layer if multi-client. Until that's wired, treat headers as advisory.

---

## SDKs

The official OpenAI SDKs (`openai-python`, `openai-node`, `openai-go`, `openai-java`) all accept a `base_url` override. 'MiOS' clients SHOULD construct clients with:

```python
from openai import OpenAI, AsyncOpenAI
import os
client = OpenAI(base_url=os.environ["MIOS_AI_ENDPOINT"],
                api_key=os.environ.get("MIOS_AI_API_KEY", "no-auth"))
```

```javascript
import OpenAI from "openai";
const client = new OpenAI({
  baseURL: process.env.MIOS_AI_ENDPOINT,
  apiKey:  process.env.MIOS_AI_API_KEY ?? "no-auth"
});
```

```bash
export OPENAI_BASE_URL="$MIOS_AI_ENDPOINT"
export OPENAI_API_KEY="$MIOS_AI_API_KEY"
# every CLI tool that respects OPENAI_BASE_URL now points at MiOS.
```

---

## Cross-references

- Architectural Law 5 (UNIFIED-AI-REDIRECTS): [`CLAUDE.md`](CLAUDE.md), [`INDEX.md`](INDEX.md), [`ENGINEERING.md`](ENGINEERING.md).
- Endpoint binding: [`etc/containers/systemd/mios-ai.container`](etc/containers/systemd/mios-ai.container).
- Endpoint manifest (machine-readable): [`manifest.json`](manifest.json) (entries keyed by `endpoint:`).
- Batch input format: [`srv/mios/api/batch.requests.jsonl`](srv/mios/api/batch.requests.jsonl).
- Embedding output format: [`var/lib/mios/embeddings/chunks.jsonl`](var/lib/mios/embeddings/chunks.jsonl).
- Fine-tuning training data: [`var/lib/mios/training/sft.jsonl`](var/lib/mios/training/sft.jsonl), [`var/lib/mios/training/dpo.jsonl`](var/lib/mios/training/dpo.jsonl).
- Eval datasets: [`var/lib/mios/evals/dataset.jsonl`](var/lib/mios/evals/dataset.jsonl).
- Upstream spec source: <https://platform.openai.com/docs/api-reference>.

---

## Verification protocol (post-build)

To flip every endpoint's `'MiOS' Status` from `Unverified` → `Served | Proxied | Unsupported`, run from inside the deployed 'MiOS' instance:

```bash
# Required: instance must have curl + jq.
export E="$MIOS_AI_ENDPOINT" K="${MIOS_AI_API_KEY:-no-auth}"
H=(-H "Authorization: Bearer $K" -H "Content-Type: application/json")

# Probe each surface; record HTTP status into a manifest the matrix can consume.
{
  for path in models chat/completions completions responses embeddings \
              audio/speech images/generations files uploads vector_stores \
              assistants threads batches fine_tuning/jobs moderations \
              realtime/sessions; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "${H[@]}" \
                -X $( [[ "$path" == models ]] && echo GET || echo POST ) \
                ${path:+-d '{}'} \
                "$E/$path")
    printf '%-30s %s\n' "$path" "$code"
  done
} > /usr/lib/mios/logs/openai-api-verification.txt
```

Update the [Compatibility Matrix](#compatibility-matrix) from the resulting file. A `405` on a `GET`-not-`POST` endpoint also confirms the route exists; `404` confirms unsupported; `401` confirms route exists but auth is enforced.
