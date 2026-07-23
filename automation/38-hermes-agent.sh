#!/bin/bash
# AI-hint: Installs the unified Hermes-Agent and opencode components into the MiOS agent plane, configuring the shared Python venv, systemd services, and core binaries for direct host-level agent operations.
# AI-related: build.sh, /usr/lib/mios/agents/, /usr/lib/mios/agents/.venv, /usr/lib/mios/agents, /usr/share/mios/vendored/hermes-agent, /usr/share/mios/vendored/hermes-agent.zip, /usr/share/mios/vendored/hermes_agent.whl, /usr/share/mios/vendored/, /usr/share/mios/vendored, /usr/share/mios/hermes/plugins/web/miosfetch
# AI-functions: _BUILD_SPA
# automation/38-hermes-agent.sh -- UNIFIED agent-plane install driver.
#
# Owns BOTH halves of the MiOS agent plane (hybrid merge):
#   PHASE 1  Hermes-Agent direct host install + shared venv (below)
#   PHASE 2  opencode binary fetch + opencode.json landing (end of file)
# Full-hybrid relocation: the whole agent plane lives under the
# unified tree /usr/lib/mios/agents/ -- hermes-agent/ (Hermes code + bin),
# opencode/bin/opencode (binary), opencode-gateway/ (the /v1 shim) -- and all
# three share ONE explicit python venv at /usr/lib/mios/agents/.venv (a SIBLING
# of the three agent dirs, mios.toml [ai].agent_venv) which mios-gateway-agent.service,
# mios-agent-pipe.service, mios-delegation-prefilter.service, AND mios-opencode-
# gateway.service all exec from. build.sh globs automation/[0-9][0-9]-*.sh, so a
# second 38-* file would double-run; this single 38- driver is the SoT
# and automation/39-opencode.sh has been deleted (its logic is fully absorbed here).
#
# PHASE 1 -- Install Hermes-Agent DIRECTLY onto the MiOS root filesystem
# - not as a container. Operator directive "Hermes-Agent
# should be installed on the Local MiOS-DEV machine directly at the root
# directory and ALL other MiOS Images/deployment types".
#
# Rationale: Hermes-Agent IS the live MiOS agent at `/` (AGENTS.md §6).
# A container boundary between the agent and the system it operates on
# meant the agent couldn't see the real root FS / systemd / git tree
# without bind-mount gymnastics. A direct host install removes that
# boundary: the agent runs as a host systemd service (hermes-agent.
# service), sees `/` natively, and uses the mios-llm-light lane as a
# swappable OpenAI-compatible inference backend.
#
# CRITICAL: this script MUST NOT fail the OCI build. Network egress,
# PyPI, and git are best-effort at build time -- if any step fails the
# script logs a warning and `exit 0`s. mios-gateway-agent.service carries
# ConditionPathExists so it cleanly no-ops on hosts where the install
# didn't land; `mios update` / a firstboot retry can complete it later.
#
# TOML-first: HERMES_REPO/REF resolve from MIOS_HERMES_AGENT_* env vars
# (exported by tools/lib/userenv.sh from mios.toml [ai].hermes_agent_*),
# with the canonical upstream as the `:-` shell default -- the same
# pattern 38-llamacpp-prep.sh uses for MIOS_LLAMACPP_BAKE_MODELS.
#
# NO `set -e` -- a sub-failure here must never cascade into a build
# failure. Explicit guards + `exit 0` everywhere.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[MiOS AI] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

HERMES_REPO="${MIOS_HERMES_AGENT_REPO:-https://github.com/NousResearch/hermes-agent.git}"
HERMES_REF="${MIOS_HERMES_AGENT_REF:-main}"
# Unified agent-plane tree. AGENTS_ROOT is the shared parent; the venv is an
# EXPLICIT SIBLING (agents/.venv) shared by hermes-agent + agent-pipe + the
# opencode gateway, NOT nested inside hermes-agent. VENV_ROOT holds Hermes code
# + the stable bin/ symlink. SSOT: mios.toml [ai].agent_venv (default below).
AGENTS_ROOT=/usr/lib/mios/agents
VENV_ROOT="${MIOS_HERMES_DIR:-${AGENTS_ROOT}/hermes-agent}"   # Hermes vendor code (FHS /usr/lib)
VENV_DIR="${MIOS_HERMES_VENV:-${AGENTS_ROOT}/.venv}"          # shared interpreter (sibling)
BIN_DIR="${VENV_ROOT}/bin"

