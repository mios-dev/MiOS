# AI-hint: !/usr/bin/env bash Provides helper functions for identifying, registering, and masking sensitive credentials (like GH_TOKEN or MIOS_PASSWORD) in logs and stdout, and...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_lib_masking_sh.md

declare -ga MASK_LIST=()

add_mask() {
    local secret="$1"
    if [[ -n "$secret" && "$secret" != "null" ]]; then
        for m in "${MASK_LIST[@]}"; do
            [[ "$m" == "$secret" ]] && return 0
        done
        MASK_LIST+=("$secret")
    fi
}

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

mask_filter() {
    if [[ ${#MASK_LIST[@]} -eq 0 ]]; then
        cat
        return
    fi

    local sed_script=""
    for secret in "${MASK_LIST[@]}"; do
        local escaped_secret
        escaped_secret=$(printf '%s' "$secret" | sed 's/[][\\.*^$|/]/\\&/g')
        sed_script+="s|$escaped_secret|[MASKED]|g;"
    done
    sed -u "$sed_script"
}

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

scurl() {
    local args=(--retry 5 --retry-delay 3 --connect-timeout 20)
    local url=""
    local is_binary=false
    local is_header=false

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

    if [[ "$url" =~ github\.com|ghcr\.io ]]; then
        if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" || -n "${GHCR_TOKEN:-}" ]]; then
            local token="${GH_TOKEN:-${GITHUB_TOKEN:-${GHCR_TOKEN:-}}}"
            args+=("-H" "Authorization: token $token")
            add_mask "$token"
        fi
    fi

    if [[ "$is_binary" == "true" || ! -t 1 ]]; then
        curl "${args[@]}" "$@"
    else
        curl "${args[@]}" "$@" | mask_filter
    fi
}
