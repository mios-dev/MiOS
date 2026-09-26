// AI-hint: mios-task -- sole writer of the canonical task store (ADR-0026): migrate, check-lossless, validate, ready.
// AI-related: /usr/share/mios/mios.toml [tasks.store], /usr/lib/mios/schemas/task-record.schema.json, TASKS.jsonl, /usr/share/doc/mios/adr/0026-global-task-store.md
// AI-functions: main, migrate, check_lossless, validate, ready, parse_markdown, parse_jsonl, heading_fields, body_fields, normalise_status

use regex::Regex;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::OnceLock;

// ---------------------------------------------------------------- config

struct SourceDecl {
    repo: String,
    path: String,
    kind: String,
    fences: bool,   // true only where a list really holds headings inside fenced blocks
    absorbed: bool, // the list was deleted: its bytes live only in the store
}

struct Distinct {
    id: String,
    source: String,
    nth: Option<usize>,
}

struct Config {
    store: String,
    schema: String,
    sources: Vec<SourceDecl>,
    distinct: Vec<Distinct>,
}

fn load_config(root: &Path) -> Result<Config, String> {
    let p = root.join("usr/share/mios/mios.toml");
    let text = fs::read_to_string(&p).map_err(|e| format!("{}: {e}", p.display()))?;
    let doc: toml::Value = text.parse().map_err(|e| format!("{}: {e}", p.display()))?;
    let st = doc
        .get("tasks")
        .and_then(|t| t.get("store"))
        .ok_or("mios.toml has no [tasks.store] -- ADR-0026 declares the store there")?;
    let s = |k: &str| -> Result<String, String> {
        st.get(k)
            .and_then(|v| v.as_str())
            .map(str::to_string)
            .ok_or(format!("[tasks.store].{k} is missing"))
    };
    let mut sources = Vec::new();
    for e in st.get("sources").and_then(|v| v.as_array()).ok_or("[tasks.store].sources is missing")? {
        let g = |k: &str| e.get(k).and_then(|v| v.as_str()).unwrap_or("").to_string();
        let fences = e.get("fences").and_then(|v| v.as_bool()).unwrap_or(false);
        let absorbed = e.get("absorbed").and_then(|v| v.as_bool()).unwrap_or(false);
        sources.push(SourceDecl { repo: g("repo"), path: g("path"), kind: g("kind"), fences, absorbed });
    }
    let mut distinct = Vec::new();
    if let Some(arr) = st.get("distinct").and_then(|v| v.as_array()) {
        for e in arr {
            distinct.push(Distinct {
                id: e.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                source: e.get("source").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                nth: e.get("nth").and_then(|v| v.as_integer()).map(|n| n as usize),
            });
        }
    }
    Ok(Config {
        store: s("path")?,
        schema: s("schema")?,
        sources,
        distinct,
    })
}

// ---------------------------------------------------------------- occurrences

#[derive(Clone)]
struct Occ {
    source: String, // repo-qualified, e.g. "MiOS:TASKS.md"
    off: usize,
    text: String,
    kind: String,
    id: String,
    prec: usize,
    nth: usize,
    fields: Vec<(String, Value)>, // parsed, in source order; typed names are lower-case keys
}

