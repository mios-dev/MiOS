// AI-hint: Library module exports for miosd crate.
// AI-related: src/mios-rs/miosd/src/main.rs, tools/native/mios-gen, automation/33-generate-quadlets.sh, usr/libexec/mios/mios-keyring-autounlock, usr/share/mios/mios.toml, usr/share/mios/configurator/mios.html, /usr/libexec/mios/mios-configurator-launch

// Same robustness lints as the binary target: without these the lint only
// covered `mod drift` reached via main.rs, so lib-only modules were never
// checked.
#![warn(clippy::unwrap_used, clippy::panic, clippy::todo)]

pub mod cli;
pub mod daemon;
pub mod drift;
pub mod native_generator {
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
}
pub mod secret {
    use std::fs;
    #[cfg(unix)]
    use std::io::BufRead;
    use std::io::Write;
    use std::path::Path;
    use std::process::{Command, Stdio};

    /// Securely prompts for a password/secret using GUI (zenity/pinentry) when available,
    /// or console TTY with terminal echo disabled.
    pub fn prompt(
        title: &str,
        message: &str,
        gui: bool,
        tty: bool,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let has_gui_env =
            std::env::var_os("DISPLAY").is_some() || std::env::var_os("WAYLAND_DISPLAY").is_some();
        let try_gui = gui || (!tty && has_gui_env);

        if try_gui {
            if let Ok(secret) = prompt_gui(title, message) {
                return Ok(secret);
            }
        }

        prompt_tty(message)
    }

    /// Prompt via GUI dialog (Quickshell, zenity, or pinentry).
    fn prompt_gui(title: &str, message: &str) -> Result<String, Box<dyn std::error::Error>> {
        // 1. Try Quickshell native Wayland prompt if available
        let qml_path = "/usr/share/mios/quickshell/SecretPrompt.qml";
        if Path::new(qml_path).exists() && std::env::var_os("WAYLAND_DISPLAY").is_some() {
            if let Ok(child) = Command::new("quickshell")
                .arg("-p")
                .arg(qml_path)
                .env("MIOS_SECRET_PROMPT_TITLE", title)
                .env("MIOS_SECRET_PROMPT_MSG", message)
                .stdout(Stdio::piped())
                .stderr(Stdio::null())
                .spawn()
            {
                if let Ok(output) = child.wait_with_output() {
                    if output.status.success() && !output.stdout.is_empty() {
                        let s = String::from_utf8_lossy(&output.stdout);
                        let trimmed = s.trim_end_matches(['\r', '\n']).to_string();
                        if !trimmed.is_empty() {
                            return Ok(trimmed);
                        }
                    }
                }
            }
        }

        // 2. Try zenity
        if let Ok(child) = Command::new("zenity")
            .arg("--password")
            .arg(format!("--title={}", title))
            .arg(format!("--text={}", message))
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
        {
            let output = child.wait_with_output()?;
            if output.status.success() {
                let s = String::from_utf8(output.stdout)?;
                let trimmed = s.trim_end_matches(['\r', '\n']).to_string();
                return Ok(trimmed);
            }
        }

        // 2. Try pinentry
        for pinentry_bin in &["pinentry-gnome3", "pinentry"] {
            if let Ok(mut child) = Command::new(pinentry_bin)
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::null())
                .spawn()
            {
                if let Some(mut stdin) = child.stdin.take() {
                    let script = format!(
                        "SETTITLE {}\nSETDESC {}\nSETPROMPT Password:\nGETPIN\nBYE\n",
                        title, message
                    );
                    let _ = stdin.write_all(script.as_bytes());
                }
                let output = child.wait_with_output()?;
                if output.status.success() {
                    let text = String::from_utf8_lossy(&output.stdout);
                    for line in text.lines() {
                        if let Some(pin) = line.strip_prefix("D ") {
                            return Ok(pin.to_string());
                        }
                    }
                }
            }
        }

