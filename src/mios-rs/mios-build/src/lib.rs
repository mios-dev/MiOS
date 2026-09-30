// AI-hint: Native build orchestrator and phase registry for MiOS.
// AI-related: automation/build.sh, automation/build-mios.sh

use serde::{Deserialize, Serialize};
use std::fmt;

/// Executable roles are distinct from Cargo libraries and from their shared
/// implementation modules. The SSOT assigns each executable exactly once.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct NativeTarget {
    pub workspace: String,
    pub package: String,
    pub binary: String,
    pub category: String,
    pub install_dir: String,
    pub expose_bin: bool,
    pub compat_dirs: Vec<String>,
    pub platform: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct NativeCategory {
    binaries: Vec<String>,
    install_dir: String,
    expose_bin: bool,
    compat_dirs: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct NativeConfig {
    workspaces: Vec<String>,
    windows_only: Vec<String>,
    categories: std::collections::BTreeMap<String, NativeCategory>,
}

#[derive(Debug, Deserialize)]
struct NativeMetadata {
    workspace_members: Vec<String>,
    packages: Vec<NativePackage>,
}

#[derive(Debug, Deserialize)]
struct NativePackage {
    id: String,
    name: String,
    targets: Vec<NativeCargoTarget>,
}

#[derive(Debug, Deserialize)]
struct NativeCargoTarget {
    name: String,
    kind: Vec<String>,
}

fn native_config(ssot: &str) -> Result<NativeConfig, String> {
    let doc: toml::Value = toml::from_str(ssot).map_err(|e| format!("native catalog TOML: {e}"))?;
    let config: NativeConfig = doc
        .get("build")
        .and_then(|v| v.get("native"))
        .ok_or("SSOT has no [build.native] catalog")?
        .clone()
        .try_into()
        .map_err(|e| format!("[build.native]: {e}"))?;
    let required = ["cli", "apps", "services", "daemons"];
    if config.categories.len() != required.len()
        || required
            .iter()
            .any(|name| !config.categories.contains_key(*name))
    {
        return Err(
            "[build.native.categories] must declare cli, apps, services and daemons exactly".into(),
        );
    }
    if config.workspaces.is_empty() {
        return Err("[build.native].workspaces is empty".into());
    }
    let mut seen = std::collections::BTreeSet::new();
    for workspace in &config.workspaces {
        if workspace.is_empty()
            || workspace.starts_with('/')
            || workspace.contains('\\')
            || workspace.chars().any(char::is_control)
            || workspace
                .split('/')
                .any(|part| part.is_empty() || part == "." || part == ".." || part.contains(':'))
            || !seen.insert(workspace)
        {
            return Err(format!(
                "invalid or duplicate native workspace {workspace:?}"
            ));
        }
    }
    seen.clear();
    for (category, group) in &config.categories {
        if group.install_dir != "/usr/bin" && group.install_dir != "/usr/libexec/mios" {
            return Err(format!(
                "native {category}: install_dir must be /usr/bin or /usr/libexec/mios"
            ));
        }
        if group
            .compat_dirs
            .iter()
            .any(|directory| directory != "/usr/bin" && directory != "/usr/libexec/mios")
        {
            return Err(format!(
                "native {category}: unsupported compatibility directory"
            ));
        }
        for binary in &group.binaries {
            if binary.is_empty()
                || !binary
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
            {
                return Err(format!("native {category}: invalid executable name"));
            }
            if !seen.insert(binary) {
                return Err(format!(
                    "native binary {binary} occurs in multiple categories"
                ));
            }
        }
    }
    if seen.is_empty() {
        return Err("native categories declare zero executables".into());
    }
    let mut windows = std::collections::BTreeSet::new();
    for binary in &config.windows_only {
        if !seen.contains(binary) || !windows.insert(binary) {
            return Err(format!(
                "windows_only contains unknown or duplicate native binary {binary}"
            ));
        }
    }
    Ok(config)
}

fn plan_native_metadata(
    config: &NativeConfig,
    metadata: &[(String, NativeMetadata)],
    platform: &str,
) -> Result<Vec<NativeTarget>, String> {
    if platform != "linux" && platform != "windows" {
        return Err(format!("unsupported native platform {platform:?}"));
    }
    let mut observed = std::collections::BTreeSet::new();
    let mut plan = Vec::new();
    for (workspace, data) in metadata {
        let members: std::collections::BTreeSet<_> = data.workspace_members.iter().collect();
        for package in &data.packages {
            if !members.contains(&package.id) {
                continue;
            }
            for target in &package.targets {
                if !target.kind.iter().any(|kind| kind == "bin") {
                    continue;
                }
                if !observed.insert(target.name.clone()) {
                    return Err(format!(
                        "multiple Cargo targets declare native binary {}",
                        target.name
                    ));
                }
                let (category, group) = config
                    .categories
                    .iter()
                    .find(|(_, group)| group.binaries.contains(&target.name))
                    .ok_or_else(|| {
                        format!(
                            "Cargo executable {} has no SSOT native category",
                            target.name
                        )
                    })?;
                let target_platform = if config.windows_only.contains(&target.name) {
                    "windows"
                } else {
                    "linux"
                };
                if platform != target_platform {
                    continue;
                }
                plan.push(NativeTarget {
                    workspace: workspace.clone(),
                    package: package.name.clone(),
                    binary: target.name.clone(),
                    category: category.clone(),
                    install_dir: group.install_dir.clone(),
                    expose_bin: group.expose_bin,
                    compat_dirs: group.compat_dirs.clone(),
                    platform: target_platform.into(),
                });
            }
        }
    }
    for group in config.categories.values() {
        for binary in &group.binaries {
            if !observed.contains(binary) {
                return Err(format!(
                    "SSOT native executable {binary} has no Cargo binary target"
                ));
            }
        }
    }
    if plan.is_empty() {
        return Err(format!("native plan selects zero {platform} executables"));
    }
    plan.sort_by(|a, b| {
        (&a.category, &a.workspace, &a.binary).cmp(&(&b.category, &b.workspace, &b.binary))
    });
    Ok(plan)
}

/// Cargo is queried without compiling. Both workspaces must be inspected,
/// including platform-specific binaries, before any selected artifact installs.
pub fn native_target_plan(
    root: &std::path::Path,
    platform: &str,
) -> Result<Vec<NativeTarget>, String> {
    if platform != "linux" && platform != "windows" {
        return Err(format!("unsupported native platform {platform:?}"));
    }
    let ssot = std::fs::read_to_string(root.join("usr/share/mios/mios.toml"))
        .map_err(|e| format!("cannot read native SSOT: {e}"))?;
    let config = native_config(&ssot)?;
    let mut metadata = Vec::new();
    for workspace in &config.workspaces {
        let output = std::process::Command::new("cargo")
            .args([
                "metadata",
                "--no-deps",
                "--format-version",
                "1",
                "--offline",
                "--locked",
            ])
            .current_dir(root.join(workspace))
            .output()
            .map_err(|e| format!("native metadata for {workspace}: {e}"))?;
        if !output.status.success() {
            return Err(format!(
                "native metadata for {workspace} failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }
        let data = serde_json::from_slice(&output.stdout)
            .map_err(|e| format!("invalid Cargo metadata for {workspace}: {e}"))?;
        metadata.push((workspace.clone(), data));
    }
    plan_native_metadata(&config, &metadata, platform)
}

#[cfg(test)]
mod native_catalog_tests {
    use super::*;
    const CATALOG: &str = r#"
[build.native]
workspaces = ["tools/native", "src/mios-rs"]
windows_only = ["wallpaper"]
[build.native.categories.cli]
binaries = ["tool"]
install_dir = "/usr/bin"
expose_bin = false
compat_dirs = ["/usr/libexec/mios"]
[build.native.categories.apps]
binaries = ["app"]
install_dir = "/usr/bin"
expose_bin = false
compat_dirs = []
[build.native.categories.services]
binaries = ["seeder"]
install_dir = "/usr/libexec/mios"
expose_bin = false
compat_dirs = []
[build.native.categories.daemons]
binaries = ["agent", "wallpaper"]
install_dir = "/usr/libexec/mios"
expose_bin = true
compat_dirs = []
"#;
    fn metadata(names: &[&str]) -> Vec<(String, NativeMetadata)> {
        let targets: Vec<_> = names
            .iter()
            .map(|name| serde_json::json!({"name": name,"kind":["bin"]}))
            .collect();
        let value = serde_json::json!({"workspace_members":["opaque-member", "library-member"],"packages":[
            {"id":"opaque-member","name":"package","targets":targets},
            {"id":"not-member","name":"dependency","targets":[{"name":"foreign","kind":["bin"]}]},
            {"id":"library-member","name":"library","targets":[{"name":"shared","kind":["lib"]}]}]});
        vec![(
            "tools/native".into(),
            serde_json::from_value(value).unwrap(),
        )]
    }
    fn all() -> Vec<(String, NativeMetadata)> {
        metadata(&["tool", "app", "seeder", "agent", "wallpaper"])
    }
    #[test]
    fn categories_cover_roles_without_copying_libraries_or_dependencies() {
        let plan = plan_native_metadata(&native_config(CATALOG).unwrap(), &all(), "linux").unwrap();
        assert_eq!(plan.len(), 4);
        assert_eq!(
            plan.iter()
                .map(|target| target.category.as_str())
                .collect::<Vec<_>>(),
            vec!["apps", "cli", "daemons", "services"]
        );
        assert_eq!(
            plan.iter()
                .find(|target| target.binary == "tool")
                .unwrap()
                .compat_dirs,
            vec!["/usr/libexec/mios"]
        );
    }
    #[test]
    fn platform_selection_preserves_windows_daemon() {
        let plan =
            plan_native_metadata(&native_config(CATALOG).unwrap(), &all(), "windows").unwrap();
        assert_eq!(plan.len(), 1);
        assert_eq!(plan[0].binary, "wallpaper");
        assert_eq!(plan[0].category, "daemons");
    }
    #[test]
    fn duplicate_category_membership_fails() {
        assert!(
            native_config(&CATALOG.replace("binaries = [\"app\"]", "binaries = [\"tool\"]"))
                .unwrap_err()
                .contains("multiple categories")
        );
    }
    #[test]
    fn missing_category_fails() {
        assert!(
            native_config(&CATALOG.replace("categories.services", "categories.other"))
                .unwrap_err()
                .contains("must declare")
        );
    }
    #[test]
    fn unclassified_cargo_target_fails() {
        assert!(plan_native_metadata(
            &native_config(CATALOG).unwrap(),
            &metadata(&["tool", "app", "seeder", "agent", "wallpaper", "unknown"]),
            "linux"
        )
        .unwrap_err()
        .contains("unknown has no SSOT"));
    }
    #[test]
    fn stale_registry_entry_fails() {
        assert!(plan_native_metadata(
            &native_config(CATALOG).unwrap(),
            &metadata(&["tool", "app", "seeder", "agent"]),
            "linux"
        )
        .unwrap_err()
        .contains("wallpaper has no Cargo"));
    }
    #[test]
    fn duplicate_cargo_binary_fails() {
        assert!(plan_native_metadata(
            &native_config(CATALOG).unwrap(),
            &metadata(&["tool", "app", "seeder", "agent", "wallpaper", "tool"]),
            "linux"
        )
        .unwrap_err()
        .contains("multiple Cargo"));
    }
    #[test]
    fn unsupported_platform_fails() {
        assert!(
            plan_native_metadata(&native_config(CATALOG).unwrap(), &all(), "other")
                .unwrap_err()
                .contains("unsupported")
        );
    }
    #[test]
    fn workspace_traversal_and_install_escape_fail() {
        assert!(
            native_config(&CATALOG.replace("tools/native", "tools\\tnative"))
                .unwrap_err()
                .contains("workspace")
        );
        assert!(
            native_config(&CATALOG.replace("tools/native", "../outside"))
                .unwrap_err()
                .contains("workspace")
        );
        assert!(native_config(&CATALOG.replace("/usr/bin", "/var/bin"))
            .unwrap_err()
            .contains("install_dir"));
    }
    #[test]
    fn unknown_windows_binary_fails() {
        assert!(native_config(&CATALOG.replace(
            "windows_only = [\"wallpaper\"]",
            "windows_only = [\"missing\"]"
        ))
        .unwrap_err()
        .contains("windows_only"));
    }
    #[test]
    fn malformed_and_empty_catalogs_fail() {
        assert!(native_config("broken = [").unwrap_err().contains("TOML"));
        assert!(native_config(&CATALOG.replace(
            "workspaces = [\"tools/native\", \"src/mios-rs\"]",
            "workspaces = []"
        ))
        .unwrap_err()
        .contains("empty"));
        assert!(native_config(&CATALOG.replace("expose_bin = false", "expose_bin = 1")).is_err());
    }
    #[test]
    fn shipped_ssot_matches_both_real_cargo_workspaces() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..");
        let plan = native_target_plan(&root, "linux").unwrap();
        assert!(plan
            .iter()
            .any(|target| target.binary == "mios-render-quadlets"));
        assert!(plan
            .iter()
            .any(|target| target.binary == "mios-node" && target.category == "daemons"));
        assert!(!plan.iter().any(|target| target.binary == "mios-wallpaperd"));
        assert!(plan.len() > 10);
    }
}

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

    /// A top-level string key of `[profiles]` (`default`).
    pub fn table_str(&self, key: &str) -> Option<String> {
        self.table
            .get(key)
            .and_then(|v| v.as_str())
            .map(str::to_string)
    }

    /// Names of the declared profiles (every sub-table).
    pub fn names(&self) -> Vec<String> {
        self.table
            .iter()
            .filter(|(_, v)| v.is_table())
            .map(|(k, _)| k.clone())
            .collect()
    }

    /// The one profile marked `floor = true`; none or several is an error.
    pub fn floor(&self) -> Result<String, String> {
        let marked: Vec<String> = self
            .table
            .iter()
            .filter(|(_, v)| v.get("floor").and_then(|f| f.as_bool()) == Some(true))
            .map(|(k, _)| k.clone())
            .collect();
        match marked.as_slice() {
            [one] => Ok(one.clone()),
            [] => Err("no profile in [profiles] declares floor = true".to_string()),
            many => Err(format!(
                "more than one profile declares floor = true: {}",
                many.join(", ")
            )),
        }
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

    /// Image kind -> the profiles whose `targets` list it, in declaration order.
    pub fn targets(&self) -> Result<Vec<(String, Vec<String>)>, String> {
        let mut by_kind: std::collections::BTreeMap<String, Vec<String>> = Default::default();
        for (name, def) in self.table.iter() {
            let Some(def) = def.as_table() else { continue };
            for kind in Self::strings(def, "targets", name)? {
                by_kind.entry(kind).or_default().push(name.clone());
            }
        }
        Ok(by_kind.into_iter().collect())
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
    run_build_selected(phase, plan_only, list_only, false, profile)
}

/// `miosd build`: phases (or, with `sections_only`, package sections) for a
/// profile. With no profile named, `[profiles].default` applies when the SSOT
/// declares `[profiles]`; a tree without it keeps the full registry.
pub fn run_build_selected(
    phase: &str,
    plan_only: bool,
    list_only: bool,
    sections_only: bool,
    profile: Option<&str>,
) -> Result<(), Box<dyn std::error::Error>> {
    let root_str = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
    let toml_path = std::path::Path::new(&root_str).join("usr/share/mios/mios.toml");
    let text = std::fs::read_to_string(&toml_path)?;
    let profiles = Profiles::from_toml_str(&text).ok();
    let name = match (profile, &profiles) {
        (Some(n), _) => n.to_string(),
        (None, Some(p)) => p.default_name()?,
        (None, None) if sections_only => {
            return Err(
                "mios.toml declares no [profiles]; there is no section selection to print".into(),
            )
        }
        (None, None) => return run_build(phase, plan_only, list_only),
    };
    let profiles = profiles.ok_or("mios.toml declares no [profiles] table")?;
    let resolved = profiles.resolve(&name)?;
    let registry = PhaseRegistry::load_from_toml(&toml_path)?;
    let selected = registry.for_profile(&resolved)?;
    if selected.is_empty() {
        return Err(format!(
            "profile {name:?} selects no phases -- a build of zero phases is not a build"
        )
        .into());
    }
    if sections_only {
        if resolved.all {
            println!("*");
        } else {
            for s in &resolved.package_sections {
                println!("{s}");
            }
        }
        return Ok(());
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
[profiles.core]
floor = true
phases = ["c", "a"]
[profiles.dev]
extends = ["core"]
package_sections = ["devcontainer"]
targets = ["wsl2", "cloud"]
[profiles.full]
all = true
targets = ["wsl2"]
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
    fn targets_invert_each_profiles_list() {
        let t = Profiles::from_toml_str(T).unwrap().targets().unwrap();
        let s = |v: &[&str]| v.iter().map(|x| x.to_string()).collect::<Vec<_>>();
        assert_eq!(
            t,
            vec![
                ("cloud".to_string(), s(&["dev"])),
                ("wsl2".to_string(), s(&["dev", "full"])),
            ]
        );
    }

    #[test]
    fn exactly_one_floor() {
        assert_eq!(Profiles::from_toml_str(T).unwrap().floor().unwrap(), "core");
        let none = Profiles::from_toml_str(&T.replace("floor = true\n", "")).unwrap();
        assert!(none.floor().unwrap_err().contains("no profile"));
        let two =
            Profiles::from_toml_str(&T.replace("all = true", "all = true\nfloor = true")).unwrap();
        assert!(two.floor().unwrap_err().contains("core, full"));
    }
}
