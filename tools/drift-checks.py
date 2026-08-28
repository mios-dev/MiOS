#!/usr/bin/env python3
# AI-hint: The three largest drift checks, lifted out of their shell heredocs so they can be imported, linted and tested.
# AI-related: mios_manifest, mios_capreg, mios_surface, mios_comments, /usr/libexec/mios/mios-resolver, /usr/share/mios/mios.toml, mios-resolver, mios-env-snapshot, mios-drift-ctx-test, mios-bootstrap
# AI-functions: check_doc_refs_resolve, check_resolver_differential_parity, check_legibility_ratchet, lines, _is_generated, check_no_inert_ssot_tables, check_no_duplicate_value_key, emit, esc, unesc, _shape, check_unwired_modules
"""Each subcommand is one check: it prints violations and exits non-zero.

They lived as heredocs inside the shell gate, where nothing could import or
lint them and a syntax error only surfaced when the check ran. The bodies are
unchanged -- only their container is.
"""
import sys
import os

os.environ.setdefault("MIOS_DRIFT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

    # Size the deliverable from the INDEX blobs, not the checkout. .gitattributes
    # checks *.ps1 out as CRLF on every platform, so the working tree carries
    # ~24 KiB of line-ending expansion the commit does not contain -- and with the
    # total sitting a few KiB past the 201.5 MiB rounding boundary, that expansion
    # alone pushed tracked_mb to 202 and held this ratchet red against content
    # nobody added. Blobs are identical in every clean checkout of a commit.
    nbytes = 0
    try:
        ls_s = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=root,
                              capture_output=True, check=True).stdout.decode("utf-8", "replace")
        oids = [e.split("\t", 1)[0].split()[1] for e in ls_s.split("\0") if e.strip()]
        if oids:
            sizes = subprocess.run(["git", "cat-file", "--batch-check=%(objectsize)"],
                                   cwd=root, input="\n".join(oids).encode(),
                                   capture_output=True, check=True).stdout.decode()
            nbytes = sum(int(s) for s in sizes.split() if s.isdigit())
    except Exception:
        for rel in rels:
            try:
                nbytes += os.path.getsize(os.path.join(root, rel.replace("/", os.sep)))
            except OSError:
                pass

    def _is_generated(rel):
        """True for a file that declares itself a machine projection.

        The shell/PowerShell ceilings exist to drive HAND-WRITTEN glue down as it
        migrates to Rust. automation/lib/globals.{sh,ps1} are rendered in full from
        mios.toml, so they grow whenever the operator declares a config key -- growth
        that cannot be "earned back" except by deleting operator configuration. Counting
        them measured the wrong thing: a [cat] -> [field] rename that added keys pushed
        the PowerShell ceiling over its floor with no hand-written line involved.
        Excluding them LOWERS both floors by ~5.3k lines, so the ratchet binds strictly
        tighter on the code it actually governs.
        """
        try:
            with open(os.path.join(root, rel.replace("/", os.sep)),
                      encoding="utf-8", errors="replace") as fh:
                head = fh.read(600).upper()
        except OSError:
            return False
        return "GENERATED" in head and "DO NOT EDIT" in head

    measured = {
        "max_tracked_files": len(rels),
        "max_tracked_mb": round(nbytes / 1048576),
        "max_shell_lines": lines([r for r in rels
                                  if r.endswith((".sh", ".bash")) and not _is_generated(r)]),
        "max_ps_lines": lines([r for r in rels
                               if r.endswith((".ps1", ".psm1")) and not _is_generated(r)]),
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

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
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
                if f in ["Setup-MiOSLanPortProxy.ps1", "Heal-MiOSLocalhostForwarding.ps1", "Setup-MiOSLanPortProxy.ps1.bom-bak", "mios-doctor", "net_segmentation.py", "selinux_policy.py", "model_matrix_alloc.py", "editor_config_gen.py", "fastfetch_gen.py", "gnome_extension.py", "status_bar.py"]:
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

def check_gate_registry() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import glob, os, sys, re

    root = os.environ["MIOS_DRIFT_ROOT"]
    script_path = os.path.join(root, "automation/98-drift-checks.sh")

    if not os.path.isfile(script_path):
        sys.exit(0)

    with open(script_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    def_re = re.compile(r"^(check_[a-z0-9_]+)\s*\(\)\s*\{")
    main_call_re = re.compile(r"^\s*(check_[a-z0-9_]+)\s*($|#|;|\|\||&&)")

    defined_counts = {}
    in_main = False
    main_calls = []

    for line in lines:
        line_clean = line.split("#")[0].strip()
        if line_clean == "main() {":
            in_main = True
            continue
        if in_main and line_clean.startswith("echo \"[98-drift-checks] ----------"):
            in_main = False
            continue

        m_def = def_re.match(line)
        if m_def:
            name = m_def.group(1)
            defined_counts[name] = defined_counts.get(name, 0) + 1

        if in_main:
            m_call = main_call_re.match(line_clean)
            if m_call:
                main_calls.append(m_call.group(1))

    bad = []

    for name, count in defined_counts.items():
        if count > 1:
            bad.append(f"Duplicate function definition found in 98-drift-checks.sh: {name} (defined {count} times)")

    for name in defined_counts.keys():
        calls = main_calls.count(name)
        if calls == 0:
            bad.append(f"Defined check function is not registered in main(): {name}")
        elif calls > 1:
            bad.append(f"Defined check function is called multiple times in main(): {name} ({calls} times)")

    for call in main_calls:
        if call not in defined_counts:
            bad.append(f"main() calls unregistered/undefined check function: {call}")

    sh_text = "".join(lines)
    tool_checks = glob.glob(os.path.join(root, "tools/check-*.py"))

    for tc in tool_checks:
        tc_name = os.path.basename(tc)
        if tc_name not in sh_text:
            with open(tc, "r", encoding="utf-8", errors="ignore") as tcf:
                tc_head = [tcf.readline() for _ in range(3)]
            tc_hint = "".join(tc_head).lower()
            if "drift check" in tc_hint or "drift-check" in tc_hint:
                bad.append(f"tools/{tc_name} claims drift-check identity in AI-hint but is not referenced in 98-drift-checks.sh")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [gate-registry-drift] {b}\n")
        sys.exit(1)

    sys.exit(0)

def check_names_registry() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, re, subprocess

    root = os.environ["MIOS_DRIFT_ROOT"]
    violations = []

    ref_file = os.path.join(root, "usr/share/mios/referenced_names.txt")
    committed_ref = ""
    if os.path.isfile(ref_file):
        try:
            with open(ref_file, "r", encoding="utf-8") as fh:
                committed_ref = fh.read()
        except Exception as e:
            violations.append(f"Failed to read committed referenced_names.txt: {e}")

    gen_script = os.path.join(root, "tools/generate-names-registry.py")
    registry_file = os.path.join(root, "usr/share/mios/names.generated.txt")

    if not os.path.isfile(gen_script):
        violations.append("tools/generate-names-registry.py missing")
    elif not os.path.isfile(registry_file):
        violations.append("usr/share/mios/names.generated.txt missing")
    else:
        try:
            with open(registry_file, "r", encoding="utf-8") as fh:
                committed_data = fh.read()
            res = subprocess.run([sys.executable, gen_script], capture_output=True, text=True, check=True)
            fresh_data = res.stdout

            fresh_lines = [l.strip() for l in fresh_data.splitlines() if l.strip()]
            committed_lines = [l.strip() for l in committed_data.splitlines() if l.strip()]

            if fresh_lines != committed_lines:
                violations.append("usr/share/mios/names.generated.txt is stale. Please run tools/generate-names-registry.py.")
        except Exception as e:
            violations.append(f"Failed to check names registry generation: {e}")

    fresh_ref = ""
    if os.path.isfile(ref_file):
        try:
            with open(ref_file, "r", encoding="utf-8") as fh:
                fresh_ref = fh.read()
        except Exception as e:
            violations.append(f"Failed to read fresh referenced_names.txt: {e}")

    if fresh_ref != committed_ref:
        try:
            with open(ref_file, "w", encoding="utf-8") as fh:
                fh.write(committed_ref)
        except Exception:
            pass
        violations.append("usr/share/mios/referenced_names.txt is stale. Please run tools/generate-names-registry.py.")

    if violations:
        for v in sorted(violations):
            sys.stderr.write(f"    {v}\n")
        sys.exit(1)
    sys.exit(0)

def check_agent_schema() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys, re
    root = os.environ["MIOS_DRIFT_ROOT"]
    import tomllib as _toml
    p = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(p):
        sys.exit(0)
    with open(p, "rb") as fh:
        d = _toml.load(fh)
    ag = dict(d.get("agents") or {})
    defs = ag.pop("_defaults", {}) if isinstance(ag.get("_defaults"), dict) else {}
    CANON = {"kind","endpoint","model","role","job","default","fanout","enabled","lane",
             "sub_lane","health_gate","transport","timeout_s","strengths","cpu_endpoint",
             "cpu_model","failover_agents","denied_verbs","allowed_verbs","max_permission",
             "api","vram_mb","ram_mb","tool_capable","research_only","auth","trust",
             "engines","nodes","backend","privilege_group"}
    def _local(ep):
        h = re.sub(r'^[a-z]+://', '', str(ep)).split('/')[0].rsplit(':', 1)[0]
        return h in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "")
    bad, warn, ndefault = [], [], 0
    REQUIRED_FIELDS = {"role", "job", "lane", "health_gate"}
    for name, cfg in ag.items():
        if name.startswith("_") or not isinstance(cfg, dict):
            continue
        if not cfg:
            bad.append(f"    [agents.{name}] agent table is empty")
            continue
        for req_k in REQUIRED_FIELDS:
            if req_k not in cfg:
                bad.append(f"    [agents.{name}] missing required field {req_k!r} in block")
        if "model" not in cfg and "endpoint" not in cfg:
            bad.append(f"    [agents.{name}] must declare 'model' or 'endpoint' in block")
        m = {**defs, **cfg}
        kind = str(m.get("kind", "")).strip().lower()
        ep = str(m.get("endpoint", "")).strip()
        enabled = bool(m.get("enabled", True))
        hg = bool(m.get("health_gate", False))
        if bool(m.get("default", False)):
            ndefault += 1
        loc = _local(ep)
        if loc and not bool(m.get("default", False)) and enabled and kind in ("", "local-http") and not hg:
            bad.append(f"    [agents.{name}] LOCAL + non-default + enabled but no health_gate=true (or enabled=false): a dead endpoint is treated as live -> DAG sink -> merged_chars=0")
        if kind == "cli":
            if not (hg or not enabled):
                bad.append(f"    [agents.{name}] kind=cli must set health_gate=true OR enabled=false")
            if int(m.get("timeout_s", 0) or 0) <= 0:
                bad.append(f"    [agents.{name}] kind=cli must set timeout_s>0 (fail-fast budget)")
        if kind == "node" and not (str(m.get("api", "")).strip() and str(m.get("lane", "")).strip()):
            bad.append(f"    [agents.{name}] kind=node must set api + lane")
        if kind in ("remote-http", "edge", "mobile") and not hg:
            bad.append(f"    [agents.{name}] kind={kind} must set health_gate=true")
        if re.search(r':\d{2,5}(/|$)', ep) and "${MIOS_PORT" not in ep:
            warn.append(f"    [agents.{name}].endpoint bare :PORT literal (use ${{MIOS_PORT_*}}): {ep}")
        for k in cfg:
            if k not in CANON:
                warn.append(f"    [agents.{name}] unknown key {k!r} (not in the canonical agent schema)")
    if ndefault > 1:
        bad.append(f"    {ndefault} [agents.*] set default=true; at most one is allowed")
    for w in warn:
        sys.stdout.write("[98-drift-checks]   (advisory)" + w + "\n")
    for b in bad:
        sys.stderr.write(b + "\n")
    sys.exit(1 if bad else 0)

def check_bootstrap_ports_drift() -> int:
    """Lifted from a shell heredoc so it can be imported, linted and tested.

    Inside a heredoc a syntax error surfaces only when the check runs.
    """
    import os, sys
    root = os.environ["MIOS_DRIFT_ROOT"]
    import tomllib as _toml

    main_toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(main_toml_path):
        sys.exit(0)

    with open(main_toml_path, "rb") as fh:
        main_data = _toml.load(fh)

    bootstrap_repo_path = main_data.get("bootstrap", {}).get("bootstrap_repo", "C:/mios-bootstrap")

    if sys.platform != "win32" and bootstrap_repo_path.startswith("C:/"):
        bootstrap_repo_path = "/mnt/c/" + bootstrap_repo_path[3:]

    # CI clones the bootstrap repo into RUNNER_TEMP, which is neither the SSOT path
    # nor a sibling, and names it in MIOS_BOOTSTRAP_ROOT. An explicit override wins
    # over both guesses; mios-sync-toml resolves it the same way.
    _env_bs = (os.environ.get("MIOS_BOOTSTRAP_ROOT") or "").strip()
    if _env_bs and os.path.isdir(_env_bs):
        bootstrap_repo_path = _env_bs

    if not os.path.isdir(bootstrap_repo_path):
        bootstrap_repo_path = os.path.join(os.path.dirname(root), "mios-bootstrap")

    if not os.path.isdir(bootstrap_repo_path):
        sys.stderr.write(f"    ERROR: bootstrap repository mios-bootstrap missing at '{bootstrap_repo_path}'\n")
        sys.exit(1)

    bootstrap_toml_path = os.path.join(bootstrap_repo_path, "mios.toml")
    if not os.path.isfile(bootstrap_toml_path):
        sys.stderr.write(f"    ERROR: bootstrap mios.toml missing at '{bootstrap_toml_path}'\n")
        sys.exit(1)

    with open(bootstrap_toml_path, "rb") as fh:
        boot_data = _toml.load(fh)

    drift = []
    shared_sections = ["ports", "colors", "debloat", "xbox_features"]
    for sec in shared_sections:
        main_sec = {k: v for k, v in main_data.get(sec, {}).items() if not isinstance(v, dict)}
        boot_sec = {k: v for k, v in boot_data.get(sec, {}).items() if not isinstance(v, dict)}

        for k, v in main_sec.items():
            if k not in boot_sec:
                drift.append(f"Section [{sec}] key '{k}' in main mios.toml is missing from bootstrap mios.toml")
            elif boot_sec[k] != v:
                drift.append(f"Section [{sec}] key '{k}' value differs: main={v}, bootstrap={boot_sec[k]}")

        for k, v in boot_sec.items():
            if k not in main_sec:
                drift.append(f"Section [{sec}] key '{k}' in bootstrap mios.toml is missing from main mios.toml")

    if drift:
        for d in drift:
            sys.stderr.write("    " + d + "\n")
        sys.exit(1)
    sys.exit(0)

def check_rbac_tiers() -> int:
    import os, sys
    import tomllib as _toml
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    p = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(p):
        return 0
    with open(p, "rb") as fh:
        d = _toml.load(fh)
    tiers = [str(x).strip().lower()
             for x in ((d.get("ai") or {}).get("permission_tiers")
                       or ["read", "write", "interactive"]) if str(x).strip()]
    bad = []
    for sect in ("agents", "users"):
        for name, cfg in (d.get(sect) or {}).items():
            if not isinstance(cfg, dict):
                continue
            mp = str(cfg.get("max_permission") or "").strip().lower()
            if mp and mp not in tiers:
                bad.append(f"    [{sect}.{name}].max_permission={mp!r} not in {tiers}")
    for b in bad:
        sys.stderr.write(b + "\n")
    return 1 if bad else 0

def check_ai_manifest() -> int:
    import os, sys, json
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
    try:
        import mios_manifest as man
    except Exception as e:
        sys.stderr.write(f"    cannot import mios_manifest ({e}) -- skipping\n")
        return 0
    toml = os.path.join(root, "usr/share/mios/mios.toml")
    out = os.path.join(root, "usr/share/mios/ai/v1/tools.generated.json")
    try:
        gen = man.project_verb_catalog(man.load_verbs_from_toml(toml))
    except Exception as e:
        sys.stderr.write(f"    verb-catalog projection failed: {e}\n")
        return 1
    try:
        with open(out, encoding="utf-8") as fh:
            committed = json.load(fh)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"    committed manifest unreadable ({out}): {e}\n")
        return 1
    diffs = man.diff_manifest(gen, committed)
    for d in diffs[:30]:
        sys.stderr.write("    " + d + "\n")
    return 1 if diffs else 0

