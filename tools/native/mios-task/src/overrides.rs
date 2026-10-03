// AI-hint: The TASKS.md operator-overrides block in the dev-loop toolkit's format -- '# TASKS' banner, overrides:begin/end markers, one {"id": ..., field: value} JSON line per override -- validated against the record schema and applied on top of tasks.jsonl.
// AI-related: TASKS.md, tasks.jsonl, /usr/lib/mios/schemas/task-record.schema.json, /usr/share/doc/mios/adr/0028-one-canonical-task-list.md
// AI-functions: parse_block, validate, apply, Effective, override_value

use crate::record::{canonical_status, Schema};
use serde_json::Value;
use std::collections::{BTreeSet, HashMap};

/// The first line of a TASKS.md the dev-loop toolkit reads overrides from; any other first line makes it foreign.
pub const BANNER: &str = "# TASKS";
pub const BEGIN: &str = "<!-- overrides:begin -->";
pub const END: &str = "<!-- overrides:end -->";
/// Record fields an override may not set: identity and history.
pub const FIXED: [&str; 2] = ["id", "provenance"];

pub struct OverrideLine {
    /// 1-based line number in TASKS.md.
    pub n: usize,
    pub raw: String,
    pub value: Option<Value>,
}

pub struct Block {
    /// Bytes strictly between the begin and end marker lines, copied verbatim by render.
    pub inner: String,
    pub lines: Vec<OverrideLine>,
}

/// The JSON text of a block line that is an override: it starts with '{' (or '- {'), as the toolkit reads it.
fn override_text(line: &str) -> Option<&str> {
    let t = line.trim();
    let t = t.strip_prefix("- ").map(str::trim_start).unwrap_or(t);
    t.starts_with('{').then_some(t)
}

/// The block of an existing TASKS.md. Errors name the file line.
pub fn parse_block(doc: &str, md: &str) -> Result<Block, Vec<String>> {
    let lines: Vec<&str> = md.split_inclusive('\n').collect();
    let strip = |l: &str| l.trim_end_matches(['\n', '\r']).to_string();
    if lines.first().map(|l| strip(l)) != Some(BANNER.to_string()) {
        return Err(vec![format!(
            "{doc}:1: does not open with the '{BANNER}' banner, so the dev-loop toolkit would not apply its overrides -- run: mios-task render"
        )]);
    }
    let begins: Vec<usize> = (0..lines.len())
        .filter(|i| strip(lines[*i]) == BEGIN)
        .collect();
    let ends: Vec<usize> = (0..lines.len())
        .filter(|i| strip(lines[*i]) == END)
        .collect();
    let mut errs = Vec::new();
    if begins.len() != 1 {
        errs.push(format!(
            "{doc}: the overrides begin marker appears {} time(s), not once ({BEGIN})",
            begins.len()
        ));
    }
    if ends.len() != 1 {
        errs.push(format!(
            "{doc}: the overrides end marker appears {} time(s), not once ({END})",
            ends.len()
        ));
    }
    if !errs.is_empty() {
        return Err(errs);
    }
    let (b, e) = (begins[0], ends[0]);
    if e < b {
        return Err(vec![format!(
            "{doc}:{}: the overrides end marker comes before the begin marker",
            e + 1
        )]);
    }
    let inner: String = lines[b + 1..e].concat();
    let mut out = Vec::new();
    for (i, l) in lines.iter().enumerate().take(e).skip(b + 1) {
        let raw = strip(l);
        if let Some(t) = override_text(&raw) {
            out.push(OverrideLine {
                n: i + 1,
                value: serde_json::from_str(t).ok(),
                raw,
            });
        }
    }
    Ok(Block { inner, lines: out })
}

/// The value an override sets, as the record would hold it: a status in either dialect becomes the canonical word.
pub fn override_value(field: &str, v: &Value) -> Value {
    if field == "status" {
        if let Some(c) = v.as_str().and_then(canonical_status) {
            return Value::String(c.to_string());
        }
    }
    v.clone()
}

/// Every refusal for the block's lines against the records; each names "<doc>:<line>".
pub fn validate(
    doc: &str,
    schema: &Schema,
    records: &HashMap<String, Value>,
    lines: &[OverrideLine],
) -> Vec<String> {
    let mut errs = Vec::new();
    let props = schema
        .record
        .get("properties")
        .and_then(|p| p.as_object())
        .cloned()
        .unwrap_or_default();
    for l in lines {
        let at = format!("{doc}:{}", l.n);
        let Some(o) = l.value.as_ref().and_then(|v| v.as_object()) else {
            errs.push(format!("{at}: override line is not a JSON object"));
            continue;
        };
        let Some(id) = o.get("id").and_then(|x| x.as_str()) else {
            errs.push(format!("{at}: override needs an \"id\""));
            continue;
        };
        if !records.contains_key(id) {
            errs.push(format!("{at}: override for unknown task {id:?}"));
            continue;
        }
        if o.len() < 2 {
            errs.push(format!("{at}: override of {id} sets no field"));
        }
        for (k, x) in o {
            if k == "id" {
                continue;
            }
            if FIXED.contains(&k.as_str()) {
                errs.push(format!("{at}: {id}.{k} cannot be overridden"));
                continue;
            }
            let Some(node) = props.get(k) else {
                errs.push(format!("{at}: {id}: {k} is not a task record field"));
                continue;
            };
            let mut e = Vec::new();
            schema.conforms(&override_value(k, x), node, &format!("{id}.{k}"), &mut e);
            for x in e {
                errs.push(format!("{at}: {x}"));
            }
            if k == "depends_on" {
                for d in x.as_array().cloned().unwrap_or_default() {
                    let d = d.as_str().unwrap_or("");
                    if !records.contains_key(d) {
                        errs.push(format!("{at}: {id}: depends_on unknown {d}"));
                    }
                }
            }
        }
    }
    errs
}

/// tasks.jsonl as every reader sees it: overrides applied in block order, the last line winning per (id, field).
pub struct Effective {
    pub records: Vec<Value>,
    pub overridden: HashMap<String, BTreeSet<String>>,
}

pub fn apply(records: &[Value], lines: &[OverrideLine]) -> Effective {
    let mut idx: HashMap<String, usize> = HashMap::new();
    for (i, r) in records.iter().enumerate() {
        if let Some(id) = r.get("id").and_then(|x| x.as_str()) {
            idx.entry(id.to_string()).or_insert(i);
        }
    }
    let mut recs = records.to_vec();
    let mut overridden: HashMap<String, BTreeSet<String>> = HashMap::new();
    for l in lines {
        let Some(o) = l.value.as_ref().and_then(|v| v.as_object()) else {
            continue;
        };
        let id = o.get("id").and_then(|x| x.as_str()).unwrap_or("");
        let Some(&i) = idx.get(id) else { continue };
        for (k, x) in o {
            if FIXED.contains(&k.as_str()) {
                continue;
            }
            overridden
                .entry(id.to_string())
                .or_default()
                .insert(k.clone());
            if let Some(m) = recs[i].as_object_mut() {
                m.insert(k.clone(), override_value(k, x));
            }
        }
    }
    Effective {
        records: recs,
        overridden,
    }
}
