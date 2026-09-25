// AI-hint: xtask -- build-resolver, regen, and artifact-prompt, which renders the repo-root ARTIFACT-PROMPT.md from mios.toml [artifacts.daily] through usr/share/mios/templates/artifact-prompt; --check is its regenerate-and-diff gate.
// AI-related: tools/native/Cargo.toml, automation/98-drift-checks.sh, tools/sync-generated.sh, usr/share/mios/mios.toml, usr/share/mios/templates/artifact-prompt, ARTIFACT-PROMPT.md
use std::env;
use std::process::Command;

fn parse_task(args: &[String]) -> &str {
    args.first().map(|s| s.as_str()).unwrap_or("help")
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let task = parse_task(&args);

    match task {
        "build-resolver" => {
            println!("[xtask] Building mios-resolver in release mode...");
            let status = Command::new("cargo")
                .args(["build", "--release", "-p", "mios-resolver"])
                .status()
                .expect("Failed to execute cargo build");
            if !status.success() {
                std::process::exit(1);
            }
            println!("[xtask] mios-resolver build complete.");
        }
        "regen" => {
            println!("[xtask] Regenerating SSOT projections...");
            let status = Command::new("cargo")
                .args(["run", "-p", "mios-resolver", "--", "--emit=shell"])
                .status()
                .expect("Failed to execute cargo run");
            if !status.success() {
                std::process::exit(1);
            }
            println!("[xtask] Regeneration complete.");
        }
        "artifact-prompt" => std::process::exit(artifact_prompt::run(&args[1..])),
        _ => {
            println!(
                "Usage: cargo xtask <build-resolver|regen|artifact-prompt [--root DIR] [--check]>"
            );
        }
    }
}

/// ARTIFACT-PROMPT.md: [artifacts.daily] values joined into the one template.
/// The daily agent fetches it fresh each run, so a render is refused when it
/// would offer ACCEPTED, carry a commit ID, leave a placeholder unfilled, name
/// an untracked sub-instruction, or ship a non-strict schema.
mod artifact_prompt {
    #![forbid(unsafe_code)]
    #![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

    use serde_json::Value as Json;
    use std::collections::BTreeSet;
    use std::path::{Path, PathBuf};
    use std::process::Command;

    pub const SSOT: &str = "usr/share/mios/mios.toml";
    pub const TEMPLATES: &str = "usr/share/mios/templates";
    /// The ingest validator's verdict. An agent that could write it would be
    /// grading its own work, so no SSOT value may ever offer it.
    pub const VALIDATOR_VERDICT: &str = "ACCEPTED";
    /// The verdict roles the template's ladder is written against.
    const ROLES: [&str; 3] = ["submitted", "rejected", "blocked"];
    /// The deliverables the template's format sections are written against.
    const OUTPUT_IDS: [&str; 4] = ["sft", "dpo", "oci", "manifest"];
    const USAGE: &str = "usage: xtask artifact-prompt [--root DIR] [--check]\n";

    #[derive(Debug, Clone)]
    pub struct Repo {
        pub name: String,
        pub canonical: bool,
        pub git_url: String,
        pub raw_base: String,
        pub api_base: String,
        pub branch: String,
    }

    #[derive(Debug, Clone)]
    pub struct Task {
        pub id: String,
        pub title: String,
        pub root_file: String,
        pub cadence: String,
    }

    #[derive(Debug, Clone)]
    pub struct SubInstruction {
        pub repo: String,
        pub path: String,
        pub purpose: String,
    }

    #[derive(Debug, Clone)]
    pub struct Verdict {
        pub role: String,
        pub word: String,
        pub meaning: String,
    }

    #[derive(Debug, Clone)]
    pub struct Output {
        pub id: String,
        pub file: String,
        pub format: String,
        pub version: String,
        pub describe: String,
        pub schema_name: Option<String>,
    }

    #[derive(Debug, Clone)]
    pub struct Spec {
        pub template: String,
        pub fixed_name: String,
        pub consumer: String,
        pub scheduler: String,
        pub scheduler_item: String,
        pub verdict_prefix: String,
        pub head_ls_remote: String,
        pub head_api: String,
        pub raw_file: String,
        pub self_url: String,
        pub bundle: String,
        pub split_rule: String,
        pub oci_layer_root: String,
        pub verdicts: Vec<Verdict>,
        pub task: Task,
        pub repos: Vec<Repo>,
        pub subs: Vec<SubInstruction>,
        pub outputs: Vec<Output>,
    }

    impl Spec {
        pub fn canonical(&self) -> &Repo {
            // load_spec guarantees exactly one; index 0 is unreachable fallback.
            self.repos
                .iter()
                .find(|r| r.canonical)
                .unwrap_or(&self.repos[0])
        }

        pub fn verdict(&self, role: &str) -> &str {
            self.verdicts
                .iter()
                .find(|v| v.role == role)
                .map(|v| v.word.as_str())
                .unwrap_or("")
        }

        pub fn output(&self, id: &str) -> Option<&Output> {
            self.outputs.iter().find(|o| o.id == id)
        }
    }

    fn text(v: &toml::Value, key: &str, at: &str) -> Result<String, String> {
        let s = v
            .get(key)
            .and_then(|x| x.as_str())
            .ok_or_else(|| format!("{at}.{key} is missing or not a string"))?
            .trim();
        if s.is_empty() {
            return Err(format!("{at}.{key} is empty"));
        }
        Ok(s.to_string())
    }

