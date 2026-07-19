// The wallpaper host (runs in the interactive session): a borderless WebView sized to the virtual
// screen, SetParent'd onto the WorkerW so it renders behind the desktop icons. Reads the SSOT
// WallpaperUrl from the registry; folds the WSLg gui-watch in as a background thread (no pwsh, no
// console flash). Built #![windows_subsystem="windows"] -> never surfaces a taskbar/console window.
use tao::dpi::{PhysicalPosition, PhysicalSize};
use tao::event::Event;
use tao::event_loop::{ControlFlow, EventLoopBuilder};
use tao::platform::windows::{WindowBuilderExtWindows, WindowExtWindows};
use tao::window::WindowBuilder;
use windows::Win32::Foundation::HWND;
use windows::Win32::UI::WindowsAndMessaging::{
    GetSystemMetrics, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN, SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN,
};
use wry::WebViewBuilder;

pub fn run_host() {
    // Folded WSLg window-centering daemon (was mios-gui-watch.ps1) -- one process, no separate pwsh.
    std::thread::spawn(super::guiwatch::run_forever);

    let url = read_wallpaper_url();

    let event_loop = EventLoopBuilder::new().build();
    let (vx, vy, vw, vh) = unsafe {
        (
            GetSystemMetrics(SM_XVIRTUALSCREEN),
            GetSystemMetrics(SM_YVIRTUALSCREEN),
            GetSystemMetrics(SM_CXVIRTUALSCREEN),
            GetSystemMetrics(SM_CYVIRTUALSCREEN),
        )
    };
    let window = WindowBuilder::new()
        .with_decorations(false)
        .with_skip_taskbar(true)
        .with_inner_size(PhysicalSize::new(vw.max(1) as u32, vh.max(1) as u32))
        .build(&event_loop)
        .expect("create wallpaper window");
    window.set_outer_position(PhysicalPosition::new(vx, vy));

    // Attach onto the WorkerW so the WebView composites as the wallpaper (behind the icons).
    let hwnd = HWND(window.hwnd() as _);
    if let Some(workerw) = super::workerw::find_wallpaper_workerw() {
        super::workerw::attach(hwnd, workerw);
    }

    // Build the WebView on the (now re-parented) window.
    let _webview = WebViewBuilder::new(&window)
        .with_url(&url)
        .build()
        .expect("create webview");

    event_loop.run(move |event, _target, control_flow| {
        *control_flow = ControlFlow::Wait;
        // Keep the window + webview alive for the process lifetime; the service restarts us on exit.
        let _ = (&event, &window, &_webview);
    });
}

fn read_wallpaper_url() -> String {
    crate::util::reg_read_sz(super::WALLPAPER_URL_KEY, super::WALLPAPER_URL_VALUE)
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| super::WALLPAPER_URL_FALLBACK.to_string())
}
