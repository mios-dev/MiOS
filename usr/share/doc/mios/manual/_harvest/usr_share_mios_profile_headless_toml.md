<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: A server-specific configuration profile for headless/inference nodes that disables GNOME, Guacamole, and remote-desktop services while enabling local AI inference and Cockpit management.
AI-related: /usr/share/mios/profile-headless.toml, /etc/mios/profile.toml, /usr/share/mios/ai/mcp.json, mios-node, mios-dev, mios-bootstrap, mios-ai, mios-ceph, mios-k3s, localhost:8080
/usr/share/mios/profile-headless.toml -- MiOS HEADLESS / SERVER profile (R14)

A server-posture variant of the default profile (etc/mios/profile.toml) for an
orchestration / inference node that should NOT run the GNOME desktop, Guacamole
remote-desktop, or Looking-Glass layer. Closes the "no headless/server profile
variant -- you take the whole kitchen sink" gap from the 2026-06 maturity review.

USE: copy this over the host profile BEFORE installing, then bootstrap normally:
    sudo cp /usr/share/mios/profile-headless.toml /etc/mios/profile.toml
  (the 3-layer overlay makes /etc/mios/profile.toml win over the vendor default.)

WHAT IS / ISN'T GUARANTEED:
  * [quadlets.enable] flags set to `false` ARE honored -- the bootstrap
    force-disables those services, so the desktop/remote-desktop sidecars never
    start on this node. (The default profile documents this contract.)
  * [desktop] keys here express intent (no auto-started GNOME session, no
    desktop flatpaks). GNOME 50 is still PRESENT in the image (it ships in
    mios.git, not the installer) -- this profile just avoids starting/seeding
    the desktop layer. For a truly minimal headless IMAGE (no GNOME at all),
    build with a headless MIOS_BASE_IMAGE; that is a separate image build, not
    a profile choice. Verify session handling on first boot.

Format: TOML 1.0. Mirrors etc/mios/profile.toml field-for-field; only the
desktop/quadlet/flatpak posture differs.

<!-- mios-src:737e0e72ae91 from usr/share/mios/profile-headless.toml:1-26 -->

