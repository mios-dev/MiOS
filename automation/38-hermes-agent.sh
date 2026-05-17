#!/bin/bash
# automation/38-hermes-agent.sh
#
# Install Hermes-Agent DIRECTLY onto the MiOS root filesystem -- not as
# a container. Operator directive 2026-05-13: "Hermes-Agent should be
# installed on the Local MiOS-DEV machine directly at the root
# directory and ALL other MiOS Images/deployment types".
#
# Rationale: Hermes-Agent IS the live MiOS agent at `/` (AGENTS.md §6).
# A container boundary between the agent and the system it operates on
# meant the agent couldn't see the real root FS / systemd / git tree
# without bind-mount gymnastics. A direct host install removes that
# boundary: the agent runs as a host systemd service (hermes-agent.
# service), sees `/` natively, and uses the ollama CONTAINER as a
# swappable OpenAI-compatible inference backend.
#
# CRITICAL: this script MUST NOT fail the OCI build. Network egress,
# PyPI, and git are best-effort at build time -- if any step fails the
# script logs a warning and `exit 0`s. hermes-agent.service carries
# ConditionPathExists so it cleanly no-ops on hosts where the install
# didn't land; `mios update` / a firstboot retry can complete it later.
#
# TOML-first: HERMES_REPO/REF resolve from MIOS_HERMES_AGENT_* env vars
# (exported by tools/lib/userenv.sh from mios.toml [ai].hermes_agent_*),
# with the canonical upstream as the `:-` shell default -- the same
# pattern 37-ollama-prep.sh uses for MIOS_OLLAMA_BAKE_MODELS.
#
# NO `set -e` -- a sub-failure here must never cascade into a build
# failure. Explicit guards + `exit 0` everywhere.
set -uo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[38-hermes-agent] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

HERMES_REPO="${MIOS_HERMES_AGENT_REPO:-https://github.com/NousResearch/hermes-agent.git}"
HERMES_REF="${MIOS_HERMES_AGENT_REF:-main}"
VENV_ROOT=/usr/lib/mios/hermes-agent          # vendor code (FHS /usr/lib)
VENV_DIR="${VENV_ROOT}/.venv"
BIN_DIR="${VENV_ROOT}/bin"

log "[38-hermes-agent] direct install: repo=${HERMES_REPO} ref=${HERMES_REF}"

# Tooling preflight -- python3 + pip + git must all be present. They're
# pulled by [packages.base] (git) + policycoreutils-python-utils
# (python3). If any is missing, skip cleanly rather than die.
_missing=""
for tool in python3 git; do
    command -v "$tool" >/dev/null 2>&1 || _missing="${_missing} ${tool}"
done
if [[ -n "$_missing" ]]; then
    warn "[38-hermes-agent] missing build tools:${_missing} -- skipping direct install (hermes-agent.service will no-op via ConditionPathExists)"
    exit 0
fi

install -d -m 0755 "${VENV_ROOT}" "${BIN_DIR}" || { warn "[38-hermes-agent] mkdir ${VENV_ROOT} failed -- skipping"; exit 0; }

# Build the venv. pip install directly from the git ref -- no editable
# checkout, no leftover src tree in the image.
if ! python3 -m venv "${VENV_DIR}" 2>/dev/null; then
    warn "[38-hermes-agent] python3 -m venv failed -- skipping direct install"
    exit 0
fi

# `pip install git+URL@ref` plus the must-have soft-deps -- single
# step, network best-effort.
#   * aiohttp -- REQUIRED by hermes-agent's api_server adapter (the
#     OpenAI /v1 surface). The base package doesn't pull it as a hard
#     dep, so the gateway starts but logs "API Server: aiohttp not
#     installed / No adapter available for api_server" and /v1 never
#     comes up (operator-confirmed 2026-05-14).
#   * websockets -- REQUIRED by tools/browser_dialog_tool +
#     tools/browser_supervisor (CDP WebSocket client). Without it,
#     Hermes prints "Could not import tool module
#     tools.browser_dialog_tool: No module named 'websockets'" on
#     every gateway start and the browser tool's dialog detection +
#     CDP supervisor never wake up (operator-confirmed 2026-05-15
#     when wiring the ChromeDev flatpak as the local CDP backend).
#   * discord.py -- REQUIRED by hermes-agent's discord adapter +
#     tools/discord_tool. Without it the gateway logs "Discord:
#     discord.py not installed / No adapter available for discord"
#     and `discord_send_message` returns ENOENT even with a valid
#     DISCORD_BOT_TOKEN (operator-confirmed 2026-05-17). audioop-lts
#     comes in transitively (Python 3.13+ dropped stdlib audioop).
#     Pinned <3 because discord.py 3.x is a partial rewrite still
#     in pre-release.
# --no-input keeps it non-interactive; failure here is non-fatal.
if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check \
        "git+${HERMES_REPO}@${HERMES_REF}" aiohttp websockets "discord.py>=2.4,<3" 2>&1 | tail -5; then
    :
