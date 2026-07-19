// mios-wallpaperd -- MiOS living-wallpaper + desktop-services daemon (Law 14 / ADR-0011 native tier).
//
// FIRST DRAFT. There is no Rust toolchain on the authoring box, so this is compiled + iterated in
// staging by the provisioned Rust (Install-MiosRust). API calls follow the `windows` 0.58 and
// `wry`/`tao` conventions but must be verified at first `cargo build`; treat compile errors as the
// expected next step, not a surprise.
//
// ONE binary, three roles (dispatched by argv[1]) -- so it can be a single auto-start service with
// NO console and NO surfacing window, replacing MiOS-Wallpaper.exe + MiOS-Wallpaper-Service.exe +
// mios-gui-watch.ps1 + the MiOSWallpaper/MiOS-GuiWatch Run keys:
//   (default | "service")  -> service controller in session 0; launches "host" in the user session.
//   "host"                 -> the wallpaper: WebView attached to WorkerW, behind the desktop icons.
//   "gui-watch"            -> standalone WSLg window-centering loop (also run as a thread inside host).
#![windows_subsystem = "windows"] // no console window, ever.

mod guiwatch;
mod host;
mod workerw;

use std::ffi::OsString;
use std::time::Duration;

pub const SERVICE_NAME: &str = "MiOS-Wallpaper-Service";
pub const HOST_ARG: &str = "host";
pub const GUIWATCH_ARG: &str = "gui-watch";
/// SSOT-derived wallpaper URL, written by Set-MiOSWallpaper.ps1 (a0..a15 palette, mode-less for live
/// theme sync). Read at host start; the host also watches it for change and reloads.
pub const WALLPAPER_URL_KEY: &str = r"SOFTWARE\MiOS";
pub const WALLPAPER_URL_VALUE: &str = "WallpaperUrl";
pub const WALLPAPER_URL_FALLBACK: &str = "file:///C:/Windows/Web/MiOS/living-wallpaper.html";

fn main() {
    let arg = std::env::args().nth(1).unwrap_or_default();
    match arg.as_str() {
        HOST_ARG => host::run_host(),
        GUIWATCH_ARG => guiwatch::run_forever(),
        // No arg (SCM launch) or explicit "service": become the Windows service.
        _ => {
            if let Err(_e) = service::run() {
                // If the SCM isn't driving us (e.g. run interactively for a smoke test), fall back to
                // hosting directly so a developer still sees the wallpaper.
                host::run_host();
            }
        }
    }
}

/// Windows-service controller (session 0). It cannot draw on the user's desktop itself, so it keeps a
/// "host" child alive in the active interactive session and relaunches it on exit or session change.
mod service {
    use super::*;
    use windows_service::service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    };
    use windows_service::service_control_handler::{self, ServiceControlHandlerResult};
    use windows_service::service_dispatcher;

    pub fn run() -> windows_service::Result<()> {
        service_dispatcher::start(SERVICE_NAME, ffi_service_main)
    }

    windows_service::define_windows_service!(ffi_service_main, service_main);

    fn service_main(_args: Vec<OsString>) {
        let (shutdown_tx, shutdown_rx) = std::sync::mpsc::channel();
        let handler = move |control| -> ServiceControlHandlerResult {
            match control {
                ServiceControl::Stop | ServiceControl::Shutdown => {
                    let _ = shutdown_tx.send(());
                    ServiceControlHandlerResult::NoError
                }
                ServiceControl::SessionChange(_) => ServiceControlHandlerResult::NoError,
                ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
                _ => ServiceControlHandlerResult::NotImplemented,
            }
        };
        let status_handle = match service_control_handler::register(SERVICE_NAME, handler) {
            Ok(h) => h,
            Err(_) => return,
        };
        let running = ServiceStatus {
            service_type: ServiceType::OWN_PROCESS,
            current_state: ServiceState::Running,
            controls_accepted: ServiceControlAccept::STOP | ServiceControlAccept::SHUTDOWN,
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        };
        let _ = status_handle.set_service_status(running.clone());

        // Supervise a host child in the active user session until asked to stop.
        loop {
            if shutdown_rx.recv_timeout(Duration::from_secs(3)).is_ok() {
                break;
            }
            super::session::ensure_host_running();
        }

        super::session::kill_host();
        let _ = status_handle.set_service_status(ServiceStatus {
            current_state: ServiceState::Stopped,
            ..running
        });
    }
}

