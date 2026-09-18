#!/usr/bin/env python3
# AI-hint: Renders usr/lib/containers/policy.json from usr/share/mios/mios.toml [security.sigstore] SSOT
import os, sys, json, tomllib


def _die(msg):
    # Every exit that is not a rendered policy is an error. This used to wrap
    # the SSOT read in `except Exception: pass` and carry on with
    # policy_mode = "insecureAcceptEverything" -- the value that accepts any
    # signature -- under a header claiming SSOT provenance.
    print(f"Error: generate-cosign-policy: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ssot_path = os.path.join(root, "usr/share/mios/mios.toml")
    target_path = os.path.join(root, "usr/lib/containers/policy.json")
    check_mode = "--check" in sys.argv

    if not os.path.isfile(ssot_path):
        _die(f"{ssot_path} not found")
    try:
        with open(ssot_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as e:
        _die(f"{ssot_path} could not be read: {e}")

    sigstore = data.get("security", {}).get("sigstore")
    if not isinstance(sigstore, dict):
        _die("mios.toml declares no [security.sigstore] table")
    policy_mode = sigstore.get("policy_mode")
    if not isinstance(policy_mode, str) or not policy_mode:
        _die("[security.sigstore].policy_mode is absent or not a string")

    rendered = json.dumps({"default": [{"type": policy_mode}]}, indent=2) + "\n"

    if check_mode:
        # BYTES, not parsed JSON. The parsed comparison this replaces called the
        # compact tracked file "in sync" with an indented render, so a bake that
        # ran the generator would rewrite a file every check reported current.
        # Law 8 asks for regenerate-and-diff; semantic equality is weaker.
        if not os.path.isfile(target_path):
            _die(f"{target_path} does not exist")
        with open(target_path, "r", encoding="utf-8") as f:
            if f.read() != rendered:
                _die(f"{target_path} is out of sync with [security.sigstore] SSOT"
                     " -- regenerate: python3 tools/generate-cosign-policy.py")
        print("[OK] usr/lib/containers/policy.json is in sync with SSOT")
        sys.exit(0)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Generated {target_path}")


if __name__ == "__main__":
    main()
