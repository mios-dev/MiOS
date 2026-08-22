<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A5 priority token-budget context packer for the agent-pipe. Given a list of candidate context items each carrying a priority + text, and a token budget, pack() greedily keeps the HIGHEST-priority items that fit the budget (measured via mios_tokenize) and DROPS the lowest-priority overflow, returning the kept items in their ORIGINAL order plus a packing report. Lets a hop assemble "as much of the most important context as fits" instead of a blind char slice. Pure stdlib; server.py decides what the items + budget are.
AI-related: ./mios_tokenize.py, ./server.py, ./mios_compact.py, ./test_mios_ctxpack.py
AI-functions: pack, class PackResult

<!-- mios-src:01ec8603e20e from usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py:1-3 -->