# Pip CONSTRAINTS for the shared Python ASGI stack (FastAPI/Starlette/pydantic/
# httpx/uvicorn/anyio). Reproducibility floor + CVE floor (an unbounded Starlette
# could regress below the patched line for CVE-2026-48710). Shipped read-only via
# system-files-overlay, so the SAME floors apply at build time AND on a runtime
# `mios update` re-run. SSOT-overridable via MIOS_HERMES_CONSTRAINTS; degrade-open
# (install unconstrained) if the file is absent so a bare dev-box re-run never
# breaks. See MIOS-GAP-REGISTER U2.
CONSTRAINTS_FILE="${MIOS_HERMES_CONSTRAINTS:-/usr/share/mios/agents/constraints.txt}"
PIP_CONSTRAINTS_ARG=""
if [[ -f "$CONSTRAINTS_FILE" ]]; then
    PIP_CONSTRAINTS_ARG="-c ${CONSTRAINTS_FILE}"
else
    warn "[MiOS AI] pip constraints ${CONSTRAINTS_FILE} absent -- installing UNCONSTRAINED (degrade-open)"
fi

log "[MiOS AI] direct install: repo=${HERMES_REPO} ref=${HERMES_REF} constraints=${PIP_CONSTRAINTS_ARG:-none}"

# Tooling preflight -- python3 + pip + git must all be present. They're
# pulled by [packages.base] (git) + policycoreutils-python-utils
# (python3). If any is missing, skip cleanly rather than die.
_missing=""
for tool in python3 git; do
    command -v "$tool" >/dev/null 2>&1 || _missing="${_missing} ${tool}"
done
if [[ -n "$_missing" ]]; then
    warn "[MiOS AI] missing build tools:${_missing} -- skipping direct install (mios-gateway-agent.service will no-op via ConditionPathExists)"
    exit 0
fi

install -d -m 0755 "${AGENTS_ROOT}" "${VENV_ROOT}" "${BIN_DIR}" || { warn "[MiOS AI] mkdir ${VENV_ROOT} failed -- skipping"; exit 0; }

# Build the venv. pip install directly from the git ref -- no editable
# checkout, no leftover src tree in the image.
# hermes-agent requires Python >=3.11,<3.14; the base image's python3 may be
# >=3.14 (Fedora 44 ships 3.14 -> pip rejects the wheel: "requires a different
# Python: 3.14.x not in '<3.14,>=3.11'"). Prefer an explicit <3.14 interpreter
# for the shared venv when one is installed; degrade-open to python3 so there is
# NO regression where only 3.14 exists (rebuild fix).
VENV_PY=python3
for _py in python3.13 python3.12 python3.11; do
    command -v "${_py}" >/dev/null 2>&1 && { VENV_PY="${_py}"; break; }
done
log "[MiOS AI] venv interpreter: ${VENV_PY} ($(${VENV_PY} --version 2>&1))"
if ! "${VENV_PY}" -m venv "${VENV_DIR}" 2>/dev/null; then
    warn "[MiOS AI] ${VENV_PY} -m venv failed -- skipping direct install"
    exit 0
fi

# Offline check: do we have a local hermes-agent wheel, archive, or source dir,
# and/or local wheels in the vendored folder?
PIP_OFFLINE_ARGS=""
LOCAL_SOURCE=""
if [ -d "/usr/share/mios/vendored/hermes-agent" ]; then
    log "[MiOS AI] Found offline vendored hermes-agent directory"
    LOCAL_SOURCE="/usr/share/mios/vendored/hermes-agent"
elif [ -f "/usr/share/mios/vendored/hermes-agent.zip" ]; then
    log "[MiOS AI] Found offline vendored hermes-agent.zip, extracting..."
    unzip -o -q /usr/share/mios/vendored/hermes-agent.zip -d /tmp/hermes-agent-src 2>/dev/null || true
    LOCAL_SOURCE="/tmp/hermes-agent-src"
elif [ -f "/usr/share/mios/vendored/hermes_agent.whl" ]; then
    log "[MiOS AI] Found offline vendored hermes_agent.whl"
    LOCAL_SOURCE="/usr/share/mios/vendored/hermes_agent.whl"
fi

if [ -n "$LOCAL_SOURCE" ]; then
    PIP_OFFLINE_ARGS="--no-index --find-links=/usr/share/mios/vendored/"
    INSTALL_TARGET="-e $LOCAL_SOURCE"
