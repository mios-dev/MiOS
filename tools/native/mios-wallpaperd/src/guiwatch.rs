// WSLg window-centering (folded from mios-gui-watch.ps1) -- runs as a thread inside the host, so
// there is NO separate pwsh process and no login terminal flash. WSLg hosts each Linux GUI app as
// an msrdc.exe-owned window; many spawn tiny (e.g. 129x113) at random coords and look "not
// rendered" on a 4K display. Poll top-level windows; the first time an msrdc window is seen smaller
// than the minimum, resize + center it once, then leave it alone (tracked in `adopted`) so the
// operator can move/resize freely afterwards.
use std::collections::HashSet;
use std::time::Duration;
use windows::core::PWSTR;
use windows::Win32::Foundation::{CloseHandle, BOOL, HWND, LPARAM, RECT, TRUE};
use windows::Win32::System::Threading::{
    OpenProcess, QueryFullProcessImageNameW, PROCESS_NAME_FORMAT, PROCESS_QUERY_LIMITED_INFORMATION,
};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetSystemMetrics, GetWindowRect, GetWindowThreadProcessId, IsIconic,
    IsWindowVisible, SetWindowPos, SM_CXSCREEN, SM_CYSCREEN, SWP_NOACTIVATE, SWP_NOZORDER,
};

const MIN_W: i32 = 1600;
const MIN_H: i32 = 1000;

pub fn run_forever() {
    let mut adopted: HashSet<isize> = HashSet::new();
    loop {
        unsafe {
            let _ = EnumWindows(Some(enum_proc), LPARAM(&mut adopted as *mut _ as isize));
        }
        std::thread::sleep(Duration::from_millis(500));
    }
}

unsafe extern "system" fn enum_proc(hwnd: HWND, lparam: LPARAM) -> BOOL {
    let adopted = &mut *(lparam.0 as *mut HashSet<isize>);
    let key = hwnd.0 as isize;
    if key == 0 || adopted.contains(&key) {
        return TRUE;
    }
    if !IsWindowVisible(hwnd).as_bool() || IsIconic(hwnd).as_bool() {
        return TRUE;
    }
    if !is_msrdc(hwnd) {
        return TRUE;
    }
    let mut r = RECT::default();
    if GetWindowRect(hwnd, &mut r).is_err() {
        return TRUE;
    }
    let (w, h) = (r.right - r.left, r.bottom - r.top);
    if w >= MIN_W && h >= MIN_H {
        return TRUE; // already usable -- don't touch
    }
    let (nw, nh) = (w.max(MIN_W), h.max(MIN_H));
    let (sw, sh) = (GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN));
    let (x, y) = (((sw - nw) / 2).max(0), ((sh - nh) / 2).max(0));
    let _ = SetWindowPos(hwnd, HWND::default(), x, y, nw, nh, SWP_NOZORDER | SWP_NOACTIVATE);
    adopted.insert(key);
    TRUE
}

fn is_msrdc(hwnd: HWND) -> bool {
    unsafe {
        let mut pid = 0u32;
        GetWindowThreadProcessId(hwnd, Some(&mut pid));
        if pid == 0 {
            return false;
        }
        let h = match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
            Ok(h) => h,
            Err(_) => return false,
        };
        let mut buf = [0u16; 260];
        let mut len = buf.len() as u32;
        let ok = QueryFullProcessImageNameW(h, PROCESS_NAME_FORMAT(0), PWSTR(buf.as_mut_ptr()), &mut len).is_ok();
        let _ = CloseHandle(h);
        if !ok {
            return false;
        }
        String::from_utf16_lossy(&buf[..len as usize]).to_lowercase().ends_with("msrdc.exe")
    }
}
