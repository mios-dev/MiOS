import sys, collections
sys.path.insert(0, "/usr/lib/mios/agent-pipe")
import server

tiers = collections.Counter(v.get("tier", "common") for v in server._VERB_CATALOG.values())
print(f"tier distribution: {dict(tiers)}")
print(f"visible to planner (core+common): {tiers['core'] + tiers['common']}")
print(f"hidden (rare): {tiers['rare']}")
print()
print("= core verbs (always-loaded once progressive disclosure ships) =")
for n, v in server._VERB_CATALOG.items():
    if v.get("tier") == "core":
        print(f"  {n:24s} -- {v['desc'][:70]}")