fn re(cell: &'static OnceLock<Regex>, pat: &str) -> &'static Regex {
    cell.get_or_init(|| Regex::new(pat).expect("static regex"))
}

const TASK_ID: &str = r"(?:G2?-TASK \d+|(?:T|AGY|MON|F)-\d+(?:\.\.(?:AGY-)?\d+)?)";

fn heading_start(line: &str, roadmap: bool) -> Option<(usize, String)> {
    static H: OnceLock<Regex> = OnceLock::new();
    static R: OnceLock<Regex> = OnceLock::new();
    let rx = if roadmap {
        re(&R, r"^(###) ([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\.\.\d+)?)(?:\s|$)")
    } else {
        re(&H, &format!(r"^(#{{2,4}}) (?:\[FOLDED\] )?\[?({TASK_ID})\]?(?:[ :\]]|$)"))
    };
    rx.captures(line).map(|c| (c[1].len(), c[2].to_string()))
}

fn heading_level(line: &str) -> Option<usize> {
    let n = line.bytes().take_while(|b| *b == b'#').count();
    if n > 0 && line.as_bytes().get(n) == Some(&b' ') {
        Some(n)
    } else {
        None
    }
}

/// CommonMark fences: 3+ backticks or tildes open; only a bare fence of the same character, as long or longer, closes.
#[derive(Default)]
struct Fence(Option<(u8, usize)>);

impl Fence {
    /// Feed one line; returns true when the line is inside a fence or is a fence line itself.
    fn step(&mut self, line: &str) -> bool {
        let indent = line.len() - line.trim_start_matches(' ').len();
        let t = &line[indent..];
        let ch = t.as_bytes().first().copied().unwrap_or(0);
        let run = if ch == b'`' || ch == b'~' { t.bytes().take_while(|b| *b == ch).count() } else { 0 };
        match self.0 {
            None => {
                if indent <= 3 && run >= 3 && !(ch == b'`' && t[run..].contains('`')) {
                    self.0 = Some((ch, run));
                    return true;
                }
                false
            }
            Some((oc, olen)) => {
                if indent <= 3 && ch == oc && run >= olen && t[run..].trim().is_empty() {
                    self.0 = None;
                }
                true
            }
        }
    }
}

type Unit = Option<(String, String, usize)>; // (kind, id, level); None = passthrough run

fn flush(source: &str, data: &str, cur: &mut Unit, start: usize, end: usize, occs: &mut Vec<Occ>, pass: &mut Vec<(usize, String)>) {
    let unit = cur.take();
    if end <= start {
        return;
    }
    let text = data[start..end].to_string();
    match unit {
        Some((kind, id, _)) => occs.push(Occ {
            source: source.to_string(),
            off: start,
            text,
            kind,
            id,
            prec: 0,
            nth: 0,
            fields: vec![],
        }),
        None => pass.push((start, text)),
    }
}

/// Split a Markdown list into records and passthrough slices that tile the file exactly.
fn parse_markdown(source: &str, data: &str, roadmap: bool, fences: bool) -> (Vec<Occ>, Vec<(usize, String)>) {
    static ROW: OnceLock<Regex> = OnceLock::new();
    static ITEM: OnceLock<Regex> = OnceLock::new();
    let row = re(&ROW, r"^\| (T-\d+) \|");
    let item = re(&ITEM, r"^\* \[[ xX]\] \*\*(M-\d+):");
    let mut occs: Vec<Occ> = Vec::new();
    let mut pass: Vec<(usize, String)> = Vec::new();
    let mut cur: Unit = None;
    let mut start = 0usize;
    let mut fence = Fence::default();
    let mut off = 0usize;
    for line in data.split_inclusive('\n') {
        let l = line.trim_end_matches(['\n', '\r']);
        let t = l.trim_start();
        // A folded heading always starts a record: the notes it wraps can leave a fence unbalanced.
        if fences && l.starts_with("## [FOLDED] [") {
            fence = Fence::default();
        }
        let fenced = fences && !l.starts_with("## [FOLDED] [") && fence.step(l);
        let mut begin: Unit = None;
        let mut ends = false;
        if !fenced {
            if let Some((lvl, id)) = heading_start(l, roadmap) {
                let kind = if roadmap {
                    "roadmap-item"
                } else if l.contains("[FOLDED]") {
                    "folded"
                } else if id.contains("..") {
                    "banner"
                } else {
                    "section"
                };
                begin = Some((kind.into(), id, lvl));
            } else if let Some(c) = row.captures(l) {
                begin = Some(("table-row".into(), c[1].to_string(), 99));
            } else if let Some(c) = item.captures(l) {
                begin = Some(("list-item".into(), c[1].to_string(), 98));
            } else if let Some(lvl) = heading_level(l) {
                if let Some((_, _, cl)) = &cur {
                    if lvl <= *cl || *cl >= 98 {
                        ends = true;
                    }
                }
            } else if let Some((k, _, _)) = &cur {
                // a table row is one line; a list item ends at the next item
                if k == "table-row" || (k == "list-item" && t.starts_with("* [")) {
                    ends = true;
                }
            }
        }
        if begin.is_some() || ends {
            flush(source, data, &mut cur, start, off, &mut occs, &mut pass);
            start = off;
            cur = begin;
        }
        off += line.len();
    }
    flush(source, data, &mut cur, start, off, &mut occs, &mut pass);
    (occs, pass)
}

fn parse_jsonl(source: &str, data: &str) -> Result<(Vec<Occ>, Vec<(usize, String)>), String> {
    let mut occs = Vec::new();
    let mut pass = Vec::new();
    let mut off = 0usize;
    for (n, line) in data.split_inclusive('\n').enumerate() {
        let v: Option<Value> = serde_json::from_str(line.trim_end()).ok();
        match v.as_ref().and_then(|v| v.get("id")).and_then(|i| i.as_str()) {
            Some(id) => occs.push(Occ {
                source: source.into(),
                off,
                text: line.into(),
                kind: "jsonl".into(),
                id: id.to_string(),
                prec: 0,
                nth: 0,
                fields: vec![],
            }),
            None if line.trim().is_empty() => pass.push((off, line.into())),
            None => return Err(format!("{source}:{}: not a JSON object with an id", n + 1)),
        }
        off += line.len();
    }
    Ok((occs, pass))
}

// ---------------------------------------------------------------- field extraction

fn normalise_status(raw: &str) -> &'static str {
    let s = raw.to_lowercase();
    let has = |w: &str| s.contains(w);
    if s.trim().is_empty() {
        "pending"
    } else if has("retired") || has("supersed") || has("skip") || has("cancel") || has("wontfix") || has("obsolete") {
        "cancelled"
    } else if has("broken") || has("blocked") || has("gated-off") || has("deferred") {
        "incomplete"
    } else if has("done") || has("complete") || has("resolved") || s.trim() == "[x]" {
        "completed"
    } else if has("in-progress") || has("in_progress") || has("partial") || has("wip") {
        "in_progress"
    } else {
        "pending"
    }
}

fn js(s: &str) -> Value {
    Value::String(s.to_string())
}

