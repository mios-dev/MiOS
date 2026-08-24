#!/usr/bin/env python3
# AI-hint: Fails when an AI header uses a comment syntax the file's own format does not understand.
# AI-related: usr/lib/wsl.conf, automation/98-drift-checks.sh
import os
import re
import subprocess
import sys

# Formats whose comment character is #. A C-style header in one of these is not
# a comment at all: systemd rejects the line, and an INI parser may too. One
# such line in usr/lib/wsl.conf drifted from its /etc twin and failed a build
# twenty-nine minutes in.
HASH_COMMENT = (".conf", ".service", ".socket", ".timer", ".target", ".mount",
                ".path", ".network", ".container", ".pod", ".volume", ".toml",
                ".ini", ".cfg", ".repo", ".preset", ".sh", ".py", ".yml",
                ".yaml", ".nft", ".rules")
BAD = re.compile(r"^/\*\s*AI-(?:doc|hint|related):", re.M)


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    out = subprocess.run(["git", "-C", root, "ls-files"],
                         capture_output=True, text=True, check=False).stdout
    viol = []
    for rel in sorted(p.strip().replace(os.sep, "/") for p in out.splitlines() if p.strip()):
        if os.path.splitext(rel)[1] not in HASH_COMMENT:
            continue
        full = os.path.join(root, rel)
        try:
            s = open(full, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if BAD.search(s):
            viol.append("%s carries a C-style AI header, but this format comments"
                        " with #" % rel)
    print("\n".join(viol[:20]))
    if viol:
        if len(viol) > 20:
            print("... and %d more" % (len(viol) - 20))
        return 1
    print("[check-header-comment-syntax] every AI header uses its format's comment"
          " character", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
