// AI-hint: Process creation flags, hidden console configuration, and workspace locking.
// AI-related: tools/native/mios-launch, tools/native/mios-agent-relay

use std::fs::{File, OpenOptions};
use std::path::Path;

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
