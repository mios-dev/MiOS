// AI-hint: Rust library for mios-install -- sysfs disk discovery, boot-disk and size safety gates, and the podman+bootc install plan.
// AI-related: tools/native/mios-install/src/main.rs, usr/share/mios/mios.toml, usr/lib/bootc/install/00-mios.toml
// AI-functions: scan, boot_disks, rank, select, plan, mock_disks

use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

const GIB: u64 = 1024 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Disk {
    pub device_path: String,
    pub name: String,
    pub model: String,
    pub serial: String,
    pub size_bytes: u64,
    pub bus_type: String,
    pub rotational: bool,
    pub is_removable: bool,
    pub is_current_boot: bool,
    pub score: u64,
    pub status: String,
}

fn read_trim(p: &Path) -> Option<String> {
    fs::read_to_string(p).ok().map(|s| s.trim().to_string())
}

/// Kernel block devices that are never install targets.
fn is_virtual(name: &str) -> bool {
    ["loop", "ram", "zram", "dm-", "sr", "md", "nbd", "fd"]
        .iter()
        .any(|p| name.starts_with(p))
}

fn bus_of(sys: &Path, name: &str) -> String {
    if name.starts_with("nvme") {
        return "nvme".into();
    }
    if name.starts_with("mmcblk") {
        return "mmc".into();
    }
    let link = fs::canonicalize(sys.join("block").join(name))
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();
    if link.contains("/usb") {
        "usb".into()
    } else if link.contains("/virtio") || name.starts_with("vd") {
        "virtio".into()
    } else {
        "sata".into()
    }
}

