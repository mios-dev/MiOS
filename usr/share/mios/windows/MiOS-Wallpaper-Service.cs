using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.ServiceProcess;
using System.Text;
using System.Threading;
using Microsoft.Win32;

namespace MiOSWallpaperService
{
    public class WallpaperService : ServiceBase
    {
        private Thread _workerThread;
        private bool _stopping = false;
        private static readonly string LogPath = @"C:\Windows\Web\MiOS\mios_wallpaper_service.log";

        // ── Win32 P/Invokes ────────────────────────────────────────────────

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

        [DllImport("userenv.dll")]
        static extern bool DestroyEnvironmentBlock(IntPtr env);

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

        // ── Service Logic ──────────────────────────────────────────────────

        public static void Main(string[] args)
        {
            if (Environment.UserInteractive)
            {
                Console.WriteLine("MiOS Wallpaper Service running in debug mode. Press Ctrl+C to exit.");
                WallpaperService svc = new WallpaperService();
                svc.OnStart(args);
                Thread.Sleep(Timeout.Infinite);
            }
            else
            {
                ServiceBase.Run(new WallpaperService());
            }
        }

        public WallpaperService()
        {
            ServiceName = "MiOS-Wallpaper-Service";
            CanHandleSessionChangeEvent = true;
        }

        private static void Log(string msg)
        {
            try
            {
                File.AppendAllText(LogPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + msg + Environment.NewLine);
            }
            catch { }
            Console.WriteLine(msg);
        }

        protected override void OnStart(string[] args)
        {
            Log("Service starting...");
            _stopping = false;
            _workerThread = new Thread(WorkerLoop);
            _workerThread.IsBackground = true;
            _workerThread.Start();
            Log("Service started worker thread.");
        }

        protected override void OnStop()
        {
            Log("Service stopping...");
            _stopping = true;
            if (_workerThread != null && _workerThread.IsAlive)
            {
                _workerThread.Join(2000);
            }
            Log("Service stopped.");
        }

        private void WorkerLoop()
        {
            while (!_stopping)
            {
                try
                {
                    CheckAndLaunchWallpaper();
                }
                catch (Exception ex)
                {
                    Log("Exception in worker loop: " + ex.Message);
                }
                Thread.Sleep(5000); // Check every 5 seconds
            }
        }

        private void CheckAndLaunchWallpaper()
        {
            // Find all running explorer.exe processes (each represents an active user session)
            Process[] explorerProcs = Process.GetProcessesByName("explorer");
            Process[] wallpaperProcs = Process.GetProcessesByName("MiOS-Wallpaper");

            foreach (Process explorer in explorerProcs)
            {
                int sessionId = explorer.SessionId;

                // Skip session 0
                if (sessionId == 0) continue;

                // Check if MiOS-Wallpaper is running in this session
                bool isRunningInSession = false;
                foreach (Process wp in wallpaperProcs)
                {
                    if (wp.SessionId == sessionId)
                    {
                        isRunningInSession = true;
                        break;
                    }
                }

                if (!isRunningInSession)
                {
                    Log("MiOS-Wallpaper not running in Session " + sessionId + ". Launching...");
                    LaunchWallpaperInSession(explorer);
                }
            }
        }

        private void LaunchWallpaperInSession(Process explorerProcess)
        {
            int sessionId = explorerProcess.SessionId;
            IntPtr explorerHandle = IntPtr.Zero;
            IntPtr explorerToken = IntPtr.Zero;
            IntPtr primaryToken = IntPtr.Zero;
            IntPtr env = IntPtr.Zero;

            try
            {
                explorerHandle = OpenProcess(PROCESS_ALL_ACCESS, false, explorerProcess.Id);
                if (explorerHandle == IntPtr.Zero)
                {
                    Log("OpenProcess failed for explorer PID " + explorerProcess.Id + ": " + Marshal.GetLastWin32Error());
                    return;
                }

                if (!OpenProcessToken(explorerHandle, TOKEN_ALL_ACCESS, out explorerToken))
                {
                    Log("OpenProcessToken failed: " + Marshal.GetLastWin32Error());
                    return;
                }

                if (!DuplicateTokenEx(explorerToken, TOKEN_ALL_ACCESS, IntPtr.Zero,
                    SecurityImpersonation, TokenPrimary, out primaryToken))
                {
                    Log("DuplicateTokenEx failed: " + Marshal.GetLastWin32Error());
                    return;
                }

                // Read wallpaper URL from registry, fall back if not found
                string wallpaperUrl = GetWallpaperUrlFromRegistry();

                string wallpaperExe = @"C:\Windows\Web\MiOS\MiOS-Wallpaper.exe";
                if (!File.Exists(wallpaperExe))
                {
                    Log("Wallpaper executable not found: " + wallpaperExe);
                    return;
                }

                CreateEnvironmentBlock(out env, primaryToken, false);

                STARTUPINFO si = new STARTUPINFO();
                si.cb = Marshal.SizeOf(si);
                si.lpDesktop = "winsta0\\default";
                si.wShowWindow = 0; // Hidden window style for the host process container

                PROCESS_INFORMATION pi = new PROCESS_INFORMATION();

                string cmdLine = "\"" + wallpaperExe + "\" \"" + wallpaperUrl + "\"";
                bool created = CreateProcessAsUser(primaryToken, null, cmdLine, IntPtr.Zero,
                    IntPtr.Zero, false, CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
                    env, @"C:\Windows\Web\MiOS", ref si, out pi);

                int createErr = Marshal.GetLastWin32Error();
                if (created)
                {
                    Log("Successfully launched MiOS-Wallpaper.exe in Session " + sessionId + " (PID " + pi.dwProcessId + ")");
                    CloseHandle(pi.hProcess);
                    CloseHandle(pi.hThread);
                }
                else
                {
                    Log("CreateProcessAsUser failed for Session " + sessionId + ": " + createErr);
                }
            }
            catch (Exception ex)
            {
                Log("Error launching wallpaper in Session " + sessionId + ": " + ex.Message);
            }
            finally
            {
                if (env != IntPtr.Zero) DestroyEnvironmentBlock(env);
                if (primaryToken != IntPtr.Zero) CloseHandle(primaryToken);
                if (explorerToken != IntPtr.Zero) CloseHandle(explorerToken);
                if (explorerHandle != IntPtr.Zero) CloseHandle(explorerHandle);
            }
        }

        private string GetWallpaperUrlFromRegistry()
        {
            try
            {
                using (RegistryKey key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\MiOS"))
                {
                    if (key != null)
                    {
                        object val = key.GetValue("WallpaperUrl");
                        if (val != null)
                        {
                            return val.ToString();
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log("Failed to read WallpaperUrl from registry: " + ex.Message);
            }
            return "file:///C:/Windows/Web/MiOS/living-wallpaper.html";
        }
    }
}
