<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### web search (local SearXNG-backed; the web_search verb...

--- web search (local SearXNG-backed; the web_search verb backend) ---
Added 2026-05-21: the agent fabricated a weather/event report because no
web tool existed -- mios-web-search closes that gap. MUST be on PATH so
the agent-pipe dispatch + the daemon-agent supplement resolve it.

<!-- mios-src:178cea62b14d from usr/lib/tmpfiles.d/mios-shim-links.conf:59-62 -->

### mios-crawl

mios-crawl: JS-rendered page -> LLM-ready markdown (the `crawl` verb
backend; POSTs to the local mios-crawl4ai.service loopback :11235, which
drives the existing Chrome over CDP with a Camoufox stealth fallback).
Distinct from web_extract (lightweight HTTP text fetch): crawl handles
JS-rendered pages + returns structured markdown/links. MUST be on PATH so
the agent-pipe dispatch resolves it (else `crawl` exits 127, same trap that
bit web_extract). Added 2026-05-24; reworked to the venv service same day.

<!-- mios-src:61d102f7fd30 from usr/lib/tmpfiles.d/mios-shim-links.conf:69-75 -->

### mios-firecrawl

mios-firecrawl: SCRAPE a page -> clean markdown via the self-hosted Firecrawl
API (the `web_scrape` verb backend; POSTs to the firecrawl-api member of the
mios-webtools pod, 127.0.0.1:3002). A SECOND fetch engine beside crawl --
Firecrawl renders news/article indexes cleanly (verified: a news-index scrape
returned the day's REAL dated headlines where web_search returned junk). MUST
be on PATH so the dispatch resolves it (else web_scrape exits 127, the same
trap that bit web_extract + crawl). Added 2026-05-25 (operator: ALL web tools
GLOBALLY accessible to every agent).

<!-- mios-src:3767a369dfa8 from usr/lib/tmpfiles.d/mios-shim-links.conf:78-85 -->

### mios-verify-launch

mios-verify-launch: SYNCHRONOUS launch success-check (the `verify_launch` verb
backend; GETs the always-on mios-daemon-agent :8644 /verify_launch route).
Closes the 4A loop -- after an agent fires open_app it calls verify_launch to
CONFIRM the app really opened (read-only window/process probe + the daemon's
recorded false-success history) instead of blind-claiming. MUST be on PATH so
the dispatch resolves it (else verify_launch exits 127). Added 2026-05-25
(operator 4A: the iGPU daemon runs the success-check; agents read the signal).

<!-- mios-src:e90a087aedf1 from usr/lib/tmpfiles.d/mios-shim-links.conf:88-94 -->

### mios-crawl4ai-setup

mios-crawl4ai-setup: one-shot installer for the crawl-engine venv (operator
runs it; creates /usr/lib/mios/crawl4ai/.venv + crawl4ai core + camoufox).
On PATH for operator convenience.

<!-- mios-src:de442dd9e64c from usr/lib/tmpfiles.d/mios-shim-links.conf:97-99 -->

### mios-computer-use-server

mios-computer-use-server: the dual MCP+A2A + HTTP-executor server a desktop
node runs so the central agent-pipe CONSUMES it (mcp.json + a2a-peers.json
overlays). On PATH for the systemd unit + operator launch.

<!-- mios-src:c6f5061930a4 from usr/lib/tmpfiles.d/mios-shim-links.conf:140-142 -->

### app-launch chain (operator 2026-06-06: the launcher broker...

--- app-launch chain (operator 2026-06-06: the launcher broker got
"mios-launch: command not found" because the launch chain wasn't shimmed; the
Environment=PATH in the --user unit didn't reliably reach the process, so the
broker only had /usr/local/{s,}bin on PATH -- shim the chain there durably so
open_app -> mios-launch -> mios-gui/flatpak-launch resolves after any rebuild). ---

<!-- mios-src:94c5c222fe72 from usr/lib/tmpfiles.d/mios-shim-links.conf:160-164 -->

### Cached FS map + RAG knowledge readers (directory_lookup /...

Cached FS map + RAG knowledge readers (directory_lookup / knowledge_search
verb backends). Were unshimmed -> both verbs exited 127 when an agent called
them. Added 2026-05-23 (toolset first-time-use audit).

<!-- mios-src:5b469d849d8b from usr/lib/tmpfiles.d/mios-shim-links.conf:231-233 -->

### mios-a2a-delegate

mios-a2a-delegate: mid-run agent-to-agent delegation over A2A (the
a2a_delegate verb backend; POSTs to the agent-pipe's /v1/a2a/dispatch
which JSON-RPCs message/send into a registered peer's /a2a). Closes the
P2.2 swarm gap -- council/swarm members can now hand sub-tasks to peers
mid-tool-loop instead of only fanning out at the orchestrator level.

<!-- mios-src:0f0302faecaa from usr/lib/tmpfiles.d/mios-shim-links.conf:240-244 -->

### mios-os-control

mios-os-control: the SSOT OS-control surface (schema/verbs/recipes/skills/
doctor) that ANY llm consumes to learn the tool surface. Was unshimmed ->
"command not found" for agents + operators. Added 2026-05-23.

<!-- mios-src:24aa17ba085b from usr/lib/tmpfiles.d/mios-shim-links.conf:298-300 -->

### mios-sysview

mios-sysview: typed system-inspection (logs/proc/containers/restart) --
the no-hardcode backend the agent-pipe verbs delegate to (replaces inline
journalctl/ps/podman literals). Added 2026-05-21.

<!-- mios-src:4d05f2dea6a7 from usr/lib/tmpfiles.d/mios-shim-links.conf:303-305 -->

### mios-sys-env

mios-sys-env: live env/app probe persisted to the shared pgvector sys_env
cache (the sys_env + sys_env_refresh verbs + the refresh timer). MUST be on
PATH so the agent-pipe broker dispatch resolves it. Added 2026-05-23.

<!-- mios-src:82f0fe835998 from usr/lib/tmpfiles.d/mios-shim-links.conf:308-310 -->

### fine-tune subsystem (operator CLI; NOT agent verbs)...

--- fine-tune subsystem (operator CLI; NOT agent verbs) ---------
mios-finetune-dataset: build the distilled SFT corpus from the live catalog.
mios-finetune: hardware-agnostic LoRA/SFT -> GGUF adapter. On PATH for
the operator; deliberately NOT in any verb catalog (no chat turn can train).

<!-- mios-src:193d71b38514 from usr/lib/tmpfiles.d/mios-shim-links.conf:317-320 -->

### maintenance

--- maintenance: operator-invoked day-0 reset ---
mios-day0-reset: clear runtime AI state (chats/tool_calls/events/scratchpads
+ caches + OWUI history) back to a day-0 starting point. KEEPS configs,
code, agent definitions, passport keys, person/skill/app inventories. NOT
an agent verb (operator runs it; mass deletion). On PATH for convenience.

<!-- mios-src:8d8a1fff0424 from usr/lib/tmpfiles.d/mios-shim-links.conf:327-331 -->

### mios-stresstest

mios-stresstest: end-to-end direct-chat stress test of the agent-pipe (T20).
Operator/dev tool (bounded, load-aware, completes every turn). On PATH for the
operator; NOT an agent verb.

<!-- mios-src:5c46850fb3e3 from usr/lib/tmpfiles.d/mios-shim-links.conf:334-336 -->
