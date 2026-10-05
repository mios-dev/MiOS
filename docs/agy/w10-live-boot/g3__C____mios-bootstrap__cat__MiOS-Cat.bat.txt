=====================================================================
HUNK 1 -- add live-chat defaults (anchor: end of the default-vars block, ~line 118-121)
=====================================================================
--- OLD ---
set "partition_label=MiOS-Cat"
set "force_format=Enabled"

:: ------------------------------------------------------------------
--- NEW ---
set "partition_label=MiOS-Cat"
set "force_format=Enabled"

:: W10 -- live-boot AI-chat ISO staging defaults (bootc-live-squashfs).
:: SSOT-overridable via [cat.live_chat] in mios.toml (loaded into the $map
:: below); these are the degrade-open fallbacks if that block is absent.
set "live_chat_enabled=Enabled"
set "live_chat_model=lfm2-700m"
set "live_chat_fallback=granite-4.1-8b"
set "live_chat_port=8642"
set "live_chat_iso_name=MiOS-Live-Chat.iso"

:: ------------------------------------------------------------------

=====================================================================
HUNK 2 -- extend the PowerShell SSOT $map (anchor: inside the single-line
loader command, ~line 51). Only the $map={...} literal changes; everything
else on that (very long) line is untouched.
=====================================================================
--- OLD (substring) ---
$map=[ordered]@{ drivepath='drivepath'; medicatver='medicatver'; file='cache_path'; bg_color='bg'; fg_color='fg'; accent_color='accent'; cursor_color='cursor'; success_color='success'; muted_color='muted'; subtle_color='subtle' };
--- NEW (substring) ---
$map=[ordered]@{ drivepath='drivepath'; medicatver='medicatver'; file='cache_path'; bg_color='bg'; fg_color='fg'; accent_color='accent'; cursor_color='cursor'; success_color='success'; muted_color='muted'; subtle_color='subtle'; live_chat_model='live_chat_model'; live_chat_fallback='live_chat_fallback'; live_chat_port='live_chat_port'; live_chat_iso_name='live_chat_iso_name' };

=====================================================================
HUNK 3 -- :menu Build line (anchor: ~line 151)
=====================================================================
--- OLD ---
echo     2. Build MiOS Images            (OCI . Xbox ISO . all)
--- NEW ---
echo     2. Build MiOS Images            (OCI . Xbox ISO . Live-Chat . all)

=====================================================================
HUNK 4 -- :sub_build menu + routing (anchor: ~line 340-351), renumbers
"Back to Main Menu" from 4 to 5
=====================================================================
--- OLD ---
echo   1. Build MiOS OCI image     : localhost/mios:latest
echo   2. Build MiOS-Xbox ISO      : Windows 11 gaming edition
echo   3. Build ALL artifacts      : OCI + raw/iso/qcow2/vhd/wsl2
echo   4. Back to Main Menu
echo ==========================================================
set "sub_choice="
set /p "sub_choice=Select an option (1-4): "
if "%sub_choice%"=="1" goto build_oci
if "%sub_choice%"=="2" goto build_xbox_iso
if "%sub_choice%"=="3" goto build_all
if "%sub_choice%"=="4" goto menu
goto sub_build
--- NEW ---
echo   1. Build MiOS OCI image     : localhost/mios:latest
echo   2. Build MiOS-Xbox ISO      : Windows 11 gaming edition
echo   3. Build MiOS Live-Chat ISO : bootc-live-squashfs, no-install AI chat
echo   4. Build ALL artifacts      : OCI + raw/iso/qcow2/vhd/wsl2/live-chat
echo   5. Back to Main Menu
echo ==========================================================
set "sub_choice="
set /p "sub_choice=Select an option (1-5): "
if "%sub_choice%"=="1" goto build_oci
if "%sub_choice%"=="2" goto build_xbox_iso
if "%sub_choice%"=="3" goto build_live_chat_iso
if "%sub_choice%"=="4" goto build_all
if "%sub_choice%"=="5" goto menu
goto sub_build

