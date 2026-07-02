#!/usr/bin/env /usr/lib/mios/agents/.venv/bin/python3
# AI-hint: Verification test suite for mios-bench harness CLI option parsing, metrics reporting, and table formatting.
# AI-related: /usr/lib/mios/agent-pipe/test_mios_bench_harness.py, /usr/libexec/mios/mios-bench

import sys
import os
import json
import subprocess
import time

# Resolve the mios-bench CLI relative to this test's location so the suite runs
# unchanged on the built image (/usr/...), a WSL checkout, or a Windows checkout
# -- no dev-host absolute path (Law 7: no SSOT-restated install-path literals).
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
MIOS_BENCH = os.path.join(_REPO, "usr", "libexec", "mios", "mios-bench")

_fails = 0

def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

def test_offline_score_table():
    # Write a temporary results file
    results = [
        {"task": "t1", "ok": True, "cost": 0.1, "latency_ms": 1500, "error": False, "security_violation": False},
        {"task": "t1", "ok": False, "cost": 0.2, "latency_ms": 2500, "error": False, "security_violation": False},
        {"task": "t2", "ok": True, "cost": 0.15, "latency_ms": 1000, "error": False, "security_violation": False}
    ]
    tmp_path = "/tmp/test_bench_results.json"
    with open(tmp_path, "w") as fh:
        json.dump({"results": results}, fh)
        
    try:
        # Run mios-bench score in a subprocess
        p = subprocess.Popen(
            [MIOS_BENCH, "score", tmp_path, "--k", "2"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = p.communicate()
        
        check("score command exit code is 0", p.returncode == 0)
        output_str = out.decode("utf-8")
        
        check("table has pass@1", "pass@1:" in output_str)
        check("table has pass@k", "pass@k:" in output_str)
        check("table has pass^k", "pass^k:" in output_str)
        check("table has throughput", "throughput:" in output_str)
        check("table has avg_wait", "avg_wait:" in output_str)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_run_command_suite_routing():
    # Create a small temp suite
    suite = [
        {"task": "addition", "prompt": "40+2", "expect": "42"}
    ]
    tmp_suite = "/tmp/test_bench_suite.json"
    with open(tmp_suite, "w") as fh:
        json.dump(suite, fh)
        
    # Start a mini local mock HTTP server
    import http.server
    import threading
    class MockHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "choices": [{"message": {"content": "The result of 40+2 is 42."}}]
            }).encode())
            
        def log_message(self, format, *args):
            pass  # Suppress logging noise
            
    server = http.server.HTTPServer(("127.0.0.1", 8699), MockHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    
    try:
        # Run run command
        p = subprocess.Popen(
            [MIOS_BENCH, "run", tmp_suite, "--endpoint", "http://127.0.0.1:8699/v1", "--k", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = p.communicate()
        check("run command exit code is 0", p.returncode == 0)
        output_str = out.decode("utf-8")
        check("results output has pass@1 == 1.0", "pass@1:     1.0000" in output_str)
    finally:
        server.shutdown()
        if os.path.exists(tmp_suite):
            os.remove(tmp_suite)

def main():
    test_offline_score_table()
    test_run_command_suite_routing()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0

if __name__ == "__main__":
    sys.exit(main())
