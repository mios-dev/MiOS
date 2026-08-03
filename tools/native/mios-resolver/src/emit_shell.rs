// AI-hint: POSIX shell binding -- serializes the export map as shell-quoted export lines for userenv.sh to eval.
// AI-related: usr/lib/mios/userenv.sh, tools/lib/userenv.sh
use std::fs;
use std::path::Path;
use toml::Value;

use crate::emit::build_exports_map;

pub fn shlex_quote(s: &str) -> String {
    if s.is_empty() {
        return "''".to_string();
    }
    if s.chars().all(|c| {
        matches!(c,
            'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' | '.' | ':' | '/' | '@')
    }) {
        return s.to_string();
    }
    format!("'{}'", s.replace('\'', "'\"'\"'"))
}

pub fn emit_shell(merged: &Value, stack_offset: i64, ref_names_path: Option<&Path>) -> String {
    let mut exports = build_exports_map(merged, stack_offset);

    // Merge [env] table verbatim sorted
    if let Some(env_table) = merged.get("env").and_then(|v| v.as_table()) {
        for (k, v) in env_table {
            let val_str = match v {
                Value::String(s) => s.clone(),
                Value::Boolean(b) => {
                    if *b {
                        "true".into()
                    } else {
                        "false".into()
                    }
                }
                Value::Integer(i) => i.to_string(),
                _ => v.to_string(),
            };
            exports.insert(k.clone(), val_str);
        }
    }

    if !exports.contains_key("MIOS_PG_BIND_ADDR") {
        let is_loopback = exports
            .get("MIOS_PGVECTOR_LISTEN_LOOPBACK")
            .map(|s| s == "true" || s == "1")
            .unwrap_or(true);
        exports.insert(
            "MIOS_PG_BIND_ADDR".to_string(),
            if is_loopback { "127.0.0.1" } else { "0.0.0.0" }.to_string(),
        );
    }

    let mut lines = Vec::new();
    for (k, v) in &exports {
        lines.push(format!("export {}={}", k, shlex_quote(v)));
    }

    // Referenced names passthrough
    if let Some(ref_path) = ref_names_path {
        if ref_path.exists() {
            if let Ok(content) = fs::read_to_string(ref_path) {
                for line in content.lines() {
                    let name = line.trim();
                    if !name.is_empty() && !exports.contains_key(name) {
                        lines.push(format!("export {}=\"${{{}:-}}\"", name, name));
                    }
                }
            }
        }
    }

    lines.sort();
    lines.join("\n") + "\n"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shlex_quote() {
        assert_eq!(shlex_quote("simple"), "simple");
        assert_eq!(shlex_quote("with space"), "'with space'");
        assert_eq!(shlex_quote("don't"), "'don'\"'\"'t'");
        assert_eq!(shlex_quote(""), "''");
    }
}
