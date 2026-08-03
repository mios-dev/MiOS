use toml::Value;

/// Recursively walk a TOML Value tree and yield `(dotted_path, value)` pairs.
/// Skips `routing.domains` as defined in `mios_toml.py`.
pub fn walk(val: &Value) -> Vec<(String, Value)> {
    let mut results = Vec::new();
    if let Value::Table(table) = val {
        walk_table(table, "", &mut results);
    }
    results
}

pub fn walk_table(table: &toml::Table, prefix: &str, results: &mut Vec<(String, Value)>) {
    for (k, v) in table {
        let path = if prefix.is_empty() {
            k.clone()
        } else {
            format!("{prefix}.{k}")
        };

        if path == "routing.domains" {
            continue;
        }

        match v {
            Value::Table(child_table) => {
                walk_table(child_table, &path, results);
            }
            _ => {
                results.push((path, v.clone()));
            }
        }
    }
}

/// Compute the multi-tenancy port stack_offset from `ports.stack_id`.
/// Formula: `int(ports.stack_id) * 10000` if present, else `0`.
pub fn compute_stack_offset(root: &Value) -> i64 {
    if let Value::Table(table) = root {
        if let Some(Value::Table(ports_table)) = table.get("ports") {
            if let Some(stack_id_val) = ports_table.get("stack_id") {
                if let Some(n) = stack_id_val.as_integer() {
                    return n * 10000;
                } else if let Some(s) = stack_id_val.as_str() {
                    if let Ok(n) = s.parse::<i64>() {
                        return n * 10000;
                    }
                }
            }
        }
    }
    0
}

/// Transform a TOML value according to MiOS business rules:
/// - Boolean -> "true" / "false"
/// - `ports.*` (except `ports.stack_id`) -> `int(v) + stack_offset` (unless port == 53)
/// - List/Array -> comma-separated string
/// - Scalar -> string representation
pub fn process_val(dotted: &str, val: &Value, stack_offset: i64) -> String {
    match val {
        Value::Boolean(b) => if *b { "true" } else { "false" }.to_string(),
        Value::Array(arr) => {
            let items: Vec<String> = arr
                .iter()
                .map(|elem| match elem {
                    Value::String(s) => s.clone(),
                    Value::Boolean(b) => if *b { "true" } else { "false" }.to_string(),
                    other => other.to_string(),
                })
                .collect();
            items.join(",")
        }
        Value::Integer(n) => {
            if dotted.starts_with("ports.") && dotted != "ports.stack_id" && *n != 53 {
                format!("{}", n + stack_offset)
            } else {
                n.to_string()
            }
        }
        Value::String(s) => {
            if dotted.starts_with("ports.") && dotted != "ports.stack_id" {
                if let Ok(n) = s.parse::<i64>() {
                    if n != 53 {
                        return format!("{}", n + stack_offset);
                    }
                }
            }
            s.clone()
        }
        Value::Float(f) => f.to_string(),
        Value::Datetime(dt) => dt.to_string(),
        Value::Table(_) => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use toml::toml;

    #[test]
    fn test_walk_basic() {
        let tree: Value = toml! {
            [system]
            name = "mios"
            [ports]
            web = 8080
        }
        .into();

        let walked = walk(&tree);
        assert_eq!(walked.len(), 2);
        assert_eq!(walked[0].0, "system.name");
        assert_eq!(walked[1].0, "ports.web");
    }

    #[test]
    fn test_walk_skips_routing_domains() {
        let tree: Value = toml! {
            [routing]
            mode = "traefik"
            domains = ["example.com"]
        }
        .into();

        let walked = walk(&tree);
        assert_eq!(walked.len(), 1);
        assert_eq!(walked[0].0, "routing.mode");
    }

    #[test]
    fn test_process_val_boolean() {
        let val_true = Value::Boolean(true);
        let val_false = Value::Boolean(false);
        assert_eq!(process_val("system.enable", &val_true, 0), "true");
        assert_eq!(process_val("system.enable", &val_false, 0), "false");
    }

    #[test]
    fn test_process_val_array() {
        let arr = Value::Array(vec![
            Value::String("a".to_string()),
            Value::String("b".to_string()),
            Value::String("c".to_string()),
        ]);
        assert_eq!(process_val("packages.list", &arr, 0), "a,b,c");
    }

    #[test]
    fn test_process_val_ports_stack_offset() {
        let port_web = Value::Integer(8080);
        let port_dns = Value::Integer(53);
        let stack_id = Value::Integer(2);

        assert_eq!(process_val("ports.web", &port_web, 20000), "28080");
        assert_eq!(process_val("ports.dns", &port_dns, 20000), "53"); // 53 exempt!
        assert_eq!(process_val("ports.stack_id", &stack_id, 20000), "2"); // stack_id exempt!
    }

    #[test]
    fn test_compute_stack_offset() {
        let tree: Value = toml! {
            [ports]
            stack_id = 3
        }
        .into();

        assert_eq!(compute_stack_offset(&tree), 30000);
    }
}
