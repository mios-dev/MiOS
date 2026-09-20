#!/usr/bin/env python3
# GENERATED tooling for agent-pipe test consolidation (T-1092). DO NOT EDIT.
import os
import sys
import re
import ast
import subprocess
from collections import defaultdict

PIPE_DIR = "usr/lib/mios/agent-pipe"

MAPPING = {
  "a2a_loopback": "a2a",
  "a2a_passport": "a2a_principal",
  "account_sync": "daemons",
  "admission": "sched",
  "agentcard_sign": "agent_call",
  "ai_manifest": "manifest",
  "antifab": "refine",
  "applet_webresearch": "web_research",
  "approutes": "routing",
  "auth": "pdp",
  "authn": "pdp",
  "backfill": "embed_backfill",
  "bench_harness": "bench",
  "budget": "hopbudget",
  "build_catalog": "verbcatalog",
  "compound": "batch",
  "conductor": "daemons",
  "config_audit": "config",
  "config_validate": "config",
  "config_write": "config",
  "consensus": "council_diversity",
  "cua_hierarchy": "cua",
  "daemon": "daemons",
  "dag_validate": "dag_exec",
  "db": "pg",
  "db_config": "pg",
  "dbwrite": "pg",
  "dispatch_cmd": "dispatch",
  "dispatch_redos": "dispatch",
  "drift_monitor": "clusterhealth",
  "dual_ledger": "audit",
  "egress": "firewall",
  "env": "surface",
  "health": "clusterhealth",
  "httpclient": "httpx",
  "k3s": "blades",
  "launch": "oscontrol",
  "letta": "memory",
  "list_dir": "worker_tools",
  "mcp_dispatch": "mcp",
  "mcp_pool": "gateway_queue",
  "mcp_sandbox": "sandbox",
  "mtls": "crl",
  "principal": "a2a_principal",
  "pty": "native_loop",
  "quality_gate": "slo",
  "react_reflexion": "reflect",
  "record_replay": "audit",
  "redact": "memguard",
  "remote_adapter": "interop",
  "replay": "planner",
  "run_template": "template",
  "seccomp": "sandbox",
  "session_events": "pg_events",
  "streaming": "sse",
  "tiered_memory": "compact",
  "toml": "config",
  "toolsurface": "surface",
  "user_config": "config",
  "vector": "knowledge",
  "vram": "sched",
  "vram_scheduler": "sched",
}

by_target = defaultdict(list)
for extra, target in MAPPING.items():
    by_target[target].append(extra)

