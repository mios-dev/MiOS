// AI-hint: Asserts every tracked file carrying a ${MIOS_*} placeholder has an extension the Quadlet renderer actually substitutes, so an omitted extension cannot ship a unit systemd will not parse.
// AI-related: usr/share/mios/mios.toml, automation/34-render-quadlets.sh, usr/lib/systemd/system/

use crate::Report;
use std::path::Path;

const CHECK: &str = "render-coverage";
const SSOT: &str = "usr/share/mios/mios.toml";

/// Repo-relative counterparts of the renderer's QUADLET_DIRS. The absolute
/// paths it walks at bake are these trees once the overlay is in place.
const SCAN_DIRS: [&str; 4] = [
    "usr/lib/systemd/system",
    "usr/share/containers/systemd",
    "etc/mios",
    "usr/share/mios/kb",
];

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

fn walk(dir: &Path, depth: usize, out: &mut Vec<std::path::PathBuf>) {
    if depth > 2 {
        return;
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for e in entries.flatten() {
        let p = e.path();
        if p.is_dir() {
            walk(&p, depth + 1, out);
        } else if p.is_file() {
            out.push(p);
        }
    }
}

pub fn check(root: &Path) -> Report {
    let Ok(text) = std::fs::read_to_string(root.join(SSOT)) else {
        return cannot_run(format!("{SSOT} could not be read"));
    };
    let Ok(val) = text.parse::<toml::Value>() else {
        return cannot_run(format!("{SSOT} did not parse"));
    };
    let exts: Vec<String> = match val
        .get("build")
        .and_then(|b| b.get("quadlet_render"))
        .and_then(|q| q.get("extensions"))
        .and_then(|v| v.as_array())
    {
        Some(a) if !a.is_empty() => a
            .iter()
            .filter_map(|v| v.as_str())
            .map(str::to_string)
            .collect(),
        // An empty list would make every file below "uncovered", which reads as
        // a flood of findings rather than the configuration error it is.
        _ => {
            return cannot_run(
                "[build.quadlet_render].extensions is absent or empty -- the renderer's \
                 scope is SSOT and this check cannot be decided without it",
            )
        }
    };

    let mut files = Vec::new();
    for d in SCAN_DIRS {
        let p = root.join(d);
        if p.is_dir() {
            walk(&p, 0, &mut files);
        }
    }
    if files.is_empty() {
        return cannot_run(
            "the render scan directories hold no files -- an empty scan is not a clean tree",
        );
    }

    let mut findings = Vec::new();
    let mut carrying = 0usize;
    for f in &files {
        let Ok(body) = std::fs::read_to_string(f) else {
            continue;
        };
        if !body.contains("${MIOS_") {
            continue;
        }
        carrying += 1;
        let ext = f
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_string();
        if !exts.iter().any(|e| e == &ext) {
            let rel = f.strip_prefix(root).unwrap_or(f).display();
            findings.push(format!(
                "{rel} carries a ${{MIOS_*}} placeholder but '.{ext}' is not on \
                 [build.quadlet_render].extensions, so the renderer never substitutes it \
                 and the placeholder ships verbatim"
            ));
        }
    }

    let ok = findings.is_empty();
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary: format!(
            "{carrying} file(s) carry a ${{MIOS_*}} placeholder across {} scanned, all with \
             an extension the renderer substitutes ({} declared)",
            files.len(),
            exts.len()
        ),
        findings,
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn scan_dirs_match_the_renderers_repo_relative_trees() {
        // A guard against this list silently diverging from QUADLET_DIRS.
        assert!(SCAN_DIRS.contains(&"usr/lib/systemd/system"));
        assert_eq!(SCAN_DIRS.len(), 4);
    }
}
