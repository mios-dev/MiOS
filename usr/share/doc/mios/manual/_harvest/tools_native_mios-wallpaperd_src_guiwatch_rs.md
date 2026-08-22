<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### WSLg window-centering (folded from mios-gui-watch.ps1) --...

WSLg window-centering (folded from mios-gui-watch.ps1) -- runs as a thread inside the host, so
there is NO separate pwsh process and no login terminal flash. WSLg hosts each Linux GUI app as
an msrdc.exe-owned window; many spawn tiny (e.g. 129x113) at random coords and look "not
rendered" on a 4K display. Poll top-level windows; the first time an msrdc window is seen smaller
than the minimum, resize + center it once, then leave it alone (tracked in `adopted`) so the
operator can move/resize freely afterwards.

<!-- mios-src:739e6f2c63a7 from tools/native/mios-wallpaperd/src/guiwatch.rs:1-6 -->
