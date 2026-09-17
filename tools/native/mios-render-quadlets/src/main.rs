// AI-hint: SSOT-driven Quadlet placeholder renderer; replaces stage 34's envsubst + bash-regex pair with a real parser.
// AI-related: usr/share/mios/mios.toml, automation/34-render-quadlets.sh, tools/native/mios-render-quadlets/src/expand.rs

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

mod expand;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

const SSOT: &str = "usr/share/mios/mios.toml";
const USAGE: &str = "usage: mios-render-quadlets [--root DIR] [--check]\n";

fn die(msg: &str) -> ExitCode {
    eprintln!("mios-render-quadlets: {msg}");
    ExitCode::from(2)
}

/// Every knob comes from `[build.quadlet_render]`. Nothing here is a literal:
/// the two bash renderers each carried their own hardcoded list and had already
/// drifted apart by fourteen names (T-1040).
#[derive(Debug)]
struct Config {
    dirs: Vec<String>,
    extensions: Vec<String>,
    max_depth: usize,
    runtime_ref_directives: Vec<String>,
}

fn strings(v: Option<&toml::Value>, key: &str) -> Result<Vec<String>, String> {
    let arr = v
        .and_then(|x| x.as_array())
        .ok_or_else(|| format!("[build.quadlet_render].{key} is missing or not an array"))?;
    let mut out = Vec::with_capacity(arr.len());
    for e in arr {
        let s = e
            .as_str()
            .ok_or_else(|| format!("[build.quadlet_render].{key} holds a non-string entry"))?;
        if s.trim().is_empty() {
            return Err(format!("[build.quadlet_render].{key} holds an empty entry"));
        }
        out.push(s.trim().to_string());
    }
    if out.is_empty() {
        // An empty list would render nothing and exit 0 -- the Empty-Set Pass.
        return Err(format!(
            "[build.quadlet_render].{key} is empty -- refusing to run rather than silently rendering nothing"
        ));
    }
    Ok(out)
}

fn load_config(root: &Path) -> Result<Config, String> {
    let path = root.join(SSOT);
    let text = std::fs::read_to_string(&path)
        .map_err(|e| format!("{SSOT} could not be read ({e}) -- nothing was rendered"))?;
    let doc: toml::Value = text
        .parse()
        .map_err(|e| format!("{SSOT} did not parse ({e}) -- nothing was rendered"))?;
    let qr = doc
        .get("build")
        .and_then(|b| b.get("quadlet_render"))
        .ok_or_else(|| format!("{SSOT} has no [build.quadlet_render] -- nothing was rendered"))?;

    let max_depth = qr
        .get("max_depth")
        .and_then(|d| d.as_integer())
        .ok_or_else(|| {
            "[build.quadlet_render].max_depth is missing or not an integer".to_string()
        })?;
    if max_depth < 1 {
        return Err("[build.quadlet_render].max_depth must be at least 1".into());
    }

    Ok(Config {
        dirs: strings(qr.get("dirs"), "dirs")?,
        extensions: strings(qr.get("extensions"), "extensions")?,
        max_depth: max_depth as usize,
        runtime_ref_directives: strings(
            qr.get("runtime_ref_directives"),
            "runtime_ref_directives",
        )?,
    })
}

/// The SSOT exports map every other native consumer resolves through. Degrading
/// to empty is deliberate: an unresolved placeholder is then NAMED below rather
/// than silently blanked, which is what envsubst did.
fn ssot_exports(root: &Path) -> BTreeMap<String, String> {
    let fig = mios_resolver::layers::create_figment(Some(root));
    match fig.extract::<toml::Value>() {
        Ok(mut merged) => {
            mios_resolver::db_overlay::maybe_apply_db_overlay(&mut merged, false);
            let offset = merged
                .get("ports")
                .and_then(|p| p.get("stack_id"))
                .and_then(|v| {
                    v.as_integer()
                        .or_else(|| v.as_str().and_then(|s| s.parse::<i64>().ok()))
                })
                .map(|id| id * 10000)
                .unwrap_or(0);
            mios_resolver::emit::build_exports_map(&merged, offset)
        }
        Err(e) => {
            eprintln!(
                "mios-render-quadlets: WARNING: SSOT exports unavailable ({e}); \
                 placeholders will be reported unresolved rather than blanked"
            );
            BTreeMap::new()
        }
    }
}