=====================================================================
HUNK 5 -- new :build_live_chat_iso target (anchor: insert between the end
of :build_xbox_iso and the :build_all label, ~line 417-419). Mirrors
:build_oci's env-var-gated call to build-mios.ps1 (MIOS_BUILD_LIVE_CHAT is a
new hook the live-iso.sh/build-driver leg -- design Phase 1 Sec.1/6 item 1,
not yet landed -- must recognize; same forward-declared pattern as the
existing MIOS_SKIP_BIB).
=====================================================================
--- OLD ---
if "%build_rc%"=="0" echo [OK] MiOS-Xbox ISO build finished.
if not "%build_rc%"=="0" echo [WARN] Xbox builder exit code %build_rc% - review the log above; you can re-run this item.
echo.
pause
goto sub_build

:build_all
--- NEW ---
if "%build_rc%"=="0" echo [OK] MiOS-Xbox ISO build finished.
if not "%build_rc%"=="0" echo [WARN] Xbox builder exit code %build_rc% - review the log above; you can re-run this item.
echo.
pause
goto sub_build

:build_live_chat_iso
cls
echo ==========================================================
echo               Build MiOS Live-Chat ISO
echo ==========================================================
echo   Produces : %live_chat_iso_name%  ^(bootc-live-squashfs^)
echo   Source   : localhost/mios:latest  ^(same image bootc install uses -- no drift^)
echo   Model    : %live_chat_model%  ^(operator step-up: %live_chat_fallback%^)
echo   Serves   : 127.0.0.1:%live_chat_port%  ^(bare llama-server, no Quadlet/pod^)
echo   Toolchain: WSL2 + podman + MiOS-DEV builder auto-provisioned
echo              if missing (offline-first from MiOS-Repo, else online)
echo   Time     : 10-25 min once the OCI image is already built
echo ==========================================================
set "confirm="
set /p "confirm=Start the Live-Chat ISO build now? (Y/N): "
if /i not "%confirm%"=="Y" goto sub_build
call :resolve_bootstrap_root
if "%bootstrap_root%"=="" goto build_need_online
if not exist "%bootstrap_root%\build-mios.ps1" goto build_need_online
echo.
echo [BUILD] Driver : %bootstrap_root%\build-mios.ps1
echo [BUILD] Mode   : Live-Chat ISO only (MIOS_BUILD_LIVE_CHAT=1)
echo [BUILD] Progress streams below and/or in the MiOS-DEV window.
echo.
set "MIOS_BUILD_LIVE_CHAT=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%bootstrap_root%\build-mios.ps1" -Unattended
set "build_rc=%errorlevel%"
set "MIOS_BUILD_LIVE_CHAT="
echo.
if "%build_rc%"=="0" echo [OK] Live-Chat ISO build finished. Output: /var/lib/mios/build/output/%live_chat_iso_name% in MiOS-DEV.
if not "%build_rc%"=="0" echo [WARN] Build driver exit code %build_rc% - review the log above; you can re-run this item.
echo.
pause
goto sub_build

:build_all

