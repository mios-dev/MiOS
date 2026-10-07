// AI-hint: Synchronizes metadata in wiki and spec markdown files by injecting current version and RAG sync timestamps into JSON blocks.
// AI-related: tools/native/mios-gen/src/main.rs, usr/share/mios/mios.toml, VERSION

use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Default)]
pub struct SyncResult {
    pub scanned: usize,
    pub modified: usize,
    pub files: Vec<PathBuf>,
}

fn format_epoch_date(secs: u64) -> String {
    let days = secs / 86400;
    let z = days as i64 + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}", y, m, d)
}

pub fn get_version(root: &Path) -> String {
    let version_file = root.join("VERSION");
    if let Ok(content) = fs::read_to_string(&version_file) {
        let v = content.trim();
        if !v.is_empty() {
            return v.to_string();
        }
    }

    let toml_path = root.join("usr/share/mios/mios.toml");
    if let Ok(content) = fs::read_to_string(&toml_path) {
        if let Ok(parsed) = content.parse::<toml::Value>() {
            if let Some(v) = parsed
                .get("meta")
                .and_then(|m| m.get("mios_version"))
                .and_then(|v| v.as_str())
            {
                return v.to_string();
            }
        }
    }

    "0.3.0".to_string()
}

pub fn get_last_rag_sync(root: &Path, explicit: Option<&str>) -> String {
    if let Some(e) = explicit {
        if !e.trim().is_empty() {
            return e.trim().to_string();
        }
    }

    let rag_file = root.join("usr/share/mios/reference/manual-corpus.tsv");
    if let Ok(meta) = fs::metadata(&rag_file) {
        if let Ok(mtime) = meta.modified() {
            if let Ok(dur) = mtime.duration_since(UNIX_EPOCH) {
                return format_epoch_date(dur.as_secs());
            }
        }
    }

    if let Ok(dur) = SystemTime::now().duration_since(UNIX_EPOCH) {
        format_epoch_date(dur.as_secs())
    } else {
        "2026-10-07".to_string()
    }
}

pub fn sync_file_content(
    content: &str,
    version: &str,
    rag_sync: &str,
    explicit_rag_sync: bool,
) -> Result<(String, bool), String> {
    let mut modified = false;

    // 1. Process ```json:knowledge ... ```
    let kb_re = Regex::new(r"(?s)```json:knowledge\s*\r?\n(.*?)\r?\n```")
        .map_err(|e| format!("regex compilation failed: {e}"))?;

    let mut new_content = String::with_capacity(content.len());
    let mut last_end = 0;

    for caps in kb_re.captures_iter(content) {
        let full_match = caps.get(0).unwrap();
        new_content.push_str(&content[last_end..full_match.start()]);

        let json_str = caps.get(1).unwrap().as_str();
        let mut data: serde_json::Value = serde_json::from_str(json_str)
            .map_err(|e| format!("invalid JSON in ```json:knowledge``` block: {e}"))?;

        if let Some(obj) = data.as_object_mut() {
            // Update version
            if obj.get("version").and_then(|v| v.as_str()) != Some(version) {
                obj.insert(
                    "version".to_string(),
                    serde_json::Value::String(version.to_string()),
                );
                modified = true;
            }

            // Update last_rag_sync
            let current_sync = obj.get("last_rag_sync").and_then(|v| v.as_str());
            if (explicit_rag_sync
                || current_sync.is_none()
                || current_sync.unwrap_or("").trim().is_empty())
                && current_sync != Some(rag_sync)
            {
                obj.insert(
                    "last_rag_sync".to_string(),
                    serde_json::Value::String(rag_sync.to_string()),
                );
                modified = true;
            }
        }

        let pretty_json = serde_json::to_string_pretty(&data)
            .map_err(|e| format!("failed to serialize JSON: {e}"))?;

        new_content.push_str(&format!("```json:knowledge\n{}\n```", pretty_json));
        last_end = full_match.end();
    }
    new_content.push_str(&content[last_end..]);

    // 2. Process ```json ... ``` with { ... }
    let json_re = Regex::new(r"(?s)```json\s*\r?\n(\{.*?\})\r?\n```")
        .map_err(|e| format!("regex compilation failed: {e}"))?;

    let intermediate = new_content;
    let mut final_content = String::with_capacity(intermediate.len());
    last_end = 0;

    for caps in json_re.captures_iter(&intermediate) {
        let full_match = caps.get(0).unwrap();
        final_content.push_str(&intermediate[last_end..full_match.start()]);

        let json_str = caps.get(1).unwrap().as_str();
        if let Ok(mut data) = serde_json::from_str::<serde_json::Value>(json_str) {
            if let Some(obj) = data.as_object_mut() {
                if obj.contains_key("baseline") {
                    let expected_baseline = format!("v{}", version);
                    if obj.get("baseline").and_then(|v| v.as_str()) != Some(&expected_baseline) {
                        obj.insert(
                            "baseline".to_string(),
                            serde_json::Value::String(expected_baseline),
                        );
                        modified = true;
                    }
                }
                if obj.contains_key("last_sync")
                    && explicit_rag_sync
                    && obj.get("last_sync").and_then(|v| v.as_str()) != Some(rag_sync)
                {
                    obj.insert(
                        "last_sync".to_string(),
                        serde_json::Value::String(rag_sync.to_string()),
                    );
                    modified = true;
                }
            }
            if let Ok(pretty_json) = serde_json::to_string_pretty(&data) {
                final_content.push_str(&format!("```json\n{}\n```", pretty_json));
                last_end = full_match.end();
                continue;
            }
        }

        final_content.push_str(full_match.as_str());
        last_end = full_match.end();
    }
    final_content.push_str(&intermediate[last_end..]);

    let norm_orig = content.replace("\r\n", "\n");
    let norm_final = final_content.replace("\r\n", "\n");
    let actually_changed = norm_orig != norm_final;

    Ok((norm_final, actually_changed || modified))
}