else
    warn "[38-hermes-agent] pip install git+${HERMES_REPO}@${HERMES_REF} + soft-deps failed (network? PyPI?) -- removing partial venv, skipping"
    rm -rf "${VENV_DIR}"
    exit 0
fi

# The pip install drops a `hermes` entry-point into the venv's bin.
# Verify it landed; symlink it to a stable vendor path the
# /usr/bin/hermes wrapper + hermes-agent.service both reference.
if [[ -x "${VENV_DIR}/bin/hermes" ]]; then
    ln -sf "${VENV_DIR}/bin/hermes" "${BIN_DIR}/hermes"
    log "[38-hermes-agent] installed: ${VENV_DIR}/bin/hermes -> ${BIN_DIR}/hermes"
    record_version "hermes-agent" "${HERMES_REF}" "$(${VENV_DIR}/bin/hermes --version 2>&1 | head -1)" 2>/dev/null || true
else
    warn "[38-hermes-agent] pip succeeded but no 'hermes' entry-point in venv -- skipping symlink"
    exit 0
fi

# ─── Plugin manifests for bundled providers ──────────────────────────
# Hermes 0.13.x's plugin loader (hermes_cli/plugins.py) discovers
# bundled backends by scanning plugins/<category>/<name>/plugin.yaml.
# The upstream pip wheel ships the python sources (plugins/web/searxng/
# __init__.py, provider.py) but NOT a plugin.yaml manifest, so the
# loader logs "Skipping ... (no plugin.yaml, depth cap reached)" and
# the provider never registers -- web_search returns "No web search
# provider configured" even with web.search_backend: searxng in
# config.yaml (operator-confirmed 2026-05-17: hermes returned the
# error verbatim until plugin.yaml was created). Drop the manifest
# alongside each bundled backend so cold-installed images get a
# working web_search loop with zero extra runtime steps.
#
# Discover the python version dir under lib/ -- python3.14 today,
# may bump on Fedora major upgrades; glob keeps this resilient.
shopt -s nullglob
for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
    searxng_dir="${site_packages}/plugins/web/searxng"
    if [[ -d "$searxng_dir" && ! -f "${searxng_dir}/plugin.yaml" ]]; then
        cat > "${searxng_dir}/plugin.yaml" <<'YAML'
name: searxng
kind: backend
version: 1.0.0
description: SearXNG web-search provider (local self-hosted instance at mios-searxng:8888).
register: plugins.web.searxng:register
YAML
        log "[38-hermes-agent] seeded ${searxng_dir#${VENV_DIR}/}/plugin.yaml"
    fi
done
shopt -u nullglob

# ─── Dashboard plugin manifests + dist (backend-only mode) ───────────
# The upstream pip wheel ships plugins/<name>/dashboard/plugin_api.py
# (the FastAPI routes) but strips manifest.json + dist/ from the
# wheel (setuptools.packages.find by default only ships *.py files).
# Without dashboard/manifest.json, hermes_cli.web_server's
# _discover_dashboard_plugins() can't see the plugin -- the kanban tab
# never registers, /api/plugins/kanban/* never mounts.
#
# Fetch them via a shallow git archive (no working tree, no
# lifecycle scripts) so fresh image builds get the kanban board API
# without operator hand-installs. The dashboard SPA itself
# (hermes_cli/web_dist/) is intentionally NOT built here: it requires
# `npm install` from an untrusted dep graph, which the operator opted
# out of (2026-05-17). Backend-only mode falls back to
# /usr/share/mios/hermes-agent/web_dist_stub/index.html (shipped via
# system-files-overlay) -- a single-page explainer + curl recipes.
# To enable the SPA, follow the instructions on the stub page.
if command -v git >/dev/null 2>&1; then
    DASH_TMP=$(mktemp -d)
    if (cd "$DASH_TMP" && git archive --remote="${HERMES_REPO}" "${HERMES_REF}" plugins 2>/dev/null | tar -x 2>/dev/null) ||
       git clone --depth 1 --branch "${HERMES_REF}" --filter=blob:none --sparse "${HERMES_REPO}" "$DASH_TMP/repo" 2>&1 | tail -3 &&
       (cd "$DASH_TMP/repo" && git sparse-checkout set plugins 2>/dev/null) ; then
        DASH_SRC="$DASH_TMP/plugins"
        [[ -d "$DASH_TMP/repo/plugins" ]] && DASH_SRC="$DASH_TMP/repo/plugins"
        shopt -s nullglob
        for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
            for plugin_name in kanban example-dashboard hermes-achievements; do
                src_dash="$DASH_SRC/$plugin_name/dashboard"
                dst_dash="$site_packages/plugins/$plugin_name/dashboard"
                if [[ -d "$src_dash" && -d "$dst_dash" ]]; then
                    [[ -f "$src_dash/manifest.json" && ! -f "$dst_dash/manifest.json" ]] && \
                        cp "$src_dash/manifest.json" "$dst_dash/manifest.json"
                    if [[ -d "$src_dash/dist" ]]; then
                        mkdir -p "$dst_dash/dist"
                        cp -n "$src_dash/dist/"*.{js,css} "$dst_dash/dist/" 2>/dev/null || true
                    fi
                fi
            done
        done
        shopt -u nullglob
        rm -rf "$DASH_TMP"
        log "[38-hermes-agent] seeded plugins/{kanban,example-dashboard,hermes-achievements}/dashboard/{manifest.json,dist}"
    else
        warn "[38-hermes-agent] could not fetch upstream dashboard manifests (git archive + sparse-clone both failed); kanban tab will not appear"
        rm -rf "$DASH_TMP"
    fi
