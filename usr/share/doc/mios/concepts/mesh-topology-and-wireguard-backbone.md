<!-- AI-hint: Blueprint and architectural specification for the MiOS v4 multi-site blade mesh, WireGuard/Headscale backbone, and translocation. -->
<!-- AI-related: usr/share/doc/mios/adr/0016-blade-node-topology.md, usr/share/doc/mios/adr/0020-edge-mesh-binary-wire-protocol-and-dual-tier-sandboxing.md -->
# MiOS Mesh Topology — Interactive Diagrams

Self-contained, interactive HTML visualisations of the MiOS **friends/collective Headscale
mesh**: MiOS-Mini **Blades** as the WireGuard backbone, MiOS **Nodes** (containers / services /
arch-matched VMs) riding on top and migrating live, per-site **exit nodes** egressing through a
chosen **FOSS external VPN** region, and an **RTC simulation** modelling faults, load-balancing,
MiOS-Xbox contention, and external-VPN translocation.

Open in any browser (pan = drag, zoom = scroll). No build step; loads Tailwind/Lucide/html2canvas
from CDN, so it needs internet the first time.

## Files

| File | Notes |
|---|---|
| `mios-mesh-topology-v4.html` | **Current.** The refined model — see "v4 changes" below. |
| `mios-mesh-topology-v3.html` | Prior version (the earlier "SSOT Topology Matrix" iteration), kept for history. |

## v4 changes

- **Blades index from 0** — `B0…B5` (0 is natural; not 1).
- **Friends / collective network, not a family** — separate physical addresses:
  Site α (Ravi's Loft, Lisbon PT), Site β (Mara's Studio, Denver US), Site γ (Field Kit,
  transient/roaming). The old "Dad's phone" / "Kids' rig" labels are gone (→ Ada's Pixel,
  Rhea's Gaming Rig, etc.).
- **External-VPN egress + translocation** — every blade carries a FOSS-adjacent, WireGuard-based,
  cross-platform egress (Proton, Mullvad, PIA, IVPN) shown as a badge + a violet egress tunnel to
  a virtual **region** marker on the outer ring. A blade can **translocate** its internet exit to
  another region (control panel, or randomly in-sim) while staying in the mesh — **other blades are
  unaffected**, and a blade's physical location is decoupled from its egress region.
- **Exit nodes per site** — each of the three sites has ≥1 blade designated an **EXIT NODE** that
  guards its site's egress behind the external VPN. Any blade *can* become one (egressing = acting
  as an exit node).
- **Blades are the backbone; nodes ride on top** — the mesh core is explicit; nodes do not have to
  sit at the VPN's physical location.
- **Natural (non-outage) migration** — nodes shed from the busiest blade for **load-balance**
  (pre-provisioned, no outage), on top of the existing fault-evacuation path.
- **MiOS-Xbox contention** — "Boot MiOS-Xbox" spins a VFIO gaming VM on an AMD blade; the GPU claim
  causes contention, and other nodes **pre-provision off that blade invisibly** to relieve it.
- **MiOS-aligned refinement** — SSOT `[colors]` palette accents, Headscale/WireGuard/SSOT
  terminology, a legend, and blade cards generated from a single `blades{}` SSOT object.

## RTC controls (right panel)

Time-dilation, pause/resume, recover-all, force outage, **Boot MiOS-Xbox (contention)**, and
**External-VPN Egress translocate** (pick a blade + region → GO). Left panel = SSOT registry map +
legend; click any entry to pan/zoom to it. **Export Diagram** renders a PNG.
