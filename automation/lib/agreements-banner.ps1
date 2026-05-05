# automation/lib/agreements-banner.ps1 -- PowerShell sibling of
# agreements-banner.sh. Dot-sourced by every PowerShell entry point in
# 'MiOS' (mios.git) and 'mios-bootstrap' (mios-bootstrap.git).
#
# Behavior summary:
#   * Default for an interactive operator: print a scrollable summary
#     of the project's licenses, research-project framing, third-party
#     agreements, and data/network posture, then require an explicit
#     "Acknowledged" or "No thanks" choice.
#   * Default for non-interactive runs (CI, no console host, irm|iex
#     redirected through a non-RawUI host): print a one-line note and
#     continue. There is no way to accept-by-prompt without a host UI.
#   * Escape hatches (any one of these skips the prompt):
#         $env:MIOS_AGREEMENT_BANNER = 'quiet' | 'silent' | 'off' | '0' | 'false'
#         $env:MIOS_AGREEMENT_ACK = 'accepted'                # explicit accept
#         $env:MIOS_REQUIRE_AGREEMENT_ACK = '0'                # explicit waive
#   * CI users that need the prompt skipped should set
#     `$env:MIOS_AGREEMENT_ACK = 'accepted'` -- declaring acknowledgment
#     by external policy is more honest than silently bypassing.
#
# Exit code 78 (EX_CONFIG) on decline, matching the bash sibling.

function Get-MiOSAgreementSummary {
    @"
================================================================================
      ___                       ___           ___
     /\__\          ___        /\  \         /\  \
    /::|  |        /\  \      /::\  \       /::\  \
   /:|:|  |        \:\  \    /:/\:\  \     /:/\ \  \
  /:/|:|__|__      /::\__\  /:/  \:\  \   _\:\~\ \  \
 /:/ |::::\__\  __/:/\/__/ /:/__/ \:\__\ /\ \:\ \ \__\
 \/__/~~/:/  / /\/:/  /    \:\  \ /:/  / \:\ \:\ \/__/
       /:/  /  \::/__/      \:\  /:/  /   \:\ \:\__\
      /:/  /    \:\__\       \:\/:/  /     \:\/:/  /
     /:/  /      \/__/        \::/  /       \::/  /
     \/__/                     \/__/         \/__/

                        MiOS  --  Project Acknowledgement
================================================================================

Read the full document at AGREEMENTS.md (in the repo root) for the
authoritative text. The summary below is the operator-facing extract
displayed at every entry point.

--------------------------------------------------------------------------------
1. WHAT MiOS IS
--------------------------------------------------------------------------------

MiOS (pronounced "MyOS") is a research-grade, single-user-oriented
Linux operating system delivered as an OCI bootc image. It is NOT a
commercial product, NOT a hardened distribution backed by a vendor
SLA, and NOT an audited reference platform. The codebase is generative
in the literal sense -- synthesized from seed scripts and documentation,
iteratively expanded with automated tooling and human review. Its
surface area is broader than its runtime test coverage. Treat every
script, postcheck, lint rule, and architectural claim as an artifact
under ongoing review.

--------------------------------------------------------------------------------
2. LICENSING
--------------------------------------------------------------------------------

* MiOS-owned source code is licensed under Apache-2.0 (see ./LICENSE).
* Bundled vendor components retain their upstream licenses; see
  usr/share/doc/mios/reference/licenses.md for the full inventory.
* Attribution to every upstream project, specification, vendor, and
  community is recorded in usr/share/doc/mios/reference/credits.md.

By invoking any entry point you acknowledge these terms. If you do
not agree with them, decline at the prompt below; no files will be
modified, no images pulled, no services started.

--------------------------------------------------------------------------------
3. THIRD-PARTY AGREEMENTS THAT APPLY IMPLICITLY
--------------------------------------------------------------------------------

A deployed MiOS image bundles components governed by third-party
terms. The notable ones are:

  * NVIDIA proprietary GPU drivers + CUDA libraries
        -- governed by the NVIDIA Software License
  * Steam (Flatpak: com.valvesoftware.Steam)
        -- Steam Subscriber Agreement applies on first launch
  * Microsoft Windows VM guests (libvirt/QEMU)
        -- bring-your-own valid Windows licenses
  * Flathub apps installed via mios.toml [desktop].flatpaks
        -- each carries its own license metadata
  * Sigstore-signed images (if you opt-in via
    `bootc switch --enforce-container-sigpolicy`)
        -- accept the Sigstore transparency-log + Fulcio identity
           attestation model

These are NOT MiOS-specific terms. They are the terms of the upstream
vendors and projects whose components MiOS integrates; MiOS merely
surfaces them at install time.

--------------------------------------------------------------------------------
4. DATA AND NETWORK POSTURE
--------------------------------------------------------------------------------

* No telemetry. There is no built-in telemetry channel in the image.
* Outbound network calls from a default deployment are limited to:
    - Fedora / RPMFusion / Flathub package mirrors during build and
      ``bootc upgrade``
    - GitHub Container Registry (ghcr.io) during image fetch
    - User-chosen Quadlet workloads (Forgejo, LocalAI, Ollama,
      Guacamole, ...)
    - The local AI runtime at MIOS_AI_ENDPOINT (default: localhost)
* Operators can audit by inspecting /etc/containers/systemd/,
  /usr/lib/systemd/system/, and the active firewalld policy on a
  deployed host.
* MiOS does not exfiltrate any user data to a vendor cloud.

--------------------------------------------------------------------------------
5. NO WARRANTY
--------------------------------------------------------------------------------

The Apache-2.0 "AS IS" clause governs the MiOS-owned source. No
MiOS-shipped component carries a warranty beyond what its upstream
license already grants (which, for the open-source components, is
generally none). CI covers the build pipeline, image lint, and
postcheck invariants. CI does NOT cover full hardware matrix testing,
multi-host upgrade drills, long-running stability, or production
failure modes. Reports of what does and does not work on real hardware
are welcome.

--------------------------------------------------------------------------------
6. TRADEMARKS
--------------------------------------------------------------------------------

MiOS is a project shorthand. All third-party trademarks (Fedora,
Universal Blue, NVIDIA, OpenAI, Anthropic, Google, GitHub, Microsoft,
Cline, Cursor, ...) belong to their respective owners and are
referenced solely to identify the upstream component or specification
they are part of.

--------------------------------------------------------------------------------
7. YOUR CHOICE
--------------------------------------------------------------------------------

To proceed, choose Acknowledged. The script will continue and may
modify your system, fetch images, install packages, and start services
under the rules described above.

To stop, choose No thanks. The script exits without making changes
(exit code 78, EX_CONFIG). Re-run any time you want to reconsider.

For unattended / CI invocation, set ``$env:MIOS_AGREEMENT_ACK = 'accepted'``
in the environment to bypass this prompt as declared policy.

================================================================================
"@
}

