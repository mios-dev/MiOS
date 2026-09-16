// AI-hint: Pipeline, gate numbering, and DAG integrity checks for miosd drift runner.
// AI-related: automation/98-drift-checks.sh, ROADMAP.md

use super::{Check, DriftCtx, Verdict};

pub struct PipelineNumberingCheck;
impl Check for PipelineNumberingCheck {
    fn id(&self) -> &'static str {
        "check_pipeline_numbering"
    }
    fn describe(&self) -> &'static str {
        "Assert dense 1..N ordinal numbering across pipeline stages and drift checks"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        if ctx.in_image {
            return Verdict::Skip(
                "Skipping pipeline numbering check in OCI build context".to_string(),
            );
        }
        // T-1043. This used to read ctx.in_image for the early skip above and
        // then return a constant Pass -- "ordinals verified dense" about a tree
        // it never opened. Naming the parameter `ctx` was the only thing that
        // made it look implemented. Ported from the bash twin's three assertions.
        let mut bad: Vec<String> = Vec::new();

        let gate = ctx.root.join("automation/98-drift-checks.sh");
        match std::fs::read_to_string(&gate) {
            Ok(text) => {
                // A hand-written "[98-drift-checks] (7)" label competes with the
                // SSOT ordinal in drift-gate-index.tsv for being the check number.
                let n = text
                    .lines()
                    .filter(|l| {
                        let Some(i) = l.find("[98-drift-checks]") else {
                            return false;
                        };
                        let rest = l[i + "[98-drift-checks]".len()..].trim_start();
                        rest.starts_with('(')
                            && rest[1..]
                                .split(')')
                                .next()
                                .map(|d| !d.is_empty() && d.chars().all(|c| c.is_ascii_digit()))
                                .unwrap_or(false)
                    })
                    .count();
                if n > 0 {
                    bad.push(format!(
                        "{n} hand-written check label(s) reintroduced in 98-drift-checks.sh"
                    ));
                }
            }
            Err(e) => bad.push(format!("automation/98-drift-checks.sh unreadable: {e}")),
        }

        let build = ctx.root.join("automation/build.sh");
        match std::fs::read_to_string(&build) {
            Ok(text) => {
                if text.contains("Step count in chain: $(ls") && text.contains("wc -l") {
                    bad.push(
                        "build.sh re-counts the chain via ls|wc -l instead of $SCRIPT_COUNT"
                            .to_string(),
                    );
                }
            }
            Err(e) => bad.push(format!("automation/build.sh unreadable: {e}")),
        }

        // The bash twin skips this when the index is absent, which is an
        // Empty-Set Pass. A missing SSOT projection is exactly what this suite
        // exists to catch, so here it fails.
        let idx = ctx
            .root
            .join("usr/share/mios/reference/drift-gate-index.tsv");
        match std::fs::read_to_string(&idx) {
            Ok(text) => {
                let mut n = 0u32;
                let mut gap: Option<String> = None;
                for line in text.lines().skip(1) {
                    let Some(first) = line.split('\t').next() else {
                        continue;
                    };
                    if first.is_empty() || !first.chars().all(|c| c.is_ascii_digit()) {
                        continue;
                    }
                    n += 1;
                    if first.parse::<u32>().ok() != Some(n) {
                        gap = Some(first.to_string());
                        break;
                    }
                }
                if n == 0 {
                    bad.push("drift-gate-index.tsv carries no ordinals".to_string());
                } else if let Some(g) = gap {
                    bad.push(format!(
                        "drift-gate-index.tsv ordinals not dense 1..N at {g}"
                    ));
                }
            }
            Err(e) => bad.push(format!(
                "usr/share/mios/reference/drift-gate-index.tsv unreadable: {e}"
            )),
        }

        if bad.is_empty() {
            Verdict::Pass("Pipeline numbering and ordinals verified dense".to_string())
        } else {
            Verdict::Fail(bad.join("; "))
        }
    }
}

pub struct DAGIntegrityCheck;
impl Check for DAGIntegrityCheck {
    fn id(&self) -> &'static str {
        "check_dag_integrity"
    }
    fn describe(&self) -> &'static str {
        "Assert task dependency DAG contains no cycles or dangling dependencies"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: DAG integrity verified acyclic".to_string())
    }
}

pub struct RoadmapIndexCheck;
impl Check for RoadmapIndexCheck {
    fn id(&self) -> &'static str {
        "check_roadmap_index"
    }
    fn describe(&self) -> &'static str {
        "Assert ROADMAP.md task index matches AGY-TASKS.md SSOT"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Roadmap index".to_string())
    }
}
