#!/usr/bin/env python3
import os
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        # Fallback if no toml library is found
        print("Error: neither tomllib nor tomli is installed.", file=sys.stderr)
        sys.exit(1)

# Define sections to walk recursively
TARGET_SECTIONS = [
    "ports", "ai", "identity", "locale", "auth", "network", "desktop", 
    "branding", "image", "bootstrap", "profile", "colors", "observability", 
    "sandbox", "security", "code_mode", "hermes", "routing", "agents", "a2a"
]

def walk(d, prefix=""):
    results = []
    if not isinstance(d, dict):
        return results
    
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        
        # Skip specific paths we know are not environment config keys
        if path == "routing.domains":
            continue
            
        if isinstance(v, dict):
            results.extend(walk(v, path))
        else:
            # It is a leaf config key
            # Generate canonical env var name:
            # MIOS_ + path upper-snake-cased
            env_name = "MIOS_" + path.upper().replace(".", "_").replace("-", "_")
            results.append((path, env_name))
    return results

def main():
    toml_path = os.environ.get("MIOS_TOML", "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        # Try running from WSL mount point or different directory
        if os.path.isfile("usr/share/mios/mios.toml"):
            toml_path = "usr/share/mios/mios.toml"
        elif os.path.isfile("/mnt/c/MiOS/usr/share/mios/mios.toml"):
            toml_path = "/mnt/c/MiOS/usr/share/mios/mios.toml"
        else:
            print(f"Error: mios.toml not found at {toml_path}", file=sys.stderr)
            return 1
        
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
        
    all_pairs = []
    for sec in TARGET_SECTIONS:
        if sec in data:
            all_pairs.extend(walk(data[sec], sec))
            
    # Sort by path for deterministic output
    all_pairs.sort(key=lambda x: x[0])
    
    # Print one section.key  MIOS_SECTION_KEY per line
    for path, env_name in all_pairs:
        print(f"{path}  {env_name}")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
