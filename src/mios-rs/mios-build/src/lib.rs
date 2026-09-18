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

/// Why loading the registry returns an error instead of a phase list.
///
/// Each variant is a case that used to resolve to a six-phase hardcoded default
/// and exit 0, which made a build that ran six of seventy-one phases
/// indistinguishable from a complete one.
#[derive(Debug)]
pub enum RegistryError {
    Unreadable {
        path: String,
        source: std::io::Error,
    },
    Unparseable {
        path: String,
        detail: String,
    },
    Missing {
        path: String,
    },
    Empty {
        path: String,
    },
}

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Unreadable { path, source } => {
                write!(f, "cannot read the phase registry at {}: {}", path, source)
            }
            Self::Unparseable { path, detail } => {
                write!(f, "cannot parse {} as TOML: {}", path, detail)
            }
            Self::Missing { path } => write!(
                f,
                "{} declares no [build.phases].list -- the phase order is SSOT-owned \
                 and there is no default to fall back to",
                path
            ),
            Self::Empty { path } => write!(
                f,
                "[build.phases].list in {} is empty -- a build of zero phases is not a build",
                path
            ),
        }
    }
}

impl std::error::Error for RegistryError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Unreadable { source, .. } => Some(source),
            _ => None,
        }
    }
}

impl PhaseRegistry {
    /// Load the phase list from `[build.phases].list` in mios.toml.
    ///
    /// This used to swallow every failure and return a six-phase hardcoded
    /// registry (Law 7: NO-HARDCODE). Nothing in the tree could tell the two
    /// apart: `miosd build --list` printed six script names and exited 0, and
    /// automation/build.sh took that list verbatim. A build launched from the
    /// wrong working directory -- MIOS_ROOT defaults to "." -- would therefore
    /// run 01, 02, 05, 07, 98, 99 and report BUILD COMPLETE, having skipped the
    /// kernel config, GPU wiring, SELinux, services, the whole AI plane and
    /// finalize. The registry now refuses rather than guesses (T-1018).
    pub fn load_from_toml(path: &std::path::Path) -> Result<Self, RegistryError> {
        let shown = path.display().to_string();
        let content =
            std::fs::read_to_string(path).map_err(|source| RegistryError::Unreadable {
                path: shown.clone(),
                source,
            })?;
        let root =
            toml::from_str::<MiosTomlRoot>(&content).map_err(|e| RegistryError::Unparseable {
                path: shown.clone(),
                detail: e.to_string(),
            })?;
        let phases = root
            .build
            .and_then(|b| b.phases)
            .ok_or(RegistryError::Missing {
                path: shown.clone(),
            })?;
        if phases.list.is_empty() {
            return Err(RegistryError::Empty { path: shown });
        }
        Ok(Self {
            phases: phases.list,
        })
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

    pub fn print_list(&self) {
        for p in &self.phases {
            println!("{}:{}", p.script, p.fatal);
        }
    }
}

pub fn run_build(
    phase: &str,
    plan_only: bool,
    list_only: bool,
) -> Result<(), Box<dyn std::error::Error>> {
    let root_str = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let toml_path = std::path::Path::new(&root_str).join("usr/share/mios/mios.toml");
    let registry = PhaseRegistry::load_from_toml(&toml_path)?;
    if list_only {
        registry.print_list();
        return Ok(());
    }
    if plan_only {
        registry.print_plan();
        return Ok(());
    }

    println!("[mios-build] Executing build phase: {}", phase);
    registry.print_plan();
    Ok(())
}
