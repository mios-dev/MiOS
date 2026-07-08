using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.ServiceProcess;
using System.Text.RegularExpressions;

namespace MiosServiceTool
{
    public class Program : ServiceBase
    {
        private Process _process;
        private IntPtr _job;

        public static void Main(string[] args)
        {
            if (Environment.UserInteractive)
            {
                // Run mode: run a command hidden
                if (args.Length < 1)
                {
                    Console.WriteLine("MiOS Service & Run-Hidden Tool");
                    Console.WriteLine("Usage (hidden run): MiosServiceTool.exe -Run <exe> [args]");
                    return;
                }

                if (args[0].Equals("-Run", StringComparison.OrdinalIgnoreCase))
                {
                    if (args.Length < 2) return;
                    string targetExe = args[1];
                    string targetArgs = args.Length > 2 ? string.Join(" ", args, 2, args.Length - 2) : "";
                    
                    Process p = new Process();
                    p.StartInfo.FileName = targetExe;
                    p.StartInfo.Arguments = targetArgs;
                    p.StartInfo.UseShellExecute = false;
                    p.StartInfo.CreateNoWindow = true;
                    p.Start();
                }
            }
            else
            {
                // Service mode: run as a Windows Service
                ServiceBase.Run(new Program());
            }
        }

        protected override void OnStart(string[] args)
        {
            try
            {
                string exePath = Process.GetCurrentProcess().MainModule.FileName;
                string configPath = Path.ChangeExtension(exePath, ".cfg");
                if (!File.Exists(configPath))
                {
                    Log("Config file not found: " + configPath);
                    Stop();
                    return;
                }

                string[] lines = File.ReadAllLines(configPath);
                if (lines.Length < 2)
                {
                    Log("Invalid config file structure (requires at least 2 lines): " + configPath);
                    Stop();
                    return;
                }
                string path = lines[0].Trim();
                string arguments = lines[1].Trim();

                Log("Starting target: " + path + " " + arguments);

                // Create Job Object to manage child processes
                _job = CreateJobObject(IntPtr.Zero, null);
                JOBOBJECT_EXTENDED_LIMIT_INFORMATION info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
                info.BasicLimitInformation.LimitFlags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                IntPtr infoPtr = Marshal.AllocHGlobal(Marshal.SizeOf(info));
                Marshal.StructureToPtr(info, infoPtr, false);
                if (!SetInformationJobObject(_job, JobObjectInfoClass.JobObjectExtendedLimitInformation, infoPtr, Marshal.SizeOf(info)))
                {
                    Log("Failed to set Job Object limits");
                }
                Marshal.FreeHGlobal(infoPtr);

                _process = new Process();
                _process.StartInfo.FileName = path;
                _process.StartInfo.Arguments = arguments;
                _process.StartInfo.UseShellExecute = false;
                _process.StartInfo.CreateNoWindow = true;
                _process.Start();

                AssignProcessToJobObject(_job, _process.Handle);
            }
            catch (Exception ex)
            {
                Log("Error during startup: " + ex.ToString());
                Stop();
            }
        }

        protected override void OnStop()
        {
            Log("Stopping service...");
            if (_process != null && !_process.HasExited)
            {
                try { _process.Kill(); } catch {}
            }
            if (_job != IntPtr.Zero)
            {
                CloseHandle(_job);
            }
            Log("Service stopped.");
        }

        private string ExtractJsonValue(string json, string key)
        {
            var match = Regex.Match(json, "\"" + key + "\"\\s*:\\s*\"([^\"]+)\"");
            if (match.Success)
            {
                return match.Groups[1].Value.Replace("\\\\", "\\");
            }
            return "";
        }

        private void Log(string message)
        {
            try
            {
                string exePath = Process.GetCurrentProcess().MainModule.FileName;
                string logPath = Path.ChangeExtension(exePath, ".log");
                File.AppendAllText(logPath, "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + message + Environment.NewLine);
            }
            catch {}
        }

        #region Win32 API
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
        private static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

        [DllImport("kernel32.dll")]
        private static extern bool SetInformationJobObject(IntPtr hJob, JobObjectInfoClass JobObjectInfoClass, IntPtr lpJobObjectInfo, int cbJobObjectInfoLength);

        [DllImport("kernel32.dll")]
        private static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

        [DllImport("kernel32.dll")]
        private static extern bool CloseHandle(IntPtr hObject);

        private enum JobObjectInfoClass
        {
            JobObjectExtendedLimitInformation = 9
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
        {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct IO_COUNTERS
        {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        {
            public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
            public IO_COUNTERS IoInfo;
            public UIntPtr ProcessMemoryLimit;
            public UIntPtr JobMemoryLimit;
            public UIntPtr PeakProcessMemoryUsed;
            public UIntPtr PeakJobMemoryUsed;
        }
        #endregion
    }
}
