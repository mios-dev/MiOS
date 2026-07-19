// WorkerW attach -- place a window BEHIND the desktop icons (the live-wallpaper layer). Standard
// Explorer technique: ask Progman (message 0x052C) to spawn the WorkerW sublayer, then find the
// WorkerW that hosts the wallpaper and SetParent our window onto it. Mirrors the proven C# host.
use windows::core::{w, PCWSTR};
use windows::Win32::Foundation::{BOOL, FALSE, HWND, LPARAM, TRUE, WPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, FindWindowExW, FindWindowW, SendMessageTimeoutW, SetParent, SMTO_NORMAL,
};

pub fn find_wallpaper_workerw() -> Option<HWND> {
    unsafe {
        let progman = FindWindowW(w!("Progman"), PCWSTR::null()).ok()?;
        // Tell Progman to create the WorkerW behind the icon layer.
        let mut _res: usize = 0;
        let _ = SendMessageTimeoutW(progman, 0x052C, WPARAM(0), LPARAM(0), SMTO_NORMAL, 1000, Some(&mut _res as *mut usize));

        // Newer / modified shells: a WorkerW directly under Progman.
        if let Ok(w) = FindWindowExW(progman, HWND::default(), w!("WorkerW"), PCWSTR::null()) {
            if !w.0.is_null() {
                return Some(w);
            }
        }

        // Else: enumerate top-level windows for the WorkerW that owns SHELLDLL_DefView (the icon
        // layer); the wallpaper WorkerW is the sibling WorkerW found after it.
        let mut found = Found { hwnd: None };
        let _ = EnumWindows(Some(enum_proc), LPARAM(&mut found as *mut _ as isize));
        found.hwnd
    }
}

struct Found {
    hwnd: Option<HWND>,
}

unsafe extern "system" fn enum_proc(top: HWND, lparam: LPARAM) -> BOOL {
    if let Ok(dv) = FindWindowExW(top, HWND::default(), w!("SHELLDLL_DefView"), PCWSTR::null()) {
        if !dv.0.is_null() {
            if let Ok(wp) = FindWindowExW(HWND::default(), top, w!("WorkerW"), PCWSTR::null()) {
                if !wp.0.is_null() {
                    (*(lparam.0 as *mut Found)).hwnd = Some(wp);
                    return FALSE; // stop enumeration
                }
            }
        }
    }
    TRUE
}

pub fn attach(child: HWND, parent: HWND) {
    unsafe {
        let _ = SetParent(child, parent);
    }
}
