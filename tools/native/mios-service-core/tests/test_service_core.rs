// AI-hint: Comprehensive unit tests for mios-service-core crate.
// AI-related: tools/native/mios-service-core, usr/share/mios/mios.toml

use mios_service_core::{
    check_socket_path_length, configure_hidden, find_active_socket, find_active_socket_required,
    is_hidden_flag, require_port, require_str, resolve_ai_endpoint, socket_candidates,
    validate_workspace_socket, verify_socket_owner, workspace_lock, ConfigError, SocketError,
    CREATE_NO_WINDOW, MAX_SOCKET_PATH_LEN,
};
use std::fs::{self, File};
use std::path::PathBuf;
use std::process::Command;
use tempfile::tempdir;

#[test]
fn test_socket_path_length_bounds() {
    let short_path = PathBuf::from("/run/mios-tmux/human.sock");
    assert!(check_socket_path_length(&short_path).is_ok());

    let exact_limit = PathBuf::from(format!("/tmp/{}", "a".repeat(MAX_SOCKET_PATH_LEN - 5)));
    assert_eq!(exact_limit.as_os_str().len(), MAX_SOCKET_PATH_LEN);
    assert!(check_socket_path_length(&exact_limit).is_ok());

    let long_path = PathBuf::from(format!("/run/mios-tmux/{}", "x".repeat(120)));
    assert!(long_path.as_os_str().len() >= 108);
    match check_socket_path_length(&long_path) {
        Err(SocketError::PathTooLong { len, max, .. }) => {
            assert!(len >= 108);
            assert_eq!(max, 107);
        }
        other => panic!("Expected PathTooLong, got {:?}", other),
    }
}

#[test]
fn test_find_active_socket_first_match() {
    let dir = tempdir().unwrap();
    let s1 = dir.path().join("missing.sock");
    let s2 = dir.path().join("active.sock");
    let s3 = dir.path().join("later.sock");

    File::create(&s2).unwrap();
    File::create(&s3).unwrap();

    let candidates = vec![&s1, &s2, &s3];
    let found = find_active_socket(&candidates).unwrap();
    assert_eq!(found, Some(s2.clone()));

    let required = find_active_socket_required(&candidates).unwrap();
    assert_eq!(required, s2);
}

#[test]
fn test_find_active_socket_none_found() {
    let dir = tempdir().unwrap();
    let s1 = dir.path().join("missing1.sock");
    let s2 = dir.path().join("missing2.sock");

    let candidates = vec![&s1, &s2];
    assert_eq!(find_active_socket(&candidates).unwrap(), None);

    assert!(matches!(
        find_active_socket_required(&candidates),
        Err(SocketError::NoActiveSocket)
    ));

    let empty: Vec<&PathBuf> = Vec::new();
    assert_eq!(find_active_socket(&empty).unwrap(), None);
}

#[test]
fn test_verify_socket_owner() {
    let dir = tempdir().unwrap();
    let sock = dir.path().join("valid.sock");
    File::create(&sock).unwrap();

    assert!(verify_socket_owner(&sock).unwrap());

    let missing = dir.path().join("nonexistent.sock");
    assert!(matches!(
        verify_socket_owner(&missing),
        Err(SocketError::NotFound(_))
    ));
}

#[cfg(unix)]
fn create_test_socket_fixture(path: &std::path::Path) -> Option<std::os::unix::net::UnixListener> {
    let _ = std::fs::remove_file(path);
    Some(std::os::unix::net::UnixListener::bind(path).expect("failed to bind test unix socket"))
}

#[cfg(not(unix))]
fn create_test_socket_fixture(path: &std::path::Path) -> Option<()> {
    File::create(path).expect("failed to create test socket file");
    None
}

#[test]
fn test_socket_candidates_discovery() {
    let dir = tempdir().unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(dir.path(), std::fs::Permissions::from_mode(0o700));
    }
    #[cfg(unix)]
    let root = dir
        .path()
        .canonicalize()
        .unwrap_or_else(|_| dir.path().to_path_buf());
    #[cfg(not(unix))]
    let root = dir.path().to_path_buf();

    let human_sock = root.join("human");
    let _l1 = create_test_socket_fixture(&human_sock);

    let mcp_sock = root.join("mcp-headless");
    let _l2 = create_test_socket_fixture(&mcp_sock);

    let sub_dir = root.join("tmux-1000");
    fs::create_dir(&sub_dir).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&sub_dir, std::fs::Permissions::from_mode(0o700));
    }
    let sub_human = sub_dir.join("human");
    let _l3 = create_test_socket_fixture(&sub_human);

    let candidates = socket_candidates(&root, "human", 0);
    assert!(!candidates.is_empty());
    assert!(candidates.contains(&human_sock));
}

