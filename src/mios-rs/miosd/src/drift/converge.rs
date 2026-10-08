// AI-hint: Convergence and cross-subsystem consistency checks for miosd drift runner.
// AI-related: usr/share/mios/mios.toml, usr/lib/systemd/system-preset, usr/share/containers/systemd/mios-llm-heavy-alt.container, usr/lib/mios/agent-pipe/test_mios_router_parity.py, usr/lib/mios/agent-pipe/tests/router_corpus.json

use super::audit::{self, Audit};
use super::{Check, DriftCtx, Verdict};
use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::process::Command;

pub struct ConvergeSSOTCheck;
impl Check for ConvergeSSOTCheck {
    fn id(&self) -> &'static str {
        "check_converge_ssot"
    }
    fn describe(&self) -> &'static str {
        "Assert system convergence scripts agree with SSOT model"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict(converge(ctx))
    }
}

pub struct GuacamoleConsistencyCheck;
impl Check for GuacamoleConsistencyCheck {
    fn id(&self) -> &'static str {
        "check_guacamole_consistency"
    }
    fn describe(&self) -> &'static str {
        "Assert guacamole configuration matches SSOT"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        super::audit::native(ctx, "mios-gen", &["render-desktop", "--check"])
    }
}

pub struct RouterParityCheck;
impl Check for RouterParityCheck {
    fn id(&self) -> &'static str {
        "check_router_parity"
    }
    fn describe(&self) -> &'static str {
        "Assert model router configuration matches SSOT"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict(router(ctx))
    }
}

const SSOT: &str = "usr/share/mios/mios.toml";
// The lane [converge.inference].retire_heavy_alt retires (the legacy check named it too).
const HEAVY_ALT: &str = "mios-llm-heavy-alt";
const INSTALL_KEYS: [&str; 3] = ["WantedBy", "RequiredBy", "UpheldBy"];
const QUADLET_DIRS: [&str; 3] = [
    "usr/share/containers/systemd",
    "usr/lib/containers/systemd",
    "etc/containers/systemd",
];

/// 1-based line of `key =` inside `[section]` (else the header) for path:line diagnostics.
fn ssot_line(text: &str, section: &str, key: &str) -> usize {
    let (mut active, mut header) = (false, 0);
    for (index, raw) in text.lines().enumerate() {
        let line = raw.split('#').next().unwrap_or("").trim();
        if line.starts_with('[') {
            active = line.trim_matches(|c| c == '[' || c == ']').trim() == section;
            if active && header == 0 {
                header = index + 1;
            }
        } else if active
            && line
                .strip_prefix(key)
                .is_some_and(|rest| rest.trim_start().starts_with('='))
        {
            return index + 1;
        }
    }
    header.max(1)
}

fn field<'a>(
    doc: &'a toml::Value,
    text: &str,
    section: &str,
    key: &str,
) -> Result<(&'a toml::Value, String), String> {
    let at = format!("{SSOT}:{}", ssot_line(text, section, key));
    let value = audit::at(doc, &format!("{section}.{key}"))
        .map_err(|e| format!("{at}: {e}; declare it"))?;
    Ok((value, at))
}

fn declared(value: &toml::Value) -> bool {
    value
        .as_str()
        .map(|s| !s.trim().is_empty())
        .or_else(|| value.as_array().map(|a| !a.is_empty()))
        .unwrap_or(true)
}

