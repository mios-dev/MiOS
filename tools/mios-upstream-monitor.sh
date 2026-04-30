#!/bin/bash
# MiOS v0.2.0 — Upstream Feed Monitor
# ----------------------------------------------------------------------------
# Automates checking for updates from core MiOS dependencies.
# Uses GitHub API and other feeds to identify new versions.
# ----------------------------------------------------------------------------
set -euo pipefail

# GitHub API Helper (supports GH_TOKEN for rate limits)
gh_api() {
  local repo="$1"
  local endpoint="${2:-releases/latest}"
  local auth_header=()
  if [[ -n "${GH_TOKEN:-}" ]]; then
    auth_header=("-H" "Authorization: token $GH_TOKEN")
  fi
  scurl -sL "${auth_header[@]}" "https://api.github.com/repos/${repo}/${endpoint}"
}

get_latest_tag() {
  # Query releases API, filter for stable versions only (exclude rc, beta, alpha),
  # and sort to find the actual highest version number.
  gh_api "$1" "releases" | grep -Po '"tag_name": "\K.*?(?=")' | grep -vE 'rc|beta|alpha' | sort -V | tail -n 1 || echo "ERROR"
}

# ----------------------------------------------------------------------------
# CORE MONITORING
# ----------------------------------------------------------------------------

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MiOS UPSTREAM MONITOR — $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Fedora Release Status (live Bodhi API)
printf '\e[36m[monitor]\e[0m Checking Fedora 44 release state (Bodhi)...\n'
F44_STATUS=$( (scurl -sL "https://bodhi.fedoraproject.org/releases/?name=F44" \
    | python3 -c "import sys,json; r=json.load(sys.stdin).get('releases',[]); print(r[0].get('state','unknown') if r else 'unknown')") \
    2>/dev/null || echo "unknown")
echo "  Fedora 44: $F44_STATUS"

# 2. bootc
printf '\e[36m[monitor]\e[0m Checking bootc (containers/bootc)...\n'
BOOTC_VER=$(get_latest_tag "bootc-dev/bootc")
echo "  Latest: $BOOTC_VER"

# 3. Cockpit
printf '\e[36m[monitor]\e[0m Checking Cockpit (cockpit-project/cockpit)...\n'
COCKPIT_VER=$(get_latest_tag "cockpit-project/cockpit")
echo "  Latest: $COCKPIT_VER"

# 4. NVIDIA Container Toolkit
printf '\e[36m[monitor]\e[0m Checking NVIDIA Container Toolkit...\n'
NCT_VER=$(get_latest_tag "NVIDIA/nvidia-container-toolkit")
echo "  Latest: $NCT_VER"

# 5. CrowdSec
printf '\e[36m[monitor]\e[0m Checking CrowdSec...\n'
CROWDSEC_VER=$(get_latest_tag "crowdsecurity/crowdsec")
echo "  Latest: $CROWDSEC_VER"

# 6. Waydroid #1883
printf '\e[36m[monitor]\e[0m Checking Waydroid CDI Issue #1883...\n'
WAYDROID_STATUS=$(gh_api "waydroid/waydroid" "issues/1883" | grep -Po '"state": "\K.*?(?=")' || echo "Unknown")
echo "  Issue Status: $WAYDROID_STATUS"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
