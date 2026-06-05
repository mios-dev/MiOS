---
name: linux-control
description: Use when the operator asks to control the LINUX / Wayland desktop on a MiOS host -- screenshot it, click/type/press keys, find a UI element, or list windows -- on bare-metal/VM GNOME or KDE, on WSLg, OR on a remote MiOS desktop node. The SEMANTIC path (cu_atspi_query / cu_ground via AT-SPI) needs NO vision model and NO pixels. The VISION path (cu_screenshot + cu_ground via qwen3-vl / UI-TARS) is the fallback only when the accessibility tree is empty. The executor is ENVIRONMENT-ADAPTIVE -- the same verbs drive bare-metal GNOME, WSLg, and a federated remote desktop with no change.
metadata:
  hermes:
    requires_tools: [terminal]
---

# linux-control -- Linux/Wayland computer-use under MiOS

The Linux peer of [pc-control](../pc-control/SKILL.md) (which drives the
Windows host via Win32). This skill drives the **Linux/Wayland desktop**
via `mios-computer-use` (the `cu_*` verbs). It is environment-adaptive:
on bare-metal/VM GNOME or KDE it uses the RemoteDesktop + Screenshot
portals; on WSLg it transparently delegates to `mios-pc-control`; and
when a remote desktop's `executor_endpoint` is configured it routes the
op there. **You don't pick the backend -- the executor does.**

## cu_* vs pc_* -- which family do I use?

* **Linux/Wayland target** (bare-metal MiOS, a Linux VM, a remote MiOS
  desktop node) -> use the **`cu_*`** verbs.
* **Windows-host target** (you're on MiOS-on-WSL2 and the operator means
  the Windows desktop the distro lives inside) -> use the **`pc_*`**
  verbs / [pc-control](../pc-control/SKILL.md).

If you're unsure which desktop the operator means, check the environment
first (`sys_env`, `mios-env-probe`, or `skill_view name=mios-environment`).
On a pure Linux deployment there is no Windows host, so `cu_*` is the only
answer. `cu_*` also self-delegates to `pc_*` under WSLg, so reaching for
`cu_*` is the safe default when the target is "this machine's desktop".

## The two paths (pick by what the operator asked for)

### Path A: SEMANTIC (no vision, no screenshots) -- PREFER THIS

The accessibility tree (AT-SPI2) exposes every GTK/Qt widget's role, name,
and on-screen coordinates **without a single pixel or model call**. Always
try this first.

* "click the Save button" / "where is the OK button"
  -> `cu_ground query="Save button"`  (AT-SPI first; returns {x,y})
  -> `cu_click x=<x> y=<y>`
* "what UI elements match X" / "find the address bar"
  -> `cu_atspi_query query="address"`  (role/name -> screen coords)
* "what windows are open"
  -> `cu_window_list`

`cu_ground` returns `{"x":..,"y":..,"confidence":0.99,"source":"atspi"}`
when the a11y tree has the element. Deterministic, instant, offline.

### Path B: VISION (screenshot -> grounded coordinates) -- FALLBACK

Use this only when AT-SPI returns nothing -- Chromium/Electron without
accessibility, canvas apps, custom-rendered UIs. `cu_ground` does this
automatically: if the a11y tree has no match it screenshots the desktop
and calls the grounding VLM.

```
cu_screenshot path=/tmp/screen.png
cu_ground query="the blue Submit button"
  -> {"x":814,"y":562,"confidence":0.9,"source":"atspi|vision","reasoning":"..."}
cu_click x=814 y=562
cu_screenshot path=/tmp/after.png    # verify
cu_ground query="did the Submit button disappear?"
```

The grounding model defaults to `qwen3-vl:4b` on the local Ollama (JSON
coordinate output). When the gated vLLM `mios-grounding` lane is enabled
(UI-TARS-1.5-7B), `mios-pc-vision` auto-switches to the UI-TARS Action-DSL
parser -- same `cu_ground` interface, better grounding on dense UIs. The
model + endpoint are SSOT (`mios.toml [ai].vision_grounding_model` /
`[computer_use].grounding_model`) -- never hardcode them.

## Acting -- write-class verbs

`cu_click`, `cu_type`, `cu_key`, `cu_key_combo` send real input via the
RemoteDesktop portal (GNOME/KDE) or a self-written uinput device (wlroots /
headless seat). They are **write-class** -- they go through the DoD /
approval gate. Read-class verbs (`cu_screenshot`, `cu_window_list`,
`cu_ground`, `cu_atspi_query`) run freely.

* `cu_type text="hello world"`            type literal text
* `cu_key key=Enter`                       single key (Enter/Tab/F5/Up/...)
* `cu_key_combo combo="Ctrl+S"`            modifier combo
* `cu_click x=200 y=140 button=right`      click (left|right|middle)

## Decision tree

```
Operator wants to control the Linux desktop
    |
    +-- "what's on screen / what windows"  -> cu_window_list
    +-- "find / where is <element>"        -> cu_ground (AT-SPI, vision fallback)
    +-- "click <named element>"            -> cu_ground -> cu_click
    +-- "type / press <keys>"              -> cu_type / cu_key / cu_key_combo
    +-- "click <thing only visible as pixels>" -> cu_screenshot + cu_ground (vision)
    +-- target is a WEBPAGE                 -> Hermes browser_* (DOM/aria, no vision)
    +-- target is the WINDOWS host          -> pc-control (pc_* verbs)
```

For BROWSER tasks prefer Hermes's `browser_*` toolset -- DOM/aria grounding
is faster and more reliable than vision for web UIs. The `cu_*` vision loop
is for native GTK/Qt/canvas apps and the desktop shell itself.

## Worked example -- click a button by name, no vision model

```bash
# AT-SPI knows the button's role + coordinates -- no screenshot, no VLM:
cu_ground query="the Save button"
  -> {"x":640,"y":480,"confidence":0.99,"source":"atspi"}
cu_click x=640 y=480
```

## Worked example -- canvas app the a11y tree can't see

```bash
cu_screenshot path=/tmp/canvas.png
cu_ground query="the red record button"        # AT-SPI empty -> vision VLM
  -> {"x":512,"y":700,"confidence":0.88,"source":"vision"}
cu_click x=512 y=700
```

## Driving a REMOTE desktop (federation)

A second MiOS/Linux machine runs `mios-computer-use-server` (dual MCP + A2A).
Register it once in the operator overlay and the central agent consumes it:

* As an **MCP server** -- add to `/etc/mios/ai/v1/mcp.json` -> its `cu.*`
  tools appear in the agent loop as `mcp.<node>.cu.*`.
* As an **A2A peer** -- add to `/etc/mios/ai/v1/a2a-peers.json` -> its
  `desktop-control` skill appears at `/v1/a2a/skills`; delegate a whole
  desktop task to it with a shared `contextId`.

See `usr/share/doc/mios/concepts/computer-use-federation.md` for the
overlay shapes. You don't do anything special in-chat -- the registered
node's tools are just there alongside the local `cu_*` verbs.

## What this skill is NOT

* NOT for the Windows host -- that's `pc_*` / pc-control.
* NOT for webpages -- prefer `browser_*` (DOM grounding).
* NOT a way to bypass the approval gate -- write-class verbs are gated.
* NOT dependent on ydotool -- input is portal (libei) or our own uinput
  device, never the AGPL ydotool daemon.
