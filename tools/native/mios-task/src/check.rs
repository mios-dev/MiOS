// AI-hint: `mios-task check` -- schema, uniqueness, depends_on/epic resolution, cycles, evidence, born-record shape, canonical serialization, hygiene, overrides, retired stores, frozen history, the migrated count, and TASKS.md == render.
// AI-related: tasks.jsonl, TASKS.md, /usr/lib/mios/schemas/task-record.schema.json, /usr/share/mios/mios.toml [tasks.store], automation/98-drift-checks.sh
// AI-functions: State::load, check, hygiene, cycles, retired_stores, first_difference

use crate::frozen;
use crate::overrides::{self, Block, Effective};
use crate::record::{dumps, lane_word, Schema};
use crate::store::{Line, Store};
use regex::Regex;
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::OnceLock;

/// The dev-loop toolkit's status-dialect marker line; not a task. Only the OpenAI dialect is MiOS's.
pub const DIALECT_KEY: &str = "_dialect";

pub fn is_marker(v: &Value) -> bool {
    v.as_object()
        .is_some_and(|o| o.len() == 1 && o.contains_key(DIALECT_KEY))
}

/// Everything a reader needs: the lines, their parses, the schema, and TASKS.md with its block.
pub struct State {
    pub lines: Vec<Line>,
    pub records: Vec<Value>,
    pub schema: Schema,
    pub md: Option<String>,
    pub block: Result<Block, Vec<String>>,
}

impl State {
    pub fn load(st: &Store) -> Result<State, String> {
        let schema = Schema::load(&st.schema_file())?;
        let lines = st.read()?;
        let records = lines
            .iter()
            .filter_map(|l| l.value.clone())
            .filter(|v| !is_marker(v))
            .collect();
        let md = fs::read_to_string(st.doc_file()).ok();
        let block = match &md {
            Some(t) => overrides::parse_block(&st.doc, t),
            None => Err(vec![format!(
                "{} is missing -- run: mios-task render",
                st.doc
            )]),
        };
        Ok(State {
            lines,
            records,
            schema,
            md,
            block,
        })
    }

    pub fn override_lines(&self) -> &[overrides::OverrideLine] {
        match &self.block {
            Ok(b) => &b.lines,
            Err(_) => &[],
        }
    }

    pub fn effective(&self) -> Effective {
        overrides::apply(&self.records, self.override_lines())
    }

    pub fn by_id(&self) -> HashMap<String, Value> {
        let mut m = HashMap::new();
        for r in &self.records {
            if let Some(id) = r.get("id").and_then(|x| x.as_str()) {
                m.entry(id.to_string()).or_insert_with(|| r.clone());
            }
        }
        m
    }

    /// The bytes render keeps between the markers: the existing block, or the one-comment default.
    pub fn inner(&self) -> String {
        match &self.block {
            Ok(b) => b.inner.clone(),
            _ => overrides::empty_block(),
        }
    }
}

fn id_of(v: &Value) -> &str {
    v.get("id").and_then(|x| x.as_str()).unwrap_or("?")
}

fn hygiene_rx() -> &'static Regex {
    static R: OnceLock<Regex> = OnceLock::new();
    R.get_or_init(|| {
        // A Temp *path* (after a separator), not the English word; a session id is a UUID.
        Regex::new(r"AppData|[\\/]Temp\b|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
            .expect("static regex")
    })
}

fn walk_strings(v: &Value, path: &str, out: &mut Vec<(String, String)>) {
    match v {
        Value::String(s) => out.push((path.to_string(), s.clone())),
        Value::Array(a) => {
            for (i, x) in a.iter().enumerate() {
                walk_strings(x, &format!("{path}[{i}]"), out);
            }
        }
        Value::Object(o) => {
            for (k, x) in o {
                let p = if path.is_empty() {
                    k.clone()
                } else {
                    format!("{path}.{k}")
                };
                walk_strings(x, &p, out);
            }
        }
        _ => {}
    }
}

/// Coordination hygiene: no AppData/Temp path or session UUID in a live record field or an override line.
/// Frozen provenance is history and is checked as the rebuilt lists (`mios-task source`), not here.
pub fn hygiene(state: &State, doc: &str) -> Vec<String> {
    let rx = hygiene_rx();
    let mut out = Vec::new();
    for r in &state.records {
        let mut strs = Vec::new();
        if let Some(o) = r.as_object() {
            for (k, x) in o {
                if k != "provenance" {
                    walk_strings(x, k, &mut strs);
                }
            }
        }
        for (p, s) in strs {
            if let Some(m) = rx.find(&s) {
                out.push(format!(
                    "{}: {p} contains an AppData/Temp path or session id ({:?})",
                    id_of(r),
                    m.as_str()
                ));
            }
        }
    }
    for l in state.override_lines() {
        if let Some(m) = rx.find(&l.raw) {
            out.push(format!(
                "{doc}:{}: override line contains an AppData/Temp path or session id ({:?})",
                l.n,
                m.as_str()
            ));
        }
    }
    out
}

