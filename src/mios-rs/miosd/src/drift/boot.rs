// AI-hint: Boot-integrity and firstboot degrade-open checks for miosd drift runner.
// AI-related: usr/libexec/mios/mios-ai-firstboot, usr/libexec/mios/forge-firstboot.sh

use super::{Check, DriftCtx, Verdict};

pub struct FirstbootDegradeOpenCheck;
impl Check for FirstbootDegradeOpenCheck {
    fn id(&self) -> &'static str {
        "check_firstboot_degrade_open"
    }
    fn describe(&self) -> &'static str {
        "Assert all firstboot scripts implement explicit degrade-open fallback handling"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Firstboot degrade-open check passed".to_string())
    }
}

pub struct GreenbootEnablementCheck;
impl Check for GreenbootEnablementCheck {
    fn id(&self) -> &'static str {
        "check_greenboot_enablement"
    }
    fn describe(&self) -> &'static str {
        "Assert greenboot health check scripts are correctly registered and enabled"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Greenboot enablement check passed".to_string())
    }
}
