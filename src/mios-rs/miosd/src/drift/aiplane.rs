// AI-hint: AI-plane lint, hint coverage, and manifest integrity checks for miosd drift runner.
// AI-related: tools/native/mios-aiplane-lint, usr/lib/mios/agent-pipe/, usr/share/mios/ai/v1/

use super::{Check, DriftCtx, Verdict};

pub struct AgentPipeBudgetsCheck;
impl Check for AgentPipeBudgetsCheck {
    fn id(&self) -> &'static str {
        "check_agent_pipe_budgets"
    }
    fn describe(&self) -> &'static str {
        "Assert agent pipe context token budgets are within bounds"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Agent pipe budgets".to_string())
    }
}

pub struct VLLMNameCanonicalCheck;
impl Check for VLLMNameCanonicalCheck {
    fn id(&self) -> &'static str {
        "check_vllm_name_canonical"
    }
    fn describe(&self) -> &'static str {
        "Assert canonical MIOS_AI_VLLM_* environment variable naming"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: vLLM canonical name".to_string())
    }
}

pub struct HintCoverageCheck;
impl Check for HintCoverageCheck {
    fn id(&self) -> &'static str {
        "check_hint_coverage"
    }
    fn describe(&self) -> &'static str {
        "Assert AI-hint comment header coverage meets ratchet baseline"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: AI hint coverage".to_string())
    }
}

pub struct StructuredAIManifestCheck;
impl Check for StructuredAIManifestCheck {
    fn id(&self) -> &'static str {
        "check_structured"
    }
    fn describe(&self) -> &'static str {
        "Assert structured AI manifest reference integrity"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Structured AI manifest".to_string())
    }
}

pub struct CapabilityManifestCheck;
impl Check for CapabilityManifestCheck {
    fn id(&self) -> &'static str {
        "check_capability_manifest"
    }
    fn describe(&self) -> &'static str {
        "Assert capability manifest matches SSOT definitions"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Capability manifest".to_string())
    }
}
