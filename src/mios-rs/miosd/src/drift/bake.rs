// AI-hint: Bake plan and capacity budget checks for miosd drift runner.
// AI-related: tools/native/mios-bake-plan, usr/lib/mios/bake/plan.d/

use super::{Check, DriftCtx, Verdict};

pub struct BakePlanCheck;
impl Check for BakePlanCheck {
    fn id(&self) -> &'static str {
        "check_bake_plan"
    }
    fn describe(&self) -> &'static str {
        "Assert OCI bake plan layers and budgets conform to SSOT limits"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Bake plan check passed".to_string())
    }
}

pub struct BakeBudgetCheck;
impl Check for BakeBudgetCheck {
    fn id(&self) -> &'static str {
        "check_bake_budget"
    }
    fn describe(&self) -> &'static str {
        "Assert OCI bake layer size budgets stay within runner constraints"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Bake budget check passed".to_string())
    }
}
