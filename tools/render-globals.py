#!/usr/bin/env python3
# AI-hint: Generates automation/lib/globals.sh and globals.ps1 IN FULL from mios.toml -- they are 100% generated artefacts with zero hand-written constants ...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_render_globals_py.md
from __future__ import annotations

import os
import re
import sys

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("MIOS_TOML_ROOT", ROOT)
sys.path.insert(0, os.path.join(ROOT, "usr/lib/mios"))

import mios_toml  # noqa: E402

SH_OUT = os.path.join(ROOT, "automation/lib/globals.sh")
PS_OUT = os.path.join(ROOT, "automation/lib/globals.ps1")

# Emitted in dependency order: a template may only reference a name already set.
_SECTION_ORDER = ("identity", "services", "versions", "image", "ports", "paths", "units", "urls")

_TEMPLATE_RE = re.compile(r"\$\{(MIOS_[A-Z0-9_]+)\}")
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]")
# Anything that could terminate/alter `"${VAR:=word}"` word-expansion.
_SH_UNSAFE_RE = re.compile(r"""['"`$\\{}\n\r]""")


def _sanitize(name: str) -> str:
    """Force a legal identifier in BOTH sh and PowerShell."""
    return _UNSAFE_NAME_RE.sub("_", name)


def build_exports() -> dict:
    """Resolve mios.toml exactly as userenv.sh does: walk + aliases + palette."""
    data = mios_toml.load_merged()
    ports = data.get("ports") or {}
    try:
        stack_offset = int(ports.get("stack_id", 0)) * 10000
    except (TypeError, ValueError):
        stack_offset = 0

    exports: dict[str, str] = {}
    for dotted, val in mios_toml.walk(data):
        section = dotted.split(".")[0]
        # Honour the resolver's own partition: [containers], [messages],
        # [verbs] etc. are data, not environment. Emitting them produced
        # invalid identifiers (a container key like `mios-llm-worker@` became
        # MIOS_..._WORKER@_... which is neither valid sh nor valid PowerShell).
        if section in mios_toml.EXCLUDED_SECTIONS:
            continue
        if dotted.endswith(".comment") or dotted.split(".")[-1] == "comment":
            continue
        processed = mios_toml.process_val(dotted, val, stack_offset)
        if processed == "":
            continue
        canonical = _sanitize("MIOS_" + dotted.upper().replace(".", "_"))
        if not (section in mios_toml.WALK_MOSTLY_DEAD
                and canonical not in mios_toml.WALK_EMIT_KEEP):
            exports[canonical] = processed
        for alias in mios_toml.get_aliases(dotted):
            exports[_sanitize(alias)] = processed

    for name, value in (mios_toml.colors(data) or {}).items():
        exports.setdefault("MIOS_COLOR_" + name.upper(), value)

    # get_aliases canon-remaps ports.guacamole_web -> MIOS_PORT_GUACAMOLE, but
    # there is no [ports].guacamole key, so emitting it trips the globals-parity
    # gate (which requires MIOS_PORT_<X> <-> [ports].<x>). The hand-written
    # resolvers never defined it either -- MIOS_PORT_GUACAMOLE_WEB is the real
    # name. It stays available from userenv.sh at runtime.
    for dead in ("MIOS_PORT_GUACAMOLE", "MIOS_GUACAMOLE_PORT"):
        exports.pop(dead, None)

    return {k: (v if isinstance(v, str) else str(v)) for k, v in exports.items()}


def ordered_names(exports: dict) -> list:
    """Names topologically sorted so `${...}` templates resolve against earlier lines."""
    deps = {}
    for k, v in exports.items():
        deps[k] = set(_TEMPLATE_RE.findall(v)) & set(exports.keys())
    
    res = []
    visited = set()
    visiting = set()

    def visit(node):
        if node in visited:
            return
        if node in visiting:
            visited.add(node)
            res.append(node)
            return
        visiting.add(node)
        for dep in sorted(deps.get(node, [])):
            visit(dep)
        visiting.remove(node)
        if node not in visited:
            visited.add(node)
            res.append(node)

    for name in sorted(exports.keys()):
        visit(name)
    return res


def expand_template(value: str, lang: str) -> str:
    """Keep `${MIOS_X}` live in the emitted language rather than baking a literal."""
    if lang == "sh":
        return value
    return _TEMPLATE_RE.sub(lambda m: "$($script:%s)" % m.group(1), value)


