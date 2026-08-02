// AI-hint: deep_merge overlay semantics -- recursive table merge where a non-empty value overrides and an empty string never does.
// AI-related: usr/lib/mios/mios_toml.py
use toml::Value;

pub fn deep_merge(dst: &mut Value, src: &Value) {
    match (dst, src) {
        (Value::Table(dst_map), Value::Table(src_map)) => {
            for (k, src_val) in src_map {
                if let Some(dst_val) = dst_map.get_mut(k) {
                    if let (Value::String(s), Value::String(d)) = (src_val, &*dst_val) {
                        if s.is_empty() && !d.is_empty() {
                            continue; // empty string never overrides non-empty lower-layer value
                        }
                    }
                    if src_val.is_table() && dst_val.is_table() {
                        deep_merge(dst_val, src_val);
                    } else {
                        dst_map.insert(k.clone(), src_val.clone());
                    }
                } else {
                    dst_map.insert(k.clone(), src_val.clone());
                }
            }
        }
        _ => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_string_never_overrides() {
        let mut dst: Value = toml::from_str(r#"
[identity]
role = "admin"
username = "operator"
"#).unwrap();

        let src: Value = toml::from_str(r#"
[identity]
role = ""
username = "new_operator"
"#).unwrap();

        deep_merge(&mut dst, &src);

        let role = dst.get("identity").unwrap().get("role").unwrap().as_str().unwrap();
        let user = dst.get("identity").unwrap().get("username").unwrap().as_str().unwrap();

        assert_eq!(role, "admin");
        assert_eq!(user, "new_operator");
    }

    #[test]
    fn test_nested_table_merge() {
        let mut dst: Value = toml::from_str(r#"
[ai]
endpoint = "http://localhost:8000"
model = "qwen"
"#).unwrap();

        let src: Value = toml::from_str(r#"
[ai]
model = "llama3"
"#).unwrap();

        deep_merge(&mut dst, &src);

        let endpoint = dst.get("ai").unwrap().get("endpoint").unwrap().as_str().unwrap();
        let model = dst.get("ai").unwrap().get("model").unwrap().as_str().unwrap();

        assert_eq!(endpoint, "http://localhost:8000");
        assert_eq!(model, "llama3");
    }
}
