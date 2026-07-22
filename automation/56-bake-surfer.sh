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
source "${SCRIPT_DIR}/lib/packages.sh"
install_packages "ai"

PIN_REF="${MIOS_BUILD_BAKE_REFS_SURFER:-17d9a1577170880cdac13dca7c3d6871716fc046}"
log "[56-bake-surfer] surfer pin ref: ${PIN_REF}"

SURFER_BUILD_DIR="/tmp/surfer-build"
SURFER_OK=""

for attempt in 1 2 3; do
    log "[56-bake-surfer] Compilation attempt $attempt/3..."
    cd /tmp
    rm -rf "$SURFER_BUILD_DIR"
    
    if ! git clone "${MIOS_URL_SURFER:-https://github.com/zen-browser/surfer.git}" "$SURFER_BUILD_DIR"; then
        warn "[56-bake-surfer] git clone failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    cd "$SURFER_BUILD_DIR"
    if ! git checkout "$PIN_REF"; then
        warn "[56-bake-surfer] git checkout to $PIN_REF failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    if ! npm install --legacy-peer-deps; then
        warn "[56-bake-surfer] npm install failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    log "[56-bake-surfer] Resolving latest Firefox version and ensuring surfer.json configuration..."
    export SURFER_PRODUCT="${SURFER_PRODUCT:-zen}"
    python3 -c '
import json, os, urllib.request
ff_ver = "153.0"
try:
    req = urllib.request.urlopen("https://product-details.mozilla.org/1.0/firefox_versions.json", timeout=10)
    vdata = json.loads(req.read().decode("utf-8"))
    ff_ver = vdata.get("LATEST_FIREFOX_VERSION") or ff_ver
except Exception:
    pass

p = "surfer.json"
data = {}
if os.path.exists(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        pass
data["product"] = os.environ.get("SURFER_PRODUCT", "zen")
data["name"] = data.get("name") or "mios-webshell"
data["binaryName"] = data.get("binaryName") or "mios-webshell"
data["firefoxVersion"] = ff_ver
data["version"] = data.get("version") or "1.0.0"
with open(p, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
'

    log "[56-bake-surfer] Fetching upstream Mozilla codebase..."
    FF_VER="$(python3 -c 'import json; print(json.load(open("surfer.json")).get("firefoxVersion", "153.0"))' 2>/dev/null || echo '153.0')"
    if ! SURFER_PRODUCT=zen npx surfer download --product zen --firefox-version "$FF_VER" 2>&1 && \
       ! SURFER_PRODUCT=zen-browser npx surfer download --product zen-browser --firefox-version "$FF_VER" 2>&1 && \
       ! SURFER_PRODUCT=zen npx surfer download "$FF_VER" 2>&1; then
        warn "[56-bake-surfer] surfer download failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    log "[56-bake-surfer] Applying custom layout patches to browser.xhtml..."
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

    if ! npx surfer import /tmp/browser_xhtml_patch.xml; then
        warn "[56-bake-surfer] surfer import patch failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    log "[56-bake-surfer] Starting native compilation..."
    if npm run build; then
        mkdir -p /usr/lib/mios/webshell
        cp -r dist/* /usr/lib/mios/webshell/
        ln -sf /usr/lib/mios/webshell/firefox /usr/bin/mios-webshell
        if [[ -x /usr/bin/mios-webshell ]]; then
            SURFER_OK=1
            break
        fi
    fi
    
    warn "[56-bake-surfer] build failed on attempt $attempt"
    sleep $((attempt * 8))
done

if [[ -z "$SURFER_OK" ]]; then
    warn "[56-bake-surfer] surfer build failed after 3 attempts."
    exit 1
fi

record_version surfer "$PIN_REF" "https://github.com/zen-browser/surfer/tree/${PIN_REF}"
echo "[56-bake-surfer] Installed /usr/lib/mios/webshell/ and symlinked /usr/bin/mios-webshell."
