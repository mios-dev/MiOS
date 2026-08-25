// AI-hint: Rust bake-plan generator (AGY-139 / Law 14). Projects plan.d/*.list and bound-images.tsv from mios.toml SSOT.
use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;
use toml::Value;

fn get_root() -> PathBuf {
    if let Ok(r) = env::var("MIOS_ROOT") {
        return PathBuf::from(r);
    }
    let current_exe = env::current_exe().unwrap_or_default();
    let mut p = current_exe.as_path();
    while let Some(parent) = p.parent() {
        if parent.join("usr/share/mios/mios.toml").is_file() {
            return parent.to_path_buf();
        }
        p = parent;
    }
    PathBuf::from(".")
}

fn resolve_image_val(val: &str, sidecars: &BTreeMap<String, String>) -> String {
    if val.is_empty() {
        return String::new();
    }
    let var_fallback_re = Regex::new(r"\$\{([A-Za-z0-9_]+):-([^}]*)\}").unwrap();
    let var_simple_re = Regex::new(r"\$\{([A-Za-z0-9_]+)\}").unwrap();

    let s1 = var_fallback_re.replace_all(val, |caps: &regex::Captures| {
        let var_name = &caps[1];
        let fallback = &caps[2];
        if let Ok(v) = env::var(var_name) {
            return v;
        }
        if var_name.starts_with("MIOS_") && var_name.ends_with("_IMAGE") {
            let key = var_name[5..var_name.len() - 6].to_lowercase();
            if let Some(sc) = sidecars.get(&key) {
                return sc.clone();
            }
        }
        fallback.to_string()
    });

    let s2 = var_simple_re.replace_all(&s1, |caps: &regex::Captures| {
        let var_name = &caps[1];
        if let Ok(v) = env::var(var_name) {
            return v;
        }
        if var_name.starts_with("MIOS_") && var_name.ends_with("_IMAGE") {
            let key = var_name[5..var_name.len() - 6].to_lowercase();
            if let Some(sc) = sidecars.get(&key) {
                return sc.clone();
            }
        }
        caps[0].to_string()
    });

    s2.trim().to_string()
}

