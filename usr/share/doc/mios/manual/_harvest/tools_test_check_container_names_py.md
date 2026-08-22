<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Sibling unit test for...

!/usr/bin/env python3
AI-hint: Sibling unit test for tools/check-container-names.py. Builds throwaway trees and asserts every direction the real audit produced: a matching pair passes, a MISSING ContainerName fails (Quadlet would name it systemd-<unit>, which no systemctl name matches), a mismatched one fails on either surface independently so SSOT and rendered file cannot drift apart alone, a TEMPLATE unit must name the instantiated `<base>-%i` form rather than its own key, a container gated off in [quadlets.enable] may render nothing but must still name itself correctly for the day it is switched on, an ENABLED container with no rendered file fails, and an empty tree fails rather than passing vacuously over nothing.
AI-related: ./check-container-names.py, usr/share/mios/mios.toml, usr/share/containers/systemd/
AI-functions: check, mkrepo, run, main

<!-- mios-src:18f2dbfafe9d from tools/test_check-container-names.py:1-4 -->