HEADER_SH = '''#!/usr/bin/env bash
# GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
# AI-related: usr/share/mios/mios.toml, automation/lib/globals.ps1, tools/render-globals.py
# AI-functions: _mios_resolve_version
#
# Shell sibling of automation/lib/globals.ps1 -- both are rendered from the same
# SSOT by the same generator, so they cannot diverge. Dot-source from any entry
# point; every constant uses `:=` so an environment variable exported BEFORE
# sourcing still wins.

_mios_resolve_version() {
    local v=""
    if   [[ -n "${MIOS_VERSION:-}" ]];        then v="$MIOS_VERSION"
    elif [[ -f /ctx/VERSION ]];               then v="$(cat /ctx/VERSION)"
    elif [[ -f /usr/share/mios/VERSION ]];    then v="$(cat /usr/share/mios/VERSION)"
    else
        local _root
        _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
        if [[ -n "$_root" && -f "${_root}/VERSION" ]]; then
            v="$(cat "${_root}/VERSION")"
        fi
    fi
    printf '%s' "${v:-VERSION_FALLBACK}" | tr -d '[:space:]'
}
: "${MIOS_VERSION:=$(_mios_resolve_version)}"
export MIOS_VERSION
'''

# Raw: the emitted PowerShell carries Windows path separators ('..\\..\\VERSION'),
# which Python would otherwise read as escape sequences.
HEADER_PS = r'''# GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
# AI-related: usr/share/mios/mios.toml, automation/lib/globals.sh, tools/render-globals.py
# AI-functions: Resolve-MiosVersion
#
# PowerShell sibling of automation/lib/globals.sh -- both are rendered from the
# same SSOT by the same generator, so they cannot diverge. Dot-source from any
# entry point:
#
#     . (Join-Path $PSScriptRoot 'automation/lib/globals.ps1')
#
# Override any constant with an environment variable BEFORE dot-sourcing -- e.g.
# `$env:MIOS_VERSION = ' - rc1'; . globals.ps1`.

function Resolve-MiosVersion {
    if ($env:MIOS_VERSION) { return ([string]$env:MIOS_VERSION).Trim() }
    foreach ($p in @(
        '/ctx/VERSION',
        '/usr/share/mios/VERSION',
        (Join-Path $PSScriptRoot '..\..\VERSION')
    )) {
        if ($p -and (Test-Path $p)) {
            $v = (Get-Content $p -EA SilentlyContinue | Out-String).Trim()
            if ($v) { return $v }
        }
    }
    return 'VERSION_FALLBACK'
}
$script:MIOS_VERSION = Resolve-MiosVersion

function Resolve-MiosDistro {
    param([string]$Default = 'podman-MiOS-DEV')
    if ($env:MIOS_WSL_DISTRO) { return $env:MIOS_WSL_DISTRO }
    try {
        $lxss = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
        if (Test-Path $lxss) {
            $all = @(Get-ChildItem $lxss -ErrorAction SilentlyContinue |
                     ForEach-Object { (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DistributionName } |
                     Where-Object { $_ })
            $resolved = ($all | Where-Object { $_ -match 'MiOS' } | Select-Object -First 1)
            if ($resolved) { return $resolved }
            $defGuid = (Get-ItemProperty $lxss -Name DefaultDistribution -ErrorAction SilentlyContinue).DefaultDistribution
            if ($defGuid) {
                $defName = (Get-ItemProperty (Join-Path $lxss $defGuid) -ErrorAction SilentlyContinue).DistributionName
                if ($defName) { return $defName }
            }
            if ($all.Count -gt 0) { return $all[0] }
        }
    } catch {}
    return $Default
}
$script:MIOS_WSL_DISTRO = Resolve-MiosDistro
'''

# Windows-host paths resolve from the live environment, so they stay expressions.
# $defaultImageName is kept because check_globals_image_parity asserts on it.
PS_HOST_PATHS = '''
# ── IMAGE DEFAULT (asserted by the image-parity drift check) ─────────
$defaultImageName = 'IMAGE_NAME_LITERAL'
'''


PS_HOST_PATHS_TAIL = '''# ── WINDOWS HOST PATHS (resolved from the live environment) ──────────
$script:MIOS_WIN_APPDATA_DIR = if ($env:APPDATA)     { $env:APPDATA }     else { "$HOME/AppData/Roaming" }
$script:MIOS_WIN_DOCS_DIR    = if ($env:USERPROFILE) { "$env:USERPROFILE/Documents" } else { "$HOME/Documents" }
$script:MIOS_WIN_REPO_DIR    = if ($env:MIOS_WIN_REPO_DIR) { $env:MIOS_WIN_REPO_DIR } else { "$HOME/MiOS" }
'''


def _sh_squote(text: str) -> str:
    """POSIX single-quote: safe for EVERY byte, including } ( ) \\ and $."""
    return "'" + text.replace("'", "'\"'\"'") + "'"


