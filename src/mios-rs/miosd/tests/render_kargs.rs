// AI-hint: Integration tests for `miosd render-kargs` -- the kernel command line is the highest-consequence projection in the build, so the unmanaged-karg preservation contract is pinned here.
// AI-related: src/mios-rs/miosd/src/main.rs, automation/75-kargs-render.sh, usr/lib/bootc/kargs.d, usr/share/mios/mios.toml

use std::fs;
use std::path::PathBuf;
use std::process::Command;

const SHIPPED_VFIO: &str = concat!(
    "# AI-hint: Configures kernel arguments for IOMMU, VFIO-PCI, and nested virtualization to enable hardware passthrough and virtualization features in the MiOS boot process.\n",
    "# Generated from mios.toml [kargs] SSOT\n",
    "kargs = [\n",
    "    \"rd.driver.pre=vfio-pci\",\n",
    "    \"kvm-intel.nested=1\",\n",
    "    \"intel_iommu=on\",\n",
    "    \"amd_iommu=on\",\n",
    "    \"iommu=pt\"\n",
    "]\n",
);

struct Fixture {
    dir: tempfile::TempDir,
}

impl Fixture {
    fn new(kargs_table: &str) -> Self {
        let dir = tempfile::tempdir().expect("tempdir");
        fs::write(dir.path().join("01-mios-vfio.toml"), SHIPPED_VFIO).expect("seed vfio");
        fs::write(dir.path().join("mios.toml"), kargs_table).expect("seed toml");
        Fixture { dir }
    }
    fn toml(&self) -> PathBuf {
        self.dir.path().join("mios.toml")
    }
    fn run(&self) -> std::process::Output {
        Command::new(env!("CARGO_BIN_EXE_miosd"))
            .args(["render-kargs", "--toml"])
            .arg(self.toml())
            .arg("--kargs-dir")
            .arg(self.dir.path())
            .output()
            .expect("run miosd")
    }
    fn vfio(&self) -> String {
        fs::read_to_string(self.dir.path().join("01-mios-vfio.toml")).expect("read vfio")
    }
    fn custom_exists(&self) -> bool {
        self.dir.path().join("99-mios-kargs.toml").exists()
    }
}

const DEFAULTS: &str = "[kargs]\niommu = \"on\"\nvfio_ids = \"\"\nhugepages = \"\"\nisolcpus = \"\"\nnohz_full = \"\"\nrcu_nocbs = \"\"\nTHP = \"\"\n";

/// The regression this file exists for. The shipped drop-in,
/// usr/lib/bootc/kargs.d/01-mios-vfio.toml, is NOT wholly generated:
/// rd.driver.pre=vfio-pci binds vfio-pci in the initramfs before a
/// GPU driver can claim the card, and kvm-intel.nested=1 enables nested KVM.
/// Neither comes from any [kargs] key. A renderer that rebuilds the list from
/// scratch deletes both from the kernel command line, exits 0, and leaves a
/// header claiming the file came from SSOT.
#[test]
fn unmanaged_kargs_survive_a_render() {
    let f = Fixture::new(DEFAULTS);
    assert!(f.run().status.success());
    let out = f.vfio();
    assert!(
        out.contains("\"rd.driver.pre=vfio-pci\""),
        "rd.driver.pre=vfio-pci was dropped from the kernel command line:\n{out}"
    );
    assert!(
        out.contains("\"kvm-intel.nested=1\""),
        "kvm-intel.nested=1 was dropped from the kernel command line:\n{out}"
    );
    assert_eq!(
        out, SHIPPED_VFIO,
        "the shipped file must round-trip exactly"
    );
}

#[test]
fn iommu_mode_swaps_only_the_managed_trio() {
    let f = Fixture::new(&DEFAULTS.replace("iommu = \"on\"", "iommu = \"amd\""));
    assert!(f.run().status.success());
    let out = f.vfio();
    assert!(out.contains("\"amd_iommu=on\"") && out.contains("\"iommu=pt\""));
    assert!(
        !out.contains("\"intel_iommu=on\""),
        "intel entry not removed:\n{out}"
    );
    assert!(
        out.contains("\"rd.driver.pre=vfio-pci\""),
        "unmanaged karg lost:\n{out}"
    );
}

#[test]
fn vfio_ids_is_replaced_not_accumulated() {
    let f = Fixture::new(&DEFAULTS.replace("vfio_ids = \"\"", "vfio_ids = \"10de:1db6\""));
    assert!(f.run().status.success());
    let first = f.vfio();
    assert!(first.contains("\"vfio-pci.ids=10de:1db6\""));
    assert!(f.run().status.success());
    assert_eq!(first, f.vfio(), "a second render must be a no-op");
}

#[test]
fn custom_kargs_file_is_written_then_removed() {
    let f = Fixture::new(&DEFAULTS.replace("isolcpus = \"\"", "isolcpus = \"2-7\""));
    assert!(f.run().status.success());
    assert!(
        f.custom_exists(),
        "99-mios-kargs.toml should exist when a custom karg is set"
    );
    fs::write(f.toml(), DEFAULTS).expect("rewrite toml");
    assert!(f.run().status.success());
    assert!(
        !f.custom_exists(),
        "stale 99-mios-kargs.toml must be removed"
    );
}

/// unwrap_or_default() on the read turned "the SSOT is unreadable" into
/// "render the defaults anyway". A renderer that invents a kernel command line
/// for a manifest it could not read is Skip-as-Pass with boot consequences.
#[test]
fn an_unreadable_ssot_fails_and_writes_nothing() {
    let f = Fixture::new(DEFAULTS);
    fs::remove_file(f.toml()).expect("remove toml");
    assert!(!f.run().status.success(), "a missing SSOT must not exit 0");
    assert_eq!(f.vfio(), SHIPPED_VFIO, "nothing may be written on failure");
}

#[test]
fn a_malformed_ssot_fails_and_writes_nothing() {
    let f = Fixture::new("[kargs\niommu = \"on\"\n");
    assert!(!f.run().status.success(), "malformed TOML must not exit 0");
    assert_eq!(f.vfio(), SHIPPED_VFIO, "nothing may be written on failure");
}
