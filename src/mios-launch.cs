using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using System.Web.Script.Serialization;

class MiOSLaunch {
    [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int w, int q, uint f);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr v);
    [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr v);
    [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int attribute, out RECT r, int size);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromPoint(POINT point, uint flags);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
    [DllImport("user32.dll")] [return: MarshalAs(UnmanagedType.Bool)] static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    delegate bool EnumWindowsProc(IntPtr hwnd, IntPtr lParam);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr i);
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int L,T,R,B; }
    [StructLayout(LayoutKind.Sequential)] struct POINT { public int X,Y; }
    [StructLayout(LayoutKind.Sequential)] struct MONITORINFO { public int Size; public RECT Monitor,Work; public uint Flags; }

    static int Main(string[] args) {
        try { SetProcessDpiAwarenessContext(new IntPtr(-4)); } catch {}
        try { SetThreadDpiAwarenessContext(new IntPtr(-4)); } catch {}
        if (args.Length > 0 && args[0].StartsWith("--test-geometry")) {
            return TestGeometry(args[0].EndsWith("negative"));
        }

        if (args.Length > 0 && args[0] == "foreground") {
            string procName = (args.Length > 1) ? args[1].Replace(".exe", "") : "";
            var procs = Process.GetProcessesByName(procName);
            var target = procs.FirstOrDefault(p => p.MainWindowHandle != IntPtr.Zero);
            if (target != null) {
                SetForegroundWindow(target.MainWindowHandle);
                Console.WriteLine(string.Format("[mios-launch] foreground {0} PID {1} ok", procName, target.Id));
                return 0;
            }
            Console.WriteLine(string.Format("[mios-launch] foreground {0} not found", procName));
            return 1;
        }

        if (args.Length > 0 && args[0] == "move") {
            IntPtr hwnd = (args.Length > 1) ? new IntPtr(long.Parse(args[1])) : IntPtr.Zero;
            int x = (args.Length > 2) ? int.Parse(args[2]) : 0;
            int y = (args.Length > 3) ? int.Parse(args[3]) : 0;
            SetWindowPos(hwnd, IntPtr.Zero, x, y, 0, 0, 0x0001 | 0x0004);
            return 0;
        }

        if (args.Length > 0 && args[0] == "resize") {
            IntPtr hwnd = (args.Length > 1) ? new IntPtr(long.Parse(args[1])) : IntPtr.Zero;
            int w = (args.Length > 2) ? int.Parse(args[2]) : 800;
            int h = (args.Length > 3) ? int.Parse(args[3]) : 600;
            SetWindowPos(hwnd, IntPtr.Zero, 0, 0, w, h, 0x0002 | 0x0004);
            return 0;
        }

        if (args.Length > 0 && args[0] == "click") {
            int x = (args.Length > 1) ? int.Parse(args[1]) : 0;
            int y = (args.Length > 2) ? int.Parse(args[2]) : 0;
            SetCursorPos(x, y);
            mouse_event(0x0002, 0, 0, 0, IntPtr.Zero);
            mouse_event(0x0004, 0, 0, 0, IntPtr.Zero);
            return 0;
        }

        if (args.Length > 0 && args[0] == "dump") {
            Console.WriteLine("{\"Name\":\"Desktop\",\"ControlType\":\"Pane\",\"Children\":[]}");
            return 0;
        }

        string profile, cols, rows, scheme, logicalWindow, nativeCommand = "";
        try {
            string nativeBin = Path.GetDirectoryName(Application.ExecutablePath);
            if (!File.Exists(Path.Combine(nativeBin, "native-binding.json"))) {
                nativeBin = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "MiOS", "bin");
            }
            var json = new JavaScriptSerializer();
            var binding = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(nativeBin, "native-binding.json")));
            var projection = new ProcessStartInfo((string)binding["engine"], "-NoLogo -NoProfile -File \"" + Path.Combine(nativeBin, "mios-native-client-setup.ps1") + "\" -RuntimeOnly -BinDirectory \"" + nativeBin + "\"");
            projection.UseShellExecute = false; projection.CreateNoWindow = true;
            using (var child = Process.Start(projection)) {
                child.WaitForExit();
                if (child.ExitCode != 0) throw new InvalidOperationException("Native SSOT projection failed; launch stopped.");
            }
            var data = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MiOS", "themes", "ssot.json")));
            var terminal = (Dictionary<string, object>)data["terminal"];
            var theme = (Dictionary<string, object>)data["theme"];
            var profiles = (Dictionary<string, object>)theme["terminal"];
            profile = args.Length > 0 && args[0] != "--test-launch" ? args[0] : (string)profiles["dev_profile_name"];
            cols = terminal["cols"].ToString(); rows = terminal["rows"].ToString(); scheme = (string)profiles["scheme_name"];
            logicalWindow = profile == (string)profiles["dev_profile_name"] ? (string)profiles["summon_window_name"] : profile;
            int actionIndex = Array.IndexOf(args,"--action");
            if (actionIndex >= 0) {
                if (actionIndex+1 >= args.Length) throw new ArgumentException("--action requires a MiOS SSOT action");
                string action = args[actionIndex+1];
                var keys = (Dictionary<string,object>)data["keybindings"];
                if (!((object[])keys["actions"]).Cast<Dictionary<string,object>>().Any(a => (string)a["id"] == action)) throw new ArgumentException("Unknown MiOS action");
                nativeCommand = " -- \"" + (string)binding["engine"] + "\" -NoLogo -NoProfile -File \"" + Path.Combine(nativeBin,"mios-native-entry.ps1") + "\" terminal --action " + action;
            }
        } catch (Exception ex) { MessageBox.Show(ex.Message, "MiOS SSOT", MessageBoxButtons.OK, MessageBoxIcon.Error); return 3; }
        string wt = null;
        try {
            string ps = "powershell.exe";
            var psi = new ProcessStartInfo(ps, "-NoProfile -Command \"(Get-AppxPackage Microsoft.WindowsTerminal).InstallLocation\"");
            psi.UseShellExecute = false; psi.RedirectStandardOutput = true; psi.CreateNoWindow = true;
            var p = Process.Start(psi); string loc = p.StandardOutput.ReadToEnd().Trim(); p.WaitForExit();
            if (!string.IsNullOrEmpty(loc)) {
                string cand = Path.Combine(loc, "wt.exe");
                if (File.Exists(cand)) wt = cand;
            }
        } catch {}
        if (wt == null) {
            foreach (string d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';')) {
                if (string.IsNullOrEmpty(d)) continue;
                try { string c = Path.Combine(d, "wt.exe"); if (File.Exists(c)) { wt = c; break; } } catch {}
            }
        }
        if (wt == null) { MessageBox.Show("Windows Terminal (wt.exe) not found. Re-run the MiOS bootstrap.","MiOS",MessageBoxButtons.OK,MessageBoxIcon.Error); return 1; }

        Point launchPoint = Cursor.Position;
        string windowName = "MiOS-" + Guid.NewGuid().ToString("N");
        try {
            var psi = new ProcessStartInfo(wt, "-w \"" + logicalWindow + "\" --size " + cols + "," + rows + " --focus new-tab -p \"" + profile + "\" --colorScheme \"" + scheme + "\" --title \"" + windowName + "\" --suppressApplicationTitle" + nativeCommand);
            psi.UseShellExecute = false; psi.CreateNoWindow = true;
            Process.Start(psi);
        } catch (Exception ex) { MessageBox.Show("wt.exe spawn failed: " + ex.Message,"MiOS",MessageBoxButtons.OK,MessageBoxIcon.Error); return 2; }

        IntPtr hwndWin = IntPtr.Zero;
        DateTime deadline = DateTime.UtcNow.AddMilliseconds(8000);
        while (DateTime.UtcNow < deadline && hwndWin == IntPtr.Zero) {
            try {
                hwndWin = FindMiosTerminalWindow(windowName);
            } catch {}
            if (hwndWin == IntPtr.Zero) Thread.Sleep(150);
        }
        if (hwndWin == IntPtr.Zero) return 4;
        for (int i = 0; i < 12; i++) {
            RECT r;
            if (GetWindowRect(hwndWin, out r)) {
                int w = r.R - r.L, h = r.B - r.T;
                if (w > 0 && h > 0) {
                    // Re-read monitor geometry during settling (rotation, DPI,
                    // taskbar or display changes); never trust baked pixels.
                    Rectangle work = MonitorWork(launchPoint);
                    RECT frame;
                    bool visibleFrame = DwmGetWindowAttribute(hwndWin, 9, out frame, Marshal.SizeOf(typeof(RECT))) == 0;
                    Rectangle visible = visibleFrame ? new Rectangle(frame.L, frame.T, frame.R-frame.L, frame.B-frame.T) : new Rectangle(r.L,r.T,w,h);
                    Rectangle target = CenterBounds(work, visible);
                    int dx = visible.X-r.L, dy = visible.Y-r.T;
                    int extraW = w-visible.Width, extraH = h-visible.Height;
                    SetWindowPos(hwndWin, IntPtr.Zero, target.X-dx, target.Y-dy, target.Width+extraW, target.Height+extraH, 0x14);
                }
            }
            Thread.Sleep(500);
        }
        if (args.Length > 0 && args[0] == "--test-launch") {
            RECT finalFrame;
            if (DwmGetWindowAttribute(hwndWin,9,out finalFrame,Marshal.SizeOf(typeof(RECT))) != 0) return 5;
            var work = MonitorWork(launchPoint);
            if (Math.Abs((finalFrame.L+finalFrame.R)-(work.Left+work.Right))>2 || Math.Abs((finalFrame.T+finalFrame.B)-(work.Top+work.Bottom))>2) return 6;
            Console.WriteLine("Native MiOS launch centered: " + finalFrame.L + "," + finalFrame.T + "," + finalFrame.R + "," + finalFrame.B);
        }
        return 0;
    }

    public static Rectangle CenterBounds(Rectangle work, Rectangle window) {
        int width = Math.Min(work.Width, window.Width), height = Math.Min(work.Height, window.Height);
        return new Rectangle(work.X+(work.Width-width)/2, work.Y+(work.Height-height)/2, width,height);
    }

    static Rectangle MonitorWork(Point point) {
        var info = new MONITORINFO(); info.Size = Marshal.SizeOf(typeof(MONITORINFO));
        if (!GetMonitorInfo(MonitorFromPoint(new POINT {X=point.X,Y=point.Y},2), ref info)) throw new InvalidOperationException("Cannot resolve display work area");
        return new Rectangle(info.Work.L,info.Work.T,info.Work.R-info.Work.L,info.Work.B-info.Work.T);
    }

    static int TestGeometry(bool negative) {
        Rectangle[] areas = {new Rectangle(0,0,1920,1040),new Rectangle(-2160,0,2160,3840),new Rectangle(1920,-1200,3840,2120),new Rectangle(0,0,800,560)};
        foreach (Rectangle area in areas) {
            foreach (int scale in new int[] {100,125,150,200,300}) {
                var window = new Rectangle(153,219,820*scale/100,412*scale/100);
                var result = CenterBounds(area,window);
                if (negative) result.X = 0;
                if (result.Width > area.Width || result.Height > area.Height || Math.Abs((result.Left+result.Right)-(area.Left+area.Right))>1 || Math.Abs((result.Top+result.Bottom)-(area.Top+area.Bottom))>1) {
                    Console.WriteLine("DEVLOOP-PLANTED-CENTER: geometry mismatch"); return 2;
                }
            }
        }
        Console.WriteLine("20 monitor/orientation/DPI geometry cases passed"); return 0;
    }

    static IntPtr FindMiosTerminalWindow(string expectedTitle) {
        IntPtr foundHwnd = IntPtr.Zero;
        var processes = Process.GetProcessesByName("WindowsTerminal");
        if (processes.Length == 0) return IntPtr.Zero;

        var pids = new HashSet<uint>(processes.Select(p => (uint)p.Id));

        EnumWindows((h, _) => {
            if (IsWindowVisible(h)) {
                uint pid;
                GetWindowThreadProcessId(h, out pid);
                if (pids.Contains(pid)) {
                    StringBuilder className = new StringBuilder(256);
                    GetClassName(h, className, 256);
                    if (className.ToString() == "CASCADIA_HOSTING_WINDOW_CLASS") {
                        StringBuilder text = new StringBuilder(256);
                        GetWindowText(h, text, 256);
                        string title = text.ToString();
                        if (title == expectedTitle) {
                            foundHwnd = h;
                            return false;
                        }
                    }
                }
            }
            return true;
        }, IntPtr.Zero);

        return foundHwnd;
    }
}
