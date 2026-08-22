#!/usr/bin/env bash
# AI-hint: Guards the object-pipeline flattening in usr/libexec/mios/mios-powershell (OAI-03). Two tiers: a stub-pwsh tier that always runs and asserts the wrapper the broker builds (Out-String width, PlainText rendering, `& '<staged script>'` call form, and that [powershell].flatten=false really removes them), and a live tier that runs a real pwsh and proves the defect it fixes -- with no console PowerShell sizes every formatter column against a window width of -1, so an object-returning cmdlet reaches the model as a BLANK LINE.
# AI-related: usr/libexec/mios/mios-powershell, usr/share/mios/mios.toml, tests/powershell/run-pester.sh
# AI-functions: log, die, ok, need, find_pwsh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="${ROOT}/usr/libexec/mios/mios-powershell"

log() { printf '[test-powershell-flatten] %s\n' "$*"; }
die() { printf '[test-powershell-flatten] ERROR: %s\n' "$*" >&2; exit 1; }
ok()  { printf '[test-powershell-flatten]   [ OK ] %s\n' "$*"; }

need() {  # need <description> <haystack-file> <needle>
    grep -qF -- "$3" "$2" || die "$1: expected to find <<$3>> in $(cat "$2")"
    ok "$1"
}

[[ -x "$BROKER" || -f "$BROKER" ]] || die "broker not found at $BROKER"

TMP="$(mktemp -d /tmp/mios-psflat.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/stage" "$TMP/bin"

# ---------------------------------------------------------------- stub tier --
# The broker deletes the staged script on exit, so the stub snapshots it while
# it is still on disk -- that copy is how the body-vs-wrapper split is checked.
cat > "$TMP/bin/pwsh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$MIOS_TEST_ARGV_LOG"
if [[ -n "${MIOS_TEST_SNAPSHOT_DIR:-}" ]]; then
    mkdir -p "$MIOS_TEST_SNAPSHOT_DIR"
    cp "$MIOS_POWERSHELL_STAGE_DIR"/mios-ps-*.ps1 "$MIOS_TEST_SNAPSHOT_DIR/" 2>/dev/null || true
fi
exit 0
STUB
chmod +x "$TMP/bin/pwsh"

export MIOS_TEST_ARGV_LOG="$TMP/argv.log"
export MIOS_POWERSHELL_EXE="$TMP/bin/pwsh"
export MIOS_POWERSHELL_STAGE_DIR="$TMP/stage"

log "stub tier: wrapper the broker hands to PowerShell"
bash "$BROKER" -c 'Get-Process' >/dev/null 2>&1 || true
need "flatten pipes the success stream through Out-String" "$MIOS_TEST_ARGV_LOG" "| Out-String -Stream -Width 200"
need "flatten forces PlainText rendering"                  "$MIOS_TEST_ARGV_LOG" 'OutputRendering="PlainText"'
need "flatten raises the enumeration limit"                "$MIOS_TEST_ARGV_LOG" '$FormatEnumerationLimit=16'
need "the staged script is CALLED, not inlined"            "$MIOS_TEST_ARGV_LOG" "& '${TMP}/stage/"
need "the wrapper propagates the callee exit code"         "$MIOS_TEST_ARGV_LOG" 'exit ([int]$LASTEXITCODE)'

log "stub tier: --work-dir lands in the wrapper, never in the body"
mkdir -p "$TMP/wd"
MIOS_TEST_SNAPSHOT_DIR="$TMP/snap" MIOS_POWERSHELL_STAGE_DIR="$TMP/wd" \
    bash "$BROKER" --work-dir /etc -c 'FIRST-LINE-MARKER' >/dev/null 2>&1 || true
need "work-dir is a wrapper statement" "$MIOS_TEST_ARGV_LOG" "Set-Location -LiteralPath '/etc';"
mapfile -t staged < <(ls "$TMP"/snap/mios-ps-*.ps1 2>/dev/null || true)
[[ "${#staged[@]}" -eq 1 ]] || die "expected exactly one staged script, found ${#staged[@]}"
head -1 "${staged[0]}" | grep -qF 'FIRST-LINE-MARKER' \
    || die "work-dir was prepended to the script body -- it would shift every error line number: $(head -2 "${staged[0]}")"
ok "the script body still starts at the caller's first line"

log "stub tier: the flatten knob is real"
MIOS_POWERSHELL_FLATTEN=false bash "$BROKER" -c 'Get-Process' >/dev/null 2>&1 || true
if grep -qF -- "Out-String" "$MIOS_TEST_ARGV_LOG"; then
    die "[powershell].flatten=false still flattened -- the knob is a no-op"
fi
ok "flatten=false removes the Out-String stage"

log "stub tier: width is SSOT-driven"
MIOS_POWERSHELL_FLATTEN_WIDTH=321 bash "$BROKER" -c 'Get-Process' >/dev/null 2>&1 || true
need "flatten_width reaches the wrapper" "$MIOS_TEST_ARGV_LOG" "-Width 321"

