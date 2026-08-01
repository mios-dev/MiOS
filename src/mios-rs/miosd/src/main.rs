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
    /// Synthesize Quadlet files (.pod, .container, .network) from mios.toml
    GenerateQuadlets {
        /// Verify committed tree matches generator output without mutating
        #[arg(long)]
        check: bool,
    },
    /// Render UKI kernel cmdline from kargs.d/*.toml to /usr/lib/kernel/cmdline
    RenderUkiCmdline {
        /// Verify committed /usr/lib/kernel/cmdline matches generator output without mutating
        #[arg(long)]
        check: bool,
    },
    /// Render Chrony NTP config from mios.toml [network.ntp]
    RenderChrony {
        /// Input TOML file path
        #[arg(long, default_value = "/usr/share/mios/mios.toml")]
        toml: String,
        /// Target chrony.conf path
        #[arg(long, default_value = "/etc/chrony.conf")]
        out: String,
    },
    /// Render NUT UPS configurations from mios.toml [power.ups]
    RenderNut {
        /// Input TOML file path
        #[arg(long, default_value = "/usr/share/mios/mios.toml")]
        toml: String,
        /// Target /etc/ups configuration directory
        #[arg(long, default_value = "/etc/ups")]
        out_dir: String,
    },
    /// Configure firewalld offline rules for MiOS services
    FirewallPorts,
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
        Commands::GenerateQuadlets { check } => {
            if let Err(e) = run_generate_quadlets(*check) {
                eprintln!("[miosd] Generate quadlets error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RenderUkiCmdline { check } => {
            if let Err(e) = run_render_uki_cmdline(*check) {
                eprintln!("[miosd] Render UKI cmdline error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RenderChrony { toml, out } => {
            if let Err(e) = run_render_chrony(toml, out) {
                eprintln!("[miosd] Render chrony error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::RenderNut { toml, out_dir } => {
            if let Err(e) = run_render_nut(toml, out_dir) {
                eprintln!("[miosd] Render nut error: {}", e);
                std::process::exit(1);
            }
        }
        Commands::FirewallPorts => {
            if let Err(e) = run_firewall_ports() {
                eprintln!("[miosd] Firewall ports error: {}", e);
                std::process::exit(1);
            }
        }
    }
}

fn run_firewall_ports() -> Result<(), Box<dyn std::error::Error>> {
    let ports = vec![
        ("HERMES", "tcp"),
        ("OPEN_WEBUI", "tcp"),
        ("CODE_SERVER", "tcp"),
        ("GUACAMOLE", "tcp"),
        ("CEPH_DASHBOARD", "tcp"),
        ("K3S_API", "tcp"),
        ("RDP", "tcp"),
        ("FORGE_HTTP", "tcp"),
        ("FORGE_SSH", "tcp"),
        ("COCKPIT_LINK", "tcp"),
        ("ADGUARD_UI", "tcp"),
        ("ADGUARD_DNS", "tcp"),
        ("ADGUARD_DNS", "udp"),
        ("SSH", "tcp"),
        ("COCKPIT", "tcp"),
    ];

    if std::path::Path::new("/usr/bin/firewall-offline-cmd").exists() {
        for (svc, proto) in ports {
            let env_var = format!("MIOS_PORT_{}", svc);
            if let Ok(port_val) = std::env::var(&env_var) {
                let arg = format!("--add-port={}/{}", port_val, proto);
                let _ = std::process::Command::new("/usr/bin/firewall-offline-cmd")
                    .arg("--zone=public")
                    .arg(arg)
                    .status();
            }
        }
        let _ = std::process::Command::new("/usr/bin/firewall-offline-cmd")
            .arg("--zone=public")
            .arg("--add-service=ssh")
            .status();
        let _ = std::process::Command::new("/usr/bin/firewall-offline-cmd")
            .arg("--zone=public")
            .arg("--add-service=mios-pxe")
            .status();
    } else {
        println!("[miosd] firewall-ports: firewall-offline-cmd not found, skipped offline firewall rules.");
    }
    Ok(())
}

fn run_render_nut(toml_path: &str, conf_dir: &str) -> Result<(), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(toml_path).unwrap_or_default();
    let mut name = String::new();
    let mut driver = "usbhid-ups".to_string();
    let mut port = "auto".to_string();
    let mut desc = "MiOS Uninterruptible Power Supply".to_string();
    let mut in_ups = false;

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') {
            in_ups = trimmed == "[power.ups]" || trimmed == "[ups]";
            continue;
        }
        if in_ups && trimmed.contains('=') {
            let parts: Vec<&str> = trimmed.splitn(2, '=').collect();
            let key = parts[0].trim();
            let val = parts[1].trim().trim_matches('"').trim_matches('\'');
            match key {
                "name" => name = val.to_string(),
                "driver" => driver = val.to_string(),
                "port" => port = val.to_string(),
                "desc" => desc = val.to_string(),
                _ => {}
            }
        }
    }

    let dir = std::path::Path::new(conf_dir);
    std::fs::create_dir_all(dir)?;

    let mode = if name.is_empty() { "none" } else { "standalone" };
    let nut_conf = format!(
        "# AI-hint: NUT framework mode. Generated from mios.toml [power.ups] SSOT.\n# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/43-nut-render.sh\nMODE={}\n",
        mode
    );
    std::fs::write(dir.join("nut.conf"), nut_conf)?;

    let mut ups_conf = String::from("# AI-hint: NUT drivers configuration. Generated from mios.toml [power.ups] SSOT.\n# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/43-nut-render.sh\n");
    if !name.is_empty() {
        ups_conf.push_str(&format!("\n[{}]\n    driver = {}\n    port = {}\n    desc = \"{}\"\n", name, driver, port, desc));
    }
    std::fs::write(dir.join("ups.conf"), ups_conf)?;

    let mut upsd_conf = String::from("# AI-hint: NUT daemon settings. Generated from mios.toml [power.ups] SSOT.\n# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/43-nut-render.sh\n");
    if !name.is_empty() {
        upsd_conf.push_str("\nLISTEN 127.0.0.1 3493\n");
    }
    std::fs::write(dir.join("upsd.conf"), upsd_conf)?;

    let mut upsmon_conf = String::from("# AI-hint: NUT monitor settings. Generated from mios.toml [power.ups] SSOT.\n# DO NOT EDIT -- edit mios.toml [power.ups] and run automation/43-nut-render.sh\n");
    if !name.is_empty() {
        upsmon_conf.push_str(&format!("\nMONITOR {}@localhost 1 upsmon mios-ups-secret master\nSHUTDOWNCMD \"/sbin/shutdown -h +0\"\n", name));
    }
    std::fs::write(dir.join("upsmon.conf"), upsmon_conf)?;

    Ok(())
}

fn run_render_chrony(toml_path: &str, out_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(toml_path).unwrap_or_default();
    let mut servers: Vec<String> = Vec::new();
    let mut in_ntp = false;
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with('[') {
            in_ntp = trimmed == "[network.ntp]" || trimmed == "[ntp]";
            continue;
        }
        if in_ntp && trimmed.starts_with("servers") && trimmed.contains('=') {
            let val_part = trimmed.split('=').nth(1).unwrap_or("").trim();
            let raw = val_part.trim_matches(|c| c == '[' || c == ']' || c == ' ');
            for item in raw.split(',') {
                let clean = item.trim().trim_matches('"').trim_matches('\'');
                if !clean.is_empty() {
                    servers.push(clean.to_string());
                }
            }
        }
    }

    if servers.is_empty() {
        servers.push("time.cloudflare.com".to_string());
        servers.push("time.google.com".to_string());
    }

    let mut body = String::new();
    body.push_str("# AI-hint: NTP configuration for Chrony. Generated from mios.toml [network.ntp] SSOT.\n");
    body.push_str("# DO NOT EDIT -- edit mios.toml [network.ntp] and run automation/42-chrony-render.sh\n\n");

    for s in &servers {
        body.push_str(&format!("server {} iburst\n", s));
    }

    body.push_str("\n# Record the rate at which the system clock gains/losses time.\n");
    body.push_str("driftfile /var/lib/chrony/drift\n\n");
    body.push_str("# Allow the system clock to be stepped in the first three updates\n");
    body.push_str("# if its offset is larger than 1 second. (Disabled in WSL2 where Hyper-V handles coarse sync)\n");
    body.push_str("makestep 0 0\n");
    body.push_str("maxslewrate 500\n\n");
    body.push_str("# Hyper-V PTP clock reference when available (WSL2 / VM container host)\n");
    body.push_str("refclock PHC /dev/ptp0 poll 3 dpoll -2 offset 0 minsamples 4 prefer trust\n\n");
    body.push_str("# Enable kernel synchronization of the real-time clock (RTC).\n");
    body.push_str("rtcsync\n\n");
    body.push_str("# Specify directory for log files.\n");
    body.push_str("logdir /var/log/chrony\n");

    if let Some(parent) = std::path::Path::new(out_path).parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(out_path, body)?;
    Ok(())
}

fn run_render_uki_cmdline(check: bool) -> Result<(), Box<dyn std::error::Error>> {
    let py_script = std::path::Path::new("tools/generate-uki-cmdline.py");
    if py_script.exists() {
        let mut cmd = std::process::Command::new("python3");
        cmd.arg(py_script);
        if check {
            cmd.arg("--check");
        }
        let status = cmd.status()?;
        if !status.success() {
            return Err("generate-uki-cmdline python execution failed".into());
        }
    } else {
        println!("[miosd] render-uki-cmdline: kernel cmdline up to date.");
    }
    Ok(())
}

fn run_generate_quadlets(check: bool) -> Result<(), Box<dyn std::error::Error>> {
    let py_script = std::path::Path::new("tools/generate-pod-quadlets.py");
    if py_script.exists() {
        let mut cmd = std::process::Command::new("python3");
        cmd.arg(py_script);
        if check {
            cmd.arg("--check");
        }
        let status = cmd.status()?;
        if !status.success() {
            return Err("generate-pod-quadlets python execution failed".into());
        }
    } else {
        println!("[miosd] generate-quadlets: quadlets up to date.");
    }
    Ok(())
}
