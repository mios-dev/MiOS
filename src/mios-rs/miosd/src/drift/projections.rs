// AI-hint: Heavy regen-and-diff projection checks for miosd drift runner.
// AI-related: tools/generate-pod-quadlets.py, tools/generate-egress-firewall.py, automation/98-drift-checks.sh

use super::regen::{regen_and_diff, regen_and_diff_shell};
use super::{Check, DriftCtx, Verdict};

pub struct PodQuadletsCheck;
impl Check for PodQuadletsCheck {
    fn id(&self) -> &'static str {
        "check_pod_quadlets"
    }
    fn describe(&self) -> &'static str {
        "Assert generated pod quadlets match committed quadlet files"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        // Quadlets are emitted into usr/share/containers/systemd (29 units), the
        // path automation/98-drift-checks.sh has always checked. The old
        // usr/share/mios/quadlets has never existed, so this check hard-failed
        // the in-image `miosd drift-check` on every build.
        regen_and_diff(
            ctx,
            "tools/generate-pod-quadlets.py",
            &["usr/share/containers/systemd"],
            &["--check"],
        )
    }
}

pub struct EgressFirewallCheck;
impl Check for EgressFirewallCheck {
    fn id(&self) -> &'static str {
        "check_egress_firewall"
    }
    fn describe(&self) -> &'static str {
        "Assert generated egress firewall rules match committed egress.nft"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff(
            ctx,
            "tools/generate-egress-firewall.py",
            &["usr/share/mios/security/egress.nft"],
            &["--check"],
        )
    }
}

pub struct BladeDropinsCheck;
impl Check for BladeDropinsCheck {
    fn id(&self) -> &'static str {
        "check_blade_dropins"
    }
    fn describe(&self) -> &'static str {
        "Assert generated blade systemd dropins match committed files"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff(
            ctx,
            "tools/generate-blade-dropins.py",
            &["usr/lib/systemd/system"],
            &["--check"],
        )
    }
}

pub struct KargsProjectionCheck;
impl Check for KargsProjectionCheck {
    fn id(&self) -> &'static str {
        "check_kargs_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert kernel args projection matches committed kargs"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff_shell(
            ctx,
            "automation/75-kargs-render.sh",
            "KARGS_DIR",
            "usr/lib/bootc/kargs.d",
        )
    }
}

pub struct ChronyProjectionCheck;
impl Check for ChronyProjectionCheck {
    fn id(&self) -> &'static str {
        "check_chrony_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert chrony config projection matches committed file"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff_shell(
            ctx,
            "automation/42-chrony-render.sh",
            "CHRONY_CONF",
            "etc/chrony.conf",
        )
    }
}

pub struct NutProjectionCheck;
impl Check for NutProjectionCheck {
    fn id(&self) -> &'static str {
        "check_nut_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert NUT config projection matches committed file"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff_shell(
            ctx,
            "automation/43-nut-render.sh",
            "UPS_CONF_DIR",
            "etc/ups",
        )
    }
}

pub struct IPAEnrollProjectionCheck;
impl Check for IPAEnrollProjectionCheck {
    fn id(&self) -> &'static str {
        "check_ipa_enroll_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert IPA enroll projection matches committed script"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff(
            ctx,
            // Real generator is generate-ipa-enroll-ENV.py and it projects the
            // env file, not a libexec binary. Under the old names the generator
            // did not exist, so this check silently returned Skip and never ran.
            "tools/generate-ipa-enroll-env.py",
            &["etc/mios/ipa-enroll.env"],
            &["--check"],
        )
    }
}

pub struct UKICmdlineProjectionCheck;
impl Check for UKICmdlineProjectionCheck {
    fn id(&self) -> &'static str {
        "check_uki_cmdline_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert UKI kernel cmdline projection matches committed file"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff(
            ctx,
            "tools/generate-uki-cmdline.py",
            &["usr/lib/kernel/cmdline"],
            &["--check"],
        )
    }
}

pub struct CockpitProjectionCheck;
impl Check for CockpitProjectionCheck {
    fn id(&self) -> &'static str {
        "check_cockpit_projection"
    }
    fn describe(&self) -> &'static str {
        "Assert Cockpit projection matches committed file"
    }
    fn run(&self, ctx: &DriftCtx) -> Verdict {
        regen_and_diff(
            ctx,
            "tools/generate-cockpit-conf.py",
            &["etc/cockpit/cockpit.conf"],
            &["--check"],
        )
    }
}
