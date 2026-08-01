// AI-hint: Entry point for the MiOS daemon native workspace (WS-LANG)
// AI-related: Containerfile, automation/98-drift-checks.sh

#![warn(clippy::unwrap_used, clippy::panic, clippy::todo)]

mod drift;

// AI-related: Containerfile, automation/98-drift-checks.sh

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "miosd")]
#[command(about = "MiOS native daemon and toolbox", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Run structural drift checks across the repository
    DriftCheck {
        /// Optional root directory to check
        #[arg(long)]
        root: Option<String>,
        /// Advisory mode (exit 0 on failure)
        #[arg(long)]
        soft: bool,
    },
    /// Scaffold a new file from a template
    Scaffold {
        /// Type of the template
        template_type: String,
        /// Name of the new file
        name: String,
    },
    /// Run or plan MiOS image build phases
    Build {
        /// Target phase or mode
        #[arg(default_value = "all")]
        phase: String,
        /// Print execution plan without running build phases
        #[arg(long)]
        plan: bool,
        /// Print raw script list for build orchestrator
        #[arg(long)]
        list: bool,
    },
    /// Resolve configuration parameters
    Resolve {
        /// Output in shell export format
        #[arg(long)]
        shell: bool,
    },
    /// Render ports from mios.toml to install.env with stack_id offset
    RenderPorts {
        /// Input TOML file path
        #[arg(long, default_value = "/usr/share/mios/mios.toml")]
        toml: String,
        /// Target install.env path
        #[arg(long, default_value = "/etc/mios/install.env")]
        out: String,
    },
    /// Render Quadlet container placeholders (${MIOS_*}) across config directories
    RenderQuadlets {
        /// Target directories to scan and render
        #[arg(long)]
        dirs: Vec<String>,
    },
    /// Render kernel arguments from mios.toml [kargs] to kargs.d/*.toml
    RenderKargs {
        /// Input TOML file path
        #[arg(long, default_value = "/usr/share/mios/mios.toml")]
        toml: String,
        /// kargs.d directory path
        #[arg(long, default_value = "/usr/lib/bootc/kargs.d")]
        kargs_dir: String,
    },
}

fn run_render_kargs(toml_path: &str, kargs_dir: &str) -> Result<(), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(toml_path).unwrap_or_default();
    let mut iommu = "on".to_string();
    let mut vfio_ids = String::new();
    let mut hugepages = String::new();
    let mut isolcpus = String::new();
    let mut nohz_full = String::new();
    let mut rcu_nocbs = String::new();
    let mut thp = String::new();

    let mut in_kargs = false;
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') {
            in_kargs = trimmed == "[kargs]";
            continue;
        }
        if in_kargs && trimmed.contains('=') {
            let parts: Vec<&str> = trimmed.splitn(2, '=').collect();
            let key = parts[0].trim();
            let val = parts[1]
                .split('#')
                .next()
                .unwrap_or("")
                .trim()
                .trim_matches('"');
            match key {
                "iommu" => iommu = val.to_string(),
                "vfio_ids" => vfio_ids = val.to_string(),
                "hugepages" => hugepages = val.to_string(),
                "isolcpus" => isolcpus = val.to_string(),
                "nohz_full" => nohz_full = val.to_string(),
                "rcu_nocbs" => rcu_nocbs = val.to_string(),
                "THP" => thp = val.to_string(),
                _ => {}
            }
        }
    }

    let vfio_path = std::path::Path::new(kargs_dir).join("01-mios-vfio.toml");
    if vfio_path.exists() {
        let mut kargs_list: Vec<String> = vec![];
        if iommu == "intel" {
            kargs_list.extend(["intel_iommu=on", "iommu=pt"].iter().map(|s| s.to_string()));
        } else if iommu == "amd" {
            kargs_list.extend(["amd_iommu=on", "iommu=pt"].iter().map(|s| s.to_string()));
        } else if iommu == "on" {
            kargs_list.extend(
                ["intel_iommu=on", "amd_iommu=on", "iommu=pt"]
                    .iter()
                    .map(|s| s.to_string()),
            );
        }

        if !vfio_ids.is_empty() {
            kargs_list.push(format!("vfio-pci.ids={}", vfio_ids));
        }

        let mut lines = vec![
            "# AI-hint: Configures kernel arguments for IOMMU, VFIO-PCI, and nested virtualization to enable hardware passthrough and virtualization features in the MiOS boot process.".to_string(),
            "# Generated from mios.toml [kargs] SSOT".to_string(),
            "kargs = [".to_string(),
        ];
        let len = kargs_list.len();
        for (idx, item) in kargs_list.iter().enumerate() {
            if idx + 1 == len {
                lines.push(format!("    \"{}\"", item));
            } else {
                lines.push(format!("    \"{}\",", item));
            }
        }
        lines.push("]".to_string());
        std::fs::write(&vfio_path, lines.join("\n") + "\n")?;
    }

    let mut custom_kargs = vec![];
    if !hugepages.is_empty() {
        custom_kargs.push(format!("hugepages={}", hugepages));
    }
    if !isolcpus.is_empty() {
        custom_kargs.push(format!("isolcpus={}", isolcpus));
    }
    if !nohz_full.is_empty() {
        custom_kargs.push(format!("nohz_full={}", nohz_full));
    }
    if !rcu_nocbs.is_empty() {
        custom_kargs.push(format!("rcu_nocbs={}", rcu_nocbs));
    }
    if !thp.is_empty() {
        custom_kargs.push(format!("transparent_hugepage={}", thp));
    }

    let custom_path = std::path::Path::new(kargs_dir).join("99-mios-kargs.toml");
    if !custom_kargs.is_empty() {
        let mut lines = vec![
            "# AI-hint: Configures custom kernel arguments from mios.toml [kargs] SSOT."
                .to_string(),
            "# Generated custom kernel arguments from mios.toml [kargs] SSOT".to_string(),
            "kargs = [".to_string(),
        ];
        let len = custom_kargs.len();
        for (idx, item) in custom_kargs.iter().enumerate() {
            if idx + 1 == len {
                lines.push(format!("    \"{}\"", item));
            } else {
                lines.push(format!("    \"{}\",", item));
            }
        }
        lines.push("]".to_string());
        std::fs::write(&custom_path, lines.join("\n") + "\n")?;
    } else if custom_path.exists() {
        let _ = std::fs::remove_file(&custom_path);
    }

    Ok(())
}

