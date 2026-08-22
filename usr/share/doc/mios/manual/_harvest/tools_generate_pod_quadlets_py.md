<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Generate .pod Quadlets from...

!/usr/bin/env python3
AI-hint: Generate .pod Quadlets from the mios.toml [pods.*] co-resident groups (WS-7 pods-as-SSOT). Renders usr/share/containers/systemd/<name>.pod deterministically from each [pods.<name>] (description/network/after/wants/wanted_by/members/doc) so a co-resident container group is declared ONCE in SSOT and the Quadlet can't drift; tools/generate-k3s-manifests.sh then projects the live pods to k3s. --check (drift gate) compares without writing; --selftest asserts the pure renderer offline.
AI-related: usr/share/mios/mios.toml, usr/share/containers/systemd, tools/generate-k3s-manifests.sh, automation/98-drift-checks.sh, automation/34-render-quadlets.sh
AI-functions: render_pod_quadlet, _wrap_doc, load_pods, main, _selftest

<!-- mios-src:a407b0f34609 from tools/generate-pod-quadlets.py:1-4 -->

