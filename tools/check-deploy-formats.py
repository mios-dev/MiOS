#!/usr/bin/env python3
# AI-hint: Fails when a declared deployment format has no build target, when a build target is undeclared, or when a variant ships a format the matrix does not define.
# AI-related: usr/share/mios/mios.toml, Justfile, config/artifacts/
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

STATUSES = ("shipping", "partial", "design")
# "artifacts" is the glob list the verifier requires a match for. A format
# without one is a format the publish gate cannot notice the absence of, which
# is how an empty build tree came to satisfy it; only the registry format,
# which writes no file, is allowed an empty list.
REQUIRED = ("title", "summary", "target", "recipe", "medium", "gui", "status",
            "artifacts")
# Targets in the Justfile that orchestrate or post-process rather than produce a
# deployable artifact. Listed so that a NEW artifact target cannot hide here.
NOT_A_FORMAT = frozenset({
    "build", "build-logged", "build-verbose", "all", "publish", "rechunk",
    "rechunk-conv", "artifact", "sbom", "verify-images", "cloud-build",
    "embed-log", "log-bootstrap", "build-and-log", "all-bootstrap",
})


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ssot = tomllib.load(fh)

    viol = []
    deploy = ssot.get("deploy") or {}
    formats = {k: v for k, v in (deploy.get("formats") or {}).items()
               if isinstance(v, dict)}
    if not formats:
        print("[deploy.formats] is empty -- a matrix with no entries supports"
              " nothing and passes every check it has")
        return 1

    just = ""
    jpath = os.path.join(root, "Justfile")
    if os.path.isfile(jpath):
        just = open(jpath, encoding="utf-8", errors="replace").read()
    else:
        viol.append("Justfile is missing -- no format can be built")
    targets = set(re.findall(r"^([a-z0-9][a-z0-9_-]*):", just, re.M))

    claimed_recipes = set()
    for name, spec in sorted(formats.items()):
        where = "[deploy.formats.%s]" % name
        for field in REQUIRED:
            if field not in spec:
                viol.append("%s is missing %s" % (where, field))
        if not spec.get("artifacts") and spec.get("medium") != "container registry":
            viol.append("%s declares no artifacts globs, so a build that produces"
                        " no %s file passes verify-images unnoticed"
                        % (where, name))
        if spec.get("status") not in STATUSES:
            viol.append("%s status %r is not one of %s"
                        % (where, spec.get("status"), list(STATUSES)))
        target = spec.get("target")
        if target and target not in targets:
            viol.append("%s names target %r, which the Justfile does not define"
                        % (where, target))
        recipe = spec.get("recipe")
        if recipe:
            claimed_recipes.add(os.path.basename(recipe))
            if not os.path.isfile(os.path.join(root, recipe)):
                viol.append("%s recipe %s does not exist" % (where, recipe))

    shared = (deploy.get("formats") or {}).get("shared_recipe")
    if shared:
        claimed_recipes.add(os.path.basename(shared))
        if not os.path.isfile(os.path.join(root, shared)):
            viol.append("[deploy.formats].shared_recipe %s does not exist" % shared)

    art_dir = os.path.join(root, "config/artifacts")
    if os.path.isdir(art_dir):
        for fn in sorted(os.listdir(art_dir)):
            if fn.endswith(".toml") and fn not in claimed_recipes:
                viol.append("config/artifacts/%s is claimed by no format -- a"
                            " recipe nothing builds from is configuration for"
                            " nothing" % fn)

    # A target that produces an artifact and is not declared is an unsupported
    # format shipping anyway, which is the half of the matrix nobody maintains.
    declared_targets = {s.get("target") for s in formats.values()}
    for t in sorted(targets):
        if t in NOT_A_FORMAT or t in declared_targets:
            continue
        body = re.search(r"^%s:.*?(?=^[a-z0-9][a-z0-9_-]*:|\Z)" % re.escape(t),
                         just, re.M | re.S)
        # Creating the output directory is what a producing target does; a
        # status target merely reads the same paths, and matching a mention
        # rather than a write reported flight-status as an undeclared format.
        if body and re.search(r"mkdir\s+-p\s+build/", body.group(0)):
            viol.append("Justfile target %r writes a deployable artifact and is"
                        " in no [deploy.formats] entry" % t)

    for vname, vspec in sorted((ssot.get("variants") or {}).get("entries", {}).items()):
        for art in vspec.get("artifacts") or []:
            if art not in formats:
                viol.append("[variants.entries.%s] ships %r, which [deploy.formats]"
                            " does not define" % (vname, art))

    print("\n".join(viol))
    if viol:
        return 1
    shipping = sum(1 for s in formats.values() if s.get("status") == "shipping")
    print("[check-deploy-formats] %d format(s), %d shipping; every target and"
          " recipe resolves" % (len(formats), shipping), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