        Err("no GUI prompt available or prompt dismissed".into())
    }

    /// Prompt via console TTY with terminal echo disabled.
    fn prompt_tty(message: &str) -> Result<String, Box<dyn std::error::Error>> {
        eprint!("{}", message);
        let _ = std::io::stderr().flush();

        let secret = read_password_no_echo()?;
        eprintln!(); // newline after secret input
        Ok(secret)
    }

    /// Read password from stdin or /dev/tty with echo disabled via termios.
    fn read_password_no_echo() -> Result<String, Box<dyn std::error::Error>> {
        #[cfg(unix)]
        {
            use std::os::unix::io::AsRawFd;

            let tty_file = fs::OpenOptions::new()
                .read(true)
                .write(true)
                .open("/dev/tty");

            let (fd, mut reader): (i32, Box<dyn BufRead>) = match tty_file {
                Ok(file) => {
                    let raw_fd = file.as_raw_fd();
                    (raw_fd, Box::new(std::io::BufReader::new(file)))
                }
                Err(_) => {
                    let stdin = std::io::stdin();
                    (stdin.as_raw_fd(), Box::new(stdin.lock()))
                }
            };

            let mut termios = std::mem::MaybeUninit::<libc::termios>::uninit();
            let is_tty = unsafe { libc::isatty(fd) == 1 };

            if is_tty {
                unsafe {
                    if libc::tcgetattr(fd, termios.as_mut_ptr()) == 0 {
                        let mut raw = termios.assume_init();
                        let orig = raw;
                        raw.c_lflag &= !(libc::ECHO | libc::ECHONL);
                        libc::tcsetattr(fd, libc::TCSANOW, &raw);

                        struct TermiosReset {
                            fd: i32,
                            orig: libc::termios,
                        }
                        impl Drop for TermiosReset {
                            fn drop(&mut self) {
                                unsafe {
                                    libc::tcsetattr(self.fd, libc::TCSANOW, &self.orig);
                                }
                            }
                        }

                        let _guard = TermiosReset { fd, orig };
                        let mut input = String::new();
                        reader.read_line(&mut input)?;
                        return Ok(input.trim_end_matches(['\r', '\n']).to_string());
                    }
                }
            }

            let mut input = String::new();
            reader.read_line(&mut input)?;
            Ok(input.trim_end_matches(['\r', '\n']).to_string())
        }

        #[cfg(not(unix))]
        {
            let mut input = String::new();
            std::io::stdin().read_line(&mut input)?;
            Ok(input.trim_end_matches(['\r', '\n']).to_string())
        }
    }

    /// Store secret in native Linux Keyring via secret-tool (Secret Service) or safe fallback.
    pub fn set(service: &str, key: &str, value: &str) -> Result<(), Box<dyn std::error::Error>> {
        let child = Command::new("secret-tool")
            .arg("store")
            .arg(format!("--label=MiOS Secret [{}/{}]", service, key))
            .arg("service")
            .arg(service)
            .arg("key")
            .arg(key)
            .stdin(Stdio::piped())
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn();

        if let Ok(mut c) = child {
            if let Some(mut stdin) = c.stdin.take() {
                stdin.write_all(value.as_bytes())?;
            }
            let status = c.wait()?;
            if status.success() {
                return Ok(());
            }
        }

        // Fallback: secure local keyring store in /run/user/<uid>/mios/keyring
        let keyring_dir = get_keyring_fallback_dir(service)?;
        fs::create_dir_all(&keyring_dir)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = fs::set_permissions(&keyring_dir, fs::Permissions::from_mode(0o700));
        }

        let secret_file = keyring_dir.join(key);
        fs::write(&secret_file, value)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = fs::set_permissions(&secret_file, fs::Permissions::from_mode(0o600));
        }

        Ok(())
    }

    /// Retrieve secret from native Linux Keyring via secret-tool or safe fallback.
    pub fn get(service: &str, key: &str) -> Result<String, Box<dyn std::error::Error>> {
        let output = Command::new("secret-tool")
            .arg("lookup")
            .arg("service")
            .arg(service)
            .arg("key")
            .arg(key)
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .output();

        if let Ok(out) = output {
            if out.status.success() && !out.stdout.is_empty() {
                let val = String::from_utf8(out.stdout)?;
                return Ok(val.trim_end_matches(['\r', '\n']).to_string());
            }
        }

        // Fallback lookup
        let keyring_dir = get_keyring_fallback_dir(service)?;
        let secret_file = keyring_dir.join(key);
        if secret_file.is_file() {
            let content = fs::read_to_string(&secret_file)?;
            return Ok(content.trim_end_matches(['\r', '\n']).to_string());
        }

        Err(format!("secret not found for service='{}', key='{}'", service, key).into())
    }

    fn get_keyring_fallback_dir(
        service: &str,
    ) -> Result<std::path::PathBuf, Box<dyn std::error::Error>> {
        let mut cand = None;
        if let Ok(run_dir) = std::env::var("XDG_RUNTIME_DIR") {
            if !run_dir.is_empty() {
                cand = Some(std::path::PathBuf::from(run_dir));
            }
        }
        if cand.is_none() {
            #[cfg(unix)]
            let uid = unsafe { libc::getuid() };
            #[cfg(not(unix))]
            let uid = 1000u32;
            let run_user = std::path::PathBuf::from(format!("/run/user/{}", uid));
            if run_user.is_dir() {
                cand = Some(run_user);
            } else if let Ok(home) = std::env::var("HOME") {
                cand = Some(std::path::PathBuf::from(home).join(".local").join("share"));
            } else {
                cand = Some(std::env::temp_dir().join(format!("mios-{}", uid)));
            }
        }
        let base = cand.unwrap_or_else(std::env::temp_dir);
        Ok(base.join("mios").join("keyring").join(service))
    }

    /// Pipeline safety net: recursively scans files for unshielded credentials, private keys, or tokens.
    pub fn scan(target: &Path, strict: bool) -> Result<usize, Box<dyn std::error::Error>> {
        let mut findings = 0;
        let mut files = Vec::new();

        collect_files(target, &mut files)?;

        let priv_key_re = regex::Regex::new(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----")?;
        let ghp_token_re = regex::Regex::new(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")?;
        let openai_re = regex::Regex::new(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9_-]{32,}\b")?;
        let aws_re = regex::Regex::new(r"\bAKIA[0-9A-Z]{16}\b")?;
        let hardcoded_pwd_re = regex::Regex::new(
            r#"(?i)^\s*(?:export\s+)?([A-Za-z0-9_]*(?:PASSWORD|SECRET|API_KEY))\s*=\s*["']([^"'$%{\s]{6,})["']"#,
        )?;

        for path in files {
            let content = match fs::read_to_string(&path) {
                Ok(c) => c,
                Err(_) => continue, // ignore non-UTF-8 binary files
            };

            for (lineno, line) in content.lines().enumerate() {
                if line.trim_start().starts_with('#') || line.trim_start().starts_with("//") {
                    continue;
                }

                if priv_key_re.is_match(line) {
                    eprintln!(
                        "[pipeline-safety-net] {}:{} UNSHIELDED PRIVATE KEY DETECTED",
                        path.display(),
                        lineno + 1
                    );
                    findings += 1;
                } else if ghp_token_re.is_match(line) {
                    eprintln!(
                        "[pipeline-safety-net] {}:{} PLAINTEXT GITHUB TOKEN DETECTED",
                        path.display(),
                        lineno + 1
                    );
                    findings += 1;
                } else if openai_re.is_match(line) {
                    eprintln!(
                        "[pipeline-safety-net] {}:{} PLAINTEXT API TOKEN DETECTED",
                        path.display(),
                        lineno + 1
                    );
                    findings += 1;
                } else if aws_re.is_match(line) {
                    eprintln!(
                        "[pipeline-safety-net] {}:{} PLAINTEXT AWS KEY DETECTED",
                        path.display(),
                        lineno + 1
                    );
                    findings += 1;
                } else if strict {
                    if let Some(caps) = hardcoded_pwd_re.captures(line) {
                        let key = caps.get(1).map_or("", |m| m.as_str());
                        eprintln!(
                        "[pipeline-safety-net] {}:{} HARDCODED CREDENTIAL '{}' DETECTED -- store via miosd secret set",
                        path.display(),
                        lineno + 1,
                        key
                    );
                        findings += 1;
                    }
                }
            }
        }

        Ok(findings)
    }

    fn collect_files(dir: &Path, out: &mut Vec<std::path::PathBuf>) -> Result<(), std::io::Error> {
        if dir.is_file() {
            out.push(dir.to_path_buf());
            return Ok(());
        }

        if !dir.is_dir() {
            return Ok(());
        }

        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let p = entry.path();
            let fname = entry.file_name().to_string_lossy().to_string();

            if fname.starts_with('.') || fname == "target" || fname == "node_modules" {
                continue;
            }

            if p.is_dir() {
                collect_files(&p, out)?;
            } else if p.is_file() {
                out.push(p);
            }
        }

        Ok(())
    }

    #[cfg(test)]
    mod tests {
        // Test code: a panic here IS the assertion. Scoped so production code stays under the lint.
        #![allow(clippy::unwrap_used)]

        use super::*;
        use tempfile::tempdir;

        #[test]
        fn test_secret_fallback_store_and_get() {
            let tmp = tempdir().unwrap();
            let old_run = std::env::var("XDG_RUNTIME_DIR").ok();
            std::env::set_var("XDG_RUNTIME_DIR", tmp.path());

            let res_set = set("test-service", "my-api-key", "super-secret-token-123");
            assert!(res_set.is_ok(), "set should succeed: {:?}", res_set);

            let res_get = get("test-service", "my-api-key");
            assert_eq!(
                res_get.unwrap(),
                "super-secret-token-123",
                "retrieved secret should match"
            );

            if let Some(r) = old_run {
                std::env::set_var("XDG_RUNTIME_DIR", r);
            }
        }

        #[test]
        fn test_scan_detects_unshielded_private_key() {
            let tmp = tempdir().unwrap();
            let test_file = tmp.path().join("leaked_key.pem");
            fs::write(
            &test_file,
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n",
        )
        .unwrap();

            let count = scan(tmp.path(), false).unwrap();
            assert_eq!(count, 1, "scanner must catch unshielded RSA private key");
        }

        #[test]
        fn test_scan_detects_tokens() {
            let tmp = tempdir().unwrap();
            let test_file = tmp.path().join("config.sh");
            fs::write(
                &test_file,
                format!(
                    "export GITHUB_TOKEN=ghp_{}\n",
                    "abcdefghijklmnopqrstuvwxyz0123456789"
                ),
            )
            .unwrap();

            let count = scan(tmp.path(), false).unwrap();
            assert_eq!(count, 1, "scanner must catch plaintext GitHub token");
        }

        #[test]
        fn test_scan_strict_detects_hardcoded_secret() {
            let tmp = tempdir().unwrap();
            let test_file = tmp.path().join("service.conf");
            fs::write(
                &test_file,
                "DATABASE_PASSWORD=\"very_secret_cleartext_password\"\n",
            )
            .unwrap();

            let count_strict = scan(tmp.path(), true).unwrap();
            assert_eq!(
                count_strict, 1,
                "strict scanner must catch hardcoded cleartext password"
            );

            let count_normal = scan(tmp.path(), false).unwrap();
            assert_eq!(
                count_normal, 0,
                "normal scanner should ignore without strict"
            );
        }
    }
}
pub mod server {
    use std::collections::HashMap;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::sync::Arc;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::{TcpListener, TcpStream};

