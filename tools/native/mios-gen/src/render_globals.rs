// AI-hint: Generates automation/lib/globals.sh and globals.ps1 IN FULL from mios.toml -- they are 100% generated artefacts with zero hand-written constants.
// AI-doc: usr/share/doc/mios/manual/tools.md
use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;
use std::sync::OnceLock;

const HEADER_SH: &str = r#"#!/usr/bin/env bash
# GENERATED IN FULL from usr/share/mios/mios.toml by mios-gen render-globals. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
# AI-related: usr/share/mios/mios.toml, automation/lib/globals.ps1, tools/native/mios-gen/src/render_globals.rs
# AI-functions: _mios_resolve_version
#
# Shell sibling of automation/lib/globals.ps1 -- both are rendered from the same
# SSOT by the same generator, so they cannot diverge. Dot-source from any entry
# point; every constant uses `:=` so an environment variable exported BEFORE
# sourcing still wins.

_mios_resolve_version() {
    local v=""
    if   [[ -n "${MIOS_VERSION:-}" ]];        then v="$MIOS_VERSION"
    elif [[ -f /ctx/VERSION ]];               then v="$(cat /ctx/VERSION)"
    elif [[ -f /usr/share/mios/VERSION ]];    then v="$(cat /usr/share/mios/VERSION)"
    else
        local _root
        _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
        if [[ -n "$_root" && -f "${_root}/VERSION" ]]; then
            v="$(cat "${_root}/VERSION")"
        fi
    fi
    printf '%s' "${v:-VERSION_FALLBACK}" | tr -d '[:space:]'
}
: "${MIOS_VERSION:=$(_mios_resolve_version)}"
export MIOS_VERSION
"#;

const HEADER_PS: &str = r#"# GENERATED IN FULL from usr/share/mios/mios.toml by mios-gen render-globals. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
# AI-related: usr/share/mios/mios.toml, automation/lib/globals.sh, tools/native/mios-gen/src/render_globals.rs
# AI-functions: Resolve-MiosVersion
#
# PowerShell sibling of automation/lib/globals.sh -- both are rendered from the
# same SSOT by the same generator, so they cannot diverge. Dot-source from any
# entry point:
#
#     . (Join-Path $PSScriptRoot 'automation/lib/globals.ps1')
#
# Override any constant with an environment variable BEFORE dot-sourcing -- e.g.
# `$env:MIOS_VERSION = ' - rc1'; . globals.ps1`.

function Resolve-MiosVersion {
    if ($env:MIOS_VERSION) { return ([string]$env:MIOS_VERSION).Trim() }
    foreach ($p in @(
        '/ctx/VERSION',
        '/usr/share/mios/VERSION',
        (Join-Path $PSScriptRoot '..\..\VERSION')
    )) {
        if ($p -and (Test-Path $p)) {
            $v = (Get-Content $p -EA SilentlyContinue | Out-String).Trim()
            if ($v) { return $v }
        }
    }
    return 'VERSION_FALLBACK'
}
$script:MIOS_VERSION = Resolve-MiosVersion

