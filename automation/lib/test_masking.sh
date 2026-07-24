#!/usr/bin/env bash
# AI-hint: Unit tests for automation/lib/masking.sh and scurl wrapper.
# ============================================================================
# automation/lib/test_masking.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/masking.sh"

echo "[test_masking] Starting masking and scurl unit tests..."

# Test 1: Piped binary stream remains byte-identical (no sed corruption)
test_binary_stream() {
    local tmp_src; tmp_src="$(mktemp)"
    local tmp_dst; tmp_dst="$(mktemp)"
    
    # Generate 1MB binary data
    head -c 1048576 /dev/urandom > "$tmp_src"
    
    # Pass through mask_filter (simulating piped binary download)
    cat "$tmp_src" | mask_filter > "$tmp_dst"
    
    if ! cmp -s "$tmp_src" "$tmp_dst"; then
        echo "[FAIL] Binary stream was corrupted by mask_filter!" >&2
        rm -f "$tmp_src" "$tmp_dst"
        exit 1
    fi
    rm -f "$tmp_src" "$tmp_dst"
    echo "[PASS] Binary stream byte-identity verified."
}

# Test 2: Registered secret is masked in text output
test_secret_masking() {
    local secret="super-secret-token-12345"
    add_mask "$secret"
    
    local out; out="$(echo "Log output with ${secret} included" | mask_filter)"
    if [[ "$out" != *"Log output with [MASKED] included"* ]]; then
        echo "[FAIL] Secret was not masked in text output: '$out'" >&2
        exit 1
    fi
    echo "[PASS] Secret masking verified."
}

# Test 3: scurl argument parser detects output flags
test_scurl_parser() {
    # Mock curl to inspect passed arguments
    curl() {
        echo "CURL_ARGS: $*"
    }
    
    # Test --output argument
    local res; res="$(scurl -sSL --output=/tmp/test.tar.gz https://github.com/test)"
    if [[ "$res" != *"https://github.com/test"* ]]; then
        echo "[FAIL] scurl failed to parse URL with --output: '$res'" >&2
        exit 1
    fi
    echo "[PASS] scurl argument parser verified."
}

test_binary_stream
test_secret_masking
test_scurl_parser

echo "[test_masking] PASS: All masking and scurl tests passed."
