// AI-hint: Rust SSOT names registry generator (check 30 generator).
use regex::Regex;
use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

const TARGET_SECTIONS: &[&str] = &[
    "ports",
    "ai",
    "identity",
    "locale",
    "auth",
    "network",
    "desktop",
    "branding",
    "image",
    "bootstrap",
    "profile",
    "colors",
    "observability",
    "sandbox",
    "security",
    "code_mode",
    "hermes",
    "routing",
    "agents",
    "a2a",
    "power",
    "metal",
    "versions",
];

fn alias_for(path: &str) -> Option<String> {
    match path {
        "ai.vllm.v1_engine" => Some("MIOS_VLLM_USE_V1".to_string()),
        "ai.sglang.unified_radix_tree" => Some("MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE".to_string()),
        "ai.sglang.hierarchical_cache" => Some("MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE".to_string()),
        _ => {
            if let Some(rest) = path.strip_prefix("ai.vllm.") {
                Some(format!(
                    "MIOS_VLLM_{}",
                    rest.to_uppercase().replace(['.', '-', '/'], "_")
                ))
            } else if let Some(rest) = path.strip_prefix("ai.sglang.") {
                Some(format!(
                    "MIOS_SGLANG_{}",
                    rest.to_uppercase().replace(['.', '-', '/'], "_")
                ))
            } else {
                path.strip_prefix("versions.").map(|rest| {
                    format!(
                        "MIOS_VERSION_{}",
                        rest.to_uppercase().replace(['.', '-', '/'], "_")
                    )
                })
            }
        }
    }
}

fn walk_value(val: &toml::Value, prefix: &str, results: &mut Vec<(String, String)>) {
    if let toml::Value::Table(table) = val {
        for (k, v) in table {
            let path = if prefix.is_empty() {
                k.clone()
            } else {
                format!("{}.{}", prefix, k)
            };
            if path == "routing.domains" {
                continue;
            }
            if let toml::Value::Table(_) = v {
                walk_value(v, &path, results);
            } else {
                let env_name = if let Some(alias) = alias_for(&path) {
                    alias
                } else {
                    format!("MIOS_{}", path.to_uppercase().replace(['.', '-', '/'], "_"))
                };
                results.push((path, env_name));
            }
        }
    }
}