def _sh_assign(name: str, value: str) -> str:
    parts = _TEMPLATE_RE.split(value)
    # The word in `"${VAR:=word}"` is still quote-processed, so a lone ' or "
    # inside it (e.g. "the operator's phone") starts an unterminated quote.
    # Only take the idiomatic form when the value is free of every metacharacter.
    if len(parts) == 1 and not _SH_UNSAFE_RE.search(value):
        return ': "${%s:=%s}"' % (name, value)
    if len(parts) == 1:
        rendered = _sh_squote(value)
    else:
        # odd indices are captured MIOS_* names -> keep them live as "$NAME"
        chunks = []
        for i, part in enumerate(parts):
            if i % 2:
                chunks.append('"${%s}"' % part)
            elif part:
                chunks.append(_sh_squote(part))
        rendered = "".join(chunks) or "''"
    return '[ -n "${%s+x}" ] || %s=%s' % (name, name, rendered)


def _ps_assign(name: str, value: str, exports: dict | None = None) -> str:
    parts = _TEMPLATE_RE.split(value)
    if len(parts) == 1 and re.fullmatch(r"\d+", value):
        # Bare integer, not a quoted string: ports really are numbers here, and
        # the globals-parity drift check parses `else { <digits> }`.
        rendered = value
    elif len(parts) == 1:
        rendered = "'%s'" % value.replace("'", "''")
    else:
        # `exports is None` means "caller supplied no name table", which the
        # branch below already reads as "every placeholder is live". The two
        # tests disagreed, so no-table callers silently got a single-quoted
        # literal and the expansion branch was unreachable.
        live_parts = [p for i, p in enumerate(parts)
                      if i % 2 and (exports is None or p in exports)]
        if not live_parts:
            rendered = "'%s'" % value.replace("'", "''")
        else:
            chunks = []
            for i, part in enumerate(parts):
                if i % 2:
                    if exports is None or part in exports:
                        chunks.append("$($script:%s)" % part)
                    else:
                        chunks.append("${%s}" % part)
                elif part:
                    # inside a PS double-quoted string, ` " $ are the metacharacters
                    chunks.append(part.replace("`", "``").replace('"', '`"')
                                  .replace("$", "`$"))
            rendered = '"%s"' % "".join(chunks)
    return "$script:%s = if ($env:%s) { $env:%s } else { %s }" % (
        name, name, name, rendered)


def render_sh(exports: dict, names: list, version_fallback: str) -> str:
    lines = [HEADER_SH.replace("VERSION_FALLBACK", version_fallback)]
    for name in names:
        if name == "MIOS_VERSION":
            continue
        lines.append(_sh_assign(name, exports[name]))
    lines.append("")
    return "\n".join(lines)


def render_ps1(exports: dict, names: list, version_fallback: str) -> str:
    lines = [HEADER_PS.replace("VERSION_FALLBACK", version_fallback)]
    for name in names:
        if name == "MIOS_VERSION":
            continue
        lines.append(_ps_assign(name, exports[name], exports))
    lines.append(PS_HOST_PATHS.replace(
        "IMAGE_NAME_LITERAL",
        exports.get("MIOS_IMAGE_NAME", "ghcr.io/mios-dev/mios").replace("'", "''")))
    lines.append(PS_HOST_PATHS_TAIL)
    return "\n".join(lines)


def main() -> int:
    check = "--check" in sys.argv
    exports = build_exports()
    version_fallback = exports.get("MIOS_META_VERSION") or exports.get("MIOS_VERSION") or "0.3.0"
    names = ordered_names(exports)

    outputs = {SH_OUT: render_sh(exports, names, version_fallback),
               PS_OUT: render_ps1(exports, names, version_fallback)}

    drifted = []
    for path, body in outputs.items():
        # .gitattributes pins `*.ps1 text eol=crlf` and `*.sh text eol=lf`, so
        # the CHECKED-OUT bytes differ per file type. Write the matching line
        # ending, and compare with newlines normalised so the gate can never
        # fail merely because a checkout honoured .gitattributes.
        eol = "\r\n" if path.endswith(".ps1") else "\n"
        existing = None
        if os.path.isfile(path):
            with open(path, encoding="utf-8-sig" if path.endswith(".ps1") else "utf-8") as fh:  # universal newlines
                existing = fh.read()
        if existing != body:
            drifted.append(path)
            if not check:
                enc = "utf-8-sig" if path.endswith(".ps1") else "utf-8"
                with open(path, "w", encoding=enc, newline=eol) as fh:
                    fh.write(body)

    if check:
        if drifted:
            sys.stderr.write("[render-globals] resolvers are stale vs SSOT:\n")
            for p in drifted:
                sys.stderr.write(f"    {os.path.relpath(p, ROOT)}\n")
            sys.stderr.write("    run: python3 tools/render-globals.py\n")
            return 1
        print(f"[render-globals] both resolvers match SSOT ({len(names)} constants)")
        return 0

    print(f"[render-globals] generated {len(names)} constants into "
          f"globals.sh + globals.ps1 (no hand-written literals remain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
