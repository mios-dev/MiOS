---
name: pc-control
description: Use whenever the operator asks to OPEN, MOVE, RESIZE, FOCUS, LIST, or otherwise manipulate Windows applications + their windows on the host. The COMMAND path (mios-pc-control window-list / window-focus / window-move / window-resize + mios-windows launch) needs NO vision LLM and NO screenshots -- it works directly against the Win32 API. The vision path (screenshot + LLM-grounded coordinate click) is only for tasks where you don't already know what + where (e.g. "click that button in the browser" when DOM grounding fails).
metadata:
  hermes:
    requires_tools: [terminal]
---

# pc-control -- Windows host computer-use under MiOS

Two distinct paths. Pick the right one based on what the operator
asked for.

## Path A: COMMAND-DRIVEN (no vision, no screenshots)

Use this for ANY task where the target is named OR position-based:

* "open Notepad / Explorer / Calc / Paint / Task Manager / RegEdit
  / Control Panel / cmd / PowerShell / pwsh"
  -> `mios-windows launch <name>`
* "list all open windows" / "what windows are open"
  -> `mios-pc-control window-list`
* "bring Notepad to the front" / "focus this app"
  -> `mios-pc-control window-focus <hwnd-or-pid>`
* "move that window to (x, y)" / "snap to top-left"
  -> `mios-pc-control window-move <hwnd> <x> <y>`
* "resize the window to 800x600" / "make it bigger"
  -> `mios-pc-control window-resize <hwnd> <w> <h>`
* "type 'hello' in the active app" / "press Enter"
  -> `mios-pc-control type "hello"` / `mios-pc-control key Enter`
* "Ctrl+S to save" / "Alt+F4 to close"
  -> `mios-pc-control key-combo "Ctrl+S"`

This path is fully deterministic, runs entirely on the Win32 API,
and works for the Windows host the WSL distro lives inside. NO model
inference involved -- it's pure tool use.

## Path B: VISION-GROUNDED (only when target isn't named)

Use this ONLY when the target can't be reached by name (a button
on a webpage where DOM grounding doesn't help, a dialog without an
hwnd, an icon visible but without a programmatic reference).

```
mios-pc-control screenshot 'C:\Users\mios\AppData\Local\Temp\screen.png'
# (the screenshot lands on the Windows side; mios-pc-vision
#  reads from /mnt/c/.../screen.png)
mios-pc-vision /mnt/c/Users/mios/AppData/Local/Temp/screen.png "the OK button"
  -> {"x": 814, "y": 562, "confidence": 0.92, "reasoning": "..."}
mios-pc-control click 814 562
mios-pc-control screenshot 'C:\Users\mios\AppData\Local\Temp\after.png'
mios-pc-vision /mnt/c/.../after.png "did the OK button disappear?"
  -> {"x": -1, "y": -1, "confidence": 0.95, "reasoning": "OK button no longer visible (success)"}
```

The vision model defaults to `qwen3-vl:4b` (read from
`mios.toml [ai].vision_grounding_model`; configured in Hermes's
`auxiliary.vision_grounding` lane). Endpoint is the existing local
Ollama on `:11434`. ~3 GB resident; native 2D coordinate grounding.

For BROWSER tasks specifically, prefer Hermes's `browser_*` toolset
-- DOM/aria-grounded, deterministic, no vision LLM needed. The
vision loop is for canvas apps + Win32 GUIs where DOM grounding
doesn't apply.

## Decision tree

```
Operator request
    |
    +-- "open <named app>"           -> mios-windows launch <name>
    +-- "list/focus/move/resize"     -> mios-pc-control window-*
    +-- "type/press <key>"           -> mios-pc-control type/key/key-combo
    +-- "navigate/click on a webpage"-> Hermes browser_navigate/_click/_type
    +-- "click something I see"      -> screenshot + mios-pc-vision (when wired)
                                        OR ask the operator for the hwnd/coords
```

## Worked examples

### Open Notepad and move it to top-left

```bash
mios-windows launch notepad
sleep 1
HWND=$(mios-pc-control window-list | awk '/Notepad/{print $1; exit}')
mios-pc-control window-move "$HWND" 0 0
mios-pc-control window-resize "$HWND" 800 600
```

### Open File Explorer at a specific path

```bash
mios-windows launch explorer 'C:\Users\mios\Documents'
```

### Capture the screen and save to operator's Pictures dir

```bash
mios-pc-control screenshot 'C:\Users\mios\Pictures\screen.png'
```

### Send Ctrl+Alt+Del (NOT supported -- security-protected combo)

The Win32 SendInput surface can't generate Ctrl+Alt+Del because
Windows reserves it for the secure attention sequence. For
similar low-level control, use Windows itself or a kernel driver.

## What this skill IS NOT

* NOT a way to escalate to admin / Windows UAC. The interop spawns
  use the operator's filtered token; for elevated commands, the
  operator needs to elevate the parent process themselves.
* NOT a replacement for Hermes's `browser_*` tools when the target
  is a webpage. Browser tools use DOM/aria grounding which is
  faster + more reliable for web UIs.
* NOT yet the vision-grounded loop. That's queued; see
  /usr/share/mios/docs/agents/PC-CONTROL-LOCAL.md for the
  proposed wiring.
