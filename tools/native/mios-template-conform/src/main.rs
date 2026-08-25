// AI-hint: Compiled Rust implementation of template conformance checker.
// AI-related: /usr/libexec/mios/check-template-conformance, /usr/share/mios/mios.toml

use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

struct CompiledTemplate {
    name: String,
    pattern: Regex,
    required_header: bool,
    required_markers: Vec<String>,
    required_ordered: Vec<String>,
}

fn load_grandfathered(root: &Path) -> HashSet<String> {
    let gf_path = root.join("usr/share/mios/templates/conformance-grandfathered.list");
    if let Ok(content) = fs::read_to_string(&gf_path) {
        content
            .lines()
            .map(|l| l.trim().to_string())
            .filter(|l| !l.is_empty() && !l.starts_with('#'))
            .collect()
    } else {
        HashSet::new()
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut root_dir = env::var("MIOS_THEME_ROOT").unwrap_or_else(|_| ".".to_string());
    let mut cli_ceiling: Option<usize> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--root" => {
                if i + 1 < args.len() {
                    root_dir = args[i + 1].clone();
                    i += 1;
                }
            }
            "--max-unconforming" if i + 1 < args.len() => {
                cli_ceiling = args[i + 1].parse().ok();
                i += 1;
            }
            _ => {}
        }
        i += 1;
    }

    let root_path = PathBuf::from(&root_dir);
    let config_path = root_path.join("usr/share/mios/mios.toml");

    let mut templates_map: HashMap<String, serde_json::Value> = HashMap::new();
    let mut default_ceiling: usize = 0;

    if let Ok(content) = fs::read_to_string(&config_path) {
        if let Ok(val) = toml::from_str::<toml::Value>(&content) {
            if let Some(ai_tag) = val.get("ai_tag") {
                if let Some(max_u) = ai_tag.get("max_unconforming").and_then(|v| v.as_integer()) {
                    default_ceiling = max_u as usize;
                }
            }
            if let Some(tmpls) = val.get("templates").and_then(|v| v.as_table()) {
                for (k, v) in tmpls {
                    if let Ok(json_val) = serde_json::to_value(v) {
                        templates_map.insert(k.clone(), json_val);
                    }
                }
            }
        }
    }

    let ceiling = cli_ceiling.unwrap_or(default_ceiling);
    let grandfathered = load_grandfathered(&root_path);

    let mut compiled_templates: Vec<CompiledTemplate> = Vec::new();
    for (tname, tcfg) in templates_map {
        if let Some(match_str) = tcfg.get("match").and_then(|v| v.as_str()) {
            if let Ok(re) = Regex::new(match_str) {
                let required_header = tcfg
                    .get("required_header")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(true);
                let mut required_markers = Vec::new();
                if let Some(arr) = tcfg.get("required_markers").and_then(|v| v.as_array()) {
                    for m in arr {
                        if let Some(s) = m.as_str() {
                            required_markers.push(s.to_string());
                        }
                    }
                }
                let mut required_ordered = Vec::new();
                if let Some(arr) = tcfg.get("required_ordered").and_then(|v| v.as_array()) {
                    for m in arr {
                        if let Some(s) = m.as_str() {
                            required_ordered.push(s.to_string());
                        }
                    }
                }
                compiled_templates.push(CompiledTemplate {
                    name: tname,
                    pattern: re,
                    required_header,
                    required_markers,
                    required_ordered,
                });
            }
        }
    }

    let mut unconforming: Vec<(String, String)> = Vec::new();
    let mut checked_count = 0;

    let ignore_dirs: HashSet<&str> = [
        ".git",
        "node_modules",
        "target",
        ".venv",
        "dist",
        "build",
        ".system_generated",
    ]
    .iter()
    .cloned()
    .collect();

    for entry in WalkDir::new(&root_path)
        .into_iter()
        .filter_entry(|e| !ignore_dirs.contains(e.file_name().to_str().unwrap_or("")))
        .filter_map(|e| e.ok())
    {
        if !entry.file_type().is_file() {
            continue;
        }

        let p = entry.path();
        let rel_path = match p.strip_prefix(&root_path) {
            Ok(rel) => rel.to_string_lossy().replace('\\', "/"),
            Err(_) => continue,
        };

        if grandfathered.contains(&rel_path) {
            continue;
        }

        checked_count += 1;
        let content = match fs::read_to_string(p) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let head_end = content
            .char_indices()
            .map(|(i, _)| i)
            .chain(std::iter::once(content.len()))
            .take_while(|i| *i <= 8192)
            .last()
            .unwrap_or(0);
        let head = &content[..head_end];

        for ct in &compiled_templates {
            if ct.pattern.is_match(&rel_path) {
                if ct.required_header && !head.contains("AI-hint:") {
                    unconforming.push((
                        rel_path.clone(),
                        format!("Missing AI-hint header (required by {})", ct.name),
                    ));
                    break;
                }
                let mut marker_failed = false;
                for marker in &ct.required_markers {
                    if !content.contains(marker) {
                        unconforming.push((
                            rel_path.clone(),
                            format!(
                                "Missing required body marker {:?} (required by {})",
                                marker, ct.name
                            ),
                        ));
                        marker_failed = true;
                        break;
                    }
                }
                if marker_failed {
                    break;
                }
                let mut last_pos = 0;
                for marker in &ct.required_ordered {
                    if let Some(pos) = content[last_pos..].find(marker) {
                        last_pos += pos + marker.len();
                    } else {
                        unconforming.push((
                            rel_path.clone(),
                            format!(
                                "Out-of-order or missing required ordered marker {:?} (required by {})",
                                marker, ct.name
                            ),
                        ));
                        break;
                    }
                }
                break;
            }
        }
    }

    println!(
        "[conformance] checked={} unconforming={} ceiling={}",
        checked_count,
        unconforming.len(),
        ceiling
    );

    if !unconforming.is_empty() {
        eprintln!("Non-conforming files:");
        for (p, err) in &unconforming {
            eprintln!("    {}: {}", p, err);
        }
    }

    if unconforming.len() > ceiling {
        eprintln!(
            "FAIL: {} unconforming files exceeds ceiling {}",
            unconforming.len(),
            ceiling
        );
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_grandfathered_nonexistent() {
        let root = Path::new("/nonexistent_dir_12345");
        let gf = load_grandfathered(root);
        assert!(gf.is_empty());
    }

    #[test]
    fn test_load_grandfathered_mock() {
        let dir = std::env::temp_dir().join("mios_tmpl_conform_test");
        let gf_dir = dir.join("usr/share/mios/templates");
        let _ = fs::create_dir_all(&gf_dir);
        let gf_path = gf_dir.join("conformance-grandfathered.list");
        fs::write(&gf_path, "file1.py\nfile2.sh\n# comment\n\nfile3.rs\n").unwrap();

        let gf = load_grandfathered(&dir);
        assert!(gf.contains("file1.py"));
        assert!(gf.contains("file2.sh"));
        assert!(gf.contains("file3.rs"));
        assert!(!gf.contains("# comment"));

        let _ = fs::remove_file(gf_path);
        let _ = fs::remove_dir_all(dir);
    }
}

