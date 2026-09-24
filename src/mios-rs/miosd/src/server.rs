// AI-hint: Lightweight, embedded HTTP loopback server hosting mios.html and SSOT /portal/config API.
// AI-related: usr/share/mios/configurator/mios.html, /usr/libexec/mios/mios-configurator-launch, usr/share/mios/mios.toml

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
    pub profile_path: PathBuf,
    pub vendor_toml_path: PathBuf,
    pub host_toml_path: PathBuf,
}

impl Default for ConfigServerConfig {
    fn default() -> Self {
        Self::resolve(None, None)
    }
}

impl ConfigServerConfig {
    pub fn resolve(bind: Option<String>, port: Option<u16>) -> Self {
        let port_str = port
            .map(|p| p.to_string())
            .or_else(|| std::env::var("MIOS_PORT_AGENT_PIPE").ok())
            .unwrap_or_else(|| "8700".to_string());

        let bind_addr = bind.unwrap_or_else(|| {
            std::env::var("MIOS_CONFIG_BIND_ADDR")
                .unwrap_or_else(|_| format!("127.0.0.1:{}", port_str))
        });

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

        let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
        let profile_path = if let Ok(custom) = std::env::var("MIOS_PROFILE_TOML") {
            PathBuf::from(custom)
        } else {
            Path::new(&home).join(".config/mios/profile.toml")
        };

        let vendor_toml_path = if Path::new("/usr/share/mios/mios.toml").is_file() {
            PathBuf::from("/usr/share/mios/mios.toml")
        } else if root_path.join("usr/share/mios/mios.toml").is_file() {
            root_path.join("usr/share/mios/mios.toml")
        } else {
            PathBuf::from("usr/share/mios/mios.toml")
        };

        let host_toml_path = if Path::new("/etc/mios/mios.toml").is_file() {
            PathBuf::from("/etc/mios/mios.toml")
        } else if root_path.join("etc/mios/mios.toml").is_file() {
            root_path.join("etc/mios/mios.toml")
        } else {
            PathBuf::from("etc/mios/mios.toml")
        };

        Self {
            bind_addr,
            html_path,
            profile_path,
            vendor_toml_path,
            host_toml_path,
        }
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
            .with_body("text/plain", format!("Redirecting to {}", location).into_bytes())
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

pub fn read_layered_toml(config: &ConfigServerConfig) -> String {
    let mut combined = String::new();

    if let Ok(vendor_content) = fs::read_to_string(&config.vendor_toml_path) {
        combined = vendor_content;
    }

    if let Ok(host_content) = fs::read_to_string(&config.host_toml_path) {
        if combined.is_empty() {
            combined = host_content;
        } else {
            combined.push_str("\n\n# --- Host Overrides ---\n");
            combined.push_str(&host_content);
        }
    }

    if let Ok(profile_content) = fs::read_to_string(&config.profile_path) {
        if combined.is_empty() {
            combined = profile_content;
        } else {
            combined.push_str("\n\n# --- User Profile Overrides ---\n");
            combined.push_str(&profile_content);
        }
    }

    if combined.is_empty() {
        "# Empty MiOS SSOT Configuration\n".to_string()
    } else {
        combined
    }
}

pub fn handle_request(req: &HttpRequest, config: &ConfigServerConfig) -> HttpResponse {
    let cors_resp = |resp: HttpResponse| {
        resp.with_header("Access-Control-Allow-Origin", "*")
            .with_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            .with_header("Access-Control-Allow-Headers", "Content-Type")
    };

    if req.method == "OPTIONS" {
        return cors_resp(
            HttpResponse::new(204, "No Content")
                .with_header("Content-Length", "0")
        );
    }

    let mut resp = match (req.method.as_str(), req.path.as_str()) {
        ("GET", "/") | ("HEAD", "/") => cors_resp(HttpResponse::redirect("/configure")),

        ("GET", "/configure") | ("HEAD", "/configure") | ("GET", "/portal/configurator") | ("HEAD", "/portal/configurator") => {
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
            let toml_data = read_layered_toml(config);
            cors_resp(HttpResponse::toml(200, "OK", toml_data))
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

            let report = mios_config::MiosValidator::validate_str(body_str);
            if !report.is_valid {
                let err_msgs: Vec<String> = report
                    .errors
                    .into_iter()
                    .map(|e| e.to_string())
                    .collect();
                let json_body = match serde_json::to_string(&serde_json::json!({ "errors": err_msgs })) {
                    Ok(j) => j,
                    Err(_) => r#"{"errors":["Validation failed"]}"#.to_string(),
                };
                return cors_resp(HttpResponse::json(422, "Unprocessable Entity", json_body));
            }

            if let Some(parent) = config.profile_path.parent() {
                if let Err(e) = fs::create_dir_all(parent) {
                    return cors_resp(HttpResponse::json(
                        500,
                        "Internal Server Error",
                        format!(r#"{{"errors":["Failed to create config dir: {}"]}}"#, e),
                    ));
                }
            }

            let tmp_path = config.profile_path.with_extension("tmp");
            if let Err(e) = fs::write(&tmp_path, body_str) {
                return cors_resp(HttpResponse::json(
                    500,
                    "Internal Server Error",
                    format!(r#"{{"errors":["Failed to write temporary file: {}"]}}"#, e),
                ));
            }

            if let Err(e) = fs::rename(&tmp_path, &config.profile_path) {
                return cors_resp(HttpResponse::json(
                    500,
                    "Internal Server Error",
                    format!(r#"{{"errors":["Failed to persist config: {}"]}}"#, e),
                ));
            }

            cors_resp(HttpResponse::json(
                200,
                "OK",
                format!(
                    r#"{{"status":"ok","message":"Saved to {}","bytes":{}}}"#,
                    config.profile_path.display(),
                    body_str.len()
                ),
            ))
        }

        ("GET", "/health") | ("HEAD", "/health") | ("GET", "/healthz") | ("HEAD", "/healthz") => cors_resp(HttpResponse::json(
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

pub async fn handle_stream(
    mut stream: TcpStream,
    config: Arc<ConfigServerConfig>,
) -> Result<(), std::io::Error> {
    let mut buf = [0u8; 65536];
    let n = stream.read(&mut buf).await?;
    if n == 0 {
        return Ok(());
    }

    let resp = match parse_http_request(&buf[..n]) {
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
    use super::*;

    #[test]
    fn test_parse_http_request_get() {
        let raw = b"GET /configure HTTP/1.1\r\nHost: localhost:8700\r\nUser-Agent: test\r\n\r\n";
        let req = parse_http_request(raw);
        assert!(req.is_some());
        let r = req.as_ref().unwrap_or_else(|| unreachable!());
        assert_eq!(r.method, "GET");
        assert_eq!(r.path, "/configure");
        assert_eq!(r.headers.get("host").map(String::as_str), Some("localhost:8700"));
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

    #[tokio::test]
    async fn test_server_loopback_health() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap_or_else(|e| panic!("{}", e));
        let local_addr = listener.local_addr().unwrap_or_else(|e| panic!("{}", e));

        let tmp_dir = tempfile::tempdir().unwrap_or_else(|e| panic!("{}", e));
        let html_file = tmp_dir.path().join("mios.html");
        fs::write(&html_file, "<html><body>MiOS Settings</body></html>").unwrap_or_else(|e| panic!("{}", e));

        let config = ConfigServerConfig {
            bind_addr: local_addr.to_string(),
            html_path: html_file,
            profile_path: tmp_dir.path().join("profile.toml"),
            vendor_toml_path: tmp_dir.path().join("vendor.toml"),
            host_toml_path: tmp_dir.path().join("host.toml"),
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

        let mut client_stream = TcpStream::connect(local_addr).await.unwrap_or_else(|e| panic!("{}", e));
        let req = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n";
        client_stream.write_all(req).await.unwrap_or_else(|e| panic!("{}", e));

        let mut resp_buf = [0u8; 4096];
        let n = client_stream.read(&mut resp_buf).await.unwrap_or_else(|e| panic!("{}", e));
        let resp_str = String::from_utf8_lossy(&resp_buf[..n]);

        assert!(resp_str.contains("HTTP/1.1 200 OK"));
        assert!(resp_str.contains("miosd-config-server"));

        let _ = shutdown_tx.send(());
        let _ = srv_handle.await;
    }
}
