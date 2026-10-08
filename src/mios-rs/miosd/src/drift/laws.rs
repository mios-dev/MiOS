// AI-hint: Laws and filesystem layout enforcement checks for miosd drift runner.
// AI-related: automation/98-drift-checks.sh, usr/share/mios/mios.toml

use super::audit::{self, at, files, finish, ini, read, ssot, strings};
use super::{Check, DriftCtx, Verdict};
use std::collections::{HashMap, HashSet};
use std::fs;

pub struct LawEnforcersCheck;
impl Check for LawEnforcersCheck {
    fn id(&self) -> &'static str {
        "check_law_enforcers"
    }
    fn describe(&self) -> &'static str {
        "Assert all laws in mios.toml have valid enforced_by target declarations"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        // T-1043. This used to test `p.exists()` and then return
        // Pass("Law enforcers resolution validated clean") -- a claim about a
        // file it never opened. Touching ctx.root to BUILD a path is not
        // reading the tree, which is why two successive stub detectors let it
        // through. CLAUDE.md calls [laws] the canonical registry; this now
        // checks it.
        let p = ctx.root.join("usr/share/mios/mios.toml");
        let text = match fs::read_to_string(&p) {
            Ok(t) => t,
            Err(e) => return Verdict::Fail(format!("mios.toml unreadable: {}", e)),
        };
        let parsed: toml::Value = match text.parse() {
            Ok(v) => v,
            Err(e) => return Verdict::Fail(format!("mios.toml did not parse: {}", e)),
        };
        let laws = parsed
            .get("laws")
            .and_then(|l| l.get("laws"))
            .and_then(|v| v.as_array());
        // An absent or empty registry is not "no violations"; it is the law
        // list having vanished.
        let laws = match laws {
            Some(a) if !a.is_empty() => a,
            _ => return Verdict::Fail("[laws].laws is absent or empty".to_string()),
        };

        let mut bad: Vec<String> = Vec::new();
        let mut seen_slugs: HashSet<String> = HashSet::new();
        let mut file_cache: HashMap<String, Option<String>> = HashMap::new();

        for (i, law) in laws.iter().enumerate() {
            let id = law.get("id").and_then(|v| v.as_integer());
            let slug = law.get("slug").and_then(|v| v.as_str()).unwrap_or("");
            let applies = law.get("applies_to").and_then(|v| v.as_str()).unwrap_or("");
            let enforced = law
                .get("enforced_by")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let label = if slug.is_empty() {
                format!("law #{}", i + 1)
            } else {
                slug.to_string()
            };

            // Dense 1..N: a gap means a law was dropped and nobody renumbered.
            if id != Some(i as i64 + 1) {
                bad.push(format!(
                    "{}: id is {:?}, expected {} (the registry must be dense 1..N)",
                    label,
                    id,
                    i + 1
                ));
            }
            if slug.is_empty() {
                bad.push(format!("{}: no slug", label));
            } else if !seen_slugs.insert(slug.to_string()) {
                bad.push(format!("{}: duplicate slug", label));
            }
            if !matches!(applies, "bootc" | "wsl" | "both") {
                bad.push(format!(
                    "{}: applies_to is {:?}, not bootc|wsl|both",
                    label, applies
                ));
            }
            if enforced.is_empty() {
                bad.push(format!("{}: no enforced_by -- the law is advisory", label));
                continue;
            }
            // enforced_by is "<file>:<symbol>[,<symbol>...]".
            let Some((file, symbols)) = enforced.split_once(':') else {
                bad.push(format!(
                    "{}: enforced_by {:?} has no <file>:<symbol> form",
                    label, enforced
                ));
                continue;
            };
            // `process:` is a real scheme, not a malformed entry: Law 15's
            // triple-check-before-acting cannot be gated, only followed. It
            // still has to SAY something, which the emptiness test above covers.
            if file == "process" {
                continue;
            }
            let body = file_cache
                .entry(file.to_string())
                .or_insert_with(|| fs::read_to_string(ctx.root.join("automation").join(file)).ok());
            let Some(body) = body else {
                bad.push(format!(
                    "{}: enforcer file automation/{} does not exist",
                    label, file
                ));
                continue;
            };
            for sym in symbols.split(',').map(str::trim).filter(|s| !s.is_empty()) {
                if !body.contains(sym) {
                    bad.push(format!(
                        "{}: enforced_by names {} but automation/{} does not contain it",
                        label, sym, file
                    ));
                }
            }
        }

        if bad.is_empty() {
            Verdict::Pass(format!(
                "{} law(s) each resolve to an enforcer that exists",
                laws.len()
            ))
        } else {
            Verdict::Fail(bad.join("; "))
        }
    }
}

