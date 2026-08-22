<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines boot-time kernel arguments for security hardening, specifically enforcing slab_nomerge and lockdown=integrity to allow signed NVIDIA modules while maintaining system integrity on x86_64.
AI-related: mios-hardening
Boot-time hardening (NVIDIA-safe subset). Does NOT include page_alloc.shuffle
or init_on_alloc=1 globally (can interfere with large CUDA allocations).
lockdown=integrity: overrides 01-mios-hardening's confidentiality so that
ucore-hci signed NVIDIA modules (enrolled via Universal Blue MOK) can load.
module.sig_enforce is NOT disabled -- MOK-enrolled keys are sufficient.

<!-- mios-src:2fdd734073fd from usr/lib/bootc/kargs.d/30-security.toml:1-7 -->

