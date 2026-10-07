// AI-hint: SSOT projector and standardizer for specs/ markdown documentation (ADR-0021 gen category).
// AI-related: tools/standardize-docs.py, specs/engineering/2026-04-26-Artifact-ENG-002-Scripts-Index.md
// AI-functions: get_version, render_header, render_footer, extract_ai_hint, standardize_content, run_standardize_docs

use std::fs;
use std::path::{Path, PathBuf};
use regex::Regex;

pub const DEFAULT_TARGETS: &[&str] = &[
    "specs/audit",
    "specs/changelogs",
    "specs/core",
    "specs/engineering",
    "specs/memory",
    "specs/knowledge",
];

#[allow(dead_code)]
pub struct StandardizeDocsResult {
    pub scanned: usize,
    pub modified: usize,
    pub violations: usize,
    pub files: Vec<String>,
}

pub fn get_version(root: &Path) -> String {
    let version_file = root.join("VERSION");
    if let Ok(content) = fs::read_to_string(&version_file) {
        let v = content.trim();
        if !v.is_empty() {
            return v.to_string();
        }
    }

    let toml_file = root.join("usr/share/mios/mios.toml");
    if let Ok(content) = fs::read_to_string(&toml_file) {
        if let Ok(val) = content.parse::<toml::Value>() {
            if let Some(meta) = val.get("meta").and_then(|m| m.as_table()) {
                if let Some(v) = meta.get("mios_version").and_then(|v| v.as_str()) {
                    return v.trim().to_string();
                }
            }
        }
    }

    "0.3.0".to_string()
}

pub fn render_header(version: &str) -> String {
    format!(
"<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project | https://github.com/mios-dev/mios -->\n\
> **Proprietor:** 'MiOS' Project\n\
> **Infrastructure:** Self-Building Infrastructure (Personal Property)\n\
> **License:** Licensed as personal property to 'MiOS' Project\n\
> **Source Reference:** MiOS-Core-v{}\n\
---",
        version
    )
}

pub fn render_footer() -> &'static str {
    "---\n\
- **Copyright:** (c) 2026 'MiOS' Project\n\
- **Status:** Personal Property / Private Infrastructure\n\
- **Project Repository:** [MiOS-DEV/mios](https://github.com/mios-dev/mios)\n\
- **Documentation:** ['MiOS' Navigation Hub](https://github.com/mios-dev/mios/blob/main/specs/Home.md)\n\
- **Artifact Hub:** [ai-context.json](https://github.com/mios-dev/mios/blob/main/ai-context.json)\n\
---"
}

fn normalize_newlines(s: &str) -> String {
    s.replace("\r\n", "\n")
}

pub fn extract_ai_hint(content: &str) -> (Option<String>, &str) {
    let trimmed_start = content.trim_start_matches('\u{feff}').trim_start();
    if trimmed_start.starts_with("<!-- AI-hint:") {
        if let Some(end_idx) = trimmed_start.find("-->") {
            let hint_block = &trimmed_start[..end_idx + 3];
            let rest = &trimmed_start[end_idx + 3..];
            return (Some(hint_block.trim().to_string()), rest);
        }
    }
    (None, content)
}

pub fn standardize_content(raw_content: &str, version: &str) -> String {
    let normalized = normalize_newlines(raw_content);
    let (ai_hint, body_part) = extract_ai_hint(&normalized);

    let mut body = body_part.trim_start().to_string();

    // Strip existing or legacy header block
    if body.starts_with("<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project") {
        if let Some(pos) = body.find("\n---\n") {
            let header_candidate = &body[..pos];
            if header_candidate.contains("> **Proprietor:**") {
                body = body[pos + 5..].to_string();
            } else if let Some(newline_pos) = body.find('\n') {
                body = body[newline_pos + 1..].to_string();
            }
        } else if let Some(newline_pos) = body.find('\n') {
            body = body[newline_pos + 1..].to_string();
        }
    } else if body.starts_with("#  MiOS") {
        if let Some(pos) = body.find("\n---\n") {
            let header_candidate = &body[..pos];
            if header_candidate.contains("> **Proprietor:**") {
                body = body[pos + 5..].to_string();
            }
        }
    }

    // Strip legacy footers
    let legacy_footer1_re = Regex::new(r"(?s)\n---\n###\s+(?:Legal & Source Reference|Bootc Ecosystem & Resources).*?---(?:\s*)$").expect("valid regex");
    let proprietary_footer_re = Regex::new(r"(?s)\n<!--\s+'MiOS'\s+Proprietary\s+Artifact.*?-->\s*$").expect("valid regex");

    body = legacy_footer1_re.replace(&body, "").to_string();
    body = proprietary_footer_re.replace(&body, "").to_string();

    // Strip existing standard footer if present
    let footer = render_footer();
    let trimmed_end = body.trim_end();
    if trimmed_end.ends_with(footer) {
        body = trimmed_end[..trimmed_end.len() - footer.len()].to_string();
    } else if let Some(pos) = trimmed_end.rfind("\n---\n- **Copyright:** (c) 2026 'MiOS' Project") {
        body = trimmed_end[..pos].to_string();
    }

    let trimmed_body = body.trim();
    let header = render_header(version);

    if let Some(hint) = ai_hint {
        format!("{}\n\n{}\n\n{}\n\n{}\n", hint, header, trimmed_body, footer)
    } else {
        format!("{}\n\n{}\n\n{}\n", header, trimmed_body, footer)
    }
}

