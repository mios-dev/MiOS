// AI-hint: Task record helpers -- canonical key order from the schema, the Python-identical serializer, the strict JSON-schema checker and the status word maps (OpenAI words canonical, legacy words read).
// AI-related: /usr/lib/mios/schemas/task-record.schema.json, tasks.jsonl, /usr/share/doc/mios/adr/0028-one-canonical-task-list.md
// AI-functions: Schema::load, Schema::canon, Schema::conforms, dumps, canonical_status, lane_word, today, is_iso_date

use regex::Regex;
use serde_json::{Map, Value};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// The canonical status words; the schema enum is their single home, this list only orders reports.
pub const STATUSES: [&str; 5] = [
    "pending",
    "in_progress",
    "completed",
    "incomplete",
    "cancelled",
];

/// The strict OpenAI json_schema wrapper for one tasks.jsonl line.
pub struct Schema {
    pub record: Value,
    patterns: HashMap<String, Regex>,
}

impl Schema {
    pub fn load(p: &Path) -> Result<Schema, String> {
        let t = fs::read_to_string(p).map_err(|e| format!("{}: {e}", p.display()))?;
        let doc: Value = serde_json::from_str(&t).map_err(|e| format!("{}: {e}", p.display()))?;
        let record = doc.get("schema").cloned().ok_or(format!(
            "{}: no `schema` member (strict json_schema wrapper)",
            p.display()
        ))?;
        let mut patterns = HashMap::new();
        collect_patterns(&record, &mut patterns)?;
        Ok(Schema { record, patterns })
    }

    /// Reorder every object to its schema node's `required` order; unknown keys keep their place after them.
    pub fn canon(&self, v: &Value, node: &Value) -> Value {
        match v {
            Value::Object(o) => {
                let props = node.get("properties").and_then(|p| p.as_object());
                let mut out = Map::new();
                for k in required(node) {
                    if let Some(x) = o.get(&k) {
                        let child = props.and_then(|p| p.get(&k)).unwrap_or(&Value::Null);
                        out.insert(k.clone(), self.canon(x, child));
                    }
                }
                for (k, x) in o {
                    if !out.contains_key(k) {
                        let child = props.and_then(|p| p.get(k)).unwrap_or(&Value::Null);
                        out.insert(k.clone(), self.canon(x, child));
                    }
                }
                Value::Object(out)
            }
            Value::Array(a) => {
                let item = node.get("items").unwrap_or(&Value::Null);
                Value::Array(a.iter().map(|x| self.canon(x, item)).collect())
            }
            x => x.clone(),
        }
    }

    /// Check `v` against `node`; problems are pushed as "<path>: <what>".
    pub fn conforms(&self, v: &Value, node: &Value, path: &str, errs: &mut Vec<String>) {
        if errs.len() > 40 {
            return;
        }
        let types: Vec<&str> = match node.get("type") {
            Some(Value::String(t)) => vec![t.as_str()],
            Some(Value::Array(a)) => a.iter().filter_map(|x| x.as_str()).collect(),
            _ => vec![],
        };
        let actual = match v {
            Value::Null => "null",
            Value::Bool(_) => "boolean",
            Value::Number(n) if n.is_i64() || n.is_u64() => "integer",
            Value::Number(_) => "number",
            Value::String(_) => "string",
            Value::Array(_) => "array",
            Value::Object(_) => "object",
        };
        if !types.is_empty()
            && !types.contains(&actual)
            && !(actual == "integer" && types.contains(&"number"))
        {
            errs.push(format!(
                "{path}: {actual} where the schema wants {}",
                types.join("|")
            ));
            return;
        }
        if let Some(e) = node.get("enum").and_then(|e| e.as_array()) {
            if !e.contains(v) {
                errs.push(format!("{path}: {v} is not in the enum"));
            }
        }
        if let Value::String(s) = v {
            if let Some(p) = node.get("pattern").and_then(|p| p.as_str()) {
                if let Some(rx) = self.patterns.get(p) {
                    if !rx.is_match(s) {
                        errs.push(format!("{path}: {s:?} does not match {p}"));
                    }
                }
            }
            if let Some(min) = node.get("minLength").and_then(|m| m.as_u64()) {
                if (s.chars().count() as u64) < min {
                    errs.push(format!("{path}: shorter than {min} character(s)"));
                }
            }
        }
        if let Value::Object(o) = v {
            let props = node
                .get("properties")
                .and_then(|p| p.as_object())
                .cloned()
                .unwrap_or_default();
            for r in required(node) {
                if !o.contains_key(&r) {
                    errs.push(format!("{path}: missing required {r}"));
                }
            }
            for (k, x) in o {
                match props.get(k) {
                    Some(ps) => self.conforms(x, ps, &format!("{path}.{k}"), errs),
                    None => errs.push(format!("{path}: additional property {k}")),
                }
            }
        }
        if let Value::Array(a) = v {
            if let Some(item) = node.get("items") {
                for (i, x) in a.iter().enumerate() {
                    self.conforms(x, item, &format!("{path}[{i}]"), errs);
                }
            }
        }
    }
}