    fn list<'a>(v: &'a toml::Value, key: &str, at: &str) -> Result<&'a [toml::Value], String> {
        let a = v
            .get(key)
            .and_then(|x| x.as_array())
            .ok_or_else(|| format!("{at}.{key} is missing or not an array"))?;
        if a.is_empty() {
            return Err(format!("{at}.{key} is empty"));
        }
        Ok(a.as_slice())
    }

    fn schema_name_ok(name: &str) -> bool {
        !name.is_empty()
            && name.len() <= 64
            && name
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    }

    /// Reads and validates [artifacts.daily]. Every refusal here is a state in
    /// which the rendered file would send the daily agent somewhere wrong.
    pub fn load_spec(ssot: &str) -> Result<Spec, String> {
        let doc: toml::Value =
            toml::from_str(ssot).map_err(|e| format!("{SSOT} did not parse ({e})"))?;
        let at = "[artifacts.daily]";
        let daily = doc
            .get("artifacts")
            .and_then(|a| a.get("daily"))
            .ok_or_else(|| format!("{SSOT} has no {at} -- nothing to project"))?;

        let template = text(daily, "template", at)?;
        let tat = format!("[templates.{template}]");
        let tcfg = doc
            .get("templates")
            .and_then(|t| t.get(template.as_str()))
            .ok_or_else(|| format!("{at}.template names {tat}, which is not declared (Law 16)"))?;
        let fixed_name = text(tcfg, "fixed_name", &tat)?;
        if tcfg.get("generated").and_then(|g| g.as_bool()) != Some(true) {
            return Err(format!(
                "{tat}.generated must be true: its output is a projection, never hand-written"
            ));
        }

        let mut verdicts = Vec::new();
        for (i, v) in list(daily, "verdicts", at)?.iter().enumerate() {
            let vat = format!("{at}.verdicts[{i}]");
            verdicts.push(Verdict {
                role: text(v, "role", &vat)?,
                word: text(v, "word", &vat)?,
                meaning: text(v, "meaning", &vat)?,
            });
        }
        if let Some(v) = verdicts.iter().find(|v| {
            v.word.eq_ignore_ascii_case(VALIDATOR_VERDICT)
                || v.role.eq_ignore_ascii_case(VALIDATOR_VERDICT)
        }) {
            return Err(format!(
                "{at}.verdicts offers {:?}: {VALIDATOR_VERDICT} is the ingest validator's word \
                 alone and is never an agent verdict",
                v.word
            ));
        }
        for role in ROLES {
            let n = verdicts.iter().filter(|v| v.role == role).count();
            if n != 1 {
                return Err(format!(
                    "{at}.verdicts must declare role {role:?} exactly once (found {n})"
                ));
            }
        }
        if verdicts.len() != ROLES.len() {
            return Err(format!(
                "{at}.verdicts declares {} entries; the verdict is only {}",
                verdicts.len(),
                ROLES.join(" | ")
            ));
        }
        let words: BTreeSet<&str> = verdicts.iter().map(|v| v.word.as_str()).collect();
        if words.len() != verdicts.len() {
            return Err(format!("{at}.verdicts repeats a word"));
        }

        let tasks = list(daily, "tasks", at)?;
        if tasks.len() != 1 {
            return Err(format!(
                "{at}.tasks declares {} tasks; one template renders one root file, so a second \
                 daily task needs its own template",
                tasks.len()
            ));
        }
        let t = &tasks[0];
        let task = Task {
            id: text(t, "id", &format!("{at}.tasks[0]"))?,
            title: text(t, "title", &format!("{at}.tasks[0]"))?,
            root_file: text(t, "root_file", &format!("{at}.tasks[0]"))?,
            cadence: text(t, "cadence", &format!("{at}.tasks[0]"))?,
        };
        if task.root_file != fixed_name {
            return Err(format!(
                "{at}.tasks[0].root_file = {:?} but {tat}.fixed_name = {:?}: the task would \
                 fetch a file the generator never writes",
                task.root_file, fixed_name
            ));
        }

        let mut repos = Vec::new();
        for (i, r) in list(daily, "repos", at)?.iter().enumerate() {
            let rat = format!("{at}.repos[{i}]");
            repos.push(Repo {
                name: text(r, "name", &rat)?,
                canonical: r.get("canonical").and_then(|c| c.as_bool()) == Some(true),
                git_url: text(r, "git_url", &rat)?,
                raw_base: text(r, "raw_base", &rat)?.trim_end_matches('/').to_string(),
                api_base: text(r, "api_base", &rat)?.trim_end_matches('/').to_string(),
                branch: text(r, "default_branch", &rat)?,
            });
        }
        let names: BTreeSet<&str> = repos.iter().map(|r| r.name.as_str()).collect();
        if names.len() != repos.len() {
            return Err(format!("{at}.repos repeats a name"));
        }
        let canon: Vec<&Repo> = repos.iter().filter(|r| r.canonical).collect();
        if canon.len() != 1 {
            return Err(format!(
                "{at}.repos must mark exactly one repo canonical = true (found {})",
                canon.len()
            ));
        }
        let canon_name = canon[0].name.clone();

        let mut subs: Vec<SubInstruction> = Vec::new();
        for (i, s) in list(daily, "sub_instructions", at)?.iter().enumerate() {
            let sat = format!("{at}.sub_instructions[{i}]");
            let sub = SubInstruction {
                repo: text(s, "repo", &sat)?,
                path: text(s, "path", &sat)?,
                purpose: text(s, "purpose", &sat)?,
            };
            if !names.contains(sub.repo.as_str()) {
                return Err(format!(
                    "{sat}.repo = {:?} is not a declared repo",
                    sub.repo
                ));
            }
            // Only the canonical tree is on disk where this runs, so only its
            // paths can be verified; an unverifiable path is a 404 in waiting.
            if sub.repo != canon_name {
                return Err(format!(
                    "{sat} is in {:?}, but only {canon_name:?} paths can be verified against a \
                     tracked tree here",
                    sub.repo
                ));
            }
            if sub.path.starts_with('/')
                || sub.path.contains("..")
                || sub.path.contains("://")
                || sub.path.contains('\\')
            {
                return Err(format!(
                    "{sat}.path = {:?} is not a repo-relative path",
                    sub.path
                ));
            }
            if subs
                .iter()
                .any(|o| o.repo == sub.repo && o.path == sub.path)
            {
                return Err(format!("{sat} repeats {}", sub.path));
            }
            subs.push(sub);
        }

        let mut outputs = Vec::new();
        for (i, o) in list(daily, "outputs", at)?.iter().enumerate() {
            let oat = format!("{at}.outputs[{i}]");
            outputs.push(Output {
                id: text(o, "id", &oat)?,
                file: text(o, "file", &oat)?,
                format: text(o, "format", &oat)?,
                version: text(o, "version", &oat)?,
                describe: text(o, "describe", &oat)?,
                schema_name: o
                    .get("schema_name")
                    .and_then(|s| s.as_str())
                    .map(|s| s.trim().to_string()),
            });
        }
        for id in OUTPUT_IDS {
            if outputs.iter().filter(|o| o.id == id).count() != 1 {
                return Err(format!("{at}.outputs must declare id {id:?} exactly once"));
            }
        }
        let files: BTreeSet<&str> = outputs.iter().map(|o| o.file.as_str()).collect();
        if files.len() != outputs.len() {
            return Err(format!("{at}.outputs repeats a file name"));
        }
        match outputs
            .iter()
            .find(|o| o.id == "manifest")
            .and_then(|o| o.schema_name.as_deref())
        {
            Some(n) if schema_name_ok(n) => {}
            _ => {
                return Err(format!(
                "{at}.outputs manifest entry needs schema_name matching ^[A-Za-z0-9_-]{{1,64}}$ \
                     (the OpenAI json_schema name rule)"
            ))
            }
        }

        Ok(Spec {
            template,
            fixed_name,
            consumer: text(daily, "task_consumer", at)?,
            scheduler: text(daily, "task_scheduler", at)?,
            scheduler_item: text(daily, "task_scheduler_item", at)?,
            verdict_prefix: text(daily, "verdict_prefix", at)?,
            head_ls_remote: text(daily, "head_ls_remote", at)?,
            head_api: text(daily, "head_api", at)?,
            raw_file: text(daily, "raw_file", at)?,
            self_url: text(daily, "self_url", at)?,
            bundle: text(daily, "bundle", at)?,
            split_rule: text(daily, "split_rule", at)?,
            oci_layer_root: text(daily, "oci_layer_root", at)?,
            verdicts,
            task,
            repos,
            subs,
            outputs,
        })
    }

    /// Fills `{key}` fields of an SSOT format string; a field left over is an
    /// SSOT typo that would otherwise ship as a literal brace in a URL.
    pub fn fill(fmt: &str, vars: &[(&str, &str)]) -> Result<String, String> {
        let mut out = fmt.to_string();
        for (k, v) in vars {
            out = out.replace(&format!("{{{k}}}"), v);
        }
        let bytes = out.as_bytes();
        let mut i = 0;
        while let Some(off) = out[i..].find('{') {
            let s = i + off;
            let rest = &out[s + 1..];
            let len = rest
                .find(|c: char| !(c.is_ascii_alphanumeric() || c == '_'))
                .unwrap_or(rest.len());
            if len > 0 && bytes.get(s + 1 + len) == Some(&b'}') {
                return Err(format!(
                    "format string {fmt:?} carries an unknown field {{{}}}",
                    &rest[..len]
                ));
            }
            i = s + 1;
        }
        Ok(out)
    }

    fn sha_token(repo: &str) -> String {
        format!("<{repo}_SHA>")
    }

    fn cell(s: &str) -> String {
        s.replace('|', "\\|").replace('\n', " ")
    }

    fn quoted(items: &[&str]) -> Result<String, String> {
        let mut parts = Vec::with_capacity(items.len());
        for it in items {
            parts.push(serde_json::to_string(it).map_err(|e| format!("json quoting: {e}"))?);
        }
        Ok(parts.join(", "))
    }

    /// The first run of 40 or more hex digits, if any: a commit ID (or any
    /// digest) baked into the file would pin every future run to one revision.
    pub fn find_hex40(s: &str) -> Option<String> {
        let mut run = String::new();
        for c in s.chars().chain(std::iter::once(' ')) {
            if c.is_ascii_hexdigit() {
                run.push(c);
            } else {
                if run.len() >= 40 {
                    return Some(run);
                }
                run.clear();
            }
        }
        None
    }

    /// The fenced ```json blocks of a Markdown document, in order.
    pub fn json_blocks(md: &str) -> Vec<String> {
        let mut blocks = Vec::new();
        let mut cur = String::new();
        let mut inside = false;
        for line in md.lines() {
            let t = line.trim();
            if !inside && t == "```json" {
                inside = true;
                cur.clear();
            } else if inside && t == "```" {
                inside = false;
                blocks.push(cur.clone());
            } else if inside {
                cur.push_str(line);
                cur.push('\n');
            }
        }
        blocks
    }

    fn strict(node: &Json, at: &str) -> Result<(), String> {
        let obj = node
            .as_object()
            .ok_or_else(|| format!("{at} is not a schema object"))?;
        match obj.get("type").and_then(|t| t.as_str()) {
            Some("object") => {
                if obj.get("additionalProperties") != Some(&Json::Bool(false)) {
                    return Err(format!(
                        "{at}: strict mode needs \"additionalProperties\": false"
                    ));
                }
                let props = obj
                    .get("properties")
                    .and_then(|p| p.as_object())
                    .ok_or_else(|| format!("{at}: an object schema needs \"properties\""))?;
                let req: BTreeSet<&str> = obj
                    .get("required")
                    .and_then(|r| r.as_array())
                    .ok_or_else(|| format!("{at}: an object schema needs \"required\""))?
                    .iter()
                    .filter_map(|v| v.as_str())
                    .collect();
                let keys: BTreeSet<&str> = props.keys().map(|k| k.as_str()).collect();
                if req != keys {
                    return Err(format!(
                        "{at}: strict mode requires every property in \"required\" \
                         (required {req:?}, properties {keys:?})"
                    ));
                }
                for (k, v) in props {
                    strict(v, &format!("{at}.{k}"))?;
                }
                Ok(())
            }
            Some("array") => strict(
                obj.get("items")
                    .ok_or_else(|| format!("{at}: an array schema needs \"items\""))?,
                &format!("{at}[]"),
            ),
            Some("string") | Some("integer") | Some("number") | Some("boolean") => Ok(()),
            other => Err(format!("{at}: unsupported schema type {other:?}")),
        }
    }

    /// The run-manifest schema block must be an OpenAI strict json_schema:
    /// the agent is told to validate against it, so a non-strict one would
    /// let it pass a manifest the ingest validator rejects.
    pub fn check_manifest_schema(md: &str, name: &str) -> Result<(), String> {
        let blocks: Vec<String> = json_blocks(md)
            .into_iter()
            .filter(|b| b.contains("\"json_schema\""))
            .collect();
        if blocks.len() != 1 {
            return Err(format!(
                "expected exactly one json_schema block in the rendered prompt, found {}",
                blocks.len()
            ));
        }
        let v: Json = serde_json::from_str(&blocks[0])
            .map_err(|e| format!("the manifest json_schema block is not valid JSON ({e})"))?;
        if v.get("type").and_then(|t| t.as_str()) != Some("json_schema") {
            return Err(
                "the manifest schema block is not a {\"type\": \"json_schema\"} response_format"
                    .into(),
            );
        }
        let js = v
            .get("json_schema")
            .ok_or_else(|| "the manifest schema block has no json_schema".to_string())?;
        if js.get("strict") != Some(&Json::Bool(true)) {
            return Err("the manifest json_schema is not \"strict\": true".into());
        }
        if js.get("name").and_then(|n| n.as_str()) != Some(name) {
            return Err(format!("the manifest json_schema is not named {name:?}"));
        }
        strict(
            js.get("schema")
                .ok_or_else(|| "the manifest json_schema has no schema".to_string())?,
            "schema",
        )
    }

    fn need<'a>(spec: &'a Spec, id: &str) -> Result<&'a Output, String> {
        spec.output(id)
            .ok_or_else(|| format!("output {id:?} vanished"))
    }

    /// Joins the template and the SSOT. Deterministic: SSOT order in, the same
    /// bytes out, with no clock, host or environment read.
    pub fn render(template: &str, spec: &Spec) -> Result<String, String> {
        let canon = spec.canonical();
        let self_url = fill(
            &spec.self_url,
            &[
                ("raw_base", &canon.raw_base),
                ("branch", &canon.branch),
                ("root_file", &spec.task.root_file),
            ],
        )?;

        let mut head = String::from(
            "| Repository | `git ls-remote` | REST API (read field `sha`) |\n|---|---|---|\n",
        );
        for r in &spec.repos {
            let ls = fill(
                &spec.head_ls_remote,
                &[("git_url", &r.git_url), ("branch", &r.branch)],
            )?;
            let api = fill(
                &spec.head_api,
                &[("api_base", &r.api_base), ("branch", &r.branch)],
            )?;
            head.push_str(&format!("| {} | `{ls}` | `{api}` |\n", cell(&r.name)));
        }
        let head = head.trim_end().to_string();

        let tokens: Vec<String> = spec
            .repos
            .iter()
            .map(|r| format!("`{}`", sha_token(&r.name)))
            .collect();

        let mut subs = String::new();
        for (n, s) in spec.subs.iter().enumerate() {
            let repo = spec
                .repos
                .iter()
                .find(|r| r.name == s.repo)
                .ok_or_else(|| format!("sub-instruction repo {:?} vanished", s.repo))?;
            let url = fill(
                &spec.raw_file,
                &[
                    ("raw_base", &repo.raw_base),
                    ("sha", &sha_token(&repo.name)),
                    ("path", &s.path),
                ],
            )?;
            subs.push_str(&format!(
                "{}. **`{}`** ({}) -- {}\n   `{url}`\n",
                n + 1,
                s.path,
                s.repo,
                s.purpose
            ));
        }
        let subs = subs.trim_end().to_string();

        let mut vtable = String::from("| Verdict | When |\n|---|---|\n");
        for v in &spec.verdicts {
            vtable.push_str(&format!("| `{}` | {} |\n", v.word, cell(&v.meaning)));
        }
        let vtable = vtable.trim_end().to_string();

        let mut otable = String::from("| File | Format | Version |\n|---|---|---|\n");
        for o in &spec.outputs {
            otable.push_str(&format!(
                "| `{}` | {} | `{}` |\n",
                o.file,
                cell(&o.describe),
                o.version
            ));
        }
        let otable = otable.trim_end().to_string();

        let (sft, dpo, oci, man) = (
            need(spec, "sft")?,
            need(spec, "dpo")?,
            need(spec, "oci")?,
            need(spec, "manifest")?,
        );
        let schema_name = man.schema_name.clone().unwrap_or_default();

        let words: Vec<&str> = spec.verdicts.iter().map(|v| v.word.as_str()).collect();
        let repos: Vec<&str> = spec.repos.iter().map(|r| r.name.as_str()).collect();

        let pairs: Vec<(&str, String)> = vec![
            ("ap_scheduler_item", spec.scheduler_item.clone()),
            ("ap_scheduler", spec.scheduler.clone()),
            ("ap_cadence", spec.task.cadence.clone()),
            ("ap_task_title", spec.task.title.clone()),
            ("ap_task_id", spec.task.id.clone()),
            ("ap_consumer", spec.consumer.clone()),
            ("ap_self_url", self_url),
            ("ap_submitted", spec.verdict("submitted").to_string()),
            ("ap_rejected", spec.verdict("rejected").to_string()),
            ("ap_blocked", spec.verdict("blocked").to_string()),
            ("ap_verdict_prefix", spec.verdict_prefix.clone()),
            ("ap_verdict_words", words.join(" | ")),
            ("ap_verdict_table", vtable),
            ("ap_verdict_enum", quoted(&words)?),
            ("ap_head_table", head),
            ("ap_sha_tokens", tokens.join(", ")),
            ("ap_repo_enum", quoted(&repos)?),
            ("ap_sub_instructions", subs),
            ("ap_bundle", spec.bundle.clone()),
            ("ap_outputs_table", otable),
            ("ap_split_rule", spec.split_rule.clone()),
            ("ap_file_sft", sft.file.clone()),
            ("ap_file_dpo", dpo.file.clone()),
            ("ap_file_oci", oci.file.clone()),
            ("ap_file_manifest", man.file.clone()),
            ("ap_oci_layout_version", oci.version.clone()),
            ("ap_oci_layer_root", spec.oci_layer_root.clone()),
            (
                "ap_dataset_format_enum",
                quoted(&[sft.format.as_str(), dpo.format.as_str()])?,
            ),
            ("ap_manifest_schema_name", schema_name.clone()),
            ("ap_manifest_schema_version", man.version.clone()),
        ];

        let mut out = template.to_string();
        for (k, v) in &pairs {
            out = out.replace(&format!("{{{{{k}}}}}"), v);
        }
        if let Some(i) = out.find("{{") {
            let near: String = out[i..].chars().take(48).collect();
            return Err(format!(
                "the template carries a placeholder the SSOT does not fill: {near:?}"
            ));
        }
        if let Some(hex) = find_hex40(&out) {
            return Err(format!(
                "the rendered prompt carries a 40+ hex run ({}...): the file must name no \
                 revision -- the agent resolves each HEAD live",
                &hex[..12]
            ));
        }
        check_manifest_schema(&out, &schema_name)?;
        if !out.ends_with('\n') {
            out.push('\n');
        }
        Ok(out)
    }

    /// Every sub-instruction must be a tracked, present file of the canonical
    /// tree, or the daily agent fetches a 404 and the whole run goes BLOCKED.
    pub fn verify_tracked(root: &Path, spec: &Spec) -> Result<(), String> {
        let out = Command::new("git")
            .arg("-C")
            .arg(root)
            .args(["ls-files", "-z"])
            .output()
            .map_err(|e| {
                format!("git could not run ({e}) -- sub-instruction paths are unverified")
            })?;
        if !out.status.success() {
            return Err(format!(
                "git ls-files failed in {} -- sub-instruction paths are unverified",
                root.display()
            ));
        }
        let listed: BTreeSet<String> = String::from_utf8_lossy(&out.stdout)
            .split('\0')
            .filter(|s| !s.is_empty())
            .map(str::to_string)
            .collect();
        if listed.is_empty() {
            return Err(
                "git ls-files listed no tracked file -- sub-instruction paths are unverified"
                    .into(),
            );
        }
        let missing: Vec<&str> = spec
            .subs
            .iter()
            .filter(|s| !listed.contains(&s.path) || !root.join(&s.path).is_file())
            .map(|s| s.path.as_str())
            .collect();
        if !missing.is_empty() {
            return Err(format!(
                "sub-instruction path(s) not tracked in {}: {}",
                spec.canonical().name,
                missing.join(", ")
            ));
        }
        Ok(())
    }

    /// Reads the SSOT and the template under `root`, verifies, renders.
    pub fn generate(root: &Path) -> Result<(Spec, String), String> {
        let ssot = std::fs::read_to_string(root.join(SSOT))
            .map_err(|e| format!("{SSOT} could not be read ({e}) -- nothing was projected"))?;
        let spec = load_spec(&ssot)?;
        verify_tracked(root, &spec)?;
        let tpath = format!("{TEMPLATES}/{}", spec.template);
        let template = std::fs::read_to_string(root.join(&tpath))
            .map_err(|e| format!("{tpath} could not be read ({e}) -- nothing was projected"))?;
        let out = render(&template, &spec)?;
        Ok((spec, out))
    }

    /// None when equal; otherwise the first differing line, for the gate log.
    pub fn first_difference(have: &str, want: &str) -> Option<String> {
        if have == want {
            return None;
        }
        let (h, w): (Vec<&str>, Vec<&str>) = (have.lines().collect(), want.lines().collect());
        for i in 0..h.len().max(w.len()) {
            let (a, b) = (h.get(i).copied(), w.get(i).copied());
            if a != b {
                return Some(format!(
                    "line {}: committed {:?}, generated {:?}",
                    i + 1,
                    a.unwrap_or("<end of file>"),
                    b.unwrap_or("<end of file>")
                ));
            }
        }
        Some("the files differ only in a trailing newline".into())
    }

    fn find_root() -> Option<PathBuf> {
        let mut dir = std::env::current_dir().ok()?;
        loop {
            if dir.join(SSOT).is_file() {
                return Some(dir);
            }
            if !dir.pop() {
                return None;
            }
        }
    }

    fn die(msg: &str) -> i32 {
        eprintln!("xtask artifact-prompt: {msg}");
        2
    }

    /// 0 projected / matches; 1 the committed file drifted; 2 could not run.
    pub fn run(args: &[String]) -> i32 {
        let mut root: Option<PathBuf> = None;
        let mut check = false;
        let mut it = args.iter();
        while let Some(a) = it.next() {
            match a.as_str() {
                "--root" => match it.next() {
                    Some(v) => root = Some(PathBuf::from(v)),
                    None => return die("--root needs a directory"),
                },
                "--check" => check = true,
                "-h" | "--help" => {
                    print!("{USAGE}");
                    return 0;
                }
                other => return die(&format!("unknown argument {other:?}\n{USAGE}")),
            }
        }
        let root = match root.or_else(find_root) {
            Some(r) => r,
            None => {
                return die(&format!(
                    "no {SSOT} above the current directory -- pass --root"
                ))
            }
        };
        let (spec, want) = match generate(&root) {
            Ok(v) => v,
            Err(e) => return die(&e),
        };
        let out = root.join(&spec.fixed_name);
        if check {
            let have = match std::fs::read_to_string(&out) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!(
                        "xtask artifact-prompt: {} is missing or unreadable ({e}) -- the daily \
                         task would fetch a 404; regenerate it",
                        spec.fixed_name
                    );
                    return 1;
                }
            };
            return match first_difference(&have, &want) {
                None => {
                    println!(
                        "xtask artifact-prompt: OK: {} matches [artifacts.daily] ({} repos, {} \
                         sub-instructions)",
                        spec.fixed_name,
                        spec.repos.len(),
                        spec.subs.len()
                    );
                    0
                }
                Some(d) => {
                    eprintln!(
                        "xtask artifact-prompt: {} differs from its projection -- it was \
                         hand-edited, or the SSOT/template moved and it was not regenerated \
                         ({d})",
                        spec.fixed_name
                    );
                    1
                }
            };
        }
        if let Err(e) = std::fs::write(&out, &want) {
            return die(&format!("{} could not be written ({e})", spec.fixed_name));
        }
        println!(
            "xtask artifact-prompt: projected {} ({} repos, {} sub-instructions)",
            spec.fixed_name,
            spec.repos.len(),
            spec.subs.len()
        );
        0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_task() {
        assert_eq!(parse_task(&[]), "help");
        assert_eq!(
            parse_task(&["build-resolver".to_string()]),
            "build-resolver"
        );
        assert_eq!(parse_task(&["regen".to_string()]), "regen");
        assert_eq!(
            parse_task(&["artifact-prompt".to_string()]),
            "artifact-prompt"
        );
        assert_eq!(parse_task(&["unknown".to_string()]), "unknown");
    }
}

