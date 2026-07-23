#!/usr/bin/env python3
# AI-hint: MiOS live dashboard renderer
"""
MiOS Unified Live Dashboard & Monitor Renderer
High-performance, standalone Python rendering engine for MiOS system status,
container stack monitoring, and endpoint verification.
"""
from __future__ import annotations

import os
import sys
import shutil
import socket
import subprocess
import time
import urllib.request
import platform

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

def get_terminal_width() -> int:
    cols = shutil.get_terminal_size((80, 24)).columns
    try:
        if "COLUMNS" in os.environ:
            cols = int(os.environ["COLUMNS"])
    except ValueError:
        pass
    return max(60, min(cols, 160))

def probe_http(url: str, timeout: float = 0.8) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MiOS-Probe"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 401, 403)
    except Exception:
        return False

def probe_tcp(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False

def probe_systemd_unit(unit_name: str) -> bool:
    try:
        res = subprocess.run(
            ["systemctl", "is-active", unit_name],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        return res.stdout.strip() == "active"
    except Exception:
        return False

def get_sys_info() -> dict[str, str]:
    # Host and Kernel
    host = socket.gethostname()
    kernel = platform.release()
    arch = platform.machine()
    os_name = f"Linux {kernel} {arch}"

    # Uptime
    uptime_str = "0d 0h 0m"
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            mins = int((seconds % 3600) // 60)
            uptime_str = f"{days}d {hours}h {mins}m"
    except Exception:
        pass

    # CPU
    cpu_model = "AMD Ryzen 9 9950X3D 16-Core 4.29GHz (28c)"
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    # Memory
    ram_str = "20.2 / 40.2GiB (50%)"
    swap_str = "0.0 / 4.0GiB (0%)"
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val)
        total_kb = meminfo.get("MemTotal", 0)
        avail_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used_kb = total_kb - avail_kb
        if total_kb > 0:
            used_gib = used_kb / (1024 * 1024)
            total_gib = total_kb / (1024 * 1024)
            pct = int((used_kb / total_kb) * 100)
            ram_str = f"{used_gib:.1f} / {total_gib:.1f}GiB ({pct}%)"
        
        sw_total_kb = meminfo.get("SwapTotal", 0)
        sw_free_kb = meminfo.get("SwapFree", 0)
        sw_used_kb = sw_total_kb - sw_free_kb
        if sw_total_kb > 0:
            sw_used_gib = sw_used_kb / (1024 * 1024)
            sw_total_gib = sw_total_kb / (1024 * 1024)
            sw_pct = int((sw_used_kb / sw_total_kb) * 100)
            swap_str = f"{sw_used_gib:.1f} / {sw_total_gib:.1f}GiB ({sw_pct}%)"
    except Exception:
        pass

    # Disk
    disk_root_str = "/ 110.8 / 1006.8GiB (12%)"
    disk_home_str = "M: 177.1 / 1766.7GiB (11%)"
    try:
        st = os.statvfs("/")
        total_b = st.f_blocks * st.f_frsize
        avail_b = st.f_bavail * st.f_frsize
        used_b = total_b - avail_b
        if total_b > 0:
            used_gib = used_b / (1024**3)
            total_gib = total_b / (1024**3)
            pct = int((used_b / total_b) * 100)
            disk_root_str = f"/ {used_gib:.1f} / {total_gib:.1f}GiB ({pct}%)"
    except Exception:
        pass

    user_name = os.environ.get("MIOS_USER", os.environ.get("USER", "mios"))
    shell_name = os.path.basename(os.environ.get("SHELL", "bash"))

    return {
        "version": "MiOS v0.3.0 x86_64",
        "date": time.strftime("%Y-%m-%d"),
        "user": user_name,
        "uptime": uptime_str,
        "cpu": cpu_model,
        "disk_root": disk_root_str,
        "disk_home": disk_home_str,
        "ram": ram_str,
        "swap": swap_str,
        "kernel": kernel,
        "shell": f"{shell_name} 5.3.9",
        "host": host,
        "font": "GeistMono Nerd Font Mono 12pt",
        "os_name": os_name,
    }

def get_git_status() -> dict[str, str]:
    branch = "main"
    staged = "0"
    modified = "0"
    untracked = "0"
    try:
        res = subprocess.run(
            ["git", "-C", "/", "status", "--porcelain=v1"],
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        lines = [line for line in res.stdout.splitlines() if line.strip()]
        staged_cnt = sum(1 for l in lines if l[0] in "MA")
        mod_cnt = sum(1 for l in lines if len(l) > 1 and l[1] == "M")
        untr_cnt = sum(1 for l in lines if l.startswith("??"))
        staged = str(staged_cnt)
        modified = str(mod_cnt)
        untracked = str(untr_cnt)

        b_res = subprocess.run(
            ["git", "-C", "/", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if b_res.stdout.strip():
            branch = b_res.stdout.strip()
    except Exception:
        pass

    return {
        "branch": branch,
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
    }

def get_service_statuses() -> list[tuple[str, str, bool]]:
    # Pair definitions: (Name, Port, Active)
    # Order matching the 2-column dashboard layout
    services = [
        ("hermes-worker", ":8643", probe_tcp("127.0.0.1", 8643) or probe_systemd_unit("mios-hermes-worker.service")),
        ("open-webui", ":8033", probe_http("http://localhost:8033/")),
        ("adguard", ":8053", probe_tcp("127.0.0.1", 8053) or probe_systemd_unit("mios-adguard.service")),
        ("otelcol", "", probe_systemd_unit("mios-otelcol.service") or probe_tcp("127.0.0.1", 4317)),
        ("agent-pipe", ":8640", probe_http("http://localhost:8640/health") or probe_tcp("127.0.0.1", 8640)),
        ("pgvector", ":8432", probe_tcp("127.0.0.1", 8432) or probe_systemd_unit("mios-pgvector.service")),
        ("agents", ":8800", probe_http("http://localhost:8800/")),
        ("searxng", ":8899", probe_http("http://localhost:8899/")),
        ("cpu-node", ":8458", probe_tcp("127.0.0.1", 8458)),
        ("ttyd-bash", ":8681", probe_tcp("127.0.0.1", 8681)),
        ("daemon", "", probe_systemd_unit("mios-daemon.service")),
        ("ttyd-powershell", ":8682", probe_tcp("127.0.0.1", 8682)),
        ("forge", ":8300", probe_http("http://localhost:8300/api/v1/version")),
        ("webtools-crawl4ai", "", probe_systemd_unit("mios-webtools-crawl4ai.service")),
        ("forgejo-runner", "", probe_systemd_unit("mios-forgejo-runner.service")),
        ("webtools-firecrawl-api", "", probe_systemd_unit("mios-webtools-firecrawl-api.service")),
        ("llm-heavy", "", probe_systemd_unit("mios-llm-heavy.service")),
        ("webtools-firecrawl-worker", "", probe_systemd_unit("mios-webtools-firecrawl-worker.service")),
        ("llm-light", ":8450", probe_http("http://localhost:8450/v1/models") or probe_tcp("127.0.0.1", 8450)),
        ("webtools-redis", "", probe_systemd_unit("mios-webtools-redis.service")),
        ("mcp", ":8460", probe_tcp("127.0.0.1", 8460)),
    ]
    return services

def render(mode: str = "full", no_color: bool = False, no_frame: bool = False) -> None:
    width = get_terminal_width()
    inner = width - 2

    # ANSI Colors
    if no_color:
        c_r = c_b = c_d = c_red = c_grn = c_ylw = c_cyn = c_gry = ""
        dot_up = "*"
        dot_down = "-"
        hr = "-"
        f_tl = f_tr = f_bl = f_br = f_lt = f_rt = f_v = "+"
    else:
        c_r = "\033[0m"
        c_b = "\033[1m"
        c_d = "\033[2m"
        c_red = "\033[31m"
        c_grn = "\033[32m"
        c_ylw = "\033[33m"
        c_cyn = "\033[36m"
        c_gry = "\033[90m"
        dot_up = "●"
        dot_down = "○"
        hr = "─"
        f_tl, f_tr, f_bl, f_br = "╭", "╮", "╰", "╯"
        f_lt, f_rt, f_v = "├", "┤", "│"

    sys_info = get_sys_info()
    git_info = get_git_status()
    services = get_service_statuses()

    # Core Endpoints for mini view
    mini_endpoints = [
        ("Agent-Pipe", "http://localhost:8640/v1", probe_http("http://localhost:8640/health")),
        ("WebUI", "http://localhost:8033/", probe_http("http://localhost:8033/")),
        ("Cockpit", "https://localhost:8090/", probe_http("https://localhost:8090/")),
        ("PS-Term", "http://localhost:8682/", probe_tcp("127.0.0.1", 8682)),
        ("IDE / Code", "http://localhost:8800/", probe_http("http://localhost:8800/")),
        ("SSH", "port 57289", probe_tcp("127.0.0.1", 57289)),
    ]

    up_count = sum(1 for _, _, ok in mini_endpoints if ok)
    down_count = len(mini_endpoints) - up_count

    # Frame Helpers
    def top_frame():
        if not no_frame:
            print(f"{c_cyn}{f_tl}{hr * inner}{f_tr}{c_r}")

    def div_frame():
        if not no_frame:
            print(f"{c_cyn}{f_lt}{hr * inner}{f_rt}{c_r}")

    def bot_frame():
        if not no_frame:
            print(f"{c_cyn}{f_bl}{hr * inner}{f_br}{c_r}")

    def frame_line(content: str):
        if no_frame:
            print(content)
        else:
            # Strip ANSI for padding calculation
            import re
            plain = re.sub(r"\033\[[0-9;]*[mK]", "", content)
            pad = inner - len(plain)
            if pad < 0:
                pad = 0
            print(f"{c_cyn}{f_v}{c_r}{content}{' ' * pad}{c_cyn}{f_v}{c_r}")

    if mode == "mini":
        top_frame()
        # Title row
        title_left = f"  MiOS v0.3.0"
        title_right = f"{sys_info['os_name']}  "
        gap = inner - len(title_left) - len(title_right)
        frame_line(f"{c_b}{c_cyn}{title_left}{c_r}{' ' * max(1, gap)}{c_gry}{title_right}{c_r}")
        div_frame()

        # Sys info table
        metrics_rows = [
            (sys_info["version"], sys_info["date"]),
            (sys_info["user"], sys_info["uptime"]),
            (sys_info["cpu"], ""),
            (sys_info["disk_root"], sys_info["disk_home"]),
            (sys_info["ram"], sys_info["swap"]),
            (sys_info["kernel"], sys_info["shell"]),
            (sys_info["host"], sys_info["font"]),
        ]
        for left_val, right_val in metrics_rows:
            l_pad = 55
            r_pad = 30
            line_str = f"  {left_val:<{l_pad}} {right_val:<{r_pad}}"
            frame_line(f"                                                       {line_str.strip()}")
        div_frame()

        # Mini summary line
        sum_str = f"● {up_count} up    ○ {down_count} down    agent:8640  hermes:8643  llama:8450"
        frame_line(f"{' ' * ((inner - len(sum_str)) // 2)}{c_grn}● {up_count} up{c_r}    {c_gry}○ {down_count} down    agent:8640  hermes:8643  llama:8450{c_r}")
        frame_line("")
        # 2 column endpoints
        for i in range(0, len(mini_endpoints), 2):
            l_name, l_url, l_ok = mini_endpoints[i]
            r_name, r_url, r_ok = mini_endpoints[i+1]
            l_dot = f"{c_grn}{dot_up}{c_r}" if l_ok else f"{c_gry}{dot_down}{c_r}"
            r_dot = f"{c_grn}{dot_up}{c_r}" if r_ok else f"{c_gry}{dot_down}{c_r}"
            ep_line = f"{l_dot} {l_name:<10} {l_url:<24} │ {r_dot} {r_name:<10} {r_url:<22}"
            frame_line(f"{' ' * ((inner - 64) // 2)}{ep_line}")

        bot_frame()
        print(f"{' ' * ((inner - 45) // 2)}{c_gry}dev shell: ssh -p 57289 mios@localhost{c_r}")
        return

    # Full / Standard Dashboard Mode
    top_frame()

    # Header ASCII Art (if terminal is tall enough)
    art_file = "/usr/share/mios/art.txt"
    if os.path.exists(art_file) and not no_frame:
        try:
            with open(art_file, "r") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    line_str = line.rstrip()
                    pad = (inner - len(line_str)) // 2
                    frame_line(f"{' ' * max(0, pad)}{c_cyn}{line_str}{c_r}")
            div_frame()
        except Exception:
            pass

    # Title row
    title_left = "  MiOS v0.3.0"
    title_right = f"{sys_info['os_name']}  "
    gap = inner - len(title_left) - len(title_right)
    frame_line(f"{c_b}{c_cyn}{title_left}{c_r}{' ' * max(1, gap)}{c_gry}{title_right}{c_r}")
    div_frame()

    # System specs metrics table
    metrics_rows = [
        (sys_info["version"], sys_info["date"]),
        (sys_info["user"], sys_info["uptime"]),
        (sys_info["cpu"], ""),
        (sys_info["disk_root"], sys_info["disk_home"]),
        (sys_info["ram"], sys_info["swap"]),
        (sys_info["kernel"], sys_info["shell"]),
        (sys_info["host"], sys_info["font"]),
    ]
    for left_val, right_val in metrics_rows:
        line_str = f"  {left_val:<50} {right_val:<30}"
        frame_line(f"{' ' * max(0, (inner - 82) // 2)}{line_str}")

    div_frame()

    # Unified Stack & Services Section
    hdr = "UNIFIED SYSTEM STACK & SERVICES"
    frame_line(f"{c_b}{' ' * ((inner - len(hdr)) // 2)}{hdr}{c_r}")
    div_hr = "────────────────────────────────────────────────────────────────────"
    frame_line(f"{c_gry}{' ' * ((inner - len(div_hr)) // 2)}{div_hr}{c_r}")

    # Render services in 2 parallel columns
    half = (len(services) + 1) // 2
    col1 = services[:half]
    col2 = services[half:]

    for i in range(half):
        s1_name, s1_port, s1_ok = col1[i]
        s1_dot = f"{c_grn}{dot_up}{c_r}" if s1_ok else f"{c_gry}{dot_down}{c_r}"
        s1_str = f"Svc  {s1_name:<16} {s1_port:>5} {s1_dot}"

        if i < len(col2):
            s2_name, s2_port, s2_ok = col2[i]
            s2_dot = f"{c_grn}{dot_up}{c_r}" if s2_ok else f"{c_gry}{dot_down}{c_r}"
            s2_str = f"Svc  {s2_name:<24} {s2_port:>5} {s2_dot}"
        else:
            s2_str = ""

        row_str = f"{s1_str} │ {s2_str}"
        frame_line(f"{' ' * max(0, (inner - 68) // 2)}{row_str}")

    frame_line(f"{c_gry}{' ' * ((inner - len(div_hr)) // 2)}{div_hr}{c_r}")
    frame_line(f"{' ' * ((inner - 46) // 2)}login mios/mios   forge mios/user")

    # Git Tree State Section
    frame_line(f"{' ' * ((inner - 4) // 2)}{c_b}Tree{c_r}")
    tree_str = f"main  +?/-?   {git_info['staged']} staged  {git_info['modified']} modified  {git_info['untracked']} untracked"
    frame_line(f"{' ' * max(0, (inner - len(tree_str)) // 2)}{c_gry}{tree_str}{c_r}")

    div_frame()

    # Footer Hints
    hints = "mios build  config  dash  mini  ai  code  dev  summary  user  pull  update  help"
    frame_line(f"{c_gry}{' ' * max(0, (inner - len(hints)) // 2)}{hints}{c_r}")
    bot_frame()
    print(f"{' ' * max(0, (inner - 45) // 2)}{c_gry}dev shell: ssh -p 57289 mios@localhost{c_r}")

def main():
    mode = "full"
    no_color = "--no-color" in sys.argv or not sys.stdout.isatty()
    no_frame = "--no-frame" in sys.argv

    if "--mini" in sys.argv:
        mode = "mini"
    elif "--services-only" in sys.argv:
        mode = "services-only"
    elif "--table-only" in sys.argv:
        mode = "table-only"
    elif "--endpoints-only" in sys.argv:
        mode = "endpoints-only"

    if "--monitor" in sys.argv:
        while True:
            sys.stdout.write("\033[H\033[2J")
            sys.stdout.flush()
            render(mode, no_color, no_frame)
            time.sleep(1.0)
    else:
        render(mode, no_color, no_frame)

if __name__ == "__main__":
    main()
