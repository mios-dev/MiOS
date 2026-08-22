<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-credential-literals.py: builds throwaway unit trees and asserts the gate passes a grandfathered literal, fails a new one, fails a stale grandfathered entry, and does NOT mistake token-count settings, boolean feature flags or ${VAR}-indirected values for credentials.
AI-related: tools/check-credential-literals.py, usr/share/mios/mios.toml, usr/share/containers/systemd

<!-- mios-src:b558211dc882 from tools/test_check-credential-literals.py:1-3 -->