else
    if [ ! -d "${VENV_ROOT}/.git" ]; then
        log "[MiOS AI] Cloning ${HERMES_REPO} (${HERMES_REF}) to ${VENV_ROOT}..."
        rm -rf "${VENV_ROOT}"
        git clone --depth 1 --branch "${HERMES_REF}" "${HERMES_REPO}" "${VENV_ROOT}" 2>/dev/null || \
            git clone "${HERMES_REPO}" "${VENV_ROOT}" 2>/dev/null || true
    fi
    INSTALL_TARGET="-e ${VENV_ROOT}"
    if [ -d "/usr/share/mios/vendored" ]; then
        PIP_OFFLINE_ARGS="--find-links=/usr/share/mios/vendored/"
    fi
fi

# `pip install -e` plus the must-have soft-deps -- single
# step, network best-effort.
# Ensure setuptools and wheel are pre-installed in the venv for pyproject_hooks build_meta
"${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check setuptools wheel 2>/dev/null || true

_REQ_FILE="/usr/lib/mios/agent-pipe/requirements.txt"
_REQ_ARG=""; [ -f "${_REQ_FILE}" ] && _REQ_ARG="-r ${_REQ_FILE}"
_venv_pip_ok=""
for _venv_attempt in 1 2 3; do
    # shellcheck disable=SC2086
    if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check --ignore-requires-python --no-build-isolation ${PIP_OFFLINE_ARGS} ${PIP_CONSTRAINTS_ARG} \
            ${INSTALL_TARGET} ${_REQ_ARG} \
            aiohttp websockets "discord.py>=2.4,<3" "psycopg[binary]" "firecrawl-py" \
            "smolagents>=1.0.0" "litellm>=1.0.0" "mcp" 2>&1 | tail -8; then
        _venv_pip_ok=1; break
    fi
    warn "[MiOS AI] agent-venv pip install attempt ${_venv_attempt}/3 failed (transient network under install load?) -- retrying in $((_venv_attempt*8))s"
    sleep $((_venv_attempt*8))
done
if [ -z "${_venv_pip_ok}" ]; then
    warn "[MiOS AI] agent-venv pip install failed after 3 attempts -- removing partial venv, will retry next boot"
    rm -rf "${VENV_DIR}"
    exit 0
fi

# The pip install drops a `hermes` entry-point into the venv's bin.
# Verify it landed; symlink it to a stable vendor path the
# /usr/bin/hermes wrapper + mios-gateway-agent.service both reference.
if [[ -x "${VENV_DIR}/bin/hermes" ]]; then
    ln -sf "${VENV_DIR}/bin/hermes" "${BIN_DIR}/hermes"
    log "[MiOS AI] installed: ${VENV_DIR}/bin/hermes -> ${BIN_DIR}/hermes"
    record_version "hermes-agent" "${HERMES_REF}" "$(${VENV_DIR}/bin/hermes --version 2>&1 | head -1)" 2>/dev/null || true
else
    warn "[MiOS AI] pip succeeded but no 'hermes' entry-point in venv -- skipping symlink"
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
# config.yaml (operator-confirmed hermes returned the
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
        log "[MiOS AI] seeded ${searxng_dir#${VENV_DIR}/}/plugin.yaml"
    fi
    # Firecrawl web provider: the wheel ships plugins/web/firecrawl/provider.py
    # but no plugin.yaml, so the loader skips it. Seed the manifest so it
    # REGISTERS -- but note it is a DORMANT fallback: hermes pins firecrawl-py v4
    # (firecrawl API v2, POST /v2/scrape) while MiOS self-hosts firecrawl v1.0.0
    # (v1 API), so web_extract via firecrawl 404s (operator-confirmed).
    # The ACTIVE extract backend is `miosfetch` (below); this seed just keeps
    # firecrawl selectable if the self-hosted container is upgraded to v2.
    firecrawl_dir="${site_packages}/plugins/web/firecrawl"
    if [[ -d "$firecrawl_dir" && ! -f "${firecrawl_dir}/plugin.yaml" ]]; then
        cat > "${firecrawl_dir}/plugin.yaml" <<'YAML'