/// A directory entry named exactly `name` (case-sensitive even on a case-insensitive filesystem).
fn entry_exists(root: &Path, rel: &str) -> bool {
    let p = root.join(rel);
    let (Some(dir), Some(name)) = (p.parent(), p.file_name()) else {
        return false;
    };
    fs::read_dir(dir)
        .map(|rd| rd.flatten().any(|e| e.file_name() == name))
        .unwrap_or(false)
}

/// The retired stores declared in the SSOT, plus any file named like the canonical list (any case) at the
/// root or one directory down: each is a second task list.
pub fn retired_stores(st: &Store) -> Vec<String> {
    let mut out = Vec::new();
    let mut named: HashSet<std::path::PathBuf> = HashSet::new();
    for rel in &st.retired {
        if entry_exists(&st.root, rel) {
            named.insert(st.root.join(rel));
            out.push(format!(
                "retired task store present: {rel} -- {} is the only task list (ADR-0028); move its change into {} and delete it",
                st.path, st.path
            ));
        }
    }
    let want = Path::new(&st.path)
        .file_name()
        .map(|n| n.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    let canonical_name = Path::new(&st.path).file_name().map(|n| n.to_os_string());
    let mut dirs = vec![st.root.clone()];
    if let Ok(rd) = fs::read_dir(&st.root) {
        let mut subs: Vec<_> = rd
            .flatten()
            .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
            .map(|e| e.path())
            .collect();
        subs.sort();
        dirs.extend(subs);
    }
    for d in dirs {
        let Ok(rd) = fs::read_dir(&d) else { continue };
        let mut hits: Vec<_> = rd
            .flatten()
            .filter(|e| e.file_name().to_string_lossy().to_lowercase() == want)
            .filter(|e| !(d == st.root && Some(e.file_name()) == canonical_name))
            .map(|e| e.path())
            .filter(|p| !named.contains(p))
            .collect();
        hits.sort();
        for p in hits {
            let rel = p.strip_prefix(&st.root).unwrap_or(&p).display().to_string();
            out.push(format!(
                "second task store present: {rel} -- {} is the only task list (ADR-0028); delete it",
                st.path
            ));
        }
    }
    out
}

/// Strongly connected components of size > 1 (or a self-edge) in the depends_on graph.
pub fn cycles(recs: &[Value]) -> Vec<Vec<String>> {
    let ids: Vec<String> = recs.iter().map(|r| id_of(r).to_string()).collect();
    let pos: HashMap<&str, usize> = ids
        .iter()
        .enumerate()
        .map(|(i, s)| (s.as_str(), i))
        .collect();
    let adj: Vec<Vec<usize>> = recs
        .iter()
        .map(|r| {
            r.get("depends_on")
                .and_then(|d| d.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().and_then(|s| pos.get(s).copied()))
                        .collect()
                })
                .unwrap_or_default()
        })
        .collect();
    // Iterative Tarjan.
    let n = recs.len();
    let (mut index, mut low, mut on) = (vec![usize::MAX; n], vec![0; n], vec![false; n]);
    let (mut stack, mut next, mut out) = (Vec::new(), 0usize, Vec::new());
    for s in 0..n {
        if index[s] != usize::MAX {
            continue;
        }
        let mut call: Vec<(usize, usize)> = vec![(s, 0)];
        index[s] = next;
        low[s] = next;
        next += 1;
        stack.push(s);
        on[s] = true;
        while let Some(&mut (v, ref mut ei)) = call.last_mut() {
            if *ei < adj[v].len() {
                let w = adj[v][*ei];
                *ei += 1;
                if index[w] == usize::MAX {
                    index[w] = next;
                    low[w] = next;
                    next += 1;
                    stack.push(w);
                    on[w] = true;
                    call.push((w, 0));
                } else if on[w] {
                    low[v] = low[v].min(index[w]);
                }
            } else {
                call.pop();
                if let Some(&(p, _)) = call.last() {
                    low[p] = low[p].min(low[v]);
                }
                if low[v] == index[v] {
                    let mut comp = Vec::new();
                    while let Some(w) = stack.pop() {
                        on[w] = false;
                        comp.push(ids[w].clone());
                        if w == v {
                            break;
                        }
                    }
                    if comp.len() > 1 || adj[v].contains(&v) {
                        comp.sort();
                        out.push(comp);
                    }
                }
            }
        }
    }
    out.sort();
    out
}

/// The first differing line (1-based) and that line of `a`, or None when the texts are equal.
pub fn first_difference(a: &str, b: &str) -> Option<(usize, String)> {
    let (mut la, mut lb) = (a.lines(), b.lines());
    let mut n = 0;
    loop {
        n += 1;
        match (la.next(), lb.next()) {
            (None, None) => {
                return if a == b {
                    None
                } else {
                    Some((n, String::new()))
                }
            }
            (x, y) if x != y => return Some((n, x.unwrap_or("").to_string())),
            _ => {}
        }
    }
}

