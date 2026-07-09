using System;
using System.Runtime.InteropServices;
using System.Text;
using System.IO;

/// <summary>
/// MiOS Wallpaper Launcher — runs as SYSTEM/elevated, steals explorer.exe's token
/// and CreateProcessAsUser to spawn MiOS-Wallpaper.exe in the user's interactive
/// WinSta0\Default desktop so it can find Progman + WorkerW.
/// </summary>
class MiOSLaunchAsUser
{
    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool OpenProcessToken(IntPtr proc, uint access, out IntPtr token);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool DuplicateTokenEx(IntPtr existing, uint desiredAccess,
        IntPtr tokenAttributes, int impersonationLevel, int tokenType, out IntPtr newToken);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcessAsUser(IntPtr token, string appName, string cmdLine,
        IntPtr procAttr, IntPtr threadAttr, bool inherit, uint creationFlags,
        IntPtr env, string cwd, ref STARTUPINFO si, out PROCESS_INFORMATION pi);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern IntPtr OpenProcess(uint access, bool inherit, int pid);

    [DllImport("userenv.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateEnvironmentBlock(out IntPtr env, IntPtr token, bool inherit);

    [DllImport("userenv.dll")] static extern bool DestroyEnvironmentBlock(IntPtr env);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct STARTUPINFO
    {
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public int dwX, dwY, dwXSize, dwYSize;
        public int dwXCountChars, dwYCountChars;
        public int dwFillAttribute;
        public int dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput, hStdOutput, hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION
    {
        public IntPtr hProcess, hThread;
        public int dwProcessId, dwThreadId;
    }

    const uint TOKEN_DUPLICATE = 0x0002;
    const uint TOKEN_QUERY = 0x0008;
    const uint TOKEN_ASSIGN_PRIMARY = 0x0001;
    const uint TOKEN_ADJUST_DEFAULT = 0x0080;
    const uint TOKEN_ADJUST_SESSIONID = 0x0100;
    const uint TOKEN_ALL_ACCESS = 0xF01FF;
    const int SecurityImpersonation = 2;
    const int TokenPrimary = 1;
    const uint PROCESS_ALL_ACCESS = 0x1F0FFF;
    const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    const uint CREATE_NO_WINDOW = 0x08000000;

    static void Main(string[] args)
    {
        string logPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "mios_launcher.log");
        Action<string> log = (msg) => {
            try { File.AppendAllText(logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + msg + Environment.NewLine); }
            catch { }
            Console.WriteLine(msg);
        };

        string wallpaperExe = @"C:\Windows\Web\MiOS\MiOS-Wallpaper.exe";
        string wallpaperUrl = args.Length > 0 ? args[0] : 
            "file:///C:/Windows/Web/MiOS/living-wallpaper.html";

        log("MiOS Launcher starting. Finding explorer.exe to steal token...");

        // Find explorer.exe in the interactive session (Session 2 on RDP)
        var procs = System.Diagnostics.Process.GetProcessesByName("explorer");
        if (procs.Length == 0)
        {
            log("FATAL: No explorer.exe found.");
            return;
        }

        var explorerProc = procs[0];
        log("Found explorer.exe PID=" + explorerProc.Id + " Session=" + explorerProc.SessionId);

        IntPtr explorerHandle = OpenProcess(PROCESS_ALL_ACCESS, false, explorerProc.Id);
        if (explorerHandle == IntPtr.Zero)
        {
            log("OpenProcess failed: " + Marshal.GetLastWin32Error());
            return;
        }

        IntPtr explorerToken = IntPtr.Zero;
        if (!OpenProcessToken(explorerHandle, TOKEN_ALL_ACCESS, out explorerToken))
        {
            log("OpenProcessToken failed: " + Marshal.GetLastWin32Error());
            CloseHandle(explorerHandle);
            return;
        }

        IntPtr primaryToken = IntPtr.Zero;
        if (!DuplicateTokenEx(explorerToken, TOKEN_ALL_ACCESS, IntPtr.Zero,
            SecurityImpersonation, TokenPrimary, out primaryToken))
        {
            log("DuplicateTokenEx failed: " + Marshal.GetLastWin32Error());
            CloseHandle(explorerToken);
            CloseHandle(explorerHandle);
            return;
        }

        log("Token duplicated successfully.");

        // Build environment block from user token
        IntPtr env = IntPtr.Zero;
        CreateEnvironmentBlock(out env, primaryToken, false);

        STARTUPINFO si = new STARTUPINFO();
        si.cb = Marshal.SizeOf(si);
        si.lpDesktop = "winsta0\\default";
        si.wShowWindow = 0; // SW_HIDE

        PROCESS_INFORMATION pi = new PROCESS_INFORMATION();

        string cmdLine = "\"" + wallpaperExe + "\" \"" + wallpaperUrl + "\"";
        log("CreateProcessAsUser: " + cmdLine);

        bool created = CreateProcessAsUser(primaryToken, null, cmdLine, IntPtr.Zero,
            IntPtr.Zero, false, CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
            env, @"C:\Windows\Web\MiOS", ref si, out pi);

        int createErr = Marshal.GetLastWin32Error();
        log("CreateProcessAsUser: " + created + " err=" + createErr + " PID=" + pi.dwProcessId);

        if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
        if (pi.hProcess != IntPtr.Zero) CloseHandle(pi.hProcess);
        if (pi.hThread != IntPtr.Zero) CloseHandle(pi.hThread);
        CloseHandle(primaryToken);
        CloseHandle(explorerToken);
        CloseHandle(explorerHandle);
    }
}
