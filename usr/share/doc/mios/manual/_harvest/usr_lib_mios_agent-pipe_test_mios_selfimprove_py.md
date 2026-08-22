<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_selfimprove (#64...

Standalone unit test for mios_selfimprove (#64 self-improvement analyzer).

Pure stdlib + the sibling module only -- no server.py / DB. Proves the analyzer
surfaces the right findings from outcome records and does not over-react to thin
samples.

Run:  python test_mios_selfimprove.py

<!-- mios-src:585ec8342721 from usr/lib/mios/agent-pipe/test_mios_selfimprove.py:3-10 -->