/// Every problem in the canonical list, its overrides and its rendered doc. Empty means clean.
pub fn check(st: &Store, state: &State, only: Option<&str>) -> Vec<String> {
    let mut p = Vec::new();
    if only == Some("hygiene") {
        p.extend(hygiene(state, &st.doc));
        return p;
    }
    p.extend(retired_stores(st));
    let node = &state.schema.record;
    let mut seen: HashSet<String> = HashSet::new();
    let mut migrated = 0usize;
    for l in &state.lines {
        let Some(v) = &l.value else {
            p.push(format!(
                "{}:{}: not JSON ({})",
                st.path,
                l.n,
                l.error.clone().unwrap_or_default()
            ));
            continue;
        };
        if is_marker(v) {
            if v.get(DIALECT_KEY).and_then(|x| x.as_str()) != Some("openai") {
                p.push(format!(
                    "{}:{}: dialect marker {} -- {} keeps the OpenAI plan-status words",
                    st.path, l.n, l.raw, st.path
                ));
            }
            continue;
        }
        let id = id_of(v).to_string();
        let mut errs = Vec::new();
        state.schema.conforms(v, node, &id, &mut errs);
        p.extend(errs);
        if let Some(w) = v.get("status").and_then(|x| x.as_str()) {
            if lane_word(w) {
                p.push(format!(
                    "{}:{} ({id}): legacy status word {w:?} on disk -- run mios-task fmt",
                    st.path, l.n
                ));
            }
        }
        if dumps(&state.schema.canon(v, node)) != l.raw {
            p.push(format!(
                "{}:{} ({id}): not in canonical serialization -- run mios-task fmt",
                st.path, l.n
            ));
        }
        if !seen.insert(id.clone()) {
            p.push(format!("duplicate id {id}"));
        }
        match v.get("provenance") {
            Some(x) if x.is_object() => migrated += 1,
            Some(Value::Null) => {
                let ac = v
                    .get("acceptance_criteria")
                    .and_then(|x| x.as_array())
                    .is_some_and(|a| {
                        a.iter()
                            .any(|x| x.as_str().is_some_and(|s| !s.trim().is_empty()))
                    });
                let cmd = |k: &str| {
                    v.get("verification")
                        .and_then(|x| x.get(k))
                        .and_then(|x| x.as_str())
                        .is_some_and(|s| !s.trim().is_empty())
                };
                if !ac {
                    p.push(format!(
                        "{id}: record born in {} lacks acceptance criteria",
                        st.path
                    ));
                }
                if !cmd("positive_cmd") {
                    p.push(format!(
                        "{id}: record born in {} lacks a positive control",
                        st.path
                    ));
                }
                if !cmd("negative_control_cmd") {
                    p.push(format!(
                        "{id}: record born in {} lacks a negative control",
                        st.path
                    ));
                }
            }
            _ => {}
        }
    }
    // Every migrated record is still here, and the frozen history still rebuilds byte for byte.
    if migrated != st.migrated {
        p.push(format!(
            "{} holds {migrated} migrated record(s) but [tasks.store].migrated is {} -- a migrated record was {}",
            st.path,
            st.migrated,
            if migrated < st.migrated { "dropped" } else { "forged" }
        ));
    }
    p.extend(frozen::verify(&state.records, &st.frozen));
    // Overrides: block structure and every line.
    let by_id = state.by_id();
    match &state.block {
        Ok(b) => p.extend(overrides::validate(
            &st.doc,
            &state.schema,
            &by_id,
            &b.lines,
        )),
        Err(e) => p.extend(e.iter().cloned()),
    }
    // Effective view: evidence, resolution, cycles.
    let eff = state.effective();
    for r in &eff.records {
        let id = id_of(r);
        if r.get("status").and_then(|x| x.as_str()) == Some("completed")
            && r.get("verification_evidence")
                .and_then(|x| x.as_str())
                .is_none_or(|s| s.trim().is_empty())
        {
            p.push(format!("{id}: completed without verification_evidence"));
        }
        for d in r
            .get("depends_on")
            .and_then(|x| x.as_array())
            .cloned()
            .unwrap_or_default()
        {
            let d = d.as_str().unwrap_or("");
            if !by_id.contains_key(d) {
                p.push(format!("{id}: depends_on unknown {d}"));
            }
        }
        let ep = r.get("epic").and_then(|x| x.as_str()).unwrap_or("");
        if !ep.is_empty() && !by_id.contains_key(ep) {
            p.push(format!("{id}: epic unknown {ep}"));
        }
    }
    for c in cycles(&eff.records) {
        p.push(format!("depends_on cycle among [{}]", c.join(", ")));
    }
    p.extend(hygiene(state, &st.doc));
    // The doc is a projection: it must equal the render byte for byte.
    if let Some(md) = &state.md {
        if state.block.is_ok() {
            let want = overrides::render(&st.path, &eff, &state.inner());
            if let Some((n, got)) = first_difference(md, &want) {
                p.push(format!(
                    "{}:{n} differs from the render of {} (a stale render, or a hand edit outside the overrides block): {:?} -- run: mios-task render",
                    st.doc,
                    st.path,
                    got.chars().take(120).collect::<String>()
                ));
            }
        }
    }
    p
}
