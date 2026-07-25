#!/usr/bin/env python3
# AI-hint: Renders usr/lib/containers/policy.json from usr/share/mios/mios.toml [security.sigstore] SSOT (AGY-165)
import os, sys, json

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ssot_path = os.path.join(root, "usr/share/mios/mios.toml")
    target_path = os.path.join(root, "usr/lib/containers/policy.json")
    check_mode = "--check" in sys.argv

    policy_mode = "insecureAcceptEverything"

    if tomllib and os.path.isfile(ssot_path):
        try:
            with open(ssot_path, "rb") as f:
                data = tomllib.load(f)
            sigstore = data.get("security", {}).get("sigstore", {})
            policy_mode = sigstore.get("policy_mode", "insecureAcceptEverything")
        except Exception:
            pass

    policy = {
        "default": [
            {
                "type": policy_mode
            }
        ]
    }

    rendered = json.dumps(policy, indent=2) + "\n"

    if check_mode:
        if not os.path.isfile(target_path):
            print(f"Error: {target_path} does not exist", file=sys.stderr)
            sys.exit(1)
        with open(target_path, "r", encoding="utf-8") as f:
            current = f.read()
        try:
            cur_json = json.loads(current)
            ren_json = json.loads(rendered)
            if cur_json != ren_json:
                print(f"Error: {target_path} is out of sync with [security.sigstore] SSOT", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error comparing json: {e}", file=sys.stderr)
            sys.exit(1)
        print("[OK] usr/lib/containers/policy.json is in sync with SSOT")
        sys.exit(0)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Generated {target_path}")

if __name__ == "__main__":
    main()
