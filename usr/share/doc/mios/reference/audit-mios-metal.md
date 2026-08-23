<!-- AI-hint: Concrete host definition for the MiOS-Metal split-plane: bootc hypervisor-router image contents, SSOT-driven vfio-pci bind, hand-authored `table inet mios-router` nft ruleset, headscale mesh join, swtpm vTPM wiring, and a guest domain XML skeleton -- with drop-in artifacts (vfio bind projector + guest XML) and file:line evidence against the current tree. -->
<!-- AI-related: docs/agy/doc-mios-metal.md, usr/lib/bootc/kargs.d/01-mios-vfio.toml, usr/lib/bootc/kargs.d/20-vfio.toml, usr/lib/bootc/kargs.d/13-rtx50-vfio-workaround.toml, automation/75-kargs-render.sh, usr/share/mios/mios.toml, usr/libexec/mios/Xbox-Final-NoAutoSelect.xml, usr/libexec/mios/vfio-check.sh, usr/libexec/mios/virt-apply.sh, usr/share/mios/security/egress.nft, automation/45-firewall.sh, automation/98-drift-checks.sh -->

# MiOS-Metal — Concrete Host Definition (refinement audit)

> **Scope.** This audit turns the north-star architecture in [`concepts/mios-metal-architecture.md`](../concepts/mios-metal-architecture.md) into a *buildable host definition*: exact image layer, the SSOT surface it projects from, and four drop-in artifacts — the **vfio-pci bind** (SSOT-driven), the **`table inet mios-router` nft ruleset**, the **headscale mesh join** (Quadlet + policy), and the **guest domain XML skeleton** (swtpm vTPM inline). Everything below is grounded in files that exist today; every gap between "what the tree does now" and "what the Mini host needs" is called out with `file:line`. The two required drop-ins — **vfio bind + guest XML** — are embedded verbatim in §4.1 and §4.6.
>
> **Status.** Refinement/spec, 2026-07-31. Untestable here (no Linux/KVM host, no dGPU); the artifacts are render-correct and drift-gateable, not VM-verified. Where a claim needs a real box, it is marked **[needs-VM]**.

---

## 0. What this refines (delta vs the north-star doc)

`doc-mios-metal.md` establishes the *architecture and the honest constraints* (GPU fractioning impossible driver-free; "tiny host" ≈ 0.9–1.4 GB floor not literal zero; swtpm vTPM; nft not firewalld; gluster sunset). It stops short of a **concrete, projectable host image**. This audit adds exactly that layer and reconciles it against the current tree, where three things are true today that the Mini design must change:

1. **The tree binds VFIO Intel-only and by empty IDs.** `usr/lib/bootc/kargs.d/20-vfio.toml:4-8` hardcodes `intel_iommu=on` + `vfio_pci.ids=` (empty); `01-mios-vfio.toml:3-9` is the SSOT-rendered one (`rd.driver.pre=vfio-pci`, both `intel_iommu`/`amd_iommu`, `iommu=pt`). The Mini host must bind **all** dGPUs, AMD-or-Intel, from the SSOT GPU list — not a single hand-set string.
2. **The tree's firewall is firewalld, not nft.** `automation/45-firewall.sh:22-49` generates a `firewall-cmd`-based init script and `[network].firewalld_default_zone = "drop"` (`mios.toml:299`). The Mini host **removes firewalld** and owns one hand-authored `inet` table (doc §3b-cross). This is a real divergence, resolved in §4.3.
3. **The GPU→guest map already exists but nothing consumes it for the bind.** `[metal.gpu]` (`mios.toml:322-326`) declares `assignments = { mios-guest = ["0000:01:00.0"] }` and `arbitration = "static"`, but no projector turns that into a driverctl override or a `vfio-pci.ids` stamp. §4.1 is that missing projector.

**Grounding evidence (all real):**

