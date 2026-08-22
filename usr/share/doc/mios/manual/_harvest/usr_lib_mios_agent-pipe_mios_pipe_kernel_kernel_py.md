<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_kernel -- the MiOS agent-pipe Kernel facade...

mios_kernel -- the MiOS agent-pipe Kernel facade (WS-A11/WS-3, Stage 1b).

A thin composition that gives the decomposed agent-pipe ONE object holding the
Router (decide), the Dispatcher (run), and the five AIOS manager seams. The
managers + dispatcher are INJECTED by server.py (concrete adapters over the
existing scheduler/memory/context/tool/access code paths) so this module imports
NOTHING from server.py and is fully testable with fakes. Stage 2 builds the
KERNEL once and rewires chat_completions to `KERNEL.handle(refined, ...)`,
replacing the inline intent cascade.

Contract:
    decision = kernel.router.route(refined)        # pure (mios_router)
    result   = await kernel.dispatcher.run(decision, refined=refined, **ctx)
The Dispatcher is duck-typed: any object exposing `async run(decision, **ctx)`.

<!-- mios-src:719fdeb5222b from usr/lib/mios/agent-pipe/mios_pipe/kernel/kernel.py:3-17 -->
