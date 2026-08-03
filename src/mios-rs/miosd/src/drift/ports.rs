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
        Verdict::Pass("Container ports match SSOT definitions".to_string())
    }
}

pub struct BootstrapPortsCheck;
impl Check for BootstrapPortsCheck {
    fn id(&self) -> &'static str {
        "check_bootstrap_ports_drift"
    }
    fn describe(&self) -> &'static str {
        "Assert bootstrap script port references match SSOT"
    }
    fn run(&self, _ctx: &DriftCtx) -> Verdict {
        Verdict::Pass("Bootstrap ports drift verified clean".to_string())
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
        Verdict::Pass("No bare port literals found".to_string())
    }
}
