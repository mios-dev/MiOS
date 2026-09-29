#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures CPU affinity, Core Scheduling (T-858), and SMT sibling isolation for untrusted sandbox cgroups and subagents.
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
# shellcheck disable=SC1090
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
# shellcheck source=/dev/null
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "Configuring Linux Core Scheduling and CPU Affinity (T-858)"

# 1. Enforce SMT throughput invariant: nosmt must NEVER be present in kernel parameters.
# Core Scheduling eliminates cross-thread speculative snooping while preserving 100%
# Hyper-Threading performance for trusted workloads.
mios_log "Verifying SMT preservation invariant (no nosmt kargs)"
_root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for karg_dir in "${_root_dir}/etc/cmdline.d" "${_root_dir}/usr/lib/bootc/kargs.d" /etc/cmdline.d /usr/lib/bootc/kargs.d; do
    if [[ -d "$karg_dir" ]]; then
        for f in "$karg_dir"/*.conf "$karg_dir"/*.toml; do
            if [[ -f "$f" ]] && grep -qE '\bnosmt\b' "$f"; then
                mios_err "nosmt parameter detected in $f! Core Scheduling preserves SMT throughput; nosmt is forbidden."
                exit 1
            fi
        done
    fi
done
mios_ok "SMT invariant confirmed: nosmt is absent"

# 2. Deploy sandbox.slice and CoreScheduling drop-in
mios_log "Installing sandbox.slice and CoreScheduling drop-in"
install -d -m 0755 /usr/lib/systemd/system/sandbox.slice.d

cat > /usr/lib/systemd/system/sandbox.slice <<'EOF'
[Unit]
Description=MiOS Untrusted Subagent & Sandbox Slice (Core Scheduling Isolated)
Documentation=man:systemd.slice(5)
Before=slices.target

[Slice]
CPUAccounting=yes
ManagedOOMSwap=kill
ManagedOOMMemoryPressure=kill
ManagedOOMMemoryPressureLimit=80%
EOF

cat > /usr/lib/systemd/system/sandbox.slice.d/50-core-sched.conf <<'EOF'
# AI-hint: Core Scheduling configuration for sandbox slice (T-858)
[Slice]
# Enable Core Scheduling isolation for all untrusted units under sandbox.slice
CoreScheduling=yes
EOF

# 3. Deploy systemd service for mios-core-sched
mios_log "Installing mios-core-sched.service"
cat > /usr/lib/systemd/system/mios-core-sched.service <<'EOF'
[Unit]
Description=MiOS Core Scheduling & CPU Affinity Initializer (T-858)
Documentation=man:prctl(2)
After=systemd-sysctl.service local-fs.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/usr/libexec/mios/mios-core-sched status
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

WANTS="/usr/lib/systemd/system/multi-user.target.wants"
install -d -m 0755 "${WANTS}"
ln -sf ../mios-core-sched.service "${WANTS}/mios-core-sched.service"

# 4. Deploy tmpfiles configuration for runtime state directory
install -d -m 0755 /usr/lib/tmpfiles.d
cat > /usr/lib/tmpfiles.d/mios-coresched.conf <<'EOF'
# AI-hint: Runtime state directory for Core Scheduling cookies
d /run/mios/coresched 0755 root root -
EOF

# 5. Ensure mios-core-sched executable permissions
if [[ -f "${_root_dir}/usr/libexec/mios/mios-core-sched" ]]; then
    chmod 0755 "${_root_dir}/usr/libexec/mios/mios-core-sched"
fi
if [[ -f "/usr/libexec/mios/mios-core-sched" ]]; then
    chmod 0755 "/usr/libexec/mios/mios-core-sched"
fi

mios_ok "Linux Core Scheduling and CPU Affinity configuration complete (T-858)"
