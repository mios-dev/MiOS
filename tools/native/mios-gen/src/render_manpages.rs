// AI-hint: Native Rust implementation of render-manpages SSOT projector (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: usr/share/mios/mios.toml, tools/native/mios-gen/src/render_manpages.rs, automation/98-drift-checks.sh

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;
#[cfg(unix)]
use std::process::Command;
use toml::Value;

const MAN: &str = "usr/share/man";
const DASH: &str = "\\-";

pub fn roff(text: &str) -> String {
    let mut out = Vec::new();
    for raw_line in text.split('\n') {
        let mut line = raw_line.replace('\\', "\\e");
        if line.starts_with('.') || line.starts_with('\'') {
            line = format!("\\&{line}");
        }
        let chars: Vec<char> = line.chars().collect();
        let mut buf = String::with_capacity(chars.len() + 8);
        for i in 0..chars.len() {
            if chars[i] == '-' {
                let prev_not_bs_or_w = if i == 0 {
                    true
                } else {
                    chars[i - 1] != '\\' && chars[i - 1] != 'w'
                };
                let next_is_word = if i + 1 < chars.len() {
                    chars[i + 1].is_ascii_alphanumeric() || chars[i + 1] == '_'
                } else {
                    false
                };
                if prev_not_bs_or_w && next_is_word {
                    buf.push('\\');
                    buf.push('-');
                    continue;
                }
            }
            buf.push(chars[i]);
        }
        out.push(buf);
    }
    out.join("\n")
}

fn th(name: &str, section: &str, version: &str, title: &str) -> String {
    format!(
        ".TH {} {} \"\" \"MiOS {}\" \"{}\"\n",
        roff(&name.to_uppercase()),
        section,
        roff(version),
        roff(title)
    )
}

fn version_of(root: &Path) -> String {
    let version_file = root.join("VERSION");
    if let Ok(raw) = fs::read_to_string(&version_file) {
        let cleaned: String = raw.chars().filter(|c| !c.is_whitespace()).collect();
        let stripped = cleaned.trim_start_matches(['v', 'V']);
        if !stripped.is_empty() {
            return stripped.to_string();
        }
    }
    "0.0.0".to_string()
}

fn prose(path: &Path, limit: usize) -> Vec<String> {
    let Ok(text) = fs::read_to_string(path) else {
        return Vec::new();
    };
    let mut paras = Vec::new();
    let mut buf: Vec<&str> = Vec::new();

    for line in text.split('\n') {
        let s = line.trim();
        if s.is_empty() || s.starts_with('#') || s.starts_with("<!--") {
            if !buf.is_empty() {
                paras.push(buf.join(" "));
                buf.clear();
            }
            continue;
        }
        buf.push(s);
    }
    if !buf.is_empty() {
        paras.push(buf.join(" "));
    }

    if paras.len() > limit {
        paras.truncate(limit);
    }
    paras
}