// Every value used to come from ${MIOS_CONV_*:-literal}, which nothing exports, so the
// legacy check graded its own drifted defaults. Read the SSOT only; a missing key fails.
fn converge(ctx: &DriftCtx) -> Audit {
    let text = audit::read(&ctx.root, SSOT)?;
    let doc: toml::Value = text.parse().map_err(|e| format!("{SSOT}: {e}"))?;
    let mut errors = Vec::new();
    let (retire, at) = field(&doc, &text, "converge.inference", "retire_heavy_alt")?;
    let retire = retire
        .as_bool()
        .ok_or_else(|| format!("{at}: [converge.inference].retire_heavy_alt must be a boolean"))?;
    let (dir, at) = field(&doc, &text, "converge.memory", "cold_storage_dir")?;
    let dir = dir
        .as_str()
        .ok_or_else(|| format!("{at}: [converge.memory].cold_storage_dir must be a path string"))?;
    if dir.contains("/tenants/") {
        errors.push(format!("{at}: [converge.memory].cold_storage_dir {dir:?} sits inside a CephFS tenants mount; keep cold archives outside /tenants/"));
    }
    let (days, at) = field(&doc, &text, "converge.memory", "cold_retention_days")?;
    if !days.as_integer().is_some_and(|d| d >= 1) {
        errors.push(format!(
            "{at}: [converge.memory].cold_retention_days must be an integer >= 1, got {days}"
        ));
    }
    let (level, at) = field(&doc, &text, "converge.memory", "cold_zstd_level")?;
    if !level.as_integer().is_some_and(|l| (1..=19).contains(&l)) {
        errors.push(format!(
            "{at}: [converge.memory].cold_zstd_level must be an integer 1..19, got {level}"
        ));
    }
    let (vec, vec_at) = field(&doc, &text, "converge.memory", "sqlite_vec_enable")?;
    let vec = vec.as_bool().ok_or_else(|| {
        format!("{vec_at}: [converge.memory].sqlite_vec_enable must be a boolean")
    })?;
    let mut subjects = 5;
    if retire {
        subjects += heavy_alt_enablement(ctx, &doc, &text, &mut errors)?;
    }
    if vec {
        subjects += sqlite_vec_installed(ctx, &doc, &vec_at, &mut errors)?;
    }
    audit::finish(
        subjects,
        errors,
        "[converge] SSOT bounds and the tree surfaces they govern",
    )
}

/// `[Section]` / `key=value` entries of a systemd or Quadlet unit, with 1-based lines.
fn unit_entries(text: &str) -> Vec<(usize, String, String, String)> {
    let (mut section, mut out) = (String::new(), Vec::new());
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') || line.starts_with(';') {
            continue;
        }
        if line.starts_with('[') {
            section = line.trim_matches(|c| c == '[' || c == ']').to_owned();
            continue;
        }
        if let Some((key, value)) = line.split_once('=') {
            out.push((
                index + 1,
                section.clone(),
                key.trim().to_owned(),
                value.trim().to_owned(),
            ));
        }
    }
    out
}

/// fnmatch(3) as systemd presets use it: `*`, `?` and `[...]` classes.
fn glob(pattern: &[u8], name: &[u8]) -> bool {
    match (pattern.first(), name.first()) {
        (None, None) => true,
        (Some(b'*'), _) => {
            glob(&pattern[1..], name) || (!name.is_empty() && glob(pattern, &name[1..]))
        }
        (Some(b'?'), Some(_)) => glob(&pattern[1..], &name[1..]),
        (Some(b'['), Some(c)) => {
            let Some(end) = pattern
                .iter()
                .skip(2)
                .position(|b| *b == b']')
                .map(|i| i + 2)
            else {
                return *c == b'[' && glob(&pattern[1..], &name[1..]);
            };
            let class = &pattern[1..end];
            let (negate, class) = match class.first() {
                Some(b'!' | b'^') => (true, &class[1..]),
                _ => (false, class),
            };
            let (mut hit, mut i) = (false, 0);
            while i < class.len() {
                if i + 2 < class.len() && class[i + 1] == b'-' {
                    hit |= (class[i]..=class[i + 2]).contains(c);
                    i += 3;
                } else {
                    hit |= class[i] == *c;
                    i += 1;
                }
            }
            hit != negate && glob(&pattern[end + 1..], &name[1..])
        }
        (Some(p), Some(c)) if p == c => glob(&pattern[1..], &name[1..]),
        _ => false,
    }
}

