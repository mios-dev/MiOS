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

        // T-1045. This used to test whether a DEBUG BUILD of the generator
        // existed and, if so, return Pass("Names registry projection matches
        // SSOT") -- without running it and without comparing anything. If the
        // binary was absent it skipped instead, so on an ordinary tree the
        // check was silent and on a developer's tree it lied. Both halves of
        // Skip-as-Pass in one function.
        //
        // The projection is produced by tools/generate-names-registry.py, the
        // same generator sync-generated.sh runs, so regenerate and diff it the
        // way every other projection check already does.
        // The generator has no --check mode and the tooling-Python ratchet has
        // no room to add one (T-1044), so compare in Rust: snapshot, render,
        // diff, restore.
        super::regen::regen_and_compare_file(
            ctx,
            "tools/generate-names-registry.py",
            "usr/share/mios/referenced_names.txt",
        )
    }
}
