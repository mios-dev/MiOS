#!/usr/bin/env python3
# AI-hint: GENERATES usr/share/doc/mios/reference/mini-vs-hosted.md from mios.toml.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Project the product and mode comparisons out of the SSOT."""

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
OUT = "usr/share/doc/mios/reference/mini-vs-hosted.md"
SEAT = "endpoint"


def load(root: str) -> dict:
    with open(os.path.join(root, TOML), "rb") as fh:
        return tomllib.load(fh)


def all_packages(data: dict) -> set:
    """Every package name [packages] installs, at any nesting depth. A marker is
    only proof if it is found the same way the installer would find it."""
    out = set()

    def walk(node):
        if isinstance(node, dict):
            for name in node.get("pkgs") or []:
                if isinstance(name, str):
                    out.add(name.strip())
            for key, val in node.items():
                if key != "pkgs" and isinstance(val, (dict, list)):
                    walk(val)
        elif isinstance(node, list):
            for name in node:
                if isinstance(name, str):
                    out.add(name.strip())
                elif isinstance(name, (dict, list)):
                    walk(name)

    walk(data.get("packages") or {})
    return out


_TRACKED = None


def _tracked_set(root: str) -> set:
    """Repo-relative paths git tracks, case-exact.

    A filesystem existence test is case-insensitive on Windows, so the shipped
    document disagreed with its own generator by machine.
    """
    import subprocess
    try:
        out = subprocess.run(["git", "-c", "core.ignorecase=false", "ls-files", "-z"],
                             cwd=root, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=True).stdout.decode("utf-8")
        paths = {r for r in out.split(chr(0)) if r}
        if paths:
            return paths
    except Exception as exc:                      # pragma: no cover
        sys.stderr.write("[mini-vs-hosted] git listing failed (%s); falling back to the filesystem\n" % exc)
    # An empty set would mark EVERY plane unwired, which is the most wrong
    # answer available and exactly what a silent failure produced. Say so and
    # fall back rather than rendering a document full of false negatives.
    return None


def plane_rows(root: str, data: dict) -> list:
    """(plane, role, owner, markers, missing, wired_by, wired, required).
    `required` = a `mini` plane not in [blade].optional_planes. ADR-0016 D14."""
    have = all_packages(data)
    global _TRACKED
    _TRACKED = _tracked_set(root)
    blade = data.get("blade") or {}
    planes = blade.get("planes") or {}
    optional = set(blade.get("optional_planes") or [])
    rows = []
    for name in sorted(planes):
        spec = planes[name] or {}
        markers = [str(m) for m in (spec.get("markers") or [])]
        missing = [m for m in markers if m not in have]
        wired_by = str(spec.get("wired_by") or "").strip()
        wired = bool(wired_by) and (wired_by in _TRACKED if _TRACKED is not None
                                    else os.path.exists(os.path.join(root, wired_by)))
        rows.append((name, str(spec.get("role") or ""), str(spec.get("owner") or ""),
                     markers, missing, wired_by, wired,
                     spec.get("owner") == "mini" and name not in optional))
    return rows


def policy_rows(data: dict) -> list:
    """(key, value, what it settles) for the axes ADR-0016 D11/D12 fixed. An
    SSOT key nothing renders is a decorative key."""
    b = data.get("blade") or {}
    spec = [
        ("blade.hardware", "min_interfaces", "the whole floor -- the LAN is uplink AND downlink"),
        ("blade.hardware", "min_ap_capable", "AP-capable interfaces required; 0 means an AP is optional"),
        ("blade.cluster", "k3s_servers", "k3s-native HA: 3 servers on embedded etcd, one per localhost host"),
        ("blade.cluster", "control_plane_ha", "quorum tolerates one member loss -- and works on a single box"),
        ("blade.fencing", "method", "how a member is fenced -- self-fence, so none must be reached"),
        ("blade.fencing", "diskless", "watchdog driven by quorum, no shared block device"),
        ("blade.storage", "replication", "data classes that shadow-copy Mini-to-Mini"),
        ("blade.storage", "at_rest", "Ceph-native: dm-crypt OSDs, key in the MON config-key store"),
        ("blade.uplink", "failover", "where the DEFAULT ROUTE goes when the WAN dies (the plane stays)"),
        ("blade.cluster", "localhost_hosts", "logical hosts one Mini serves itself as -- \"its own cluster\""),
        ("blade.mesh", "blocks_boot", "Law 12 -- enrolment never gates a boot"),
        ("blade.mesh", "federate", "peers join by each system's OWN mechanism, never by hand"),
        ("blade.hardware", "max_radios", "radios a Mini uses; 0 is a supported build"),
    ]
    out = []
    for table, key, what in spec:
        node = b.get(table.split(".", 1)[1]) or {}
        if key in node:
            out.append(("[%s].%s" % (table, key), node[key], what))
    return out


