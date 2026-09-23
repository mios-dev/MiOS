<!-- AI-hint: Guide for connecting to GitHub Codespaces and Google Cloud Shell visual dev environments using Blink Shell on iOS. -->
<!-- AI-related: /usr/share/doc/mios/README.md, usr/share/mios/blink/shortcuts.json, usr/share/mios/blink/snips/cs.sh, usr/share/mios/blink/snips/gcp.sh -->

# Blink Shell: Visual Dev Environments & Shortcuts for MiOS

This guide explains how to configure **Blink Shell** on iPhone and iPad to connect directly to **GitHub Codespaces** and **Google Cloud Shell** environments for MiOS project development using both visual web editors and optimized mobile terminal sessions.

---

## 1. Visual Web Dev Environments in Blink Shell

Blink Shell integrates a high-performance WebKit engine and the `code` command, allowing developers to run full visual VS Code environments directly inside the iOS app without leaving the terminal context.

### A. GitHub Codespaces

To launch the full visual Codespaces environment for MiOS:

```bash
# In Blink Shell:
code https://github.com/codespaces/new?repo=mios-dev/MiOS
```

Or for an instant, lightweight repository view:

```bash
code https://github.dev/mios-dev/MiOS
```

### B. Google Cloud Shell

To launch Google Cloud Shell with the pre-configured visual IDE containing the MiOS workspace:

```bash
code "https://shell.cloud.google.com/?show=ide&cloudshell_git_repo=https://github.com/mios-dev/MiOS"
```

This automatically clones the MiOS repository and opens Cloud Shell Editor with the devcontainer ready to bootstrap.

---

## 2. Installing MiOS Blink Shell Snips

MiOS provides pre-packaged snip scripts under [`/usr/share/mios/blink/snips/`](file:///usr/share/mios/blink/snips/) that streamline launching both visual web IDEs and mobile-optimized terminal sessions.

### Step 1: Copy Snips into Blink Shell

From your iOS device, copy the snip files into Blink Shell's local storage:
- In Blink Shell, navigate to `~/Documents/snips` (accessible via the iOS Files app under `On My iPhone/iPad > Blink > snips`).
- Copy:
  - `cs.sh` -> Save as `cs` (or `cs.sh`)
  - `gcp.sh` -> Save as `gcp` (or `gcp.sh`)
  - `mios-web.sh` -> Save as `mios-web` (or `mios-web.sh`)

Ensure permissions are executable in Blink Shell:
```bash
chmod +x ~/Documents/snips/cs ~/Documents/snips/gcp ~/Documents/snips/mios-web
```

### Step 2: Using the Snips

```bash
# Launch visual Codespaces in Blink
snip cs web

# Attach to active Codespace SSH with mobile keyboard support
snip cs ssh

# Launch Google Cloud Shell visual IDE
snip gcp web

# Launch Google Cloud Shell terminal
snip gcp term

# Launch local MiOS visual web surfaces (Open WebUI, Code-Server, Cockpit)
snip mios-web owui
snip mios-web code
snip mios-web cockpit
```

---

## 3. Blink Shell SmartBar Shortcuts

You can bind these shortcuts directly to the Blink Shell on-screen SmartBar for instant one-tap access on iPhone:

1. In Blink Shell, type `config` to open settings.
2. Select **Keyboard** > **Custom Keys** / **SmartBar**.
3. Add custom SmartBar buttons:
   - Label: `CS-Web` -> Action: Run command -> `code https://github.com/codespaces/new?repo=mios-dev/MiOS`
   - Label: `GCP-IDE` -> Action: Run command -> `code https://shell.cloud.google.com/?show=ide&cloudshell_git_repo=https://github.com/mios-dev/MiOS`
   - Label: `CS-SSH` -> Action: Run command -> `snip cs ssh`
   - Label: `⇧⇥` (Backtab) -> Action: Send characters -> `\e[Z`

---

## 4. iOS Shortcuts Integration (One-Tap Homescreen Launch)

Blink Shell supports the `blinkshell://` URL scheme, allowing you to create iOS Shortcuts that launch directly from your iPhone Home Screen or Action Button:

| Action | iOS Shortcut URL Scheme |
|---|---|
| **Codespaces Web IDE** | `blinkshell://run?cmd=code%20https%3A%2F%2Fgithub.com%2Fcodespaces%2Fnew%3Frepo%3Dmios-dev%2FMiOS` |
| **Cloud Shell Web IDE** | `blinkshell://run?cmd=code%20https%3A%2F%2Fshell.cloud.google.com%2F%3Fshow%3Dide%26cloudshell_git_repo%3Dhttps%3A%2F%2Fgithub.com%2Fmios-dev%2FMiOS` |
| **Codespaces Terminal** | `blinkshell://run?cmd=snip%20cs%20ssh` |
| **Cloud Shell Terminal** | `blinkshell://run?cmd=snip%20gcp%20term` |
| **MiOS Open WebUI** | `blinkshell://run?cmd=code%20http%3A%2F%2Flocalhost%3A8080` |

All definitions and schemas are cataloged in [`/usr/share/mios/blink/shortcuts.json`](file:///usr/share/mios/blink/shortcuts.json).

---

## 5. Tmux Mobile Keys Integration

When connecting via SSH, the snips automatically load [`/usr/share/mios/tmux/blink-mobile-keys.tmux.conf`](file:///usr/share/mios/tmux/blink-mobile-keys.tmux.conf), enabling:
- True `Shift + Tab` backtab pass-through (`\033[Z`).
- Mobile touch-friendly navigation (`Prefix + Tab`, `M-Tab`).
- Extended terminal protocol (`extended-keys on`) for key combinations in `vim`, `fzf`, and `zsh`.
