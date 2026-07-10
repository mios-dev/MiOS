<!-- AI-hint: Execution plan for the MiOS Awareness+Grounding initiative (2026-06-15), synthesized by the mios-grounding-aware-plan ultracode workflow (6 agents, 624k tok). Covers WS-A env-awareness, WS-B root-MD grounding, WS-C Hermes-to-root+MD symlinks, WS-D app-type aliases, WS-E OpenAI-API conformance. File-grounded, P0-P4, owner-tagged. -->

# MiOS Awareness + Grounding Initiative — execution plan (2026-06-15)

## Situation
Five investigations expose one failure mode: MiOS agents are well-architected but **structurally blind to their own identity and environment**. The agent never learns its real OS (the SOUL points at `mios-system-status`, which has **no OS field**, so the model answers "Windows 10" from its base-model prior — there is **no hardcoded "Windows 10" anywhere**; it fills a vacuum). The root `/MiOS.md` contract is truncated on slow lanes and bypassed by the Zen path. The root MD files exist today only via the Phase-1 git clone — a clean OCI image has none. The launch system has one global OS-preference and a flat alias map with no per-type policy, so the operator's real Windows browser (Zen) is unreachable. The OpenAI client-tools passthrough is shape-conformant but drops `tool_choice`/`parallel_tool_calls` and relays backend tool-call `id`s unguarded. All fixable without violating no-injection / no-hardcode / SSOT-in-mios.toml.

## WS-A — Environment-awareness (agent never learns its real OS)  **[P0]**
**Finding:** `mios-system-status` payload (`usr/libexec/mios/mios-system-status:246-255`) has no `os/kernel/distro/is_wsl/windows_host` field, yet `hermes-soul.md:69`+rule10 say host facts come from it *only*. The OS-bearing `mios-env-probe` is reachable only via `sys_env` whose desc never mentions OS/WSL/Windows. The `pre_llm_call` init-hook is dead (correctly, per no-injection). `owui/.../mios-agent.md:72` still falsely claims env is "auto-injected on first turn" (suppresses the tool call).
**Steps (Claude-doable):**
1. **(PRIMARY)** `mios-system-status` — add `_probe_os()` → `{distro, kernel, is_wsl, wsl_distro, windows_host (Win32_OperatingSystem.Caption+Version via guarded `mios-windows ps`, degrade-open null)}`; add `"os": _probe_os()` to payload.
2. `mios.toml` — OS/WSL/Windows wording into `[verbs.system_status].desc`, `[verbs.sys_env].desc`+`examples`, `[routing.domains.system].desc`.
3. `hermes-soul.md` (L69+rule10) + `ai/system.md` + `/MiOS.md` — "verify the dual identity, never assume; never state the OS from training data."
4. `owui/.../mios-agent.md` (L72,82-83) — delete the false "auto-injected" claim → "call `system_status`/`sys_env`."
5. `server.py` `_CLIENT_TOOLS_IDENTITY` — "For host/OS questions call `system_status`; never assume the OS."
6. (opt) probe emits `windows_host: null`+reason on failure. 7. delete dead `mios-hermes-init-hook`.
**MVP = 1+2+3+4.**

