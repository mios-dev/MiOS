<!-- AI-hint: Documentation of the Layer 3 runtime security triplet (CrowdSec IPS, fapolicyd application whitelisting, USBGuard device whitelisting) — their configuration paths, operational modes, and roles in mitigating network, execution, and hardware threats; explains how this runtime posture lets MiOS run an immutable OS image AND a least-privileged local agentic-AI plane on the same box. -->
# Defense-in-Depth Layer 3 — Runtime Guards

> **Purpose.** MiOS is one thing built two ways at once: an immutable,
> bootc/OCI-shaped Fedora workstation *and* a local, self-replicating agentic
> AI operating system that runs an inference + agent stack on the same hardware.
> The build pipeline and the Architectural Laws lock down the *image* (composefs
> fs-verity for offline tamper-resistance, cosign for image-swap detection,
> Law 6 keeps the agent Quadlets unprivileged). This doc covers the third,
> complementary layer: the **runtime guards** that defend the *running* host —
> CrowdSec, fapolicyd, and USBGuard. They are MiOS's runtime watchdogs against
> network, execution, and hardware threats while the desktop, the VMs, and the
> always-on local agent plane are all live.
>
> Configured by `automation/33-firewall.sh`, `automation/12-virt.sh` (CrowdSec
> sovereign mode, ~lines 46-59), and shipped via `etc/fapolicyd/fapolicyd.rules`.
> All three packages are declared in `mios.toml` under the `[packages.security]`
> set — no hard-coded `dnf install`.

This triplet is what makes the dual nature safe: the same box runs a GNOME
session, VFIO-passthrough VMs, and an always-listening OpenAI-compatible agent
endpoint. Layer 3 ensures that an exposed service, a dropped binary, or a hostile
USB device can't pivot off the agent plane — without depending on any vendor
cloud, exactly like the rest of the system, which is fully offline-capable.

## CrowdSec — IPS in sovereign/offline mode

- Project: <https://www.crowdsec.net/> · repo <https://github.com/crowdsecurity/crowdsec>
- MiOS uses **sovereign/offline mode** — no telemetry to crowdsec.net,
  no community blocklists pulled. The Central API (`online_client`) is disabled
  in `/etc/crowdsec/config.yaml` (the only `/etc/` location, not `/usr/lib/`,
  because CrowdSec's upstream contract requires it there). `automation/12-virt.sh`
  comments out `online_client:` at build time so decisions stay local-only;
  RE2 is the default regex engine.
- Bouncer: `crowdsec-firewall-bouncer-nftables`, integrated with firewalld
- Status:
  ```bash
  sudo cscli metrics
  sudo cscli decisions list
  sudo cscli alerts list
  ```

> **Note on the dashboard sidecar.** A `crowdsec-dashboard` container existed
> historically; under the global `mios-<component>` naming convention it became
> `mios-crowdsec-dashboard`, and it is **force-disabled** in `mios.toml`
> (`mios-crowdsec-dashboard = false`). It ran the full CrowdSec image against the
> shared `/var/lib/crowdsec` volume and planted dangling `/staging` symlinks that
> crash-looped the host agent. The host CrowdSec agent already provides the IPS
> function on its own; the redundant sidecar is retired.

## fapolicyd — Application Whitelisting

- Project: <https://github.com/linux-application-whitelisting/fapolicyd>
- Mode: deny-by-default
- Trust DB: built from the RPM database (every package-installed binary is
  trusted), plus `/etc/fapolicyd/fapolicyd.trust` for admin additions
- Rules: `etc/fapolicyd/fapolicyd.rules` — MiOS-tuned ruleset
- Status:
  ```bash
  systemctl status fapolicyd
  fapolicyd-cli --dump-db | head -20
  ```
- When a binary is blocked, the user sees `Permission denied` and an
  AVC-style log entry in the journal.

> A separate, UKI-targeted **permissive/observe** rollout (`[security.fapolicyd_observe]`
> in `mios.toml`) logs would-be denials and blocks nothing while a whitelist is
> tuned, because an incomplete enforce-mode whitelist under a sealed UKI can brick
> boot. See `concepts/ws7-uki-fapolicyd.md` for that staged enforce-mode plan.

## USBGuard — USB Device Whitelisting

- Project: <https://usbguard.github.io/>
- Mode: **off by default** (MiOS choice; SecureBlue would have it on)
- To enable:
  ```bash
  sudo usbguard generate-policy > /etc/usbguard/rules.conf
  sudo systemctl restart usbguard
  sudo usbguard list-devices
  sudo usbguard allow-device <id>
  ```

## Why this triplet

Each guard closes one class of runtime attack. Read with the image-level
protections (composefs fs-verity, cosign), they cover the path from the network
edge, through execution, down to the physical port:

| Threat | Defended by |
| --- | --- |
| Attacker inserts a malicious USB | USBGuard (when enabled) |
| Attacker drops a binary in `/tmp` and runs it | fapolicyd |
| Attacker scans/probes the network from outside | firewalld + CrowdSec |
| Attacker exploits a service to spawn arbitrary code | fapolicyd + SELinux |
| Attacker tampers with disk content offline | composefs (fs-verity) |
| Attacker swaps the OS image | cosign signature verification |

Each layer is independent — failure of one doesn't compromise the others. The
last two rows are properties of the bootc/OCI image itself (the build pipeline
and Architectural Laws guarantee them); the first four are this doc's runtime
guards. Together they let an immutable OS that also hosts a self-driving local
agent stack stay trustworthy under load.

## Cross-refs

- `usr/share/doc/mios/guides/security.md` — overall hardening posture (kargs, SELinux, lockdown)
- `usr/share/doc/mios/upstream/secureblue.md` — the hardening profile MiOS draws from
- `usr/share/doc/mios/upstream/selinux.md` — the MAC layer fapolicyd pairs with
- `usr/share/doc/mios/upstream/composefs.md` / `usr/share/doc/mios/upstream/cosign.md` — the image-integrity rows above