name: firecrawl
kind: backend
version: 1.0.0
description: Firecrawl web provider (self-hosted at FIRECRAWL_API_URL; DORMANT -- SDK v2 vs container v1 mismatch, web.extract_backend defaults to miosfetch).
register: plugins.web.firecrawl:register
YAML
        log "[MiOS AI] seeded ${firecrawl_dir#${VENV_DIR}/}/plugin.yaml"
    fi
    # miosfetch: MiOS's OWN offline direct-fetch web-EXTRACT provider (stdlib
    # urllib + readability HTML->text; no firecrawl SDK / no container / no cloud)
    # -- the ACTIVE extract backend (web.extract_backend: miosfetch). Source ships
    # via system-files-overlay at /usr/share/mios/hermes/plugins/web/miosfetch;
    # copy it into the venv's bundled plugin tree so the loader auto-registers it.
    # This is the real fix for "research can't drill past search-result homepages"
    # (operator-confirmed).
    _mf_src="/usr/share/mios/hermes/plugins/web/miosfetch"
    _mf_dst="${site_packages}/plugins/web/miosfetch"
    if [[ -d "$_mf_src" ]]; then
        install -d "$_mf_dst"
        cp -f "$_mf_src"/provider.py "$_mf_src"/__init__.py "$_mf_src"/plugin.yaml "$_mf_dst"/ 2>/dev/null \
            && log "[MiOS AI] deployed miosfetch plugin -> ${_mf_dst#${VENV_DIR}/}"
    fi
    # Teach the LEGACY web_tools backend-availability check about miosfetch:
    # tools/web_tools.py::_is_backend_available hardcodes the built-in backend
    # names and returns False for any custom provider, so _get_capability_backend
    # would discard `extract_backend: miosfetch` and fall back to firecrawl. One
    # guarded line makes miosfetch a recognized (always-available, stdlib) backend.
    _wt="${site_packages}/tools/web_tools.py"
    if [[ -f "$_wt" ]] && ! grep -q 'backend == "miosfetch"' "$_wt"; then
        sed -i 's/^    if backend == "exa":/    if backend == "miosfetch":  # MiOS offline direct-fetch provider (stdlib; always usable)\n        return True\n    if backend == "exa":/' "$_wt" \
            && log "[MiOS AI] patched web_tools._is_backend_available for miosfetch"
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
# out of. Backend-only mode falls back to
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
        log "[MiOS AI] seeded plugins/{kanban,example-dashboard,hermes-achievements}/dashboard/{manifest.json,dist}"
    else
        warn "[MiOS AI] could not fetch upstream dashboard manifests (git archive + sparse-clone both failed); kanban tab will not appear"
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
    if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check ${PIP_CONSTRAINTS_ARG} \
            "fastapi>=0.110" "uvicorn[standard]>=0.30" "python-multipart" "ptyprocess>=0.7" 2>&1 | tail -3; then
        log "[MiOS AI] installed fastapi + uvicorn + ptyprocess into venv (dashboard runtime + /chat PTY)"
    else
        warn "[MiOS AI] dashboard runtime deps install failed -- hermes-dashboard.service will refuse to start"
    fi
fi

# ─── MCP client SDK ("Hermes should have access to all
# Global MiOS MCP surfaces"). hermes-agent's MCP-client subsystem (hermes_cli/
# mcp_*) is a documented NO-OP without the optional `mcp` SDK -- without it the
# `mcp_servers:` config is inert and Hermes never sees the global mios-mcp-server.
# Installing it lets Hermes discover + register the COMPLETE MiOS tool surface
# (verbs + recipes + skills) over stdio, routed through the launcher broker.
if ! "${VENV_DIR}/bin/python3" -c "import mcp" 2>/dev/null; then
    if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check ${PIP_CONSTRAINTS_ARG} "mcp>=1.0" 2>&1 | tail -3; then
        log "[MiOS AI] installed mcp SDK into venv (Hermes MCP client -> global mios-mcp-server)"
    else
        warn "[MiOS AI] mcp SDK install failed -- Hermes MCP client disabled (mcp_servers config inert)"
    fi
fi

