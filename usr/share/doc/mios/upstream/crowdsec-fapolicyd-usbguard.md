# Defense-in-Depth Layer 3 — Runtime Guards

> CrowdSec, fapolicyd, and USBGuard are MiOS's runtime watchdogs.
> Configured by `automation/33-firewall.sh`, `automation/12-virt.sh:42-50`
> (CrowdSec sovereign mode), and shipped via `etc/fapolicyd/fapolicyd.rules`.

## CrowdSec — IPS in sovereign/offline mode

- Project: <https://www.crowdsec.net/> · repo <https://github.com/crowdsecurity/crowdsec>
- 'MiOS' uses **sovereign/offline mode** — no telemetry to crowdsec.net,
  no community blocklists pulled. `online_client` is disabled in
  `/etc/crowdsec/config.yaml` (the only `/etc/` location, not
  `/usr/lib/`, because CrowdSec's upstream contract requires it there)
- Bouncer: nftables, integrated with firewalld
- Status:
  ```bash
  sudo cscli metrics
  sudo cscli decisions list
  sudo cscli alerts list
  ```

## fapolicyd — Application Whitelisting

- Project: <https://github.com/linux-application-whitelisting/fapolicyd>
- Mode: deny-by-default
- Trust DB: built from RPM database (every package-installed binary is
  trusted), plus `/etc/fapolicyd/fapolicyd.trust` for admin additions
- Rules: `etc/fapolicyd/fapolicyd.rules` — MiOS-tuned ruleset
- Status:
  ```bash
  systemctl status fapolicyd
  fapolicyd-cli --dump-db | head -20
  ```
- When a binary is blocked, the user sees `Permission denied` and an
  AVC-style log entry in journal.

## USBGuard — USB Device Whitelisting

- Project: <https://usbguard.github.io/>
- Mode: **off by default** ('MiOS' choice; SecureBlue would have it on)
- To enable:
  ```bash
  sudo usbguard generate-policy > /etc/usbguard/rules.conf
  sudo systemctl restart usbguard
  sudo usbguard list-devices
  sudo usbguard allow-device <id>
  ```

## Why this triplet

| Threat | Defended by |
| --- | --- |
| Attacker inserts a malicious USB | USBGuard (when enabled) |
| Attacker drops a binary in `/tmp` and runs it | fapolicyd |
| Attacker scans/probes the network from outside | firewalld + CrowdSec |
| Attacker exploits a service to spawn arbitrary code | fapolicyd + SELinux |
| Attacker tampers with disk content offline | composefs (fs-verity) |
| Attacker swaps the OS image | cosign signature verification |

Each layer is independent — failure of one doesn't compromise the others.

## Cross-refs

- `usr/share/doc/mios/80-security.md`
- `usr/share/doc/mios/upstream/secureblue.md`
- `usr/share/doc/mios/upstream/selinux.md`
