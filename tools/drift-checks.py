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
    md_link_re = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    for rpath, _, files in os.walk(root):
        if any(skip in rpath for skip in ['.git', '.venv', '__pycache__', 'node_modules', 'vendored', 'output', '.rustup', '.cargo']):
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
                if fn.endswith('.md'):
                    for m in md_link_re.finditer(text):
                        target = m.group(2).split('#')[0].strip()
                        if not target or target.startswith(('http://', 'https://', 'mailto:', '#', 'file://')):
                            continue
                        if not (target.endswith(('.md', '.sh', '.py', '.toml', '.json', '.txt', '.png', '.svg', '.jpg')) or '/' in target):
                            continue
                        rel = target.lstrip('/')
                        cands = [
                            os.path.normpath(os.path.join(dirpath, rel)),
                            os.path.normpath(os.path.join(os.path.dirname(dirpath), rel)),
                            os.path.normpath(os.path.join(root, rel)),
                        ]
                        if not any(os.path.exists(c) for c in cands):
                            stale.append(f'{fn}: {target}')
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
    import os as _os
    import sys as _sys
    # Callable with no arguments: a caller that omits them gets the shipped
    # paths rather than an IndexError, which is what a bare invocation raised.
    _rest = _sys.argv[2:]
    if len(_rest) < 2:
        _root = (_os.environ.get("MIOS_DRIFT_ROOT")
                 or _os.environ.get("MIOS_ROOT") or _os.getcwd())
        _rest = [_os.path.join(_root, "usr/libexec/mios/mios-env-snapshot"),
                 _os.path.join(_root, "usr/share/mios/reference/value-dup-baseline.tsv")]
    _sys.argv = [__file__] + _rest
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
    # Git Bash cannot resolve an absolute path given as a script argument when
    # bash.exe is launched from Windows Python: both C:/MiOS/... and /c/MiOS/...
    # exit 127 "No such file", because /c is resolved against the MSYS root
    # rather than the drive. The same file runs when passed RELATIVE to a cwd.
    # The gate passes an absolute $ROOT, so on Windows this check reported "the
    # resolver produced no environment" -- a gate that could not run at all,
    # rather than one that passed or failed.
    _cwd = os.path.dirname(os.path.abspath(snap_tool)) or None
    _snap = os.path.basename(snap_tool)
    proc = subprocess.run(["bash", _snap], capture_output=True, text=True,
                          errors="replace", cwd=_cwd)
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

    # Two spellings of ONE key are not two keys. The resolver emits an aliased
    # name beside the walked name -- MIOS_CODEMODE_SOCKET and
    # MIOS_CODE_MODE_SOCKET are one declaration -- so counting them as a
    # collision made every new key in an aliased table breach the ratchet, which
    # would have forced the ceiling up for a duplicate that is not one.
    def _shape(name):
        return name.replace("_", "")

    live = {}
    for val, keys in by_value.items():
        if val in EXEMPT_VALUES:
            continue
        if len({_shape(k) for k in keys}) > 1:
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

def check_unwired_modules() -> int:
    """An agent-pipe module imported but never called by a non-test caller.

    Lifted out of its shell heredoc so it can be imported, linted and tested;
    inside one, a syntax error surfaces only when the check runs.
    """
    import os, sys, ast
    root = os.environ["MIOS_DRIFT_ROOT"]
    pipe = os.path.join(root, "usr/lib/mios/agent-pipe")
    if not os.path.isdir(pipe):
        if os.environ.get("MIOS_DRIFT_REQUIRE_TOOLS") == "1":
            sys.stderr.write(f"FAIL: agent-pipe directory missing at {pipe} (MIOS_DRIFT_REQUIRE_TOOLS=1)\n")
            sys.exit(1)
        sys.exit(0)  # nothing to check on a bare checkout

    import tomllib as _toml
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        _data = _toml.load(fh)
    ALLOW = set(_data.get("drift", {}).get("denylist", []))

    def is_test(path):
        b = os.path.basename(path)
        if b.startswith("test_") or b.endswith("_test.py"):
            return True
        segs = path.replace("\\", "/").split("/")
        return "tests" in segs or "test" in segs

    pipe_py = []
    for dp, _dn, files in os.walk(pipe):
        for f in files:
            if f.endswith(".py") and not is_test(os.path.join(dp, f)):
                pipe_py.append(os.path.join(dp, f))
    ref_py = list(pipe_py)
    for sub in ("usr/libexec/mios", "tools"):
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dp, _dn, files in os.walk(base):
            for f in files:
                if f.endswith(".py") and not is_test(os.path.join(dp, f)):
                    ref_py.append(os.path.join(dp, f))

    modules = sorted(f[:-3] for f in os.listdir(pipe)
                     if f.startswith("mios_") and f.endswith(".py")
                     and not is_test(os.path.join(pipe, f)))

    def parse(p):
        try:
            return ast.parse(open(p, encoding="utf-8").read())
        except Exception:
            return None

    pipe_trees = {p: parse(p) for p in pipe_py}
    ref_trees = {p: parse(p) for p in ref_py}

    def binds(tree, mod):
        """Names this tree binds for `mod`: (import-aliases, from-names, star?)."""
        al, fr, star = set(), set(), False
        if tree is None:
            return al, fr, star
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name == mod:
                        al.add(a.asname or a.name)
            elif isinstance(n, ast.ImportFrom):
                if n.module == mod and (n.level or 0) == 0:
                    for a in n.names:
                        if a.name == "*":
                            star = True
                        else:
                            fr.add(a.asname or a.name)
        return al, fr, star

    def uses(tree, names):
        """True if tree references a bound name. Imports bind via alias nodes, not
        ast.Name, so any ast.Name match is a genuine (non-import) reference."""
        if tree is None or not names:
            return False
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id in names:
                return True
        return False

    dead = set()
    for mod in modules:
        mf = os.path.abspath(os.path.join(pipe, mod + ".py"))
        imported = False
        for p, t in pipe_trees.items():
            if os.path.abspath(p) == mf:
                continue
            al, fr, star = binds(t, mod)
            if al or fr or star:
                imported = True
                break
        if not imported:
            continue  # never imported by the core -> not the imported-but-dead class
        wired = False
        for p, t in ref_trees.items():
            if os.path.abspath(p) == mf:
                continue
            al, fr, star = binds(t, mod)
            if star:
                wired = True
                break
            if (al or fr) and uses(t, al | fr):
                wired = True
                break
        if not wired:
            dead.add(mod)

    new_dead = sorted(dead - ALLOW)   # NEW imported-but-dead module -> fail
    stale = sorted(ALLOW - dead)      # allowlisted but now wired/removed -> fail
    for m in new_dead:
        sys.stderr.write(f"    {m}: imported by agent-pipe but no real (non-test) call site "
                         "-- wire it (give it a caller) or add it to _UNWIRED_ALLOW with a register note\n")
    for m in stale:
        sys.stderr.write(f"    {m}: listed in _UNWIRED_ALLOW but now WIRED or removed "
                         "-- delete it from the allowlist (A1 register self-cleans)\n")
    sys.exit(1 if (new_dead or stale) else 0)


def check_header_integrity() -> int:
    """A header tagger must never consume line 1 (AGY-1607)."""
    import os, re, subprocess, sys

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    try:
        rels = [p for p in subprocess.run(["git", "ls-files", "-z"], cwd=root,
                capture_output=True, check=True).stdout.decode("utf-8", "replace").split("\0") if p]
    except Exception:
        sys.exit(0)

    ABSORBED_SHEBANG = re.compile(r"AI-hint:\s*!")
    ABSORBED_DIRECTIVE = re.compile(r"AI-hint:\s*(?:bash|sh|python3?|pwsh|zsh)?\s*MIOS_[A-Z_]+=")
    NUL = b"\x00"
    viol = []
    for rel in rels:
        p = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "rb") as fh:
                raw = fh.read(4096)
        except OSError:
            continue
        if NUL in raw:
            continue
        try:
            head = raw.decode("utf-8").splitlines()[:5]
        except UnicodeDecodeError:
            continue
        for ln in head:
            if ABSORBED_SHEBANG.search(ln):
                viol.append("%s: the shebang was absorbed into the AI-hint -- the file "
                            "has no interpreter line any more" % rel)
                break
            if ABSORBED_DIRECTIVE.search(ln):
                viol.append("%s: a MIOS_* build directive was folded into the AI-hint "
                            "instead of standing on its own line" % rel)
                break
    if viol:
        viol.append("A header tagger must never consume line 1. Restore the shebang "
                    "and the directive, then re-tag.")
    print("\n".join(viol))
    sys.exit(1 if viol else 0)


