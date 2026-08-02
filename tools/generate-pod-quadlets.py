#!/usr/bin/env python3
# AI-hint: Generate .pod Quadlets from the mios.toml [pods.*] co-resident groups (WS-7 pods-as-SSOT). Renders usr/share/containers/systemd/<name>.pod deterministically from each [pods.<name>] (description/network/after/wants/wanted_by/members/doc) so a co-resident container group is declared ONCE in SSOT and the Quadlet can't drift; tools/generate-k3s-manifests.sh then projects the live pods to k3s. --check (drift gate) compares without writing; --selftest asserts the pure renderer offline.
# AI-related: usr/share/mios/mios.toml, usr/share/containers/systemd, tools/generate-k3s-manifests.sh, automation/98-drift-checks.sh, automation/34-render-quadlets.sh
# AI-functions: render_pod_quadlet, _wrap_doc, load_pods, main, _selftest
"""Generate MiOS .pod Quadlets from the [pods.*] SSOT (WS-7).

A co-resident group -- a set of containers that must share a podman pod (one
network namespace + lifecycle) -- was previously a hand-authored .pod Quadlet
(only mios-webtools). That is drift-prone: the pod's [Unit]/[Pod]/[Install] and
its member list lived only in the file. This projects each [pods.<name>] in
mios.toml to a deterministic <name>.pod under usr/share/containers/systemd/, so:

  * the co-resident group is declared ONCE (SSOT), and
  * tools/generate-k3s-manifests.sh -- which reads the LIVE pods -- projects the
    same workloads to k3s, so the cluster path is one faithful bridge from SSOT.

Each member .container still declares `Pod=<name>.pod` (Quadlet wires the
Wants/After on the pod service); the member list here is the documented SSOT +
fuels a drift check that every declared member exists as a .container.

Pure renderer (render_pod_quadlet) so it unit-tests offline (--selftest), in the
sibling style of the other tools/ generators. Same SSOT -> byte-identical output.
"""
from __future__ import annotations

import os
import sys
import re

_SIDECARS: dict = {}

def _sidecar_image(var_name: str):
    """Digest-pinned image for a MIOS_<X>_IMAGE var from [image.sidecars] (the
    digest SSOT), used when the env isn't sourced so bare regeneration renders
    the SAME @sha256 as a build-time render (fixes Quadlet digest clobber).
    Returns None for non-image vars or sidecars not in SSOT (keeps literal
    fallback behaviour for locally-built images like MIOS_FIRECRAWL_IMAGE)."""
    m = re.match(r'^MIOS_(.+)_IMAGE$', var_name)
    if not m:
        return None
    val = _SIDECARS.get(m.group(1).lower())
    return val if isinstance(val, str) and val else None

def resolve_env_vars(val: str | bool | list | dict) -> str | bool | list | dict:
    if isinstance(val, list):
        return [resolve_env_vars(x) for x in val]
    if isinstance(val, dict):
        return {k: resolve_env_vars(v) for k, v in val.items()}
    if not isinstance(val, str):
        return val
    
    def _env(var_name: str):
        v = os.environ.get(var_name)
        return v if v else None

    def repl_fallback(m):
        var_name = m.group(1)
        fallback = m.group(2)
        if var_name.startswith("MIOS_PORT_"):
            return f"${{{var_name}}}"
        # FEDORA_VERSION floats from SSOT: keep it a placeholder (like MIOS_PORT_*) so the
        # committed Quadlet is NOT baked to a hardcoded fedora-NN at generation. Resolved at
        # build/render, keeping check_pod_quadlets and check_no_hardcoded_ssot_literal both happy.
        if var_name == "FEDORA_VERSION":
            return m.group(0)
        env_val = _env(var_name)
        if env_val is not None:
            return env_val
        pinned = _sidecar_image(var_name)
        if pinned is not None:
            return pinned
        return fallback
    val = re.sub(r'\$\{([A-Za-z0-9_]+):-([^}]*)\}', repl_fallback, val)

    def repl_var(m):
        var_name = m.group(1)
        if var_name.startswith("MIOS_PORT_"):
            return m.group(0)
        if var_name == "FEDORA_VERSION":
            return m.group(0)
        env_val = _env(var_name)
        if env_val is not None:
            return env_val
        pinned = _sidecar_image(var_name)
        if pinned is not None:
            return pinned
        return m.group(0)
    val = re.sub(r'\$\{([A-Za-z0-9_]+)\}', repl_var, val)
    
    return val

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
TOML = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")
OUT_DIR = os.environ.get("MIOS_POD_OUT") or os.path.join(
    ROOT, "usr/share/containers/systemd")


