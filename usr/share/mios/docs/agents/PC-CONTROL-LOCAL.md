# Local-only PC Control: Hermes + opencode + a vision LLM under MiOS

**Status:** architecture proposal (May 2026). Building blocks identified;
helper + skill not yet wired (tracked as future task).

This document captures the research synthesis behind achieving Anthropic-
"Computer Use"-style desktop automation on a MiOS-on-WSL2 host using ONLY
local models running on the operator's Ollama instance (`MiOS-Inference`
on `:11434`). No cloud APIs; no Browserbase / Browser Use / Firecrawl
dependencies.

## TL;DR

Hermes is the orchestrator. opencode is the coder. The missing piece is
a **screen-grounding vision LLM** that can take a screenshot and return
clickable coordinates for UI elements. The cleanest local options today
(May 2026):

| Vision model | Size | Native grounding? | Local Ollama tag | Notes |
|---|---|---|---|---|
| **UI-TARS-1.5-7B** (ByteDance, Apache 2.0) | 7B | YES -- trained on Win/macOS/Web GUI traces, returns absolute coords directly | `avil/UI-TARS` (1.7B variant) on Ollama; full 7B via HF | Purpose-built for PC control; **strongest local option** |
| **Qwen3-VL** (Alibaba, Apache 2.0) | 2B / 4B / 8B / 32B / 235B | YES -- 2D grounding (absolute + relative coords); native "operates PC/mobile GUIs, recognizes elements" | `qwen3-vl:4b` / `qwen3-vl:8b` | Smaller variants run on a 4090 alongside the existing chat model |
| Llama 3.2-Vision | 11B / 90B | NO grounding -- general image understanding only | `llama3.2-vision:11b` | Needs Set-of-Mark prompting for grounding; weaker for PC tasks |
| MiniCPM-V / Moondream | 2B-8B | Partial | various | OCR-strong; coordinate output is unreliable |

**Recommended baseline:** `qwen3-vl:4b` for the grounding pass, reused via
the existing `auxiliary` lane in Hermes config. Upgrade path: pull
`bytedance/UI-TARS-1.5-7B` when the GGUF lands officially in the Ollama
library.

## Pieces already in place

* **Action engine -- `mios-pc-control`** (`/usr/libexec/mios/mios-pc-control`)
  ships in the MiOS image, driven by `mios-pc-control.ps1` on the
  Windows side. Subcommands: `screenshot`, `click`, `double-click`,
  `mouse-move`, `type`, `key`, `key-combo`, `window-list`,
  `window-focus`, `window-move`, `window-resize`. All Win32 SendInput
  + GDI capture + EnumWindows via PowerShell. Same as Anthropic's
  Computer Use surface but Windows-native.
* **Web-via-CDP -- `mios-hermes-browser` + Hermes browser_***
  toolset.** Hermes's `browser_navigate` / `_snapshot` / `_click` /
  `_type` / `_vision` already work against the local ChromeDev with
  `--remote-debugging-port=9222`. Auto-wired in `browser.cdp_url:
  http://localhost:9222`. Uses the **DOM/aria tree** as the primary
  grounding (cheap, no vision LLM needed) and falls back to
  `browser_vision` (screenshot + analysis) only when the page defeats
  DOM-based interaction (canvas apps, captchas, custom-rendered UIs).
* **Operator-side launcher broker -- `mios-launcher.service`**
  bridges the WSL service-user perm wall so any agent action can
  reach the operator's WSLg session.
* **mios-pwsh** + **mios-windows {ps,cmd,launch}** for raw shell-out
  to the Windows side.
* **opencode** (host install at `/usr/lib/mios/opencode/bin/opencode`)
  reachable as a delegate-task ACP target:
  `delegate_task(tasks=[{goal:..., acp_command:"opencode"}])`.

## What's missing

A bridge between **screenshot** (we have) and **action** (we have)
that doesn't require Hermes's main reasoning model to be vision-
capable. The current `qwen3-coder:30b` is text-only.

Two implementation options:

### Option A: vision-aux model in Hermes config (smallest change)

Hermes 0.13.x's `auxiliary:` block lets you point individual subtasks
at different models. Add a `vision_grounding:` lane:

```yaml
auxiliary:
  vision_grounding:
    provider: custom:local-ollama
    base_url: http://localhost:11434/v1
    model: qwen3-vl:4b
```

Then a new `mios-pc-vision` helper:

```
mios-pc-vision <screenshot.png> "<query>"
  -> calls /v1/chat/completions on auxiliary.vision_grounding with
     [system: "You are a UI grounding model. Given a screenshot +
      query, return the {x, y} click coordinates of the matching
      element."]
  -> returns JSON { "x": ..., "y": ..., "confidence": ..., "reasoning": ... }
```

The agent's loop becomes:

```
mios-pc-control screenshot /tmp/screen.png
mios-pc-vision /tmp/screen.png "the OK button"
  -> {"x": 814, "y": 562, "confidence": 0.92, ...}
mios-pc-control click 814 562
mios-pc-control screenshot /tmp/screen.png    # verify
```

