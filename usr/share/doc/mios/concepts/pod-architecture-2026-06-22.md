<!-- AI-hint: Concept documentation explaining the MiOS 7-pod architecture, port-minimization strategy, host services constraint, and SSOT-driven generation lifecycle.
     AI-related: ./MIOS-ROADMAP-2026-06-22.md, ../../../mios.toml, ../../../../tools/generate-pod-quadlets.py, ../../../containers/systemd -->
# MiOS Pod Architecture (2026-06-22)

This document describes the structural transition from disjoint standalone containers to the **7-Pod Capability Architecture**. This refactor minimizes the exposed networking surface and unifies container lifecycle under `podman` pod boundaries.

See `MIOS-ROADMAP-2026-06-22.md` §WS-C for the historical context and original design goals.

## The 7-Pod Map

The containers are now consolidated into seven core capability pods, defined in the `mios.toml` SSOT (`[pods.*]`):

1. **`mios-ai-heavy`**: The dGPU heavy reasoner lanes.
   - Members: `mios-llm-heavy`, `mios-llm-heavy-alt`
   - Rationale: Groups mutually-exclusive heavy inference engines.
2. **`mios-ai-inference`**: The light and CPU lanes.
   - Members: `mios-llm-light`, `mios-cpu-node`, `mios-llm-worker@`
   - Rationale: Groups the primary multi-model and fallback CPU inference engines.
3. **`mios-ai-data`**: The agent-plane memory datastore.
   - Members: `mios-pgvector`
   - Rationale: Unified PostgreSQL+pgvector database.
4. **`mios-webtools`**: The scraping and web-search capability tools.
   - Members: `mios-webtools-firecrawl-api`, `mios-webtools-firecrawl-worker`, `mios-webtools-redis`, `mios-webtools-crawl4ai`
   - Rationale: Groups all scraping components behind a single pod network namespace.
5. **`mios-devforge`**: The developer environment.
   - Members: `mios-code-server`, `mios-forge`, `mios-forgejo-runner`
   - Rationale: Consolidates the code editor, git forge, and CI runner.
6. **`mios-netinfra-dns`**: Network infrastructure.
   - Members: `mios-adguard`
   - Rationale: Dedicated pod for the system-wide DNS resolver.
7. **`mios-remote-desktop`**: Remote graphical access.
   - Members: `mios-guacamole`, `mios-guacd`, `mios-guacamole-postgres`
   - Rationale: Groups the Apache Guacamole remote desktop suite.

### Standalone Exceptions
A few critical containers remain explicitly outside the pod structure:
- **`mios-open-webui`**: Acts as the user-facing front door, deliberately kept separate.
- **`mios-searxng`**: Standalone instance that now only publishes to the loopback interface, consumed solely by the host agent.

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
