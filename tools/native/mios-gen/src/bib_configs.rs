// AI-hint: Native Rust projector for BIB artifact filesystem configurations (config/artifacts/*.toml).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: usr/share/mios/mios.toml, config/artifacts/bib.toml, config/artifacts/iso.toml

use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};

const SSOT_REL: &str = "usr/share/mios/mios.toml";
const BIB_REL: &str = "config/artifacts/bib.toml";
const ISO_REL: &str = "config/artifacts/iso.toml";

const DEFAULT_RAW_SIZE: &str = "80 GiB";
const DEFAULT_ISO_SIZE: &str = "150 GiB";

/// Result of checking or rendering BIB artifact configs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BibConfigsResult {
    pub raw_size: String,
    pub iso_size: String,
    pub stale_files: Vec<String>,
    pub clean: bool,
}

/// Extract sizes from mios.toml SSOT.
pub fn extract_ssot_sizes(root: &Path) -> Result<(String, String), String> {
    let ssot_path = root.join(SSOT_REL);
    if !ssot_path.is_file() {
        return Err(format!("ERROR: {} not found", ssot_path.display()));
    }

    let content = fs::read_to_string(&ssot_path)
        .map_err(|e| format!("Failed to read {}: {}", ssot_path.display(), e))?;

    let doc: toml::Value = content
        .parse::<toml::Value>()
        .map_err(|e| format!("Failed to parse {}: {}", ssot_path.display(), e))?;

    let deploy = doc.get("deploy").and_then(|d| d.get("artifacts"));
    let raw_size = deploy
        .and_then(|d| d.get("raw"))
        .and_then(|r| r.get("size"))
        .and_then(|s| s.as_str())
        .unwrap_or(DEFAULT_RAW_SIZE)
        .to_string();

    let iso_size = deploy
        .and_then(|d| d.get("iso"))
        .and_then(|i| i.get("minsize"))
        .and_then(|s| s.as_str())
        .unwrap_or(DEFAULT_ISO_SIZE)
        .to_string();

    Ok((raw_size, iso_size))
}

/// Render the updated content for a single artifact config file.
pub fn render_artifact_config(content: &str, size: &str) -> String {
    let re = Regex::new(r#"minsize\s*=\s*"[^"]+""#).expect("valid regex");
    let replacement = format!(r#"minsize = "{}""#, size);
    re.replace(content, replacement.as_str()).to_string()
}

/// Normalize newlines to LF for clean cross-platform comparison.
fn normalize_newlines(s: &str) -> String {
    s.replace("\r\n", "\n")
}

/// Run check or write for BIB artifact configs.
pub fn run_bib_configs(root: &Path, check: bool) -> Result<BibConfigsResult, String> {
    let (raw_size, iso_size) = extract_ssot_sizes(root)?;

    let bib_path = root.join(BIB_REL);
    let iso_path = root.join(ISO_REL);

    let targets = [
        (BIB_REL, bib_path, &raw_size),
        (ISO_REL, iso_path, &iso_size),
    ];

    let mut stale_files = Vec::new();
    let mut rendered_contents: Vec<(PathBuf, String)> = Vec::new();

    for (rel_path, abs_path, target_size) in &targets {
        if !abs_path.is_file() {
            stale_files.push(format!("{} (missing)", rel_path));
            continue;
        }

        let raw_content = fs::read_to_string(abs_path)
            .map_err(|e| format!("Failed to read {}: {}", abs_path.display(), e))?;

        let current_normalized = normalize_newlines(&raw_content);
        let rendered_normalized =
            normalize_newlines(&render_artifact_config(&raw_content, target_size));

        if current_normalized != rendered_normalized {
            stale_files.push(rel_path.to_string());
        }

        rendered_contents.push((abs_path.clone(), rendered_normalized));
    }

    let is_clean = stale_files.is_empty();

    if check {
        if !is_clean {
            return Err(format!(
                "ERROR: BIB artifact configs out of sync with mios.toml [deploy.artifacts] (raw={}, iso={}): {}",
                raw_size,
                iso_size,
                stale_files.join(", ")
            ));
        }
    } else {
        // Write mode
        for (abs_path, content) in rendered_contents {
            if let Some(parent) = abs_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            fs::write(&abs_path, content.as_bytes())
                .map_err(|e| format!("Failed to write {}: {}", abs_path.display(), e))?;
        }
    }

    Ok(BibConfigsResult {
        raw_size,
        iso_size,
        stale_files,
        clean: is_clean,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_artifact_config_basic() {
        let input = "mountpoint = \"/\"\nminsize = \"80 GiB\"\n";
        let output = render_artifact_config(input, "120 GiB");
        assert_eq!(output, "mountpoint = \"/\"\nminsize = \"120 GiB\"\n");
    }

    #[test]
    fn test_render_artifact_config_spacing_normalized() {
        let input = "mountpoint = \"/\"\n  minsize   =   \"old-size\"  \n";
        let output = render_artifact_config(input, "100 GiB");
        assert_eq!(output, "mountpoint = \"/\"\n  minsize = \"100 GiB\"  \n");
    }

    #[test]
    fn test_render_artifact_config_no_match() {
        let input = "mountpoint = \"/\"\n";
        let output = render_artifact_config(input, "100 GiB");
        assert_eq!(output, input);
    }
}
