#!/usr/bin/env bash
# AI-hint: mios-mcp-enable-tier0.sh -- OPERATOR-RUN activation of the Tier-0 MCP servers
# AI-related: /usr/libexec/mios/mios-mcp-enable-tier0.sh, /etc/mios/ai/v1/mcp.json, /etc/mios/ai/v1, mios-mcp-enable-tier0, mios-agent-pipe, mios-ai-owned, mios-ai, mios-agent-pipe.service
# mios-mcp-enable-tier0.sh -- OPERATOR-RUN activation of the Tier-0 MCP servers
# (DuckDB + Postgres). The agent-pipe CODE is already P4-ready + the embed/taint/
# tool_search reachability is live; this performs the OPERATOR-GATED activation that
# the assistant must not do unilaterally (installing + running external code).
#
# RUN (inside the MiOS distro, as root):
#   wsl.exe -d podman-MiOS-DEV -u root -- bash /usr/libexec/mios/mios-mcp-enable-tier0.sh
#
# Why this is your step, not the assistant's: enabling agent-installed external code
# as a spawned MCP server is gated by the security classifier; YOUR execution carries
# your authority, so no bypass is involved. Playwright (already live) is preserved.
#
# Idempotent + safe to re-run. To revert: delete the duckdb/postgres entries from
# /etc/mios/ai/v1/mcp.json (or set enabled:false) and restart mios-agent-pipe.
set -uo pipefail
VENV=/var/lib/mios/ai/mcp-venv

echo "[1/5] writable dirs (mios-ai-owned -- the stdio server de-escalates to mios-ai)"
mkdir -p /var/lib/mios/ai/tmp /var/lib/mios/ai/.npm /var/lib/mios/ai/.cache "$VENV"
chown -R mios-ai:mios-ai /var/lib/mios/ai/tmp /var/lib/mios/ai/.npm /var/lib/mios/ai/.cache "$VENV"

echo "[2/5] server binaries (build deps for postgres-mcp's pglast, then pip into the mios-ai venv)"
[ -x "$VENV/bin/python3" ] || runuser -u mios-ai -- python3 -m venv "$VENV"
command -v gcc >/dev/null 2>&1 || dnf install -y --setopt=install_weak_deps=False gcc python3-devel
runuser -u mios-ai -- "$VENV/bin/pip" install --quiet --disable-pip-version-check \
    mcp-server-motherduck postgres-mcp || { echo "pip install failed"; exit 1; }

# Guard set -u: a value with shell-metachars must not abort under set -u.
if [ -r /etc/mios/install.env ]; then
    _mios_had_u=0; case "$-" in *u*) _mios_had_u=1;; esac
    set +u; set -a; . /etc/mios/install.env 2>/dev/null || true; set +a
    [ "$_mios_had_u" = 1 ] && set -u
fi
_PGPORT="${MIOS_PORT_PGVECTOR:-8432}"

echo "[3/5] /etc overlay -- enable duckdb + postgres (Postgres uses the EXISTING mios role, restricted/read-only)"
mkdir -p /etc/mios/ai/v1
cat > /etc/mios/ai/v1/mcp.json <<JSON
{ "object":"mios.mcp.registry","version":"v1","servers":[
  { "id":"playwright","label":"Playwright","enabled":true,"transport":"stdio","command":"npx",
    "args":["-y","@playwright/mcp@0.0.76","--headless","--isolated"],"cwd":"/var/lib/mios/ai",
    "env":{"HOME":"/var/lib/mios/ai","npm_config_cache":"/var/lib/mios/ai/.npm","TMPDIR":"/var/lib/mios/ai/tmp","PATH":"/usr/sbin:/usr/bin:/bin","PLAYWRIGHT_BROWSERS_PATH":"/var/lib/mios/ai/.cache/ms-playwright"},
    "tier":"rare","namespace":"browser_","taint":"untrusted_web",
    "examples":["open a web page in a browser","click a button on the page","take a screenshot of the rendered page"] },
  { "id":"duckdb","label":"DuckDB (analytical SQL)","enabled":true,"transport":"stdio",
    "command":"/var/lib/mios/ai/mcp-venv/bin/mcp-server-motherduck","args":["--db-path",":memory:","--read-write"],
    "cwd":"/var/lib/mios/ai","env":{"HOME":"/var/lib/mios/ai","TMPDIR":"/var/lib/mios/ai/tmp"},
    "tier":"rare","namespace":"duckdb_","taint":"",
    "examples":["run a sql query over a csv file","analyze data with sql","query a parquet or json file"] },
  { "id":"postgres","label":"Postgres (restricted, reads pgvector)","enabled":true,"transport":"stdio",
    "command":"/var/lib/mios/ai/mcp-venv/bin/postgres-mcp","args":["--access-mode","restricted"],
    "cwd":"/var/lib/mios/ai",
    "env":{"HOME":"/var/lib/mios/ai","TMPDIR":"/var/lib/mios/ai/tmp","DATABASE_URI":"postgresql://mios:mios@127.0.0.1:\${_PGPORT}/mios"},
    "tier":"rare","namespace":"pg_","taint":"",
    "examples":["query the postgres database read-only","run a select over the data","look up rows in pgvector"] } ]}
JSON

echo "[4/5] restart agent-pipe"
systemctl restart mios-agent-pipe.service
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do curl -sf http://127.0.0.1:8640/v1/models >/dev/null 2>&1 && break; sleep 4; done
sleep 12

echo "[5/5] verify probes (expect playwright + duckdb + postgres ready)"
journalctl -u mios-agent-pipe.service --since "90 sec ago" --no-pager \
  | grep -oE "(playwright|duckdb|postgres) ready \([0-9]+ tools[^)]*\)" | sort -u
echo "if a server is missing, check:  journalctl -u mios-agent-pipe -g 'mcp stdio' --since '2 min ago'"
