# AI-hint: Differential parity check asserting native mios-comment-lex binary and Python lexer produce identical sha12 sets.
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "usr", "lib", "mios"))

import mios_comments

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", _REPO_ROOT)
    native_bin = mios_comments._find_native_comment_lex()

    if not native_bin:
        print("[check-comment-lex] SKIPPED: mios-comment-lex binary not present (optional native tier)")
        sys.exit(0)

    print(f"[check-comment-lex] Testing differential equivalence using {native_bin}")

    mismatches = []
    files_tested = 0

    for rel, full in mios_comments.iter_source_files(root):
        if rel.endswith(".py"):
            continue  # Python files use AST docstring lexer in Python
        files_tested += 1

        # Python lexer pass (force raw reading)
        with open(full, "rb") as fh:
            raw = fh.read()
        py_blocks = mios_comments._lex_generic(
            full,
            raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n"),
            mios_comments._style_for(full),
        )
        py_hashes = sorted([b.sha12 for b in py_blocks])

        # Native lexer pass
        try:
            import json, subprocess
            proc = subprocess.run([native_bin, full], capture_output=True, check=True)
            records = json.loads(proc.stdout.decode("utf-8"))
            native_hashes = sorted([r["sha12"] for r in records])
        except Exception as exc:
            mismatches.append(f"{rel}: native lexer execution failed: {exc}")
            continue

        if py_hashes != native_hashes:
            mismatches.append(f"{rel}: py hashes {py_hashes} != native hashes {native_hashes}")

    print(f"[check-comment-lex] Tested {files_tested} non-python source files.")
    if mismatches:
        print(f"[check-comment-lex] ERROR: {len(mismatches)} file hash mismatches found:")
        for m in mismatches[:10]:
            print(f"  {m}")
        sys.exit(1)

    print("[check-comment-lex] SUCCESS: Python and native lexers are equivalent!")
    sys.exit(0)

if __name__ == "__main__":
    main()
