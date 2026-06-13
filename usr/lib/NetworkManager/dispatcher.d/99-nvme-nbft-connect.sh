#!/usr/bin/bash
# AI-hint: Triggers the nvmf-connect-nbft.service systemd unit when a network interface matching the nbft* pattern transitions to an 'up' state via NetworkManager.
# AI-related: nvmf-connect-nbft.service

if [[ "$1" == nbft* ]] && [[ "$2" == "up" ]]; then
    systemctl start nvmf-connect-nbft.service
fi