def _wrap_doc(doc: str, width: int = 76) -> "list[str]":
    """Wrap the SSOT `doc` prose into `# `-prefixed comment lines (deterministic,
    greedy word wrap) so the rationale rides in the generated Quadlet."""
    out: list[str] = []
    for para in str(doc or "").split("\n"):
        words = para.split()
        if not words:
            out.append("#")
            continue
        line = "#"
        for w in words:
            if len(line) + 1 + len(w) > width and line != "#":
                out.append(line)
                line = "# " + w
            else:
                line = (line + " " + w) if line != "#" else "# " + w
        out.append(line)
    return out


def _resolve_port(port_str: str, ports: dict) -> str:
    parts = port_str.split(":")
    resolved_parts = []
    for p in parts:
        p_clean = p.strip()
        if p_clean.startswith("${") and p_clean.endswith("}"):
            p_clean = p_clean[2:-1]
            if p_clean.startswith("ports."):
                p_clean = p_clean[6:]
        if p_clean in ports:
            resolved_parts.append(str(ports[p_clean]))
        else:
            resolved_parts.append(p)
    return ":".join(resolved_parts)


def render_pod_quadlet(name: str, spec: dict, ports: dict | None = None) -> str:
    """Render the .pod Quadlet text for one [pods.<name>] spec. Deterministic:
    sorted nothing (preserve declared order), fixed section order. PodName is the
    pod `name` with any leading 'mios-' kept (the unit is <name>.pod -> Quadlet
    derives <name>-pod.service)."""
    desc = resolve_env_vars(str(spec.get("description") or f"MiOS {name} pod"))
    network = resolve_env_vars(str(spec.get("network") or "host"))
    after = [resolve_env_vars(str(x)) for x in (spec.get("after") or [])]
    wants = [resolve_env_vars(str(x)) for x in (spec.get("wants") or [])]
    wanted_by = [resolve_env_vars(str(x)) for x in (spec.get("wanted_by") or ["multi-user.target"])]
    publish_ports = [resolve_env_vars(str(x)) for x in (spec.get("publish_ports") or [])]
    if ports:
        publish_ports = [_resolve_port(p, ports) for p in publish_ports]
    members = [str(x).split("#", 1)[0].strip() for x in (spec.get("members") or [])]
    members = [m for m in members if m]

    lines: list[str] = []
    lines.append(
        f"# AI-hint: GENERATED Quadlet pod for the co-resident group '{name}' "
        f"(WS-7 pods-as-SSOT). DO NOT EDIT -- regenerate via "
        f"tools/generate-pod-quadlets.py from [pods.{name}] in mios.toml. "
        f"Members ({len(members)}): {', '.join(members)}.")
    lines.append(
        f"# AI-related: usr/share/mios/mios.toml, tools/generate-pod-quadlets.py, "
        + ", ".join(f"{m}.container" for m in members))
    lines.append(f"# /usr/share/containers/systemd/{name}.pod")
    if spec.get("doc"):
        lines.extend(_wrap_doc(spec["doc"]))
    if members:
        lines.append("# Members (each member .container declares Pod="
                     f"{name}.pod):")
        for m in members:
            lines.append(f"#   {m}")
    lines.append("[Unit]")
    lines.append(f"Description={desc}")
    if after:
        lines.append("After=" + " ".join(after))
    if wants:
        lines.append("Wants=" + " ".join(wants))
    lines.append("")
    lines.append("[Pod]")
    lines.append(f"PodName={name}")
    lines.append(f"Network={network}")
    for port in publish_ports:
        lines.append(f"PublishPort={port}")
    lines.append("")
    lines.append("[Install]")
    lines.append("WantedBy=" + " ".join(wanted_by))
    return "\n".join(lines) + "\n"


