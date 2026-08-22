<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: One-shot first-boot Machine Owner Key (MOK) enrollment so the baked signed-UKI (rendered by automation/76-uki-render.sh + tools/generate-uki-cmdline.py) verifies under ENFORCING Secure Boot on the INSTALLED disk; mirrors automation/enroll-mok.sh (mokutil --import --root-pw, real /etc/pki/mios/mok.der key with the akmods-ublue fallback pick_key uses). Self-contained + idempotent: no-op when mokutil absent, Secure Boot off, key missing, or already enrolled/queued (/var/lib/mios/.mok-enrolled sentinel). Completes the shim -> GRUB -> UKI -> MOK-trusted chain that Ventoy's /S flag only covers for the USB's own shim.
AI-related: automation/enroll-mok.sh, automation/generate-mok-key.sh, automation/76-uki-render.sh, tools/generate-uki-cmdline.py, /etc/pki/mios/mok.der, /etc/pki/akmods/certs/akmods-ublue.der, usr/lib/bootc/kargs.d/32-mios-ws7-uki.toml, usr/share/doc/mios/reference/audit-deploy-plane.md

<!-- mios-src:47bed679c344 from usr/lib/systemd/system/mios-mok-enroll.service:1-2 -->