# ─── Tokenizer backend (WS-A5): EXACT token counts for the agent-pipe ───
# mios_tokenize ships an EXACT tokenizer (default tiktoken, SSOT [ai].tokenizer_*)
# so context-fit sizing + the client-visible usage object measure real tokens, not
# the ~chars/token heuristic. Install the optional dep into the shared venv AND
# PRE-WARM the encoding blob into the baked, read-only offline cache so the running
# agent-pipe needs NO network. All values come from the SSOT (no restated literal);
# everything is best-effort -- a failure just degrades-open to the heuristic at
# runtime (mios_tokenize.make_backend returns None -> HeuristicBackend stays).
TOK_BACKEND="${MIOS_TOKENIZER_BACKEND:-}"
TOK_ENCODING="${MIOS_TOKENIZER_ENCODING:-}"
TOK_CACHE_DIR="${MIOS_TOKENIZER_CACHE_DIR:-}"
if [[ "$TOK_BACKEND" == "tiktoken" ]]; then
    if ! "${VENV_DIR}/bin/python3" -c "import tiktoken" 2>/dev/null; then
        if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check ${PIP_CONSTRAINTS_ARG} "tiktoken>=0.7" 2>&1 | tail -3; then
            log "[MiOS AI] installed tiktoken into the agent venv (WS-A5 exact token counts)"
        else
            warn "[MiOS AI] tiktoken install failed -- agent-pipe degrades-open to the ~chars/token heuristic"
        fi
    fi
    # Pre-warm the SSOT encoding into the baked offline cache (no runtime network).
    if [[ -n "$TOK_ENCODING" && -n "$TOK_CACHE_DIR" ]] && "${VENV_DIR}/bin/python3" -c "import tiktoken" 2>/dev/null; then
        mkdir -p "$TOK_CACHE_DIR" 2>/dev/null || true
        if TIKTOKEN_CACHE_DIR="$TOK_CACHE_DIR" "${VENV_DIR}/bin/python3" \
                -c "import sys, tiktoken; tiktoken.get_encoding(sys.argv[1])" "$TOK_ENCODING" 2>&1 | tail -2; then
            log "[MiOS AI] pre-warmed tiktoken encoding ${TOK_ENCODING} into ${TOK_CACHE_DIR} (offline-baked)"
        else
            warn "[MiOS AI] tiktoken encoding pre-warm failed (${TOK_ENCODING}) -- runtime needs network or degrades-open to heuristic"
        fi
    fi
fi

# ─── smolagents + LiteLLM (Part 10: Converged-Resource Architecture) ───
# The queue-based gateway worker (T-095) runs smolagents.ToolCallingAgent
# with smolagents.LiteLLMModel.
if ! "${VENV_DIR}/bin/python3" -c "import smolagents, litellm" 2>/dev/null; then
    if "${VENV_DIR}/bin/pip" install --no-input --disable-pip-version-check ${PIP_CONSTRAINTS_ARG} \
            "smolagents>=1.0.0" "litellm>=1.0.0" 2>&1 | tail -3; then
        log "[MiOS AI] installed smolagents + litellm into the agent venv (queue-based gateway worker)"
    else
        warn "[MiOS AI] smolagents + litellm install failed -- queue-based gateway mode will be unavailable"
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
# operator-audited — no analytics/trackers/sentry/
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
    command -v node >/dev/null 2>&1 || { warn "[MiOS AI] node not installed -- skipping SPA build (dashboard will use stub)"; return 1; }
    command -v npm  >/dev/null 2>&1 || { warn "[MiOS AI] npm not installed -- skipping SPA build"; return 1; }
    command -v git  >/dev/null 2>&1 || { warn "[MiOS AI] git not installed -- skipping SPA build"; return 1; }

    local spa_tmp
    spa_tmp=$(mktemp -d)
    if ! git clone --depth 1 --branch "${HERMES_REF}" "${HERMES_REPO}" "$spa_tmp/repo" 2>&1 | tail -3 ; then
        warn "[MiOS AI] SPA: clone failed"
        rm -rf "$spa_tmp"; return 1
    fi

    if ! (cd "$spa_tmp/repo/web" && npm install --ignore-scripts --no-audit --no-fund 2>&1 | tail -3); then
        warn "[MiOS AI] SPA: npm install failed"
        rm -rf "$spa_tmp"; return 1
    fi

    if ! (cd "$spa_tmp/repo/web" && npm run build 2>&1 | tail -8); then
        warn "[MiOS AI] SPA: npm run build failed"
        rm -rf "$spa_tmp"; return 1
    fi

    local built="$spa_tmp/repo/hermes_cli/web_dist"
    if [[ ! -f "$built/index.html" ]]; then
        warn "[MiOS AI] SPA: build produced no index.html at $built"
        rm -rf "$spa_tmp"; return 1
    fi

    # Strip externally-hosted URLs (Law 7). Helper lives next to this
    # script (build-time only; not installed onto the image).
    local strip_helper="${BASH_SOURCE[0]%/*}/support/hermes-dashboard-strip-externals.py"
    if [[ -x "$strip_helper" || -f "$strip_helper" ]]; then
        if ! python3 "$strip_helper" "$built" ; then
            warn "[MiOS AI] SPA: strip-externals reported leftover external refs"
            rm -rf "$spa_tmp"; return 1
        fi
    else
        warn "[MiOS AI] SPA: strip-externals helper missing at $strip_helper -- aborting build (would leak fonts.googleapis.com requests)"
        rm -rf "$spa_tmp"; return 1
    fi

    shopt -s nullglob
    for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
        local dst="$site_packages/hermes_cli/web_dist"
        rm -rf "$dst"
        mkdir -p "$(dirname "$dst")"
        cp -r "$built" "$dst"
        log "[MiOS AI] SPA: installed $(du -sh "$dst" | cut -f1) to ${dst#${VENV_DIR}/}"
    done
    shopt -u nullglob

    rm -rf "$spa_tmp"
    return 0
}

