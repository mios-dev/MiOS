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
    /// Commands run before `command` (an offline image load), in order.
    pub preload: Vec<Vec<String>>,
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
    plan_from(image_ref, None, target, filesystem, bound_images, uefi)
}

/// An offline source bootc can install from without a registry.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Source {
    /// A `podman save --format oci-archive` tarball (the staged USB payload).
    OciArchive(String),
}

impl Source {
    pub fn parse(s: &str) -> Result<Source, String> {
        match s.strip_prefix("oci-archive:") {
            Some(p) if !p.is_empty() => Ok(Source::OciArchive(p.to_string())),
            _ => Err(format!(
                "--source {s:?}: only oci-archive:PATH is supported"
            )),
        }
    }
}

/// Offline variant: load the archive into the host's container storage,
/// run the loaded image (`loaded_ref`, the tag it was saved under), and set
/// `--target-imgref` to `image_ref` so the installed host upgrades from the
/// registry rather than tracking the archive.
pub fn plan_offline(
    image_ref: &str,
    source: &Source,
    loaded_ref: &str,
    target: Disk,
    filesystem: Option<&str>,
    bound_images: &str,
    uefi: bool,
) -> Plan {
    let Source::OciArchive(path) = source;
    let mut p = plan_from(
        loaded_ref,
        Some(image_ref),
        target,
        filesystem,
        bound_images,
        uefi,
    );
    p.preload = vec![["podman", "load", "-i", path.as_str()]
        .iter()
        .map(|s| s.to_string())
        .collect()];
    p
}

/// The image `podman load` reports ("Loaded image: REF" or
/// "Loaded image(s): REF[,…]"), so the install runs what was actually
/// loaded rather than an assumed tag.
pub fn loaded_ref(output: &str) -> Option<String> {
    output.lines().find_map(|l| {
        let rest = l
            .strip_prefix("Loaded image(s):")
            .or_else(|| l.strip_prefix("Loaded image:"))?;
        rest.split(',')
            .next()
            .map(|r| r.trim().to_string())
            .filter(|r| !r.is_empty())
    })
}

fn plan_from(
    run_ref: &str,
    target_imgref: Option<&str>,
    target: Disk,
    filesystem: Option<&str>,
    bound_images: &str,
    uefi: bool,
) -> Plan {
    let image_ref = target_imgref.unwrap_or(run_ref);
    let mut command = podman_prefix(run_ref, &[]);
    command.extend(
        ["to-disk", "--wipe", "--bound-images", bound_images]
            .iter()
            .map(|s| s.to_string()),
    );
    if let Some(fs) = filesystem {
        command.extend(["--filesystem".to_string(), fs.to_string()]);
    }
    if let Some(t) = target_imgref {
        command.extend(["--target-imgref".to_string(), t.to_string()]);
    }
    command.push(target.device_path.clone());
    Plan {
        image_ref: image_ref.to_string(),
        target,
        filesystem: filesystem.map(str::to_string),
        bound_images: bound_images.to_string(),
        uefi,
        preload: Vec::new(),
        command,
    }
}

/// `podman run` of the image with what bootc install needs from the host,
/// up to and including `bootc install`.
fn podman_prefix(image_ref: &str, extra_mounts: &[&str]) -> Vec<String> {
    let mut c: Vec<String> = [
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
    ]
    .iter()
    .map(|s| s.to_string())
    .collect();
    for m in extra_mounts {
        c.extend(["-v".to_string(), m.to_string()]);
    }
    c.extend(
        [
            "--security-opt",
            "label=type:unconfined_t",
            image_ref,
            "bootc",
            "install",
        ]
        .iter()
        .map(|s| s.to_string()),
    );
    c
}

/// `bootc install to-existing-root` from the image: the running system stays
/// in place until reboot (bootc's default --replace=alongside) and the
/// bootloader is pointed at the new deployment. The host root is mounted at
/// /target, as bootc's install documentation still shows. --cleanup adds
/// bootc's first-boot removal of the previous install's files.
pub fn plan_existing_root(image_ref: &str, bound_images: &str, cleanup: bool) -> Vec<String> {
    let mut command = podman_prefix(image_ref, &["/:/target"]);
    command.extend(
        [
            "to-existing-root",
            "--acknowledge-destructive",
            "--bound-images",
            bound_images,
        ]
        .iter()
        .map(|s| s.to_string()),
    );
    if cleanup {
        command.push("--cleanup".to_string());
    }
    command
}

/// Options for `bootc install to-filesystem`.
#[derive(Clone, Debug, Default)]
pub struct FsOpts {
    pub root_mount_spec: Option<String>,
    pub boot_mount_spec: Option<String>,
    pub skip_finalize: bool,
}

/// A to-filesystem target must be a mounted, empty directory other than the
/// running root (that is `existing-root`'s job). `mountinfo` is
/// /proc/self/mountinfo; `entries` are the directory's names.
pub fn check_target_root(root: &str, mountinfo: &str, entries: &[String]) -> Result<(), String> {
    let root = root.trim_end_matches('/');
    if root.is_empty() {
        return Err(
            "refusing /: that is the running system; use `mios-install existing-root`".into(),
        );
    }
    let mounted = mountinfo
        .lines()
        .filter_map(|l| l.split_whitespace().nth(4))
        .any(|m| m == root);
    if !mounted {
        return Err(format!(
            "{root} is not a mount point; mount the target root filesystem there first"
        ));
    }
    let content: Vec<&String> = entries.iter().filter(|e| *e != "lost+found").collect();
    if !content.is_empty() {
        return Err(format!(
            "{root} is not empty ({} entries); bootc expects an empty root filesystem",
            content.len()
        ));
    }
    Ok(())
}