=====================================================================
HUNK 6 -- :build_all: mention live-chat in the artifact list + gate
MIOS_BUILD_LIVE_CHAT on live_chat_enabled (anchor: ~line 424-446)
=====================================================================
--- OLD ---
echo   Produces : localhost/mios:latest PLUS deployment artifacts
echo              raw - iso - qcow2 - vhd - wsl2 tarball
echo   Where    : /var/lib/mios/build/output inside MiOS-DEV
echo   Requires : a Linux/podman build host - auto-provisioned
echo              (WSL2 + podman + MiOS-DEV) if missing, offline-first
echo   Size/Time: ~30-40 GB, 45-90 min for the full matrix
echo ==========================================================
set "confirm="
set /p "confirm=Build the FULL artifact matrix now? (Y/N): "
if /i not "%confirm%"=="Y" goto sub_build
call :resolve_bootstrap_root
if "%bootstrap_root%"=="" goto build_need_online
if not exist "%bootstrap_root%\build-mios.ps1" goto build_need_online
echo.
echo [BUILD] Driver : %bootstrap_root%\build-mios.ps1
echo [BUILD] Mode   : full matrix (OCI + all [deployment] targets)
echo [BUILD] Progress streams below and/or in the MiOS-DEV window.
echo.
set "MIOS_SKIP_BIB="
powershell -NoProfile -ExecutionPolicy Bypass -File "%bootstrap_root%\build-mios.ps1" -Unattended
set "build_rc=%errorlevel%"
echo.
--- NEW ---
echo   Produces : localhost/mios:latest PLUS deployment artifacts
echo              raw - iso - qcow2 - vhd - wsl2 tarball - live-chat iso
echo   Where    : /var/lib/mios/build/output inside MiOS-DEV
echo   Requires : a Linux/podman build host - auto-provisioned
echo              (WSL2 + podman + MiOS-DEV) if missing, offline-first
echo   Size/Time: ~30-40 GB, 45-90 min for the full matrix
echo ==========================================================
set "confirm="
set /p "confirm=Build the FULL artifact matrix now? (Y/N): "
if /i not "%confirm%"=="Y" goto sub_build
call :resolve_bootstrap_root
if "%bootstrap_root%"=="" goto build_need_online
if not exist "%bootstrap_root%\build-mios.ps1" goto build_need_online
echo.
echo [BUILD] Driver : %bootstrap_root%\build-mios.ps1
echo [BUILD] Mode   : full matrix (OCI + all [deployment] targets)
echo [BUILD] Progress streams below and/or in the MiOS-DEV window.
echo.
set "MIOS_SKIP_BIB="
set "MIOS_BUILD_LIVE_CHAT="
if "%live_chat_enabled%"=="Enabled" set "MIOS_BUILD_LIVE_CHAT=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%bootstrap_root%\build-mios.ps1" -Unattended
set "build_rc=%errorlevel%"
set "MIOS_BUILD_LIVE_CHAT="
echo.

=====================================================================
HUNK 7 -- :manual_about mention (anchor: ~line 634-637)
=====================================================================
--- OLD ---
echo   Build       : builds MiOS images from this machine -
echo                 OCI (localhost/mios:latest), MiOS-Xbox ISO,
echo                 or the full artifact matrix. The toolchain is
echo                 self-provisioned (WSL2 + podman) if missing.
--- NEW ---
echo   Build       : builds MiOS images from this machine -
echo                 OCI (localhost/mios:latest), MiOS-Xbox ISO,
echo                 MiOS-Live-Chat ISO (zero-install AI-chat live boot),
echo                 or the full artifact matrix. The toolchain is
echo                 self-provisioned (WSL2 + podman) if missing.

=====================================================================
HUNK 8 -- :start_install summary block (anchor: ~line 826-827)
=====================================================================
--- OLD ---
echo Build MiOS-Xbox   : %build_xbox%
echo Partition Label   : %partition_label%
--- NEW ---
echo Build MiOS-Xbox   : %build_xbox%
echo Live-Chat ISO     : %live_chat_enabled% (%live_chat_model%, :%live_chat_port%)
echo Partition Label   : %partition_label%

=====================================================================
HUNK 9 -- stage the ISO (anchor: right after the Fedora ISO + kickstart
copy, before the PortableApps theming section, ~line 1067-1073). New
labels (live_chat_disabled/have_src/missing/done) are goto-driven, NOT
nested inside a shared parenthesized block that also sets the var being
tested -- avoids the parse-time-stale-%var% class of bug already present
elsewhere in this file (see disk_check at :run_preflight_checks and the
unmount retry counter).
=====================================================================
--- OLD ---
:: Copy Fedora ISO and Kickstart to Ventoy paths
echo Copying Fedora Server ISO and Kickstart template to USB...
copy "%fedora_file%" "%drivepath%:\Live_Operating_Systems\Fedora-Server.iso" /Y >nul
copy "%maindir%\resources\ventoy\mios-kickstart.cfg" "%drivepath%:\ventoy\mios-kickstart.cfg" /Y >nul