### Option B: native UI-TARS-Desktop wrapper

Pull UI-TARS into Ollama (1.7B variant exists at `avil/UI-TARS`;
7B via direct GGUF). Wrap its API with the same `mios-pc-vision`
shim. Trade-off: better grounding accuracy on PC tasks vs. carrying
two vision models.

## Hermes + opencode division of labor

Once `mios-pc-vision` exists, the architecturally clean orchestration
is:

| Phase | Owner | Tools |
|---|---|---|
| **Plan**: decompose "open Notepad and type 'hello'" into clicks/keys | Hermes (qwen3-coder:30b) | `todo`, `delegate_task`, reasoning |
| **Ground** each step: where IS the Notepad icon? | `mios-pc-vision` (qwen3-vl:4b auxiliary) | `mios-pc-control screenshot` -> vision LLM call |
| **Act**: clicks + keystrokes | `mios-pc-control` (Win32 SendInput) | -- |
| **Verify**: screenshot + diff against goal | Hermes + vision aux | -- |
| **Code-gen** when a task wants a script (PowerShell, Python) | opencode via delegate_task | `acp_command:"opencode"` |

For BROWSER tasks (URL nav, form fill, scraping), skip the vision
loop entirely -- Hermes's `browser_*` toolset uses DOM/aria
references which are deterministic and don't need a vision LLM.
The vision loop is only needed for canvas apps + Win32 GUIs.

## Pull sequence (operator-side, when ready to enable)

```
# 1. Pull the vision model
ollama pull qwen3-vl:4b   # ~3 GB

# 2. Add the vision_grounding aux lane to mios.toml [ai] (proposed)
#    or directly to /var/lib/mios/hermes/config.yaml

# 3. Build mios-pc-vision (the grounding wrapper) -- not yet shipped
#    Future: /usr/libexec/mios/mios-pc-vision

# 4. Author a pc-control SKILL.md in /usr/share/mios/hermes/skills/
#    that documents the screenshot -> vision -> click loop pattern

# 5. Test against a known target:
#    mios-pc-control screenshot /tmp/desktop.png
#    mios-pc-vision /tmp/desktop.png "the Start button"
#    mios-pc-control click <x> <y>
```

## Why local-only is feasible NOW (vs. 12 months ago)

* **UI-TARS-1.5-7B** (ByteDance, Apache 2.0, May 2025) was the first
  open vision model trained specifically on PC GUI traces -- before
  it, local PC control needed Set-of-Mark prompting hacks on top of
  general vision LLMs. Direct coordinate output makes the loop
  efficient.
* **Qwen3-VL 4B** (Alibaba, late 2025) brings native 2D grounding to
  a 4B-parameter footprint that fits alongside qwen3-coder:30b on a
  single 4090.
* **Hermes-Agent's local browser path** (Playwright-driven local
  Chromium via CDP) eliminates the Browserbase dependency for web
  tasks; combined with the desktop loop above, the entire PC-Control
  surface stays on-host.

## Architectural invariants (don't violate)

* **mios.toml first.** The vision-aux model + any ollama-pull list
  must be declared in `mios.toml [ai]`, not hardcoded in scripts.
* **BOUND-IMAGES.** New vision models in the bake set go through
  automation/37-ollama-prep.sh, not runtime pulls.
* **TOML-first.** `mios-pc-vision` reads its model name + base URL
  from the layered mios.toml resolver, not env var defaults.

## References

| # | Source | Notes |
|---|---|---|
| 1 | https://ollama.com/blog/qwen3-vl | Qwen3-VL launch + GUI agent capabilities |
| 2 | https://github.com/bytedance/UI-TARS | UI-TARS model; Win/macOS/Web training |
| 3 | https://github.com/bytedance/UI-TARS-desktop | UI-TARS-Desktop reference impl |
| 4 | https://ollama.com/avil/UI-TARS | 1.7B UI-TARS GGUF on Ollama |
| 5 | https://hermes-agent.nousresearch.com/docs/user-guide/features/browser | Hermes browser_* tool surface |
| 6 | https://github.com/NousResearch/hermes-agent/issues/374 | Local browser backend (Playwright) tracking |
| 7 | https://github.com/NousResearch/hermes-agent/issues/6780 | Auto-detect local Chrome CDP (already handled in MiOS via mios-hermes-browser.service) |
| 8 | https://github.com/anomalyco/opencode/pull/7302 | opencode native browser tools (Playwright; alternative to Hermes browser_* path) |
| 9 | https://github.com/microsoft/UFO | Windows-specific reference (Hybrid UIA + Vision); architecturally similar to what mios-pc-control + mios-pc-vision would do |
| 10 | https://github.com/openinterpreter/open-interpreter | Vision-mode reference; uses screenshot + GPT/Claude vision; we replace with local Qwen3-VL or UI-TARS |
| 11 | https://fazm.ai/blog/best-open-source-computer-use-ai-agents-2026 | 2026 survey; UI-TARS rated strongest open option for Windows |
