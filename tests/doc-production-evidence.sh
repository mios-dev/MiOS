#!/usr/bin/env bash
# AI-hint: CI-visible proof that the documentation programme produced its artifacts: counts distilled manual pages, landed comment passages and spliced MIOS-GEN sections, then runs the mios-manual read-only gates (ledger, render, landing, coverage).
# AI-related: /usr/libexec/mios/mios-manual, /usr/lib/mios/mios_comments.py, /usr/share/doc/mios/manual, /usr/share/mios/reference/manual-corpus.tsv, /usr/share/doc/mios/reference/documentation-pipeline.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# The comment census is interpreter-sensitive (PEP 701); prefer 3.12+ like the gates do.
PY="$(command -v python3.12 || command -v python3)"

LEDGER=usr/share/mios/reference/manual-corpus.tsv
MANUAL_DIR=usr/share/doc/mios/manual

pages=$(git ls-files "${MANUAL_DIR}/*.md" | wc -l)
landed=$(awk -F'\t' 'NR>1 && $11!=""{n++} END{print n+0}' "$LEDGER")
pruned=$(awk -F'\t' 'NR>1 && $14=="1"{n++} END{print n+0}' "$LEDGER")
# Marker count comes from render itself; a plain grep would over-count the fenced spec examples.
sites=$("$PY" usr/libexec/mios/mios-manual render --check 2>&1 | tail -1 | grep -oE '[0-9]+' | head -1 || echo 0)

echo "== manuals & documentation: production evidence =="
echo "  distilled manual pages under ${MANUAL_DIR}/: ${pages}"
echo "  comment passages landed in docs (ledger):    ${landed}  (pruned from source: ${pruned})"
echo "  generated sections spliced (MIOS-GEN markers): ${sites}"
echo "  entry points: usr/share/doc/mios/README.md, usr/share/doc/mios/manual.md,"
echo "                usr/share/doc/mios/reference/documentation-pipeline.md"

if [ "$pages" -lt 1 ] || [ "$landed" -lt 1 ] || [ "$sites" -lt 1 ]; then
    echo "ERROR: documentation production is empty -- the distill/render pass produced nothing" >&2
    exit 1
fi

run() { echo "  [gate] mios-manual $*"; "$PY" usr/libexec/mios/mios-manual "$@"; }
run ledger --check
run render --check
run landing --check
run coverage
echo "== documentation gates: all green =="