#[cfg(test)]
// Fixture setup panics on failure by design; the module-level bans exist to
// keep the production paths from doing that.
#[allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
mod artifact_prompt_tests {
    use super::artifact_prompt::*;
    use std::collections::BTreeSet;
    use std::path::PathBuf;

    fn repo_root() -> PathBuf {
        let mut d = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        while !d.join(SSOT).is_file() {
            assert!(d.pop(), "no {SSOT} above the xtask crate");
        }
        d
    }

    fn real_ssot() -> String {
        std::fs::read_to_string(repo_root().join(SSOT)).expect("read SSOT")
    }

    fn real_template(spec: &Spec) -> String {
        std::fs::read_to_string(repo_root().join(TEMPLATES).join(&spec.template))
            .expect("read template")
    }

    fn real() -> (Spec, String) {
        let spec = load_spec(&real_ssot()).expect("the committed SSOT must load");
        let out = render(&real_template(&spec), &spec).expect("the committed SSOT must render");
        (spec, out)
    }

    /// Re-serialises the real SSOT after `edit`, so a mutation test exercises
    /// the same table the gate reads rather than a hand-kept copy of it.
    fn mutated(edit: impl FnOnce(&mut toml::value::Table)) -> String {
        let mut doc: toml::Value = toml::from_str(&real_ssot()).expect("parse");
        let daily = doc
            .get_mut("artifacts")
            .and_then(|a| a.get_mut("daily"))
            .and_then(|d| d.as_table_mut())
            .expect("[artifacts.daily]");
        edit(daily);
        toml::to_string(&doc).expect("serialise")
    }

