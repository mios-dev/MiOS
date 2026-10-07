// AI-hint: SSOT module-boundary manifest generator for the agent-pipe DI contract (ADR-0021 gen category).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: usr/share/mios/pipe-boundaries.manifest.json, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

use regex::Regex;
use serde::Serialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Serialize, Debug, Clone)]
pub struct ModuleEntry {
    pub configure_kwargs: Vec<String>,
    pub public_symbols: Vec<String>,
}

#[derive(Serialize, Debug, Clone)]
pub struct Manifest {
    pub modules: BTreeMap<String, ModuleEntry>,
}

#[derive(Debug, Clone)]
pub struct PipeBoundaryResult {
    pub modules_count: usize,
}

pub fn extract_module_boundaries(content: &str) -> (Vec<String>, Vec<String>) {
    let mut config_kwargs = Vec::new();

    // 1. Parse def configure(...)
    let configure_re = Regex::new(r"(?s)def configure\s*\((.*?)\)(?:\s*->\s*[^:]+)?\s*:").unwrap();
    if let Some(caps) = configure_re.captures(content) {
        let args_str = caps.get(1).map(|m| m.as_str()).unwrap_or("");
        let kw_re = Regex::new(r"(?s)(?:^|,)\s*\*(?:[a-zA-Z_0-9]+)?\s*,\s*(.*)").unwrap();
        if let Some(kw_caps) = kw_re.captures(args_str) {
            let raw_kw = kw_caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let mut parts = Vec::new();
            let mut depth = 0;
            let mut cur = String::new();
            for ch in raw_kw.chars() {
                match ch {
                    '(' | '[' | '{' => {
                        depth += 1;
                        cur.push(ch);
                    }
                    ')' | ']' | '}' => {
                        depth -= 1;
                        cur.push(ch);
                    }
                    ',' if depth == 0 => {
                        let trimmed = cur.trim();
                        if !trimmed.is_empty() {
                            parts.push(trimmed.to_string());
                        }
                        cur.clear();
                    }
                    _ => cur.push(ch),
                }
            }
            let trimmed = cur.trim();
            if !trimmed.is_empty() {
                parts.push(trimmed.to_string());
            }

            let ident_re = Regex::new(r"^([a-zA-Z_][a-zA-Z0-9_]*)").unwrap();
            for p in parts {
                if p.starts_with("**") {
                    continue;
                }
                if let Some(icaps) = ident_re.captures(&p) {
                    config_kwargs.push(icaps[1].to_string());
                }
            }
        }
    }
    config_kwargs.sort();

    // 2. Parse public_symbols (functions and classes not starting with _)
    let mut public_symbols = Vec::new();
    let def_re = Regex::new(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(").unwrap();
    let cls_re = Regex::new(r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\b").unwrap();

    let mut in_multiline_str: Option<&str> = None;
    for line in content.lines() {
        let sline = line.trim();

        if let Some(delim) = in_multiline_str {
            if sline.contains(delim) {
                in_multiline_str = None;
            }
            continue;
        }

        if sline.contains("\"\"\"") && sline.matches("\"\"\"").count() % 2 == 1 {
            in_multiline_str = Some("\"\"\"");
            continue;
        }
        if sline.contains("'''") && sline.matches("'''").count() % 2 == 1 {
            in_multiline_str = Some("'''");
            continue;
        }

        if let Some(caps) = def_re.captures(line) {
            let name = &caps[1];
            if name != "configure" && !name.starts_with('_') {
                public_symbols.push(name.to_string());
            }
        } else if let Some(caps) = cls_re.captures(line) {
            let name = &caps[1];
            if !name.starts_with('_') {
                public_symbols.push(name.to_string());
            }
        }
    }
    public_symbols.sort();

    (config_kwargs, public_symbols)
}

pub fn render_manifest(root: &Path) -> Result<(String, usize), String> {
    let pipe_dir = root.join("usr/lib/mios/agent-pipe/mios_pipe");
    if !pipe_dir.is_dir() {
        return Err(format!(
            "[gen-pipe-boundary-manifest] agent-pipe directory not found: {:?}",
            pipe_dir
        ));
    }

    let mut files: Vec<(String, PathBuf)> = Vec::new();
    for entry in WalkDir::new(&pipe_dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
    {
        let path = entry.path();
        let fname = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
        if fname.ends_with(".py") && !fname.starts_with("test_") {
            let rel = path
                .strip_prefix(root)
                .map_err(|e| format!("Strip prefix failed: {}", e))?;
            let rel_str = rel.to_string_lossy().replace('\\', "/");
            files.push((rel_str, path.to_path_buf()));
        }
    }
    files.sort_by(|a, b| a.0.cmp(&b.0));

    let mut manifest = Manifest {
        modules: BTreeMap::new(),
    };

    for (rel_path, abs_path) in files {
        let content = fs::read_to_string(&abs_path)
            .map_err(|e| format!("Failed to read {}: {}", abs_path.display(), e))?;
        let (configure_kwargs, public_symbols) = extract_module_boundaries(&content);
        if !configure_kwargs.is_empty() || !public_symbols.is_empty() {
            manifest.modules.insert(
                rel_path,
                ModuleEntry {
                    configure_kwargs,
                    public_symbols,
                },
            );
        }
    }

    let modules_count = manifest.modules.len();
    let mut rendered = serde_json::to_string_pretty(&manifest)
        .map_err(|e| format!("Serialization error: {}", e))?;
    rendered.push('\n');

    Ok((rendered, modules_count))
}

fn normalize_newlines(s: &str) -> String {
    s.replace("\r\n", "\n")
}

pub fn run_pipe_boundaries(root: &Path, check: bool) -> Result<PipeBoundaryResult, String> {
    let out_json = root.join("usr/share/mios/pipe-boundaries.manifest.json");
    let (rendered, modules_count) = render_manifest(root)?;

    if check {
        if !out_json.exists() {
            return Err(format!("MISSING {}", out_json.display()));
        }

        let committed = fs::read_to_string(&out_json)
            .map_err(|e| format!("Failed to read {}: {}", out_json.display(), e))?;

        if normalize_newlines(&committed) != normalize_newlines(&rendered) {
            return Err(format!(
                "[gen-pipe-boundary-manifest] STALE: {} does not match the tree",
                out_json.display()
            ));
        }

        Ok(PipeBoundaryResult { modules_count })
    } else {
        if let Some(parent) = out_json.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory {}: {}", parent.display(), e))?;
        }

        fs::write(&out_json, rendered.as_bytes())
            .map_err(|e| format!("Failed to write {}: {}", out_json.display(), e))?;

        Ok(PipeBoundaryResult { modules_count })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_module_boundaries_simple() {
        let content = r#"
class Foo:
    def __init__(self):
        pass
    def bar(self):
        pass

def _private_func():
    pass

def public_func():
    pass

def configure(*, alpha=None, beta=123):
    pass
"#;
        let (kwargs, symbols) = extract_module_boundaries(content);
        assert_eq!(kwargs, vec!["alpha", "beta"]);
        assert_eq!(symbols, vec!["Foo", "bar", "public_func"]);
    }
}