fi

# ─── Dashboard runtime deps (fastapi + uvicorn + ptyprocess) ─────────
# `hermes dashboard` requires the [web] extra (fastapi + uvicorn) which
# `pip install hermes-agent` does NOT pull in by default. Without them
# the service prints "Web UI dependencies not installed" and exits 1.
# `ptyprocess` is the POSIX-PTY wrapper hermes_cli.pty_bridge needs to
# spawn the /api/pty child (bash, with the HERMES_PTY_SHELL patch
# below). Without ptyprocess, the dashboard's /chat tab WebSocket
# closes 1011 "Chat unavailable: requires POSIX PTY" on every connect.
# Install all together inline so hermes-dashboard.service can start cold.
if ! "${VENV_DIR}/bin/python3" -c "import fastapi, uvicorn, ptyprocess" 2>/dev/null; then
    if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check \
            "fastapi>=0.110" "uvicorn[standard]>=0.30" "python-multipart" "ptyprocess>=0.7" 2>&1 | tail -3; then
        log "[38-hermes-agent] installed fastapi + uvicorn + ptyprocess into venv (dashboard runtime + /chat PTY)"
    else
        warn "[38-hermes-agent] dashboard runtime deps install failed -- hermes-dashboard.service will refuse to start"
    fi
fi

# ─── Dashboard SPA build (self-hosted, build-time only) ──────────────
# Build the React UI shell that `hermes dashboard` serves out of
# `hermes_cli/web_dist`. The upstream pip wheel doesn't ship this dir
# (you have to build it from `web/` source). Without it, `hermes
# dashboard` either aborts with --skip-build or tries to npm-install
# itself at runtime — neither is acceptable on a sealed bootc image.
#
# Build phases:
#   1. Fetch the upstream sources via shallow clone (already on the
#      box during the manifest-seed step above? not necessarily;
#      separate clone here keeps this section idempotent on re-runs).
#   2. npm install --ignore-scripts (deps are 33 standard OSS pkgs;
#      operator-audited 2026-05-17 — no analytics/trackers/sentry/
#      posthog. --ignore-scripts blocks supply-chain lifecycle hooks).
#   3. npm run build → outputs to ../hermes_cli/web_dist.
#   4. STRIP externally-hosted URLs from the bundle — runtime is
#      offline-first (Law 7). The default theme uses the @nous-
#      research/ui bundled woff2 fonts and stays clean; FIVE optional
#      theme stylesheets reference fonts.googleapis.com which the
#      strip-externals helper rewrites to data:text/css,.
#   5. Copy the patched dist into the venv at hermes_cli/web_dist.
#   6. Hermes dashboard now serves the real SPA at /, /kanban, etc.
#
# Best-effort: if nodejs/npm/git aren't installed, OR network is
# unreachable, OR the build fails, the dashboard falls back to the
# /usr/share/mios/hermes-agent/web_dist_stub HTML page shipped by the
# system-files-overlay (curl recipes + SPA-install instructions). The
# operator can always re-run this script to retry.
_BUILD_SPA() {
    command -v node >/dev/null 2>&1 || { warn "[38-hermes-agent] node not installed -- skipping SPA build (dashboard will use stub)"; return 1; }
    command -v npm  >/dev/null 2>&1 || { warn "[38-hermes-agent] npm not installed -- skipping SPA build"; return 1; }
    command -v git  >/dev/null 2>&1 || { warn "[38-hermes-agent] git not installed -- skipping SPA build"; return 1; }

    local spa_tmp
    spa_tmp=$(mktemp -d)
    if ! git clone --depth 1 --branch "${HERMES_REF}" "${HERMES_REPO}" "$spa_tmp/repo" 2>&1 | tail -3 ; then
        warn "[38-hermes-agent] SPA: clone failed"
        rm -rf "$spa_tmp"; return 1
    fi

    if ! (cd "$spa_tmp/repo/web" && npm install --ignore-scripts --no-audit --no-fund 2>&1 | tail -3); then
        warn "[38-hermes-agent] SPA: npm install failed"
        rm -rf "$spa_tmp"; return 1
    fi

    if ! (cd "$spa_tmp/repo/web" && npm run build 2>&1 | tail -8); then
        warn "[38-hermes-agent] SPA: npm run build failed"
        rm -rf "$spa_tmp"; return 1
    fi

    local built="$spa_tmp/repo/hermes_cli/web_dist"
    if [[ ! -f "$built/index.html" ]]; then
        warn "[38-hermes-agent] SPA: build produced no index.html at $built"
        rm -rf "$spa_tmp"; return 1
    fi

    # Strip externally-hosted URLs (Law 7). Helper lives next to this
    # script (build-time only; not installed onto the image).
    local strip_helper="${BASH_SOURCE[0]%/*}/support/hermes-dashboard-strip-externals.py"
    if [[ -x "$strip_helper" || -f "$strip_helper" ]]; then
        if ! python3 "$strip_helper" "$built" ; then
            warn "[38-hermes-agent] SPA: strip-externals reported leftover external refs"
            rm -rf "$spa_tmp"; return 1
        fi
    else
        warn "[38-hermes-agent] SPA: strip-externals helper missing at $strip_helper -- aborting build (would leak fonts.googleapis.com requests)"
        rm -rf "$spa_tmp"; return 1
    fi

    shopt -s nullglob
    for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
        local dst="$site_packages/hermes_cli/web_dist"
        rm -rf "$dst"
        mkdir -p "$(dirname "$dst")"
        cp -r "$built" "$dst"
        log "[38-hermes-agent] SPA: installed $(du -sh "$dst" | cut -f1) to ${dst#${VENV_DIR}/}"
    done
    shopt -u nullglob

    rm -rf "$spa_tmp"
    return 0
}

