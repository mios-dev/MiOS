#!/usr/bin/env python3
# AI-hint: The three largest drift checks, lifted out of their shell heredocs so they can be imported, linted and tested.
# AI-related: automation/98-drift-checks.sh, usr/share/mios/mios.toml
"""Each subcommand is one check: it prints violations and exits non-zero.

They lived as heredocs inside the shell gate, where nothing could import or
lint them and a syntax error only surfaced when the check ran. The bodies are
unchanged -- only their container is.
"""
import sys


def check_doc_refs_resolve() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        sys.exit(0)

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    docs_cfg = data.get("docs") or {}
    max_stale = int(docs_cfg.get("max_stale_doc_refs", 0))
    allowlist = set(docs_cfg.get("ref_allowlist") or [])

    stale = []
    ref_re = re.compile(r'^\s*#\s*AI-(?:related|doc):\s*(.+)$|<!--\s*AI-(?:related|doc):\s*(.*?)\s*-->', re.MULTILINE)

    for rpath, _, files in os.walk(root):
        if any(skip in rpath for skip in ['.git', '.venv', '__pycache__', 'node_modules', 'vendored', 'output']):
            continue
        for fn in files:
            if not (fn.endswith('.py') or fn.endswith('.sh') or fn.endswith('.ps1') or fn.endswith('.md')):
                continue
            if fn in ('AGY-TASKS.md', 'TASKS.md', 'doc-generative-documentation.md', 'drift-gate-negatives.sh'):
                continue
            fpath = os.path.join(rpath, fn)
            dirpath = os.path.dirname(fpath)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as sfh:
                    text = sfh.read()
                for m in ref_re.finditer(text):
                    raw_line = m.group(1) or m.group(2) or ''
                    tokens = [t.strip().rstrip(',') for t in raw_line.split(',') if t.strip()]
                    for t in tokens:
                        t_clean = t.rstrip(',').strip()
                        t_clean = re.sub(r':\d+.*$', '', t_clean).strip()
                        t_clean = re.sub(r'\s*\([^)]*\)', '', t_clean).strip()
                        # "file.toml [section]" is a file + section, not a path.
                        t_clean = re.sub(r'\s*\[[^\]]*\]\s*$', '', t_clean).strip()
                        if not t_clean or any(al in t_clean for al in allowlist):
                            continue
                        if t_clean.startswith('[') or t_clean.startswith('@@') or t_clean.startswith('<'):
                            continue
                        if not ('/' in t_clean or t_clean.endswith(('.sh', '.py', '.toml', '.ps1', '.json', '.yaml', '.yml', '.md'))):
                            continue
                        if t_clean.startswith('/etc/') or t_clean.startswith('/var/') or t_clean.startswith('/tmp/') or t_clean.startswith('/proc/') or t_clean.startswith('/sys/') or t_clean.startswith('/run/'):
                            continue
                        if t_clean.startswith('http://') or t_clean.startswith('https://') or t_clean.startswith('localhost'):
                            continue

                        rel = t_clean.lstrip('/')
                        cands = [
                            os.path.normpath(os.path.join(dirpath, rel)),
                            os.path.normpath(os.path.join(os.path.dirname(dirpath), rel)),
                            os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(dirpath)), rel)),
                            os.path.normpath(os.path.join(root, 'usr/lib/mios/agent-pipe', rel)),
                            os.path.normpath(os.path.join(root, rel)),
                        ]
                        if not any(os.path.exists(c) for c in cands):
                            stale.append(f'{fn}: {t_clean}')
            except Exception:
                pass

    if len(stale) > max_stale:
        sys.stdout.write(f"    check_doc_refs_resolve: {len(stale)} stale reference(s) found (max allowed {max_stale}):\n")
        for s in stale[:10]:
            sys.stdout.write(f"      {s}\n")
        sys.exit(1)

    sys.exit(0)