pub fn collect_target_files(root: &Path, paths: &[PathBuf]) -> Vec<PathBuf> {
    let mut files = Vec::new();
    if !paths.is_empty() {
        for p in paths {
            let full = if p.is_absolute() { p.clone() } else { root.join(p) };
            if full.is_file() {
                if full.extension().and_then(|e| e.to_str()) == Some("md") {
                    files.push(full);
                }
            } else if full.is_dir() {
                walk_md_files(&full, &mut files);
            }
        }
    } else {
        for target in DEFAULT_TARGETS {
            let target_dir = root.join(target);
            if target_dir.is_dir() {
                walk_md_files(&target_dir, &mut files);
            }
        }
    }
    files.sort();
    files.dedup();
    files
}

fn walk_md_files(dir: &Path, out: &mut Vec<PathBuf>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk_md_files(&path, out);
            } else if path.is_file() && path.extension().and_then(|e| e.to_str()) == Some("md") {
                out.push(path);
            }
        }
    }
}

pub fn run_standardize_docs(
    root: &Path,
    check: bool,
    paths: &[PathBuf],
) -> Result<StandardizeDocsResult, String> {
    let version = get_version(root);
    let target_files = collect_target_files(root, paths);

    let mut scanned = 0;
    let mut modified = 0;
    let mut violations = 0;
    let mut unstandardized = Vec::new();

    for file_path in &target_files {
        scanned += 1;
        let content = fs::read_to_string(file_path)
            .map_err(|e| format!("Failed to read {}: {}", file_path.display(), e))?;

        let standardized = standardize_content(&content, &version);
        let normalized_current = normalize_newlines(&content);
        let normalized_standard = normalize_newlines(&standardized);

        if normalized_current != normalized_standard {
            let rel = file_path.strip_prefix(root).unwrap_or(file_path);
            let rel_str = rel.display().to_string().replace('\\', "/");
            if check {
                violations += 1;
                eprintln!("[standardize-docs] UNSTANDARDIZED: {} does not match standardized format", rel_str);
                unstandardized.push(rel_str);
            } else {
                fs::write(file_path, standardized.as_bytes())
                    .map_err(|e| format!("Failed to write {}: {}", file_path.display(), e))?;
                println!("Standardizing {}...", rel_str);
                modified += 1;
            }
        }
    }

    if check && violations > 0 {
        return Err(format!(
            "[standardize-docs] {} file(s) require standardization: {}",
            violations,
            unstandardized.join(", ")
        ));
    }

    Ok(StandardizeDocsResult {
        scanned,
        modified,
        violations,
        files: target_files
            .iter()
            .map(|p| {
                p.strip_prefix(root)
                    .unwrap_or(p)
                    .display()
                    .to_string()
                    .replace('\\', "/")
            })
            .collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_standardize_plain_content() {
        let content = "# My Spec Title\n\nSome spec content here.";
        let res = standardize_content(content, "0.3.0");
        assert!(res.contains("<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project"));
        assert!(res.contains("> **Source Reference:** MiOS-Core-v0.3.0"));
        assert!(res.contains("# My Spec Title"));
        assert!(res.contains("- **Copyright:** (c) 2026 'MiOS' Project"));
    }

    #[test]
    fn test_standardize_idempotent() {
        let content = "# Initial Title\n\nBody content.";
        let first = standardize_content(content, "0.3.0");
        let second = standardize_content(&first, "0.3.0");
        assert_eq!(first, second);
    }

    #[test]
    fn test_standardize_with_ai_hint() {
        let content = "<!-- AI-hint: Important hint for AI agents. -->\n# Header\nBody.";
        let res = standardize_content(content, "0.3.0");
        assert!(res.starts_with("<!-- AI-hint: Important hint for AI agents. -->"));
        assert!(res.contains("<!--  'MiOS' Artifact"));

        let res2 = standardize_content(&res, "0.3.0");
        assert_eq!(res, res2);
    }

    #[test]
    fn test_standardize_legacy_cleanup() {
        let content = "#  MiOS Legacy Spec\n> **Proprietor:** Old\n---\n# Real Title\nBody.\n---\n### Legal & Source Reference\nOld stuff.\n---";
        let res = standardize_content(content, "0.3.0");
        assert!(!res.contains("Legacy Spec"));
        assert!(!res.contains("Old stuff"));
        assert!(res.contains("# Real Title"));
        assert!(res.contains("- **Copyright:** (c) 2026 'MiOS' Project"));
    }

    #[test]
    fn test_standardize_preserves_title_with_single_line_artifact_comment() {
        let content = "<!-- AI-hint: Hint. -->\n<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project | https://github.com/MiOS-DEV/mios -->\n#  'MiOS' Scripts Index\n> **Status:** Maintained\n\nContent.";
        let res = standardize_content(content, "0.3.0");
        assert!(res.starts_with("<!-- AI-hint: Hint. -->"));
        assert!(res.contains("<!--  'MiOS' Artifact | Proprietor: 'MiOS' Project | https://github.com/mios-dev/mios -->"));
        assert!(res.contains("#  'MiOS' Scripts Index"));
        assert!(res.contains("> **Status:** Maintained"));
        assert!(res.contains("Content."));

        let res2 = standardize_content(&res, "0.3.0");
        assert_eq!(res, res2);
    }
}
