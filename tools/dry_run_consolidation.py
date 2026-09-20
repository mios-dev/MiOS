import os, sys, re, ast, subprocess

PIPE_DIR = "usr/lib/mios/agent-pipe"

MAPPING = {
  "a2a_loopback": "a2a",
  "compound": "batch",
  "agentcard_sign": "agent_call",
  "admission": "sched",
  "vram": "sched",
  "vram_scheduler": "sched",
  "config_audit": "config",
  "config_validate": "config",
  "config_write": "config",
  "toml": "config",
  "user_config": "config",
}

from collections import defaultdict
by_target = defaultdict(list)
for extra, target in MAPPING.items():
    by_target[target].append(extra)

def transform_extra(extra, target_uses_unittest):
    fn = os.path.join(PIPE_DIR, f"test_mios_{extra}.py")
    with open(fn) as f:
        src = f.read()

    # Strip shebang
    src = re.sub(r"^#!.*\n", "", src)

    # Identifiers
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
    if extra == "react_reflexion":
        src = re.sub(r"\b_FakeClient\b", f"_FakeClient_{extra}", src)
    if extra == "tiered_memory":
        src = re.sub(r"\bdef m\(", f"def _m_{extra}(", src)
        src = re.sub(r"\bm\(", f"_m_{extra}(", src)

    # Strip if __name__ == "__main__":
    src = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]\s*:[\s\S]*$", "", src)

    # Parse AST
    tree = ast.parse(src)
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    func_names = {n.name for n in funcs}
    is_main_async = any(isinstance(n, ast.AsyncFunctionDef) and n.name == f"_main_{extra}" for n in funcs)
    has_main = f"_main_{extra}" in func_names

    test_classes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # check if base is TestCase or has test_ methods
            has_test_methods = any(isinstance(m, ast.FunctionDef) and m.name.startswith("test_") for m in node.body)
            is_test_case = any("TestCase" in getattr(b, "id", "") or "TestCase" in getattr(b, "attr", "") for b in node.bases)
            if is_test_case or has_test_methods:
                test_classes.append(node.name)

    # Build runner function
    runner_lines = [f"def _run_extra_{extra}():"]
    if has_main:
        if is_main_async:
            runner_lines.append(f"    import asyncio")
            runner_lines.append(f"    return asyncio.run(_main_{extra}())")
        else:
            runner_lines.append(f"    return _main_{extra}()")
    elif test_classes and not target_uses_unittest:
        runner_lines.append(f"    import unittest")
        runner_lines.append(f"    suite = unittest.TestSuite()")
        for tc in test_classes:
            runner_lines.append(f"    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase({tc}))")
        runner_lines.append(f"    res = unittest.TextTestRunner().run(suite)")
        runner_lines.append(f"    return 0 if res.wasSuccessful() else 1")
    else:
        runner_lines.append(f"    return 0")

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
    folded_blocks = []
    runners = []

    for extra in extras:
        block, runner_name = transform_extra(extra, target_uses_unittest)
        folded_blocks.append(block)
        runners.append(runner_name)

    all_folded_code = "\n".join(folded_blocks)

    # Build overall runner
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
        # Insert before if __name__
        parts = re.split(r"(if __name__\s*==\s*['\"]__main__['\"]\s*:)", target_src, maxsplit=1)
        new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + parts[2]
    elif has_if_main:
        # Insert before if __name__, and inside __main__ call _run_all_folded
        parts = re.split(r"(if __name__\s*==\s*['\"]__main__['\"]\s*:\n)", target_src, maxsplit=1)
        hook = f"    _run_all_folded_{target}_suites()\n"
        new_target_src = parts[0] + "\n" + combined_block + "\n" + parts[1] + hook + parts[2]
    else:
        # Append at end and call
        new_target_src = target_src + "\n" + combined_block + f"\n_run_all_folded_{target}_suites()\n"

    # Write and test
    with open(target_fn, "w") as f:
        f.write(new_target_src)

    res = subprocess.run(["python3", target_fn], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED target: {target}")
        print("STDOUT:\n", res.stdout[-500:] if res.stdout else "")
        print("STDERR:\n", res.stderr[-500:] if res.stderr else "")
        return False
    else:
        print(f"PASSED target: {target} (folded {extras})")
        return True

for t in sorted(by_target.keys()):
    ok = consolidate_target(t)
    if not ok:
        sys.exit(1)
print("All sample targets passed!")
