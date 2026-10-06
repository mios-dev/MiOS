// AI-hint: Native Windows terminal launcher: render layered MiOS SSOT before launching and center the visible frame on the current monitor work area.
// AI-related: usr/share/mios/windows/mios-native-client-setup.ps1, usr/share/mios/mios.toml, usr/share/mios/windows/mios-pc-control.ps1
#![cfg_attr(windows, windows_subsystem = "windows")]

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Bounds {
    x: i32,
    y: i32,
    width: i32,
    height: i32,
}

fn center(work: Bounds, window: Bounds) -> Bounds {
    let width = work.width.min(window.width);
    let height = work.height.min(window.height);
    Bounds {
        x: work.x + (work.width - width) / 2,
        y: work.y + (work.height - height) / 2,
        width,
        height,
    }
}

fn geometry_proof(negative: bool) -> Result<(), String> {
    let areas = [
        Bounds {
            x: 0,
            y: 0,
            width: 1920,
            height: 1040,
        },
        Bounds {
            x: -2160,
            y: 0,
            width: 2160,
            height: 3840,
        },
        Bounds {
            x: 1920,
            y: -1200,
            width: 3840,
            height: 2120,
        },
        Bounds {
            x: 0,
            y: 0,
            width: 800,
            height: 560,
        },
    ];
    for work in areas {
        for scale in [100, 125, 150, 200, 300] {
            let mut result = center(
                work,
                Bounds {
                    x: 153,
                    y: 219,
                    width: 820 * scale / 100,
                    height: 412 * scale / 100,
                },
            );
            if negative {
                result.x = 0;
            }
            if result.width > work.width
                || result.height > work.height
                || (2 * result.x + result.width - (2 * work.x + work.width)).abs() > 1
                || (2 * result.y + result.height - (2 * work.y + work.height)).abs() > 1
            {
                return Err("DEVLOOP-PLANTED-CENTER: geometry mismatch".into());
            }
        }
    }
    Ok(())
}

#[cfg(windows)]
mod desktop {
    use super::{center, Bounds};
    use serde_json::Value;
    use std::os::windows::process::CommandExt;
    use std::{
        env, fs, mem,
        path::PathBuf,
        process::Command,
        ptr, thread,
        time::{Duration, Instant, SystemTime, UNIX_EPOCH},
    };
    use windows_sys::Win32::{
        Foundation::{HWND, LPARAM, POINT, RECT},
        Graphics::{
            Dwm::{DwmGetWindowAttribute, DWMWA_EXTENDED_FRAME_BOUNDS},
            Gdi::{GetMonitorInfoW, MonitorFromPoint, MONITORINFO, MONITOR_DEFAULTTONEAREST},
        },
        UI::{
            HiDpi::{
                SetProcessDpiAwarenessContext, SetThreadDpiAwarenessContext,
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
            },
            WindowsAndMessaging::*,
        },
    };

