<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A4 KV-cache file garbage-collection PLANNER. Pure-stdlib decision core for reclaiming the on-disk KV slot-save files the agent-pipe writes for conversation paging + WS-8 KV-forks (mios-kv-*.bin / fork children) under the llama.cpp --slot-save-path. plan_gc() decides which files to evict by TTL (age) THEN a total-size cap (oldest-first), never touching protected/active-slot files -- so an unbounded fork fan-out can't fill the disk. server.py owns the actual deletion (when the slots dir is FS-accessible) + the background loop; the systemd-tmpfiles age-out is the OS-level backstop. This module is pure (no fs/network) so it unit-tests in isolation.
AI-related: ./mios_kvfork.py, ./server.py, /usr/lib/tmpfiles.d/, /usr/share/mios/mios.toml, ./test_mios_kvgc.py
AI-functions: plan_gc, class GcPlan

<!-- mios-src:712d9a34756a from usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py:1-3 -->

