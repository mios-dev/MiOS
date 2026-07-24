#!/usr/bin/env bash
# AI-hint: Provides helper functions for identifying, registering, and masking sensitive credentials (like GH_TOKEN or MIOS_PASSWORD) in logs and stdout, and provides a secure scurl wrapper for credential-aware requests.
# AI-functions: add_mask, register_common_masks, mask_filter, ensure_cred, scurl
# ============================================================================
# automation/lib/masking.sh
# ----------------------------------------------------------------------------
# Credential masking and secure execution helpers.
# ============================================================================

# Internal array of strings to mask
declare -ga MASK_LIST=()

# Register a string to be masked in output
# Usage: add_mask "my-secret-string"
add_mask() {
    local secret="$1"
    if [[ -n "$secret" && "$secret" != "null" ]]; then
        # Avoid duplicates
        for m in "${MASK_LIST[@]}"; do
            [[ "$m" == "$secret" ]] && return 0
        done
        MASK_LIST+=("$secret")
    fi
}

# Register common sensitive environment variables
register_common_masks() {
    local vars=(
        GHCR_TOKEN
        GH_TOKEN
        GITHUB_TOKEN
        MIOS_PASSWORD
        MIOS_PASSWORD_HASH
        SIGNING_SECRET
        COSIGN_PASSWORD
    )
    for v in "${vars[@]}"; do
        if [[ -n "${!v:-}" ]]; then
            add_mask "${!v}"
        fi
    done
}

# Filter stdin to mask registered secrets
# Usage: some_command | mask_filter
mask_filter() {
    if [[ ${#MASK_LIST[@]} -eq 0 ]]; then
        cat
        return
    fi

    local sed_script=""
    for secret in "${MASK_LIST[@]}"; do
        # Escape characters that are special to sed's regex and the delimiter
        # We use '|' as the delimiter for 's' because it's less common in hashes
        # than '/', but we still must escape it if it appears in the secret.
        local escaped_secret=$(printf '%s' "$secret" | sed 's/[][\\.*^$|/]/\\&/g')
        sed_script+="s|$escaped_secret|[MASKED]|g;"
    done
    sed -u "$sed_script"
}

# Prompt for credentials if not set
# Usage: ensure_cred "GHCR_TOKEN" "Enter your GitHub Container Registry Token"
ensure_cred() {
    local var_name="$1"
    local prompt_msg="$2"
    if [[ -z "${!var_name:-}" ]]; then
        read -rsp "$prompt_msg: " val
        echo >&2 # Newline after silent read
        export "$var_name"="$val"
    fi
    add_mask "${!var_name}"
}

# Secure curl wrapper with optional credentials
# Usage: scurl [curl-args] URL
scurl() {
    # Retry transient network failures (timeouts, 429, 5xx incl. the 504s that abort
    # CI builds) -- one hiccup on a version-lookup / asset download must not kill the
    # OCI build. Plain --retry (not --retry-all-errors) so a real 404 still fails fast
    # and non-idempotent methods stay safe.
    local args=(--retry 5 --retry-delay 3 --connect-timeout 20)
    local url=""
    local is_binary=false
    local is_header=false

    # Parse arguments for output flags, URL, and headers
    for arg in "$@"; do
        if [[ "$is_header" == "true" ]]; then
            is_header=false
            continue
        fi
        if [[ "$arg" == "-H" || "$arg" == "--header" ]]; then
            is_header=true
            continue
        fi

        if [[ "$arg" =~ ^-o || "$arg" == "-O" || "$arg" =~ ^--output ]]; then
            is_binary=true
        elif [[ "$arg" =~ ^--url=(https?://.+) ]]; then
            url="${BASH_REMATCH[1]}"
        elif [[ "$arg" =~ ^https?:// ]]; then
            url="$arg"
        fi
    done

    # Inherit credentials from environment if available and URL matches github/ghcr
    if [[ "$url" =~ github\.com|ghcr\.io ]]; then
        if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" || -n "${GHCR_TOKEN:-}" ]]; then
            local token="${GH_TOKEN:-${GITHUB_TOKEN:-${GHCR_TOKEN:-}}}"
            # Use -H for token auth to avoid process list exposure of -u
            args+=("-H" "Authorization: token $token")
            add_mask "$token"
        fi
    fi

    # Never pipe binary streams or stdout redirects to mask_filter (sed corrupts binaries)
    # Only run mask_filter when stdout is an interactive terminal (stdout is TTY)
    if [[ "$is_binary" == "true" || ! -t 1 ]]; then
        curl "${args[@]}" "$@"
    else
        curl "${args[@]}" "$@" | mask_filter
    fi
}