:: Brand the PortableApps Menu to match MiOS
--- NEW ---
:: Copy Fedora ISO and Kickstart to Ventoy paths
echo Copying Fedora Server ISO and Kickstart template to USB...
copy "%fedora_file%" "%drivepath%:\Live_Operating_Systems\Fedora-Server.iso" /Y >nul
copy "%maindir%\resources\ventoy\mios-kickstart.cfg" "%drivepath%:\ventoy\mios-kickstart.cfg" /Y >nul

:: 6c. Stage the W10 live-boot AI-chat ISO (bootc-live-squashfs; the model +
:: the mios-live-chat client are baked into the ISO at build time by
:: automation\build\live-iso.sh -- this step only finds/builds/copies the
:: single artifact). Copy-if-present / build-if-missing, same idiom as the
:: Fedora DVD above. Never blocks the rest of staging if it's unavailable --
:: worst case the "Chat with MiOS AI" menu entry just doesn't appear (its
:: grub entry is `search --file`-guarded, see ventoy_grub.cfg).
set "live_chat_iso_src="
if not "%live_chat_enabled%"=="Enabled" goto live_chat_disabled
echo.
echo Checking for MiOS Live-Chat ISO (%live_chat_iso_name%)...
if exist "%drivepath%:\Live_Operating_Systems\%live_chat_iso_name%" (
    echo [OK] %live_chat_iso_name% already staged on %drivepath%:.
    goto live_chat_done
)
call :resolve_live_chat_iso
if not "%live_chat_iso_src%"=="" goto live_chat_have_src
echo [INFO] %live_chat_iso_name% not found in cache or MiOS-DEV build output.
call :resolve_bootstrap_root
if "%bootstrap_root%"=="" goto live_chat_missing
if not exist "%bootstrap_root%\build-mios.ps1" goto live_chat_missing
echo Building it now via %bootstrap_root%\build-mios.ps1 (MIOS_BUILD_LIVE_CHAT=1)...
echo Model: %live_chat_model%  Port: %live_chat_port%  (operator step-up: %live_chat_fallback%)
set "MIOS_BUILD_LIVE_CHAT=1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%bootstrap_root%\build-mios.ps1" -Unattended
set "MIOS_BUILD_LIVE_CHAT="
call :resolve_live_chat_iso
if "%live_chat_iso_src%"=="" goto live_chat_missing

:live_chat_have_src
echo Copying %live_chat_iso_name% to %drivepath%:\Live_Operating_Systems\...
copy "%live_chat_iso_src%" "%drivepath%:\Live_Operating_Systems\%live_chat_iso_name%" /Y >nul
if errorlevel 1 (
    echo [WARN] Copy of %live_chat_iso_name% failed -- the "Chat with MiOS AI" menu entry will not appear. >^&2
    goto live_chat_done
)
echo [OK] %live_chat_iso_name% staged.
echo Recording SBOM hash (sha256, per ADR-0003 -- never hand-pinned in mios.toml)...
powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -LiteralPath '%drivepath%:\Live_Operating_Systems\%live_chat_iso_name%').Hash.ToLower()" > "%drivepath%:\Live_Operating_Systems\%live_chat_iso_name%.sha256" 2>nul
goto live_chat_done

:live_chat_missing
echo [WARN] %live_chat_iso_name% could not be found or built -- the "Chat with MiOS AI" menu entry will not appear. >^&2
echo        Run "Build MiOS Live-Chat ISO" from the Build menu, or place a pre-built copy at %stage_dir%\%live_chat_iso_name%, and re-run Stage USB. >^&2
goto live_chat_done