def shed_split(rows: list) -> tuple:
    """(planes that can move, planes that cannot). This IS the definition of
    offload -- ADR-0016 D10."""
    movable = [r[0] for r in rows if r[2] == "either"]
    fixed = [r[0] for r in rows if r[2] != "either"]
    return sorted(movable), sorted(fixed)


def _caps(v):
    return [v] if isinstance(v, str) else list(v or [])


def _requires(data: dict) -> dict:
    return {k: _caps(v) for k, v in
            ((data.get("blade") or {}).get("requires") or {}).items()}


def archetype_rows(data: dict) -> list:
    """(archetype, capabilities, gated units started, total units)."""
    blade = data.get("blade") or {}
    arche = blade.get("archetypes") or {}
    req = _requires(data)
    seat_n = len(blade.get("seat_side") or [])
    rows = []
    for name in sorted(arche):
        have = set(_caps(arche[name]))
        started = sum(1 for caps in req.values() if set(caps) <= have)
        rows.append((name, sorted(have), started, started + seat_n))
    return rows


def seat_units(data: dict) -> list:
    return sorted((data.get("blade") or {}).get("seat_side") or [])


def gated_off_on_seat(data: dict) -> list:
    """Every unit a seat does NOT start, with the capability that withholds it."""
    have = set(_caps(((data.get("blade") or {}).get("archetypes") or {}).get(SEAT)))
    out = []
    for unit, caps in sorted(_requires(data).items()):
        missing = sorted(set(caps) - have)
        if missing:
            out.append((unit, missing))
    return out


def greenboot_rows(data: dict) -> list:
    """(service, unit it probes, whether a seat probes it)."""
    gb = data.get("greenboot") or {}
    probe = gb.get("probe") or {}
    req = _requires(data)
    have = set(_caps(((data.get("blade") or {}).get("archetypes") or {}).get(SEAT)))
    seat = set(seat_units(data))
    rows = []
    for svc in gb.get("critical_services") or []:
        spec = probe.get(str(svc).replace("-", "_")) or probe.get(svc) or {}
        unit = str(spec.get("unit") or ("mios-%s.service" % svc))
        stem = unit[:-len(".service")] if unit.endswith(".service") else unit
        caps = req.get(stem) or req.get("mios-%s" % svc) or []
        probed = stem in seat or "mios-%s" % svc in seat or set(caps) <= have
        rows.append((str(svc), unit, bool(probed), sorted(caps)))
    return rows


def overlay_keys(data: dict) -> list:
    """The canonical keys a seat's /etc/mios overlay repoints -- the key each
    service's consumers already resolve, never a second name for it."""
    return [
        ("[ai].endpoint", "MIOS_AI_ENDPOINT", "the AI front door every client dials"),
        ("[search].endpoint", "MIOS_SEARCH_ENDPOINT", "web search"),
        ("[nodes.<name>].endpoint", "-", "a compute lane in the fan-out pool"),
        ("[blades.<name>]", "-", "a remote machine's capacity envelope"),
        ("[urls].<tile>", "MIOS_URLS_<TILE>", "a browser-openable tile only"),
    ]


def baked_payloads(data: dict) -> list:
    """[(name, source)] for every model weight the image bakes. Derived, never
    hand-listed -- ADR-0016 D7."""
    out = []
    spec = str(((data.get("llamacpp") or {}).get("bake_models") or "")).strip()
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        local, remote = entry.split("=", 1)
        out.append((local.strip(), remote.strip()))
    vllm = (data.get("ai") or {}).get("vllm") or {}
    model = str(vllm.get("bake_model") or "").strip()
    if model:
        out.append(("vLLM snapshot", model))
    return out