#[test]
fn test_validate_workspace_socket() {
    let dir = tempdir().unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(dir.path(), std::fs::Permissions::from_mode(0o700));
    }
    #[cfg(unix)]
    let root = dir
        .path()
        .canonicalize()
        .unwrap_or_else(|_| dir.path().to_path_buf());
    #[cfg(not(unix))]
    let root = dir.path().to_path_buf();

    let sock = root.join("mios-test.sock");
    let _l = create_test_socket_fixture(&sock);

    // Absolute, valid name starting with "mios-"
    let res = validate_workspace_socket(&sock, "human");
    assert!(res.is_ok());

    // Relative path should fail
    let rel = PathBuf::from("mios-test.sock");
    assert!(validate_workspace_socket(&rel, "human").is_err());
}

#[test]
fn test_require_port_ssot_reading() {
    // Read headscale port from SSOT
    let headscale_port = require_port("headscale").unwrap();
    assert_eq!(headscale_port, 8085);

    // Read llm_light port from SSOT
    let llm_port = require_port("llm_light").unwrap();
    assert_eq!(llm_port, 8500);

    // Read with MIOS_PORT_ prefix format
    let llm_port_prefix = require_port("MIOS_PORT_LLM_LIGHT").unwrap();
    assert_eq!(llm_port_prefix, 8500);
}

#[test]
fn test_require_port_missing_key() {
    let err = require_port("nonexistent_service_port_xyz").unwrap_err();
    assert!(matches!(err, ConfigError::MissingKey(_)));
}

#[test]
fn test_require_port_bounds_and_env_override() {
    std::env::set_var("MIOS_PORT_TEST_BOUNDS", "9999");
    assert_eq!(require_port("test_bounds").unwrap(), 9999);

    std::env::set_var("MIOS_PORT_TEST_BOUNDS", "0");
    assert!(matches!(
        require_port("test_bounds").unwrap_err(),
        ConfigError::InvalidPort { .. }
    ));

    std::env::set_var("MIOS_PORT_TEST_BOUNDS", "70000");
    assert!(matches!(
        require_port("test_bounds").unwrap_err(),
        ConfigError::InvalidPort { .. }
    ));

    std::env::set_var("MIOS_PORT_TEST_BOUNDS", "not_a_number");
    assert!(matches!(
        require_port("test_bounds").unwrap_err(),
        ConfigError::InvalidPort { .. }
    ));

    std::env::remove_var("MIOS_PORT_TEST_BOUNDS");
}

#[test]
fn test_resolve_ai_endpoint_law_5() {
    let ep = resolve_ai_endpoint().unwrap();
    assert!(!ep.is_empty());
    assert!(!ep.contains("api.openai.com"));
    assert!(!ep.contains("generativelanguage.googleapis.com"));
    assert!(!ep.contains("api.anthropic.com"));
    assert!(ep.contains("127.0.0.1") || ep.contains("localhost"));
}

#[test]
fn test_resolve_endpoint_prohibits_cloud() {
    assert!(matches!(
        mios_service_core::ssot::validate_no_cloud_endpoints("https://api.openai.com/v1"),
        Err(ConfigError::ForbiddenCloudEndpoint(_))
    ));
    assert!(matches!(
        mios_service_core::ssot::validate_no_cloud_endpoints(
            "https://generativelanguage.googleapis.com/v1"
        ),
        Err(ConfigError::ForbiddenCloudEndpoint(_))
    ));
    assert!(matches!(
        mios_service_core::ssot::validate_no_cloud_endpoints("https://api.anthropic.com/v1"),
        Err(ConfigError::ForbiddenCloudEndpoint(_))
    ));
    assert!(
        mios_service_core::ssot::validate_no_cloud_endpoints("http://127.0.0.1:8500/v1").is_ok()
    );
}

#[test]
fn test_require_str_reading() {
    let version = require_str("meta.mios_version").unwrap();
    assert_eq!(version, "0.3.0");
}

#[test]
fn test_process_hidden_window_flag() {
    assert_eq!(CREATE_NO_WINDOW, 0x0800_0000);
    assert!(is_hidden_flag(CREATE_NO_WINDOW));
    assert!(is_hidden_flag(CREATE_NO_WINDOW | 0x0000_0001));
    assert!(!is_hidden_flag(0));
    assert!(!is_hidden_flag(0x0000_0001));

    let mut cmd = Command::new("cargo");
    configure_hidden(&mut cmd);
}

#[test]
fn test_workspace_locking() {
    let dir = tempdir().unwrap();
    let sock = dir.path().join("test.sock");
    File::create(&sock).unwrap();

    let lock_file = workspace_lock(&sock, "test.lock").unwrap();
    assert!(dir.path().join("test.lock").exists());
    drop(lock_file);
}
