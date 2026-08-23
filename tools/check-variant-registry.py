#!/usr/bin/env python3
# AI-hint: Fails when a MiOS variant names a config table, edition, archetype, artifact or document that does not exist, or breaks the naming convention.
# AI-related: usr/share/mios/mios.toml, config/artifacts/
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

STATUSES = ("shipping", "partial", "design")
REQUIRED = ("title", "summary", "target", "config", "archetype", "artifacts",
            "doc", "status")


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ssot = tomllib.load(fh)

    viol = []
    variants = ssot.get("variants") or {}
    entries = variants.get("entries") or {}
    naming = variants.get("naming") or {}
    if not entries:
        print("[variants.entries] is empty -- a registry with no entries passes"
              " every check it has and states nothing")
        return 1

    editions = ssot.get("editions") or {}
    archetypes = ((ssot.get("blade") or {}).get("archetypes") or {})
    recipes = set()
    art_dir = os.path.join(root, "config/artifacts")
    if os.path.isdir(art_dir):
        recipes = {f[:-5] for f in os.listdir(art_dir) if f.endswith(".toml")}
    # raw is produced by the installer path rather than a recipe file.
    recipes |= {"raw"}

    key_re = re.compile(r"^[%s]+$" % naming.get("key_charset", "a-z0-9-"))
    prefix = naming.get("prefix", "MiOS")
    sep = naming.get("separator", "-")
    base = naming.get("base", "mios")

    claimed = set()
    for key, spec in sorted(entries.items()):
        where = "[variants.entries.%s]" % key
        for field in REQUIRED:
            if field not in spec:
                viol.append("%s is missing %s" % (where, field))
        if not key_re.match(key):
            viol.append("%s key breaks %s" % (where, naming.get("key_pattern", "")))

        title = str(spec.get("title", ""))
        if key == base:
            if title != prefix:
                viol.append("%s the base variant is titled %r, expected %r"
                            % (where, title, prefix))
        elif not title.startswith(prefix + sep):
            viol.append("%s title %r does not follow %s"
                        % (where, title, naming.get("title_pattern", "")))
        elif title.lower() != key:
            viol.append("%s title %r and key %r are not the same name in two"
                        " registers" % (where, title, key))

        status = spec.get("status")
        if status not in STATUSES:
            viol.append("%s status %r is not one of %s" % (where, status, list(STATUSES)))

        for table in spec.get("config") or []:
            if table not in ssot:
                viol.append("%s config names [%s], which the SSOT does not define"
                            % (where, table))
        ed = spec.get("edition")
        if ed:
            claimed.add(ed)
            if ed not in editions:
                viol.append("%s edition %r is not in [editions]" % (where, ed))
        arch = spec.get("archetype")
        if arch and arch not in archetypes:
            viol.append("%s archetype %r is not in [blade.archetypes]" % (where, arch))
        for art in spec.get("artifacts") or []:
            if art not in recipes:
                viol.append("%s artifact %r has no recipe in config/artifacts/"
                            % (where, art))
        doc = spec.get("doc")
        if doc and not os.path.isfile(os.path.join(root, doc)):
            viol.append("%s doc %s does not exist" % (where, doc))

    for ed in sorted(editions):
        if ed not in claimed:
            viol.append("[editions.%s] is claimed by no variant -- an edition"
                        " nobody ships is configuration for nothing" % ed)

    ceiling = variants.get("max_design_variants")
    design = [k for k, v in entries.items() if v.get("status") == "design"]
    if ceiling is None:
        viol.append("[variants] has no max_design_variants -- an absent ceiling"
                    " lets a design doc stay the deliverable")
    elif len(design) > int(ceiling):
        viol.append("variants still in design %d > ceiling %d: %s"
                    % (len(design), ceiling, sorted(design)))

    print("\n".join(viol))
    if viol:
        return 1
    print("[check-variant-registry] %d variant(s); %d shipping, %d partial, %d design"
          % (len(entries),
             sum(1 for v in entries.values() if v.get("status") == "shipping"),
             sum(1 for v in entries.values() if v.get("status") == "partial"),
             len(design)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
