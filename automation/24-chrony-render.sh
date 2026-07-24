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

# DETERMINISTIC at build time: PTP/Hyper-V tuning is a DEPLOY-HOST property, not a
# build property. Keying off the BUILD host having /dev/ptp0 (e.g. an Azure/Hyper-V
# CI runner, or the container host) bakes a host-specific chrony.conf -> the image
# differs per build host AND drift-check 55 (which validates the CANONICAL SSOT
# projection, and re-renders inside a podman container with NO /dev/ptp0) fails.
# Default canonical; a deploy/first-boot render can set MIOS_CHRONY_PTP=1 to emit the
# noselect / no-rtcsync PTP variant when the REAL host has a PTP clock.
has_ptp = os.environ.get("MIOS_CHRONY_PTP", "").strip().lower() in ("1", "true", "yes")
for s in servers:
    opt = " iburst noselect" if has_ptp else " iburst"
    lines.append(f"server {s}{opt}")

rtc_line = "# rtcsync (disabled under Hyper-V PTP time sync)" if has_ptp else "rtcsync"
lines.extend([
    "",
    "# Record the rate at which the system clock gains/losses time.",
    "driftfile /var/lib/chrony/drift",
    "",
    "# Allow the system clock to be stepped in the first three updates",
    "# if its offset is larger than 1 second. (Disabled in WSL2 where Hyper-V handles coarse sync)",
    "makestep 0 0",
    "maxslewrate 500",
    "",
    "# Hyper-V PTP clock reference when available (WSL2 / VM container host)",
    "refclock PHC /dev/ptp0 poll 3 dpoll -2 offset 0 minsamples 4 prefer trust",
    "",
    "# Enable kernel synchronization of the real-time clock (RTC).",
    rtc_line,
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
