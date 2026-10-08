// AI-hint: Adversarial native dashboard controls for full service coverage, layer mutations, narrow/Unicode layout and actual TCP reachability.
// AI-related: /usr/share/mios/templates/rust, tools/native/mios-service-core/src/dashboard.rs
use mios_service_core::dashboard::{catalog, probe, render};
use serde_json::{json, Value};
use std::net::TcpListener;
use std::time::Duration;

fn config() -> Value {
    json!({"meta":{"mios_version":"test-version"},"theme":{"font":{"family":"Operator Font","size":17}},
        "dashboard":{"title":"Operator dashboard","show_title":true,"show_services":true,"show_verb_hints":true,"verb_hint":"operator verbs","rows":[["cpu","ram"],["version","font"]]},
        "ports":{"categories":{"agent":{"members":["agent_pipe",""],"pinned":{"dns":53}},"webui":{"members":["open_webui"]}},"agent_pipe":17400,"dns":53,"open_webui":18200}})
}

#[test]
fn every_category_member_and_pin_survives_width_and_operator_mutations() -> Result<(), String> {
    let mut config = config();
    config["ports"]["categories"]["agent"]["members"] = json!(["agent_pipe", "operator_service"]);
    config["ports"]["operator_service"] = json!(19500);
    let endpoints = catalog(&config)?;
    assert_eq!(endpoints.len(), 4);
    for width in [24, 59, 60, 80, 141] {
        let text = render(&config, &json!([{ "type":"CPU", "result":{"cpu":"Long processor 漢字 name with all its information intact"}}]), &endpoints, width)?;
        assert!(text.lines().all(|line| unicode_width::UnicodeWidthStr::width(line) == width));
        let joined = text.replace(['\n', '|', ' '], "");
        for value in ["operator_service", "19500", "dns", "53", "open_webui", "18200", "test-version", "OperatorFont", "17pt"] { assert!(joined.contains(value), "missing {value} at width {width}: {text}"); }
        let left: String = text.lines().filter_map(|line| line.split('|').nth(1)).collect();
        assert!(left.replace(' ', "").contains("processor漢字namewithallitsinformationintact"));
    }
    Ok(())
}

#[test]
fn invalid_or_empty_catalogs_and_metrics_fail_instead_of_rendering_old_defaults() {
    for patch in [json!({}), json!({"empty":{"members":[]}})] {
        let mut doc = config(); doc["ports"]["categories"] = patch; assert!(catalog(&doc).is_err());
    }
    let mut doc = config(); doc["ports"]["agent_pipe"] = json!(70000); assert!(catalog(&doc).is_err());
    doc = config(); doc["ports"]["categories"]["webui"]["members"] = json!(["agent_pipe"]); assert!(catalog(&doc).is_err());
    doc = config(); doc["dashboard"]["rows"] = json!([["new_unknown_metric"]]); assert!(render(&doc, &json!([]), &catalog(&doc).expect("valid fixture"), 80).is_err());
    doc = config(); assert!(render(&doc, &json!([]), &[], 80).is_err());
    assert!(render(&doc, &json!([]), &[], 0).is_err());
}

#[test]
fn stack_offset_applies_to_the_same_catalog_and_rejects_overflow() -> Result<(), String> {
    let mut doc = config(); doc["ports"]["stack_id"] = json!(1);
    let endpoints = catalog(&doc)?;
    assert_eq!(endpoints.iter().find(|e| e.name == "agent_pipe").map(|e| e.port), Some(27400));
    doc["ports"]["stack_id"] = json!(7); assert!(catalog(&doc).is_err());
    Ok(())
}

#[test]
fn real_listener_is_open_and_unused_socket_is_closed() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let unused = TcpListener::bind("127.0.0.1:0")?;
    let closed = unused.local_addr()?.port(); drop(unused);
    let mut doc = config(); doc["ports"]["agent_pipe"] = json!(listener.local_addr()?.port()); doc["ports"]["open_webui"] = json!(closed);
    let mut endpoints = catalog(&doc)?;
    probe(&mut endpoints, Duration::from_millis(100))?;
    assert_eq!(endpoints.iter().find(|e| e.name == "agent_pipe").map(|e| e.state.as_str()), Some("open"));
    assert_eq!(endpoints.iter().find(|e| e.name == "open_webui").map(|e| e.state.as_str()), Some("closed"));
    Ok(())
}

#[test]
fn structured_hardware_keeps_gpu_types_and_sums_swap_devices_without_inventing_missing_disk_values() -> Result<(), String> {
    let facts = json!([
        {"type":"GPU","result":[{"type":"Integrated","name":"Integrated GPU"},{"type":"Discrete","name":"Discrete GPU"}]},
        {"type":"Swap","result":[{"used":1073741824_u64,"total":2147483648_u64},{"used":0,"total":2147483648_u64}]},
        {"type":"Disk","result":[{"mountpoint":"C:\\","bytes":{"total":1073741824_u64}}]}
    ]);
    let values = mios_service_core::dashboard::metrics(&config(), &facts)?;
    assert_eq!(values.get("gpu_discrete").map(String::as_str), Some("Discrete GPU"));
    assert_eq!(values.get("gpu_integrated").map(String::as_str), Some("Integrated GPU"));
    assert_eq!(values.get("swap").map(String::as_str), Some("1.0 / 4.0 GiB (25%)"));
    assert_eq!(values.get("disk_c").map(String::as_str), Some("unavailable"));
    Ok(())
}
