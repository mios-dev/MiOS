# automation/lib/agreements-banner.ps1 -- PowerShell sibling of
# agreements-banner.sh. Dot-sourced by every PowerShell entry point in
# 'MiOS' (mios.git) and 'mios-bootstrap' (mios-bootstrap.git).
#
# Prints a one-line note to the host stream unless
# $env:MIOS_AGREEMENT_BANNER -eq 'quiet'. Invocation of the enclosing
# script is treated as acknowledgment of:
#   - LICENSE                 (Apache-2.0)
#   - LICENSES.md             (bundled-component licenses)
#   - CREDITS.md              (attribution registry)
#   - AGREEMENTS.md           (runtime agreements + research-project framing)
#
# Operators who require a hard interactive gate can set
# $env:MIOS_REQUIRE_AGREEMENT_ACK = '1' before invocation; the banner
# then prompts and aborts on anything other than 'y'/'yes'.

function Invoke-MiOSAgreementBanner {
    [CmdletBinding()]
    param(
        [string]$Entry = $MyInvocation.PSCommandPath
    )
    $quiet = @('quiet','silent','off','0','false','FALSE')
    if ($env:MIOS_AGREEMENT_BANNER -and $quiet -contains $env:MIOS_AGREEMENT_BANNER) {
        return
    }
    if (-not $Entry) { $Entry = 'this entry point' }
    $entryName = if ($Entry -match '[/\\]') { Split-Path -Leaf $Entry } else { $Entry }

    $msg = @"
[mios] By invoking $entryName you acknowledge AGREEMENTS.md
       (Apache-2.0 main + bundled-component licenses in LICENSES.md +
        attribution in CREDITS.md). 'MiOS' is a research project
       (pronounced 'MyOS'; generative, seed-script-derived).
"@
    [Console]::Error.WriteLine($msg)

    if ($env:MIOS_REQUIRE_AGREEMENT_ACK -eq '1') {
        $reply = Read-Host '[mios] Acknowledge? [y/N]'
        if ($reply -notmatch '^(y|Y|yes|YES|Yes)$') {
            [Console]::Error.WriteLine('[mios] not acknowledged; aborting.')
            exit 78
        }
    }
}