/// Title and decorations from a heading, table row or list line.
fn heading_fields(kind: &str, first: &str) -> Vec<(String, Value)> {
    static SEP: OnceLock<Regex> = OnceLock::new();
    static WS: OnceLock<Regex> = OnceLock::new();
    static DEC: OnceLock<Regex> = OnceLock::new();
    static PRI: OnceLock<Regex> = OnceLock::new();
    static FOLD: OnceLock<Regex> = OnceLock::new();
    let mut f: Vec<(String, Value)> = Vec::new();
    if kind == "table-row" {
        let cells: Vec<&str> = first.trim().trim_matches('|').split('|').map(str::trim).collect();
        if cells.len() >= 3 {
            f.push(("priority".into(), js(cells[1])));
            f.push(("status".into(), js(cells[2])));
            if cells.len() >= 5 {
                f.push(("domain".into(), js(cells[3])));
                f.push(("title".into(), js(&cells[4..].join(" | "))));
            } else if cells.len() == 4 {
                f.push(("title".into(), js(cells[3])));
            }
        }
        return f;
    }
    let mut rest = first.trim_start_matches('#').trim().to_string();
    if kind == "list-item" {
        rest = rest.trim_start_matches("* ").to_string();
        let done = rest.starts_with("[x]") || rest.starts_with("[X]");
        f.push(("status".into(), js(if done { "[x]" } else { "[ ]" })));
        rest = rest.get(3..).unwrap_or("").trim().trim_matches('*').to_string();
    }
    rest = rest.replacen("[FOLDED] ", "", 1);
    let sep = re(
        &SEP,
        &format!(r"^\[?(?:{TASK_ID}|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+(?:\.\.\d+)?)\]?(?:\s*\[[xX ]\])?\s*(?:--|—|:|-)?\s*"),
    );
    if let Some(m) = sep.find(&rest) {
        let head = &rest[..m.end()];
        if head.contains("[x]") || head.contains("[X]") {
            f.push(("status".into(), js("[x]")));
        }
        rest = rest[m.end()..].to_string();
    }
    let fold = re(&FOLD, r"\s*\(Folded [^)]*\)\s*$");
    rest = fold.replace(&rest, "").to_string();
    let dec = re(
        &DEC,
        r"\s*(\*\*\[(?:DONE|x)\]\*\*|\*\*DONE\*\*|\*\*\((?:DONE|RESOLVED)[^)]*\)\*\*|\((?:DONE|RESOLVED)[^)]*\)|\[(?:DONE|BROKEN)\]|\bDONE\b)\s*$",
    );
    while let Some(c) = dec.captures(&rest) {
        f.push(("status".into(), js(&c[1])));
        let at = c.get(0).map(|m| m.start()).unwrap_or(rest.len());
        rest.truncate(at);
    }
    let pri = re(&PRI, r"\s*\*\*\[(P\d)\]\*\*\s*$");
    if let Some(c) = pri.captures(&rest) {
        f.push(("priority".into(), js(&c[1])));
        let at = c.get(0).map(|m| m.start()).unwrap_or(rest.len());
        rest.truncate(at);
    }
    let ws = re(&WS, r"\s*\(([^()|]*?)\s*\|\s*(P\d)\s*\|\s*([A-Z]{1,3})\s*\)\s*$");
    if let Some(c) = ws.captures(&rest) {
        f.push(("workstream".into(), js(c[1].trim())));
        f.push(("priority".into(), js(&c[2])));
        f.push(("size".into(), js(&c[3])));
        let at = c.get(0).map(|m| m.start()).unwrap_or(rest.len());
        rest.truncate(at);
    }
    f.push(("title".into(), js(rest.trim().trim_matches('*').trim())));
    f
}

fn typed_name(key: &str) -> Option<&'static str> {
    Some(match key.to_lowercase().trim() {
        "goal" => "goal",
        "what+how" | "what + how" => "what_how",
        "where" | "files" => "where",
        "why" => "why",
        "do not" => "do_not",
        "done when" | "acceptance criteria" => "done_when",
        "verify" => "verify",
        "dep" | "deps" | "depends" => "deps",
        "status" | "status at fold" => "status",
        "domain" => "domain",
        "who" => "owner",
        "priority" => "priority",
        "effort" | "size" => "size",
        "converted" => "converted",
        _ => return None,
    })
}

/// `**Key:** value` fields from a record body, including several on one line separated by ` | `.
fn body_fields(text: &str) -> Vec<(String, Value)> {
    static START: OnceLock<Regex> = OnceLock::new();
    static SPLIT: OnceLock<Regex> = OnceLock::new();
    let start = re(&START, r"^(?:>\s*|[-*]\s+)?\*\*([A-Za-z][A-Za-z0-9 +/&'().-]{0,40}?):\*\*\s?(.*)$");
    let split = re(&SPLIT, r"\s\|\s(\*\*[A-Za-z][A-Za-z0-9 +/&'().-]{0,40}?:\*\*)");
    let mut out: Vec<(String, String)> = Vec::new();
    let mut fence = Fence::default();
    for line in text.lines().skip(1) {
        let c = if fence.step(line) { None } else { start.captures(line) };
        match c {
            Some(c) => {
                let seg = format!("**{}:** {}", &c[1], &c[2]);
                let marked = split.replace_all(&seg, "\u{1}$1");
                for part in marked.split('\u{1}') {
                    if let Some(cc) = start.captures(part) {
                        out.push((cc[1].to_string(), cc[2].trim().to_string()));
                    }
                }
            }
            None => {
                if let Some(last) = out.last_mut() {
                    last.1.push('\n');
                    last.1.push_str(line);
                }
            }
        }
    }
    out.into_iter()
        .map(|(k, v)| {
            let v = v.trim_end().to_string();
            let name = typed_name(&k).map(str::to_string).unwrap_or_else(|| format!("extra:{k}"));
            (name, js(&v))
        })
        .collect()
}

fn jsonl_fields(id: &str, text: &str) -> Vec<(String, Value)> {
    let v: Value = serde_json::from_str(text.trim_end()).unwrap_or(Value::Null);
    let Some(obj) = v.as_object() else { return vec![] };
    let has_legacy = obj.get("legacy_status").map(|x| x.is_string()).unwrap_or(false);
    let mut f = Vec::new();
    for (k, val) in obj.iter() {
        match k.as_str() {
            "id" => {}
            "title" => {
                let line = format!("## {id} -- {}", val.as_str().unwrap_or(""));
                f.extend(heading_fields("section", &line));
            }
            "legacy_status" if val.is_string() => f.push(("status".into(), val.clone())),
            "status" if !has_legacy => f.push(("status".into(), val.clone())),
            "owner" if val.as_str().map(|s| !s.is_empty()).unwrap_or(false) => f.push(("owner".into(), val.clone())),
            "depends_on" => f.push(("deps".into(), val.clone())),
            "acceptance_criteria" => f.push(("done_when".into(), val.clone())),
            "type" => f.push(("type".into(), val.clone())),
            _ => f.push((format!("extra:{k}"), val.clone())),
        }
    }
    f
}

// ---------------------------------------------------------------- merge

fn sha(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    format!("{:x}", h.finalize())
}

fn id_refs(text: &str) -> Vec<String> {
    static IDS: OnceLock<Regex> = OnceLock::new();
    let rx = re(&IDS, r"\b(?:T|AGY|F|MON|M)-\d+\b");
    let mut seen = HashSet::new();
    rx.find_iter(text).map(|m| m.as_str().to_string()).filter(|s| seen.insert(s.clone())).collect()
}

fn as_lines(v: &Value) -> Vec<String> {
    match v {
        Value::String(s) => s
            .lines()
            .map(|l| l.trim().trim_start_matches(['-', '*']).trim().trim_start_matches("[x] ").trim_start_matches("[ ] ").trim().to_string())
            .filter(|l| !l.is_empty())
            .collect(),
        Value::Array(a) => a.iter().map(|x| x.as_str().map(str::to_string).unwrap_or_else(|| x.to_string())).collect(),
        _ => vec![],
    }
}

