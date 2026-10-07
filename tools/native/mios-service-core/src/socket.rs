// AI-hint: Socket discovery, validation, and ownership verification routines.
// AI-related: tools/native/mios-agent-relay, usr/libexec/mios/mios-mcp-server

use std::fs;
use std::path::{Path, PathBuf};

/// Linux sockaddr_un limit is 108 bytes including trailing null byte.
pub const MAX_SOCKET_PATH_LEN: usize = 107;

#[derive(Debug, thiserror::Error)]
pub enum SocketError {
    #[error("Socket path length {len} exceeds sockaddr_un limit of {max}: {path}")]
    PathTooLong {
        path: String,
        len: usize,
        max: usize,
    },

    #[error("Unsafe socket path: {0}")]
    UnsafePath(String),

    #[error("Socket path does not exist: {0}")]
    NotFound(String),

    #[error("Path is not a valid socket: {0}")]
    NotASocket(String),

    #[error("No active socket found among candidates")]
    NoActiveSocket,

    #[error("Socket parent directory is missing")]
    MissingParent,

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Enforces the 108-byte sockaddr_un path length limit on UNIX domain socket paths.
pub fn check_socket_path_length(path: &Path) -> Result<(), SocketError> {
    let len = path.as_os_str().len();
    if len >= 108 {
        return Err(SocketError::PathTooLong {
            path: path.to_string_lossy().to_string(),
            len,
            max: MAX_SOCKET_PATH_LEN,
        });
    }
    Ok(())
}

/// Verifies that a path is not a symlink and is owned by the current caller process.
pub fn owned_path(path: &Path) -> bool {
    let Ok(meta) = fs::symlink_metadata(path) else {
        return false;
    };
    if meta.file_type().is_symlink() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        let Ok(caller) = fs::metadata("/proc/self") else {
            return false;
        };
        if meta.uid() != caller.uid() {
            return false;
        }
    }
    true
}

/// Verifies that a socket path exists and is owned by the current user.
pub fn verify_socket_owner(path: &Path) -> Result<bool, SocketError> {
    if !path.exists() {
        return Err(SocketError::NotFound(path.to_string_lossy().to_string()));
    }
    Ok(owned_path(path))
}

/// Discovers candidate tmux sockets within a root directory up to a bounded recursion depth.
pub fn socket_candidates(root: &Path, human: &str, depth: usize) -> Vec<PathBuf> {
    let mut sockets = Vec::new();
    if !owned_path(root) || !root.is_dir() {
        return sockets;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::FileTypeExt;
        for leaf in [human, "mcp-headless"] {
            let socket = root.join(leaf);
            if owned_path(&socket)
                && fs::symlink_metadata(&socket).is_ok_and(|m| m.file_type().is_socket())
            {
                sockets.push(socket);
            }
        }
    }
    #[cfg(not(unix))]
    {
        for leaf in [human, "mcp-headless"] {
            let socket = root.join(leaf);
            if owned_path(&socket) && socket.exists() {
                sockets.push(socket);
            }
        }
    }
    let Ok(entries) = fs::read_dir(root) else {
        return sockets;
    };
    for entry in entries.flatten().take(128) {
        let path = entry.path();
        if !owned_path(&path) || !path.is_dir() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        if name.starts_with("tmux-") {
            for leaf in [human, "mcp-headless"] {
                let socket = path.join(leaf);
                #[cfg(unix)]
                {
                    use std::os::unix::fs::FileTypeExt;
                    if owned_path(&socket)
                        && fs::symlink_metadata(&socket).is_ok_and(|m| m.file_type().is_socket())
                    {
                        sockets.push(socket);
                    }
                }
                #[cfg(not(unix))]
                {
                    if owned_path(&socket) && socket.exists() {
                        sockets.push(socket);
                    }
                }
            }
        } else if depth < 2 && (name.starts_with("uid-") || name.starts_with("mios-tmux-")) {
            sockets.extend(socket_candidates(&path, human, depth + 1));
        }
        if sockets.len() >= 16 {
            break;
        }
    }
    sockets.truncate(16);
    sockets
}

/// Discovers the first active, existing socket among candidates, enforcing path bounds.
pub fn find_active_socket<P: AsRef<Path>>(
    candidates: &[P],
) -> Result<Option<PathBuf>, SocketError> {
    for c in candidates {
        let p = c.as_ref();
        // Path bounds check failure propagates.
        check_socket_path_length(p)?;
        if p.exists() {
            return Ok(Some(p.to_path_buf()));
        }
    }
    Ok(None)
}

/// Discovers the first active socket or returns `SocketError::NoActiveSocket`.
pub fn find_active_socket_required<P: AsRef<Path>>(
    candidates: &[P],
) -> Result<PathBuf, SocketError> {
    find_active_socket(candidates)?.ok_or(SocketError::NoActiveSocket)
}

/// Validates workspace socket path for security, length, symlinks, and ownership.
pub fn validate_workspace_socket(path: &Path, human_socket: &str) -> Result<(), SocketError> {
    let file_name = path.file_name().and_then(|s| s.to_str()).unwrap_or("");
    let is_tmux_env = std::env::var("TMUX")
        .ok()
        .and_then(|t| t.split(',').next().map(|s| s.to_string()))
        .as_deref()
        == path.to_str();
    let is_valid_name = file_name == human_socket
        || file_name == "default"
        || file_name.starts_with("tmux-")
        || file_name.starts_with("mios-")
        || is_tmux_env;

    let is_canonical = if cfg!(windows) {
        if let Ok(_c) = path.canonicalize() {
            !path.is_symlink() && path.parent().map(|p| !p.is_symlink()).unwrap_or(true)
        } else {
            false
        }
    } else {
        path.canonicalize().ok().as_deref() == Some(path)
    };

    if !path.is_absolute()
        || !is_canonical
        || path.as_os_str().len() >= 104
        || !owned_path(path)
        || !path.parent().map(owned_path).unwrap_or(false)
        || !is_valid_name
    {
        return Err(SocketError::UnsafePath(
            "unsafe native workspace socket".into(),
        ));
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::{FileTypeExt, PermissionsExt};
        if !fs::symlink_metadata(path)?.file_type().is_socket() {
            return Err(SocketError::NotASocket(
                "workspace path is not a socket".into(),
            ));
        }
        if fs::symlink_metadata(path.parent().ok_or(SocketError::MissingParent)?)?
            .permissions()
            .mode()
            & 0o077
            != 0
        {
            return Err(SocketError::UnsafePath(
                "workspace socket parent is not private".into(),
            ));
        }
    }
    Ok(())
}
