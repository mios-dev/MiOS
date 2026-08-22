<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for mios_http_caps -- the advertised-surface / capability route LOGIC extracted from server.py (refactor R-CAPS). Stubs every injected dep via configure() (no network / no DB) and asserts the moved *_logic functions still produce the byte-shape the @app thin wrappers used to: the /v1/verbs MCP projection (inputSchema + annotations), the /v1/verbs/openai-tools + /v1/tools projections, the /v1/capabilities manifest envelope, the /v1/peers gossip digest, the /v1/resources MCP Resource list + the moved projectors, the /v1/cost ledger, the /v1/trace reads, /v1/models single-model advert, the /v1/embeddings proxy passthrough (stubbed backend), and /dci/schema. Run: python test_mios_http_caps.py
AI-related: ./mios_http_caps.py, ./server.py
AI-functions: main

<!-- mios-src:d6c16c44bc66 from usr/lib/mios/agent-pipe/test_mios_http_caps.py:1-3 -->

