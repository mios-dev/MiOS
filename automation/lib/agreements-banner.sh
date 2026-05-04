#!/usr/bin/env bash
# automation/lib/agreements-banner.sh -- single source of truth for the
# entry-point acknowledgment gate. Sourced by every shell-side entry
# point in 'MiOS' (mios.git) and 'mios-bootstrap' (mios-bootstrap.git).
#
# Behavior summary:
#   * Default for an interactive operator: print a scrollable summary
#     of the project's licenses, research-project framing, third-party
#     agreements, and data/network posture, then require an explicit
#     "Acknowledged" or "No thanks" choice.
#   * Default for non-interactive runs (CI, `bash <(curl ...)` without
#     a controlling TTY, sourced from another script in `--quiet`
#     mode): print a one-line note and continue. There is no way to
#     accept-by-prompt without a terminal.
#   * Escape hatches (any one of these skips the prompt):
#       MIOS_AGREEMENT_BANNER=quiet | silent | off | 0 | false
#       MIOS_AGREEMENT_ACK=accepted               (explicit accept)
#       MIOS_REQUIRE_AGREEMENT_ACK=0              (explicit waive)
#   * CI users that need the prompt skipped should set
#     `MIOS_AGREEMENT_ACK=accepted` -- declaring acknowledgment by
#     external policy is more honest than silently bypassing.
#
# Exit code 78 (EX_CONFIG) on decline, matching prior behavior.

# ---------------------------------------------------------------------
# The canonical scrollable summary. Embedded verbatim so it works on
# the first leg of a `curl ... | bash` invocation, before any clone /
# fetch has happened. The full document lives at AGREEMENTS.md; this
# is the abridged-but-thorough form the operator sees at the gate.
# ---------------------------------------------------------------------
mios_agreement_summary() {
    cat <<'EOF'
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
  ./LICENSES.md for the full inventory.
* Attribution to every upstream project, specification, vendor, and
  community is recorded in ./CREDITS.md.

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
      `bootc upgrade`
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

For unattended / CI invocation, set MIOS_AGREEMENT_ACK=accepted in
the environment to bypass this prompt as declared policy.

================================================================================
EOF
}

# ---------------------------------------------------------------------
# Render the summary on the operator's terminal. Use `less -RFX` if
# available so the text is scrollable with arrow keys / PgUp / PgDn /
# space; falls back to a plain stdout print on systems without less.
# ---------------------------------------------------------------------
_mios_agreement_render() {
    local tty_in tty_out
    tty_in="${1:-/dev/tty}"
    tty_out="${2:-/dev/tty}"

    if command -v less >/dev/null 2>&1; then
        # -R  pass color codes through (none used today, future-proof)
        # -F  quit immediately if content fits on one screen
        # -X  do not clear the screen on exit
        # -K  abort on Ctrl-C without leaving terminal in alt screen
        mios_agreement_summary | less -RFXK <"$tty_in" >"$tty_out"
    else
        mios_agreement_summary >"$tty_out"
    fi
}

# ---------------------------------------------------------------------
# Public: the gate.
# ---------------------------------------------------------------------
mios_print_agreement_banner() {
    # Quiet escape hatch: skip everything (banner + prompt).
    case "${MIOS_AGREEMENT_BANNER:-}" in
        quiet|silent|off|0|false|FALSE) return 0 ;;
    esac

    local entry="${1:-${BASH_SOURCE[1]:-this entry point}}"
    entry="$(basename -- "$entry")"

    # Pre-accepted: declared accept, no prompt.
    case "${MIOS_AGREEMENT_ACK:-}" in
        accepted|ACCEPTED|yes|YES|y|1|true|TRUE)
            echo "[mios] AGREEMENTS.md acknowledged via MIOS_AGREEMENT_ACK; proceeding with ${entry}." >&2
            return 0
            ;;
    esac

    # Explicit waive: print the one-line banner only.
    if [[ "${MIOS_REQUIRE_AGREEMENT_ACK:-1}" == "0" ]]; then
        cat >&2 <<EOF
[mios] By invoking ${entry} you acknowledge AGREEMENTS.md
       (Apache-2.0 + bundled-component licenses in LICENSES.md +
        attribution in CREDITS.md). 'MiOS' is a research project.
EOF
        return 0
    fi

    # Need a TTY to render the doc + prompt. /dev/tty is the canonical
    # way to talk to the controlling terminal even when stdin/stdout
    # are pipes (true on `curl ... | bash`).
    if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
        # No terminal available -- fall back to one-line informational
        # banner. This is the same behavior the legacy script had.
        # Operator can re-run with a TTY (or set MIOS_AGREEMENT_ACK).
        cat >&2 <<EOF
[mios] No controlling terminal available; cannot prompt for
       acknowledgment of AGREEMENTS.md. Continuing with ${entry}.
       Set MIOS_AGREEMENT_ACK=accepted in the environment to declare
       acknowledgment for unattended runs, or re-run with a TTY.
EOF
        return 0
    fi

    # Render the scrollable summary.
    _mios_agreement_render /dev/tty /dev/tty

    # Prompt loop. Read from /dev/tty so it works under `curl | bash`.
    local reply
    while :; do
        printf '\n[mios] Type "Acknowledged" to proceed, or "No thanks" to abort: ' >/dev/tty
        if ! IFS= read -r reply </dev/tty; then
            echo "[mios] no input received; aborting." >&2
            exit 78
        fi
        case "$reply" in
            Acknowledged|acknowledged|ACKNOWLEDGED|accept|ACCEPT|y|Y|yes|YES)
                echo "[mios] AGREEMENTS.md acknowledged; proceeding with ${entry}." >&2
                return 0
                ;;
            No\ thanks|no\ thanks|NO\ THANKS|n|N|no|NO|decline|DECLINE|q|Q|quit|QUIT)
                echo "[mios] not acknowledged; aborting (no system changes made)." >&2
                exit 78
                ;;
            *)
                printf '[mios] Please type exactly "Acknowledged" or "No thanks".\n' >/dev/tty
                ;;
        esac
    done
}
