<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Idempotent patch

Idempotent patch: give Hermes' BACKGROUND REVIEW the full global tool
surface ("make sure MiOS-Hermes can use all global
tools!! ... and all Global MiOS tools for Hermes too").

Upstream `agent/background_review.py` runs the post-turn self-improvement
pass under a thread-local tool whitelist built from ONLY the ["memory",
"skills"] toolsets -- everything else is denied at runtime. That made the
review agent's `patch` call fail ("Background review denied non-whitelisted
tool: patch. Only memory/skill tools are allowed."), so when its skill_manage
edit missed it had no working file-edit fallback, looped on a malformed
recreate, and burned the tool-turn budget ("agent may appear stuck").

This patch UNIONS the parent agent's full tool surface (`agent.valid_tool_names`
-- the same global tools the main loop has, MiOS verbs included) into the
review whitelist, so the background pass is no longer denied any tool. It also
softens the now-false "other tools will be denied" instruction. Memory/skill
tools remain first-class via the existing prompt; this only REMOVES the cap.

Idempotent: re-runs are no-ops once the marker is present (survives image
rebuilds; re-applied by automation/72-hermes-agent.sh over each site-packages).
Run: python3 hermes-background-review-tools-patch.py <path/to/background_review.py>

<!-- mios-src:195f18162af7 from automation/support/hermes-background-review-tools-patch.py:4-25 -->
