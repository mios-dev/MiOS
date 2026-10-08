// AI-hint: Shared native generator dispatch for build verbs and read-only drift checks.
// AI-related: tools/native/mios-gen, automation/33-generate-quadlets.sh
use std::path::Path;
use std::process::Command;

pub fn command(root: &Path, verb: &str, check: bool) -> Result<Command, String> {
    let name = if cfg!(windows) {
        "mios-gen.exe"
    } else {
        "mios-gen"
    };
    let mut candidates = Vec::new();
    if let Some(explicit) = std::env::var_os("MIOS_GEN_BIN") {
        candidates.push(explicit.into());
    } else {
        candidates.extend([
            root.join("tools/native/target/release").join(name),
            root.join("usr/bin").join(name),
            root.join("usr/libexec/mios").join(name),
        ]);
        if let Ok(executable) = std::env::current_exe() {
            if let Some(parent) = executable.parent() {
                candidates.push(parent.join(name));
            }
        }
        candidates.extend([
            Path::new("/usr/bin").join(name),
            Path::new("/usr/libexec/mios").join(name),
        ]);
    }
    let binary = candidates
        .into_iter()
        .find(|p| p.is_file())
        .ok_or_else(|| {
            format!("{verb}: native {name} is required; build/install the SSOT release catalog")
        })?;
    let mut command = Command::new(binary);
    command
        .arg(verb)
        .arg("--root")
        .arg(root)
        .env("MIOS_ROOT", root);
    if check {
        command.arg("--check");
    }
    Ok(command)
}

pub fn run(root: &Path, verb: &str, check: bool) -> Result<(), Box<dyn std::error::Error>> {
    let status = command(root, verb, check)?.status()?;
    if !status.success() {
        return Err(format!("native mios-gen {verb} failed: {status}").into());
    }
    Ok(())
}