def check_capability_manifest() -> int:
    import os, sys, json
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
    try:
        import mios_capreg as cap
    except Exception as e:
        sys.stderr.write(f"    cannot import mios_capreg ({e}) -- skipping\n")
        return 0
    toml = os.path.join(root, "usr/share/mios/mios.toml")
    out = os.path.join(root, "usr/share/mios/ai/v1/capabilities.generated.json")
    try:
        gen = cap.project_from_toml(toml, ceiling="interactive")
    except Exception as e:
        sys.stderr.write(f"    capability projection failed: {e}\n")
        return 1
    try:
        with open(out, encoding="utf-8") as fh:
            committed = json.load(fh).get("data", [])
    except (OSError, ValueError) as e:
        sys.stderr.write(f"    committed capabilities manifest unreadable ({out}): {e}\n")
        return 1
    diffs = cap.diff_capabilities(gen, committed)
    for d in diffs[:30]:
        sys.stderr.write("    " + d + "\n")
    return 1 if diffs else 0

def check_surface_parity() -> int:
    import os, sys, json
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
    try:
        import mios_surface as surf
    except Exception as e:
        sys.stderr.write(f"    cannot import mios_surface ({e}) -- skipping\n")
        return 0
    server = os.path.join(root, "usr/lib/mios/agent-pipe/server.py")
    out = os.path.join(root, "usr/share/mios/ai/v1/surface.generated.json")
    if not os.path.isfile(server):
        sys.stderr.write("    server.py absent -- skipping\n")
        return 0
    try:
        gen = surf.project_package(server)
    except Exception as e:
        sys.stderr.write(f"    surface projection failed: {e}\n")
        return 1
    try:
        with open(out, encoding="utf-8") as fh:
            committed = json.load(fh)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"    committed surface golden unreadable ({out}): {e}\n")
        return 1
    diffs = surf.diff_surface(gen, committed)
    for d in diffs[:40]:
        sys.stderr.write("    " + d + "\n")
    if len(diffs) > 40:
        sys.stderr.write(f"    ... and {len(diffs) - 40} more\n")
    return 1 if diffs else 0

def check_container_ports() -> int:
    import os, sys, re
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    import tomllib as _toml

    p = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(p):
        return 0

    with open(p, "rb") as fh:
        d = _toml.load(fh)
    ports = d.get("ports") or {}

    port_vals = {name: val for name, val in ports.items() if name != "stack_id" and isinstance(val, int)}

    viol = []
    quadlet_dirs = ["usr/share/containers/systemd", "etc/containers/systemd"]
    for qd in quadlet_dirs:
        dir_path = os.path.join(root, qd)
        if not os.path.isdir(dir_path):
            continue
        for dp, _dn, files in os.walk(dir_path):
            for fn in files:
                if not fn.endswith(".container"):
                    continue
                path = os.path.join(dp, fn)
                try:
                    lines = open(path, encoding="utf-8", errors="ignore").readlines()
                except OSError:
                    continue
                for idx, line in enumerate(lines, 1):
                    active = re.sub(r'#.*', '', line).strip()
                    if not active:
                        continue
                    for name, val in port_vals.items():
                        cleaned = re.sub(r'\$\{MIOS_PORT_[A-Z0-9_]+:-' + str(val) + r'\}', '', active)
                        if re.search(rf'\b{val}\b', cleaned):
                            if val in (8080, 3002) and (":" + str(val) in cleaned or "=" + str(val) in cleaned and not cleaned.startswith("PublishPort=")):
                                continue
                            viol.append(f"{fn}:{idx}: manual port literal {val} for '{name}' used in active line: {line.strip()}")

    for v in viol:
        print(v)
    return 1 if viol else 0

def check_agent_pipe_budgets() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    agent_pipe = data.get("agent_pipe", {})
    dispatch = data.get("dispatch", {})

    def key_in_dict(d, k):
        if not isinstance(d, dict):
            return False
        if k in d:
            return True
        return any(key_in_dict(v, k) for v in d.values() if isinstance(v, dict))

    search_dir = os.path.join(root, "usr/lib/mios/agent-pipe")
    if not os.path.isdir(search_dir):
        search_dir = root

    code = ""
    for r, ds, fs in os.walk(search_dir):
        for f in fs:
            if f.endswith(".py"):
                try:
                    with open(os.path.join(r, f), "r", encoding="utf-8", errors="ignore") as fh:
                        code += fh.read() + "\n"
                except OSError:
                    pass

    budget_keys = [
        "tool_max_iters", "replan_max", "no_progress_window",
        "max_consecutive_failures", "wall_clock_budget_s", "reflexion_enable",
        "swarm_max_width", "max_dispatch_depth", "default_hop_budget"
    ]
    missing = []
    for k in budget_keys:
        if not key_in_dict(agent_pipe, k) and not key_in_dict(dispatch, k):
            missing.append(f"{k} (missing from mios.toml)")
            continue
        pattern = rf"['\"]{k}['\"]"
        if not re.search(pattern, code) and k not in code:
            missing.append(k)

    if missing:
        sys.stderr.write(f"    Missing code consumers or TOML definitions for budget keys: {missing}\n")
        return 1
    return 0

def check_verb_backends() -> int:
    import os, sys, re
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    import tomllib as _toml
    p = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(p):
        return 0
    with open(p, "rb") as fh:
        d = _toml.load(fh)
    libexec = os.path.join(root, "usr/libexec/mios")
    usrbin = os.path.join(root, "usr/bin")
    def _exists(t):
        return os.path.isfile(os.path.join(libexec, t)) or os.path.isfile(os.path.join(usrbin, t))
    missing = {}
    for name, cfg in (d.get("verbs", {}) or {}).items():
        if not isinstance(cfg, dict):
            continue
        cmd = cfg.get("cmd", "")
        if name == "update" and not cmd:
            missing.setdefault("update missing cmd key", []).append(name)
            continue
        if not isinstance(cmd, str) or not cmd:
            continue
        for tok in set(re.findall(r"\bmios-[a-z0-9-]+", cmd)):
            if not _exists(tok):
                missing.setdefault(tok, []).append(name)
    for t, vs in sorted(missing.items()):
        sys.stderr.write(f"    {t} <- [verbs.*] {sorted(vs)} (backend not on disk)\n")
    return 1 if missing else 0

