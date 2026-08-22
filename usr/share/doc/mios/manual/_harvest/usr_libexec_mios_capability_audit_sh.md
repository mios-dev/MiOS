<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env bash AI-hint: A diagnostic script that audits...

!/usr/bin/env bash
AI-hint: A diagnostic script that audits hardware topology, IOMMU groups, VFIO bindings, and PCIe layout to determine device passthrough readiness for the MiOS virtualization layer.
AI-related: cockpit.socket, cockpit.service
AI-functions: print_section, print_subsection, cmd_exists, run_if_exists, read_file_if_exists, check_privileges, check_pass

<!-- mios-src:ffb86f5f59b0 from usr/libexec/mios/capability-audit.sh:1-4 -->