def render(data: dict, root: str = ".") -> str:
    rows = archetype_rows(data)
    seat_row = next(r for r in rows if r[0] == SEAT)
    full = max(rows, key=lambda r: r[3])
    gated = gated_off_on_seat(data)
    gb = greenboot_rows(data)
    blade = data.get("blade") or {}

    L = []
    a = L.append
    a("<!-- AI-hint: GENERATED by tools/generate-mini-vs-hosted.py from mios.toml. "
      "DO NOT EDIT -- re-run the generator. Part 1 compares the two PRODUCTS "
      "([blade.planes]); Part 2 the two MODES ([blade.archetypes]). Every count "
      "is derived, so neither can go stale. ADR-0016 D10-D14. -->")
    a("<!-- AI-related: usr/share/mios/mios.toml, usr/share/doc/mios/adr/"
      "0016-blade-node-topology.md, tools/generate-mini-vs-hosted.py -->")
    a("")
    a("# MiOS-Mini vs hosted MiOS — the products, then the modes")
    a("")
    a("A MiOS-Mini boots the **entire** image, runs the AI plane, is an access "
      "point and a router at once, and is its own cluster (ADR-0016 D9). "
      "\"Offload\" describes what it *can do* — shed a workload across the mesh "
      "to a peer to scale or fail over — never something it lacks. Two earlier "
      "revisions of this page had that backwards and were wrong.")
    a("")
    a("Two different comparisons follow, and confusing them is what produced "
      "those revisions. **Part 1** compares the two *products* — a Mini against "
      "a hosted image, which differ by what metal they own. **Part 2** compares "
      "two *archetypes* — a posture any single node can boot into, which is not "
      "a product at all.")
    a("")
    planes = plane_rows(root, data)
    movable, fixed = shed_split(planes)
    a("## Part 1 — the two products")
    a("")
    a("A **MiOS-Mini** is a box. A **hosted MiOS OCI image** is the same image "
      "in a different position: a container, a VM, or another machine, local or "
      "remote. They are not two builds — one artifact, one tag, one bake. What "
      "separates them is not what they *contain* but what they *own*.")
    a("")
    a("`[blade.planes].owner` is that line, and it is the whole definition of "
      "offload:")
    a("")
    a("- **`mini`** — the plane is bound to metal this box has and a guest does "
      "not: radios, the uplink NIC, the hypervisor itself, the bare-metal "
      "filesystem. It **cannot be shed**, because a hosted image has nothing "
      "to shed it onto.")
    a("- **`either`** — the plane is a workload. A Mini runs it by default and "
      "may hand it to any peer; a hosted image can accept it.")
    a("")
    if not planes:
        a("**`[blade.planes]` is empty**, so nothing declares which planes "
          "a Mini owns and the shed set cannot be derived. That is a defect "
          "in the SSOT, not an empty answer.")
        a("")
    else:
        a("So \"offload all services to hosted MiOS OCI image(s)\" means exactly "
          "**%d of %d planes**: %s. The other %d (%s) are what make the box a Mini, "
          "and a Mini that shed them would stop being one."
          % (len(movable), len(planes),
             ", ".join("`%s`" % m for m in movable),
             len(fixed), ", ".join("`%s`" % f for f in fixed)))
        a("")
        a("| Plane | Owner | Can be shed | A Mini runs it | Baked | Wired |")
        a("|---|---|---|---|---|---|")
        for name, role, owner, markers, missing, wired_by, wired, req in planes:
            if not markers:
                baked = "n/a — payload, not RPM"
            elif missing:
                baked = "**no** — missing `%s`" % "`, `".join(missing)
            else:
                baked = "yes — `%s`" % "`, `".join(markers)
            if not wired_by:
                wire = "**nothing declared**"
            else:
                wire = ("`%s`" % wired_by) if wired else ("**missing** `%s`" % wired_by)
            a("| `%s` | `%s` | %s | %s | %s | %s |"
              % (name, owner, "yes" if owner == "either" else "**no**",
                 "**always**" if req else
                 ("optional" if owner == "mini" else "by default"),
                 baked, wire))
        a("")
        a("| Plane | What it does |")
        a("|---|---|")
        for name, role, _o, _m, _mi, _w, _wd, _rq in planes:
            a("| `%s` | %s |" % (name, role))
        a("")
    if planes:
        hw = (data.get("blade") or {}).get("hardware") or {}
        opt = [r[0] for r in planes if r[2] == "mini" and not r[7]]
        if hw:
            nif = hw.get("min_interfaces", "?")
            a("**MiOS boots on any hardware**, so these numbers gate a *plane*, "
              "never the boot (ADR-0016 D14). The floor is **%s interface%s** — "
              "the LAN is both uplink and downlink — and a radio is optional at "
              "**%s**, of which **%s** need be AP-capable. A box that misses one "
              "still boots; it simply does not run that plane."
              % (nif, "" if nif == 1 else "s",
                 hw.get("max_radios", "?"), hw.get("min_ap_capable", "?")))
            a("")
        if opt:
            a("That is why %s %s `owner = \"mini\"` but **not** required: a Mini "
              "with no radio is still a Mini, whereas one without a hypervisor, "
              "a router, a mesh or CephFS is not."
              % (", ".join("`%s`" % o for o in opt),
                 "is" if len(opt) == 1 else "are"))
            a("")
        pol = policy_rows(data)
        if pol:
            a("The axes the operator settled, as the SSOT now carries them "
              "(ADR-0016 D11 and D12):")
            a("")
            a("| Key | Value | What it settles |")
            a("|---|---|---|")
            for key, val, what in pol:
                shown = str(val).lower() if isinstance(val, bool) else str(val)
                a("| `%s` | `%s` | %s |" % (key, shown, what))
            a("")
        a("**Read the two right-hand columns narrowly.** *Baked* means every "
          "marker package is in `[packages]` — Law 12 satisfied, nothing to "
          "fetch at boot. *Wired* means the named file exists in the tree. "
          "Neither claims the plane is finished: `router` is baked and its "
          "forwarding sysctl is applied, and it still has no NAT ruleset or "
          "client DHCP (T-337). A plane is only complete when a gate proves it "
          "end to end.")
        a("")
        unbaked = [r for r in planes if r[3] and r[4]]
        unwired = [r for r in planes if not r[5]]
        if unbaked or unwired:
            a("What that leaves open right now, derived rather than asserted:")
            a("")
            for name, _r, owner, _m, missing, _w, _wd, _rq in unbaked:
                a("- `%s` (`%s`) is **not baked** — `%s` absent from "
                  "`[packages]`, so the plane would have to be fetched at "
                  "runtime, which Law 12 forbids."
                  % (name, owner, "`, `".join(missing)))
            for name, _r, owner, _m, _mi, wired_by, _wd, _rq in unwired:
                if not wired_by:
                    a("- `%s` (`%s`) has **no wiring declared** — nothing in "
                      "the tree activates it." % (name, owner))
            a("")
            # Derived, not asserted: if a movable plane ever joins this set the
            # sentence must change, because then a peer COULD supply it.
            open_owners = set(r[2] for r in unbaked) | set(
                r[2] for r in unwired if not r[5])
            if open_owners == {"mini"}:
                a("Every one of those is an `owner = \"mini\"` plane, and that "
                  "is the finding: the planes a hosted image was never going to "
                  "provide are exactly the ones the Mini does not have yet — "
                  "and the only ones adding a peer cannot supply.")
            else:
                a("Not all of those are `owner = \"mini\"`. The `%s` ones can "
                  "be supplied by adding a peer; the `mini` ones cannot."
                  % "`, `".join(sorted(open_owners - {"mini"})))
            a("")
    a("## Part 2 — the two modes")
    a("")
    a("Part 1 asked what a machine *owns*. This asks what a machine *starts*. "
      "The two archetypes are `%s`, which grants no capabilities, against the "
      "widest one. Both are the same OCI image, byte for byte — no separate "
      "Containerfile, tag or conditional bake — so every difference below is a "
      "*runtime* difference." % SEAT)
    a("")
    a("| Surface | `%s` (grants nothing) | `%s` (widest) |" % (SEAT, full[0]))
    a("|---|---|---|")
    a("| Image | identical OCI image and tag | identical |")
    a("| Bake | every payload baked, including model weights | identical |")
    a("| Units started | **%d** | **%d** |" % (seat_row[3], full[3]))
    a("| Capabilities granted | *(none)* | `%s` |" % "`, `".join(full[1]))
    a("| Capability-gated units it starts | %d | %d |" % (seat_row[2], full[2]))
    a("| Always-on units (`[blade].seat_side`) | %d | %d |"
      % (len(seat_units(data)), len(seat_units(data))))
    a("| Local inference lanes | **0** | up to %d |"
      % sum(1 for u, _ in gated if "llm" in u or u.endswith("cpu-node")))
    a("| Greenboot probes | %d of %d critical services | %d of %d |"
      % (sum(1 for r in gb if r[2]), len(gb),
         len(gb), len(gb)))
    a("| Addressing | `/etc/mios` overlay repoints the canonical keys | vendor defaults, all `localhost` |")
    a("")
    a("## What a seat runs, and why each one")
    a("")
    a("`[blade].seat_side` is a positive declaration, not debt: a seat runs what "
      "the **person** touches, a blade runs what the **work** needs.")
    a("")
    a("| Unit | Why a seat keeps it |")
    a("|---|---|")
    for u in seat_units(data):
        a("| `%s` | local I/O |" % u)
    a("")
    a("## What a seat does not run")
    a("")
    a("%d units are capability-gated off. A failed `ConditionPathExists` is a "
      "clean skip, not a failure — the unit is *baked and present*, it simply "
      "never starts." % len(gated))
    a("")
    a("| Withheld capability | Units it gates off |")
    a("|---|---|")
    by_cap = {}
    for unit, missing in gated:
        by_cap.setdefault(", ".join(missing), []).append(unit)
    for cap in sorted(by_cap):
        a("| `%s` | %d |" % (cap, len(by_cap[cap])))
    a("")
    a("## Health: what greenboot asks on each")
    a("")
    a("| Critical service | Unit probed | On a seat |")
    a("|---|---|---|")
    for svc, unit, probed, caps in gb:
        a("| `%s` | `%s` | %s |"
          % (svc, unit, "probed" if probed else
             "skipped (needs `%s`)" % "`, `".join(caps)))
    a("")
    a("`[greenboot].blade_reachability_critical = %s` — a seat whose blade is "
      "unreachable does **not** roll itself back."
      % str(bool((data.get("greenboot") or {}).get("blade_reachability_critical"))).lower())
    a("")
    a("## Addressing: the only thing an operator changes")
    a("")
    a("A service's canonical address is the key its consumers already resolve "
      "(ADR-0016 Decision 1). \"local, localhost or remote\" are three *values* "
      "of one mechanism.")
    a("")
    a("| Overlay key | Canonical env | What it moves |")
    a("|---|---|---|")
    for key, env, what in overlay_keys(data):
        a("| `%s` | `%s` | %s |" % (key, env, what))
    a("")
    a("## The seat's defining constraint")
    a("")
    a("A seat has **no local inference floor**. Every lane — heavy, alt, light "
      "and the CPU node — is capability-gated off, including the lane the "
      "resolver calls \"the always-on floor\". When the blade is unreachable a "
      "seat has a front door that can reach nothing. The model weights are "
      "baked regardless (Law 12), so a seat carries them and never loads them.")
    payloads = baked_payloads(data)
    if payloads:
        a("")
        a("Exactly what it carries and never loads — derived from "
          "`[llamacpp].bake_models` and `[ai.vllm].bake_model`, so this list "
          "cannot drift from what the image actually bakes:")
        a("")
        a("| Baked payload | Source |")
        a("|---|---|")
        for name, source in payloads:
            a("| `%s` | `%s` |" % (name, source))
        vllm = (data.get("ai") or {}).get("vllm") or {}
        if str(vllm.get("bake_model") or "").strip() and not vllm.get("enable"):
            a("")
            a("The vLLM snapshot is baked while `[ai.vllm].enable = false`: it "
              "ships on every image, seat and blade alike, and no archetype "
              "starts the lane that would load it. That is an unreviewed "
              "default rather than Law 12 discipline — see T-330.")
    a("")
    a("Whether that is right is an operator decision, recorded in ADR-0016 "
      "Decision 6, not a defect: giving a seat a micro local lane would trade "
      "\"offload *all* services\" for a degraded-but-alive floor.")
    a("")
    return "\n".join(L) + "\n"


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    check = "--check" in sys.argv
    try:
        data = load(root)
    except OSError as exc:
        print("generate-mini-vs-hosted: cannot read the SSOT: %s" % exc,
              file=sys.stderr)
        return 1
    want = render(data, root)
    path = os.path.join(root, OUT)
    if check:
        try:
            with open(path, encoding="utf-8") as fh:
                have = fh.read()
        except OSError:
            print("generate-mini-vs-hosted: %s is missing -- run the generator"
                  % OUT, file=sys.stderr)
            return 1
        if have.replace("\r\n", "\n") != want:
            print("generate-mini-vs-hosted: %s has drifted from the SSOT -- "
                  "re-run tools/generate-mini-vs-hosted.py" % OUT, file=sys.stderr)
            return 1
        print("[generate-mini-vs-hosted] %s matches the SSOT" % OUT)
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(want)
    print("[generate-mini-vs-hosted] wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
