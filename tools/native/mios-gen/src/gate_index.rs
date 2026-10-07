// AI-hint: Generator and validator for usr/share/mios/reference/drift-gate-index.tsv from automation/98-drift-checks.sh.
// AI-related: usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md, tools/native/mios-gen/src/main.rs

use regex::Regex;
use std::fs;
use std::path::{Path, PathBuf};

fn body(lines: &[&str], name: &str) -> Vec<String> {
    let opener = Regex::new(&format!(r"^\s*{}\(\)\s*\{{", regex::escape(name))).unwrap();
    for (i, ln) in lines.iter().enumerate() {
        if !opener.is_match(ln) {
            continue;
        }
        let trimmed = ln.trim_end();
        if trimmed.ends_with('}') {
            let start = trimmed.find('{').unwrap() + 1;
            let end = trimmed.rfind('}').unwrap();
            return vec![trimmed[start..end].to_string()];
        }
        let mut out = Vec::new();
        for nxt in &lines[i + 1..] {
            if nxt.starts_with('}') {
                return out;
            }
            out.push((*nxt).to_string());
        }
        return out;
    }
    Vec::new()
}

fn first_sentence(text: &str) -> &str {
    let bytes = text.as_bytes();
    for i in 1..bytes.len() {
        if bytes[i] == b'.'
            && (bytes[i - 1].is_ascii_alphanumeric() || bytes[i - 1] == b')')
            && (i + 1 == bytes.len() || bytes[i + 1].is_ascii_whitespace())
        {
            return &text[..i];
        }
    }
    text
}

fn hint_of(root: &Path, command: &str) -> String {
    let parts: Vec<&str> = command.trim_end_matches(';').split_whitespace().collect();
    if parts.is_empty() {
        return String::new();
    }
    if parts.iter().skip(1).any(|p| !p.starts_with('-')) {
        return String::new();
    }
    let path = root.join(parts[0]);
    if !path.is_file() {
        return String::new();
    }
    let Ok(content) = fs::read_to_string(&path) else {
        return String::new();
    };
    let hint_re = Regex::new(r"#\s*AI-hint:\s*(.+)").unwrap();
    for (i, ln) in content.lines().enumerate() {
        if i > 8 {
            break;
        }
        if let Some(caps) = hint_re.captures(ln.trim()) {
            let text = caps.get(1).unwrap().as_str().trim();
            let first = first_sentence(text);
            if first.ends_with("...") {
                return String::new();
            }
            return first
                .trim_end_matches('.')
                .replace('\t', " ")
                .trim()
                .to_string();
        }
    }
    String::new()
}

fn describe(root: &Path, lines: &[&str], content: &str, name: &str) -> String {
    let pat = format!(
        r"#\s*---\s*(?:\(\d+,\s*)?([^\n#]+?)\s*---\s*\n\s*{}\(\)\s*\{{",
        regex::escape(name)
    );
    if let Ok(re) = Regex::new(&pat) {
        if let Some(caps) = re.captures(content) {
            return caps.get(1).unwrap().as_str().trim().to_string();
        }
    }

    let b = body(lines, name);
    let echo_re = Regex::new(r#"echo\s+"\[98-drift-checks\]\s+(?:\(\d+\)\s+)?([^"]+)""#).unwrap();
    let b_joined = b.join("\n");
    for caps in echo_re.captures_iter(&b_joined) {
        let em = caps.get(1).unwrap().as_str().trim();
        if !em.starts_with("WARNING") && !em.starts_with("VIOLATION") && !em.starts_with("---") {
            return em.to_string();
        }
    }

    let run_py_re = Regex::new(r#"_run_py_check\s+\S+\s+(?:"([^"]+)"|(\S+))"#).unwrap();
    for line in &b {
        if let Some(caps) = run_py_re.captures(line) {
            let cmd = caps.get(1).or_else(|| caps.get(2)).unwrap().as_str();
            let hint = hint_of(root, cmd);
            if !hint.is_empty() {
                return hint;
            }
        }
    }

    name.strip_prefix("check_")
        .unwrap_or(name)
        .replace('_', " ")
}

pub fn run_gate_index(
    root: &Path,
    custom_script: Option<PathBuf>,
    custom_output: Option<PathBuf>,
    check_mode: bool,
) -> Result<(), (String, i32)> {
    let script_path = custom_script.unwrap_or_else(|| root.join("automation/98-drift-checks.sh"));
    let output_path =
        custom_output.unwrap_or_else(|| root.join("usr/share/mios/reference/drift-gate-index.tsv"));

    if !script_path.is_file() {
        return Err((format!("{} not found", script_path.display()), 1));
    }

    let content = fs::read_to_string(&script_path)
        .map_err(|e| (format!("Failed to read {}: {e}", script_path.display()), 1))?;

    let main_start = content.find("main() {").ok_or_else(|| {
        (
            "ERROR: main() function not found in 98-drift-checks.sh".to_string(),
            1,
        )
    })?;

    let main_body = &content[main_start..];
    let check_re = Regex::new(r"(?m)^\s*(check_[a-z0-9_]+)\s*$").unwrap();
    let check_names: Vec<String> = check_re
        .captures_iter(main_body)
        .map(|c| c.get(1).unwrap().as_str().to_string())
        .collect();

    if check_names.is_empty() {
        return Err(("ERROR: No check_* functions found in main()".to_string(), 1));
    }

    let mut seen = std::collections::HashSet::new();
    for name in &check_names {
        if !seen.insert(name) {
            return Err((
                format!("ERROR: Duplicate check_* functions found in main(): {name}"),
                1,
            ));
        }
    }

    let lines: Vec<&str> = content.lines().collect();
    let mut rows = Vec::new();
    for (idx, name) in check_names.iter().enumerate() {
        let desc = describe(root, &lines, &content, name);
        rows.push(format!("{}\t{}\t{}", idx + 1, name, desc));
    }

    let tsv_content = format!(
        "# Ordinal\tCheck Function\tDescription\n{}\n",
        rows.join("\n")
    );

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
                "ERROR: drift-gate-index.tsv is out of sync with 98-drift-checks.sh. Run mios-gen gate-index to regenerate."
                    .to_string(),
                1,
            ));
        }
        println!("PASS: drift-gate-index.tsv is in sync.");
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
        "Generated {} with {} gate entries.",
        output_path.display(),
        check_names.len()
    );
    Ok(())
}