fn required(node: &Value) -> Vec<String> {
    node.get("required")
        .and_then(|r| r.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default()
}

fn collect_patterns(node: &Value, out: &mut HashMap<String, Regex>) -> Result<(), String> {
    match node {
        Value::Object(o) => {
            if let Some(p) = o.get("pattern").and_then(|p| p.as_str()) {
                if !out.contains_key(p) {
                    let rx = Regex::new(p).map_err(|e| format!("schema pattern {p}: {e}"))?;
                    out.insert(p.to_string(), rx);
                }
            }
            for x in o.values() {
                collect_patterns(x, out)?;
            }
        }
        Value::Array(a) => {
            for x in a {
                collect_patterns(x, out)?;
            }
        }
        _ => {}
    }
    Ok(())
}

/// Serialize exactly like Python `json.dumps(obj, ensure_ascii=False)`: ", " and ": " separators,
/// keys in the value's own order, non-ASCII written raw, control characters as \uXXXX.
pub fn dumps(v: &Value) -> String {
    let mut s = String::new();
    write_value(v, &mut s);
    s
}

fn write_value(v: &Value, out: &mut String) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) => out.push_str(&n.to_string()),
        Value::String(s) => write_str(s, out),
        Value::Array(a) => {
            out.push('[');
            for (i, x) in a.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_value(x, out);
            }
            out.push(']');
        }
        Value::Object(o) => {
            out.push('{');
            for (i, (k, x)) in o.iter().enumerate() {
                if i > 0 {
                    out.push_str(", ");
                }
                write_str(k, out);
                out.push_str(": ");
                write_value(x, out);
            }
            out.push('}');
        }
    }
}

fn write_str(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

/// A lane word (open/done/blocked) or a canonical word, as the canonical word.
pub fn canonical_status(w: &str) -> Option<&'static str> {
    Some(match w {
        "pending" | "open" => "pending",
        "in_progress" => "in_progress",
        "completed" | "done" => "completed",
        "incomplete" | "blocked" => "incomplete",
        "cancelled" => "cancelled",
        _ => return None,
    })
}

/// True for a word only the lane dialect uses.
pub fn lane_word(w: &str) -> bool {
    matches!(w, "open" | "done" | "blocked")
}

pub fn is_iso_date(s: &str) -> bool {
    let b = s.as_bytes();
    b.len() == 10
        && b.iter().enumerate().all(|(i, c)| {
            if i == 4 || i == 7 {
                *c == b'-'
            } else {
                c.is_ascii_digit()
            }
        })
}

/// Today's UTC date as YYYY-MM-DD (civil-from-days, no calendar crate).
pub fn today() -> String {
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0) as i64;
    let z = secs.div_euclid(86_400) + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02}")
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn dumps_matches_python_separators_and_escapes() {
        let v = json!({"b": [1, "x\u{1}\"\\\n"], "a": {}, "c": [], "d": "é\u{2028}", "e": null, "f": true});
        assert_eq!(
            dumps(&v),
            "{\"b\": [1, \"x\\u0001\\\"\\\\\\n\"], \"a\": {}, \"c\": [], \"d\": \"é\u{2028}\", \"e\": null, \"f\": true}"
        );
    }

    #[test]
    fn lane_words_map_and_unknown_words_do_not() {
        assert_eq!(canonical_status("done"), Some("completed"));
        assert_eq!(canonical_status("open"), Some("pending"));
        assert_eq!(canonical_status("blocked"), Some("incomplete"));
        assert_eq!(canonical_status("finished"), None);
        assert!(is_iso_date("2026-10-02") && !is_iso_date("2026-1-02"));
        assert!(is_iso_date(&today()));
    }
}