fn run_render_quadlets(dirs: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let target_dirs = if dirs.is_empty() {
        vec![
            "/etc/containers/systemd".to_string(),
            "/etc/containers/systemd/users".to_string(),
            "/usr/share/containers/systemd".to_string(),
            "/usr/share/containers/systemd/users".to_string(),
            "/etc/mios".to_string(),
            "/usr/share/mios/kb".to_string(),
            "/usr/lib/systemd/system/cockpit.socket.d".to_string(),
            "/usr/lib/systemd/system".to_string(),
        ]
    } else {
        dirs.to_vec()
    };

    let re_default = regex::Regex::new(r"\$\{([A-Z_][A-Z0-9_]*):-([^}]*)\}")?;
    let re_plain = regex::Regex::new(r"\$\{([A-Z_][A-Z0-9_]*)\}")?;

    for dir_path in target_dirs {
        let path = std::path::Path::new(&dir_path);
        if !path.exists() {
            continue;
        }

        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let fpath = entry.path();
                if fpath.is_file() {
                    if let Ok(content) = std::fs::read_to_string(&fpath) {
                        if !content.contains("${MIOS_") {
                            continue;
                        }

                        let mut rendered = re_default
                            .replace_all(&content, |caps: &regex::Captures| {
                                let var_name = &caps[1];
                                let default_val = &caps[2];
                                std::env::var(var_name).unwrap_or_else(|_| default_val.to_string())
                            })
                            .to_string();

                        rendered = re_plain
                            .replace_all(&rendered, |caps: &regex::Captures| {
                                let var_name = &caps[1];
                                std::env::var(var_name).unwrap_or_else(|_| caps[0].to_string())
                            })
                            .to_string();

                        if rendered != content {
                            let _ = std::fs::write(&fpath, rendered);
                        }
                    }
                }
            }
        }
    }

    Ok(())
}

fn run_render_ports(toml_path: &str, out_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(toml_path).unwrap_or_default();
    let mut in_ports = false;
    let mut stack_id: u32 = 0;
    let mut entries: Vec<(String, String)> = Vec::new();

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') {
            in_ports = trimmed == "[ports]";
            continue;
        }
        if in_ports && trimmed.contains('=') {
            let parts: Vec<&str> = trimmed.splitn(2, '=').collect();
            let key = parts[0].trim();
            let val = parts[1]
                .split('#')
                .next()
                .unwrap_or("")
                .trim()
                .trim_matches('"');

            if key == "stack_id" {
                stack_id = val.parse().unwrap_or(0);
            } else {
                entries.push((key.to_uppercase(), val.to_string()));
            }
        }
    }

    let mut out_lines = Vec::new();
    if let Ok(existing) = std::fs::read_to_string(out_path) {
        for line in existing.lines() {
            if !line.starts_with("MIOS_PORT_") {
                out_lines.push(line.to_string());
            }
        }
    }

    for (key, val) in entries {
        let final_val = if let Ok(num) = val.parse::<u32>() {
            if num == 53 {
                "53".to_string()
            } else {
                (num + (stack_id * 10000)).to_string()
            }
        } else {
            val
        };
        out_lines.push(format!("MIOS_PORT_{}={}", key, final_val));
    }

    if let Some(parent) = std::path::Path::new(out_path).parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    std::fs::write(out_path, out_lines.join("\n") + "\n")?;
    Ok(())
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::DriftCheck { root, soft } => {
            let root_dir = root.as_deref().unwrap_or(".");
            drift::run_checks(root_dir, *soft);
        }
        Commands::Scaffold {
            template_type,
            name,
        } => {
            println!("[miosd] Scaffolding {} as {}...", template_type, name);
            // TODO: Fold mios-new Python logic into this Rust command.
            println!("[miosd] (Stub) Scaffolding complete.");
        }
        Commands::Build { phase, plan, list } => {
            if let Err(e) = mios_build::run_build(phase, *plan, *list) {
                eprintln!("[miosd] Build error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::Resolve { shell } => {
            let config = mios_config::MiosConfig::load_default().unwrap_or_default();
            if *shell {
                println!("export MIOS_USER=\"{}\"", config.identity.username);
                println!("export MIOS_USER_FULLNAME=\"{}\"", config.identity.fullname);
                println!("export MIOS_HOSTNAME=\"{}\"", config.identity.hostname);
                println!("export MIOS_USER_SHELL=\"{}\"", config.identity.shell);
                println!("export MIOS_VERSION=\"{}\"", config.meta.mios_version);
            } else {
                println!("{:#?}", config);
            }
        }
        Commands::RenderPorts { toml, out } => {
            if let Err(e) = run_render_ports(toml, out) {
                eprintln!("[miosd] Render ports error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RenderQuadlets { dirs } => {
            if let Err(e) = run_render_quadlets(dirs) {
                eprintln!("[miosd] Render quadlets error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RenderKargs { toml, kargs_dir } => {
            if let Err(e) = run_render_kargs(toml, kargs_dir) {
                eprintln!("[miosd] Render kargs error: {}", e);
                std::process::exit(1);
            }
        }
    }
}
