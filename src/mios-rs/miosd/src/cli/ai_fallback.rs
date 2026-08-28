// AI-hint: OpenAI-compatible /v1/chat/completions client fallback for interactive prompts.
// AI-related: usr/bin/mios, MIOS_AI_ENDPOINT

use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::net::TcpStream;

#[derive(Serialize)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Serialize)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<ChatMessage>,
    stream: bool,
}

#[derive(Deserialize)]
struct ChatChoice {
    message: Option<ChatMessageResponse>,
}

#[derive(Deserialize)]
struct ChatMessageResponse {
    content: Option<String>,
}

#[derive(Deserialize)]
struct ChatCompletionResponse {
    choices: Option<Vec<ChatChoice>>,
}

pub struct AiFallback;

impl AiFallback {
    pub fn resolve_endpoint() -> (String, String) {
        let ep = std::env::var("MIOS_AI_ENDPOINT")
            .unwrap_or_else(|_| "http://localhost:8640/v1".to_string());
        let model = std::env::var("MIOS_AI_MODEL")
            .or_else(|_| std::env::var("MIOS_AI_GATEWAY_MODEL"))
            .unwrap_or_else(|_| "MiOS AI".to_string());
        (ep, model)
    }

    pub fn execute_prompt(prompt: &str) -> i32 {
        let (endpoint, model) = Self::resolve_endpoint();
        println!(
            "[mios] Connecting to AI endpoint: {} (model: {})",
            endpoint, model
        );

        let req = ChatCompletionRequest {
            model: model.clone(),
            messages: vec![ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            stream: false,
        };

        let json_body = match serde_json::to_string(&req) {
            Ok(j) => j,
            Err(e) => {
                eprintln!("mios: failed to serialize chat request: {}", e);
                return 1;
            }
        };

        // Parse host and port from endpoint URL
        let url_no_proto = endpoint
            .trim_start_matches("http://")
            .trim_start_matches("https://");
        let parts: Vec<&str> = url_no_proto.split('/').collect();
        let host_port = parts[0];
        let path_prefix = if parts.len() > 1 {
            format!("/{}", parts[1..].join("/"))
        } else {
            "/v1".to_string()
        };
        let full_path = format!("{}/chat/completions", path_prefix.trim_end_matches('/'));

        let (host, port) = if host_port.contains(':') {
            let hp: Vec<&str> = host_port.split(':').collect();
            (hp[0], hp[1].parse::<u16>().unwrap_or(8640))
        } else {
            (host_port, 80)
        };

        let stream_res = TcpStream::connect((host, port));
        let mut stream = match stream_res {
            Ok(s) => s,
            Err(e) => {
                eprintln!("mios: could not reach AI endpoint at {}:{} ({}). Ensure mios-llm-light or agent-pipe is running.", host, port, e);
                return 1;
            }
        };

        let http_req = format!(
            "POST {} HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            full_path, host_port, json_body.len(), json_body
        );

        if let Err(e) = stream.write_all(http_req.as_bytes()) {
            eprintln!("mios: failed to write HTTP request: {}", e);
            return 1;
        }

        let mut response_bytes = Vec::new();
        if let Err(e) = stream.read_to_end(&mut response_bytes) {
            eprintln!("mios: failed to read HTTP response: {}", e);
            return 1;
        }

        let response_str = String::from_utf8_lossy(&response_bytes);
        if let Some(body_start) = response_str.find("\r\n\r\n") {
            let body = &response_str[body_start + 4..];
            if let Ok(parsed) = serde_json::from_str::<ChatCompletionResponse>(body) {
                if let Some(choices) = parsed.choices {
                    if let Some(first) = choices.first() {
                        if let Some(msg) = &first.message {
                            if let Some(content) = &msg.content {
                                println!("{}", content.trim());
                                return 0;
                            }
                        }
                    }
                }
            }
            println!("{}", body.trim());
            return 0;
        }

        println!("{}", response_str);
        0
    }
}
