// AI-hint: SSOT projector and verifier for [ports] flat table and port fallbacks (ADR-0021 gen category).
// AI-related: usr/share/mios/mios.toml, tools/render-ports.py, automation/35-render-ports.sh, automation/98-drift-checks.sh

use regex::Regex;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use toml::Value;
use walkdir::WalkDir;

pub const DEFAULT_TOML_PATH: &str = "usr/share/mios/mios.toml";

const SWEEP_PATHS: &[&str] = &["automation", "usr", "etc", "tools"];
const SWEEP_SKIP: &[&str] = &[
    "manifest.json",
    ".tsv",
    "/reference/",
    "/knowledge/",
    "/target/",
    "/.git/",
    "node_modules",
    "/tools/test_",
    "/tests/",
];

pub fn derive_ports(data: &Value) -> BTreeMap<String, i64> {
    let mut out = BTreeMap::new();
    let categories = match data
        .get("ports")
        .and_then(|p| p.get("categories"))
        .and_then(|c| c.as_table())
    {
        Some(c) => c,
        None => return out,
    };

    let mut cat_keys: Vec<&String> = categories.keys().collect();
    cat_keys.sort();

    for cat in cat_keys {
        let cfg = match categories.get(cat).and_then(|v| v.as_table()) {
            Some(t) => t,
            None => continue,
        };
        let base = cfg.get("base").and_then(|v| v.as_integer()).unwrap_or(0);
        let stride = cfg.get("stride").and_then(|v| v.as_integer()).unwrap_or(1);

        if let Some(members) = cfg.get("members").and_then(|v| v.as_array()) {
            for (idx, member) in members.iter().enumerate() {
                if let Some(name) = member.as_str() {
                    let trimmed = name.trim();
                    if !trimmed.is_empty() {
                        out.insert(trimmed.to_string(), base + (idx as i64) * stride);
                    }
                }
            }
        }

        if let Some(pinned) = cfg.get("pinned").and_then(|v| v.as_table()) {
            let mut pinned_keys: Vec<&String> = pinned.keys().collect();
            pinned_keys.sort();
            for name in pinned_keys {
                if let Some(val) = pinned.get(name).and_then(|v| v.as_integer()) {
                    out.insert(name.clone(), val);
                }
            }
        }
    }

    out
}

pub fn category_band(cfg: &Value) -> (i64, i64) {
    let base = cfg.get("base").and_then(|v| v.as_integer()).unwrap_or(0);
    let stride = cfg.get("stride").and_then(|v| v.as_integer()).unwrap_or(1);
    let n = cfg
        .get("members")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    if n == 0 {
        (base, base)
    } else {
        (base, base + ((n - 1) as i64) * stride)
    }
}

pub fn find_violations(data: &Value) -> Vec<String> {
    let mut problems = Vec::new();
    let categories = match data
        .get("ports")
        .and_then(|p| p.get("categories"))
        .and_then(|c| c.as_table())
    {
        Some(c) => c,
        None => return problems,
    };

    let flat: BTreeMap<String, i64> = match data.get("ports").and_then(|p| p.as_table()) {
        Some(p) => p
            .iter()
            .filter_map(|(k, v)| {
                if k != "stack_id" && k != "categories" {
                    v.as_integer().map(|i| (k.clone(), i))
                } else {
                    None
                }
            })
            .collect(),
        None => BTreeMap::new(),
    };

    // 1. every port declared in exactly one category
    let mut seen: BTreeMap<String, String> = BTreeMap::new();
    let mut cat_keys: Vec<&String> = categories.keys().collect();
    cat_keys.sort();

    for cat in cat_keys {
        let cfg = match categories.get(cat).and_then(|v| v.as_table()) {
            Some(t) => t,
            None => continue,
        };
        let mut names = Vec::new();
        if let Some(members) = cfg.get("members").and_then(|v| v.as_array()) {
            for m in members {
                if let Some(s) = m.as_str() {
                    names.push(s.to_string());
                }
            }
        }
        if let Some(pinned) = cfg.get("pinned").and_then(|v| v.as_table()) {
            let mut pk: Vec<&String> = pinned.keys().collect();
            pk.sort();
            for k in pk {
                names.push(k.clone());
            }
        }

        for name in names {
            let trimmed = name.trim();
            if trimmed.is_empty() {
                continue;
            }
            if let Some(prev_cat) = seen.get(trimmed) {
                problems.push(format!(
                    "port '{trimmed}' is claimed by both [ports.categories.{prev_cat}] and [ports.categories.{cat}]"
                ));
            } else {
                seen.insert(trimmed.to_string(), cat.clone());
            }
        }
    }

    for name in flat.keys() {
        if !seen.contains_key(name) {
            problems.push(format!(
                "port '{name}' is in the flat [ports] table but belongs to no category"
            ));
        }
    }
    for name in seen.keys() {
        if !flat.contains_key(name) {
            problems.push(format!(
                "port '{name}' is declared in [ports.categories.{}] but missing from the flat [ports] table",
                seen[name]
            ));
        }
    }

    // 2. no two ports share a value
    let derived = derive_ports(data);
    let mut by_value: BTreeMap<i64, Vec<String>> = BTreeMap::new();
    for (name, val) in &derived {
        by_value.entry(*val).or_default().push(name.clone());
    }
    for (val, names) in &by_value {
        if names.len() > 1 {
            problems.push(format!("port collision at {val}: {}", names.join(", ")));
        }
    }

    // 3. category bands must not overlap
    let mut bands = Vec::new();
    for (cat, cfg) in categories {
        if let Some(cfg_tbl) = cfg.as_table() {
            if let Some(members) = cfg_tbl.get("members").and_then(|v| v.as_array()) {
                if !members.is_empty() {
                    let (lo, hi) = category_band(cfg);
                    bands.push((lo, hi, cat.clone()));
                }
            }
        }
    }
    bands.sort_by_key(|b| (b.0, b.1, b.2.clone()));
    for pair in bands.windows(2) {
        let (lo1, hi1, ref c1) = pair[0];
        let (lo2, hi2, ref c2) = pair[1];
        if lo2 <= hi1 {
            problems.push(format!(
                "category band overlap: {c1} [{lo1}-{hi1}] overlaps {c2} [{lo2}-{hi2}]"
            ));
        }
    }

    // 4. the rendered projection must equal the flat table
    for (name, der_val) in &derived {
        if let Some(flat_val) = flat.get(name) {
            if der_val != flat_val {
                let cat_name = seen.get(name).map(|s| s.as_str()).unwrap_or("unknown");
                problems.push(format!(
                    "[ports].{name} = {flat_val} but [ports.categories.{cat_name}] derives {der_val} -- run tools/render-ports.py"
                ));
            }
        }
    }

    problems
}

