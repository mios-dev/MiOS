#!/usr/bin/env python3
# AI-hint: Renders etc/mios/ipa-enroll.env from usr/share/mios/mios.toml [identity.ipa] SSOT (AGY-162)
import os, sys

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
    target_path = os.path.join(root, "etc/mios/ipa-enroll.env")
    check_mode = "--check" in sys.argv

    if not os.path.isfile(ssot_path):
        print(f"Error: SSOT file not found at {ssot_path}", file=sys.stderr)
        sys.exit(1)

    if not tomllib:
        print("Error: tomllib unavailable", file=sys.stderr)
        sys.exit(1)

    with open(ssot_path, "rb") as f:
        data = tomllib.load(f)

    ipa = data.get("identity", {}).get("ipa", {})
    enabled = "true" if ipa.get("enabled", False) else "false"
    realm = ipa.get("realm", "MIOS.INTERNAL")
    server = ipa.get("server", "ipa.mios.internal")
    domain = ipa.get("domain", "mios.internal")
    principal = ipa.get("enroll_principal", "admin")
    otp = ipa.get("otp", "placeholder-one-time-password")

    rendered = f"""# FreeIPA Zero-Touch Enrollment Config
# Generated from mios.toml [identity.ipa] -- DO NOT EDIT DIRECTLY
MIOS_IPA_ENABLED="{enabled}"
MIOS_IPA_REALM="{realm}"
MIOS_IPA_SERVER="{server}"
MIOS_IPA_DOMAIN="{domain}"
MIOS_IPA_ENROLL_PRINCIPAL="{principal}"
MIOS_IPA_OTP="{otp}"
"""

    if check_mode:
        if not os.path.isfile(target_path):
            print(f"Error: {target_path} does not exist", file=sys.stderr)
            sys.exit(1)
        with open(target_path, "r", encoding="utf-8") as f:
            current = f.read()
        if current.strip() != rendered.strip():
            print(f"Error: {target_path} is out of sync with [identity.ipa] SSOT", file=sys.stderr)
            sys.exit(1)
        print("[OK] ipa-enroll.env is in sync with SSOT")
        sys.exit(0)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"Generated {target_path}")

if __name__ == "__main__":
    main()
