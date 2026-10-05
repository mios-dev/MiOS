# MiOS Architecture: Unified Desktop & Terminal Interaction Mechanics

> **Architectural Status**: Canonical System Specification
> **Governing Standards**: ADR 0009 (Unified Config Surface via `mios.html` / `:8640/configure`), ADR 0010 (SSOT-as-system-dotfiles), Architectural Law 5 (UNIFIED-AI-REDIRECTS), Law 8 (SSOT Primacy).

---

## 1. Overview and Dual-Surface Architecture

In the MiOS architecture, keyboard shortcuts and interaction mechanics span two unified surfaces:
1. **The Desktop Environment Plane**: Governed by the **Hyprland** Wayland compositor and the **Quickshell** reactive UI engine.
2. **The Native Root Terminal Plane**: Multiplexing POSIX execution with the local OpenAI-compatible agent loop without modal boundaries.

Both planes are governed by the Single Source of Truth (SSOT) defined in `/usr/share/mios/mios.toml` and edited graphically via `mios.html` (hosted locally at `:8640/configure` per ADR 0009). In accordance with ADR 0010 (SSOT-as-system-dotfiles), one `mios.toml` file deterministically projects Hyprland keybindings (`~/.config/hypr/hyprland.conf`), Quickshell launcher channels, shell aliases, and terminal hotkeys into active userland configuration.

```
+-------------------------------------------------------------------------------+
|                       Single Source of Truth (SSOT)                           |
|                 /usr/share/mios/mios.toml & /etc/mios/mios.toml               |
|                     (Edited graphically via mios.html :8640)                  |
+---------------------------------------+---------------------------------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
                   v                                         v
+-------------------------------------+   +-------------------------------------+
|      Desktop Environment Plane      |   |      Native Root Terminal Plane     |
|   (Hyprland Wayland + Quickshell)   |   |   (POSIX Execution + Agent Loop)    |
|                                     |   |                                     |
| • Hyprland dynamic tiling & chords  |   | • Unmodal POSIX & AI co-execution   |
| • Quickshell reactive UI engine     |   | • GNU Readline & process supervisor |
| • Universal App Drawer (Super+Space)|   | • In-Terminal AI Sigils (!, @, %, ?) |
| • Dynamic Browser Dispatch (Super+b)|   | • Streamlined Slash Commands (/...) |
| • Native Root Terminal (Super+Enter)|   | • tmux-mcp + MiOS-MCP integration   |
+-------------------------------------+   +-------------------------------------+
```

---

## 2. Desktop & Window Management Architecture: Hyprland + Quickshell

The graphical desktop integrates a Wayland compositor with a reactive user-interface shell:

* **Hyprland Compositor:** Manages dynamic tiling window layouts, multi-monitor topology, hardware-accelerated rendering, input device dispatch, and low-level key chord interception.
* **Quickshell Engine:** A high-performance Qt/QML reactive shell layer that renders desktop panels, system overlays, on-screen displays (OSDs), notifications, and the global application drawer.
* **Global Application Drawer (`Super + Space`):** Unlike traditional Linux launchers that index only native desktop entries, the Quickshell drawer unifies application discovery across three distinct runtime environments into a single fuzzy-search model:
  1. **Native Linux Applications:** Standard FreeDesktop `.desktop` files located in `/usr/share/applications` and `~/.local/share/applications`, including containerized Flatpaks and host system binaries.
  2. **Windows Applications:** Deployed via KVM/VFIO microVMs, Proton/Wine prefixes, or seamless RDP/WinApps containers. These launch through lightweight bridge shims that manage headless background VM states transparently.
  3. **Android Applications:** Run via Waydroid (containerized LXC Android userland sharing the host kernel and Wayland socket). Applications are indexed directly by their Android package names (`apk`/intent shortcuts) and launch into native Wayland windows with full hardware acceleration.
* **Browser Dispatch via Aliases (`Super + b`):** Pressing `Super + b` does not hardcode a specific executable. Instead, it reads the `[aliases]` section projected from `mios.toml` / `mios.html` (e.g., `aliases.browser = "firefox"`, `"chromium"`, `"zen"`, or `"brave"`). The `userenv.sh` / `mios_toml.py` projection engine sets `$MIOS_BROWSER`, ensuring `Super + b` opens the operator's configured browser across host and containerized workspaces.

---

## 3. Complete MiOS Keybindings Reference

### 3.1 Canonical Implemented SSOT Keymap (`[keybindings]` in `usr/share/mios/mios.toml` & `README.md`)