    #[test]
    fn output_is_deterministic() {
        let (spec, a) = real();
        let b = render(&real_template(&spec), &spec).unwrap();
        assert_eq!(a, b);
        let again = load_spec(&real_ssot()).unwrap();
        assert_eq!(a, render(&real_template(&again), &again).unwrap());
    }

    #[test]
    fn an_ssot_change_changes_the_output() {
        let (spec, before) = real();
        let text = mutated(|d| {
            d.insert(
                "task_consumer".into(),
                toml::Value::String("Probe Agent Nine".into()),
            );
        });
        let moved = load_spec(&text).unwrap();
        let after = render(&real_template(&spec), &moved).unwrap();
        assert_ne!(before, after);
        assert!(after.contains("Probe Agent Nine"));
        assert!(!after.contains(&spec.consumer));
    }

    #[test]
    fn every_sub_instruction_path_is_tracked() {
        let root = repo_root();
        let (spec, _) = real();
        verify_tracked(&root, &spec).expect("every sub-instruction must be tracked");
        let out = std::process::Command::new("git")
            .arg("-C")
            .arg(&root)
            .args(["ls-files", "-z"])
            .output()
            .expect("git must run: an unverified path is not a pass");
        assert!(out.status.success());
        let listed: BTreeSet<String> = String::from_utf8_lossy(&out.stdout)
            .split('\0')
            .map(str::to_string)
            .collect();
        for s in &spec.subs {
            assert!(listed.contains(&s.path), "{} is not tracked", s.path);
        }
    }

