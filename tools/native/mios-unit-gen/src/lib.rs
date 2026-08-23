// AI-hint: Systemd unit generator library projecting units from mios.toml SSOT.
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
                        // Blank line before each header, above the comment
                        // block: the tree separates sections 208:16 and glues
                        // comment-to-header 94:23.
                        if !out.is_empty() && !out.ends_with("\n\n") {
                            out.push('\n');
                        }
                        // A section's `comment` is the block ABOVE its header;
                        // the SSOT nests it, so a top-level-only hoist emitted a
                        // bogus `comment=` key.
                        if let Some(c) = table.get("comment").and_then(|v| v.as_str()) {
                            out.push_str(c);
                            if !c.ends_with('\n') {
                                out.push('\n');
                            }
                        }
                        out.push_str(&format!("[{}]\n", sec_name));
                        let is_service = sec_name == "Service";
                        let is_unconfined = unconfined_units.contains(&filename);

                        let mut existing_keys = BTreeMap::new();
                        for (k, v) in table {
                            if k == "comment" {
                                continue;
                            }
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
                                    // systemd's own spelling; `true`/`false`
                                    // parse but are not what the tree ships.
                                    out.push_str(&format!(
                                        "{}={}\n",
                                        k,
                                        if *b { "yes" } else { "no" }
                                    ));
                                }
                                toml::Value::Integer(i) => {
                                    out.push_str(&format!("{}={}\n", k, i));
                                }
                                _ => {}
                            }
                        }

                        // No hardening baseline is injected: a generator that
                        // adds undeclared directives is not a projection.
                        // See TASKS.md T-317.
                        let _ = (is_service, is_unconfined, &existing_keys);
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

/// Compare unit bodies on content, not on byte-exactness: line endings differ
/// between a Windows checkout and the Linux build, and a trailing newline is
/// not drift. Anything else is.
pub fn normalize(s: &str) -> String {
    let mut out: Vec<&str> = s.lines().map(|l| l.trim_end()).collect();
    while out.last().is_some_and(|l| l.is_empty()) {
        out.pop();
    }
    out.join("\n")
}

/// What `[units.*]` projects onto `usr/lib/systemd/system`, in four buckets.
#[derive(Debug, Default, Clone)]
pub struct Projection {
    /// Declared in `[units.*]` and rendering byte-equal (after `normalize`).
    pub faithful: Vec<String>,
    /// Declared in `[units.*]` but rendering something else than the file.
    pub drifted: Vec<String>,
    /// Declared in `[units.*]` with no file on disk at all.
    pub missing: Vec<String>,
    /// Shipped units the SSOT does not describe -- outside the projection.
    pub undeclared: Vec<String>,
}

const UNIT_SUFFIXES: [&str; 7] = [
    ".service", ".target", ".timer", ".path", ".socket", ".mount", ".slice",
];

/// The shrink-only drift register: `[unit_projection].drift` in the SSOT.
///
/// It exists because `[units.*]` describes 68 of the tree's units and most of
/// those descriptions are stale. The register makes that debt COUNTED rather
/// than absent, so the projection can be gated today and drained unit by unit.
pub fn drift_register(ssot_toml: &str) -> Result<Vec<String>, UnitGenError> {
    let root: toml::Value = toml::from_str(ssot_toml)?;
    Ok(root
        .get("unit_projection")
        .and_then(|t| t.get("drift"))
        .and_then(|d| d.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_string())
                .collect()
        })
        .unwrap_or_default())
}

fn shipped_units(unit_dir: &Path) -> Vec<String> {
    let mut out = Vec::new();
    if let Ok(entries) = fs::read_dir(unit_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if !path.is_file() {
                continue;
            }
            if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                if UNIT_SUFFIXES.iter().any(|sfx| name.ends_with(sfx)) {
                    out.push(name.to_string());
                }
            }
        }
    }
    out.sort();
    out
}

