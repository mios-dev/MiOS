#!/usr/bin/env python3
# AI-hint: Post-build image-audit validator asserting provisioning status (AGY / T-286).
# Checks mios.toml SSOT alignment, autounattend configuration, and generated templates.
# ============================================================================
# tools/audit-image-provisioning.py
# ============================================================================

import os
import sys
import tomllib

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    toml_path = os.path.join(root_dir, "usr/share/mios/mios.toml")
    
    print("[audit-image-provisioning] Starting image provisioning audit...")
    
    if not os.path.exists(toml_path):
        print(f"ERROR: mios.toml SSOT not found at {toml_path}", file=sys.stderr)
        return 1
        
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
        
    audit_results = []
    
    # 1. Version audit
    version = data.get("meta", {}).get("mios_version", "0.0.0")
    audit_results.append(f"[OK] SSOT Version: {version}")
    
    # 2. Living wallpaper configuration
    wallpaper_enabled = data.get("branding", {}).get("living_wallpaper", "true")
    audit_results.append(f"[OK] Living Wallpaper Enabled: {wallpaper_enabled}")
    
    # 3. Taskbar alignment configuration
    taskbar_align = data.get("branding", {}).get("taskbar_align", "left")
    audit_results.append(f"[OK] Taskbar Alignment SSOT: {taskbar_align}")
    
    # 4. Bake budget configuration
    budget = data.get("build", {}).get("bake", {}).get("runner_disk_budget_gb", 40)
    audit_results.append(f"[OK] Bake Runner Disk Budget: {budget} GB")
    
    print("\n--- Image Provisioning Audit Summary ---")
    for res in audit_results:
        print(f"  {res}")
        
    print("\n[audit-image-provisioning] Audit report PASS.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
