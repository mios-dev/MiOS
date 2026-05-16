---
name: mios-environment
description: |
  Canonical map of the MiOS host's operator-facing surface. View this whenever
  the operator asks you to do something MiOS-specific (build, launch a GUI,
  restart a service, diagnose, inspect logs, switch models). It catalogues
  the shims, helper commands, services, ports, paths, and the few non-obvious
  pitfalls that have bitten the agent repeatedly. Always prefer the
  documented shortcuts here over reconstructing the workflow from training
  data -- the shortcuts handle the namespace escape, sudo grant, and other
  MiOS-specific plumbing for you.
metadata:
  hermes:
    requires_tools:
      - terminal
---

# MiOS environment — shortcuts and surface map

<!-- MiOS-managed: seeded into $HERMES_HOME/skills/mios-environment/SKILL.md
     and ~/.hermes/skills/mios-environment/SKILL.md by mios-hermes-firstboot
     from /usr/share/mios/hermes/skills/mios-environment/SKILL.md. Edit it
     in place + drop the "MiOS-managed" marker to take ownership. -->

You are running on a **MiOS host** — an immutable Fedora bootc workstation
where `/` itself is a git working tree. The operator drives this host
through you (the Hermes-Agent gateway) via Open WebUI, the Hermes CLI, or
direct API. MiOS pre-installs **shortcuts** (commands + shims) that
collapse the multi-step shell incantations operators would otherwise
type. **Use the shortcuts.** They handle the things that have repeatedly
broken when the agent tried to reconstruct the workflow from first
principles: mount-namespace escape, sudo escalation, podman vs systemctl
restart, additional-image-store permissions, GUI session attach.

## Helper commands you should reach for first

All under `/usr/libexec/mios/`, symlinked to `/usr/local/bin/` so they are
on `$PATH` for both the operator and the agent.

### `mios-doctor` — health probe

```
mios-doctor
```

Runs the structured diagnostic the operator (and you) keep recreating
ad-hoc: privilege chain, hermes-agent state + NoNewPrivileges, ollama
reachability + loaded models, OWUI container + API, baked-image store
permissions + storage.conf, WSLg X11 + Wayland sockets, GUI shim count,
build pipeline readiness (driver present + namespace escape block),
agent config YAML sanity. Exit code = number of failures. Run this
**first** when the operator says "something's wrong" -- it usually
points at the right subsystem in <5 seconds.

### `mios-gui <app>` — launch a GUI flatpak

```
mios-gui chrome              # com.google.ChromeDev (dark mode + Wayland)
mios-gui nautilus            # org.gnome.Nautilus.Devel (file manager)
mios-gui epiphany            # org.gnome.Epiphany (web browser)
mios-gui codium .            # com.vscodium.codium (open dir)
mios-gui ptyxis              # app.devsuite.Ptyxis (terminal)
mios-gui flatseal            # com.github.tchx84.Flatseal (perms editor)
mios-gui extension-manager   # com.mattjakeman.ExtensionManager
mios-gui                     # no args -> prints the catalogue
```

You don't need to remember flatpak app IDs, --env flags, or the existence
of the shim layer. `mios-gui chrome` does the right thing. The shim
chain (`mios-gui` -> `/usr/local/bin/chrome` -> `/usr/libexec/mios/flatpak-launch`)
handles:
  * service-user re-exec to the operator (when called as `mios-hermes`)
  * mount-namespace escape via `systemd-run` (PID 1 forks the unit fresh)
  * dark-theme + Wayland env defaults for Chrome
  * fire-and-forget detachment (returns ~instantly; GUI runs detached)

**Never** tell the operator "set DISPLAY" or "install an X server on
Windows" -- WSLg already provides DISPLAY=:0 + WAYLAND_DISPLAY=wayland-0
+ /tmp/.X11-unix/X0 + /mnt/wslg/PulseServer automatically.

### `mios-build-status` and `mios-build-tail` — build introspection

```
mios-build-status            # last log path/size/state + 30 lines tail
mios-build-status 200        # ... + 200 lines tail
mios-build-tail              # raw last 100 lines of newest log
mios-build-tail -f           # follow live (tail -f)
mios-build-tail -n 500       # last 500 lines
```

`mios-build-status` answers "how's the build going" with a
structured header (path, size, mtime, RUNNING/FAILED/completed state,
OCI image artifact if produced) plus a tail. Use this to check on a
build the operator started; never `find /var/log/mios/build-driver-*.log`
and grep -- this command knows about the `/tmp/` fallback the driver
writes to before its namespace escape fires.

