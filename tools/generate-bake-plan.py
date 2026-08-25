#!/usr/bin/env python3
import os
import sys
import re
import glob

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
    firstboot_tokens = build_bake.get("firstboot_tokens", [])
    def is_firstboot(img):
        return any(tok and tok in img for tok in firstboot_tokens)

    enabled_map = config.get("quadlets", {}).get("enable", {})
    
    quadlet_dir = os.path.join(ROOT, "usr/share/containers/systemd")
    
    def classify(img):
        for g in groups:
            for tok in group_members.get(g, []):
                if tok and tok in img:
                    return g
        return groups[-1] # extra is catch-all
        
    var_re = re.compile(r"\$\{([A-Za-z0-9_]+):-([^}]*)\}")
    
    sidecars = (config.get("image") or {}).get("sidecars") or {}

    # Quadlets float their image tags from the SSOT (`ceph:${MIOS_VERSION_CEPH}`)
    # rather than hardcoding them, so resolving an Image= line needs the same
    # canonical key map every other consumer uses. Without it a floated tag
    # stays literal, the quadlet is skipped, and its image then reports as
    # "not referenced by any Quadlet" -- an error that names the wrong thing.
    ssot_vars = {}
    if mios_toml is not None:
        try:
            ssot_vars = mios_toml.emit_exports()
        except Exception:
            ssot_vars = {}
    
    def _env(var_name):
        v = os.environ.get(var_name)
        return v if v else None

    def resolve_image_val(val):
        if not val:
            return ""
        def repl_fallback(m):
            var_name = m.group(1)
            fallback = m.group(2)
            env_val = _env(var_name)
            if env_val is not None:
                return env_val
            ssot_val = ssot_vars.get(var_name)
            if ssot_val:
                return ssot_val
            m_s = re.match(r'^MIOS_(.+)_IMAGE$', var_name)
            if m_s:
                sc_val = sidecars.get(m_s.group(1).lower())
                if sc_val:
                    return sc_val
            return fallback
        val = var_re.sub(repl_fallback, val)

        def repl_var(m):
            var_name = m.group(1)
            env_val = _env(var_name)
            if env_val is not None:
                return env_val
            ssot_val = ssot_vars.get(var_name)
            if ssot_val:
                return ssot_val
            m_s = re.match(r'^MIOS_(.+)_IMAGE$', var_name)
            if m_s:
                sc_val = sidecars.get(m_s.group(1).lower())
                if sc_val:
                    return sc_val
            return m.group(0)
        val = re.sub(r'\$\{([A-Za-z0-9_]+)\}', repl_var, val)
        return val.strip()

    images_to_bake = []
    unresolved = []
    
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
        if not resolved_img:
            continue
        if "$" in resolved_img:
            # Dropping this quietly is how a floated tag turned into "core image
            # is not referenced by any Quadlet" three lines of SSOT away from the
            # actual cause. Name the variable that did not resolve instead.
            unresolved.append((os.path.basename(q), img))
            continue
            
        first = resolved_img.split("/", 1)[0]
        if first == "localhost":
            continue
            
        is_core = (resolved_img in core)
        if is_core or enabled_map.get(base_name) is not False:
            images_to_bake.append((resolved_img, base_name))
            
    for core_img in sorted(core):
        if core_img.startswith("localhost/"):
            if not any(img == core_img for img, _ in images_to_bake):
                images_to_bake.append((core_img, "core-localhost"))

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
            
    errors = []
    for quadlet_name, raw in sorted(unresolved):
        errors.append(
            f"Quadlet '{quadlet_name}' has an Image= that does not resolve "
            f"against the SSOT: {raw}")
    for tok in firstboot_tokens:
        if tok and not any(tok in img for img in core):
            errors.append(f"Firstboot token '{tok}' matches no image in core bake list")

    for img in firstboot_images:
        if img not in core:
            errors.append(f"Firstboot image '{img}' is missing from core bake list")

    discovered_non_localhost = {img for img, _ in images_to_bake if not img.startswith("localhost/")}
    core_non_localhost = {img for img in core if not img.startswith("localhost/")}
    missing_from_core = discovered_non_localhost - core_non_localhost
    extra_in_core = core_non_localhost - discovered_non_localhost
    if missing_from_core:
        for img in sorted(missing_from_core):
            errors.append(f"Quadlet image '{img}' is missing from [build.bake].core")
    if extra_in_core:
        for img in sorted(extra_in_core):
            errors.append(f"Core image '{img}' is not referenced by any Quadlet")

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
            
    if not check:
        os.makedirs(out_dir, exist_ok=True)
        for f in glob.glob(os.path.join(out_dir, "*.list")):
            try:
                os.remove(f)
            except OSError:
                pass

        sbom_dir = os.environ.get("MIOS_SBOM_DIR") or os.path.join(ROOT, "usr/share/mios/artifacts/sbom")
        os.makedirs(sbom_dir, exist_ok=True)
        sbom_file = os.path.join(sbom_dir, "bound-images.tsv")

        existing_digests = {}
        existing_sizes = {}
        if os.path.exists(sbom_file):
            try:
                with open(sbom_file, "r", encoding="utf-8") as sfh:
                    for line in sfh:
                        parts = line.strip().split("\t")
                        if len(parts) >= 3 and parts[0] != "image":
                            existing_digests[parts[0]] = parts[1]
                            if len(parts) >= 4:
                                existing_sizes[parts[0]] = parts[3]
            except OSError:
                pass

        seen_images = set()
        with open(sbom_file, "w", encoding="utf-8", newline="\n") as sfh:
            sfh.write("image\tdigest\tgroup\tsize_gb\n")
            for base_img, grp in [("localhost/mios-sys:latest", "sys"), ("localhost/mios-cuda:latest", "cuda")]:
                sz = existing_sizes.get(base_img, "2.5" if grp == "sys" else "4.0")
                sfh.write(f"{base_img}\t{existing_digests.get(base_img, 'local')}\t{grp}\t{sz}\n")
                seen_images.add(base_img)

            for img, base_name in images_to_bake:
                if img not in seen_images:
                    g = classify(img)
                    digest = existing_digests.get(img, "local")
                    sz = existing_sizes.get(img, "1.0")
                    sfh.write(f"{img}\t{digest}\t{g}\t{sz}\n")
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
            
    fb_file = os.path.join(out_dir, "firstboot.list")
    fb_content = "".join(f"{img}\n" for img in firstboot_images)
    if check:
        cur_fb = ""
        if os.path.exists(fb_file):
            with open(fb_file, "r", encoding="utf-8") as fh:
                cur_fb = fh.read()
        if cur_fb != fb_content:
            print(f"[bake-plan-gen] DRIFT: {fb_file} does not match projected plan", file=sys.stderr)
            drift_detected = True
    else:
        with open(fb_file, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(fb_content)
        print(f"[bake-plan-gen] wrote {fb_file}")

    return 1 if drift_detected else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
