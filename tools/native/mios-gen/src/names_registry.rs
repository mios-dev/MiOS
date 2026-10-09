// AI-hint: Rust SSOT names registry generator (check 30 generator).
use regex::Regex;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;

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
                let env_name = mios_resolver::names::canonical_name(&path);
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
        .arg("-z")
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
    let paths: Vec<String> = String::from_utf8(out.stdout)
        .map_err(|e| format!("tracked paths are not UTF-8: {e}"))?
        .split('\0')
        .map(|l| l.replace('\\', "/"))
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

fn render_referenced_vars(root: &Path) -> Result<String, String> {
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

    let mut out = String::new();
    for r in &refs {
        out.push_str(r);
        out.push('\n');
    }
    Ok(out)
}

/// Write via a sibling temp file and rename, as the Python leg does: a reader
/// racing the generator must never see a half-written registry.
fn write_atomic(path: &Path, body: &[u8]) -> Result<(), String> {
    use std::io::Write;
    let mut temporary =
        tempfile::NamedTempFile::new_in(path.parent().ok_or("output has no parent")?)
            .map_err(|e| e.to_string())?;
    temporary.write_all(body).map_err(|e| e.to_string())?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let permissions = fs::metadata(path)
            .map(|m| m.permissions())
            .unwrap_or_else(|_| fs::Permissions::from_mode(0o644));
        temporary
            .as_file()
            .set_permissions(permissions)
            .map_err(|e| e.to_string())?;
    }
    temporary
        .persist(path)
        .map_err(|e| format!("{}: {}", path.display(), e.error))?;
    Ok(())
}

fn previous_artifact(path: &Path) -> Result<Option<Vec<u8>>, String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.is_file() => fs::read(path).map(Some).map_err(|e| e.to_string()),
        Ok(_) => Err(format!(
            "registry output must be a regular file: {}",
            path.display()
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.to_string()),
    }
}

fn write_registry_pair(
    names: &Path,
    names_content: &str,
    references: &Path,
    referenced_content: &str,
) -> Result<(), String> {
    let previous_names = previous_artifact(names)?;
    previous_artifact(references)?;
    write_atomic(names, names_content.as_bytes())?;
    if let Err(error) = write_atomic(references, referenced_content.as_bytes()) {
        let restored = match previous_names {
            Some(bytes) => write_atomic(names, &bytes),
            None => fs::remove_file(names).map_err(|e| e.to_string()),
        };
        return Err(match restored {
            Ok(()) => format!("{error}; previous name registry restored"),
            Err(restore) => format!(
                "{error}; restoring {} also failed: {restore}",
                names.display()
            ),
        });
    }
    Ok(())
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

const NAMES_FILE: &str = "usr/share/mios/names.generated.txt";
const REFERENCES_FILE: &str = "usr/share/mios/referenced_names.txt";

pub fn run(root: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let (names_content, referenced_content) = render(root)?;
    let names_file = root.join(NAMES_FILE);
    if let Some(parent) = names_file.parent() {
        fs::create_dir_all(parent)?;
    }
    print!("{names_content}");
    write_registry_pair(
        &names_file,
        &names_content,
        &root.join(REFERENCES_FILE),
        &referenced_content,
    )?;
    Ok(())
}

/// The read-only twin of `run`: the committed artefacts the generator would
/// rewrite, compared in memory. A drift gate must never write the tree it
/// grades -- check_names_registry ran `run` and left a stale binary's 720-line
/// registry over the 6488-line one.
pub fn check(root: &Path) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let (names_content, referenced_content) = render(root)?;
    Ok([
        (NAMES_FILE, names_content),
        (REFERENCES_FILE, referenced_content),
    ]
    .into_iter()
    .filter(|(rel, want)| fs::read(root.join(rel)).ok().as_deref() != Some(want.as_bytes()))
    .map(|(rel, _)| rel.to_string())
    .collect())
}

