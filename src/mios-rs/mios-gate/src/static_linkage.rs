// AI-hint: Static linkage verification gate for mios-gate: asserts absence of PT_INTERP and DT_NEEDED on Linux native binaries per Law 14 (WS-LANG / ADR-0011 / ADR-0021).
// AI-related: src/mios-rs/mios-gate/src/main.rs, usr/share/mios/mios.toml, automation/98-drift-checks.sh, automation/55-native-build.sh

use crate::Report;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

const CHECK: &str = "static-linkage";

pub struct Options {
    pub root: PathBuf,
    pub binary: Option<PathBuf>,
    pub arch: Option<String>,
}

fn cannot_run(why: impl Into<String>) -> Report {
    Report {
        check: CHECK.to_string(),
        ok: false,
        could_not_run: Some(why.into()),
        summary: String::new(),
        findings: Vec::new(),
    }
}

/// Detect ELF architecture (62 -> x86_64, 183 -> aarch64) from header.
fn detect_elf_arch(data: &[u8]) -> Option<&'static str> {
    if data.len() < 20 || data.get(..4) != Some(b"\x7fELF") {
        return None;
    }
    let machine = u16::from_le_bytes([data[18], data[19]]);
    match machine {
        62 => Some("x86_64"),
        183 => Some("aarch64"),
        _ => None,
    }
}

/// Resolve PIE requirement from SSOT or architecture defaults.
fn resolve_pie_policy(root: &Path, arch: &str) -> bool {
    let ssot_path = root.join("usr/share/mios/mios.toml");
    if ssot_path.is_file() {
        if let Ok(target_policy) = mios_build::native_linux_target(root, arch) {
            return target_policy.pie;
        }
        if let Ok(content) = std::fs::read_to_string(&ssot_path) {
            if let Ok(val) = content.parse::<toml::Value>() {
                if let Some(pie_val) = val
                    .get("build")
                    .and_then(|b| b.get("native"))
                    .and_then(|n| n.get("linux"))
                    .and_then(|l| l.get("pie"))
                    .and_then(|p| p.get(arch))
                    .and_then(|v| v.as_bool())
                {
                    return pie_val;
                }
            }
        }
    }
    // Architecture default: x86_64 requires static-pie, aarch64 currently does not
    arch == "x86_64"
}

/// Load approved dynamic linkage exceptions from SSOT.
fn load_exceptions(root: &Path) -> BTreeSet<String> {
    let ssot_path = root.join("usr/share/mios/mios.toml");
    let mut exceptions = BTreeSet::new();
    if let Ok(content) = std::fs::read_to_string(&ssot_path) {
        if let Ok(val) = content.parse::<toml::Value>() {
            if let Some(list) = val
                .get("build")
                .and_then(|b| b.get("native"))
                .and_then(|n| n.get("linux"))
                .and_then(|l| l.get("exceptions"))
                .and_then(|e| e.as_array())
            {
                for item in list {
                    if let Some(name) = item.get("binary").and_then(|b| b.as_str()) {
                        exceptions.insert(name.to_string());
                    }
                }
            }
        }
    }
    exceptions
}

fn check_single_binary(
    path: &Path,
    arch_override: Option<&str>,
    root: &Path,
    exceptions: &BTreeSet<String>,
    findings: &mut Vec<String>,
) -> bool {
    let file_name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or_default();
    if exceptions.contains(file_name) {
        return true;
    }

    let data = match std::fs::read(path) {
        Ok(d) => d,
        Err(e) => {
            findings.push(format!("{}: failed to read binary: {e}", path.display()));
            return false;
        }
    };

    let arch = match arch_override {
        Some(a) => a,
        None => detect_elf_arch(&data).unwrap_or("x86_64"),
    };

    let require_pie = resolve_pie_policy(root, arch);

    if let Err(e) = mios_build::verify_static_elf(&data, arch, require_pie) {
        findings.push(format!("{}: {e}", path.display()));
        return false;
    }
    true
}

