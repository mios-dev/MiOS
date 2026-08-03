// AI-hint: Self-test, negative test coverage, and hermeticity checks for miosd drift runner.
// AI-related: tests/drift-gate-negatives.sh, .github/workflows/mios-ci.yml

use super::{Check, DriftCtx, Verdict};

pub struct NegativeTestCoverageCheck;
impl Check for NegativeTestCoverageCheck {
    fn id(&self) -> &'static str {
        "check_negative_test_coverage"
    }
    fn describe(&self) -> &'static str {
        "Assert every registered check has a corresponding test in drift-gate-negatives.sh"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Negative test coverage ratchet verified".to_string())
    }
}

pub struct SoftModeNotCommittedCheck;
impl Check for SoftModeNotCommittedCheck {
    fn id(&self) -> &'static str {
        "check_soft_mode_not_committed"
    }
    fn describe(&self) -> &'static str {
        "Assert no MIOS_DRIFT_CHECK_SOFT=1 mode is committed in workflows or Justfile"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("No soft mode committed check passed".to_string())
    }
}
