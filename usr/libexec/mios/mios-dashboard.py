#!/usr/bin/env python3
# AI-hint: MiOS live dashboard renderer
"""
MiOS Unified Live Dashboard & Monitor Renderer
High-performance, standalone Python rendering engine for MiOS system status,
container stack monitoring, and endpoint verification.
"""
import sys, os, glob, subprocess, socket, urllib.request, time

def probe_http(url, timeout=1.0):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MiOS-Probe"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 301, 302, 401, 403)
    except Exception:
        return False

def probe_tcp(host, port, timeout=0.8):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False

def render_dashboard(mode="full", no_color=False):
    c_grn = "" if no_color else "\033[32m"
    c_red = "" if no_color else "\033[31m"
    c_cyn = "" if no_color else "\033[36m"
    c_gry = "" if no_color else "\033[90m"
    c_b   = "" if no_color else "\033[1m"
    c_r   = "" if no_color else "\033[0m"

    dot_up = "*" if no_color else "●"
    dot_down = "-" if no_color else "○"

    # Services and containers definitions
    endpoints = [
        ("Agent-Pipe", "http://localhost:8640/v1", probe_http("http://localhost:8640/health")),
        ("WebUI", "http://localhost:8033/", probe_http("http://localhost:8033/")),
        ("Cockpit", "https://localhost:8090/", probe_http("https://localhost:8090/")),
        ("Bash-Term", "http://localhost:8681/", probe_tcp("127.0.0.1", 8681)),
        ("IDE / Code", "http://localhost:8800/", probe_http("http://localhost:8800/")),
        ("PS-Term", "http://localhost:8682/", probe_tcp("127.0.0.1", 8682)),
        ("Forge", "http://localhost:8300/", probe_http("http://localhost:8300/api/v1/version")),
        ("SSH", "port 57289", probe_tcp("127.0.0.1", 57289)),
    ]

    up_count = sum(1 for _, _, ok in endpoints if ok)
    down_count = len(endpoints) - up_count

    if mode == "mini":
        print(f"|   {c_grn}{dot_up}{c_r} {c_b}{up_count} up{c_r}    {c_gry}{dot_down} {down_count} down{c_r}    agent:8640  hermes:8643  llama:8450   |")
        print("|                                                                              |")
        for i in range(0, len(endpoints), 2):
            l_name, l_url, l_ok = endpoints[i]
            r_name, r_url, r_ok = endpoints[i+1]
            l_dot = f"{c_grn}{dot_up}{c_r}" if l_ok else f"{c_gry}{dot_down}{c_r}"
            r_dot = f"{c_grn}{dot_up}{c_r}" if r_ok else f"{c_gry}{dot_down}{c_r}"
            print(f"|   {l_dot} {l_name:<10} {l_url:<24} | {r_dot} {r_name:<10} {r_url:<22} |")
    else:
        # Full dashboard invocation
        cmd = ["/usr/libexec/mios/mios-dashboard.sh"] + sys.argv[1:]
        if os.path.exists(cmd[0]):
            os.execv(cmd[0], cmd)
        else:
            print(f"MiOS Dashboard Live: {up_count} up, {down_count} down")

def main():
    mode = "full"
    no_color = "--no-color" in sys.argv or not sys.stdout.isatty()
    if "--mini" in sys.argv:
        mode = "mini"
    elif "--services-only" in sys.argv:
        mode = "services-only"
    render_dashboard(mode, no_color)

if __name__ == "__main__":
    main()
