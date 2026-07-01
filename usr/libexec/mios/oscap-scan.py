#!/usr/bin/env python3
# AI-hint: Helper script to parse mios.toml compliance options, dynamically construct an XCCDF tailoring file to skip specified rules, invoke oscap-im for scan/remediation, and execute mios-oscap-gate to enforce the build gate.
# AI-related: /usr/share/mios/mios.toml, /usr/libexec/mios/mios-oscap-gate, Containerfile, oscap-im

import os
import sys
import subprocess
import tomllib
from datetime import datetime

TOML_PATH = "/usr/share/mios/mios.toml"

def log(msg):
    print(f"[oscap-scan] {msg}", flush=True)

def die(msg):
    print(f"[oscap-scan] FATAL: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)

def main():
    if not os.path.exists(TOML_PATH):
        log(f"{TOML_PATH} not found. Skipping compliance check.")
        sys.exit(0)

    try:
        with open(TOML_PATH, "rb") as f:
            cfg = tomllib.load(f)
    except Exception as e:
        die(f"Failed to parse {TOML_PATH}: {e}")

    compliance = cfg.get("compliance", {})
    enabled = compliance.get("enabled", False)
    if not enabled:
        log("Compliance scan not enabled in mios.toml. Skipping.")
        sys.exit(0)

    profile = compliance.get("profile", "standard")
    datastream = compliance.get("datastream", "")
    severity_gate = compliance.get("severity_gate", "high")
    fetch_resources = compliance.get("fetch_remote_resources", False)
    report_path = compliance.get("report_path", "/usr/share/mios/compliance")
    skip_rules = compliance.get("oscap_skip_rules", [])

    # Resolve datastream path
    ds_path = datastream
    if not ds_path:
        os_candidates = []
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ID="):
                        val = line.split("=", 1)[1].strip('"').strip("'")
                        os_candidates.append(val)
                    elif line.startswith("ID_LIKE="):
                        val = line.split("=", 1)[1].strip('"').strip("'")
                        os_candidates.extend(val.split())
        os_candidates.append("fedora")  # final safety default

        for os_id in os_candidates:
            cand = f"/usr/share/xml/scap/ssg/content/ssg-{os_id}-ds.xml"
            if os.path.exists(cand):
                ds_path = cand
                break
            # Try rpm query lookup
            try:
                out = subprocess.check_output(["rpm", "-ql", "scap-security-guide"], text=True)
                found = False
                for line in out.splitlines():
                    if line.endswith(f"/ssg-{os_id}-ds.xml"):
                        ds_path = line.strip()
                        found = True
                        break
                if found:
                    break
            except Exception:
                pass

    if not ds_path or not os.path.exists(ds_path):
        die(f"SSG datastream not found at {ds_path}. Is scap-security-guide installed?")

    log(f"Starting compliance scan: profile={profile}, datastream={ds_path}, severity_gate={severity_gate}")

    os.makedirs(report_path, exist_ok=True)
    arf_path = os.path.join(report_path, "oscap-results-arf.xml")
    html_path = os.path.join(report_path, "oscap-report.html")

    tailoring_file = None
    profile_to_run = f"xccdf_org.ssgproject.content_profile_{profile}"

    if skip_rules:
        tailoring_file = "/tmp/tailoring.xml"
        profile_to_run = "xccdf_compliance_profile_custom"
        log(f"Generating tailoring file {tailoring_file} to skip {len(skip_rules)} rule(s)")
        
        selects = "\n".join(f'        <xccdf:select idref="{rule}" selected="false"/>' for rule in skip_rules)
        time_str = datetime.now().isoformat()
        
        tailoring_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<xccdf:Tailoring xmlns:xccdf="http://checklists.nist.gov/xccdf/1.2" id="xccdf_compliance_tailoring_default">
    <xccdf:benchmark href="{ds_path}"/>
    <xccdf:version time="{time_str}">1.0</xccdf:version>
    <xccdf:Profile id="xccdf_compliance_profile_custom" extends="xccdf_org.ssgproject.content_profile_{profile}">
        <xccdf:title>Custom Compliance Profile</xccdf:title>
{selects}
    </xccdf:Profile>
</xccdf:Tailoring>
"""
        with open(tailoring_file, "w", encoding="utf-8") as f:
            f.write(tailoring_xml)

    # Construct oscap-im command
    cmd = ["oscap-im", "--results-arf", arf_path, "--report", html_path]
    if fetch_resources:
        cmd.append("--fetch-remote-resources")
    if tailoring_file:
        cmd.extend(["--tailoring-file", tailoring_file])
    cmd.extend(["--profile", profile_to_run, ds_path])

    log(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        die(f"oscap-im failed with exit code {e.returncode}")

    # Enforce the gate
    gate_bin = "/usr/libexec/mios/mios-oscap-gate"
    if not os.path.exists(gate_bin):
        # Fallback to local dev tree lookup
        gate_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mios-oscap-gate")

    if not os.path.exists(gate_bin):
        die(f"Gating executable not found at {gate_bin}")

    log(f"Running severity gate: {gate_bin} {arf_path} {severity_gate}")
    try:
        subprocess.run([gate_bin, arf_path, severity_gate], check=True)
    except subprocess.CalledProcessError as e:
        die(f"Compliance gate FAILED with exit code {e.returncode} (failed rules found at/above severity '{severity_gate}')")

    log("Compliance gate PASSED successfully.")

if __name__ == "__main__":
    main()