fn source_key(repo: &str, path: &str) -> String {
    format!("{repo}:{path}")
}

const TYPED: [&str; 12] = ["title", "status", "priority", "size", "workstream", "domain", "owner", "goal", "what_how", "where", "why", "do_not"];

fn build_record(key: &str, group: &mut [Occ], ids: &HashSet<String>, totals: &HashMap<String, (usize, String)>) -> Value {
    group.sort_by_key(|o| (o.prec, o.off));
    let head = group[0].clone();
    let mut val: BTreeMap<&str, String> = BTreeMap::new();
    let mut conflicts: Vec<Value> = Vec::new();
    let mut extra: Vec<(String, Value)> = Vec::new();
    let mut done_when: Vec<String> = Vec::new();
    let mut verify: Vec<String> = Vec::new();
    let mut deps: Vec<(String, &str)> = Vec::new();
    let mut rtype: Option<String> = None;
    for (i, o) in group.iter().enumerate() {
        for (k, v) in &o.fields {
            if let Some(x) = k.strip_prefix("extra:") {
                // Extras come from the defining occurrence; the others stay verbatim in sources[].
                if i == 0 && !extra.iter().any(|(ek, _)| ek == x) {
                    extra.push((x.to_string(), v.clone()));
                }
                continue;
            }
            match k.as_str() {
                "done_when" => {
                    if done_when.is_empty() {
                        done_when = as_lines(v);
                    }
                }
                "verify" => {
                    if verify.is_empty() {
                        verify = as_lines(v);
                    }
                }
                "deps" => {
                    for t in id_refs(&v.to_string()) {
                        if !deps.iter().any(|(d, _)| *d == t) {
                            deps.push((t, "blocks"));
                        }
                    }
                }
                "converted" => {
                    for t in id_refs(&v.to_string()) {
                        deps.push((t, "converted_to"));
                    }
                }
                "type" => {
                    if rtype.is_none() {
                        rtype = v.as_str().map(str::to_string);
                    }
                }
                kk => {
                    if let Some(name) = TYPED.iter().find(|n| **n == kk) {
                        let s = v.as_str().map(str::to_string).unwrap_or_else(|| v.to_string());
                        match val.get(name) {
                            None => {
                                val.insert(name, s);
                            }
                            Some(prev) if *prev != s && !s.is_empty() => conflicts.push(json!({
                                "field": kk, "source_file": o.source, "value_json": v.to_string()})),
                            _ => {}
                        }
                    }
                }
            }
        }
        if o.kind == "roadmap-item" {
            for t in id_refs(&o.text) {
                if t != o.id && !deps.iter().any(|(d, _)| *d == t) {
                    deps.push((t, "references"));
                }
            }
        }
    }
    let deps: Vec<Value> = deps
        .into_iter()
        .filter(|(t, _)| *t != head.id)
        .map(|(t, ty)| {
            // an undefined target cannot gate readiness
            let ty = if ty == "blocks" && !ids.contains(&t) { "references" } else { ty };
            json!({"id": t, "type": ty})
        })
        .collect();
    let raw = val.get("status").cloned();
    let status = normalise_status(raw.as_deref().unwrap_or(""));
    let rtype = if head.id.contains("..") {
        "epic"
    } else if head.kind == "roadmap-item" {
        "roadmap_item"
    } else {
        match rtype.as_deref() {
            Some("epic") => "epic",
            Some("bug") => "bug",
            _ => "task",
        }
    };
    let g = |k: &str| val.get(k).map(|s| js(s)).unwrap_or(Value::Null);
    let mut m = Map::new();
    m.insert("key".into(), js(key));
    m.insert("id".into(), js(&head.id));
    m.insert("origin".into(), js(&head.source));
    m.insert("type".into(), js(rtype));
    m.insert("title".into(), val.get("title").map(|s| js(s)).unwrap_or(js("")));
    m.insert("status".into(), js(status));
    m.insert("status_raw".into(), raw.map(Value::String).unwrap_or(Value::Null));
    for k in ["priority", "size", "workstream", "domain", "owner", "goal", "what_how", "where", "why", "do_not"] {
        m.insert(k.into(), g(k));
    }
    m.insert("done_when".into(), json!(done_when));
    m.insert("verify".into(), json!(verify));
    m.insert("deps".into(), Value::Array(deps));
    m.insert(
        "extra".into(),
        Value::Array(extra.into_iter().map(|(k, v)| json!({"key": k, "value_json": v.to_string()})).collect()),
    );
    m.insert("conflicts".into(), Value::Array(conflicts));
    m.insert(
        "sources".into(),
        Value::Array(
            group
                .iter()
                .map(|o| {
                    let (n, h) = totals.get(&o.source).cloned().unwrap_or_default();
                    json!({"source_file": o.source, "byte_offset": o.off, "byte_length": o.text.len(),
                           "kind": o.kind, "sha256": sha(&o.text), "source_bytes": n, "source_sha256": h, "text": o.text})
                })
                .collect(),
        ),
    );
    Value::Object(m)
}