/// `check` for a command line: each drifted artefact on stderr; true when clean.
pub fn check_cli(root: &Path, tag: &str) -> bool {
    match check(root) {
        Ok(drift) if drift.is_empty() => {
            println!("[{tag}] both names artefacts match what the generator renders");
            true
        }
        Ok(drift) => {
            for rel in drift {
                eprintln!("[{tag}] {rel} differs from what the generator renders -- run mios-gen names-registry");
            }
            false
        }
        Err(error) => {
            eprintln!("[{tag}] {error}");
            false
        }
    }
}

/// Both artefacts exactly as `run` writes them.
fn render(root: &Path) -> Result<(String, String), Box<dyn std::error::Error>> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.exists() {
        return Err(format!("mios.toml not found at {}", toml_path.display()).into());
    }

    let content = fs::read_to_string(&toml_path)?;
    let data: toml::Value = toml::from_str(&content)?;

    let order = document_order(&content);
    let mut all_pairs = Vec::new();
    // Validate all keys, including sections previously omitted by a fixed list.
    mios_resolver::names::registry(&data)
        .map_err(|e| -> Box<dyn std::error::Error> { e.into() })?;
    walk_value(&data, "", &mut all_pairs);
    all_pairs.sort_by_key(|(path, _)| order_of(&order, path));

    // Census and parse failures must preserve BOTH existing projections.
    let referenced_content = render_referenced_vars(root)?;
    let mut names_content = String::new();
    for (path, env_name) in &all_pairs {
        names_content.push_str(&format!("{}  {}\n", path, env_name));
    }
    Ok((names_content, referenced_content))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_census_and_colliding_names_preserve_both_projections() {
        let root = tempfile::tempdir().unwrap();
        let directory = root.path().join("usr/share/mios");
        fs::create_dir_all(&directory).unwrap();
        let names = directory.join("names.generated.txt");
        let references = directory.join("referenced_names.txt");
        fs::write(&names, b"previous names\xff").unwrap();
        fs::write(&references, "previous references\n").unwrap();
        for source in ["[ports]\nhttp=80\n", "[a]\n'b-c'=1\nb_c=2\n"] {
            fs::write(directory.join("mios.toml"), source).unwrap();
            assert!(run(root.path()).is_err());
            assert_eq!(fs::read(&names).unwrap(), b"previous names\xff");
            assert_eq!(
                fs::read_to_string(&references).unwrap(),
                "previous references\n"
            );
        }
    }

    #[test]
    fn invalid_second_output_preserves_the_first_projection() {
        let root = tempfile::tempdir().unwrap();
        let names = root.path().join("names.txt");
        let references = root.path().join("references.txt");
        fs::write(&names, "previous\n").unwrap();
        fs::create_dir(&references).unwrap();
        assert!(write_registry_pair(&names, "replacement\n", &references, "references\n").is_err());
        assert_eq!(fs::read_to_string(&names).unwrap(), "previous\n");
        fs::remove_dir(&references).unwrap();
        write_registry_pair(&names, "replacement\n", &references, "references\n").unwrap();
        assert_eq!(fs::read_to_string(&names).unwrap(), "replacement\n");
        assert_eq!(fs::read_to_string(&references).unwrap(), "references\n");
    }

    /// `check` names what drifted, both ways, and never writes.
    #[test]
    fn check_reports_drift_and_writes_nothing() {
        let root = tempfile::tempdir().unwrap();
        let r = root.path();
        fs::create_dir_all(r.join("usr/share/mios")).unwrap();
        fs::write(r.join("usr/share/mios/mios.toml"), "[ports]\nhttp = 80\n").unwrap();
        fs::write(r.join("serve.sh"), "httpd --port \"${MIOS_PORTS_HTTP}\"\n").unwrap();
        for args in [
            &["init", "-q"][..],
            &["add", "usr/share/mios/mios.toml", "serve.sh"],
        ] {
            let ok = std::process::Command::new("git")
                .arg("-C")
                .arg(r)
                .args(args)
                .status();
            assert!(ok.unwrap().success());
        }
        run(r).unwrap();
        assert!(check(r).unwrap().is_empty());
        fs::write(r.join(NAMES_FILE), "planted\n").unwrap();
        assert_eq!(check(r).unwrap(), vec![NAMES_FILE.to_string()]);
        assert_eq!(fs::read_to_string(r.join(NAMES_FILE)).unwrap(), "planted\n");
    }

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