    #[test]
    fn an_untracked_sub_instruction_is_refused() {
        let root = repo_root();
        let (mut spec, _) = real();
        spec.subs[0].path = "docs/no-such-file-for-the-daily-agent.md".into();
        let e = verify_tracked(&root, &spec).unwrap_err();
        assert!(e.contains("no-such-file"), "{e}");
    }

    #[test]
    fn the_output_carries_no_commit_id() {
        let (_, out) = real();
        assert_eq!(None, find_hex40(&out));
        assert!(find_hex40(&format!("x {} y", "a".repeat(40))).is_some());
        assert!(find_hex40(&format!("x {} y", "a".repeat(39))).is_none());
    }

    #[test]
    fn a_commit_id_in_the_ssot_is_refused() {
        let text = mutated(|d| {
            d.insert(
                "split_rule".into(),
                toml::Value::String(format!("pinned to {}", "0123456789abcdef".repeat(3))),
            );
        });
        let spec = load_spec(&text).unwrap();
        let e = render(&real_template(&spec), &spec).unwrap_err();
        assert!(e.contains("hex run"), "{e}");
    }

    #[test]
    fn accepted_is_never_offered_to_the_generator() {
        let (spec, out) = real();
        assert!(spec
            .verdicts
            .iter()
            .all(|v| !v.word.eq_ignore_ascii_case(VALIDATOR_VERDICT)));
        // The committed verdict line and the manifest enum never offer it.
        for line in out.lines() {
            if line.starts_with(&spec.verdict_prefix) || line.contains("\"enum\"") {
                assert!(!line.contains(VALIDATOR_VERDICT), "{line}");
            }
        }
        for word in ["ACCEPTED", "accepted", "Accepted"] {
            let text = mutated(|d| {
                let vs = d
                    .get_mut("verdicts")
                    .and_then(|v| v.as_array_mut())
                    .unwrap();
                vs[0]
                    .as_table_mut()
                    .unwrap()
                    .insert("word".into(), toml::Value::String(word.into()));
            });
            let e = load_spec(&text).unwrap_err();
            assert!(e.contains("ingest validator"), "{e}");
        }
    }

