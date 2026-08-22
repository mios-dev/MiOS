<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Powershell script that generates native Windows .lnk shortcuts for all .desktop files (including Flatpaks) in the MiOS-DEV WSL distro to ensure they appear in the Windows Start Menu with correct icons and no console window flash.
AI-related: /usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1, mios-wsl-flatpak-export-sync, mios-desktops, mios-icons, mios-icon-stage, mios-icon-batch, mios-full-desktop, mios-wsl-flatpak-export-sync.service
AI-functions: resolve_icon, Convert-PngToIco, Clear-WindowsIconCache
/usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1

Build Windows Start Menu .lnk shortcuts for every visible .desktop
entry inside the MiOS-DEV WSL distro (including flatpak apps), using
WSL2's NATIVE shortcut mechanism so apps launch without a pwsh /
conhost window flashing on-screen.

Native mechanism (reverse-engineered from a working WSL2-generated
shortcut on the operator's box):
  Target            : C:\Program Files\WSL\wslg.exe   (GUI app -- no console)
  Arguments         : -d <distro> --cd "~" -- <linux exec line>
  WindowStyle       : 7                                (minimized, GUI)
  IconLocation      : %LOCALAPPDATA%\Temp\WSLDVCPlugin\<distro>\<name>.ico,0

Operator-flagged twice:
  * "no icons match and all apps aren't populating in windows NATIVELY"
  * "opening WSL apps in windows is NOT native WSL behaviour (it
    launches a pwsh window for each app and the icons should be
    visible for each application NATIVELY!"

Why we have to do this ourselves instead of relying on WSL's built-
in sync: WSL2's sync (a) only fires on distro shutdown/boot and (b)
scans /usr/share/applications only -- flatpak's exports under
/var/lib/flatpak/exports/share are invisible. The companion
mios-wsl-flatpak-export-sync.service drops symlinks into
/usr/share/applications so flatpaks become visible too.

Idempotent. Re-run any time .desktop entries change.

<!-- mios-src:8dfca16e93b3 from usr/libexec/mios/Update-MiOSStartMenuShortcuts.ps1:1-31 -->

