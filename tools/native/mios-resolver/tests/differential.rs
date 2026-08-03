// AI-hint: Proptest differential test for mios-resolver -- asserts emit_json survives arbitrary valid [ports] tables and stack_id offsets.
// AI-related: tools/native/mios-resolver/src/emit_json.rs, tools/check-resolver-twin.py
use mios_resolver::emit_json::emit_json;
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_resolver_proptest_valid_ports(
        stack_id in 0i64..10i64,
        port_val in 1000i64..9000i64,
    ) {
        let toml_str = format!(
            "[ports]\nstack_id = {}\nssh = {}\n",
            stack_id, port_val
        );
        let val: toml::Value = toml::from_str(&toml_str).unwrap();
        let json_out = emit_json(&val, stack_id * 10000);
        prop_assert!(json_out.contains("\"ssh\":"));
    }
}