/// Every disk under `<sys>/block`, unranked.
pub fn scan(sys: &Path) -> Vec<Disk> {
    let mut out = Vec::new();
    let Ok(entries) = fs::read_dir(sys.join("block")) else {
        return out;
    };
    for e in entries.flatten() {
        let name = e.file_name().to_string_lossy().to_string();
        if is_virtual(&name) {
            continue;
        }
        let dir = sys.join("block").join(&name);
        let sectors: u64 = read_trim(&dir.join("size"))
            .and_then(|s| s.parse().ok())
            .unwrap_or(0);
        if sectors == 0 {
            continue;
        }
        let device = dir.join("device");
        out.push(Disk {
            device_path: format!("/dev/{name}"),
            model: read_trim(&device.join("model")).unwrap_or_default(),
            serial: read_trim(&device.join("serial"))
                .or_else(|| read_trim(&device.join("wwid")))
                .unwrap_or_default(),
            size_bytes: sectors * 512,
            bus_type: bus_of(sys, &name),
            rotational: read_trim(&dir.join("queue/rotational")).as_deref() == Some("1"),
            is_removable: read_trim(&dir.join("removable")).as_deref() == Some("1"),
            is_current_boot: false,
            score: 0,
            status: String::new(),
            name,
        });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    out
}

/// The whole disks under a block device: a partition's parent, and for
/// device-mapper (LVM, LUKS) every slave, recursively.
fn disks_under(sys: &Path, name: &str, acc: &mut Vec<String>) {
    let class = sys.join("class/block").join(name);
    let slaves = class.join("slaves");
    if let Ok(entries) = fs::read_dir(&slaves) {
        let mut any = false;
        for e in entries.flatten() {
            any = true;
            disks_under(sys, &e.file_name().to_string_lossy(), acc);
        }
        if any {
            return;
        }
    }
    let disk = if class.join("partition").exists() {
        fs::canonicalize(&class)
            .ok()
            .and_then(|p| p.parent().map(Path::to_path_buf))
            .and_then(|p| p.file_name().map(|n| n.to_string_lossy().to_string()))
    } else {
        Some(name.to_string())
    };
    if let Some(d) = disk {
        if !acc.contains(&d) {
            acc.push(d);
        }
    }
}

/// Disks backing the running system (its root, /boot, /sysroot or live
/// media), from a mountinfo-format file. Installing onto one is refused.
pub fn boot_disks(sys: &Path, mountinfo: &str) -> Vec<String> {
    let mut acc = Vec::new();
    for line in mountinfo.lines() {
        let fields: Vec<&str> = line.split_whitespace().collect();
        let Some(sep) = fields.iter().position(|f| *f == "-") else {
            continue;
        };
        let (Some(mnt), Some(src)) = (fields.get(4), fields.get(sep + 2)) else {
            continue;
        };
        if !matches!(
            *mnt,
            "/" | "/boot" | "/boot/efi" | "/sysroot" | "/run/initramfs/live"
        ) {
            continue;
        }
        if let Some(dev) = src.strip_prefix("/dev/") {
            let real = fs::canonicalize(Path::new("/dev").join(dev))
                .ok()
                .and_then(|p| p.file_name().map(|n| n.to_string_lossy().to_string()))
                .unwrap_or_else(|| dev.rsplit('/').next().unwrap_or(dev).to_string());
            disks_under(sys, &real, &mut acc);
        }
    }
    acc
}

/// Mark the boot disks and the too-small ones, and score the rest: NVMe >
/// SSD > HDD, plus up to 100 for size (the Python planner's ranking).
pub fn rank(mut disks: Vec<Disk>, boot: &[String], min_bytes: u64) -> Vec<Disk> {
    for d in &mut disks {
        d.is_current_boot = boot.contains(&d.name);
        if d.is_current_boot {
            d.score = 0;
            d.status = "ineligible_current_boot".into();
        } else if d.size_bytes < min_bytes {
            d.score = 0;
            d.status = "ineligible_too_small".into();
        } else {
            let kind = if d.bus_type == "nvme" {
                800
            } else if !d.rotational {
                500
            } else {
                200
            };
            d.score = 100 + kind + (d.size_bytes / GIB / 10).min(100);
            d.status = "eligible".into();
        }
    }
    disks.sort_by(|a, b| b.score.cmp(&a.score).then(a.name.cmp(&b.name)));
    disks
}

/// The target: the named disk (which must be eligible), or with `auto` the
/// best eligible one. Never a boot disk, never one below the floor.
pub fn select(disks: &[Disk], target: Option<&str>, auto: bool) -> Result<Disk, String> {
    if let Some(t) = target {
        let want = t.strip_prefix("/dev/").unwrap_or(t);
        let d = disks
            .iter()
            .find(|d| d.name == want)
            .ok_or_else(|| format!("target disk {t} is not a block device on this system"))?;
        return match d.status.as_str() {
            "eligible" => Ok(d.clone()),
            "ineligible_current_boot" => Err(format!(
                "refusing {}: it backs the running system",
                d.device_path
            )),
            other => Err(format!("refusing {}: {other}", d.device_path)),
        };
    }
    if !auto {
        return Err("name a disk with --target-disk, or pass --auto-select".into());
    }
    disks
        .iter()
        .find(|d| d.status == "eligible")
        .cloned()
        .ok_or_else(|| "no eligible disk: every disk backs the running system or is below [bootc_install].root_min_gb".into())
}

#[derive(Clone, Debug, Serialize)]
pub struct Plan {
    pub image_ref: String,
    pub target: Disk,
    pub filesystem: Option<String>,
    pub bound_images: String,
    pub uefi: bool,
    pub command: Vec<String>,
}

/// `bootc install to-disk` run by the image's own bootc inside a privileged
/// podman container -- the invocation bootc documents. No --filesystem
/// unless asked: the image's usr/lib/bootc/install config decides.
pub fn plan(
    image_ref: &str,
    target: Disk,
    filesystem: Option<&str>,
    bound_images: &str,
    uefi: bool,
) -> Plan {
    let mut command: Vec<String> = [
        "podman",
        "run",
        "--rm",
        "--privileged",
        "--pid=host",
        "--ipc=host",
        "-v",
        "/dev:/dev",
        "-v",
        "/var/lib/containers:/var/lib/containers",
        "--security-opt",
        "label=type:unconfined_t",
        image_ref,
        "bootc",
        "install",
        "to-disk",
        "--wipe",
        "--bound-images",
        bound_images,
    ]
    .iter()
    .map(|s| s.to_string())
    .collect();
    if let Some(fs) = filesystem {
        command.extend(["--filesystem".to_string(), fs.to_string()]);
    }
    command.push(target.device_path.clone());
    Plan {
        image_ref: image_ref.to_string(),
        target,
        filesystem: filesystem.map(str::to_string),
        bound_images: bound_images.to_string(),
        uefi,
        command,
    }
}

/// A fixed three-disk machine for --mock: an NVMe and a SATA SSD that are
/// eligible, and the USB stick the system booted from.
pub fn mock_disks() -> (Vec<Disk>, Vec<String>) {
    let d = |name: &str, model: &str, serial: &str, gib: u64, bus: &str, removable: bool| Disk {
        device_path: format!("/dev/{name}"),
        name: name.into(),
        model: model.into(),
        serial: serial.into(),
        size_bytes: gib * GIB,
        bus_type: bus.into(),
        rotational: false,
        is_removable: removable,
        is_current_boot: false,
        score: 0,
        status: String::new(),
    };
    (
        vec![
            d(
                "nvme0n1",
                "Samsung SSD 990 PRO 1TB (Mock)",
                "S6P2NJ0W123456",
                1000,
                "nvme",
                false,
            ),
            d(
                "sda",
                "Crucial MX500 500GB (Mock)",
                "2145E5E98765",
                500,
                "sata",
                false,
            ),
            d(
                "sdb",
                "SanDisk Ultra USB 3.0 (Mock)",
                "4C5300012345",
                32,
                "usb",
                true,
            ),
        ],
        vec!["sdb".to_string()],
    )
}

pub fn uefi(sys: &Path) -> bool {
    sys.join("firmware/efi").is_dir()
}

pub fn default_sys() -> PathBuf {
    PathBuf::from("/sys")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn disk(sys: &Path, name: &str, gib: u64, rot: &str) {
        let d = sys.join("block").join(name);
        fs::create_dir_all(d.join("queue")).unwrap_or_else(|e| panic!("{e}"));
        fs::create_dir_all(d.join("device")).unwrap_or_else(|e| panic!("{e}"));
        fs::write(d.join("size"), format!("{}\n", gib * GIB / 512))
            .unwrap_or_else(|e| panic!("{e}"));
        fs::write(d.join("queue/rotational"), rot).unwrap_or_else(|e| panic!("{e}"));
        fs::write(d.join("device/model"), "Model\n").unwrap_or_else(|e| panic!("{e}"));
    }

    #[test]
    fn scan_reads_sysfs_and_skips_virtual_devices() {
        let t = tempfile::tempdir().unwrap_or_else(|e| panic!("{e}"));
        disk(t.path(), "nvme0n1", 500, "0");
        disk(t.path(), "sda", 2000, "1");
        disk(t.path(), "loop0", 1, "0");
        let found = scan(t.path());
        let names: Vec<_> = found.iter().map(|d| d.name.as_str()).collect();
        assert_eq!(names, ["nvme0n1", "sda"]);
        assert_eq!(found[0].size_bytes, 500 * GIB);
        assert!(found[1].rotational);
    }

    #[test]
    fn ranking_prefers_nvme_and_refuses_boot_and_small_disks() {
        let (disks, boot) = mock_disks();
        let ranked = rank(disks, &boot, 80 * GIB);
        assert_eq!(ranked[0].name, "nvme0n1");
        let sdb = ranked
            .iter()
            .find(|d| d.name == "sdb")
            .unwrap_or_else(|| panic!("sdb"));
        assert_eq!(sdb.status, "ineligible_current_boot");
        let small = rank(mock_disks().0, &[], 600 * GIB);
        assert_eq!(
            small
                .iter()
                .find(|d| d.name == "sda")
                .map(|d| d.status.as_str()),
            Some("ineligible_too_small")
        );
    }

    #[test]
    fn select_never_returns_a_boot_or_unknown_disk() {
        let (disks, boot) = mock_disks();
        let ranked = rank(disks, &boot, 80 * GIB);
        assert!(select(&ranked, Some("/dev/sdb"), false)
            .unwrap_err()
            .contains("backs the running system"));
        assert!(select(&ranked, Some("/dev/sdz"), false).is_err());
        assert!(select(&ranked, None, false).is_err());
        assert_eq!(
            select(&ranked, None, true).map(|d| d.name),
            Ok("nvme0n1".to_string())
        );
        assert_eq!(
            select(&ranked, Some("sda"), false).map(|d| d.name),
            Ok("sda".to_string())
        );
    }

    #[test]
    fn plan_runs_the_images_own_bootc_in_podman() {
        let (disks, boot) = mock_disks();
        let target =
            select(&rank(disks, &boot, 80 * GIB), None, true).unwrap_or_else(|e| panic!("{e}"));
        let p = plan(
            "registry.example/os:1",
            target.clone(),
            None,
            "stored",
            true,
        );
        let c = p.command.join(" ");
        assert!(
            c.starts_with("podman run --rm --privileged --pid=host --ipc=host"),
            "{c}"
        );
        assert!(c.contains("registry.example/os:1 bootc install to-disk --wipe --bound-images stored /dev/nvme0n1"), "{c}");
        assert!(
            !c.contains("--filesystem") && !c.contains("--generic-image-from"),
            "{c}"
        );
        let p = plan("r/x:1", target, Some("btrfs"), "pull", true);
        assert!(p
            .command
            .join(" ")
            .ends_with("--bound-images pull --filesystem btrfs /dev/nvme0n1"));
    }

    #[test]
    fn a_partition_or_dm_device_resolves_to_its_whole_disk() {
        let t = tempfile::tempdir().unwrap_or_else(|e| panic!("{e}"));
        let sys = t.path();
        let dev = sys.join("devices/pci/nvme0n1");
        fs::create_dir_all(dev.join("nvme0n1p2")).unwrap_or_else(|e| panic!("{e}"));
        fs::write(dev.join("nvme0n1p2/partition"), "2").unwrap_or_else(|e| panic!("{e}"));
        fs::create_dir_all(sys.join("class/block")).unwrap_or_else(|e| panic!("{e}"));
        std::os::unix::fs::symlink(dev.join("nvme0n1p2"), sys.join("class/block/nvme0n1p2"))
            .unwrap_or_else(|e| panic!("{e}"));
        fs::create_dir_all(sys.join("class/block/dm-0/slaves/nvme0n1p2"))
            .unwrap_or_else(|e| panic!("{e}"));
        let mi = "29 1 253:0 / / rw - xfs /dev/dm-0 rw\n30 29 259:1 / /boot rw - ext4 /dev/nvme0n1p2 rw\n";
        assert_eq!(boot_disks(sys, mi), vec!["nvme0n1".to_string()]);
    }
}