fn migrate(root: &Path, repos: &HashMap<String, PathBuf>, cfg: &Config) -> Result<(), String> {
    let mut occs: Vec<Occ> = Vec::new();
    let mut passthrough: Vec<(String, usize, String)> = Vec::new();
    let mut totals: HashMap<String, (usize, String)> = HashMap::new();
    let stored = stored_slices(&root.join(&cfg.store))?;
    let mut parsed: Vec<String> = Vec::new();
    for d in &cfg.sources {
        let key = source_key(&d.repo, &d.path);
        if parsed.contains(&key) {
            continue; // one file, one parse: TASKS.md is declared once per kind
        }
        parsed.push(key.clone());
        let base = repos.get(&d.repo).ok_or(format!("no checkout for repo {} (pass --repo {}=PATH)", d.repo, d.repo))?;
        let p = base.join(&d.path);
        let data = if d.absorbed && p.exists() {
            return Err(format!("{key} was absorbed into {} but exists again; delete it (the store holds every byte)", cfg.store));
        } else if d.absorbed || !p.exists() {
            // Absorbed lists, and sibling checkouts that are not present, are rebuilt from the store's own slices.
            rematerialize(&key, &stored).map_err(|e| format!("{key} is not on disk and {e}"))?
        } else {
            let bytes = fs::read(&p).map_err(|e| format!("{}: {e}", p.display()))?;
            String::from_utf8(bytes).map_err(|_| format!("{key}: not UTF-8; refusing, a lossy decode would drop bytes"))?
        };
        totals.insert(key.clone(), (data.len(), sha(&data)));
        let (o, pt) = if d.path.ends_with(".jsonl") {
            parse_jsonl(&key, &data)?
        } else {
            parse_markdown(&key, &data, d.repo == "MiOS" && d.path == "ROADMAP.md", d.fences)
        };
        occs.extend(o);
        passthrough.extend(pt.into_iter().map(|(off, t)| (key.clone(), off, t)));
    }
    let mut nth: HashMap<(String, String, String), usize> = HashMap::new();
    for o in occs.iter_mut() {
        let exact = cfg.sources.iter().position(|d| source_key(&d.repo, &d.path) == o.source && d.kind == o.kind);
        o.prec = exact
            .or_else(|| cfg.sources.iter().position(|d| source_key(&d.repo, &d.path) == o.source))
            .unwrap_or(usize::MAX);
        let class = if o.kind == "banner" { "section".to_string() } else { o.kind.clone() };
        let c = nth.entry((o.source.clone(), class, o.id.clone())).or_insert(0);
        *c += 1;
        o.nth = *c;
        let first = o.text.lines().next().unwrap_or("").to_string();
        o.fields = match o.kind.as_str() {
            "jsonl" => jsonl_fields(&o.id, &o.text),
            "table-row" => heading_fields("table-row", &first),
            k => {
                let mut f = heading_fields(k, &first);
                f.extend(body_fields(&o.text));
                f
            }
        };
    }
    let key_of = |o: &Occ| -> String {
        for d in &cfg.distinct {
            if d.id == o.id && d.source == o.source {
                match d.nth {
                    Some(n) if n == o.nth => return format!("{}#{}", o.id, n),
                    None => return format!("{}#{}", o.source, o.id),
                    _ => {}
                }
            }
        }
        o.id.clone()
    };
    let ids: HashSet<String> = occs.iter().map(|o| o.id.clone()).collect();
    let mut groups: BTreeMap<String, Vec<Occ>> = BTreeMap::new();
    for o in &occs {
        groups.entry(key_of(o)).or_default().push(o.clone());
    }
    // Non-task text rides on the record before it (or the first record of its file), so one file holds every byte.
    for (src, off, text) in &passthrough {
        let same: Vec<&Occ> = occs.iter().filter(|o| o.source == *src).collect();
        let host = same.iter().filter(|o| o.off < *off).max_by_key(|o| o.off).or_else(|| same.iter().min_by_key(|o| o.off));
        let Some(host) = host else { return Err(format!("{src} has no task record to carry its non-task text")) };
        let o = Occ { source: src.clone(), off: *off, text: text.clone(), kind: "passthrough".into(), id: host.id.clone(),
                      prec: usize::MAX, nth: 0, fields: vec![] };
        groups.entry(key_of(host)).or_default().push(o);
    }
    let mut records: Vec<((usize, usize), Value)> = groups
        .iter_mut()
        .map(|(k, g)| {
            let r = build_record(k, g, &ids, &totals);
            ((g[0].prec, g[0].off), r)
        })
        .collect();
    records.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1["key"].as_str().cmp(&b.1["key"].as_str())));
    let mut out = String::new();
    for (_, v) in &records {
        out.push_str(&serde_json::to_string(v).map_err(|e| e.to_string())?);
        out.push('\n');
    }
    write_atomic(&root.join(&cfg.store), &out)?;
    let conflicts: usize = records.iter().map(|r| r.1["conflicts"].as_array().map_or(0, |a| a.len())).sum();
    println!(
        "migrate: {} record(s) from {} occurrence(s) in {} source(s); {} non-task slice(s) carried; {} conflict(s) listed",
        records.len(),
        occs.len(),
        parsed.len(),
        passthrough.len(),
        conflicts
    );
    Ok(())
}

fn write_atomic(p: &Path, s: &str) -> Result<(), String> {
    if let Some(d) = p.parent() {
        fs::create_dir_all(d).map_err(|e| format!("{}: {e}", d.display()))?;
    }
    let tmp = p.with_extension("tmp");
    fs::write(&tmp, s).map_err(|e| format!("{}: {e}", tmp.display()))?;
    fs::rename(&tmp, p).map_err(|e| format!("{}: {e}", p.display()))
}

// ---------------------------------------------------------------- checks

fn read_jsonl(p: &Path) -> Result<Vec<Value>, String> {
    let t = fs::read_to_string(p).map_err(|e| format!("{}: {e}", p.display()))?;
    t.lines()
        .enumerate()
        .map(|(n, l)| serde_json::from_str(l).map_err(|e| format!("{}:{}: {e}", p.display(), n + 1)))
        .collect()
}

type Slices = HashMap<String, Vec<(usize, String, String, String, usize, String)>>; // src -> (off, text, sha, key, total, total_sha)

fn stored_slices(store: &Path) -> Result<Slices, String> {
    let mut out: Slices = HashMap::new();
    if !store.exists() {
        return Ok(out);
    }
    for r in read_jsonl(store)? {
        let key = r["key"].as_str().unwrap_or("?").to_string();
        for s in r["sources"].as_array().cloned().unwrap_or_default() {
            out.entry(s["source_file"].as_str().unwrap_or("").to_string()).or_default().push((
                s["byte_offset"].as_u64().unwrap_or(0) as usize,
                s["text"].as_str().unwrap_or("").to_string(),
                s["sha256"].as_str().unwrap_or("").to_string(),
                key.clone(),
                s["source_bytes"].as_u64().unwrap_or(0) as usize,
                s["source_sha256"].as_str().unwrap_or("").to_string(),
            ));
        }
    }
    Ok(out)
}

