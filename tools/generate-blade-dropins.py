#!/usr/bin/env python3
# AI-hint: Generate systemd capability drop-in files, k3s nodeSelectors, and Pacemaker location rules from the mios.toml [blade.requires] SSOT (AGY-1595).
# AI-related: usr/share/mios/dropins/blade-*.conf, usr/share/mios/dropins/k3s-node-selectors.yaml, usr/share/mios/dropins/pcs-location-rules.pcs, usr/share/mios/mios.toml, automation/98-drift-checks.sh
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOML = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")
DROPINS_DIR = os.path.join(ROOT, "usr/share/mios/dropins")


def build_dropin_content(capability: str) -> str:
    return f"""# AI-hint: GENERATED systemd capability drop-in for MiOS (WS-BLADE). DO NOT EDIT -- regenerate via tools/generate-blade-dropins.py.
[Unit]
ConditionPathExists=/etc/mios/blade.d/{capability}
"""


def build_k3s_selectors(requires: dict) -> str:
    lines = [
        "# AI-hint: GENERATED k3s nodeSelectors/tolerations from mios.toml [blade.requires] SSOT (AGY-1595). DO NOT EDIT.",
        "# Rendered by tools/generate-blade-dropins.py.",
        "services:"
    ]
    for svc, caps in sorted(requires.items()):
        if isinstance(caps, str):
            caps = [caps]
        cap_list = [str(c).strip() for c in (caps or []) if str(c).strip()]
        lines.append(f"  {svc}:")
        lines.append("    nodeSelector:")
        for cap in cap_list:
            lines.append(f"      mios.capability/{cap}: \"true\"")
        lines.append("    tolerations:")
        for cap in cap_list:
            lines.append(f"      - key: \"mios.capability/{cap}\"")
            lines.append("        operator: \"Exists\"")
            lines.append("        effect: \"NoSchedule\"")
    return "\n".join(lines) + "\n"


def build_pcs_rules(requires: dict) -> str:
    lines = [
        "# AI-hint: GENERATED Pacemaker location constraint rules from mios.toml [blade.requires] SSOT (AGY-1595). DO NOT EDIT.",
        "# Rendered by tools/generate-blade-dropins.py."
    ]
    for svc, caps in sorted(requires.items()):
        if isinstance(caps, str):
            caps = [caps]
        cap_list = [str(c).strip() for c in (caps or []) if str(c).strip()]
        if not cap_list:
            continue
        rule_conds = " and ".join(f"mios-cap-{c} eq true" for c in cap_list)
        lines.append(f"pcs constraint location {svc} rule score=100 {rule_conds}")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        with open(TOML, "rb") as f:
            d = tomllib.load(f)
    except Exception as e:
        print(f"[generate-blade-dropins] ERROR: Failed to load {TOML}: {e}", file=sys.stderr)
        return 1

    blade = d.get("blade") or {}
    requires = blade.get("requires") or {}

    unique_caps = set()
    for caps in requires.values():
        if isinstance(caps, list):
            for cap in caps:
                unique_caps.add(str(cap).strip())
        elif isinstance(caps, str):
            unique_caps.add(caps.strip())

    os.makedirs(DROPINS_DIR, exist_ok=True)

    for cap in sorted(unique_caps):
        if not cap:
            continue
        out_path = os.path.join(DROPINS_DIR, f"blade-{cap}.conf")
        content = build_dropin_content(cap)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    k3s_path = os.path.join(DROPINS_DIR, "k3s-node-selectors.yaml")
    with open(k3s_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_k3s_selectors(requires))

    pcs_path = os.path.join(DROPINS_DIR, "pcs-location-rules.pcs")
    with open(pcs_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_pcs_rules(requires))

    print(f"[generate-blade-dropins] Wrote dropins, k3s-node-selectors.yaml and pcs-location-rules.pcs to {DROPINS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
