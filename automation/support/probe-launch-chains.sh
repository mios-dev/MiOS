#!/bin/bash
# Probe launch chains for the common operator queries.
set -u
for q in files terminal editor calc chrome browser music maps; do
    bash /mnt/c/MiOS/automation/support/probe-launch-chain.sh "$q"
    echo
done
