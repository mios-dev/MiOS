<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Systemd unit defining the agent-pipe FastAPI service which acts as a router, refiner, and critic for the Hermes gateway, routing inference requests to the llama.cpp light lane (mios-llm-light); the lane port is the single SSOT key [ports].llm_light (MIOS_PORT_LLM_LIGHT), composed in server.py via _LIGHT_BASE.
AI-related: /usr/lib/mios/agent-pipe/server.py, /etc/mios/install.env, /etc/mios/agent-pipe.env, /usr/lib/mios/agents/.venv/bin/python3, mios-pgvector, mios-passport-provision, mios-ai, mios-hermes, mios-env

<!-- mios-src:a405329f8ba7 from usr/lib/systemd/system/mios-agent-pipe.service:1-2 -->