/// Rebuild one source list byte-for-byte from its slices; any gap, overlap or hash mismatch is an error naming it.
fn rematerialize(src: &str, all: &Slices) -> Result<String, String> {
    let mut v = all.get(src).cloned().ok_or(format!("the store holds no slice of {src}"))?;
    v.sort_by_key(|x| x.0);
    let (want, want_sha) = (v[0].4, v[0].5.clone());
    let (mut pos, mut prev, mut out) = (0usize, "(file start)".to_string(), String::new());
    for (off, text, s, owner, n, h) in &v {
        if (*n, h) != (want, &want_sha) {
            return Err(format!("LOSSY: {src}: {owner} records a different size or hash for the source"));
        }
        if sha(text) != *s {
            return Err(format!("LOSSY: {src}: {owner} slice at offset {off} fails its sha256"));
        }
        if *off != pos {
            let n = if *off > pos { off - pos } else { pos - off };
            return Err(format!("LOSSY: {src}: {n} byte(s) at offset {pos} not covered (after {prev})"));
        }
        out.push_str(text);
        pos += text.len();
        prev = owner.clone();
    }
    if pos != want {
        return Err(format!("LOSSY: {src}: {} byte(s) at offset {pos} not covered (after {prev})", want.saturating_sub(pos)));
    }
    if sha(&out) != want_sha {
        return Err(format!("LOSSY: {src}: the rebuilt bytes differ from the recorded sha256"));
    }
    Ok(out)
}

fn check_lossless(root: &Path, cfg: &Config) -> Result<bool, String> {
    let all = stored_slices(&root.join(&cfg.store))?;
    let mut ok = true;
    let mut srcs: Vec<&String> = all.keys().collect();
    srcs.sort();
    for src in srcs {
        match rematerialize(src, &all) {
            Ok(b) => println!("LOSSLESS: {src}: {} bytes", b.len()),
            Err(e) => {
                println!("{e}");
                ok = false;
            }
        }
    }
    // Freshness: a live list in this tree must still hash to what was migrated; an absorbed list must stay gone.
    let mut seen = HashSet::new();
    for d in cfg.sources.iter().filter(|d| d.repo == "MiOS") {
        let key = source_key(&d.repo, &d.path);
        if !seen.insert(key.clone()) {
            continue;
        }
        let want = all.get(&key).and_then(|v| v.first()).map(|x| x.5.clone()).unwrap_or_default();
        match (d.absorbed, fs::read(root.join(&d.path))) {
            (true, Ok(_)) => {
                println!("REAPPEARED: {key} exists again -- its tasks live in {}; delete it", cfg.store);
                ok = false;
            }
            (true, Err(_)) => {}
            (false, Ok(b)) if format!("{:x}", Sha256::digest(&b)) == want => {}
            (false, Ok(_)) => {
                println!("STALE: {key} changed after the store was migrated -- rerun: mios-task migrate");
                ok = false;
            }
            (false, Err(_)) => {
                println!("STALE: {key} is gone, but the store still records it -- rerun: mios-task migrate");
                ok = false;
            }
        }
    }
    Ok(ok)
}