    fn wide(text: &str) -> Vec<u16> {
        text.encode_utf16().chain(Some(0)).collect()
    }
    fn bounds(r: RECT) -> Bounds {
        Bounds {
            x: r.left,
            y: r.top,
            width: r.right - r.left,
            height: r.bottom - r.top,
        }
    }
    fn hidden(command: &mut Command) -> &mut Command {
        command.creation_flags(0x0800_0000)
    }
    fn native_bin() -> Result<PathBuf, String> {
        let exe = env::current_exe().map_err(|e| e.to_string())?;
        let parent = exe.parent().ok_or("Executable directory missing")?;
        if parent.join("native-binding.json").is_file() {
            return Ok(parent.into());
        }
        Ok(
            PathBuf::from(env::var_os("ProgramData").ok_or("ProgramData missing")?)
                .join("MiOS/bin"),
        )
    }
    fn json(path: PathBuf) -> Result<Value, String> {
        serde_json::from_slice(&fs::read(path).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())
    }
    fn text<'a>(value: &'a Value, key: &str) -> Result<&'a str, String> {
        value[key]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| format!("SSOT {key} is missing"))
    }
    fn terminal() -> Result<PathBuf, String> {
        for dir in env::split_paths(&env::var_os("PATH").unwrap_or_default()) {
            let path = dir.join("wt.exe");
            if path.is_file() {
                return Ok(path);
            }
        }
        let output = hidden(Command::new("powershell.exe").args([
            "-NoLogo",
            "-NoProfile",
            "-Command",
            "(Get-AppxPackage Microsoft.WindowsTerminal).InstallLocation",
        ]))
        .output()
        .map_err(|e| e.to_string())?;
        let path = PathBuf::from(String::from_utf8_lossy(&output.stdout).trim()).join("wt.exe");
        if !output.status.success() || !path.is_file() {
            return Err("Windows Terminal is missing; run the MiOS installer".into());
        }
        Ok(path)
    }
    fn monitor(point: POINT) -> Result<Bounds, String> {
        let mut info: MONITORINFO = unsafe { mem::zeroed() };
        info.cbSize = mem::size_of::<MONITORINFO>() as u32;
        if unsafe { GetMonitorInfoW(MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST), &mut info) }
            == 0
        {
            return Err("Cannot read display work area".into());
        }
        Ok(bounds(info.rcWork))
    }
    struct Search {
        title: String,
        hwnd: HWND,
    }
    unsafe extern "system" fn find(hwnd: HWND, context: LPARAM) -> i32 {
        let search = &mut *(context as *mut Search);
        if IsWindowVisible(hwnd) == 0 {
            return 1;
        }
        let mut name = [0u16; 512];
        let len = GetWindowTextW(hwnd, name.as_mut_ptr(), name.len() as i32);
        if len <= 0 {
            return 1;
        }
        if String::from_utf16_lossy(&name[..len as usize]) != search.title {
            return 1;
        }
        let mut class = [0u16; 128];
        let len = GetClassNameW(hwnd, class.as_mut_ptr(), class.len() as i32);
        if String::from_utf16_lossy(&class[..len.max(0) as usize])
            != "CASCADIA_HOSTING_WINDOW_CLASS"
        {
            return 1;
        }
        search.hwnd = hwnd;
        0
    }
    fn window(title: &str) -> HWND {
        let mut search = Search {
            title: title.into(),
            hwnd: ptr::null_mut(),
        };
        unsafe {
            EnumWindows(Some(find), &mut search as *mut Search as LPARAM);
        }
        search.hwnd
    }
    fn place(hwnd: HWND, point: POINT) -> Result<Bounds, String> {
        if unsafe { IsZoomed(hwnd) } != 0 || unsafe { IsIconic(hwnd) } != 0 {
            unsafe { ShowWindow(hwnd, SW_RESTORE); }
        }
        let mut r: RECT = unsafe { mem::zeroed() };
        if unsafe { GetWindowRect(hwnd, &mut r) } == 0 {
            return Err("Cannot read terminal window bounds".into());
        }
        let outer = bounds(r);
        let mut frame = r;
        unsafe {
            DwmGetWindowAttribute(
                hwnd,
                DWMWA_EXTENDED_FRAME_BOUNDS as u32,
                &mut frame as *mut RECT as _,
                mem::size_of::<RECT>() as u32,
            );
        }
        let visible = bounds(frame);
        if visible.width <= 0 || visible.height <= 0 {
            return Err("Terminal has no visible frame".into());
        }
        let target = center(monitor(point)?, visible);
        if unsafe {
            SetWindowPos(
                hwnd,
                ptr::null_mut(),
                target.x - (visible.x - outer.x),
                target.y - (visible.y - outer.y),
                target.width + outer.width - visible.width,
                target.height + outer.height - visible.height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        } == 0
        {
            return Err("Terminal placement failed".into());
        }
        Ok(target)
    }
    fn helper(action: &str, args: &[String]) -> Result<(), String> {
        // Keep the complete existing GUI/UIA surface, including right/middle
        // click and real accessibility trees, in its canonical implementation.
        let bin = native_bin()?;
        let binding = json(bin.join("native-binding.json"))?;
        let script = match action {
            "dump" => "mios-uia-dump.ps1",
            "foreground" => "mios-window-foreground.ps1",
            _ => "mios-pc-control.ps1",
        };
        let mut command = Command::new(text(&binding, "engine")?);
        command
            .args(["-NoLogo", "-NoProfile", "-File"])
            .arg(bin.join(script));
        if !matches!(action, "dump" | "foreground") {
            command.arg(action);
        }
        if action == "foreground" {
            command.arg("-ProcessName");
        }
        command.args(args);
        let status = hidden(&mut command).status().map_err(|e| e.to_string())?;
        if !status.success() {
            return Err(format!("{action} failed: {status}"));
        }
        Ok(())
    }
    pub fn run(args: &[String]) -> Result<(), String> {
        unsafe {
            SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
            SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
        }
        if let Some(action) = args.first().filter(|s| {
            matches!(
                s.as_str(),
                "dump" | "foreground" | "click" | "move" | "resize"
            )
        }) {
            return helper(action, &args[1..]);
        }
        let bin = native_bin()?;
        let binding = json(bin.join("native-binding.json"))?;
        let engine = text(&binding, "engine")?;
        let projection = hidden(
            Command::new(engine)
                .args(["-NoLogo", "-NoProfile", "-File"])
                .arg(bin.join("mios-native-client-setup.ps1"))
                .args(["-RuntimeOnly", "-EmitConfig", "-BinDirectory"])
                .arg(&bin),
        )
        .output()
        .map_err(|e| e.to_string())?;
        if !projection.status.success() {
            return Err("Runtime SSOT projection failed; launch stopped".into());
        }
        // Packaged clients may see a virtualized stale LocalAppData file.
        // Use this invocation's resolved SSOT rather than re-reading a cache.
        let config: Value = serde_json::from_slice(&projection.stdout)
            .map_err(|e| format!("Runtime SSOT projection returned invalid JSON: {e}"))?;
        let profiles = &config["theme"]["terminal"];
        let centered = profiles["center_on_launch"]
            .as_bool()
            .ok_or("SSOT center_on_launch must be a boolean")?;
        let dev = text(profiles, "dev_profile_name")?;
        let profile = args
            .first()
            .filter(|s| !s.starts_with("--"))
            .map(String::as_str)
            .unwrap_or(dev);
        let action = args.iter().position(|a| a == "--action")
            .map(|i| args.get(i + 1).map(String::as_str).ok_or("--action needs a MiOS action"))
            .transpose()?;
        let ai = action == Some("ai");
        let logical = if ai {
            text(&config["mcp"]["tmux"]["workspace"], "window_name")?
        } else if profile == dev {
            text(profiles, "summon_window_name")?
        } else {
            profile
        };
        let compact = args.iter().any(|a| a == "--compact");
        let dimensions = &config["terminal"];
        let cols = dimensions["cols"]
            .as_u64()
            .filter(|n| *n > 0)
            .ok_or("SSOT terminal.cols missing")?;
        let rows = dimensions["rows"]
            .as_u64()
            .filter(|n| *n > 0)
            .ok_or("SSOT terminal.rows missing")?;
        let title = format!(
            "MiOS-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|e| e.to_string())?
                .as_nanos()
        );
        let window_name = if args.iter().any(|a| a == "--test-launch") {
            title.as_str()
        } else {
            logical
        };
        let mut point = POINT { x: 0, y: 0 };
        if unsafe { GetCursorPos(&mut point) } == 0 {
            return Err("Cannot read launch monitor cursor".into());
        }
        let mut command = Command::new(terminal()?);
        command.args([
            "-w",
            window_name,
            "--size",
            &format!("{cols},{rows}"),
            "--focus",
            "new-tab",
            "-p",
            profile,
            "--colorScheme",
            text(profiles, "scheme_name")?,
            "--title",
            &title,
            "--suppressApplicationTitle",
        ]);
        if let Some(action) = action {
            if !config["keybindings"]["actions"]
                .as_array()
                .ok_or("SSOT keybindings missing")?
                .iter()
                .any(|a| a["id"].as_str() == Some(action))
            {
                return Err("Unknown MiOS SSOT action".into());
            }
            command
                .args(["--", engine, "-NoLogo", "-NoProfile", "-File"])
                .arg(bin.join("mios-native-entry.ps1"))
                .args(["terminal", "--action", action]);
            if compact { command.arg("--compact"); }
        }
        hidden(&mut command).spawn().map_err(|e| e.to_string())?;
        let deadline = Instant::now() + Duration::from_secs(8);
        let hwnd = loop {
            let hwnd = window(&title);
            if !hwnd.is_null() {
                break hwnd;
            }
            if Instant::now() >= deadline {
                return Err("Launched terminal window did not appear".into());
            }
            thread::sleep(Duration::from_millis(150));
        };
        if !centered {
            return if args.iter().any(|a| a == "--test-launch") {
                Err("SSOT centering is disabled".into())
            } else {
                Ok(())
            };
        }
        for _ in 0..12 {
            // Work area and visible DWM frame are re-read during settling;
            // rotation, taskbar offsets and DPI are never baked into pixels.
            place(hwnd, point)?;
            thread::sleep(Duration::from_millis(500));
        }
        {
            let mut frame: RECT = unsafe { mem::zeroed() };
            if unsafe {
                DwmGetWindowAttribute(
                    hwnd,
                    DWMWA_EXTENDED_FRAME_BOUNDS as u32,
                    &mut frame as *mut RECT as _,
                    mem::size_of::<RECT>() as u32,
                )
            } != 0
            {
                return Err("Visible frame proof unavailable".into());
            }
            let frame = bounds(frame);
            let work = monitor(point)?;
            if (2 * frame.x + frame.width - (2 * work.x + work.width)).abs() > 2
                || (2 * frame.y + frame.height - (2 * work.y + work.height)).abs() > 2
            {
                return Err("DEVLOOP-PLANTED-CENTER: visible frame is not centered".into());
            }
            if args.iter().any(|a| a == "--test-launch") {
                println!("Native MiOS launch centered: {frame:?}");
            }
        }
        Ok(())
    }
    pub fn error(message: &str) {
        unsafe {
            MessageBoxW(
                ptr::null_mut(),
                wide(message).as_ptr(),
                wide("MiOS SSOT").as_ptr(),
                MB_OK | MB_ICONERROR,
            );
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let proof = args
        .first()
        .is_some_and(|a| a.starts_with("--test-geometry"));
    let result = if proof {
        geometry_proof(args[0].ends_with("negative"))
    } else {
        #[cfg(windows)]
        {
            desktop::run(&args)
        }
        #[cfg(not(windows))]
        {
            Err("This launcher requires a Windows desktop".into())
        }
    };
    if let Err(error) = result {
        eprintln!("{error}");
        #[cfg(windows)]
        if !proof && !args.iter().any(|a| a == "--test-launch") {
            desktop::error(&error);
        }
        std::process::exit(if proof { 2 } else { 3 });
    }
    if proof {
        println!("20 monitor/orientation/DPI geometry cases passed");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn geometry_and_planted_negative() {
        assert!(geometry_proof(false).is_ok());
        assert!(geometry_proof(true)
            .unwrap_err()
            .contains("DEVLOOP-PLANTED-CENTER"));
    }
    #[test]
    fn clamps_oversized_window_on_negative_portrait_monitor() {
        let work = Bounds {
            x: -1080,
            y: -640,
            width: 1080,
            height: 1840,
        };
        assert_eq!(
            center(
                work,
                Bounds {
                    x: 2000,
                    y: 0,
                    width: 3840,
                    height: 2160
                }
            ),
            work
        );
    }
    #[test]
    fn centers_odd_dimensions_with_one_pixel_rounding() {
        assert_eq!(
            center(
                Bounds {
                    x: 1920,
                    y: 41,
                    width: 1919,
                    height: 1039
                },
                Bounds {
                    x: 0,
                    y: 0,
                    width: 800,
                    height: 400
                }
            ),
            Bounds {
                x: 2479,
                y: 360,
                width: 800,
                height: 400
            }
        );
    }
}
