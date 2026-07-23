#!/usr/bin/env python3
# AI-hint: MiOS dashboard binary compiler
"""
MiOS Static Binary Dashboard Compiler
Compiles the unified Python live rendering system into a self-contained executable binary.
"""
import os, sys, shutil, zipapp, stat

def compile_binary():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    py_script = os.path.join(repo_root, "usr", "libexec", "mios", "mios-dashboard.py")
    target_bin = os.path.join(repo_root, "usr", "libexec", "mios", "mios-dashboard")
    staging_dir = os.path.join(repo_root, "tmp", "dashboard_build")

    try:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.makedirs(staging_dir, exist_ok=True)

        main_py = os.path.join(staging_dir, "__main__.py")
        shutil.copyfile(py_script, main_py)

        zipapp.create_archive(
            staging_dir,
            target_bin,
            interpreter="/usr/bin/env python3",
            compressed=True
        )

        # Ensure executable permissions (+x)
        st = os.stat(target_bin)
        os.chmod(target_bin, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[compile-dashboard] Compiled static dashboard binary: {target_bin}")
    finally:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir, ignore_errors=True)

if __name__ == "__main__":
    compile_binary()
