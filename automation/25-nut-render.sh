#!/usr/bin/env bash
# AI-hint: Projects UPS settings from mios.toml [power.ups] SSOT to /etc/ups/ configurations (nut.conf, ups.conf, upsd.conf, upsmon.conf).
set -euo pipefail

echo "==> Preparing Network UPS Tools (NUT) configuration..."

TOML_FILE="${MIOS_TOML:-/usr/share/mios/mios.toml}"
UPS_CONF_DIR="${UPS_CONF_DIR:-/etc/ups}"

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
conf_dir = sys.argv[2]

with open(toml_path, "rb") as f:
    config = tomllib.load(f)

power_conf = config.get("power", {})
ups_conf = power_conf.get("ups", {})
name = str(ups_conf.get("name", "")).strip()
driver = str(ups_conf.get("driver", "usbhid-ups")).strip()
port = str(ups_conf.get("port", "auto")).strip()
desc = str(ups_conf.get("desc", "MiOS Uninterruptible Power Supply")).strip()

os.makedirs(conf_dir, exist_ok=True)

# 1. nut.conf
nut_lines = [
    "# AI-hint: NUT framework mode. Generated from mios.toml [power.ups] SSOT.",
    "# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/25-nut-render.sh",
]
if name:
    nut_lines.append("MODE=standalone")
else:
    nut_lines.append("MODE=none")

with open(os.path.join(conf_dir, "nut.conf"), "w", encoding="utf-8") as f:
    f.write("\n".join(nut_lines) + "\n")

# 2. ups.conf
ups_lines = [
    "# AI-hint: NUT drivers configuration. Generated from mios.toml [power.ups] SSOT.",
    "# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/25-nut-render.sh",
]
if name:
    ups_lines.extend([
        "",
        f"[{name}]",
        f"    driver = {driver}",
        f"    port = {port}",
        f"    desc = \"{desc}\""
    ])

with open(os.path.join(conf_dir, "ups.conf"), "w", encoding="utf-8") as f:
    f.write("\n".join(ups_lines) + "\n")

# 3. upsd.conf
upsd_lines = [
    "# AI-hint: NUT daemon settings. Generated from mios.toml [power.ups] SSOT.",
    "# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/25-nut-render.sh",
]
if name:
    upsd_lines.extend([
        "",
        "LISTEN 127.0.0.1 3493"
    ])

with open(os.path.join(conf_dir, "upsd.conf"), "w", encoding="utf-8") as f:
    f.write("\n".join(upsd_lines) + "\n")

# 4. upsmon.conf
upsmon_lines = [
    "# AI-hint: NUT monitor settings. Generated from mios.toml [power.ups] SSOT.",
    "# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/25-nut-render.sh",
]
if name:
    upsmon_lines.extend([
        "",
        f"MONITOR {name}@localhost 1 upsmon mios-ups-secret master",
        "SHUTDOWNCMD \"/sbin/shutdown -h +0\""
    ])

with open(os.path.join(conf_dir, "upsmon.conf"), "w", encoding="utf-8") as f:
    f.write("\n".join(upsmon_lines) + "\n")

if name:
    print(f"Generated standalone NUT configs for UPS {name} in {conf_dir}")
else:
    print(f"Generated inert NUT configs (MODE=none) in {conf_dir}")
' "$TOML_FILE" "$UPS_CONF_DIR"

echo "==> Network UPS Tools (NUT) configuration complete."