pub struct QuadletPrivilegeCheck;
impl Check for QuadletPrivilegeCheck {
    fn id(&self) -> &'static str {
        "check_quadlet_privilege"
    }
    fn describe(&self) -> &'static str {
        "Assert root quadlet privilege whitelist matches committed roster"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let policy = ssot(ctx)?;
            let root = strings(&policy, "security.privileged_quadlets.root")?;
            let exempt = strings(&policy, "security.privileged_quadlets.no_group_delegate")?;
            let mut paths = files(&ctx.root, "usr/share/containers/systemd")?;
            if ctx.root.join("etc/containers/systemd").exists() {
                paths.extend(files(&ctx.root, "etc/containers/systemd")?);
            }
            let mut errors = Vec::new();
            let mut count = 0;
            for path in paths.iter().filter(|p| p.ends_with(".container")) {
                count += 1;
                let name = path.rsplit('/').next().unwrap_or(path);
                let body = read(&ctx.root, path)?;
                let user = ini(&body, "Container", "User")
                    .or_else(|| ini(&body, "Service", "User"))
                    .unwrap_or_default();
                let is_root = matches!(user.as_str(), "" | "root" | "0");
                if is_root && !root.iter().any(|s| s == name) {
                    errors.push(format!(
                        "{path}: User={user} runs as root without a roster entry"
                    ));
                }
                if !exempt.iter().any(|s| s == name) {
                    if !is_root
                        && ini(&body, "Container", "Group")
                            .or_else(|| ini(&body, "Service", "Group"))
                            .filter(|s| !s.is_empty())
                            .is_none()
                    {
                        errors.push(format!("{path}: non-root User requires Group="));
                    }
                    if ini(&body, "Service", "Delegate").as_deref() != Some("yes") {
                        errors.push(format!("{path}: missing Delegate=yes"));
                    }
                }
            }
            finish(count, errors, "Quadlet privilege roster")
        })())
    }
}

pub struct CouncilGateSSOTCheck;
impl Check for CouncilGateSSOTCheck {
    fn id(&self) -> &'static str {
        "check_council_gate_ssot"
    }
    fn describe(&self) -> &'static str {
        "Assert council gate configuration matches SSOT"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let policy = ssot(ctx)?;
            let council = at(&policy, "agent_pipe.council")?;
            let paths = files(&ctx.root, "usr/lib/mios/agent-pipe")?;
            let mut code = String::new();
            let mut count = 0;
            for path in paths.iter().filter(|p| {
                p.ends_with(".py")
                    && !p.contains("/tests/")
                    && !p.rsplit('/').next().unwrap_or("").starts_with("test_")
            }) {
                count += 1;
                code.push_str(&read(&ctx.root, path)?);
                code.push('\n');
            }
            let errors = [
                "diversity_gate",
                "diversity_threshold",
                "aggregator_bypass",
                "aggregator_bypass_threshold",
            ]
            .iter()
            .filter(|key| council.get(**key).is_none() || !code.contains(**key))
            .map(|key| format!("agent_pipe.council.{key}: missing policy or source consumer"))
            .collect();
            finish(count, errors, "council policy consumer audit")
        })())
    }
}

pub struct UsrOverEtcCheck;
impl Check for UsrOverEtcCheck {
    fn id(&self) -> &'static str {
        "check_usr_over_etc"
    }
    fn describe(&self) -> &'static str {
        "Assert /usr defaults take precedence over /etc in vendor config"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let paths = audit::tracked(ctx)?;
            let mut errors = Vec::new();
            for path in paths.iter().filter(|p| p.starts_with("etc/")) {
                if [
                    "etc/containers/",
                    "etc/wsl.conf",
                    "etc/wsl-distribution.conf",
                    "etc/cockpit/",
                    "etc/greenboot/",
                    "etc/mios/",
                    "etc/skel/",
                    "etc/profile.d/",
                ]
                .iter()
                .any(|p| path.starts_with(p))
                    || path.contains(".d/")
                    || path.rsplit('/').next().unwrap_or("").contains(".d")
                {
                    continue;
                }
                read(&ctx.root, path)?;
                for base in ["usr/share", "usr/lib"] {
                    let vendor = format!("{base}/{}", &path[4..]);
                    if ctx.root.join(&vendor).is_file() {
                        errors.push(format!("{path} shadows {vendor}"));
                    }
                }
            }
            finish(paths.len(), errors, "tracked /etc vendor shadow audit")
        })())
    }
}

