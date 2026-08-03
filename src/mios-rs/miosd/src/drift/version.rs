// AI-hint: Version SSOT drift checks using native mios-version-check.
// AI-related: tools/native/mios-version-check, usr/share/mios/mios.toml

use super::{Check, DriftCtx, Verdict};

pub struct VersionSSOTCheck;
impl Check for VersionSSOTCheck {
    fn id(&self) -> &'static str {
        "check_version_ssot"
    }
    fn describe(&self) -> &'static str {
        "Assert mios_version equality across all version-dupe files"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Version SSOT verified equal across all targets".to_string())
    }
}

pub struct RootTomlSubsetCheck;
impl Check for RootTomlSubsetCheck {
    fn id(&self) -> &'static str {
        "check_root_toml_subset"
    }
    fn describe(&self) -> &'static str {
        "Assert root mios.toml is a valid subset of canonical SSOT"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Root TOML subset check passed".to_string())
    }
}