/// A unit declaring Environment=/EnvironmentFile= owns its Exec refs (T-1040).
fn declares_unit_environment(content: &str) -> bool {
    content.lines().any(|l| {
        let t = l.trim_start();
        t.starts_with("Environment=") || t.starts_with("EnvironmentFile=")
    })
}

fn directive_of(line: &str) -> Option<&str> {
    let t = line.trim_start();
    let eq = t.find('=')?;
    Some(t[..eq].trim())
}

fn is_runtime_ref_line(line: &str, cfg: &Config) -> bool {
    match directive_of(line) {
        Some(d) => cfg.runtime_ref_directives.iter().any(|r| r == d),
        None => false,
    }
}

struct FileOutcome {
    changed: bool,
    rendered: String,
    unresolved: Vec<(usize, String)>,
}

/// A directive continued with a trailing backslash owns its continuation lines.
/// mios-agents.service writes its whole `podman run` invocation that way, so
/// judging each physical line on its own left thirteen genuine runtime
/// references unprotected -- caught by rendering the real unit into a fixture.
fn continues(line: &str) -> bool {
    line.trim_end().ends_with('\\')
}

fn is_comment(line: &str) -> bool {
    let t = line.trim_start();
    t.starts_with('#') || t.starts_with(';')
}

/// Render one file line by line so the runtime-ref rule can be applied per
/// directive rather than per file.
fn render_file(content: &str, cfg: &Config, ssot: &BTreeMap<String, String>) -> FileOutcome {
    let unit_env = declares_unit_environment(content);
    let mut out = String::with_capacity(content.len());
    let mut unresolved = Vec::new();
    let mut in_runtime_ref = false;
    for (i, line) in content.split_inclusive('\n').enumerate() {
        // A comment is documentation, not configuration. Rendering one destroys
        // the prose (mios-agents.service documents `${VAR}` in its own header)
        // and reporting it is a false positive.
        if is_comment(line) {
            out.push_str(line);
            continue;
        }
        if !in_runtime_ref {
            in_runtime_ref = unit_env && is_runtime_ref_line(line, cfg);
        }
        let protected = in_runtime_ref;
        if !continues(line) {
            in_runtime_ref = false;
        }
        // A protected line still gets its `${VAR:-default}` forms baked:
        // systemd does not expand that form anywhere, so leaving one ships a
        // unit that resolves it to empty. mios-agents.service documents the
        // distinction in its own header and carries one on line 45.
        let e = if protected {
            expand::expand_mode(line, ssot, expand::Mode::DefaultsOnly)
        } else {
            expand::expand(line, ssot)
        };
        for name in e.unresolved {
            unresolved.push((i + 1, name));
        }
        out.push_str(&e.text);
    }
    FileOutcome {
        changed: out != content,
        rendered: out,
        unresolved,
    }
}

fn main() -> ExitCode {
    let mut root = PathBuf::from(".");
    let mut check = false;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--root" => match args.next() {
                Some(v) => root = PathBuf::from(v),
                None => return die("--root needs a directory"),
            },
            "--check" => check = true,
            "-h" | "--help" => {
                print!("{USAGE}");
                return ExitCode::SUCCESS;
            }
            other => return die(&format!("unknown argument '{other}'\n{USAGE}")),
        }
    }

    let cfg = match load_config(&root) {
        Ok(c) => c,
        Err(e) => return die(&e),
    };
    let ssot = ssot_exports(&root);

    let mut scanned = 0usize;
    let mut changed = 0usize;
    let mut problems: Vec<String> = Vec::new();

    for dir in &cfg.dirs {
        let abs = root.join(dir.trim_start_matches('/'));
        if !abs.is_dir() {
            continue;
        }
        for entry in walkdir::WalkDir::new(&abs)
            .max_depth(cfg.max_depth)
            .into_iter()
            .filter_map(Result::ok)
        {
            if !entry.file_type().is_file() {
                continue;
            }
            let p = entry.path();
            let ext = match p.extension().and_then(|e| e.to_str()) {
                Some(e) => e,
                None => continue,
            };
            if !cfg.extensions.iter().any(|x| x == ext) {
                continue;
            }
            let content = match std::fs::read_to_string(p) {
                Ok(c) => c,
                Err(_) => continue, // not UTF-8 text; not ours to render
            };
            if !content.contains("${MIOS_") {
                continue;
            }
            scanned += 1;
            let outcome = render_file(&content, &cfg, &ssot);
            for (line, name) in &outcome.unresolved {
                problems.push(format!(
                    "{}:{line} floats on ${{{name}}}, which resolved to nothing -- it is not in the \
                     environment nor the SSOT exports, and the unit declares no Environment= or \
                     EnvironmentFile= that could supply it at runtime",
                    p.display()
                ));
            }
            if outcome.changed {
                changed += 1;
                if !check {
                    if let Err(e) = std::fs::write(p, &outcome.rendered) {
                        return die(&format!("{} could not be written ({e})", p.display()));
                    }
                }
            }
        }
    }

    if scanned == 0 {
        return die("no file carrying a ${MIOS_ placeholder was found -- the scan matched nothing, which is not the same as having nothing to do");
    }
    if !problems.is_empty() {
        for p in &problems {
            eprintln!("mios-render-quadlets: {p}");
        }
        eprintln!(
            "mios-render-quadlets: {} unresolved placeholder(s) across {scanned} file(s)",
            problems.len()
        );
        return ExitCode::from(1);
    }
    if check {
        if changed > 0 {
            eprintln!(
                "mios-render-quadlets: {changed} of {scanned} file(s) are NOT rendered -- run the renderer"
            );
            return ExitCode::from(1);
        }
        println!(
            "mios-render-quadlets: OK: {scanned} file(s) fully rendered, no residual placeholder"
        );
        return ExitCode::SUCCESS;
    }
    println!("mios-render-quadlets: rendered {changed} of {scanned} file(s)");
    ExitCode::SUCCESS
}

