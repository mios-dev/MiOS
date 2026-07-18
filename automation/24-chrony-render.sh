#!/usr/bin/env bash
# AI-hint: Projects NTP servers from mios.toml [network.ntp] SSOT to /etc/chrony.conf configuration file.
set -euo pipefail

echo "==> Preparing Chrony NTP configuration..."

TOML_FILE="${MIOS_TOML:-/usr/share/mios/mios.toml}"
CHRONY_CONF="${CHRONY_CONF:-/etc/chrony.conf}"

if [[ ! -f "$TOML_FILE" ]]; then
    echo "Error: manifest file $TOML_FILE not found" >&2
    exit 1
fi

# Resolve Python executable robustly
PYTHON_EXE=""
if command -v py &>/dev/null; then
    PYTHON_EXE=py
elif command -v python3 &>/dev/null && python3 --version &>/dev/null; then
    PYTHON_EXE=python3
elif command -v python &>/dev/null && python --version &>/dev/null; then
    PYTHON_EXE=python
else
    PYTHON_EXE=python3
fi

"$PYTHON_EXE" -c '
import os
import sys
import tomllib

toml_path = sys.argv[1]
conf_path = sys.argv[2]

with open(toml_path, "rb") as f:
    config = tomllib.load(f)

net_conf = config.get("network", {})
ntp_conf = net_conf.get("ntp", {})
servers = ntp_conf.get("servers", [])

if not isinstance(servers, list):
    servers = []

lines = [
    "# AI-hint: NTP configuration for Chrony. Generated from mios.toml [network.ntp] SSOT.",
    "# DO NOT EDIT -- edit mios.toml [network.ntp] and run automation/24-chrony-render.sh",
    ""
]

for s in servers:
    lines.append(f"server {s} iburst")

lines.extend([
    "",
    "# Record the rate at which the system clock gains/losses time.",
    "driftfile /var/lib/chrony/drift",
    "",
    "# Allow the system clock to be stepped in the first three updates",
    "# if its offset is larger than 1 second.",
    "makestep 1.0 3",
    "",
    "# Enable kernel synchronization of the real-time clock (RTC).",
    "rtcsync",
    "",
    "# Specify directory for log files.",
    "logdir /var/log/chrony"
])

os.makedirs(os.path.dirname(conf_path), exist_ok=True)
with open(conf_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Generated {conf_path} with {len(servers)} NTP servers")
' "$TOML_FILE" "$CHRONY_CONF"

echo "==> Chrony NTP configuration complete."
