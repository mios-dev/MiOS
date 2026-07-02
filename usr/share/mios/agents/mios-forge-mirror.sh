#!/usr/bin/env bash
# Create/refresh a Forgejo PULL-MIRROR of the GitHub MiOS repo. GitHub stays the
# canonical origin; Forgejo holds an auto-syncing local mirror (offline-first).
#
# NO-HARDCODE: owner + forge port are resolved from SSOT at runtime — never a
# literal. Resolution order (all runtime): $FORGE_OWNER override -> install.env
# identity (MIOS_FORGE_ADMIN_USER/MIOS_LINUX_USER/MIOS_USER) -> the SSOT-
# provisioned Forgejo admin account (queried live). Port from MIOS_PORT_FORGE_HTTP.
# The token is minted via the in-container admin CLI and piped straight into the
# API call — never printed. Idempotent (409 -> mirror-sync).
set -uo pipefail

ENV_FILE=/etc/mios/install.env
[ -r "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }

FORGE_PORT="${MIOS_PORT_FORGE_HTTP:-${MIOS_FORGE_HTTP_PORT:-3000}}"
FORGE="${FORGE_URL:-http://localhost:${FORGE_PORT}}"
SRC="${GITHUB_URL:-https://github.com/mios-dev/MiOS.git}"
REPONAME="${MIRROR_NAME:-MiOS}"

FORGE_EXEC=(podman exec --user 816:816 mios-forge forgejo --config /data/gitea/conf/app.ini)

# Resolve owner from SSOT (never a literal).
OWNER="${FORGE_OWNER:-${MIOS_FORGE_ADMIN_USER:-${MIOS_LINUX_USER:-${MIOS_USER:-}}}}"
if [ -z "$OWNER" ]; then
  OWNER="$("${FORGE_EXEC[@]}" admin user list 2>/dev/null | awk 'NR>1 && $5=="true"{print $2; exit}')"
fi
[ -n "$OWNER" ] || { echo "ERROR: could not resolve forge owner from SSOT" >&2; exit 1; }
echo "forge=$FORGE  owner(SSOT)=$OWNER  mirror=$OWNER/$REPONAME  src=$SRC"

# Mint a scoped token for OWNER, straight into the API call (never printed).
TOKEN="$("${FORGE_EXEC[@]}" admin user generate-access-token \
          --username "$OWNER" --token-name "mios-a2o-mirror-$(date +%s)" \
          --scopes write:repository --raw 2>/tmp/mint.err | tr -d '[:space:]')"
if [ -z "$TOKEN" ]; then echo "ERROR: token mint failed:" >&2; cat /tmp/mint.err >&2; exit 1; fi

payload="{\"clone_addr\":\"$SRC\",\"repo_name\":\"$REPONAME\",\"repo_owner\":\"$OWNER\",\"mirror\":true,\"private\":false,\"service\":\"git\""
[ -n "${GH_TOKEN:-}" ] && payload="$payload,\"auth_token\":\"$GH_TOKEN\""
payload="$payload}"

code=$(curl -sS -o /tmp/forge-mirror.json -w '%{http_code}' \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -X POST "$FORGE/api/v1/repos/migrate" -d "$payload" || echo 000)
case "$code" in
  201) echo "OK: mirror created -> $FORGE/$OWNER/$REPONAME (pull-mirrors $SRC)";;
  409) echo "exists: triggering mirror-sync for $OWNER/$REPONAME"
       curl -sS -H "Authorization: token $TOKEN" -X POST "$FORGE/api/v1/repos/$OWNER/$REPONAME/mirror-sync" >/dev/null && echo "OK: sync triggered";;
  401|403) echo "AUTH FAILED (HTTP $code) — token scope/owner issue"; exit 1;;
  422) echo "HTTP 422 (unprocessable — often a private source needing GH_TOKEN):"; cat /tmp/forge-mirror.json; exit 1;;
  *) echo "FAILED HTTP $code:"; cat /tmp/forge-mirror.json 2>/dev/null; exit 1;;
esac