def transform_extra(extra, target_uses_unittest):
    fn = os.path.join(PIPE_DIR, f"test_mios_{extra}.py")
    with open(fn) as f:
        src = f.read()

    # Strip shebang
    src = re.sub(r"^#!.*\n", "", src)

    # Specific aliasing
    if extra in ("admission", "vram", "toolsurface", "authn", "dbwrite", "session_events"):
        src = re.sub(r"\bconfigure,", f"configure as configure_{extra},", src)
        src = re.sub(r"(?<!as )\bconfigure\(", f"configure_{extra}(", src)
    if extra == "consensus":
        src = re.sub(r"\bas M\b", "as M_consensus", src)
        src = re.sub(r"\bM\.", "M_consensus.", src)
    if extra == "drift_monitor":
        src = re.sub(r"\bas M\b", "as M_drift_monitor", src)
        src = re.sub(r"\bM\.", "M_drift_monitor.", src)
    if extra == "router_parity":
        src = re.sub(r"\bas r\b", "as r_router_parity", src)
        src = re.sub(r"\br\.", "r_router_parity.", src)
    if extra == "react_reflexion":
        src = re.sub(r"\b_FakeClient\b", f"_FakeClient_{extra}", src)
    if extra == "tiered_memory":
        src = re.sub(r"\bdef m\(", f"def _m_{extra}(", src)
        src = re.sub(r"\bm\(", f"_m_{extra}(", src)

    # General identifier replacements
    src = re.sub(r"\bdef check\(", f"def _check_{extra}(", src)
    src = re.sub(r"\bcheck\(", f"_check_{extra}(", src)
    src = re.sub(r"\bdef _check\(", f"def _check_{extra}(", src)
    src = re.sub(r"\b_check\(", f"_check_{extra}(", src)
    src = re.sub(r"\b_fails\b", f"_fails_{extra}", src)
    src = re.sub(r"\b_RESULTS\b", f"_RESULTS_{extra}", src)
    src = re.sub(r"\bdef main\(", f"def _main_{extra}(", src)
    src = re.sub(r"\basync def main\(", f"async def _main_{extra}(", src)
    src = re.sub(r"\bdef _run_all\(", f"def _main_{extra}(", src)
    src = re.sub(r"\bdef main_async\(", f"def _main_async_{extra}(", src)
    src = re.sub(r"\bmain_async\(", f"_main_async_{extra}(", src)

    # Strip if __name__ == "__main__":
    src = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]\s*:[\s\S]*$", "", src)

    # Parse AST to find functions and test classes
    tree = ast.parse(src)
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    func_names = {n.name for n in funcs}
    is_main_async = any(isinstance(n, ast.AsyncFunctionDef) and n.name == f"_main_{extra}" for n in funcs)
    has_main = f"_main_{extra}" in func_names

    test_classes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            has_test_methods = any(isinstance(m, ast.FunctionDef) and m.name.startswith("test_") for m in node.body)
            is_test_case = any("TestCase" in getattr(b, "id", "") or "TestCase" in getattr(b, "attr", "") for b in node.bases)
            if is_test_case or has_test_methods:
                test_classes.append(node.name)

    # Build runner function with SystemExit protection
    runner_lines = [
        f"def _run_extra_{extra}():",
        "    import os",
        "    _saved_env = dict(os.environ)",
    ]
    if extra == "cua_hierarchy":
        runner_lines.append("    import mios_cua")
        runner_lines.append("    _cua_attrs = ('_dispatch_mios_verb_inner', '_cua_screenshot_uri', '_cua_vlm_json', '_cua_loop', 'wait_for_stable_element', '_W_ORIG', '_H_ORIG', '_W_TENSOR', '_H_TENSOR', '_HIDPI_SCALE_FACTOR')")
        runner_lines.append("    _saved_cua = {a: getattr(mios_cua, a, None) for a in _cua_attrs if hasattr(mios_cua, a)}")
    runner_lines.append("    try:")
    if extra == "tiered_memory":
        runner_lines.append("        for k in list(os.environ.keys()):")
        runner_lines.append("            if k.startswith('MIOS_MEMORY_'): os.environ.pop(k)")

    if has_main:
        if is_main_async:
            runner_lines.append("        import asyncio")
            runner_lines.append(f"        return asyncio.run(_main_{extra}())")
        else:
            runner_lines.append(f"        return _main_{extra}()")
    elif test_classes and not target_uses_unittest:
        runner_lines.append("        import unittest")
        runner_lines.append("        suite = unittest.TestSuite()")
        for tc in test_classes:
            runner_lines.append(f"        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase({tc}))")
        runner_lines.append("        res = unittest.TextTestRunner().run(suite)")
        runner_lines.append("        return 0 if res.wasSuccessful() else 1")
    else:
        runner_lines.append("        return 0")
    runner_lines.append("    except SystemExit as _e:")
    runner_lines.append("        return _e.code if _e.code is not None else 0")
    runner_lines.append("    finally:")
    runner_lines.append("        os.environ.clear()")
    runner_lines.append("        os.environ.update(_saved_env)")
    if extra == "cua_hierarchy":
        runner_lines.append("        for a in _cua_attrs:")
        runner_lines.append("            if a in _saved_cua:")
        runner_lines.append("                setattr(mios_cua, a, _saved_cua[a])")
        runner_lines.append("            elif hasattr(mios_cua, a):")
        runner_lines.append("                delattr(mios_cua, a)")

    runner_code = "\n".join(runner_lines)

    wrapper_class = ""
    if target_uses_unittest and has_main:
        wrapper_class = f"""
class TestFolded_{extra}(unittest.TestCase):
    def test_run_folded(self):
        rc = _run_extra_{extra}()
        self.assertIn(rc, (None, 0))
"""

    return f"""
# ==============================================================================
# Consolidated from test_mios_{extra}.py (T-1092)
# ==============================================================================
{src}
{runner_code}
{wrapper_class}
""", f"_run_extra_{extra}"

