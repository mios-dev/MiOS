<#
.SYNOPSIS  Fix token paste bug in mios-build-local.ps1
.DESCRIPTION
    The [Console]::ReadKey loop doesn't detect Enter after paste in PS 7.6.
    Replace with Read-Host -MaskInput (PS 7.1+, handles paste natively).

    Run from repo root:
      cd $env:USERPROFILE\OneDrive\Documents\GitHub\MiOS   # or wherever the repo is
      .\fix-token-input.ps1
#>
$ErrorActionPreference = "Stop"

if (-not (Test-Path "mios-build-local.ps1")) {
    Write-Host "  ERROR: Run from \MiOS repo root" -ForegroundColor Red; exit 1
}

$file = "mios-build-local.ps1"
$content = [System.IO.File]::ReadAllText((Resolve-Path $file).Path)

# Old: custom ReadKey loop that breaks on paste
$old = @'
        if ($Secret) {
            $secBuf = ""
            while ($true) {
                $key = [Console]::ReadKey($true)
                if ($key.Key -eq 'Enter') { Write-Host ""; break }
                if ($key.Key -eq 'Backspace') {
                    if ($secBuf.Length -gt 0) { $secBuf = $secBuf.Substring(0, $secBuf.Length - 1); Write-Host "`b `b" -NoNewline }
                } else {
                    $secBuf += $key.KeyChar; Write-Host "*" -NoNewline
                }
            }
            $buf = $secBuf
'@

# New: Read-Host -MaskInput (PS 7.1+, handles paste correctly)
$new = @'
        if ($Secret) {
            $buf = Read-Host -MaskInput
'@

if ($content.Contains($old)) {
    $content = $content.Replace($old, $new)
    [System.IO.File]::WriteAllText(
        (Resolve-Path $file).Path, $content,
        [System.Text.UTF8Encoding]::new($true)  # BOM for PS file
    )
    Write-Host "  [ok] Token input fixed: Read-Host -MaskInput (handles paste)" -ForegroundColor Green
} else {
    # Try with normalized line endings
    $content = $content -replace "`r`n", "`n"
    $old = $old -replace "`r`n", "`n"
    $new = $new -replace "`r`n", "`n"
    if ($content.Contains($old)) {
        $content = $content.Replace($old, $new)
        [System.IO.File]::WriteAllText(
            (Resolve-Path $file).Path, $content,
            [System.Text.UTF8Encoding]::new($true)
        )
        Write-Host "  [ok] Token input fixed (LF normalized)" -ForegroundColor Green
    } else {
        Write-Host "  [x] ReadKey pattern not found -- checking manually" -ForegroundColor Red
        Write-Host "  Line 91:" -ForegroundColor Yellow
        Get-Content $file | Select-Object -Skip 90 -First 1
    }
}

git add mios-build-local.ps1
git commit -m "fix: token paste bug -- replace ReadKey loop with Read-Host -MaskInput`n`n[Console]::ReadKey loop in Read-Timed -Secret doesn't detect Enter`nafter paste in PowerShell 7.6/Windows Terminal. Each Enter press`nadds another masked character instead of submitting.`n`nRead-Host -MaskInput (PS 7.1+) handles paste, Enter, backspace`nnatively with * masking."
git push origin main 2>&1 | ForEach-Object { Write-Host "  $_" }
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n  [ok] Pushed. Re-clone and rebuild.`n" -ForegroundColor Green
}
