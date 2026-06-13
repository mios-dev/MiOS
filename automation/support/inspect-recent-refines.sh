#!/bin/bash
# AI-hint: Retrieves the 4 most recent "refine" events from the local SQL database via a curl-to-json pipeline to help agents identify and analyze recent system refinements or state changes.
set -euo pipefail
curl -s -u root:root \
    -H "NS: mios" -H "DB: agent" \
    -H "Accept: application/json" -H "Content-Type: text/plain" \
    --data 'SELECT ts, summary, payload FROM event WHERE kind = "refine" ORDER BY ts DESC LIMIT 4;' \
    http://127.0.0.1:8000/sql \
    | python3 -m json.tool