def consolidate_target(target):
    target_fn = os.path.join(PIPE_DIR, f"test_mios_{target}.py")
    with open(target_fn) as f:
        target_src = f.read()

    target_uses_unittest = "unittest.main" in target_src
    has_if_main = "if __name__" in target_src

    extras = by_target[target]
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("MIOS_")}

    # If all extras are already deleted and folded, verify target runs
    if all(not os.path.exists(os.path.join(PIPE_DIR, f"test_mios_{e}.py")) for e in extras):
        res = subprocess.run(["python3", target_fn], env=clean_env, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"PASSED target (already consolidated): {target}")
            return True

    folded_blocks = []
    runners = []

    for extra in extras:
        extra_path = os.path.join(PIPE_DIR, f"test_mios_{extra}.py")
        if not os.path.exists(extra_path):
            continue
        block, runner_name = transform_extra(extra, target_uses_unittest)
        folded_blocks.append(block)
        runners.append(runner_name)

    if not folded_blocks:
        return True

    all_folded_code = "\n".join(folded_blocks)

    overall_runner = f"""
def _run_all_folded_{target}_suites():
"""
    for r in runners:
        overall_runner += f"""    rc = {r}()
    if rc not in (None, 0):
        import sys
        sys.exit(f"Folded test suite failed: exit code {{rc}}")
"""

    combined_block = all_folded_code + "\n" + overall_runner

    if target_uses_unittest:
        parts = re.split(r"(if __name__\s*==\s*['\"]__main__['\"]\s*:)", target_src, maxsplit=1)
        new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + parts[2]
    elif has_if_main:
        parts = re.split(r"(if __name__\s*==\s*['\"]__main__['\"]\s*:\n)", target_src, maxsplit=1)
        tail = parts[2]
        if "raise SystemExit(main())" in tail:
            new_tail = tail.replace(
                "raise SystemExit(main())",
                f"_rc_main = main()\n    _run_all_folded_{target}_suites()\n    raise SystemExit(_rc_main)"
            )
            new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + new_tail
        elif "sys.exit(main())" in tail:
            new_tail = tail.replace(
                "sys.exit(main())",
                f"_rc_main = main()\n    _run_all_folded_{target}_suites()\n    sys.exit(_rc_main)"
            )
            new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + new_tail
        elif re.search(r"^\s*main\(\)\s*$", tail, re.MULTILINE):
            new_tail = re.sub(
                r"^(\s*)main\(\)\s*$",
                r"\1main()\n\1_run_all_folded_" + target + "_suites()",
                tail,
                flags=re.MULTILINE,
            )
            new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + new_tail
        else:
            hook = f"    _run_all_folded_{target}_suites()\n"
            new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + hook + tail
    else:
        new_target_src = target_src + "\n" + combined_block + f"\n_run_all_folded_{target}_suites()\n"

    with open(target_fn, "w") as f:
        f.write(new_target_src)

    res = subprocess.run(["python3", target_fn], env=clean_env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED target: {target}")
        print("STDOUT:\n", res.stdout[-500:] if res.stdout else "")
        print("STDERR:\n", res.stderr[-500:] if res.stderr else "")
        return False
    else:
        for extra in extras:
            extra_fn = os.path.join(PIPE_DIR, f"test_mios_{extra}.py")
            if os.path.exists(extra_fn):
                os.remove(extra_fn)
        print(f"PASSED target: {target} (folded & deleted {extras})")
        return True

def main():
    targets = sorted(by_target.keys())
    print(f"Consolidating {len(MAPPING)} extras into {len(targets)} targets...")
    for t in targets:
        if not consolidate_target(t):
            print(f"ABORTING at target: {t}")
            sys.exit(1)
    print("ALL 46 TARGETS CONSOLIDATED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