function Test-MiOSInteractiveHost {
    # PowerShell's `irm | iex` keeps a real Console host most of the
    # time, but redirected output, transcript hosts, and remoting
    # sessions don't. We probe by trying a non-destructive RawUI access.
    if ($env:CI -or $env:GITHUB_ACTIONS) { return $false }
    try {
        $null = $Host.UI.RawUI.WindowSize
        return [Environment]::UserInteractive -and ($Host.Name -ne 'Default Host')
    } catch {
        return $false
    }
}

function Show-MiOSAgreementScrollable {
    # Out-Host -Paging gives PgUp/PgDn/space scrolling on console hosts.
    # Falls back to a plain Write-Host if the host doesn't support it.
    $text = Get-MiOSAgreementSummary
    try {
        $text -split "`r?`n" | Out-Host -Paging
    } catch {
        Write-Host $text
    }
}

function Invoke-MiOSAgreementBanner {
    [CmdletBinding()]
    param(
        [string]$Entry = $MyInvocation.PSCommandPath
    )

    # Quiet escape hatch.
    $quietValues = @('quiet','silent','off','0','false','FALSE')
    if ($env:MIOS_AGREEMENT_BANNER -and $quietValues -contains $env:MIOS_AGREEMENT_BANNER) {
        return
    }

    if (-not $Entry) { $Entry = 'this entry point' }
    $entryName = if ($Entry -match '[/\\]') { Split-Path -Leaf $Entry } else { $Entry }

    # Pre-accepted: declared accept, no prompt.
    $acceptValues = @('accepted','ACCEPTED','yes','YES','y','1','true','TRUE')
    if ($env:MIOS_AGREEMENT_ACK -and $acceptValues -contains $env:MIOS_AGREEMENT_ACK) {
        [Console]::Error.WriteLine("[mios] AGREEMENTS.md acknowledged via MIOS_AGREEMENT_ACK; proceeding with $entryName.")
        return
    }

    # Explicit waive: one-line banner only.
    if ($env:MIOS_REQUIRE_AGREEMENT_ACK -eq '0') {
        $shortMsg = @"
[mios] By invoking $entryName you acknowledge AGREEMENTS.md
       (Apache-2.0 + bundled-component licenses in usr/share/doc/mios/reference/licenses.md +
        attribution in usr/share/doc/mios/reference/credits.md). 'MiOS' is a research project.
"@
        [Console]::Error.WriteLine($shortMsg)
        return
    }

    # No interactive host -> degrade to one-line note.
    if (-not (Test-MiOSInteractiveHost)) {
        $autoMsg = @"
[mios] Non-interactive host detected; cannot prompt for
       acknowledgment of AGREEMENTS.md. Continuing with $entryName.
       Set `$env:MIOS_AGREEMENT_ACK = 'accepted' to declare
       acknowledgment for unattended runs.
"@
        [Console]::Error.WriteLine($autoMsg)
        return
    }

    # Interactive: render scrollable summary, then prompt.
    Show-MiOSAgreementScrollable

    while ($true) {
        $reply = Read-Host -Prompt "`n[mios] Type 'Acknowledged' to proceed, or 'No thanks' to abort"
        switch -Regex ($reply) {
            '^(Acknowledged|acknowledged|ACKNOWLEDGED|accept|ACCEPT|y|Y|yes|YES)$' {
                [Console]::Error.WriteLine("[mios] AGREEMENTS.md acknowledged; proceeding with $entryName.")
                return
            }
            '^(No\s+thanks|no\s+thanks|NO\s+THANKS|n|N|no|NO|decline|DECLINE|q|Q|quit|QUIT)$' {
                [Console]::Error.WriteLine('[mios] not acknowledged; aborting (no system changes made).')
                exit 78
            }
            default {
                [Console]::Error.WriteLine("[mios] Please type exactly 'Acknowledged' or 'No thanks'.")
            }
        }
    }
}
