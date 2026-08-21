<!-- AI-hint: Manual pages distilled from the source comments of support, sanitized, each passage anchored to the comment it came from. -->

# support

### AI-facing doc genericity audit. Walks every doc that gets...

AI-facing doc genericity audit.

Walks every doc that gets loaded into an LLM's context window and
flags content bound to a single deployment / operator / project
state. Covers:

  * /usr/share/mios/hermes/skills/*/SKILL.md   (per-skill guidance)
  * /usr/share/mios/ai/*.md                    (system + SOUL docs)

Findings:
  * conversational tone in body prose ("operator-flagged YYYY-MM-DD")
  * hardcoded paths bound to a single user (/mnt/c/Users/<name>,
    /var/home/<name>); operator name is an SSOT variable
    ([identity].username -> MIOS_USER)
  * hardcoded hostnames (MiOS-955, mios-ec377, ...)
  * project-internal phase jargon in YAML frontmatter description
    (descriptions get surfaced to LLM context; jargon noise wastes
    tokens + leaks implementation detail)

These are LLM-guidance docs, so prose in the body is EXPECTED.
The check is for guidance bound to a specific operator / machine
/ project state vs. guidance portable to any MiOS deployment.

Exits 0 (clean) / 1 (findings).

<!-- mios-src:65a0b7c0f706 from automation/support/audit-hermes-skills.py:5-29 -->

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

### In-place patch of hermes_cli/web_server.py so the /api/pty...

In-place patch of hermes_cli/web_server.py so the /api/pty endpoint
honors HERMES_PTY_SHELL env var.

Upstream hermes-agent hardcodes `_resolve_chat_argv` to spawn
`hermes --tui` (the Node-built TUI chat). MiOS-DEV wants a plain bash
shell in the dashboard's /chat tab (operator directive
"do we have a react window for terminal(s)?" -> chose "plain bash").
Setting `HERMES_PTY_SHELL=/bin/bash` (or any shell binary) replaces
the hardcoded TUI spawn with the requested shell.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: leaves the upstream fallback when HERMES_PTY_SHELL is unset.

Usage:
    hermes-dashboard-shell-patch.py /path/to/hermes_cli/web_server.py

<!-- mios-src:89f7c843cfc6 from automation/support/hermes-dashboard-shell-patch.py:4-19 -->

### Strip externally-hosted asset URLs from the built Hermes...

Strip externally-hosted asset URLs from the built Hermes dashboard.

Runs after `npm run build` against `<repo>/hermes_cli/web_dist`. The
upstream React bundle ships five OPTIONAL theme stylesheets that
reference `fonts.googleapis.com` for typography (Inter, JetBrains Mono,
Spectral, IBM Plex, Share Tech Mono, Fraunces, DM Mono). The DEFAULT
theme uses the @nous-research/ui bundled woff2 fonts (in `web/public/
fonts/`) and works offline. Patching the optional-theme URLs to an
inert `data:text/css,` URI keeps the theme switcher's UI alive but
turns the non-default themes into a no-op rather than a Google Fonts
fetch.

Architectural Law 7 (OFFLINE-FIRST): the runtime must never reach out
to an external service. Build-time deps (npm install from registry)
happen once during image build; runtime is offline.

Usage:
    hermes-dashboard-strip-externals.py /path/to/hermes_cli/web_dist

<!-- mios-src:f28ea281a9e5 from automation/support/hermes-dashboard-strip-externals.py:4-22 -->

### In-place patch of gateway/platforms/discord.py to add...

In-place patch of gateway/platforms/discord.py to add progressive
"thinking" reactions on the operator's Discord message during agent
processing.

Operator directive "also add more reactions to the
MiOS-Hermes Discord bot--Should be using more discord reactions to
show it's thinking!"

Upstream hermes-agent's Discord gateway emits exactly two reactions:
  on_processing_start    -> 👀 (single "looking" emoji)
  on_processing_complete -> ✅ / ❌

That gives the operator no visibility into what stage the agent is in
mid-run. This patch enriches the reaction surface with a progressive
sequence:
    📡 (received)          immediate
    🧠 (thinking)          after 2s if still processing
    🛠️ (using tools)       after 8s if still processing
    ⏳ (still working)      after 20s if still processing
    ✅ / ❌ (final)         on completion (and all phase reactions
                            are cleared first so the final outcome
                            stands alone)

A background asyncio.create_task() drives the progression so the
gateway's normal flow isn't blocked. The task is stashed on the
gateway instance keyed by Discord message id so concurrent
in-flight messages each get their own task that the matching
on_processing_complete can cancel.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: if Discord's add_reaction / remove_reaction fail (rate limit,
missing perm), each call already swallows the exception in the
existing _add_reaction / _remove_reaction helpers, so the progression
degrades silently.

Usage:
    hermes-discord-reactions-patch.py /path/to/discord.py

<!-- mios-src:72d662d789d6 from automation/support/hermes-discord-reactions-patch.py:4-41 -->

### Locate the contiguous on_processing_start +...

Locate the contiguous on_processing_start + on_processing_complete
    method pair by line-scanning. Returns (start_idx, end_idx) as half-
    open slice indices into `lines`. (-1, -1) if not found.

    Line-by-line scanning avoids the catastrophic backtracking that a
    nested-quantifier regex hits on this 5500-line file (the upstream
    discord.py has dozens of `async def` at 4-space indent, and the
    regex explores every alignment).

<!-- mios-src:e413ead8f7a4 from automation/support/hermes-discord-reactions-patch.py:105-113 -->