fn classify(img: &str, groups: &[String], group_members: &BTreeMap<String, Vec<String>>) -> String {
    for g in groups {
        if let Some(members) = group_members.get(g) {
            for tok in members {
                if !tok.is_empty() && img.contains(tok) {
                    return g.clone();
                }
            }
        }
    }
    groups
        .last()
        .cloned()
        .unwrap_or_else(|| "extra".to_string())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let check = args.iter().any(|a| a == "--check");

    let root = get_root();
    let toml_path = env::var("MIOS_TOML")
        .map(PathBuf::from)
        .unwrap_or_else(|_| root.join("usr/share/mios/mios.toml"));
    let out_dir = env::var("MIOS_PLAN_OUT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| root.join("usr/lib/mios/bake/plan.d"));

    let content = match fs::read_to_string(&toml_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!(
                "[bake-plan-gen] ERROR: cannot read {}: {}",
                toml_path.display(),
                e
            );
            process::exit(1);
        }
    };

    let parsed: Value = match content.parse() {
        Ok(v) => v,
        Err(e) => {
            eprintln!(
                "[bake-plan-gen] ERROR: cannot parse {}: {}",
                toml_path.display(),
                e
            );
            process::exit(1);
        }
    };

    let build_bake = parsed.get("build").and_then(|b| b.get("bake"));
    let core: BTreeSet<String> = build_bake
        .and_then(|b| b.get("core"))
        .and_then(|c| c.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();

    let groups: Vec<String> = build_bake
        .and_then(|b| b.get("groups"))
        .and_then(|g| g.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_else(|| {
            vec![
                "vllm".to_string(),
                "sglang".to_string(),
                "ai".to_string(),
                "infra".to_string(),
                "extra".to_string(),
            ]
        });

    let mut group_members: BTreeMap<String, Vec<String>> = BTreeMap::new();
    if let Some(gm) = build_bake
        .and_then(|b| b.get("group_members"))
        .and_then(|m| m.as_table())
    {
        for (k, v) in gm {
            if let Some(arr) = v.as_array() {
                let members: Vec<String> = arr
                    .iter()
                    .filter_map(|s| s.as_str().map(String::from))
                    .collect();
                group_members.insert(k.clone(), members);
            }
        }
    }

    let firstboot_tokens: Vec<String> = build_bake
        .and_then(|b| b.get("firstboot_tokens"))
        .and_then(|t| t.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default();

    let is_firstboot = |img: &str| -> bool {
        firstboot_tokens
            .iter()
            .any(|tok| !tok.is_empty() && img.contains(tok))
    };

    let mut enabled_map: BTreeMap<String, bool> = BTreeMap::new();
    if let Some(q) = parsed
        .get("quadlets")
        .and_then(|q| q.get("enable"))
        .and_then(|e| e.as_table())
    {
        for (k, v) in q {
            if let Some(b) = v.as_bool() {
                enabled_map.insert(k.clone(), b);
            }
        }
    }

    let mut sidecars: BTreeMap<String, String> = BTreeMap::new();
    if let Some(sc) = parsed
        .get("image")
        .and_then(|i| i.get("sidecars"))
        .and_then(|s| s.as_table())
    {
        for (k, v) in sc {
            if let Some(s) = v.as_str() {
                sidecars.insert(k.to_lowercase(), s.to_string());
            }
        }
    }

    let quadlet_dir = root.join("usr/share/containers/systemd");
    let mut images_to_bake: Vec<(String, String)> = Vec::new();

    if quadlet_dir.is_dir() {
        if let Ok(entries) = fs::read_dir(&quadlet_dir) {
            let mut paths: Vec<PathBuf> = entries
                .filter_map(|e| e.ok().map(|entry| entry.path()))
                .filter(|p| {
                    p.extension()
                        .is_some_and(|ext| ext == "container" || ext == "image")
                })
                .collect();
            paths.sort();

            for path in paths {
                let base_name = path
                    .file_stem()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                let mut img = String::new();
                if let Ok(fc) = fs::read_to_string(&path) {
                    for line in fc.lines() {
                        let trimmed = line.trim();
                        if let Some(stripped) = trimmed.strip_prefix("Image=") {
                            img = stripped.trim().to_string();
                            break;
                        }
                    }
                }
                if img.is_empty() {
                    continue;
                }
                let resolved = resolve_image_val(&img, &sidecars);
                if resolved.is_empty() || resolved.contains('$') {
                    continue;
                }
                let first = resolved.split('/').next().unwrap_or("");
                if first == "localhost" {
                    continue;
                }
                let is_core = core.contains(&resolved);
                if is_core || enabled_map.get(&base_name) != Some(&false) {
                    images_to_bake.push((resolved, base_name));
                }
            }
        }
    }

    let mut group_lists: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for g in &groups {
        group_lists.insert(g.clone(), Vec::new());
    }

    let mut firstboot_images: Vec<String> = Vec::new();
    for (img, _base_name) in &images_to_bake {
        if is_firstboot(img) {
            if !firstboot_images.contains(img) {
                firstboot_images.push(img.clone());
            }
            continue;
        }
        let g = classify(img, &groups, &group_members);
        if let Some(list) = group_lists.get_mut(&g) {
            if !list.contains(img) {
                list.push(img.clone());
            }
        }
    }

    let mut errors: Vec<String> = Vec::new();
    for tok in &firstboot_tokens {
        if !tok.is_empty() && !core.iter().any(|img| img.contains(tok)) {
            errors.push(format!(
                "Firstboot token '{}' matches no image in core bake list",
                tok
            ));
        }
    }
    for img in &firstboot_images {
        if !core.contains(img) {
            errors.push(format!(
                "Firstboot image '{}' is missing from core bake list",
                img
            ));
        }
    }

    let discovered_non_localhost: BTreeSet<String> = images_to_bake
        .iter()
        .filter(|(img, _)| !img.starts_with("localhost/"))
        .map(|(img, _)| img.clone())
        .collect();
    let core_non_localhost: BTreeSet<String> = core
        .iter()
        .filter(|img| !img.starts_with("localhost/"))
        .cloned()
        .collect();

    for img in discovered_non_localhost.difference(&core_non_localhost) {
        errors.push(format!(
            "Quadlet image '{}' is missing from [build.bake].core",
            img
        ));
    }
    for img in core_non_localhost.difference(&discovered_non_localhost) {
        errors.push(format!(
            "Core image '{}' is not referenced by any Quadlet",
            img
        ));
    }

    for img in &core {
        let first = img.split('/').next().unwrap_or("");
        if !(first.contains('.') || first.contains(':') || first == "localhost") {
            errors.push(format!(
                "Core image '{}' is not fully-qualified (missing registry prefix)",
                img
            ));
        }
    }

    for (img, base_name) in &images_to_bake {
        if img.starts_with("systemd-") {
            continue;
        }
        let first = img.split('/').next().unwrap_or("");
        if !(first.contains('.') || first.contains(':') || first == "localhost") {
            errors.push(format!(
                "Referenced image '{}' in {} is not fully-qualified",
                img, base_name
            ));
        }
    }

    if !errors.is_empty() {
        for err in &errors {
            eprintln!("[bake-plan-gen] VALIDATION ERROR: {}", err);
        }
        process::exit(2);
    }

    if !check {
        let _ = fs::create_dir_all(&out_dir);
        if let Ok(entries) = fs::read_dir(&out_dir) {
            for entry in entries.flatten() {
                if entry.path().extension().is_some_and(|e| e == "list") {
                    let _ = fs::remove_file(entry.path());
                }
            }
        }

        let sbom_dir = env::var("MIOS_SBOM_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| root.join("usr/share/mios/artifacts/sbom"));
        let _ = fs::create_dir_all(&sbom_dir);
        let sbom_file = sbom_dir.join("bound-images.tsv");

        let mut existing_digests: BTreeMap<String, String> = BTreeMap::new();
        if sbom_file.is_file() {
            if let Ok(c) = fs::read_to_string(&sbom_file) {
                for line in c.lines() {
                    let parts: Vec<&str> = line.trim().split('\t').collect();
                    if parts.len() >= 3 && parts[0] != "image" {
                        existing_digests.insert(parts[0].to_string(), parts[1].to_string());
                    }
                }
            }
        }

        let mut seen_images: BTreeSet<String> = BTreeSet::new();
        let mut sbom_content = String::from("image\tdigest\tgroup\n");
        for (base_img, grp) in [
            ("localhost/mios-sys:latest", "sys"),
            ("localhost/mios-cuda:latest", "cuda"),
        ] {
            let digest = existing_digests
                .get(base_img)
                .cloned()
                .unwrap_or_else(|| "local".to_string());
            sbom_content.push_str(&format!("{}\t{}\t{}\n", base_img, digest, grp));
            seen_images.insert(base_img.to_string());
        }

        for (img, _base_name) in &images_to_bake {
            if !seen_images.contains(img) {
                let g = classify(img, &groups, &group_members);
                let digest = existing_digests
                    .get(img)
                    .cloned()
                    .unwrap_or_else(|| "local".to_string());
                sbom_content.push_str(&format!("{}\t{}\t{}\n", img, digest, g));
                seen_images.insert(img.clone());
            }
        }

        let _ = fs::write(&sbom_file, sbom_content);
        println!("[bake-plan-gen] wrote {}", sbom_file.display());
    }

    let mut drift_detected = false;

    for (idx, g) in groups.iter().enumerate() {
        let prefix = format!("{:02}", idx + 1);
        let plan_file = out_dir.join(format!("{}-{}.list", prefix, g));
        let list = group_lists.get(g).cloned().unwrap_or_default();
        let mut content = String::new();
        for img in &list {
            content.push_str(img);
            content.push('\n');
        }

        if check {
            let cur = fs::read_to_string(&plan_file).unwrap_or_default();
            if cur != content {
                eprintln!(
                    "[bake-plan-gen] DRIFT: {} does not match projected plan",
                    plan_file.display()
                );
                drift_detected = true;
            }
        } else {
            let _ = fs::write(&plan_file, &content);
            println!("[bake-plan-gen] wrote {}", plan_file.display());
        }
    }

    let fb_file = out_dir.join("firstboot.list");
    let mut fb_content = String::new();
    for img in &firstboot_images {
        fb_content.push_str(img);
        fb_content.push('\n');
    }

    if check {
        let cur_fb = fs::read_to_string(&fb_file).unwrap_or_default();
        if cur_fb != fb_content {
            eprintln!(
                "[bake-plan-gen] DRIFT: {} does not match projected plan",
                fb_file.display()
            );
            drift_detected = true;
        }
    } else {
        let _ = fs::write(&fb_file, &fb_content);
        println!("[bake-plan-gen] wrote {}", fb_file.display());
    }

    if drift_detected {
        process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_image_val() {
        let sidecars = BTreeMap::new();
        assert_eq!(
            resolve_image_val("ghcr.io/org/app:latest", &sidecars),
            "ghcr.io/org/app:latest"
        );
        assert_eq!(
            resolve_image_val("${MIOS_CUSTOM_IMAGE:-docker.io/library/redis:alpine}", &sidecars),
            "docker.io/library/redis:alpine"
        );
    }

    #[test]
    fn test_classify() {
        let groups = vec![
            "vllm".to_string(),
            "sglang".to_string(),
            "extra".to_string(),
        ];
        let mut members = BTreeMap::new();
        members.insert("vllm".to_string(), vec!["vllm".to_string()]);
        members.insert("sglang".to_string(), vec!["sglang".to_string()]);

        assert_eq!(classify("quay.io/vllm/vllm:v0.6.0", &groups, &members), "vllm");
        assert_eq!(classify("docker.io/sglang:latest", &groups, &members), "sglang");
        assert_eq!(classify("docker.io/other:1.0", &groups, &members), "extra");
    }
}