    #[derive(Debug, Clone)]
    pub struct ConfigServerConfig {
        pub bind_addr: String,
        pub html_path: PathBuf,
        /// The user tier operator saves land in (resolver's user path).
        pub user_toml_path: PathBuf,
        /// [portal].config_max_body_bytes.
        pub max_body_bytes: usize,
        /// Root the six-tier SSOT resolves under; None is the installed FHS tiers
        /// (or the source tree's vendor file when MiOS is not installed).
        pub ssot_root: Option<PathBuf>,
    }

    impl ConfigServerConfig {
        /// The listen port is `[ports].agent_pipe` (the route agent-pipe's portal
        /// serves) unless given; an unresolvable port is an error, never a literal.
        pub fn resolve(bind: Option<String>, port: Option<u16>) -> Result<Self, String> {
            let bind_addr = match bind.or_else(|| std::env::var("MIOS_CONFIG_BIND_ADDR").ok()) {
                Some(b) => b,
                None => {
                    let port = match port {
                        Some(p) => p,
                        None => mios_resolver::runtime::require_port("MIOS_PORTS_AGENT_PIPE")
                            .map_err(|e| e.to_string())?,
                    };
                    format!("127.0.0.1:{port}")
                }
            };

            let root = std::env::var("MIOS_ROOT").unwrap_or_else(|_| ".".to_string());
            let root_path = Path::new(&root);

            let html_path = if let Ok(custom) = std::env::var("MIOS_CONFIGURATOR_HTML") {
                PathBuf::from(custom)
            } else if Path::new("/usr/share/mios/configurator/mios.html").is_file() {
                PathBuf::from("/usr/share/mios/configurator/mios.html")
            } else if root_path
                .join("usr/share/mios/configurator/mios.html")
                .is_file()
            {
                root_path.join("usr/share/mios/configurator/mios.html")
            } else {
                PathBuf::from("usr/share/mios/configurator/mios.html")
            };

            let ssot_root = std::env::var("MIOS_ROOT")
                .ok()
                .filter(|r| !r.is_empty())
                .map(PathBuf::from);
            let user_toml_path = mios_resolver::user_toml_path(ssot_root.as_deref());
            let raw_max = mios_resolver::runtime::require("MIOS_PORTAL_CONFIG_MAX_BODY_BYTES")
                .map_err(|e| e.to_string())?;
            let max_body_bytes = raw_max.parse::<usize>().map_err(|_| {
                format!("MIOS_PORTAL_CONFIG_MAX_BODY_BYTES={raw_max} is not a byte count")
            })?;

            Ok(Self {
                bind_addr,
                html_path,
                user_toml_path,
                max_body_bytes,
                ssot_root,
            })
        }
    }

