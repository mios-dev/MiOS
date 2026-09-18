// AI-hint: install.env binding -- renders the KEY=value environment file consumed by Quadlets via EnvironmentFile.
// AI-related: /etc/mios/install.env, usr/share/containers/systemd
use std::path::Path;
use toml::Value;

use crate::emit::{build_exports_map, resolve_cross_references};

pub fn emit_install_env(
    merged: &Value,
    stack_offset: i64,
    _ref_names_path: Option<&Path>,
) -> String {
    let mut exports = build_exports_map(merged, stack_offset);

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

    // After the [env] merge, so an [env] value can both reference an
    // exported key and be referenced by one. Unresolved values still carry
    // `$` and are dropped by the bare-safe filter below (Law 10) -- which is
    // exactly how MIOS_AI_ENDPOINT went missing before T-1060.
    resolve_cross_references(&mut exports);

    let mut lines = Vec::new();

    for (k, v) in &exports {
        if k.contains("SECRET") || k.contains("TOKEN") || k.contains("PASSWORD") {
            continue;
        }
        if v.contains(' ') || v.contains('\n') || v.contains('$') {
            continue;
        }
        lines.push(format!("{}={}", k, v));
    }

    lines.sort();
    lines.join("\n") + "\n"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_emit_install_env() {
        let val: Value = toml::from_str(
            r#"
[identity]
role = "mini"
"#,
        )
        .unwrap();
        let env_str = emit_install_env(&val, 0, None);
        assert!(env_str.contains("MIOS_IDENTITY_ROLE=mini"));
    }
}
