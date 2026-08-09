<!-- AI-hint: ADR-0005: Unified Native Resolver Architecture. Historically, MiOS maintained three parallel SSOT resolver implementations: 1. `usr/lib/mios/mios_toml.py` (Python) 2. `tools/lib/userenv.sh` and `usr/lib/mios/userenv.sh` (Bash) 3. `automation/lib/globals.ps1` (PowerShell)
     AI-related: usr/share/mios/mios.toml, docs/adr/, AGY-TASKS.md -->
# ADR-0005: Unified Native Resolver Architecture

## Context & Problem Statement
Historically, MiOS maintained three parallel SSOT resolver implementations:
1. `usr/lib/mios/mios_toml.py` (Python)
2. `tools/lib/userenv.sh` and `usr/lib/mios/userenv.sh` (Bash)
3. `automation/lib/globals.ps1` (PowerShell)

These parallel implementations resulted in drift risk, duplicated logic, and maintenance overhead across Linux and Windows execution environments.

## Decision
Collapse all SSOT resolver surfaces into a single compiled Rust crate: `tools/native/mios-resolver`.
- **Framework**: `figment` for multi-layered TOML configuration loading (vendor, host, user, `.d` drop-ins).
- **Strangler-Fig Cutover Sequence**: Shell -> PowerShell -> Python -> Install Env -> Names Registry.
- **Rollback Safety**: `[migration]` SSOT toggles (`use_rust_resolver_*`) allowing instant fallback to legacy shims without build reverts.
- **Fitness Functions**:
  - `check_resolver_shell_equivalence`: Byte-identical bash snapshot checks.
  - `check_resolver_ps_equivalence`: Regeneration equivalence for `globals.generated.ps1`.
  - Differential proptest gate: Automated equivalence verification (`crate == python == bash`).
  - `deny.toml`: Supply-chain security and license policy enforcement via `cargo-deny`.

## Consequences
- Single source of truth for configuration resolution logic across Linux and Windows.
- Compiler-grade `miette` diagnostic errors identifying exact line spans on malformed TOML keys.
- Deletion of legacy heredoc fallbacks and reduction of drift-check duplication.
