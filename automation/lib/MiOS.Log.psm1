# AI-hint: Shared PowerShell logging module for MiOS scripts (Write-Step, Write-Ok, Write-Warn, Write-Bad, Info, Ok, Warn, Fail).
# AI-related: automation/lib/MiOS.Console.psm1, installation/mios-common.ps1

function Write-Step([string]$Message) {
    Write-Host "  [*] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  [+] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [!] $Message" -ForegroundColor Yellow
}

function Write-Bad([string]$Message) {
    Write-Host "  [X] $Message" -ForegroundColor Red
}

function Info([string]$Message) { Write-Step $Message }
function Ok([string]$Message)   { Write-Ok $Message   }
function Warn([string]$Message) { Write-Warn $Message }
function Fail([string]$Message) { Write-Bad $Message; throw $Message }

Export-ModuleMember -Function Write-Step, Write-Ok, Write-Warn, Write-Bad, Info, Ok, Warn, Fail
