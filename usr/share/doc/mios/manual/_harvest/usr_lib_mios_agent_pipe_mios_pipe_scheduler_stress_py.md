<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Stress test harness for the...

!/usr/bin/env python3
AI-hint: Stress test harness for the agent-pipe that validates the /v1/chat/completions path under load-aware concurrency, ensuring stability of the llama.cpp/pgvector stack by monitoring latency and error rates.
AI-related: mios-stresstest, mios-agent, localhost `agent_pipe` port
AI-functions: percentile, aggregate, should_throttle, ramp_concurrency, build_scenarios, verdict, by_kind, _poll_load, _one, run, main

<!-- mios-src:3df9c555acf9 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/stress.py:1-4 -->

