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

/// A profile resolved over its `extends` closure: which phases and package
/// sections it selects. `all` selects every registered phase and section.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ResolvedProfile {
    pub name: String,
    pub all: bool,
    pub phases: std::collections::BTreeSet<String>,
    pub package_sections: std::collections::BTreeSet<String>,
}

/// `mios.toml [profiles]` (ADR-0025): named selections over the pipeline's own
/// phases and package sections. Every error names what is wrong; nothing
/// resolves to a default selection.
pub struct Profiles {
    table: toml::value::Table,
}

impl Profiles {
    pub fn from_toml_str(text: &str) -> Result<Self, String> {
        let root: toml::Value = text
            .parse()
            .map_err(|e| format!("mios.toml did not parse: {e}"))?;
        let table = root
            .get("profiles")
            .and_then(|v| v.as_table())
            .cloned()
            .ok_or("mios.toml declares no [profiles] table")?;
        Ok(Self { table })
    }

    /// The profile an unparameterised build means: `[profiles].default`.
    pub fn default_name(&self) -> Result<String, String> {
        self.table
            .get("default")
            .and_then(|v| v.as_str())
            .map(str::to_string)
            .ok_or_else(|| "[profiles].default is absent".to_string())
    }

    /// A top-level string key of `[profiles]` (`default`, `floor`).
    pub fn table_str(&self, key: &str) -> Option<String> {
        self.table
            .get(key)
            .and_then(|v| v.as_str())
            .map(str::to_string)
    }

    /// Names of the declared profiles (every sub-table except `targets`).
    pub fn names(&self) -> Vec<String> {
        self.table
            .iter()
            .filter(|(k, v)| v.is_table() && k.as_str() != "targets")
            .map(|(k, _)| k.clone())
            .collect()
    }

    fn strings(def: &toml::value::Table, key: &str, prof: &str) -> Result<Vec<String>, String> {
        match def.get(key) {
            None => Ok(Vec::new()),
            Some(toml::Value::Array(a)) => a
                .iter()
                .map(|v| {
                    v.as_str()
                        .map(str::to_string)
                        .ok_or_else(|| format!("[profiles.{prof}].{key} holds a non-string"))
                })
                .collect(),
            Some(_) => Err(format!("[profiles.{prof}].{key} is not a list")),
        }
    }

    /// Resolve `name` over its `extends` closure; a cycle or an unknown name is an error.
    pub fn resolve(&self, name: &str) -> Result<ResolvedProfile, String> {
        let mut out = ResolvedProfile {
            name: name.to_string(),
            ..Default::default()
        };
        let mut stack: Vec<String> = Vec::new();
        self.walk(name, &mut stack, &mut out)?;
        Ok(out)
    }

    fn walk(
        &self,
        name: &str,
        stack: &mut Vec<String>,
        out: &mut ResolvedProfile,
    ) -> Result<(), String> {
        if stack.iter().any(|s| s == name) {
            return Err(format!(
                "[profiles] extends cycle: {} -> {}",
                stack.join(" -> "),
                name
            ));
        }
        let def = self
            .table
            .get(name)
            .and_then(|v| v.as_table())
            .filter(|_| name != "targets")
            .ok_or_else(|| format!("no profile named {name:?} in [profiles]"))?;
        stack.push(name.to_string());
        for parent in Self::strings(def, "extends", name)? {
            self.walk(&parent, stack, out)?;
        }
        stack.pop();
        out.all |= def.get("all").and_then(|v| v.as_bool()).unwrap_or(false);
        out.phases.extend(Self::strings(def, "phases", name)?);
        out.package_sections
            .extend(Self::strings(def, "package_sections", name)?);
        Ok(())
    }

    /// `[profiles.targets]`: image kind -> one or more profile names.
    pub fn targets(&self) -> Result<Vec<(String, Vec<String>)>, String> {
        let Some(t) = self.table.get("targets") else {
            return Ok(Vec::new());
        };
        let t = t.as_table().ok_or("[profiles.targets] is not a table")?;
        t.iter()
            .map(|(kind, v)| {
                let names = match v {
                    toml::Value::String(s) => vec![s.clone()],
                    toml::Value::Array(_) => {
                        let mut tbl = toml::value::Table::new();
                        tbl.insert("v".into(), v.clone());
                        Self::strings(&tbl, "v", "targets")?
                    }
                    _ => {
                        return Err(format!(
                            "[profiles.targets].{kind} is neither a name nor a list"
                        ))
                    }
                };
                Ok((kind.clone(), names))
            })
            .collect()
    }
}

