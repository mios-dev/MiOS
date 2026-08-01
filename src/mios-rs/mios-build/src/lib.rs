// AI-hint: Native build orchestrator and phase registry for MiOS.
// AI-related: automation/build.sh, automation/build-mios.sh

use serde::{Deserialize, Serialize};
use std::fmt;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Phase {
    pub ordinal: String,
    pub name: String,
    pub script: String,
    pub fatal: bool,
    pub apply_class: String,
}

impl fmt::Display for Phase {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}] {} ({}) [fatal={}]",
            self.ordinal, self.name, self.script, self.fatal
        )
    }
}

pub struct PhaseRegistry {
    phases: Vec<Phase>,
}

#[derive(Deserialize)]
struct BuildPhasesTable {
    list: Vec<Phase>,
}

#[derive(Deserialize)]
struct BuildToml {
    phases: Option<BuildPhasesTable>,
}

#[derive(Deserialize)]
struct MiosTomlRoot {
    build: Option<BuildToml>,
}

impl PhaseRegistry {
    pub fn load_from_toml(path: &std::path::Path) -> Self {
        if let Ok(content) = std::fs::read_to_string(path) {
            if let Ok(root) = toml::from_str::<MiosTomlRoot>(&content) {
                if let Some(build) = root.build {
                    if let Some(phases) = build.phases {
                        if !phases.list.is_empty() {
                            return Self {
                                phases: phases.list,
                            };
                        }
                    }
                }
            }
        }
        Self::default_registry()
    }

    pub fn default_registry() -> Self {
        let phases = vec![
            Phase {
                ordinal: "01".into(),
                name: "system-files-overlay".into(),
                script: "01-system-files-overlay.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
            Phase {
                ordinal: "02".into(),
                name: "materialize-build-ctx".into(),
                script: "02-materialize-build-ctx.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
            Phase {
                ordinal: "05".into(),
                name: "repos".into(),
                script: "05-repos.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
            Phase {
                ordinal: "07".into(),
                name: "kernel".into(),
                script: "07-kernel.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
            Phase {
                ordinal: "98".into(),
                name: "drift-checks".into(),
                script: "98-drift-checks.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
            Phase {
                ordinal: "99".into(),
                name: "postcheck".into(),
                script: "99-postcheck.sh".into(),
                fatal: true,
                apply_class: "universal".into(),
            },
        ];
        Self { phases }
    }

    pub fn phases(&self) -> &[Phase] {
        &self.phases
    }

    pub fn print_plan(&self) {
        println!("[mios-build] Execution Plan:");
        for p in &self.phases {
            println!("  {}", p);
        }
    }
}

pub fn run_build(phase: &str, plan_only: bool) -> Result<(), Box<dyn std::error::Error>> {
    let root_str = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let toml_path = std::path::Path::new(&root_str).join("usr/share/mios/mios.toml");
    let registry = PhaseRegistry::load_from_toml(&toml_path);
    if plan_only {
        registry.print_plan();
        return Ok(());
    }

    println!("[mios-build] Executing build phase: {}", phase);
    registry.print_plan();
    Ok(())
}