The production MiOS system implements a single, unified action map for desktop shortcuts and terminal sessions defined under `[keybindings]` in `usr/share/mios/mios.toml`. This avoids conflicting with window manager Super chords:

* **Desktop Accelerator (`<Control><Alt><Shift>` / `Ctrl+Alt+Shift`):**
  - `Ctrl + Alt + Shift + t`: Opens the **MiOS Terminal** (`alacritty -e /usr/libexec/mios/mios-terminal`).
  - `Ctrl + Alt + Shift + a`: Opens the **MiOS AI Terminal** (`alacritty -e /usr/libexec/mios/mios-terminal --action ai` -> `/usr/libexec/mios/mios-ai-terminal`).
  - `Ctrl + Alt + Shift + g`: Opens **MiOS Agents Observer** (`alacritty -e /usr/libexec/mios/mios-terminal --action agents` -> `mios agents --watch`).
  - `Ctrl + Alt + Shift + m`: Opens the **MiOS System Monitor** (`alacritty -e /usr/libexec/mios/mios-terminal --action system` -> `mios mon`).

* **In-Terminal tmux-mcp Prefix (`Ctrl-b` / `C-b`):**
  Within native terminal sessions (`socket_name = "mios-human"`, session `mios`), `Ctrl-b` serves as the canonical command prefix:
  - `Ctrl-b` then `t`: New window (`new-window`).
  - `Ctrl-b` then `a`: New AI window (`new-window -n MiOS-AI /usr/libexec/mios/mios-ai-terminal`).
  - `Ctrl-b` then `g`: Run agents observer (`run-shell '/usr/libexec/mios/mios-terminal --action agents'`).
  - `Ctrl-b` then `m`: New system monitor window (`new-window -n MiOS-System mios mon`).
  - Window & Pane navigation: `h`/`j`/`k`/`l` (pane select), `s` (split vertical), `v` (split horizontal), `n`/`p` (next/prev window), `z` (zoom toggle), `d` (detach).

---

### 3.2 Proposed Extended Wayland Compositor Spec (Hyprland + Quickshell Architectural Design)

The following Super-based chord layout represents the extended Wayland compositor specification designed for Hyprland and Quickshell desktop environments:

| Keybinding | Scope | Action and Behavioral Mechanics | Governing SSOT Key / Config |
| :--- | :--- | :--- | :--- |
| `Super + Space` | Quickshell Overlay | Opens the **Universal Global App Drawer**, indexing across native Linux, Windows (VM/Proton), and Android (Waydroid) applications. | `[desktop.launcher]` (Proposed) |
| `Super + b` | Desktop / Shell | Launches the **User Preferred Browser**, resolving dynamically from `aliases.browser` in `mios.toml`. | `aliases.browser` |
| `Super + Return` | Desktop / Shell | Opens the **Native MiOS AI Root Terminal** (`[desktop.terminal]`). | `[desktop.terminal]` (Proposed) |
| `Super + e` | Desktop / Shell | Opens the default file manager (resolves from `aliases.file_manager`). | `aliases.file_manager` |
| `Super + q` | Hyprland | Closes the actively focused window (`killactive`). | `hyprland.conf` |
| `Super + f` | Hyprland | Toggles fullscreen mode for the active window. | `hyprland.conf` |
| `Super + v` | Hyprland | Toggles floating mode for the active window. | `hyprland.conf` |
| `Super + r` | Quickshell / Hypr | Re-evaluates and hot-reloads desktop layouts directly from `mios.toml` projections. | ADR 0010 |
| `Super + a` | Quickshell Panel | Opens the **Quick Settings / Control Center** (WiFi mesh, Bluetooth, Blade-node cluster). | `[blade.mesh]` (Proposed) |
| `Super + n` | Quickshell Panel | Toggles the Quickshell Notification and Action Center. | `[desktop.notifications]` (Proposed) |
| `Super + m` | Quickshell Overlay | Toggles the **Hardware & AI Inference Lane Monitor** (live GPU/NPU utilization, vLLM status). | `[observability]` (Proposed) |
| `Super + Escape` | Session / Lock | Locks the graphical session and engages the Quickshell lockscreen. | `[desktop.security]` |
| `Super + h/j/k/l` | Hyprland Focus | Moves window focus left, down, up, or right across tiled windows (Vim navigation). | `hyprland.conf` |
| `Super + Shift + h/j/k/l` | Hyprland Window | Moves the active window position within the current tiled layout. | `hyprland.conf` |
| `Super + 1 .. 9` | Hyprland Workspace | Switches to virtual desktop workspace 1 through 9. | `hyprland.conf` |
| `Super + Shift + 1 .. 9` | Hyprland Workspace | Moves the active window to virtual desktop workspace 1 through 9. | `hyprland.conf` |

