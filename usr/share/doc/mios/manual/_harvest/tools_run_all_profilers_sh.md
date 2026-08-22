<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/bin/bash AI-hint: Executes a sequential chain of...

!/bin/bash
AI-hint: Executes a sequential chain of diagnostic scripts (quick-summary, iommu-visualizer, system-profiler) to generate a comprehensive system performance and hardware configuration report in a timestamped directory.
AI-functions: print_banner, print_step, print_info, print_success, print_error, wait_for_user, check_sudo, create_output_dir, run_quick_summary, run_iommu_visualizer, run_system_profiler, generate_summary

<!-- mios-src:3c3d12d06288 from tools/run-all-profilers.sh:1-3 -->