function Resolve-MiosDistro {
    param([string]$Default = 'podman-MiOS-DEV')
    if ($env:MIOS_WSL_DISTRO) { return $env:MIOS_WSL_DISTRO }
    try {
        $lxss = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
        if (Test-Path $lxss) {
            $all = @(Get-ChildItem $lxss -ErrorAction SilentlyContinue |
                     ForEach-Object { (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DistributionName } |
                     Where-Object { $_ })
            $resolved = ($all | Where-Object { $_ -match 'MiOS' } | Select-Object -First 1)
            if ($resolved) { return $resolved }
            $defGuid = (Get-ItemProperty $lxss -Name DefaultDistribution -ErrorAction SilentlyContinue).DefaultDistribution
            if ($defGuid) {
                $defName = (Get-ItemProperty (Join-Path $lxss $defGuid) -ErrorAction SilentlyContinue).DistributionName
                if ($defName) { return $defName }
            }
            if ($all.Count -gt 0) { return $all[0] }
        }
    } catch {}
    return $Default
}
$script:MIOS_WSL_DISTRO = Resolve-MiosDistro
"#;

const PS_HOST_PATHS: &str = r#"
# ── IMAGE DEFAULT (asserted by the image-parity drift check) ─────────
$defaultImageName = 'IMAGE_NAME_LITERAL'
"#;

const INPUT_SH: &str = r#"
# Legacy environment inputs are accepted only when they have one SSOT owner.
_mios_input() {
    local canonical="$1" name value selected='' chosen=''
    shift
    [[ -n "${!canonical:-}" ]] && return 0
    for name do
        value="${!name:-}"
        [[ -n "$value" ]] || continue
        if [[ -n "$chosen" && "$selected" != "$value" ]]; then
            printf 'conflicting legacy inputs %s and %s; set %s\n' "$chosen" "$name" "$canonical" >&2
            return 1
        fi
        selected="$value"; chosen="$name"
    done
    if [[ -n "$chosen" ]]; then printf -v "$canonical" '%s' "$selected"; fi
    return 0
}
"#;

const INPUT_PS: &str = r#"
function Resolve-MiosInput {
    param([string]$Canonical, [string[]]$Aliases, [object]$Default)
    $selected = $null
    $chosen = $null
    foreach ($name in $Aliases) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ([string]::IsNullOrEmpty($value)) { continue }
        if ($null -ne $chosen -and $selected -cne $value) {
            throw "conflicting legacy inputs $chosen and $name; set $Canonical"
        }
        $selected = $value
        $chosen = $name
    }
    if ($null -ne $chosen) { return $selected }
    return $Default
}
"#;

const PS_HOST_PATHS_TAIL: &str = r#"# ── WINDOWS HOST PATHS (resolved from the live environment) ──────────
$script:MIOS_WIN_APPDATA_DIR = if ($env:APPDATA)     { $env:APPDATA }     else { "$HOME/AppData/Roaming" }
$script:MIOS_WIN_DOCS_DIR    = if ($env:USERPROFILE) { "$env:USERPROFILE/Documents" } else { "$HOME/Documents" }
$script:MIOS_WIN_REPO_DIR    = if ($env:MIOS_WIN_REPO_DIR) { $env:MIOS_WIN_REPO_DIR } else { "$HOME/MiOS" }
"#;

fn template_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\$\{(MIOS_[A-Z0-9_]+)\}").unwrap())
}

fn sh_unsafe_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r#"['"`$\\{}\r\n]"#).unwrap())
}

pub fn build_exports(root: &Path) -> Result<BTreeMap<String, String>, String> {
    let merged = mios_resolver::resolve_merged(Some(root), false)
        .map_err(|e| format!("failed to resolve merged mios.toml: {e}"))?;
    Ok(mios_resolver::emit::build_globals_map(
        &merged,
        mios_resolver::stack_offset_of(&merged),
    ))
}

pub fn ordered_names(exports: &BTreeMap<String, String>) -> Vec<String> {
    let re = template_re();
    let mut deps: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
    for (k, v) in exports {
        let mut d = BTreeSet::new();
        for cap in re.captures_iter(v) {
            let name = cap.get(1).unwrap().as_str();
            if exports.contains_key(name) {
                d.insert(name);
            }
        }
        deps.insert(k.as_str(), d);
    }

    let mut res = Vec::new();
    let mut visited = BTreeSet::new();
    let mut visiting = BTreeSet::new();

    fn visit<'a>(
        node: &'a str,
        deps: &BTreeMap<&str, BTreeSet<&'a str>>,
        visited: &mut BTreeSet<&'a str>,
        visiting: &mut BTreeSet<&'a str>,
        res: &mut Vec<String>,
    ) {
        if visited.contains(node) {
            return;
        }
        if visiting.contains(node) {
            visited.insert(node);
            res.push(node.to_string());
            return;
        }
        visiting.insert(node);
        if let Some(d_set) = deps.get(node) {
            for dep in d_set {
                visit(dep, deps, visited, visiting, res);
            }
        }
        visiting.remove(node);
        if !visited.contains(node) {
            visited.insert(node);
            res.push(node.to_string());
        }
    }

    for name in exports.keys() {
        visit(name.as_str(), &deps, &mut visited, &mut visiting, &mut res);
    }

    res
}

pub fn sh_squote(text: &str) -> String {
    format!("'{}'", text.replace('\'', "'\"'\"'"))
}

