// AI-hint: Generator and validator for usr/share/mios/reference/pipeline-index.tsv from automation/[0-9][0-9]-*.sh and SSOT.
// AI-related: usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md, tools/native/mios-gen/src/main.rs

use regex::Regex;
use std::collections::HashSet;
use std::fs;
use std::path::Path;

pub fn run_pipeline_index(root: &Path, check_mode: bool) -> Result<(), (String, i32)> {
    let automation_dir = root.join("automation");
    let ssot_path = root.join("usr/share/mios/mios.toml");

    let mut nn_min = 0i64;
    let mut nn_max = 99i64;
    let mut prefix_unique = true;
    let mut output_rel = "usr/share/mios/reference/pipeline-index.tsv".to_string();

    if ssot_path.is_file() {
        if let Ok(toml_bytes) = fs::read(&ssot_path) {
            if let Ok(toml_str) = std::str::from_utf8(&toml_bytes) {
                if let Ok(val) = toml::from_str::<toml::Value>(toml_str) {
                    if let Some(pipe) = val.get("pipeline").and_then(|p| p.as_table()) {
                        if let Some(space) = pipe.get("space").and_then(|s| s.as_table()) {
                            if let Some(min_val) = space.get("min").and_then(|m| m.as_integer()) {
                                nn_min = min_val;
                            }
                            if let Some(max_val) = space.get("max").and_then(|m| m.as_integer()) {
                                nn_max = max_val;
                            }
                        }
                        if let Some(inv) = pipe.get("invariants").and_then(|i| i.as_table()) {
                            if let Some(pu) = inv.get("prefix_unique").and_then(|p| p.as_bool()) {
                                prefix_unique = pu;
                            }
                        }
                        if let Some(map_str) = pipe.get("map").and_then(|m| m.as_str()) {
                            output_rel = map_str.to_string();
                        }
                    }
                }
            }
        }
    }

    let output_path = root.join(&output_rel);

    if !automation_dir.is_dir() {
        return Err((format!("ERROR: {} not found", automation_dir.display()), 1));
    }

    let mut script_paths = Vec::new();
    let entries = fs::read_dir(&automation_dir).map_err(|e| {
        (
            format!("Failed to read {}: {e}", automation_dir.display()),
            1,
        )
    })?;
    let file_re = Regex::new(r"^([0-9]{2})-(.+)\.sh$").unwrap();

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file() {
            if let Some(fname) = path.file_name().and_then(|f| f.to_str()) {
                if file_re.is_match(fname) {
                    script_paths.push(path);
                }
            }
        }
    }
    script_paths.sort();

    let mut rows = Vec::new();
    let mut seen_nns = HashSet::new();

    for script_path in script_paths {
        let basename = script_path.file_name().unwrap().to_str().unwrap();
        let caps = file_re.captures(basename).unwrap();
        let nn_str = caps.get(1).unwrap().as_str();
        let name = caps.get(2).unwrap().as_str();

        let Ok(nn) = nn_str.parse::<i64>() else {
            continue;
        };

        if nn < nn_min || nn > nn_max {
            return Err((
                format!(
                    "ERROR: {basename} prefix {nn_str} is outside the declared [pipeline].space {nn_min}..{nn_max}"
                ),
                1,
            ));
        }

        if prefix_unique && !seen_nns.insert(nn_str.to_string()) {
            return Err((
                format!("ERROR: Duplicate NN prefix found: {nn_str} in {basename}"),
                1,
            ));
        }

        let mut oneline = String::new();
        if let Ok(content) = fs::read_to_string(&script_path) {
            for line in content.lines() {
                let trimmed = line.trim();
                if trimmed.starts_with("# AI-hint:") || trimmed.starts_with("# AI-related:") {
                    continue;
                }
                if trimmed.starts_with('#') && !trimmed.starts_with("#!") {
                    let text = trimmed.trim_start_matches('#').trim();
                    if !text.is_empty() && !text.starts_with("---") && !text.starts_with("Usage:") {
                        oneline = text.to_string();
                        break;
                    }
                }
            }
        }

        if oneline.is_empty() {
            oneline = name.replace('-', " ");
        }

        let rel_path = script_path
            .strip_prefix(root)
            .map(|p| p.to_string_lossy().replace('\\', "/"))
            .unwrap_or_else(|_| script_path.to_string_lossy().replace('\\', "/"));

        rows.push(format!("{nn_str}\tscript\t{name}\t{rel_path}\t{oneline}"));
    }

    let tsv_content = format!("# NN\tkind\tname\tfile\toneline\n{}\n", rows.join("\n"));

    if check_mode {
        if !output_path.is_file() {
            return Err((
                format!("ERROR: {} does not exist", output_path.display()),
                1,
            ));
        }
        let existing = fs::read_to_string(&output_path)
            .map_err(|e| (format!("Failed to read {}: {e}", output_path.display()), 1))?;
        if existing.replace("\r\n", "\n") != tsv_content.replace("\r\n", "\n") {
            return Err((
                "ERROR: pipeline-index.tsv is out of sync with automation scripts. Run mios-gen pipeline-index to regenerate."
                    .to_string(),
                1,
            ));
        }
        println!("PASS: pipeline-index.tsv is in sync.");
        return Ok(());
    }

    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent).map_err(|e| {
            (
                format!("Failed to create directory {}: {e}", parent.display()),
                1,
            )
        })?;
    }
    let tmp_path = output_path.with_extension("tmp");
    fs::write(&tmp_path, tsv_content.as_bytes())
        .map_err(|e| (format!("Failed to write {}: {e}", tmp_path.display()), 1))?;
    fs::rename(&tmp_path, &output_path).map_err(|e| {
        (
            format!("Failed to replace {}: {e}", output_path.display()),
            1,
        )
    })?;

    println!(
        "Generated {} with {} pipeline stages.",
        output_path.display(),
        rows.len()
    );
    Ok(())
}
