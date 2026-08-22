<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A15 pluggable MemoryProvider seam for the agent-pipe. Wraps the pgvector recall/store path behind a small MemoryProvider interface (retrieve/add) so the agent's long-term memory backend is swappable (a different vector store, a remote memory service, a test fake) without touching the recall call sites. PgVectorMemoryProvider is the default, delegating verbatim to the mios_pg client; get_memory_provider(name, backend) is a fail-CLOSED factory (raises ValueError on an unknown name). server.py owns the wiring (resolve [pgvector].memory_provider, build the module-global _MEMORY, route _recall_agent_memory/_recall_knowledge_pg through it); this module owns only the seam.
AI-related: ./mios_pg.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_memory.py
AI-functions: retrieve, add, get_memory_provider, register_provider, class MemoryProvider, class PgVectorMemoryProvider

<!-- mios-src:7da57cfc3ace from usr/lib/mios/agent-pipe/mios_pipe/memory/memory.py:1-3 -->

