// AI-hint: POSIX shell binding -- serializes the export map as shell-quoted export lines for userenv.sh to eval.
// AI-related: usr/lib/mios/userenv.sh, tools/lib/userenv.sh
use std::fs;
use std::path::Path;
use toml::Value;

use crate::emit::{build_exports_map, resolve_cross_references};

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

    // shlex_quote single-quotes anything containing `$`, and bash does not
    // expand inside single quotes -- so a live ${MIOS_*} reference here is
    // exported as literal text, never as its value. Nor is there anything to
    // expand against: these lines are sorted alphabetically, not
    // topologically, so a referent may be defined after its referrer. Unlike
    // automation/lib/globals.sh, which splices and topologically sorts, this
    // binding also exports unconditionally, so it never offered the
    // "pre-exported value wins" property that a live reference would serve.
    // Resolving here is what makes userenv.sh's native tier agree with its
    // Python fallback.
    resolve_cross_references(&mut exports);

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

    /// shlex_quote single-quotes any value containing `$`, and bash does not
    /// expand inside single quotes. userenv.sh evals this output in its primary
    /// tier, so a value that still carried `${MIOS_PORT_AGENT_PIPE}` here was
    /// exported to consumers verbatim, as that literal text.
    #[test]
    fn test_cross_reference_is_resolved_not_quoted_literal() {
        let val: Value = toml::from_str(
            r#"
[ports]
agent_pipe = 8700

[ai]
endpoint = "http://localhost:${MIOS_PORT_AGENT_PIPE}/v1"
"#,
        )
        .unwrap();
        let out = emit_shell(&val, 0, None);
        let line = out
            .lines()
            .find(|l| l.starts_with("export MIOS_AI_ENDPOINT="))
            .expect("MIOS_AI_ENDPOINT is emitted");
        assert_eq!(line, "export MIOS_AI_ENDPOINT=http://localhost:8700/v1");
        assert!(
            !out.contains("${MIOS_PORT_AGENT_PIPE}"),
            "a single-quoted ${{...}} is exported as literal text, not expanded"
        );
    }
}
