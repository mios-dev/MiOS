#Requires -Version 7.0
#Requires -RunAsAdministrator
# AI-hint: Generated for MiOS M: drive Hyper-V deployment
# Creates a Generation-2 Hyper-V VM attached to the converted MiOS vhdx on the M: drive.

param(
    [string]$VmName = 'MiOS-DEV',
    [string]$VhdPath = 'M:\MiOS\images\mios.vhdx',
    [string]$SwitchName = 'Default Switch'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $VhdPath)) {
    Write-Host "[!] VHDX not found at $VhdPath. Ensure the M: drive is mounted and the artifact exists." -ForegroundColor Red
    exit 1
}

Write-Host "▶ Creating Hyper-V Gen2 VM '$VmName' from $VhdPath ..." -ForegroundColor Cyan

# Remove existing VM if it exists
$existing = Get-VM -Name $VmName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  [-] Removing existing VM '$VmName'" -ForegroundColor Yellow
    Remove-VM -Name $VmName -Force
}

New-VM -Name $VmName -Generation 2 -MemoryStartupBytes 8GB -VHDPath $VhdPath -SwitchName $SwitchName | Out-Null
Set-VMProcessor -VMName $VmName -Count 4
Set-VMMemory -VMName $VmName -DynamicMemoryEnabled $true -MinimumBytes 2GB -MaximumBytes 16GB
Set-VMFirmware -VMName $VmName -EnableSecureBoot Off
Add-VMDvdDrive -VMName $VmName | Out-Null

Write-Host "  [+] VM ready. Start with: Start-VM -Name $VmName" -ForegroundColor Green