/// JSON-schema check for the strict subset the store schema uses.
fn conforms(v: &Value, s: &Value, path: &str, errs: &mut Vec<String>) {
    if errs.len() > 20 {
        return;
    }
    let types: Vec<&str> = match &s["type"] {
        Value::String(t) => vec![t.as_str()],
        Value::Array(a) => a.iter().filter_map(|x| x.as_str()).collect(),
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
    if !types.is_empty() && !types.contains(&actual) {
        errs.push(format!("{path}: {actual} where the schema wants {types:?}"));
        return;
    }
    if let (Some(e), Some(x)) = (s["enum"].as_array(), v.as_str()) {
        if !e.iter().any(|y| y.as_str() == Some(x)) {
            errs.push(format!("{path}: {x:?} is not in the enum"));
        }
    }
    if let (Some(min), Some(n)) = (s["minimum"].as_i64(), v.as_i64()) {
        if n < min {
            errs.push(format!("{path}: {n} < {min}"));
        }
    }
    if let Value::Object(o) = v {
        let props = s["properties"].as_object().cloned().unwrap_or_default();
        for r in s["required"].as_array().cloned().unwrap_or_default() {
            if let Some(r) = r.as_str() {
                if !o.contains_key(r) {
                    errs.push(format!("{path}: missing required {r}"));
                }
            }
        }
        for (k, x) in o {
            match props.get(k) {
                Some(ps) => conforms(x, ps, &format!("{path}.{k}"), errs),
                None => errs.push(format!("{path}: unknown property {k}")),
            }
        }
    }
    if let Value::Array(a) = v {
        if let Some(mi) = s["minItems"].as_u64() {
            if (a.len() as u64) < mi {
                errs.push(format!("{path}: fewer than {mi} item(s)"));
            }
        }
        for (i, x) in a.iter().enumerate() {
            conforms(x, &s["items"], &format!("{path}[{i}]"), errs);
        }
    }
}

fn validate(root: &Path, cfg: &Config) -> Result<bool, String> {
    let stext = fs::read_to_string(root.join(&cfg.schema)).map_err(|e| format!("{}: {e}", cfg.schema))?;
    let doc: Value = serde_json::from_str(&stext).map_err(|e| e.to_string())?;
    let schema = &doc["schema"];
    let recs = read_jsonl(&root.join(&cfg.store))?;
    let ids: HashSet<String> = recs.iter().filter_map(|r| r["id"].as_str().map(str::to_string)).collect();
    let mut keys = HashSet::new();
    let mut ok = true;
    for r in &recs {
        let key = r["key"].as_str().unwrap_or("?").to_string();
        let mut errs = Vec::new();
        conforms(r, schema, &key, &mut errs);
        for e in errs {
            println!("INVALID: {e}");
            ok = false;
        }
        if !keys.insert(key.clone()) {
            println!("INVALID: duplicate key {key}");
            ok = false;
        }
        for s in r["sources"].as_array().cloned().unwrap_or_default() {
            if sha(s["text"].as_str().unwrap_or("")) != s["sha256"].as_str().unwrap_or("") {
                println!("INVALID: {key}: a source slice fails its sha256");
                ok = false;
            }
        }
        for d in r["deps"].as_array().cloned().unwrap_or_default() {
            if d["type"] == "blocks" && !ids.contains(d["id"].as_str().unwrap_or("")) {
                println!("INVALID: {key}: blocks {} which no record defines", d["id"]);
                ok = false;
            }
        }
    }
    if ok {
        println!("valid: {} record(s), {} unique key(s)", recs.len(), keys.len());
    }
    Ok(ok)
}

fn ready(root: &Path, cfg: &Config, as_json: bool) -> Result<(), String> {
    let recs = read_jsonl(&root.join(&cfg.store))?;
    let done: HashSet<&str> = recs
        .iter()
        .filter(|r| r["status"] == "completed" || r["status"] == "cancelled")
        .filter_map(|r| r["id"].as_str())
        .collect();
    let out: Vec<Value> = recs
        .iter()
        .filter(|r| r["status"] == "pending")
        .filter(|r| {
            r["deps"].as_array().map_or(true, |d| {
                d.iter().all(|e| e["type"] != "blocks" || done.contains(e["id"].as_str().unwrap_or("")))
            })
        })
        .map(|r| json!({"key": r["key"], "id": r["id"], "priority": r["priority"], "title": r["title"]}))
        .collect();
    if as_json {
        println!("{}", serde_json::to_string(&out).map_err(|e| e.to_string())?);
    } else {
        for r in &out {
            println!(
                "{}\t{}\t{}",
                r["key"].as_str().unwrap_or(""),
                r["priority"].as_str().unwrap_or("-"),
                r["title"].as_str().unwrap_or("")
            );
        }
    }
    Ok(())
}

// ---------------------------------------------------------------- main

fn usage() -> ExitCode {
    eprintln!("usage: mios-task <migrate|validate|check-lossless|ready [--json]|source SRC> [--root DIR] [--repo NAME=PATH]...");
    ExitCode::from(64)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some(cmd) = args.first().cloned() else { return usage() };
    let mut root = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let mut repos: HashMap<String, PathBuf> = HashMap::new();
    let mut as_json = false;
    let mut src_arg: Option<String> = None;
    let mut i = 1;
    if cmd == "source" {
        src_arg = args.get(1).cloned();
        i = 2;
    }
    while i < args.len() {
        match args[i].as_str() {
            "--root" if i + 1 < args.len() => {
                root = PathBuf::from(&args[i + 1]);
                i += 1;
            }
            "--repo" if i + 1 < args.len() => {
                if let Some((n, p)) = args[i + 1].split_once('=') {
                    repos.insert(n.to_string(), PathBuf::from(p));
                }
                i += 1;
            }
            "--json" => as_json = true,
            _ => return usage(),
        }
        i += 1;
    }
    repos.entry("MiOS".into()).or_insert_with(|| root.clone());
    if let Some(parent) = root.parent() {
        for n in ["-dev-loop", "mios-micro", "mios-bootstrap"] {
            repos.entry(n.into()).or_insert_with(|| parent.join(n));
        }
    }
    let cfg = match load_config(&root) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("mios-task: {e}");
            return ExitCode::from(2);
        }
    };
    let r = match cmd.as_str() {
        "migrate" => migrate(&root, &repos, &cfg).map(|_| true),
        "check-lossless" => check_lossless(&root, &cfg),
        "validate" => validate(&root, &cfg),
        "ready" => ready(&root, &cfg, as_json).map(|_| true),
        "source" => {
            // Print one merged list exactly as it was, e.g. `mios-task source MiOS:TASKS.md`.
            let Some(src) = src_arg else { return usage() };
            stored_slices(&root.join(&cfg.store)).and_then(|all| rematerialize(&src, &all)).map(|b| {
                print!("{b}");
                true
            })
        }
        _ => return usage(),
    };
    match r {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::from(1),
        Err(e) => {
            eprintln!("mios-task: {e}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = "# Title\n\n| T-001 | P1 | done | D | first |\n| T-002 | P2 | open | D | second |\n\n## T-001 -- First task  (WS-A | P1 | M)\n**Goal:** g\n**Status:** done | **Domain:** D | **Who:** ops\n```\n## T-777 inside a fence\n```\n## AGY-5 -- Fifth  (WS-B | P2 | S)**[DONE]**\n```\n## AGY-6 -- after a stray fence\n* [x] **M-01: micro**\n  body\n* [ ] **M-02: open**\n";

    fn tile(occ: &[Occ], pass: &[(usize, String)]) -> String {
        let mut v: Vec<(usize, &str)> = occ.iter().map(|o| (o.off, o.text.as_str())).collect();
        v.extend(pass.iter().map(|(o, t)| (*o, t.as_str())));
        v.sort_by_key(|x| x.0);
        v.into_iter().map(|x| x.1).collect()
    }

    #[test]
    fn markdown_slices_tile_the_file_and_a_stray_fence_hides_nothing() {
        let (occ, pass) = parse_markdown("MiOS:X.md", SAMPLE, false, false);
        assert_eq!(tile(&occ, &pass), SAMPLE);
        let ids: Vec<&str> = occ.iter().map(|o| o.id.as_str()).collect();
        assert_eq!(ids, ["T-001", "T-002", "T-001", "T-777", "AGY-5", "AGY-6", "M-01", "M-02"]);
        let (occ, _) = parse_markdown("MiOS:X.md", SAMPLE, false, true);
        assert!(!occ.iter().any(|o| o.id == "T-777"), "a fenced heading must stay body text when fences are honoured");
    }

    #[test]
    fn fence_closes_only_on_a_bare_fence_of_the_same_kind() {
        let mut f = Fence::default();
        assert!(f.step("```text"));
        assert!(f.step("```bash"));
        assert!(f.step("~~~"));
        assert!(f.step("```"));
        assert!(!f.step("## AGY-1 -- after"));
    }

    #[test]
    fn headings_rows_and_items_parse_their_decorations() {
        let f = heading_fields("section", "## AGY-5 -- Fifth  (WS-B | P2 | S)**[DONE]**");
        let get = |k: &str| f.iter().find(|x| x.0 == k).map(|x| x.1.as_str().unwrap_or("").to_string());
        assert_eq!(get("title").as_deref(), Some("Fifth"));
        assert_eq!(get("status").as_deref(), Some("**[DONE]**"));
        assert_eq!((get("workstream").as_deref(), get("priority").as_deref(), get("size").as_deref()), (Some("WS-B"), Some("P2"), Some("S")));
        let r = heading_fields("table-row", "| T-259 | P1 | open | Dom | a | b |");
        assert_eq!(r.last().unwrap().1, "a | b");
        let m = heading_fields("list-item", "* [x] **M-01: micro**");
        assert_eq!(m[0].1, "[x]");
        assert_eq!(m.last().unwrap().1, "micro");
        let body = body_fields("h\n**Status:** done | **Domain:** D | **Who:** ops\n**Goal:** a\nb\n");
        assert_eq!(body.iter().map(|x| x.0.as_str()).collect::<Vec<_>>(), ["status", "domain", "owner", "goal"]);
        assert_eq!(body[3].1, "a\nb");
    }

    #[test]
    fn statuses_normalise_to_the_openai_words() {
        for (raw, want) in [("done-by-code", "completed"), ("**[DONE]**", "completed"), ("[x]", "completed"), ("open", "pending"),
                            ("planned", "pending"), ("in-progress", "in_progress"), ("partial", "in_progress"), ("[BROKEN]", "incomplete"),
                            ("built-gated-off", "incomplete"), ("retired", "cancelled"), ("SUPERSEDED / SKIP", "cancelled"), ("", "pending")] {
            assert_eq!(normalise_status(raw), want, "{raw}");
        }
    }

    fn sandbox(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("mios-task-test-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(d.join("usr/share/mios")).unwrap();
        fs::create_dir_all(d.join("usr/lib/mios/schemas")).unwrap();
        let schema = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../usr/lib/mios/schemas/task-record.schema.json");
        fs::copy(schema, d.join("usr/lib/mios/schemas/task-record.schema.json")).unwrap();
        fs::write(d.join("usr/share/mios/mios.toml"), "[tasks.store]\npath = \"TASKS.jsonl\"\nschema = \"usr/lib/mios/schemas/task-record.schema.json\"\nsources = [ { repo = \"MiOS\", path = \"TASKS.md\", kind = \"section\" } ]\n").unwrap();
        fs::write(d.join("TASKS.md"), SAMPLE).unwrap();
        d
    }

    fn run(root: &Path) -> Config {
        let cfg = load_config(root).unwrap();
        let repos = HashMap::from([("MiOS".to_string(), root.to_path_buf())]);
        migrate(root, &repos, &cfg).unwrap();
        cfg
    }

    #[test]
    fn migrate_is_lossless_and_valid() {
        let d = sandbox("ok");
        let cfg = run(&d);
        assert!(check_lossless(&d, &cfg).unwrap());
        assert!(validate(&d, &cfg).unwrap());
    }

    #[test]
    fn a_shortened_slice_is_lossy() {
        let d = sandbox("short");
        let cfg = run(&d);
        let p = d.join(&cfg.store);
        let t = fs::read_to_string(&p).unwrap();
        let planted: Vec<String> = t
            .lines()
            .map(|l| {
                let mut r: Value = serde_json::from_str(l).unwrap();
                if r["key"] == "AGY-5" {
                    let s = &mut r["sources"][0];
                    let short = s["text"].as_str().unwrap().replace("**[DONE]**", "");
                    s["sha256"] = json!(sha(&short));
                    s["byte_length"] = json!(short.len());
                    s["text"] = json!(short);
                }
                serde_json::to_string(&r).unwrap()
            })
            .collect();
        fs::write(&p, planted.join("\n") + "\n").unwrap();
        assert!(!check_lossless(&d, &cfg).unwrap(), "a slice planted short must be LOSSY");
    }

    #[test]
    fn an_edited_source_is_stale_and_a_duplicate_key_is_invalid() {
        let d = sandbox("stale");
        let cfg = run(&d);
        fs::write(d.join("TASKS.md"), format!("{SAMPLE}| T-009 | P3 | open | D | planted |\n")).unwrap();
        assert!(!check_lossless(&d, &cfg).unwrap(), "an edit after migrate must be STALE");
        let p = d.join(&cfg.store);
        let t = fs::read_to_string(&p).unwrap();
        let first = t.lines().next().unwrap().to_string();
        fs::write(&p, format!("{t}{first}\n")).unwrap();
        assert!(!validate(&d, &cfg).unwrap(), "a duplicate key must be INVALID");
    }

    #[test]
    fn an_absorbed_list_is_rebuilt_from_the_store_and_may_not_reappear() {
        let d = sandbox("absorbed");
        run(&d);
        fs::remove_file(d.join("TASKS.md")).unwrap();
        let toml = d.join("usr/share/mios/mios.toml");
        let t = fs::read_to_string(&toml).unwrap().replace("kind = \"section\" }", "kind = \"section\", absorbed = true }");
        fs::write(&toml, t).unwrap();
        let cfg = run(&d); // re-migrates from the store's own slices
        assert!(check_lossless(&d, &cfg).unwrap());
        let all = stored_slices(&d.join(&cfg.store)).unwrap();
        assert_eq!(rematerialize("MiOS:TASKS.md", &all).unwrap(), SAMPLE, "the absorbed list must come back byte-identical");
        fs::write(d.join("TASKS.md"), "stub\n").unwrap();
        assert!(!check_lossless(&d, &cfg).unwrap(), "a re-created absorbed list must be REAPPEARED");
    }
}
