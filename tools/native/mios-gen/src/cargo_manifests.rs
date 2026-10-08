// AI-hint: Native Rust projector for tools/native/Cargo.toml workspace manifest (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/Cargo.toml, usr/share/mios/mios.toml, tools/sync-generated.sh

use std::fs;
use std::path::Path;

const SSOT_REL: &str = "usr/share/mios/mios.toml";
const VERSION_REL: &str = "VERSION";
const NATIVE_REL: &str = "tools/native";
const CARGO_TOML_REL: &str = "tools/native/Cargo.toml";

const DEFAULT_VERSION: &str = "0.3.0";

/// Result of checking or projecting cargo manifests.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CargoManifestResult {
    pub members_count: usize,
    pub version: String,
    pub clean: bool,
}

/// Extract SSOT version from mios.toml or VERSION file.
pub fn get_ssot_version(root: &Path) -> String {
    let ssot_path = root.join(SSOT_REL);
    if ssot_path.is_file() {
        if let Ok(content) = fs::read_to_string(&ssot_path) {
            if let Ok(doc) = content.parse::<toml::Value>() {
                if let Some(v) = doc
                    .get("meta")
                    .and_then(|m| m.get("mios_version"))
                    .and_then(|s| s.as_str())
                {
                    return v.to_string();
                }
            }
        }
    }

    let version_path = root.join(VERSION_REL);
    if version_path.is_file() {
        if let Ok(content) = fs::read_to_string(&version_path) {
            let trimmed = content.trim();
            if !trimmed.is_empty() {
                return trimmed.to_string();
            }
        }
    }

    DEFAULT_VERSION.to_string()
}

/// Enumerate all crate member directories under tools/native holding a Cargo.toml.
pub fn enumerate_members(native_dir: &Path) -> Result<Vec<String>, String> {
    if !native_dir.is_dir() {
        return Ok(Vec::new());
    }

    let entries = fs::read_dir(native_dir)
        .map_err(|e| format!("Failed to read {}: {}", native_dir.display(), e))?;

    let mut members = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() && path.join("Cargo.toml").is_file() {
            if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                members.push(name.to_string());
            }
        }
    }

    members.sort();
    Ok(members)
}

/// Render the complete tools/native/Cargo.toml content.
pub fn render_cargo_manifest(members: &[String], version: &str) -> String {
    let mut listed = String::new();
    for m in members {
        listed.push_str(&format!("    \"{}\",\n", m));
    }

    format!(
        "# AI-hint: Generated from mios.toml SSOT by mios-gen cargo-manifests. DO NOT EDIT DIRECTLY.\n\
        [workspace]\n\
        members = [\n\
        {}\
        ]\n\
        resolver = \"2\"\n\
        \n\
        [workspace.package]\n\
        version = \"{}\"\n\
        edition = \"2021\"\n\
        \n\
        [workspace.dependencies]\n\
        clap = {{ version = \"4.5\", features = [\"derive\"] }}\n\
        figment = {{ version = \"0.10\", features = [\"toml\", \"env\"] }}\n\
        flate2 = \"1.0\"\n\
        miette = {{ version = \"5.10\", features = [\"fancy\"] }}\n\
        regex = \"1.10\"\n\
        serde = {{ version = \"1.0\", features = [\"derive\"] }}\n\
        serde_json = \"1.0\"\n\
        sha2 = \"0.10\"\n\
        tempfile = \"3.10\"\n\
        thiserror = \"1.0\"\n\
        toml = \"0.8\"\n\
        toml_edit = \"0.20\"\n\
        walkdir = \"2.4\"\n\
        \n\
        # Size-optimized release for the Windows wallpaper daemon (its profile\n\
        # previously sat in the member manifest, where cargo silently ignored\n\
        # it). lto/strip/panic are workspace-level profile knobs cargo cannot\n\
        # set per package.\n\
        [profile.release.package.mios-wallpaperd]\n\
        opt-level = \"z\"\n\
        codegen-units = 1\n",
        listed, version
    )
}

/// Normalize newlines to LF for clean cross-platform comparison.
fn normalize_newlines(s: &str) -> String {
    s.replace("\r\n", "\n")
}

/// Run check or projection for tools/native/Cargo.toml.
pub fn run_cargo_manifests(root: &Path, check: bool) -> Result<CargoManifestResult, String> {
    let native_dir = root.join(NATIVE_REL);
    let cargo_toml_path = root.join(CARGO_TOML_REL);

    let members = enumerate_members(&native_dir)?;
    if members.is_empty() {
        return Err(format!(
            "[generate-cargo-manifests] FAIL: no crate directory under {}, so the projection would empty the workspace",
            native_dir.display()
        ));
    }

    let version = get_ssot_version(root);
    let projected_content = render_cargo_manifest(&members, &version);

    if check {
        if !cargo_toml_path.is_file() {
            return Err(format!(
                "[generate-cargo-manifests] FAIL: cannot read {} (file not found)",
                cargo_toml_path.display()
            ));
        }

        let committed_content = fs::read_to_string(&cargo_toml_path).map_err(|e| {
            format!(
                "[generate-cargo-manifests] FAIL: cannot read {} ({})",
                cargo_toml_path.display(),
                e
            )
        })?;

        if normalize_newlines(&committed_content) != normalize_newlines(&projected_content) {
            return Err(
                "[generate-cargo-manifests] FAIL: tools/native/Cargo.toml differs from its projection".to_string()
            );
        }

        Ok(CargoManifestResult {
            members_count: members.len(),
            version,
            clean: true,
        })
    } else {
        // Write mode
        fs::write(&cargo_toml_path, projected_content.as_bytes())
            .map_err(|e| format!("Failed to write {}: {}", cargo_toml_path.display(), e))?;

        Ok(CargoManifestResult {
            members_count: members.len(),
            version,
            clean: true,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_render_cargo_manifest_format() {
        let members = vec!["crate-a".to_string(), "crate-b".to_string()];
        let rendered = render_cargo_manifest(&members, "0.3.0");
        assert!(rendered.contains("    \"crate-a\",\n"));
        assert!(rendered.contains("    \"crate-b\",\n"));
        assert!(rendered.contains("version = \"0.3.0\"\n"));
        assert!(rendered.contains("resolver = \"2\"\n"));
    }

    #[test]
    fn test_normalize_newlines() {
        assert_eq!(normalize_newlines("a\r\nb\r\nc"), "a\nb\nc");
    }
}