fn is_elf_file(path: &Path) -> bool {
    if let Ok(mut f) = std::fs::File::open(path) {
        use std::io::Read;
        let mut magic = [0_u8; 4];
        if f.read_exact(&mut magic).is_ok() && &magic == b"\x7fELF" {
            return true;
        }
    }
    false
}

fn collect_elf_files_flat(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in rd.flatten() {
        let path = entry.path();
        if path.is_file() && is_elf_file(&path) {
            out.push(path);
        }
    }
}

fn collect_elf_files_recursive(dir: &Path, out: &mut Vec<PathBuf>) {
    collect_elf_files_recursive_bounded(dir, out, 0);
}

fn collect_elf_files_recursive_bounded(dir: &Path, out: &mut Vec<PathBuf>, depth: usize) {
    if depth > 32 {
        return;
    }
    let Ok(rd) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in rd.flatten() {
        let path = entry.path();
        if path.is_file() {
            if is_elf_file(&path) {
                out.push(path);
            }
        } else if path.is_dir() {
            collect_elf_files_recursive_bounded(&path, out, depth + 1);
        }
    }
}

pub fn check(opts: &Options) -> Report {
    let exceptions = load_exceptions(&opts.root);
    let mut findings = Vec::new();

    if let Some(ref binary_path) = opts.binary {
        if !binary_path.is_file() {
            return cannot_run(format!(
                "specified binary {} does not exist",
                binary_path.display()
            ));
        }

        let ok = check_single_binary(
            binary_path,
            opts.arch.as_deref(),
            &opts.root,
            &exceptions,
            &mut findings,
        );

        let summary = if ok {
            format!(
                "binary {} verified as static ELF (no PT_INTERP, no DT_NEEDED)",
                binary_path.display()
            )
        } else {
            format!(
                "static linkage audit failed for binary {}: {} violation(s)",
                binary_path.display(),
                findings.len()
            )
        };

        return Report {
            check: CHECK.to_string(),
            ok,
            could_not_run: None,
            summary,
            findings,
        };
    }

    // Scan candidate directories for standalone Linux release ELF binaries
    let mut binaries = Vec::new();

    // 1. Installed FHS directories in root
    for sub in &["usr/bin", "usr/libexec/mios"] {
        let p = opts.root.join(sub);
        if p.is_dir() {
            collect_elf_files_recursive(&p, &mut binaries);
        }
    }

    // 2. Musl release target directories
    for sub in &[
        "tools/native/target/x86_64-unknown-linux-musl/release",
        "src/mios-rs/target/x86_64-unknown-linux-musl/release",
        "target/x86_64-unknown-linux-musl/release",
        "tools/native/target/aarch64-unknown-linux-musl/release",
        "src/mios-rs/target/aarch64-unknown-linux-musl/release",
        "target/aarch64-unknown-linux-musl/release",
    ] {
        let p = opts.root.join(sub);
        if p.is_dir() {
            collect_elf_files_recursive(&p, &mut binaries);
        }
    }

    // 3. Environment overrides
    if let Ok(dir) = std::env::var("MIOS_STATIC_LINKAGE_DIR") {
        let p = PathBuf::from(dir);
        if p.is_dir() {
            collect_elf_files_recursive(&p, &mut binaries);
        }
    }
    if let Ok(prefix) = std::env::var("MIOS_NATIVE_INSTALL_ROOT") {
        for sub in &["usr/bin", "usr/libexec/mios"] {
            let p = PathBuf::from(&prefix).join(sub);
            if p.is_dir() {
                collect_elf_files_recursive(&p, &mut binaries);
            }
        }
    }

    // 4. If root itself contains regular ELF files (e.g. test directory or flat output)
    if opts.root.is_dir() {
        collect_elf_files_flat(&opts.root, &mut binaries);
        let bin_sub = opts.root.join("bin");
        if bin_sub.is_dir() {
            collect_elf_files_recursive(&bin_sub, &mut binaries);
        }
    }

    // Deduplicate binaries by canonical path
    binaries.sort();
    binaries.dedup();

    if binaries.is_empty() {
        return cannot_run(format!(
            "no standalone Linux release ELF binaries found to audit in {}",
            opts.root.display()
        ));
    }

    for b in &binaries {
        check_single_binary(
            b,
            opts.arch.as_deref(),
            &opts.root,
            &exceptions,
            &mut findings,
        );
    }

    let ok = findings.is_empty();
    let summary = if ok {
        format!(
            "{} standalone Linux release binary(ies) verified as static ELF (no PT_INTERP, no DT_NEEDED)",
            binaries.len()
        )
    } else {
        format!(
            "static linkage audit failed: {} violation(s) detected across {} binary(ies)",
            findings.len(),
            binaries.len()
        )
    };
    Report {
        check: CHECK.to_string(),
        ok,
        could_not_run: None,
        summary,
        findings,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_elf(extra: u32) -> Vec<u8> {
        let mut data = vec![0_u8; 256];
        data[..7].copy_from_slice(b"\x7fELF\x02\x01\x01");
        data[16..18].copy_from_slice(&2_u16.to_le_bytes()); // ET_EXEC
        data[18..20].copy_from_slice(&62_u16.to_le_bytes()); // x86_64
        data[20..24].copy_from_slice(&1_u32.to_le_bytes());
        data[24..32].copy_from_slice(&0x1080_u64.to_le_bytes()); // entry
        data[32..40].copy_from_slice(&64_u64.to_le_bytes()); // phoff
        data[52..54].copy_from_slice(&64_u16.to_le_bytes()); // ehsize
        data[54..56].copy_from_slice(&56_u16.to_le_bytes()); // phentsize
        data[56..58].copy_from_slice(&2_u16.to_le_bytes()); // phnum
                                                            // Program header 0: PT_LOAD
        data[64..68].copy_from_slice(&1_u32.to_le_bytes()); // PT_LOAD
        data[68..72].copy_from_slice(&5_u32.to_le_bytes()); // PF_R | PF_X
        data[80..88].copy_from_slice(&0x1000_u64.to_le_bytes()); // vaddr
        data[96..104].copy_from_slice(&256_u64.to_le_bytes()); // filesz
        data[104..112].copy_from_slice(&256_u64.to_le_bytes()); // memsz
                                                                // Program header 1: extra
        data[120..124].copy_from_slice(&extra.to_le_bytes());
        if extra == 2 {
            // PT_DYNAMIC
            data[128..136].copy_from_slice(&224_u64.to_le_bytes()); // offset
            data[152..160].copy_from_slice(&32_u64.to_le_bytes()); // filesz
        }
        data
    }

    fn make_static_pie() -> Vec<u8> {
        let mut pie = make_elf(2);
        pie[16..18].copy_from_slice(&3_u16.to_le_bytes()); // ET_DYN
        pie[224..232].copy_from_slice(&0x6fff_fffb_u64.to_le_bytes()); // DT_FLAGS_1
        pie[232..240].copy_from_slice(&0x0800_0001_u64.to_le_bytes()); // DF_1_PIE
        pie
    }

    fn make_dynamic_interp() -> Vec<u8> {
        make_elf(3) // PT_INTERP
    }

    fn make_dynamic_needed() -> Vec<u8> {
        let mut dyn_bin = make_elf(2);
        dyn_bin[224..232].copy_from_slice(&1_u64.to_le_bytes()); // DT_NEEDED
        dyn_bin
    }

    #[test]
    fn positive_control_static_pie_passes() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("static_bin");
        std::fs::write(&bin_path, make_static_pie()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(
            report.ok,
            "Expected static PIE to pass: {:?}",
            report.findings
        );
        assert_eq!(report.code(), 0);
        assert!(report.findings.is_empty());
    }

    #[test]
    fn positive_control_directory_scan_passes() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("my_service");
        std::fs::write(&bin_path, make_static_pie()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: None,
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(
            report.ok,
            "Expected directory scan to pass: {:?}",
            report.findings
        );
        assert_eq!(report.code(), 0);
        assert!(report.summary.contains("1 standalone Linux release binary"));
    }

    #[test]
    fn negative_control_pt_interp_fails_and_names_defect() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("dynamic_interp_bin");
        std::fs::write(&bin_path, make_dynamic_interp()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok, "Expected dynamic binary with PT_INTERP to fail");
        assert_eq!(report.code(), 1);
        assert!(
            report.findings.iter().any(|f| f.contains("PT_INTERP")),
            "Expected defect to name PT_INTERP, got: {:?}",
            report.findings
        );
    }

    #[test]
    fn negative_control_dt_needed_fails_and_names_defect() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("dynamic_needed_bin");
        std::fs::write(&bin_path, make_dynamic_needed()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok, "Expected dynamic binary with DT_NEEDED to fail");
        assert_eq!(report.code(), 1);
        assert!(
            report.findings.iter().any(|f| f.contains("DT_NEEDED")),
            "Expected defect to name DT_NEEDED, got: {:?}",
            report.findings
        );
    }

    #[test]
    fn negative_control_non_pie_fails_on_x86_64() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("non_pie_bin");
        std::fs::write(&bin_path, make_elf(0)).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok, "Expected non-PIE executable to fail on x86_64");
        assert_eq!(report.code(), 1);
        assert!(
            report.findings.iter().any(|f| f.contains("static-pie")),
            "Expected defect to name static-pie, got: {:?}",
            report.findings
        );
    }

    #[test]
    fn negative_control_corrupt_artifact_fails() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("corrupt_bin");
        std::fs::write(&bin_path, b"MZ\x90\x00not_an_elf_binary").unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok, "Expected non-ELF artifact to fail");
        assert_eq!(report.code(), 1);
    }

    #[test]
    fn missing_binary_cannot_run() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("nonexistent_binary");

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: None,
        };
        let report = check(&opts);
        assert_eq!(report.code(), 2);
        assert!(report.could_not_run.is_some());
    }

    #[test]
    fn empty_directory_cannot_run() {
        let tmp = tempfile::tempdir().unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: None,
            arch: None,
        };
        let report = check(&opts);
        assert_eq!(report.code(), 2);
        assert!(report.could_not_run.is_some());
    }

    #[test]
    fn negative_control_directory_scan_violations_summary() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("dynamic_service");
        std::fs::write(&bin_path, make_dynamic_interp()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: None,
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok, "Expected directory scan to fail");
        assert_eq!(report.code(), 1);
        assert!(!report.summary.contains("verified as static ELF"));
        assert!(report.summary.contains("static linkage audit failed"));
    }

    #[test]
    fn negative_control_single_binary_violations_summary() {
        let tmp = tempfile::tempdir().unwrap();
        let bin_path = tmp.path().join("dynamic_bin");
        std::fs::write(&bin_path, make_dynamic_interp()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: Some(bin_path),
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(!report.ok);
        assert_eq!(report.code(), 1);
        assert!(!report.summary.contains("verified as static ELF"));
        assert!(report.summary.contains("static linkage audit failed"));
    }

    #[test]
    fn positive_control_recursive_directory_scan_finds_nested_binaries() {
        let tmp = tempfile::tempdir().unwrap();
        let nested_dir = tmp
            .path()
            .join("usr")
            .join("bin")
            .join("deep")
            .join("nested");
        std::fs::create_dir_all(&nested_dir).unwrap();
        let bin_path = nested_dir.join("deep_service");
        std::fs::write(&bin_path, make_static_pie()).unwrap();

        let opts = Options {
            root: tmp.path().to_path_buf(),
            binary: None,
            arch: Some("x86_64".into()),
        };
        let report = check(&opts);
        assert!(
            report.ok,
            "Expected nested directory scan to pass: {:?}",
            report.findings
        );
        assert_eq!(report.code(), 0);
        assert!(report.summary.contains("1 standalone Linux release binary"));
    }
}
