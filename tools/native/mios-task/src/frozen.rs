// AI-hint: The retired task lists as frozen history -- every byte lives in a record's provenance.sources slice; rebuild a list by offset, verify each slice and each list against [tasks.store].frozen, and name a dropped record from the slice that followed it.
// AI-related: tasks.jsonl, /usr/share/mios/mios.toml [tasks.store], /usr/lib/mios/schemas/task-record.schema.json, /usr/share/doc/mios/adr/0028-one-canonical-task-list.md
// AI-functions: sha, Slice, slices, rebuild, verify

use crate::store::Frozen;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

pub fn sha(s: &str) -> String {
    format!("{:x}", Sha256::digest(s.as_bytes()))
}

/// One provenance slice with the record that owns it.
pub struct Slice {
    pub owner: String,
    pub offset: usize,
    pub after: String,
    pub sha256: String,
    pub length: usize,
    pub text: String,
}

/// Every slice of every record, grouped by file and sorted by offset.
pub fn slices(records: &[Value]) -> BTreeMap<String, Vec<Slice>> {
    let mut out: BTreeMap<String, Vec<Slice>> = BTreeMap::new();
    for r in records {
        let owner = r.get("id").and_then(|x| x.as_str()).unwrap_or("?");
        let Some(a) = r
            .get("provenance")
            .and_then(|p| p.get("sources"))
            .and_then(|s| s.as_array())
        else {
            continue;
        };
        for s in a {
            let g = |k: &str| s.get(k).and_then(|x| x.as_str()).unwrap_or("").to_string();
            let n = |k: &str| s.get(k).and_then(|x| x.as_u64()).unwrap_or(0) as usize;
            out.entry(g("file")).or_default().push(Slice {
                owner: owner.to_string(),
                offset: n("offset"),
                after: g("after"),
                sha256: g("sha256"),
                length: n("length"),
                text: g("text"),
            });
        }
    }
    for v in out.values_mut() {
        v.sort_by_key(|s| s.offset);
    }
    out
}

/// The bytes of one frozen list, rebuilt from its slices; Err names every gap, overlap or edited slice.
pub fn rebuild(file: &str, sl: &[Slice], want: Option<&Frozen>) -> Result<String, Vec<String>> {
    let mut errs = Vec::new();
    let mut out = String::new();
    let mut at = 0usize;
    for s in sl {
        if sha(&s.text) != s.sha256 || s.text.len() != s.length {
            errs.push(format!(
                "{file}: the slice {} owns at offset {} was edited (sha256/length no longer match its text)",
                s.owner, s.offset
            ));
        }
        if s.offset > at {
            errs.push(format!(
                "{file}: bytes {at}..{} are missing -- record {} was dropped (the slice owned by {} follows it)",
                s.offset,
                if s.after.is_empty() { "(unnamed)" } else { s.after.as_str() },
                s.owner
            ));
        } else if s.offset < at {
            errs.push(format!(
                "{file}: the slice {} owns at offset {} overlaps the one before it (a record was duplicated)",
                s.owner, s.offset
            ));
            continue;
        }
        out.push_str(&s.text);
        at = s.offset + s.text.len();
    }
    if let Some(f) = want {
        if at < f.bytes {
            let last = sl.last().map(|s| s.owner.as_str()).unwrap_or("(none)");
            errs.push(format!(
                "{file}: bytes {at}..{} are missing at the end -- a record after {last} was dropped",
                f.bytes
            ));
        }
        if errs.is_empty() && sha(&out) != f.sha256 {
            errs.push(format!(
                "{file}: the rebuilt bytes differ from [tasks.store].frozen sha256"
            ));
        }
    }
    if errs.is_empty() {
        Ok(out)
    } else {
        Err(errs)
    }
}

/// Every problem with the frozen history: each declared list rebuilds to its digest, every other slice is intact.
pub fn verify(records: &[Value], frozen: &[Frozen]) -> Vec<String> {
    let all = slices(records);
    let mut errs = Vec::new();
    for f in frozen {
        match all.get(&f.source) {
            None => errs.push(format!(
                "{}: no record carries its slices any more -- every record migrated from it was dropped",
                f.source
            )),
            Some(sl) => {
                if let Err(e) = rebuild(&f.source, sl, Some(f)) {
                    errs.extend(e);
                }
            }
        }
    }
    // Slices of a list that is not frozen whole (a record moved from a sibling's backlog) still keep their digest.
    for (file, sl) in &all {
        if frozen.iter().any(|f| &f.source == file) {
            continue;
        }
        for s in sl {
            if sha(&s.text) != s.sha256 || s.text.len() != s.length {
                errs.push(format!(
                    "{file}: the slice {} owns at offset {} was edited (sha256/length no longer match its text)",
                    s.owner, s.offset
                ));
            }
        }
    }
    errs
}
