#!/usr/bin/env python3
# AI-hint: Drift gate for the blade ROLE axis -- Law 9 applied to the one value that decides what an image is.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: the blade role is stated once, legally, and in one place."""

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
UNIT_DIR = "usr/lib/systemd/system"

# Both halves of the resolver twin. Neither may keep the retired names alive.
KEEP_LISTS = ("usr/lib/mios/mios_toml.py",
              "tools/native/mios-ssot-walk/src/lib.rs")
RETIRED_NAMES = ("MIOS_PROFILE_ROLE", "MIOS_PROFILE_FEATURES")

# Executable blade code: a re-introduced `case "$ROLE" in hybrid) ...` here is
# a second copy of [blade.archetypes].
BLADE_CODE = ("usr/lib/mios/blade.sh",
              "usr/libexec/mios/role-apply",
              "usr/libexec/mios/mios-blade")

def archetypes(data: dict) -> dict:
    """{name: [capability, ...]} from [blade.archetypes]."""
    out = {}
    for name, caps in ((data.get("blade") or {}).get("archetypes") or {}).items():
        if isinstance(caps, str):
            caps = [caps]
        out[str(name)] = [str(c).strip() for c in (caps or []) if str(c).strip()]
    return out

def aliases(data: dict) -> dict:
    """{legacy-spelling: archetype} from [blade.role_aliases]."""
    return {str(k): str(v)
            for k, v in ((data.get("blade") or {}).get("role_aliases") or {}).items()}

def role_targets(data: dict) -> list:
    """The unit each archetype's name derives, in [blade.archetypes] order."""
    return ["mios-%s.target" % name for name in sorted(archetypes(data))]