# Build is idempotent + best-effort; absent a working SPA the
# dashboard service still serves the stub /usr/share/mios/hermes-agent/
# web_dist_stub explainer page + the kanban API.
_BUILD_SPA || warn "[MiOS AI] dashboard SPA not built; hermes-dashboard.service will fall back to the web_dist_stub"

# ─── OpenUI generative-UI bundle (vendor offline) ────────────────────
# OWUI's OpenUI Tool (operator-supplied) renders interactive
# UI (charts/forms/tables/cards/follow-ups) from a DSL. The upstream
# tool fetches its JS bundle from jsDelivr at render time -- VIOLATES
# Law 7. MiOS ships a patched copy that INLINES the bundle from
# /usr/share/mios/openui/ so iframes need zero external requests.
# This step downloads the bundle ONCE at image-build time.
_VENDOR_OPENUI="${BASH_SOURCE[0]%/*}/support/mios-vendor-openui.sh"
if [[ -x "$_VENDOR_OPENUI" || -f "$_VENDOR_OPENUI" ]]; then
    bash "$_VENDOR_OPENUI" || warn "[MiOS AI] OpenUI bundle download failed; render panel will report 'bundle missing' until re-run"
else
    warn "[MiOS AI] mios-vendor-openui.sh missing at $_VENDOR_OPENUI"
fi

# ─── /api/pty HERMES_PTY_SHELL patch (bash in the dashboard /chat tab) ───
# Upstream hardcodes the PTY child to `hermes --tui` (the Node-built
# TUI chat). MiOS-DEV ships a bash terminal in the dashboard instead:
# /chat tab renders xterm.js over /api/pty WebSocket -> bash --login -i.
# Loopback + per-session-token still gate the endpoint. Operator
# directive "do we have a react window for terminal(s)?"
# -> "Plain bash terminal" picked.
_PTY_PATCH="${BASH_SOURCE[0]%/*}/support/hermes-dashboard-shell-patch.py"
shopt -s nullglob
for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
    _ws="$site_packages/hermes_cli/web_server.py"
    if [[ -f "$_ws" && -f "$_PTY_PATCH" ]]; then
        if python3 "$_PTY_PATCH" "$_ws" 2>&1 | tail -2; then
            : # ok; idempotent — re-runs are no-ops once marker present
        else
            warn "[MiOS AI] HERMES_PTY_SHELL patch failed on $_ws (dashboard /chat tab will spawn hermes --tui instead of bash)"
        fi
    fi
done
shopt -u nullglob

# ─── Background-review tool-access patch ───────
# Upstream agent/background_review.py runs the post-turn self-improvement
# pass under a tool whitelist of ONLY ["memory","skills"] -- so the review
# agent's `patch` call was denied ("Only memory/skill tools are allowed"),
# its skill_manage edit had no working file-edit fallback, and it looped to
# the tool-turn budget ("agent may appear stuck"). This unions the parent
# agent's FULL tool surface (valid_tool_names) into the review whitelist so
# MiOS-Hermes can use ALL global tools in background review too.
_BGREVIEW_PATCH="${BASH_SOURCE[0]%/*}/support/hermes-background-review-tools-patch.py"
shopt -s nullglob
for site_packages in "${VENV_DIR}/lib/"python*/site-packages; do
    _br="$site_packages/agent/background_review.py"
    if [[ -f "$_br" && -f "$_BGREVIEW_PATCH" ]]; then
        if python3 "$_BGREVIEW_PATCH" "$_br" 2>&1 | tail -2; then
            : # ok; idempotent -- re-runs are no-ops once marker present
        else
            warn "[MiOS AI] background-review tool patch failed on $_br"
        fi
    fi
done
shopt -u nullglob