## WS-B — Root-MD grounding (contract truncated/bypassed)  **[P1]**
**Finding:** `_load_agent_contract()` (`server.py:5711-5744`) loads `/MiOS.md` once at import. **Live bug:** streaming council secondaries get `_trim_sys_prefix` (`server.py:23307`) capping every system block to `SLOW_LANE_BLOCK_CHARS=1500` (`server.py:438`) on slow lanes → contract truncated to ~25%; non-stream path doesn't trim (inconsistent grounding). **Zen drift:** `_client_tools_inject_identity` (`server.py:19829`) injects a hardcoded string, not `_agent_contract()`; relay fallback injects nothing.
**Steps (Claude-doable):** (B) pin the contract block (`_mios_pin`) so `_trim_sys_prefix` skips it. (C) Zen path uses `_agent_contract()`+addendum (coordinate w/ WS-A#5, WS-E). (D) add `_lead_system_blocks()` chokepoint. (A,opt) layer `ai/system.md`+`INDEX.md` as a trimmable block. (F,opt) mtime-reload `/MiOS.md`. Leave `/AGENTS.md`,`/CLAUDE.md` as build-time stubs (by design). Refine/polish stay contract-light (defensible).

## WS-C — Hermes-to-root + MD symlinks (root MDs absent in sealed image)  **[P1 / operator-decision]**
**Finding:** `Containerfile` copies only `automation/ usr/ etc/ VERSION config/artifacts/ tools/` — **NOT the root MDs** (`/MiOS.md`,`/AGENTS.md`,`/CLAUDE.md`,…). On a clean OCI image they don't exist → contract degrades to `""`. Literal `HOME=/` is **rejected** (read-only composefs `/usr`; Hermes writes config/SOUL → would fail; FHS/ProtectSystem). Physical install stays FHS: `/usr/lib/mios/agents` + `HERMES_HOME=/var/lib/mios/hermes`.
**Steps:** (1) add canonical MD copies under `usr/share/mios/ai/` (rides `COPY usr/`). (2) get root MDs into the image — **Option 1A bake real files via Containerfile COPY+install (recommended; safe on git-worktree AND image-only)** vs 1B `L+` tmpfiles symlinks (image-only — an `L+` over `/MiOS.md` would destroy a git worktree). (3) Hermes-asset discovery aliases via `mios-ai-links.conf` (`/usr/local/bin/hermes`, link vendor SSOT only — never `/var` firstboot targets). (4) do NOT move the venv. (5) reconcile dead `/etc/mios/hermes/config.yaml` seed. (6) `just lint` + restorecon.

## WS-D — App-type alias system (per-type OS-pref; Zen reachable)  **[P2]**
**Finding:** one global OS-pref (`[os_control].launch_category_priority`) + flat `[mios-find.aliases]` with no type metadata. **Zen invisible:** registers as `FirefoxURL` URL-protocol handler under `HKCU\...\zen.exe`, not in Get-StartApps/no .lnk → `mios-find "zen"` fails / mis-matches a garbage UWP.
**Steps (Claude-doable):** (1) `mios.toml` new `[[desktop.app_types]]` (type, os_pref ∈ linux-first|windows|both, default, windows_default, desc) — browser/editor/files/terminal/media=linux-first, games=windows, settings/system=both; browser.windows_default=zen; add `os`+`win_handler` keys to `[[desktop.apps]]` + a Zen row (`win_handler="url-protocol:<live ProgId>"`). (2) new `mios-app-type` resolver shim. (3) new `mios-app-default` switch verb (writes `~/.config/mios/mios.toml`). (4) `mios-open-url`/`mios-launch`/`mios-find` delegate to it. (5) `mios-apps` generative `windows-browser` scan (UserChoice→ProgId→command) + `mios-windows` `_url_protocol_resolve`. (6) `mios_verbs.py` optional `os` param + skill note. (7) configurator HTML round-trip. **Additive/back-compat.**

## WS-E — OpenAI-API conformance (client-tools passthrough)  **[P2-P4]**
**Finding:** structurally conformant (correct tool_calls shape, tool_call_id adjacency, finish_reason, JSON args, name-based routing, identity prepended). Gaps: **(#2)** backend `id` relayed verbatim → `id:null` → client follow-up 400 (synthesize `call_{chat_id}_{index}` when missing). **(#4)** `tool_choice` dropped (forward it). **(#3)** `parallel_tool_calls` not forwarded. **(#1)** keep `_client_tools_sse` the single re-synthesis point. **(#7)** do NOT migrate to Responses API — Chat Completions is the correct interop contract.

## Operator decisions (recommended default in **bold**)
- **WS-C deploy model:** image-only vs git-worktree-at-`/`? → **bake real root MDs (1A)** (safe on both); symlink only non-colliding Hermes aliases.
- **WS-C "move Hermes to root":** literal vs convention? → **the convention** (FHS install + root-anchored discovery symlinks); literal `HOME=/` rejected.
- **WS-B fold `INDEX.md`/`system.md` into runtime contract?** → **yes, as a separate trimmable block**; keep `/AGENTS.md`/`/CLAUDE.md` as stubs.
- **WS-D per-type os_pref:** → **games=windows, settings/system=both, else linux-first; browser default Epiphany + windows_default=zen** (flip generic→Zen only on `app_default set browser zen`).
- **WS-D Zen ProgId:** → **read live from `HKCU\...\UrlAssociations\https\UserChoice`, never bake `FirefoxURL`.**
- **Delete dead `mios-hermes-init-hook` + reconcile `/etc/mios/hermes/config.yaml` seed?** → **delete the hook; flag the config seed.**
- **uid drift in `hermes-agent.service`** → **out of scope; track separately; don't touch ownership here.**

## Recommended execution order
1. **WS-A 1+2+3+4** (P0) — headline OS-blindness; smallest, highest-impact. ← **starting now**
2. **WS-B (B slow-lane pin + C Zen)** (P1) jointly with **WS-A#5** + **WS-E #2/#4** (same `_client_tools_*` funcs).
3. **WS-C root-MD-into-image** (P1, after deploy-model decision).
4. **WS-E #2+#4** (P2) folded into the Zen pass.
5. **WS-D** (P2) — schema + 2 shims + consumers + Zen discovery (largest surface, last).
6. **WS-B A/D/F + WS-C aliases/cleanup + WS-E #3/#1/#5 + dead-code deletion** (P3-P4) cleanup pass.

## Risks
git-worktree `.git==/` symlink collision (bake, don't `L+`, over tracked MDs) · `L+` clobbers operator edits each boot (keep overrides in `/etc`+`~/.config`) · early-boot `/var` dangling links + SELinux contexts (`just lint`) · Windows-probe degrades when interop/broker down (emit `windows_host:null`+reason, don't fabricate) · slow-lane pin must apply ONLY to the identity block (not research block) or latency regresses · WS-D must read Zen ProgId live · VM `/usr` is a copy → every change is source-only, needs operator deploy+restart+verify, watch for runaway after restart.
