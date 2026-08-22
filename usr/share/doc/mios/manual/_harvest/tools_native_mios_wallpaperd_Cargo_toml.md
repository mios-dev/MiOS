<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: MiOS wallpaper daemon manifest.
mios-wallpaperd -- MiOS living-wallpaper + desktop-services daemon.
Law 14 / ADR-0011 (WS-LANG): the Rust native tier. This ONE binary replaces the whole scattered
stack it consolidates:
  * MiOS-Wallpaper.exe            (C# WebView2 WorkerW host)
  * MiOS-Wallpaper-Service.exe    (C# service shell)
  * mios-gui-watch.ps1            (pwsh WSLg window-centering daemon -- the login terminal flash)
  * HKCU/HKLM Run keys MiOSWallpaper + MiOS-GuiWatch  (the visible-window launches)
-> one silent auto-start Windows service, no console, no surfacing window.

NOTE: versions below are indicative; pin/resolve at build time (cargo generates Cargo.lock). Built
by the provisioned Rust toolchain during staging (Install-MiosRust), never hand-compiled on a bare
box. GNU host triple works (no MSVC required) but MSVC is fine too.

<!-- mios-src:d44ae1201a08 from tools/native/mios-wallpaperd/Cargo.toml:1-13 -->

