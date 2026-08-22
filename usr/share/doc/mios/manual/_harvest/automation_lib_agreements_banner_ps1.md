<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: PowerShell script that displays and enforces legal/policy acknowledgments for interactive users, supporting bypass via MIOS_AGREEMENT_* environment variables to control entry-point access.
AI-related: mios-bootstrap
AI-functions: Get-MiOSAgreementSummary, Test-MiOSInteractiveHost, Show-MiOSAgreementScrollable, Invoke-MiOSAgreementBanner
automation/lib/agreements-banner.ps1 -- PowerShell sibling of
agreements-banner.sh. Dot-sourced by every PowerShell entry point in
'MiOS' (mios.git) and 'mios-bootstrap' (mios-bootstrap.git).

Behavior summary:
  * Default for an interactive operator: print a scrollable summary
    of the project's licenses, research-project framing, third-party
    agreements, and data/network posture, then require an explicit
    "Acknowledged" or "No thanks" choice.
  * Default for non-interactive runs (CI, no console host, irm|iex
    redirected through a non-RawUI host): print a one-line note and
    continue. There is no way to accept-by-prompt without a host UI.
  * Escape hatches (any one of these skips the prompt):
        $env:MIOS_AGREEMENT_BANNER = 'quiet' | 'silent' | 'off' | '0' | 'false'
        $env:MIOS_AGREEMENT_ACK = 'accepted'                # explicit accept
        $env:MIOS_REQUIRE_AGREEMENT_ACK = '0'                # explicit waive
  * CI users that need the prompt skipped should set
    `$env:MIOS_AGREEMENT_ACK = 'accepted'` -- declaring acknowledgment
    by external policy is more honest than silently bypassing.

Exit code 78 (EX_CONFIG) on decline, matching the bash sibling.

<!-- mios-src:8aef9c3bb4a6 from automation/lib/agreements-banner.ps1:1-24 -->

