<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib unit test for the extracted A2A peer-client consumer half (mios_a2a_client). Injects lightweight stubs via configure() -- a synthetic 3-path layered peer registry (vendor/etc/user JSON written to tmp files), a fake self-peer-url predicate, an asyncio.Lock, a by-reference _A2A_PEERS/_A2A_PEER_SKILLS/_AGENT_REGISTRY, a stub _A2A_REPUTATION recorder, a fake async HTTP client + card-fetch helper, and a worker-cache invalidator spy -- then asserts: _a2a_load_peers reads + id-dedupes + self-loop-excludes the layered registry; _a2a_probe_peer indexes a card's skills + registers the synthetic a2a:<pid> DAG agent + fires the cache invalidator; _a2a_send_message_to_peer builds the JSON-RPC message/send body shape (kind/method/params.message.parts text) against the chosen peer + records the outcome; _a2a_extract_text pulls assistant text from an A2A Task envelope (artifacts then status.message). No network, no DB, no server import.
AI-related: ./mios_a2a_client.py, ./server.py

<!-- mios-src:6f3b81196ac7 from usr/lib/mios/agent-pipe/test_mios_a2a_client.py:1-2 -->