    #[derive(Debug, Clone, PartialEq, Eq)]
    pub struct HttpRequest {
        pub method: String,
        pub path: String,
        pub headers: HashMap<String, String>,
        pub body: Vec<u8>,
    }

    #[derive(Debug, Clone)]
    pub struct HttpResponse {
        pub status_code: u16,
        pub status_text: &'static str,
        pub headers: Vec<(String, String)>,
        pub body: Vec<u8>,
    }

    impl HttpResponse {
        pub fn new(status_code: u16, status_text: &'static str) -> Self {
            Self {
                status_code,
                status_text,
                headers: vec![
                    ("Server".to_string(), "miosd-config-server".to_string()),
                    ("Connection".to_string(), "close".to_string()),
                ],
                body: Vec::new(),
            }
        }

        pub fn with_header(mut self, key: &str, value: &str) -> Self {
            self.headers.push((key.to_string(), value.to_string()));
            self
        }

        pub fn with_body(mut self, content_type: &str, body: Vec<u8>) -> Self {
            self.headers
                .push(("Content-Type".to_string(), content_type.to_string()));
            self.headers
                .push(("Content-Length".to_string(), body.len().to_string()));
            self.body = body;
            self
        }

        pub fn html(status_code: u16, status_text: &'static str, html: String) -> Self {
            Self::new(status_code, status_text)
                .with_body("text/html; charset=utf-8", html.into_bytes())
        }

        pub fn json(status_code: u16, status_text: &'static str, json_str: String) -> Self {
            Self::new(status_code, status_text)
                .with_body("application/json; charset=utf-8", json_str.into_bytes())
        }

        pub fn toml(status_code: u16, status_text: &'static str, toml_str: String) -> Self {
            Self::new(status_code, status_text)
                .with_body("application/toml; charset=utf-8", toml_str.into_bytes())
        }

        pub fn redirect(location: &str) -> Self {
            Self::new(302, "Found")
                .with_header("Location", location)
                .with_body(
                    "text/plain",
                    format!("Redirecting to {}", location).into_bytes(),
                )
        }

        pub fn to_bytes(&self) -> Vec<u8> {
            let mut out = Vec::new();
            let status_line = format!("HTTP/1.1 {} {}\r\n", self.status_code, self.status_text);
            out.extend_from_slice(status_line.as_bytes());

            for (k, v) in &self.headers {
                let header_line = format!("{}: {}\r\n", k, v);
                out.extend_from_slice(header_line.as_bytes());
            }
            out.extend_from_slice(b"\r\n");
            out.extend_from_slice(&self.body);
            out
        }
    }

    pub fn parse_http_request(raw: &[u8]) -> Option<HttpRequest> {
        let mut headers_end = 0;
        for i in 0..raw.len().saturating_sub(3) {
            if &raw[i..i + 4] == b"\r\n\r\n" {
                headers_end = i;
                break;
            }
        }
        if headers_end == 0 {
            return None;
        }

        let header_str = std::str::from_utf8(&raw[..headers_end]).ok()?;
        let mut lines = header_str.lines();
        let request_line = lines.next()?;
        let mut req_parts = request_line.split_whitespace();
        let method = req_parts.next()?.to_string();
        let raw_path = req_parts.next()?.to_string();

        let path = if let Some(idx) = raw_path.find('?') {
            raw_path[..idx].to_string()
        } else {
            raw_path
        };

        let mut headers = HashMap::new();
        for line in lines {
            if let Some((k, v)) = line.split_once(':') {
                headers.insert(k.trim().to_ascii_lowercase(), v.trim().to_string());
            }
        }

        let body_start = headers_end + 4;
        let mut body = if body_start < raw.len() {
            raw[body_start..].to_vec()
        } else {
            Vec::new()
        };

        if let Some(len_str) = headers.get("content-length") {
            if let Ok(expected_len) = len_str.parse::<usize>() {
                if body.len() > expected_len {
                    body.truncate(expected_len);
                }
            }
        }

        Some(HttpRequest {
            method,
            path,
            headers,
            body,
        })
    }