| Concern | File:line | What it gives us | What the Mini needs on top |
|---|---|---|---|
| IOMMU + early vfio bind | `usr/lib/bootc/kargs.d/01-mios-vfio.toml:3-9` | `rd.driver.pre=vfio-pci`, `intel_iommu=on amd_iommu=on iommu=pt` | driven fully from `[metal.gpu]`, all dGPU BDFs |
| Generic vfio hooks | `usr/lib/bootc/kargs.d/20-vfio.toml:4-8` | `kvm.ignore_msrs=1`, `vfio_pci.ids=` | AMD parity; ids populated from SSOT |
| Blackwell idle fix | `usr/lib/bootc/kargs.d/13-rtx50-vfio-workaround.toml:4-6` | `vfio_pci.disable_idle_d3=1` | keep as-is (RTX 50 passthrough) |
| kargs projector | `automation/75-kargs-render.sh:37-133` | renders `[kargs]`→`01-mios-vfio.toml`/`99-mios-kargs.toml` | extend to accept BDF→id resolution (§4.1) |
| `[kargs]` SSOT | `mios.toml:11437-11444` | `iommu`, `vfio_ids`, `hugepages`, `isolcpus`, `nohz_full`, `rcu_nocbs`, `THP` | the housekeeping/isolcpus split (§4.2) |
| GPU→guest map | `mios.toml:322-326` `[metal.gpu]` | `assignments`, `arbitration="static"` | the bind projector consumes it (§4.1) |
| CDI device surface | `mios.toml:675-676` `[gpu]` | `device = "nvidia.com/gpu=all"` | guest-side only, downstream of vfio |
| Domain XML skeleton | `usr/libexec/mios/Xbox-Final-NoAutoSelect.xml:1-249` | q35+OVMF-secboot, `<cputune>`, `<hostdev managed="yes">`, **`<tpm model="tpm-crb"><backend type="emulator" version="2.0"/>` (177-179)** | generalize to all-dGPU + NIC-less + hugepages/numatune (§4.6) |
| Render convention | `usr/libexec/mios/virt-apply.sh:82-84` | `sed 's|{{PLACEHOLDER}}|val|g'` XML templating | reuse for the guest template |
| VFIO state check | `usr/libexec/mios/vfio-check.sh:24-35` | reads `/etc/modprobe.d/vfio.conf` + `/sys/bus/pci/drivers/vfio-pci` | Mini binds via kargs+driverctl, not modprobe.d (§4.1 note) |
| nft convention | `usr/share/mios/security/egress.nft:1-15` | `table inet mios_egress`, generated-header style, `nft -f` apply | the master `inet mios-router` table (§4.3) |
| Root-quadlet allowlist | `mios.toml:786-808` `[security.privileged_quadlets].root` | Law 6 exception list | add `mios-headscale.container` (§4.4) |
| NTP / UPS host-owned | `mios.toml:305-320` | chrony servers; `[power.ups]` inert | host-master posture (doc §2a) |

---

## 1. The host, in one paragraph

MiOS-Metal is a derived `fedora-bootc-minimal` image carrying **only** the hypervisor+router floor: `libvirt`(≥12.2.0)+`qemu-kvm`+`edk2/OVMF`+`swtpm`, `driverctl`, `nftables`, `dnsmasq`, `hostapd`, `chrony`, `nut`, `headscale`+`tailscale`, and (AMD only) a `vendor-reset` akmod. **No firewalld, no ROCm/CUDA, no desktop, no k3s.** At early boot the signed-UKI cmdline (`intel_iommu=on amd_iommu=on iommu=pt rd.driver.pre=vfio-pci vfio-pci.ids=<all dGPU ids>`) plus `/etc/driverctl.d` overrides claim every discrete GPU for `vfio-pci` before any GPU driver can. libvirt boots the full MiOS guest qcow2 as one super-privileged domain: `<hostdev>` for every dGPU IOMMU group, `host-passthrough` CPU pinned to the non-housekeeping cores, hugepages+`<locked/>`, `numatune strict`, an emulated `swtpm` vTPM, and **exactly one** `virtio-net` to the host's `mios-guest` bridge — the guest's only path to the world, routed through nft + tailscale/headscale on the host.

---

## 2. bootc host image contents (the layer)

Layer this over `quay.io/fedora/fedora-bootc:minimal` (D1 in the north-star doc). The Containerfile below is the concrete expression of doc §2a's dependency-floor table; nothing here is on the host that isn't required by *routing* or *hypervision*.

