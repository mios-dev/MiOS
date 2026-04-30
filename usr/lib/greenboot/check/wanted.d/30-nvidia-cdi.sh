#!/usr/bin/bash
# Wanted (warning only, not rollback): NVIDIA CDI spec exists when a GPU is present
set -euo pipefail
if compgen -G "/dev/nvidia*" >/dev/null; then
    if [[ -s /var/run/cdi/nvidia.yaml ]] || [[ -s /etc/cdi/nvidia.yaml ]]; then
        if command -v nvidia-ctk >/dev/null; then
            if ! nvidia-ctk cdi list 2>/dev/null | grep -q "nvidia.com/gpu"; then
                echo "NVIDIA CDI spec exists but nvidia-ctk reports no valid devices"
                exit 1
            fi
        fi
    else
        echo "NVIDIA device present but CDI spec missing (/var/run/cdi/ and /etc/cdi/)"
        exit 1
    fi
fi