    /// The live configuration: the resolver's six-tier merge (vendor < vendor.d <
    /// host < host.d < user < user.d, [ports] derived), serialized as one valid
    /// TOML document. Splicing the tier files' text together produced duplicate
    /// tables whenever a host override repeated a vendor table.
    pub fn read_layered_toml(config: &ConfigServerConfig) -> Result<String, String> {
        let merged = mios_resolver::resolve_merged(config.ssot_root.as_deref(), false)
            .map_err(|e| format!("the layered mios.toml did not resolve: {e}"))?;
        toml::to_string(&merged).map_err(|e| format!("the merged config did not serialize: {e}"))
    }

    /// Sections whose loss bricks a deploy: a save may not drop one the live
    /// config has. Mirrors mios_pipe.kernel.config._VALIDATE_CRITICAL_SECTIONS.
    const CRITICAL_SECTIONS: [&str; 2] = ["identity", "ports"];

    /// The configurator-save safety net, the same rules agent-pipe's
    /// validate_config applies: parseable TOML, no dropped critical section, a
    /// non-empty [identity].mios_user when present, and every scalar [ports]
    /// value an integer in 1..=65535 (stack_id and nested values excepted).
    /// The size ceiling is enforced while the request is read.
    pub fn validate_portal_save(body: &str, config: &ConfigServerConfig) -> Vec<String> {
        let posted = match body.parse::<toml::Value>() {
            Ok(v) => v,
            Err(e) => return vec![format!("Invalid TOML: {e}")],
        };
        let live = mios_resolver::resolve_merged(config.ssot_root.as_deref(), false).ok();
        let mut errors = Vec::new();
        for sec in CRITICAL_SECTIONS {
            let live_has = live
                .as_ref()
                .and_then(|l| l.get(sec))
                .and_then(toml::Value::as_table)
                .is_some_and(|t| !t.is_empty());
            let posted_has = posted
                .get(sec)
                .and_then(toml::Value::as_table)
                .is_some_and(|t| !t.is_empty());
            if live_has && !posted_has {
                errors.push(format!(
                "Refusing to drop critical [{sec}] section -- it is present in the live config and losing it bricks the deploy."
            ));
            }
        }
        if let Some(mu) = posted.get("identity").and_then(|i| i.get("mios_user")) {
            if mu.as_str().is_none_or(|s| s.trim().is_empty()) {
                errors.push("[identity].mios_user must be a non-empty string.".to_string());
            }
        }
        if let Some(ports) = posted.get("ports").and_then(toml::Value::as_table) {
            for (k, v) in ports {
                if k == "stack_id" || v.is_table() || v.is_array() {
                    continue;
                }
                match v.as_integer() {
                    Some(p) if (1..=65535).contains(&p) => {}
                    Some(p) => errors.push(format!(
                        "[ports].{k} = {p} is out of the valid 1-65535 range."
                    )),
                    None => {
                        errors.push(format!("[ports].{k} must be an integer 1-65535 (got {v})."))
                    }
                }
            }
        }
        errors
    }