```dockerfile
# Containerfile.mini  --  MiOS-Metal hypervisor-router host (bootc)
# Projected package set == doc-mios-metal.md §2a floor. NO firewalld / ROCm / desktop / k3s.
FROM quay.io/fedora/fedora-bootc:minimal

# --- hypervisor floor (the irreducible KVM host) ---
RUN dnf -y install \
      libvirt-daemon-kvm qemu-kvm edk2-ovmf swtpm swtpm-tools \
      libvirt-client virtiofsd \
 # --- the bind front-end ---
      driverctl pciutils \
 # --- router / AP data plane ---
      nftables dnsmasq hostapd iproute \
 # --- host services owned by the metal ---
      chrony nut \
 # --- mesh control + data plane ---
      headscale tailscale \
 && dnf -y remove firewalld \
 && dnf clean all

# vendor-reset akmod is AMD-only + image-baked (doc §2a / R5); gate on [metal.gpu] vendor.
# COPY / akmods build step omitted here -- add only when an AMD dGPU is in the assignment set.

# SSOT-projected surfaces (rendered at build by mios-sync-toml; drift-gated, NOT hand-authored):
#   /usr/lib/bootc/kargs.d/*.toml          (iommu + vfio-pci.ids + isolcpus/hugepages)  <- 75-kargs-render.sh
#   /etc/driverctl.d/20-mios-metal.conf     (per-BDF vfio-pci overrides)                  <- §4.1 drop-in
#   /etc/nftables.d/mios-router.nft        (master inet table)                           <- §4.3 drop-in
#   /etc/hostapd/hostapd.conf              (country/EHT/WPA3-SAE)                         <- from [metal.wifi]
#   /etc/dnsmasq.d/mios-guest.conf         (DHCP/DNS on guest bridge + split-DNS)        <- from [metal.net]
#   /etc/headscale/config.yaml + policy.hujson                                            <- §4.4 drop-in
#   /etc/libvirt/qemu/mios-guest.xml       (guest domain)                                <- §4.6 drop-in

RUN systemctl enable libvirtd nftables dnsmasq chrony \
 && systemctl enable mios-headscale.service mios-metal-vfio-verify.service

LABEL mios.plane="mini-host" mios.firewall="nftables" mios.gpu="vfio-pci-all"
```

