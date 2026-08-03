# AI-hint: Forwarding wrapper delegating to provision-env.ps1 for MiOS environment and secret provisioning.
# AI-related: config/bootstrap/provision-env.ps1

$target = Join-Path $PSScriptRoot "provision-env.ps1"
if (Test-Path $target) {
    & $target @args
} else {
    throw "Target script not found: $target"
}
