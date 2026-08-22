<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Windows-side execution bridge for MiOS-Agent to perform GUI interactions (click, type, move, resize) and window management via Win32 API calls triggered by the Linux-side mios-pc-control helper.
AI-related: /usr/share/mios/windows/mios-pc-control.ps1, /usr/libexec/mios/mios-pc-control, mios-pc-control, mios-windows
/usr/share/mios/windows/mios-pc-control.ps1

Windows-side computer-use surface for MiOS-Agent. Called from the
Linux helper /usr/libexec/mios/mios-pc-control via mios-windows ps.

Subcommands (passed via -Action):
  screenshot <out-path>
  click <x> <y> [button]
  double-click <x> <y>
  mouse-move <x> <y>
  type "<text>"
  key <name>
  key-combo "Ctrl+C"
  window-list
  window-focus <hwnd-or-pid>
  window-move <hwnd> <x> <y>
  window-resize <hwnd> <w> <h>

<!-- mios-src:e8c7d7b9c257 from usr/share/mios/windows/mios-pc-control.ps1:1-19 -->

