<!-- AI-hint: Index of every shipped MiOS tool, generated from the AI-hint header each one already carries. -->

# Tool index

<!-- MIOS-GEN:boilerplate:what-mios-is -->
MiOS is one thing built two ways at once: an immutable, `bootc`/OCI-shaped
Fedora workstation -- the whole OS is a single container image, so `bootc
upgrade` behaves like a `git pull` and `bootc rollback` like a Ctrl-Z -- that
is *also* a local, self-hosted, agentic AI operating system.

<!-- derived from usr/share/mios/mios.toml [docs.boilerplate].what-mios-is -->
<!-- /MIOS-GEN:boilerplate:what-mios-is -->

Every file in the tree carries an `AI-hint:` header saying, in one line, what it
is for. Those headers are written next to the code and kept honest by
`check_hint_coverage`, so this page is not a hand-kept list that rots: it is
those same headers, read back out.

That is the whole point of the arrangement. A description lives in exactly one
place — beside the thing it describes — and every index, manual chapter and
overview is a projection of it. Correcting a description means editing the
header, never the pages that quote it.

## Executables (`usr/libexec/mios`)

The tools the system runs: firstboot sequences, health probes, resolvers,
generators and the agent-facing CLIs.

<!-- MIOS-GEN:index:usr/libexec/mios/mios-* -->
| File | What it is |
|---|---|
| `usr/libexec/mios/MiOS-Mon.py` | MiOS Unified TUI App -- The single cross-platform shared surface. |
| `usr/libexec/mios/mios-a2a-delegate` | Python shim for mid-run agent-to-agent delegation via the /v1/a2a/dispatch endpoint, allowing agents to offload sub-tasks to peers and inject responses into their reasoning loop as a live bus. |
| `usr/libexec/mios/mios-a2a-discover` | Scans and validates A2A peer nodes from mios.toml and CIDR ranges to populate /etc/mios/ai/v1/a2a-peers.json, ensuring the agent-pipe has a verified list of live, reachable peers for delegation. |
| `usr/libexec/mios/mios-a2a-mdns` | SSOT-driven avahi/mDNS side of A2A discovery. Renders the LAN-announce avahi service file from the /usr/lib template (port + service-type substituted from mios.toml, never hardcoded) when... |
| `usr/libexec/mios/mios-a2a-test` | A2A federation loopback smoke test -- drives a Message -> Task -> Artifact round-trip against the local MiOS /a2a JSON-RPC surface (MiOS talking to itself as a peer) and confirms the event table... |
| `usr/libexec/mios/mios-account-sync` | Daemon script that synchronizes PostgreSQL-defined accounts and aliases with the host UNIX user accounts (/etc/passwd, /etc/shadow, and /etc/group). |
| `usr/libexec/mios/mios-adguard-firstboot` | Generates the initial AdGuardHome.yaml config by merging mios.toml settings with live Tailscale network data (IPv4 and MagicDNS) to establish DNS binding and split-DNS rules during first boot. |
| `usr/libexec/mios/mios-agents-firstboot.sh` | Build-if-missing bootstrap for the mios-agents A2O super-container image |
| `usr/libexec/mios/mios-ai-capabilities-gen` | WS-2/WS-10 generator CLI -- regenerates (or --check verifies) the UNIFIED RBAC capability manifest ai/v1/capabilities.generated.json from the live mios.toml [verbs.*] + [recipes.*] SSOT, via the pure... |
| `usr/libexec/mios/mios-ai-clear` | Executes a Day-0 global reset of the MiOS AI stack by purging all transient runtime states, Hermes cron jobs, OWUI data, and pgvector agent caches while preserving core identities and configurations. |
| `usr/libexec/mios/mios-ai-firstboot` | Provisioning script that installs the hermes-agent Python venv and extracts llama.cpp GGUF models to enable AI services, creating a sentinel file to gate network-less boot retries. |
| `usr/libexec/mios/mios-ai-hint-coverage` | AI-hint coverage fitness-function -- reuses the mios-ai-tag taggability |
| `usr/libexec/mios/mios-ai-manifest-gen` | WS-A1 anti-drift generator CLI -- regenerates (or --check verifies) the ai/v1 verb-catalog manifest projection (ai/v1/tools.generated.json) from the live mios.toml [verbs.*] SSOT, via the pure... |
| `usr/libexec/mios/mios-ai-reset` | Wipes all non-persistent AI state (chat history, kanban, memory, and browser profiles) while preserving core configs and models to provide a clean slate for testing or new sessions. |
| `usr/libexec/mios/mios-ai-tag` | Codebase tagger -- writes a rich, structured AI header on every file. |
| `usr/libexec/mios/mios-app-default` | Mutates /etc/mios/mios.toml to switch the default application for a given type. |
| `usr/libexec/mios/mios-app-search` | Provides semantic search over the mios-apps inventory via the agent-pipe endpoint to resolve ambiguous natural-language queries into specific app metadata for agent-driven actions. |
| `usr/libexec/mios/mios-app-type` | Resolves an abstract application type (e.g. browser, editor) into a concrete app name using the [[desktop.app_types]] SSOT in mios.toml. |
| `usr/libexec/mios/mios-apps` | Provides a unified inventory of all launchable entities (Flatpaks, RPMs, Windows apps, shims, and service URLs) across all environments, used by agents to discover and target specific applications... |
| `usr/libexec/mios/mios-as-operator` | Executes commands in a fresh WSL login session as the operator user to bootstrap the full WSLg environment (Wayland, user-bus, and interop) required for GUI applications and Flatpaks to function... |
| `usr/libexec/mios/mios-autocenter` | Executes a polling loop to identify and center newly mapped windows (WSLg/Flatpak) by comparing current HWNDs against a pre-launch snapshot via the os_control executor to ensure correct placement of... |
| `usr/libexec/mios/mios-bench` | MiOS agentic-capability benchmark harness CLI. `score` (OFFLINE, pure): reads a trial-results JSON, prints the CLASSic rollup + pass@k / pass^k (tau-bench) via the tested mios_bench core. `run`... |
| `usr/libexec/mios/mios-blade` | The `mios blade` verb -- the day-2 face of the blade archetype (WS-BLADE). Writes the HOST tier (/etc/mios/role.conf) and re-runs role-apply, which detects the change and activates the new role... |
| `usr/libexec/mios/mios-bound-images-firstboot` | FBM first-boot bound-image provisioner. Reads [ai].firstboot_bound_images from mios.toml |
| `usr/libexec/mios/mios-build-driver` | Entry point for the MiOS-DEV build pipeline; executes the full multi-format build process (OCI, WSL, QEMU, etc.) and renders the interactive dashboard within a Windows-hosted terminal session. |
| `usr/libexec/mios/mios-build-status` | Provides a summary of the most recent build's status, log location, and success state by analyzing /var/log/mios/build-driver-*.log files and active build-driver processes. |
| `usr/libexec/mios/mios-build-tail` | Retrieves and streams the most recent raw build log from /var/log/mios or /tmp, used by agents to inspect real-time or historical build output from the mios-build-driver. |
| `usr/libexec/mios/mios-cache-clear` | Executes a safe, selective purge of non-essential OWUI, Hermes, and system cache data while preserving critical auth, config, and model assets to reset state without causing user lockouts or data... |
| `usr/libexec/mios/mios-cdi-detect` | Detects GPU hardware (NVIDIA, AMD, Intel) and generates corresponding CDI specification files in /run/cdi/ to enable containerized GPU access before the nvidia-cdi-refresh service. |
| `usr/libexec/mios/mios-cdp-fetch` | Fetches rendered text and title from a URL via the Chrome DevTools Protocol (CDP) on port 9222 to provide the agent with grounded, non-hallucinated DOM content instead of predicted text. |
| `usr/libexec/mios/mios-ceph-configure` | Automated client cache configuration utility for CephFS, rendering performance options into /etc/ceph/ceph.conf. |
| `usr/libexec/mios/mios-cephfs-provision` | Automated provisioning utility for CephFS user home subvolumes and path-scoped CephX keyrings. |
| `usr/libexec/mios/mios-chain-verify` | SEC-03 CLI that verifies the tamper-evident SHA-256 hash chain over the agent-plane `event` table. Reads every chained row (WHERE chain_hash IS NOT NULL) in chain_seq order via mios-pg-query's... |
| `usr/libexec/mios/mios-chrony-ptp-dropin` | Generates /etc/chrony.d/10-ptp.conf on first boot if /dev/ptp0 exists (PTP hardware present). |
| `usr/libexec/mios/mios-clevis-luks-gen` | Generates clevis LUKS TPM2 binding configuration from mios.toml [security.luks] SSOT. |
| `usr/libexec/mios/mios-codebase-index` | Comprehensive codebase discovery index -- harvests the AI-hint/header |
| `usr/libexec/mios/mios-codemode-api.py` | mios_tools -- the in-sandbox Code Mode tool API (WS-2). This module is the LOCAL Python API the model's generated code imports INSIDE the coderun-sandbox. |
| `usr/libexec/mios/mios-coderun` | Executes agent-provided bash or python snippets within a restricted bubblewrap sandbox, providing a safe, ephemeral execution environment with controlled network access and a private scratch... |
| `usr/libexec/mios/mios-coderun-broker` | Lightweight per-session Code Mode Unix socket broker listening on %t/mios-coderun-%i.sock and forwarding tool RPC requests to the host-side agent-pipe (/v1/dispatch) HTTP endpoint. |
| `usr/libexec/mios/mios-coderun-codemode` | Executes agent-supplied code snippets within a hardened, persistent Podman container sandbox to provide a "Code Mode" tool interface that reduces context window usage by replacing numerous function... |
| `usr/libexec/mios/mios-coderun-session` | Orchestrates the lifecycle of agent-specific coderun sandboxes by managing systemd user units, btrfs snapshots, and git stashes for project isolation and state recovery based on a unique session ID. |
| `usr/libexec/mios/mios-compact` | Compacts recent agent interactions, launch failures, and system logs into a timestamped markdown digest in /var/lib/mios/compacted/ to be ingested as an OWUI knowledge artifact for RAG. |
| `usr/libexec/mios/mios-computer-use` | Executes Linux/Wayland desktop interactions via RemoteDesktop portal, uinput, or WSL-delegated Windows control, providing a unified `cu_*` verb interface for remote/local UI automation and vision... |
| `usr/libexec/mios/mios-computer-use-server` | Provides a dual-protocol (MCP/A2A) and REST-compliant FastAPI server that exposes local desktop automation tools, window management, and input injection as a federated capability for the central... |
| `usr/libexec/mios/mios-conductor` | stub |
| `usr/libexec/mios/mios-configurator-launch` | Opens the unified MiOS Settings surface. PRIMARY target is the configurator embedded in the MiOS Portal at /configure on the `agent_pipe` port (probed with curl); only when the Portal is unreachable... |
| `usr/libexec/mios/mios-crawl` | Python script providing a thin client to the local crawl4ai service to fetch and convert web pages into LLM-ready markdown, used by agents to ground responses in actual content rather than search... |
| `usr/libexec/mios/mios-cron-director` | A cron-task scheduler that parses system and user rules from TOML files, executing commands via bash while optionally gating execution through a local LLM's YES/NO decision based on system state. |
| `usr/libexec/mios/mios-cron-schedule` | CLI tool for managing cron-director rules by translating human-readable intervals into cron expressions, storing prompt text in /var/lib/mios/cron-director/prompts, and updating... |
| `usr/libexec/mios/mios-cu-verify` | Visual Definition-of-Done tool for PC-CONTROL. Takes a screenshot and asks the vision model if a specified condition (e.g., "is the terminal open?") is met on screen. Returns {ok: bool, reasoning:... |
| `usr/libexec/mios/mios-cursor-apply` | Sets the X11 root-window default cursor via XDefineCursor to ensure consistent cursor themes across GTK4/Xwayland windows where explicit cursor names are missing, using settings from mios.toml. |
| `usr/libexec/mios/mios-cursor-ensure` | Ensures the global system cursor theme (Bibata) is correctly installed and linked in /usr/share/icons or ~/.local/share/icons based on available privileges to guarantee consistent cursor rendering... |
| `usr/libexec/mios/mios-daemon` | Consolidated MiOS core daemon that unifies log classification, refusal detection, and cron task evaluation into a single llama.cpp /v1-backed process, outputting a unified state.json for the OWUI... |
| `usr/libexec/mios/mios-dashboard-render-issue.sh` | bash Composites the MiOS dashboard into /etc/issue.d/30-mios.issue so it AI-related: /usr/libexec/mios/mios-dashboard-render-issu... |
| `usr/libexec/mios/mios-dashboard.sh` | MiOS live system dashboard shim. Forwards to the unified Python TUI. |
| `usr/libexec/mios/mios-day0-reset` | Purges volatile runtime data (sessions, tool_calls, knowledge, logs) from the pgvector agent DB (via parameterized mios-db --pg) plus OWUI's sqlite chats and filesystem caches, while preserving core... |
| `usr/libexec/mios/mios-db` | Unified MiOS shared-state CLI fronting the agent backends: PostgreSQL/pgvector for cross-cutting state (--pg), Open WebUI's SQLite webui.db (--owui), and local OpenAI-compat embeddings on... |
| `usr/libexec/mios/mios-directory-lookup` | Provides high-speed (<100ms) retrieval of the pgvector-cached directory map (parameterized pg via mios-db --pg-json) to allow agents to perform rapid file/directory lookups and navigation instead of... |
| `usr/libexec/mios/mios-discord-send` | Python script for sending deterministic Discord messages or DMs to specific users/channels, providing the orchestrator with real-time success/failure JSON results instead of hallucinated outcomes. |
| `usr/libexec/mios/mios-discord-status` | Diagnostic script for the Hermes-Agent Discord integration that validates token validity, API connectivity, and configuration completeness to help agents and operators troubleshoot Discord... |
| `usr/libexec/mios/mios-doc-distill` | Day-N+1 runner -- distils source comments into the manual and re-renders every derived section, refusing to touch a read-only tree so a booted immutable host no-ops instead of failing. |
| `usr/libexec/mios/mios-docgen` | A headless document generation engine using Pandoc and LibreOffice to convert markdown/text into office binaries (docx, pptx, xlsx, pdf) or perform format conversions, gated by the... |
| `usr/libexec/mios/mios-docs-index` | Generates a unified index of all system documentation (.md files) across MiOS directories to allow agents to discover and selectively load specific documentation into context via grep or direct path... |
| `usr/libexec/mios/mios-doctor` | A diagnostic tool for identifying system-level failures in MiOS, checking sudo permissions, hermes-agent status, and mount-namespace escapability to troubleshoot environment issues. |
| `usr/libexec/mios/mios-dotfiles` | The operator-facing `mios dotfiles` verb backend (ADR-0010) -- projects |
| `usr/libexec/mios/mios-dotfiles-render` | The GLOBAL runtime theme + dotfiles projector -- renders EVERY committed theme surface (the btop theme, oh-my-posh, quickshell, fastfetch, the app-shell CSS, the terminal OSC fallbacks) from the... |
| `usr/libexec/mios/mios-dup-report` | Value duplication reporter wrapper for MiOS resolved environment |
| `usr/libexec/mios/mios-enroll-secure-boot` | Enrolls the ublue/akmods Machine Owner Key (MOK) via mokutil to allow Secure Boot systems to load signed NVIDIA and ZFS kernel modules. |
| `usr/libexec/mios/mios-env-probe` | Captures and formats the system's hardware, service status, and configuration facts into brief, full, or machine-readable formats to provide the Hermes agent with deterministic environmental context. |
| `usr/libexec/mios/mios-env-snapshot` | Captures a clean-environment snapshot of resolved MIOS_* environment variables for lossless diffing. |
| `usr/libexec/mios/mios-everything` | A high-speed wrapper for the Voidtools Everything CLI that provides agents with sub-100ms access to the full Windows NTFS index for file discovery across all mounted drives. |
| `usr/libexec/mios/mios-find` | Provides high-speed fuzzy lookup against the cached environment inventory to resolve "launch <app>" requests into executable commands in <100ms, bypassing slow filesystem crawls. |
| `usr/libexec/mios/mios-finetune` | Python script for hardware-agnostic LoRA/SFT fine-tuning of the MiOS model; detects CUDA/ROCm/MPS/CPU to train a local adapter from the mios-finetune-dataset and exports it as a GGUF LoRA adapter for... |
| `usr/libexec/mios/mios-finetune-dataset` | A script to generate a supervised fine-tuning (SFT) JSONL dataset by distilling a teacher model's responses to live system verbs and intent schemas into a training corpus for the MiOS role model. |
| `usr/libexec/mios/mios-finetune-serve` | A Python server providing OpenAI-compatible and MiOS-native chat endpoints for fine-tuned LoRA adapters, used by the agent-pipe refiner to serve specialized models on any hardware via the... |
| `usr/libexec/mios/mios-firecrawl` | Python script to scrape web pages via the local Firecrawl API (port 3002) to produce clean, LLM-ready markdown, providing a high-quality alternative to crawl4ai for rendering news and article content. |
| `usr/libexec/mios/mios-flatpak` | Agent-facing JSON-wrapped CLI for managing flatpak packages (search, install, upgrade, run) providing structured output for automated lifecycle management and non-interactive installation. |
| `usr/libexec/mios/mios-flatpak-beta-migrate` | One-shot migration script that identifies Flatpaks from the flathub remote and reinstalls them from flathub-beta to update the origin while preserving user data. |
| `usr/libexec/mios/mios-flatpak-icon-sanitize` | Renames .svg files containing non-SVG data (e.g., PNGs) to .disabled-not-svg to prevent the WSLg weston compositor from crashing during RemoteApp list generation. |
| `usr/libexec/mios/mios-flatpak-init` | Initializes system-wide flatpak overrides at first boot to grant all flatpaks read/write access to standard XDG user directories and shared themes, ensuring persistent data access in bootc-compatible... |
| `usr/libexec/mios/mios-flatpak-install` | Non-interactive wrapper for `flatpak install` that forces `--noninteractive` and `--from` flags to prevent agent hangs, while ensuring new apps inherit MiOS system-wide XDG override policies. |
| `usr/libexec/mios/mios-flatpak-overrides-apply` | Executes `flatpak override` to apply global theme, portal, and cursor settings from `mios.toml` to all flatpak applications, ensuring consistent UI styling across the system. |
| `usr/libexec/mios/mios-flatpak-preflight` | Validates if a flatpak app can successfully bootstrap its sandbox by running a probe command and checking for specific stderr signatures (GPU, portal, or D-Bus errors) to provide a synchronous... |
| `usr/libexec/mios/mios-forgejo-runner-firstboot.sh` | bash Run `forgejo-runner register` once so /srv/mios/forge-runner/.runner AI-related: /usr/libexec/mios/mios-forgejo-runner-fir... |
| `usr/libexec/mios/mios-freeipa-enroll.sh` | bash Bash oneshot run by mios-freeipa-enroll.service that joins the host to a FreeIPA domain via ipa-client-install; gated on /etc/mios/i... |
| `usr/libexec/mios/mios-gen-role-system` | Generates unified, SSOT-driven SYSTEM prompts for MiOS agent roles by merging mios.toml configs, live verb/skill catalogs, and A2A peer surfaces into a single source for Modelfile and agent-pipe... |
| `usr/libexec/mios/mios-generate-icons` | Generates the MiOS XDG icon theme index.theme and SVG icon stubs |
| `usr/libexec/mios/mios-gpu-passthrough` | Syncs Quadlet container configurations with live CDI specifications in /run/cdi/ to automatically map NVIDIA, AMD, or Intel GPUs to background AI service Quadlets (mios-llm-light, vLLM heavy lanes)... |
| `usr/libexec/mios/mios-gui` | A wrapper script that resolves and launches flatpak applications via shims, exact IDs, or fuzzy matches, then BOUNDED-polls the OS-control executor for a newly-mapped window to honestly confirm the... |
| `usr/libexec/mios/mios-gui-launch` | A wrapper script that launches Linux GUI applications via WSLg by enforcing required environment variables (WAYLAND_DISPLAY, XDG_CURRENT_DESKTOP, XDG_SESSION_TYPE), detaching the process, and logging... |
| `usr/libexec/mios/mios-handoff` | Migrates active session state, tool outputs, and context from a large model to a smaller/local model by serializing the A2A-context blackboard and dispatching a TAKE-OVER frame to a target peer or... |
| `usr/libexec/mios/mios-hardcode-lint` | Enforcement gate for the NO-HARDCODE law (Architectural Law 7). Read-only repo scan that FAILS on three regression classes the law forbids: (1) a literal date/timestamp or dated attribution in... |
| `usr/libexec/mios/mios-hermes-browser` | Launches and manages the ChromeDev flatpak instance on port 9222, providing a dedicated, isolated profile for the Hermes-Agent to perform CDP-based browser actions like navigation and screenshots. |
| `usr/libexec/mios/mios-hermes-dashboard-auth-stub` | A shim script that injects a minimal Python stub for the missing `hermes_cli.dashboard_auth` package to prevent `hermes-dashboard.service` from crash-looping due to a broken upstream import in the... |
| `usr/libexec/mios/mios-hermes-discord-reactions-patch` | Python script that patches gateway/platforms/discord.py to inject a multi-stage emoji progression (📡, 🧠, 🛠️, ⏳) into Discord messages to provide operators with visual feedback on the agent's... |
| `usr/libexec/mios/mios-hermes-firstboot` | Initializes the Hermes gateway and web-ui components by generating /etc/mios/hermes/api.env and seeding /var/lib/mios/hermes/config.yaml based on mios.toml configurations during first boot. |
| `usr/libexec/mios/mios-hermes-init-hook` | Python hook that executes mios-env-probe on the first turn of a session to inject a system environment snapshot into the LLM context, providing the agent with initial awareness of the host... |
| `usr/libexec/mios/mios-hermes-soul-sync` | Syncs the core hermes-soul.md identity file from system shares to the gateway-service home AND every interactive operator ~/.hermes home, so the agent's persona stays consistent across both the... |
| `usr/libexec/mios/mios-hermes-tail` | Tailer script that parses hermes-agent.service logs to extract tool-calls and sub-agent tasks into /var/lib/mios/hermes-tail/latest.json, providing the real-time status bridge for the OWUI... |
| `usr/libexec/mios/mios-host-launch` | Wraps host GUI binaries (e.g., gnome-software) to inject the operator's session environment (DISPLAY, WAYLAND_DISPLAY, DBUS_SESSION_BUS_ADDRESS) via systemd-run when invoked by service-level agents. |
| `usr/libexec/mios/mios-html` | A shim script that resolves and opens the mios.html configurator in the operator's default browser via a WSL UNC path, mapping "configurator" and "settings" commands to the UI for editing mios.toml. |
| `usr/libexec/mios/mios-ingest` | Python script for offline ingestion of local files (md, txt, rst, org) into the Postgres+pgvector knowledge table via parameterized mios-pg-query (extended-protocol bound params), utilizing... |
| `usr/libexec/mios/mios-installer` | Unified cross-platform package manager entry point that abstracts winget, dnf, and flatpak into a single interface for installing, searching, and listing software across Windows and Linux... |
| `usr/libexec/mios/mios-keyring-autounlock` | A dual-mode helper that unlocks the gnome-keyring-daemon using credentials from mios.toml, supporting both proactive systemd startup and D-Bus activation to provide libsecret and xdg-desktop-portal... |
| `usr/libexec/mios/mios-kg` | CLI for the PostgreSQL/pgvector Personal Knowledge Graph (PKG) that resolves ambiguous user phrases into concrete app targets via the kg_lookup() helper in the agent-pipe. WS-A3: every read + write... |
| `usr/libexec/mios/mios-knowledge-add` | Registers markdown files or directories into the OWUI `file` table and links them to a named Knowledge collection to enable RAG capabilities for the MiOS-Agent model via meta.knowledge binding. |
| `usr/libexec/mios/mios-knowledge-search` | Python shim providing sub-agents with a tool to query OWUI RAG knowledge collections via the /api/v1/retrieval/process/query endpoint, with a fallback to local pgvector storage if the OWUI API is... |
| `usr/libexec/mios/mios-lan-status` | Checks and configures Windows-side port forwarding for MiOS services (e.g., Open WebUI, mios-llm-light) to ensure LAN/Wi-Fi accessibility from the host machine via a PowerShell helper script. |
| `usr/libexec/mios/mios-launch` | Universal launcher that resolves and executes applications across multiple environments (internal services, URLs, Windows binaries, MiOS shims, Linux GUI apps, and PATH binaries) based on a... |
| `usr/libexec/mios/mios-launcher-daemon` | Broker service that provides a Unix socket for the mios-hermes agent to execute shell commands within the operator's user context, enabling GUI apps and Windows .exe interop via the operator's... |
| `usr/libexec/mios/mios-living-wallpaper` | Daemon script to manage the GPU-accelerated animated living wallpaper on Linux (WBRAND-05). |
| `usr/libexec/mios/mios-lldap-seed` | Projects Postgres account table rows into lldap bootstrap format. |
| `usr/libexec/mios/mios-locate` | Linux-side filesystem search shim that provides a unified interface for agents to locate files/directories using plocate, locate, or find, supporting filtering by count, extension, type, and specific... |
| `usr/libexec/mios/mios-login-account` | Resolves the DB-driven LOGIN account the dashboards advertise -- the globally-controlled account SSOT (pgvector), NOT the operator DISPLAY name ([user].name). Shared by the Linux dashboard and the... |
| `usr/libexec/mios/mios-lsfs` | LSFS-01 Semantic Filesystem CLI dispatcher for mount/create/write/search/rollback/share verbs. |
| `usr/libexec/mios/mios-luks-enroll` | Enrolls LUKS keys using systemd-cryptenroll or clevis based on mios.toml [security.disk_encryption] SSOT. |
| `usr/libexec/mios/mios-manual` | The generative documentation CLI. Builds the comment corpus ledger that makes "this comment's knowledge landed in a doc" a machine-checkable fact, and reports the census that drives the documentation... |
| `usr/libexec/mios/mios-map` | A shim script that constructs and opens Google Maps URLs for locations or directions, providing a single-call interface for agents to bypass complex URL construction and browser-launch logic. |
| `usr/libexec/mios/mios-mcp-enable-tier0.sh` | bash mios-mcp-enable-tier0.sh -- OPERATOR-RUN activation of the Tier-0 MCP servers AI-related: /usr/libexec/mios/mios-mcp-enable-tier0.... |
| `usr/libexec/mios/mios-mcp-server` | Provides a Model Context Protocol (MCP) stdio server that exposes the MiOS [verbs.*] catalog as tools and resources for local agents (Hermes, OpenCode) to execute system actions via the agent-pipe. |
| `usr/libexec/mios/mios-md` | A CLI shim that launches a local browser-based markdown editor and live previewer, converting local files or inline strings into a URL-encoded state for the standalone viewer at... |
| `usr/libexec/mios/mios-mdev-define-gen` | Generates mdevctl persistent configuration JSON drop-ins for SR-IOV VFs and vendor mediated devices from mios.toml [mdev] SSOT. |
| `usr/libexec/mios/mios-metal-mesh-gen` | Generates Headscale/Tailscale mesh configuration from mios.toml [metal.mesh] SSOT. |
| `usr/libexec/mios/mios-metal-vfio-gen` | Generates vfio-pci binding kargs/modprobe configuration from mios.toml [metal] SSOT. |
| `usr/libexec/mios/mios-micro-llm` | Thin client for the resident qwen3:1.7b model on the mios-llm-light /v1 lane, providing low-latency (<500ms) classification for mios-log-watcher, mios-cron-director, and other system agents. |
| `usr/libexec/mios/mios-model-router` | Acts as the primary OpenAI-compatible entry point and load balancer for MiOS, routing requests to specific hardware lanes (dGPU, iGPU, CPU) based on performance profiles and managing the 17K-token... |
| `usr/libexec/mios/mios-models` | FBM CLI. `mios models list` prints the DECLARED set from the layered [ai].firstboot_models SSOT joined against what is on disk (it used to glob the filesystem and never open the TOML at all, so it... |
| `usr/libexec/mios/mios-models-firstboot` | FBM first-boot large-model provisioner. Reads [ai].firstboot_models from the layered mios.toml, downloads each GGUF with resume, VERIFIES its sha256 (streamed, chunked) and discards the part file on... |
| `usr/libexec/mios/mios-new` | Command-line utility to scaffold new MiOS files from canonical templates, interpolating names, dates, and settings. |
| `usr/libexec/mios/mios-oci-delta-apply` | stub |
| `usr/libexec/mios/mios-oci-delta-service.sh` | GAP-5 (T-050) edge distribution wrapper |
| `usr/libexec/mios/mios-open-url` | Resolves and launches a URL in the MiOS-defined default browser or a specified override by resolving mios.toml entries and dispatching via mios-gui to the operator's WSLg desktop session. |
| `usr/libexec/mios/mios-os-control` | The primary entrypoint for MiOS OS-control, providing an OpenAI-compliant tool schema, verb catalog, and skill discovery system derived from mios.toml to allow LLMs to execute system operations... |
| `usr/libexec/mios/mios-os-recipe` | Executes allowlisted, shell-escaped OS-specific commands defined in mios.toml, handling cross-platform path conversion and security-hardened parameter filtering for MiOS system operations. |
| `usr/libexec/mios/mios-oscap-gate` | Severity-gated pass/fail parser for an OpenSCAP results file (ARF or XCCDF results XML), the decision half of the BOOT-02 scan-only build gate. Counts rule-result/result=fail entries whose rule... |
| `usr/libexec/mios/mios-oscontrol-health` | Probes the MiOS Windows OS-control plane (in-session executor :11437 via the |
| `usr/libexec/mios/mios-owui-apply-knowledge` | Registers the authoritative MiOS knowledge corpus from FHS paths into the Open WebUI database, linking specific files and their content to the MiOS-Agent model row for RAG-enabled context. |
| `usr/libexec/mios/mios-owui-apply-suggestions` | Clears hardcoded prompt_suggestions from the Open WebUI database to ensure the system defaults to dynamic, LLM-generated suggestions based on the current session's context and locale. |
| `usr/libexec/mios/mios-owui-apply-system-prompt` | Python script that synchronizes the Open WebUI database with the MiOS-managed system prompt for the "MiOS-Agent" model, ensuring the agent's persona and capabilities are correctly injected into the... |
| `usr/libexec/mios/mios-owui-apply-websearch` | Configures Open WebUI's web-search feature by updating the webui.db SQLite database to enable search augmentation and point the search engine to the local SearXNG instance on the `searxng` port. |
| `usr/libexec/mios/mios-owui-bootstrap-admin` | Bootstraps the initial Open WebUI admin account by injecting a user into the SQLite database if empty, resolving credentials from mios.toml and secrets.env to ensure operator access during first-boot. |
| `usr/libexec/mios/mios-owui-install-computer-use` | Registers the MiOS Computer Use tool into webui.db to provide the LLM with direct desktop control, vision grounding, and doc-gen capabilities via typed tool_calls instead of generic shell commands. |
| `usr/libexec/mios/mios-owui-install-pipe` | Registers the MiOS Agent pipe and anti-meta filters into the Open WebUI database, ensuring the "MiOS AI" model is available in the UI dropdown and automatically configured for the agent's interaction... |
| `usr/libexec/mios/mios-owui-install-tools` | Registers the MiOS Verbs toolset into the webui.db database to provide the LLM with native typed tool_calls for actions like launch_app and mios_find, bypassing terminal-mediated execution. |
| `usr/libexec/mios/mios-passport` | CLI tool for managing Ed25519 identity keys for MiOS agents, used to provision, rotate, and verify signed passport envelopes for authenticated agent-DB operations like tool calls and skill... |
| `usr/libexec/mios/mios-pc-control` | Provides a Windows-host computer-use interface for MiOS-Agent via PowerShell scripts to perform screen capture, mouse/keyboard input, and window management on WSL2-hosted systems. |
| `usr/libexec/mios/mios-pc-vision` | Provides vision-based grounding for the PC-CONTROL agent by processing screenshots and natural language queries via a local VLM to return precise JSON coordinates for UI element interaction. |
| `usr/libexec/mios/mios-pg-query` | A standalone Python-based PostgreSQL wire-protocol client used by the MiOS agent plane to execute SQL directly over a loopback TCP socket when psql or podman access is restricted. Two modes: legacy... |
| `usr/libexec/mios/mios-pgvector-major-upgrade` | Boot-time guard that lets the pgvector image float across PostgreSQL MAJORS without stranding the agent datastore -- detects a PG_VERSION/image-tag major mismatch, logical-dumps the old cluster with... |
| `usr/libexec/mios/mios-policy-arbiter` | WS-9 out-of-process HITL policy-arbiter SERVICE. A tiny stdlib HTTP service (no deps, loopback) that answers the agent-pipe's HITL arbiter client (_hitl_arbiter_verdict): POST / with {verb,tier,args}... |
| `usr/libexec/mios/mios-powershell` | Executes PowerShell scripts on Windows via pwsh.exe or powershell.exe, providing a first-class `powershell_run` verb for agents to interact with Windows cmdlets, registry, and COM objects with... |
| `usr/libexec/mios/mios-ps` | Displays a list of all MiOS containers by reading the root-owned podman-ps.json snapshot, allowing non-root users to view container status and images without direct podman socket access. |
| `usr/libexec/mios/mios-rag` | Python tool for RAG retrieval that embeds MiOS documentation into Postgres+pgvector (table mios_rag) via nomic-embed-text to provide context to agents during the agent-pipe enrich stage. WS-A3: the... |
| `usr/libexec/mios/mios-rechunk` | GAP-5 -- post-build binary diff between new OCI layer blobs and prior manifest |
| `usr/libexec/mios/mios-registry` | WS-A17 read-mostly local package-registry CLI. `list` prints the materialized package index, `verify` checks the committed registry.json is in sync with the live SSOT (exit 1 on drift, used by the... |
| `usr/libexec/mios/mios-remember` | Active-memory write interface for agents to store/update/delete durable facts in the Postgres+pgvector agent_memory table, scoped global/agent:<name>/conversation:<id>. WS-A3: every write is... |
| `usr/libexec/mios/mios-remote` | Executes the Claude Code CLI with remote-control mode enabled to allow mobile-to-host session syncing via official Anthropic OAuth polling, providing a persistent mobile-driven development loop for... |
| `usr/libexec/mios/mios-resolve-latest` | Always-latest container image resolver. Reads the sidecar image refs from the mios.toml [image.sidecars] SSOT (never a hand-mirrored list), resolves each to its registry digest, and appends the... |
| `usr/libexec/mios/mios-restart` | Executes smart restarts for MiOS services, handling specific logic for Podman Quadlets (systemctl-based), standard systemd units, and hermes-agent soft restarts to clear in-process skill caches. |
| `usr/libexec/mios/mios-sandbox-exec` | Executes agent-generated code within a bubblewrap-based userspace sandbox, enforcing filesystem isolation, resource limits (cgroups), network restrictions and (T-230) a SECCOMP syscall filter based... |
| `usr/libexec/mios/mios-scheduled-research` | Executes scheduled research tasks by processing prompts through the agent-pipe with a bounded research path to prevent resource exhaustion, then reporting results to Discord via mios-discord-send. |
| `usr/libexec/mios/mios-screenshot` | A bash wrapper for capturing the primary Windows monitor as a PNG via mios-pc-control, supporting optional --open and --clipboard flags to provide a unified interface for remote screen capture. |
| `usr/libexec/mios/mios-seccomp-filter` | Emits the compiled seccomp cBPF program that mios-sandbox-exec hands bwrap on --seccomp FD. Reads the denylist and action from mios.toml [sandbox] through the layered resolver, builds the program... |
| `usr/libexec/mios/mios-shell-session` | SHELL-01 runner for the persistent PTY substrate. Drives tmux with the pure protocol in mios_pipe.routing.pty: `exec` sends one nonce-framed command into the chat's session (creating it under the... |
| `usr/libexec/mios/mios-show-image` | Executes a SearXNG image search and opens the top result's URL in the system's default browser, optionally moving the resulting window to a specified screen position. |
| `usr/libexec/mios/mios-shutdown` | Hardens Day-N shutdown loops by detecting dirty working tree edits (+1 compilations), presenting a formatted git diff preview, and offering choices to carry-forward, include in Day-N updates/builds,... |
| `usr/libexec/mios/mios-skill-clone` | Copies system-provided Hermes skills from /usr/share/mios/hermes/skills/ to the agent's writable home directory to allow local modification and overriding of system-wide skill definitions. |
| `usr/libexec/mios/mios-skills` | CLI tool for mining repetitive tool_call sequences into typed-verb DAGs in parameterized Postgres/pgvector, providing a unified skill catalog for mios-agent-pipe, Hermes, and OpenCode to share... |
| `usr/libexec/mios/mios-smart-resize` | Performs 3-constraint spatial normalization for VLM input image resizing and records output dimensions. |
| `usr/libexec/mios/mios-sriov-init` | Initializes SR-IOV Virtual Functions on Physical Functions (PFs) by parsing /etc/mios/sriov.conf and writing to /sys/bus/pci/devices/ paths during early boot to enable multi-device networking. |
| `usr/libexec/mios/mios-ssh-dev-cmd` | Prints the LIVE, copy-pasteable "SSH from your host into the code-server dev container at the MiOS root tree" command. Single source of truth shared by the Linux dashboard (mios-dashboard.sh) and the... |
| `usr/libexec/mios/mios-ssot-regen` | One-command regeneration of every mios.toml-derived SSOT projection the drift-gate verifies |
| `usr/libexec/mios/mios-stage-oci-archive` | Stages built mios oci-archive tarball to /mnt/mios-repo/mios-latest.tar for tools/install.sh (AGY-152) |
| `usr/libexec/mios/mios-steamcmd` | A wrapper for Valve's SteamCMD providing a unified interface for game installation, updates, and status checks via both GUI-based URI dispatching and headless SteamCMD commands for server hosting. |
| `usr/libexec/mios/mios-stresstest` | A developer tool to stress-test the agent-pipe chat endpoint via a Python harness, used to validate system stability, concurrency limits, and latency under load. |
| `usr/libexec/mios/mios-suggestion-refresh` | Refreshes OWUI's ui.prompt_suggestions by analyzing MiOS state (kanban, daemon nudges, recent intents) via a refine model to generate 5-28 context-aware starter chips for the operator. |
| `usr/libexec/mios/mios-summarize` | Provides tiered summarization (L0/L1/L2) via a local LLM on the CPU-bound light lane to generate concise abstracts and structured overviews for efficient document indexing and navigation. |
| `usr/libexec/mios/mios-swarm-pack-firstboot` | Parses mios.toml to arm concurrent llama-server instances in swarm mode, enforcing vram_budget_mb limits to prevent OOM on shared GPUs and generating per-worker environment files in /run/mios/swarm/. |
| `usr/libexec/mios/mios-sync-theme` | Regenerates the /etc/mios/theme/ bridge (theme.json + mios-theme.css) |
| `usr/libexec/mios/mios-sync-to-root` | Applies the code-server / war-room workspace (an ext4 replica of the MiOS |
| `usr/libexec/mios/mios-sync-toml` | Projects the canonical-owned, drift-prone sections of mios.toml into the two |
| `usr/libexec/mios/mios-sys-env` | Provides a shared, persistent snapshot of hardware, services, and app inventory in pgvector, allowing agents to query current system state via the `sys_env` table instead of performing live probes. |
| `usr/libexec/mios/mios-system-status` | Provides a single JSON blob of hardware (CPU, GPU, RAM, Disk), service status, and model data (via the mios-llm-light API) to the `system_status` verb to prevent the LLM from hallucinating system... |
| `usr/libexec/mios/mios-sysview` | Provides a unified system inspection tool for agents to query journalctl, process lists, and podman containers by abstracting complex command construction and flag validation into a single interface. |
| `usr/libexec/mios/mios-template-engine` | Thin shim delegating template rendering to the mios-new canonical generator, preserving the legacy <kind> <target_filepath> [description] contract. |
| `usr/libexec/mios/mios-text-edit` | Provides a robust, filesystem-direct text editing primitive for agents to view, create, and mutate files via atomic str_replace or line-based insertion, bypassing unreliable UI-driven keystroke... |
| `usr/libexec/mios/mios-theme-render` | Deprecated compatibility alias wrapper. Delegates execution to mios-dotfiles-render. |
| `usr/libexec/mios/mios-toml-get` | Thin shell-facing CLI over the shared usr/lib/mios/mios_toml.py resolver, so bash scripts + `python3 - <<PY` heredocs stop re-rolling their own awk/regex mios.toml scanners (which mishandle... |
| `usr/libexec/mios/mios-tool-clone` | Copies a system-shipped MiOS shim from /usr/libexec/mios/ to /usr/local/bin/ to create a mutable version that overrides the default on PATH, allowing agents to iteratively modify and improve existing... |
| `usr/libexec/mios/mios-tool-search` | A thin client for the agent-pipe tool-search endpoint that performs RAG-based retrieval of the verb catalog to resolve ambiguous intents via semantic similarity scoring. |
| `usr/libexec/mios/mios-ttyd-expose` | Configures and toggles the Tailscale HTTPS reverse proxy for the ttyd terminal service on port 7681, enabling secure mobile access via the Tailnet based on the [ttyd].tailnet_expose setting in... |
| `usr/libexec/mios/mios-ttyd-launch` | Parses MIOS_TTYD_* environment variables and mios.toml configurations to construct and execute the ttyd web terminal process for either bash or powershell shells on specific ports. |
| `usr/libexec/mios/mios-userdb-render` | Projects Postgres account table rows into systemd userdb JSON drop-ins. |
| `usr/libexec/mios/mios-v2v-import` | Virt-V2V guest import wrapper resolving storage pool, network, and output format from mios.toml [virt.v2v] SSOT. |
| `usr/libexec/mios/mios-vendor-refresh` | One-command offline asset vendor refresh tool. Re-pulls vendored k3s, cursors, fonts, and wheels at LATEST tag resolution. |
| `usr/libexec/mios/mios-verify-launch` | Synchronously queries the mios-daemon-agent to verify if an app actually launched via a live window/process probe and historical failure logs, preventing agents from reporting false successes. |
| `usr/libexec/mios/mios-version-lint` | NO-HARDCODE-VERSION law enforcement (Law 7 / ADR-0003). Scans tracked source for hand-pinned version literals in URLs, pip/npm pins, and @sha256 image digests. |
| `usr/libexec/mios/mios-viking` | Provides a tiered, read-only virtual filesystem (viking://) for agents to navigate local skills, knowledge, and memory via L0 (abstract), L1 (overview), and L2 (raw) levels to manage context window... |
| `usr/libexec/mios/mios-web-extract` | Python utility to fetch a URL and strip HTML noise (scripts, styles, nav) to return raw, readable text for grounding agent responses on actual web content rather than search snippets. |
| `usr/libexec/mios/mios-web-search` | Python backend for the web_search verb that queries a local SearXNG instance using concurrent fan-out (RAG-Fusion) to provide agents with real-time, grounded data for facts, weather, and news. |
| `usr/libexec/mios/mios-webtools-firstboot.sh` | Build-if-missing bootstrap for the mios-webtools container images |
| `usr/libexec/mios/mios-win-scan` | Wine-free native enumerator of the REAL Windows host's installed apps + games, read straight off the drvfs /mnt mount (NO .exe execution) so the inventory is correct even when WSL-interop is hijacked... |
| `usr/libexec/mios/mios-winaccounts-render` | Projects Postgres account table rows into Windows accounts manifest JSON. |
| `usr/libexec/mios/mios-window` | A title-pattern-driven wrapper for mios-pc-control that allows agents to perform window operations (center, focus, move, resize) using human-readable titles instead of raw handles. |
| `usr/libexec/mios/mios-window-active` | Provides a JSON-formatted status of a specific application's window state, used by MiOS Agents to verify if a process is actually visible and presented to the operator rather than just running in the... |
| `usr/libexec/mios/mios-windows` | Provides a bridge for the agent to execute Windows-side commands, launch GUI applications, or run elevated PowerShell scripts via WSL interop or Tailscale SSH from within the WSL2 environment. |
| `usr/libexec/mios/mios-winget` | Wraps winget.exe via WSL interop to provide a unified JSON-structured interface for MiOS agents to search, install, upgrade, and manage Windows-side packages from the Linux-side agent stack. |
| `usr/libexec/mios/mios-wsl-flatpak-export-sync.sh` | Mirror flatpak's `.desktop` + icon exports into the system XDG dirs so |
| `usr/libexec/mios/mios-wsl-flatpak-heal` | Ensures the flatpak-portal and xdg-desktop-portal services are active and responsive on the user bus to prevent sandbox credential failures in WSL2 environments. |
| `usr/libexec/mios/mios-wslg-env-import` | Injects WSLg display, Wayland, and PulseAudio environment variables into the systemd --user manager and D-Bus activation environment to ensure GUI applications and Flatpaks can reach the WSLg... |

<!-- derived from the AI-hint headers of 210 file(s) matching usr/libexec/mios/mios-* -->
<!-- /MIOS-GEN:index:usr/libexec/mios/mios-* -->

## Generators and repo tooling (`tools/`)

Everything that projects the SSOT into a derived surface. If a file in the tree
is generated, its generator is here.

<!-- MIOS-GEN:index:tools/*.py -->
| File | What it is |
|---|---|
| `tools/ascii-sweep.py` | A one-shot utility to normalize MiOS-owned text by replacing non-ASCII typographic characters and emojis with ASCII equivalents to ensure consistent... |
| `tools/audit-image-provisioning.py` | Post-build image-audit validator asserting provisioning status (AGY / T-286). |
| `tools/audit-version-literals.py` | Inventories every version token in the repo and classifies it as SSOT-definition, SSOT-derived placeholder, or hardcoded literal, emittin... |
| `tools/check-blade-coverage.py` | Drift gate for the blade ACTIVATION axis. |
| `tools/check-comment-lex-equivalence.py` | Differential parity check asserting native mios-comment-lex binary and Python lexer produce identical sha12 sets. |
| `tools/check-comment-ratchet.py` | Drift check 155 check_comment_ratchet -- asserts measured comment metrics do not exceed ceiling values. |
| `tools/check-container-names.py` | Drift gate for unmappable container names. |
| `tools/check-credential-literals.py` | Law-11 extension gate: fails any NEW credential literal baked into a world-readable systemd unit or Quadlet (Environment=...PASSWORD/S... |
| `tools/check-daemon-governor.py` | Structural governor-coverage gate for mios-daemon: asserts every autonomous *_loop consults the host-pressure gate, that the SSOT [daemon]... |
| `tools/check-doc-ratchet-monotone.py` | Drift check 156 check_doc_ratchet_monotone -- asserts ceiling values in mios.toml are <= recorded floor values. |
| `tools/check-firstboot-provisioners.py` | Drift gate for the first-boot provisioner triples (FBM T-200/T-202). |
| `tools/check-fleet-safety.py` | Drift gate for hazards that are SAFE on one node and dangerous above it. A MiOS-Mini fleet is 2-6 boxes, so a config that only works standalone is a defect waiting for the operator to add a peer.... |
| `tools/check-manual-links.py` | Link-integrity gate for the shipped docs. |
| `tools/check-module-length.py` | Module-size ratchet for the agent-pipe extraction (drift check 149). |
| `tools/check-no-generated-prose-in-resolvers.py` | Drift check 157 check_no_generated_prose_in_resolvers -- asserts zero AI-hint: and zero MIOS_UNITS_*_COMMENT= in globals.sh/ps1. |
| `tools/check-node-pool.py` | Drift gate for the fan-out pool. [nodes.*] is dispatched by capacity behind per-lane and per-endpoint semaphores, so a node that repeats another... |
| `tools/check-port-fallbacks.py` | Drift gate for Law 7 at the point it actually bites -- a MIOS_PORT_<KEY> paired with a literal that disagrees with [ports].<key>. |
| `tools/check-ports-bound.py` | Drift gate for allocated-but-unbound ports. |
| `tools/check-redact-coverage.py` | DURA-02 persist-redaction coverage gate: asserts every table in postgres/schema-init.sql is classified in exactly one of [security.redact]... |
| `tools/check-resolver-twin.py` | Drift check helper to verify resolver twin equivalence between mios_toml.py and userenv.sh. |
| `tools/check-role-ssot.py` | Drift gate for the blade ROLE axis -- Law 9 applied to the one value that decides what an image is. |
| `tools/check-schema-consumers.py` | Drift gate for dead schema. Every table in usr/share/mios/postgres/schema-init.sql must have at least one non-doc consumer in the tree --... |
| `tools/check-service-urls.py` | Drift gate for service addressing. Every numeric [ports] key must resolve to exactly one canonical address -- either a [urls] entry that temp... |
| `tools/check-ssot-consumer-keys.py` | Drift gate for the SSOT<->consumer contract. Shipped Python reads config as _toml_section("<table>").get("<key>"); this asserts that <t... |
| `tools/check-tasks-status-parity.py` | Drift gate for a lying roadmap. TASKS.md carries every task twice -- once as a row in the summary table and once as a `**Status:**` li... |
| `tools/check-unit-projection.py` | Drift gate for the [units] projection debt register. |
| `tools/compile-dashboard-binary.py` | MiOS dashboard binary compiler |
| `tools/compile-templates.py` | Golden round-trip compiler for templates -- verifies all templates parse cleanly. |
| `tools/gen-pipe-boundary-manifest.py` | Generates a machine-readable module-boundary manifest for the agent-pipe DI contract. |
| `tools/generate-adr-index.py` | Generates the repo-root ADR.md breadcrumb from the front-matter of usr/share/doc/mios/adr/NNNN-*.md (T-265). |
| `tools/generate-ai-manifest.py` | Parses Markdown files and metadata blocks to generate a JSON manifest of the project structure, providing agents with a searchable index of documentation, knowle... |
| `tools/generate-blade-dropins.py` | Generate systemd capability drop-in files, k3s nodeSelectors, and Pacemaker location rules from the mios.toml [blade.requires] SSOT (AGY-1595). |
| `tools/generate-blade-karg.py` | Generate usr/lib/bootc/kargs.d/05-mios-blade.toml from the mios.toml [blade].type SSOT, so the karg role-apply already parses has a Law-8 pr... |
| `tools/generate-cargo-manifests.py` | Generator that projects tools/native/Cargo.toml from mios.toml [meta].mios_version SSOT. |
| `tools/generate-cockpit-conf.py` | Renders etc/cockpit/cockpit.conf from usr/share/mios/mios.toml SSOT |
| `tools/generate-cosign-policy.py` | Renders usr/lib/containers/policy.json from usr/share/mios/mios.toml [security.sigstore] SSOT |
| `tools/generate-egress-firewall.py` | Generate the agent OUTBOUND egress nftables ruleset (#54 zero-trust federation). |
| `tools/generate-ipa-enroll-env.py` | Renders etc/mios/ipa-enroll.env from usr/share/mios/mios.toml [identity.ipa] SSOT |
| `tools/generate-manual.py` | A generation tool to compile and structure the complete 50-chapter MiOS User Manual into a single All-in-One file, cleaning up modular directories. |
| `tools/generate-mini-vs-hosted.py` | GENERATES usr/share/doc/mios/reference/mini-vs-hosted.md -- the systematic, surface-by-surface comparison of a MiOS-Mini seat against a ... |
| `tools/generate-pipeline-index.py` | ) or line_str.startswith("# AI-related:"): continue if line_str.startswith("#") and not line_str.startswith("#!"): |
| `tools/generate-pod-quadlets.py` | Generate .pod Quadlets from the mios.toml [pods.*] co-resident groups (WS-7 pods-as-SSOT). |
| `tools/generate-uki-cmdline.py` | Flattens usr/lib/bootc/kargs.d/*.toml drop-ins into usr/lib/kernel/cmdline SSOT |
| `tools/journal-sync.py` | Parses legacy Markdown-based memory logs and synchronizes them into structured JSONL format for the MiOS memory system, extracting timestamps, agent IDs, thoughts, and actions. |
| `tools/lib/generate-build-scripts.py` | Generates a consolidated markdown reference of all build scripts in execution order, used by agents to map the MiOS build pipeline, i... |
| `tools/lib/generate-sbom.py` | Parses mios.toml to generate MiOS-SBOM.csv, aggregating package metadata, Quadlet image references, and environment defaults to provide a comp... |
| `tools/lib/path-refactor.py` | Refactors hardcoded MiOS system paths into environment variable constants (e.g., ${MIOS_LOG_DIR}) in configuration files while preserving comm... |
| `tools/lib/quote-mios.py` | A utility script that uses regex to wrap the "MiOS" proper noun in single quotes in documentation and config files to ensure legal-attribution co... |
| `tools/pipe-parity-check.py` | Drift check helper for verifying surface parity and one-way imports. |
| `tools/provision-agent-mtls.py` | Provision the MiOS agent mTLS PKI (#54 zero-trust federation): self-signed CA + agent cert/key. |
| `tools/refresh-env.py` | Syncs .ai-environment.json with .vscode/settings.json to synchronize editor font preferences and update the environment's last_refresh timestamp for consistent UI/UX across tools. |
| `tools/render-desktop.py` | Generates usr/share/applications/*.desktop files from SSOT ports and [desktop.launchers] table. Zero hardcoded port literals; --check is the drift gate. |
| `tools/render-globals.py` | Generates automation/lib/globals.sh and globals.ps1 IN FULL from mios.toml -- they are 100% generated artefacts with zero hand-written constants ... |
| `tools/render-ports.py` | Renders the flat [ports] projection from the [ports.categories] numbering SSOT -- every port is derived as base + index*stride, so an operator reta... |
| `tools/standardize-docs.py` | A maintenance script that enforces uniform legal headers and footers across all .md files in the specs/ directories to ensure consistent ownership metadata and documentation links. |
| `tools/sync-bootstrap.py` | Law 15 repo sync. Mirrors the surfaces mios.toml [bootstrap.sync] declares from mios.git into mios-bootstrap.git, and mirrors the SSOT tables it ... |
| `tools/sync-wiki.py` | Updates metadata in wiki markdown files by injecting current version and RAG sync timestamps into JSON blocks to ensure documentation reflects the latest system state and a... |
| `tools/test_audit_version_literals.py` | Unit test for audit-version-literals.py -- asserts the repo-wide version-literal scanner runs and returns the (results, counts) shap... |
| `tools/test_check-blade-coverage.py` | Unit tests for tools/check-blade-coverage.py. |
| `tools/test_check-comment-lex-equivalence.py` | Fixtures for check-comment-lex-equivalence.py -- proves it runs clean on the shipped tree and that its exit code is meaningful rather than constant. |
| `tools/test_check-comment-ratchet.py` | Fixtures for check-comment-ratchet.py -- proves it runs clean on the shipped tree and that its exit code is meaningful rather than constant. |
| `tools/test_check-container-names.py` | Sibling unit test for tools/check-container-names.py. |
| `tools/test_check-credential-literals.py` | Sibling unit test for tools/check-credential-literals.py: builds throwaway unit trees and asserts the gate passes a grandfathered... |
| `tools/test_check-daemon-governor.py` | Sibling unit test for tools/check-daemon-governor.py: builds throwaway daemon/SSOT/chat trees in a temp dir and asserts the gate pass... |
| `tools/test_check-doc-ratchet-monotone.py` | Fixtures for check-doc-ratchet-monotone.py -- proves it runs clean on the shipped tree and that its exit code is meaningful rather than constant. |
| `tools/test_check-firstboot-provisioners.py` | Sibling unit test for tools/check-firstboot-provisioners.py. |
| `tools/test_check-fleet-safety.py` | Unit tests for tools/check-fleet-safety.py. Covers both detectors independently -- k3s multi-server needs BOTH two grantors and a join-less `k3s server`, so a K3S_URL or a single grantor must clear... |
| `tools/test_check-manual-links.py` | Sibling unit test for tools/check-manual-links.py: builds throwaway manual trees in a temp dir and asserts the gate exits 0 on a clean T... |
| `tools/test_check-module-length.py` | Sibling unit test for tools/check-module-length.py -- the agent-pipe module-size ratchet (check 149). |
| `tools/test_check-no-generated-prose-in-resolvers.py` | Fixtures for check-no-generated-prose-in-resolvers.py -- proves it flags an AI-hint or a MIOS_UNITS_*_COMMENT payload inside a generated resolver, and passes on a clean one. |
| `tools/test_check-node-pool.py` | Unit tests for tools/check-node-pool.py. |
| `tools/test_check-port-fallbacks.py` | Unit tests for tools/check-port-fallbacks.py. |
| `tools/test_check-ports-bound.py` | Unit tests for tools/check-ports-bound.py. |
| `tools/test_check-redact-coverage.py` | Sibling unit test for tools/check-redact-coverage.py: builds throwaway schema/SSOT/pg.py trees and asserts the gate passes a fully cl... |
| `tools/test_check-role-ssot.py` | Unit tests for tools/check-role-ssot.py. |
| `tools/test_check-schema-consumers.py` | Sibling unit test for tools/check-schema-consumers.py. |
| `tools/test_check-service-urls.py` | Unit tests for tools/check-service-urls.py. |
| `tools/test_check-ssot-consumer-keys.py` | Unit tests for tools/check-ssot-consumer-keys.py. |
| `tools/test_check-tasks-status-parity.py` | Sibling unit test for tools/check-tasks-status-parity.py. |
| `tools/test_check-unit-projection.py` | Unit tests for tools/check-unit-projection.py. |
| `tools/test_conformance_golden.py` | Golden CLI fixture test runner for check-template-conformance CLI output and behavior. |
| `tools/test_generate-adr-index.py` | Sibling unit test for tools/generate-adr-index.py (T-265). |
| `tools/test_generate-blade-karg.py` | Unit tests for tools/generate-blade-karg.py. |
| `tools/test_generate-mini-vs-hosted.py` | Sibling unit test for tools/generate-mini-vs-hosted.py. |
| `tools/test_render-desktop.py` | Fixtures for render-desktop.py -- proves the launcher renderer derives its port from SSOT, refuses an empty launcher table, and flags a .desktop file no [desktop.launchers] entry declares. |
| `tools/test_render_globals.py` | Unit tests for render-globals.py -- proves shell and PowerShell constants are escaped so the generated resolvers always parse, that ${MIOS_X... |
| `tools/test_render_ports.py` | Unit tests for render-ports.py -- proves the [ports.categories] allocator derives base + index*stride, honours pinned ports, and that the sche... |
| `tools/test_sync-bootstrap.py` | Fixtures for sync-bootstrap.py -- the Law 15 mirror. Proves it reports drift without --apply, that a table mirror rewrites values rather than appending duplicates, and that it never touches a surface... |
| `tools/test_templates_golden.py` | Golden fixture test runner for mios-new template generator across all 20 template types. |
| `tools/verb-template-check.py` | Validates verb command templates against declared verb arguments and synonyms at build time. |

<!-- derived from the AI-hint headers of 90 file(s) matching tools/*.py -->
<!-- /MIOS-GEN:index:tools/*.py -->

## Libraries (`usr/lib/mios`)

<!-- MIOS-GEN:index:usr/lib/mios/*.py -->
| File | What it is |
|---|---|
| `usr/lib/mios/agent-pipe/mios_a2a.py` | Re-export shim for mios_pipe.federation.a2a |
| `usr/lib/mios/agent-pipe/mios_a2a_client.py` | Re-export shim for mios_pipe.federation.a2a_client |
| `usr/lib/mios/agent-pipe/mios_a2a_principal.py` | Re-export shim for mios_pipe.identity.principal |
| `usr/lib/mios/agent-pipe/mios_aci.py` | Re-export shim for mios_pipe.routing.aci |
| `usr/lib/mios/agent-pipe/mios_agent_call.py` | Re-export shim for mios_pipe.routing.agent_call |
| `usr/lib/mios/agent-pipe/mios_agentreg.py` | Re-export shim for mios_pipe.routing.agentreg |
| `usr/lib/mios/agent-pipe/mios_arbiter.py` | Re-export shim for mios_pipe.access.arbiter |
| `usr/lib/mios/agent-pipe/mios_argval.py` | Verb argument validation and synonym mapping helper (WS-DEBT / TD-5 / T-273). Extracted from mios_dispatch.py. Pure helper, must NOT import server.py or... |
| `usr/lib/mios/agent-pipe/mios_audit.py` | Re-export shim for mios_pipe.observability.audit |
| `usr/lib/mios/agent-pipe/mios_batch.py` | Re-export shim for mios_pipe.scheduler.batch |
| `usr/lib/mios/agent-pipe/mios_bench.py` | Re-export shim for mios_pipe.scheduler.bench |
| `usr/lib/mios/agent-pipe/mios_blades.py` | Re-export shim for mios_pipe.scheduler.blades |
| `usr/lib/mios/agent-pipe/mios_capreg.py` | Re-export shim for mios_pipe.lifecycle.capreg |
| `usr/lib/mios/agent-pipe/mios_chat.py` | Re-export shim for mios_pipe.routing.chat |
| `usr/lib/mios/agent-pipe/mios_classify.py` | Re-export shim for mios_pipe.routing.classify |
| `usr/lib/mios/agent-pipe/mios_clusterhealth.py` | Re-export shim for mios_pipe.kernel.clusterhealth |
| `usr/lib/mios/agent-pipe/mios_codemode.py` | Provides pure, side-effect-free logic for WS-2 Code Mode, including session ID derivation, podman exec argument construction, and tool-call normalizat... |
| `usr/lib/mios/agent-pipe/mios_cold_evict.py` | Cold-export and zstd compression module for knowledge table eviction (CONV-09). |
| `usr/lib/mios/agent-pipe/mios_compact.py` | Re-export shim for mios_pipe.context.compact |
| `usr/lib/mios/agent-pipe/mios_config.py` | Re-export shim for mios_pipe.kernel.config |
| `usr/lib/mios/agent-pipe/mios_cost.py` | Re-export shim for mios_pipe.observability.cost |
| `usr/lib/mios/agent-pipe/mios_council_diversity.py` | Re-export shim for mios_pipe.routing.council_diversity |
| `usr/lib/mios/agent-pipe/mios_crl.py` | Re-export shim for mios_pipe.identity.crl |
| `usr/lib/mios/agent-pipe/mios_ctxpack.py` | Re-export shim for mios_pipe.context.ctxpack |
| `usr/lib/mios/agent-pipe/mios_cua.py` | Re-export shim for mios_pipe.routing.cua |
| `usr/lib/mios/agent-pipe/mios_daemons.py` | Re-export shim for mios_pipe.kernel.daemons |
| `usr/lib/mios/agent-pipe/mios_dag_exec.py` | Re-export shim for mios_pipe.routing.dag_exec |
| `usr/lib/mios/agent-pipe/mios_dci.py` | Re-export shim for mios_pipe.routing.dci |
| `usr/lib/mios/agent-pipe/mios_dispatch.py` | Verb->bash DISPATCH chokepoint extracted VERBATIM from server.py (refactor R7 wave). |
| `usr/lib/mios/agent-pipe/mios_dispatcher.py` | Re-export shim for mios_pipe.routing.dispatcher |
| `usr/lib/mios/agent-pipe/mios_embed_backfill.py` | Re-export shim for mios_pipe.memory.embed_backfill |
| `usr/lib/mios/agent-pipe/mios_endpoints.py` | Pure endpoint capability detection extracted verbatim from server.py (strangler-fig refactor R-wave). |
| `usr/lib/mios/agent-pipe/mios_evict.py` | Re-export shim for mios_pipe.scheduler.evict |
| `usr/lib/mios/agent-pipe/mios_fanout.py` | Re-export shim for mios_pipe.routing.fanout |
| `usr/lib/mios/agent-pipe/mios_firewall.py` | Re-export shim for mios_pipe.access.firewall |
| `usr/lib/mios/agent-pipe/mios_gateway_queue.py` | In-process asyncio.Queue gateway producer-consumer seam (CONV-02). |
| `usr/lib/mios/agent-pipe/mios_gossip.py` | Re-export shim for mios_pipe.kernel.gossip |
| `usr/lib/mios/agent-pipe/mios_grounding.py` | Re-export shim for mios_pipe.context.grounding |
| `usr/lib/mios/agent-pipe/mios_hitl.py` | Re-export shim for mios_pipe.access.hitl |
| `usr/lib/mios/agent-pipe/mios_hitlflow.py` | Re-export shim for mios_pipe.access.hitlflow |
| `usr/lib/mios/agent-pipe/mios_hopbudget.py` | Re-export shim for mios_pipe.routing.hopbudget |
| `usr/lib/mios/agent-pipe/mios_http_caps.py` | Re-export shim for mios_pipe.federation.http_caps |
| `usr/lib/mios/agent-pipe/mios_interop.py` | Re-export shim for mios_pipe.routing.interop |
| `usr/lib/mios/agent-pipe/mios_jsonsalvage.py` | Re-export shim for mios_pipe.routing.jsonsalvage |
| `usr/lib/mios/agent-pipe/mios_kernel.py` | Re-export shim for mios_pipe.kernel.kernel |
| `usr/lib/mios/agent-pipe/mios_knowledge.py` | Re-export shim for mios_pipe.memory.knowledge |
| `usr/lib/mios/agent-pipe/mios_kvfork.py` | Re-export shim for mios_pipe.context.kvfork |
| `usr/lib/mios/agent-pipe/mios_kvgc.py` | Re-export shim for mios_pipe.context.kvgc |
| `usr/lib/mios/agent-pipe/mios_lanes.py` | Re-export shim for mios_pipe.routing.lanes |
| `usr/lib/mios/agent-pipe/mios_lanes_resolver.py` | Re-export shim for mios_pipe.routing.lanes_resolver |
| `usr/lib/mios/agent-pipe/mios_manifest.py` | Re-export shim for mios_pipe.lifecycle.manifest |
| `usr/lib/mios/agent-pipe/mios_mcp.py` | Re-export shim for mios_pipe.federation.mcp |
| `usr/lib/mios/agent-pipe/mios_memguard.py` | Re-export shim for mios_pipe.access.memguard |
| `usr/lib/mios/agent-pipe/mios_memory.py` | Re-export shim for mios_pipe.memory.memory |
| `usr/lib/mios/agent-pipe/mios_native_loop.py` | Re-export shim for mios_pipe.routing.native_loop |
| `usr/lib/mios/agent-pipe/mios_oscontrol.py` | Re-export shim for mios_pipe.routing.oscontrol |
| `usr/lib/mios/agent-pipe/mios_owui.py` | Re-export shim for mios_pipe.routing.owui |
| `usr/lib/mios/agent-pipe/mios_pdp.py` | Re-export shim for mios_pipe.access.pdp |
| `usr/lib/mios/agent-pipe/mios_pg.py` | Re-export shim for mios_pipe.memory.pg |
| `usr/lib/mios/agent-pipe/mios_pipe/__init__.py` | root of mios_pipe package. Sanitizes empty MIOS_* env vars on import so |
| `usr/lib/mios/agent-pipe/mios_pipe/access/__init__.py` | access manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/access/arbiter.py` | WS-9 out-of-process policy-arbiter DECISION core. Pure-stdlib verdict logic the mios-policy-arbiter service uses to answer the agent-pipe's... |
| `usr/lib/mios/agent-pipe/mios_pipe/access/authn.py` | Authentication / caller-key helpers extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/access/firewall.py` | Provenance-taint + Semantic Firewall plane extracted verbatim from server.py (refactor R7 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/access/hitl.py` | Provides deterministic logic for the WS-6 HITL approval gate, determining if actions should proceed or be blocked/logged based on verb scope and mode. |
| `usr/lib/mios/agent-pipe/mios_pipe/access/hitlflow.py` | HITL ask-to-run + runtime approval-gate flow extracted verbatim from server.py (refactor R7 security wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/access/memguard.py` | WS-MEM-VALIDATE write-time memory-poisoning guard (OWASP ASI08). |
| `usr/lib/mios/agent-pipe/mios_pipe/access/pdp.py` | WS-A9 Policy Decision Point (PDP) -- the pure capability/risk decision core shared by the agent-pipe's RBAC SURFACE filters (_agent_rbac_filter... |
| `usr/lib/mios/agent-pipe/mios_pipe/access/policy.py` | RBAC/PDP/quota + human-in-the-loop POLICY plane extracted verbatim from server.py (refactor R7 security wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/access/quarantine.py` | CaMeL dual-context QUARANTINE boundary -- the deeper half of the F2/T-033 prompt-injection defense (Debenedetti et al., "Defeating Promp... |
| `usr/lib/mios/agent-pipe/mios_pipe/access/quota.py` | WS-6 per-user quota + rate-limit core. Pure-stdlib tracker modelled on the LiteLLM per-key budget + RPM pattern: each user gets a sliding-win... |
| `usr/lib/mios/agent-pipe/mios_pipe/access/sandbox.py` | WS-A13 risk-tier dispatch-sandbox profile resolver. Pure-stdlib core that maps a verb's permission tier (read|write|interactive) to a Sandb... |
| `usr/lib/mios/agent-pipe/mios_pipe/access/seccomp.py` | T-230 seccomp filter builder for the risk-tier dispatch sandbox. |
| `usr/lib/mios/agent-pipe/mios_pipe/access/secset.py` | WS-A14 SSOT-derived security sets. Pure-stdlib resolver that derives the agent-pipe's high-privilege verb set (the taint-firewall + HITL gat... |
| `usr/lib/mios/agent-pipe/mios_pipe/auth.py` | Extracted module for auth.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/context/__init__.py` | context manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/context/compact.py` | WS-A5 rolling-summary compaction planner for the agent-pipe. When a conversation's message history exceeds a token budget, plan_compaction... |
| `usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py` | WS-A5 priority token-budget context packer for the agent-pipe. |
| `usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py` | Per-turn ENV-GROUNDING subsystem extracted verbatim from server.py (refactor R2 leaf wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/context/kvfork.py` | Provides filesystem-safe KV-cache fork primitives for the agent-pipe, enabling branching of shared conversation prefixes into independent c... |
| `usr/lib/mios/agent-pipe/mios_pipe/context/kvgc.py` | WS-A4 KV-cache file garbage-collection PLANNER. Pure-stdlib decision core for reclaiming the on-disk KV slot-save files the agent-pipe writes... |
| `usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py` | Pure prompt text-block formatters lifted verbatim from server.py AI-related: server.py, mios_fanout.py, mios_swarm.py, mios_daemons.py A... |
| `usr/lib/mios/agent-pipe/mios_pipe/context/promptver.py` | WS-LIFECYCLE-VER prompt-version registry (the PURE half). The ~12 agent-pipe hop prompts (router/refine/synthesis/polish/swarm/native-lo... |
| `usr/lib/mios/agent-pipe/mios_pipe/context/scratchpad.py` | Agent scratchpad blackboard extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/context/tokenize.py` | WS-A5 tokenizer seam for the agent-pipe. Centralizes the scattered "len // 4" token estimate behind ONE pluggable interface -- count_text... |
| `usr/lib/mios/agent-pipe/mios_pipe/db.py` | Extracted module for db.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/dbwrite.py` | Database writer layer extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/__init__.py` | federation manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/a2a.py` | A2A FEDERATION publish/server surface extracted VERBATIM from server.py (refactor R11 federation wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/a2a_client.py` | A2A PEER-CLIENT consumer half extracted VERBATIM from server.py (refactor R11 federation follow-up). |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/agentcard_sign.py` | Pure A2A AgentCard JWS/JCS signing and verification module. |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/http_caps.py` | ADVERTISED-SURFACE / capability + read-only admin route-handler LOGIC extracted VERBATIM from server.py (refactor R-CAPS wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/federation/mcp.py` | External-MCP CONSUME client extracted VERBATIM from server.py (refactor R-MCP wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/health.py` | Health and status endpoint response builder module for MiOS agent-pipe. |
| `usr/lib/mios/agent-pipe/mios_pipe/identity/__init__.py` | identity manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/identity/crl.py` | WS-A10 certificate/token revocation list (CRL). Pure-stdlib revocation set: load revoked token-ids / principal-ids from a list (or a caller-t... |
| `usr/lib/mios/agent-pipe/mios_pipe/identity/principal.py` | Pure A2A signed-delegation-principal helpers (#60 WS-6). Builds + verifies. |
| `usr/lib/mios/agent-pipe/mios_pipe/identity/reputation.py` | Pure in-memory per-peer reliability tracker (#54 zero-trust federation): AI-related: server.py, mios_a2a_principal, mios_lanes AI-func... |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/__init__.py` | kernel manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/clusterhealth.py` | CLUSTER/SCHEDULER/HEALTH route-handler LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py` | Pure config-constant + SSOT-reader layer extracted from server.py (refactor WS R1). |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/daemons.py` | BACKGROUND async daemon-loop bodies extracted VERBATIM from server.py AI-related: ./server.py, ./mios_config.py, ./mios_gossip.py, ./mios_p... |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/gossip.py` | WS-A18 federated agent discovery -- the PURE epidemic-gossip + SWIM-style anti-entropy core (the transport-free half; mios_reputation alread... |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/httpclient.py` | The ONE shared outbound httpx.AsyncClient for the whole pipe, extracted verbatim from server.py, plus the WS-A6/T-226 batch-coalescing c... |
| `usr/lib/mios/agent-pipe/mios_pipe/kernel/kernel.py` | WS-A11/WS-3 server.py decomposition -- Stage 1b: the pure Kernel facade. |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/__init__.py` | lifecycle manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/capreg.py` | WS-2 unified capability registry projection -- the PURE half: merge the [verbs.*] catalog, the [recipes.*] OS-command templates, AND the ... |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/manifest.py` | WS-A1 anti-drift manifest projection -- the PURE core that projects the live verb catalog (mios.toml [verbs.*]) into a deterministic ai... |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove.py` | Pure self-improvement ANALYZER (#64) -- improvement signals from local outcome data. |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/selfimprove_act.py` | Pure self-improvement ACT-half decision core (T-062 ACT + T-064 proof-of-utility). |
| `usr/lib/mios/agent-pipe/mios_pipe/lifecycle/verity.py` | Anti-fabrication POLISH/VERITY cluster extracted verbatim from server.py (refactor R6 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/mcp_dispatch.py` | MCP tool call dispatch module for MiOS agent-pipe. |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/__init__.py` | memory manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py` | WS-A2 embedding-version hygiene -- the pure decision core for an off-hot-path re-embed (backfill) job. |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/knowledge.py` | Tiered pgvector KNOWLEDGE memory subsystem extracted verbatim from server.py (refactor R6 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/memory.py` | WS-A15 pluggable MemoryProvider seam for the agent-pipe. Wraps the pgvector recall/store path behind a small MemoryProvider interface (retri... |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/pg.py` | Provides a PostgreSQL and pgvector client for the agent plane (WS-9), offering a standalone, SQL-injection-safe datastore client using parameter... |
| `usr/lib/mios/agent-pipe/mios_pipe/memory/worker_tools.py` | BM25/RRF/MMR tool reranker + tool-priority ranking helpers extracted verbatim from server.py (refactor R4 worker-tools wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/__init__.py` | observability manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/audit.py` | SEC-03 tamper-evident SHA-256 hash chain over the agent-plane `event` stream. |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/cost.py` | WS-RES-GOV cost/energy accounting core (the PURE half, CLASSic "Cost" axis). |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/drift_monitor.py` | Pure Jensen-Shannon divergence monitor over agent-plane verdict/intent/score histograms (CONS-02). |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/session_events.py` | Session-event emitter + tool-text sanitizer extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/observability/trace.py` | WS-A8 per-request trace/span observability primitive for the agent-pipe. |
| `usr/lib/mios/agent-pipe/mios_pipe/redact.py` | Redaction utilities for secrets and PII. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/__init__.py` | routing manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/aci.py` | Normalizes raw tool/terminal output into a context-safe format by preserving the head and tail while eliding the middle with a specific marker... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/agent_call.py` | Shared sub-agent COMPLETION-call primitive extracted verbatim from server.py (refactor R3 dispatch-substrate wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/agentreg.py` | Agent/node REGISTRY builders extracted verbatim from server.py (refactor R3/mios_agentreg wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/applet_webresearch.py` | Web-research SSE applet -- app-ifies the "Discovery / resolution" verb cluster (web_search/web_extract/crawl) as an HTML-over-S... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py` | The agent-pipe CHAT-COMPLETIONS router-brain, extracted VERBATIM from AI-related: ./server.py, ./mios_vision.py, ./mios_oscontrol.py, ./mios_... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/classify.py` | Layer-1 micro-LLM CLASSIFIER cluster, extracted verbatim from server.py |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/consensus.py` | Pure consensus math for multi-judge Definition-of-Done verdicts. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/council_diversity.py` | Council input-diversity gate + confidence-aware aggregation bypass (T-047 RouteMoA GAP-1 / T-048 MOSAIC GAP-2). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/cua.py` | WS-8 computer-use perceive->act->verify loop core (the PURE half). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/dag_exec.py` | DAG EXECUTION entrypoints extracted VERBATIM from server.py (refactor R8 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/dag_validate.py` | Pure pre-execution validator and Kahn topological classifier for runtime agent DAGs. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/dci.py` | Deliberative Collective Intelligence (DCI) subsystem extracted verbatim from server.py (refactor R6 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/dispatch_cmd.py` | Verb -> bash COMMAND BUILDER, extracted VERBATIM from mios_dispatch.py (T-273). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/dispatcher.py` | WS-A11/WS-3 server.py decomposition -- Stage 1c: the pure Dispatcher. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py` | Council/swarm fan-out SELECTION (refactor R3 wave; de-hardcoded per operator "the scoring IS a hardcode in and of itself"). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/hopbudget.py` | WS-4 orchestrator-worker hop-budget + effort-scaling pure core. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/interop.py` | WS-11 layered-interop 3-projection core. Pure-stdlib projector that renders ONE MiOS capability (a verb, a recipe, or a promoted skill) in... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/jsonsalvage.py` | Provides a dependency-free, regex-based JSON parser to recover malformed JSON objects from small-model outputs by repairing common syntax errors like trailing commas, comments, and empty values. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/lanes.py` | Unified inference-lane resolver (WS-1) -- the ONE place the agent-pipe chooses a model lane. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/lanes_resolver.py` | INFERENCE LANE-RESOLVER cluster extracted VERBATIM from server.py AI-related: ./server.py, ./mios_config.py, ./mios_lanes.py, ./tes... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/native_loop.py` | NATIVE single-agent tool-loop responders extracted VERBATIM from server.py AI-related: ./server.py, ./mios_config.py, ./mios_turn.py, ... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py` | OS-CONTROL fast-path responder + window enum/verify helpers extracted VERBATIM from server.py (refactor R9 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/owui.py` | Adapter for Open WebUI requests that identifies and strips OWUI-specific RAG/task templates to isolate the raw user query from downstream processing in the agent-pipe. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/planner.py` | Planner / DAG-decomposition layer extracted verbatim from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py` | WEB PORTAL helper logic + PWA asset builders + the swarm-roster probe, extracted VERBATIM from server.py (refactor R10 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/provider_translate.py` | Pure cross-provider wire-format adapter extracted from server.py (refactor WS R2 leaf wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/pty.py` | Pure PTY-session protocol for the persistent shell substrate (SHELL-01). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/quality_gate.py` | Pure deterministic quality gate producer for smartroute escalation decisions. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py` | REFINE intent-classifier extracted verbatim from server.py (refactor R5/mios_refine wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/reflect.py` | Reflection / self-assessment cluster extracted verbatim from server.py (strangler-fig wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/remote_adapter.py` | Remote multi-provider adapter module. Normalizes OpenAI Chat Completions requests for remote [nodes.*] bindings declaring api='anth... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/replay.py` | OAI-04/T-225 run-template REPLAY matcher -- the reuse half of the WS-6 capture path. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/router.py` | WS-A11/WS-3 server.py decomposition -- Stage 1: the pure Router. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/routing.py` | ROUTING layer extracted verbatim from server.py (refactor R2/mios_routing wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/ruleof2.py` | CaMeL-class architectural prompt-injection defense -- Meta's "Agents Rule of Two" composed as a DETERMINISTIC (not probabilistic) dispatch gate. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/run_template.py` | WS-6 run-template CAPTURE + the T-225 replay source, extracted out of dag_exec so the two halves of one feature live together. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/secondary_loop.py` | Sub-agent TOOL LOOP for the OpenAI /v1 surface (MiOS is /v1-only), extracted verbatim from server.py (refactor R4 + a later move-home wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/smartroute.py` | WS-A16 cost/quality SmartRouting core, designed per researched best practice (LiteLLM router + adaptive/cascading routing): LOCAL-FIRST... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/sse.py` | OpenAI streaming SSE chunk + status-emit primitives extracted from server.py (refactor WS R2 leaf wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/swarm.py` | SWARM brain extracted VERBATIM from server.py (refactor R8 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/toolconflict.py` | WS-A7 per-verb conflict/parallel-limit serialization for the agent-pipe Tool Manager. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/toolexec.py` | Tool-call EXECUTION primitive extracted verbatim from server.py (refactor R4 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/toolsearch.py` | Embedding TOOL/APP semantic-search core extracted verbatim from server.py (refactor R10 toolsearch wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/toolsurface.py` | Worker-tool surface assembly + child-tool selection extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/turn.py` | PER-TURN message-prep + agent-selection helpers extracted VERBATIM from AI-related: ./server.py, ./mios_config.py, ./test_mios_turn.py AI-fun... |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/verbcatalog.py` | VERB/RECIPE CATALOG loader + 3-projection SSOT source, extracted verbatim from server.py (refactor R2 leaf wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/vision.py` | VISION + CLIENT-TOOLS responders extracted VERBATIM from server.py (refactor R9 wave). |
| `usr/lib/mios/agent-pipe/mios_pipe/routing/web_research.py` | WEB-RESEARCH enrichment subsystem extracted verbatim from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/__init__.py` | scheduler manager package |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/admission.py` | Admission control / SLO / lane-semaphore seam extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/batch.py` | WS-A6 batch-coalescing core, designed per 2026 best practice (researched): vLLM/SGLang/llama.cpp already do SERVER-SIDE continuous batchin... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/bench.py` | Pure, DB-free scoring core for the MiOS agentic-capability benchmark harness. |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py` | Pure-stdlib BLADE/topology model for the agent-pipe (V4 + V5 multi-blade AI-related: ./mios_config.py, ./mios_agentreg.py, ./server.py, .... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/evict.py` | WS-A3 pure, DB-free logic for the knowledge-table eviction sweep -- now PARAMETERIZED POSTGRES (the cutover). |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/preempt.py` | WS-A12 round-robin preemption state machine + generation-snapshot contract, PLUS the T-019/SCHED-01 TURN-boundary preemption seam AND th... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/sched.py` | The MiOS agent-pipe scheduler module. Provides (1) PriorityGate, the WS-1 AI-related: server.py, mios_config.py, test_mios_sched.py AI-fun... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/slo.py` | WS-SCHED-SLO deadline/SLO scheduling core (the PURE half). The MiOS admission gate is capacity-only (VRAM/host-load) and degrades OPEN -- it... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/stress.py` | Stress test harness for the agent-pipe that validates the /v1/chat/completions path under load-aware concurrency, e... |
| `usr/lib/mios/agent-pipe/mios_pipe/scheduler/vram.py` | VRAM and model-residency manager extracted from server.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/streaming.py` | Extracted module for streaming.py. |
| `usr/lib/mios/agent-pipe/mios_pipe/vram_scheduler.py` | Extracted module for vram_scheduler.py. |
| `usr/lib/mios/agent-pipe/mios_planner.py` | Re-export shim for mios_pipe.routing.planner |
| `usr/lib/mios/agent-pipe/mios_policy.py` | Re-export shim for mios_pipe.access.policy |
| `usr/lib/mios/agent-pipe/mios_portal.py` | Re-export shim for mios_pipe.routing.portal |
| `usr/lib/mios/agent-pipe/mios_preempt.py` | Re-export shim for mios_pipe.scheduler.preempt |
| `usr/lib/mios/agent-pipe/mios_promptfmt.py` | Re-export shim for mios_pipe.context.promptfmt |
| `usr/lib/mios/agent-pipe/mios_promptver.py` | Re-export shim for mios_pipe.context.promptver |
| `usr/lib/mios/agent-pipe/mios_provider_translate.py` | Re-export shim for mios_pipe.routing.provider_translate |
| `usr/lib/mios/agent-pipe/mios_quarantine.py` | Re-export shim for mios_pipe.access.quarantine |
| `usr/lib/mios/agent-pipe/mios_quota.py` | Re-export shim for mios_pipe.access.quota |
| `usr/lib/mios/agent-pipe/mios_refine.py` | Re-export shim for mios_pipe.routing.refine |
| `usr/lib/mios/agent-pipe/mios_reflect.py` | Re-export shim for mios_pipe.routing.reflect |
| `usr/lib/mios/agent-pipe/mios_registry.py` | WS-A17 versioned agent/tool package format + local registry projection. |
| `usr/lib/mios/agent-pipe/mios_reputation.py` | Re-export shim for mios_pipe.identity.reputation |
| `usr/lib/mios/agent-pipe/mios_router.py` | Re-export shim for mios_pipe.routing.router |
| `usr/lib/mios/agent-pipe/mios_routing.py` | Re-export shim for mios_pipe.routing.routing |
| `usr/lib/mios/agent-pipe/mios_ruleof2.py` | Re-export shim for mios_pipe.routing.ruleof2 |
| `usr/lib/mios/agent-pipe/mios_sandbox.py` | Re-export shim for mios_pipe.access.sandbox |
| `usr/lib/mios/agent-pipe/mios_sched.py` | Re-export shim for mios_pipe.scheduler.sched |
| `usr/lib/mios/agent-pipe/mios_scratchpad.py` | In-process SQLite vector store (sqlite-vec) scratchpad module for ephemeral tool outputs (CONV-08). |
| `usr/lib/mios/agent-pipe/mios_secondary_loop.py` | Re-export shim for mios_pipe.routing.secondary_loop |
| `usr/lib/mios/agent-pipe/mios_secset.py` | Re-export shim for mios_pipe.access.secset |
| `usr/lib/mios/agent-pipe/mios_selfimprove.py` | Re-export shim for mios_pipe.lifecycle.selfimprove |
| `usr/lib/mios/agent-pipe/mios_selfimprove_act.py` | Re-export shim for mios_pipe.lifecycle.selfimprove_act |
| `usr/lib/mios/agent-pipe/mios_skills.py` | SKILLS execution cluster extracted verbatim from server.py (refactor R7/mios_skills wave). |
| `usr/lib/mios/agent-pipe/mios_slo.py` | Re-export shim for mios_pipe.scheduler.slo |
| `usr/lib/mios/agent-pipe/mios_smartroute.py` | Re-export shim for mios_pipe.routing.smartroute |
| `usr/lib/mios/agent-pipe/mios_sse.py` | Re-export shim for mios_pipe.routing.sse |
| `usr/lib/mios/agent-pipe/mios_stress.py` | Re-export shim for mios_pipe.scheduler.stress |
| `usr/lib/mios/agent-pipe/mios_surface.py` | Pure stdlib (ast) extractor of the server.py PUBLIC SURFACE for the refactor parity gate (refactor WS R0). |
| `usr/lib/mios/agent-pipe/mios_swarm.py` | Re-export shim for mios_pipe.routing.swarm |
| `usr/lib/mios/agent-pipe/mios_template.py` | Renders an SSOT verb command template into the broker bash line. |
| `usr/lib/mios/agent-pipe/mios_tokenize.py` | Re-export shim for mios_pipe.context.tokenize |
| `usr/lib/mios/agent-pipe/mios_toolconflict.py` | Re-export shim for mios_pipe.routing.toolconflict |
| `usr/lib/mios/agent-pipe/mios_toolexec.py` | Re-export shim for mios_pipe.routing.toolexec |
| `usr/lib/mios/agent-pipe/mios_toolsearch.py` | Re-export shim for mios_pipe.routing.toolsearch |
| `usr/lib/mios/agent-pipe/mios_trace.py` | Re-export shim for mios_pipe.observability.trace |
| `usr/lib/mios/agent-pipe/mios_turn.py` | Re-export shim for mios_pipe.routing.turn |
| `usr/lib/mios/agent-pipe/mios_verbcatalog.py` | Re-export shim for mios_pipe.routing.verbcatalog |
| `usr/lib/mios/agent-pipe/mios_verity.py` | Re-export shim for mios_pipe.lifecycle.verity |
| `usr/lib/mios/agent-pipe/mios_vision.py` | Re-export shim for mios_pipe.routing.vision |
| `usr/lib/mios/agent-pipe/mios_web_research.py` | Re-export shim for mios_pipe.routing.web_research |
| `usr/lib/mios/agent-pipe/mios_worker_tools.py` | Re-export shim for mios_pipe.memory.worker_tools |
| `usr/lib/mios/agent-pipe/server.py` | FastAPI gateway service on the `agent_pipe` port that routes, dispatches, and proxies chat/embedding requests from external interfaces (Discord, Slack) to th... |
| `usr/lib/mios/agent-pipe/test_lora_endpoints.py` | Standalone assert-script unit test for LoRA list/load endpoints (CONV-06). |
| `usr/lib/mios/agent-pipe/test_mios_a2a.py` | Stdlib unit test for the extracted A2A federation publish surface (mios_a2a). |
| `usr/lib/mios/agent-pipe/test_mios_a2a_client.py` | Stdlib unit test for the extracted A2A peer-client consumer half (mios_a2a_client). |
| `usr/lib/mios/agent-pipe/test_mios_a2a_loopback.py` | Offline unit test for the mios-a2a-test loopback smoke-test helper -- exercises the pure message-builder, artifact extr... |
| `usr/lib/mios/agent-pipe/test_mios_a2a_passport.py` | Standalone unit test for mios_a2a_principal (#60 WS-6 signed A2A delegation principal): claim shape, text-binding digest, and the send->verif... |
| `usr/lib/mios/agent-pipe/test_mios_a2a_principal.py` | Standalone assert-script unit test for mios_a2a_principal (#60 WS-6 signed A2A delegation principal). Pure stdlib, no ... |
| `usr/lib/mios/agent-pipe/test_mios_account_sync.py` | stdlib unit test for mios-account-sync daemon. |
| `usr/lib/mios/agent-pipe/test_mios_aci.py` | Standalone unit test for the mios_aci.normalize_output function to verify that ACI output truncation, labeling, and head/tail preservation logic corre... |
| `usr/lib/mios/agent-pipe/test_mios_admission.py` | Unit tests for mios_pipe.scheduler.admission. |
| `usr/lib/mios/agent-pipe/test_mios_agent_call.py` | Stdlib assert-script for mios_agent_call. Stubs every injected dep (no |
| `usr/lib/mios/agent-pipe/test_mios_agentcard_sign.py` | Unit test suite for mios_pipe.federation.agentcard_sign module. |
| `usr/lib/mios/agent-pipe/test_mios_agentreg.py` | Standalone assert-script unit test for mios_agentreg (R3 agent/node registry builders). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_ai_manifest.py` | Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog manifest projection). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_antifab.py` | Standalone assert-script unit test for the anti-fabrication guard AI-related: ./mios_pipe/routing/chat.py, ./mios_chat.py, ./test_mios_chat.py AI-... |
| `usr/lib/mios/agent-pipe/test_mios_approutes.py` | Runtime route-parity gate for the agent-pipe strangler-fig refactor (WS R13 Step 2b) -- the LIVE-FastAPI complement to the... |
| `usr/lib/mios/agent-pipe/test_mios_arbiter.py` | Standalone assert-script unit test for mios_arbiter (WS-9 out-of-process policy-arbiter decision core). Pure stdlib, no serv... |
| `usr/lib/mios/agent-pipe/test_mios_argval.py` | Sibling unit test for the mios_argval python module, ensuring compliance with drift-check 11. |
| `usr/lib/mios/agent-pipe/test_mios_audit.py` | Unit tests for mios_audit, the SEC-03 SHA-256 tamper-evident event-bus hash chain. |
| `usr/lib/mios/agent-pipe/test_mios_auth.py` | Placeholder test for mios_auth.py. |
| `usr/lib/mios/agent-pipe/test_mios_authn.py` | Unit tests for mios_pipe.access.authn. |
| `usr/lib/mios/agent-pipe/test_mios_batch.py` | Standalone assert-script unit test for mios_batch (WS-A6 batch coalescing). Stdlib + asyncio, no DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_bench.py` | Standalone assert-script unit test for mios_bench (agentic-capability benchmark scoring core). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_bench_harness.py` | Verification test suite for mios-bench harness CLI option parsing, metrics reporting, a... |
| `usr/lib/mios/agent-pipe/test_mios_blades.py` | Standalone assert-script unit test for mios_blades (V4/V5 blade topology + AI-related: ./mios_blades.py, ./mios_config.py, ./... |
| `usr/lib/mios/agent-pipe/test_mios_budget.py` | stdlib unit test for mios_agent_call budget and depth limits. |
| `usr/lib/mios/agent-pipe/test_mios_capreg.py` | Standalone assert-script unit test for mios_capreg (WS-2 unified RBAC-filtered capability manifest). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_chat.py` | Routing-PRECEDENCE gate for the extracted chat-completions router-brain |
| `usr/lib/mios/agent-pipe/test_mios_classify.py` | Stdlib unit tests for mios_classify (layer-1 micro-LLM classifiers). |
| `usr/lib/mios/agent-pipe/test_mios_clusterhealth.py` | Stdlib unit test for mios_clusterhealth -- the cluster/scheduler/health route LOGIC extracted VERBATIM from server.py (refactor ROUTE-SURFACE wave). |
| `usr/lib/mios/agent-pipe/test_mios_codemode.py` | Standalone unit test for mios_codemode logic to verify language normalization, timeout clamping, and session ID generation without requiring the ... |
| `usr/lib/mios/agent-pipe/test_mios_cold_evict.py` | Standalone assert-script unit test for mios_cold_evict (CONV-09). |
| `usr/lib/mios/agent-pipe/test_mios_compact.py` | Standalone assert-script unit test for mios_compact (WS-A5 rolling-summary compaction planner). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_compound.py` | Standalone unit test for the #49 read-tool-enrich domain-filter fix: a compound that spans domains must keep verbs refine EXPLICITLY hinted (and,... |
| `usr/lib/mios/agent-pipe/test_mios_conductor.py` | stub |
| `usr/lib/mios/agent-pipe/test_mios_config.py` | Standalone assert-script unit test for mios_config (refactor WS R1 config-constants extraction). Pure stdlib, no server.py/DB... |
| `usr/lib/mios/agent-pipe/test_mios_config_validate.py` | Hermetic unit tests for the WS-CONFIG server-side SAFETY validator |
| `usr/lib/mios/agent-pipe/test_mios_config_write.py` | Standalone unit test for the /portal/config read/write routes to ensure correct auth, TOML parsing, and background DB re-seeding. |
| `usr/lib/mios/agent-pipe/test_mios_consensus.py` | Stdlib offline unit tests for mios_pipe.routing.consensus -- the weighted multi-judge Definition-of-Done fold (CONS-01). No network / no DB / no... |
| `usr/lib/mios/agent-pipe/test_mios_cost.py` | Standalone assert-script unit test for mios_cost (WS-RES-GOV cost/energy accounting, CLASSic Cost axis). Pure stdlib, no server.py/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_council_diversity.py` | Stdlib offline unit tests for mios_council_diversity -- the council input-diversity gate (T-047 RouteMoA GAP-1) + confidence-aware aggre... |
| `usr/lib/mios/agent-pipe/test_mios_crl.py` | Standalone assert-script unit test for mios_crl (WS-A10 cert/token revocation list). Pure stdlib, no server.py/DB/pytest/network. |
| `usr/lib/mios/agent-pipe/test_mios_ctxpack.py` | Standalone assert-script unit test for mios_ctxpack (WS-A5 priority token-budget packer). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_cua.py` | Standalone assert-script unit test for mios_cua (WS-8 perceive->act->verify computer-use loop core). Pure stdlib, no server.py/VLM/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_cua_hierarchy.py` | Verification test suite for mios_cua hierarchy routing, verify-after-action, and coordinate scaling. |
| `usr/lib/mios/agent-pipe/test_mios_daemon.py` | stdlib unit test for mios_agent_call daemon runaway controls. |
| `usr/lib/mios/agent-pipe/test_mios_daemons.py` | stdlib unit test for mios_daemons -- single-iteration behaviour of the |
| `usr/lib/mios/agent-pipe/test_mios_dag_exec.py` | Stdlib assert-test for mios_dag_exec (refactor R8 DAG execution wave). |
| `usr/lib/mios/agent-pipe/test_mios_dag_validate.py` | Unit test suite for pre-execution DAG validator dag_validate.py. |
| `usr/lib/mios/agent-pipe/test_mios_db.py` | Placeholder test for mios_db.py. |
| `usr/lib/mios/agent-pipe/test_mios_db_config.py` | stdlib unit test for mios_db_config resolver. |
| `usr/lib/mios/agent-pipe/test_mios_dbwrite.py` | Unit tests for mios_pipe.dbwrite. |
| `usr/lib/mios/agent-pipe/test_mios_dci.py` | Standalone assert-script unit test for mios_dci (refactor R6 DCI extraction). Pure stdlib, no server.py/DB/httpx-network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_dispatch.py` | Offline stdlib-assert test for mios_dispatch (the verb->bash dispatch chokepoint). |
| `usr/lib/mios/agent-pipe/test_mios_dispatch_cmd.py` | Isolation tests for mios_pipe.routing.dispatch_cmd -- the verb->bash command BUILDER extracted from the dispatch chokepoint (T-273). |
| `usr/lib/mios/agent-pipe/test_mios_dispatch_redos.py` | Regression test for the ReDoS in dispatch_cmd's podman-exec shell-stripper. The flag-repetition group allowed a flag's ARGUMENT to start with '-', so "-a -b" had two legal parses and the group... |
| `usr/lib/mios/agent-pipe/test_mios_dispatcher.py` | Standalone assert-script unit test for mios_dispatcher (WS-A11/WS-3 decomposition Stage 1c: the pure mode Dispatcher) + i... |
| `usr/lib/mios/agent-pipe/test_mios_drift_monitor.py` | Stdlib offline unit tests for mios_pipe.observability.drift_monitor -- the Jensen-Shannon Goodhart alarm (CONS-02). No network / no DB / no ... |
| `usr/lib/mios/agent-pipe/test_mios_dual_ledger.py` | Standalone assert-script unit test for T-030 (Dual-Ledger + Typed-Output Synthesis). Pure stdlib + asyncio, no server.py/DB/network. |
| `usr/lib/mios/agent-pipe/test_mios_egress.py` | Standalone unit test for tools/generate-egress-firewall (#54 egress firewall): build_ruleset emits a uid-scoped nftables ruleset with the always-al... |
| `usr/lib/mios/agent-pipe/test_mios_embed_backfill.py` | Standalone assert-script unit test for mios_embed_backfill (WS-A2 embedding-version hygiene). |
| `usr/lib/mios/agent-pipe/test_mios_endpoints.py` | Standalone assert-script unit test for mios_endpoints (refactor R-wave leaf extraction). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_env.py` | Unit test for empty MIOS_* env contract. |
| `usr/lib/mios/agent-pipe/test_mios_evict.py` | Standalone assert-script unit test for mios_evict (WS-A3 parameterized-pg eviction). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_fanout.py` | Standalone assert-script unit test for mios_fanout (council/swarm fan-out SELECTION; de-hardcoded to model-driven relevance).... |
| `usr/lib/mios/agent-pipe/test_mios_firewall.py` | Standalone stdlib assert-script for mios_firewall (the provenance-taint + Semantic Firewall plane). |
| `usr/lib/mios/agent-pipe/test_mios_gateway_queue.py` | Standalone assert-script unit test for mios_gateway_queue (CONV-03). |
| `usr/lib/mios/agent-pipe/test_mios_gossip.py` | Standalone assert-script unit test for mios_gossip (WS-A18 epidemic-gossip + SWIM anti-entropy discovery core). Pure stdlib, ... |
| `usr/lib/mios/agent-pipe/test_mios_grounding.py` | Standalone assert-script unit test for mios_grounding (refactor R2 leaf extraction of the per-turn ENV-GROUNDING cluster).... |
| `usr/lib/mios/agent-pipe/test_mios_health.py` | Unit test suite for mios_pipe.health module. |
| `usr/lib/mios/agent-pipe/test_mios_hitl.py` | Standalone unit test for mios_hitl to verify deterministic logic for Human-In-The-Loop (HITL) decision gating, scope parsing, and action blocking wit... |
| `usr/lib/mios/agent-pipe/test_mios_hitlflow.py` | Stdlib assert-script for mios_hitlflow (R7 security wave) -- the HITL |
| `usr/lib/mios/agent-pipe/test_mios_hopbudget.py` | Standalone assert-script unit test for mios_hopbudget (WS-4 hop-budget guard + effort scaling). Pure stdlib, no server.py/... |
| `usr/lib/mios/agent-pipe/test_mios_http_caps.py` | Stdlib unit test for mios_http_caps -- the advertised-surface / capability route LOGIC extracted from server.py (refactor R-CAPS). |
| `usr/lib/mios/agent-pipe/test_mios_httpclient.py` | Standalone assert-script unit test for mios_pipe.kernel.httpclient -- the ONE shared outbound AsyncClient and the T-226 b... |
| `usr/lib/mios/agent-pipe/test_mios_interop.py` | Standalone assert-script unit test for mios_interop (WS-11 3-projection: the A2A skill shape). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_jsonsalvage.py` | Standalone assert-script unit test for mios_jsonsalvage.loads_lenient (lenient JSON-grammar salvage for small-model outp... |
| `usr/lib/mios/agent-pipe/test_mios_k3s.py` | Standalone unit test for the #61 generated k3s manifests: every committed usr/share/mios/k3s/generated/*.yaml parses, declares an apiVersion, carries ... |
| `usr/lib/mios/agent-pipe/test_mios_kernel.py` | Standalone assert-script unit test for mios_kernel (WS-A11/WS-3 decomposition Stage 1b: the pure Kernel facade). Pure stdlib ... |
| `usr/lib/mios/agent-pipe/test_mios_knowledge.py` | Standalone assert-script unit test for mios_knowledge (refactor R6 KNOWLEDGE-cluster extraction). Pure stdlib, no server.p... |
| `usr/lib/mios/agent-pipe/test_mios_kvfork.py` | Standalone unit test for mios_kvfork to verify KV-cache fork primitives, ensuring filename sanitization, length capping, and fork validation logic ... |
| `usr/lib/mios/agent-pipe/test_mios_kvgc.py` | Standalone assert-script unit test for mios_kvgc (WS-A4 KV-file GC planner). Pure stdlib, no server.py/DB/podman/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_lanes.py` | Standalone unit test for mios_lanes (WS-1 unified lane resolver) -- verifies build_chain ordering, health-cached pick, per-lane cooldown failover, t... |
| `usr/lib/mios/agent-pipe/test_mios_lanes_resolver.py` | Stdlib unit tests for mios_lanes_resolver (strangler-fig lane-resolver |
| `usr/lib/mios/agent-pipe/test_mios_launch.py` | Standalone unit test for the deterministic_action_route logic to ensure "open/launch" commands correctly strip filler phrases and map to open_app(n... |
| `usr/lib/mios/agent-pipe/test_mios_letta.py` | Standalone unit test suite for LettaMemoryClient and letta_dispatch_handler (T-077). |
| `usr/lib/mios/agent-pipe/test_mios_list_dir.py` | Sibling unit test for mios-text-edit view directory depth logic (T-112). |
| `usr/lib/mios/agent-pipe/test_mios_manifest.py` | Standalone assert-script unit test for mios_manifest (WS-A1 verb-catalog -> ai/v1 manifest projection; drift-check 8 depend... |
| `usr/lib/mios/agent-pipe/test_mios_mcp.py` | Stdlib unit test for mios_mcp -- the external-MCP CONSUME client extracted from server.py (refactor R-MCP). |
| `usr/lib/mios/agent-pipe/test_mios_mcp_dispatch.py` | Unit test suite for mios_pipe.mcp_dispatch module. |
| `usr/lib/mios/agent-pipe/test_mios_mcp_pool.py` | Standalone assert-script unit test for MCPClientPool (CONV-13). |
| `usr/lib/mios/agent-pipe/test_mios_mcp_sandbox.py` | Standalone assert-script unit test for T-032 (SEC-01 Hermetic MCP Sandboxing). Pure stdlib + asyncio, no server.py/DB/network. |
| `usr/lib/mios/agent-pipe/test_mios_memguard.py` | Standalone assert-script unit test for mios_memguard (WS-MEM-VALIDATE / OWASP ASI08 write-time memory-poisoning guard, de-h... |
| `usr/lib/mios/agent-pipe/test_mios_memory.py` | Standalone assert-script unit test for mios_memory (WS-A15 MemoryProvider seam). |
| `usr/lib/mios/agent-pipe/test_mios_mtls.py` | Standalone unit test for tools/provision-agent-mtls (#54 mTLS PKI): the agent leaf cert is signed by the CA, carries clientAuth+serverAuth EKU, and r... |
| `usr/lib/mios/agent-pipe/test_mios_native_loop.py` | stdlib assert-script for mios_native_loop -- exercises the NATIVE |
| `usr/lib/mios/agent-pipe/test_mios_oscontrol.py` | Offline stdlib test for mios_oscontrol (refactor R9): stubs every sibling (fastapi.responses + mios_sse/mios_jsonsalvage/m... |
| `usr/lib/mios/agent-pipe/test_mios_owui.py` | Standalone assert-script unit test for mios_owui (OWUI RAG/task-template scaffold stripper). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_pdp.py` | Standalone assert-script unit test for mios_pdp (WS-A9 PDP capability gate). |
| `usr/lib/mios/agent-pipe/test_mios_pg.py` | Standalone unit test for mios_pg to verify pure-python PostgreSQL helper logic, including DSN construction, vector literal formatting, and SQL insert g... |
| `usr/lib/mios/agent-pipe/test_mios_planner.py` | Stdlib assert-script for mios_planner. No network: the planner LLM call in decompose_intent is exercised only on the early short-prompt-skip / dis... |
| `usr/lib/mios/agent-pipe/test_mios_policy.py` | Stdlib assert-script for mios_policy (R7 security wave). Proves the |
| `usr/lib/mios/agent-pipe/test_mios_portal.py` | Standalone unit test for mios_portal (refactor R10) -- proves the moved portal logic works with stubs and no network/DB. |
| `usr/lib/mios/agent-pipe/test_mios_preempt.py` | Standalone assert-script unit test for mios_preempt (WS-A12 RR-preemption state machine + snapshot contract, PLUS the T-019/... |
| `usr/lib/mios/agent-pipe/test_mios_principal.py` | Unit test suite for mios_pipe.identity.principal module (signed A2A delegation principal). |
| `usr/lib/mios/agent-pipe/test_mios_promptfmt.py` | Stdlib unit tests for mios_promptfmt (pure prompt text-block |
| `usr/lib/mios/agent-pipe/test_mios_promptver.py` | Standalone assert-script unit test for mios_promptver (WS-LIFECYCLE-VER prompt-version registry). Pure stdlib, no server.py/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_provider_translate.py` | Standalone assert-script unit test for mios_provider_translate (refactor WS R2 leaf extraction). Pure stdlib, no ... |
| `usr/lib/mios/agent-pipe/test_mios_pty.py` | Stdlib offline tests for mios_pipe.routing.pty -- the persistent shell substrate's pure protocol (SHELL-01). No tmux, no subproc... |
| `usr/lib/mios/agent-pipe/test_mios_quality_gate.py` | Unit test suite for quality_gate.py and smartroute escalation integration. |
| `usr/lib/mios/agent-pipe/test_mios_quarantine.py` | Offline stdlib-assert test for the F2 CaMeL dual-context QUARANTINE gate (the deeper half of T-033, mios_quarantine). |
| `usr/lib/mios/agent-pipe/test_mios_quota.py` | Standalone assert-script unit test for mios_quota (WS-6 per-user quota + rate limit). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_react_reflexion.py` | Standalone assert-script unit test for T-031 (ReAct+Reflexion Durable Loop + Checkpoint-per-Superstep). Pure stdlib ... |
| `usr/lib/mios/agent-pipe/test_mios_record_replay.py` | Unit tests for T-040 (OBS-03 record-and-replay determinism + session hash chaining). |
| `usr/lib/mios/agent-pipe/test_mios_redact.py` | stdlib unit test for secrets and PII redaction. |
| `usr/lib/mios/agent-pipe/test_mios_refine.py` | Standalone assert-script unit test for mios_refine (refactor R5 REFINE-classifier extraction). Pure stdlib, no server.py/DB/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_reflect.py` | Standalone assert-script unit test for mios_reflect (strangler-fig extraction). Pure stdlib, no server.py/DB/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_registry.py` | Standalone assert-script unit test for mios_registry (WS-A17 versioned package + registry projection). Pure stdlib, no serv... |
| `usr/lib/mios/agent-pipe/test_mios_remote_adapter.py` | Unit test for mios_pipe.routing.remote_adapter. Validates Anthropic, Gemini, and OpenAI remote calls. |
| `usr/lib/mios/agent-pipe/test_mios_replay.py` | Standalone assert-script unit test for the T-225 run-template REPLAY path -- the pure matcher (mios_pipe.routing.replay), the... |
| `usr/lib/mios/agent-pipe/test_mios_reputation.py` | Standalone unit test for mios_reputation (#54 peer reputation): neutral-with-no-history, success-rate scoring, recent-failure penalty, and STAB... |
| `usr/lib/mios/agent-pipe/test_mios_router.py` | Standalone assert-script unit test for mios_router (WS-A11/WS-3 decomposition Stage 1: the pure Router). Pure stdlib, no serv... |
| `usr/lib/mios/agent-pipe/test_mios_router_parity.py` | Standalone assert-script unit test for mios_router Stage-2 parity. Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_routing.py` | Standalone assert-script unit test for mios_routing (refactor R2 ROUTING-layer extraction). Pure stdlib, no server.py/DB/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_ruleof2.py` | Offline stdlib-assert test for the F2/T-033 Rule-of-Two architectural prompt-injection gate. |
| `usr/lib/mios/agent-pipe/test_mios_run_template.py` | Standalone assert-script unit test for mios_pipe.routing.run_template -- the WS-6 capture half plus the T-225 replay re... |
| `usr/lib/mios/agent-pipe/test_mios_sandbox.py` | Standalone assert-script unit test for mios_sandbox (WS-A13 risk-tier dispatch sandbox). Pure stdlib, no server.py/bwrap/podman/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_sched.py` | Standalone unit test for mios_sched -- PriorityGate concurrency logic (permit capping, priority reordering, anti-starvation) plus the lane/schedulin... |
| `usr/lib/mios/agent-pipe/test_mios_scratchpad.py` | Unit tests for mios_pipe.context.scratchpad. |
| `usr/lib/mios/agent-pipe/test_mios_seccomp.py` | Standalone assert-script unit test for mios_pipe.access.seccomp (T-230). |
| `usr/lib/mios/agent-pipe/test_mios_secondary_loop.py` | Stdlib assert-script for mios_secondary_loop (the /v1 sub-agent tool-loop + its |
| `usr/lib/mios/agent-pipe/test_mios_secset.py` | Standalone assert-script unit test for mios_secset (WS-A14 SSOT-derived security sets). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_selfimprove.py` | Standalone unit test for mios_selfimprove (#64 self-improve analysis): per-tool failure-rate + slow-tool + unreliable-peer findings, min-sampl... |
| `usr/lib/mios/agent-pipe/test_mios_selfimprove_act.py` | Standalone unit test for mios_selfimprove_act (T-062 ACT + T-064 proof-of-utility decision core): structural anti-reward-hacking isolation... |
| `usr/lib/mios/agent-pipe/test_mios_session_events.py` | Unit tests for mios_pipe.observability.session_events. |
| `usr/lib/mios/agent-pipe/test_mios_skills.py` | Standalone assert-script unit test for mios_skills (refactor R7 SKILLS-cluster extraction). Pure stdlib, no server.py/DB/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_slo.py` | Standalone assert-script unit test for mios_slo (WS-SCHED-SLO deadline/SLO scheduling core). Pure stdlib, no server.py/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_smartroute.py` | Standalone assert-script unit test for mios_smartroute (WS-A16 cost/quality SmartRouting). Pure stdlib, no server.py/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_sse.py` | Standalone assert-script unit test for mios_sse (refactor WS R2 leaf extraction). Pure stdlib, no server.py/DB/pytest/FastAPI. |
| `usr/lib/mios/agent-pipe/test_mios_streaming.py` | Placeholder test for mios_streaming.py. |
| `usr/lib/mios/agent-pipe/test_mios_stress.py` | Standalone unit test for mios_stress logic to verify percentile calculations, request aggregation, throttling logic, and concurrency ramping algori... |
| `usr/lib/mios/agent-pipe/test_mios_surface.py` | Standalone assert-script unit test for mios_surface (refactor WS R0 parity gate + R13 Step 2a whole-package projection). Pur... |
| `usr/lib/mios/agent-pipe/test_mios_swarm.py` | stdlib assert-script gate for mios_swarm (the SWARM brain). Drives the |
| `usr/lib/mios/agent-pipe/test_mios_template.py` | stdlib unit test for mios_template. |
| `usr/lib/mios/agent-pipe/test_mios_tiered_memory.py` | Standalone assert-script unit test for MEM-02 (tiered memory / context warning and eviction logic). Pure stdlib + asyncio, no live Letta server required. Runs as `python3 test_mios_tiered_memory.py`... |
| `usr/lib/mios/agent-pipe/test_mios_tokenize.py` | Standalone assert-script unit test for mios_tokenize (WS-A5 tokenizer seam). Pure stdlib, no server.py/DB/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_toml.py` | Standalone unit test for mios_toml.py overlay and DB authoritative fallbacks. |
| `usr/lib/mios/agent-pipe/test_mios_toolconflict.py` | Standalone assert-script unit test for mios_toolconflict.ConflictGate (WS-A7). |
| `usr/lib/mios/agent-pipe/test_mios_toolexec.py` | Stdlib assert-script for mios_toolexec. Stubs every injected dep (no |
| `usr/lib/mios/agent-pipe/test_mios_toolsearch.py` | Stdlib unit test for mios_toolsearch -- the embedding tool/app semantic-search core extracted from server.py (refactor R10). |
| `usr/lib/mios/agent-pipe/test_mios_toolsurface.py` | Unit tests for mios_pipe.routing.toolsurface. |
| `usr/lib/mios/agent-pipe/test_mios_trace.py` | Standalone assert-script unit test for mios_trace (WS-A8 trace/span observability). |
| `usr/lib/mios/agent-pipe/test_mios_turn.py` | Stdlib unit tests for mios_turn (per-turn message-prep + agent-selection |
| `usr/lib/mios/agent-pipe/test_mios_vector.py` | stdlib unit test for pgvector schema and cosine similarity matching. |
| `usr/lib/mios/agent-pipe/test_mios_verbcatalog.py` | Stdlib unit test for mios_verbcatalog -- the verb/recipe catalog loader + 3-projection SSOT source. |
| `usr/lib/mios/agent-pipe/test_mios_verity.py` | Standalone assert-script unit test for mios_verity (refactor R6 extraction). Pure stdlib, no server.py/DB/network/pytest. |
| `usr/lib/mios/agent-pipe/test_mios_vision.py` | Stdlib assert-script for mios_vision (refactor R9). Covers the two |
| `usr/lib/mios/agent-pipe/test_mios_vram.py` | Unit tests for mios_pipe.scheduler.vram. |
| `usr/lib/mios/agent-pipe/test_mios_vram_scheduler.py` | Placeholder test for mios_vram_scheduler.py. |
| `usr/lib/mios/agent-pipe/test_mios_web_research.py` | Stdlib assert-script for mios_web_research. No network. Drives |
| `usr/lib/mios/agent-pipe/test_mios_worker_tools.py` | Standalone assert-script unit test for mios_worker_tools (refactor R4 worker-tools reranker extraction). Pure stdlib, n... |
| `usr/lib/mios/agent-pipe/test_server_import.py` | Near-runtime import gate for the agent-pipe strangler-fig refactor (WS R0+). |
| `usr/lib/mios/agent-pipe/tests/test_mios_health.py` | Unit test for mios_pipe.health module. |
| `usr/lib/mios/agent-pipe/tests/test_mios_mcp_dispatch.py` | Unit test for mios_pipe.mcp_dispatch module. |
| `usr/lib/mios/agents/opencode-gateway/server.py` | Provides an OpenAI-compatible HTTP shim for the opencode CLI, exposing /v1/models and /v1/chat/completions endpoints to in... |
| `usr/lib/mios/crawl4ai/mios-crawl4ai-service.py` | FastAPI service providing a persistent crawl4ai/camoufox backend that converts URLs to LLM-ready markdown by maintaining w... |
| `usr/lib/mios/mios_comments.py` | The MiOS comment lexer and classifier -- extracts comment blocks from any source file and decides, deterministically, whether each block ST... |
| `usr/lib/mios/mios_db_config.py` | Peer of mios_toml.py resolving configuration settings from PostgreSQL config tables (WS-VECTOR V1 / T-243). |
| `usr/lib/mios/mios_env.py` | Shared environment helper for stripping empty MIOS_* environment variables. |
| `usr/lib/mios/mios_toml.py` | The single shared Python resolver for the layered mios.toml SSOT -- the Python peer of tools/lib/userenv.sh. |
| `usr/lib/mios/test_mios_comments.py` | Unit tests for the comment lexer and classifier -- one fixture per classifier rule so every rule is proven to fire, plus lexer tests f... |

<!-- derived from the AI-hint headers of 400 file(s) matching usr/lib/mios/*.py -->
<!-- /MIOS-GEN:index:usr/lib/mios/*.py -->

## Cross-refs

- `usr/share/doc/mios/reference/build-pipeline.md` — the numbered build phases and the Law-6 root exceptions.
- `usr/share/doc/mios/reference/ports-and-laws.md` — port allocations and the law registry.
- `usr/libexec/mios/mios-ai-tag` — the tagger that writes and maintains the headers this page is built from.
