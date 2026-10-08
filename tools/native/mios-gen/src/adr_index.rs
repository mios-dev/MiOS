// AI-hint: SSOT projector and verifier for ADR.md breadcrumb index (ADR-0021 gen category).
// AI-related: usr/share/doc/mios/adr/, usr/share/mios/mios.toml, tools/native/mios-gen/src/adr_index.rs

use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use toml::Value;

pub const ADR_DIR: &str = "usr/share/doc/mios/adr";
pub const OUT: &str = "ADR.md";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdrRow {
    pub file: String,
    pub num: String,
    pub title: String,
    pub status: String,
    pub date: String,
    pub laws: Vec<String>,
    pub ssot: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParsedVal {
    Scalar(String),
    List(Vec<String>),
}

pub fn parse_front_matter(content: &str) -> HashMap<String, ParsedVal> {
    let mut out = HashMap::new();
    let scalar_re = Regex::new(r"^([a-z_]+):\s*(.*)$").unwrap();

    let lines: Vec<&str> = content.lines().collect();
    let start_idx = match lines.iter().position(|&l| l.trim() == "---") {
        Some(idx) => idx,
        None => return out,
    };

    for line in &lines[start_idx + 1..] {
        if line.trim() == "---" {
            break;
        }
        if let Some(caps) = scalar_re.captures(line) {
            let key = caps.get(1).unwrap().as_str().to_string();
            let val = caps.get(2).unwrap().as_str().trim();
            if val.starts_with('[') && val.ends_with(']') {
                let inner = &val[1..val.len() - 1].trim();
                let items: Vec<String> = inner
                    .split(',')
                    .map(|p| p.trim().to_string())
                    .filter(|p| !p.is_empty())
                    .collect();
                out.insert(key, ParsedVal::List(items));
            } else {
                out.insert(key, ParsedVal::Scalar(val.to_string()));
            }
        }
    }
    out
}

pub fn collect(root: &Path) -> (Vec<AdrRow>, Vec<String>) {
    let d = root.join(ADR_DIR);
    if !d.is_dir() {
        return (Vec::new(), Vec::new());
    }

    let mut entries = Vec::new();
    if let Ok(read_dir) = fs::read_dir(&d) {
        for entry in read_dir.flatten() {
            let fn_str = entry.file_name().to_string_lossy().to_string();
            if fn_str.ends_with(".md") && fn_str.chars().next().is_some_and(|c| c.is_ascii_digit())
            {
                entries.push(fn_str);
            }
        }
    }
    entries.sort();

    let mut rows = Vec::new();
    let mut malformed = Vec::new();

    for fn_str in entries {
        let path = d.join(&fn_str);
        let content = fs::read_to_string(&path).unwrap_or_default();
        let fm = parse_front_matter(&content);

        let adr_num = match fm.get("adr") {
            Some(ParsedVal::Scalar(s)) if !s.trim().is_empty() => s.trim().to_string(),
            _ => {
                malformed.push(fn_str);
                continue;
            }
        };

        let title = match fm.get("title") {
            Some(ParsedVal::Scalar(s)) => s.trim().to_string(),
            _ => String::new(),
        };
        let status = match fm.get("status") {
            Some(ParsedVal::Scalar(s)) => s.trim().to_string(),
            _ => String::new(),
        };
        let date = match fm.get("date") {
            Some(ParsedVal::Scalar(s)) => s.trim().to_string(),
            _ => String::new(),
        };
        let laws = match fm.get("laws") {
            Some(ParsedVal::List(l)) => l.clone(),
            _ => Vec::new(),
        };
        let ssot = match fm.get("ssot_keys") {
            Some(ParsedVal::List(s)) => s.clone(),
            _ => Vec::new(),
        };

        rows.push(AdrRow {
            file: fn_str,
            num: adr_num,
            title,
            status,
            date,
            laws,
            ssot,
        });
    }

    (rows, malformed)
}

pub fn render(rows: &[AdrRow]) -> String {
    let n = rows.len();
    let accepted = rows.iter().filter(|r| r.status == "accepted").count();

    let mut lines = Vec::new();
    lines.push("<!-- AI-hint: Repo-root breadcrumb to the MiOS Architecture Decision Records. GENERATED from the ADR front-matter by mios-gen adr-index; do not hand-edit -- run the generator. The ADRs themselves stay baked at usr/share/doc/mios/adr/ (Law 1: a running MiOS carries its own why), so this file is a pointer, not a copy. -->".to_string());
    lines.push("<!-- AI-related: usr/share/doc/mios/adr/, usr/share/doc/mios/adr/README.md, usr/share/mios/mios.toml [laws], tools/native/mios-gen/src/adr_index.rs -->".to_string());
    lines.push("".to_string());
    lines.push("# MiOS Architecture Decision Records".to_string());
    lines.push("".to_string());
    lines.push(format!(
        "**{} ADRs** ({} accepted). The records live at [`{}/`]({}/) and are **baked into the image** -- a running MiOS carries its own *why*. This file is the root breadcrumb so an agent starting at either repo root reaches any decision in two hops; the format and status lifecycle are described in [the ADR README]({}/README.md).",
        n, accepted, ADR_DIR, ADR_DIR, ADR_DIR
    ));
    lines.push("".to_string());
    lines.push("| # | Decision | Status | Date | Laws | SSOT keys |".to_string());
    lines.push("|---|---|---|---|---|---|".to_string());

    for r in rows {
        let laws = if r.laws.is_empty() {
            "--".to_string()
        } else {
            r.laws.join(", ")
        };

        let ssot = if r.ssot.is_empty() {
            "--".to_string()
        } else {
            let first_four: Vec<String> =
                r.ssot.iter().take(4).map(|x| format!("`{}`", x)).collect();
            let mut s = first_four.join(", ");
            if r.ssot.len() > 4 {
                s.push_str(&format!(", +{}", r.ssot.len() - 4));
            }
            s
        };

        lines.push(format!(
            "| {} | [{}]({}/{}) | {} | {} | {} | {} |",
            r.num, r.title, ADR_DIR, r.file, r.status, r.date, laws, ssot
        ));
    }

    lines.push("".to_string());
    lines.push(format!(
        "<!-- derived from the front-matter of {} file(s) under {}/ -->",
        n, ADR_DIR
    ));
    lines.push("".to_string());

    lines.join("\n")
}

pub fn validate_adr_ssot_consistency(root: &Path) -> Vec<String> {
    let ssot_path = root.join("usr/share/mios/mios.toml");
    if !ssot_path.is_file() {
        return vec!["usr/share/mios/mios.toml is missing (ADR-0009 violation)".to_string()];
    }

    let content = match fs::read_to_string(&ssot_path) {
        Ok(c) => c,
        Err(e) => return vec![format!("failed to parse mios.toml: {}", e)],
    };

    let ssot: Value = match toml::from_str(&content) {
        Ok(v) => v,
        Err(e) => return vec![format!("failed to parse mios.toml: {}", e)],
    };

    let mut violations = Vec::new();

    // ADR-0009: single SSOT config surface
    let has_version = ssot
        .get("meta")
        .and_then(|m| m.get("mios_version"))
        .is_some();
    if !has_version {
        violations
            .push("ADR-0009: mios.toml missing [meta].mios_version SSOT declaration".to_string());
    }

    // ADR-0010: SSOT as system dotfiles registry
    let has_dotfiles = ssot
        .get("dotfiles")
        .and_then(|d| d.as_table())
        .is_some_and(|t| !t.is_empty());
    if !has_dotfiles {
        violations
            .push("ADR-0010: mios.toml missing or empty [dotfiles] table registry".to_string());
    }

    // ADR-0003: SBOM image references integrity (no hardcoded @sha256: digests in [image])
    fn check_image_node(path: &str, node: &Value, viols: &mut Vec<String>) {
        match node {
            Value::String(s) => {
                if s.contains("@sha256:") {
                    viols.push(format!(
                        "ADR-0003: hardcoded @sha256 digest found in [image].{}: {}",
                        path, s
                    ));
                }
            }
            Value::Table(tbl) => {
                for (k, v) in tbl {
                    let sub = if path.is_empty() {
                        k.clone()
                    } else {
                        format!("{}.{}", path, k)
                    };
                    check_image_node(&sub, v, viols);
                }
            }
            _ => {}
        }
    }

    if let Some(images) = ssot.get("image") {
        check_image_node("", images, &mut violations);
    }

    // Enforce single canonical ADR directory: no shadow ADR namespaces in any */adr/
    let mut shadow_adrs = Vec::new();
    let norm_adr_dir = Path::new(ADR_DIR);

    fn walk_shadow(dir: &Path, root: &Path, norm_adr_dir: &Path, shadows: &mut Vec<String>) {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Ok(rel) = path.strip_prefix(root) {
                    let rel_str = rel.to_string_lossy().replace('\\', "/");
                    if path.is_dir() {
                        let dir_name = path.file_name().unwrap_or_default();
                        let dir_str = dir_name.to_string_lossy();
                        if dir_str.starts_with('.')
                            || dir_str == "target"
                            || dir_str == "node_modules"
                        {
                            continue;
                        }
                        if dir_str == "adr" && rel != norm_adr_dir {
                            if let Ok(sub) = fs::read_dir(&path) {
                                for f in sub.flatten() {
                                    let fn_str = f.file_name().to_string_lossy().to_string();
                                    if fn_str.ends_with(".md")
                                        && fn_str.chars().next().is_some_and(|c| c.is_ascii_digit())
                                    {
                                        shadows.push(format!("{}/{}", rel_str, fn_str));
                                    }
                                }
                            }
                        } else {
                            walk_shadow(&path, root, norm_adr_dir, shadows);
                        }
                    }
                }
            }
        }
    }

    walk_shadow(root, root, norm_adr_dir, &mut shadow_adrs);
    shadow_adrs.sort();
    if !shadow_adrs.is_empty() {
        violations.push(format!(
            "shadow ADR namespace found outside {}: {}",
            ADR_DIR,
            shadow_adrs.join(", ")
        ));
    }

    violations
}

