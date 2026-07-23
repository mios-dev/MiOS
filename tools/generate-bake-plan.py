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
    # firstboot tier (SSOT [build.bake].firstboot_tokens): images whose rendered
    # ref substring-matches any token are NOT baked -- excluded from every group
    # list -> they go to plan.d/firstboot.list and are pulled at first boot.
    firstboot_tokens = build_bake.get("firstboot_tokens", [])
    def is_firstboot(img):
        return any(tok and tok in img for tok in firstboot_tokens)

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
            
    # Group the images. Firstboot-tier images are NOT baked -> excluded from every
    # group list (they stay in images_to_bake for the SBOM); collect them for
    # plan.d/firstboot.list so mios-ai-firstboot / the USB stager can pull them.
    group_lists = {g: [] for g in groups}
    firstboot_images = []
    for img, base_name in images_to_bake:
        if is_firstboot(img):
            if img not in firstboot_images:
                firstboot_images.append(img)
            continue
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
        if img.startswith("systemd-"):
            continue
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

        # Generate SSOT-compliant bound-images.tsv SBOM artifact
        sbom_dir = os.environ.get("MIOS_SBOM_DIR") or os.path.join(ROOT, "usr/share/mios/artifacts/sbom")
        os.makedirs(sbom_dir, exist_ok=True)
        sbom_file = os.path.join(sbom_dir, "bound-images.tsv")

        existing_digests = {}
        if os.path.exists(sbom_file):
            try:
                with open(sbom_file, "r", encoding="utf-8") as sfh:
                    for line in sfh:
                        parts = line.strip().split("\t")
                        if len(parts) >= 3 and parts[0] != "image":
                            existing_digests[parts[0]] = parts[1]
            except OSError:
                pass

        seen_images = set()
        with open(sbom_file, "w", encoding="utf-8", newline="\n") as sfh:
            sfh.write("image\tdigest\tgroup\n")
            for base_img, grp in [("localhost/mios-sys:latest", "sys"), ("localhost/mios-cuda:latest", "cuda")]:
                sfh.write(f"{base_img}\t{existing_digests.get(base_img, 'local')}\t{grp}\n")
                seen_images.add(base_img)

            for img, base_name in images_to_bake:
                if img not in seen_images:
                    g = classify(img)
                    digest = existing_digests.get(img, "local")
                    sfh.write(f"{img}\t{digest}\t{g}\n")
                    seen_images.add(img)

        print(f"[bake-plan-gen] wrote {sbom_file}")
            
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
            
    # firstboot tier: emit the not-baked images for mios-ai-firstboot / the USB
    # data-partition stager. Written only in write mode and OUTSIDE the group
    # lists, so drift-check 35 (which compares only the group lists) is unaffected.
    if not check:
        fb_file = os.path.join(out_dir, "firstboot.list")
        with open(fb_file, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(f"{img}\n" for img in firstboot_images))
        print(f"[bake-plan-gen] wrote {fb_file}")

    return 1 if drift_detected else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
