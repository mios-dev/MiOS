// AI-hint: Native btop theme projector: renders the [dotfiles.registry.btop] template through mios.toml tokens, byte-identical to mios-dotfiles-render, so the theme has one source.
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: usr/share/mios/mios.toml, usr/share/mios/theme/templates/btop-mios.theme.tmpl, usr/libexec/mios/mios-dotfiles-render, etc/btop/themes/mios.theme, automation/98-drift-checks.sh

#![forbid(unsafe_code)]

use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

/// The `[dotfiles.registry.<surface>]` entry this renderer projects.
const SURFACE: &str = "btop";

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct RenderBtopThemeResult {
    pub status: String,
    pub target: PathBuf,
    pub theme_len: usize,
    pub keys_count: usize,
}

/// A TOML scalar as the conf surfaces spell it: bools capitalised (btop's
/// on-disk form), everything else verbatim. Tables and arrays are not tokens.
fn fmt_conf(v: &toml::Value) -> Option<String> {
    match v {
        toml::Value::Boolean(b) => Some(if *b { "True" } else { "False" }.to_string()),
        toml::Value::String(s) => Some(s.clone()),
        toml::Value::Integer(i) => Some(i.to_string()),
        toml::Value::Float(f) => Some(f.to_string()),
        toml::Value::Datetime(d) => Some(d.to_string()),
        toml::Value::Array(_) | toml::Value::Table(_) => None,
    }
}

fn walk<'a>(doc: &'a toml::Value, dotted: &str) -> Option<&'a toml::Value> {
    dotted.split('.').try_fold(doc, |cur, part| cur.get(part))
}

/// The token map mios-dotfiles-render builds for a surface: every `[colors]`
/// key, then `<section>_<key>` for the flat scalars of `[identity]` and of the
/// surface's own `section`, when it names one.
fn resolved_tokens(doc: &toml::Value, section: Option<&str>) -> BTreeMap<String, String> {
    let mut out = BTreeMap::new();
    if let Some(colors) = doc.get("colors").and_then(toml::Value::as_table) {
        for (k, v) in colors {
            if let Some(s) = fmt_conf(v) {
                out.insert(k.clone(), s);
            }
        }
    }
    for sec in std::iter::once("identity").chain(section) {
        if let Some(t) = walk(doc, sec).and_then(toml::Value::as_table) {
            for (k, v) in t {
                if let Some(s) = fmt_conf(v) {
                    out.insert(format!("{sec}_{k}"), s);
                }
            }
        }
    }
    out
}

/// A token outside the map: a dotted SSOT path, else `<section>_<key>` split
/// at each underscore in turn -- the same fallback mios-dotfiles-render uses.
fn arbitrary_token(doc: &toml::Value, tok: &str) -> Option<String> {
    if let Some(v) = walk(doc, tok).and_then(fmt_conf) {
        return Some(v);
    }
    let parts: Vec<&str> = tok.split('_').collect();
    (1..parts.len()).find_map(|i| {
        let path = format!("{}.{}", parts[..i].join("_"), parts[i..].join("_"));
        walk(doc, &path).and_then(fmt_conf)
    })
}

/// Substitute every `@MIOS:<token>@` sentinel; an unknown token is an error,
/// never a literal left in the projected file.
pub fn render_tokens(
    template: &str,
    doc: &toml::Value,
    section: Option<&str>,
) -> Result<String, String> {
    let sentinel = Regex::new(r"@MIOS:([a-z0-9_.-]+)@")
        .map_err(|e| format!("Failed to compile token pattern: {e}"))?;
    let resolved = resolved_tokens(doc, section);
    let mut unknown = BTreeSet::new();
    let out = sentinel.replace_all(template, |caps: &regex::Captures| {
        let tok = &caps[1];
        resolved
            .get(tok)
            .cloned()
            .or_else(|| arbitrary_token(doc, tok))
            .unwrap_or_else(|| {
                unknown.insert(tok.to_string());
                caps[0].to_string()
            })
    });
    if unknown.is_empty() {
        Ok(out.into_owned())
    } else {
        Err(format!(
            "unknown theme/dotfile token(s) {} (not in [colors] or an SSOT key)",
            unknown
                .iter()
                .map(|t| format!("@MIOS:{t}@"))
                .collect::<Vec<_>>()
                .join(", ")
        ))
    }
}

