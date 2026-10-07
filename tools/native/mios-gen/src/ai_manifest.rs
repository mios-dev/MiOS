// AI-hint: SSOT projector and verifier for AI repository and tool manifests (ADR-0021 gen category).
// AI-related: tools/generate-ai-manifest.py, automation/manifest.json, tools/manifest.json, specs/manifest.json

use flate2::read::GzDecoder;
use flate2::write::GzEncoder;
use flate2::Compression;
use regex::Regex;
use serde::Serialize;
use serde_json::Value;
use std::collections::HashSet;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

pub const TARGETS: &[(&str, &str, bool)] = &[
    ("specs", "specs/manifest.json", false),
    (
        ".ai/foundation/memories",
        ".ai/foundation/memories/manifest.json",
        false,
    ),
    ("artifacts", "artifacts/manifest.json.gz", false),
    ("automation", "automation/manifest.json", true),
    ("tools", "tools/manifest.json", true),
    ("overlay", "manifest.json", true),
    ("evals", "evals/manifest.json", true),
    ("bib-configs", "bib-configs/manifest.json", true),
    ("agents/research", "agents/research/manifest.json", true),
    (".", "root-manifest.json", false),
];

pub const IGNORE_DIRS: &[&str] = &[
    ".git",
    ".venv",
    "output",
    "__pycache__",
    "agents/research",
    "node_modules",
    "target",
    "dist",
    "build",
    ".system_generated",
    "scratch",
    "logs",
];

#[derive(Serialize)]
pub struct Manifest {
    pub source_directory: String,
    pub entries: Vec<ManifestEntry>,
}

#[derive(Serialize)]
#[serde(untagged)]
pub enum ManifestEntry {
    Documentation {
        path: String,
        title: String,
        #[serde(rename = "type")]
        entry_type: &'static str,
        metadata: serde_json::Map<String, Value>,
        knowledge: Value,
        content_preview: String,
        full_content: String,
    },
    StructuredData {
        path: String,
        title: String,
        #[serde(rename = "type")]
        entry_type: &'static str,
        structured_data: Value,
    },
    SourceCode {
        path: String,
        title: String,
        #[serde(rename = "type")]
        entry_type: &'static str,
        full_content: String,
    },
}

#[allow(dead_code)]
impl ManifestEntry {
    pub fn path(&self) -> &str {
        match self {
            ManifestEntry::Documentation { path, .. } => path,
            ManifestEntry::StructuredData { path, .. } => path,
            ManifestEntry::SourceCode { path, .. } => path,
        }
    }
}

pub fn parse_markdown_metadata(content: &str) -> (String, serde_json::Map<String, Value>, Value) {
    let title_re = Regex::new(r"(?m)^#\s+(.+)$").expect("valid title regex");
    let title = title_re
        .captures(content)
        .and_then(|caps| caps.get(1))
        .map(|m| m.as_str().trim().to_string())
        .unwrap_or_else(|| "Untitled".to_string());

    let meta_re = Regex::new(r"(?m)^>\s+\*\*(.+?):\*\*\s+(.+)$").expect("valid meta regex");
    let mut metadata = serde_json::Map::new();
    for caps in meta_re.captures_iter(content) {
        if let (Some(k), Some(v)) = (caps.get(1), caps.get(2)) {
            let key = k.as_str().trim().to_lowercase().replace(' ', "_");
            let val = v.as_str().trim().to_string();
            metadata.insert(key, Value::String(val));
        }
    }

    let kb_re = Regex::new(r"(?s)```json:knowledge\s*\r?\n(.*?)\r?\n```").expect("valid kb regex");
    let knowledge_block = if let Some(caps) = kb_re.captures(content) {
        caps.get(1)
            .and_then(|m| serde_json::from_str(m.as_str()).ok())
            .unwrap_or_else(|| serde_json::json!({}))
    } else {
        serde_json::json!({})
    };

    (title, metadata, knowledge_block)
}

