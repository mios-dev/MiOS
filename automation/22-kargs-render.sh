#!/usr/bin/env bash
# AI-hint: Processes kernel arguments from mios.toml [kargs] section and updates kargs.d/*.toml files accordingly.
set -euo pipefail

echo "==> Preparing kernel boot arguments (kargs.d)..."

# Path to mios.toml
TOML_FILE="${MIOS_TOML:-/usr/share/mios/mios.toml}"
KARGS_DIR="${KARGS_DIR:-/usr/lib/bootc/kargs.d}"

if [[ ! -f "$TOML_FILE" ]]; then
    echo "Error: manifest file $TOML_FILE not found" >&2
    exit 1
fi

if [[ ! -d "$KARGS_DIR" ]]; then
    echo "Warning: $KARGS_DIR not found, skipping kargs rendering"
    exit 0
fi

# Resolve Python executable robustly (preferring py launcher on Windows, fallback to python3/python)
PYTHON_EXE=""
if command -v py &>/dev/null; then
    PYTHON_EXE=py
elif command -v python3 &>/dev/null && python3 --version &>/dev/null; then
    PYTHON_EXE=python3
elif command -v python &>/dev/null && python --version &>/dev/null; then
    PYTHON_EXE=python
else
    # Default fallback for standard Linux builds
    PYTHON_EXE=python3
fi

# Run the python generator
"$PYTHON_EXE" -c '
import os
import sys
import tomllib

mios_toml_path = sys.argv[1]
kargs_dir = sys.argv[2]

with open(mios_toml_path, "rb") as f:
    config = tomllib.load(f)

kargs_conf = config.get("kargs", {})

# 1. Modify 01-mios-vfio.toml
vfio_toml_path = os.path.join(kargs_dir, "01-mios-vfio.toml")
if os.path.exists(vfio_toml_path):
    with open(vfio_toml_path, "rb") as f:
        vfio_data = tomllib.load(f)
    
    kargs_list = vfio_data.get("kargs", [])
    
    # Process iommu
    iommu = kargs_conf.get("iommu", "on")
    # Clean existing IOMMU settings from list
    kargs_list = [k for k in kargs_list if k not in ("intel_iommu=on", "amd_iommu=on", "iommu=pt")]
    if iommu == "intel":
        kargs_list.extend(["intel_iommu=on", "iommu=pt"])
    elif iommu == "amd":
        kargs_list.extend(["amd_iommu=on", "iommu=pt"])
    elif iommu == "on":
        kargs_list.extend(["intel_iommu=on", "amd_iommu=on", "iommu=pt"])
        
    # Process vfio_ids
    vfio_ids = kargs_conf.get("vfio_ids", "").strip()
    kargs_list = [k for k in kargs_list if not k.startswith("vfio-pci.ids")]
    if vfio_ids:
        kargs_list.append(f"vfio-pci.ids={vfio_ids}")
        
    # Write back 01-mios-vfio.toml
    lines = [
        "# AI-hint: Configures kernel arguments for IOMMU, VFIO-PCI, and nested virtualization to enable hardware passthrough and virtualization features in the MiOS boot process.",
        "# Generated from mios.toml [kargs] SSOT",
        "kargs = ["
    ]
    for k in kargs_list:
        lines.append(f"    \"{k}\",")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("]")
    
    with open(vfio_toml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Updated {vfio_toml_path}")

# 2. Generate 99-mios-kargs.toml for hugepages, isolcpus, nohz_full, rcu_nocbs, THP
custom_kargs = []
hugepages = str(kargs_conf.get("hugepages", "")).strip()
if hugepages:
    custom_kargs.append(f"hugepages={hugepages}")
    
isolcpus = kargs_conf.get("isolcpus", "").strip()
if isolcpus:
    custom_kargs.append(f"isolcpus={isolcpus}")
    
nohz_full = kargs_conf.get("nohz_full", "").strip()
if nohz_full:
    custom_kargs.append(f"nohz_full={nohz_full}")
    
rcu_nocbs = kargs_conf.get("rcu_nocbs", "").strip()
if rcu_nocbs:
    custom_kargs.append(f"rcu_nocbs={rcu_nocbs}")
    
thp = kargs_conf.get("THP", "").strip()
if thp:
    custom_kargs.append(f"transparent_hugepage={thp}")

custom_toml_path = os.path.join(kargs_dir, "99-mios-kargs.toml")
if custom_kargs:
    lines = [
        "# AI-hint: Configures custom kernel arguments from mios.toml [kargs] SSOT.",
        "# Generated custom kernel arguments from mios.toml [kargs] SSOT",
        "kargs = ["
    ]
    for k in custom_kargs:
        lines.append(f"    \"{k}\",")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("]")
    
    with open(custom_toml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Generated {custom_toml_path}")
else:
    if os.path.exists(custom_toml_path):
        os.remove(custom_toml_path)
        print(f"Removed stale {custom_toml_path}")
' "$TOML_FILE" "$KARGS_DIR"

echo "==> Kernel boot arguments preparation complete."