---

### 3.3 Root Terminal TUI, Process Control, and Readline Keybindings

Within the MiOS native root terminal, POSIX execution and AI conversational loops coexist in a single window without modal boundaries.

| Keybinding | Domain | Classification | Operational Semantics and State Transitions |
| :--- | :--- | :--- | :--- |
| `Ctrl+C` | Subshell / Inference | Soft Interrupt | Interrupts active model token streaming or cancels a running tool without terminating the terminal process; clears unsubmitted composer text. |
| `Ctrl+C Ctrl+C` | Agent Runtime | Emergency Stop | Pressing twice within 800 milliseconds force-terminates child processes, subagents, and releases sandbox namespace locks. |
| `Escape` | Stream Reader | Stream Cancel | Cancels streaming generation mid-turn while preserving partial response tokens in the context buffer. |
| `Escape Escape` | Checkpoint Stack | State Rewind | If drafting in the composer, clears text to history; if composer is empty, opens the interactive Rewind Menu to roll back conversation and filesystem changes. |
| `Ctrl+D` (Empty) | Shell Session | Process Exit | Cleanly shuts down the session, serializes JSONL transcripts to disk, and closes background sandbox containers. |
| `Ctrl+D` (With Text) | Composer Buffer | Character Deletion | Performs a standard EOF forward character deletion at the current cursor position. |
| `Ctrl+B` | Terminal Multiplexer | Tmux Command Prefix | Standard prefix for tmux commands (`Ctrl-B` then `t`/`a`/`g`/`m` or navigation chords) in `mios-human`. |
| `Ctrl+X Ctrl+K` | Agent Process Group | Subagent Termination | Broadcasts a global kill signal to terminate all running background subagents and auxiliary workers in the active session. |
| `Ctrl+Z` | POSIX Control | Job Suspension | Emits a `SIGTSTP` signal to suspend the active foreground process; resumes execution via the native `fg` shell command. |
| `Ctrl+A` | GNU Readline | Cursor Navigation | Moves the cursor immediately to the beginning of the active logical line. |
| `Ctrl+E` | GNU Readline | Cursor Navigation | Moves the cursor immediately to the end of the active logical line. |
| `Alt+B` / `Alt+F` | GNU Readline | Word Navigation | Moves the cursor backward (`Alt+B`) or forward (`Alt+F`) one word. |
| `Ctrl+K` | GNU Readline | Line Kill | Deletes all text from the current cursor position to the end of the line, storing it in the kill ring. |
| `Ctrl+U` | GNU Readline | Line Kill | Deletes all text backward from the current cursor position to the start of the line, storing it in the kill ring. |
| `Ctrl+W` | GNU Readline | Word Kill | Deletes the preceding whitespace-delimited word, storing it in the kill ring. |
| `Ctrl+Y` | GNU Readline | Yank / Paste | Pastes the most recently deleted string from the kill ring into the composer. |
| `Alt+Y` | GNU Readline | Kill Ring Cycle | Immediately after a yank, cycles backward through older entries in the kill ring. |
| `Ctrl+S` | POSIX Flow Control / Composer | XOFF / Draft Stashing (Proposal) | **Standard POSIX**: Transmits XOFF flow control, pausing terminal output until `Ctrl+Q` (XON). In dedicated AI composers where IXON is disabled (`stty -ixon`), stashes/restores prompt drafts. |
| `Ctrl+R` | Command History | Reverse Search | Opens an interactive reverse-search through past commands, prompts, and slash directives. |
| `Ctrl+G` / `Ctrl+X Ctrl+E` | External Composition | Editor Hand-off | Opens `$EDITOR` (e.g., Neovim, Nano) pre-populated with active prompt text and model context; reloads into composer upon save and exit. |
| `Ctrl+O` | Viewport Renderer | Transcript Inspection | Toggles the transcript viewer to inspect raw timestamps, routing metadata, token counts, and full MCP JSON payloads. |
| `Ctrl+T` | Statusline | Checklist Toggle | Toggles the visibility of the agent's step-by-step execution roadmap in the terminal statusline. |
| `Ctrl+L` | Screen Buffer | Screen Redraw | Triggers a full terminal screen redraw to clear visual ANSI stream artifacts without modifying context. |
| `Shift+Tab` | Permission Controller | Mode Cycling | Cycles runtime permission modes between standard prompting (`untrusted`), risky-action prompting (`on-request`), and full autonomy (`never`). |
| `Alt+,` / `Alt+.` | Deliberation Engine | Reasoning Steering | Dynamically decreases (`Alt+,`) or increases (`Alt+.`) the model's reasoning token budget on the fly. |