/// Render `[units.*]` from the SSOT at `root` and compare it to the shipped tree.
pub fn project(root: &Path) -> Result<Projection, UnitGenError> {
    let ssot = fs::read_to_string(root.join("usr/share/mios/mios.toml"))?;
    let rendered = render_units(&ssot)?;
    let unit_dir = root.join("usr/lib/systemd/system");

    let mut p = Projection::default();
    for (filename, body) in &rendered {
        match fs::read_to_string(unit_dir.join(filename)) {
            Err(_) => p.missing.push(filename.clone()),
            Ok(actual) => {
                if normalize(&actual) == normalize(body) {
                    p.faithful.push(filename.clone());
                } else {
                    p.drifted.push(filename.clone());
                }
            }
        }
    }
    for name in shipped_units(&unit_dir) {
        if !rendered.contains_key(&name) {
            p.undeclared.push(name);
        }
    }
    Ok(p)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The renderer is a PROJECTION: only what `[units.*]` declares comes
    /// out. It used to inject a hardening baseline. See TASKS.md T-317.
    #[test]
    fn test_render_invents_no_directives() {
        let toml_str = r#"
[units."sample.service".Service]
Type = "simple"
ExecStart = "/usr/bin/sample"
"#;
        let rendered = render_units(toml_str).unwrap();
        let sample = rendered.get("sample.service").unwrap();
        assert_eq!(
            sample,
            "[Service]\nType=simple\nExecStart=/usr/bin/sample\n"
        );
        for invented in [
            "NoNewPrivileges",
            "ProtectSystem",
            "ProtectHome",
            "PrivateTmp",
            "SystemCallFilter",
        ] {
            assert!(
                !sample.contains(invented),
                "renderer invented {invented}, which the SSOT never declared"
            );
        }
    }

    /// Being on the unconfined roster must not change the output either: with
    /// no injection there is nothing left for the roster to suppress.
    #[test]
    fn test_unconfined_roster_changes_nothing() {
        let body = r#"
[units."sample.service".Service]
Type = "simple"
ExecStart = "/usr/bin/sample"
"#;
        let with_roster =
            format!("[security.privileged_units]\nunconfined = [\"sample.service\"]\n{body}");
        assert_eq!(
            render_units(body).unwrap().get("sample.service"),
            render_units(&with_roster).unwrap().get("sample.service")
        );
    }

    /// A section's `comment` is the block ABOVE its header -- for the first
    /// section that is the file's AI-hint. Hoisting only a top-level `comment`
    /// emitted a literal `comment=` line, which is not a systemd key at all.
    #[test]
    fn test_section_comment_is_hoisted_above_the_header() {
        let toml_str = r##"
[units."sample.service".Unit]
comment = "# AI-hint: sample\n"
Description = "sample"

[units."sample.service".Service]
ExecStart = "/usr/bin/sample"
"##;
        let out = render_units(toml_str).unwrap();
        let sample = out.get("sample.service").unwrap();
        assert_eq!(
            sample,
            "# AI-hint: sample\n[Unit]\nDescription=sample\n\n[Service]\nExecStart=/usr/bin/sample\n"
        );
        assert!(
            !sample.contains("comment="),
            "comment leaked as a directive"
        );
    }

    /// systemd's own spelling. `true`/`false` parse, but they are not what the
    /// tree ships, so a bool rendered that way is drift on every boolean key.
    #[test]
    fn test_booleans_render_as_yes_no() {
        let toml_str = r#"
[units."sample.service".Service]
RemainAfterExit = true
PrivateTmp = false
"#;
        let out = render_units(toml_str).unwrap();
        assert_eq!(
            out.get("sample.service").unwrap(),
            "[Service]\nRemainAfterExit=yes\nPrivateTmp=no\n"
        );
    }

    /// systemd repeats a key rather than joining values, so an array is N lines.
    #[test]
    fn test_arrays_repeat_the_key() {
        let toml_str = r#"
[units."sample.service".Service]
ExecStartPre = ["/usr/bin/a", "/usr/bin/b"]
"#;
        let out = render_units(toml_str).unwrap();
        assert_eq!(
            out.get("sample.service").unwrap(),
            "[Service]\nExecStartPre=/usr/bin/a\nExecStartPre=/usr/bin/b\n"
        );
    }

    /// `normalize` must forgive line endings and a trailing newline, and NOTHING
    /// else -- an interior blank line is real drift.
    #[test]
    fn test_normalize_forgives_only_eol_and_trailing_blanks() {
        assert_eq!(normalize("[Unit]\r\nX=1\r\n"), normalize("[Unit]\nX=1"));
        assert_eq!(normalize("[Unit]\nX=1\n\n\n"), normalize("[Unit]\nX=1"));
        assert_ne!(normalize("[Unit]\n\nX=1"), normalize("[Unit]\nX=1"));
    }

    #[test]
    fn test_drift_register_reads_the_ssot_table() {
        let toml_str = r#"
[unit_projection]
drift = ["a.service", "b.timer"]
"#;
        assert_eq!(
            drift_register(toml_str).unwrap(),
            vec!["a.service".to_string(), "b.timer".to_string()]
        );
        assert!(drift_register("").unwrap().is_empty());
    }
}