pub fn run_adr_index(root: &Path, check: bool, json_mode: bool) -> Result<(), (String, i32)> {
    let (rows, malformed) = collect(root);

    if !malformed.is_empty() {
        let mut lines = Vec::new();
        for fn_str in &malformed {
            lines.push(format!(
                "VIOLATION: {}/{} has no `adr:` front-matter -- add it or rename",
                ADR_DIR, fn_str
            ));
        }
        return Err((lines.join("\n"), 1));
    }

    if rows.is_empty() {
        return Err((
            format!(
                "VIOLATION: no ADR front-matter collected under {}/ -- {} cannot be verified",
                ADR_DIR, OUT
            ),
            1,
        ));
    }

    let body = render(&rows);
    let path = root.join(OUT);

    if check {
        let current = match fs::read_to_string(&path) {
            Ok(c) => c,
            Err(_) => {
                return Err((
                    format!("{} is missing -- run mios-gen adr-index", OUT),
                    1,
                ));
            }
        };

        if current != body {
            return Err((
                format!("{} is stale -- run mios-gen adr-index", OUT),
                1,
            ));
        }

        let adr_viols = validate_adr_ssot_consistency(root);
        if !adr_viols.is_empty() {
            let mut lines = vec!["ADR SSOT consistency check failed:".to_string()];
            for v in &adr_viols {
                lines.push(format!("  {}", v));
            }
            return Err((lines.join("\n"), 1));
        }

        if !json_mode {
            println!(
                "{} matches the {} baked ADR(s) and SSOT consistency checks pass",
                OUT,
                rows.len()
            );
        }
        return Ok(());
    }

    let tmp_path = root.join(format!("{}.tmp", OUT));
    if let Err(e) = fs::write(&tmp_path, &body) {
        return Err((format!("failed to write {}: {}", tmp_path.display(), e), 1));
    }
    if let Err(e) = fs::rename(&tmp_path, &path) {
        return Err((format!("failed to replace {}: {}", path.display(), e), 1));
    }

    if !json_mode {
        println!("wrote {} from {} ADR(s)", OUT, rows.len());
    }
    Ok(())
}
