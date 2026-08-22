<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios-wallpaperd -- MiOS living-wallpaper + desktop-services...

mios-wallpaperd -- MiOS living-wallpaper + desktop-services daemon (Law 14 / ADR-0011 native tier).

FIRST DRAFT. There is no Rust toolchain on the authoring box, so this is compiled + iterated in
staging by the provisioned Rust (Install-MiosRust). API calls follow the `windows` 0.58 and
`wry`/`tao` conventions but must be verified at first `cargo build`; treat compile errors as the
expected next step, not a surprise.

ONE binary, three roles (dispatched by argv[1]) -- so it can be a single auto-start service with
NO console and NO surfacing window, replacing MiOS-Wallpaper.exe + MiOS-Wallpaper-Service.exe +
mios-gui-watch.ps1 + the MiOSWallpaper/MiOS-GuiWatch Run keys:
  (default | "service")  -> service controller in session 0; launches "host" in the user session.
  "host"                 -> the wallpaper: WebView attached to WorkerW, behind the desktop icons.
  "gui-watch"            -> standalone WSLg window-centering loop (also run as a thread inside host).

<!-- mios-src:0d6d907a715f from tools/native/mios-wallpaperd/src/main.rs:1-13 -->
