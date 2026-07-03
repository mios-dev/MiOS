#!/bin/bash
# AI-hint: Node builder script to pull the zen-browser surfer repository, download the upstream Firefox codebase, apply structural three-pane browser UI patches, and run native mach compilations.
# AI-related: /usr/bin/mios-webshell, /usr/lib/mios/webshell/
set -euo pipefail

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
cat << 'EOF' > /tmp/browser_xhtml_patch.xml
<!-- Add sidebar panels for navigation cockpit and AI interaction to browser.xhtml -->
<hbox flex="1" id="mios-three-pane-container">
  <vbox id="mios-custom-sidebar" width="220" style="background-color: #1e1e2e; border-right: 1px solid #313244;">
    <vbox id="mios-panel-cockpit" flex="1">
      <!-- Nav cockpit & System controls -->
      <button label="Local Dashboard" oncommand="loadURI('http://localhost:8033/')" />
      <button label="Container Status" oncommand="loadURI('http://localhost:8642/v1/cluster/health')" />
    </vbox>
    <hbox id="mios-action-area" style="padding: 10px; border-top: 1px solid #313244;">
      <button id="mios-terminal-trigger" label="Launch Terminal" oncommand="launchTerminalAsync()" style="flex: 1;" />
    </hbox>
  </vbox>
  <splitter id="mios-sidebar-splitter" resizebefore="grow" resizeafter="shrink" class="chromeclass-extrachrome" />
  <vbox id="appcontent" flex="1" />
  <splitter id="mios-ai-splitter" resizebefore="grow" resizeafter="shrink" class="chromeclass-extrachrome" />
  <vbox id="mios-ai-sidebar" width="300" style="background-color: #181825;">
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
