// AI-hint: Port literal and container ports checks for miosd drift runner.
// AI-related: mios.toml [ports], automation/98-drift-checks.sh

use super::{Check, DriftCtx, Verdict};

pub struct ContainerPortsCheck;
impl Check for ContainerPortsCheck {
    fn id(&self) -> &'static str {
        "check_container_ports"
    }
    fn describe(&self) -> &'static str {
        "Assert container port mappings match SSOT [ports] definitions"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: Container ports match SSOT definitions".to_string())
    }
}

pub struct BarePortLiteralsCheck;
impl Check for BarePortLiteralsCheck {
    fn id(&self) -> &'static str {
        "check_no_bare_port_literals"
    }
    fn describe(&self) -> &'static str {
        "Assert no bare port number literals exist outside SSOT"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Skip("NOT IMPLEMENTED: No bare port literals".to_string())
    }
}