pub struct EtcDuplicatesCheck;
impl Check for EtcDuplicatesCheck {
    fn id(&self) -> &'static str {
        "check_etc_duplicates"
    }
    fn describe(&self) -> &'static str {
        "Assert no duplicate file declarations in /etc tree"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let vendor = files(&ctx.root, "usr/share/containers/systemd")?;
            let mut errors = Vec::new();
            if ctx.root.join("etc/containers/systemd").exists() {
                for path in files(&ctx.root, "etc/containers/systemd")? {
                    if ![".container", ".pod", ".network", ".volume"]
                        .iter()
                        .any(|ext| path.ends_with(ext))
                    {
                        continue;
                    }
                    let suffix = path.trim_start_matches("etc/containers/systemd/");
                    let target = format!("usr/share/containers/systemd/{suffix}");
                    if vendor.contains(&target) {
                        errors.push(format!("{path} shadows generated {target}"));
                    }
                }
            }
            finish(vendor.len(), errors, "Quadlet duplicate audit")
        })())
    }
}

pub struct NoMkdirInVarCheck;
impl Check for NoMkdirInVarCheck {
    fn id(&self) -> &'static str {
        "check_no_mkdir_in_var"
    }
    fn describe(&self) -> &'static str {
        "Assert scripts do not invoke explicit mkdir in /var"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let mut paths = files(&ctx.root, "automation")?;
            paths.retain(|p| {
                !p[11..].contains('/')
                    && p.ends_with(".sh")
                    && p.as_bytes().get(11).is_some_and(u8::is_ascii_digit)
            });
            for entry in fs::read_dir(&ctx.root).map_err(|e| e.to_string())? {
                let entry = entry.map_err(|e| e.to_string())?;
                if entry.file_type().map_err(|e| e.to_string())?.is_file()
                    && entry
                        .file_name()
                        .to_string_lossy()
                        .starts_with("Containerfile")
                {
                    paths.push(entry.file_name().to_string_lossy().into_owned());
                }
            }
            let pattern =
                regex::Regex::new(r#"\bmkdir[^;&|#]*[\s'\"]/var/"#).map_err(|e| e.to_string())?;
            let mut errors = Vec::new();
            for path in &paths {
                for (line, text) in read(&ctx.root, path)?.lines().enumerate() {
                    if !text.trim_start().starts_with('#') && pattern.is_match(text) {
                        errors.push(format!(
                            "{path}:{}: imperative /var mkdir; declare tmpfiles instead",
                            line + 1
                        ));
                    }
                }
            }
            finish(paths.len(), errors, "numbered build /var mkdir audit")
        })())
    }
}