log "stub tier: no Windows-visible staging falls back to -EncodedCommand"
MIOS_POWERSHELL_STAGE_DIR=/proc/nope/stage bash "$BROKER" -c 'Get-Process' >/dev/null 2>&1 || true
need "fallback uses -EncodedCommand" "$MIOS_TEST_ARGV_LOG" "-EncodedCommand"
if grep -qF -- '-Command -' "$MIOS_TEST_ARGV_LOG"; then
    die "fallback used '-Command -', which reads stdin a line at a time and never parses a multi-line block"
fi
ok "fallback avoids the line-at-a-time stdin reader"

# ---------------------------------------------------------------- live tier --
find_pwsh() {
    local c
    for c in "${MIOS_TEST_REAL_PWSH:-}" pwsh pwsh.exe \
             "/mnt/c/Program Files/PowerShell/7/pwsh.exe"; do
        [[ -z "$c" ]] && continue
        if [[ -x "$c" ]]; then printf '%s' "$c"; return 0; fi
        if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
    done
    return 1
}

REAL_PWSH="$(find_pwsh || true)"
if [[ -z "$REAL_PWSH" ]]; then
    if [[ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" == "1" ]]; then
        die "no pwsh available and MIOS_DRIFT_REQUIRE_TOOLS=1 -- the live tier cannot be skipped"
    fi
    log "SKIP live tier: no pwsh on this host (set MIOS_DRIFT_REQUIRE_TOOLS=1 to make this fatal)"
    log "PASS (stub tier only)"
    exit 0
fi

log "live tier: $REAL_PWSH"
export MIOS_POWERSHELL_EXE="$REAL_PWSH"
export MIOS_POWERSHELL_STAGE_DIR="$TMP/live"
mkdir -p "$TMP/live"

out="$TMP/out.txt"; err="$TMP/err.txt"

bash "$BROKER" -c 'Get-Item /etc/hostname | Select-Object Name, Length' >"$out" 2>"$err" || true
need "an object-returning cmdlet arrives as flat text" "$out" "Name"
grep -q '^hostname' "$out" || die "the object's own row is missing: $(cat "$out")"
ok "the object's row survives the formatter"

MIOS_POWERSHELL_FLATTEN=false bash "$BROKER" \
    -c 'Get-Item /etc/hostname | Select-Object Name, Length' >"$TMP/raw.txt" 2>/dev/null || true
if grep -q '[^[:space:]]' "$TMP/raw.txt"; then
    log "NOTE: unflattened output was non-blank on this host -- the console is not width -1"
else
    ok "unflattened output is blank -- the defect reproduces, and flattening is what fixes it"
fi

set +e
bash "$BROKER" -c 'Write-Output "before"
[pscustomobject]@{K=1}
exit 7' >"$out" 2>"$err"
rc=$?
set -e
[[ "$rc" -eq 7 ]] || die "explicit exit lost: rc=$rc"
need "output emitted before an explicit exit survives" "$out" "before"
need "the object emitted before an explicit exit survives" "$out" "K"
ok "explicit exit propagates as rc=7"

bash "$BROKER" -c '"one"
"two"
Get-Item /no/such/path' >"$out" 2>"$err" || true
grep -qE '\.ps1:3' "$err" || die "error record lost the caller's line number: $(cat "$err")"
ok "an error record names the caller's own line (3)"

bash "$BROKER" --work-dir /etc -c '"one"
Get-Item /no/such/path' >"$out" 2>"$err" || true
grep -qE '\.ps1:2' "$err" \
    || die "--work-dir shifted the reported line number: $(cat "$err")"
ok "--work-dir leaves the caller's line numbers untouched (2)"

if grep -qP '\x1b\[' "$err" 2>/dev/null; then
    die "ANSI escapes reached the caller despite PlainText rendering"
fi
ok "no ANSI escapes in the error stream"

bash "$BROKER" -c '[pscustomobject]@{A="x";B="yyyyyyyy"}
[pscustomobject]@{A="zzzzzzzzzz";B="q"}' >"$out" 2>/dev/null || true
if grep -qE '[[:blank:]]+$' "$out"; then
    die "formatter column padding survived into the caller's output"
fi
ok "no trailing column padding"

bash "$BROKER" --json -c 'Get-Item /etc/hostname | Select-Object Name' >"$out" 2>/dev/null || true
MIOS_TEST_JSON="$out" python3 - <<'PY' || die "the --json envelope is not usable"
import json, os, sys
d = json.load(open(os.environ["MIOS_TEST_JSON"], encoding="utf-8"))
assert d["ok"] is True, d
assert d["verb"] == "powershell_run", d
assert d["exit_code"] == 0, d
assert "hostname" in d["stdout"], d
PY
ok "--json carries the flattened text"

MIOS_POWERSHELL_STAGE_DIR=/proc/nope/stage bash "$BROKER" \
    -c 'Get-Item /etc/hostname | Select-Object Name, Length
"second line ok"' >"$out" 2>/dev/null || true
need "the -EncodedCommand fallback still flattens" "$out" "hostname"
need "the -EncodedCommand fallback parses multi-line scripts" "$out" "second line ok"

log "PASS (stub + live tiers)"
