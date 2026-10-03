// AI-hint: tasks.jsonl access -- the [tasks.store] table from the SSOT (path, schema, doc, retired, frozen, migrated), repo-root discovery, line reading, and locked tmp+rename writes.
// AI-related: /usr/share/mios/mios.toml [tasks.store], tasks.jsonl, TASKS.md, /usr/share/doc/mios/adr/0028-one-canonical-task-list.md
// AI-functions: Store::open, Store::read, Store::write_lines, Store::locked, find_root, read_lines, lock_file, write_atomic

use serde_json::Value;
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};

/// The SSOT file every lookup starts from; the repo root is the directory that holds it.
pub const SSOT: &str = "usr/share/mios/mios.toml";

/// The only keys [tasks.store] may carry (ADR-0028).
pub const STORE_KEYS: [&str; 6] = ["path", "schema", "doc", "retired", "frozen", "migrated"];

/// One retired list whose bytes now live only in the records' provenance slices.
#[derive(Clone)]
pub struct Frozen {
    /// Repo-qualified name as the slices spell it, e.g. "MiOS:AGY-TASKS.md".
    pub source: String,
    pub bytes: usize,
    pub sha256: String,
}

pub struct Store {
    pub root: PathBuf,
    pub path: String,
    pub schema: String,
    pub doc: String,
    /// Repo-relative paths that must not exist any more: the retired task stores and absorbed lists.
    pub retired: Vec<String>,
    pub frozen: Vec<Frozen>,
    /// How many records the migration carried; each keeps a non-null provenance.
    pub migrated: usize,
}

/// One line of the canonical file: its 1-based number, its bytes, and its parse (None if not JSON).
pub struct Line {
    pub n: usize,
    pub raw: String,
    pub value: Option<Value>,
    pub error: Option<String>,
}

/// Walk up from `start` to the first directory holding the SSOT.
pub fn find_root(start: &Path) -> Option<PathBuf> {
    let mut d = Some(start);
    while let Some(p) = d {
        if p.join(SSOT).is_file() {
            return Some(p.to_path_buf());
        }
        d = p.parent();
    }
    None
}

fn table(root: &Path) -> Result<toml::value::Table, String> {
    let p = root.join(SSOT);
    let text = fs::read_to_string(&p).map_err(|e| format!("{}: {e}", p.display()))?;
    let doc: toml::Value = text.parse().map_err(|e| format!("{}: {e}", p.display()))?;
    let st = doc
        .get("tasks")
        .and_then(|t| t.get("store"))
        .and_then(|s| s.as_table())
        .cloned()
        .ok_or("mios.toml has no [tasks.store] table (ADR-0028 declares the task list there)")?;
    let mut unknown: Vec<&String> = st
        .keys()
        .filter(|k| !STORE_KEYS.contains(&k.as_str()))
        .collect();
    unknown.sort();
    if !unknown.is_empty() {
        return Err(format!(
            "[tasks.store] carries {} -- only {} are allowed (ADR-0028)",
            unknown
                .iter()
                .map(|k| format!("'{k}'"))
                .collect::<Vec<_>>()
                .join(", "),
            STORE_KEYS.join(", ")
        ));
    }
    Ok(st)
}

impl Store {
    pub fn open(root: &Path) -> Result<Store, String> {
        let st = table(root)?;
        let s = |k: &str| -> Result<String, String> {
            st.get(k)
                .and_then(|v| v.as_str())
                .filter(|v| !v.is_empty())
                .map(str::to_string)
                .ok_or(format!("[tasks.store].{k} is missing"))
        };
        let retired = st
            .get("retired")
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|x| x.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default();
        let mut frozen = Vec::new();
        for e in st
            .get("frozen")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default()
        {
            let g = |k: &str| e.get(k).and_then(|v| v.as_str()).map(str::to_string);
            let (Some(source), Some(sha256), Some(bytes)) = (
                g("source"),
                g("sha256"),
                e.get("bytes").and_then(|v| v.as_integer()),
            ) else {
                return Err("[tasks.store].frozen entries need source, bytes and sha256".into());
            };
            frozen.push(Frozen {
                source,
                bytes: bytes as usize,
                sha256,
            });
        }
        let migrated = st.get("migrated").and_then(|v| v.as_integer()).unwrap_or(0) as usize;
        Ok(Store {
            root: root.to_path_buf(),
            path: s("path")?,
            schema: s("schema")?,
            doc: s("doc")?,
            retired,
            frozen,
            migrated,
        })
    }

    pub fn file(&self) -> PathBuf {
        self.root.join(&self.path)
    }

    pub fn doc_file(&self) -> PathBuf {
        self.root.join(&self.doc)
    }

    pub fn schema_file(&self) -> PathBuf {
        self.root.join(&self.schema)
    }

    pub fn read(&self) -> Result<Vec<Line>, String> {
        read_lines(&self.file())
    }

    /// Hold the shared '<path>.lock' (the same lock file the dev-loop toolkit takes) for the life of the guard.
    pub fn locked(&self) -> Result<File, String> {
        lock_file(&self.file())
    }

    pub fn write_lines(&self, lines: &[String]) -> Result<(), String> {
        let mut s = String::with_capacity(lines.iter().map(|l| l.len() + 1).sum());
        for l in lines {
            s.push_str(l);
            s.push('\n');
        }
        write_atomic(&self.file(), &s)
    }
}

/// Lines split on '\n' only (a JSON string may hold U+2028 or a form feed raw); a trailing '\r' is a terminator.
pub fn read_lines(p: &Path) -> Result<Vec<Line>, String> {
    let t = fs::read_to_string(p).map_err(|e| format!("{}: {e}", p.display()))?;
    Ok(t.lines()
        .enumerate()
        .map(|(i, l)| {
            let (value, error) = match serde_json::from_str::<Value>(l) {
                Ok(v) => (Some(v), None),
                Err(e) => (None, Some(e.to_string())),
            };
            Line {
                n: i + 1,
                raw: l.to_string(),
                value,
                error,
            }
        })
        .collect())
}

pub fn lock_file(p: &Path) -> Result<File, String> {
    let mut name = p.as_os_str().to_os_string();
    name.push(".lock");
    let lp = PathBuf::from(name);
    let f = OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(&lp)
        .map_err(|e| format!("{}: {e}", lp.display()))?;
    f.lock().map_err(|e| format!("{}: {e}", lp.display()))?;
    Ok(f)
}

/// Write through '<path>.tmp' and rename, so a reader never sees half a file.
pub fn write_atomic(p: &Path, s: &str) -> Result<(), String> {
    if let Some(d) = p.parent() {
        if !d.as_os_str().is_empty() {
            fs::create_dir_all(d).map_err(|e| format!("{}: {e}", d.display()))?;
        }
    }
    let mut name = p.as_os_str().to_os_string();
    name.push(".tmp");
    let tmp = PathBuf::from(name);
    fs::write(&tmp, s).map_err(|e| format!("{}: {e}", tmp.display()))?;
    fs::rename(&tmp, p).map_err(|e| format!("{}: {e}", p.display()))
}