pub fn get_tracked_files(root: &Path) -> Result<Option<HashSet<String>>, String> {
    // A standalone fixture has no index. A checkout with an unreadable index
    // must fail rather than accidentally publishing ignored operator files.
    if !root.join(".git").try_exists().map_err(|e| e.to_string())? {
        return Ok(None);
    }
    let output = Command::new("git")
        .current_dir(root)
        .args(["ls-files"])
        .output()
        .map_err(|e| format!("cannot read tracked source index: {e}"))?;

    if !output.status.success() {
        return Err(format!(
            "cannot read tracked source index: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }

    let text = String::from_utf8(output.stdout)
        .map_err(|e| format!("invalid tracked source index paths: {e}"))?;
    let set: HashSet<String> = text
        .lines()
        .map(|l| l.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    if set.is_empty() {
        return Err("tracked source index is empty".into());
    }
    Ok(Some(set))
}

fn is_tracked(rel_path: &str, tracked: Option<&HashSet<String>>) -> bool {
    tracked.is_none_or(|set| set.contains(rel_path))
}

fn collect_json_entries(
    dir: &Path,
    root: &Path,
    recursive: bool,
    ignore_dirs: &HashSet<&str>,
    output_prefix: &str,
    tracked: Option<&HashSet<String>>,
    entries: &mut Vec<ManifestEntry>,
) {
    let read_res = match fs::read_dir(dir) {
        Ok(r) => r,
        Err(_) => return,
    };

    let mut subdirs: Vec<PathBuf> = Vec::new();
    let mut files: Vec<PathBuf> = Vec::new();

    for entry in read_res.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = match path.file_name().and_then(|n| n.to_str()) {
                Some(n) => n,
                None => continue,
            };
            if !ignore_dirs.contains(name) {
                subdirs.push(path);
            }
        } else if path.is_file() {
            files.push(path);
        }
    }

    subdirs.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    files.sort_by(|a, b| a.file_name().cmp(&b.file_name()));

    for file_path in files {
        let file_name = match file_path.file_name().and_then(|n| n.to_str()) {
            Some(n) => n,
            None => continue,
        };

        if file_name.starts_with(output_prefix) || file_name.ends_with(".tmp") {
            continue;
        }

        let rel_path_buf = match file_path.strip_prefix(root) {
            Ok(p) => p,
            Err(_) => continue,
        };
        let rel_path = rel_path_buf.to_string_lossy().replace('\\', "/");

        if !is_tracked(&rel_path, tracked) {
            continue;
        }

        if file_name.ends_with(".md") {
            let raw_bytes = match fs::read(&file_path) {
                Ok(b) => b,
                Err(_) => continue,
            };
            let content = match std::str::from_utf8(&raw_bytes) {
                Ok(s) => s.replace("\r\n", "\n"),
                Err(_) => continue,
            };

            let (title, metadata, knowledge) = parse_markdown_metadata(&content);
            let char_count = content.chars().count();
            let content_preview = if char_count > 500 {
                let mut s: String = content.chars().take(500).collect();
                s.push_str("...");
                s
            } else {
                content.clone()
            };

            entries.push(ManifestEntry::Documentation {
                path: rel_path,
                title,
                entry_type: "documentation",
                metadata,
                knowledge,
                content_preview,
                full_content: content,
            });
        } else if file_name.ends_with(".json") {
            let raw_bytes = match fs::read(&file_path) {
                Ok(b) => b,
                Err(_) => continue,
            };
            let text = match std::str::from_utf8(&raw_bytes) {
                Ok(s) => s,
                Err(_) => continue,
            };
            let data: Value = match serde_json::from_str(text) {
                Ok(v) => v,
                Err(_) => continue,
            };

            let title = if let Value::Object(ref map) = data {
                map.get("artifact_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or(file_name)
                    .to_string()
            } else {
                file_name.to_string()
            };

            entries.push(ManifestEntry::StructuredData {
                path: rel_path,
                title,
                entry_type: "structured_data",
                structured_data: data,
            });
        } else if file_name.ends_with(".sh")
            || file_name.ends_with(".ps1")
            || file_name.ends_with(".py")
            || file_name.ends_with(".toml")
            || file_name.ends_with("Containerfile")
            || file_name.ends_with("Justfile")
        {
            let raw_bytes = match fs::read(&file_path) {
                Ok(b) => b,
                Err(_) => continue,
            };
            let content = match std::str::from_utf8(&raw_bytes) {
                Ok(s) => s.replace("\r\n", "\n"),
                Err(_) => continue,
            };

            entries.push(ManifestEntry::SourceCode {
                path: rel_path,
                title: file_name.to_string(),
                entry_type: "source_code",
                full_content: content,
            });
        }
    }

    if recursive {
        for sub in subdirs {
            collect_json_entries(
                &sub,
                root,
                recursive,
                ignore_dirs,
                output_prefix,
                tracked,
                entries,
            );
        }
    }
}

fn collect_gz_entries(
    dir: &Path,
    root: &Path,
    recursive: bool,
    ignore_dirs: &HashSet<&str>,
    output_prefix: &str,
    tracked: Option<&HashSet<String>>,
    entries: &mut Vec<ManifestEntry>,
) {
    let read_res = match fs::read_dir(dir) {
        Ok(r) => r,
        Err(_) => return,
    };

    let mut subdirs: Vec<PathBuf> = Vec::new();
    let mut files: Vec<PathBuf> = Vec::new();

    for entry in read_res.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = match path.file_name().and_then(|n| n.to_str()) {
                Some(n) => n,
                None => continue,
            };
            if !ignore_dirs.contains(name) {
                subdirs.push(path);
            }
        } else if path.is_file() {
            files.push(path);
        }
    }

    subdirs.sort_by(|a, b| a.file_name().cmp(&b.file_name()));
    files.sort_by(|a, b| a.file_name().cmp(&b.file_name()));

    for file_path in files {
        let file_name = match file_path.file_name().and_then(|n| n.to_str()) {
            Some(n) => n,
            None => continue,
        };

        if file_name.starts_with(output_prefix) || file_name.ends_with(".tmp") {
            continue;
        }

        let rel_path_buf = match file_path.strip_prefix(root) {
            Ok(p) => p,
            Err(_) => continue,
        };
        let rel_path = rel_path_buf.to_string_lossy().replace('\\', "/");

        if !is_tracked(&rel_path, tracked) {
            continue;
        }

        if file_name.ends_with(".json.gz") {
            let file = match fs::File::open(&file_path) {
                Ok(f) => f,
                Err(_) => continue,
            };
            let mut decoder = GzDecoder::new(file);
            let mut text = String::new();
            if decoder.read_to_string(&mut text).is_err() {
                continue;
            }
            let data: Value = match serde_json::from_str(&text) {
                Ok(v) => v,
                Err(_) => continue,
            };

            let title = if let Value::Object(ref map) = data {
                map.get("artifact_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or(file_name)
                    .to_string()
            } else {
                file_name.to_string()
            };

            entries.push(ManifestEntry::StructuredData {
                path: rel_path,
                title,
                entry_type: "structured_data",
                structured_data: data,
            });
        } else if file_name.ends_with(".json") {
            let raw_bytes = match fs::read(&file_path) {
                Ok(b) => b,
                Err(_) => continue,
            };
            let text = match std::str::from_utf8(&raw_bytes) {
                Ok(s) => s,
                Err(_) => continue,
            };
            let data: Value = match serde_json::from_str(text) {
                Ok(v) => v,
                Err(_) => continue,
            };

            let title = if let Value::Object(ref map) = data {
                map.get("artifact_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or(file_name)
                    .to_string()
            } else {
                file_name.to_string()
            };

            entries.push(ManifestEntry::StructuredData {
                path: rel_path,
                title,
                entry_type: "structured_data",
                structured_data: data,
            });
        }
    }

    if recursive {
        for sub in subdirs {
            collect_gz_entries(
                &sub,
                root,
                recursive,
                ignore_dirs,
                output_prefix,
                tracked,
                entries,
            );
        }
    }
}

pub fn escape_ascii_json(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        let code = c as u32;
        if code > 0x7F {
            if code <= 0xFFFF {
                use std::fmt::Write;
                let _ = write!(out, "\\u{:04x}", code);
            } else {
                let n = code - 0x10000;
                let hi = 0xD800 + (n >> 10);
                let lo = 0xDC00 + (n & 0x3FF);
                use std::fmt::Write;
                let _ = write!(out, "\\u{:04x}\\u{:04x}", hi, lo);
            }
        } else {
            out.push(c);
        }
    }
    out
}

pub fn generate_manifest(
    root: &Path,
    target_dir: &str,
    output_file: &str,
    recursive: bool,
    tracked: Option<&HashSet<String>>,
) -> Result<Vec<u8>, String> {
    let ignore_dirs: HashSet<&str> = IGNORE_DIRS.iter().copied().collect();
    let target_path = if target_dir == "." {
        root.to_path_buf()
    } else {
        root.join(target_dir)
    };

    if !target_path.exists() {
        return Err(format!("Target directory does not exist: {target_dir}"));
    }

    let output_basename = Path::new(output_file)
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .replace(".tmp", "");

    let mut entries = Vec::new();

    if output_file.ends_with(".gz") {
        collect_gz_entries(
            &target_path,
            root,
            recursive,
            &ignore_dirs,
            &output_basename,
            tracked,
            &mut entries,
        );

        let manifest = Manifest {
            source_directory: target_dir.to_string(),
            entries,
        };

        let json_str = serde_json::to_string_pretty(&manifest)
            .map_err(|e| format!("Failed to format JSON: {e}"))?;
        let escaped = escape_ascii_json(&json_str);

        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder
            .write_all(escaped.as_bytes())
            .map_err(|e| format!("Failed to gzip manifest: {e}"))?;
        encoder
            .finish()
            .map_err(|e| format!("Failed to finalize gzip: {e}"))
    } else {
        collect_json_entries(
            &target_path,
            root,
            recursive,
            &ignore_dirs,
            &output_basename,
            tracked,
            &mut entries,
        );

        let manifest = Manifest {
            source_directory: target_dir.to_string(),
            entries,
        };

        let json_str =
            serde_json::to_string(&manifest).map_err(|e| format!("Failed to format JSON: {e}"))?;
        let escaped = escape_ascii_json(&json_str);

        Ok(escaped.into_bytes())
    }
}

pub fn run_ai_manifest(root: &Path, check: bool, json_format: bool) -> Result<(), (String, i32)> {
    if !root.is_dir() {
        return Err((format!("Repository root not found: {}", root.display()), 1));
    }

    let tracked = get_tracked_files(root).map_err(|e| (e, 1))?;
    let mut has_drift = false;
    let mut first_error = None;

    for &(target_dir, output_file, recursive) in TARGETS {
        let target_path = if target_dir == "." {
            root.to_path_buf()
        } else {
            root.join(target_dir)
        };

        if !target_path.exists() {
            continue;
        }

        // Only GATE manifests that are actually committed in git
        if check && tracked.as_ref().is_some_and(|k| !k.contains(output_file)) {
            continue;
        }

        let full_output_path = root.join(output_file);

        let generated_bytes =
            match generate_manifest(root, target_dir, output_file, recursive, tracked.as_ref()) {
                Ok(b) => b,
                Err(e) => {
                    return Err((e, 2));
                }
            };

        if check {
            if !full_output_path.exists() {
                eprintln!("[generate-ai-manifest] Missing manifest file: {output_file}");
                has_drift = true;
                if first_error.is_none() {
                    first_error = Some(format!("Missing manifest file: {output_file}"));
                }
                continue;
            }

            let matches = if output_file.ends_with(".gz") {
                // For gz, decompress and compare strings
                let file = match fs::File::open(&full_output_path) {
                    Ok(f) => f,
                    Err(e) => {
                        eprintln!("[generate-ai-manifest] Cannot read {output_file}: {e}");
                        has_drift = true;
                        continue;
                    }
                };
                let mut d1 = String::new();
                let mut d2 = String::new();
                let _ = GzDecoder::new(file).read_to_string(&mut d1);
                let _ = GzDecoder::new(&generated_bytes[..]).read_to_string(&mut d2);
                d1 == d2
            } else {
                let existing_bytes = match fs::read(&full_output_path) {
                    Ok(b) => b,
                    Err(e) => {
                        eprintln!("[generate-ai-manifest] Cannot read {output_file}: {e}");
                        has_drift = true;
                        continue;
                    }
                };
                existing_bytes == generated_bytes
            };

            if !matches {
                eprintln!("[generate-ai-manifest] Manifest drift detected: {output_file}");

                // Surface diff diagnostics matching Python
                if !output_file.ends_with(".gz") {
                    if let (Ok(v1), Ok(v2)) = (
                        serde_json::from_slice::<Value>(
                            &fs::read(&full_output_path).unwrap_or_default(),
                        ),
                        serde_json::from_slice::<Value>(&generated_bytes),
                    ) {
                        let e1: HashSet<String> = v1
                            .get("entries")
                            .and_then(|e| e.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|x| {
                                        x.get("path")
                                            .and_then(|p| p.as_str())
                                            .map(|s| s.to_string())
                                    })
                                    .collect()
                            })
                            .unwrap_or_default();
                        let e2: HashSet<String> = v2
                            .get("entries")
                            .and_then(|e| e.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|x| {
                                        x.get("path")
                                            .and_then(|p| p.as_str())
                                            .map(|s| s.to_string())
                                    })
                                    .collect()
                            })
                            .unwrap_or_default();

                        let mut only1: Vec<&String> = e1.difference(&e2).collect();
                        let mut only2: Vec<&String> = e2.difference(&e1).collect();
                        only1.sort();
                        only2.sort();

                        if !only1.is_empty() {
                            let preview = if only1.len() > 8 {
                                &only1[..8]
                            } else {
                                &only1[..]
                            };
                            eprintln!(
                                "    committed-only entries ({}): {:?}",
                                only1.len(),
                                preview
                            );
                        }
                        if !only2.is_empty() {
                            let preview = if only2.len() > 8 {
                                &only2[..8]
                            } else {
                                &only2[..]
                            };
                            eprintln!(
                                "    regenerated-only entries ({}): {:?}",
                                only2.len(),
                                preview
                            );
                        }
                    }
                }

                has_drift = true;
                if first_error.is_none() {
                    first_error = Some(format!("Manifest drift detected: {output_file}"));
                }
            }
        } else {
            if let Some(parent) = full_output_path.parent() {
                if !parent.exists() {
                    let _ = fs::create_dir_all(parent);
                }
            }
            if let Err(e) = fs::write(&full_output_path, &generated_bytes) {
                return Err((
                    format!("Failed to write {}: {}", full_output_path.display(), e),
                    1,
                ));
            }
            if !json_format {
                println!("Generated {output_file}");
            }
        }
    }

    if check {
        if has_drift {
            return Err((
                first_error.unwrap_or_else(|| "Manifest drift detected".to_string()),
                1,
            ));
        }
        if !json_format {
            println!("[OK] AI repository and tool manifests are in sync");
        }
    }

    Ok(())
}