impl PhaseRegistry {
    /// The registered phases a resolved profile selects, in registry order. A
    /// phase the profile names that the registry lacks is an error, never a skip.
    pub fn for_profile(&self, prof: &ResolvedProfile) -> Result<Vec<Phase>, String> {
        let known: std::collections::BTreeSet<&str> =
            self.phases.iter().map(|p| p.name.as_str()).collect();
        let unknown: Vec<&String> = prof
            .phases
            .iter()
            .filter(|n| !known.contains(n.as_str()))
            .collect();
        if !unknown.is_empty() {
            return Err(format!(
                "profile {:?} names phase(s) absent from [build.phases].list: {}",
                prof.name,
                unknown
                    .iter()
                    .map(|s| s.as_str())
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
        }
        // Named phases are validated even under `all`, so a typo there is never silently accepted.
        if prof.all {
            return Ok(self.phases.clone());
        }
        Ok(self
            .phases
            .iter()
            .filter(|p| prof.phases.contains(&p.name))
            .cloned()
            .collect())
    }
}

pub fn run_build_profile(
    phase: &str,
    plan_only: bool,
    list_only: bool,
    profile: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let Some(name) = profile else {
        return run_build(phase, plan_only, list_only);
    };
    let root_str = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let toml_path = std::path::Path::new(&root_str).join("usr/share/mios/mios.toml");
    let registry = PhaseRegistry::load_from_toml(&toml_path)?;
    let text = std::fs::read_to_string(&toml_path)?;
    let profiles = Profiles::from_toml_str(&text)?;
    let selected = registry.for_profile(&profiles.resolve(name)?)?;
    if selected.is_empty() {
        return Err(format!(
            "profile {name:?} selects no phases -- a build of zero phases is not a build"
        )
        .into());
    }
    for p in &selected {
        if list_only {
            println!("{}:{}", p.script, p.fatal);
        } else {
            println!("  {}", p);
        }
    }
    Ok(())
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

#[cfg(test)]
mod profile_tests {
    // Test code: a panic here IS the assertion. Scoped so production code stays under the lint.
    #![allow(clippy::unwrap_used, clippy::panic)]
    use super::*;

    const T: &str = r#"
[build.phases]
list = [
  { ordinal = "01", name = "a", script = "01-a.sh", fatal = true, apply_class = "universal" },
  { ordinal = "02", name = "b", script = "02-b.sh", fatal = true, apply_class = "universal" },
  { ordinal = "03", name = "c", script = "03-c.sh", fatal = false, apply_class = "universal" },
]
[profiles]
default = "full"
floor = "core"
[profiles.core]
phases = ["c", "a"]
[profiles.dev]
extends = ["core"]
package_sections = ["devcontainer"]
[profiles.full]
extends = ["core"]
all = true
[profiles.targets]
wsl2 = ["full", "dev"]
"#;

    fn reg() -> PhaseRegistry {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("m.toml");
        std::fs::write(&p, T).unwrap();
        PhaseRegistry::load_from_toml(&p).unwrap()
    }

    #[test]
    fn a_profile_selects_its_phases_in_registry_order() {
        let p = Profiles::from_toml_str(T).unwrap();
        let got: Vec<String> = reg()
            .for_profile(&p.resolve("core").unwrap())
            .unwrap()
            .into_iter()
            .map(|x| x.name)
            .collect();
        assert_eq!(got, ["a", "c"]);
    }

    #[test]
    fn extends_unions_and_all_selects_everything() {
        let p = Profiles::from_toml_str(T).unwrap();
        let dev = p.resolve("dev").unwrap();
        assert!(dev.phases.contains("a") && dev.package_sections.contains("devcontainer"));
        assert_eq!(
            reg()
                .for_profile(&p.resolve("full").unwrap())
                .unwrap()
                .len(),
            3
        );
    }

    #[test]
    fn an_unknown_phase_is_an_error_naming_it() {
        let p = Profiles::from_toml_str(
            &T.replace(r#"phases = ["c", "a"]"#, r#"phases = ["c", "zz-planted"]"#),
        )
        .unwrap();
        let e = reg().for_profile(&p.resolve("core").unwrap()).unwrap_err();
        assert!(e.contains("zz-planted"), "{e}");
    }

    #[test]
    fn a_cycle_and_an_unknown_profile_are_errors() {
        let p = Profiles::from_toml_str(&T.replace(
            "[profiles.core]\n",
            "[profiles.core]\nextends = [\"dev\"]\n",
        ))
        .unwrap();
        assert!(p.resolve("dev").unwrap_err().contains("cycle"));
        assert!(Profiles::from_toml_str(T)
            .unwrap()
            .resolve("nosuch")
            .unwrap_err()
            .contains("nosuch"));
    }

    #[test]
    fn targets_accept_a_name_or_a_list() {
        let t = Profiles::from_toml_str(T).unwrap().targets().unwrap();
        assert_eq!(
            t,
            vec![(
                "wsl2".to_string(),
                vec!["full".to_string(), "dev".to_string()]
            )]
        );
    }
}
