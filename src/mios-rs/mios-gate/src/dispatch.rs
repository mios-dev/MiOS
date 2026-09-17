// AI-hint: Detects bake-time tool-dispatch gates whose PATH lookup cannot resolve, against the shrink-only register in SSOT.
// AI-related: usr/share/mios/mios.toml, Containerfile, automation/98-drift-checks.sh, TASKS.md

use crate::Report;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

const CHECK: &str = "build-tool-dispatch";

/// Directories a shipped executable is reachable from without a PATH edit.
const SHIPPED_PATH_DIRS: [&str; 4] = ["usr/bin", "usr/local/bin", "usr/sbin", "usr/local/sbin"];

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

fn read(path: &Path) -> Option<String> {
    std::fs::read_to_string(path).ok()
}

pub fn check(root: &Path) -> Report {
    let containerfile = root.join("Containerfile");
    let ssot = root.join("usr/share/mios/mios.toml");
    for subject in [&containerfile, &ssot] {
        if !subject.is_file() {
            return cannot_run(format!(
                "{} is missing, so this check cannot run",
                subject.display()
            ));
        }
    }

    let Some(cf_text) = read(&containerfile) else {
        return cannot_run("the Containerfile could not be read");
    };
    let Some(ssot_text) = read(&ssot) else {
        return cannot_run("usr/share/mios/mios.toml could not be read");
    };
    let Ok(ssot_val) = ssot_text.parse::<toml::Value>() else {
        return cannot_run("usr/share/mios/mios.toml did not parse");
    };

    let reg = ssot_val.get("build").and_then(|b| b.get("tool_dispatch"));
    let Some(ceiling) = reg
        .and_then(|r| r.get("max_unreachable"))
        .and_then(|v| v.as_integer())
    else {
        return cannot_run("mios.toml is missing [build.tool_dispatch].max_unreachable");
    };
    let listed: BTreeSet<String> = reg
        .and_then(|r| r.get("unreachable"))
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();

    // Where the built binaries land, read from the Containerfile rather than
    // assumed, so moving them moves this check with them.
    let Ok(copy_re) = regex::Regex::new(r"(?m)^COPY --from=\S*builder\S*\s+\S+\s+(\S+)") else {
        return cannot_run("the builder-COPY pattern did not compile");
    };
    let install_dirs: Vec<String> = copy_re
        .captures_iter(&cf_text)
        .filter_map(|c| {
            c.get(1)
                .map(|m| m.as_str().trim_end_matches('/').to_string())
        })
        .collect();
    if install_dirs.is_empty() {
        return cannot_run(
            "no builder-stage COPY in the Containerfile, so the install directory is unknown",
        );
    }

    // Anything the build chain actually adds to PATH makes the gates live.
    let mut path_sources = vec![root.join("Containerfile"), root.join("automation/build.sh")];
    if let Ok(entries) = std::fs::read_dir(root.join("automation/lib")) {
        let mut libs: Vec<_> = entries
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|x| x == "sh"))
            .collect();
        libs.sort();
        path_sources.extend(libs);
    }
    let Ok(path_re) = regex::Regex::new(r"(?:export\s+)?PATH=([^\n]*)") else {
        return cannot_run("the PATH pattern did not compile");
    };
    let mut added = BTreeSet::new();
    for src in &path_sources {
        let Some(text) = read(src) else { continue };
        for c in path_re.captures_iter(&text) {
            let Some(rhs) = c.get(1) else { continue };
            for d in &install_dirs {
                if rhs.as_str().contains(d.as_str()) {
                    added.insert(d.clone());
                }
            }
        }
    }
    if !added.is_empty() {
        return Report {
            check: CHECK.to_string(),
            ok: false,
            could_not_run: None,
            summary: String::new(),
            findings: vec![format!(
                "{} is on PATH at bake time now -- the unreachable register is stale, \
                 re-measure and shrink it",
                added.into_iter().collect::<Vec<_>>().join(", ")
            )],
        };
    }

    let Ok(bin_re) =
        regex::Regex::new(r"command -v (miosd|mios-[a-z0-9-]+|generate-names-registry)\b")
    else {
        return cannot_run("the binary-name pattern did not compile");
    };

    let adir = root.join("automation");
    let Ok(entries) = std::fs::read_dir(&adir) else {
        return cannot_run("automation/ could not be listed, so nothing was examined");
    };
    let mut names: Vec<_> = entries
        .flatten()
        .map(|e| e.file_name().to_string_lossy().to_string())
        .filter(|n| n.ends_with(".sh"))
        .collect();
    names.sort();
    if names.is_empty() {
        return cannot_run("automation/ holds no shell stage, so nothing was examined");
    }

    let mut found: BTreeMap<String, usize> = BTreeMap::new();
    let mut sites = Vec::new();
    for name in &names {
        let rel = format!("automation/{name}");
        let Some(text) = read(&adir.join(name)) else {
            continue;
        };
        for (lineno, line) in text.lines().enumerate() {
            // A comment naming the lookup is not a dispatch gate. Mention is not
            // subject: the comment recording why a branch was REMOVED counted as
            // the branch still being there.
            if line.trim_start().starts_with('#') {
                continue;
            }
            for c in bin_re.captures_iter(line) {
                let Some(bin) = c.get(1).map(|m| m.as_str()) else {
                    continue;
                };
                if SHIPPED_PATH_DIRS
                    .iter()
                    .any(|d| root.join(d).join(bin).exists())
                {
                    continue; // reachable without a PATH edit
                }
                *found.entry(rel.clone()).or_insert(0) += 1;
                sites.push(format!(
                    "{}:{} gates the {} path on `command -v {}`, but {} ships only to {}",
                    rel,
                    lineno + 1,
                    bin,
                    bin,
                    bin,
                    install_dirs.join(", ")
                ));
            }
        }
    }

    let total = sites.len() as i64;
    let mut findings = Vec::new();
    if total > ceiling {
        findings.push(format!(
            "{total} unreachable dispatch gate(s) exceeds the ceiling of {ceiling} -- give the \
             binary a PATH location or dispatch by absolute path, do NOT raise the ceiling"
        ));
    }
    // A ceiling above the measurement is slack a later regression can hide in.
    // The ratchet only bites if the ceiling EQUALS what is actually there, so a
    // ceiling left high after a conversion is itself the violation.
    if total < ceiling {
        findings.push(format!(
            "the ceiling is {ceiling} but only {total} gate(s) are unreachable -- lower \
             max_unreachable to {total}; a ceiling above the measurement is slack"
        ));
    }
    let present: BTreeSet<String> = found.keys().cloned().collect();
    for rel in present.difference(&listed) {
        findings.push(format!(
            "{rel} has an unreachable dispatch gate and is not on the register"
        ));
    }
    for rel in listed.difference(&present) {
        findings.push(format!(
            "{rel} is on the register but has no unreachable gate -- remove it and lower \
             max_unreachable"
        ));
    }

    if findings.is_empty() {
        Report {
            check: CHECK.to_string(),
            ok: true,
            could_not_run: None,
            summary: format!(
                "{total} gate(s) unreachable, at the register ceiling of {ceiling} across {} file(s)",
                found.len()
            ),
            findings,
        }
    } else {
        findings.extend(sites.into_iter().map(|s| format!("  {s}")));
        Report {
            check: CHECK.to_string(),
            ok: false,
            could_not_run: None,
            summary: String::new(),
            findings,
        }
    }
}
