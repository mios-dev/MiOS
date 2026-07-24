// AI-hint: Rust SSOT names registry generator (check 30 generator).
use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use regex::Regex;
use walkdir::WalkDir;

const TARGET_SECTIONS: &[&str] = &[
    "ports", "ai", "identity", "locale", "auth", "network", "desktop", 
    "branding", "image", "bootstrap", "profile", "colors", "observability", 
    "sandbox", "security", "code_mode", "hermes", "routing", "agents", "a2a",
    "power", "mini"
];

fn alias_for(path: &str) -> Option<String> {
    match path {
        "ai.vllm.v1_engine" => Some("MIOS_VLLM_USE_V1".to_string()),
        "ai.sglang.unified_radix_tree" => Some("MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE".to_string()),
        "ai.sglang.hierarchical_cache" => Some("MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE".to_string()),
        _ => {
            if let Some(rest) = path.strip_prefix("ai.vllm.") {
                Some(format!("MIOS_VLLM_{}", rest.to_uppercase().replace('.', "_").replace('-', "_")))
            } else if let Some(rest) = path.strip_prefix("ai.sglang.") {
                Some(format!("MIOS_SGLANG_{}", rest.to_uppercase().replace('.', "_").replace('-', "_")))
            } else {
                None
            }
        }
    }
}

fn walk_value(val: &toml::Value, prefix: &str, results: &mut Vec<(String, String)>) {
    if let toml::Value::Table(table) = val {
        for (k, v) in table {
            let path = if prefix.is_empty() { k.clone() } else { format!("{}.{}", prefix, k) };
            if path == "routing.domains" {
                continue;
            }
            if let toml::Value::Table(_) = v {
                walk_value(v, &path, results);
            } else {
                let env_name = if let Some(alias) = alias_for(&path) {
                    alias
                } else {
                    format!("MIOS_{}", path.to_uppercase().replace('.', "_").replace('-', "_"))
                };
                results.push((path, env_name));
            }
        }
    }
}

fn generate_referenced_vars(root: &Path) -> std::io::Result<()> {
    let emitter_suffixes = [
        "usr/lib/mios/userenv.sh",
        "tools/lib/userenv.sh",
        "usr/libexec/mios/system-sync-env.sh",
        "usr/share/mios/names.generated.txt",
        "usr/share/doc/mios/reference/naming-unification.md",
    ];

    let var_re = Regex::new(r"MIOS_[A-Z0-9_]+").unwrap();
    let assign_re = Regex::new(r"^\s*(export\s+)?MIOS_[A-Z0-9_]+=").unwrap();
    let mut refs = BTreeSet::new();

    for entry in WalkDir::new(root).into_iter().filter_map(|e| e.ok()) {
        let path = entry.path();
        if !path.is_file() {
            continue;
        }

        let rel_path = match path.strip_prefix(root) {
            Ok(p) => p.to_string_lossy().replace('\\', "/"),
            Err(_) => continue,
        };

        // Skip ignored directories
        let parts: Vec<&str> = rel_path.split('/').collect();
        if parts.iter().any(|p| matches!(*p, "tmp" | ".git" | ".venv" | "__pycache__" | "node_modules" | "dist" | "build" | ".system_generated" | "scratch" | "logs" | "bib-configs" | "medicat_stage" | "isobuild" | "isobuild_live" | "isobuild2")) {
            continue;
        }

        if emitter_suffixes.iter().any(|s| rel_path.ends_with(s)) {
            continue;
        }

        let filename = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
        let matches_glob = filename.ends_with(".container")
            || filename.ends_with(".service")
            || filename.ends_with(".timer")
            || filename.ends_with(".py")
            || filename.ends_with(".sh")
            || filename.ends_with(".toml")
            || filename.ends_with(".ps1")
            || filename.ends_with(".psm1")
            || filename.ends_with(".yaml")
            || filename.ends_with(".yml")
            || filename == "Justfile"
            || filename == ".env.mios"
            || filename.ends_with(".tmpl")
            || filename.starts_with("Containerfile")
            || filename.ends_with(".nft")
            || filename.ends_with(".sql");

        if !matches_glob {
            continue;
        }

        if let Ok(content) = fs::read_to_string(path) {
            for line in content.lines() {
                if assign_re.is_match(line) {
                    continue;
                }
                for cap in var_re.find_iter(line) {
                    refs.insert(cap.as_str().to_string());
                }
            }
        }
    }

    let ref_file = root.join("usr/share/mios/referenced_names.txt");
    if let Some(parent) = ref_file.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut out = String::new();
    for r in refs {
        out.push_str(&r);
        out.push('\n');
    }
    fs::write(ref_file, out)?;
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root_str = std::env::var("MIOS_DRIFT_ROOT")
        .unwrap_or_else(|_| std::env::current_dir().unwrap().to_string_lossy().to_string());
    let root = PathBuf::from(&root_str);

    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.exists() {
        eprintln!("Error: mios.toml not found at {}", toml_path.display());
        std::process::exit(1);
    }

    let content = fs::read_to_string(&toml_path)?;
    let data: toml::Value = toml::from_str(&content)?;

    let mut all_pairs = Vec::new();
    if let toml::Value::Table(ref root_table) = data {
        for sec in TARGET_SECTIONS {
            if let Some(sec_val) = root_table.get(*sec) {
                walk_value(sec_val, sec, &mut all_pairs);
            }
        }
    }

    let names_file = root.join("usr/share/mios/names.generated.txt");
    if let Some(parent) = names_file.parent() {
        fs::create_dir_all(parent)?;
    }

    let mut names_content = String::new();
    for (path, env_name) in &all_pairs {
        names_content.push_str(&format!("{}  {}\n", path, env_name));
        println!("{}  {}", path, env_name);
    }
    fs::write(names_file, names_content)?;

    generate_referenced_vars(&root)?;
    Ok(())
}