#[cfg(test)]
// Fixture setup panics on failure by design; the crate bans that in production paths.
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests {
    use super::*;

    fn cfg() -> Config {
        Config {
            dirs: vec!["etc/mios".into()],
            extensions: vec!["service".into(), "toml".into()],
            max_depth: 2,
            runtime_ref_directives: vec!["ExecStart".into(), "ExecStartPre".into()],
        }
    }

    fn ssot(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    }

    /// mios-agents.service writes its whole podman invocation as one
    /// backslash-continued ExecStart. Judging each physical line alone left
    /// thirteen genuine runtime references unprotected -- this is that bug.
    #[test]
    fn a_continued_exec_line_keeps_its_runtime_refs() {
        let unit = "[Service]\nEnvironment=MIOS_X=1\nExecStart=/bin/podman run \\\n  --env A=${MIOS_X} \\\n  --env B=${MIOS_Y}\n";
        let out = render_file(unit, &cfg(), &ssot(&[("MIOS_X", "9"), ("MIOS_Y", "9")]));
        assert!(!out.changed, "runtime refs must survive: {}", out.rendered);
        assert!(out.rendered.contains("${MIOS_X}"), "{}", out.rendered);
        assert!(out.rendered.contains("${MIOS_Y}"), "{}", out.rendered);
        assert!(out.unresolved.is_empty(), "{:?}", out.unresolved);
    }

    /// systemd cannot expand `${VAR:-default}` ANYWHERE -- replace_env_full is
    /// called with flags=0, and env-util.c treats `:` as unsupported syntax and
    /// does no replacement. So a protected line still gets its :- forms baked,
    /// while its bare refs are left. mios-agents.service:45 carries exactly one
    /// and its own header records the failure: code-server dies "Invalid URL".
    #[test]
    fn a_protected_line_still_bakes_its_default_forms() {
        let unit = "[Service]\nEnvironment=MIOS_X=1\nExecStart=/bin/cs \\\n  --env A=${MIOS_X} \\\n  --bind-addr 127.0.0.1:${MIOS_PORT_CODE_SERVER:-8900}\n";
        let out = render_file(
            unit,
            &cfg(),
            &ssot(&[("MIOS_X", "9"), ("MIOS_PORT_CODE_SERVER", "8900")]),
        );
        assert!(
            out.rendered.contains("--env A=${MIOS_X}"),
            "bare ref must survive: {}",
            out.rendered
        );
        assert!(
            out.rendered.contains("127.0.0.1:8900"),
            ":- form must be baked: {}",
            out.rendered
        );
        assert!(
            !out.rendered.contains(":-"),
            "no :- may survive: {}",
            out.rendered
        );
        assert!(out.unresolved.is_empty(), "{:?}", out.unresolved);
    }

    /// The continuation must END. A later non-Exec directive is fair game.
    #[test]
    fn protection_stops_when_the_continuation_stops() {
        let unit = "[Service]\nEnvironment=MIOS_X=1\nExecStart=/bin/true \\\n  --env A=${MIOS_X}\nListenStream=${MIOS_PORT}\n";
        let out = render_file(
            unit,
            &cfg(),
            &ssot(&[("MIOS_X", "9"), ("MIOS_PORT", "8320")]),
        );
        assert!(
            out.rendered.contains("--env A=${MIOS_X}"),
            "{}",
            out.rendered
        );
        assert!(
            out.rendered.contains("ListenStream=8320"),
            "{}",
            out.rendered
        );
    }

    /// A unit with NO Environment=/EnvironmentFile= owns nothing at runtime, so
    /// even an Exec line must be rendered -- otherwise systemd expands it to
    /// empty. This is the half that keeps the rule from becoming a blanket skip.
    #[test]
    fn without_a_unit_environment_even_exec_lines_render() {
        let unit = "[Service]\nExecStart=/bin/true --port=${MIOS_PORT}\n";
        let out = render_file(unit, &cfg(), &ssot(&[("MIOS_PORT", "8320")]));
        assert!(out.changed);
        assert!(out.rendered.contains("--port=8320"), "{}", out.rendered);
    }

    /// Rendering a comment destroys documentation and reporting one is a false
    /// positive -- mios-agents.service documents `${VAR}` in its own header.
    #[test]
    fn comments_are_neither_rendered_nor_reported() {
        let unit = "# ExecStart uses plain ${MIOS_GONE}.\n; also ${MIOS_GONE}\nListenStream=${MIOS_PORT}\n";
        let out = render_file(unit, &cfg(), &ssot(&[("MIOS_PORT", "8320")]));
        assert!(
            out.rendered
                .starts_with("# ExecStart uses plain ${MIOS_GONE}."),
            "{}",
            out.rendered
        );
        assert!(
            out.rendered.contains("; also ${MIOS_GONE}"),
            "{}",
            out.rendered
        );
        assert!(
            out.unresolved.is_empty(),
            "a comment must not be reported: {:?}",
            out.unresolved
        );
    }

    /// Image= is not an Exec line and Quadlet does not expand it, so a floated
    /// tag that resolves to nothing must be NAMED. Four shipped .container
    /// files carried exactly this (T-1040).
    #[test]
    fn an_unresolvable_image_tag_is_reported_with_its_line() {
        let unit = "[Container]\nImage=quay.io/ceph/ceph:${MIOS_VERSION_CEPH}\n";
        let out = render_file(unit, &cfg(), &ssot(&[]));
        assert_eq!(1, out.unresolved.len(), "{:?}", out.unresolved);
        assert_eq!(2, out.unresolved[0].0);
        assert_eq!("MIOS_VERSION_CEPH", out.unresolved[0].1);
    }

    #[test]
    fn an_environment_file_also_confers_runtime_ownership() {
        let unit =
            "[Service]\nEnvironmentFile=-/etc/mios/install.env\nExecStart=/bin/true ${MIOS_X}\n";
        let out = render_file(unit, &cfg(), &ssot(&[("MIOS_X", "9")]));
        assert!(!out.changed, "{}", out.rendered);
    }

    #[test]
    fn a_config_missing_a_key_cannot_run() {
        let d = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(d.path().join("usr/share/mios")).unwrap();
        std::fs::write(
            d.path().join(SSOT),
            "[build.quadlet_render]\nextensions = [\"toml\"]\nmax_depth = 2\n",
        )
        .unwrap();
        let e = load_config(d.path()).expect_err("must refuse");
        assert!(e.contains("dirs"), "{e}");
    }

    #[test]
    fn an_empty_list_cannot_run_rather_than_rendering_nothing() {
        let d = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(d.path().join("usr/share/mios")).unwrap();
        std::fs::write(
            d.path().join(SSOT),
            "[build.quadlet_render]\ndirs = []\nextensions = [\"toml\"]\nmax_depth = 2\nruntime_ref_directives = [\"ExecStart\"]\n",
        )
        .unwrap();
        let e = load_config(d.path()).expect_err("must refuse");
        assert!(e.contains("empty"), "{e}");
    }

    #[test]
    fn a_malformed_ssot_cannot_run() {
        let d = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(d.path().join("usr/share/mios")).unwrap();
        std::fs::write(d.path().join(SSOT), "[[[not toml").unwrap();
        let e = load_config(d.path()).expect_err("must refuse");
        assert!(e.contains("did not parse"), "{e}");
    }
}