**Why each line is on the host and not the guest** is already argued in doc §2a; the only additions here are the **explicit `dnf -y remove firewalld`** (resolving gap #2 above) and the `swtpm-tools`/`virtiofsd` pair the guest domain in §4.6 needs.

---

## 3. The SSOT surface (extend `[metal.*]`)

The bind, the routing, the mesh, and the guest split all project from one `[metal]` block. `[metal.gpu]` exists (`mios.toml:322-326`); the rest is the concrete extension this audit proposes. Keep the operator authoring **this**, never the rendered files (doc §1.1: "zero hand-maintained config").

```toml
# ---- extend mios.toml -------------------------------------------------------
[metal]
enable        = false            # ships INERT until a real Mini box is provisioned (fail-safe)
wan_iface     = "enp1s0"         # the uplink NIC the host masquerades to
guest_bridge  = "mios-guest"     # the libvirt bridge the NIC-less guest's single virtio-net joins

[metal.gpu]                       # EXISTS today (mios.toml:322). assignments = guest -> [BDF,...]
assignments   = { mios-guest = ["0000:01:00.0"] }
arbitration   = "static"         # "static" = pre-bind at boot (the driver-free-host invariant)
host_console_reserve = ""        # optional: a BDF (or "igpu") kept on the host for a console (doc §2d)

[metal.cpu]                       # the router-floor-first budget (doc §2e)
housekeeping  = "0-1,16-17"      # cores RESERVED for the host packet path -- sized BEFORE the guest
# guest cores == all cores MINUS housekeeping; isolcpus below fences them for the guest
isolcpus      = "2-15,18-31"
nohz_full     = "2-15,18-31"
rcu_nocbs     = "2-15,18-31"

[metal.mem]
hugepages_1g  = 96               # 1GiB pages locked to the guest (96 GiB); host keeps the remainder
numa_node     = 0                # the NUMA node the assigned dGPU(s) hang off

[metal.wifi]                      # host owns the radio (doc §2a)
enable   = false
country  = "US"
ssid     = "MiOS"
band     = "6g"                  # Wi-Fi 6E/7; 802.11be AP mode is driver-gated (doc R7)

[metal.mesh]                      # host owns the tailnet (doc §2a)
headscale_url   = "https://mini.mios.local:8642"
advertise_routes = ["192.168.64.0/24"]   # the guest bridge subnet the host subnet-routes
exit_node        = true
router_tag       = "tag:router"
# policy is fail-closed by default (doc R6); empty == deny, never allow-all
```

> **Reconciliation note (real gap).** `75-kargs-render.sh` reads `[kargs].vfio_ids` as a raw `vendor:device` string (`mios.toml:11438`). `[metal.gpu].assignments` names **BDFs**, not vendor:device IDs. The §4.1 projector closes this: it resolves each BDF → `vendor:device` (SBOM-not-hardcode: resolved at build/first-boot via `lspci`, not hand-pinned), writes the driverctl overrides by BDF, and **stamps** `[kargs].vfio_ids` so the existing kargs render keeps working unchanged.

---

## 4. Drop-in artifacts

### 4.1 vfio-pci bind (SSOT-driven) — **DROP-IN #1**

Two coordinated outputs, both projected from `[metal.gpu].assignments`, so the host loads no GPU driver:

- **early bind (wins the race):** `vfio-pci.ids=<vendor:device,...>` on the signed-UKI cmdline via the existing `01-mios-vfio.toml`/`75-kargs-render.sh` path, plus `rd.driver.pre=vfio-pci`.
- **persistent per-slot bind (survives id collisions):** `/etc/driverctl.d/20-mios-metal.conf` — `driverctl` binds by **BDF**, so two identical cards (same `vendor:device`) still each land on `vfio-pci` and the wrong one is never claimed by `amdgpu`/`nvidia`/`i915`.

Save as `usr/libexec/mios/mios-metal-vfio-bind` (mode 0755). It is a **bake-time projector** (like `75-kargs-render.sh`) plus a `--verify` post-boot mode (like `vfio-check.sh`).

```bash
#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Projects [metal.gpu].assignments (BDFs) into the driver-free-host vfio-pci bind:
#   writes /etc/driverctl.d/20-mios-metal.conf (per-BDF overrides) and stamps [kargs].vfio_ids
#   (BDF->vendor:device resolved at build, SBOM-not-hardcode) for 75-kargs-render.sh.
# AI-related: automation/75-kargs-render.sh, usr/lib/bootc/kargs.d/01-mios-vfio.toml,
#   usr/libexec/mios/vfio-check.sh, usr/share/mios/mios.toml
set -euo pipefail
TOML="${MIOS_TOML:-/usr/share/mios/mios.toml}"
DRIVERCTL_D="${DRIVERCTL_D:-/etc/driverctl.d}"
OUT="${DRIVERCTL_D}/20-mios-metal.conf"

# ---- read the SSOT: flatten every BDF across every guest in [metal.gpu].assignments ----
mapfile -t BDFS < <(python3 - "$TOML" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1],"rb"))
mini = cfg.get("mini",{}).get("gpu",{})
reserve = str(mini.get("host_console_reserve","")).strip()
seen=[]
for guest, bdfs in (mini.get("assignments") or {}).items():
    for b in bdfs:
        b=b.strip()
        if b and b != reserve and b not in seen:
            seen.append(b)
print("\n".join(seen))
PY
)

if [[ "${1:-}" == "--verify" ]]; then
    rc=0
    for bdf in "${BDFS[@]}"; do
        drv="$(basename "$(readlink -f "/sys/bus/pci/devices/${bdf}/driver" 2>/dev/null || echo none)")"
        if [[ "$drv" != "vfio-pci" ]]; then
            echo "FAIL ${bdf}: bound to '${drv}', expected vfio-pci (slot moved? id race lost?)" >&2
            rc=1
        else
            echo "ok   ${bdf}: vfio-pci"
        fi
    done
    exit $rc
fi

# ---- emit per-BDF driverctl overrides (bind by slot -- id-collision safe) ----
mkdir -p "$DRIVERCTL_D"
{
    echo "# GENERATED from mios.toml [metal.gpu].assignments -- DO NOT EDIT."
    echo "# Regenerate: mios-metal-vfio-bind   |   Verify (post-boot): mios-metal-vfio-bind --verify"
    for bdf in "${BDFS[@]}"; do
        echo "${bdf} vfio-pci"                      # driverctl set-override <BDF> vfio-pci
    done
} > "$OUT"

# ---- resolve BDF -> vendor:device (SBOM-not-hardcode: from live PCI, not hand-pinned) ----
ids=""
for bdf in "${BDFS[@]}"; do
    id="$(cat "/sys/bus/pci/devices/${bdf}/vendor" 2>/dev/null | sed 's/0x//')"
    dev="$(cat "/sys/bus/pci/devices/${bdf}/device" 2>/dev/null | sed 's/0x//')"
    # audio/bridge functions in the same IOMMU group must ride along:
    grp="$(basename "$(readlink -f "/sys/bus/pci/devices/${bdf}/iommu_group" 2>/dev/null)")"
    for fn in /sys/kernel/iommu_groups/"${grp}"/devices/*; do
        v="$(cat "$fn/vendor" 2>/dev/null | sed 's/0x//')"; d="$(cat "$fn/device" 2>/dev/null | sed 's/0x//')"
        [[ -n "$v" && -n "$d" ]] && ids+="${v}:${d},"
    done
done
ids="${ids%,}"

# ---- stamp [kargs].vfio_ids so 75-kargs-render.sh emits vfio-pci.ids= on the UKI cmdline ----
python3 - "$TOML" "$ids" <<'PY'
import sys, re
path, ids = sys.argv[1], sys.argv[2]
txt = open(path, encoding="utf-8").read()
txt = re.sub(r'(?m)^(vfio_ids\s*=\s*)".*"', r'\1"%s"' % ids, txt, count=1)
open(path,"w",encoding="utf-8").write(txt)
print(f"[mini-vfio] stamped [kargs].vfio_ids = {ids}")
PY
echo "[mini-vfio] wrote ${OUT} ($(wc -l < "$OUT") lines)"
```

Then the *existing* `automation/75-kargs-render.sh:70-73` picks up `[kargs].vfio_ids` and writes `vfio-pci.ids=` into `01-mios-vfio.toml` — no change to the render path. A `mios-metal-vfio-verify.service` (oneshot, `After=basic.target`) runs `mios-metal-vfio-bind --verify` and **fails loud** on a slot swap (doc step 4). Note: this deliberately uses `kargs.d` + `driverctl.d`, **not** `/etc/modprobe.d/vfio.conf` that `vfio-check.sh:24` reads — on a bootc host the kargs path is the SSOT; `modprobe.d` is the mutable-Arch tool's surface and is not authoritative here.

### 4.2 CPU/RAM partition (kargs, from `[metal.cpu]`/`[metal.mem]`)

The `75-kargs-render.sh:92-128` path already emits `isolcpus`/`nohz_full`/`rcu_nocbs`/`hugepages` into `99-mios-kargs.toml` from `[kargs]`. Point those `[kargs]` values at the `[metal.cpu]`/`[metal.mem]` computation (router-floor-first, doc §2e): **housekeeping cores are subtracted first**, the guest gets the isolated remainder, and the drift-gate fails if the guest share would leave the router below its floor. Rendered result (indicative, 32-thread box):

```
isolcpus=2-15,18-31  nohz_full=2-15,18-31  rcu_nocbs=2-15,18-31  default_hugepagesz=1G hugepagesz=1G hugepages=96
```

### 4.3 nft routing ruleset — **DROP-IN #2** (`table inet mios-router`)

Replaces firewalld on the Mini host (gap #2; doc §3b-cross). One hand-authored master `inet` table; libvirt/netavark/tailscale each own their **own** table and coexist by hook priority. Follows the `egress.nft:1-4` generated-header + `nft -f` convention. Save as `usr/share/mios/mini/mios-router.nft` (projected to `/etc/nftables.d/mios-router.nft`).

```nft
# AI-hint: GENERATED master router table for MiOS-Metal. DO NOT EDIT -- regenerate from mios.toml [metal].
# Apply: nft -f /etc/nftables.d/mios-router.nft   |   Remove: nft delete table inet mios-router
# Devices are projected from [metal].wan_iface / [metal].guest_bridge; subnets from [metal.mesh].
define WAN   = enp1s0            # <- [metal].wan_iface
define GUEST = mios-guest        # <- [metal].guest_bridge  (the NIC-less guest's only link)
define TSNET = 100.64.0.0/10     # tailnet CGNAT range (matches egress.nft:11)

table inet mios-router {
    # HW offload where the NIC implements TC_SETUP_FT; else SW fast-path (doc §2e).
    flowtable ft {
        hook ingress priority filter
        devices = { $WAN, $GUEST }
        flags offload
    }

    chain input {
        type filter hook input priority filter; policy drop
        iif "lo" accept
        ct state established,related accept
        ct state invalid drop
        # host admin services on the guest bridge only (never on WAN):
        iifname $GUEST tcp dport 22 accept
        iifname $GUEST udp dport { 53, 67 } accept          # dnsmasq DNS/DHCP
        iifname $GUEST tcp dport 53 accept
        iifname $GUEST tcp dport 8642 accept                # headscale control plane
        # WireGuard / tailscale data plane arrives on WAN:
        iifname $WAN udp dport 41641 accept                 # tailscaled
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept
    }

    chain forward {
        type filter hook forward priority filter; policy drop
        # offload established flows to the fast path (bypasses per-packet hooks):
        ct state established,related meta l4proto { tcp, udp } flow add @ft
        ct state established,related accept
        # guest -> world (the ONLY egress path the guest has):
        iifname $GUEST oifname $WAN accept
        # world -> guest only for return traffic (covered by established above); else drop.
        # per-bridge isolation: no bridge-to-bridge leakage (single guest bridge today).
        iifname $GUEST oifname $GUEST drop
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept
        oifname $WAN masquerade                             # guest subnet -> WAN
    }
}
```

The drift-gate must confirm no *other* table installs a conflicting masquerade/forward verdict on `$GUEST`, and that conntrack sees both directions across the bridge (doc §3b-cross).

### 4.4 headscale mesh join — **DROP-IN #3** (Quadlet + fail-closed policy)

The host owns the tailnet. Runs as a **root** Quadlet — so `mios-headscale.container` must be added to `[security.privileged_quadlets].root` (`mios.toml:786-808`) or `check_quadlet_privilege` fails (postcheck item 13). State lives on `/var/lib/headscale` (survives `bootc upgrade`; doc §2a). Save as `usr/share/containers/systemd/mios-headscale.container`.

```ini
# AI-hint: MiOS-Metal headscale control plane (host owns the tailnet). Root Quadlet --
#   MUST be listed in mios.toml [security.privileged_quadlets].root or drift-check 13 fails.
# AI-related: usr/share/mios/mini/headscale-policy.hujson, mios.toml [metal.mesh]
[Unit]
Description=MiOS-Metal headscale control plane
After=network-online.target nftables.service
Wants=network-online.target

[Container]
Image=ghcr.io/juanfont/headscale:v0.29.2
User=root
PublishPort=8642:8080
Volume=/var/lib/headscale:/var/lib/headscale:Z
Volume=/etc/headscale:/etc/headscale:ro,Z
Exec=serve

[Service]
Restart=always

[Install]
WantedBy=multi-user.target
```

Fail-closed policy (doc R6: empty default == deny, **never** allow-all). Save as `usr/share/mios/mini/headscale-policy.hujson`, projected to `/etc/headscale/policy.hujson`:

```hujson
{
  // GENERATED from mios.toml [metal.mesh] -- fail-closed. Empty groups == deny.
  "tagOwners": { "tag:router": ["mini-admin"] },
  "autoApprovers": {
    // the host subnet-router pre-approves ONLY the guest bridge route it advertises:
    "routes": { "192.168.64.0/24": ["tag:router"] },
    "exitNode": ["tag:router"]
  },
  "acls": [
    // default-deny is implicit; grant only guest-subnet -> declared destinations.
    { "action": "accept", "src": ["192.168.64.0/24"], "dst": ["autogroup:internet:*"] }
  ]
}
```

`tailscaled` then joins as subnet-router/exit-node against this control plane (`--advertise-routes=192.168.64.0/24 --advertise-exit-node`, `[metal.mesh]`); kernel routing mode for line-rate (doc §3b). Because the guest is a *routed subnet, not a tailnet node* (doc §3b mini-gap), Grants apply to the **route**, and embedded DERP is disabled on the single box.

### 4.5 swtpm vTPM wiring

Already correct in the tree — `Xbox-Final-NoAutoSelect.xml:177-179` carries exactly the upstream-standard KVM answer:

```xml
<tpm model="tpm-crb">
  <backend type="emulator" version="2.0"/>
</tpm>
```

libvirt spawns `swtpm` per-domain; NVRAM state lands on host `/var/lib/libvirt/swtpm/<domain>` and must be backed by the DR state-guard (doc R4). This gives the guest its **own** PCRs for in-guest `clevis-tpm2` / `systemd-cryptenroll --tpm2` FDE — a sealing root independent of the host's physical TPM (doc §2b). The host image adds `swtpm swtpm-tools` (§2); no host TPM passthrough. The skeleton in §4.6 keeps this block verbatim.

### 4.6 guest domain XML skeleton — **DROP-IN #4**

Generalizes `Xbox-Final-NoAutoSelect.xml` for the Mini guest: **all** assigned dGPU IOMMU groups via a repeatable `<hostdev>` block, `<vcpupin>` matched to the isolated cores, hugepages+`<locked/>`, `numatune strict` on the dGPU's NUMA node, the swtpm vTPM, and **exactly one** `virtio-net` to `mios-guest` (the guest's only wire — no second NIC). Rendered with the same `sed 's|{{X}}|val|g'` convention as `virt-apply.sh:82-84`. Save as `usr/share/mios/mini/mios-guest.xml.tmpl`; project to `/etc/libvirt/qemu/mios-guest.xml`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED from mios.toml [metal.*]. Placeholders rendered by mios-metal render (sed). -->
<domain type="kvm">
  <name>mios-guest</name>
  <uuid>{{MIOS_GUEST_UUID}}</uuid>

  <!-- 75-90% of RAM as locked 1GiB hugepages ([metal.mem].hugepages_1g) -->
  <memory unit="GiB">{{MIOS_GUEST_MEM_GIB}}</memory>
  <currentMemory unit="GiB">{{MIOS_GUEST_MEM_GIB}}</currentMemory>
  <memoryBacking>
    <hugepages><page size="1" unit="G"/></hugepages>
    <locked/>
    <nosharepages/>
  </memoryBacking>

  <!-- vCPUs == the isolcpus set from [metal.cpu]; emulator == housekeeping cores -->
  <vcpu placement="static">{{MIOS_GUEST_VCPUS}}</vcpu>
  <cputune>
    <!-- {{MIOS_GUEST_VCPUPIN}} expands to one <vcpupin vcpu=N cpuset=C/> per isolated core -->
    {{MIOS_GUEST_VCPUPIN}}
    <emulatorpin cpuset="{{MIOS_HOUSEKEEPING_CPUS}}"/>   <!-- [metal.cpu].housekeeping -->
  </cputune>
  <numatune>
    <memory mode="strict" nodeset="{{MIOS_GUEST_NUMA_NODE}}"/>  <!-- [metal.mem].numa_node -->
  </numatune>

  <os>
    <type arch="x86_64" machine="pc-q35-10.1">hvm</type>
    <!-- GUEST's OWN Secure Boot domain (separate from host UKI SB) -->
    <loader readonly="yes" secure="yes" type="pflash">/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd</loader>
    <nvram template="/usr/share/edk2/x64/OVMF_VARS.4m.fd">/var/lib/libvirt/qemu/nvram/mios-guest_VARS.fd</nvram>
    <bootmenu enable="yes"/>
  </os>
  <features><acpi/><apic/><smm state="on"/></features>
  <cpu mode="host-passthrough" check="none" migratable="off">
    <cache mode="passthrough"/>
    <feature policy="require" name="invtsc"/>
  </cpu>
  <clock offset="utc"/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>

  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>

    <!-- ===== ALL assigned dGPUs ([metal.gpu].assignments[mios-guest]) ===== -->
    <!-- {{MIOS_GUEST_HOSTDEV_GPUS}} expands to one managed hostdev per BDF (GPU + its -->
    <!-- HD-audio/bridge functions in the same IOMMU group). Managed='yes' auto-unbinds -->
    <!-- from vfio-pci at start and rebinds at teardown. Template for one function:      -->
    <!--                                                                                 -->
    <!--   <hostdev mode="subsystem" type="pci" managed="yes">                           -->
    <!--     <source><address domain="0x0000" bus="0xNN" slot="0xNN" function="0xN"/></source> -->
    <!--     <rom bar="off"/>                                                             -->
    <!--   </hostdev>                                                                     -->
    {{MIOS_GUEST_HOSTDEV_GPUS}}

    <!-- ===== optional dedicated data controller (multi-drive box; doc §2c) ===== -->
    <!-- NEVER the boot NVMe. {{MIOS_GUEST_HOSTDEV_STORAGE}} is empty on single-drive boxes -->
    {{MIOS_GUEST_HOSTDEV_STORAGE}}

    <!-- ===== single-drive box: virtio-backed guest volume on host /var (doc §2c) ===== -->
    <disk type="file" device="disk">
      <driver name="qemu" type="qcow2" cache="none" io="native" discard="unmap"/>
      <source file="/var/lib/libvirt/images/mios-guest.qcow2"/>
      <target dev="vda" bus="virtio"/>
    </disk>

    <!-- ===== THE ONLY WIRE: one virtio-net to the host guest-bridge. NO second NIC. ===== -->
    <interface type="bridge">
      <source bridge="{{MIOS_GUEST_BRIDGE}}"/>          <!-- [metal].guest_bridge -->
      <mac address="{{MIOS_GUEST_MAC}}"/>
      <model type="virtio"/>
      <driver name="vhost" queues="4"/>
    </interface>

    <!-- ===== emulated vTPM (verbatim from Xbox-Final-NoAutoSelect.xml:177-179) ===== -->
    <tpm model="tpm-crb">
      <backend type="emulator" version="2.0"/>
    </tpm>

    <!-- host-side serial for headless recovery (doc §2d); no SPICE, no emulated video -->
    <serial type="pty"><target type="isa-serial" port="0"><model name="isa-serial"/></target></serial>
    <console type="pty"><target type="serial" port="0"/></console>
    <video><model type="none"/></video>
    <memballoon model="none"/>
    <watchdog model="itco" action="reset"/>
  </devices>
</domain>
```

The renderer (`mios-metal` verb / oneshot) computes `MIOS_GUEST_VCPUS`, `MIOS_GUEST_VCPUPIN`, `MIOS_GUEST_MEM_GIB`, and the `MIOS_GUEST_HOSTDEV_GPUS` loop from `[metal.cpu]`/`[metal.mem]`/`[metal.gpu]`, then `virsh define`s it (mirroring `virt-apply.sh:82-86`). Guest share is computed from the **router floor first** (doc §2e); the drift-gate rejects a render that leaves the housekeeping slice under its declared minimum.

---

## 5. Sequenced build/deploy steps (maps to doc §4)

1. **Build the host image** — `Containerfile.mini` (§2). `dnf remove firewalld`. Bake `vendor-reset` akmod **only if** `[metal.gpu].assignments` contains an AMD BDF.
2. **Project the bind** — run `mios-metal-vfio-bind` (§4.1) at bake: writes `/etc/driverctl.d/20-mios-metal.conf` + stamps `[kargs].vfio_ids`; `75-kargs-render.sh` then emits the UKI cmdline. Bake a **second, non-vfio recovery UKI entry** (doc §2d).
3. **Sign + install** — `systemd-ukify` the cmdline; `bootc install to-disk`; enroll host LUKS with `systemd-cryptenroll --tpm2-public-key-pcrs=11` **plus an escrowed recovery passphrase** (doc R3).
4. **Verify the bind** — `mios-metal-vfio-verify.service` runs `mios-metal-vfio-bind --verify`; every assigned BDF must read `vfio-pci` or boot fails loud (respecting `host_console_reserve`).
5. **Assign storage** — validate `[metal.gpu]`/storage never names the boot controller; multi-drive → `<hostdev>` the data NVMe; single-drive → virtio-backed volume on `/var` (§4.6; doc §2c).
6. **Stand up routing** — `nft -f /etc/nftables.d/mios-router.nft` (§4.3); `hostapd` + `dnsmasq` on `$GUEST` only with split-DNS; `mios-headscale.container` with the fail-closed policy (§4.4); `tailscaled` subnet-router/exit.
7. **Define + start the guest** — render `mios-guest.xml` (§4.6), `virsh define`, `virsh start`; confirm the guest's **only** route to the world is through the host (doc step 11).
8. **DR state-guard** — pin `/var` (guest qcow2, headscale DB, swtpm NVRAM) against `bootc rollback` skew; wire greenboot↔vendor-reset (doc R4/R5, step 12).

---

## 6. Drift-gates to add (extends `automation/98-drift-checks.sh`)

New fitness-functions, in the style of `check_kargs_projection` (`98-drift-checks.sh:3220+`) and `check_template_conformance` (`:3195-3213`):

- **`check_metal_vfio_projection`** — re-run `mios-metal-vfio-bind` to a tmp dir; fail on any drift between the rendered `20-mios-metal.conf`/stamped `vfio_ids` and the committed files. Also assert every `[metal.gpu].assignments` BDF appears exactly once (doc: "each GPU → exactly one guest", `mios.toml:323`).
- **`check_metal_router_table`** — parse `mios-router.nft`; assert `policy drop` on `forward`+`input`, a `masquerade` only on `$WAN`, and no *other* committed nft table installs a conflicting verdict on `$GUEST` (doc §3b-cross).
- **`check_metal_headscale_failclosed`** — assert `headscale-policy.hujson` has no allow-all ACL and `mios-headscale.container` is in `[security.privileged_quadlets].root` (else `check_quadlet_privilege` already fails).
- **`check_metal_guest_isolation`** — assert the rendered `mios-guest.xml` has **exactly one** `<interface>`, that its bridge == `[metal].guest_bridge`, that `<vcpupin>` ⊆ `[metal.cpu].isolcpus`, and that the housekeeping slice ≥ its declared floor (doc §2e). Also assert the swtpm `<tpm>` block is present.
- **`check_metal_no_firewalld`** — assert the Mini host image does not enable `firewalld` (resolves gap #2).

Note: drift-check **46** (`check_template_conformance`, `98-drift-checks.sh:3195`) gates markdown headers only under `^usr/share/doc/mios/...\.md$|^README\.md$` (`mios.toml:11409-11415`), so this file now lives under usr/share/doc/mios/reference/ so it IS gated — the AI-hint/AI-related headers are carried anyway per the template convention.

---

## 7. Residual risks specific to this concretization

- **[needs-VM] the id-race.** `vfio-pci.ids=` + `rd.driver.pre=vfio-pci` usually wins, but NVIDIA modeset can still grab a card; the driverctl per-BDF override (§4.1) is the belt to that suspenders, verified at boot (step 4). Unprovable without a dGPU box.
- **BDF→id resolution runs where PCI exists.** The §4.1 id-resolution reads `/sys/bus/pci/...`; at pure build-time (container, no host PCI) it must run at **first-boot** instead, then drift-gate the stamped value — same pattern as `nvidia-ctk cdi generate` (doc §2b, "runs only where devices exist").
- **The `[metal.*]` surface is proposed, not landed.** `[metal.gpu]` exists (`mios.toml:322`); `[metal]/[metal.cpu]/[metal.mem]/[metal.wifi]/[metal.mesh]` are this audit's extension. Landing them is a `mios.toml` + `mios-sync-toml` change (Law 15: update both repos), not covered here.
- **firewalld removal is a host-image divergence.** `[network].firewalld_default_zone` (`mios.toml:299`) and `45-firewall.sh` remain correct for the *single-plane* MiOS-on-metal build; the Mini host is the only image that strips firewalld. The build must branch on plane, or the drift-gate `check_metal_no_firewalld` will fight `45-firewall.sh` on a shared tree.
- Everything inherited from the north-star doc (R1–R11) still applies; this audit changes none of those verdicts, only makes the host concrete.