pub fn render_pages(root: &Path, ssot: &Value) -> BTreeMap<String, String> {
    let v = version_of(root);
    let mut out = BTreeMap::new();
    let empty_table = toml::value::Table::new();

    let verbs_table = ssot
        .get("verbs")
        .and_then(|v| v.as_table())
        .unwrap_or(&empty_table);

    let mut names: Vec<&str> = verbs_table.keys().map(|k| k.as_str()).collect();
    names.sort_unstable();

    // 1. usr/share/man/man1/mios.1
    let mut idx = vec![
        th("mios", "1", &v, "MiOS Manual"),
        format!(".SH NAME\nmios {DASH} the MiOS verb dispatcher\n"),
        ".SH SYNOPSIS\n.B mios\n.I verb\n".to_string(),
        ".SH DESCRIPTION\n".to_string(),
        format!(
            "MiOS exposes its capabilities as verbs. Every verb below is declared\nin the single source of truth and has its own page: run\n.B man mios{DASH}verb\nfor any of them.\n"
        ),
        ".SH VERBS\n".to_string(),
    ];

    for &n in &names {
        let desc = verbs_table
            .get(n)
            .and_then(|spec| spec.get("description"))
            .and_then(|d| d.as_str())
            .unwrap_or("")
            .trim();
        let fallback_desc = if desc.is_empty() {
            "(no description)"
        } else {
            desc
        };
        idx.push(format!(".TP\n.B {}\n{}\n", roff(n), roff(fallback_desc)));
    }

    idx.push(
        ".SH FILES\n.TP\n.I /usr/share/mios/mios.toml\nThe single source of truth.\n.TP\n.I /usr/share/doc/mios/manual/\nThe distilled prose manual.\n".to_string(),
    );
    idx.push(".SH SEE ALSO\n.BR mios.toml (5),\n.BR mios (7)\n".to_string());
    out.insert(format!("{MAN}/man1/mios.1"), idx.concat());

    // 2. usr/share/man/man1/mios-<n>.1
    for &n in &names {
        let spec = verbs_table.get(n).and_then(|s| s.as_table());
        let desc = spec
            .and_then(|s| s.get("description"))
            .and_then(|d| d.as_str())
            .unwrap_or("")
            .trim();
        let d = if desc.is_empty() {
            "A MiOS verb."
        } else {
            desc
        };

        let d_trimmed_dot = d.trim_end_matches('.');
        let mut body = vec![
            th(&format!("mios-{n}"), "1", &v, "MiOS Verbs"),
            format!(
                ".SH NAME\nmios{DASH}{} {DASH} {}\n",
                roff(n),
                roff(d_trimmed_dot)
            ),
            format!(".SH SYNOPSIS\n.B mios {}\n", roff(n)),
            format!(".SH DESCRIPTION\n{}\n", roff(d)),
        ];

        let surface = spec
            .and_then(|s| s.get("surface"))
            .and_then(|s| s.as_str())
            .unwrap_or("")
            .trim();
        if !surface.is_empty() {
            body.push(format!(
                ".SH SURFACE\nThis verb runs on the\n.B {}\nsurface.\n",
                roff(surface)
            ));
        }

        body.push(
            ".SH FILES\n.TP\n.I /usr/share/mios/mios.toml\nDeclares this verb and the description shown above.\n".to_string(),
        );
        body.push(".SH SEE ALSO\n.BR mios (1),\n.BR mios.toml (5),\n.BR mios (7)\n".to_string());
        out.insert(format!("{MAN}/man1/mios-{n}.1"), body.concat());
    }

    // 3. usr/share/man/man5/mios.toml.5
    let mut cfg = vec![
        th("mios.toml", "5", &v, "MiOS Configuration"),
        format!(".SH NAME\nmios.toml {DASH} the MiOS single source of truth\n"),
        ".SH DESCRIPTION\nEvery MiOS surface is projected from this file: units, ports, themes,\ncontainer definitions, verbs and the installers. Editing a\nprojection by hand is undone by the next build; edit the table\nhere instead.\n.SH SECTIONS\n".to_string(),
    ];

    if let Some(ssot_table) = ssot.as_table() {
        let mut section_keys: Vec<&str> = ssot_table.keys().map(|k| k.as_str()).collect();
        section_keys.sort_unstable();
        for key in section_keys {
            let val = &ssot_table[key];
            let kind = if let Some(t) = val.as_table() {
                format!("table with {} key(s)", t.len())
            } else if let Some(a) = val.as_array() {
                format!("array of {} entry(ies)", a.len())
            } else {
                "scalar".to_string()
            };
            cfg.push(format!(".TP\n.B [{}]\n{}\n", roff(key), roff(&kind)));
        }
    }

    cfg.push(
        ".SH FILES\n.TP\n.I /usr/share/mios/mios.toml\nThe vendor copy that ships in the image.\n.TP\n.I /etc/mios/mios.toml\nHost overrides, layered over the vendor copy.\n".to_string(),
    );
    cfg.push(".SH SEE ALSO\n.BR mios (1),\n.BR mios (7)\n".to_string());
    out.insert(format!("{MAN}/man5/mios.toml.5"), cfg.concat());

    // 4. usr/share/man/man7/mios.7
    let mut con = vec![
        th("mios", "7", &v, "MiOS Concepts"),
        format!(".SH NAME\nmios {DASH} what MiOS is and how its pieces relate\n"),
        ".SH DESCRIPTION\n".to_string(),
    ];
    let ch01_path = root
        .join("usr/share/doc/mios/manual")
        .join("ch01-introduction-and-core-concepts.md");
    let mut ps = prose(&ch01_path, 14);
    if ps.is_empty() {
        ps.push("The distilled manual is installed under /usr/share/doc/mios/manual/.".to_string());
    }
    for p in ps {
        con.push(format!(".PP\n{}\n", roff(&p)));
    }
    con.push(
        ".SH FILES\n.TP\n.I /usr/share/doc/mios/manual/\nThe full distilled manual.\n".to_string(),
    );
    con.push(".SH SEE ALSO\n.BR mios (1),\n.BR mios.toml (5)\n".to_string());
    out.insert(format!("{MAN}/man7/mios.7"), con.concat());

    // 5. usr/share/man/man7/mios-variants.7 (if [variants.entries] exists)
    if let Some(var_entries) = ssot
        .get("variants")
        .and_then(|v| v.get("entries"))
        .and_then(|e| e.as_table())
    {
        if !var_entries.is_empty() {
            let mut vp = vec![
                th("mios-variants", "7", &v, "MiOS Variants"),
                format!(".SH NAME\nmios{DASH}variants {DASH} the MiOS product line\n"),
                ".SH DESCRIPTION\nEvery variant below is one entry in the single source of truth.\nThe status is measured, not aspirational: shipping means\nbuilt, published and observed; partial means the machinery\nruns but does not yet do the whole job; design means\nspecified with no artifact yet.\n.SH VARIANTS\n".to_string(),
            ];

            let mut var_keys: Vec<&str> = var_entries.keys().map(|k| k.as_str()).collect();
            var_keys.sort_unstable();

            for k in var_keys {
                let e = var_entries[k].as_table();
                let title = e
                    .and_then(|t| t.get("title"))
                    .and_then(|v| v.as_str())
                    .unwrap_or(k);
                let status = e
                    .and_then(|t| t.get("status"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("?");
                let summary = e
                    .and_then(|t| t.get("summary"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let target = e
                    .and_then(|t| t.get("target"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("?");

                vp.push(format!(
                    ".TP\n.B {} ({})\n{}\n.br\nRuns on: {}.\n",
                    roff(title),
                    roff(status),
                    roff(summary),
                    roff(target)
                ));
            }

            if let Some(naming) = ssot
                .get("variants")
                .and_then(|v| v.get("naming"))
                .and_then(|n| n.as_table())
            {
                let title_pattern = naming
                    .get("title_pattern")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let key_pattern = naming
                    .get("key_pattern")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                vp.push(format!(
                    ".SH NAMING\nTitles read {} and keys read {}: the same name in two registers.\nA suffix names the job, not the size.\n",
                    roff(title_pattern),
                    roff(key_pattern)
                ));
            }

            vp.push(".SH SEE ALSO\n.BR mios (1),\n.BR mios.toml (5),\n.BR mios (7)\n".to_string());
            out.insert(format!("{MAN}/man7/mios-variants.7"), vp.concat());
        }
    }

    out
}

pub fn validate_man_page(full_path: &Path) -> Result<(), String> {
    let content = fs::read_to_string(full_path)
        .map_err(|e| format!("cannot read {}: {e}", full_path.display()))?;

    if !content.starts_with(".TH ") {
        return Err(format!("{} missing .TH header", full_path.display()));
    }

    let has_name = content.contains(".SH NAME");
    let has_synopsis_or_desc =
        content.contains(".SH SYNOPSIS") || content.contains(".SH DESCRIPTION");
    if !has_name || !has_synopsis_or_desc {
        return Err(format!(
            "{} missing required .SH NAME / SYNOPSIS / DESCRIPTION section",
            full_path.display()
        ));
    }

    // Unix-only external command check if available
    #[cfg(unix)]
    {
        if which_cmd("man") {
            if let Ok(res) = Command::new("man")
                .args(["-l", &full_path.to_string_lossy()])
                .output()
            {
                if !res.status.success() {
                    let err = String::from_utf8_lossy(&res.stderr);
                    return Err(format!(
                        "man -l {} exited {:?}: {err}",
                        full_path.display(),
                        res.status.code()
                    ));
                }
                if String::from_utf8_lossy(&res.stdout).trim().is_empty() {
                    return Err(format!(
                        "man -l {} produced empty output",
                        full_path.display()
                    ));
                }
            }
        }

        if which_cmd("groff") {
            if let Ok(res) = Command::new("groff")
                .args(["-mandoc", "-Tutf8", &full_path.to_string_lossy()])
                .output()
            {
                if !res.status.success() {
                    return Err(format!(
                        "groff -mandoc {} exited {:?}",
                        full_path.display(),
                        res.status.code()
                    ));
                }
                if String::from_utf8_lossy(&res.stdout).trim().is_empty() {
                    return Err(format!(
                        "groff -mandoc {} produced empty output",
                        full_path.display()
                    ));
                }
            }
        }
    }

    Ok(())
}

#[cfg(unix)]
fn which_cmd(name: &str) -> bool {
    Command::new("which")
        .arg(name)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub fn run_render_manpages(
    root: &Path,
    check: bool,
    validate: bool,
) -> Result<(String, i32), (String, i32)> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    let toml_str = fs::read_to_string(&toml_path).map_err(|e| {
        (
            format!(
                "render-manpages: {} could not be read: {e}",
                toml_path.display()
            ),
            1,
        )
    })?;

    let ssot: Value = toml_str.parse().map_err(|e| {
        (
            format!(
                "render-manpages: failed to parse {}: {e}",
                toml_path.display()
            ),
            1,
        )
    })?;

    let rendered = render_pages(root, &ssot);
    let mut drift = Vec::new();

    for (rel, body) in &rendered {
        let full = root.join(rel);
        let current = fs::read_to_string(&full).ok();
        let matches = match &current {
            Some(curr) => curr.replace("\r\n", "\n") == body.replace("\r\n", "\n"),
            None => false,
        };

        if matches {
            continue;
        }

        if check {
            if current.is_some() {
                drift.push(rel.clone());
            } else {
                drift.push(format!("{rel} (missing)"));
            }
            continue;
        }

        if let Some(parent) = full.parent() {
            let _ = fs::create_dir_all(parent);
        }
        if let Err(e) = fs::write(&full, body.as_bytes()) {
            return Err((
                format!("render-manpages: write {} failed: {e}", full.display()),
                1,
            ));
        }
    }

    let mut orphans = Vec::new();
    let man_root = root.join(MAN);
    if man_root.is_dir() {
        for entry in walkdir::WalkDir::new(&man_root)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                let p = entry.path();
                if let Ok(rel) = p.strip_prefix(root) {
                    let rel_norm = rel.to_string_lossy().replace('\\', "/");
                    if !rendered.contains_key(&rel_norm) {
                        orphans.push(rel_norm);
                    }
                }
            }
        }
    }

    if check && (!drift.is_empty() || !orphans.is_empty()) {
        let mut lines = vec![
            "man pages out of sync with the SSOT -- run mios-gen render-manpages:".to_string(),
        ];
        for d in drift.iter().take(10) {
            lines.push(format!("  {d}"));
        }
        for o in orphans.iter().take(5) {
            lines.push(format!("  {o} (no verb declares it)"));
        }
        return Err((lines.join("\n"), 1));
    }

    for o in &orphans {
        let _ = fs::remove_file(root.join(o));
    }

    let mut messages = Vec::new();

    if validate {
        let mut valid_errors = Vec::new();
        let mut validated = 0;
        for rel in rendered.keys() {
            let full = root.join(rel);
            if !full.is_file() {
                valid_errors.push(format!("{rel}: rendered but absent from the tree"));
                continue;
            }
            validated += 1;
            if let Err(msg) = validate_man_page(&full) {
                valid_errors.push(msg);
            }
        }
        if validated == 0 {
            valid_errors.push(
                "no man page was validated, so a clean result here means nothing".to_string(),
            );
        }
        if !valid_errors.is_empty() {
            let mut lines = vec!["man page validation failed:".to_string()];
            for ve in valid_errors.iter().take(10) {
                lines.push(format!("  {ve}"));
            }
            if valid_errors.len() > 10 {
                lines.push(format!("  ... and {} more", valid_errors.len() - 10));
            }
            return Err((lines.join("\n"), 1));
        }
        messages.push(format!("[render-manpages] {validated} page(s) validated"));
    }

    let action = if check { "verified" } else { "rendered" };
    messages.push(format!(
        "[render-manpages] {} page(s) {action}",
        rendered.len()
    ));

    Ok((messages.join("\n"), 0))
}
