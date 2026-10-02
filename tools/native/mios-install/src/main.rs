// AI-hint: Rust CLI entry point for mios-install -- installs [image].ref to a disk or over the running root through the image's own bootc.
// AI-related: tools/native/mios-install/src/lib.rs, usr/share/mios/mios.toml, usr/libexec/mios/deploy/baremetal_install.py
// AI-functions: main, run, parse, ssot

#![forbid(unsafe_code)]
#![warn(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

use mios_install::{
    boot_disks, default_sys, loaded_ref, mock_disks, plan, plan_existing_root, plan_offline, rank,
    scan, select, uefi, Source,
};
use mios_resolver::runtime;
use std::path::PathBuf;
use std::process::{Command, ExitCode};

const USAGE: &str = "usage: mios-install disk [--target-disk DEV | --auto-select] [--image-ref REF]
                         [--source oci-archive:PATH] [--filesystem xfs|ext4|btrfs]
                         [--yes] [--force] [--dry-run] [--mock] [--json]
       mios-install existing-root [--image-ref REF] [--cleanup] [--yes] [--force] [--dry-run] [--json]

Installs [image].ref from mios.toml by running the image's own bootc in a
privileged podman container. `disk` erases DEV (`bootc install to-disk --wipe`);
a disk backing the running system is always refused. `existing-root` installs
over the running system (`bootc install to-existing-root`), which keeps running
until reboot; --cleanup removes the previous install's files at first boot.
--source installs offline: the archive is loaded with podman, the loaded image
([image].local_tag) runs bootc, and the host tracks [image].ref for upgrades.
A real install needs --yes. --force only skips the UEFI check.
";

#[derive(Default)]
struct Args {
    verb: String,
    cleanup: bool,
    source: Option<Source>,
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
        Some(v @ ("disk" | "existing-root")) => a.verb = v.to_string(),
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
            "--source" => a.source = Some(Source::parse(&value("--source")?)?),
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
            "--cleanup" => a.cleanup = true,
            "--yes" => a.yes = true,
            "--force" => a.force = true,
            "--dry-run" => a.dry_run = true,
            "--mock" => a.mock = true,
            "--json" => a.json = true,
            "-h" | "--help" => return Err(String::new()),
            other => return Err(format!("unknown option {other:?}")),
        }
    }
    let disk_only =
        a.target.is_some() || a.auto || a.filesystem.is_some() || a.mock || a.source.is_some();
    if a.verb == "existing-root" && disk_only {
        return Err(
            "--target-disk, --auto-select, --filesystem, --source and --mock apply to `disk` only"
                .into(),
        );
    }
    if a.verb == "disk" && a.cleanup {
        return Err("--cleanup applies to `existing-root` only".into());
    }
    Ok(a)
}

/// Run the planned command; a real install needs --yes.
fn execute(command: &[String], yes: bool, what: String) -> Result<(), String> {
    if !yes {
        return Err(format!("{what}; pass --yes to confirm"));
    }
    let status = Command::new(&command[0])
        .args(&command[1..])
        .status()
        .map_err(|e| format!("could not run {}: {e}", command[0]))?;
    if !status.success() {
        return Err(format!("{} exited with {status}", command.join(" ")));
    }
    Ok(())
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
    let run_it = !a.dry_run && !a.mock;
    if a.verb == "existing-root" {
        if !uefi(&sys) && !a.force {
            return Err(
                "MiOS requires UEFI firmware (/sys/firmware/efi is absent); --force skips this check"
                    .into(),
            );
        }
        let command = plan_existing_root(&image, &bound, a.cleanup);
        if run_it {
            execute(
                &command,
                a.yes,
                format!("this replaces the running system with {image} at next boot"),
            )?;
        }
        return Ok(serde_json::json!({
            "status": "success",
            "mode": "existing-root",
            "image_ref": image,
            "bound_images": bound,
            "cleanup": a.cleanup,
            "command": command,
            "executed": run_it,
            "dry_run": a.dry_run,
        }));
    }
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
    let p = match &a.source {
        Some(src) => plan_offline(
            &image,
            src,
            &ssot("MIOS_LOCAL_TAG")?,
            target,
            a.filesystem.as_deref(),
            &bound,
            is_uefi,
        ),
        None => plan(&image, target, a.filesystem.as_deref(), &bound, is_uefi),
    };

    if run_it {
        let mut command = p.command.clone();
        // The archive is loaded only once the erase is confirmed, and the
        // install runs the image podman reports, not an assumed tag.
        if a.yes {
            if let Some(load) = p.preload.first() {
                let out = Command::new(&load[0])
                    .args(&load[1..])
                    .output()
                    .map_err(|e| format!("could not run {}: {e}", load[0]))?;
                let text = String::from_utf8_lossy(&out.stdout).to_string();
                if !out.status.success() {
                    return Err(format!("{} exited with {}", load.join(" "), out.status));
                }
                let got = loaded_ref(&text)
                    .ok_or_else(|| format!("{} reported no loaded image", load.join(" ")))?;
                let planned = ssot("MIOS_LOCAL_TAG")?;
                for part in command.iter_mut() {
                    if *part == planned {
                        *part = got.clone();
                    }
                }
            }
        }
        execute(
            &command,
            a.yes,
            format!(
                "this ERASES {} ({}, {} GB, serial {})",
                p.target.device_path,
                p.target.model,
                p.target.size_bytes / (1024 * 1024 * 1024),
                p.target.serial
            ),
        )?;
    }
    let mut v = serde_json::to_value(&p).map_err(|e| e.to_string())?;
    if let Some(o) = v.as_object_mut() {
        o.insert("status".into(), "success".into());
        o.insert("mode".into(), "disk".into());
        o.insert("executed".into(), run_it.into());
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
                    v["target"]["device_path"]
                        .as_str()
                        .unwrap_or("the running system"),
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
