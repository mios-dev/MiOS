// AI-hint: Law-11 extension gate: fails any credential literal baked into a world-readable unit whose exact path:KEY=value is not on the shrink-only register.
// AI-related: usr/share/mios/mios.toml, usr/share/containers/systemd, usr/lib/systemd/system, tools/generate-pod-quadlets.py

use crate::Report;
use std::collections::BTreeSet;
use std::path::Path;

const CHECK: &str = "credential-literals";

/// Law 11 scans only .env files; a Quadlet is a world-readable unit under /usr
/// and carries the same hazard.
const UNIT_DIRS: [&str; 2] = ["usr/share/containers/systemd", "usr/lib/systemd/system"];

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// A credential-shaped variable name. Counters and feature flags are not
/// credentials, however they are spelled.
fn is_credential_key(key: &str) -> bool {
    let looks = key.contains("PASSWORD")
        || key.contains("SECRET")
        || key.contains("APIKEY")
        || key.contains("API_KEY")
        || key.contains("TOKEN");
    if !looks {
        return false;
    }
    let not_cred = key.contains("MAX_TOKENS")
        || key.ends_with("_TOKENS")
        || key.starts_with("ENABLE_")
        || key.ends_with("_ENABLED")
        || key.contains("NUM_")
        || key.ends_with("_LIMIT");
    !not_cred
}

/// True when the value is a real baked literal rather than an indirection.
fn is_literal(val: &str) -> bool {
    if val.is_empty() || val.starts_with("${") || val.starts_with('%') {
        return false; // indirected through an env var or a systemd specifier
    }
    let lower = val.to_ascii_lowercase();
    if lower == "true" || lower == "false" {
        return false;
    }
    !val.chars().all(|c| c.is_ascii_digit())
}

fn walk(dir: &Path, out: &mut Vec<std::path::PathBuf>) {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    let mut entries: Vec<_> = rd.flatten().map(|e| e.path()).collect();
    entries.sort();
    for p in entries {
        if p.is_dir() {
            walk(&p, out);
        } else if p.is_file() {
            out.push(p);
        }
    }
}

pub fn check(root: &Path) -> Report {
    let ssot = root.join("usr/share/mios/mios.toml");
    if !ssot.is_file() {
        return cannot_run(format!("{} is missing", ssot.display()));
    }
    let Ok(text) = std::fs::read_to_string(&ssot) else {
        return cannot_run("usr/share/mios/mios.toml could not be read");
    };
    let Ok(val) = text.parse::<toml::Value>() else {
        return cannot_run("usr/share/mios/mios.toml did not parse");
    };

    let mut files: Vec<std::path::PathBuf> = Vec::new();
    let mut present_dirs = 0usize;
    for d in UNIT_DIRS {
        let full = root.join(d);
        if full.is_dir() {
            present_dirs += 1;
            walk(&full, &mut files);
        }
    }
    // An empty scan is not a clean scan: a moved unit directory would otherwise
    // report "no credential literals" forever.
    if present_dirs == 0 || files.is_empty() {
        return cannot_run("no unit files were scanned, so nothing was compared");
    }

    let mut found: BTreeSet<String> = BTreeSet::new();
    for path in &files {
        let Ok(body) = std::fs::read_to_string(path) else {
            continue;
        };
        // Forward slashes always: a backslash spelling made every entry read as
        // NEW on one host and as removed on the other, for an identical tree.
        let rel = path
            .strip_prefix(root)
            .unwrap_or(path)
            .to_string_lossy()
            .replace('\\', "/");
        for line in body.lines() {
            let Some(rest) = line.trim().strip_prefix("Environment=") else {
                continue;
            };
            let Some((key, value)) = rest.split_once('=') else {
                continue;
            };
            if !key
                .chars()
                .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit() || c == '_')
            {
                continue;
            }
            if !is_credential_key(key) {
                continue;
            }
            let value = value.trim();
            if !is_literal(value) {
                continue;
            }
            // The register pins the VALUE, not just the key. A key-only register
            // cannot tell the shipped placeholder from an operator's real
            // password baked in by a build-environment variable.
            found.insert(format!("{rel}:{key}={value}"));
        }
    }

    let cfg = val
        .get("security")
        .and_then(|s| s.get("credential_literals"));
    let allowed: BTreeSet<String> = cfg
        .and_then(|c| c.get("grandfathered"))
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(|s| s.trim().to_string())
                .collect()
        })
        .unwrap_or_default();

    let mut findings: Vec<String> = Vec::new();
    for e in &allowed {
        if !e.contains('=') {
            findings.push(format!(
                "{e}: register entry pins no value -- write it as path:KEY=value so a changed \
                 credential is a new finding rather than a silent pass"
            ));
        }
    }
    for f in found.difference(&allowed) {
        findings.push(format!(
            "NEW credential literal baked into a world-readable unit: {f}"
        ));
    }
    for f in allowed.difference(&found) {
        if f.contains('=') {
            findings.push(format!(
                "grandfathered entry no longer present (shrink the list): {f}"
            ));
        }
    }

    let ok = findings.is_empty();
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary: format!(
            "no new unit credential literals ({} grandfathered, shrink-only, {} unit file(s) scanned)",
            found.len(),
            files.len()
        ),
        findings,
    }
}
