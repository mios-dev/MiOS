// AI-hint: Laws and filesystem layout enforcement checks for miosd drift runner.
// AI-related: automation/98-drift-checks.sh, usr/share/mios/mios.toml

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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Quadlet privilege roster".to_string())
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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Council gate SSOT".to_string())
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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: /usr precedence".to_string())
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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: No duplicate /etc definitions".to_string())
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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: No explicit mkdir in /var".to_string())
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
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Var closure".to_string())
    }
}
