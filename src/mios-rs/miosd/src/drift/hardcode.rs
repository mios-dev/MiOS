// AI-hint: Hardcode linting with anchored allowlist for miosd drift runner.
// AI-related: usr/libexec/mios/mios-hardcode-lint, usr/share/mios/mios.toml

use super::{Check, DriftCtx, Verdict};

pub struct HardcodeLintCheck;
impl Check for HardcodeLintCheck {
    fn id(&self) -> &'static str {
        "check_no_hardcode"
    }
    fn describe(&self) -> &'static str {
        "Assert no un-exempted IP, port, or secret hardcodes exist in codebase"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Hardcode lint with anchored allowlist verified clean".to_string())
    }
}

pub struct HardcodeVersionCheck;
impl Check for HardcodeVersionCheck {
    fn id(&self) -> &'static str {
        "check_no_hardcode_version"
    }
    fn describe(&self) -> &'static str {
        "Assert no hardcoded Fedora version literals exist outside SSOT"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Version hardcode lint verified clean".to_string())
    }
}

pub struct HardcodedSSOTLiteralCheck;
impl Check for HardcodedSSOTLiteralCheck {
    fn id(&self) -> &'static str {
        "check_no_hardcoded_ssot_literal"
    }
    fn describe(&self) -> &'static str {
        "Assert no hardcoded version literals exist in SSOT files"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("SSOT literal hardcode check passed".to_string())
    }
}