enum Part<'a> {
    Lit(&'a str),
    Placeholder(&'a str),
}

fn split_template<'a>(re: &Regex, text: &'a str) -> Vec<Part<'a>> {
    let mut parts = Vec::new();
    let mut last_end = 0;
    for cap in re.captures_iter(text) {
        let m = cap.get(0).unwrap();
        if m.start() > last_end {
            parts.push(Part::Lit(&text[last_end..m.start()]));
        }
        let var_name = cap.get(1).unwrap().as_str();
        parts.push(Part::Placeholder(var_name));
        last_end = m.end();
    }
    if last_end < text.len() {
        parts.push(Part::Lit(&text[last_end..]));
    }
    if parts.is_empty() {
        parts.push(Part::Lit(""));
    }
    parts
}

pub fn sh_assign(name: &str, value: &str) -> String {
    let re = template_re();
    let parts = split_template(re, value);
    let has_placeholders = parts.iter().any(|p| matches!(p, Part::Placeholder(_)));

    if !has_placeholders && !sh_unsafe_re().is_match(value) {
        return format!(": \"${{{name}:={value}}}\"");
    }

    let rendered = if !has_placeholders {
        sh_squote(value)
    } else {
        let mut chunks = Vec::new();
        for part in parts {
            match part {
                Part::Placeholder(var) => chunks.push(format!("\"${{{var}:-}}\"")),
                Part::Lit(lit) => {
                    if !lit.is_empty() {
                        chunks.push(sh_squote(lit));
                    }
                }
            }
        }
        if chunks.is_empty() {
            "''".to_string()
        } else {
            chunks.join("")
        }
    };

    format!("[ -n \"${{{name}+x}}\" ] || {name}={rendered}")
}

pub fn ps_assign(name: &str, value: &str, exports: Option<&BTreeMap<String, String>>) -> String {
    ps_assign_with_inputs(name, value, exports, &[])
}

fn ps_assign_with_inputs(
    name: &str,
    value: &str,
    exports: Option<&BTreeMap<String, String>>,
    aliases: &[String],
) -> String {
    let re = template_re();
    let parts = split_template(re, value);
    let has_placeholders = parts.iter().any(|p| matches!(p, Part::Placeholder(_)));

    let rendered = if !has_placeholders {
        if !value.is_empty() && value.chars().all(|c| c.is_ascii_digit()) {
            value.to_string()
        } else {
            format!("'{}'", value.replace('\'', "''"))
        }
    } else {
        let has_live_parts = parts.iter().any(|p| match p {
            Part::Placeholder(p_name) => exports.map(|e| e.contains_key(*p_name)).unwrap_or(true),
            _ => false,
        });
        if !has_live_parts {
            format!("'{}'", value.replace('\'', "''"))
        } else {
            let mut chunks = Vec::new();
            for part in parts {
                match part {
                    Part::Placeholder(p_name) => {
                        if exports.map(|e| e.contains_key(p_name)).unwrap_or(true) {
                            chunks.push(format!("$($script:{p_name})"));
                        } else {
                            chunks.push(format!("${{{p_name}}}"));
                        }
                    }
                    Part::Lit(lit) => {
                        if !lit.is_empty() {
                            chunks.push(
                                lit.replace('`', "``")
                                    .replace('"', "`\"")
                                    .replace('$', "`$"),
                            );
                        }
                    }
                }
            }
            format!("\"{}\"", chunks.join(""))
        }
    };

    let fallback = if aliases.is_empty() {
        rendered
    } else {
        let aliases = aliases
            .iter()
            .map(|alias| format!("'{alias}'"))
            .collect::<Vec<_>>()
            .join(", ");
        format!("Resolve-MiosInput -Canonical '{name}' -Aliases @({aliases}) -Default ({rendered})")
    };
    format!("$script:{name} = if ($env:{name}) {{ $env:{name} }} else {{ {fallback} }}")
}

