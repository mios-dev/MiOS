#!/bin/bash
# AI-hint: Node builder script to pull the zen-browser surfer repository, download the upstream Firefox codebase, apply structural three-pane browser UI patches, and run native mach compilations.
# AI-related: /usr/bin/mios-webshell, /usr/lib/mios/webshell/, usr/share/mios/mios.toml [colors]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# tools/lib/userenv.sh (sourced via lib/common.sh, the same convention every
# other automation/*.sh script uses) already exports MIOS_COLOR_* from
# mios.toml [colors] -- this script previously hardcoded Catppuccin Mocha
# literals here instead of using them (Law 7 gap; see design spec
# usr/share/doc/mios/concepts/mios-app-browser-portal-dashboard-design-*.md
# §8/§12). Best-effort: if common.sh/userenv.sh can't be located, the
# `${VAR:-default}` fallbacks below keep this script working exactly as
# before (degrade-open).
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh" 2>/dev/null || true

echo "[56-bake-surfer] Preparing surfer directory..."
SURFER_BUILD_DIR="/tmp/surfer-build"
rm -rf "$SURFER_BUILD_DIR"
git clone --depth 1 "${MIOS_URL_SURFER:-https://github.com/zen-browser/surfer.git}" "$SURFER_BUILD_DIR"

cd "$SURFER_BUILD_DIR"
npm install

echo "[56-bake-surfer] Fetching upstream Mozilla codebase..."
npx surfer download

# Apply three-pane layout patch inside chrome://browser/content/browser.xhtml
# This splits the main content area into:
#  - [left] mios-custom-sidebar (sidebar navigational cockpit)
#  - [center] appcontent (standard Gecko rendering viewport)
#  - [right] mios-ai-sidebar (agent discussion panel)
echo "[56-bake-surfer] Applying custom layout patches to browser.xhtml..."
# SSOT colors (Law 7): mios.toml [colors] -- deep indigo bg, operator-blue
# border, operator-blue AI panel (distinguishes the agent pane from the nav
# pane, both keyed off the same brand palette the Portal/Configurator/
# Quickshell shell already use). Previously hardcoded to Catppuccin Mocha
# (#1e1e2e/#313244/#181825), which matched no other MiOS surface.
: "${MIOS_COLOR_BG:=#282262}"
: "${MIOS_COLOR_ACCENT:=#1A407F}"
: "${MIOS_COLOR_SUBTLE:=#B7C9D7}"
cat << EOF > /tmp/browser_xhtml_patch.xml
<!-- Add sidebar panels for navigation cockpit and AI interaction to browser.xhtml -->
<hbox flex="1" id="mios-three-pane-container">
  <vbox id="mios-custom-sidebar" width="220" style="background-color: ${MIOS_COLOR_BG}; border-right: 1px solid ${MIOS_COLOR_SUBTLE};">
    <vbox id="mios-panel-cockpit" flex="1">
      <!-- Nav cockpit & System controls -->
      <button label="Local Dashboard" oncommand="loadURI('http://localhost:8033/')" />
      <button label="Container Status" oncommand="loadURI('http://localhost:8642/v1/cluster/health')" />
    </vbox>
    <hbox id="mios-action-area" style="padding: 10px; border-top: 1px solid ${MIOS_COLOR_SUBTLE};">
      <button id="mios-terminal-trigger" label="Launch Terminal" oncommand="launchTerminalAsync()" style="flex: 1;" />
    </hbox>
  </vbox>
  <splitter id="mios-sidebar-splitter" resizebefore="grow" resizeafter="shrink" class="chromeclass-extrachrome" />
  <vbox id="appcontent" flex="1" />
  <splitter id="mios-ai-splitter" resizebefore="grow" resizeafter="shrink" class="chromeclass-extrachrome" />
  <vbox id="mios-ai-sidebar" width="300" style="background-color: ${MIOS_COLOR_ACCENT};">
    <!-- Local AI agent panel -->
    <browser id="mios-ai-frame" src="http://localhost:3030" flex="1" />
  </vbox>
</hbox>
EOF

# Integrate layout patch using surfer importer
npx surfer import /tmp/browser_xhtml_patch.xml

echo "[56-bake-surfer] Starting native compilation..."
npm run build

echo "[56-bake-surfer] Staging compiled binary..."
mkdir -p /usr/lib/mios/webshell
cp -r dist/* /usr/lib/mios/webshell/
ln -sf /usr/lib/mios/webshell/firefox /usr/bin/mios-webshell

echo "[56-bake-surfer] Custom webshell built successfully."