def check_drift_build_catalog() -> int:
    """Lifted out of a shell heredoc so it can be imported and linted."""
    import sys
    import os
    import json
    import collections
    import io
    import contextlib

    class MockCursor:
        def __init__(self, db_store):
            self.db_store = db_store
            self.results = []
            self.index = 0

        def execute(self, query, params=None):
            query_upper = " ".join(query.upper().split())

            if "INSERT INTO SYSTEM_CONFIG" in query_upper:
                pass
            elif "INSERT INTO CONFIG_KV" in query_upper:
                pass
            elif "INSERT INTO VERB" in query_upper:
                pass
            elif "TRUNCATE TABLE DOMAIN_VERB" in query_upper:
                pass
            elif "INSERT INTO DOMAIN_VERB" in query_upper:
                pass
            elif "SELECT 1 FROM VERB" in query_upper:
                self.results = []
                self.index = 0
            elif "INSERT INTO PACKAGE_SET" in query_upper:
                name, section, pkgs_json, enable, layer, base_image_ref = params
                self.db_store["package_set"][name] = {
                    "name": name,
                    "section": section,
                    "pkgs": pkgs_json,
                    "enable": enable,
                    "layer": layer,
                    "base_image_ref": base_image_ref
                }
            elif "INSERT INTO BUILD_PHASE" in query_upper:
                if len(params) == 3:
                    ordinal, script, deps_json = params
                    stage = "container"
                else:
                    script = params[0]
                    ordinal = None
                    stage = "firstboot"
                    deps_json = "[]"
                self.db_store["build_phase"][script] = {
                    "ordinal": ordinal,
                    "script": script,
                    "stage": stage,
                    "deps": deps_json
                }
            elif "INSERT INTO DEBLOAT_POLICY" in query_upper:
                name, policy_type, rules_json = params
                self.db_store["debloat_policy"][name] = {
                    "name": name,
                    "policy_type": policy_type,
                    "rules": rules_json
                }
            elif "INSERT INTO DEBLOAT_PROFILE" in query_upper:
                self.db_store["debloat_profile"]["default"] = {
                    "name": "default",
                    "description": "Default debloat profile"
                }
            elif "INSERT INTO PRESET" in query_upper:
                features_json = params[0]
                self.db_store["preset"]["default"] = {
                    "name": "default",
                    "description": "Default preset",
                    "features": features_json,
                    "debloat_profile_name": "default"
                }
            elif "SELECT NAME, SECTION, PKGS, ENABLE, LAYER, BASE_IMAGE_REF FROM PACKAGE_SET" in query_upper:
                rows = []
                for name in sorted(self.db_store["package_set"].keys()):
                    p = self.db_store["package_set"][name]
                    rows.append({
                        "name": p["name"],
                        "section": p["section"],
                        "pkgs": p["pkgs"],
                        "enable": p["enable"],
                        "layer": p["layer"],
                        "base_image_ref": p["base_image_ref"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT ORDINAL, SCRIPT, STAGE, DEPS FROM BUILD_PHASE" in query_upper:
                rows = []
                def sort_key(item):
                    o = item["ordinal"]
                    return (item["stage"], o if o is not None else 999999, item["script"])
                for script in sorted(self.db_store["build_phase"].keys()):
                    p = self.db_store["build_phase"][script]
                    rows.append(p)
                rows.sort(key=sort_key)
                self.results = [{
                    "ordinal": r["ordinal"],
                    "script": r["script"],
                    "stage": r["stage"],
                    "deps": r["deps"]
                } for r in rows]
                self.index = 0
            elif "SELECT NAME, POLICY_TYPE, RULES FROM DEBLOAT_POLICY" in query_upper:
                rows = []
                for name in sorted(self.db_store["debloat_policy"].keys()):
                    p = self.db_store["debloat_policy"][name]
                    rows.append({
                        "name": p["name"],
                        "policy_type": p["policy_type"],
                        "rules": p["rules"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT NAME, DESCRIPTION FROM DEBLOAT_PROFILE" in query_upper:
                rows = []
                for name in sorted(self.db_store["debloat_profile"].keys()):
                    p = self.db_store["debloat_profile"][name]
                    rows.append({
                        "name": p["name"],
                        "description": p["description"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT NAME, DESCRIPTION, FEATURES, DEBLOAT_PROFILE_NAME FROM PRESET" in query_upper:
                rows = []
                for name in sorted(self.db_store["preset"].keys()):
                    p = self.db_store["preset"][name]
                    rows.append({
                        "name": p["name"],
                        "description": p["description"],
                        "features": p["features"],
                        "debloat_profile_name": p["debloat_profile_name"]
                    })
                self.results = rows
                self.index = 0

        def fetchall(self):
            return self.results

        def fetchone(self):
            if self.index < len(self.results):
                r = self.results[self.index]
                self.index += 1
                return r
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        def __init__(self, db_store):
            self.db_store = db_store

        def cursor(self, row_factory=None):
            return MockCursor(self.db_store)

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockPsycopgModule:
        def __init__(self, db_store):
            self.db_store = db_store

        def connect(self, *args, **kwargs):
            return MockConnection(self.db_store)

    def check_roundtrip(root):
        db_store = {
            "package_set": {},
            "build_phase": {},
            "debloat_policy": {},
            "debloat_profile": {},
            "preset": {}
        }
        mock_psycopg = MockPsycopgModule(db_store)
        mock_psycopg.__path__ = []
        class DictRowMock:
            pass
        mock_psycopg.rows = DictRowMock()
        mock_psycopg.rows.dict_row = DictRowMock

        sys.modules["psycopg"] = mock_psycopg
        sys.modules["psycopg.rows"] = mock_psycopg.rows

        seed_path = os.path.join(root, "usr/libexec/mios/seed-db-config.py")
        os.environ["MIOS_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
        os.environ["MIOS_VENDOR_TOML"] = os.environ["MIOS_TOML"]

        seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                exec(f.read(), seed_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Seed script exited with code {e.code}")
                sys.exit(1)

        materialize_path = os.path.join(root, "usr/libexec/mios/materialize-build-ctx.py")
        temp_ctx_dir = "/tmp/mios-drift-ctx-test"
        os.makedirs(temp_ctx_dir, exist_ok=True)
        os.environ["MIOS_BUILD_CTX"] = temp_ctx_dir

        mat_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": materialize_path}
        try:
            with open(materialize_path, "r", encoding="utf-8") as f:
                exec(f.read(), mat_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Materialize script exited with code {e.code}")
                sys.exit(1)

        import tomllib

        with open(os.environ["MIOS_TOML"], "rb") as f:
            toml_data = tomllib.load(f)

        with open(os.path.join(temp_ctx_dir, "package_sets.json"), "r", encoding="utf-8") as f:
            mat_sets = json.load(f)

        orig_packages = toml_data.get("packages", {})
        for sec_name, sec_cfg in orig_packages.items():
            if sec_name == "sections" or not isinstance(sec_cfg, dict) or "pkgs" not in sec_cfg:
                continue
            mat_item = next((x for x in mat_sets if x["name"] == sec_name), None)
            if not mat_item:
                print(f"Drift: Package set '{sec_name}' missing in materialized output")
                sys.exit(1)
            orig_pkgs = sec_cfg.get("pkgs", [])
            mat_pkgs = mat_item["pkgs"]
            if orig_pkgs != mat_pkgs:
                print(f"Drift in package set '{sec_name}':")
                print(f"  Expected: {orig_pkgs}")
                print(f"  Got:      {mat_pkgs}")
                sys.exit(1)

            orig_enable = sec_cfg.get("enable", True)
            orig_layer = sec_cfg.get("layer", 0)
            orig_base_ref = sec_cfg.get("base_image_ref", "")
            orig_section = sec_cfg.get("section", "Misc")

            if (mat_item.get("enable", True) != orig_enable or
                mat_item.get("layer", 0) != orig_layer or
                mat_item.get("base_image_ref", "") != orig_base_ref or
                mat_item.get("section", "Misc") != orig_section):
                print(f"Drift in package set '{sec_name}' metadata:")
                print(f"  Expected: enable={orig_enable}, layer={orig_layer}, base={orig_base_ref}, section={orig_section}")
                print(f"  Got:      enable={mat_item.get('enable')}, layer={mat_item.get('layer')}, base={mat_item.get('base_image_ref')}, section={mat_item.get('section')}")
                sys.exit(1)

        with open(os.path.join(temp_ctx_dir, "build_phases.json"), "r", encoding="utf-8") as f:
            mat_phases = json.load(f)

        automation_dir = os.path.join(root, "automation")
        import re
        scripts = sorted([f for f in os.listdir(automation_dir) if re.match(r"^\d{2}-.*\.sh$", f)])

        prev_script = None
        for s in scripts:
            ordinal = int(s.split("-", 1)[0])
            expected_deps = [prev_script] if prev_script else []
            mat_item = next((x for x in mat_phases if x["script"] == s), None)
            if not mat_item:
                print(f"Drift: Build phase script '{s}' missing in materialized output")
                sys.exit(1)
            if mat_item["ordinal"] != ordinal or mat_item["deps"] != expected_deps or mat_item["stage"] != "container":
                print(f"Drift in build phase script '{s}':")
                print(f"  Expected: ordinal={ordinal}, stage=container, deps={expected_deps}")
                print(f"  Got:      ordinal={mat_item['ordinal']}, stage={mat_item['stage']}, deps={mat_item['deps']}")
                sys.exit(1)
            prev_script = s

        bootstrap_dir = os.path.abspath(os.path.join(root, "..", "mios-bootstrap", "src", "autounattend"))
        debloat_json_path = os.path.join(bootstrap_dir, "mios-debloat.json")
        features_txt_path = os.path.join(bootstrap_dir, "mios-xbox-features.txt")

        if os.path.isfile(debloat_json_path) or os.path.isfile(features_txt_path):
            with open(os.path.join(temp_ctx_dir, "debloat_profiles.json"), "r", encoding="utf-8") as f:
                mat_debloat = json.load(f)

            if os.path.isfile(debloat_json_path):
                with open(debloat_json_path, "r", encoding="utf-8") as f:
                    orig_debloat = json.load(f)
                for k, val in orig_debloat.items():
                    if k == "_comment" or not isinstance(val, list):
                        continue
                    mat_policy = next((x for x in mat_debloat["policies"] if x["name"] == k), None)
                    if not mat_policy:
                        print(f"Drift: Debloat policy '{k}' missing in materialized output")
                        sys.exit(1)
                    if mat_policy["rules"] != val:
                        print(f"Drift in debloat policy '{k}'")
                        sys.exit(1)

            if os.path.isfile(features_txt_path):
                with open(features_txt_path, "r", encoding="utf-8") as f:
                    orig_features = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                mat_preset = next((x for x in mat_debloat["presets"] if x["name"] == "default"), None)
                if not mat_preset:
                    print("Drift: Default preset missing in materialized output")
                    sys.exit(1)
                if mat_preset["features"] != orig_features:
                    print("Drift in preset features")
                    sys.exit(1)
                if mat_preset.get("debloat_profile_name") != "default":
                    print("Drift: Default preset debloat_profile_name is not 'default'")
                    sys.exit(1)

            mat_profile = next((x for x in mat_debloat["profiles"] if x["name"] == "default"), None)
            if not mat_profile:
                print("Drift: Default debloat profile missing in materialized output")
                sys.exit(1)
            if mat_profile.get("description") != "Default debloat profile":
                print("Drift: Default debloat profile description does not match")
                sys.exit(1)

        sys.exit(0)

    if __name__ == "__main__":
        check_roundtrip(os.environ["MIOS_DRIFT_ROOT"])

def check_drift_projection() -> int:
    """Lifted out of a shell heredoc so it can be imported and linted."""
    import sys
    import os
    import json
    import collections
    import io
    import contextlib

    class MockCursor:
        def __init__(self, db_store):
            self.db_store = db_store
            self.results = []
            self.index = 0

        def execute(self, query, params=None):
            query_upper = " ".join(query.upper().split())
            if "INSERT INTO SYSTEM_CONFIG" in query_upper:
                pass
            elif "INSERT INTO PACKAGE_SET" in query_upper:
                pass
            elif "INSERT INTO BUILD_PHASE" in query_upper:
                pass
            elif "INSERT INTO CONFIG_KV" in query_upper:
                if len(params) == 1:
                    val_json = params[0]
                    scope = "verbs"
                    key = "_defaults"
                    layer = 0
                else:
                    scope, key, val_json, desc = params
                    layer = 0
                self.db_store["config_kv"][(scope, key, layer)] = {
                    "scope": scope,
                    "key": key,
                    "value": json.loads(val_json) if isinstance(val_json, str) else val_json,
                    "layer": layer
                }
            elif "INSERT INTO VERB" in query_upper:
                name, sig, desc, tier, perm, cmd, params_json, section, examples_json, model_name, hidden, aliases_json, conflict_group, parallel_limit, max_result_chars = params
                self.db_store["verb"][name] = {
                    "name": name,
                    "sig": sig,
                    "desc_default": desc,
                    "tier": tier,
                    "permission": perm,
                    "cmd": cmd,
                    "params": json.loads(params_json) if isinstance(params_json, str) else params_json,
                    "section": section,
                    "examples": json.loads(examples_json) if isinstance(examples_json, str) else examples_json,
                    "model_name": model_name,
                    "hidden": hidden,
                    "aliases": json.loads(aliases_json) if isinstance(aliases_json, str) else aliases_json,
                    "conflict_group": conflict_group,
                    "parallel_limit": parallel_limit,
                    "max_result_chars": max_result_chars
                }
            elif "TRUNCATE TABLE DOMAIN_VERB" in query_upper:
                self.db_store["domain_verb"] = []
            elif "INSERT INTO DOMAIN_VERB" in query_upper:
                domain, verb_name, description = params
                self.db_store["domain_verb"].append({
                    "domain": domain,
                    "verb_name": verb_name,
                    "description": description
                })
            elif "SELECT 1 FROM VERB WHERE NAME =" in query_upper:
                name = params[0]
                if name in self.db_store["verb"]:
                    self.results = [(1,)]
                else:
                    self.results = []
                self.index = 0
            elif "SELECT SCOPE, KEY, VALUE FROM CONFIG_KV" in query_upper:
                rows = []
                for (scope, key, layer), item in sorted(self.db_store["config_kv"].items()):
                    if layer == 0 and scope != 'verbs':
                        rows.append((scope, key, item["value"]))
                self.results = rows
                self.index = 0
            elif "SELECT DOMAIN, DESCRIPTION, ARRAY_AGG(VERB_NAME" in query_upper or "SELECT DOMAIN, DESCRIPTION, ARRAY_AGG" in query_upper:
                by_domain = collections.defaultdict(list)
                descs = {}
                for item in self.db_store["domain_verb"]:
                    dom = item["domain"]
                    by_domain[dom].append(item["verb_name"])
                    descs[dom] = item["description"]

                rows = []
                for dom in sorted(by_domain.keys()):
                    rows.append((dom, descs[dom], sorted(by_domain[dom])))
                self.results = rows
                self.index = 0
            elif "SELECT VALUE FROM CONFIG_KV WHERE SCOPE = 'VERBS' AND KEY = '_DEFAULTS'" in query_upper:
                item = self.db_store["config_kv"].get(('verbs', '_defaults', 0))
                if item:
                    self.results = [(item["value"],)]
                else:
                    self.results = []
                self.index = 0
            elif "SELECT NAME, SIG, DESC_DEFAULT, TIER, PERMISSION, CMD, PARAMS" in query_upper:
                rows = []
                for name in sorted(self.db_store["verb"].keys()):
                    v = self.db_store["verb"][name]
                    rows.append((
                        v["name"], v["sig"], v["desc_default"], v["tier"], v["permission"], v["cmd"],
                        v["params"], v["section"], v["examples"], v["model_name"], v["hidden"],
                        v["aliases"], v["conflict_group"], v["parallel_limit"], v["max_result_chars"]
                    ))
                self.results = rows
                self.index = 0

        def fetchall(self):
            return self.results

        def fetchone(self):
            if self.index < len(self.results):
                r = self.results[self.index]
                self.index += 1
                return r
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        def __init__(self, db_store):
            self.db_store = db_store

        def cursor(self):
            return MockCursor(self.db_store)

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockPsycopgModule:
        def __init__(self, db_store):
            self.db_store = db_store

        def connect(self, *args, **kwargs):
            return MockConnection(self.db_store)

    def check_roundtrip(root):
        db_store = {
            "config_kv": {},
            "verb": {},
            "domain_verb": []
        }
        mock_psycopg = MockPsycopgModule(db_store)
        sys.modules["psycopg"] = mock_psycopg

        seed_path = os.path.join(root, "usr/libexec/mios/seed-db-config.py")
        os.environ["MIOS_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
        os.environ["MIOS_VENDOR_TOML"] = os.environ["MIOS_TOML"]

        seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                exec(f.read(), seed_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Seed script exited with code {e.code}")
                sys.exit(1)

        materialize_path = os.path.join(root, "usr/libexec/mios/materialize-config-toml.py")
        mat_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": materialize_path}

        stdout_capture = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_capture):
                with open(materialize_path, "r", encoding="utf-8") as f:
                    exec(f.read(), mat_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Materialize script exited with code {e.code}")
                sys.exit(1)

        materialized_toml_str = stdout_capture.getvalue()

        import tomllib

        with open(os.environ["MIOS_TOML"], "rb") as f:
            orig_data = tomllib.load(f)

        try:
            mat_data = tomllib.loads(materialized_toml_str)
        except Exception as parse_err:
            print("Materialized TOML parsing failed!")
            lines = materialized_toml_str.splitlines()
            import re as _re
            _m = _re.search(r"at line (\d+)", str(parse_err))
            _n = int(_m.group(1)) if _m else getattr(parse_err, "lineno", None)
            _lo = max(0, (_n - 4)) if _n else 29
            _hi = (_n + 3) if _n else 70
            print("Lines %d-%d:" % (_lo + 1, _hi))
            for i, l in enumerate(lines[_lo:_hi]):
                print(f"{_lo+i+1:4d}: {l}")
            raise parse_err

        scopes = ["ports", "ai", "routing", "pgvector", "a2a", "mcp", "observability", "sandbox", "security", "agent_passport", "agent_pipe"]
        for scope in scopes:
            orig_scope = orig_data.get(scope, {})
            mat_scope = mat_data.get(scope, {})

            if scope == "routing":
                orig_keys = {k: v for k, v in orig_scope.items() if k not in ("domains", "nohc_allowlist")}
                mat_keys = {k: v for k, v in mat_scope.items() if k not in ("domains", "nohc_allowlist")}
            else:
                orig_keys = orig_scope
                mat_keys = mat_scope

            if orig_keys != mat_keys:
                print(f"Drift in scope [{scope}]:")
                print(f"  Expected: {orig_keys}")
                print(f"  Got:      {mat_keys}")
                sys.exit(1)

        orig_domains = orig_data.get("routing", {}).get("domains", {})
        mat_domains = mat_data.get("routing", {}).get("domains", {})
        orig_domains_norm = {
            dom: {
                "desc": val.get("desc", ""),
                "verbs": sorted(val.get("verbs", []))
            }
            for dom, val in orig_domains.items()
        }
        mat_domains_norm = {
            dom: {
                "desc": val.get("desc", ""),
                "verbs": sorted(val.get("verbs", []))
            }
            for dom, val in mat_domains.items()
        }
        if orig_domains_norm != mat_domains_norm:
            print("Drift in routing.domains:")
            print(f"  Expected: {orig_domains_norm}")
            print(f"  Got:      {mat_domains_norm}")
            sys.exit(1)

        orig_verbs = orig_data.get("verbs", {})
        mat_verbs = mat_data.get("verbs", {})

        if orig_verbs.get("_defaults") != mat_verbs.get("_defaults"):
            print("Drift in verbs._defaults:")
            print(f"  Expected: {orig_verbs.get('_defaults')}")
            print(f"  Got:      {mat_verbs.get('_defaults')}")
            sys.exit(1)

        supported_verb_fields = {
            "sig", "desc", "tier", "permission", "cmd", "params",
            "section", "examples", "model_name", "hidden", "aliases",
            "conflict_group", "parallel_limit", "max_result_chars"
        }

        for vname, orig_vcfg in orig_verbs.items():
            if vname == "_defaults":
                continue
            if vname not in mat_verbs:
                print(f"Verb '{vname}' missing in materialized output")
                sys.exit(1)

            mat_vcfg = mat_verbs[vname]
            orig_defaults = orig_verbs.get("_defaults", {})
            mat_defaults = mat_verbs.get("_defaults", {})

            orig_full = orig_defaults.copy()
            orig_full.update(orig_vcfg)

            mat_full = mat_defaults.copy()
            mat_full.update(mat_vcfg)

            for key in supported_verb_fields:
                orig_val = orig_full.get(key)
                mat_val = mat_full.get(key)

                if key in ("sig", "desc", "cmd", "section", "model_name", "conflict_group"):
                    if orig_val == "": orig_val = None
                    if mat_val == "": mat_val = None
                elif key in ("examples", "aliases"):
                    if orig_val == []: orig_val = None
                    if mat_val == []: mat_val = None
                elif key == "params":
                    if orig_val == {}: orig_val = None
                    if mat_val == {}: mat_val = None
                elif key == "hidden":
                    orig_val = bool(orig_val)
                    mat_val = bool(mat_val)
                elif key in ("parallel_limit", "max_result_chars"):
                    orig_val = int(orig_val or 0)
                    mat_val = int(mat_val or 0)

                if orig_val != mat_val:
                    print(f"Drift in verb '{vname}' field '{key}':")
                    print(f"  Expected: {orig_val}")
                    print(f"  Got:      {mat_val}")
                    sys.exit(1)

        sys.exit(0)

    if __name__ == "__main__":
        check_roundtrip(os.environ["MIOS_DRIFT_ROOT"])

def check_drift_build_catalog() -> int:
    """Lifted out of a shell heredoc so it can be imported and linted."""
    import sys
    import os
    import json
    import collections
    import io
    import contextlib

    class MockCursor:
        def __init__(self, db_store):
            self.db_store = db_store
            self.results = []
            self.index = 0

        def execute(self, query, params=None):
            query_upper = " ".join(query.upper().split())

            if "INSERT INTO SYSTEM_CONFIG" in query_upper:
                pass
            elif "INSERT INTO CONFIG_KV" in query_upper:
                pass
            elif "INSERT INTO VERB" in query_upper:
                pass
            elif "TRUNCATE TABLE DOMAIN_VERB" in query_upper:
                pass
            elif "INSERT INTO DOMAIN_VERB" in query_upper:
                pass
            elif "SELECT 1 FROM VERB" in query_upper:
                self.results = []
                self.index = 0
            elif "INSERT INTO PACKAGE_SET" in query_upper:
                name, section, pkgs_json, enable, layer, base_image_ref = params
                self.db_store["package_set"][name] = {
                    "name": name,
                    "section": section,
                    "pkgs": pkgs_json,
                    "enable": enable,
                    "layer": layer,
                    "base_image_ref": base_image_ref
                }
            elif "INSERT INTO BUILD_PHASE" in query_upper:
                if len(params) == 3:
                    ordinal, script, deps_json = params
                    stage = "container"
                else:
                    script = params[0]
                    ordinal = None
                    stage = "firstboot"
                    deps_json = "[]"
                self.db_store["build_phase"][script] = {
                    "ordinal": ordinal,
                    "script": script,
                    "stage": stage,
                    "deps": deps_json
                }
            elif "INSERT INTO DEBLOAT_POLICY" in query_upper:
                name, policy_type, rules_json = params
                self.db_store["debloat_policy"][name] = {
                    "name": name,
                    "policy_type": policy_type,
                    "rules": rules_json
                }
            elif "INSERT INTO DEBLOAT_PROFILE" in query_upper:
                self.db_store["debloat_profile"]["default"] = {
                    "name": "default",
                    "description": "Default debloat profile"
                }
            elif "INSERT INTO PRESET" in query_upper:
                features_json = params[0]
                self.db_store["preset"]["default"] = {
                    "name": "default",
                    "description": "Default preset",
                    "features": features_json,
                    "debloat_profile_name": "default"
                }
            elif "SELECT NAME, SECTION, PKGS, ENABLE, LAYER, BASE_IMAGE_REF FROM PACKAGE_SET" in query_upper:
                rows = []
                for name in sorted(self.db_store["package_set"].keys()):
                    p = self.db_store["package_set"][name]
                    rows.append({
                        "name": p["name"],
                        "section": p["section"],
                        "pkgs": p["pkgs"],
                        "enable": p["enable"],
                        "layer": p["layer"],
                        "base_image_ref": p["base_image_ref"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT ORDINAL, SCRIPT, STAGE, DEPS FROM BUILD_PHASE" in query_upper:
                rows = []
                def sort_key(item):
                    o = item["ordinal"]
                    return (item["stage"], o if o is not None else 999999, item["script"])
                for script in sorted(self.db_store["build_phase"].keys()):
                    p = self.db_store["build_phase"][script]
                    rows.append(p)
                rows.sort(key=sort_key)
                self.results = [{
                    "ordinal": r["ordinal"],
                    "script": r["script"],
                    "stage": r["stage"],
                    "deps": r["deps"]
                } for r in rows]
                self.index = 0
            elif "SELECT NAME, POLICY_TYPE, RULES FROM DEBLOAT_POLICY" in query_upper:
                rows = []
                for name in sorted(self.db_store["debloat_policy"].keys()):
                    p = self.db_store["debloat_policy"][name]
                    rows.append({
                        "name": p["name"],
                        "policy_type": p["policy_type"],
                        "rules": p["rules"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT NAME, DESCRIPTION FROM DEBLOAT_PROFILE" in query_upper:
                rows = []
                for name in sorted(self.db_store["debloat_profile"].keys()):
                    p = self.db_store["debloat_profile"][name]
                    rows.append({
                        "name": p["name"],
                        "description": p["description"]
                    })
                self.results = rows
                self.index = 0
            elif "SELECT NAME, DESCRIPTION, FEATURES, DEBLOAT_PROFILE_NAME FROM PRESET" in query_upper:
                rows = []
                for name in sorted(self.db_store["preset"].keys()):
                    p = self.db_store["preset"][name]
                    rows.append({
                        "name": p["name"],
                        "description": p["description"],
                        "features": p["features"],
                        "debloat_profile_name": p["debloat_profile_name"]
                    })
                self.results = rows
                self.index = 0

        def fetchall(self):
            return self.results

        def fetchone(self):
            if self.index < len(self.results):
                r = self.results[self.index]
                self.index += 1
                return r
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        def __init__(self, db_store):
            self.db_store = db_store

        def cursor(self, row_factory=None):
            return MockCursor(self.db_store)

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockPsycopgModule:
        def __init__(self, db_store):
            self.db_store = db_store

        def connect(self, *args, **kwargs):
            return MockConnection(self.db_store)

    def check_roundtrip(root):
        db_store = {
            "package_set": {},
            "build_phase": {},
            "debloat_policy": {},
            "debloat_profile": {},
            "preset": {}
        }
        mock_psycopg = MockPsycopgModule(db_store)
        mock_psycopg.__path__ = []
        class DictRowMock:
            pass
        mock_psycopg.rows = DictRowMock()
        mock_psycopg.rows.dict_row = DictRowMock

        sys.modules["psycopg"] = mock_psycopg
        sys.modules["psycopg.rows"] = mock_psycopg.rows

        seed_path = os.path.join(root, "usr/libexec/mios/seed-db-config.py")
        os.environ["MIOS_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
        os.environ["MIOS_VENDOR_TOML"] = os.environ["MIOS_TOML"]

        seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                exec(f.read(), seed_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Seed script exited with code {e.code}")
                sys.exit(1)

        materialize_path = os.path.join(root, "usr/libexec/mios/materialize-build-ctx.py")
        temp_ctx_dir = "/tmp/mios-drift-ctx-test"
        os.makedirs(temp_ctx_dir, exist_ok=True)
        os.environ["MIOS_BUILD_CTX"] = temp_ctx_dir

        mat_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": materialize_path}
        try:
            with open(materialize_path, "r", encoding="utf-8") as f:
                exec(f.read(), mat_globals)
        except SystemExit as e:
            if e.code != 0:
                print(f"Materialize script exited with code {e.code}")
                sys.exit(1)

        import tomllib

        with open(os.environ["MIOS_TOML"], "rb") as f:
            toml_data = tomllib.load(f)

        with open(os.path.join(temp_ctx_dir, "package_sets.json"), "r", encoding="utf-8") as f:
            mat_sets = json.load(f)

        orig_packages = toml_data.get("packages", {})
        for sec_name, sec_cfg in orig_packages.items():
            if sec_name == "sections" or not isinstance(sec_cfg, dict) or "pkgs" not in sec_cfg:
                continue
            mat_item = next((x for x in mat_sets if x["name"] == sec_name), None)
            if not mat_item:
                print(f"Drift: Package set '{sec_name}' missing in materialized output")
                sys.exit(1)
            orig_pkgs = sec_cfg.get("pkgs", [])
            mat_pkgs = mat_item["pkgs"]
            if orig_pkgs != mat_pkgs:
                print(f"Drift in package set '{sec_name}':")
                print(f"  Expected: {orig_pkgs}")
                print(f"  Got:      {mat_pkgs}")
                sys.exit(1)

            orig_enable = sec_cfg.get("enable", True)
            orig_layer = sec_cfg.get("layer", 0)
            orig_base_ref = sec_cfg.get("base_image_ref", "")
            orig_section = sec_cfg.get("section", "Misc")

            if (mat_item.get("enable", True) != orig_enable or
                mat_item.get("layer", 0) != orig_layer or
                mat_item.get("base_image_ref", "") != orig_base_ref or
                mat_item.get("section", "Misc") != orig_section):
                print(f"Drift in package set '{sec_name}' metadata:")
                print(f"  Expected: enable={orig_enable}, layer={orig_layer}, base={orig_base_ref}, section={orig_section}")
                print(f"  Got:      enable={mat_item.get('enable')}, layer={mat_item.get('layer')}, base={mat_item.get('base_image_ref')}, section={mat_item.get('section')}")
                sys.exit(1)

        with open(os.path.join(temp_ctx_dir, "build_phases.json"), "r", encoding="utf-8") as f:
            mat_phases = json.load(f)

        automation_dir = os.path.join(root, "automation")
        import re
        scripts = sorted([f for f in os.listdir(automation_dir) if re.match(r"^\d{2}-.*\.sh$", f)])

        prev_script = None
        for s in scripts:
            ordinal = int(s.split("-", 1)[0])
            expected_deps = [prev_script] if prev_script else []
            mat_item = next((x for x in mat_phases if x["script"] == s), None)
            if not mat_item:
                print(f"Drift: Build phase script '{s}' missing in materialized output")
                sys.exit(1)
            if mat_item["ordinal"] != ordinal or mat_item["deps"] != expected_deps or mat_item["stage"] != "container":
                print(f"Drift in build phase script '{s}':")
                print(f"  Expected: ordinal={ordinal}, stage=container, deps={expected_deps}")
                print(f"  Got:      ordinal={mat_item['ordinal']}, stage={mat_item['stage']}, deps={mat_item['deps']}")
                sys.exit(1)
            prev_script = s

        bootstrap_dir = os.path.abspath(os.path.join(root, "..", "mios-bootstrap", "src", "autounattend"))
        debloat_json_path = os.path.join(bootstrap_dir, "mios-debloat.json")
        features_txt_path = os.path.join(bootstrap_dir, "mios-xbox-features.txt")

        if os.path.isfile(debloat_json_path) or os.path.isfile(features_txt_path):
            with open(os.path.join(temp_ctx_dir, "debloat_profiles.json"), "r", encoding="utf-8") as f:
                mat_debloat = json.load(f)

            if os.path.isfile(debloat_json_path):
                with open(debloat_json_path, "r", encoding="utf-8") as f:
                    orig_debloat = json.load(f)
                for k, val in orig_debloat.items():
                    if k == "_comment" or not isinstance(val, list):
                        continue
                    mat_policy = next((x for x in mat_debloat["policies"] if x["name"] == k), None)
                    if not mat_policy:
                        print(f"Drift: Debloat policy '{k}' missing in materialized output")
                        sys.exit(1)
                    if mat_policy["rules"] != val:
                        print(f"Drift in debloat policy '{k}'")
                        sys.exit(1)

            if os.path.isfile(features_txt_path):
                with open(features_txt_path, "r", encoding="utf-8") as f:
                    orig_features = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
                mat_preset = next((x for x in mat_debloat["presets"] if x["name"] == "default"), None)
                if not mat_preset:
                    print("Drift: Default preset missing in materialized output")
                    sys.exit(1)
                if mat_preset["features"] != orig_features:
                    print("Drift in preset features")
                    sys.exit(1)
                if mat_preset.get("debloat_profile_name") != "default":
                    print("Drift: Default preset debloat_profile_name is not 'default'")
                    sys.exit(1)

            mat_profile = next((x for x in mat_debloat["profiles"] if x["name"] == "default"), None)
            if not mat_profile:
                print("Drift: Default debloat profile missing in materialized output")
                sys.exit(1)
            if mat_profile.get("description") != "Default debloat profile":
                print("Drift: Default debloat profile description does not match")
                sys.exit(1)

        sys.exit(0)

    if __name__ == "__main__":
        check_roundtrip(os.environ["MIOS_DRIFT_ROOT"])

def check_structured() -> int:
    """A [nodes.local-*] lane with no server, or an ai/v1 manifest that does not resolve.

    Lifted out of its shell heredoc so it can be imported, linted and tested;
    inside one, a syntax error surfaces only when the check runs.
    """
    import os, sys, re, json
    root = os.environ["MIOS_DRIFT_ROOT"]
    viol = []

    import tomllib as _toml

    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if _toml is None:
        sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli -- skipping [nodes.*] check\n")
    elif os.path.isfile(toml_path):
        with open(toml_path, "rb") as fh:
            data = _toml.load(fh)
        nodes = data.get("nodes", {}) or {}
        served = set()
        for ud in ("usr/share/containers/systemd", "usr/lib/systemd/system",
                   "etc/containers/systemd"):
            base = os.path.join(root, ud)
            if not os.path.isdir(base):
                continue
            for dirpath, _dn, files in os.walk(base):
                for fn in files:
                    if not fn.endswith((".container", ".service")):
                        continue
                    try:
                        txt = open(os.path.join(dirpath, fn), encoding="utf-8",
                                   errors="ignore").read()
                    except OSError:
                        continue
                    for m in re.findall(r":(\d{4,5})\b", txt):
                        served.add(m)
                    for m in re.findall(r"(?:--port[= ]|PublishPort[= ])(\d{4,5})", txt):
                        served.add(m)
        for name, cfg in nodes.items():
            if not isinstance(cfg, dict):
                continue
            ep = (cfg.get("endpoint") or "").strip()
            if not ep:
                continue  # empty endpoint = inert node, skipped by the loader
            m = re.search(r"://(?:localhost|127\.0\.0\.1|host\.containers\.internal):(\d{4,5})", ep)
            if not m:
                continue  # remote / non-local endpoint -- operator overlay, unverifiable
            port = m.group(1)
            if port not in served:
                viol.append(f"[nodes.{name}] endpoint {ep} -> localhost:{port} is served by NO shipped unit "
                            f"(dangling lane; served ports: {sorted(served)})")

        obs = data.get("observability", {}) or {}
        if "surface_default" not in obs:
            viol.append("[observability] surface_default is missing")
        elif obs.get("surface_default") not in ("clean", "inline"):
            viol.append(f"[observability] surface_default '{obs.get('surface_default')}' must be 'clean' or 'inline'")

        channels = obs.get("channels", {}) or {}
        req_channels = {"thinking", "plan", "tool_call", "tool_result", "source", "content"}
        for rc in req_channels:
            if rc not in channels:
                viol.append(f"[observability.channels] key '{rc}' is missing")

        lanes = data.get("lanes", {}) or {}
        for lname in ("light", "sglang", "vllm"):
            if lname not in lanes:
                viol.append(f"[lanes.{lname}] section is missing")
            else:
                lcfg = lanes[lname] or {}
                for k in ("stream_thinking", "tool_call_parser", "reasoning_parser", "constrained_tools"):
                    if k not in lcfg:
                        viol.append(f"[lanes.{lname}].{k} is missing")

        ap = data.get("agent_pipe", {}) or {}
        for k in ("tool_loop_limit", "reflexion_limit", "reflexion_enable"):
            if k not in ap:
                viol.append(f"[agent_pipe].{k} is missing")

    v1 = os.path.join(root, "usr/share/mios/ai/v1")
    if os.path.isdir(v1):
        for fn in sorted(os.listdir(v1)):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(v1, fn)
            try:
                doc = json.load(open(p, encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                viol.append(f"ai/v1/{fn} does not parse as JSON: {e}")
                continue
            if fn == "tools.json":
                for e in doc.get("data", []):
                    if not isinstance(e, dict):
                        continue
                    for key in ("chat_completions", "responses", "schema_output"):
                        ref = e.get(key)
                        if isinstance(ref, str) and ref.startswith("/usr/"):
                            if not os.path.exists(os.path.join(root, ref.lstrip("/"))):
                                viol.append(f"tools.json: {e.get('name')!r} {key} -> {ref} (missing on disk)")

    for v in viol:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1 if viol else 0)


def check_negative_test_coverage() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, re

    root = os.environ["MIOS_DRIFT_ROOT"]
    harness_path = os.path.join(root, "tests/drift-gate-negatives.sh")

    if not os.path.isfile(harness_path):
        sys.exit(0)

    with open(harness_path, "r", encoding="utf-8", errors="ignore") as f:
        harness_content = f.read()

    required_checks = [
        "check_version_ssot",
        "check_resolver_twin_equivalence",
        "check_cli_eval_safety",
        "check_shellcheck",
        "check_names_registry",
        "check_root_toml_subset",
        "check_toml_projection",
        "check_curl_retry",
        "check_nested_podman_caps",
        "check_bake_budget",
        "check_module_test_coverage",
        "check_router_parity",
        "check_council_gate_ssot",
        "check_agent_pipe_budgets",
        "check_bake_plan",
        "check_containerfile_pinned_clones",
        "check_firstboot_tier",
        "check_rechunk_budget",
        "check_gate_registry",
        "check_test_hermeticity",
        "check_no_mkdir_in_var",
        "check_quadlet_privilege",
        "check_firstboot_degrade_open",
        "check_firstboot_provisioners",
        "check_schema_consumers",
        "check_tasks_status_parity",
        "check_agy_tasks",
        "check_mios_toml_integrity",
        "check_privileged_quadlets_minimal",
        "check_container_names",
        "check_service_urls",
        "check_ports_bound",
        "check_blade_coverage",
        "check_blade_karg",
        "check_role_ssot",
        "check_port_fallbacks",
        "check_node_pool",
        "check_metal_vs_hosted",
        "check_unit_projection",
        "check_ssot_consumer_keys",
        "check_fleet_safety",
        "check_adr_index",
        "check_ssot_lint_equivalence",
        "check_oci_archive_path",
        "check_replaceme_mount_substitution",
        "check_kickstart_shell_syntax",
        "check_offline_install_invariant",
        "check_installer_family_roles",
        "check_bib_configs_projection",
        "check_repo_partition_label_ssot",
        "check_bib_single_config_invariant",
        "check_build_artifacts_output_dir",
        "check_win11_vm_template_xml",
        "check_ipa_enroll_projection",
        "check_uki_cmdline_projection",
        "check_composefs_projection",
        "check_cockpit_projection",
        "check_chrony_ptp_dropin",
        "check_chrony_projection",
        "check_nut_projection",
        "check_renderer_gate_coverage",
    ]

    test_fns = re.findall(r'^\s*(test_[a-z0-9_]+)\(\)\s*\{', harness_content, re.MULTILINE)

    bad = []
    if len(test_fns) < len(required_checks):
        bad.append(f"Negative test suite count ({len(test_fns)}) is less than required law gates count ({len(required_checks)})")

    for chk in required_checks:
        if chk not in harness_content:
            bad.append(f"Required law/security check '{chk}' has no negative test in tests/drift-gate-negatives.sh")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [negatives-coverage-drift] {b}\n")
        sys.exit(1)

    sys.exit(0)


def check_bake_plan_integrity() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import glob, os, sys
    import tomllib

    root = os.environ["MIOS_DRIFT_ROOT"]
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    plan_dir = os.path.join(root, "usr/lib/mios/bake/plan.d")

    if not os.path.isfile(toml_path) or not os.path.isdir(plan_dir):
        sys.exit(0)

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    bake_cfg = data.get("build", {}).get("bake", {})
    core_set = set(bake_cfg.get("core", []))
    tokens = bake_cfg.get("firstboot_tokens", [])

    group_files = sorted(glob.glob(os.path.join(plan_dir, "[0-9][0-9]-*.list")))
    fb_file = os.path.join(plan_dir, "firstboot.list")

    group_images = set()
    group_map = {}
    for gf in group_files:
        gname = os.path.basename(gf)
        with open(gf, "r", encoding="utf-8") as f:
            imgs = set(line.strip() for line in f if line.strip())
        group_map[gname] = imgs
        group_images.update(imgs)

    fb_images = set()
    if os.path.isfile(fb_file):
        with open(fb_file, "r", encoding="utf-8") as f:
            fb_images = set(line.strip() for line in f if line.strip())

    viol = []

    for tok in tokens:
        for gname, imgs in group_map.items():
            hits = [img for img in imgs if tok in img.lower()]
            if hits:
                viol.append(f"Firstboot token '{tok}' image(s) found in baked group list {gname}: {hits}")

        matching_core = [img for img in core_set if tok in img.lower()]
        for img in matching_core:
            if img not in fb_images:
                viol.append(f"Core image '{img}' matching firstboot token '{tok}' missing from firstboot.list")

    for tok in tokens:
        matching_fb = [img for img in fb_images if tok in img.lower()]
        for img in matching_fb:
            if img not in core_set:
                viol.append(f"Firstboot image '{img}' is not listed in [build.bake].core SSOT")

    all_plan_imgs = list(group_images) + list(fb_images)
    if len(all_plan_imgs) != len(set(all_plan_imgs)):
        viol.append("Duplicate image entries found across plan.d/*.list and firstboot.list")

    if set(all_plan_imgs) != core_set:
        missing_from_plan = core_set - set(all_plan_imgs)
        extra_in_plan = set(all_plan_imgs) - core_set
        if missing_from_plan:
            viol.append(f"Core images missing from plan.d: {missing_from_plan}")
        if extra_in_plan:
            viol.append(f"Extra images in plan.d not in core: {extra_in_plan}")

    if bool(tokens) != bool(fb_images):
        viol.append(f"firstboot_tokens non-empty ({tokens}) but firstboot.list empty ({fb_images}) or vice versa")

    if viol:
        for v in viol:
            sys.stderr.write(f"    {v}\n")
        sys.exit(1)

    sys.exit(0)


def check_globals_image_parity() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, re
    root = os.environ["MIOS_DRIFT_ROOT"]
    import tomllib as _toml
    toml = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml):
        sys.exit(0)
    with open(toml, "rb") as fh:
        img = (_toml.load(fh).get("image", {}) or {})

    expected_name = img.get("name", "ghcr.io/mios-dev/mios")
    expected_base = img.get("base", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")
    expected_bib = img.get("bib", "quay.io/centos-bootc/bootc-image-builder:latest")

    bad = []
    sh = os.path.join(root, "automation/lib/globals.sh")
    if os.path.isfile(sh):
        with open(sh, encoding="utf-8") as fh:
            content = fh.read()

            m = re.search(r'MIOS_IMAGE_NAME:=([^}]+)\}', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_name:
                    bad.append(f"globals.sh default MIOS_IMAGE_NAME={got} != mios.toml [image].name={expected_name}")
            else:
                bad.append("globals.sh is missing default MIOS_IMAGE_NAME definition")

            m = re.search(r'MIOS_BASE_IMAGE:=([^}]+)\}', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_base:
                    bad.append(f"globals.sh default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
            else:
                bad.append("globals.sh is missing default MIOS_BASE_IMAGE definition")

            m = re.search(r'MIOS_BIB_IMAGE:=([^}]+)\}', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_bib:
                    bad.append(f"globals.sh default MIOS_BIB_IMAGE={got} != mios.toml [image].bib={expected_bib}")
            else:
                bad.append("globals.sh is missing default MIOS_BIB_IMAGE definition")

    ps1 = os.path.join(root, "automation/lib/globals.ps1")
    if os.path.isfile(ps1):
        with open(ps1, encoding="utf-8") as fh:
            content = fh.read()

            m = re.search(r'\$defaultImageName\s*=\s*([^#\r\n]+)', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_name:
                    bad.append(f"globals.ps1 defaultImageName={got} != mios.toml [image].name={expected_name}")
            else:
                bad.append("globals.ps1 is missing $defaultImageName definition")

            m = re.search(r'MIOS_BASE_IMAGE[^\r\n]+else\s*\{\s*([^}]+)\}', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_base:
                    bad.append(f"globals.ps1 default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
            else:
                bad.append("globals.ps1 is missing default MIOS_BASE_IMAGE definition")

            m = re.search(r'MIOS_BIB_IMAGE[^\r\n]+else\s*\{\s*([^}]+)\}', content)
            if m:
                got = m.group(1).strip('"\' ')
                if got != expected_bib:
                    bad.append(f"globals.ps1 default MIOS_BIB_IMAGE={got} != mios.toml [image].bib={expected_bib}")
            else:
                bad.append("globals.ps1 is missing default MIOS_BIB_IMAGE definition")

    for b in bad:
        sys.stderr.write(f"    {b}\n")
    sys.exit(1 if bad else 0)


def check_no_bare_port_literals() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, re, ast

    root = os.environ["MIOS_DRIFT_ROOT"]
    banned_ports = ["11450", "11441", "11440", "11451", "11434", "11435"]
    scan_dirs = [
        os.path.join(root, "usr/lib/mios/agent-pipe"),
        os.path.join(root, "usr/libexec/mios"),
        os.path.join(root, "usr/bin")
    ]

    class DocstringCollector(ast.NodeVisitor):
        def __init__(self):
            self.docstring_nodes = set()
        def check_body(self, body):
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    self.docstring_nodes.add(body[0].value)
        def visit_Module(self, node):
            self.check_body(node.body)
            self.generic_visit(node)
        def visit_FunctionDef(self, node):
            self.check_body(node.body)
            self.generic_visit(node)
        def visit_AsyncFunctionDef(self, node):
            self.check_body(node.body)
            self.generic_visit(node)
        def visit_ClassDef(self, node):
            self.check_body(node.body)
            self.generic_visit(node)

    violations = []
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for r, ds, fs in os.walk(d):
            for f in fs:
                if not f.endswith((".py", ".sh", ".ps1")) or "test_" in f:
                    continue
                if f in ["Setup-MiOSLanPortProxy.ps1", "Heal-MiOSLocalhostForwarding.ps1", "Setup-MiOSLanPortProxy.ps1.bom-bak", "mios-doctor"]:
                    continue
                path = os.path.join(r, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()

                    if f.endswith(".py"):
                        try:
                            tree = ast.parse(content)
                            collector = DocstringCollector()
                            collector.visit(tree)

                            for node in ast.walk(tree):
                                if isinstance(node, ast.Constant):
                                    if node in collector.docstring_nodes:
                                        continue
                                    val = str(node.value)
                                    for port in banned_ports:
                                        if port in val:
                                            violations.append(f"{f}:{getattr(node, 'lineno', '?')} contains banned port '{port}' in constant '{val}'")
                        except Exception as e:
                            for line_no, line in enumerate(content.splitlines(), 1):
                                stripped = line.strip()
                                if stripped.startswith(("#", "'''", '"""')):
                                    continue
                                code_part = line.split("#", 1)[0]
                                for port in banned_ports:
                                    if port in code_part:
                                        violations.append(f"{f}:{line_no} contains banned port '{port}' (fallback)")
                    else:
                        for line_no, line in enumerate(content.splitlines(), 1):
                            stripped = line.strip()
                            if stripped.startswith(("#", "//", "Write-Host", "echo", "help", "usage")):
                                continue
                            # Only "#" starts a comment in sh and PowerShell. Splitting on
                            # "//" as well truncated every line at the scheme separator of a
                            # URL, so a retired port was invisible in http://host:PORT/... --
                            # the one form these ports actually take. Verified: PORT=11434 was
                            # reported, the identical port inside a URL was not.
                            code_part = line.split("#", 1)[0]
                            for port in banned_ports:
                                if port in code_part:
                                    violations.append(f"{f}:{line_no} contains banned port '{port}'")
                except OSError:
                    pass

    if violations:
        for v in sorted(set(violations)):
            sys.stderr.write(f"    {v}\n")
        sys.exit(1)
    sys.exit(0)


def check_verb_stub_backends() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, glob, re
    import tomllib

    root = os.environ["MIOS_DRIFT_ROOT"]
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")

    if not os.path.isfile(toml_path):
        sys.stderr.write("    SSOT mios.toml missing\n")
        sys.exit(1)

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    verbs = data.get("verbs", {})
    violations = []

    def check_script_body(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Cannot read file {filepath}: {e}"

        code_lines = []
        for line in lines:
            l = line.strip()
            if not l or l.startswith("#"):
                continue
            if re.match(r'^(echo|printf|set\s+-|exit\s+[0-9]+|true|return\s+[0-9]+|export\s+[A-Z_]+=|usage\(\)\s*\{|:\s*;\s*|\}\s*;\s*)$', l):
                continue
            code_lines.append(l)

        if len(code_lines) == 0:
            return "Script body is a stub (produces no side effects)"
        return None

    REGISTERED_STUBS = set()

    for sdir in [os.path.join(root, "usr/libexec/mios"), os.path.join(root, "installation")]:
        if os.path.isdir(sdir):
            for path in glob.glob(os.path.join(sdir, "**/*"), recursive=True):
                if os.path.isfile(path) and (path.endswith(".sh") or path.endswith(".ps1") or "." not in os.path.basename(path)):
                    rel = os.path.relpath(path, root).replace("\\", "/")
                    res = check_script_body(path)
                    if res and rel not in REGISTERED_STUBS:
                        violations.append(f"{rel}: {res}")

    def walk_verbs(prefix, d):
        for k, v in d.items():
            if k == "_defaults":
                continue
            full_name = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                cmd = v.get("cmd") or v.get("exec")
                if cmd:
                    tokens = cmd.strip().split()
                    first = tokens[0] if tokens else ""
                    if first.startswith("/usr/libexec/mios/") or first.startswith("/installation/"):
                        rel_path = first.lstrip("/")
                        full = os.path.join(root, rel_path)
                        if not os.path.exists(full):
                            violations.append(f"Verb {full_name} backend script missing: {rel_path}")
                elif any(isinstance(val, dict) for val in v.values()):
                    walk_verbs(full_name, v)

    walk_verbs("", verbs)

    if violations:
        for v in violations:
            sys.stderr.write(f"    {v}\n")
        sys.exit(1)

    sys.exit(0)


def check_cephfs_ssot() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys
    root = os.environ["MIOS_DRIFT_ROOT"]
    viol = []

    import tomllib as _toml

    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if _toml is None:
        sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli -- skipping CephFS check\n")
    elif os.path.isfile(toml_path):
        with open(toml_path, "rb") as fh:
            data = _toml.load(fh)
        cephfs = data.get("storage", {}).get("cephfs", {}) or {}
        enable = cephfs.get("enable", False)

        if enable:
            monitors = cephfs.get("monitors", [])
            if not monitors or monitors == ["127.0.0.1:6789"]:
                viol.append("[storage.cephfs].monitors must be set to actual monitor IPs when enable=true")

            cache_override = cephfs.get("xdg_cache_home_override", "")
            hostnames = [m.split(":")[0] for m in monitors]
            if ("ceph" in cache_override.lower() or 
                    "/tenants/" in cache_override or 
                    cache_override.startswith("/home/") or 
                    any(h in cache_override for h in hostnames if h)):
                viol.append("[storage.cephfs].xdg_cache_home_override must be local tmpfs, NEVER CephFS (MDS storm hazard)")

            hot_pool = cephfs.get("data_pool_hot", "")
            bulk_pool = cephfs.get("data_pool_bulk", "")
            if hot_pool and bulk_pool and hot_pool == bulk_pool:
                viol.append("[storage.cephfs] data_pool_hot and data_pool_bulk must be distinct pools for tiering")

            prov_script = cephfs.get("provision_script", "")
            if prov_script:
                rel_path = prov_script.lstrip("/")
                repo_path = os.path.join(root, rel_path)
                if not os.path.exists(repo_path) and not os.path.exists(prov_script):
                    viol.append(f"[storage.cephfs].provision_script path '{prov_script}' does not exist on disk")

            if cephfs.get("automount_enable", False):
                mount_tmpl = os.path.join(root, "usr/share/mios/systemd/home-@.mount.tmpl")
                if not os.path.exists(mount_tmpl):
                    viol.append("home-@.mount.tmpl is missing from usr/share/mios/systemd/ but [storage.cephfs].automount_enable is true")

        import re
        tmpls = [
            os.path.join(root, "usr/share/mios/systemd/home-@.mount.tmpl"),
            os.path.join(root, "usr/share/mios/systemd/home-@.automount.tmpl"),
        ]
        setup_script = os.path.join(root, "automation/firstboot/mios-cephfs-mount-setup.sh")
        setup_code = ""
        if os.path.exists(setup_script):
            with open(setup_script, "r", encoding="utf-8", errors="ignore") as sf:
                setup_code = sf.read()

        for tmpl in tmpls:
            if os.path.exists(tmpl):
                with open(tmpl, "r", encoding="utf-8", errors="ignore") as tf:
                    tokens = set(re.findall(r"\$\{MIOS_CEPHFS_([A-Z0-9_]+)\}", tf.read()))
                for tok in tokens:
                    key = tok.lower()
                    if key not in cephfs:
                        viol.append(f"Template token ${{MIOS_CEPHFS_{tok}}} has no corresponding key '{key}' in [storage.cephfs]")
                    if setup_code and f"MIOS_CEPHFS_{tok}" not in setup_code:
                        viol.append(f"Template token ${{MIOS_CEPHFS_{tok}}} is not substituted by mios-cephfs-mount-setup.sh")

    for v in viol:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1 if viol else 0)


def check_firstboot_tier() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, glob
    import tomllib

    root = os.environ["MIOS_DRIFT_ROOT"]
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    fb_list = os.path.join(root, "usr/lib/mios/bake/plan.d/firstboot.list")
    qdir = os.path.join(root, "usr/share/containers/systemd")
    bdir = os.path.join(root, "usr/lib/bootc/bound-images.d")

    if not os.path.isfile(toml_path) or not os.path.isfile(fb_list):
        sys.exit(0)

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    firstboot_tokens = data.get("build", {}).get("bake", {}).get("firstboot_tokens", [])
    if not firstboot_tokens:
        sys.exit(0)

    bad = []
    fb_just = data.get("build", {}).get("bake", {}).get("firstboot_justifications", {})
    for tok in firstboot_tokens:
        if tok not in fb_just or not fb_just[tok]:
            bad.append(f"firstboot token '{tok}' has no justification in [build.bake.firstboot_justifications]")

    with open(fb_list, "r", encoding="utf-8") as fh:
        for line in fh:
            img = line.strip()
            if not img or img.startswith("#"):
                continue
            if not any(tok and tok in img for tok in firstboot_tokens):
                bad.append(f"firstboot.list entry '{img}' matches no token in firstboot_tokens")

    if os.path.isdir(bdir):
        for q in sorted(glob.glob(os.path.join(qdir, "*.container")) + glob.glob(os.path.join(qdir, "*.image"))):
            name = os.path.basename(q)
            img = ""
            try:
                with open(q, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        if line.strip().startswith("Image="):
                            img = line.strip()[6:].strip()
                            break
            except OSError:
                pass
            if any(tok and tok in img for tok in firstboot_tokens):
                if os.path.lexists(os.path.join(bdir, name)):
                    bad.append(f"Firstboot-tier Quadlet '{name}' ({img}) is wrongly symlinked under bound-images.d")

    consumer_script = os.path.join(root, "usr/libexec/mios/mios-ai-firstboot")
    if os.path.isfile(consumer_script):
        with open(consumer_script, "r", encoding="utf-8", errors="ignore") as fh:
            if "firstboot.list" not in fh.read():
                bad.append("usr/libexec/mios/mios-ai-firstboot does not reference firstboot.list")

    if bad:
        for b in bad:
            sys.stderr.write(f"    {b}\n")
        sys.exit(1)
    sys.exit(0)


SUBCOMMANDS = {
    "firstboot-tier": check_firstboot_tier,
    "cephfs-ssot": check_cephfs_ssot,
    "verb-stub-backends": check_verb_stub_backends,
    "no-bare-port-literals": check_no_bare_port_literals,
    "globals-image-parity": check_globals_image_parity,
    "bake-plan-integrity": check_bake_plan_integrity,
    "negative-test-coverage": check_negative_test_coverage,
    "structured": check_structured,
    "drift-build-catalog": check_drift_build_catalog,
    "drift-projection": check_drift_projection,
    "drift-build-catalog": check_drift_build_catalog,
    "unwired-modules": check_unwired_modules,
    "no-duplicate-value-key": check_no_duplicate_value_key,
    "no-inert-ssot-tables": check_no_inert_ssot_tables,
    "doc-refs-resolve": check_doc_refs_resolve,
    "resolver-differential-parity": check_resolver_differential_parity,
    "legibility-ratchet": check_legibility_ratchet,
    "header-integrity": check_header_integrity,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in SUBCOMMANDS:
        print("usage: drift-checks.py {%s}" % "|".join(sorted(SUBCOMMANDS)),
              file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(SUBCOMMANDS[sys.argv[1]]() or 0)