def unit_body(root: str, name: str) -> str:
    try:
        with open(os.path.join(root, UNIT_DIR, name), encoding="utf-8",
                  errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""

def check_type(data: dict) -> list:
    arche = archetypes(data)
    btype = str((data.get("blade") or {}).get("type") or "").strip()
    if not btype:
        return ["[blade].type is empty -- the image would have no archetype"]
    if not arche:
        return ["[blade.archetypes] is empty -- the gate would pass vacuously"]
    if btype not in arche:
        return ["[blade].type is '%s', which is not an archetype (declared: %s)"
                % (btype, ", ".join(sorted(arche)))]
    return []

def check_targets(data: dict, root: str) -> list:
    viol = []
    for name in sorted(archetypes(data)):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            viol.append("archetype '%s' is not a legal unit-name stem -- it derives "
                        "mios-%s.target" % (name, name))
        unit = "mios-%s.target" % name
        if not os.path.isfile(os.path.join(root, UNIT_DIR, unit)):
            viol.append("archetype '%s' derives %s, which is not a shipped unit -- "
                        "role-apply would set-default a target that does not exist"
                        % (name, unit))
    return viol

def check_capabilities_consumed(data: dict) -> list:
    """Every capability an archetype grants must be required by some unit --
    the reverse of check_blade_coverage, which proves the forward direction."""
    granted, viol = set(), []
    for caps in ((data.get("blade") or {}).get("archetypes") or {}).values():
        if isinstance(caps, str):
            caps = [caps]
        granted |= {str(c).strip() for c in (caps or []) if str(c).strip()}
    required = set()
    for caps in ((data.get("blade") or {}).get("requires") or {}).values():
        if isinstance(caps, str):
            caps = [caps]
        required |= {str(c).strip() for c in (caps or []) if str(c).strip()}
    for cap in sorted(granted - required):
        viol.append("capability '%s' is granted by an archetype but required by "
                    "NO unit -- an archetype that grants only it is a duplicate "
                    "of one that grants nothing" % cap)
    return viol

def check_aliases(data: dict) -> list:
    viol, arche = [], archetypes(data)
    for legacy, target in sorted(aliases(data).items()):
        if target not in arche:
            viol.append("[blade.role_aliases].%s points at '%s', which is not an "
                        "archetype" % (legacy, target))
        if legacy in arche:
            viol.append("[blade.role_aliases].%s shadows an archetype of the same "
                        "name -- one spelling, one meaning (Law 9)" % legacy)
    return viol

def check_conflicts(data: dict, root: str) -> list:
    """Role targets must conflict pairwise: they are reached by `systemctl
    start`, not by isolation, so a missing edge leaves the old role active."""
    viol, targets = [], role_targets(data)
    if len(targets) < 2:
        return viol
    for unit in targets:
        body = unit_body(root, unit)
        if not body:
            continue  # check_targets already reported the missing unit
        m = re.search(r"^Conflicts=(.*)$", body, re.M)
        have = set(m.group(1).split()) if m else set()
        want = set(targets) - {unit}
        missing = sorted(want - have)
        if missing:
            viol.append("%s does not conflict with %s -- switching away from it "
                        "would leave it active" % (unit, ", ".join(missing)))
        stray = sorted(have - want)
        if stray:
            viol.append("%s conflicts with %s, which is not a role target"
                        % (unit, ", ".join(stray)))
    return viol

def check_aliases_in_units(root: str) -> list:
    """An Alias= must carry the same suffix as the unit itself; systemd cannot
    install one that does not, leaving the unit with no [Install] at all."""
    viol = []
    unit_dir = os.path.join(root, UNIT_DIR)
    if not os.path.isdir(unit_dir):
        return viol
    for name in sorted(os.listdir(unit_dir)):
        path = os.path.join(unit_dir, name)
        if not os.path.isfile(path) or "." not in name:
            continue
        suffix = "." + name.rsplit(".", 1)[1]
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        for m in re.finditer(r"^Alias=(.*)$", body, re.M):
            for alias in m.group(1).split():
                if not alias.endswith(suffix):
                    viol.append("%s declares Alias=%s -- an alias must carry the "
                                "same suffix (%s) as its unit, so systemd cannot "
                                "install it" % (name, alias, suffix))
    return viol

def check_profile_retired(data: dict, root: str) -> list:
    """[profile].role was a second spelling of the archetype, read by nothing.
    It may come back only as a legal alias of [blade].type."""
    viol, arche = [], archetypes(data)
    profile = data.get("profile")
    if isinstance(profile, dict):
        for key in profile:
            if key.lower() == "role":
                val = str(profile[key] or "").strip()
                if val not in arche:
                    viol.append("[profile].%s is '%s', which is not a legal "
                                "[blade].type (declared: %s)"
                                % (key, val, ", ".join(sorted(arche))))
            if key.lower() == "features":
                viol.append("[profile].%s is retired -- blade capabilities are a "
                            "closed set; grant one with `mios blade "
                            "add-capability`" % key)
    for rel in KEEP_LISTS:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        for name in RETIRED_NAMES:
            if name in body:
                viol.append("%s still references %s -- the retired [profile] keys "
                            "must not be resurrected by a keep-list" % (rel, name))
    return viol

def check_no_hardcoded_roles(data: dict, root: str) -> list:
    """The blade code must not restate [blade.archetypes]. No literal is
    permitted: the floor is the generated karg, the demotion target is
    [blade].fallback."""
    viol = []
    names = sorted(archetypes(data))
    for rel in BLADE_CODE:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        in_heredoc = None
        for num, line in enumerate(lines, 1):
            # A heredoc body is not shell control flow. The embedded python that
            # READS [blade.archetypes] necessarily names TOML keys -- `endpoint`
            # is both an archetype and a very ordinary config key -- and flagging
            # that would punish the SSOT read this rule exists to require.
            if in_heredoc is not None:
                if line.strip() == in_heredoc:
                    in_heredoc = None
                continue
            opened = re.search(r"<<-?'?([A-Za-z_][A-Za-z0-9_]*)'?", line)
            if opened:
                in_heredoc = opened.group(1)
                continue
            code = line.split("#", 1)[0]
            for name in names:
                # A token after `.` is a member/key access, not a bare role:
                # `[ai].endpoint` names a TOML key that happens to share a name
                # with an archetype. `mios-endpoint.target` is still caught --
                # only `.` is excluded, never `-`.
                if re.search(r"(?<!\.)\b%s\b" % re.escape(name), code):
                    viol.append("%s:%d spells the archetype '%s' as a literal -- "
                                "the archetype table is [blade.archetypes], not "
                                "code (Law 7)" % (rel, num, name))
    return viol

def collect(data: dict, root: str) -> list:
    return (check_type(data)
            + check_targets(data, root)
            + check_capabilities_consumed(data)
            + check_aliases(data)
            + check_conflicts(data, root)
            + check_aliases_in_units(root)
            + check_profile_retired(data, root)
            + check_no_hardcoded_roles(data, root))

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-role-ssot: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = collect(data, root)
    if viol:
        for v in viol:
            print("check_role_ssot: %s" % v, file=sys.stderr)
        return 1

    arche = archetypes(data)
    seats = sorted(n for n, caps in arche.items() if not caps)
    print("[check-role-ssot] %d archetype(s), each with a shipped target and a "
          "complete conflict graph; %d alias(es); seat(s): %s; [blade].type=%s"
          % (len(arche), len(aliases(data)), ", ".join(seats) or "none",
             (data.get("blade") or {}).get("type")))
    return 0

if __name__ == "__main__":
    sys.exit(main())
