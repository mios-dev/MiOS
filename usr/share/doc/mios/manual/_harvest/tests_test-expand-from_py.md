<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Smoke-test the skill engine's expand_from semantics. Calls...

Smoke-test the skill engine's expand_from semantics.

Calls execute_skill('open-url-fallback-chain', ...) with 3 browsers
and a deliberately-bad URL; verifies the engine fanned 1 step into
3 (one per browser) by inspecting the returned `steps` list length.

Exits 0 on PASS, 1 on FAIL.

<!-- mios-src:2cc352692064 from tests/test-expand-from.py:3-10 -->
