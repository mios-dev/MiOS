#!/usr/bin/bash
# AI-hint: NetworkManager dispatcher hook: when an NBFT (NVMe-oF boot firmware table) interface comes up, start nvmf-connect-nbft.service.

if [[ "$1" == nbft* ]] && [[ "$2" == "up" ]]; then
    systemctl start nvmf-connect-nbft.service
fi