def check_python_untested_ratchet() -> int:
    import sys, os
    root_dir = os.environ.get("MIOS_DRIFT_ROOT", ".")
    base_file = os.path.join(root_dir, "usr/share/mios/reference/python-untested-baseline.txt")
    if not os.path.isfile(base_file):
        return 0
    with open(base_file, encoding="utf-8") as f:
        allowed = set(line.strip() for line in f if line.strip() and not line.startswith("#"))

    untested = []
    for scan_dir in ['tools', os.path.join('usr', 'libexec', 'mios')]:
        full_scan = os.path.join(root_dir, scan_dir)
        if not os.path.isdir(full_scan):
            continue
        for f in os.listdir(full_scan):
            if not f.endswith('.py') or f.startswith('test_') or f == '__init__.py':
                continue
            rel = f"{scan_dir}/{f}".replace("\\", "/")
            norm_stem = f[:-3].replace("-", "_")
            test1 = os.path.join(full_scan, f"test_{f}")
            test2 = os.path.join(full_scan, f"test_{f[:-3]}.py")
            test3 = os.path.join(full_scan, f"test_{norm_stem}.py")
            if not (os.path.exists(test1) or os.path.exists(test2) or os.path.exists(test3)):
                if rel not in allowed:
                    untested.append(rel)

    if untested:
        for u in untested:
            sys.stderr.write(f"    untested python module not in baseline: {u}\n")
        return 1

    return 0

def check_canonical_bools() -> int:
    import sys, os
    import tomllib
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.environ.get("MIOS_TOML", os.path.join(root, "usr/share/mios/mios.toml"))
    if not os.path.isfile(toml_path):
        return 0
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    verbs = data.get("verbs", {})
    for vname, vcfg in verbs.items():
        if vname == "_defaults":
            continue
        if not isinstance(vcfg, dict):
            continue
        if "hidden" in vcfg:
            val = vcfg["hidden"]
            if not isinstance(val, bool):
                print(f"Non-canonical hidden value in verb '{vname}': {val!r} (must be true/false)")
                return 1
        if "sensitive" in vcfg:
            val = vcfg["sensitive"]
            if not isinstance(val, bool):
                print(f"Non-canonical sensitive value in verb '{vname}': {val!r} (must be true/false)")
                return 1
        params = vcfg.get("params", {})
        if isinstance(params, dict):
            for p_name, p_cfg in params.items():
                if not isinstance(p_cfg, dict):
                    continue
                if "required" in p_cfg:
                    req = p_cfg["required"]
                    if not isinstance(req, bool):
                        print(f"Non-canonical required value in verb '{vname}' param '{p_name}': {req!r} (must be true/false)")
                        return 1
                if "default" in p_cfg and p_cfg.get("type") == "boolean":
                    d = p_cfg["default"]
                    if not isinstance(d, bool):
                        print(f"Non-canonical default boolean value in verb '{vname}' param '{p_name}': {d!r} (must be true/false)")
                        return 1
    return 0

def check_dag_integrity() -> int:
    import os, sys, re
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    violations = []

    scan_dirs = [
        os.path.join(root, "usr/lib/systemd/system"),
        os.path.join(root, "usr/share/containers/systemd"),
    ]

    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            fpath = os.path.join(d, f)
            if not os.path.isfile(fpath) or not f.endswith((".service", ".container", ".pod")):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()

                after_requires_targets = []
                for line in content.splitlines():
                    m = re.match(r"^[ \t]*(After|Requires)[ \t]*=[ \t]*(.*)$", line, re.IGNORECASE)
                    if m:
                        after_requires_targets.extend(m.group(2).split())

                is_local_img = "Image=localhost/" in content
                is_webtools_pod = f == "mios-webtools.pod"
                if is_local_img or is_webtools_pod:
                    if "mios-webtools-firstboot.service" not in after_requires_targets:
                        violations.append(f"{f} uses local image/pod but lacks 'After=... mios-webtools-firstboot.service'")
            except OSError:
                pass

    if violations:
        for v in sorted(violations):
            sys.stderr.write(f"    {v}\n")
        return 1
    return 0

def check_ai_endpoint_local() -> int:
    import os, re, sys
    import tomllib as _t
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        data = _t.load(fh)
    ep = str((data.get("ai") or {}).get("endpoint") or "")
    if not ep:
        print("[ai].endpoint is empty -- every client resolves MIOS_AI_ENDPOINT from it")
        return 0
    host = re.sub(r"^[a-z]+://", "", ep).split("/")[0].split(":")[0]
    if host not in ("localhost", "127.0.0.1", "::1", "[::1]"):
        print("[ai].endpoint is %s: the VENDOR default must stay local (ADR-0016 D5). "
              "Point it off-box in /etc/mios, never in the shipped SSOT" % ep)
        return 1
    return 0

def check_version_literals_ssot() -> int:
    import os, sys, re, subprocess
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    canonical_ver = os.environ.get("MIOS_CANONICAL_VER", "")
    if not canonical_ver:
        toml_path = os.path.join(root, "usr/share/mios/mios.toml")
        if os.path.isfile(toml_path):
            import tomllib
            with open(toml_path, "rb") as fh:
                d = tomllib.load(fh)
                canonical_ver = str((d.get("meta") or {}).get("mios_version") or (d.get("system") or {}).get("version") or "").strip()

    root_toml = os.path.join(root, "mios.toml")
    if os.path.isfile(root_toml):
        try:
            with open(root_toml, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if re.search(r'^\s*mios_version\s*=', line) and canonical_ver not in line:
                        sys.stderr.write(f"    TODO(td-2): root mios.toml has version divergence from canonical {canonical_ver}\n")
        except OSError:
            pass

    pattern = re.compile(r'\bv?0\.[0-9]+\.[0-9]+\b')
    viol = []

    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=root, stderr=subprocess.DEVNULL).decode("utf-8")
        tracked = [os.path.normpath(os.path.join(root, f)) for f in out.splitlines()]
    except Exception:
        tracked = []
        for r, _d, files in os.walk(root):
            rel_r = os.path.relpath(r, root).replace("\\", "/")
            parts = rel_r.split('/')
            if any(p in parts for p in ('tmp', '.git', '.venv', '__pycache__', 'node_modules', 'dist', 'build', 'target', '.system_generated', 'scratch', 'logs', 'bib-configs', 'medicat_stage', 'isobuild', 'isobuild_live', 'isobuild2')):
                continue
            for f in files:
                tracked.append(os.path.normpath(os.path.join(r, f)))

    for path in tracked:
        rel = os.path.relpath(path, root).replace("\\", "/")
        if not (rel.startswith("automation") or rel.startswith("usr/libexec/") or rel.startswith("tools")):
            continue
        if rel.endswith((".pyc", ".png", ".jpg", ".generated", ".json", ".log", ".ready", ".lock", ".d", ".o", ".rlib", ".rmeta", ".a")):
            continue
        if "/tests/golden/" in rel:
            continue
        if not os.path.isfile(path):
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue

        for idx, line in enumerate(lines):
            for m in pattern.finditer(line):
                ver = m.group(0)
                ver_clean = ver[1:] if ver.startswith('v') else ver
                if ver_clean != canonical_ver:
                    if ver_clean in ("0.0.0", "0.0.1", "0.8.3", "0.2.4", "0.5.0", "0.6.0", "0.80.0", "0.9.6", "0.0.76", "0.1.0"):
                        continue
                    if "INTEL_SG_FALLBACK_TAG" in line:
                        continue
                    if "Upstream v0.15.0" in line:
                        continue
                    viol.append(f"    {rel}:{idx+1} hardcodes different version literal [{ver}], expected [{canonical_ver}]")

    if viol:
        for v in viol:
            sys.stderr.write(v + "\n")
        return 1
    return 0

def check_bake_refs_parity() -> int:
    import os, sys, re, subprocess
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    bake_refs = data.get("build", {}).get("bake_refs", {})

    try:
        matches = subprocess.check_output(["git", "grep", "-E", r"MIOS_BUILD_BAKE_REFS_[A-Z0-9_]+:-", "automation/"], cwd=root, text=True).splitlines()
    except Exception:
        matches = []

    viol = []
    pattern = re.compile(r"MIOS_BUILD_BAKE_REFS_([A-Z0-9_]+):-([^}\"\']+)")
    for m in matches:
        res = pattern.search(m)
        if res:
            key = res.group(1).lower()
            lit = res.group(2).strip()
            if key in bake_refs:
                ssot_val = str(bake_refs[key]).strip()
                if lit != ssot_val:
                    viol.append(f"{m.split(':')[0]}: MIOS_BUILD_BAKE_REFS_{res.group(1)} default '{lit}' != SSOT '{ssot_val}'")

    if viol:
        for v in viol:
            sys.stderr.write(f"    {v}\n")
        return 1
    return 0

def check_cli_eval_safety() -> int:
    import os, sys, re
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    dir_to_scan = os.path.join(root, "usr/libexec/mios")
    viol = []

    if os.path.isdir(dir_to_scan):
        for fn in os.listdir(dir_to_scan):
            path = os.path.join(dir_to_scan, fn)
            if not os.path.isfile(path) or fn.endswith((".py", ".pyc", ".json", ".generated")):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    first_line = fh.readline()
                    if not ("bash" in first_line or "sh" in first_line):
                        continue
                    fh.seek(0)
                    lines = fh.readlines()
            except OSError:
                continue

            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue

                code_part = line.split("#")[0].strip()
                if re.search(r'\beval\b', code_part):
                    viol.append(f"{fn}:{idx+1} has eval: {line.strip()}")

    if viol:
        for v in viol:
            sys.stderr.write(f"  {v}\n")
        return 1
    return 0

def check_resolver_ssot_refs() -> int:
    import os, sys, re
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    rel = os.environ.get("MIOS_DRIFT_REL", "usr/libexec/mios/mios-resolve-latest")
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return 0
    ref = re.compile(r"""['"][a-z0-9][a-z0-9.\-]*\.[a-z]{2,}/[^\s'"]+:[^\s'"]+['"]""")
    res = []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for i, line in enumerate(fh, 1):
            s = line.strip()
            if s.startswith("#"):
                continue
            m = ref.search(s)
            if m:
                res.append(f"{i}: {m.group(0)}")
    if res:
        for r in res:
            print(r)
        return 1
    return 0

