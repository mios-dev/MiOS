#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Extracts port definitions from mios.toml [ports] section and appends them to install.env as MIOS_PORT_* variables for container environment injection.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

TOML_FILE="/usr/share/mios/mios.toml"
ENV_FILE="/etc/mios/install.env"

mios_log "Extract ports from $TOML_FILE to $ENV_FILE"

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"

if command -v miosd >/dev/null 2>&1; then
    miosd render-ports --toml "$TOML_FILE" --out "$ENV_FILE"
    mios_ok "Wrote MIOS_PORT_* to $ENV_FILE via miosd"
    exit 0
fi

sed -i '/^MIOS_PORT_/d' "$ENV_FILE"

# Ports are ALLOCATED from [ports.categories] (base + index*stride), not read
# off the flat table -- and the allocation must honour the layered override
# chain (vendor/OEM default < /etc operator < user). The shared resolver is the
# only thing that does both, so prefer it; the awk fallback below can only see
# the flat vendor projection and exists purely so a stripped build host without
# python still produces SOMETHING rather than an empty install.env.
if command -v python3 >/dev/null 2>&1; then
    if python3 - "$ENV_FILE" <<'PY'
import sys, os
for cand in ("/usr/lib/mios", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../usr/lib/mios")):
    if os.path.isdir(cand):
        sys.path.insert(0, cand)
try:
    import mios_toml
except Exception:
    sys.exit(1)

merged = mios_toml.load_merged()
ports = merged.get("ports") or {}
try:
    offset = int(ports.get("stack_id", 0)) * 10000
except (TypeError, ValueError):
    offset = 0

lines = []
for name, value in sorted(ports.items()):
    if name in ("stack_id", "categories") or not isinstance(value, int):
        continue
    lines.append("MIOS_PORT_%s=%d" % (name.upper(), value if value == 53 else value + offset))
if not lines:
    sys.exit(1)
with open(sys.argv[1], "a", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
PY
    then
        mios_ok "Wrote MIOS_PORT_* to $ENV_FILE via the layered SSOT allocator"
        exit 0
    fi
    mios_skip "SSOT allocator unavailable; falling back to flat-table awk"
fi

awk '
BEGIN { stack_id = 0 }
/^\[ports\]/ {flag=1; next}
/^\[/ {flag=0}
flag && /=/ {
    split($0, arr, "=")
    key = arr[1]
    val = arr[2]
    
    sub(/^[ \t]+/, "", key)
    sub(/[ \t]+$/, "", key)
    sub(/^[ \t]+/, "", val)
    sub(/[ \t]+#.*$/, "", val)
    sub(/[ \t]+$/, "", val)
    
    if (key == "stack_id") {
        stack_id = val + 0
        next
    }
    
    if (val ~ /^[0-9]+$/ && val != "53") {
        val = val + (stack_id * 10000)
    }
    
    key = toupper(key)
    
    print "MIOS_PORT_" key "=" val
}' "$TOML_FILE" >> "$ENV_FILE"

mios_ok "Wrote MIOS_PORT_* to $ENV_FILE"