def load_pods(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("pods") or {}


def load_ports(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("ports") or {}


def load_sidecars(toml_path: str) -> dict:
    """[image.sidecars] -- the digest-pinned image SSOT. Consulted by
    _sidecar_image() so bare (no-userenv) regeneration renders the committed
    @sha256 instead of the digestless inline fallback (Quadlet digest drift)."""
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return (d.get("image") or {}).get("sidecars") or {}


def load_containers(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("containers") or {}


def load_networks(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("networks") or d.get("network") or {}


def load_volumes(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("volumes") or d.get("volume") or {}


def load_enabled_quadlets(toml_path: str) -> dict:
    with open(toml_path, "rb") as f:
        d = tomllib.load(f)
    return d.get("quadlets", {}).get("enable", {})


def render_nested_quadlet(name: str, spec: dict, unit_type: str) -> str:
    lines: list[str] = []
    lines.append(
        f"# AI-hint: GENERATED Quadlet {unit_type} '{name}' "
        f"(WS-7 pods-as-SSOT). DO NOT EDIT -- regenerate via "
        f"tools/generate-pod-quadlets.py from [{unit_type}s.{name}] in mios.toml."
    )
    lines.append(f"# /usr/share/containers/systemd/{name}.{unit_type}")
    if name == "mios-llm-heavy-alt" and unit_type == "container":
        lines.append("# DEPRECATED (Part 10): retire by setting [converge.inference].retire_heavy_alt = true and running the migration guide at usr/share/doc/mios/guides/inference-consolidation.md.")
    
    main_section = unit_type.capitalize()
    
    def section_key(sec_name: str):
        if sec_name.lower() == "unit":
            return (0, sec_name)
        elif sec_name.lower() == main_section.lower():
            return (1, sec_name)
        elif sec_name.lower() == "install":
            return (2, sec_name)
        else:
            return (3, sec_name)
            
    for sec in sorted(spec.keys(), key=section_key):
        sec_data = spec[sec]
        if not isinstance(sec_data, dict):
            continue
        lines.append("")
        lines.append(f"[{sec}]")
        for k in sorted(sec_data.keys()):
            val = sec_data[k]
            if isinstance(val, list):
                for item in val:
                    resolved_item = resolve_env_vars(item)
                    lines.append(f"{k}={resolved_item}")
            elif isinstance(val, bool):
                lines.append(f"{k}={'true' if val else 'false'}")
            else:
                resolved_val = resolve_env_vars(val)
                if k == "Image" and resolved_val == "":
                    continue
                if k in ("User", "Group") and resolved_val == "":
                    continue
                lines.append(f"{k}={resolved_val}")

                
    return "\n".join(lines).strip() + "\n"


def main(argv: "list[str]") -> int:
    if "--selftest" in argv:
        return _selftest()
    check = "--check" in argv
    global _SIDECARS
    _SIDECARS = load_sidecars(TOML)
    enabled_map = load_enabled_quadlets(TOML)
    pods = load_pods(TOML)
    ports = load_ports(TOML)
    containers = load_containers(TOML)
    networks = load_networks(TOML)
    volumes = load_volumes(TOML)

    for name in enabled_map:
        if name not in containers:
            print(f"[pod-gen] ERROR: key '{name}' in [quadlets.enable] does not map to any container in [containers]", file=sys.stderr)
            return 1

    if not pods and not containers and not networks and not volumes:
        print("[pod-gen] no Quadlets in SSOT -- nothing to do")
        return 0

    for pod_name, pod_spec in pods.items():
        if "members" in pod_spec:
            filtered_members = []
            for m in pod_spec["members"]:
                m_name = str(m).split("#", 1)[0].strip()
                if enabled_map.get(m_name) is not False:
                    filtered_members.append(m)
            pod_spec["members"] = filtered_members

    os.makedirs(OUT_DIR, exist_ok=True)
    drift = 0
    wrote = 0
    member_miss = 0
    active_units = 0

    for name in sorted(pods):
        spec = pods[name]
        if not isinstance(spec, dict):
            continue
        text = render_pod_quadlet(name, spec, ports)
        out = os.path.join(OUT_DIR, f"{name}.pod")
        for m in [str(x).split("#", 1)[0].strip() for x in (spec.get("members") or [])]:
            if m and not os.path.exists(os.path.join(OUT_DIR, f"{m}.container")):
                print(f"[pod-gen] WARN {name}: member {m}.container missing", file=sys.stderr)
                member_miss += 1
        active_units += 1
        if check:
            cur = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    cur = f.read()
            if cur != text:
                print(f"[pod-gen] DRIFT {out} (regenerate via tools/generate-pod-quadlets.py)",
                      file=sys.stderr)
                drift += 1
            continue
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        wrote += 1
        print(f"[pod-gen]   wrote {out}")

    categories = [
        (containers, "container"),
        (networks, "network"),
        (volumes, "volume")
    ]

    for specs, unit_type in categories:
        for name in sorted(specs):
            spec = specs[name]
            if not isinstance(spec, dict):
                continue

            if unit_type == "container" and enabled_map.get(name) is False:
                out = os.path.join(OUT_DIR, f"{name}.{unit_type}")
                if check:
                    if os.path.exists(out):
                        print(f"[pod-gen] DRIFT {out} should not exist (disabled in SSOT)", file=sys.stderr)
                        drift += 1
                else:
                    if os.path.exists(out):
                        os.remove(out)
                        print(f"[pod-gen]   removed disabled {out}")
                continue

            text = render_nested_quadlet(name, spec, unit_type)
            out = os.path.join(OUT_DIR, f"{name}.{unit_type}")
            active_units += 1
            if check:
                cur = ""
                if os.path.exists(out):
                    with open(out, encoding="utf-8") as f:
                        cur = f.read()
                if cur != text:
                    print(f"[pod-gen] DRIFT {out} (regenerate via tools/generate-pod-quadlets.py)",
                          file=sys.stderr)
                    drift += 1
                continue
            with open(out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            wrote += 1
            print(f"[pod-gen]   wrote {out}")

    if check:
        if drift:
            print(f"[pod-gen] {drift} Quadlet unit(s) DRIFTED from SSOT", file=sys.stderr)
            return 1
        print(f"[pod-gen] all {active_units} Quadlet unit(s) match SSOT")
        return 1 if member_miss else 0

    print(f"[pod-gen] wrote {wrote} Quadlet unit(s) to {OUT_DIR}")
    return 0


def _selftest() -> int:
    fails = 0

    def ck(name, cond):
        nonlocal fails
        if not cond:
            fails += 1
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    spec = {
        "description": "test pod",
        "network": "host",
        "after": ["network-online.target", "x.service"],
        "wants": ["network-online.target"],
        "wanted_by": ["multi-user.target", "default.target"],
        "publish_ports": ["8080:8080", "${ports.open_webui}:8080", "searxng:80"],
        "members": ["mios-a", "mios-b  # comment"],
        "doc": "Line one rationale that is reasonably long so wrapping engages across the width boundary deterministically.",
    }
    mock_ports = {"open_webui": 8033, "searxng": 8899}
    t = render_pod_quadlet("mios-test", spec, mock_ports)
    ck("selftest: has [Pod] section", "[Pod]" in t)
    ck("selftest: PodName from name", "PodName=mios-test" in t)
    ck("selftest: Network rendered", "Network=host" in t)
    ck("selftest: PublishPort literal rendered", "PublishPort=8080:8080" in t)
    ck("selftest: PublishPort resolved placeholder", "PublishPort=8033:8080" in t)
    ck("selftest: PublishPort resolved raw name", "PublishPort=8899:80" in t)
    ck("selftest: After joined", "After=network-online.target x.service" in t)
    ck("selftest: Wants joined", "Wants=network-online.target" in t)
    ck("selftest: WantedBy joined", "WantedBy=multi-user.target default.target" in t)
    ck("selftest: member comment stripped", "mios-b.container" in t and "# comment" not in t.split("AI-related")[1].split("\n")[0])
    ck("selftest: doc wrapped as comments", "# Line one rationale" in t)
    ck("selftest: deterministic", render_pod_quadlet("mios-test", spec, mock_ports) == t)
    ck("selftest: trailing newline", t.endswith("\n"))

    container_spec = {
        "Unit": {
            "Description": "Test container unit",
            "After": "network-online.target"
        },
        "Container": {
            "Image": "docker.io/library/alpine:latest",
            "ContainerName": "test-alpine",
            "Environment": ["A=1", "B=2"]
        }
    }
    tc = render_nested_quadlet("test", container_spec, "container")
    ck("selftest nested: has [Unit] section", "[Unit]" in tc)
    ck("selftest nested: has [Container] section", "[Container]" in tc)
    ck("selftest nested: has Environment entries", "Environment=A=1" in tc and "Environment=B=2" in tc)
    ck("selftest nested: Unit section before Container", tc.index("[Unit]") < tc.index("[Container]"))
    ck("selftest nested: trailing newline", tc.endswith("\n"))

    global _SIDECARS
    _SIDECARS = {"pgvector": "docker.io/pgvector/pgvector:0.8.3-pg17@sha256:deadbeef"}
    os.environ.pop("MIOS_PGVECTOR_IMAGE", None)
    img_spec = {"Container": {"Image": "${MIOS_PGVECTOR_IMAGE:-docker.io/pgvector/pgvector:0.8.3-pg17}"}}
    ic = render_nested_quadlet("mios-pgvector", img_spec, "container")
    ck("selftest: bare-env resolves digest from [image.sidecars]", "@sha256:deadbeef" in ic)

    priv_spec = {"Container": {
        "Image": "${MIOS_PGVECTOR_IMAGE:-docker.io/pgvector/pgvector:0.8.3-pg17}",
        "User": "${MIOS_GUACD_UID:-811}",
        "Group": "${MIOS_GUACD_GID:-811}",
    }}
    for _v in ("MIOS_GUACD_UID", "MIOS_GUACD_GID", "MIOS_PGVECTOR_IMAGE"):
        os.environ[_v] = ""
    pc = render_nested_quadlet("mios-guacd", priv_spec, "container")
    for _v in ("MIOS_GUACD_UID", "MIOS_GUACD_GID", "MIOS_PGVECTOR_IMAGE"):
        os.environ.pop(_v, None)
    ck("selftest: empty env var falls back to inline default (User=)", "User=811" in pc)
    ck("selftest: empty env var falls back to inline default (Group=)", "Group=811" in pc)
    ck("selftest: empty env var still resolves the sidecar digest", "@sha256:deadbeef" in pc)
    ck("selftest: empty-env render == bare-env render",
       pc == render_nested_quadlet("mios-guacd", priv_spec, "container"))
    _SIDECARS = {}

    print(f"\n{'ok' if fails == 0 else str(fails) + ' FAILED'}")
    return 1 if fails else 0



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