/// Launch/track the "host" child inside the active interactive session (CreateProcessAsUser with the
/// console-session token) so the wallpaper renders on the real desktop, not session 0.
mod session {
    use std::sync::atomic::{AtomicU32, Ordering};
    use windows::Win32::Foundation::{CloseHandle, HANDLE};
    use windows::Win32::System::RemoteDesktop::{WTSGetActiveConsoleSessionId, WTSQueryUserToken};
    use windows::Win32::System::Threading::{
        CreateProcessAsUserW, OpenProcess, TerminateProcess, PROCESS_INFORMATION,
        PROCESS_TERMINATE, STARTUPINFOW,
    };

    static HOST_PID: AtomicU32 = AtomicU32::new(0);

    pub fn ensure_host_running() {
        let pid = HOST_PID.load(Ordering::SeqCst);
        if pid != 0 && super::util::process_alive(pid) {
            return;
        }
        if let Some(new_pid) = spawn_host_in_session() {
            HOST_PID.store(new_pid, Ordering::SeqCst);
        }
    }

    pub fn kill_host() {
        let pid = HOST_PID.swap(0, Ordering::SeqCst);
        if pid == 0 {
            return;
        }
        unsafe {
            if let Ok(h) = OpenProcess(PROCESS_TERMINATE, false, pid) {
                let _ = TerminateProcess(h, 0);
                let _ = CloseHandle(h);
            }
        }
    }

    fn spawn_host_in_session() -> Option<u32> {
        unsafe {
            let session = WTSGetActiveConsoleSessionId();
            if session == 0xFFFF_FFFF {
                return None; // no interactive session yet (login screen)
            }
            let mut token = HANDLE::default();
            if WTSQueryUserToken(session, &mut token).is_err() {
                return None;
            }
            let exe = super::util::current_exe_wide();
            let mut cmd = super::util::wide(&format!("\"{}\" {}", super::util::current_exe_string(), super::HOST_ARG));
            let si = STARTUPINFOW { cb: std::mem::size_of::<STARTUPINFOW>() as u32, ..Default::default() };
            let mut pi = PROCESS_INFORMATION::default();
            let ok = CreateProcessAsUserW(
                Some(token),
                windows::core::PCWSTR(exe.as_ptr()),
                Some(windows::core::PWSTR(cmd.as_mut_ptr())),
                None, None, false,
                Default::default(),
                None, None,
                &si, &mut pi,
            );
            let _ = CloseHandle(token);
            if ok.is_err() { return None; }
            let _ = CloseHandle(pi.hThread);
            let _ = CloseHandle(pi.hProcess);
            Some(pi.dwProcessId)
        }
    }
}

/// Small shared helpers (UTF-16 conversion, process liveness, current exe path).
pub mod util {
    use windows::Win32::Foundation::CloseHandle;
    use windows::Win32::System::Threading::{
        GetExitCodeProcess, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
    };

    pub fn wide(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }
    pub fn current_exe_string() -> String {
        std::env::current_exe().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default()
    }
    pub fn current_exe_wide() -> Vec<u16> {
        wide(&current_exe_string())
    }
    pub fn process_alive(pid: u32) -> bool {
        const STILL_ACTIVE: u32 = 259;
        unsafe {
            match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
                Ok(h) => {
                    let mut code = 0u32;
                    let alive = GetExitCodeProcess(h, &mut code).is_ok() && code == STILL_ACTIVE;
                    let _ = CloseHandle(h);
                    alive
                }
                Err(_) => false,
            }
        }
    }

    /// Read a REG_SZ under HKLM (used to fetch the SSOT WallpaperUrl written by Set-MiOSWallpaper).
    pub fn reg_read_sz(subkey: &str, value: &str) -> Option<String> {
        use windows::Win32::System::Registry::{RegGetValueW, HKEY_LOCAL_MACHINE, RRF_RT_REG_SZ};
        unsafe {
            let sub = wide(subkey);
            let val = wide(value);
            let mut buf = vec![0u16; 2048];
            let mut size = (buf.len() * 2) as u32;
            let rc = RegGetValueW(
                HKEY_LOCAL_MACHINE,
                windows::core::PCWSTR(sub.as_ptr()),
                windows::core::PCWSTR(val.as_ptr()),
                RRF_RT_REG_SZ,
                None,
                Some(buf.as_mut_ptr() as *mut core::ffi::c_void),
                Some(&mut size),
            );
            if rc.0 == 0 {
                let chars = (size as usize / 2).saturating_sub(1);
                Some(String::from_utf16_lossy(&buf[..chars]))
            } else {
                None
            }
        }
    }
}
