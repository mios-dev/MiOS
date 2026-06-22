<!-- AI-hint: Concept documentation detailing the research and architecture for integrating native Windows UI Automation (UIA) into the MiOS AI agent ecosystem.
     AI-related: ../../../windows/mios-oscontrol-server.ps1, ../../../windows/mios-uia-dump.ps1 -->
# MiOS Native Windows UIA Integration (2026-06-22)

This document synthesizes the research and architectural strategy for enabling MiOS (the AI system) to deeply understand and interact with full applications based on arbitrary windowing frameworks (Win32, UWP, WPF, Electron, etc.) via **Windows UI Automation (UIA)**.

## Background: The Limits of Visual-Only Parsing

Historically, AI desktop automation relied on visual models (e.g., OmniParser, pure VLM inputs). While flexible, visual parsing suffers from:
1. **Latency & Cost:** Processing full-resolution screenshots through multimodal LLMs for every interaction step is computationally expensive.
2. **Ambiguity:** Guessing the semantic intent of a button from pixels alone (especially when icon-only) often results in hallucinations.
3. **Fragility:** Changes in resolution, themes (dark/light mode), or pixel-level UI updates break visual coordinate mapping.

## The UIA Solution

The **Windows UI Automation (UIA)** framework is the operating system's native accessibility layer. It constructs a structured, semantic tree of every open window.
Unlike standard `Get-Process` or basic `EnumWindows` Win32 calls (which miss internal elements and child frames in Electron or UWP apps), UIA exposes a unified Document Object Model (DOM) for the desktop.

### Core Architecture for MiOS

MiOS leverages UIA through a two-way **Grounding & Execution** pipeline mediated by the `mios-oscontrol-server.ps1` executor.

#### 1. UIA Grounding (Perception)
Instead of relying solely on pixels, the MiOS agent queries the OS control server for a structured representation of the active window's UI tree.
- **`UIAutomationClient.dll`**: The executor uses the native COM API to crawl the `AutomationElement` tree.
- **Tree Filtering**: The raw UIA tree is incredibly dense. MiOS implements a "Shadow DOM" approach, filtering out non-interactive layout containers and retaining only semantic targets: `ControlType.Button`, `ControlType.Edit`, `ControlType.Document`, etc.
- **Tokenization**: The filtered tree is returned to the LLM as a JSON object containing `AutomationId`, `Name`, `ControlType`, and absolute screen coordinates (`BoundingRectangle`).

#### 2. UIA Execution (Action)
Once the LLM reasons over the UI tree, it issues semantic actions (e.g., "click button with AutomationId 'submit_btn'").
- **Semantic Targeting**: The executor matches the requested target against the Live UIA tree.
- **Pattern Invocation (Preferred)**: Where possible, MiOS uses native UIA Patterns (`InvokePattern.Invoke()`, `ValuePattern.SetValue()`) instead of simulating keystrokes or mouse clicks. This completely eliminates race conditions, input focus stealing (UIPI blocks), and "dropped keystroke" bugs.
- **Fallback Simulation**: If a control exposes no writable UIA pattern (e.g., custom rendering engines or legacy Win32), the executor falls back to `SetCursorPos` and `mouse_event` on the element's calculated center coordinates (`cx, cy`).

### Framework Compatibility

UIA inherently normalizes the UI tree across disparate rendering frameworks:
- **Electron (Spotify, Discord, VS Code)**: Chromium natively maps its DOM to the Windows UIA tree. Buttons, text fields, and links are fully enumerable, bypassing the "MainWindowHandle=0" problem of the parent stub processes.
- **UWP (Settings, Windows Store)**: Natively integrated with UIA.
- **Legacy Win32**: Best-effort mapping; some custom-drawn controls may appear as opaque `Pane` elements, requiring hybrid vision fallback.

## Implementation Details

The `mios-oscontrol-server.ps1` already implements `Find-UIElements` to target individual elements by name. The next phase (implemented via `mios-uia-dump.ps1`) expands this to capture the *entire* semantic tree for LLM grounding, allowing the agent to "see" the application structure before deciding on an action.