### `mios-windows <powershell-command>` — reach the Windows host

```
mios-windows 'Get-Service vmcompute | Format-List Name,Status'
mios-windows 'Get-NetIPAddress -AddressFamily IPv4'
mios-windows 'Get-Process | Where-Object Name -match "vmwp|vmmem"'
```

SSHes to the Windows host (this WSL distro's parent) via Tailscale.
USE THIS when the operator reports a Windows-side problem the agent
can't reach from inside WSL: WSL service wedged, Windows Firewall
rule missing, vmcompute restart needed, Hyper-V state check, etc.

The Tailscale path doesn't need a port-22 hole on the LAN -- auth is
the operator's tailnet identity, ACL-gated. **Non-elevated**: for
elevated Windows operations (Restart-Service, New-NetFirewallRule,
registry writes) the operator still needs to run those manually
unless they've configured UAC "elevate without prompting" or the
SYSTEM-level scheduled-task escape hatch (see
`/usr/share/doc/mios/guides/agent-windows-ssh.md`).

### `mios-open-url <url>` — open a URL in the operator's browser

```
mios-open-url https://github.com/mios-dev/MiOS
mios-open-url https://localhost:8080
```

Resolves through the broker (`/run/mios-launcher/launcher.sock`) so it
works from BOTH the operator's shell AND the agent's service-user
context. Lands the URL in ChromeDev (the operator's preferred browser,
set in `mios.toml [browser]`). Don't `xdg-open` -- xdg-open inside the
agent's PrivateTmp + service-user context can't reach the operator's
display surface.

### `mios-windows launch <app>` / `mios-pc-control <subcmd>` — control the Windows host

```
mios-windows launch notepad
mios-windows launch chrome https://example.com
mios-windows ps 'Get-Date'                  # one-shot PowerShell on Windows
mios-windows list                            # what's installed

mios-pc-control window-list                 # Win32 EnumWindows -> table
mios-pc-control window-focus 'Visual Studio Code'
mios-pc-control window-move 'Notepad' 100 100 800 600
mios-pc-control screenshot /tmp/screen.png
mios-pc-control click 540 300                # Win32 SendInput at (x,y)
mios-pc-control type 'hello world'           # types into focused window
mios-pc-control key-combo ctrl+shift+t
```

These are the Path-A (command-driven) and Path-B (Win32 input)
surfaces for native Windows control from inside WSL/the agent.
`mios-windows` covers launch/enumerate/PS-one-shot; `mios-pc-control`
covers Win32 input + GDI capture + EnumWindows. **No vision needed
for any of the above** -- they all use direct Win32 APIs through a
bundled PowerShell sidecar (`mios-pc-control.ps1`).

### `mios-pc-vision <image> <description>` — screenshot → click coords

```
mios-pc-control screenshot /tmp/s.png
mios-pc-vision /tmp/s.png "the start button"
# -> {"x": 18, "y": 1058, "confidence": 0.92, "reasoning": "..."}
mios-pc-control click 18 1058
```

Vision-grounded UI control via `qwen3-vl:4b` (configurable at
`mios.toml [ai].vision_grounding_model`). Use this when there is no
window-title / hot-key shortcut and you need to point at something on
the screen. Three steps: capture, ground, click. Don't try to use a
non-vision LLM for this -- pixel-accurate 2D coordinates need a vision
model with native grounding.

## Observability layer (always-on micro-LLM)

A persistent ~600 MB micro-LLM (`qwen3:0.6b`) lives in VRAM via
`keep_alive=-1`. Two daemons consume it:

### `mios-log-watcher` — journal triage

```
cat /var/lib/mios/log-watcher/latest.json
# -> {"timestamp": "...", "events_count": 7, "summary": "...",
#     "tags": ["service-restart", "noise"], "severity": "low"}
tail /var/lib/mios/log-watcher/summary.jsonl
```

Streams `journalctl -f` (PRIORITY=4 / warning+), batches every 30s,
asks the micro-LLM for `{summary, tags, severity}`. Cheap (~30 s of
CPU per hour). Read `latest.json` when the operator asks "what's
been going on" or you want a system-state snippet to inform a
decision. Tags: `service-restart`, `service-fail`, `auth-fail`, `OOM`,
`disk-pressure`, `network`, `container-event`, `agent-event`,
`hardware`, `selinux`, `security`, `noise`.

### `mios-cron-director` — LLM-gated scheduler

```
cat /etc/mios/cron-rules.toml
systemctl status mios-cron-director           # daemon status
journalctl -u mios-cron-director -n 30        # what fired / what was gated off
systemctl kill -s HUP mios-cron-director      # reload rules without restart
```

Reads `/etc/mios/cron-rules.toml`. Each `[[rule]]` is `cron + do +
optional gate`. When the cron matches, the gate (if present) is
evaluated by the micro-LLM with current system state -- YES fires
the `do` command, NO skips. Lives ALONGSIDE Hermes's in-process
cronjob_tool (which fires PROMPTS in the gateway) + the host's
`crond` (raw shell). Operators add rules by editing the toml + SIGHUP.

### `mios-micro-llm` — direct micro-LLM access

```
mios-micro-llm classify "Is the load high? loadavg=0.8"
mios-micro-llm warm                           # ensure it's loaded
mios-micro-llm status                         # endpoint + model + keep-alive
```

If you need a cheap one-shot classification yourself, route through
this -- don't pull the heavy chat model into a binary decision.

### `mios-restart <svc>` — smart service restart

```
mios-restart hermes              # hermes-agent.service + drop skills cache
mios-restart open-webui          # mios-open-webui.service
mios-restart ollama              # mios-ollama.service
mios-restart chrome              # not a service -- pkill bwrap+chrome instead
```

Knows the **podman vs systemctl** distinction: Quadlet-managed containers
MUST be restarted via `systemctl restart`, never `podman restart`
(podman's restart desyncs systemd's view, the unit gets ExecStop'd ~1
minute later, the container is killed -- operator-confirmed regression
2026-05-15). For `mios-restart hermes` it also drops the in-process
skills-prompt cache so freshly-edited SOUL.md / SKILL.md files take
effect on the very next chat without a second restart.

Aliases: `hermes`, `ollama`, `open-webui`/`owui`, `searxng`, `forge`,
`forge-runner`, `code-server`/`code`, `crowdsec`, `k3s`. Or pass a full
unit name (`mios-restart mios-anything.service`).

## The privileged build (`sudo mios build`)

The operator-facing entry point is `mios build`. Variants:

```
sudo mios build                  # interactive (TTY-driven configurator)
mios build                       # the agent's path -- preflight + escape are automatic
```

The driver (`/usr/libexec/mios/mios-build-driver`) does several MiOS-
specific things you do NOT need to reproduce by hand:

  1. **Privilege preflight** -- fails FATAL with a clear message if
     neither root nor passwordless sudo is available.
  2. **Mount-namespace escape** -- if invoked from inside a service
     namespace where `/var/lib/containers/storage` is read-only (e.g.,
     hermes-agent.service has ProtectSystem=strict), re-execs via
     `sudo systemd-run --pipe --wait` to escape into a fresh PID-1-
     forked unit with the host's writable mount view. Works whether
     you call `sudo mios build` or `mios build` (driver self-elevates).
  3. **Always pull from origin** -- `git pull --ff-only origin <branch>`
     before any work, with 3 retries + 30s Ctrl+C countdown on TTY,
     skip with `MIOS_NO_PULL=1`.
  4. **Bound-images bake** -- pulls every Quadlet's `Image=` into
     `/usr/lib/containers/storage` as part of the OCI build; bootc
     install-to-filesystem then resolves bound images from there with
     ZERO runtime pulls.
  5. **Exits non-zero on any BIB format failure** so the agent doesn't
     fabricate a "build succeeded" reply on partial success.

**For long-running operations like `mios build` (15-20 min):** ALWAYS
launch via `terminal(command="sudo mios build", background=True,
notify_on_complete=True)` -- never wrap the build in a synchronous
`terminal()` call. The synchronous form blocks your reply for the
entire build duration, OWUI's HTTP fetch times out (NetworkError on
the operator's side), and your work is wasted. The background form
returns ~instantly with a session id; the harness re-invokes you
when the build finishes. Between launch and notification you can use
`mios-build-status` to peek at progress.

## Service map (what listens on which port)

```
hermes-agent.service            DIRECT host install (NOT a container)
                                 :8642  OpenAI-compat gateway
                                 :9119  Hermes dashboard
mios-ollama.service             :11434 raw inference + embeddings
mios-open-webui.service         :3030  browser UI (-> hermes :8642)
mios-searxng.service            :8888  privacy search (Hermes web tool)
mios-forge.service              :3000  Forgejo git server
mios-forgejo-runner.service     -      runner (no public port)
mios-code-server.service        :8080  VSCode-in-browser
mios-crowdsec.service           -      log analysis (no public port)
mios-k3s.service                :6443  Kubernetes API (skipped on WSL)
```

The AI chain runs *through* hermes:
`ollama (:11434)` <- `hermes-agent (:8642)` <- `OWUI (:3030)`. OWUI talks
to hermes, NOT to ollama directly -- so the agent's tool-calling /
sessions / kanban / skills surface is what OWUI serves
(Architectural Law 5: UNIFIED-AI-REDIRECTS).

## Canonical paths

```
/                              git working tree (yes, the literal /)
/.git                          system repo's .git (read-only inside the
                                 agent service namespace; auto-escape if writing)
/var/lib/mios/git/mios.git     local git mirror (build pulls from here)
/var/lib/mios/build/           build workspace (build-context, BIB outputs)
/var/log/mios/                 build logs (build-driver-YYYYMMDD-HHMMSS.log)
/usr/libexec/mios/             helper scripts (this file's authors)
/usr/share/mios/               vendor read-only (ai/, hermes/skills/, mios.toml)
/usr/share/mios/hermes/skills/ MiOS-managed skills (parallel-fanout,
                                 mios-environment <- you are here)
/etc/mios/                     operator overlays (config, secrets.env, ...)
/etc/mios/mios.toml            host-level mios.toml override layer
/var/lib/mios/hermes/          gateway service home (HERMES_HOME)
/var/home/mios/.hermes/        operator CLI home
/var/lib/mios/open-webui/      OWUI persistent state (webui.db lives here)
/etc/containers/systemd/       Quadlet definitions (.container, .network, .volume)
/usr/lib/bootc/bound-images.d/ symlinks driving the bake step
/usr/lib/containers/storage/   baked image store (additionalimagestores)
/etc/sudoers.d/10-mios-hermes  operator-authorised sudo grant for the agent
```

## Reference docs (read on demand, not by default)

```
/usr/share/mios/ai/system.md        canonical agent system prompt
/usr/share/mios/ai/INDEX.md         architecture + service map (longer form)
/usr/share/mios/ai/audit-prompt.md  review/audit checklist
/usr/share/mios/ai/v1/              versioned data surface (JSON):
                                       models.json, tools.json, mcp.json,
                                       surface.json, context.json, config.json,
                                       system-prompts.json, knowledge.md
/usr/share/mios/ai/hermes-soul.md   YOUR persona + the 9 truthfulness rules
                                       (this file is reloaded fresh every message)
/AGENTS.md /CLAUDE.md               repo-root architectural laws + agent guidance
/usr/share/mios/mios.toml           vendor SSOT for tunables (image refs,
                                       host thresholds, ports, sidecar versions)
```

## Pitfalls that have bitten the agent (so you can skip them)

1. **`df` does NOT show mount read-only state.** Use
   `findmnt -n -o OPTIONS /path` or `cat /proc/self/mountinfo` or just
   try writing (`: > /path/.probe`). `df`'s `Use%` column is bytes used,
   nothing about mount options.

2. **`podman restart <name>` desyncs Quadlet units.** Always use
   `systemctl restart <name>.service` for any container that lives
   under `/etc/containers/systemd/`. Use `mios-restart` to do it right.

3. **`sudo` does NOT escape mount namespaces.** It changes UID/GID and
   capabilities; the child inherits the parent's mount namespace.
   The build driver and flatpak-launch both auto-escape via
   `systemd-run` -- you don't need to reproduce that, just call them.

4. **`hermes setup` writes a destructive stub** that drops every MiOS
   customisation (auxiliary lanes, delegation, agent.reasoning_effort,
   approvals). Never re-run it on a MiOS host. Firstboot owns the
   config; if it's broken, run `sudo systemctl restart mios-hermes-firstboot`
   (or just `mios-restart hermes` after the gateway config is fixed).

5. **OWUI's chat fetch times out around 60s** for synchronous tool
   calls. Long-running commands (`mios build`, `bootc upgrade`,
   `dnf install`, large `git clone`, big downloads) ALWAYS go in
   `background=True, notify_on_complete=True`. See SOUL.md rule 9.

6. **Skill files cache via mtime/size** in `.skills_prompt_snapshot.json`.
   When you (or the operator) edit a skill, run `mios-restart hermes`
   -- it drops the snapshot cache. Otherwise the next chat reads the
   stale skill index.

## Where to look when something's wrong

Almost every "something's wrong" investigation should start with:

```
mios-doctor
```

If that passes 0 failures and the operator still has a complaint, the
problem is more specific than infrastructure -- ask them to paste the
literal output of whatever they tried, then go from there. Do NOT
guess from training-data priors about WSL, Linux desktops, flatpak in
general, or sudo subtleties. This host has its own answers, all
documented above, all reachable via the helpers.
