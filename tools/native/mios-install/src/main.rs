// AI-hint: Rust CLI entry point for mios-install -- `mios-install disk` installs [image].ref to a disk through the image's own bootc.
// AI-related: tools/native/mios-install/src/lib.rs, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
// AI-functions: main, run, parse, ssot

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use mios_install::{boot_disks, default_sys, mock_disks, plan, rank, scan, select, uefi};
use mios_resolver::runtime;
use std::path::PathBuf;
use std::process::{Command, ExitCode};

const USAGE: &str = "usage: mios-install disk [--target-disk DEV | --auto-select] [--image-ref REF]
                         [--filesystem xfs|ext4|btrfs] [--yes] [--force] [--dry-run] [--mock] [--json]

Installs [image].ref from mios.toml onto DEV by running the image's own bootc
(`bootc install to-disk --wipe`) in a privileged podman container. The disk is
erased: a real install needs --yes. --force only skips the UEFI check; a disk
backing the running system is always refused.
";

#[derive(Default)]
struct Args {
    target: Option<String>,
    auto: bool,
    image: Option<String>,
    filesystem: Option<String>,
    yes: bool,
    force: bool,
    dry_run: bool,
    mock: bool,
    json: bool,
    sys: Option<PathBuf>,
}

fn parse(argv: &[String]) -> Result<Args, String> {
    let mut a = Args::default();
    let mut it = argv.iter();
    match it.next().map(String::as_str) {
        Some("disk") => {}
        Some("-h" | "--help") => return Err(String::new()),
        Some(other) => return Err(format!("unknown verb {other:?}")),
        None => return Err("a verb is required".into()),
    }
    while let Some(arg) = it.next() {
        let mut value = |flag: &str| {
            it.next()
                .cloned()
                .ok_or_else(|| format!("{flag} needs a value"))
        };
        match arg.as_str() {
            "--target-disk" => a.target = Some(value("--target-disk")?),
            "--image-ref" => a.image = Some(value("--image-ref")?),
            "--filesystem" => {
                let fs = value("--filesystem")?;
                if !matches!(fs.as_str(), "xfs" | "ext4" | "btrfs") {
                    return Err(format!(
                        "--filesystem {fs:?} is not one of bootc's xfs | ext4 | btrfs"
                    ));
                }
                a.filesystem = Some(fs);
            }
            // Test hook: read a fixture tree instead of /sys.
            "--sysfs" => a.sys = Some(PathBuf::from(value("--sysfs")?)),
            "--auto-select" => a.auto = true,
            "--yes" => a.yes = true,
            "--force" => a.force = true,
            "--dry-run" => a.dry_run = true,
            "--mock" => a.mock = true,
            "--json" => a.json = true,
            "-h" | "--help" => return Err(String::new()),
            other => return Err(format!("unknown option {other:?}")),
        }
    }
    Ok(a)
}

/// A value from the environment or the layered mios.toml; never a literal.
fn ssot(name: &str) -> Result<String, String> {
    runtime::require(name).map_err(|e| e.to_string())
}

fn run(a: &Args) -> Result<serde_json::Value, String> {
    let image = match &a.image {
        Some(i) => i.clone(),
        None => ssot("MIOS_IMAGE_REF")?,
    };
    let bound = ssot("MIOS_BOOTC_INSTALL_BOUND_IMAGES")?;
    if !matches!(bound.as_str(), "stored" | "pull") {
        return Err(format!(
            "[bootc_install].bound_images = {bound:?} is not bootc's stored | pull"
        ));
    }
    let min_gb: u64 = ssot("MIOS_BOOTC_INSTALL_ROOT_MIN_GB")?
        .parse()
        .map_err(|_| "[bootc_install].root_min_gb is not a whole number of GB".to_string())?;
    let min_bytes = min_gb * 1024 * 1024 * 1024;

    let sys = a.sys.clone().unwrap_or_else(default_sys);
    let (disks, boot, is_uefi) = if a.mock {
        let (d, b) = mock_disks();
        (d, b, true)
    } else {
        let mountinfo = std::fs::read_to_string("/proc/self/mountinfo").unwrap_or_default();
        (scan(&sys), boot_disks(&sys, &mountinfo), uefi(&sys))
    };
    if !is_uefi && !a.force {
        return Err(
            "MiOS requires UEFI firmware (/sys/firmware/efi is absent); --force skips this check"
                .into(),
        );
    }
    let ranked = rank(disks, &boot, min_bytes);
    let target = select(&ranked, a.target.as_deref(), a.auto)?;
    let p = plan(&image, target, a.filesystem.as_deref(), &bound, is_uefi);

    let execute = !a.dry_run && !a.mock;
    if execute {
        if !a.yes {
            return Err(format!(
                "this ERASES {} ({}, {} GB, serial {}); pass --yes to confirm",
                p.target.device_path,
                p.target.model,
                p.target.size_bytes / (1024 * 1024 * 1024),
                p.target.serial
            ));
        }
        let status = Command::new(&p.command[0])
            .args(&p.command[1..])
            .status()
            .map_err(|e| format!("could not run {}: {e}", p.command[0]))?;
        if !status.success() {
            return Err(format!("bootc install exited with {status}"));
        }
    }
    let mut v = serde_json::to_value(&p).map_err(|e| e.to_string())?;
    if let Some(o) = v.as_object_mut() {
        o.insert("status".into(), "success".into());
        o.insert("executed".into(), execute.into());
        o.insert("dry_run".into(), a.dry_run.into());
        o.insert("mock".into(), a.mock.into());
    }
    Ok(v)
}

fn main() -> ExitCode {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    let args = match parse(&argv) {
        Ok(a) => a,
        Err(e) if e.is_empty() => {
            print!("{USAGE}");
            return ExitCode::SUCCESS;
        }
        Err(e) => {
            eprint!("mios-install: {e}\n{USAGE}");
            return ExitCode::from(2);
        }
    };
    match run(&args) {
        Ok(v) => {
            if args.json {
                println!("{}", serde_json::to_string_pretty(&v).unwrap_or_default());
            } else {
                let verb = if v["executed"] == true {
                    "Installed"
                } else {
                    "Planned"
                };
                println!(
                    "[mios-install] {verb} {} on {}: {}",
                    v["image_ref"].as_str().unwrap_or_default(),
                    v["target"]["device_path"].as_str().unwrap_or_default(),
                    v["command"]
                        .as_array()
                        .map(|c| c
                            .iter()
                            .filter_map(|s| s.as_str())
                            .collect::<Vec<_>>()
                            .join(" "))
                        .unwrap_or_default()
                );
            }
            ExitCode::SUCCESS
        }
        Err(e) => {
            if args.json {
                println!("{}", serde_json::json!({ "status": "error", "error": e }));
            } else {
                eprintln!("mios-install: {e}");
            }
            ExitCode::from(1)
        }
    }
}
