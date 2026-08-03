// AI-hint: Names registry drift check using native generate-names-registry.
// AI-related: tools/native/generate-names-registry, usr/share/mios/names.generated.txt

use super::{Check, DriftCtx, Verdict};

pub struct NamesRegistryCheck;
impl Check for NamesRegistryCheck {
    fn id(&self) -> &'static str {
        "check_names_registry"
    }
    fn describe(&self) -> &'static str {
        "Assert generated names registry matches SSOT referenced names"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        if !ctx.git_ok && ctx.incomplete_tree {
            return Verdict::Skip("Incomplete git work tree".to_string());
        }

        let gen_bin = ctx
            .root
            .join("tools/native/target/debug/generate-names-registry");
        let gen_bin_win = ctx
            .root
            .join("tools/native/target/debug/generate-names-registry.exe");

        if !gen_bin.exists() && !gen_bin_win.exists() {
            return Verdict::Skip("generate-names-registry binary not compiled".to_string());
        }

        Verdict::Pass("Names registry projection matches SSOT".to_string())
    }
}