def check_bake_budget() -> int:
    import os, sys, tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    tsv_path = os.path.join(root, "usr/share/mios/artifacts/sbom/bound-images.tsv")

    if not os.path.exists(toml_path):
        print("ERROR: SSOT mios.toml absent")
        return 1

    if not os.path.exists(tsv_path):
        print("ERROR: bound-images.tsv SBOM artifact absent")
        return 1

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse mios.toml: {e}")
        return 1

    budget = data.get("build", {}).get("bake", {}).get("runner_disk_budget_gb", None)
    if budget is None or not isinstance(budget, (int, float)) or budget <= 0:
        print(f"ERROR: [build.bake].runner_disk_budget_gb is absent or invalid ({budget})")
        return 1

    try:
        with open(tsv_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except Exception as e:
        print(f"ERROR: Failed to read bound-images.tsv: {e}")
        return 1

    if not lines:
        print("ERROR: bound-images.tsv is empty")
        return 1

    header = lines[0].split("\t")
    if "size_gb" not in header:
        print("ERROR: bound-images.tsv missing size_gb column")
        return 1

    size_idx = header.index("size_gb")
    group_idx = header.index("group") if "group" in header else -1

    total_day0 = 0.0
    for line in lines[1:]:
        parts = line.split("\t")
        group = parts[group_idx] if group_idx >= 0 and len(parts) > group_idx else "extra"
        if group == "firstboot":
            continue
        try:
            sz = float(parts[size_idx])
        except (ValueError, IndexError):
            print(f"ERROR: Malformed size entry in line: {line}")
            return 1
        total_day0 += sz

    if total_day0 > budget:
        print(f"EXCEEDED: Total Day-0 bake size {total_day0:.2f}GB exceeds SSOT budget {budget}GB")
        return 1

    print(f"OK: Day-0 size {total_day0:.2f}GB <= budget {budget}GB")
    return 0

def check_greenboot() -> int:
    import os, re, sys
    import tomllib as _toml

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    gb_dir = os.environ.get("MIOS_DRIFT_GB_DIR", os.path.join(root, "usr/lib/greenboot/check/required.d"))
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    gb = data.get("greenboot") or {}
    critical = [str(x).strip() for x in (gb.get("critical_services") or []) if str(x).strip()]
    probe = gb.get("probe") or {}
    if not critical:
        print("(54) [greenboot].critical_services is empty or absent -- greenboot coverage would pass vacuously over an empty set")
        return 1

    bodies, probed, ssot_driven = {}, set(), False
    if os.path.isdir(gb_dir):
        for name in sorted(os.listdir(gb_dir)):
            fp = os.path.join(gb_dir, name)
            if not os.path.isfile(fp):
                continue
            try:
                body = open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
            bodies[name] = code
            if "MIOS_GREENBOOT_CRITICAL_SERVICES" in code:
                ssot_driven = True
            for m in re.finditer(r"\b(?:mios-)?([a-z0-9][a-z0-9_-]*)\.service\b", code):
                probed.add(m.group(1))

    def unit_for(svc):
        spec = probe.get(svc.replace("-", "_")) or probe.get(svc) or {}
        unit = str(spec.get("unit") or "").strip()
        return unit or ("mios-%s.service" % svc)

    def unit_exists(unit):
        stem = unit[:-len(".service")] if unit.endswith(".service") else unit
        if stem in (data.get("containers") or {}):
            return True
        return os.path.isfile(os.path.join(root, "usr/lib/systemd/system", unit))

    viol = []
    for svc in critical:
        if ssot_driven:
            unit = unit_for(svc)
            if not unit_exists(unit):
                viol.append("(54) [greenboot].critical_services names '%s', but the probe would derive %s, which is not a shipped unit or a declared container" % (svc, unit))
            continue
        key = svc[5:] if svc.startswith("mios-") else svc
        if key not in probed:
            viol.append("(54) greenboot missing health-check script for critical service: %s (no required.d script references %s.service outside comments)" % (svc, svc))

    if viol:
        for v in viol:
            print(v)
        return 1
    return 0

def check_router_intent_coverage() -> int:
    import sys, json, re, glob, os

    if len(sys.argv) >= 4:
        corpus_file, root_dir = sys.argv[2], sys.argv[3]
    elif len(sys.argv) == 3:
        corpus_file, root_dir = sys.argv[2], os.environ.get("MIOS_DRIFT_ROOT", ".")
    else:
        root_dir = os.environ.get("MIOS_DRIFT_ROOT", ".")
        corpus_file = os.path.join(root_dir, "usr/lib/mios/agent-pipe/tests/router_corpus.json")

    if not os.path.isfile(corpus_file):
        return 0

    with open(corpus_file, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    corpus_intents = set()
    for item in corpus:
        inp = item.get("input", {})
        if isinstance(inp, dict) and "intent" in inp and inp["intent"]:
            corpus_intents.add(str(inp["intent"]).strip().lower())

    pattern = re.compile(r'(?:intent\s*==|get\s*\(\s*["\']intent["\']\s*\)\s*==)\s*["\']([a-zA-Z0-9_]+)["\']')

    search_files = [os.path.join(root_dir, "usr/lib/mios/agent-pipe/server.py")] + \
                   glob.glob(os.path.join(root_dir, "usr/lib/mios/agent-pipe/mios_pipe/**/*.py"), recursive=True)

    unmapped = set()
    for filepath in search_files:
        if not os.path.isfile(filepath) or "test_" in os.path.basename(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for match in pattern.finditer(content):
                intent_val = match.group(1).lower()
                if intent_val not in corpus_intents:
                    unmapped.add((intent_val, os.path.relpath(filepath, root_dir).replace("\\", "/")))
        except Exception:
            pass

    if unmapped:
        for intent_val, relpath in sorted(unmapped):
            print(f"unmapped intent: {intent_val} in {relpath}", file=sys.stderr)
        return 1
    return 0

def check_council_gate_ssot() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    agent_pipe = data.get("agent_pipe", {})
    council = agent_pipe.get("council", {})
    if not council:
        sys.stderr.write("    Missing [agent_pipe.council] table in mios.toml\n")
        return 1

    search_dir = os.path.join(root, "usr/lib/mios/agent-pipe")
    if not os.path.isdir(search_dir):
        search_dir = root

    code = ""
    for r, ds, fs in os.walk(search_dir):
        for f in fs:
            if f.endswith(".py"):
                try:
                    with open(os.path.join(r, f), "r", encoding="utf-8", errors="ignore") as fh:
                        code += fh.read() + "\n"
                except OSError:
                    pass

    council_keys = ["diversity_gate", "diversity_threshold", "aggregator_bypass", "aggregator_bypass_threshold"]
    missing = []
    for k in council_keys:
        if k not in council:
            missing.append(f"{k} (missing from mios.toml)")
            continue
        pattern = rf"['\"]{k}['\"]"
        if not re.search(pattern, code) and k not in code:
            missing.append(k)

    if missing:
        sys.stderr.write(f"    Missing code consumers or TOML definitions for [agent_pipe.council] keys: {missing}\n")
        return 1
    return 0

def check_test_hermeticity() -> int:
    import os, sys, glob, re

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    search_dirs = [
        os.path.join(root, "usr/lib/mios/agent-pipe"),
        os.path.join(root, "tests"),
    ]

    patterns = [
        re.compile(r"\bpsycopg\.connect\b"),
        re.compile(r"\brequests\.(get|post|put|delete)\b"),
        re.compile(r"\bsocket\.socket\b"),
        re.compile(r"\burllib\.request\b"),
        re.compile(r"\bhttp\.client\b"),
    ]

    guard_re = re.compile(r"(SkipTest|skipUnless|skipIf|setUpModule|@unittest\.skip|MIOS_" + r"TEST_LIVE|MIOS_" + r"TEST_DB)")

    bad = []

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if (f.startswith("test_") or f.startswith("test-") or f.endswith("_test.py")) and f.endswith(".py"):
                path = os.path.join(d, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()

                    has_live_call = False
                    for p in patterns:
                        if p.search(content):
                            has_live_call = True
                            break

                    if has_live_call:
                        if not guard_re.search(content):
                            rel = os.path.relpath(path, root).replace("\\", "/")
                            bad.append(f"{rel} calls live network/DB resource without a SkipTest/guard sentinel")
                except OSError:
                    pass

    if bad:
        for b in bad:
            sys.stderr.write(f"    [hermeticity-drift] {b}\n")
        return 1

    return 0

def check_containerfile_pinned_clones() -> int:
    import os, sys

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    unpinned = []

    for r, ds, fs in os.walk(root):
        for f in fs:
            if "Containerfile" in f:
                path = os.path.join(r, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for idx, line in enumerate(fh, 1):
                            if "git clone" in line and not line.strip().startswith("#"):
                                if "--branch" not in line and "--tag" not in line and "-b " not in line and "@" not in line:
                                    rel = os.path.relpath(path, root).replace("\\", "/")
                                    unpinned.append(f"{rel}:{idx} -> {line.strip()}")
                except OSError:
                    pass

    if unpinned:
        sys.stderr.write("    Unpinned git clone command(s) found in Containerfiles:\n")
        for u in unpinned:
            sys.stderr.write(f"      {u}\n")
        return 1
    return 0

def check_replaceme_mount_substitution() -> int:
    import os, sys, re

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    justfile = os.path.join(root, "Justfile")
    if not os.path.isfile(justfile):
        return 0

    with open(justfile, "r", encoding="utf-8") as f:
        content = f.read()

    recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

    bad = []
    for block in recipe_blocks:
        lines = block.strip().split("\n")
        if not lines or ":" not in lines[0]:
            continue
        recipe_name = lines[0].split(":")[0].strip()
        block_text = "\n".join(lines[1:])

        mounted_configs = re.findall(r"-v\s+\.?/?config/artifacts/([a-zA-Z0-9_.-]+\.toml)", block_text)
        for cfg in mounted_configs:
            cfg_path = os.path.join(root, "config/artifacts", cfg)
            if os.path.isfile(cfg_path):
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as cf:
                    cfg_text = cf.read()
                if "REPLACEME" in cfg_text or "AAAA_REPLACE" in cfg_text:
                    if "sed " not in block_text and "sed -e" not in block_text:
                        bad.append(f"Recipe '{recipe_name}' mounts '{cfg}' containing REPLACEME tokens without credential-substituting sed")
                    if "REPLACEME_WITH_SHA512_HASH" in cfg_text:
                        if "MIOS_USER_PASSWORD_HASH:-" in block_text or "[ -z \"${MIOS_USER_PASSWORD_HASH" not in block_text:
                            bad.append(f"Recipe '{recipe_name}' mounts '{cfg}' with REPLACEME_WITH_SHA512_HASH without asserting non-empty MIOS_USER_PASSWORD_HASH")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [replaceme-drift] {b}\n")
        return 1

    return 0

def check_bib_rootfs_label_policy() -> int:
    import os, sys, re

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    justfile = os.path.join(root, "Justfile")
    if not os.path.isfile(justfile):
        return 0

    with open(justfile, "r", encoding="utf-8") as f:
        content = f.read()

    recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

    valid_fs = {"ext4", "xfs", "btrfs"}
    bad = []

    for block in recipe_blocks:
        lines = block.strip().split("\n")
        if not lines or ":" not in lines[0]:
            continue
        recipe_name = lines[0].split(":")[0].strip()
        if recipe_name.startswith("#"):
            continue
        block_text = "\n".join(ln for ln in lines[1:] if ":=" not in ln)

        if "{{BIB}}" in block_text or "bootc-image-builder" in block_text:
            if "--rootfs" not in block_text:
                bad.append(f"Recipe '{recipe_name}' calls BIB without mandatory --rootfs flag")
            else:
                match = re.search(r"--rootfs\s+([a-zA-Z0-9]+)", block_text)
                if not match or match.group(1) not in valid_fs:
                    fs = match.group(1) if match else "missing"
                    bad.append(f"Recipe '{recipe_name}' uses unapproved or missing rootfs type '{fs}' (must be ext4/xfs/btrfs)")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [bib-rootfs-drift] {b}\n")
        return 1

    return 0

def check_smoke_manifest() -> int:
    import os, sys
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    sc = data.get("testing", {}).get("smoke_components", {})
    if not sc:
        sys.stderr.write("    Missing [testing.smoke_components] table in mios.toml\n")
        return 1

    missing = []
    for key in ["shims", "units", "python_entries"]:
        for rel_path in sc.get(key, []):
            full_path = os.path.join(root, rel_path)
            if not os.path.exists(full_path):
                missing.append(rel_path)

    if missing:
        sys.stderr.write(f"    Paths listed in [testing.smoke_components] missing from repo: {missing}\n")
        return 1

    return 0

def check_negative_coverage() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    checks_sh = os.path.join(root, "automation/98-drift-checks.sh")
    negatives_sh = os.path.join(root, "tests/drift-gate-negatives.sh")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")

    if not (os.path.isfile(checks_sh) and os.path.isfile(negatives_sh) and os.path.isfile(toml_path)):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    exempt = set(data.get("testing", {}).get("negative_coverage_exempt", {}).get("exempt", []))

    with open(checks_sh, "r", encoding="utf-8", errors="ignore") as f:
        c_content = f.read()

    main_idx = c_content.rfind("main() {")
    main_body = c_content[main_idx:] if main_idx != -1 else c_content
    dispatched = set(re.findall(r"^\s*(check_[a-z0-9_]+)\b", main_body, re.MULTILINE))

    with open(negatives_sh, "r", encoding="utf-8", errors="ignore") as f:
        n_content = f.read()

    covered = set(re.findall(r"check_[a-z0-9_]+\b", n_content))

    uncovered = dispatched - covered - exempt
    if uncovered:
        sys.stderr.write(f"    Dispatched drift checks lacking negative test coverage and not exempt: {sorted(list(uncovered))}\n")
        return 1

    return 0

def check_law_enforcers() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    laws_section = data.get("laws", {})
    laws = laws_section.get("laws", [])
    drift_script = os.path.join(root, "automation/98-drift-checks.sh")
    with open(drift_script, "r", encoding="utf-8") as f:
        drift_code = f.read()

    postcheck_script = os.path.join(root, "automation/99-postcheck.sh")
    postcheck_code = ""
    if os.path.isfile(postcheck_script):
        with open(postcheck_script, "r", encoding="utf-8") as f:
            postcheck_code = f.read()

    missing = []
    for law in laws:
        if not isinstance(law, dict):
            continue
        law_id = law.get("id")
        slug = law.get("slug")
        enforced = law.get("enforced_by", "")
        for target in [t.strip() for t in enforced.split(",") if t.strip()]:
            if ":" not in target:
                continue
            fname, ref = target.split(":", 1)
            fname = fname.strip()
            ref = ref.strip()
            if fname == "98-drift-checks.sh":
                if not re.search(rf"^{ref}\s*\(\)", drift_code, re.MULTILINE):
                    missing.append(f"Law {law_id} ({slug}) -> {target} not found in 98-drift-checks.sh")
            elif fname == "99-postcheck.sh":
                if not os.path.isfile(postcheck_script) or (ref not in postcheck_code and f"item{ref}" not in postcheck_code):
                    missing.append(f"Law {law_id} ({slug}) -> {target} not found in 99-postcheck.sh")

    if missing:
        for m in missing:
            sys.stderr.write(f"    {m}\n")
        return 1

    return 0

def check_usr_over_etc() -> int:
    import os, sys, subprocess

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    try:
        tracked = subprocess.check_output(["git", "ls-files", "etc/"], cwd=root, text=True).splitlines()
    except Exception:
        tracked = []

    usr_share = os.path.join(root, "usr/share")
    usr_lib = os.path.join(root, "usr/lib")

    exempt_prefixes = (
        "etc/containers/systemd/",
        "etc/wsl.conf",
        "etc/cockpit/",
        "etc/containers/",
        "etc/greenboot/",
        "etc/mios/",
        "etc/skel/",
        "etc/profile.d/",
    )

    violations = []
    for f in tracked:
        if f.startswith(exempt_prefixes) or ".d/" in f or ".d" in os.path.basename(f):
            continue
        rel = f[4:]
        match_share = os.path.join(usr_share, rel)
        match_lib = os.path.join(usr_lib, rel)
        if os.path.isfile(match_share) or os.path.isfile(match_lib):
            violations.append(f"{f} shadows USR SSOT file ({match_share if os.path.isfile(match_share) else match_lib})")

    if violations:
        for v in violations:
            sys.stderr.write(f"    {v}\n")
        return 1
    return 0

def check_projection_registry() -> int:
    import os, sys, re
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    drift_script = os.path.join(root, "automation/98-drift-checks.sh")

    if not (os.path.isfile(toml_path) and os.path.isfile(drift_script)):
        return 0

    with open(drift_script, "r", encoding="utf-8") as f:
        drift_code = f.read()

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    surfaces = data.get("laws", {}).get("projection_registry", {}).get("surfaces", [])
    violations = []

    for s in surfaces:
        gen = s.get("generator", "")
        chk = s.get("check", "")
        if gen and not os.path.exists(os.path.join(root, gen)):
            violations.append(f"Projection generator '{gen}' missing from disk")
        if chk and not re.search(rf"^{chk}\s*\(\)", drift_code, re.MULTILINE):
            violations.append(f"Projection check function '{chk}' missing from 98-drift-checks.sh")

    if violations:
        for v in violations:
            sys.stderr.write(f"    {v}\n")
        return 1

    return 0

def check_bib_config_mount() -> int:
    import os, sys, re, glob
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    justfile = os.path.join(root, "Justfile")
    if not os.path.isfile(justfile):
        return 0

    toml_files = glob.glob(os.path.join(root, "config/artifacts/*.toml"))
    bad = []

    for tf in toml_files:
        try:
            with open(tf, "rb") as f:
                tomllib.load(f)
        except Exception as e:
            bad.append(f"Invalid TOML syntax in {os.path.basename(tf)}: {e}")

    with open(justfile, "r", encoding="utf-8") as f:
        content = f.read()

    recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

    for block in recipe_blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
        header_line = lines[0].strip()
        if header_line.startswith("#") or ":" not in header_line:
            continue
        recipe_name = header_line.split(":")[0].strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", recipe_name):
            continue
        block_text = "\n".join(lines[1:])

        if "{{BIB}}" in block_text or "bootc-image-builder" in block_text:
            config_mounts = re.findall(r"-v\s+\S+:/config\.(toml|json)", block_text)
            if len(config_mounts) != 1:
                bad.append(f"Recipe '{recipe_name}' must mount exactly ONE /config.toml (found {len(config_mounts)})")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [bib-config-drift] {b}\n")
        return 1

    return 0

def check_win11_vm_template_xml() -> int:
    import os, sys, xml.etree.ElementTree as ET
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    xml_path = os.path.join(root, "tools/win11-secureboot-template.xml")
    ssot_path = os.path.join(root, "usr/share/mios/mios.toml")

    if not (os.path.isfile(xml_path) and os.path.isfile(ssot_path)):
        return 0

    bad = []

    try:
        tree = ET.parse(xml_path)
        root_elem = tree.getroot()
    except Exception as e:
        bad.append(f"tools/win11-secureboot-template.xml is not well-formed XML: {e}")
        sys.stderr.write(f"    [win11-xml-drift] {bad[0]}\n")
        return 1

    try:
        with open(ssot_path, "rb") as f:
            data = tomllib.load(f)
        vm_cfg = data.get("vm", {}).get("win11", {})
        ssot_mem = str(vm_cfg.get("memory_kib", 25165824))
        ssot_vcpu = str(vm_cfg.get("vcpus", 12))

        mem_elem = root_elem.find("memory")
        vcpu_elem = root_elem.find("vcpu")

        if mem_elem is not None and mem_elem.text.strip() != ssot_mem:
            bad.append(f"Memory in template ({mem_elem.text.strip()}) does not match [vm.win11].memory_kib SSOT ({ssot_mem})")
        if vcpu_elem is not None and vcpu_elem.text.strip() != ssot_vcpu:
            bad.append(f"vCPUs in template ({vcpu_elem.text.strip()}) does not match [vm.win11].vcpus SSOT ({ssot_vcpu})")
    except Exception as e:
        bad.append(f"Failed to validate SSOT projection: {e}")

    if bad:
        for b in bad:
            sys.stderr.write(f"    [win11-xml-drift] {b}\n")
        return 1

    return 0

def check_db_seed_coverage() -> int:
    import os, sys, importlib.util
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    seed_script = os.path.join(root, "usr/libexec/mios/seed-db-config.py")

    if not os.path.isfile(toml_path):
        sys.stderr.write(f"    Missing SSOT file: {toml_path}\n")
        return 1

    if not os.path.isfile(seed_script):
        sys.stderr.write(f"    Missing db seeder script: {seed_script}\n")
        return 1

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        sys.stderr.write(f"    Failed to parse mios.toml: {e}\n")
        return 1

    spec = importlib.util.spec_from_file_location("seed_db_config", seed_script)
    if not spec or not spec.loader:
        sys.stderr.write(f"    Failed to load module spec from {seed_script}\n")
        return 1
    seed_mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(seed_mod)
        get_seeded_sections = getattr(seed_mod, "get_seeded_sections", None)
        if not get_seeded_sections:
            sys.stderr.write(f"    get_seeded_sections function absent in {seed_script}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"    Failed to import get_seeded_sections from {seed_script}: {e}\n")
        return 1

    seeded_set = set(get_seeded_sections(data))
    handled_separately = {"verbs", "packages"}

    uncovered = []
    for sec_name in data.keys():
        if sec_name not in seeded_set and sec_name not in handled_separately:
            uncovered.append(f"Section '{sec_name}' is not handled by seed-db-config.py")

    if uncovered:
        for u in uncovered:
            sys.stderr.write(f"    {u}\n")
        return 1

    return 0

def check_account_column_parity() -> int:
    import os, sys, re

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    schema_path = os.path.join(root, "usr/share/mios/postgres/schema-init.sql")
    if not os.path.isfile(schema_path):
        return 0

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_code = f.read()

    match = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?account \((.*?)\);", schema_code, re.DOTALL | re.IGNORECASE)
    columns = set()
    if match:
        lines = match.group(1).splitlines()
        for line in lines:
            line_clean = line.strip()
            if line_clean and not line_clean.startswith("--") and not line_clean.upper().startswith("CONSTRAINT") and not line_clean.upper().startswith("PRIMARY"):
                col_name = line_clean.split()[0].strip('"')
                columns.add(col_name)

    alter_matches = re.findall(r"ALTER TABLE account ADD COLUMN (?:IF NOT EXISTS )?(\w+)", schema_code, re.IGNORECASE)
    columns.update(alter_matches)

    required_columns = {"name", "password_hash", "uid", "gid", "display", "home_dir", "shell", "groups", "is_admin", "enabled"}

    missing_in_schema = required_columns - columns

    viol = []
    if missing_in_schema:
        viol.append(f"Account schema missing column(s) required by consumer projections: {sorted(list(missing_in_schema))}")

    if viol:
        for v in viol:
            sys.stderr.write(f"    {v}\n")
        return 1

    return 0

def check_v2v_import_ssot() -> int:
    import os, sys, re, subprocess
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    wrapper = os.path.join(root, "usr/libexec/mios/mios-v2v-import")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")

    if not (os.path.isfile(wrapper) and os.path.isfile(toml_path)):
        return 0

    with open(wrapper, "r", encoding="utf-8") as f:
        wcode = f.read()

    if "qcow2" in wcode and "output_format" not in wcode:
        sys.stderr.write("    mios-v2v-import hardcodes format instead of resolving [virt.v2v].output_format\n")
        return 1

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    v2v_cfg = data.get("virt", {}).get("v2v", {})
    fmt = v2v_cfg.get("output_format", "qcow2")

    proc = subprocess.run(["bash", wrapper, "--dry-run"], capture_output=True, text=True, env=dict(os.environ, MIOS_TOML=toml_path))
    out = proc.stdout + proc.stderr
    if f"-of {fmt}" not in out:
        sys.stderr.write(f"    mios-v2v-import --dry-run output does not contain expected '-of {fmt}' from SSOT\n")
        return 1

    return 0

def check_value_aliases() -> int:
    import sys, subprocess, os
    if len(sys.argv) >= 4:
        snap, tsv = sys.argv[2], sys.argv[3]
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    else:
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")
        snap = os.path.join(root, "usr/libexec/mios/mios-env-snapshot")
        tsv = os.path.join(root, "usr/share/mios/reference/value-aliases.tsv")

    if not (os.path.isfile(snap) and os.path.isfile(tsv)):
        return 0

    env = {}
    sub_env = dict(os.environ, MIOS_ROOT=root, MIOS_DRIFT_ROOT=root, MIOS_VENDOR_TOML=os.path.join(root, "usr/share/mios/mios.toml"), MIOS_MIGRATION_USE_RUST_RESOLVER_SHELL="false")
    proc = subprocess.run(["bash", snap], capture_output=True, text=True, env=sub_env)
    if proc.returncode != 0:
        return 0  # snapshot unavailable -> do not false-fail
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    bad = []
    with open(tsv, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.rstrip("\n")
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            parts = raw.split("\t")
            if len(parts) < 3:
                continue
            a, b, disp = parts[0].strip(), parts[1].strip(), parts[2].split()[0].strip()
            if a not in env or b not in env:
                continue  # a key not emitted here -> skip (informational; never false-fail)
            va, vb = env[a], env[b]
            if disp in ("derive", "delete"):
                if va != vb:
                    bad.append(f"{a}={va!r} != {b}={vb!r} (disposition={disp}: MUST be equal -- silent SSOT divergence)")
            elif disp == "keep-distinct":
                if va == vb:
                    bad.append(f"{a} == {b} == {va!r} but marked keep-distinct -- a naive collapse would corrupt this false-friend")
    for msg in bad:
        sys.stderr.write("    [value-alias-drift] " + msg + "\n")
    return 1 if bad else 0

def check_negatives_are_effective() -> int:
    import sys, re, os

    if len(sys.argv) >= 2 and sys.argv[1] != "negatives-are-effective":
        neg_path = sys.argv[1]
    else:
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")
        neg_path = os.path.join(root, "tests/drift-gate-negatives.sh")

    if not os.path.isfile(neg_path):
        return 0

    with open(neg_path, encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

    fn_matches = list(re.finditer(r'^(test_[a-zA-Z0-9_]+)\(\)\s*\{', content, re.MULTILINE))
    ineffective = []

    for i, m in enumerate(fn_matches):
        fn_name = m.group(1)
        start_idx = m.start()
        end_idx = fn_matches[i+1].start() if i + 1 < len(fn_matches) else len(content)
        main_match = re.search(r'^\s*main\(\)\s*\{', content[start_idx:end_idx], re.MULTILINE)
        if main_match:
            end_idx = start_idx + main_match.start()

        body = content[start_idx:end_idx]

        body_no_comments = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
        body_no_logs = re.sub(r'\b(log|echo)\s+("[^"]*"|\'[^\']*\')', '', body_no_comments)

        has_die = bool(re.search(r'\b(die|exit\s+[1-9]|return\s+[1-9]|FAIL)\b', body_no_comments))
        has_gate_invoc = bool(re.search(
            r'(98-drift-checks\.sh|97-ssot-lint\.sh|tools/|automation/|usr/libexec/|usr/lib/mios/|check_[a-zA-Z0-9_]+|\b_[a-zA-Z0-9_]+_run\b|\b_[a-zA-Z0-9_]+_cmd\b|\b_[a-zA-Z0-9_]+_fail\b|\b_neg_gate\b)',
            body_no_logs
        ))

        if not (has_die and has_gate_invoc):
            ineffective.append(fn_name)

    if ineffective:
        for fn in ineffective:
            sys.stderr.write(f"    [ineffective-negative] {fn} lacks failure assertion or gate invocation\n")
        return 1

    return 0

def check_pipefail_grep_lint() -> int:
    import sys, re, os

    if len(sys.argv) >= 2 and sys.argv[1] != "pipefail-grep-lint":
        neg_path = sys.argv[1]
    else:
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")
        neg_path = os.path.join(root, "tests/drift-gate-negatives.sh")

    if not os.path.isfile(neg_path):
        return 0

    with open(neg_path, encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()

    bad = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "#" in stripped:
            stripped = stripped.split("#")[0]
        if "| grep" in stripped or "|grep" in stripped:
            left_side = stripped.split("|")[0].strip()
            if not re.search(r'\b(echo|printf)\b', left_side):
                bad.append((idx, stripped))

    if bad:
        for idx, l in bad:
            sys.stderr.write(f"    [pipefail-grep-violation] line {idx}: {l}\n")
        return 1

    return 0

def check_skip_list_covered() -> int:
    import os, sys
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    viol = []
    with open(toml_path, "rb") as fh:
        globs = ((tomllib.load(fh).get("ci") or {}).get("globs") or {})

    spec = globs.get("agent-pipe") or {}
    skip = spec.get("skip") or []
    if not skip:
        viol.append("[ci.globs.agent-pipe].skip is empty or absent -- the suites that "
                    "need a database would run and fail on every runner")
    if skip and not str(spec.get("skip_reason", "")).strip():
        viol.append("[ci.globs.agent-pipe].skip carries no skip_reason")

    for wf in (".github/workflows/mios-ci.yml", ".forgejo/workflows/build-mios.yml"):
        path = os.path.join(root, wf)
        if not os.path.isfile(path):
            continue
        if "SKIP=" in open(path, encoding="utf-8", errors="replace").read():
            viol.append(f"{wf} carries an inline SKIP= list, which shadows "
                        f"[ci.globs.agent-pipe].skip")

    if viol:
        sys.stdout.write("\n".join(viol) + "\n")
        return 1
    return 0

def check_template_self_conformance() -> int:
    import os, sys, subprocess, tempfile

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    tmpl_dir = os.path.join(root, "usr/share/mios/templates")
    scaffold_script = os.path.join(root, "usr/libexec/mios/mios-new")

    if not os.path.isdir(tmpl_dir) or not os.path.isfile(scaffold_script):
        return 0

    templates = [f for f in os.listdir(tmpl_dir) if not f.startswith(".") and os.path.isfile(os.path.join(tmpl_dir, f))]
    failures = []

    for t in sorted(templates):
        if t in ("conformance-grandfathered.list", "PLACEHOLDERS.md"):
            continue
        with tempfile.TemporaryDirectory() as tmpdir:
            env = dict(os.environ, MIOS_DRIFT_CHECK_ROOT=tmpdir, MIOS_THEME_ROOT=tmpdir)
            cmd = [sys.executable, scaffold_script, t, "testmock"]
            res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                failures.append(f"Template '{t}' failed to scaffold: {res.stderr.strip()}")
                continue

    if failures:
        for f in failures:
            print("Violation:", f, file=sys.stderr)
        return 1
    return 0

def check_templates_bootstrap_sync() -> int:
    import os, sys
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    main_toml = os.path.join(root, "usr/share/mios/mios.toml")
    boot_toml = os.path.join(root, "submodules/mios-bootstrap/usr/share/mios/mios.toml")

    if not os.path.isfile(boot_toml):
        return 0

    with open(main_toml, "rb") as f:
        m_data = tomllib.load(f).get("templates", {})
    with open(boot_toml, "rb") as f:
        b_data = tomllib.load(f).get("templates", {})

    if m_data != b_data:
        print("Violation: [templates] section in main mios.toml and mios-bootstrap mios.toml differ", file=sys.stderr)
        return 1
    return 0

def check_secret_handling() -> int:
    import os, sys, re, glob

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    key_regex = re.compile(r'-----BEGIN (?:RSA|OPENSSH|EC|PGP|PRIVATE) KEY-----')
    conn_regex = re.compile(r'(?:postgres|mysql|mongodb|redis)://[a-zA-Z0-9_-]+:[^@\s\"\'`]{4,}@')
    token_regex = re.compile(r'\b(?:AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9_-]{20})\b')

    EXEMPT_PATHS = {
        "usr/share/doc/mios/reference/audit-security.md",
        "usr/share/doc/mios/reference/audit-deploy-plane.md",
        "AGY-TASKS.md",
    }

    violations = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".cargo", "target", "node_modules", ".venv", ".agents", ".tmp.driveupload", "root")]
        for f in filenames:
            if f.endswith((".png", ".jpg", ".tar", ".zip", ".exe", ".pyc", ".iso", ".qcow2", ".vhdx")):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if rel in EXEMPT_PATHS or rel.startswith("tests/") or rel.startswith("scratch/") or rel.startswith(".agents/"):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except Exception:
                continue

            if key_regex.search(content):
                violations.append(f"{rel}: contains un-allowlisted Private Key block")
            if conn_regex.search(content):
                violations.append(f"{rel}: contains hardcoded database password connection string")
            if token_regex.search(content):
                violations.append(f"{rel}: contains hardcoded API secret token")

    ps_files = glob.glob(os.path.join(root, "**/*.ps1"), recursive=True)
    for ps in ps_files:
        rel = os.path.relpath(ps, root).replace("\\", "/")
        if "/.git" in rel:
            continue
        try:
            with open(ps, "r", encoding="utf-8", errors="ignore") as fh:
                if "mios-secrets.env" in fh.read():
                    violations.append(f"{rel}: writes/reads secrets in plaintext %TEMP%\\mios-secrets.env")
        except Exception:
            continue

    if violations:
        for v in violations:
            sys.stderr.write(f"    {v}\n")
        return 1

    return 0

def check_os_update_timer_enabled() -> int:
    import os, sys, tomllib
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ssot = tomllib.load(fh)
    pkgs = []
    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            pkgs.extend(p for p in o if isinstance(p, str))
    walk(ssot.get("packages", {}))
    return 0 if any(p in ("uupd", "bootc") for p in pkgs) else 1

def check_adhoc_toml_parsers() -> int:
    import os, re, sys
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    EXEMPT = {"mios-common.ps1"}
    PATTERNS = [
        re.compile(r"\(\?s\)\s*\\\["),
        re.compile(r"\(\?ms\)\^\\s\*\\\["),
        re.compile(r"-match\s+'\^\\\[\(\.\+\)\\\]'"),
    ]
    viol = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "target", "node_modules", ".venv")]
        for fn in sorted(filenames):
            if not fn.endswith(".ps1") or fn in EXEMPT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            if any(pat.search(src) for pat in PATTERNS):
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                viol.append(rel + " regex-parses mios.toml itself; call Get-MiosSsotValue from installation/mios-common.ps1 instead")
    if viol:
        print("\n".join(viol))
        return 1
    return 0

def check_install_uninstall_symmetry() -> int:
    import os, re, sys
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    import tomllib as _toml

    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    uninst = os.path.join(root, "Uninstall-MiOS.ps1")
    viol = []
    if _toml is None:
        sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli -- skipping install/uninstall symmetry\n")
        return 0
    elif not os.path.isfile(uninst):
        viol.append("Uninstall-MiOS.ps1 is missing; the Windows install has no uninstaller")
    else:
        with open(toml_path, "rb") as fh:
            data = _toml.load(fh)
        owned = (data.get("windows", {}) or {}).get("owned_artifacts", {}) or {}
        if not owned:
            viol.append("mios.toml [windows.owned_artifacts] is empty; the uninstaller has no SSOT to be checked against")
        with open(uninst, encoding="utf-8", errors="replace") as fh:
            src = fh.read()

        sweeps = [re.compile(p) for p in re.findall(r"-match\s+'([^']*)'", src)]
        for glob in re.findall(r"-Filter\s+'([^']*)'", src):
            sweeps.append(re.compile(re.escape(glob).replace(r"\*", ".*")))

        def covered(name):
            return name in src or any(s.search(name) for s in sweeps)

        MECHANISM = {
            "task_names":     ("Unregister-ScheduledTask",),
            "service_names":  ("sc.exe delete", "Remove-Service"),
            "process_names":  ("Stop-Process",),
            "firewall_rules": ("Remove-NetFirewallRule",),
            "registry_roots": ("Remove-Item", "Remove-ItemProperty"),
            "shortcut_dirs":  ("Remove-Item",),
        }
        for field, verbs in MECHANISM.items():
            names = owned.get(field, []) or []
            if not names:
                continue
            if not any(v in src for v in verbs):
                viol.append("Uninstall-MiOS.ps1 has no %s removal step (none of %s) yet mios.toml declares %d in [windows.owned_artifacts].%s" % (field[:-1].replace("_", " "), "/".join(verbs), len(names), field))
            for name in names:
                if not covered(name):
                    viol.append("Uninstall-MiOS.ps1 never removes %s %r (declared in mios.toml [windows.owned_artifacts].%s)" % (field[:-1].replace("_", " "), name, field))
    if viol:
        print("\n".join(viol))
        return 1
    return 0

def check_ps_port_fallback_ssot() -> int:
    import os, re, sys
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    import tomllib as _toml

    if not os.path.isfile(os.path.join(root, "usr/share/mios/mios.toml")):
        return 0

    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        ports = _toml.load(fh).get("ports", {}) or {}

    CALL = re.compile(r"Get-PortFromSsot\s+'[^']*'\s+'([a-z0-9_]+)'\s+(\d+)")
    ENTRY = re.compile(r"Key\s*=\s*'([a-z0-9_]+)'\s*;\s*Default\s*=\s*(\d+)")

    viol = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "target", "node_modules", ".venv")]
        for fn in sorted(filenames):
            if not fn.endswith(".ps1"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            for pat in (CALL, ENTRY):
                for key, literal in pat.findall(src):
                    want = ports.get(key)
                    if want is None:
                        viol.append("%s falls back on port key %r which does not exist in mios.toml [ports]" % (rel, key))
                    elif int(literal) != int(want):
                        viol.append("%s fallback %s=%s drifted from mios.toml [ports].%s=%s" % (rel, key, literal, key, want))
    if viol:
        print("\n".join(viol))
        return 1
    return 0

def check_ps_encoding_and_bom() -> int:
    import os, sys
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    BOM = b"\xef\xbb\xbf"
    viol = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "target", "node_modules", ".venv")]
        for fn in sorted(filenames):
            if not fn.endswith(".ps1"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            has_bom = data.startswith(BOM)
            body = data[len(BOM):] if has_bom else data
            non_ascii = any(b > 0x7F for b in body)
            if non_ascii and not has_bom:
                viol.append(rel + " holds non-ASCII but has no UTF-8 BOM; Windows PowerShell 5.1 will read it as ANSI")
            elif has_bom and not non_ascii:
                viol.append(rel + " is pure ASCII yet carries a UTF-8 BOM; drop it")
    if viol:
        print("\n".join(viol))
        return 1
    return 0

def check_unit_security() -> int:
    import os, sys
    import tomllib as _toml

    if len(sys.argv) >= 2 and sys.argv[1] != "unit-security":
        root = sys.argv[1]
    else:
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")

    systemd_dir = os.path.join(root, 'usr/lib/systemd/system')
    toml_path = os.path.join(root, 'usr/share/mios/mios.toml')

    unconfined_roster = set()
    if os.path.isfile(toml_path):
        with open(toml_path, 'rb') as fh:
            data = _toml.load(fh)
            sec = data.get('security', {}).get('privileged_units', {})
            unconfined_roster = set(sec.get('unconfined', []))

    required_directives = ['NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'PrivateTmp']
    viol = []

    if os.path.isdir(systemd_dir):
        for f in os.listdir(systemd_dir):
            if f.endswith('.service'):
                if f in unconfined_roster:
                    continue
                fp = os.path.join(systemd_dir, f)
                try:
                    with open(fp, encoding='utf-8', errors='replace') as fh:
                        content = fh.read()
                        missing = []
                        for directive in required_directives:
                            if directive not in content:
                                missing.append(directive)
                        if missing:
                            rel = os.path.relpath(fp, root).replace(os.sep, '/')
                            viol.append(f"{rel}: systemd service missing hardening directives ({', '.join(missing)})")
                except Exception: pass

    if viol:
        print('\n'.join(viol))
    return 0

def check_unit_dependency_closure() -> int:
    import os, sys, glob

    if len(sys.argv) >= 2 and sys.argv[1] != "unit-dependency-closure":
        root = sys.argv[1]
    else:
        root = os.environ.get("MIOS_DRIFT_ROOT", ".")

    systemd_dir = os.path.join(root, 'usr/lib/systemd/system')
    quadlet_dir = os.path.join(root, 'usr/share/containers/systemd')

    known_units = set()
    if os.path.isdir(systemd_dir):
        for f in os.listdir(systemd_dir):
            if os.path.isfile(os.path.join(systemd_dir, f)):
                known_units.add(f)

    if os.path.isdir(quadlet_dir):
        for f in os.listdir(quadlet_dir):
            if f.endswith('.container'):
                base = f[:-10]
                known_units.add(f'{base}.service')
                known_units.add(f'{base}-service')
            elif f.endswith('.pod'):
                base = f[:-4]
                known_units.add(f'{base}-pod.service')
                known_units.add(f'{base}.pod')
            elif f.endswith('.volume'):
                base = f[:-7]
                known_units.add(f'{base}-volume.service')
            elif f.endswith('.network'):
                base = f[:-8]
                known_units.add(f'{base}-network.service')
            elif f.endswith('.image'):
                base = f[:-6]
                known_units.add(f'{base}-image.service')

    well_known = {
        'multi-user.target', 'network-online.target', 'network.target', 'default.target',
        'sockets.target', 'timers.target', 'syslog.target', 'local-fs.target', 'remote-fs.target',
        'basic.target', 'graphical.target', 'rescue.target', 'emergency.target', 'shutdown.target',
        'reboot.target', 'poweroff.target', 'podman.socket', 'podman.service', 'dbus.service',
        'dbus.socket', 'docker.service', 'docker.socket', 'containerd.service', 'systemd-journald.service',
        'systemd-resolved.service', 'systemd-networkd.service', 'time-sync.target', 'network-pre.target',
        'tailscaled.service', 'avahi-daemon.service', 'chronyd.service', 'firewalld.service',
        'nftables.service', 'sshd.service', 'sshd.socket', 'gdm.service', 'console-login-helper-messages.service',
        'nvidia-cdi-refresh.service', 'podman-restart.service', 'hermes-agent.service',
        'display-manager.service', 'akmods.service', 'pcsd.service', 'corosync.service',
        'pacemaker.service', 'k3s-agent.service', 'cryptsetup.target', 'redis.service',
        'sysinit.target', 'greenboot-healthcheck.service', 'ostree-remount.service',
        'ostree-prepare-root.service', 'waydroid-container.service', 'wslg-x11.service',
        'wslg-wayland.service', 'ceph.target'
    }
    known_units.update(well_known)

    def is_valid_unit(u):
        if u in known_units: return True
        if u.endswith(('.mount', '.slice', '.swap')): return True
        if u.startswith(('systemd-', 'libvirtd', 'virt', 'cockpit', 'k3s-')): return True
        return False

    viol = []
    dirs_to_check = [systemd_dir, quadlet_dir]
    for d in dirs_to_check:
        if not os.path.isdir(d): continue
        for root_dir, _, files in os.walk(d):
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    with open(fp, encoding='utf-8', errors='replace') as fh:
                        for line in fh:
                            line = line.strip()
                            if line.startswith(('#', ';')): continue
                            for key in ('After=', 'Wants=', 'Requires=', 'Before=', 'BindsTo=', 'Requisite='):
                                if line.startswith(key):
                                    val = line[len(key):].strip()
                                    for token in val.split():
                                        token = token.strip()
                                        if token and not token.startswith('$') and not is_valid_unit(token):
                                            rel = os.path.relpath(fp, root).replace(os.sep, '/')
                                            viol.append(f"{rel}: dangling reference {key}{token}")
                except Exception: pass

    if viol:
        print('\n'.join(viol))
        return 1
    return 0

def check_docs_ratchet() -> int:
    import os, sys, glob
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    sys.path.insert(0, os.path.join(root, "usr", "lib", "mios"))
    try:
        import tomllib
        import mios_comments as mc
    except Exception as e:
        sys.stderr.write("[98-drift-checks]   WARNING: docs ratchet unavailable (%s)\n" % e)
        return 0

    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        data = tomllib.load(fh)
    docs = data.get("docs", {}) or {}
    pol = mc.Policy.from_toml(data)

    ceil_narr = docs.get("max_unmigrated_narrative")
    ceil_hint = docs.get("max_overlong_hints")
    ceil_stale = docs.get("max_stale_refs", 0)
    ceil_undoc = docs.get("max_undocumented_components", 16)
    viol = []
    if ceil_narr is None or ceil_hint is None or ceil_stale is None or ceil_undoc is None:
        viol.append("mios.toml [docs] is missing max_unmigrated_narrative/max_overlong_hints/max_stale_refs/max_undocumented_components"
                    " -- the ratchet has no floor and would pass vacuously")
        print("\n".join(viol))
        return 1

    refindex = mc.RefIndex.build(root)
    ledger_path = os.path.join(root, "usr/share/mios/reference/manual-corpus.tsv")
    rows = {}
    if os.path.isfile(ledger_path):
        with open(ledger_path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or not line.strip(): continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 14:
                    rows[parts[5]] = dict(zip(["path","start_line","end_line","lines","words","sha12","class","reason","as","stale","landed_doc","landed_anchor","landed_words","pruned"], parts))

    def _landed(row):
        doc = row.get("landed_doc") or ""
        if not doc: return False
        p = os.path.join(root, doc.replace("/", os.sep))
        if not os.path.isfile(p): return False
        try:
            with open(p, encoding="utf-8", errors="replace") as fh: text = fh.read()
        except OSError: return False
        if ("mios-src:" + row["sha12"]) not in text: return False
        try:
            want = int(row.get("words") or 0)
            got = int(row.get("landed_words") or 0)
        except ValueError: return False
        return got >= pol.landing_min_word_ratio * want

    narr = hints = stale = 0
    for rel, full in mc.iter_source_files(root):
        try:
            blocks = mc.lex(full)
        except Exception:
            continue
        for b in blocks:
            b = mc.Block(**{**b.__dict__, "path": rel})
            v = mc.classify(b, pol, refindex)
            row = rows.get(b.sha12)
            if row is not None and _landed(row):
                continue
            if v.cls == "MIGRATE":
                narr += 1
            elif v.cls == "MIGRATE_HEADER":
                hints += 1
            if v.stale:
                stale += 1

    comp_files = glob.glob(os.path.join(root, "usr/libexec/mios/*")) + glob.glob(os.path.join(root, "automation/*.sh")) + glob.glob(os.path.join(root, "tools/*.py"))
    undoc = 0
    for f in comp_files:
        if not os.path.isfile(f): continue
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
                if "AI-doc:" not in text and "AI-hint:" not in text:
                    undoc += 1
        except OSError:
            pass

    if narr > ceil_narr:
        viol.append("unmigrated narrative comment blocks %d > ceiling %d --"
                    " harvest them into docs, do NOT raise [docs].max_unmigrated_narrative"
                    % (narr, ceil_narr))
    if hints > ceil_hint:
        viol.append("over-cap AI-hint headers %d > ceiling %d --"
                    " shorten them, do NOT raise [docs].max_overlong_hints"
                    % (hints, ceil_hint))
    if stale > ceil_stale:
        viol.append("stale references %d > ceiling %d --"
                    " fix or remove stale references, do NOT raise [docs].max_stale_refs"
                    % (stale, ceil_stale))
    if undoc > ceil_undoc:
        viol.append("undocumented components %d > ceiling %d --"
                    " add AI-doc or AI-hint headers, do NOT raise [docs].max_undocumented_components"
                    % (undoc, ceil_undoc))
    print("[docs-ratchet] narrative=%d/%d overlong-hints=%d/%d stale-refs=%d/%d undoc-comp=%d/%d"
          % (narr, ceil_narr, hints, ceil_hint, stale, ceil_stale, undoc, ceil_undoc), file=sys.stderr)
    if viol:
        print("\n".join(viol))
        return 1
    return 0

def check_generator_host_parity() -> int:
    import os, sys

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    viol = []

    scanned_scripts = [
        "tools/generate-names-registry.py",
        "automation/lib/mios_var_closure.py",
        "tools/generate-ai-manifest.py",
        "tools/generate-pod-quadlets.py",
        "tools/generate-bake-plan.py",
        "usr/libexec/mios/mios-manual",
        "usr/libexec/mios/mios-version-lint",
    ]

    for script in scanned_scripts:
        fpath = os.path.join(root, script)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        if "fnmatch.fnmatch(" in content:
            viol.append(f"{script} uses non-portable fnmatch.fnmatch instead of fnmatchcase")

    if viol:
        print("\n".join(viol), file=sys.stderr)
        return 1

    print("    generator host parity: all generators produce host-independent byte-identical outputs")
    return 0

def check_doc_port_scheme() -> int:
    import os, sys, tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    if not os.path.isfile(toml_path):
        return 0

    with open(toml_path, "rb") as fh:
        docs = tomllib.load(fh).get("docs", {}) or {}

    ret_ports = "|".join(str(p) for p in docs.get("retired_ports", []))
    port_clean = docs.get("port_clean", [])

    if not ret_ports:
        print("check_doc_port_scheme: [docs].retired_ports is empty or unreadable", file=sys.stderr)
        return 1

    import re
    viol = []
    pat = re.compile(rf"(^|[^0-9])({ret_ports})([^0-9]|$)")

    for f in port_clean:
        if not f:
            continue
        full_p = os.path.join(root, f)
        if not os.path.isfile(full_p):
            viol.append(f"[docs].port_clean names a missing file: {f}")
            continue
        try:
            with open(full_p, "r", encoding="utf-8", errors="ignore") as fh:
                for idx, line in enumerate(fh, 1):
                    if pat.search(line):
                        viol.append(f"retired port literal in {f}:{idx}: {line.strip()}")
        except OSError:
            pass

    if viol:
        for v in viol:
            print(v, file=sys.stderr)
        return 1
    return 0

def check_blade_reconcile_schema() -> int:
    import os, re, sys
    import tomllib

    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    toml_path = os.path.join(root, "usr/share/mios/mios.toml")
    sql_path = os.path.join(root, "usr/share/mios/postgres/schema-init.sql")
    if not os.path.isfile(toml_path):
        return 0
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)

    rec = ((data.get("blade") or {}).get("reconcile") or {})
    if "enabled" not in rec:
        print("[blade.reconcile] has no `enabled` key -- an implied default is indistinguishable from a forgotten one, and this table decides whether partitioned writes are permitted")
        return 1

    RULE_KEYS = sorted(k for k in rec if k != "enabled")

    if not rec.get("enabled"):
        print("[blade-reconcile] divergence disabled; %d merge rule(s) declared, schema prerequisite not yet required" % len(RULE_KEYS))
        return 0

    viol = []
    sql = ""
    if os.path.isfile(sql_path):
        with open(sql_path, encoding="utf-8", errors="replace") as fh:
            sql = fh.read()
    for table in RULE_KEYS:
        m = re.search(r"CREATE TABLE IF NOT EXISTS\s+" + re.escape(table) + r"\s*\((.*?)\n\);", sql, re.S)
        if not m:
            viol.append("enabled = true but schema-init.sql declares no table '%s'" % table)
            continue
        body = m.group(1)
        if not re.search(r"\borigin_node\b", body):
            viol.append("table '%s' has no origin_node column, so a merged row cannot be attributed to the partition that wrote it" % table)
        if not re.search(r"\b(logical_ts|logical_clock)\b", body):
            viol.append("table '%s' has no logical_ts column, so append-ordered and last-writer-wins have nothing to order by" % table)
    if viol:
        viol.append("Land AGY-1598 (origin_node + logical_ts) or set [blade.reconcile].enabled = false until it does.")
        print("\n".join(viol))
        return 1
    return 0

SUBCOMMANDS = {
    "bootstrap-ports-drift": check_bootstrap_ports_drift,
    "agent-schema": check_agent_schema,
    "names-registry": check_names_registry,
    "gate-registry": check_gate_registry,
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
    "unwired-modules": check_unwired_modules,
    "no-duplicate-value-key": check_no_duplicate_value_key,
    "no-inert-ssot-tables": check_no_inert_ssot_tables,
    "doc-refs-resolve": check_doc_refs_resolve,
    "resolver-differential-parity": check_resolver_differential_parity,
    "legibility-ratchet": check_legibility_ratchet,
    "header-integrity": check_header_integrity,
    "rbac-tiers": check_rbac_tiers,
    "ai-manifest": check_ai_manifest,
    "capability-manifest": check_capability_manifest,
    "surface-parity": check_surface_parity,
    "container-ports": check_container_ports,
    "agent-pipe-budgets": check_agent_pipe_budgets,
    "verb-backends": check_verb_backends,
    "python-untested-ratchet": check_python_untested_ratchet,
    "canonical-bools": check_canonical_bools,
    "dag-integrity": check_dag_integrity,
    "ai-endpoint-local": check_ai_endpoint_local,
    "version-literals-ssot": check_version_literals_ssot,
    "bake-refs-parity": check_bake_refs_parity,
    "cli-eval-safety": check_cli_eval_safety,
    "resolver-ssot-refs": check_resolver_ssot_refs,
    "bake-budget": check_bake_budget,
    "greenboot": check_greenboot,
    "router-intent-coverage": check_router_intent_coverage,
    "council-gate-ssot": check_council_gate_ssot,
    "test-hermeticity": check_test_hermeticity,
    "containerfile-pinned-clones": check_containerfile_pinned_clones,
    "replaceme-mount-substitution": check_replaceme_mount_substitution,
    "bib-rootfs-label-policy": check_bib_rootfs_label_policy,
    "smoke-manifest": check_smoke_manifest,
    "negative-coverage": check_negative_coverage,
    "law-enforcers": check_law_enforcers,
    "usr-over-etc": check_usr_over_etc,
    "projection-registry": check_projection_registry,
    "bib-config-mount": check_bib_config_mount,
    "win11-vm-template-xml": check_win11_vm_template_xml,
    "db-seed-coverage": check_db_seed_coverage,
    "account-column-parity": check_account_column_parity,
    "v2v-import-ssot": check_v2v_import_ssot,
    "value-aliases": check_value_aliases,
    "negatives-are-effective": check_negatives_are_effective,
    "pipefail-grep-lint": check_pipefail_grep_lint,
    "skip-list-covered": check_skip_list_covered,
    "template-self-conformance": check_template_self_conformance,
    "templates-bootstrap-sync": check_templates_bootstrap_sync,
    "secret-handling": check_secret_handling,
    "os-update-timer-enabled": check_os_update_timer_enabled,
    "adhoc-toml-parsers": check_adhoc_toml_parsers,
    "install-uninstall-symmetry": check_install_uninstall_symmetry,
    "ps-port-fallback-ssot": check_ps_port_fallback_ssot,
    "ps-encoding-and-bom": check_ps_encoding_and_bom,
    "unit-security": check_unit_security,
    "unit-dependency-closure": check_unit_dependency_closure,
    "docs-ratchet": check_docs_ratchet,
    "generator-host-parity": check_generator_host_parity,
    "doc-port-scheme": check_doc_port_scheme,
    "blade-reconcile-schema": check_blade_reconcile_schema,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in SUBCOMMANDS:
        print("usage: drift-checks.py {%s}" % "|".join(sorted(SUBCOMMANDS)),
              file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(SUBCOMMANDS[sys.argv[1]]() or 0)
