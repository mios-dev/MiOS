// AI-hint: Main entrypoint for mios-gen -- the unified SSOT projector and code generator binary (ADR-0021 gen category).
// AI-related: usr/share/mios/mios.toml, tools/native/Cargo.toml, docs/design/doc-rust-static-port.md, usr/share/doc/mios/adr/0021-rust-static-binary-consolidation.md

#![forbid(unsafe_code)]

use clap::{Parser, Subcommand};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

mod adr_index;
mod ai_manifest;
mod gate_index;
mod metal_vs_hosted;
mod pipeline_index;
mod roadmap_index;

#[derive(Parser, Debug)]
#[command(
    name = "mios-gen",
    version,
    about = "MiOS SSOT projector verbs (ADR-0021 gen category)"
)]
struct Cli {
    /// Output format (text or json)
    #[arg(long, global = true, default_value = "text")]
    format: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Renders usr/lib/containers/policy.json from usr/share/mios/mios.toml [security.sigstore] SSOT
    #[command(name = "cosign-policy")]
    CosignPolicy {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed file is in sync with SSOT without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates the agent outbound egress nftables ruleset from [security.egress] SSOT
    #[command(name = "egress-firewall")]
    EgressFirewall {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,
    },

    /// Generates usr/share/mios/reference/drift-gate-index.tsv from automation/98-drift-checks.sh
    #[command(name = "gate-index")]
    GateIndex {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Path to 98-drift-checks.sh (default: automation/98-drift-checks.sh)
        #[arg(long)]
        script: Option<PathBuf>,

        /// Output path for drift-gate-index.tsv
        #[arg(long)]
        output: Option<PathBuf>,

        /// Check mode: verify committed TSV is in sync without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates usr/share/mios/reference/pipeline-index.tsv from automation/[0-9][0-9]-*.sh and SSOT
    #[command(name = "pipeline-index")]
    PipelineIndex {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed TSV is in sync without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates repo-root ADR.md breadcrumb index from usr/share/doc/mios/adr/
    #[command(name = "adr-index")]
    AdrIndex {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed ADR.md is in sync without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates usr/share/doc/mios/reference/metal-vs-hosted.md from [blade] SSOT
    #[command(name = "metal-vs-hosted")]
    MetalVsHosted {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed markdown is in sync without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates and validates Table of Contents, Index, Metrics, and Rollup in ROADMAP.md
    #[command(name = "roadmap-index")]
    RoadmapIndex {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed ROADMAP.md is in sync without modifying it
        #[arg(long)]
        check: bool,
    },

    /// Generates or checks AI repository and tool manifests from Markdown and source files
    #[command(name = "ai-manifest")]
    AiManifest {
        /// Repository root directory
        #[arg(long)]
        root: Option<PathBuf>,

        /// Check mode: verify committed manifests are in sync without modifying them
        #[arg(long)]
        check: bool,
    },
}

fn resolve_root(cli_root: Option<PathBuf>) -> PathBuf {
    if let Some(r) = cli_root {
        return r;
    }
    if let Ok(r) = env::var("MIOS_DRIFT_ROOT") {
        if !r.trim().is_empty() {
            return PathBuf::from(r.trim());
        }
    }
    if let Ok(r) = env::var("MIOS_ROOT") {
        if !r.trim().is_empty() {
            return PathBuf::from(r.trim());
        }
    }
    PathBuf::from(".")
}

fn run_cosign_policy(root: &Path, check_mode: bool) -> Result<(), (String, i32)> {
    let ssot_path = root.join("usr/share/mios/mios.toml");
    let target_path = root.join("usr/lib/containers/policy.json");

    if !ssot_path.is_file() {
        return Err((format!("{} not found", ssot_path.display()), 1));
    }

    let toml_bytes = fs::read(&ssot_path).map_err(|e| {
        (
            format!("{} could not be read: {}", ssot_path.display(), e),
            1,
        )
    })?;
    let toml_str = std::str::from_utf8(&toml_bytes).map_err(|e| {
        (
            format!("{} could not be read: {}", ssot_path.display(), e),
            1,
        )
    })?;
    let val: toml::Value = toml::from_str(toml_str).map_err(|e| {
        (
            format!("{} could not be read: {}", ssot_path.display(), e),
            1,
        )
    })?;

    let sigstore = val
        .get("security")
        .and_then(|s| s.get("sigstore"))
        .and_then(|s| s.as_table())
        .ok_or_else(|| {
            (
                "mios.toml declares no [security.sigstore] table".to_string(),
                1,
            )
        })?;

    let policy_mode = sigstore
        .get("policy_mode")
        .and_then(|p| p.as_str())
        .map(|s| s.trim())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| {
            (
                "[security.sigstore].policy_mode is absent or not a string".to_string(),
                1,
            )
        })?;

    let json_val = serde_json::json!({
        "default": [
            {
                "type": policy_mode
            }
        ]
    });
    let rendered = serde_json::to_string_pretty(&json_val)
        .map_err(|e| (format!("Failed to format JSON: {e}"), 1))?
        + "\n";

    if check_mode {
        if !target_path.is_file() {
            return Err((format!("{} does not exist", target_path.display()), 1));
        }
        let committed = fs::read_to_string(&target_path)
            .map_err(|e| (format!("Failed to read {}: {e}", target_path.display()), 1))?;
        if committed != rendered {
            return Err((
                format!(
                    "{} is out of sync with [security.sigstore] SSOT -- regenerate: mios-gen cosign-policy",
                    target_path.display()
                ),
                1,
            ));
        }
        println!("[OK] usr/lib/containers/policy.json is in sync with SSOT");
        return Ok(());
    }

    if let Some(parent) = target_path.parent() {
        fs::create_dir_all(parent).map_err(|e| {
            (
                format!("Failed to create directory {}: {e}", parent.display()),
                1,
            )
        })?;
    }
    fs::write(&target_path, rendered.as_bytes())
        .map_err(|e| (format!("Failed to write {}: {e}", target_path.display()), 1))?;

    println!("Generated {}", target_path.display());
    Ok(())
}

fn get_agent_user(root: &Path) -> String {
    if let Ok(u) = env::var("MIOS_AGENT_USER") {
        let trimmed = u.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    let service_path = root.join("usr/lib/systemd/system/mios-agent-pipe.service");
    if let Ok(content) = fs::read_to_string(&service_path) {
        for line in content.lines() {
            if let Some(rest) = line.strip_prefix("User=") {
                let trimmed = rest.trim();
                if !trimmed.is_empty() {
                    return trimmed.to_string();
                }
            }
        }
    }

    "mios-ai".to_string()
}

fn build_egress_ruleset(mode: &str, allow: &[String], user: &str) -> (String, &'static str) {
    let (final_rule, note, normalized_mode) = match mode {
        "enforce" => (
            "        log prefix \"mios-egress-drop \" drop",
            "ENFORCE: the agent's non-allowed external egress is logged + DROPPED.",
            "enforce",
        ),
        "audit" => (
            "        log prefix \"mios-egress-audit \" accept",
            "AUDIT: the agent's external egress is LOGGED then accepted (observe only).",
            "audit",
        ),
        _ => (
            "        accept   # mode=off -> no-op even if applied",
            "OFF: informational ruleset; applying it changes nothing.",
            "off",
        ),
    };

    let mut allow_rules = String::new();
    let mut v4: Vec<&str> = allow
        .iter()
        .map(|s| s.as_str())
        .filter(|s| !s.contains(':'))
        .collect();
    let mut v6: Vec<&str> = allow
        .iter()
        .map(|s| s.as_str())
        .filter(|s| s.contains(':'))
        .collect();
    v4.sort_unstable();
    v6.sort_unstable();

    if !v4.is_empty() {
        allow_rules.push_str(&format!(
            "        ip daddr {{ {} }} accept\n",
            v4.join(", ")
        ));
    }
    if !v6.is_empty() {
        allow_rules.push_str(&format!(
            "        ip6 daddr {{ {} }} accept\n",
            v6.join(", ")
        ));
    }

    let content = format!(
        r#"# AI-hint: GENERATED nftables egress firewall for the MiOS agent (#54). DO NOT EDIT -- regenerate via mios-gen egress-firewall. {note}
table inet mios_egress {{
    chain output {{
        type filter hook output priority filter; policy accept;
        meta skuid != "{user}" accept
        oifname "lo" accept
        ip daddr 127.0.0.0/8 accept
        ip6 daddr ::1 accept
        ip daddr 100.64.0.0/10 accept
        ip daddr 172.16.0.0/12 accept
{allow_rules}{final_rule}
    }}
}}
"#
    );

    (content, normalized_mode)
}

fn run_egress_firewall(root: &Path) -> Result<(), (String, i32)> {
    let toml_path = env::var("MIOS_TOML")
        .map(PathBuf::from)
        .unwrap_or_else(|_| root.join("usr/share/mios/mios.toml"));
    let out_path = env::var("MIOS_EGRESS_OUT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| root.join("usr/share/mios/security/egress.nft"));

    let toml_bytes = fs::read(&toml_path)
        .map_err(|e| (format!("Failed to read {}: {e}", toml_path.display()), 1))?;
    let toml_str = std::str::from_utf8(&toml_bytes)
        .map_err(|e| (format!("Failed to read {}: {e}", toml_path.display()), 1))?;
    let val: toml::Value = toml::from_str(toml_str)
        .map_err(|e| (format!("Failed to parse {}: {e}", toml_path.display()), 1))?;

    let egress_table = val
        .get("security")
        .and_then(|s| s.get("egress"))
        .and_then(|e| e.as_table());

    let mode = egress_table
        .and_then(|e| e.get("mode"))
        .and_then(|m| m.as_str())
        .unwrap_or("off")
        .trim()
        .to_ascii_lowercase();

    let mut allow = Vec::new();
    if let Some(arr) = egress_table
        .and_then(|e| e.get("allow"))
        .and_then(|a| a.as_array())
    {
        for item in arr {
            let s = match item {
                toml::Value::String(s) => s.trim().to_string(),
                toml::Value::Integer(i) => i.to_string(),
                _ => item.to_string(),
            };
            if !s.is_empty() {
                allow.push(s);
            }
        }
    }

    let user = get_agent_user(root);
    let (ruleset, normalized_mode) = build_egress_ruleset(&mode, &allow, &user);

    if let Some(parent) = out_path.parent() {
        fs::create_dir_all(parent).map_err(|e| {
            (
                format!("Failed to create directory {}: {e}", parent.display()),
                1,
            )
        })?;
    }
    fs::write(&out_path, ruleset.as_bytes())
        .map_err(|e| (format!("Failed to write {}: {e}", out_path.display()), 1))?;

    println!(
        "[egress-fw] wrote {} (mode={}, user={}, allow={})",
        out_path.display(),
        normalized_mode,
        user,
        allow.len()
    );
    Ok(())
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let (subcommand, target, result) = match cli.command {
        Commands::CosignPolicy { root, check } => {
            let r = resolve_root(root);
            (
                "cosign-policy",
                "usr/lib/containers/policy.json",
                run_cosign_policy(&r, check),
            )
        }
        Commands::EgressFirewall { root } => {
            let r = resolve_root(root);
            (
                "egress-firewall",
                "usr/share/mios/security/egress.nft",
                run_egress_firewall(&r),
            )
        }
        Commands::GateIndex {
            root,
            script,
            output,
            check,
        } => {
            let r = resolve_root(root);
            (
                "gate-index",
                "usr/share/mios/reference/drift-gate-index.tsv",
                gate_index::run_gate_index(&r, script, output, check),
            )
        }
        Commands::PipelineIndex { root, check } => {
            let r = resolve_root(root);
            (
                "pipeline-index",
                "usr/share/mios/reference/pipeline-index.tsv",
                pipeline_index::run_pipeline_index(&r, check),
            )
        }
        Commands::AdrIndex { root, check } => {
            let r = resolve_root(root);
            (
                "adr-index",
                "ADR.md",
                adr_index::run_adr_index(&r, check, cli.format == "json"),
            )
        }
        Commands::MetalVsHosted { root, check } => {
            let r = resolve_root(root);
            (
                "metal-vs-hosted",
                "usr/share/doc/mios/reference/metal-vs-hosted.md",
                metal_vs_hosted::run_metal_vs_hosted(&r, check, cli.format == "json"),
            )
        }
        Commands::RoadmapIndex { root, check } => {
            let r = resolve_root(root);
            (
                "roadmap-index",
                "ROADMAP.md",
                roadmap_index::run_roadmap_index(&r, check, cli.format == "json"),
            )
        }
        Commands::AiManifest { root, check } => {
            let r = resolve_root(root);
            (
                "ai-manifest",
                "manifests",
                ai_manifest::run_ai_manifest(&r, check, cli.format == "json"),
            )
        }
    };

    if cli.format == "json" {
        match &result {
            Ok(()) => {
                let json = serde_json::json!({
                    "status": "clean",
                    "subcommand": subcommand,
                    "target": target,
                    "violations": 0
                });
                println!("{}", serde_json::to_string_pretty(&json).unwrap());
            }
            Err((msg, code)) => {
                let json = serde_json::json!({
                    "status": "violation",
                    "subcommand": subcommand,
                    "target": target,
                    "violations": 1,
                    "message": msg,
                    "exit_code": code
                });
                println!("{}", serde_json::to_string_pretty(&json).unwrap());
            }
        }
    } else if let Err((msg, _)) = &result {
        if msg.starts_with("VIOLATION:")
            || msg.starts_with("Error:")
            || msg.starts_with("generate-metal-vs-hosted:")
            || msg.contains("ADR SSOT consistency check failed:")
        {
            eprintln!("{msg}");
        } else {
            eprintln!("Error: generate-{subcommand}: {msg}");
        }
    }

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err((_, code)) => ExitCode::from(code as u8),
    }
}
