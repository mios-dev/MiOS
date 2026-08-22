<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Powershell script that manually generates Windows Start Menu .lnk shortcuts for Flatpak applications in the MiOS-DEV distro to bypass WSLg's failure to automatically import icons for Flatpak .desktop files.
AI-related: mios-flatpak-install
tools/refresh-flatpak-shortcuts.ps1

Windows-side helper that creates Start Menu .lnk entries for every
installed flatpak in the MiOS-DEV distro that WSLg's auto-discovery
silently dropped. Run after `mios-flatpak-install` (or any time the
flatpak set changes) and the new apps appear under Start ->
"MiOS Apps" within seconds.

Background: WSLg's wslservice scans /usr/share/applications/ inside
the distro and writes .lnk files into
%APPDATA%\Microsoft\Windows\Start Menu\Programs\<distro>\ -- but
its icon-conversion step silently fails for many flatpak .desktop
files (operator-confirmed ChromeDev, Codium, gedit,
ExtensionManager, Flatseal all skipped despite valid Categories,
Type=Application, present .svg icons under
/var/lib/flatpak/exports/share/icons). When the icon-conversion
step fails, WSLg drops the entire entry instead of using a
fallback icon. Net: missing apps in the Start Menu.

Fix: this script bypasses WSLg's batch by:
  1. enumerating flatpak .desktop files inside the distro
  2. parsing Name + Exec from each
  3. writing one .lnk per flatpak to a SEPARATE folder (
     "MiOS Apps") so WSLg's next scan won't clobber what we wrote
  4. using generic imageres.dll icons -- the operator can right-
     click + "Change Icon" if they want a custom one

Idempotent: skips .lnk files that already exist + are current.
Removes stale .lnk files whose flatpak was uninstalled.

Usage:
  pwsh -File tools/refresh-flatpak-shortcuts.ps1            # default distro
  pwsh -File tools/refresh-flatpak-shortcuts.ps1 -Distro X  # other distro

Operators can wire it into mios-flatpak-install via a Scheduled
Task or just re-run when needed.

<!-- mios-src:57d2e7ed37ee from tools/refresh-flatpak-shortcuts.ps1:1-38 -->

