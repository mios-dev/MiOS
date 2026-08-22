<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-6 run-template CAPTURE + the T-225 replay source, extracted out of dag_exec so the two halves of one feature live together. Owns the structural plan-shape class (_run_template_class -- computable only AFTER planning), the fire-and-forget capture that now also records the TURN's intent key (the question you can ask BEFORE planning), and load_run_templates, the newest-first reader the planner's replay matcher consults. Every DB helper and the RUN_TEMPLATE_ENABLE flag arrive by one-way injection through configure(); this module NEVER imports server or dag_exec. dag_exec re-exports all three names so server.py's imports are unchanged.
AI-related: ./replay.py, ./dag_exec.py, ./planner.py, /usr/share/mios/postgres/schema-init.sql, ./test_mios_run_template.py
AI-functions: configure, _run_template_class, load_run_templates, _capture_run_template

<!-- mios-src:6f146cd2bcdf from usr/lib/mios/agent-pipe/mios_pipe/routing/run_template.py:1-3 -->