pub struct VarClosureCheck;
impl Check for VarClosureCheck {
    fn id(&self) -> &'static str {
        "check_var_closure"
    }
    fn describe(&self) -> &'static str {
        "Assert /var directory structure closure is complete"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        audit::verdict((|| {
            let policy = ssot(ctx)?;
            let merged = mios_resolver::resolve_projection(&ctx.root).map_err(|e| e.to_string())?;
            let exports = mios_resolver::emit::build_exports_map(
                &merged,
                mios_resolver::stack_offset_of(&merged),
            );
            if exports.is_empty() {
                return Err("resolver emitted no variables".into());
            }
            let mut emitted: HashSet<String> = exports.into_keys().collect();
            let prefixes: Vec<_> = policy
                .as_table()
                .ok_or("SSOT is not a table")?
                .keys()
                .map(|key| format!("MIOS_{}_", key.to_uppercase().replace(['-', '.'], "_")))
                .collect();
            for surface in at(&policy, "laws.projection_registry.surfaces")?
                .as_array()
                .ok_or("projection surfaces must be an array")?
            {
                for path in surface
                    .get("output")
                    .and_then(toml::Value::as_str)
                    .unwrap_or("")
                    .split(',')
                    .map(str::trim)
                    .filter(|p| p.ends_with(".env"))
                {
                    if !ctx.root.join(path).is_file() {
                        continue;
                    }
                    for line in read(&ctx.root, path)?.lines() {
                        if let Some((name, _)) =
                            line.trim().trim_start_matches("export ").split_once('=')
                        {
                            if name.trim().starts_with("MIOS_") {
                                emitted.insert(name.trim().to_owned());
                            }
                        }
                    }
                }
            }
            let variable = regex::Regex::new(r"\bMIOS_[A-Z0-9_]+").map_err(|e| e.to_string())?;
            let directives = [
                "MIOS_APPLY_CLASS",
                "MIOS_SUBSTRATE",
                "MIOS_ROOT",
                "MIOS_VENDOR_TOML",
                "MIOS_HOST_TOML",
                "MIOS_USER_TOML",
                "MIOS_VENDOR_TOML_D",
                "MIOS_HOST_TOML_D",
                "MIOS_USER_TOML_D",
                "MIOS_CONFIG_DIR",
                "MIOS_TOML_ROOT",
                "MIOS_TOML",
            ];
            let emitters = [
                "usr/lib/mios/userenv.sh",
                "tools/lib/userenv.sh",
                "usr/libexec/mios/system-sync-env.sh",
                "usr/share/mios/names.generated.txt",
                "usr/share/doc/mios/reference/naming-unification.md",
                "automation/lib/globals.sh",
                "automation/lib/globals.ps1",
                "tools/render-globals.py",
                "tools/render-ports.py",
                "usr/share/mios/mios.toml",
                "Justfile",
            ];
            let mut missing = std::collections::BTreeMap::new();
            let mut count = 0;
            for path in files(&ctx.root, "")? {
                let base = path.rsplit('/').next().unwrap_or(&path);
                if path.split('/').any(|p| {
                    matches!(
                        p,
                        "tests" | ".agents" | ".claude" | ".gemini" | ".system_generated"
                    )
                }) || base.starts_with("test_")
                    || base.ends_with("_test.py")
                    || emitters.iter().any(|p| path.ends_with(p))
                {
                    continue;
                }
                if !(base == ".env.mios"
                    || [
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
                    ]
                    .iter()
                    .any(|ext| path.ends_with(ext)))
                {
                    continue;
                }
                if path.starts_with("docs/")
                    && ctx
                        .root
                        .join(&path)
                        .parent()
                        .is_some_and(|p| p.join("_design.md").is_file())
                {
                    continue;
                }
                count += 1;
                for (number, line) in read(&ctx.root, &path)?.lines().enumerate() {
                    let code = line
                        .split('#')
                        .next()
                        .unwrap_or("")
                        .split("//")
                        .next()
                        .unwrap_or("");
                    for hit in variable.find_iter(code) {
                        let name = hit.as_str();
                        if name.ends_with('_')
                            || emitted.contains(name)
                            || directives.contains(&name)
                            || prefixes.iter().any(|p| name.starts_with(p))
                            || code[hit.end()..].trim_start().starts_with('=')
                        {
                            continue;
                        }
                        missing
                            .entry(name.to_owned())
                            .or_insert_with(|| format!("{path}:{}", number + 1));
                    }
                }
            }
            let ledger = read(
                &ctx.root,
                "usr/share/mios/reference/var-closure-baseline.tsv",
            )?;
            let ceiling: usize = ledger
                .lines()
                .find_map(|s| s.strip_prefix("#!ceiling "))
                .ok_or("var closure ledger has no ceiling")?
                .split_whitespace()
                .next()
                .ok_or("empty closure ceiling")?
                .parse()
                .map_err(|_| "invalid closure ceiling")?;
            let declared: HashSet<_> = ledger
                .lines()
                .filter(|s| s.starts_with("MIOS_"))
                .map(|s| s.split('\t').next().unwrap_or(s).to_owned())
                .collect();
            let mut errors = Vec::new();
            for (name, source) in &missing {
                if !declared.contains(name) {
                    errors.push(format!(
                        "{source}: {name} referenced but not emitted or on closure ledger"
                    ));
                }
            }
            for name in &declared {
                if !missing.contains_key(name) {
                    errors.push(format!(
                        "{name}: stale closure ledger entry; remove it and lower ceiling"
                    ));
                }
            }
            if missing.len() != ceiling || declared.len() != ceiling {
                errors.push(format!(
                    "var closure exact ratchet: found {}, ledger {}, ceiling {ceiling}",
                    missing.len(),
                    declared.len()
                ));
            }
            finish(count, errors, "native resolver variable closure")
        })())
    }
}
