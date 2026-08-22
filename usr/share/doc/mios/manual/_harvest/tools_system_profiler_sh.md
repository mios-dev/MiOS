<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: A diagnostic script that aggregates...

!/bin/bash
AI-hint: A diagnostic script that aggregates hardware, kernel, and peripheral data (PCI, USB, GPU, IOMMU) into text and JSON reports to provide a comprehensive hardware profile for MiOS-Build environment configuration.
AI-functions: print_header, print_section, print_info, print_warning, print_error, command_exists, safe_exec, append_to_output, check_tools, collect_basic_info, collect_cpu_info, collect_memory_info

<!-- mios-src:748f5d79729b from tools/system-profiler.sh:1-3 -->

