#!/usr/bin/env bash
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
    local args=()
    local use_creds=false
    local url=""
    local is_binary=false
    
    # Simple parser to find the URL and check for binary download flags
    for arg in "$@"; do
        if [[ "$arg" =~ ^https?:// ]]; then
            url="$arg"
        elif [[ "$arg" == "-o" || "$arg" == "-O" || "$arg" == "--output" ]]; then
            is_binary=true
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

    if [[ "$is_binary" == "true" ]]; then
        curl "${args[@]}" "$@"
    else
        curl "${args[@]}" "$@" | mask_filter
    fi
}
