<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Defines the Anaconda kickstart configuration and kernel parameters for generating a bare-metal installation ISO, including filesystem sizing, user accounts, and boot-time driver blacklisting.
bib-configs/iso.toml - 'MiOS' v0.3.0
Target: Anaconda unattended installer ISO for bare-metal install.

NOTE: BIB #528 - [customizations.user] is ignored when kickstart is present.
      User is defined IN the kickstart below.
NOTE: Source container image MUST include dracut-live + squashfs-tools, or
      this build leg will fail. Containerfile installs these in v0.2.0.

<!-- mios-src:3f07beb78726 from config/artifacts/iso.toml:1-8 -->