def check_resolver_differential_parity() -> int:
    import os, sys, subprocess
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    _toml_data = tomllib.load(open(os.path.join(root, "usr/share/mios/mios.toml"), "rb"))
    resolver_bin = None

    for cand in [os.path.join(root, "tools/native/target", p, "mios-resolver" + x)
                 for p in ("debug", "release") for x in ("", ".exe")] + [
                 "/usr/libexec/mios/mios-resolver", "/usr/bin/mios-resolver"]:
        if os.path.isfile(cand):
            resolver_bin = cand
            break

    if not resolver_bin:
        # A silent skip is how a gate stays green while proving nothing. Where the
        # environment declares tools mandatory, an absent binary is a violation.
        if os.environ.get("MIOS_DRIFT_REQUIRE_TOOLS", "0") == "1":
            print("    mios-resolver is not built, so the Python/Rust resolvers were "
                  "never compared (MIOS_DRIFT_REQUIRE_TOOLS=1). Build it: "
                  "cd tools/native && cargo build -p mios-resolver", file=sys.stderr)
            sys.exit(1)
        print("    mios-resolver binary not built locally -- advisory skip")
        sys.exit(0)

    import importlib.util as _ilu  # the file is render-globals.py; the import name never resolved
    _sp = _ilu.spec_from_file_location("rg", os.path.join(root, "tools", "render-globals.py")); render_globals = _ilu.module_from_spec(_sp); _sp.loader.exec_module(render_globals)

    py_exports = render_globals.build_exports()

    try:
        res = subprocess.run([resolver_bin, "--emit=json"], capture_output=True, text=True, check=True)
        import json
        rs_exports = (_j := json.loads(res.stdout)).get("exports", _j)  # emit_json wraps: {merged, exports}
    except Exception as exc:
        print(f"    mios-resolver --emit=json execution failed: {exc}", file=sys.stderr)
        sys.exit(1)

    _rc = _toml_data.get("resolver") or {}; ceil_div = _rc.get("max_key_divergence")
    diff_keys = set(py_exports) ^ set(rs_exports)
    if ceil_div is None or len(diff_keys) > int(ceil_div):
        print(f"    key divergence {len(diff_keys)} vs ceiling {ceil_div}: {sorted(diff_keys)[:10]}", file=sys.stderr)
        sys.exit(1)

    mismatches = []
    for k in sorted(set(py_exports) & set(rs_exports)):
        v_py = str(py_exports[k])
        v_rs = str(rs_exports[k])
        if v_py != v_rs:
            mismatches.append(f"{k}: py='{v_py}' vs rs='{v_rs}'")

    ceil_val = _rc.get("max_value_divergence")
    if ceil_val is None or len(mismatches) > int(ceil_val):
        print(f"    value divergence {len(mismatches)} vs ceiling {ceil_val}:", file=sys.stderr)
        for m in mismatches[:10]:
            print(f"      {m}", file=sys.stderr)
        sys.exit(1)
    print(f"    resolver divergence: {len(diff_keys)}/{ceil_div} keys, {len(mismatches)}/{ceil_val} values (shrink-only; AGY-1676)", file=sys.stderr)

    print("    mios-resolver --emit=json matches Python SSOT render 100%")
    sys.exit(0)


def check_legibility_ratchet() -> int:
    import os, subprocess, sys
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        lim = (tomllib.load(fh).get("legibility") or {})
    if not lim:
        print("mios.toml [legibility] is absent -- the size of the deliverable is "
              "then bounded by nothing")
        sys.exit(1)

    try:
        rels = [r for r in subprocess.run(["git", "ls-files", "-z"], cwd=root,
                capture_output=True, check=True).stdout.decode("utf-8", "replace").split("\0") if r]
    except Exception as exc:
        sys.stderr.write("[legibility] not a work tree (%s); skipping\n" % exc)
        sys.exit(0)

    def lines(paths):
        n = 0
        for rel in paths:
            try:
                with open(os.path.join(root, rel.replace("/", os.sep)), "rb") as fh:
                    n += fh.read().count(b"\n")
            except OSError:
                pass
        return n

    nbytes = 0
    for rel in rels:
        try:
            nbytes += os.path.getsize(os.path.join(root, rel.replace("/", os.sep)))
        except OSError:
            pass

    measured = {
        "max_tracked_files": len(rels),
        "max_tracked_mb": round(nbytes / 1048576),
        "max_shell_lines": lines([r for r in rels if r.endswith((".sh", ".bash"))]),
        "max_ps_lines": lines([r for r in rels if r.endswith((".ps1", ".psm1"))]),
        "max_automation_phases": len([r for r in rels if r.startswith("automation/")
                                      and r.endswith(".sh") and r[11:13].isdigit()]),
        "max_libexec_verbs": len([r for r in rels if r.startswith("usr/libexec/mios/")
                                  and r.count("/") == 3]),
    }
    viol = []
    for k, got in sorted(measured.items()):
        cap = lim.get(k)
        if cap is None:
            continue
        if got > cap:
            viol.append("%s = %d, over the floor of %d. This ratchet only comes DOWN: "
                        "fold or delete, do not raise it." % (k.replace("max_", ""), got, cap))
    print("[legibility] " + "  ".join("%s=%d/%s" % (k.replace("max_", ""), v, lim.get(k, "-"))
                                      for k, v in sorted(measured.items())), file=sys.stderr)
    print("\n".join(viol))
    sys.exit(1 if viol else 0)


