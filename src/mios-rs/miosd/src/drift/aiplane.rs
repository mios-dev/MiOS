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
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        super::audit::native(ctx, "mios-aiplane-lint", &[])
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
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        super::audit::verdict((|| {
            let pattern = regex::Regex::new(r"\bMIOS_AI_(?:VLLM|SGLANG)_").map_err(|e| e.to_string())?;
            let mut errors = Vec::new();
            let mut count = 0;
            for directory in ["automation", "usr/lib/mios"] {
                for path in super::audit::files(&ctx.root, directory)? {
                    if path == "automation/98-drift-checks.sh" { continue; }
                    let bytes = std::fs::read(ctx.root.join(&path)).map_err(|e| format!("{path}: {e}"))?;
                    if bytes.contains(&0) { continue; }
                    let Ok(text) = std::str::from_utf8(&bytes) else { continue; };
                    count += 1;
                    for (line, text) in text.lines().enumerate() {
                        if pattern.is_match(text) { errors.push(format!("{path}:{}: legacy long-form inference variable", line + 1)); }
                    }
                }
            }
            super::audit::finish(count, errors, "canonical inference variable scan")
        })())
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