# ════════════════════════════════════════════════════════════════════
# PHASE 2 -- opencode (unified agent-plane driver; merged)
# ════════════════════════════════════════════════════════════════════
# Operator front-door decision: opencode is a first-class
# OpenAI /v1 COUNCIL PEER served by mios-opencode-gateway.service (:8633),
# NOT a Hermes ACP subprocess. This phase -- absorbed from the retired
# automation/39-opencode.sh -- fetches the opencode binary and lands the
# vendored opencode.json into the gateway's config dir so the gateway has
# a usable runtime the moment mios-gateway-agent.service's shared venv is built
# (the gateway reuses THIS venv's python3; see mios-opencode-gateway.
# service ExecStart + mios.toml [ai].agent_venv).
#
# Why merged into THIS script instead of a separate stage 39: build.sh
# globs automation/[0-9][0-9]-*.sh, and two 38-* drivers would BOTH run;
# the historic 38- slot already owns the shared venv + Hermes, so the
# single unified driver lives here and the historical 39-opencode.sh is deleted.
#
# Still best-effort + non-fatal: a failed binary fetch leaves the gateway
# unit no-op'ing cleanly via ConditionPathExists; `mios update` re-runs
# this script to complete it.
#
# SSOT: all paths/urls resolve from mios.toml via the MIOS_OPENCODE_*
# env (tools/lib/userenv.sh), with the canonical upstream as the `:-`
# default -- never a hardcoded literal (Law 5).
OPENCODE_VERSION="${MIOS_OPENCODE_VERSION:-latest}"
OPENCODE_INSTALL_URL="${MIOS_OPENCODE_INSTALL_URL:-https://opencode.ai/install}"
# [ai].opencode_bin = /usr/lib/mios/agents/opencode/bin/opencode -> root is the
# parent of bin. Derive the root from the SSOT bin path so the two never
# drift.
OPENCODE_BIN="${MIOS_OPENCODE_BIN:-/usr/lib/mios/agents/opencode/bin/opencode}"
OPENCODE_BIN_DIR="$(dirname "${OPENCODE_BIN}")"
OPENCODE_ROOT="$(dirname "${OPENCODE_BIN_DIR}")"
# [ai].opencode_config = /etc/mios/opencode/opencode.json (admin-override
# location the gateway reads via OPENCODE_CONFIG). The vendored SoT ships
# read-only under /usr/share (Law 1: USR-OVER-ETC); we copy it into /etc
# only if the admin hasn't already placed one there.
OPENCODE_CONFIG="${MIOS_OPENCODE_CONFIG:-/etc/mios/opencode/opencode.json}"
OPENCODE_CONFIG_DIR="$(dirname "${OPENCODE_CONFIG}")"
OPENCODE_VENDOR_CONFIG=/usr/share/mios/opencode/opencode.json

log "[MiOS AI] opencode phase: version=${OPENCODE_VERSION} root=${OPENCODE_ROOT}"

# Land the vendored opencode.json into the admin-override config dir. The
# dir + ownership are also guaranteed by usr/lib/tmpfiles.d/mios-opencode-
# gateway.conf at first boot; this build-time copy makes the config
# present in the baked image. USR-is-SoT: never edit the /usr copy as the
# live config -- /etc is the override the gateway actually reads.
if [[ -f "${OPENCODE_VENDOR_CONFIG}" ]]; then
    if install -d -m 0750 "${OPENCODE_CONFIG_DIR}" 2>/dev/null; then
        if [[ ! -f "${OPENCODE_CONFIG}" ]]; then
            if install -m 0640 "${OPENCODE_VENDOR_CONFIG}" "${OPENCODE_CONFIG}"; then
                # #57: the gateway runs as mios-ai but the file lands root:root,
                # which mios-ai cannot read -> opencode "PermissionDenied:
                # FileSystem.readFile (opencode.json)" -> inert peer. Make it
                # group-readable by mios-ai per the MiOS cross-agent-read
                # convention (chgrp mios-ai + 0640; 50-mios-services.conf). The
                # dir is mios-ai-owned at boot (tmpfiles); systemd-tmpfiles can't
                # do this chgrp itself (root-file-under-mios-ai-dir = "unsafe path
                # transition"), so it must happen here at land time.
                if getent group mios-ai >/dev/null 2>&1; then
                    chgrp mios-ai "${OPENCODE_CONFIG}" 2>/dev/null \
                        && chmod 0640 "${OPENCODE_CONFIG}" 2>/dev/null || true
                fi
                log "[MiOS AI] landed opencode.json -> ${OPENCODE_CONFIG} (group mios-ai)"
            else
                warn "[MiOS AI] failed to land opencode.json into ${OPENCODE_CONFIG}"
            fi
        else
            log "[MiOS AI] ${OPENCODE_CONFIG} already present (admin override) -- not overwriting"
        fi
    else
        warn "[MiOS AI] could not create ${OPENCODE_CONFIG_DIR} -- gateway config not landed"
    fi
