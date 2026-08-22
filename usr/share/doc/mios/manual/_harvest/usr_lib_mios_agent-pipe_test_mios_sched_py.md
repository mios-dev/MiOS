<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Standalone unit test for mios_sched.PriorityGate (WS-1)....

Standalone unit test for mios_sched.PriorityGate (WS-1).

Pure stdlib + the sibling module only -- no server.py import, so it runs on any
Python 3.10+ without the agent-pipe runtime deps (httpx/fastapi/...). Mirrors the
_execute_dag_saturated standalone-test pattern: a mock-free asyncio harness with
explicit asserts and a PASS/FAIL summary; exit code != 0 on any failure.

Run:  python test_mios_sched.py

<!-- mios-src:2bdaac1e6456 from usr/lib/mios/agent-pipe/test_mios_sched.py:3-11 -->

### Under contention, a freed slot goes to a tenant UNDER its...

Under contention, a freed slot goes to a tenant UNDER its cap even over a
    HIGHER-priority waiter whose tenant is AT its cap -- one tenant can't starve another.
    Tenant A holds a slot for the whole test (A pinned AT cap); B1 holds its slot so the
    fairness moment (B1 served, A2 still queued) is observable, then A2 is served
    (degrade-open: it becomes the sole waiter).

<!-- mios-src:2372a57da968 from usr/lib/mios/agent-pipe/test_mios_sched.py:232-236 -->
