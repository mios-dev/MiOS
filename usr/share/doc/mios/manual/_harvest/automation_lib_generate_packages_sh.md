<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: WS-A17 build-time materializer...

!/usr/bin/env bash
AI-hint: WS-A17 build-time materializer for the local package registry. Thin, flag-gated wrapper around `mios-registry generate`: when [ai].package_registry (MIOS_PACKAGE_REGISTRY) is true it projects the live SSOT catalogs into ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml + registry.json; when false (the default) it is a no-op so the feature ships dormant. Sourced/called by the build (or run manually); never fails the build when the flag is off.
AI-related: /usr/libexec/mios/mios-registry, /usr/lib/mios/agent-pipe/mios_registry.py, /usr/share/mios/mios.toml, ./build.sh
AI-functions: (sourced helper -- no functions; guards on MIOS_PACKAGE_REGISTRY)

<!-- mios-src:ae74b5e69761 from automation/lib/generate-packages.sh:1-4 -->