    #[test]
    fn a_fourth_verdict_is_refused() {
        let text = mutated(|d| {
            let vs = d
                .get_mut("verdicts")
                .and_then(|v| v.as_array_mut())
                .unwrap();
            let mut extra = vs[0].clone();
            let t = extra.as_table_mut().unwrap();
            t.insert("role".into(), toml::Value::String("deferred".into()));
            t.insert("word".into(), toml::Value::String("DEFERRED".into()));
            vs.push(extra);
        });
        assert!(load_spec(&text).is_err());
    }

    #[test]
    fn openai_dpo_keys_present_and_trl_keys_absent() {
        let (_, out) = real();
        for k in [
            "\"input\"",
            "\"preferred_output\"",
            "\"non_preferred_output\"",
            "\"messages\"",
        ] {
            assert!(out.contains(k), "missing OpenAI key {k}");
        }
        for k in ["\"prompt\"", "\"chosen\"", "\"rejected\""] {
            assert!(!out.contains(k), "TRL key {k} present");
        }
        // The exemplar lines themselves parse and carry exactly the OpenAI keys.
        let lines: Vec<serde_json::Value> = json_blocks(&out)
            .iter()
            .filter(|b| b.lines().count() == 1)
            .map(|b| serde_json::from_str(b.trim()).expect("exemplar line is JSON"))
            .collect();
        let keysets: Vec<BTreeSet<String>> = lines
            .iter()
            .map(|v| v.as_object().unwrap().keys().cloned().collect())
            .collect();
        let sft: BTreeSet<String> = ["messages"].iter().map(|s| s.to_string()).collect();
        let dpo: BTreeSet<String> = ["input", "preferred_output", "non_preferred_output"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        assert!(keysets.contains(&sft), "{keysets:?}");
        assert!(keysets.contains(&dpo), "{keysets:?}");
    }

    #[test]
    fn the_manifest_schema_is_openai_strict() {
        let (spec, out) = real();
        let name = spec
            .output("manifest")
            .and_then(|o| o.schema_name.clone())
            .unwrap();
        check_manifest_schema(&out, &name).unwrap();
        let loose = out.replacen(
            "\"additionalProperties\": false",
            "\"additionalProperties\": true",
            1,
        );
        assert!(check_manifest_schema(&loose, &name).is_err());
    }

    #[test]
    fn sub_instruction_urls_pin_a_revision_and_never_a_branch_or_blob() {
        let (spec, out) = real();
        for s in &spec.subs {
            let line = out
                .lines()
                .find(|l| l.trim_start().starts_with('`') && l.contains(&format!("/{}`", s.path)))
                .unwrap_or_else(|| panic!("no URL line for {}", s.path));
            assert!(line.contains(&format!("<{}_SHA>", s.repo)), "{line}");
            assert!(!line.contains("/blob/"), "{line}");
            let repo = spec.repos.iter().find(|r| r.name == s.repo).unwrap();
            assert!(!line.contains(&format!("/{}/", repo.branch)), "{line}");
        }
    }

    #[test]
    fn the_task_text_fetches_the_root_file_from_the_canonical_default_branch() {
        let (spec, out) = real();
        let c = spec.canonical();
        let url = format!("{}/{}/{}", c.raw_base, c.branch, spec.fixed_name);
        let block = out
            .split("```text")
            .nth(1)
            .and_then(|b| b.split("```").next())
            .unwrap();
        assert!(block.contains(&url), "{block}");
        assert!(
            block.contains(&format!("{}:", spec.verdict("blocked"))),
            "{block}"
        );
    }

    #[test]
    fn root_file_must_equal_the_template_fixed_name() {
        let text = mutated(|d| {
            let ts = d.get_mut("tasks").and_then(|v| v.as_array_mut()).unwrap();
            ts[0]
                .as_table_mut()
                .unwrap()
                .insert("root_file".into(), toml::Value::String("OTHER.md".into()));
        });
        let e = load_spec(&text).unwrap_err();
        assert!(e.contains("fixed_name"), "{e}");
    }

    #[test]
    fn a_sub_instruction_outside_the_canonical_tree_is_refused() {
        let text = mutated(|d| {
            let ss = d
                .get_mut("sub_instructions")
                .and_then(|v| v.as_array_mut())
                .unwrap();
            let repos = ["mios-bootstrap"];
            ss[0]
                .as_table_mut()
                .unwrap()
                .insert("repo".into(), toml::Value::String(repos[0].into()));
        });
        let e = load_spec(&text).unwrap_err();
        assert!(e.contains("verified"), "{e}");
    }

    #[test]
    fn an_unfilled_placeholder_is_refused() {
        let (spec, _) = real();
        let tpl = format!("{}\n{{{{ap_not_a_key}}}}\n", real_template(&spec));
        let e = render(&tpl, &spec).unwrap_err();
        assert!(e.contains("placeholder"), "{e}");
    }

    #[test]
    fn an_unknown_format_field_is_refused() {
        assert!(fill("{raw_base}/{shaa}", &[("raw_base", "x")]).is_err());
        assert_eq!(fill("{raw_base}/p", &[("raw_base", "x")]).unwrap(), "x/p");
    }

    #[test]
    fn a_hand_edit_is_reported_with_its_line() {
        let (_, out) = real();
        assert_eq!(None, first_difference(&out, &out));
        let edited = out.replacen("## Mandate", "## Mandate (edited)", 1);
        let d = first_difference(&edited, &out).unwrap();
        assert!(d.contains("Mandate"), "{d}");
    }

    /// `(owned, net)` from the table's "Tracked-file cost, net +<net>: ... owns
    /// <owned> tracked files" comment, searched between `[artifacts.daily]` and
    /// its first `[[artifacts.daily.*]]` entry. None when it is not recorded.
    fn declared_tracked_cost(ssot: &str) -> Option<(usize, usize)> {
        let start = ssot.find("\n[artifacts.daily]\n")?;
        let end = start + ssot[start..].find("\n[[artifacts.daily.")?;
        let line = ssot[start..end]
            .lines()
            .find(|l| l.starts_with('#') && l.contains("Tracked-file cost"))?;
        let num_after = |tag: &str| -> Option<usize> {
            let rest = &line[line.find(tag)? + tag.len()..];
            let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
            digits.parse().ok()
        };
        Some((num_after("owns ")?, num_after("net +")?))
    }

    /// The tracked_files ratchet only comes down, and this projection raises
    /// the count by one (output + template, less the pointer it retired). The
    /// cost is recorded beside its SSOT table, and the record is held to the
    /// tree: every file it claims is tracked, and stripping it is caught.
    #[test]
    fn the_tracked_file_cost_is_declared_and_true() {
        let root = repo_root();
        let (spec, _) = real();
        let ssot = real_ssot();
        let (owned, net) = declared_tracked_cost(&ssot).expect(
            "[artifacts.daily] must record its tracked-file cost: \
             \"# Tracked-file cost, net +<n>: ... owns <m> tracked files\"",
        );
        let template = format!("{TEMPLATES}/{}", spec.template);
        let out = std::process::Command::new("git")
            .arg("-C")
            .arg(&root)
            .args(["ls-files", "-z", "--"])
            .arg(&spec.fixed_name)
            .arg(&template)
            .output()
            .expect("git must run: an unverified claim is not a pass");
        assert!(out.status.success());
        let tracked = String::from_utf8_lossy(&out.stdout)
            .split('\0')
            .filter(|s| !s.is_empty())
            .count();
        assert_eq!(
            tracked, 2,
            "{} and {template} must both be tracked",
            spec.fixed_name
        );
        assert_eq!(
            owned, tracked,
            "the recorded owned-file count is not the tracked count"
        );
        assert_eq!(
            net + 1,
            owned,
            "net must be owned less the one retired pointer file"
        );
        let stripped: Vec<&str> = ssot
            .lines()
            .filter(|l| !l.contains("Tracked-file cost"))
            .collect();
        assert_eq!(None, declared_tracked_cost(&stripped.join("\n")));
    }

    #[test]
    fn the_committed_file_is_the_projection() {
        let root = repo_root();
        let (spec, want) = generate(&root).unwrap();
        let have = std::fs::read_to_string(root.join(&spec.fixed_name))
            .expect("the generated file must be committed at the repo root");
        assert_eq!(None, first_difference(&have, &want));
    }
}
