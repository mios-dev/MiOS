// AI-hint: Walk and value-transform pass -- emits (dotted_path, value) pairs applying stack_offset, the port-53 exemption, bool and CSV normalization.
// AI-related: usr/lib/mios/mios_toml.py, usr/share/mios/mios.toml
use toml::Value;

pub fn process_val(dotted: &str, v: &Value, stack_offset: i32) -> String {
    match v {
        Value::Boolean(b) => {
            if *b {
                "true".into()
            } else {
                "false".into()
            }
        }
        Value::Integer(n) => {
            if dotted.starts_with("ports.") && dotted != "ports.stack_id" && *n != 53 {
                return (*n as i32 + stack_offset).to_string();
            }
            n.to_string()
        }
        Value::String(s) => {
            if dotted.starts_with("ports.") && dotted != "ports.stack_id" {
                if let Ok(parsed) = s.parse::<i32>() {
                    if parsed != 53 {
                        return (parsed + stack_offset).to_string();
                    }
                }
            }
            s.clone()
        }
        Value::Array(arr) => {
            let items: Vec<String> = arr
                .iter()
                .map(|item| match item {
                    Value::String(s) => s.clone(),
                    Value::Boolean(b) => {
                        if *b {
                            "true".into()
                        } else {
                            "false".into()
                        }
                    }
                    Value::Integer(i) => i.to_string(),
                    Value::Float(f) => f.to_string(),
                    _ => item.to_string(),
                })
                .collect();
            items.join(",")
        }
        Value::Float(f) => f.to_string(),
        Value::Datetime(dt) => dt.to_string(),
        Value::Table(_) => String::new(),
    }
}

pub fn walk_table(val: &Value, prefix: &str) -> Vec<(String, Value)> {
    let mut results = Vec::new();
    if let Value::Table(map) = val {
        for (k, v) in map {
            let path = if prefix.is_empty() {
                k.clone()
            } else {
                format!("{}.{}", prefix, k)
            };

            if path == "routing.domains" {
                continue;
            }

            if v.is_table() {
                results.extend(walk_table(v, &path));
            } else {
                results.push((path, v.clone()));
            }
        }
    }
    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_val_boolean() {
        let b_true = Value::Boolean(true);
        let b_false = Value::Boolean(false);
        assert_eq!(process_val("sandbox.enable", &b_true, 0), "true");
        assert_eq!(process_val("sandbox.enable", &b_false, 0), "false");
    }

    #[test]
    fn test_process_val_ports_stack_offset() {
        let p_vllm = Value::Integer(8000);
        let p_dns = Value::Integer(53);
        let stack_id = Value::Integer(2);

        assert_eq!(process_val("ports.vllm", &p_vllm, 20000), "28000");
        assert_eq!(process_val("ports.adguard_dns", &p_dns, 20000), "53"); // port 53 exempt!
        assert_eq!(process_val("ports.stack_id", &stack_id, 20000), "2"); // stack_id exempt!
    }

    #[test]
    fn test_process_val_array() {
        let arr = Value::Array(vec![
            Value::String("a".into()),
            Value::String("b".into()),
            Value::String("c".into()),
        ]);
        assert_eq!(process_val("profile.features", &arr, 0), "a,b,c");
    }
}
