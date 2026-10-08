// AI-hint: Shared daemon, relay, and service helpers for MiOS native binaries.
// AI-related: tools/native/Cargo.toml, usr/share/mios/mios.toml

pub mod launcher;
pub mod host_tmux;
pub mod process;
pub mod socket;
pub mod ssot;
pub mod tmux_theme;

pub use process::{
    configure_hidden, is_hidden_flag, workspace_lock, ProcessError, CREATE_NO_WINDOW,
};
pub use socket::{
    check_socket_path_length, find_active_socket, find_active_socket_required, owned_path,
    socket_candidates, validate_workspace_socket, verify_socket_owner, SocketError,
    MAX_SOCKET_PATH_LEN,
};
pub use ssot::{
    find_ssot_path, require_port, require_str, resolve_ai_endpoint, resolve_endpoint, ConfigError,
};
