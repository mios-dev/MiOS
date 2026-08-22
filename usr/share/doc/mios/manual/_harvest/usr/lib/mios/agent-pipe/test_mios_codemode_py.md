<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_codemode (WS-2 Code Mode pure...

Standalone unit test for mios_codemode (WS-2 Code Mode pure helpers).

Pure stdlib + the sibling module only -- no server.py / podman / DB import, so it
runs on any Python 3.10+ without the agent-pipe runtime deps. Mirrors the
test_mios_sched / test_mios_evict pattern: explicit asserts + a PASS/FAIL summary;
exit code != 0 on any failure.

Run:  python test_mios_codemode.py

<!-- mios-src:fe6a7cb70ecf from usr/lib/mios/agent-pipe/test_mios_codemode.py:3-11 -->