pub fn run_sync_wiki(
    root: &Path,
    check: bool,
    explicit_rag_sync: Option<&str>,
    target_paths: &[PathBuf],
) -> Result<SyncResult, String> {
    if !root.is_dir() {
        return Err(format!("Root directory does not exist: {}", root.display()));
    }

    let version = get_version(root);
    let rag_sync = get_last_rag_sync(root, explicit_rag_sync);
    let has_explicit_rag = explicit_rag_sync.is_some();

    let files_to_check: Vec<PathBuf> = if !target_paths.is_empty() {
        target_paths
            .iter()
            .map(|p| {
                if p.is_absolute() {
                    p.clone()
                } else {
                    root.join(p)
                }
            })
            .collect()
    } else {
        let mut candidates = vec![
            root.join("specs/engineering/2026-04-26-Artifact-ENG-002-Scripts-Index.md"),
            root.join("README.md"),
            root.join("usr/share/mios/ai/INDEX.md"),
            root.join("specs/Home.md"),
        ];

        let specs_dir = root.join("specs");
        if specs_dir.is_dir() {
            for entry in walkdir::WalkDir::new(&specs_dir)
                .follow_links(false)
                .into_iter()
                .filter_map(|e| e.ok())
            {
                let p = entry.path();
                if p.is_file() && p.extension().and_then(|ext| ext.to_str()) == Some("md") {
                    let pb = p.to_path_buf();
                    if !candidates.contains(&pb) {
                        candidates.push(pb);
                    }
                }
            }
        }
        candidates
    };

    let mut result = SyncResult::default();
    let mut stale_files: Vec<String> = Vec::new();

    for path in files_to_check {
        if !path.is_file() {
            continue;
        }

        let content = match fs::read_to_string(&path) {
            Ok(c) => c,
            Err(e) => {
                return Err(format!("Failed to read file {}: {}", path.display(), e));
            }
        };

        if !content.contains("```json") {
            continue;
        }

        result.scanned += 1;
        result.files.push(path.clone());

        let (synced, changed) =
            match sync_file_content(&content, &version, &rag_sync, has_explicit_rag) {
                Ok(res) => res,
                Err(err) => {
                    return Err(format!("{}: {}", path.display(), err));
                }
            };

        if changed {
            if check {
                let rel_path = path
                    .strip_prefix(root)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .to_string();
                stale_files.push(rel_path);
            } else {
                if let Err(e) = fs::write(&path, synced.as_bytes()) {
                    return Err(format!("Failed to write {}: {}", path.display(), e));
                }
                println!("[ok] Propagated sync values to {}", path.display());
                result.modified += 1;
            }
        }
    }

    if check && !stale_files.is_empty() {
        return Err(format!(
            "Wiki documentation embeds are STALE ({} files require sync: {}). Run 'mios-gen sync-wiki' to synchronize.",
            stale_files.len(),
            stale_files.join(", ")
        ));
    }

    Ok(result)
}