/// The legacy check asked the LIVE host (`systemctl is-enabled`), which says nothing about
/// the image and was silently skipped wherever systemctl was absent. Retirement is asserted
/// on every surface the TREE enables a unit through: presets, .wants/.requires/.upholds
/// links, the Quadlet's [Install], its Pod= membership (the generated pod service Wants=
/// every member), and the SSOT [containers.*]/[pods.*] tables those Quadlets project from.
fn heavy_alt_enablement(
    ctx: &DriftCtx,
    doc: &toml::Value,
    text: &str,
    errors: &mut Vec<String>,
) -> Result<usize, String> {
    let unit = format!("{HEAVY_ALT}.service");
    let why = "although [converge.inference].retire_heavy_alt = true";
    // Presets: the first matching line wins across files ordered by name; /etc shadows /usr/lib.
    let mut presets = BTreeMap::new();
    for dir in ["usr/lib/systemd/system-preset", "etc/systemd/system-preset"] {
        if dir.starts_with("etc/") && !ctx.root.join(dir).is_dir() {
            continue;
        }
        for path in audit::files(&ctx.root, dir)? {
            if let Some(name) = path
                .strip_prefix(&format!("{dir}/"))
                .filter(|n| n.ends_with(".preset") && !n.contains('/'))
            {
                presets.insert(name.to_owned(), path.clone());
            }
        }
    }
    if presets.is_empty() {
        return Err(format!("usr/lib/systemd/system-preset: no *.preset files; cannot tell whether {unit} is enabled"));
    }
    let mut surfaces = presets.len();
    'presets: for path in presets.values() {
        for (index, line) in audit::read(&ctx.root, path)?.lines().enumerate() {
            let mut words = line.split_whitespace();
            let (Some(verb), Some(pattern)) = (words.next(), words.next()) else {
                continue;
            };
            if verb.starts_with('#')
                || verb.starts_with(';')
                || !glob(pattern.as_bytes(), unit.as_bytes())
            {
                continue;
            }
            if verb == "enable" {
                errors.push(format!(
                    "{path}:{}: '{}' enables {unit} {why}; put 'disable {unit}' ahead of it",
                    index + 1,
                    line.trim()
                ));
            }
            break 'presets;
        }
    }
    for dir in ["usr/lib/systemd/system", "etc/systemd/system"] {
        let entries = match fs::read_dir(ctx.root.join(dir)) {
            Ok(entries) => entries,
            Err(_) if dir.starts_with("etc/") => continue,
            Err(e) => {
                return Err(format!(
                    "{dir}: {e}; the unit directory is a required subject"
                ))
            }
        };
        for entry in entries {
            let entry = entry.map_err(|e| format!("{dir}: {e}"))?;
            let name = entry.file_name().to_string_lossy().into_owned();
            if ![".wants", ".requires", ".upholds"]
                .iter()
                .any(|s| name.ends_with(s))
                || !entry.path().is_dir()
            {
                continue;
            }
            surfaces += 1;
            // symlink_metadata: a dangling link still enables the unit once it is installed.
            if fs::symlink_metadata(entry.path().join(&unit)).is_ok() {
                errors.push(format!(
                    "{dir}/{name}/{unit}:1: links {unit} into {name} {why}; remove the link"
                ));
            }
        }
    }
    let mut quadlets = Vec::new();
    for dir in QUADLET_DIRS {
        if ctx.root.join(dir).is_dir() {
            quadlets.extend(audit::files(&ctx.root, dir)?);
        }
    }
    let base = |path: &str| path.rsplit('/').next().unwrap_or(path).to_owned();
    let (own, dropins) = (
        format!("{HEAVY_ALT}.container"),
        format!("/{HEAVY_ALT}.container.d/"),
    );
    let mut pods = Vec::new();
    for path in quadlets
        .iter()
        .filter(|p| base(p) == own || (p.contains(&dropins) && p.ends_with(".conf")))
    {
        surfaces += 1;
        for (line, section, key, value) in unit_entries(&audit::read(&ctx.root, path)?) {
            if section == "Install" && INSTALL_KEYS.contains(&key.as_str()) && !value.is_empty() {
                errors.push(format!("{path}:{line}: [Install] {key}={value} enables {unit} {why}; drop [containers.{HEAVY_ALT}.Install] and regenerate the Quadlet"));
            }
            if section == "Container" && key == "Pod" {
                pods.push((path.clone(), line, value));
            }
        }
    }
    for (path, line, pod) in pods {
        // An unresolvable Pod= makes Quadlet refuse the member: broken, but not enabled.
        let Some(pod_path) = quadlets.iter().find(|p| base(p) == pod) else {
            continue;
        };
        let enabled = unit_entries(&audit::read(&ctx.root, pod_path)?).iter().any(
            |(_, section, key, value)| {
                section == "Install" && INSTALL_KEYS.contains(&key.as_str()) && !value.is_empty()
            },
        );
        if enabled {
            errors.push(format!("{path}:{line}: Pod={pod} joins {pod_path}, an enabled pod whose service Wants= every member, so {unit} starts {why}; remove {HEAVY_ALT} from the pod"));
        }
    }
    surfaces += 1;
    let section = format!("containers.{HEAVY_ALT}.Install");
    if let Some(install) = doc
        .get("containers")
        .and_then(|c| c.get(HEAVY_ALT))
        .and_then(|c| c.get("Install"))
        .and_then(toml::Value::as_table)
    {
        for key in INSTALL_KEYS {
            if install.get(key).is_some_and(declared) {
                errors.push(format!("{SSOT}:{}: [{section}].{key} enables {unit} {why}; delete [{section}] and regenerate the Quadlet", ssot_line(text, &section, key)));
            }
        }
    }
    if let Some(table) = doc.get("pods").and_then(toml::Value::as_table) {
        for (name, pod) in table {
            surfaces += 1;
            let member = pod
                .get("members")
                .and_then(toml::Value::as_array)
                .is_some_and(|m| m.iter().any(|v| v.as_str() == Some(HEAVY_ALT)));
            if member
                && ["wanted_by", "required_by", "upheld_by"]
                    .iter()
                    .any(|k| pod.get(*k).is_some_and(declared))
            {
                let section = format!("pods.{name}");
                errors.push(format!("{SSOT}:{}: [{section}].members includes {HEAVY_ALT} in an enabled pod (its service Wants= every member) {why}; remove it from members", ssot_line(text, &section, "members")));
            }
        }
    }
    Ok(surfaces)
}