    /// Persist a configurator save into the user tier: only what differs from
    /// vendor..host.d (ports derived), written atomically -- the same contract as
    /// agent-pipe's write_user_config. Returns the path and bytes written.
    pub fn save_user_tier(
        config: &ConfigServerConfig,
        body: &str,
    ) -> Result<(PathBuf, usize), String> {
        let posted = body
            .parse::<toml::Value>()
            .map_err(|e| format!("Invalid TOML: {e}"))?;
        let base = mios_resolver::resolve_below_user(config.ssot_root.as_deref())
            .map_err(|e| format!("the lower tiers did not resolve: {e}"))?;
        let delta = mios_resolver::merge::diff_against(&posted, &base)
            .unwrap_or_else(|| toml::Value::Table(toml::Table::new()));
        let text =
            toml::to_string(&delta).map_err(|e| format!("the delta did not serialize: {e}"))?;
        let dest = &config.user_toml_path;
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent).map_err(|e| format!("Failed to create config dir: {e}"))?;
        }
        let tmp_path = dest.with_extension("toml.tmp");
        fs::write(&tmp_path, &text).map_err(|e| format!("Failed to write temporary file: {e}"))?;
        fs::rename(&tmp_path, dest).map_err(|e| format!("Failed to persist config: {e}"))?;
        Ok((dest.clone(), text.len()))
    }

    pub fn handle_request(req: &HttpRequest, config: &ConfigServerConfig) -> HttpResponse {
        let cors_resp = |resp: HttpResponse| {
            resp.with_header("Access-Control-Allow-Origin", "*")
                .with_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                .with_header("Access-Control-Allow-Headers", "Content-Type")
        };

        if req.method == "OPTIONS" {
            return cors_resp(
                HttpResponse::new(204, "No Content").with_header("Content-Length", "0"),
            );
        }

        let mut resp = match (req.method.as_str(), req.path.as_str()) {
            ("GET", "/") | ("HEAD", "/") => cors_resp(HttpResponse::redirect("/configure")),

            ("GET", "/configure")
            | ("HEAD", "/configure")
            | ("GET", "/portal/configurator")
            | ("HEAD", "/portal/configurator") => {
                if config.html_path.is_file() {
                    match fs::read_to_string(&config.html_path) {
                        Ok(content) => cors_resp(HttpResponse::html(200, "OK", content)),
                        Err(e) => cors_resp(HttpResponse::html(
                            500,
                            "Internal Server Error",
                            format!("<h1>Error reading configurator</h1><pre>{}</pre>", e),
                        )),
                    }
                } else {
                    cors_resp(HttpResponse::html(
                        404,
                        "Not Found",
                        format!(
                            "<h1>Configurator Not Found</h1><p>Expected mios.html at {:?}</p>",
                            config.html_path
                        ),
                    ))
                }
            }

            ("GET", "/portal/config") | ("HEAD", "/portal/config") => {
                match read_layered_toml(config) {
                    Ok(toml_data) => cors_resp(HttpResponse::toml(200, "OK", toml_data)),
                    Err(e) => cors_resp(HttpResponse::json(
                        500,
                        "Internal Server Error",
                        serde_json::json!({ "errors": [e] }).to_string(),
                    )),
                }
            }

            ("POST", "/portal/config") => {
                let body_str = match std::str::from_utf8(&req.body) {
                    Ok(s) => s,
                    Err(_) => {
                        return cors_resp(HttpResponse::json(
                            422,
                            "Unprocessable Entity",
                            r#"{"errors":["Request body must be valid UTF-8"]}"#.to_string(),
                        ));
                    }
                };

                let errors = validate_portal_save(body_str, config);
                if !errors.is_empty() {
                    return cors_resp(HttpResponse::json(
                        422,
                        "Unprocessable Entity",
                        serde_json::json!({ "errors": errors }).to_string(),
                    ));
                }

                match save_user_tier(config, body_str) {
                    Ok((path, bytes)) => cors_resp(HttpResponse::json(
                        200,
                        "OK",
                        serde_json::json!({
                            "status": "ok",
                            "message": format!("Saved to {}", path.display()),
                            "bytes": bytes,
                        })
                        .to_string(),
                    )),
                    Err(e) => cors_resp(HttpResponse::json(
                        500,
                        "Internal Server Error",
                        serde_json::json!({ "errors": [e] }).to_string(),
                    )),
                }
            }

            ("GET", "/health")
            | ("HEAD", "/health")
            | ("GET", "/healthz")
            | ("HEAD", "/healthz") => cors_resp(HttpResponse::json(
                200,
                "OK",
                r#"{"status":"ok","engine":"miosd-config-server"}"#.to_string(),
            )),

            _ => cors_resp(HttpResponse::new(404, "Not Found").with_body(
                "text/plain",
                format!("Path not found: {}", req.path).into_bytes(),
            )),
        };

        if req.method == "HEAD" {
            resp.body.clear();
        }
        resp
    }

    /// Read one whole request: headers, then Content-Length bytes of body. A
    /// single read() truncated any body past one TCP segment, so a configurator
    /// save of the full config arrived as invalid TOML. The body ceiling is
    /// [portal].config_max_body_bytes.
    async fn read_request(
        stream: &mut TcpStream,
        max_body: usize,
    ) -> std::io::Result<Option<Vec<u8>>> {
        let mut raw = Vec::new();
        let mut chunk = [0u8; 65536];
        loop {
            let n = stream.read(&mut chunk).await?;
            if n == 0 {
                return Ok((!raw.is_empty()).then_some(raw));
            }
            raw.extend_from_slice(&chunk[..n]);
            let Some(end) = raw.windows(4).position(|w| w == b"\r\n\r\n") else {
                if raw.len() > max_body {
                    return Ok(None);
                }
                continue;
            };
            let head = String::from_utf8_lossy(&raw[..end]).to_ascii_lowercase();
            let want = head
                .lines()
                .find_map(|l| l.strip_prefix("content-length:"))
                .and_then(|v| v.trim().parse::<usize>().ok())
                .unwrap_or(0);
            if want > max_body {
                return Ok(None);
            }
            if raw.len() >= end + 4 + want {
                return Ok(Some(raw));
            }
        }
    }

    pub async fn handle_stream(
        mut stream: TcpStream,
        config: Arc<ConfigServerConfig>,
    ) -> Result<(), std::io::Error> {
        let raw = match read_request(&mut stream, config.max_body_bytes).await? {
            Some(raw) => raw,
            None => {
                let resp = HttpResponse::new(413, "Payload Too Large").with_body(
                    "text/plain",
                    b"Request exceeds [portal].config_max_body_bytes".to_vec(),
                );
                stream.write_all(&resp.to_bytes()).await?;
                let _ = stream.shutdown().await;
                return Ok(());
            }
        };

        let resp = match parse_http_request(&raw) {
            Some(req) => handle_request(&req, &config),
            None => HttpResponse::new(400, "Bad Request")
                .with_body("text/plain", b"Malformed HTTP request".to_vec()),
        };

        let resp_bytes = resp.to_bytes();
        stream.write_all(&resp_bytes).await?;
        stream.flush().await?;
        let _ = stream.shutdown().await;
        Ok(())
    }

    pub async fn run_config_server(
        config: ConfigServerConfig,
        mut shutdown_rx: Option<tokio::sync::oneshot::Receiver<()>>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let listener = TcpListener::bind(&config.bind_addr).await?;
        let config_arc = Arc::new(config);

        loop {
            tokio::select! {
                accept_res = listener.accept() => {
                    match accept_res {
                        Ok((stream, _peer)) => {
                            let cfg = Arc::clone(&config_arc);
                            tokio::spawn(async move {
                                let _ = handle_stream(stream, cfg).await;
                            });
                        }
                        Err(e) => {
                            eprintln!("[miosd-server] Accept error: {}", e);
                        }
                    }
                }
                _ = async {
                    match &mut shutdown_rx {
                        Some(rx) => {
                            let _ = rx.await;
                        }
                        None => {
                            std::future::pending::<()>().await;
                        }
                    }
                } => {
                    break;
                }
            }
        }

        Ok(())
    }

    #[cfg(test)]
    mod tests {
        // Test code: a panic here IS the assertion. Scoped so production code stays under the lint.
        #![allow(clippy::panic)]

        use super::*;

        #[test]
        fn test_parse_http_request_get() {
            let raw =
                b"GET /configure HTTP/1.1\r\nHost: localhost:8700\r\nUser-Agent: test\r\n\r\n";
            let req = parse_http_request(raw);
            assert!(req.is_some());
            let r = req.as_ref().unwrap_or_else(|| unreachable!());
            assert_eq!(r.method, "GET");
            assert_eq!(r.path, "/configure");
            assert_eq!(
                r.headers.get("host").map(String::as_str),
                Some("localhost:8700")
            );
            assert!(r.body.is_empty());
        }

        #[test]
        fn test_parse_http_request_post_with_body() {
            let raw = b"POST /portal/config HTTP/1.1\r\nHost: localhost:8700\r\nContent-Length: 12\r\n\r\nhello=world\n";
            let req = parse_http_request(raw);
            assert!(req.is_some());
            let r = req.as_ref().unwrap_or_else(|| unreachable!());
            assert_eq!(r.method, "POST");
            assert_eq!(r.path, "/portal/config");
            assert_eq!(r.body, b"hello=world\n");
        }

        #[test]
        fn test_response_to_bytes() {
            let resp = HttpResponse::html(200, "OK", "<h1>Test</h1>".to_string());
            let bytes = resp.to_bytes();
            let s = String::from_utf8_lossy(&bytes);
            assert!(s.starts_with("HTTP/1.1 200 OK\r\n"));
            assert!(s.contains("Content-Type: text/html; charset=utf-8\r\n"));
            assert!(s.ends_with("\r\n\r\n<h1>Test</h1>"));
        }

        #[test]
        fn test_get_config_is_the_merged_ssot_as_valid_toml() {
            let tmp_dir = tempfile::tempdir().unwrap_or_else(|e| panic!("{}", e));
            let root = tmp_dir.path();
            fs::create_dir_all(root.join("usr/share/mios")).unwrap_or_else(|e| panic!("{}", e));
            fs::create_dir_all(root.join("etc/mios")).unwrap_or_else(|e| panic!("{}", e));
            fs::write(
                root.join("usr/share/mios/mios.toml"),
                "[ai]\nendpoint = \"vendor\"\nagent_model = \"m\"\n",
            )
            .unwrap_or_else(|e| panic!("{}", e));
            // The host tier repeats [ai]: spliced text would be a duplicate table.
            fs::write(
                root.join("etc/mios/mios.toml"),
                "[ai]\nendpoint = \"host\"\n",
            )
            .unwrap_or_else(|e| panic!("{}", e));
            let config = ConfigServerConfig {
                bind_addr: String::new(),
                html_path: root.join("mios.html"),
                user_toml_path: root.join("home/.config/mios/mios.toml"),
                max_body_bytes: 1 << 20,
                ssot_root: Some(root.to_path_buf()),
            };
            let req = HttpRequest {
                method: "GET".to_string(),
                path: "/portal/config".to_string(),
                headers: HashMap::new(),
                body: Vec::new(),
            };
            let resp = handle_request(&req, &config);
            assert_eq!(resp.status_code, 200);
            let body = String::from_utf8_lossy(&resp.body);
            let parsed: toml::Value = body.parse().unwrap_or_else(|e| panic!("{e}: {body}"));
            assert_eq!(parsed["ai"]["endpoint"].as_str(), Some("host"));
            assert_eq!(parsed["ai"]["agent_model"].as_str(), Some("m"));
        }

        #[test]
        fn test_post_config_saves_only_the_delta_to_the_user_tier() {
            let tmp_dir = tempfile::tempdir().unwrap_or_else(|e| panic!("{}", e));
            let root = tmp_dir.path();
            fs::create_dir_all(root.join("usr/share/mios")).unwrap_or_else(|e| panic!("{}", e));
            fs::write(
                root.join("usr/share/mios/mios.toml"),
                "[ai]\nendpoint = \"vendor\"\nagent_model = \"m\"\n",
            )
            .unwrap_or_else(|e| panic!("{}", e));
            let user = root.join("home/.config/mios/mios.toml");
            let config = ConfigServerConfig {
                bind_addr: String::new(),
                html_path: root.join("mios.html"),
                user_toml_path: user.clone(),
                max_body_bytes: 1 << 20,
                ssot_root: Some(root.to_path_buf()),
            };
            let (path, _) = save_user_tier(
                &config,
                "[ai]\nendpoint = \"operator\"\nagent_model = \"m\"\n",
            )
            .unwrap_or_else(|e| panic!("{e}"));
            assert_eq!(path, user);
            let saved: toml::Value = fs::read_to_string(&user)
                .unwrap_or_else(|e| panic!("{e}"))
                .parse()
                .unwrap_or_else(|e| panic!("{e}"));
            assert_eq!(saved["ai"]["endpoint"].as_str(), Some("operator"));
            assert!(
                saved["ai"].get("agent_model").is_none(),
                "unchanged keys stay in lower tiers: {saved}"
            );
        }

        async fn received(req: Vec<u8>, max_body: usize) -> Option<Vec<u8>> {
            let listener = TcpListener::bind("127.0.0.1:0")
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            let addr = listener.local_addr().unwrap_or_else(|e| panic!("{}", e));
            let srv = tokio::spawn(async move {
                let (mut stream, _) = listener.accept().await.unwrap_or_else(|e| panic!("{}", e));
                read_request(&mut stream, max_body)
                    .await
                    .unwrap_or_else(|e| panic!("{}", e))
            });
            let mut client = TcpStream::connect(addr)
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            client
                .write_all(&req)
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            srv.await.unwrap_or_else(|e| panic!("{}", e))
        }

        fn post(body_len: usize) -> Vec<u8> {
            let body = "x".repeat(body_len);
            format!(
            "POST /portal/config HTTP/1.1\r\nHost: x\r\nContent-Length: {body_len}\r\n\r\n{body}"
        )
            .into_bytes()
        }

        #[test]
        fn test_portal_save_rules_match_agent_pipe() {
            let tmp_dir = tempfile::tempdir().unwrap_or_else(|e| panic!("{}", e));
            let root = tmp_dir.path();
            fs::create_dir_all(root.join("usr/share/mios")).unwrap_or_else(|e| panic!("{}", e));
            fs::write(
                root.join("usr/share/mios/mios.toml"),
                "[identity]\nmios_user = \"u\"\n[ports]\na = 1\n",
            )
            .unwrap_or_else(|e| panic!("{}", e));
            let config = ConfigServerConfig {
                bind_addr: String::new(),
                html_path: root.join("mios.html"),
                user_toml_path: root.join("u.toml"),
                max_body_bytes: 1 << 20,
                ssot_root: Some(root.to_path_buf()),
            };
            let ok = "[identity]\nmios_user = \"u\"\n[ports]\nstack_id = 0\na = 9\nlist = [1]\n[ports.categories.x]\nbase = 0\n";
            assert!(validate_portal_save(ok, &config).is_empty());
            assert_eq!(
                validate_portal_save("[ports]\na = 1\n", &config).len(),
                1,
                "dropped [identity]"
            );
            assert_eq!(
                validate_portal_save("[identity]\nmios_user = \" \"\n[ports]\na = 1\n", &config)
                    .len(),
                1
            );
            assert_eq!(
                validate_portal_save(
                    "[identity]\nmios_user = \"u\"\n[ports]\na = 70000\nb = \"x\"\n",
                    &config
                )
                .len(),
                2
            );
            assert_eq!(validate_portal_save("not = = toml", &config).len(), 1);
        }

        #[tokio::test]
        async fn test_a_body_larger_than_one_read_arrives_whole() {
            let req = post(200_000);
            let got = received(req.clone(), 1 << 20).await;
            assert_eq!(got.map(|r| r.len()), Some(req.len()));
        }

        #[tokio::test]
        async fn test_a_body_over_the_ssot_ceiling_is_refused() {
            assert_eq!(received(post(5_000), 4_096).await, None);
        }

        #[tokio::test]
        async fn test_server_loopback_health() {
            let listener = TcpListener::bind("127.0.0.1:0")
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            let local_addr = listener.local_addr().unwrap_or_else(|e| panic!("{}", e));

            let tmp_dir = tempfile::tempdir().unwrap_or_else(|e| panic!("{}", e));
            let html_file = tmp_dir.path().join("mios.html");
            fs::write(&html_file, "<html><body>MiOS Settings</body></html>")
                .unwrap_or_else(|e| panic!("{}", e));

            let config = ConfigServerConfig {
                bind_addr: local_addr.to_string(),
                html_path: html_file,
                user_toml_path: tmp_dir.path().join("user.toml"),
                max_body_bytes: 1 << 20,
                ssot_root: Some(tmp_dir.path().to_path_buf()),
            };

            let cfg_arc = Arc::new(config);
            let cfg_clone = Arc::clone(&cfg_arc);

            let (shutdown_tx, shutdown_rx) = tokio::sync::oneshot::channel();

            let srv_handle = tokio::spawn(async move {
                tokio::select! {
                    res = listener.accept() => {
                        if let Ok((stream, _)) = res {
                            let _ = handle_stream(stream, cfg_clone).await;
                        }
                    }
                    _ = shutdown_rx => {}
                }
            });

            let mut client_stream = TcpStream::connect(local_addr)
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            let req = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n";
            client_stream
                .write_all(req)
                .await
                .unwrap_or_else(|e| panic!("{}", e));

            let mut resp_buf = [0u8; 4096];
            let n = client_stream
                .read(&mut resp_buf)
                .await
                .unwrap_or_else(|e| panic!("{}", e));
            let resp_str = String::from_utf8_lossy(&resp_buf[..n]);

            assert!(resp_str.contains("HTTP/1.1 200 OK"));
            assert!(resp_str.contains("miosd-config-server"));

            let _ = shutdown_tx.send(());
            let _ = srv_handle.await;
        }
    }
}
