// AI-hint: Transactional caller-owned agent mailboxes with leases, idempotent sends and recipient receipts.
// AI-related: usr/libexec/mios/mios-mcp-server, usr/share/mios/mios.toml [mcp.agents]
// AI-functions: main, dispatch
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, OpenOptions},
    io::Read,
    path::Path,
    time::{SystemTime, UNIX_EPOCH},
};

fn identifier(value: &str) -> Result<(), String> {
    if value.is_empty()
        || value.len() > 160
        || !value
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || b"-_.:".contains(&c))
    {
        return Err("invalid agent or message identifier".into());
    }
    Ok(())
}
fn string<'a>(request: &'a Value, field: &str) -> Result<&'a str, String> {
    request[field]
        .as_str()
        .ok_or_else(|| format!("missing {field}"))
}
fn digest(value: &str) -> String {
    format!("{:x}", Sha256::digest(value.as_bytes()))
}
fn dispatch(state: &mut Value, request: &Value, now: u64) -> Result<Value, String> {
    let cfg = &request["config"];
    let limit = |key: &str| {
        cfg[key]
            .as_u64()
            .filter(|n| *n > 0)
            .ok_or_else(|| format!("invalid [mcp.agents].{key}"))
    };
    let ttl = limit("lease_s")?;
    let max_agents = limit("max_agents")?;
    let max_pending = limit("max_pending")?;
    let max_bytes = limit("max_message_bytes")?;
    let max_receipts = limit("max_receipts")?;
    let action = string(request, "action")?;
    if action == "list" {
        let agents:Vec<Value>=state["agents"].as_object().unwrap().iter().map(|(id,a)|json!({
            "agent_id":id,"kind":a["kind"],"label":a["label"],"online":a["expires"].as_u64().unwrap_or(0)>now,
            "pending":state["messages"].as_array().unwrap().iter().filter(|m|m["to"]==*id && m["status"]=="queued").count()
        })).collect();
        return Ok(json!({"agents":agents}));
    }
    let id = string(request, "agent_id")?;
    identifier(id)?;
    let token = string(request, "token")?;
    if token.len() < 32 || token.len() > 256 {
        return Err("invalid agent lease token".into());
    }
    if action == "register" {
        let agents = state["agents"].as_object_mut().unwrap();
        if let Some(prior) = agents.get(id) {
            if prior["expires"].as_u64().unwrap_or(0) > now && prior["token_hash"] != digest(token)
            {
                return Err("agent identifier already registered by another lease".into());
            }
        } else if agents
            .values()
            .filter(|a| a["expires"].as_u64().unwrap_or(0) > now)
            .count() as u64
            >= max_agents
        {
            return Err("agent registry is full".into());
        }
        let kind = string(request, "kind")?;
        identifier(kind)?;
        let label = request["label"].as_str().unwrap_or(id);
        if label.len() > max_bytes as usize {
            return Err("agent label is too long".into());
        }
        agents.retain(|other, a| other == id || a["expires"].as_u64().unwrap_or(0) > now);
        agents.insert(
            id.into(),
            json!({"kind":kind,"label":label,"token_hash":digest(token),"expires":now+ttl}),
        );
        return Ok(json!({"agent_id":id,"expires":now+ttl}));
    }
    let agent = &state["agents"][id];
    if agent["token_hash"].as_str() != Some(digest(token).as_str()) {
        return Err("unknown agent or invalid lease".into());
    }
    if agent["expires"].as_u64().unwrap_or(0) <= now {
        return Err("agent lease expired; register again".into());
    }
    state["agents"][id]["expires"] = json!(now + ttl);
    match action {
        "unregister" => {
            state["agents"][id]["expires"] = json!(now);
            Ok(json!({"agent_id":id,"closed":true}))
        }
        "send" => {
            let to = string(request, "to")?;
            identifier(to)?;
            let body = string(request, "message")?;
            if body.is_empty() || body.len() as u64 > max_bytes {
                return Err("empty or oversized agent message".into());
            }
            let message_id = string(request, "message_id")?;
            identifier(message_id)?;
            let recipient_online = state["agents"][to]["expires"].as_u64().unwrap_or(0) > now;
            let messages = state["messages"].as_array_mut().unwrap();
            if let Some(prior) = messages.iter().find(|m| m["message_id"] == message_id) {
                if prior["from"] != id || prior["to"] != to || prior["message"] != body {
                    return Err("message identifier reused with different content".into());
                }
                return Ok(
                    json!({"message_id":message_id,"to":to,"status":prior["status"],"duplicate":true}),
                );
            }
            if !recipient_online {
                return Err("recipient is not registered or is offline".into());
            }
            if messages.iter().filter(|m| m["status"] == "queued").count() as u64 >= max_pending {
                return Err("agent message queue is full".into());
            }
            messages.push(json!({"message_id":message_id,"from":id,"to":to,"message":body,"created":now,"status":"queued"}));
            while messages
                .iter()
                .filter(|m| m["status"] == "received")
                .count() as u64
                > max_receipts
            {
                if let Some(index) = messages.iter().position(|m| m["status"] == "received") {
                    messages.remove(index);
                }
            }
            Ok(json!({"message_id":message_id,"to":to,"status":"queued"}))
        }
        "receive" => {
            let messages: Vec<&Value> = state["messages"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|m| m["to"] == id && m["status"] == "queued")
                .collect();
            Ok(json!({"agent_id":id,"messages":messages}))
        }
        "ack" => {
            let message_id = string(request, "message_id")?;
            let row = state["messages"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|m| m["to"] == id && m["message_id"] == message_id)
                .ok_or("message does not belong to this recipient")?;
            row["status"] = json!("received");
            row["received"] = json!(now);
            Ok(json!({"message_id":message_id,"status":"received"}))
        }
        _ => Err("unknown agent relay action".into()),
    }
}
fn run(directory: &Path, request: &Value) -> Result<Value, Box<dyn std::error::Error>> {
    if directory.is_symlink() {
        return Err("agent state directory is a symlink".into());
    }
    fs::create_dir_all(directory)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::{MetadataExt, PermissionsExt};
        if fs::metadata(directory)?.uid() != fs::metadata("/proc/self")?.uid() {
            return Err("agent state belongs to another user".into());
        }
        fs::set_permissions(directory, fs::Permissions::from_mode(0o755))?;
    }
    let lock_path = directory.join("lock");
    if lock_path.is_symlink() {
        return Err("agent lock is a symlink".into());
    }
    let lock = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(lock_path)?;
    lock.lock()?;
    let path = directory.join("state.json");
    if path.is_symlink() {
        return Err("agent state is a symlink".into());
    }
    let mut state: Value = if path.exists() {
        serde_json::from_slice(&fs::read(&path)?)?
    } else {
        json!({"agents":{},"messages":[]})
    };
    if !state["agents"].is_object() || !state["messages"].is_array() {
        return Err("invalid agent relay state".into());
    }
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    let result = dispatch(&mut state, request, now).map_err(std::io::Error::other)?;
    if request["action"] != "list" {
        let mut temporary = tempfile::NamedTempFile::new_in(directory)?;
        serde_json::to_writer(temporary.as_file_mut(), &state)?;
        temporary.as_file_mut().sync_all()?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = fs::set_permissions(temporary.path(), fs::Permissions::from_mode(0o644));
        }
        temporary.persist(&path)?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = fs::set_permissions(&path, fs::Permissions::from_mode(0o644));
        }
    }
    Ok(result)
}
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = (|| -> Result<Value, Box<dyn std::error::Error>> {
        if args.len() != 3 || args[1] != "--state" {
            return Err("Usage: mios-agent-relay --state PATH < request.json".into());
        }
        let mut raw = String::new();
        std::io::stdin()
            .take(2 * 1024 * 1024)
            .read_to_string(&mut raw)?;
        run(Path::new(&args[2]), &serde_json::from_str(&raw)?)
    })();
    match result {
        Ok(value) => println!("{}", json!({"ok":true,"result":value})),
        Err(error) => {
            println!("{}", json!({"ok":false,"error":error.to_string()}));
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn request(action: &str, id: &str) -> Value {
        json!({"action":action,"agent_id":id,"token":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","kind":"codex","config":{"lease_s":60,"max_agents":2,"max_pending":2,"max_message_bytes":256,"max_receipts":2}})
    }
    #[test]
    fn recipient_receipt_and_idempotent_send() {
        let mut state = json!({"agents":{},"messages":[]});
        dispatch(&mut state, &request("register", "head"), 1).unwrap();
        dispatch(&mut state, &request("register", "worker"), 1).unwrap();
        let mut send = request("send", "head");
        send["to"] = json!("worker");
        send["message"] = json!("bounded task");
        send["message_id"] = json!("task-1");
        assert_eq!(dispatch(&mut state, &send, 2).unwrap()["status"], "queued");
        assert_eq!(dispatch(&mut state, &send, 2).unwrap()["duplicate"], true);
        assert_eq!(
            dispatch(&mut state, &request("receive", "worker"), 3).unwrap()["messages"]
                .as_array()
                .unwrap()
                .len(),
            1
        );
        let mut ack = request("ack", "worker");
        ack["message_id"] = json!("task-1");
        assert_eq!(dispatch(&mut state, &ack, 4).unwrap()["status"], "received");
        assert_eq!(
            dispatch(&mut state, &send, 5).unwrap()["status"],
            "received"
        );
        dispatch(&mut state, &request("unregister", "worker"), 6).unwrap();
        assert_eq!(
            dispatch(&mut state, &send, 7).unwrap()["status"],
            "received"
        );
        send["message_id"] = json!("DEVLOOP-PLANTED-OFFLINE");
        assert!(dispatch(&mut state, &send, 7)
            .unwrap_err()
            .contains("offline"));
        assert!(dispatch(&mut state, &request("receive", "worker"), 100)
            .unwrap_err()
            .contains("expired"));
    }
    #[test]
    fn planted_misrouting_and_lease_impersonation_fail() {
        let mut state = json!({"agents":{},"messages":[]});
        dispatch(&mut state, &request("register", "head"), 1).unwrap();
        let mut stolen = request("register", "head");
        stolen["token"] = json!("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
        assert!(dispatch(&mut state, &stolen, 2)
            .unwrap_err()
            .contains("another lease"));
        let mut send = request("send", "head");
        send["to"] = json!("DEVLOOP-PLANTED-ABSENT");
        send["message"] = json!("negative");
        send["message_id"] = json!("task-1");
        assert!(dispatch(&mut state, &send, 2)
            .unwrap_err()
            .contains("offline"));
        assert!(state["messages"].as_array().unwrap().is_empty());
        stolen["action"] = json!("receive");
        assert!(dispatch(&mut state, &stolen, 2)
            .unwrap_err()
            .contains("invalid lease"));
    }
    #[test]
    fn simultaneous_sends_preserve_every_message() {
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("registry");
        run(&path, &request("register", "head")).unwrap();
        run(&path, &request("register", "worker")).unwrap();
        let jobs: Vec<_> = (0..8)
            .map(|i| {
                let path = path.clone();
                std::thread::spawn(move || {
                    let mut send = request("send", "head");
                    send["config"]["max_pending"] = json!(16);
                    send["to"] = json!("worker");
                    send["message"] = json!("hello");
                    send["message_id"] = json!(format!("task-{i}"));
                    run(&path, &send).unwrap();
                })
            })
            .collect();
        for job in jobs {
            job.join().unwrap();
        }
        assert_eq!(
            run(&path, &request("receive", "worker")).unwrap()["messages"]
                .as_array()
                .unwrap()
                .len(),
            8
        );
    }
}
