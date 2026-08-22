<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Manages libvirt hook scripts to pin VM...

!/bin/bash
AI-hint: Manages libvirt hook scripts to pin VM CPU threads to specific physical cores, optimizing performance for AMD Ryzen, Intel Hybrid, and NUMA architectures by isolating cores and preventing cross-CCD/CCD-hopping.
AI-functions: log_info, log_success, log_warning, log_error, log_header, check_root, detect_cpu_topology, detect_amd_ccds, list_vms, display_cpu_topology, display_ccd_layout, display_linear_layout

<!-- mios-src:857cc99eaa9a from tools/vm-cpu-pin-manager.sh:1-3 -->

