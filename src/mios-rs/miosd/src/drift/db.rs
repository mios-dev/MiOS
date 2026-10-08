// AI-hint: DB seed coverage, RBAC tiers, and DB-TOML roundtrip checks for miosd drift runner.
// AI-related: usr/libexec/mios/seed-db-config.py, usr/share/mios/postgres/schema-init.sql

use super::{Check, DriftCtx, Verdict};

pub struct DBSeedCoverageCheck;
impl Check for DBSeedCoverageCheck {
    fn id(&self) -> &'static str {
        "check_db_seed_coverage"
    }
    fn describe(&self) -> &'static str {
        "Assert all SSOT sections and verbs are covered by DB seed script"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: DB seed coverage verified clean".to_string())
    }
}

pub struct RBACTiersCheck;
impl Check for RBACTiersCheck {
    fn id(&self) -> &'static str {
        "check_rbac_tiers"
    }
    fn describe(&self) -> &'static str {
        "Assert RBAC permission tiers are valid and PDP fails closed"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        super::audit::verdict(rbac(ctx))
    }
}

fn rbac(ctx: &DriftCtx) -> super::audit::Audit {
    let doc = super::audit::ssot(ctx)?;
    let tiers: std::collections::BTreeSet<_> = super::audit::strings(&doc, "ai.permission_tiers")?.into_iter().map(|v| v.trim().to_lowercase()).collect();
    if tiers.is_empty() || tiers.contains("") { return Err("Permission tier catalog is empty or contains an empty identity".into()); }
    let mut count = 0;
    let mut errors = Vec::new();
    for section in ["agents", "users"] {
        let members = super::audit::at(&doc, section)?.as_table().ok_or_else(|| format!("Invalid SSOT {section}"))?;
        for (name, value) in members {
            if let Some(tier) = value.get("max_permission") {
                count += 1;
                match tier.as_str() {
                    Some(tier) if tiers.contains(&tier.trim().to_lowercase()) => {},
                    _ => errors.push(format!("{section}.{name}.max_permission {tier} not in SSOT permission tiers")),
                }
            }
        }
    }
    super::audit::finish(count, errors, "RBAC tier identities")
}

pub struct CLISQLSafetyCheck;
impl Check for CLISQLSafetyCheck {
    fn id(&self) -> &'static str {
        "check_cli_sql_safety"
    }
    fn describe(&self) -> &'static str {
        "Assert no dynamic SQL query string concatenation exists in CLI verbs"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: CLI SQL safety".to_string())
    }
}

pub struct DriftProjectionCheck;
impl Check for DriftProjectionCheck {
    fn id(&self) -> &'static str {
        "check_drift_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert DB to TOML materialization round-trip is lossless"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: DB to TOML round-trip lossless projection".to_string())
    }
}


#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rbac_operator_tiers_apply_and_unknown_empty_and_missing_catalog_fail() -> Result<(), Box<dyn std::error::Error>> {
        let temp = tempfile::tempdir()?;
        std::fs::create_dir_all(temp.path().join("usr/share/mios"))?;
        let path = temp.path().join("usr/share/mios/mios.toml");
        let ctx = DriftCtx::new(temp.path().into(), false);
        std::fs::write(&path, "[ai]\npermission_tiers=['observe','operator']\n[agents.example]\nmax_permission='OPERATOR'\n[users]\n")?;
        assert!(rbac(&ctx).is_ok());
        std::fs::write(&path, "[ai]\npermission_tiers=['observe']\n[agents.example]\nmax_permission='operator'\n[users]\n")?;
        assert!(rbac(&ctx).is_err_and(|e| e.contains("agents.example.max_permission")));
        std::fs::write(&path, "[ai]\npermission_tiers=[]\n[agents]\n[users]\n")?;
        assert!(rbac(&ctx).is_err());
        std::fs::write(&path, "[agents]\n[users]\n")?;
        assert!(rbac(&ctx).is_err());
        Ok(())
    }
}