pub fn render_table(text: &str, derived: &BTreeMap<String, i64>) -> Result<String, String> {
    let port_line = Regex::new(r"^(\s*)([a-z0-9_]+)(\s*)=(\s*)(\d+)(\s*)(#.*)?$")
        .map_err(|e| format!("regex compile failed: {e}"))?;

    let mut lines: Vec<String> = text.split('\n').map(|s| s.to_string()).collect();
    let mut start = None;
    for (i, line) in lines.iter().enumerate() {
        if line.trim() == "[ports]" {
            start = Some(i);
            break;
        }
    }

    let start_idx = match start {
        Some(s) => s,
        None => return Err("render-ports: no [ports] table found".to_string()),
    };

    for line in lines.iter_mut().skip(start_idx + 1) {
        let stripped = line.trim();
        if stripped.starts_with('[') {
            break;
        }
        let line_without_cr = line.trim_end_matches('\r');
        let has_cr = line.ends_with('\r');

        if let Some(caps) = port_line.captures(line_without_cr) {
            let indent = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let key = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            let sp1 = caps.get(3).map(|m| m.as_str()).unwrap_or("");
            let sp2 = caps.get(4).map(|m| m.as_str()).unwrap_or("");
            let old = caps.get(5).map(|m| m.as_str()).unwrap_or("");
            let sp3 = caps.get(6).map(|m| m.as_str()).unwrap_or("");
            let comment = caps.get(7).map(|m| m.as_str());

            if key == "stack_id" || !derived.contains_key(key) {
                continue;
            }

            let new = derived[key].to_string();
            let mut pad = format!("{}{}", sp2, " ".repeat(old.len().saturating_sub(new.len())));
            if new.len() > old.len() {
                let cut = sp2.len().saturating_sub(new.len() - old.len()).max(1);
                pad = sp2[..cut].to_string();
            }

            let mut rebuilt = format!("{indent}{key}{sp1}={pad}{new}");
            if let Some(c) = comment {
                rebuilt.push_str(&format!("{sp3}{c}"));
            }
            if has_cr {
                rebuilt.push('\r');
            }
            *line = rebuilt;
        }
    }

    Ok(lines.join("\n"))
}

pub fn sweep_files(root: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    for top in SWEEP_PATHS {
        let top_dir = root.join(top);
        if !top_dir.exists() {
            continue;
        }
        for entry in WalkDir::new(top_dir)
            .into_iter()
            .filter_entry(|e| {
                let name = e.file_name().to_string_lossy();
                name != ".git" && name != "target" && name != "node_modules" && name != "__pycache__"
            })
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                let path = entry.path();
                let path_str = path.to_string_lossy().replace('\\', "/");
                let rel = path
                    .strip_prefix(root)
                    .unwrap_or(path)
                    .to_string_lossy()
                    .replace('\\', "/");
                let rel_with_slash = format!("/{rel}");

                if SWEEP_SKIP
                    .iter()
                    .any(|s| path_str.contains(s) || rel.contains(s) || rel_with_slash.contains(s))
                {
                    continue;
                }
                out.push(path.to_path_buf());
            }
        }
    }
    out
}

