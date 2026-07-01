<!-- AI-hint: Concept documentation explaining the MiOS 3-pod architecture, port-minimization strategy, host services constraint, and SSOT-driven generation lifecycle.
     AI-related: ./MIOS-ROADMAP-2026-06-22.md, ../../../mios.toml, ../../../../tools/generate-pod-quadlets.py, ../../../containers/systemd -->
# MiOS Pod Architecture (2026-06-22)

This document describes the structural transition from disjoint standalone containers to the **3-Pod Capability Architecture**. This refactor minimizes the exposed networking surface and unifies container lifecycle under `podman` pod boundaries.

See `MIOS-ROADMAP-2026-06-22.md` §WS-C for the historical context and original design goals.

## The 3-Pod Map

The containers are now consolidated into three core capability pods, defined in the `mios.toml` SSOT (`[pods.*]`):

1. **`mios-ai`**: The AI plane.
   - Members: `mios-llm-light`, `mios-cpu-node`, `mios-llm-worker@`, `mios-agent-pipe`, `mios-llm-heavy`, `mios-pgvector`, `mios-letta-server`, `mios-open-webui`
   - Rationale: Consolidates the inference engines (CPU, dGPU) and the agent-plane memory datastore (PostgreSQL+pgvector) into a single pod network namespace.
2. **`mios-webtools`**: The scraping, web-search, and developer tools capability.
   - Members: `mios-webtools-redis`, `mios-webtools-firecrawl-api`, `mios-webtools-firecrawl-worker`, `mios-webtools-crawl4ai`, `mios-searxng`, `mios-forge`, `mios-forgejo-runner`, `mios-code-server`
   - Rationale: Groups all scraping components, the SearXNG search engine, and developer tools (code editor, git forge, CI runner) behind a single pod network namespace.
3. **`mios-system`**: Network and system infrastructure.
   - Members: `mios-adguard`, `mios-ceph`, `mios-cockpit-link`, `mios-crowdsec-dashboard`, `mios-pxe-hub`, `mios-k3s`, `mios-guacamole`, `mios-guacd`, `mios-guacamole-postgres`
   - Rationale: Consolidated system services pod for the system-wide DNS resolver, storage, admin interfaces, and remote graphical access suite.

### Standalone Exceptions
A few critical containers remain explicitly outside the pod structure:
- **`mios-open-webui`**: Acts as the user-facing front door, deliberately kept separate (although its systemd service can integrate with the AI pod if configured).

## Port Minimization

The transition to pod-based networking heavily reduced the system's exposed attack surface. By collapsing standalone ports, the host bindings dropped from **~24 raw binds** down to **~8 deliberate front doors**.

For example, internal components like `mios-webtools-redis` or the firecrawl API now operate entirely on the pod's loopback and are never exposed directly to the LAN.

## Host Services Stay Host

A core constraint of the architecture is that **host-services stay on the host**. 
Services like `hermes-agent`, `agent-pipe`, and MCP servers run natively on the host system (often as systemd services). These host services can reach the containerized pod applications via `host.containers.internal` (or simply `localhost` where `Network=host` is used by the pod).

## The SSOT Pod-Gen Lifecycle

The entire pod and container topology is completely deterministic and generated from the Single Source of Truth (SSOT).
- The `[pods.*]` structures are defined in `/usr/share/mios/mios.toml`.
- The Quadlet files (`.pod` definitions and the `Pod=` injection in `.container` files) are rendered at build time using `tools/generate-pod-quadlets.py`.
- This ensures zero configuration drift between the declarative state and the actual systemd units.
