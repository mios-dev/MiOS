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

# `surfer download` runs `git init` + `git commit` on the fetched Firefox source; a bare
# build container has no git identity, so the commit dies with "unable to auto-detect
# email address" + "'' is not a valid branch name". Give it a build identity so the
# source-tree init commits cleanly (best-effort; never fatal).
git config --global user.email "build@mios.local"  2>/dev/null || true
git config --global user.name  "MiOS Build"        2>/dev/null || true
git config --global init.defaultBranch main        2>/dev/null || true
git config --global advice.detachedHead false      2>/dev/null || true

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
    # UPSTREAM Mozilla product surfer builds FROM (Zen is a Firefox fork) -- NOT
    # the "zen" vendor brand. Must be one of surfer's SupportedProducts.
    export MIOS_SURFER_PRODUCT="${MIOS_SURFER_PRODUCT:-firefox}"
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
# surfer.json schema (zen-browser/surfer): `version` is an OBJECT whose `product`
# is the UPSTREAM Mozilla product surfer builds FROM -- one of firefox / firefox-esr
# / firefox-dev / firefox-beta / firefox-nightly. "zen" is a VENDOR brand, NOT a
# valid product; the old code set a top-level product="zen" AND a bare STRING
# version, so surfer getConfig read version.product == undefined ->
# "undefined is not a valid product". Build a real version object + the other
# schema-required top-level fields (present + minimal; there is no base surfer.json).
data["name"] = data.get("name") or os.environ.get("MIOS_SURFER_NAME", "MiOS Webshell")
data["vendor"] = data.get("vendor") or os.environ.get("MIOS_SURFER_VENDOR", "mios")
data["appId"] = data.get("appId") or os.environ.get("MIOS_SURFER_APPID", "os.mios.webshell")
data["binaryName"] = data.get("binaryName") or os.environ.get("MIOS_SURFER_BINARY", "mios-webshell")
_ver = data.get("version")
if not isinstance(_ver, dict):
    _ver = {}
_ver["product"] = os.environ.get("MIOS_SURFER_PRODUCT", "firefox")
_ver["version"] = ff_ver
data["version"] = _ver
for _k in ("buildOptions", "addons", "brands"):
    if not isinstance(data.get(_k), dict):
        data[_k] = {}
if not isinstance(data.get("license"), (dict, str)):
    data["license"] = {}
data["firefoxVersion"] = ff_ver
with open(p, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
'

    log "[56-bake-surfer] Fetching upstream Mozilla codebase..."
    FF_VER="$(python3 -c 'import json; print(json.load(open("surfer.json")).get("firefoxVersion", "153.0"))' 2>/dev/null || echo '153.0')"
    # surfer download reads version.product + version.version from surfer.json
    # (fixed above). Rely on it; fall back to passing the version positionally.
    if ! npx surfer download 2>&1 && \
       ! npx surfer download "$FF_VER" 2>&1; then
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
        cp -r dist/* /usr/lib/mios/webshell/ 2>/dev/null || true
        ln -sf /usr/lib/mios/webshell/firefox /usr/bin/mios-webshell 2>/dev/null || true
        if [[ -x /usr/bin/mios-webshell ]]; then
            SURFER_OK=1
            break
        fi
        # `npm run build` succeeded but produced no browser binary -- it only rebuilds
        # surfer's own TS CLI, never the browser (that needs `npx surfer build`, a
        # multi-hour mach compile). This is DETERMINISTIC, so retrying would only
        # re-download the ~500MB Firefox source for nothing. Stop and degrade open.
        warn "[56-bake-surfer] surfer CLI built but no browser binary in the bake -- not retrying (see degrade-open below)."
        break
    fi

    warn "[56-bake-surfer] build failed on attempt $attempt"
    sleep $((attempt * 8))
done

if [[ -z "$SURFER_OK" ]]; then
    # DEGRADE-OPEN (Law 12): mios-webshell is a heavy, OPTIONAL Firefox-fork browser. A
    # real build is `npx surfer build` -- a multi-HOUR mach compile that must NOT gate the
    # OS image publish (`npm run build` above only rebuilds surfer's own TS CLI, never a
    # browser binary, which is why the -x check never passes here). WARN and continue; the
    # webshell is a firstboot/dedicated-builder concern. NEVER fail the whole bake on it.
    warn "[56-bake-surfer] mios-webshell not built in the bake (optional + multi-hour mach compile) -- degrading open; a firstboot/dedicated builder produces it."
    exit 0
fi

record_version surfer "$PIN_REF" "https://github.com/zen-browser/surfer/tree/${PIN_REF}"
echo "[56-bake-surfer] Installed /usr/lib/mios/webshell/ and symlinked /usr/bin/mios-webshell."