else
    warn "[MiOS AI] vendored ${OPENCODE_VENDOR_CONFIG} missing -- skipping config land (overlay drift?)"
fi

# Fetch the opencode binary. curl + bash must be present.
_oc_missing=""
for tool in curl bash; do
    command -v "$tool" >/dev/null 2>&1 || _oc_missing="${_oc_missing} ${tool}"
done
if [[ -n "$_oc_missing" ]]; then
    warn "[MiOS AI] opencode phase: missing tools:${_oc_missing} -- skipping binary fetch (gateway no-ops via ConditionPathExists)"
elif [[ -x "${OPENCODE_BIN}" ]]; then
    log "[MiOS AI] opencode binary already present at ${OPENCODE_BIN} -- skipping fetch"
elif ! install -d -m 0755 "${OPENCODE_ROOT}" "${OPENCODE_BIN_DIR}" 2>/dev/null; then
    warn "[MiOS AI] mkdir ${OPENCODE_ROOT} failed -- skipping opencode fetch"
elif ! curl -fsSL --max-time 60 "${OPENCODE_INSTALL_URL}" -o /tmp/opencode-install.sh; then
    warn "[MiOS AI] could not fetch opencode installer from ${OPENCODE_INSTALL_URL} -- skipping; mios update will retry"
else
    # The opencode installer respects OPENCODE_INSTALL_DIR (vendor env).
    OPENCODE_INSTALL_DIR="${OPENCODE_BIN_DIR}" \
    OPENCODE_VERSION="${OPENCODE_VERSION}" \
        bash /tmp/opencode-install.sh 2>&1 | tail -10 || \
        warn "[MiOS AI] opencode installer exited non-zero -- continuing; mios update will retry"
    rm -f /tmp/opencode-install.sh 2>/dev/null || true

    # Locate the binary. Some installer versions ignore OPENCODE_INSTALL_DIR
    # and drop it under $HOME/.opencode/bin or alongside the root without
    # a /bin/ subdir; probe the known fallbacks and normalise to OPENCODE_BIN.
    if [[ ! -x "${OPENCODE_BIN}" ]]; then
        for cand in "${OPENCODE_BIN_DIR}/opencode" "${OPENCODE_ROOT}/opencode" \
                    "${HOME:-/root}/.opencode/bin/opencode" /root/.opencode/bin/opencode \
                    /var/home/mios/.opencode/bin/opencode; do
            if [[ -x "$cand" ]]; then
                if [[ "$cand" != "${OPENCODE_BIN}" ]]; then
                    install -d -m 0755 "${OPENCODE_BIN_DIR}"
                    install -m 0755 "$cand" "${OPENCODE_BIN}" \
                        && log "[MiOS AI] copied opencode ${cand} -> ${OPENCODE_BIN}"
                fi
                break
            fi
        done
    fi

    if [[ -x "${OPENCODE_BIN}" ]]; then
        # Symlink onto PATH so the operator can run `opencode` directly.
        ln -sf "${OPENCODE_BIN}" /usr/local/bin/opencode 2>/dev/null || true
        record_version "opencode" "${OPENCODE_VERSION}" "$("${OPENCODE_BIN}" --version 2>&1 | head -1 || echo unknown)" 2>/dev/null || true
        log "[MiOS AI] installed opencode: ${OPENCODE_BIN} (gateway -> mios-opencode-gateway.service :${MIOS_PORT_OPENCODE_GATEWAY:-8633})"
    else
        warn "[MiOS AI] opencode binary not found at ${OPENCODE_BIN} or fallbacks -- gateway will no-op via ConditionPathExists; mios update will retry"
    fi
fi

log "[MiOS AI] done -- runtime: mios-gateway-agent.service (:${MIOS_PORT_HERMES:-8642}/v1) + mios-opencode-gateway.service (:${MIOS_PORT_OPENCODE_GATEWAY:-8633}/v1); shared venv = ${VENV_DIR}; backend = mios.toml [ai].hermes_backend_url"
exit 0