/// `bootc install to-filesystem ROOT` from the image, with ROOT mounted at
/// the same path inside the container. `target_imgref` is set for offline
/// sources so the host tracks the registry image.
pub fn plan_filesystem(
    run_ref: &str,
    target_imgref: Option<&str>,
    root: &str,
    bound_images: &str,
    opts: &FsOpts,
) -> Vec<String> {
    let mount = format!("{root}:{root}");
    let mut c = podman_prefix(run_ref, &[mount.as_str()]);
    c.extend(
        ["to-filesystem", "--bound-images", bound_images]
            .iter()
            .map(|s| s.to_string()),
    );
    if let Some(s) = &opts.root_mount_spec {
        c.extend(["--root-mount-spec".to_string(), s.clone()]);
    }
    if let Some(s) = &opts.boot_mount_spec {
        c.extend(["--boot-mount-spec".to_string(), s.clone()]);
    }
    if opts.skip_finalize {
        c.push("--skip-finalize".to_string());
    }
    if let Some(t) = target_imgref {
        c.extend(["--target-imgref".to_string(), t.to_string()]);
    }
    c.push(root.to_string());
    c
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
    fn existing_root_mounts_the_host_root_and_cleans_up_only_when_asked() {
        let c = plan_existing_root("r/os:1", "pull", false).join(" ");
        assert!(c.contains("-v /:/target --security-opt label=type:unconfined_t r/os:1 bootc install to-existing-root --acknowledge-destructive --bound-images pull"), "{c}");
        assert!(!c.contains("--cleanup") && !c.contains("--wipe"), "{c}");
        assert!(plan_existing_root("r/os:1", "stored", true)
            .join(" ")
            .ends_with("--bound-images stored --cleanup"));
    }

    #[test]
    fn an_offline_archive_is_loaded_then_installed_tracking_the_registry_image() {
        let (disks, boot) = mock_disks();
        let target =
            select(&rank(disks, &boot, 80 * GIB), None, true).unwrap_or_else(|e| panic!("{e}"));
        let src = Source::parse("oci-archive:/mnt/repo/mios.tar").unwrap_or_else(|e| panic!("{e}"));
        let p = plan_offline(
            "ghcr.example/os:latest",
            &src,
            "localhost/os:latest",
            target,
            None,
            "stored",
            true,
        );
        assert_eq!(
            p.preload,
            vec![vec!["podman", "load", "-i", "/mnt/repo/mios.tar"]]
        );
        let c = p.command.join(" ");
        assert!(
            c.contains("label=type:unconfined_t localhost/os:latest bootc install to-disk"),
            "{c}"
        );
        assert!(
            c.ends_with("--target-imgref ghcr.example/os:latest /dev/nvme0n1"),
            "{c}"
        );
        assert_eq!(p.image_ref, "ghcr.example/os:latest");
        assert!(Source::parse("docker://x").is_err() && Source::parse("oci-archive:").is_err());
    }

    #[test]
    fn the_loaded_image_is_read_from_podman_load_output() {
        assert_eq!(
            loaded_ref("Getting image source signatures\nLoaded image: localhost/mios:latest\n")
                .as_deref(),
            Some("localhost/mios:latest")
        );
        assert_eq!(
            loaded_ref("Loaded image(s): localhost/a:1,localhost/b:2").as_deref(),
            Some("localhost/a:1")
        );
        assert_eq!(loaded_ref("Error: nothing"), None);
    }

    #[test]
    fn a_filesystem_target_must_be_a_mounted_empty_non_root_directory() {
        let mi = "36 1 8:1 / /mnt/target rw - ext4 /dev/sda1 rw\n";
        assert!(check_target_root("/", mi, &[])
            .unwrap_err()
            .contains("existing-root"));
        assert!(check_target_root("/mnt/other", mi, &[])
            .unwrap_err()
            .contains("not a mount point"));
        assert!(check_target_root("/mnt/target", mi, &["etc".into()])
            .unwrap_err()
            .contains("not empty"));
        assert!(check_target_root("/mnt/target/", mi, &["lost+found".into()]).is_ok());
    }

    #[test]
    fn to_filesystem_mounts_the_root_and_passes_only_given_options() {
        let c =
            plan_filesystem("r/os:1", None, "/mnt/target", "stored", &FsOpts::default()).join(" ");
        assert!(c.contains("-v /mnt/target:/mnt/target --security-opt label=type:unconfined_t r/os:1 bootc install to-filesystem --bound-images stored /mnt/target"), "{c}");
        let o = FsOpts {
            root_mount_spec: Some("LABEL=root".into()),
            boot_mount_spec: None,
            skip_finalize: true,
        };
        let c = plan_filesystem("localhost/os", Some("ghcr/os:1"), "/mnt/t", "pull", &o).join(" ");
        assert!(c.ends_with("--bound-images pull --root-mount-spec LABEL=root --skip-finalize --target-imgref ghcr/os:1 /mnt/t"), "{c}");
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