---

## 4. In-Terminal AI Syntax and Sigils Mapped to Upstream AI Patterns

The input evaluator uses leading character sigils to route commands without requiring subshell wrappers:

| Sigil / Delimiter | MiOS Syntax | Upstream Patterns | Upstream Semantic Mapping | MiOS Operating Semantics |
| :--- | :--- | :--- | :--- | :--- |
| `!` | `!<cmd>` | Claude Code, Aider, Cursor CLI | Inline subshell escape. | **Sandboxed Shell Escape:** Native host binaries execute directly in the root terminal without prefixes. `!<cmd>` forces command execution inside the unprivileged container sandbox (ADR 0020), capturing logs into context. |
| `@` | `@<resource>` | Claude Code, Amazon Q, Cursor | Workspace file addressing. | **Deterministic Context Ingestion:** Bypasses vector searches to inject filesystem assets (`@/path`), Single Source of Truth blocks (`@ssot:<key>`), systemd journal logs (`@log:<unit>`), or AST outlines (`@tree:<dir>`). |
| `%` | `%<directive>` | Open Interpreter | Runtime metaprogramming. | **Harness Diagnostics:** Inspects local memory allocations, token counters, inference sidecar health, or dumps the in-memory ring tracer. |
| `?` | `? [topic]` | Claude Code | Interactive cheat sheet. | **Offline Documentation:** Queries local system manuals (`/usr/share/doc/mios/`) and the offline knowledge graph without network transit. |
| `??` | `?? <intent>` | GitHub Copilot CLI | Natural-language shell synthesis. | **Inline Shell Synthesis:** Invokes the local fast-tier model lane to synthesize a POSIX command string directly into the active composer line. |
| `{tag ... tag}` | `{tag\n...\ntag}` | Aider | Multi-line prompt enclosure. | **Tagged Multi-Line Block:** Encloses complex payloads, JSON objects, or code snippets, preventing internal literal braces from triggering early execution. |
| `\` + `Enter` | `\<Enter>` | Claude Code, Cursor CLI | Composer line break. | **Line Continuation:** Appends a literal newline to the prompt composer across terminal emulators. |

---

## 5. Streamlined Slash Commands Mapped to Upstream AI Standards

Commands beginning with a forward slash (`/`) are parsed locally before network transit, operating strictly over the OpenAI API schema (Law 2/5) and the SSOT configuration layer (Law 8). Redundant upstream shims (such as `/shell`, `/run`, or `/git`) are dropped in favor of native POSIX execution.

| MiOS Slash Command | Arguments | Upstream Pattern Equivalents | Upstream Comparison and MiOS Implementation |
| :--- | :--- | :--- | :--- |
| `/new` | `[name]` | Codex CLI (`/clear`, `/new`), Claude Code (`/clear`), Cursor (`/new-chat`) | Resets conversational dialogue buffer while maintaining terminal scrollback; initializes a new transcript in `/var/lib/mios/agent-pipe/sessions/`. |
| `/resume` | `[id \| --last]` | Codex CLI (`/resume`), Claude Code (`/resume`), Cursor (`/resume`) | Restores dialogue history, AST maps, and tool execution state from a persisted JSONL transcript. |
| `/fork` | `[name]` | Cursor CLI (`/fork`), Claude Code (`/fork`), Codex CLI (`/fork`) | Clones the active conversation tree and tool state into an independent process branch to explore alternative solutions safely. |
| `/compact` | `[tokens]` | Codex CLI (`/compact`), Claude Code (`/compact`), Goose CLI (`/compact`) | Summarizes dialogue history into an abstract semantic representation using native OpenAI Responses API compaction semantics. |
| `/tangent` | `[start \| drop \| merge]` | Amazon Q CLI (`/tangent`), Claude Code (`/btw`), Codex CLI (`/side`) | Checkpoints the primary conversation thread to investigate troubleshooting side-paths without context pollution. |
| `/plan` | `[prompt]` | Cursor CLI (`/plan`), Claude Code (`/plan`), Codex CLI (`/plan`) | Enters read-only analysis mode; requires the agent to formulate an implementation roadmap before making modifications (ADR 0019). |
| `/permissions` | `<untrusted \| on-request \| never>` | Codex CLI (`/permissions`, `/mode`), Cursor (`/run-everything`), Claude Code (`/permissions`) | Adjusts runtime autonomy: `untrusted` prompts for all actions, `on-request` prompts for consequential system writes, and `never` allows autonomous execution. |
| `/sandbox` | `<ro \| ws-write \| full>` | Cursor CLI (`/sandbox`), Codex CLI (`sandbox_mode`) | Configures filesystem namespace isolation boundaries and network egress filters per ADR 0020. |
| `/model` | `<model_id>` | Codex CLI (`/model`), Claude Code (`/model`), Open Interpreter (`/model`) | Swaps the active reasoning model mid-session via the local OpenAI-compatible catalog. |
| `/lane` | `<fast \| code \| reason>` | Aider (`/architect`, `/weak-model`), Claude Code (`/advisor`), Codex CLI (`/fast`) | Maps requests to local hardware-optimized execution lanes declared in `mios.toml` (e.g., vLLM sidecars, Hermes, or CPU runtimes). |
| `/advisor` | `[lane \| off]` | Claude Code (`/advisor`), Aider (`/architect`) | Initializes a dual-model architecture where an auxiliary model audits generated patches and configuration changes before disk writes. |
| `/init` | `[dir]` | Codex CLI (`/init`), Claude Code (`/init`) | Scaffolds a canonical `AGENTS.md` file while configuring vendor rule stubs as thin redirectors. |
| `/diff` | `[staged \| commit]` | Aider (`/diff`), Claude Code (`/diff`), Codex CLI (`/diff`) | Renders syntax-highlighted unified diffs across the root filesystem overlay (`.git` $\equiv$ `/`). |
| `/undo` | None | Aider (`/undo`), Codex CLI (`/undo`), Claude Code (`/rewind`) | *(Roadmap / Design Proposal)* Reverts the last atomic Git commit synthesized by the harness across the root overlay. |
| `/rollback` | `[checkpoint]` | *Native MiOS Primitive* (maps to Claude Code `/rewind`) | *(Roadmap / Design Proposal)* Interfaces directly with the underlying `bootc` deployment controller to execute `bootc rollback` if host-level mutations fail. |
| `/mcp` | `<list \| reload \| auth>` | Claude Code (`/mcp`), Codex CLI (`/mcp`), Goose CLI (`/mcp`) | Connects and manages Model Context Protocol tools mediated via the OpenAI Responses API schema (Law 2). |
| `/mesh` | `<nodes \| status \| tasks>` | *Native MiOS Primitive* | *(Roadmap / Design Proposal)* Interrogates the local 16-byte binary wire protocol, monitoring peer discovery and workload placement across the Blade-node cluster (ADR 0016/0020). |

---

## 6. Single Source of Truth Configuration: `mios.toml` / `mios.html`

The aliases, keybindings, and application execution parameters are declared in `/usr/share/mios/mios.toml` and projected into userland:

```toml
# ==============================================================================
# MiOS SSOT Configuration: Desktop & Environment Aliases
# ==============================================================================

