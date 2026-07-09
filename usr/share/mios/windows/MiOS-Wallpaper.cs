using System;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace MiOSWallpaper
{
    /// <summary>
    /// MiOS Living Wallpaper Host
    /// Uses WebView2 WinForms control created natively as a direct child of the
    /// Windows WorkerW background layer, falling back to Progman if WorkerW
    /// cannot be spawned. No SetParent block - the DPI context is matched dynamically
    /// to the parent handle before SetParent, and Form is created as TopLevel = false.
    /// </summary>
    static class Program
    {
        // ── Win32 ──────────────────────────────────────────────────────────

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, IntPtr wParam,
            IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
        delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter,
            string lpszClass, string lpszWindow);

        [DllImport("user32.dll")]
        static extern int GetSystemMetrics(int nIndex);

        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr OpenInputDesktop(uint dwFlags, bool fInherit, uint dwDesiredAccess);

        [DllImport("user32.dll", SetLastError = true)]
        static extern bool SetThreadDesktop(IntPtr hDesktop);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr SetThreadDpiAwarenessContext(IntPtr dpiContext);

        [DllImport("user32.dll", SetLastError = true)]
        static extern bool SetParent(IntPtr hWndChild, IntPtr hWndNewParent);

        [DllImport("user32.dll")]
        static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
            int X, int Y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll", EntryPoint = "GetWindowLongW", SetLastError = true)]
        static extern int GetWindowLong32(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
        static extern IntPtr GetWindowLongPtr64(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll", EntryPoint = "SetWindowLongW", SetLastError = true)]
        static extern int SetWindowLong32(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
        static extern IntPtr SetWindowLongPtr64(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

        [DllImport("user32.dll")]
        static extern IntPtr GetWindowDpiAwarenessContext(IntPtr hwnd);

        // ── Constants ──────────────────────────────────────────────────────

        const int SM_CXVIRTUALSCREEN = 78;
        const int SM_CYVIRTUALSCREEN = 79;
        const int SM_XVIRTUALSCREEN = 76;
        const int SM_YVIRTUALSCREEN = 77;
        const int GWL_STYLE = -16;
        const int GWL_EXSTYLE = -20;
        const long WS_CHILD = 0x40000000;
        const long WS_POPUP = unchecked((long)0x80000000);
        const long WS_CAPTION = 0x00C00000;
        const long WS_THICKFRAME = 0x00040000;
        const int WS_EX_TOOLWINDOW = 0x00000080;
        const int WS_EX_APPWINDOW = 0x00040000;
        const int WS_EX_NOACTIVATE = 0x08000000;
        const uint DESKTOP_ALL_ACCESS = 0x1FF;
        const uint SWP_NOSIZE = 0x0001;
        const uint SWP_NOMOVE = 0x0002;
        const uint SWP_NOACTIVATE = 0x0010;
        const uint SWP_FRAMECHANGED = 0x0020;
        const uint SWP_SHOWWINDOW = 0x0040;

        // ── Logging ────────────────────────────────────────────────────────

        static string _logPath = @"C:\Windows\Web\MiOS\mios_wallpaper.log";
        static void Log(string msg)
        {
            try { File.AppendAllText(_logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + msg + Environment.NewLine); }
            catch { }
            Console.WriteLine(msg);
        }

        // Helper methods for 32/64 bit compatibility
        public static IntPtr GetWindowLong(IntPtr hWnd, int nIndex)
        {
            if (IntPtr.Size == 8)
                return GetWindowLongPtr64(hWnd, nIndex);
            else
                return new IntPtr(GetWindowLong32(hWnd, nIndex));
        }

        public static IntPtr SetWindowLong(IntPtr hWnd, int nIndex, IntPtr dwNewLong)
        {
            if (IntPtr.Size == 8)
                return SetWindowLongPtr64(hWnd, nIndex, dwNewLong);
            else
                return new IntPtr(SetWindowLong32(hWnd, nIndex, (int)dwNewLong.ToInt64()));
        }

        static void EnsureIgpuPreference()
        {
            try
            {
                using (var directXKey = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\DirectX"))
                {
                    if (directXKey != null)
                    {
                        using (var gpuKey = directXKey.CreateSubKey("UserGpuPreferences"))
                        {
                            if (gpuKey != null)
                            {
                                string exePath = System.Reflection.Assembly.GetExecutingAssembly().Location;
                                // GpuPreference=1; is Power Saving (iGPU)
                                gpuKey.SetValue(exePath, "GpuPreference=1;", Microsoft.Win32.RegistryValueKind.String);
                                Log("GPU Preference set to Power Saving (iGPU) for: " + exePath);
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log("EnsureIgpuPreference error: " + ex.Message);
            }
        }

        // ── Main ───────────────────────────────────────────────────────────

        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                MainInner(args);
            }
            catch (Exception ex)
            {
                try { File.WriteAllText(@"C:\Windows\Web\MiOS\crash.log", ex.ToString()); } catch {}
            }
        }

        static void MainInner(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Ensure we run on the iGPU (Power Saving)
            EnsureIgpuPreference();

            string url = args.Length > 0 ? args[0] : "file:///C:/Windows/Web/MiOS/living-wallpaper.html";

            Log("MiOS Living Wallpaper starting. URL=" + url);

            // Set DPI awareness context to Per-Monitor-V2 before any window ops
            try
            {
                SetThreadDpiAwarenessContext(new IntPtr(-4)); // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                Log("DPI awareness: Per-Monitor-V2");
            }
            catch (Exception ex) { Log("DPI awareness set failed: " + ex.Message); }

            // Bind to the interactive input desktop BEFORE any window lookup
            for (int attempt = 0; attempt < 3; attempt++)
            {
                try
                {
                    IntPtr hDesk = OpenInputDesktop(0, true, DESKTOP_ALL_ACCESS);
                    if (hDesk != IntPtr.Zero)
                    {
                        SetThreadDesktop(hDesk);
                        Log("Thread desktop: input desktop (attempt " + (attempt + 1) + ")");
                        break;
                    }
                    else
                    {
                        Log("OpenInputDesktop returned null, retrying... err=" + Marshal.GetLastWin32Error());
                        System.Threading.Thread.Sleep(1000);
                    }
                }
                catch (Exception ex) { Log("SetThreadDesktop failed: " + ex.Message); }
            }

            // ── 1. Spawn the WorkerW layer behind desktop icons ─────────────

            IntPtr progman = IntPtr.Zero;
            for (int i = 0; i < 15; i++)
            {
                progman = FindWindow("Progman", null);
                if (progman != IntPtr.Zero) break;
                Log("Progman not yet visible, waiting... (" + i + ")");
                System.Threading.Thread.Sleep(1000);
            }
            Log("Progman HWND: " + progman);

            if (progman == IntPtr.Zero)
            {
                Log("FATAL: Progman not found after retries. Aborting.");
                return;
            }

            // Sending 0x052C to Progman triggers Explorer to create the WorkerW sublayer
            IntPtr result;
            SendMessageTimeout(progman, 0x052C, new IntPtr(0x0D), new IntPtr(1), 0, 2000, out result);
            System.Threading.Thread.Sleep(500); // Give Explorer time to split

            // ── 2. Find the WorkerW that sits BEHIND the desktop icon layer ─
            IntPtr wallpaperWorkerW = IntPtr.Zero;

            // First check if there is a child WorkerW directly under Progman (common in newer/modified shells)
            wallpaperWorkerW = FindWindowEx(progman, IntPtr.Zero, "WorkerW", null);
            Log("Child WorkerW under Progman: " + wallpaperWorkerW);

            if (wallpaperWorkerW == IntPtr.Zero)
            {
                // If not under Progman, look for top-level WorkerW windows
                IntPtr shellWorkerW = IntPtr.Zero;
                EnumWindows((hwnd, _) =>
                {
                    StringBuilder sb = new StringBuilder(256);
                    GetClassName(hwnd, sb, 256);
                    if (sb.ToString() == "WorkerW")
                    {
                        IntPtr defView = FindWindowEx(hwnd, IntPtr.Zero, "SHELLDLL_DefView", null);
                        if (defView != IntPtr.Zero)
                            shellWorkerW = hwnd;
                    }
                    return true;
                }, IntPtr.Zero);
                Log("Shell WorkerW (icon layer): " + shellWorkerW);

                if (shellWorkerW != IntPtr.Zero)
                {
                    wallpaperWorkerW = FindWindowEx(IntPtr.Zero, shellWorkerW, "WorkerW", null);
                }
            }

            // If still no wallpaperWorkerW was found, fall back to Progman itself
            if (wallpaperWorkerW == IntPtr.Zero)
            {
                Log("Wallpaper WorkerW not found, falling back to Progman as parent.");
                wallpaperWorkerW = progman;
            }
            Log("Wallpaper layer HWND (target parent): " + wallpaperWorkerW);

            // ── 3. Create a hidden host Form ───────────────────────────────

            // The Form is invisible and parented to WorkerW/Progman — it is the Win32 owner
            // of the WebView2 control. We never show it on screen as a standalone window.
            WallpaperHostForm form = new WallpaperHostForm(url, wallpaperWorkerW);

            Log("Running application message loop...");
            Application.Run(form);
        }
    }

    /// <summary>
    /// WinForms Form that hosts the WebView2 control.
    /// On Load, it re-parents itself into the desktop layer.
    /// </summary>
    class WallpaperHostForm : Form
    {
        readonly string _url;
        readonly IntPtr _parentHwnd;
        WebView2 _wv;

        // Win32 imports for form parenting
        [DllImport("user32.dll", SetLastError = true)]
        static extern bool SetParent(IntPtr hWndChild, IntPtr hWndNewParent);

        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
        static extern IntPtr SetWindowLongPtr64(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

        [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
        static extern IntPtr GetWindowLongPtr64(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll")]
        static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter,
            int X, int Y, int cx, int cy, uint uFlags);

        [DllImport("user32.dll")]
        static extern int GetSystemMetrics(int nIndex);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr SetThreadDpiAwarenessContext(IntPtr dpiContext);

        [DllImport("user32.dll")]
        static extern IntPtr GetWindowDpiAwarenessContext(IntPtr hwnd);

        const int GWL_STYLE = -16;
        const int GWL_EXSTYLE = -20;
        const long WS_CHILD = 0x40000000;
        const long WS_POPUP = unchecked((long)0x80000000);
        const long WS_CAPTION = 0x00C00000;
        const long WS_THICKFRAME = 0x00040000;
        const int WS_EX_TOOLWINDOW = 0x00000080;
        const int WS_EX_APPWINDOW = 0x00040000;
        const int WS_EX_NOACTIVATE = 0x08000000;
        const uint SWP_FRAMECHANGED = 0x0020;
        const uint SWP_SHOWWINDOW = 0x0040;
        const uint SWP_NOACTIVATE = 0x0010;

        static string _logPath = @"C:\Windows\Web\MiOS\mios_wallpaper.log";
        static void Log(string msg)
        {
            try { File.AppendAllText(_logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + msg + Environment.NewLine); }
            catch { }
            Console.WriteLine(msg);
        }

        public WallpaperHostForm(string url, IntPtr parentHwnd)
        {
            _url = url;
            _parentHwnd = parentHwnd;

            // Make the form a child window from the very beginning to avoid SetParent errors
            TopLevel = false;
            FormBorderStyle = FormBorderStyle.None;
            ShowInTaskbar = false;

            // Size to cover the full virtual screen
            UpdateBoundsInternal();

            // Subscribe to display settings change event to auto-reposition on remote/display connect
            Microsoft.Win32.SystemEvents.DisplaySettingsChanged += SystemEvents_DisplaySettingsChanged;
        }

        private void SystemEvents_DisplaySettingsChanged(object sender, EventArgs e)
        {
            Log("Display settings changed event received. Re-aligning wallpaper bounds.");
            if (InvokeRequired)
            {
                BeginInvoke(new Action(UpdateBoundsInternal));
            }
            else
            {
                UpdateBoundsInternal();
            }
        }

        private void UpdateBoundsInternal()
        {
            try
            {
                int vx = GetSystemMetrics(76);  // SM_XVIRTUALSCREEN
                int vy = GetSystemMetrics(77);  // SM_YVIRTUALSCREEN
                int vcx = GetSystemMetrics(78); // SM_CXVIRTUALSCREEN
                int vcy = GetSystemMetrics(79); // SM_CYVIRTUALSCREEN
                Bounds = new Rectangle(vx, vy, vcx, vcy);

                if (Handle != IntPtr.Zero)
                {
                    SetWindowPos(Handle, new IntPtr(1), vx, vy, vcx, vcy,
                        SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOACTIVATE);
                    Log("Repositioned to screen bounds: " + vx + "," + vy + " " + vcx + "x" + vcy);
                }
            }
            catch (Exception ex)
            {
                Log("UpdateBoundsInternal error: " + ex.Message);
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            Microsoft.Win32.SystemEvents.DisplaySettingsChanged -= SystemEvents_DisplaySettingsChanged;
            base.OnFormClosed(e);
        }

        protected override async void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            Log("Form HWND: " + Handle);

            // ── Strip caption/popup style, ensure WS_CHILD ─────────────────
            long style = GetWindowLongPtr64(Handle, GWL_STYLE).ToInt64();
            style &= ~WS_POPUP;
            style &= ~WS_CAPTION;
            style &= ~WS_THICKFRAME;
            style |= WS_CHILD;
            SetWindowLongPtr64(Handle, GWL_STYLE, new IntPtr(style));

            long exStyle = GetWindowLongPtr64(Handle, GWL_EXSTYLE).ToInt64();
            exStyle &= ~WS_EX_APPWINDOW;
            exStyle |= WS_EX_TOOLWINDOW;
            exStyle |= WS_EX_NOACTIVATE;
            SetWindowLongPtr64(Handle, GWL_EXSTYLE, new IntPtr(exStyle));

            // ── Re-parent form HWND into the desktop layer ─────────────────
            // Match the thread's DPI context dynamically to the parent's to bypass SetParent restrictions (err=87)
            IntPtr parentDpi = GetWindowDpiAwarenessContext(_parentHwnd);
            IntPtr prevDpi = SetThreadDpiAwarenessContext(parentDpi);
            bool parentOk = SetParent(Handle, _parentHwnd);
            int parentErr = Marshal.GetLastWin32Error();
            SetThreadDpiAwarenessContext(prevDpi); // restore
            Log("SetParent(Form to parent): " + parentOk + ", err=" + parentErr);

            // Resize and position at the very bottom
            UpdateBoundsInternal();

            // ── Create WebView2 control ─────────────────────────────────────
            _wv = new WebView2();
            _wv.Dock = DockStyle.Fill;
            Controls.Add(_wv);

            try
            {
                string userDataFolder = @"C:\Windows\Temp\MiOS-WV2-Profile";
                var options = new CoreWebView2EnvironmentOptions();
                options.AdditionalBrowserArguments = "--ignore-gpu-blocklist --disable-gpu-driver-bug-workarounds --enable-gpu-rasterization";
                CoreWebView2Environment env = await CoreWebView2Environment.CreateAsync(
                    null, userDataFolder, options);
                Log("WebView2 environment created with GPU flags.");

                await _wv.EnsureCoreWebView2Async(env);
                Log("CoreWebView2 initialized.");

                // Suppress browser UI noise
                _wv.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                _wv.CoreWebView2.Settings.AreDevToolsEnabled = false;
                _wv.CoreWebView2.Settings.IsStatusBarEnabled = false;
                _wv.CoreWebView2.Settings.IsZoomControlEnabled = false;

                // Set virtual host name mapping for local files to allow query parameters
                _wv.CoreWebView2.SetVirtualHostNameToFolderMapping(
                    "mios.local",
                    @"C:\Windows\Web\MiOS",
                    CoreWebView2HostResourceAccessKind.Allow);
                Log("Virtual host name mapping registered.");

                string targetUrl = _url;
                if (targetUrl.StartsWith("file:///C:/Windows/Web/MiOS/", StringComparison.OrdinalIgnoreCase))
                {
                    targetUrl = "https://mios.local/" + targetUrl.Substring("file:///C:/Windows/Web/MiOS/".Length);
                }
                else if (targetUrl.StartsWith("file:///C:\\Windows\\Web\\MiOS\\", StringComparison.OrdinalIgnoreCase))
                {
                    targetUrl = "https://mios.local/" + targetUrl.Substring("file:///C:\\Windows\\Web\\MiOS\\".Length).Replace('\\', '/');
                }

                _wv.Source = new Uri(targetUrl);
                Log("Navigating to target: " + targetUrl);
            }
            catch (Exception ex)
            {
                Log("WebView2 init error: " + ex);
            }
        }
    }
}