/// Tracked paths, slash-separated. An error or an empty listing is fatal.
///
/// The walk this replaced skipped every directory named `build`, so it silently
/// dropped tracked files and still exited 0. A census that cannot be answered
/// must refuse, not guess.
fn tracked(root: &Path) -> Result<Vec<String>, String> {
    let out = std::process::Command::new("git")
        .arg("-C")
        .arg(root)
        .arg("ls-files")
        .output()
        .map_err(|e| format!("git ls-files could not run in {}: {e}", root.display()))?;
    if !out.status.success() {
        return Err(format!(
            "git ls-files failed in {} ({}): {}",
            root.display(),
            out.status,
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    let paths: Vec<String> = String::from_utf8_lossy(&out.stdout)
        .lines()
        .map(|l| l.trim().replace('\\', "/"))
        .filter(|l| !l.is_empty())
        .collect();
    if paths.is_empty() {
        return Err(format!(
            "git ls-files listed no tracked file in {}, so nothing would be \
             scanned and the result would be clean for the wrong reason",
            root.display()
        ));
    }
    Ok(paths)
}

/// True when `line` ASSIGNS `v`, matching the Python leg's
/// `\s*(export\s+)?<v>=`. Judging the whole line instead drops every name that
/// rides on an env-prefix line -- 16 of them in this tree.
fn assigned_at_start(line: &str, v: &str) -> bool {
    let rest = line.trim_start();
    let is_assign = |s: &str| s.strip_prefix(v).is_some_and(|t| t.starts_with('='));
    if is_assign(rest) {
        return true;
    }
    match rest.strip_prefix("export") {
        Some(after) => {
            let t = after.trim_start();
            after.len() != t.len() && is_assign(t)
        }
        None => false,
    }
}

/// Basename globs, matched exactly as the Python leg's fnmatchcase does.
fn matches_consumer_glob(fname: &str) -> bool {
    const SUFFIXES: [&str; 12] = [
        ".container",
        ".service",
        ".timer",
        ".py",
        ".sh",
        ".toml",
        ".ps1",
        ".psm1",
        ".yaml",
        ".yml",
        ".tmpl",
        ".nft",
    ];
    if fname == "Justfile" || fname == ".env.mios" || fname == "Containerfile" {
        return true;
    }
    if fname.ends_with(".sql") {
        return true;
    }
    // `Containerfile.*` needs the dot: `starts_with("Containerfile")` also took
    // Containerfilexyz, which fnmatchcase never would.
    if fname.starts_with("Containerfile.") {
        return true;
    }
    SUFFIXES.iter().any(|s| fname.ends_with(s))
}

fn generate_referenced_vars(root: &Path) -> Result<(), String> {
    // globals.{sh,ps1} are rendered in full and DEFINE the namespace; the
    // renderers' prose carries example placeholders that are not variables.
    let emitter_suffixes = [
        "usr/lib/mios/userenv.sh",
        "tools/lib/userenv.sh",
        "usr/libexec/mios/system-sync-env.sh",
        "usr/share/mios/names.generated.txt",
        "usr/share/doc/mios/reference/naming-unification.md",
        "automation/lib/globals.sh",
        "automation/lib/globals.ps1",
        "tools/render-globals.py",
        "tools/render-ports.py",
    ];

    let var_re = Regex::new(r"MIOS_[A-Z0-9_]+").map_err(|e| e.to_string())?;
    let mut refs: BTreeSet<String> = BTreeSet::new();

    for rel in tracked(root)? {
        let path = root.join(&rel);
        if !path.is_file() {
            continue;
        }
        if emitter_suffixes.iter().any(|s| rel.ends_with(s)) {
            continue;
        }
        let fname = match path.file_name().and_then(|n| n.to_str()) {
            Some(f) => f,
            None => continue,
        };
        if !matches_consumer_glob(fname) {
            continue;
        }
        let Ok(content) = fs::read_to_string(&path) else {
            continue;
        };
        for line in content.lines() {
            for m in var_re.find_iter(line) {
                let v = m.as_str().trim_end_matches('_');
                if v.is_empty() || v == "MIOS" {
                    continue;
                }
                if assigned_at_start(line, v) {
                    continue;
                }
                refs.insert(v.to_string());
            }
        }
    }

    // The file also carries names that are not MIOS_*; a rewrite that forgets
    // them drops 19 rows the registry is the only record of.
    let ref_file = root.join("usr/share/mios/referenced_names.txt");
    if let Ok(existing) = fs::read_to_string(&ref_file) {
        for line in existing.lines() {
            let s = line.trim();
            if !s.is_empty() && !s.starts_with("MIOS_") {
                refs.insert(s.to_string());
            }
        }
    }

    if let Some(parent) = ref_file.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let mut out = String::new();
    for r in &refs {
        out.push_str(r);
        out.push('\n');
    }
    write_atomic(&ref_file, &out)
}

/// Write via a sibling temp file and rename, as the Python leg does: a reader
/// racing the generator must never see a half-written registry.
fn write_atomic(path: &Path, body: &str) -> Result<(), String> {
    let tmp = path.with_extension("txt.tmp");
    fs::write(&tmp, body).map_err(|e| format!("{}: {e}", tmp.display()))?;
    fs::rename(&tmp, path).map_err(|e| format!("{}: {e}", path.display()))
}

/// Document order for each dotted path, from one scan of the SSOT text.
///
/// toml::Value::Table is a BTreeMap, so walking it is alphabetical while the
/// Python leg follows the file, and check_names_registry compares line order.
fn document_order(text: &str) -> std::collections::HashMap<String, usize> {
    let mut order = std::collections::HashMap::new();
    let mut cur = String::new();
    let mut seq = 0usize;
    for line in text.lines() {
        let t = line.trim();
        if t.is_empty() || t.starts_with('#') {
            continue;
        }
        // A header DECLARES its own path too. tomllib inserts `catalog` into
        // the `ai` dict when it first meets [[ai.catalog]], and the walk emits
        // that array as one leaf -- without this it had no position at all.
        // The bracket is matched rather than the line end: six channel keys
        // sorted wrong because their header carries a trailing comment.
        if t.starts_with('[') {
            let (open, close) = if t.starts_with("[[") {
                (2, "]]")
            } else {
                (1, "]")
            };
            if let Some(i) = t.find(close) {
                if i >= open {
                    cur = t[open..i].trim().trim_matches('"').to_string();
                    order.entry(cur.clone()).or_insert(seq);
                    seq += 1;
                    continue;
                }
            }
        }
        let Some(eq) = t.find('=') else { continue };
        let key = t[..eq].trim().trim_matches('"');
        if key.is_empty() || key.contains(' ') {
            continue;
        }
        let path = if cur.is_empty() {
            key.to_string()
        } else {
            format!("{cur}.{key}")
        };
        order.entry(path).or_insert(seq);
        seq += 1;
    }
    order
}

/// A path the scan never saw (an inline table member) sorts with its
/// nearest declared ancestor, so siblings stay together.
fn order_of(order: &std::collections::HashMap<String, usize>, path: &str) -> usize {
    let mut probe = path;
    loop {
        if let Some(n) = order.get(probe) {
            return *n;
        }
        match probe.rfind('.') {
            Some(i) => probe = &probe[..i],
            None => return usize::MAX,
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let root_str = std::env::var("MIOS_DRIFT_ROOT").unwrap_or_else(|_| {
        std::env::current_dir()
            .unwrap()
            .to_string_lossy()
            .to_string()
    });
    let root = PathBuf::from(&root_str);

    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.exists() {
        eprintln!("Error: mios.toml not found at {}", toml_path.display());
        std::process::exit(1);
    }

    let content = fs::read_to_string(&toml_path)?;
    let data: toml::Value = toml::from_str(&content)?;

    let order = document_order(&content);
    let mut all_pairs = Vec::new();
    if let toml::Value::Table(ref root_table) = data {
        for sec in TARGET_SECTIONS {
            if let Some(sec_val) = root_table.get(*sec) {
                let mut sec_pairs = Vec::new();
                walk_value(sec_val, sec, &mut sec_pairs);
                sec_pairs.sort_by_key(|(path, _)| order_of(&order, path));
                all_pairs.extend(sec_pairs);
            }
        }
    }

    let names_file = root.join("usr/share/mios/names.generated.txt");
    if let Some(parent) = names_file.parent() {
        fs::create_dir_all(parent)?;
    }

    let mut names_content = String::new();
    for (path, env_name) in &all_pairs {
        names_content.push_str(&format!("{}  {}\n", path, env_name));
        println!("{}  {}", path, env_name);
    }
    write_atomic(&names_file, &names_content)
        .map_err(|e| -> Box<dyn std::error::Error> { Box::from(e) })?;

    if let Err(e) = generate_referenced_vars(&root) {
        eprintln!("Error: refusing to rewrite referenced_names.txt -- {e}");
        std::process::exit(1);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A whole-line skip loses every name riding on an env-prefix line.
    #[test]
    fn only_the_name_actually_assigned_is_skipped() {
        assert!(assigned_at_start("MIOS_FOO=1", "MIOS_FOO"));
        assert!(assigned_at_start("  export MIOS_FOO=1", "MIOS_FOO"));
        assert!(!assigned_at_start(
            "MIOS_FOO=1 cmd --flag ${MIOS_BAR}",
            "MIOS_BAR"
        ));
        assert!(!assigned_at_start("echo ${MIOS_FOO}", "MIOS_FOO"));
        // export must be followed by whitespace, not glued to the name.
        assert!(!assigned_at_start("exportMIOS_FOO=1", "MIOS_FOO"));
        // the rstripped name must not match a longer assignment.
        assert!(!assigned_at_start("MIOS_FOO_=1", "MIOS_FOO"));
    }

    #[test]
    fn containerfile_glob_needs_the_dot() {
        assert!(matches_consumer_glob("Containerfile"));
        assert!(matches_consumer_glob("Containerfile.builder"));
        assert!(!matches_consumer_glob("Containerfilexyz"));
        assert!(matches_consumer_glob("x.sql"));
        assert!(matches_consumer_glob("Justfile"));
        assert!(!matches_consumer_glob("README.md"));
    }

    /// A header declares its own path, and a trailing comment must not hide it.
    #[test]
    fn headers_declare_their_own_path_and_survive_a_comment() {
        let text = "[a]\nx = 1\n[[a.list]]\nk = 2\n[a.chan]   # trailing\nthinking = 3\nplan = 4\n";
        let o = document_order(text);
        assert!(
            o.contains_key("a.list"),
            "an array-of-tables header declares its key"
        );
        assert!(
            o.contains_key("a.chan.thinking"),
            "a commented header still sets the prefix"
        );
        assert!(
            o["a.chan.thinking"] < o["a.chan.plan"],
            "keys keep document order, not alphabetical"
        );
        assert!(o["a.x"] < o["a.list"]);
    }

    /// An inline table's member sorts with its nearest declared ancestor rather
    /// than jumping to the end of the section.
    #[test]
    fn an_undeclared_path_inherits_its_ancestors_position() {
        let text = "[a]\nfirst = 1\ninline = { deep = 2 }\nlast = 3\n";
        let o = document_order(text);
        let d = order_of(&o, "a.inline.deep");
        assert_eq!(d, o["a.inline"]);
        assert!(o["a.first"] < d && d < o["a.last"]);
        assert_eq!(order_of(&o, "nothing.like.this"), usize::MAX);
    }

    #[test]
    fn test_alias_for() {
        assert_eq!(
            alias_for("ai.vllm.v1_engine"),
            Some("MIOS_VLLM_USE_V1".to_string())
        );
        assert_eq!(
            alias_for("ai.vllm.max_model_len"),
            Some("MIOS_VLLM_MAX_MODEL_LEN".to_string())
        );
        assert_eq!(
            alias_for("ai.sglang.unified_radix_tree"),
            Some("MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE".to_string())
        );
        assert_eq!(
            alias_for("ai.sglang.hierarchical_cache"),
            Some("MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE".to_string())
        );
        assert_eq!(
            alias_for("versions.ceph"),
            Some("MIOS_VERSION_CEPH".to_string())
        );
        assert_eq!(
            alias_for("versions.k3s"),
            Some("MIOS_VERSION_K3S".to_string())
        );
        assert_eq!(
            alias_for("versions.forgejo"),
            Some("MIOS_VERSION_FORGEJO".to_string())
        );
        assert_eq!(
            alias_for("versions.fedora"),
            Some("MIOS_VERSION_FEDORA".to_string())
        );
        assert_eq!(alias_for("ports.http"), None);
    }

    #[test]
    fn test_walk_value() {
        let toml_str = r#"
        [ports]
        http = 80
        https = 443
        "#;
        let val: toml::Value = toml::from_str(toml_str).unwrap();
        let mut results = Vec::new();
        walk_value(&val, "", &mut results);
        assert_eq!(
            results,
            vec![
                ("ports.http".to_string(), "MIOS_PORTS_HTTP".to_string()),
                ("ports.https".to_string(), "MIOS_PORTS_HTTPS".to_string()),
            ]
        );
    }
}
