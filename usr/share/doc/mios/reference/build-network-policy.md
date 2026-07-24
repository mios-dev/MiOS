<!-- AI-hint: Technical reference on MiOS build-time network fetch policy, retry requirements, and degrade-open classification rules. -->
---
title: Build-Time Network Fetch Policy Reference
description: Technical specification and policy rules for build-time network downloads, retry enforcement, credential masking, and degrade-open classification.
type: reference
---

# Build-Time Network Fetch Policy Reference

## Overview

MiOS container builds and image composition pipelines execute across both local developer hosts and automated CI runners (GitHub Actions and Forgejo). To ensure robust, reproducible, and resilient builds under transient network failures (such as HTTP 429 rate limits or HTTP 504 gateway timeouts), all network downloads MUST adhere to strict policy rules.

## Core Network Policy Laws

### 1. SSOT Resolution (SBOM-Not-Hardcode)
- **Law**: Download URLs, release tags, and version strings MUST resolve from `mios.toml` SSOT configuration or `userenv.sh` environment bindings.
- **Rule**: Never hardcode version tags or SHA digests directly in scripts or Containerfiles. Record resolved hashes at build time in the SBOM (`usr/share/mios/artifacts/sbom/bound-images.tsv`).

### 2. Mandatory Retries & Timeouts
- **Law**: Every network fetch (`curl`, `wget`) MUST specify explicit retry counts and connection timeouts.
- **Enforcement**:
  - `curl` invocations MUST include `--retry 3` (or higher), `--retry-delay`, and `--connect-timeout`.
  - Alternatively, use the `scurl` wrapper (`automation/lib/masking.sh`), which automatically injects `--retry 5 --retry-delay 3 --connect-timeout 20`.
  - Monitored by `automation/38-drift-checks.sh` (Check 64: `check_curl_retry`).

### 3. Classification: Fatal vs. Degrade-Open
- **FATAL (Core Binaries)**: Downloads required for core system binaries or base OS layers (e.g., core packages, base image layers) MUST fail the build cleanly on exit (`exit 1`).
- **DEGRADE-OPEN (Provenance & Auxiliary Assets)**: Optional metadata, telemetry, or provenance artifacts (e.g. `automation/90-generate-sbom.sh`) MUST NOT fail the image build. If network access or tool installation fails, log a `WARN` message and exit cleanly (`exit 0`).

### 4. Credential Masking (`scurl`)
- **Law**: Requests requiring authentication headers (e.g., GitHub API, GHCR tokens) MUST route through `scurl` or use `-H "Authorization: Bearer ..."` headers.
- **Rule**: Never pass tokens as URL query parameters or process command line options (`-u user:token`) that expose credentials in process lists.

## Related References & Gates

- **Check 64 (curl/wget retries)**: `automation/38-drift-checks.sh`
- **Check 65 (nested-podman capabilities)**: [nested-podman-caps.md](file:///C:/MiOS/usr/share/doc/mios/reference/nested-podman-caps.md)
- **Check 66 (bake-budget gate)**: `mios.toml [build.bake].runner_disk_budget_gb`
- **Pre-flight URL probe**: [tools/check-build-urls.sh](file:///C:/MiOS/tools/check-build-urls.sh) (`just check-build-urls`)
