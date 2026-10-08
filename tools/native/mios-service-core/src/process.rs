// AI-hint: Process creation flags, hidden console configuration, and workspace locking.
// AI-related: tools/native/mios-launch, tools/native/mios-agent-relay

use std::fs::{File, OpenOptions};
use std::path::Path;

/// Bound direct control clients which own their output pipes. Kill only the
/// client we started on timeout; an existing server is never a timeout target.
pub fn output_timeout(
    command: &mut std::process::Command,
    timeout: std::time::Duration,
) -> Result<std::process::Output, String> {
    use std::io::Read;
    use std::process::Stdio;
    use std::time::{Duration, Instant};
    if timeout.is_zero() {
        return Err("Control client timeout must be positive".into());
    }
    configure_hidden(command);
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|e| format!("Control client start: {e}"))?;
    let stdout = child.stdout.take().ok_or("Control stdout missing")?;
    let stderr = child.stderr.take().ok_or("Control stderr missing")?;
    let reader = |stream: Box<dyn Read + Send>| {
        std::thread::spawn(move || {
            let mut data = Vec::new();
            stream
                .take(1024 * 1024 + 1)
                .read_to_end(&mut data)
                .map(|_| data)
        })
    };
    let out = reader(Box::new(stdout));
    let err = reader(Box::new(stderr));
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) if start.elapsed() < timeout => std::thread::sleep(Duration::from_millis(10)),
            Ok(None) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err(format!(
                    "Control client timed out after {}ms",
                    timeout.as_millis()
                ));
            }
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err(format!("Control client wait: {e}"));
            }
        }
    };
    let stdout = out
        .join()
        .map_err(|_| "Control stdout reader panicked")?
        .map_err(|e| e.to_string())?;
    let stderr = err
        .join()
        .map_err(|_| "Control stderr reader panicked")?
        .map_err(|e| e.to_string())?;
    let status = status?;
    if stdout.len() > 1024 * 1024 || stderr.len() > 1024 * 1024 {
        return Err("Control client output exceeds 1 MiB per stream".into());
    }
    Ok(std::process::Output {
        status,
        stdout,
        stderr,
    })
}

#[cfg(all(test, unix))]
mod timeout_tests {
    use super::*;
    #[test]
    fn bounded_clients_preserve_status_diagnostics_and_terminate_only_their_own_process(
    ) -> Result<(), String> {
        let output = output_timeout(
            std::process::Command::new("sh")
                .args(["-c", "printf result; printf diagnostic >&2; exit 7"]),
            std::time::Duration::from_secs(1),
        )?;
        assert_eq!(output.status.code(), Some(7));
        assert_eq!(output.stdout, b"result");
        assert_eq!(output.stderr, b"diagnostic");
        let started = std::time::Instant::now();
        let failure = output_timeout(
            std::process::Command::new("sleep").arg("5"),
            std::time::Duration::from_millis(30),
        );
        assert!(failure.is_err_and(|e| e.contains("timed out")));
        assert!(started.elapsed() < std::time::Duration::from_secs(1));
        Ok(())
    }
}

/// Win32 CREATE_NO_WINDOW creation flag (0x0800_0000).
pub const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Debug, thiserror::Error)]
pub enum ProcessError {
    #[error("Missing socket parent directory")]
    MissingParent,

    #[error("Unsafe workspace lock: {0}")]
    UnsafeLock(String),

    #[error("Workspace lock belongs to another user")]
    PermissionDenied,

    #[error("Lock acquisition error: {0}")]
    LockFailed(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Applies the hidden window creation flag (CREATE_NO_WINDOW) to a Command on Windows.
#[cfg(windows)]
pub fn configure_hidden(command: &mut std::process::Command) -> &mut std::process::Command {
    use std::os::windows::process::CommandExt;
    command.creation_flags(CREATE_NO_WINDOW)
}

/// Non-Windows no-op pass-through for configure_hidden.
#[cfg(not(windows))]
pub fn configure_hidden(command: &mut std::process::Command) -> &mut std::process::Command {
    command
}

/// Checks whether a given Win32 creation flag contains CREATE_NO_WINDOW.
pub fn is_hidden_flag(flag: u32) -> bool {
    (flag & CREATE_NO_WINDOW) != 0
}

/// Acquires an exclusive file lock in the socket parent directory with security checks.
pub fn workspace_lock(path: &Path, name: &str) -> Result<File, ProcessError> {
    let parent = path.parent().ok_or(ProcessError::MissingParent)?;
    let lock_path = parent.join(name);
    if lock_path.is_symlink() {
        return Err(ProcessError::UnsafeLock("symlink lock path".into()));
    }
    let lock = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(&lock_path)?;
    if !crate::socket::owned_path(&lock_path) {
        return Err(ProcessError::PermissionDenied);
    }
    lock.lock()
        .map_err(|e| ProcessError::LockFailed(e.to_string()))?;
    Ok(lock)
}
