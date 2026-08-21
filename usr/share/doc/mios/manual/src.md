<!-- AI-hint: Manual pages distilled from the source comments of src, sanitized, each passage anchored to the comment it came from. -->

# src

### Schema-generic configuration container. Owns stable fields...

Schema-generic configuration container. Owns stable fields directly
(`meta`, `identity`, `build`) while storing all dynamic/operator-defined
sections generically in `raw` to prevent recompilation on mios.toml schema changes.

<!-- mios-src:62e97279e9f1 from src/mios-rs/mios-config/src/lib.rs:102-104 -->

### Allocate every `[ports]` value from `[ports.categories]`...

Allocate every `[ports]` value from `[ports.categories]`, in place.

Must run AFTER all layers merge so a factory/OEM default in the vendor
mios.toml, an operator override in /etc/mios/mios.toml, and a user override
in ~/.config all feed the same derivation. `members` is ordered and the order
IS the numbering, so adding or removing a service reallocates the category
without a hand edit. `pinned` entries are protocol contracts (DNS/53) and are
written verbatim.

This OVERRIDES the flat `[ports]` table, which is only a rendered projection
kept for readability -- otherwise a stale vendor literal would silently beat
an operator who retargeted a category base.

<!-- mios-src:43bce08392de from tools/native/mios-resolver/src/ports.rs:5-16 -->

### WSLg window-centering (folded from mios-gui-watch.ps1) --...

WSLg window-centering (folded from mios-gui-watch.ps1) -- runs as a thread inside the host, so
there is NO separate pwsh process and no login terminal flash. WSLg hosts each Linux GUI app as
an msrdc.exe-owned window; many spawn tiny (e.g. 129x113) at random coords and look "not
rendered" on a 4K display. Poll top-level windows; the first time an msrdc window is seen smaller
than the minimum, resize + center it once, then leave it alone (tracked in `adopted`) so the
operator can move/resize freely afterwards.

<!-- mios-src:739e6f2c63a7 from tools/native/mios-wallpaperd/src/guiwatch.rs:1-6 -->

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