def check_no_inert_ssot_tables() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        sys.exit(0)

    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    inert = []
    for section in data.keys():
        pattern = re.compile(r'(\b' + re.escape(section) + r'\b|\[' + re.escape(section) + r'\]|MIOS_' + re.escape(section.upper()) + r')')
        found = False
        for rpath, _, files in os.walk(root):
            if any(skip in rpath for skip in ['.git', '.venv', '__pycache__', 'node_modules', 'vendored']):
                continue
            for fn in files:
                if fn == 'mios.toml' or not (fn.endswith('.py') or fn.endswith('.sh') or fn.endswith('.ps1') or fn.endswith('.md')):
                    continue
                fpath = os.path.join(rpath, fn)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as sfh:
                        if pattern.search(sfh.read()):
                            found = True
                            break
                except Exception:
                    pass
            if found:
                break
        if not found:
            inert.append(section)

    if inert:
        sys.stdout.write(f"Inert SSOT top-level table(s) found with zero consumers: {', '.join(inert)}\n")
        sys.exit(1)

    sys.exit(0)


def check_no_duplicate_value_key() -> int:
    """One value, one name, ratcheted against the baseline ledger.

    Lifted out of its heredoc in the shell gate: 211 lines that nothing
    could import or lint, where a syntax error surfaced only when the
    check ran.
    """
    import sys as _sys
    _sys.argv = [__file__] + _sys.argv[2:]
    import os
    import subprocess
    import sys

    snap_tool, baseline_path = sys.argv[1], sys.argv[2]
    BUMP = os.environ.get("MIOS_VALUE_DUP_BASELINE_BUMP", "0") == "1"

    # Well-known/protocol values only. A MiOS-allocated port must NOT be listed
    # here -- 8222 (the old ssh port) sat in this set and silently went dead when
    # [ports.categories] moved ssh, which is exactly how a stale exemption hides a
    # real duplicate.
    EXEMPT_VALUES = {"", "true", "false", "0", "1", "80", "443", "8080", "53", "22"}

    DEFAULT_HEADER = [
        "# value-dup-baseline.tsv -- ratcheted exemption ledger for",
        "# automation/98-drift-checks.sh::check_no_duplicate_value_key (WS-GUP AGY-1422).",
        "# Regenerate: MIOS_VALUE_DUP_BASELINE_BUMP=1 bash automation/98-drift-checks.sh check_no_duplicate_value_key",
        "# Format: value<TAB>key_count<TAB>comma-separated MIOS_* keys  (value escapes \\\\ \\t \\r)",
    ]


    def emit(msg):
        sys.stderr.write("    [value-dup-drift] " + msg + "\n")


    def esc(text):
        out = text.replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r")
        # A value may legitimately BE a comment -- systemd unit comments are
        # projected into MIOS_*_COMMENT keys -- so a leading "#" has to be escaped
        # or the writer emits 109 rows the reader then discards as comments, and
        # the ledger silently disagrees with the tree it was generated from.
        if out.startswith("#"):
            out = "\\#" + out[1:]
        return out


    def unesc(text):
        out = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\\" and i + 1 < len(text):
                nxt = text[i + 1]
                if nxt == "t":
                    out.append("\t")
                    i += 2
                    continue
                if nxt == "r":
                    out.append("\r")
                    i += 2
                    continue
                if nxt == "#":
                    out.append("#")
                    i += 2
                    continue
                if nxt == "\\":
                    out.append("\\")
                    i += 2
                    continue
            out.append(ch)
            i += 1
        return "".join(out)


    # --- resolve the live environment -------------------------------------------
    proc = subprocess.run(["bash", snap_tool], capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        emit("mios-env-snapshot exited %d -- the resolver produced no environment, so this gate has no data" % proc.returncode)
        for tail in (proc.stderr or "").strip().splitlines()[-5:]:
            emit("  snapshot stderr: " + tail)
        sys.exit(1)

    env = {}
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw.startswith("MIOS_") or "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        env[key] = val

    by_value = {}
    for key, val in env.items():
        by_value.setdefault(val, []).append(key)

    live = {}
    for val, keys in by_value.items():
        if len(keys) > 1 and val not in EXEMPT_VALUES:
            live[val] = sorted(keys)

    # --- regeneration -----------------------------------------------------------
    if BUMP:
        header = list(DEFAULT_HEADER)
        if os.path.isfile(baseline_path):
            header = []
            with open(baseline_path, encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.rstrip("\n")
                    if raw.startswith("#!"):
                        continue
                    if raw.startswith("#") or not raw.strip():
                        header.append(raw)
                    else:
                        break
        rows = []
        for val in sorted(live, key=lambda v: (-len(live[v]), v)):
            rows.append("%s\t%d\t%s" % (esc(val), len(live[val]), ",".join(live[val])))
        with open(baseline_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(header) + "\n")
            fh.write("#!ceiling\t%d\n" % len(live))
            fh.write("\n".join(rows) + "\n")
        emit("LEDGER REGENERATED from the live resolver: %d groups, ceiling %d (MIOS_VALUE_DUP_BASELINE_BUMP=1)" % (len(live), len(live)))
        emit("review the diff -- every row added here is a duplicate this gate will stop reporting")
        sys.exit(0)

    # --- read the ledger --------------------------------------------------------
    ceiling = None
    base = {}
    try:
        fh = open(baseline_path, encoding="utf-8")
    except OSError as exc:
        emit("ratchet ledger unreadable: %s" % exc)
        sys.exit(1)
    with fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.rstrip("\n")
            if raw.startswith("#!ceiling\t"):
                try:
                    ceiling = int(raw.split("\t", 1)[1].strip())
                except ValueError:
                    emit("ledger line %d: malformed #!ceiling directive" % lineno)
                    sys.exit(1)
                continue
            # Column 0 only: lstrip() here would swallow a data row whose VALUE
            # begins with whitespace and then a "#".
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) != 3:
                emit("ledger line %d: expected 3 tab-separated fields, found %d" % (lineno, len(parts)))
                sys.exit(1)
            try:
                declared = int(parts[1])
            except ValueError:
                emit("ledger line %d: key_count field is not an integer" % lineno)
                sys.exit(1)
            keys = [k for k in parts[2].split(",") if k]
            if declared != len(keys):
                emit("ledger line %d: key_count %d disagrees with the %d keys listed" % (lineno, declared, len(keys)))
                sys.exit(1)
            base[unesc(parts[0])] = sorted(keys)

    bad = 0
    CAP = 15

    # --- new groups: a value that duplicates and is not on the ledger ------------
    new_groups = sorted(v for v in live if v not in base)
    if new_groups:
        bad += 1
        for val in new_groups[:CAP]:
            emit("NEW duplicate-value group, not on the ratchet ledger: %r is shared by %s" % (val, ", ".join(live[val])))
        if len(new_groups) > CAP:
            emit("... and %d further new groups" % (len(new_groups) - CAP))

    # --- growth: a NEW key joining a group the ledger already tolerates ----------
    grown = []
    shrunk = []
    for val in sorted(live):
        if val not in base:
            continue
        added = sorted(set(live[val]) - set(base[val]))
        removed = sorted(set(base[val]) - set(live[val]))
        if added:
            grown.append((val, added))
        if removed:
            shrunk.append((val, removed))

    if grown:
        bad += 1
        for val, added in grown[:CAP]:
            emit("group %r GREW: %s now also resolve to it" % (val, ", ".join(added)))
        if len(grown) > CAP:
            emit("... and %d further grown groups" % (len(grown) - CAP))

    # --- shrinkage / disappearance: the ledger is stale and must be tightened ----
    gone = sorted(v for v in base if v not in live)
    if gone or shrunk:
        bad += 1
        for val in gone[:CAP]:
            emit("ledger records a group for %r that no longer exists -- tighten the ledger" % val)
        for val, removed in shrunk[:CAP]:
            emit("group %r SHRANK: %s no longer resolve to it -- tighten the ledger" % (val, ", ".join(removed)))
        if len(gone) + len(shrunk) > CAP:
            emit("... and %d further stale ledger rows" % (len(gone) + len(shrunk) - CAP))

    # --- the ceiling ------------------------------------------------------------
    if ceiling is None:
        bad += 1
        emit("ratchet ledger carries no #!ceiling directive -- a ratchet without a ceiling is not a ratchet")
    elif len(live) > ceiling:
        bad += 1
        emit("duplicate-value group count %d EXCEEDS the ratchet ceiling %d -- collapse the new duplicate instead of raising the ceiling" % (len(live), ceiling))
    elif len(live) < ceiling:
        bad += 1
        emit("duplicate-value group count %d is BELOW the ratchet ceiling %d -- lower the ceiling to %d so the progress is locked in" % (len(live), ceiling, len(live)))

    if bad:
        emit("resolver emitted %d MIOS_* keys forming %d non-exempt duplicate-value groups; ledger declares %s" % (len(env), len(live), ceiling))
        sys.exit(1)

    sys.stdout.write("%d groups at ceiling %d\n" % (len(live), ceiling))
    sys.exit(0)

SUBCOMMANDS = {
    "no-duplicate-value-key": check_no_duplicate_value_key,
    "no-inert-ssot-tables": check_no_inert_ssot_tables,
    "doc-refs-resolve": check_doc_refs_resolve,
    "resolver-differential-parity": check_resolver_differential_parity,
    "legibility-ratchet": check_legibility_ratchet,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in SUBCOMMANDS:
        print("usage: drift-checks.py {%s}" % "|".join(sorted(SUBCOMMANDS)),
              file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(SUBCOMMANDS[sys.argv[1]]() or 0)