pub fn sync_fallbacks(
    root: &Path,
    derived: &BTreeMap<String, i64>,
    apply: bool,
) -> Vec<String> {
    let fallback_re = match Regex::new(r"\$\{MIOS_PORT_([A-Z0-9_]+):-(\d+)\}") {
        Ok(r) => r,
        Err(_) => return Vec::new(),
    };

    let mut upper: BTreeMap<String, i64> = BTreeMap::new();
    for (k, v) in derived {
        upper.insert(k.to_uppercase(), *v);
    }

    let mut problems = Vec::new();
    for path in sweep_files(root) {
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(_) => continue,
        };
        if !text.contains("MIOS_PORT_") {
            continue;
        }

        let mut changed: Vec<(String, String, i64)> = Vec::new();
        let new_text = fallback_re
            .replace_all(&text, |caps: &regex::Captures| {
                let key = caps.get(1).map(|m| m.as_str()).unwrap_or("");
                let lit = caps.get(2).map(|m| m.as_str()).unwrap_or("");
                let name = if key == "GUACAMOLE" {
                    "GUACAMOLE_WEB"
                } else {
                    key
                };
                if let Some(&want) = upper.get(name) {
                    if want.to_string() != lit {
                        changed.push((key.to_string(), lit.to_string(), want));
                        return format!("${{MIOS_PORT_{key}:-{want}}}");
                    }
                }
                caps.get(0).map(|m| m.as_str()).unwrap_or("").to_string()
            })
            .to_string();

        if !changed.is_empty() {
            let rel = path
                .strip_prefix(root)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            for (key, lit, want) in &changed {
                problems.push(format!("{rel}: MIOS_PORT_{key} fallback :-{lit} != SSOT {want}"));
            }
            if apply {
                let _ = fs::write(&path, new_text);
            }
        }
    }

    problems
}

pub fn run_render_ports(
    root: &Path,
    toml_override: Option<&Path>,
    check: bool,
    print_ports: bool,
) -> Result<(String, i32), (String, i32)> {
    let toml_path = match toml_override {
        Some(p) => p.to_path_buf(),
        None => match std::env::var("MIOS_TOML") {
            Ok(v) if !v.trim().is_empty() => PathBuf::from(v.trim()),
            _ => root.join(DEFAULT_TOML_PATH),
        },
    };

    let content = fs::read_to_string(&toml_path).map_err(|e| {
        (
            format!("render-ports: {} could not be read: {e}", toml_path.display()),
            1,
        )
    })?;

    let parsed: Value = content.parse().map_err(|e| {
        (
            format!("render-ports: {} did not parse: {e}", toml_path.display()),
            1,
        )
    })?;

    let derived = derive_ports(&parsed);

    if print_ports {
        let mut by_val_name: Vec<(&String, &i64)> = derived.iter().collect();
        by_val_name.sort_by_key(|&(name, &val)| (val, name));
        let mut out = String::new();
        for (name, val) in by_val_name {
            out.push_str(&format!("{val:>6}  {name}\n"));
        }
        return Ok((out, 0));
    }

    let mut problems = find_violations(&parsed);
    let fallback_problems = sync_fallbacks(root, &derived, !check);

    let num_categories = parsed
        .get("ports")
        .and_then(|p| p.get("categories"))
        .and_then(|c| c.as_table())
        .map(|t| t.len())
        .unwrap_or(0);

    if check {
        problems.extend(fallback_problems);
        if !problems.is_empty() {
            let mut msg = "[render-ports] port schema drift:\n".to_string();
            for p in &problems {
                msg.push_str(&format!("    {p}\n"));
            }
            return Err((msg, 1));
        }
        let msg = format!(
            "[render-ports] {} ports derive cleanly from {} categories\n",
            derived.len(),
            num_categories
        );
        return Ok((msg, 0));
    }

    // Apply mode
    let fatal: Vec<&String> = problems
        .iter()
        .filter(|p| {
            !p.contains("run tools/render-ports.py") && !p.contains("run mios-gen render-ports")
        })
        .collect();

    if !fatal.is_empty() {
        let mut msg = "[render-ports] cannot render, fix the schema first:\n".to_string();
        for p in fatal {
            msg.push_str(&format!("    {p}\n"));
        }
        return Err((msg, 1));
    }

    let mut out_msg = String::new();
    if !fallback_problems.is_empty() {
        out_msg.push_str(&format!(
            "[render-ports] re-synced {} stale ${{MIOS_PORT_*:-N}} fallback(s) from SSOT\n",
            fallback_problems.len()
        ));
    }

    let new_toml = render_table(&content, &derived).map_err(|e| (e, 1))?;
    fs::write(&toml_path, new_toml).map_err(|e| {
        (
            format!("render-ports: failed to write {}: {e}", toml_path.display()),
            1,
        )
    })?;

    out_msg.push_str(&format!(
        "[render-ports] rendered {} ports into the flat [ports] table\n",
        derived.len()
    ));

    Ok((out_msg, 0))
}
