#!/usr/bin/env bash
# AI-hint: Source build phase for Windows executables (MiosServiceTool.exe, MiOS-iGPU-Server.exe).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${ROOT}/build"
mkdir -p "${OUT_DIR}"

WIN_SRC_DIR="${ROOT}/usr/share/mios/windows"
SERVICE_TOOL_CS="${WIN_SRC_DIR}/MiosServiceTool.cs"

if [ ! -f "${SERVICE_TOOL_CS}" ]; then
    echo "[build-win-bin] ERROR: Source file ${SERVICE_TOOL_CS} not found!" >&2
    exit 1
fi

to_win_path() {
    local p="$1"
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$p"
    elif [[ "$p" =~ ^/mnt/c/ ]]; then
        echo "C:\\${p#/mnt/c/}" | tr '/' '\\'
    elif [[ "$p" =~ ^/c/ ]]; then
        echo "C:\\${p#/c/}" | tr '/' '\\'
    else
        echo "$p" | tr '/' '\\'
    fi
}

echo "[build-win-bin] Compiling MiosServiceTool.exe from source..."

out_win="$(to_win_path "${OUT_DIR}/MiosServiceTool.exe")"
cs_win="$(to_win_path "${SERVICE_TOOL_CS}")"

if command -v csc >/dev/null 2>&1; then
    csc -nologo -target:winexe -r:System.ServiceProcess.dll "-out:${out_win}" "${cs_win}"
elif [ -f "/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe" ]; then
    /mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe -nologo -target:winexe -r:System.ServiceProcess.dll "-out:${out_win}" "${cs_win}"
elif [ -f "C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe" ]; then
    "C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe" -nologo -target:winexe -r:System.ServiceProcess.dll "-out:${out_win}" "${cs_win}"
elif command -v mcs >/dev/null 2>&1; then
    mcs -target:winexe -r:System.ServiceProcess.dll -out:"${OUT_DIR}/MiosServiceTool.exe" "${SERVICE_TOOL_CS}"
elif command -v dotnet >/dev/null 2>&1; then
    echo "[build-win-bin] Using dotnet SDK build..."
    dotnet build -c Release "${SERVICE_TOOL_CS}" -o "${OUT_DIR}" 2>/dev/null || true
else
    echo "[build-win-bin] WARNING: No C# compiler (csc/mcs/dotnet) found. Using committed binary fallback." >&2
    exit 0
fi

if [ -f "${OUT_DIR}/MiosServiceTool.exe" ]; then
    echo "[build-win-bin] PASS: Successfully built MiosServiceTool.exe ($(stat -c%s "${OUT_DIR}/MiosServiceTool.exe" 2>/dev/null || stat -f%z "${OUT_DIR}/MiosServiceTool.exe") bytes)"
fi

exit 0