pub fn render_sh(
    exports: &BTreeMap<String, String>,
    names: &[String],
    version_fallback: &str,
    inputs: &BTreeMap<String, Vec<String>>,
) -> String {
    let mut lines = Vec::new();
    lines.push(HEADER_SH.replace("VERSION_FALLBACK", version_fallback));
    lines.push(INPUT_SH.to_string());
    for name in names {
        if name == "MIOS_VERSION" {
            continue;
        }
        if let Some(val) = exports.get(name) {
            if let Some(aliases) = inputs.get(name).filter(|aliases| !aliases.is_empty()) {
                lines.push(format!(
                    "_mios_input {name} {} || {{ return 1 2>/dev/null || exit 1; }}",
                    aliases.join(" ")
                ));
            }
            lines.push(sh_assign(name, val));
        }
    }
    lines.push("unset -f _mios_input\n".to_string());
    lines.join("\n")
}

pub fn render_ps1(
    exports: &BTreeMap<String, String>,
    names: &[String],
    version_fallback: &str,
    inputs: &BTreeMap<String, Vec<String>>,
) -> String {
    let mut lines = Vec::new();
    lines.push(HEADER_PS.replace("VERSION_FALLBACK", version_fallback));
    lines.push(INPUT_PS.to_string());
    for name in names {
        if name == "MIOS_VERSION" {
            continue;
        }
        if let Some(val) = exports.get(name) {
            let aliases = inputs.get(name).map(Vec::as_slice).unwrap_or(&[]);
            lines.push(if aliases.is_empty() {
                ps_assign(name, val, Some(exports))
            } else {
                ps_assign_with_inputs(name, val, Some(exports), aliases)
            });
        }
    }
    let image_name = exports
        .get("MIOS_IMAGE_NAME")
        .map(|s| s.as_str())
        .unwrap_or("ghcr.io/mios-dev/mios")
        .replace('\'', "''");
    lines.push(PS_HOST_PATHS.replace("IMAGE_NAME_LITERAL", &image_name));
    lines.push(PS_HOST_PATHS_TAIL.to_string());
    lines.join("\n")
}