:live_chat_disabled
echo [INFO] Live-Chat ISO staging disabled ([cat.live_chat] enabled=false / live_chat_enabled=Disabled).

:live_chat_done


:: Brand the PortableApps Menu to match MiOS

NOTE: the two ">^&2" above are the literal escaped form (caret before &) --
MiOS-Cat.bat already uses plain ">&2" unescaped elsewhere (e.g. the Fedora
DVD failure at ~line 961) because those lines sit outside any parenthesized
block; here the two >&2 lines that ARE inside `if errorlevel 1 ( ... )` /
plain sequential context should just use ">&2" too (cmd.exe only requires
the caret-escape for `&` inside a `(...)` block when it would otherwise be
misparsed as a command separator -- since each `echo ... >&2` here is a
whole line inside its own `if` body or a bare sequential line, plain "&"
works; use ">^&2" only if you keep it on a line that shares parens with
other `&`-sensitive syntax). Match whichever the surrounding hunk ends up
using after a quick manual smoke-run.

=====================================================================
HUNK 10 -- Live_Operating_Systems README (anchor: ~line 1135-1138)
=====================================================================
--- OLD ---
(
echo # MiOS-Cat Operating Systems
echo This folder contains the live WinPE recovery image ^(MiOS_PE.wim^) and SystemRescue ISO.
) > "%drivepath%:\Live_Operating_Systems\README.md"
--- NEW ---
(
echo # MiOS-Cat Operating Systems
echo This folder contains the live WinPE recovery image ^(MiOS_PE.wim^), the
echo SystemRescue ISO, and MiOS-Live-Chat.iso -- the W10 zero-install
echo live-USB-to-AI-chat ^(bootc-live-squashfs: boots the actual MiOS bootc
echo image RAM-resident with a bundled model, no changes to this machine^).
) > "%drivepath%:\Live_Operating_Systems\README.md"

=====================================================================
HUNK 11 -- new :resolve_live_chat_iso helper (anchor: insert between the
end of :resolve_xbox_builder and the :update_repo label, ~line 1419-1421)
=====================================================================
--- OLD ---
if exist "C:\mios-bootstrap\cat\autounattend\New-MiOSISO.ps1" (
    set "xbox_builder=C:\mios-bootstrap\cat\autounattend\New-MiOSISO.ps1"
    goto :eof
)
goto :eof

:update_repo
--- NEW ---
if exist "C:\mios-bootstrap\cat\autounattend\New-MiOSISO.ps1" (
    set "xbox_builder=C:\mios-bootstrap\cat\autounattend\New-MiOSISO.ps1"
    goto :eof
)
goto :eof

:resolve_live_chat_iso
:: Resolve a pre-built MiOS-Live-Chat.iso before staging falls back to
:: triggering a build. Preference order: build cache (fast re-run path,
:: mirrors the Fedora/MediCat M:\-style cache) -> MiOS-DEV build output
:: over the WSL2 UNC share -> not found (caller decides build-or-skip).
set "live_chat_iso_src="
if exist "%stage_dir%\%live_chat_iso_name%" (
    set "live_chat_iso_src=%stage_dir%\%live_chat_iso_name%"
    goto :eof
)
if exist "\\wsl.localhost\MiOS-DEV\var\lib\mios\build\output\%live_chat_iso_name%" (
    set "live_chat_iso_src=\\wsl.localhost\MiOS-DEV\var\lib\mios\build\output\%live_chat_iso_name%"
    goto :eof
)
if exist "\\wsl$\MiOS-DEV\var\lib\mios\build\output\%live_chat_iso_name%" (
    set "live_chat_iso_src=\\wsl$\MiOS-DEV\var\lib\mios\build\output\%live_chat_iso_name%"
    goto :eof
)
goto :eof

:update_repo