# Build is idempotent + best-effort; absent a working SPA the
# dashboard service still serves the stub /usr/share/mios/hermes-agent/
# web_dist_stub explainer page + the kanban API.
_BUILD_SPA || warn "[38-hermes-agent] dashboard SPA not built; hermes-dashboard.service will fall back to the web_dist_stub"

# ─── OpenUI generative-UI bundle (vendor offline) ────────────────────
# OWUI's OpenUI Tool (operator-supplied 2026-05-17) renders interactive
# UI (charts/forms/tables/cards/follow-ups) from a DSL. The upstream
# tool fetches its JS bundle from jsDelivr at render time -- VIOLATES
# Law 7. MiOS ships a patched copy that INLINES the bundle from
# /usr/share/mios/openui/ so iframes need zero external requests.
# This step downloads the bundle ONCE at image-build time.
_VENDOR_OPENUI="${BASH_SOURCE[0]%/*}/support/mios-vendor-openui.sh"
if [[ -x "$_VENDOR_OPENUI" || -f "$_VENDOR_OPENUI" ]]; then
    bash "$_VENDOR_OPENUI" || warn "[38-hermes-agent] OpenUI bundle download failed; render panel will report 'bundle missing' until re-run"
else
    warn "[38-hermes-agent] mios-vendor-openui.sh missing at $_VENDOR_OPENUI"
fi

# ─── /api/pty HERMES_PTY_SHELL patch (bash in the dashboard /chat tab) ───
# Upstream hardcodes the PTY child to `hermes --tui` (the Node-built
# TUI chat). MiOS-DEV ships a bash terminal in the dashboard instead:
# /chat tab renders xterm.js over /api/pty WebSocket -> bash --login -i.
# Loopback + per-session-token still gate the endpoint. Operator
# directive 2026-05-17: "do we have a react window for terminal(s)?"
# -> "Plain bash terminal" picked.
_PTY_PATCH="${BASH_SOURCE[0]%/*}/support/hermes-dashboard-shell-patch.py"
shopt -s nullglob
for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
    _ws="$site_packages/hermes_cli/web_server.py"
    if [[ -f "$_ws" && -f "$_PTY_PATCH" ]]; then
        if python3 "$_PTY_PATCH" "$_ws" 2>&1 | tail -2; then
            : # ok; idempotent — re-runs are no-ops once marker present
        else
            warn "[38-hermes-agent] HERMES_PTY_SHELL patch failed on $_ws (dashboard /chat tab will spawn hermes --tui instead of bash)"
        fi
    fi
done
shopt -u nullglob

log "[38-hermes-agent] done -- runtime: hermes-agent.service (gateway mode); backend = mios.toml [ai].hermes_backend_url"
exit 0
