#!/bin/bash
set -euo pipefail
curl -s -u root:root \
    -H "NS: mios" -H "DB: agent" \
    -H "Accept: application/json" -H "Content-Type: text/plain" \
    --data 'SELECT ts, summary, payload FROM event WHERE kind = "refine" ORDER BY ts DESC LIMIT 4;' \
    http://127.0.0.1:8000/sql \
    | python3 -m json.tool