pub fn check_globals_parity(sh_body: &str, ps_body: &str) -> Vec<String> {
    static SH_RE: OnceLock<Regex> = OnceLock::new();
    let sh_re = SH_RE.get_or_init(|| {
        Regex::new(r#"(?::\s*"\$\{|\[\s*-n\s*"\$\{|export\s+)(MIOS_[A-Z0-9_]+)"#).unwrap()
    });

    static PS_RE: OnceLock<Regex> = OnceLock::new();
    let ps_re = PS_RE.get_or_init(|| Regex::new(r"\$script:(MIOS_[A-Z0-9_]+)\s*=").unwrap());

    let sh_keys: BTreeSet<&str> = sh_re
        .captures_iter(sh_body)
        .map(|c| c.get(1).unwrap().as_str())
        .collect();

    let ps_keys: BTreeSet<&str> = ps_re
        .captures_iter(ps_body)
        .map(|c| c.get(1).unwrap().as_str())
        .collect();

    let ps_keys_common: BTreeSet<&str> = ps_keys
        .into_iter()
        .filter(|k| !k.starts_with("MIOS_WIN_"))
        .collect();

    let sh_keys_common = sh_keys;

    let mut problems = Vec::new();
    let missing_in_ps: Vec<&str> = sh_keys_common
        .difference(&ps_keys_common)
        .copied()
        .collect();
    if !missing_in_ps.is_empty() {
        problems.push(format!(
            "keys in globals.sh but missing in globals.ps1: {}",
            missing_in_ps.join(", ")
        ));
    }

    let missing_in_sh: Vec<&str> = ps_keys_common
        .difference(&sh_keys_common)
        .copied()
        .collect();
    if !missing_in_sh.is_empty() {
        problems.push(format!(
            "keys in globals.ps1 but missing in globals.sh: {}",
            missing_in_sh.join(", ")
        ));
    }

    problems
}

pub fn run_render_globals(root: &Path, check: bool) -> Result<(String, usize), (String, i32)> {
    let toml_path = root.join("usr/share/mios/mios.toml");
    if !toml_path.is_file() {
        return Err((
            format!("render-globals: {} does not exist", toml_path.display()),
            1,
        ));
    }

    let mut exports = build_exports(root).map_err(|e| (e, 1))?;
    let merged =
        mios_resolver::resolve_merged(Some(root), false).map_err(|e| (e.to_string(), 1))?;
    let inputs = mios_resolver::names::registry(&merged)
        .map_err(|e| (e, 1))?
        .input_aliases();
    for (canonical, aliases) in &inputs {
        if !exports.contains_key(canonical) {
            continue;
        }
        for alias in aliases {
            if exports.contains_key(alias) {
                exports.insert(alias.clone(), format!("${{{canonical}}}"));
            }
        }
    }
    let version_fallback = exports
        .get("MIOS_META_VERSION")
        .or_else(|| exports.get("MIOS_VERSION"))
        .map(|s| s.as_str())
        .unwrap_or("0.3.0");

    let names = ordered_names(&exports);
    let sh_body = render_sh(&exports, &names, version_fallback, &inputs);
    let ps_body = render_ps1(&exports, &names, version_fallback, &inputs);

    let parity_problems = check_globals_parity(&sh_body, &ps_body);
    if !parity_problems.is_empty() {
        let msg = format!(
            "[render-globals] globals.sh / globals.ps1 parity check failed:\n{}",
            parity_problems
                .iter()
                .map(|p| format!("    {p}"))
                .collect::<Vec<_>>()
                .join("\n")
        );
        return Err((msg, 1));
    }

    let sh_path = root.join("automation/lib/globals.sh");
    let ps_path = root.join("automation/lib/globals.ps1");

    let mut drifted = Vec::new();

    // Check sh_path
    let sh_existing = if sh_path.is_file() {
        fs::read_to_string(&sh_path)
            .ok()
            .map(|s| s.replace("\r\n", "\n"))
    } else {
        None
    };
    let sh_norm = sh_body.replace("\r\n", "\n");
    if sh_existing.as_deref() != Some(&sh_norm) {
        drifted.push("automation/lib/globals.sh".to_string());
        if !check {
            if let Some(parent) = sh_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            if let Err(e) = fs::write(&sh_path, &sh_norm) {
                return Err((format!("failed to write {}: {e}", sh_path.display()), 1));
            }
        }
    }

    // Check ps_path
    let ps_existing = if ps_path.is_file() {
        fs::read(&ps_path).ok().map(|bytes| {
            let slice = if bytes.starts_with(&[0xEF, 0xBB, 0xBF]) {
                &bytes[3..]
            } else {
                &bytes[..]
            };
            String::from_utf8_lossy(slice).replace("\r\n", "\n")
        })
    } else {
        None
    };
    let ps_norm = ps_body.replace("\r\n", "\n");
    if ps_existing.as_deref() != Some(&ps_norm) {
        drifted.push("automation/lib/globals.ps1".to_string());
        if !check {
            if let Some(parent) = ps_path.parent() {
                let _ = fs::create_dir_all(parent);
            }
            let mut bytes = vec![0xEF, 0xBB, 0xBF];
            let crlf_body = ps_norm.replace('\n', "\r\n");
            bytes.extend_from_slice(crlf_body.as_bytes());
            if let Err(e) = fs::write(&ps_path, bytes) {
                return Err((format!("failed to write {}: {e}", ps_path.display()), 1));
            }
        }
    }

    let count = names.len();

    if check {
        if !drifted.is_empty() {
            let drift_list = drifted
                .iter()
                .map(|p| format!("    {p}"))
                .collect::<Vec<_>>()
                .join("\n");
            let msg = format!(
                "[render-globals] resolvers are stale vs SSOT:\n{drift_list}\n    run: mios-gen render-globals"
            );
            return Err((msg, 1));
        }
        Ok((
            format!("[render-globals] both resolvers match SSOT ({count} constants)"),
            count,
        ))
    } else {
        Ok((
            format!(
                "[render-globals] generated {count} constants into globals.sh + globals.ps1 (no hand-written literals remain)"
            ),
            count,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sh_assign_simple_value() {
        assert_eq!(
            sh_assign("MIOS_PORTS_SSH", "8100"),
            ": \"${MIOS_PORTS_SSH:=8100}\""
        );
    }

    #[test]
    fn test_sh_assign_value_with_brace() {
        let out = sh_assign("MIOS_MSG", "hello {name}");
        assert!(!out.contains(":="));
        assert!(out.contains("MIOS_MSG+x"));
    }

    #[test]
    fn test_sh_assign_value_with_apostrophe() {
        let out = sh_assign("MIOS_JOB", "the operator's phone");
        assert!(!out.contains(":="));
        assert!(out.contains("'\"'\"'"));
    }

    #[test]
    fn test_sh_assign_template_stays_live() {
        let out = sh_assign(
            "MIOS_URLS_FORGE",
            "http://localhost:${MIOS_PORTS_FORGE_HTTP}",
        );
        assert!(out.contains("\"${MIOS_PORTS_FORGE_HTTP:-}\""));
    }

    #[test]
    fn test_sh_assign_assignment_is_conditional() {
        for value in ["8100", "has }brace", "has 'quote"] {
            let out = sh_assign("MIOS_X", value);
            assert!(out.contains(":=") || out.contains("+x"));
        }
    }

    #[test]
    fn test_ps_assign_numeric_is_bare() {
        let out = ps_assign("MIOS_PORTS_SSH", "8100", None);
        assert!(out.contains("else { 8100 }"));
    }

    #[test]
    fn test_ps_assign_string_is_single_quoted() {
        let out = ps_assign("MIOS_IDENTITY_USERNAME", "mios", None);
        assert!(out.contains("else { 'mios' }"));
    }

    #[test]
    fn test_ps_assign_embedded_quote_is_doubled() {
        let out = ps_assign("MIOS_JOB", "operator's phone", None);
        assert!(out.contains("''"));
    }

    #[test]
    fn test_ps_assign_template_becomes_subexpression() {
        let mut exports = BTreeMap::new();
        exports.insert("MIOS_PORTS_FORGE_HTTP".to_string(), "8400".to_string());
        let out = ps_assign(
            "MIOS_URLS_FORGE",
            "http://localhost:${MIOS_PORTS_FORGE_HTTP}",
            Some(&exports),
        );
        assert!(out.contains("$($script:MIOS_PORTS_FORGE_HTTP)"));
    }

    #[test]
    fn test_ps_assign_dollar_in_template_is_escaped() {
        let mut exports = BTreeMap::new();
        exports.insert("MIOS_PORTS_SSH".to_string(), "8100".to_string());
        let out = ps_assign("MIOS_X", "a $literal and ${MIOS_PORTS_SSH}", Some(&exports));
        assert!(out.contains("`$literal"));
    }

    #[test]
    fn test_ps_assign_env_override_wins() {
        let out = ps_assign("MIOS_PORTS_SSH", "8100", None);
        assert!(out.contains("if ($env:MIOS_PORTS_SSH)"));
    }

    #[test]
    fn test_ordered_names_topology() {
        let mut exports = BTreeMap::new();
        exports.insert(
            "MIOS_URLS_FORGE".to_string(),
            "http://localhost:${MIOS_PORTS_FORGE_HTTP}".to_string(),
        );
        exports.insert("MIOS_PORTS_FORGE_HTTP".to_string(), "8400".to_string());

        let names = ordered_names(&exports);
        let idx_dep = names
            .iter()
            .position(|n| n == "MIOS_PORTS_FORGE_HTTP")
            .unwrap();
        let idx_ref = names.iter().position(|n| n == "MIOS_URLS_FORGE").unwrap();
        assert!(idx_dep < idx_ref);
    }

    #[test]
    fn test_globals_parity() {
        let sh_body = ": \"${MIOS_TEST_KEY:=1234}\"\n";
        let ps_body = "$script:MIOS_TEST_KEY = 1234\n";
        let problems = check_globals_parity(sh_body, ps_body);
        assert!(
            problems.is_empty(),
            "expected 0 problems, got: {problems:?}"
        );

        let ps_missing = "$script:MIOS_OTHER_KEY = 1234\n";
        let problems_missing_ps = check_globals_parity(sh_body, ps_missing);
        assert!(problems_missing_ps
            .iter()
            .any(|p| p.contains("missing in globals.ps1")));

        let sh_missing = ": \"${MIOS_OTHER_KEY:=1234}\"\n";
        let problems_missing_sh = check_globals_parity(sh_missing, ps_body);
        assert!(problems_missing_sh
            .iter()
            .any(|p| p.contains("missing in globals.sh")));
    }
}
