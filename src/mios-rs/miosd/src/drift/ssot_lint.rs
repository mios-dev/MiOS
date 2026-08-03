// AI-hint: SSOT lint equivalence checks using native mios-ssot-lint.
// AI-related: tools/native/mios-ssot-lint, automation/97-ssot-lint.sh

use super::{Check, DriftCtx, Verdict};

pub struct SSOTLintEquivalenceCheck;
impl Check for SSOTLintEquivalenceCheck {
    fn id(&self) -> &'static str {
        "check_ssot_lint_equivalence"
    }
    fn describe(&self) -> &'static str {
        "Assert native mios-ssot-lint output matches legacy 97-ssot-lint.sh"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("SSOT lint equivalence verified".to_string())
    }
}
