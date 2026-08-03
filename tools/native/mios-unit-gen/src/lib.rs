//! MiOS Systemd Unit Generator & Golden Master Deviance Oracle.

use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UnitGenError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("TOML parse error: {0}")]
    Toml(#[from] toml::de::Error),
    #[error("Golden master verification error: {0}")]
    GoldenMaster(String),
}

#[derive(Deserialize, Debug, Clone)]
pub struct SsotRoot {
    pub security: Option<SecurityTable>,
    pub units: Option<BTreeMap<String, toml::Value>>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct SecurityTable {
    pub privileged_units: Option<PrivilegedUnitsRoster>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct PrivilegedUnitsRoster {
    pub unconfined: Option<Vec<String>>,
}

/// Render units from SSOT TOML string. Returns map of relative path -> rendered content.
pub fn render_units(ssot_toml: &str) -> Result<BTreeMap<String, String>, UnitGenError> {
    let root: SsotRoot = toml::from_str(ssot_toml)?;
    let mut rendered = BTreeMap::new();

    let unconfined_units: Vec<String> = root
        .security
        .as_ref()
        .and_then(|s| s.privileged_units.as_ref())
        .and_then(|p| p.unconfined.clone())
        .unwrap_or_default();

    if let Some(units) = root.units {
        for (filename, val) in units {
            if let Some(sections) = val.as_table() {
                let mut out = String::new();
                if let Some(comment_val) = sections.get("comment").and_then(|v| v.as_str()) {
                    out.push_str(comment_val);
                    if !comment_val.ends_with('\n') {
                        out.push('\n');
                    }
                }
                for (sec_name, sec_kv) in sections {
                    if sec_name == "comment" {
                        continue;
                    }
                    if let Some(table) = sec_kv.as_table() {
                        out.push_str(&format!("[{}]\n", sec_name));
                        let is_service = sec_name == "Service";
                        let is_unconfined = unconfined_units.contains(&filename);

                        let mut existing_keys = BTreeMap::new();
                        for (k, v) in table {
                            existing_keys.insert(k.as_str(), v);
                            match v {
                                toml::Value::String(s) => {
                                    out.push_str(&format!("{}={}\n", k, s));
                                }
                                toml::Value::Array(arr) => {
                                    for item in arr {
                                        if let Some(s) = item.as_str() {
                                            out.push_str(&format!("{}={}\n", k, s));
                                        }
                                    }
                                }
                                toml::Value::Boolean(b) => {
                                    out.push_str(&format!("{}={}\n", k, b));
                                }
                                toml::Value::Integer(i) => {
                                    out.push_str(&format!("{}={}\n", k, i));
                                }
                                _ => {}
                            }
                        }

                        // Apply hardening baseline for long-running / standard Services if not unconfined & not overridden
                        if is_service && !is_unconfined {
                            if !existing_keys.contains_key("NoNewPrivileges") {
                                out.push_str("NoNewPrivileges=yes\n");
                            }
                            if !existing_keys.contains_key("ProtectSystem") {
                                out.push_str("ProtectSystem=strict\n");
                            }
                            if !existing_keys.contains_key("ProtectHome") {
                                out.push_str("ProtectHome=yes\n");
                            }
                            if !existing_keys.contains_key("PrivateTmp") {
                                out.push_str("PrivateTmp=yes\n");
                            }
                            if !existing_keys.contains_key("SystemCallFilter") {
                                out.push_str("SystemCallFilter=@system-service\n");
                            }
                        }
                    }
                }
                if !out.is_empty() {
                    rendered.insert(filename, out);
                }
            }
        }
    }

    Ok(rendered)
}

/// Verify that every file under `golden_dir` matches `systemd_dir` byte-for-byte.
pub fn verify_golden_master(systemd_dir: &Path, golden_dir: &Path) -> Result<(), String> {
    if !systemd_dir.exists() {
        return Err(format!(
            "Systemd directory does not exist: {}",
            systemd_dir.display()
        ));
    }
    if !golden_dir.exists() {
        return Err(format!(
            "Golden directory does not exist: {}",
            golden_dir.display()
        ));
    }

    let mut mismatches = Vec::new();
    let mut checked_count = 0;

    fn walk_dir(
        base: &Path,
        current: &Path,
        golden_base: &Path,
        mismatches: &mut Vec<String>,
        count: &mut usize,
    ) {
        if let Ok(entries) = fs::read_dir(current) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    walk_dir(base, &path, golden_base, mismatches, count);
                } else if path.is_file() {
                    *count += 1;
                    if let Ok(rel) = path.strip_prefix(base) {
                        let golden_path = golden_base.join(rel);
                        if !golden_path.exists() {
                            mismatches
                                .push(format!("Missing golden snapshot for {}", rel.display()));
                            continue;
                        }
                        let actual_bytes = fs::read(&path).unwrap_or_default();
                        let golden_bytes = fs::read(&golden_path).unwrap_or_default();
                        if actual_bytes != golden_bytes {
                            mismatches
                                .push(format!("Mismatch in golden snapshot for {}", rel.display()));
                        }
                    }
                }
            }
        }
    }

    walk_dir(
        systemd_dir,
        systemd_dir,
        golden_dir,
        &mut mismatches,
        &mut checked_count,
    );

    if !mismatches.is_empty() {
        return Err(format!(
            "Golden master verification failed with {} errors:\n{}",
            mismatches.len(),
            mismatches.join("\n")
        ));
    }

    if checked_count == 0 {
        return Err("No files were checked during golden master verification".to_string());
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_units_default_sandbox() {
        let toml_str = r#"
[units."sample.service".Service]
Type = "simple"
ExecStart = "/usr/bin/sample"
"#;
        let rendered = render_units(toml_str).unwrap();
        let sample = rendered.get("sample.service").unwrap();
        assert!(sample.contains("NoNewPrivileges=yes"));
        assert!(sample.contains("ProtectSystem=strict"));
        assert!(sample.contains("ProtectHome=yes"));
        assert!(sample.contains("PrivateTmp=yes"));
        assert!(sample.contains("SystemCallFilter=@system-service"));
    }

    #[test]
    fn test_render_units_privileged_override() {
        let toml_str = r#"
[security.privileged_units]
unconfined = ["sample.service"]

[units."sample.service".Service]
Type = "simple"
ExecStart = "/usr/bin/sample"
"#;
        let rendered = render_units(toml_str).unwrap();
        let sample = rendered.get("sample.service").unwrap();
        assert!(!sample.contains("NoNewPrivileges=yes"));
        assert!(!sample.contains("ProtectSystem=strict"));
    }
}