/// PEP 503-normalised project name a requirements.txt line declares, if any.
fn requirement(line: &str) -> Option<String> {
    let line = line.split('#').next()?.trim();
    if line.starts_with('-') {
        return None;
    }
    let name: String = line
        .chars()
        .take_while(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.'))
        .collect();
    let mut out = String::new();
    for c in name.to_ascii_lowercase().chars() {
        if !matches!(c, '-' | '_' | '.') {
            out.push(c);
        } else if !out.ends_with('-') {
            out.push('-');
        }
    }
    (!out.is_empty()).then_some(out)
}

/// The legacy check imported sqlite_vec on the HOST running the gate, which says nothing
/// about the image. The tree property: a package set the image installs declares it --
/// a requirements file phase 72 pip-installs (automation/72-hermes-agent.sh reads exactly
/// [packages.ai].python_requirements) or the Fedora RPM in an enabled [packages.*].pkgs.
fn sqlite_vec_installed(
    ctx: &DriftCtx,
    doc: &toml::Value,
    at: &str,
    errors: &mut Vec<String>,
) -> Result<usize, String> {
    let (mut examined, mut found) = (0, false);
    for file in audit::strings(doc, "packages.ai.python_requirements")? {
        examined += 1;
        found |= audit::read(&ctx.root, file.trim_start_matches('/'))?
            .lines()
            .any(|line| requirement(line).as_deref() == Some("sqlite-vec"));
    }
    let packages = audit::at(doc, "packages")?
        .as_table()
        .ok_or("SSOT packages must be a table")?;
    for section in packages.values().filter_map(toml::Value::as_table) {
        if section.get("enable").and_then(toml::Value::as_bool) == Some(false) {
            continue;
        }
        examined += 1;
        found |= section
            .get("pkgs")
            .and_then(toml::Value::as_array)
            .is_some_and(|pkgs| {
                pkgs.iter()
                    .any(|p| p.as_str() == Some("python3-sqlite-vec"))
            });
    }
    if !found {
        errors.push(format!("{at}: [converge.memory].sqlite_vec_enable = true but no package set the image installs declares sqlite_vec; add sqlite-vec to a [packages.ai].python_requirements file or python3-sqlite-vec to an enabled [packages.*].pkgs"));
    }
    Ok(examined)
}

const PARITY_TEST: &str = "usr/lib/mios/agent-pipe/test_mios_router_parity.py";
const CORPUS: &str = "usr/lib/mios/agent-pipe/tests/router_corpus.json";
const SERVER: &str = "usr/lib/mios/agent-pipe/server.py";
const ROUTING_PACKAGE: &str = "usr/lib/mios/agent-pipe/mios_pipe";

fn router(ctx: &DriftCtx) -> Audit {
    let missing: Vec<String> = [PARITY_TEST, CORPUS]
        .iter()
        .filter(|p| !ctx.root.join(p).is_file())
        .map(|p| format!("{p}:1: router parity input is missing; restore it"))
        .collect();
    if !missing.is_empty() {
        return Err(missing.join("\n"));
    }
    let (rows, intents) = corpus_intents(ctx)?;
    let mut errors = Vec::new();
    if let Err(e) = parity(ctx) {
        errors.push(e);
    }
    let scanned = intent_coverage(ctx, &intents, &mut errors)?;
    audit::finish(
        rows + scanned,
        errors,
        "router Stage-2 parity (corpus rows and routing sources)",
    )
}

fn corpus_intents(ctx: &DriftCtx) -> Result<(usize, BTreeSet<String>), String> {
    let rows: Vec<serde_json::Value> = serde_json::from_str(&audit::read(&ctx.root, CORPUS)?)
        .map_err(|e| {
            format!(
                "{CORPUS}:{}: not a JSON array of corpus rows: {e}",
                e.line()
            )
        })?;
    if rows.is_empty() {
        return Err(format!(
            "{CORPUS}:1: corpus has no rows, so router parity is untested; add rows"
        ));
    }
    let mut intents = BTreeSet::new();
    for (index, row) in rows.iter().enumerate() {
        if !row.is_object() {
            return Err(format!("{CORPUS}:1: row {index} is not an object"));
        }
        match row.get("input").and_then(|input| input.get("intent")) {
            Some(serde_json::Value::String(intent)) if !intent.is_empty() => {
                intents.insert(intent.trim().to_lowercase());
            }
            None | Some(serde_json::Value::Null | serde_json::Value::String(_)) => {}
            Some(other) => {
                return Err(format!(
                    "{CORPUS}:1: row {index} input.intent {other} is not a string"
                ))
            }
        }
    }
    Ok((rows.len(), intents))
}

/// Running the agent-pipe's own parity test is legitimate: the subject IS Python behaviour.
/// Hermetic: the SSOT interpreter with -E -s -B (no PYTHON* env, no user site, no bytecode
/// written into the tree), a cleared environment, and a scratch cwd/HOME/TMPDIR. The
/// script's own directory stays on sys.path because that is how it imports mios_pipe.
fn parity(ctx: &DriftCtx) -> Result<(), String> {
    let config = audit::ssot(ctx)?;
    let python = audit::at(&config, "drift.lint.python")?.as_str().filter(|s| !s.is_empty())
        .ok_or("SSOT drift.lint.python is empty; name the interpreter that runs the router parity test")?.to_owned();
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or_default();
    let scratch = std::env::temp_dir().join(format!(
        "miosd-router-parity-{}-{stamp}",
        std::process::id()
    ));
    fs::create_dir_all(&scratch).map_err(|e| format!("{}: {e}", scratch.display()))?;
    let mut command = Command::new(&python);
    command
        .args(["-E", "-s", "-B"])
        .arg(ctx.root.join(PARITY_TEST))
        .current_dir(&scratch)
        .env_clear()
        .env("HOME", &scratch)
        .env("TMPDIR", &scratch);
    for name in ["PATH", "SYSTEMROOT"] {
        if let Some(value) = std::env::var_os(name) {
            command.env(name, value);
        }
    }
    let output = command.output();
    let _ = fs::remove_dir_all(&scratch);
    let output = output.map_err(|e| format!("{PARITY_TEST}:1: cannot run SSOT drift.lint.python {python:?}: {e}; install it or correct [drift.lint].python"))?;
    if output.status.success() {
        return Ok(());
    }
    let log = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    let detail: Vec<&str> = log
        .lines()
        .filter(|line| !line.starts_with("[PASS]") && !line.trim().is_empty())
        .collect();
    Err(format!("{PARITY_TEST}:1: router parity test {} on {CORPUS}; the Stage-2 router and the server.py intent cascade disagree -- fix the router or the corpus row:\n    {}", output.status, detail.join("\n    ")))
}

/// Port of tools/drift-checks.py check_router_intent_coverage: every `intent == "x"` branch
/// in server.py or mios_pipe/**/*.py must have a corpus row, or parity never exercises it.
fn intent_coverage(
    ctx: &DriftCtx,
    intents: &BTreeSet<String>,
    errors: &mut Vec<String>,
) -> Result<usize, String> {
    let branch = Regex::new(
        r#"(?:intent\s*==|get\s*\(\s*["']intent["']\s*\)\s*==)\s*["']([a-zA-Z0-9_]+)["']"#,
    )
    .map_err(|e| e.to_string())?;
    let mut sources = vec![SERVER.to_owned()];
    sources.extend(
        audit::files(&ctx.root, ROUTING_PACKAGE)?
            .into_iter()
            .filter(|p| p.ends_with(".py")),
    );
    let mut scanned = 0;
    for path in sources {
        if path.rsplit('/').next().unwrap_or("").contains("test_") {
            continue;
        }
        scanned += 1;
        // Unlike the legacy scan, an unreadable source fails instead of being skipped.
        let text = audit::read(&ctx.root, &path)?;
        for capture in branch.captures_iter(&text) {
            let (Some(whole), Some(intent)) = (capture.get(0), capture.get(1)) else {
                continue;
            };
            let intent = intent.as_str().to_lowercase();
            if !intents.contains(&intent) {
                let line = text[..whole.start()].matches('\n').count() + 1;
                errors.push(format!("{path}:{line}: intent == {intent:?} branch is not represented in {CORPUS}; add a corpus row whose input.intent is {intent:?}"));
            }
        }
    }
    Ok(scanned)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(
        root: &std::path::Path,
        rel: &str,
        body: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let path = root.join(rel);
        fs::create_dir_all(path.parent().ok_or("no parent")?)?;
        fs::write(path, body)?;
        Ok(())
    }

    const CONVERGE: &str = "[converge.inference]\nretire_heavy_alt = false\n[converge.memory]\nsqlite_vec_enable = false\ncold_storage_dir = \"/var/lib/mios/history/\"\ncold_retention_days = 90\ncold_zstd_level = 10\n";

    #[test]
    fn converge_reads_ssot_bounds_and_fails_on_missing_or_illegal_values(
    ) -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        let root = temp.path();
        let ctx = DriftCtx::new(root.into(), false);
        assert!(converge(&ctx).is_err());
        write(root, SSOT, "[other]\nx = 1\n")?;
        assert!(converge(&ctx)
            .is_err_and(|e| e.contains("converge.inference.retire_heavy_alt is missing")));
        write(root, SSOT, CONVERGE)?;
        assert!(converge(&ctx).is_ok_and(|m| m.contains("5 subject")));
        write(
            root,
            SSOT,
            &CONVERGE.replace("/var/lib/mios/history/", "/mnt/ceph/tenants/a/"),
        )?;
        assert!(converge(&ctx).is_err_and(|e| e
            .contains("mios.toml:5: [converge.memory].cold_storage_dir")
            && e.contains("tenants mount")));
        write(root, SSOT, &CONVERGE.replace("= 90", "= 0"))?;
        assert!(converge(&ctx)
            .is_err_and(|e| e.contains("mios.toml:6:") && e.contains("integer >= 1, got 0")));
        write(root, SSOT, &CONVERGE.replace("= 90", "= \"90\""))?;
        assert!(converge(&ctx).is_err_and(|e| e.contains("cold_retention_days must be an integer")));
        write(root, SSOT, &CONVERGE.replace("= 10", "= 20"))?;
        assert!(converge(&ctx)
            .is_err_and(|e| e.contains("mios.toml:7:") && e.contains("1..19, got 20")));
        write(
            root,
            SSOT,
            &CONVERGE.replace("retire_heavy_alt = false", "retire_heavy_alt = \"no\""),
        )?;
        assert!(converge(&ctx).is_err_and(|e| e.contains("must be a boolean")));
        Ok(())
    }

    #[test]
    fn retired_heavy_alt_must_not_be_enabled_by_any_tree_surface(
    ) -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        let root = temp.path();
        let ctx = DriftCtx::new(root.into(), false);
        let config = CONVERGE.replace("retire_heavy_alt = false", "retire_heavy_alt = true");
        write(root, SSOT, &config)?;
        assert!(converge(&ctx).is_err_and(|e| e.contains("system-preset")));
        let preset = "usr/lib/systemd/system-preset/90-mios.preset";
        write(root, preset, "# enable mios-llm-heavy-alt.service\ndisable mios-llm-heavy-alt.service\nenable mios-*\n")?;
        assert!(converge(&ctx).is_err_and(|e| e.contains("unit directory is a required subject")));
        fs::create_dir_all(root.join("usr/lib/systemd/system/multi-user.target.wants"))?;
        let quadlet = "usr/share/containers/systemd/mios-llm-heavy-alt.container";
        write(root, quadlet, "[Container]\nImage=x\nPod=mios-ai.pod\n")?;
        write(
            root,
            "usr/share/containers/systemd/mios-ai.pod",
            "[Pod]\nPodName=mios-ai\n",
        )?;
        write(
            root,
            SSOT,
            &format!(
                "{config}[pods.mios-ai]\nmembers = [\"mios-llm-heavy-alt\"]\nwanted_by = []\n"
            ),
        )?;
        assert!(converge(&ctx).is_ok());
        write(
            root,
            preset,
            "enable mios-llm-heavy-*.service\ndisable mios-llm-heavy-alt.service\n",
        )?;
        assert!(converge(&ctx).is_err_and(
            |e| e.contains("90-mios.preset:1: 'enable mios-llm-heavy-*.service' enables")
        ));
        write(root, preset, "disable *\n")?;
        write(
            root,
            "usr/lib/systemd/system/multi-user.target.wants/mios-llm-heavy-alt.service",
            "",
        )?;
        assert!(converge(&ctx).is_err_and(
            |e| e.contains("multi-user.target.wants/mios-llm-heavy-alt.service:1: links")
        ));
        fs::remove_file(
            root.join("usr/lib/systemd/system/multi-user.target.wants/mios-llm-heavy-alt.service"),
        )?;
        write(root, quadlet, "[Container]\nImage=x\nPod=mios-ai.pod\n\n[Install]\nWantedBy=multi-user.target default.target\n")?;
        assert!(converge(&ctx)
            .is_err_and(|e| e.contains("mios-llm-heavy-alt.container:6: [Install] WantedBy=")));
        write(root, quadlet, "[Container]\nImage=x\nPod=mios-ai.pod\n")?;
        write(
            root,
            "usr/share/containers/systemd/mios-ai.pod",
            "[Pod]\nPodName=mios-ai\n[Install]\nWantedBy=multi-user.target\n",
        )?;
        assert!(converge(&ctx)
            .is_err_and(|e| e.contains("mios-llm-heavy-alt.container:3: Pod=mios-ai.pod joins")));
        write(
            root,
            "usr/share/containers/systemd/mios-ai.pod",
            "[Pod]\nPodName=mios-ai\n",
        )?;
        write(root, SSOT, &format!("{config}[containers.mios-llm-heavy-alt.Install]\nWantedBy = \"multi-user.target\"\n[pods.mios-ai]\nmembers = [\"mios-llm-heavy-alt\"]\nwanted_by = [\"multi-user.target\"]\n"))?;
        assert!(converge(&ctx).is_err_and(|e| e
            .contains("mios.toml:9: [containers.mios-llm-heavy-alt.Install].WantedBy")
            && e.contains("mios.toml:11: [pods.mios-ai].members")));
        Ok(())
    }

    #[test]
    fn sqlite_vec_must_be_declared_by_an_installed_package_set(
    ) -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        let root = temp.path();
        let ctx = DriftCtx::new(root.into(), false);
        let config = CONVERGE.replace("sqlite_vec_enable = false", "sqlite_vec_enable = true");
        write(root, SSOT, &config)?;
        assert!(
            converge(&ctx).is_err_and(|e| e.contains("packages.ai.python_requirements is missing"))
        );
        let packages = "[packages.ai]\npython_requirements = [\"usr/lib/mios/agent-pipe/requirements.txt\"]\npkgs = [\"python3\"]\n[packages.bloat]\nenable = false\npkgs = [\"python3-sqlite-vec\"]\n";
        write(root, SSOT, &format!("{config}{packages}"))?;
        assert!(converge(&ctx).is_err_and(|e| e.contains("requirements.txt")));
        write(
            root,
            "usr/lib/mios/agent-pipe/requirements.txt",
            "# sqlite-vec\nfastapi\nsqlite-vecx\n",
        )?;
        assert!(converge(&ctx).is_err_and(|e| e.contains(
            "mios.toml:4: [converge.memory].sqlite_vec_enable = true but no package set"
        )));
        write(
            root,
            "usr/lib/mios/agent-pipe/requirements.txt",
            "fastapi\nSqlite_Vec>=0.1 ; python_version >= '3.9'\n",
        )?;
        assert!(converge(&ctx).is_ok());
        write(
            root,
            "usr/lib/mios/agent-pipe/requirements.txt",
            "fastapi\n",
        )?;
        write(
            root,
            SSOT,
            &format!(
                "{config}{}",
                packages.replace("enable = false", "enable = true")
            ),
        )?;
        assert!(converge(&ctx).is_ok());
        assert_eq!(
            requirement("  Foo.Bar__baz[extra]>=1 # c").as_deref(),
            Some("foo-bar-baz")
        );
        assert_eq!(requirement("-r other.txt"), None);
        Ok(())
    }

    #[test]
    fn router_parity_runs_the_test_and_maps_every_intent_branch(
    ) -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        let root = temp.path();
        let ctx = DriftCtx::new(root.into(), false);
        assert!(router(&ctx).is_err_and(|e| e.contains("router parity input is missing")));
        write(root, SSOT, "[drift.lint]\npython = \"python3\"\n")?;
        let test = "import json, os, sys\nrows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'router_corpus.json')))\nbad = [r for r in rows if r.get('expected_mode') != r.get('input', {}).get('intent')]\nfor r in bad:\n    print('[FAIL] ' + r['description'])\nprint('[PASS] ran')\nsys.exit(1 if bad else 0)\n";
        write(root, PARITY_TEST, test)?;
        write(root, CORPUS, "[]")?;
        write(
            root,
            SERVER,
            "def route(plan):\n    if plan.get(\"intent\") == \"chat\":\n        return 1\n",
        )?;
        write(
            root,
            "usr/lib/mios/agent-pipe/mios_pipe/routing/router.py",
            "def r(intent):\n    return intent == 'CHAT'\n",
        )?;
        write(
            root,
            "usr/lib/mios/agent-pipe/mios_pipe/routing/test_router.py",
            "assert intent == 'ghost'\n",
        )?;
        assert!(router(&ctx).is_err_and(|e| e.contains("router_corpus.json:1: corpus has no rows")));
        let corpus = "[{\"description\":\"chat row\",\"input\":{\"intent\":\"chat\"},\"expected_mode\":\"chat\"},{\"description\":\"empty\",\"input\":{}}]";
        write(
            root,
            CORPUS,
            &corpus.replace(",\"input\":{}}", ",\"input\":{},\"expected_mode\":null}"),
        )?;
        assert!(router(&ctx).is_ok_and(|m| m.contains("4 subject")));
        write(
            root,
            CORPUS,
            &corpus.replace("\"expected_mode\":\"chat\"", "\"expected_mode\":\"agent\""),
        )?;
        assert!(router(&ctx).is_err_and(|e| e.contains("router parity test")
            && e.contains("[FAIL] chat row")
            && !e.contains("[PASS]")));
        write(
            root,
            CORPUS,
            &corpus.replace(",\"input\":{}}", ",\"input\":{},\"expected_mode\":null}"),
        )?;
        write(root, SERVER, "def route(plan):\n    if plan.get(\"intent\") == \"chat\":\n        return 1\n    elif intent == 'dag':\n        return 2\n")?;
        assert!(router(&ctx).is_err_and(|e| e
            .contains("server.py:4: intent == \"dag\" branch is not represented")
            && !e.contains("ghost")));
        fs::remove_file(root.join(SERVER))?;
        assert!(router(&ctx).is_err_and(|e| e.contains("server.py")));
        write(root, SERVER, "\n")?;
        write(
            root,
            SSOT,
            "[drift.lint]\npython = \"mios-no-such-python\"\n",
        )?;
        assert!(router(&ctx).is_err_and(|e| e.contains("cannot run SSOT drift.lint.python")));
        Ok(())
    }

    #[test]
    fn preset_globs_follow_fnmatch() {
        assert!(glob(b"mios-*", b"mios-llm-heavy-alt.service"));
        assert!(glob(
            b"mios-llm-heavy-?lt.service",
            b"mios-llm-heavy-alt.service"
        ));
        assert!(glob(
            b"mios-llm-heavy-[a-c]lt.*",
            b"mios-llm-heavy-alt.service"
        ));
        assert!(!glob(
            b"mios-llm-heavy-[!a]lt.*",
            b"mios-llm-heavy-alt.service"
        ));
        assert!(!glob(
            b"mios-llm-heavy.service",
            b"mios-llm-heavy-alt.service"
        ));
    }
}
