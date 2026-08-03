// AI-hint: DB-authoritative overlay hook -- inert by default unless MIOS_ACCOUNTS_DB_BACKED is enabled or --db-overlay is set.
// AI-related: usr/lib/mios/mios_toml.py, usr/lib/mios/mios_db_config.py
use crate::merge::deep_merge;
use std::process::Command;
use toml::Value;

pub fn is_db_authoritative() -> bool {
    std::env::var("MIOS_ACCOUNTS_DB_BACKED")
        .map(|v| v == "true" || v == "1")
        .unwrap_or(false)
}

/// If DB mode is authoritative (or requested), shell out to mios_db_config and deep-merge the result.
pub fn maybe_apply_db_overlay(dst: &mut Value, force_db: bool) {
    if !force_db && !is_db_authoritative() {
        return;
    }

    let python_cmd = "import mios_db_config, json; cfg = mios_db_config.load_db_config() if mios_db_config.is_db_authoritative() else {}; print(json.dumps(cfg or {}))";

    let output = Command::new("python3").arg("-c").arg(python_cmd).output();

    if let Ok(out) = output {
        if out.status.success() {
            if let Ok(json_str) = String::from_utf8(out.stdout) {
                if let Ok(json_val) = serde_json::from_str::<serde_json::Value>(&json_str) {
                    if let Ok(toml_val) = json_to_toml(&json_val) {
                        deep_merge(dst, toml_val);
                    }
                }
            }
        }
    }
}

fn json_to_toml(j: &serde_json::Value) -> Result<Value, ()> {
    match j {
        serde_json::Value::Null => Ok(Value::String("".into())),
        serde_json::Value::Bool(b) => Ok(Value::Boolean(*b)),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(Value::Integer(i))
            } else if let Some(f) = n.as_f64() {
                Ok(Value::Float(f))
            } else {
                Err(())
            }
        }
        serde_json::Value::String(s) => Ok(Value::String(s.clone())),
        serde_json::Value::Array(arr) => {
            let mut vec = Vec::new();
            for item in arr {
                if let Ok(tv) = json_to_toml(item) {
                    vec.push(tv);
                }
            }
            Ok(Value::Array(vec))
        }
        serde_json::Value::Object(map) => {
            let mut table = toml::map::Map::new();
            for (k, v) in map {
                if let Ok(tv) = json_to_toml(v) {
                    table.insert(k.clone(), tv);
                }
            }
            Ok(Value::Table(table))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_db_authoritative_default() {
        assert!(!is_db_authoritative());
    }

    #[test]
    fn test_default_path_leaves_value_untouched() {
        let mut original: Value = toml::from_str(
            r#"
[identity]
role = "mini"
"#,
        )
        .unwrap();

        let expected = original.clone();
        maybe_apply_db_overlay(&mut original, false);
        assert_eq!(original, expected);
    }
}
