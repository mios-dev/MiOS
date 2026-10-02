// AI-hint: Integration tests for the mios-install CLI -- plan shape, SSOT-sourced values, and every refusal path that must never reach podman.
// AI-related: tools/native/mios-install/src/main.rs, tools/native/mios-install/src/lib.rs
// AI-functions: run, fixture

use std::fs;
use std::path::Path;
use std::process::Command;

fn run(args: &[&str]) -> (i32, String) {
    let out = Command::new(env!("CARGO_BIN_EXE_mios-install"))
        .args(args)
        // SSOT values arrive through the environment first, as from a unit.
        .env("MIOS_IMAGE_REF", "registry.example/mios:test")
        .env("MIOS_BOOTC_INSTALL_BOUND_IMAGES", "stored")
        .env("MIOS_BOOTC_INSTALL_ROOT_MIN_GB", "80")
        .env("MIOS_LOCAL_TAG", "localhost/mios:test")
        .output()
        .unwrap_or_else(|e| panic!("{e}"));
    let mut s = String::from_utf8_lossy(&out.stdout).to_string();
    s.push_str(&String::from_utf8_lossy(&out.stderr));
    (out.status.code().unwrap_or(-1), s)
}

fn fixture(sys: &Path, efi: bool) {
    let d = sys.join("block/vdz");
    fs::create_dir_all(d.join("queue")).unwrap_or_else(|e| panic!("{e}"));
    fs::create_dir_all(d.join("device")).unwrap_or_else(|e| panic!("{e}"));
    fs::write(
        d.join("size"),
        format!("{}", 200u64 * 1024 * 1024 * 1024 / 512),
    )
    .unwrap_or_else(|e| panic!("{e}"));
    fs::write(d.join("queue/rotational"), "0").unwrap_or_else(|e| panic!("{e}"));
    if efi {
        fs::create_dir_all(sys.join("firmware/efi")).unwrap_or_else(|e| panic!("{e}"));
    }
}

#[test]
fn a_mock_dry_run_plans_the_images_own_bootc_on_the_best_disk() {
    let (code, out) = run(&["disk", "--auto-select", "--mock", "--dry-run", "--json"]);
    assert_eq!(code, 0, "{out}");
    let v: serde_json::Value = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out}"));
    assert_eq!(v["image_ref"], "registry.example/mios:test");
    assert_eq!(v["target"]["device_path"], "/dev/nvme0n1");
    assert_eq!(v["executed"], false);
    let cmd: Vec<&str> = v["command"]
        .as_array()
        .unwrap_or_else(|| panic!("{out}"))
        .iter()
        .filter_map(|s| s.as_str())
        .collect();
    assert_eq!(&cmd[..2], ["podman", "run"]);
    assert!(cmd.join(" ").contains("registry.example/mios:test bootc install to-disk --wipe --bound-images stored /dev/nvme0n1"));
}

#[test]
fn the_disk_backing_the_running_system_is_refused() {
    let (code, out) = run(&["disk", "--target-disk", "/dev/sdb", "--mock", "--json"]);
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("backs the running system"), "{out}");
}

#[test]
fn a_real_install_without_yes_is_refused_before_podman() {
    let t = tempfile::tempdir().unwrap_or_else(|e| panic!("{e}"));
    fixture(t.path(), true);
    let sys = t.path().to_string_lossy().to_string();
    let (code, out) = run(&["disk", "--target-disk", "vdz", "--sysfs", &sys]);
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("pass --yes to confirm"), "{out}");
}

#[test]
fn legacy_bios_is_refused_unless_forced() {
    let t = tempfile::tempdir().unwrap_or_else(|e| panic!("{e}"));
    fixture(t.path(), false);
    let sys = t.path().to_string_lossy().to_string();
    let (code, out) = run(&["disk", "--auto-select", "--sysfs", &sys, "--dry-run"]);
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("UEFI"), "{out}");
    let (code, out) = run(&[
        "disk",
        "--auto-select",
        "--sysfs",
        &sys,
        "--dry-run",
        "--force",
    ]);
    assert_eq!(code, 0, "{out}");
    assert!(out.contains("/dev/vdz"), "{out}");
}

#[test]
fn a_filesystem_bootc_does_not_support_is_a_usage_error() {
    let (code, out) = run(&["disk", "--auto-select", "--mock", "--filesystem", "zfs"]);
    assert_eq!(code, 2, "{out}");
}

#[test]
fn the_filesystem_flag_is_passed_only_when_given() {
    let (_, out) = run(&[
        "disk",
        "--auto-select",
        "--mock",
        "--dry-run",
        "--filesystem",
        "btrfs",
    ]);
    assert!(
        out.contains("--bound-images stored --filesystem btrfs /dev/nvme0n1"),
        "{out}"
    );
}

#[test]
fn existing_root_plans_over_the_running_system_and_needs_yes() {
    let t = tempfile::tempdir().unwrap_or_else(|e| panic!("{e}"));
    fixture(t.path(), true);
    let sys = t.path().to_string_lossy().to_string();
    let (code, out) = run(&[
        "existing-root",
        "--sysfs",
        &sys,
        "--dry-run",
        "--cleanup",
        "--json",
    ]);
    assert_eq!(code, 0, "{out}");
    let v: serde_json::Value = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out}"));
    let cmd = v["command"]
        .as_array()
        .unwrap_or_else(|| panic!("{out}"))
        .iter()
        .filter_map(|s| s.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    assert!(cmd.contains("-v /:/target"), "{cmd}");
    assert!(cmd.ends_with("registry.example/mios:test bootc install to-existing-root --acknowledge-destructive --bound-images stored --cleanup"), "{cmd}");
    let (code, out) = run(&["existing-root", "--sysfs", &sys]);
    assert_eq!(code, 1, "{out}");
    assert!(out.contains("pass --yes to confirm"), "{out}");
}

#[test]
fn disk_flags_are_refused_for_existing_root_and_vice_versa() {
    assert_eq!(run(&["existing-root", "--target-disk", "/dev/sda"]).0, 2);
    assert_eq!(run(&["disk", "--auto-select", "--mock", "--cleanup"]).0, 2);
}

#[test]
fn an_offline_install_loads_the_archive_and_tracks_the_registry_image() {
    let (code, out) = run(&[
        "disk",
        "--auto-select",
        "--mock",
        "--dry-run",
        "--json",
        "--source",
        "oci-archive:/mnt/mios-repo/mios-latest.tar",
    ]);
    assert_eq!(code, 0, "{out}");
    let v: serde_json::Value = serde_json::from_str(&out).unwrap_or_else(|e| panic!("{e}: {out}"));
    assert_eq!(v["preload"][0][0], "podman");
    assert_eq!(v["preload"][0][3], "/mnt/mios-repo/mios-latest.tar");
    let cmd = v["command"]
        .as_array()
        .unwrap_or_else(|| panic!("{out}"))
        .iter()
        .filter_map(|s| s.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    assert!(
        cmd.contains("localhost/mios:test bootc install to-disk"),
        "{cmd}"
    );
    assert!(
        cmd.ends_with("--target-imgref registry.example/mios:test /dev/nvme0n1"),
        "{cmd}"
    );
    assert_eq!(
        run(&["disk", "--auto-select", "--mock", "--source", "docker://x"]).0,
        2
    );
}
