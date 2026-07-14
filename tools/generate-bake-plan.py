#!/usr/bin/env python3
# tools/generate-bake-plan.py
import os
import sys
import re
import glob

# Ensure we can load mios_toml
ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "usr/lib/mios"))
try:
    import mios_toml
except ImportError:
    mios_toml = None

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

def main(argv):
    toml_path = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")
    out_dir = os.environ.get("MIOS_PLAN_OUT") or os.path.join(ROOT, "usr/lib/mios/bake/plan.d")
    
    check = "--check" in argv
    
    with open(toml_path, "rb") as fh:
        config = tomllib.load(fh)
        
    build_bake = config.get("build", {}).get("bake", {})
    core = set(build_bake.get("core", []))
    groups = build_bake.get("groups", ["vllm", "sglang", "ai", "infra", "extra"])
    group_members = build_bake.get("group_members", {})
    
    enabled_map = config.get("quadlets", {}).get("enable", {})
    
    # We will scan both *.container and *.image files from usr/share/containers/systemd/
    quadlet_dir = os.path.join(ROOT, "usr/share/containers/systemd")
    
    def classify(img):
        for g in groups:
            for tok in group_members.get(g, []):
                if tok and tok in img:
                    return g
        return groups[-1] # extra is catch-all
        
    var_re = re.compile(r"\$\{([A-Za-z0-9_]+):-([^}]*)\}")
    
    # Load all sidecars to resolve variable substitutions
    sidecars = (config.get("image") or {}).get("sidecars") or {}
    
    def resolve_image_val(val):
        if not val:
            return ""
        # Resolve ${VAR:-fallback}
        def repl_fallback(m):
            var_name = m.group(1)
            fallback = m.group(2)
            if var_name in os.environ:
                return os.environ[var_name]
            m_s = re.match(r'^MIOS_(.+)_IMAGE$', var_name)
            if m_s:
                sc_val = sidecars.get(m_s.group(1).lower())
                if sc_val:
                    return sc_val
            return fallback
        val = var_re.sub(repl_fallback, val)
        
        # Resolve ${VAR}
        def repl_var(m):
            var_name = m.group(1)
            if var_name in os.environ:
                return os.environ[var_name]
            m_s = re.match(r'^MIOS_(.+)_IMAGE$', var_name)
            if m_s:
                sc_val = sidecars.get(m_s.group(1).lower())
                if sc_val:
                    return sc_val
            return m.group(0)
        val = re.sub(r'\$\{([A-Za-z0-9_]+)\}', repl_var, val)
        return val.strip()

    images_to_bake = []
    
    # Scan all Quadlet files
    for q in sorted(glob.glob(os.path.join(quadlet_dir, "*.container")) +
                    glob.glob(os.path.join(quadlet_dir, "*.image"))):
        base_name = os.path.splitext(os.path.basename(q))[0]
        ext = os.path.splitext(q)[1]
        
        if ext == ".container" and enabled_map.get(base_name) is False:
            continue
            
        img = None
        try:
            with open(q, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    s = line.strip()
                    if s.startswith("Image="):
                        img = s[len("Image="):].strip()
                        break
        except OSError:
            continue
            
        if not img:
            continue
            
        resolved_img = resolve_image_val(img)
        if not resolved_img or "$" in resolved_img:
            continue
            
        first = resolved_img.split("/", 1)[0]
        if first == "localhost":
            continue
            
        is_core = (resolved_img in core)
        if is_core or enabled_map.get(base_name) is not False:
            images_to_bake.append((resolved_img, base_name))
            
    # Group the images
    group_lists = {g: [] for g in groups}
    for img, base_name in images_to_bake:
        g = classify(img)
        if img not in group_lists[g]:
            group_lists[g].append(img)
            
    # Assertions / Validation
    errors = []
    vllm_whale = "docker.io/vllm/vllm-openai:latest"
    sglang_whale = "docker.io/lmsysorg/sglang:latest"
    if vllm_whale not in core:
        errors.append(f"Whale {vllm_whale} is missing from core bake list")
    if sglang_whale not in core:
        errors.append(f"Whale {sglang_whale} is missing from core bake list")
        
    for img in core:
        parts = img.split("/", 1)
        first = parts[0]
        if not ("." in first or ":" in first or first == "localhost"):
            errors.append(f"Core image '{img}' is not fully-qualified (missing registry prefix)")
            
    for img, base_name in images_to_bake:
        parts = img.split("/", 1)
        first = parts[0]
        if not ("." in first or ":" in first or first == "localhost"):
            errors.append(f"Referenced image '{img}' in {base_name} is not fully-qualified")

    if errors:
        for err in errors:
            print(f"[bake-plan-gen] VALIDATION ERROR: {err}", file=sys.stderr)
        return 2
            
    # Generate list files
    if not check:
        os.makedirs(out_dir, exist_ok=True)
        for f in glob.glob(os.path.join(out_dir, "*.list")):
            try:
                os.remove(f)
            except OSError:
                pass
                
    drift_detected = False
    
    for idx, g in enumerate(groups):
        prefix = f"{idx+1:02d}"
        plan_file = os.path.join(out_dir, f"{prefix}-{g}.list")
        content = "".join(f"{img}\n" for img in group_lists[g])
        
        if check:
            cur = ""
            if os.path.exists(plan_file):
                with open(plan_file, "r", encoding="utf-8") as fh:
                    cur = fh.read()
            if cur != content:
                print(f"[bake-plan-gen] DRIFT: {plan_file} does not match projected plan", file=sys.stderr)
                drift_detected = True
        else:
            with open(plan_file, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
            print(f"[bake-plan-gen] wrote {plan_file}")
            
    return 1 if drift_detected else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