[aliases]
browser = "firefox"                    # Super + b dispatch target (firefox | chromium | zen | brave)
file_manager = "nautilus"              # Super + e dispatch target
editor = "nvim"                        # $EDITOR fallback for terminal hand-offs
terminal = "mios-terminal"             # Super + Return dispatch target

[desktop.bindings]
mod_key = "SUPER"
app_drawer = "Space"                   # Super + Space triggers Quickshell global drawer
browser_launch = "b"                   # Super + b triggers aliases.browser
quick_settings = "a"                   # Super + a triggers control center
monitor_overlay = "m"                  # Super + m triggers hardware/AI monitor

[desktop.applications.runtimes]
linux_native = true                    # Indexes FreeDesktop .desktop paths
windows_seamless = true                # Bridges Proton prefixes and KVM/WinApps shims
android_waydroid = true                # Indexes Waydroid session APKs and intents

[ai.lanes]
fast = "http://localhost:8640/v1/models/hermes-light"
code = "http://localhost:8640/v1/models/qwen-coder"
reason = "http://localhost:8640/v1/models/deepseek-r1"
```

When an operator updates values via the browser configurator `mios.html`, the changes persist to `/etc/mios/mios.toml`, and the `userenv.sh` and Hyprland projection daemons update the active desktop and terminal keymaps without requiring a host reboot.