/// Every non-comment line is `theme[key]="#rrggbb"` (or `""`, transparent),
/// and the slots btop cannot draw without are present.
pub fn validate_theme_content(content: &str) -> Result<usize, Vec<String>> {
    let mut errors = Vec::new();
    let mut found_keys = BTreeSet::new();
    let line_re = Regex::new(r#"^theme\[([a-zA-Z0-9_]+)\]\s*=\s*"([^"]*)""#)
        .map_err(|e| vec![format!("Failed to compile theme validator: {e}")])?;
    let hex_re = Regex::new(r"^#[0-9a-fA-F]{6}$")
        .map_err(|e| vec![format!("Failed to compile color validator: {e}")])?;

    for (idx, raw_line) in content.lines().enumerate() {
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        match line_re.captures(line) {
            Some(caps) => {
                let key = caps.get(1).map_or("", |m| m.as_str());
                let hex_val = caps.get(2).map_or("", |m| m.as_str());
                found_keys.insert(key.to_string());
                if !hex_val.is_empty() && !hex_re.is_match(hex_val) {
                    errors.push(format!(
                        "Line {}: Invalid hex color '{}' for key '{}'",
                        idx + 1,
                        hex_val,
                        key
                    ));
                }
            }
            None => errors.push(format!(
                "Line {}: Invalid syntax format: '{}'",
                idx + 1,
                line
            )),
        }
    }

    for req in [
        "main_bg",
        "main_fg",
        "cpu_box",
        "mem_box",
        "temp_start",
        "cpu_start",
    ] {
        if !found_keys.contains(req) {
            errors.push(format!("Missing required btop theme key: '{req}'"));
        }
    }

    if errors.is_empty() {
        Ok(found_keys.len())
    } else {
        Err(errors)
    }
}

fn registry_str<'a>(entry: &'a toml::Value, key: &str) -> Result<&'a str, String> {
    entry
        .get(key)
        .and_then(toml::Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or_else(|| format!("[dotfiles.registry.{SURFACE}].{key} is missing or empty"))
}

pub fn run_render_btop_theme(
    root: &Path,
    check: bool,
    out_path: Option<&Path>,
) -> Result<RenderBtopThemeResult, String> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    let toml_str = fs::read_to_string(&toml_path)
        .map_err(|e| format!("Failed to read {}: {}", toml_path.display(), e))?;
    let doc: toml::Value = toml_str
        .parse()
        .map_err(|e| format!("Failed to parse {}: {}", toml_path.display(), e))?;

    let entry = walk(&doc, &format!("dotfiles.registry.{SURFACE}"))
        .ok_or_else(|| format!("mios.toml declares no [dotfiles.registry.{SURFACE}]"))?;
    let template_rel = registry_str(entry, "template")?;
    let target_rel = registry_str(entry, "target")?;
    let section = entry.get("section").and_then(toml::Value::as_str);

    let template_path = root.join(template_rel);
    let template = fs::read_to_string(&template_path)
        .map_err(|e| format!("Failed to read {}: {}", template_path.display(), e))?;
    let rendered = render_tokens(&template, &doc, section)?;
    // The projection itself must be a theme btop can load, so a template edit
    // that breaks the format fails here rather than on someone's desktop.
    let keys_count = validate_theme_content(&rendered).map_err(|errs| {
        format!(
            "{} does not render a valid btop theme: {}",
            template_rel,
            errs.join("; ")
        )
    })?;

    let target_path = match out_path {
        Some(p) => p.to_path_buf(),
        None => root.join(target_rel),
    };

    if check {
        if !target_path.is_file() {
            return Err(format!(
                "btop theme target does not exist for verification: {}",
                target_path.display()
            ));
        }
        let disk_content = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read {}: {}", target_path.display(), e))?;
        validate_theme_content(&disk_content).map_err(|errs| errs.join("; "))?;
        if disk_content.replace("\r\n", "\n") != rendered.replace("\r\n", "\n") {
            return Err(format!(
                "btop theme drifted from SSOT projection at {} (template {})",
                target_path.display(),
                template_rel
            ));
        }
    } else {
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create parent dir {}: {}", parent.display(), e))?;
        }
        fs::write(&target_path, rendered.as_bytes())
            .map_err(|e| format!("Failed to write {}: {}", target_path.display(), e))?;
    }

    Ok(RenderBtopThemeResult {
        status: "success".to_string(),
        target: target_path,
        theme_len: rendered.len(),
        keys_count,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn doc() -> toml::Value {
        "[colors]\naccent = \"#1A407F\"\n[identity]\nusername = \"mios\"\n[btop]\nshown = true\n"
            .parse()
            .unwrap()
    }

    #[test]
    fn tokens_resolve_from_colors_identity_and_dotted_paths() {
        let d = doc();
        let out = render_tokens(
            "a=@MIOS:accent@ u=@MIOS:identity_username@ s=@MIOS:btop.shown@ t=@MIOS:btop_shown@",
            &d,
            None,
        )
        .unwrap();
        assert_eq!(out, "a=#1A407F u=mios s=True t=True");
    }

    #[test]
    fn an_unknown_token_is_an_error_not_a_literal() {
        let err = render_tokens("x=@MIOS:nope@", &doc(), None).unwrap_err();
        assert!(err.contains("@MIOS:nope@"), "{err}");
    }

    #[test]
    fn a_projection_missing_a_required_slot_is_invalid() {
        let errs = validate_theme_content("theme[main_bg]=\"\"\n").unwrap_err();
        assert!(errs.iter().any(|e| e.contains("main_fg")), "{errs:?}");
    }
}
