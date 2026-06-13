#!/bin/bash
# AI-hint: Iterates through a predefined list of common operator queries (files, terminal, editor, etc.) to execute the probe_launch_chain.sh script for each, initializing the environment for automated testing.
# Probe launch chains for the common operator queries.
set -euo pipefail
for q in files terminal editor calc chrome browser music maps; do
    bash /mnt/c/MiOS/automation/support/probe-launch-chain.sh "$q"
    echo
done
