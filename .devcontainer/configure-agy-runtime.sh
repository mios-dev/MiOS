#!/usr/bin/env bash
set -euo pipefail

settings_dir="${HOME}/.gemini/antigravity-cli"
settings_file="${settings_dir}/settings.json"

install -d -m 0700 "$settings_dir"

python3 - "$settings_file" <<'PY'
import json
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
settings = {}
if path.exists():
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"AGY settings are unreadable: {exc}")
    if not isinstance(value, dict):
        raise SystemExit("AGY settings must contain a JSON object")
    settings = value

settings["modelProvider"] = "gemini"
temporary = path.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(settings, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
os.chmod(temporary, 0o600)
temporary.replace(path)
os.chmod(path, 0o600)
PY

if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    echo "AGY Gemini API-key mode is configured."
else
    echo "AGY settings are configured; GEMINI_API_KEY is not present."
    echo "Set it as a runtime Codespaces secret before launching AGY."
fi
