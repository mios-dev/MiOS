#!/bin/bash
# MiOS v0.1.1 — 37-selinux: Build-time SELinux policy fixes
# Custom per-rule modules for known Fedora Rawhide / systemd 260 denials.
set -euo pipefail

echo "[37-selinux] Applying SELinux build-time fixes..."

# ═══ Restorecon — fix labels for all major trees ═══
if command -v restorecon &>/dev/null; then
    echo "[37-selinux] Running restorecon on /boot /etc /usr /var..."
    restorecon -R /boot /etc /usr /var 2>/dev/null || true
fi

# ═══ Semanage import — atomic booleans + fcontexts ═══
if command -v semanage &>/dev/null; then
    echo "[37-selinux] Applying SELinux booleans and fcontexts..."
    semanage import <<'EOSEM' 2>/dev/null || true
boolean -m --on container_manage_cgroup
boolean -m --on container_use_cephfs
boolean -m --on daemons_dump_core
boolean -m --on domain_can_mmap_files
boolean -m --on virt_sandbox_use_all_caps
boolean -m --on virt_use_nfs
boolean -m --on virt_use_samba
boolean -m --on nis_enabled
fcontext -a -t boot_t '/boot/bootupd-state.json'
fcontext -a -t accountsd_var_lib_t '/usr/share/accountsservice/interfaces(/.*)?'
fcontext -a -t ceph_var_lib_t '/var/lib/ceph(/.*)?'
fcontext -a -t ceph_log_t '/var/log/ceph(/.*)?'
fcontext -a -t xdm_var_lib_t '/var/lib/gnome-remote-desktop(/.*)?'
EOSEM
    restorecon -v /boot/bootupd-state.json 2>/dev/null || true
    restorecon -R /usr/share/accountsservice 2>/dev/null || true
    restorecon -R /var/lib/gnome-remote-desktop 2>/dev/null || true
    echo "[37-selinux] ✓ Booleans and fcontexts applied"
fi

# ═══ Custom policy modules ═══
if command -v checkmodule &>/dev/null && command -v semodule_package &>/dev/null; then
    echo "[37-selinux] Building custom SELinux policy modules..."

    SELINUX_OK=0
    SELINUX_FAIL=0

    declare -A MIOS_POLICIES

    MIOS_POLICIES[bootupd]='
module mios_bootupd 1.0;
require { type boot_t; type bootupd_t; class file { read getattr open }; }
allow bootupd_t boot_t:file { read getattr open };'

    MIOS_POLICIES[accountsd]='
module mios_accountsd 1.0;
require { type accountsd_t; class lnk_file { read getattr }; }
allow accountsd_t self:lnk_file { read getattr };'

    MIOS_POLICIES[resolved]='
module mios_resolved 1.0;
require { type systemd_resolved_t; type init_var_run_t; class sock_file write; }
allow systemd_resolved_t init_var_run_t:sock_file write;'

    MIOS_POLICIES[fapolicyd]='
module mios_fapolicyd 1.0;
require { type fapolicyd_t; type xdm_var_run_t; class sock_file write; }
allow fapolicyd_t xdm_var_run_t:sock_file write;'

    MIOS_POLICIES[chcon]='
module mios_chcon 1.0;
require { type chcon_t; class capability mac_admin; }
allow chcon_t self:capability mac_admin;'

    MIOS_POLICIES[accountsd_homed]='
module mios_accountsd_homed 1.0;
require { type accountsd_t; type systemd_homed_t; class dbus send_msg; }
allow accountsd_t systemd_homed_t:dbus send_msg;
allow systemd_homed_t accountsd_t:dbus send_msg;'

    MIOS_POLICIES[accountsd_watch]='
module mios_accountsd_watch 1.0;
require { type accountsd_t; type usr_t; class dir { watch watch_reads }; }
allow accountsd_t usr_t:dir { watch watch_reads };'

    MIOS_POLICIES[fapolicyd_gdm]='
module mios_fapolicyd_gdm 1.1;
require { type fapolicyd_t; type xdm_t; class unix_stream_socket connectto; class fd use; class fifo_file write; }
allow fapolicyd_t xdm_t:unix_stream_socket connectto;
allow fapolicyd_t xdm_t:fd use;
allow fapolicyd_t xdm_t:fifo_file write;'

    MIOS_POLICIES[fapolicyd_grd]='
module mios_fapolicyd_grd 1.0;
require { type fapolicyd_t; type gnome_remote_desktop_t; class unix_stream_socket connectto; class fd use; class fifo_file write; }
allow fapolicyd_t gnome_remote_desktop_t:unix_stream_socket connectto;
allow fapolicyd_t gnome_remote_desktop_t:fd use;
allow fapolicyd_t gnome_remote_desktop_t:fifo_file write;'

    MIOS_POLICIES[portabled]='
module mios_portabled 1.0;
require { type init_t; type systemd_portabled_t; class dbus send_msg; }
allow init_t systemd_portabled_t:dbus send_msg;
allow systemd_portabled_t init_t:dbus send_msg;'

    MIOS_POLICIES[kvmfr]='
module mios_kvmfr 1.0;
require { type svirt_t; type device_t; class chr_file { open read write map getattr }; }
allow svirt_t device_t:chr_file { open read write map getattr };'

    MIOS_POLICIES[coreos_bootmount]='
module mios_coreos_bootmount 1.0;
require { type coreos_boot_mount_generator_t; type systemd_generator_unit_file_t; class dir { write add_name remove_name }; class file { create write open rename unlink }; }
allow coreos_boot_mount_generator_t systemd_generator_unit_file_t:dir { write add_name remove_name };
allow coreos_boot_mount_generator_t systemd_generator_unit_file_t:file { create write open rename unlink };'

    MIOS_POLICIES[gdm_cache]='
module mios_gdm_cache 1.0;
require { type xdm_t; type cache_home_t; class dir { add_name write create setattr }; class file { create write open getattr setattr }; }
allow xdm_t cache_home_t:dir { add_name write create setattr };
allow xdm_t cache_home_t:file { create write open getattr setattr };'

    MIOS_POLICIES[homed_varhome]='
module mios_homed_varhome 1.0;
require { type systemd_homed_t; type home_root_t; class dir { read getattr open search }; }
allow systemd_homed_t home_root_t:dir { read getattr open search };'

    MIOS_POLICIES[bootupd_state]='
module mios_bootupd_state 1.1;
require { type bootupd_t; type boot_t; class file { read open getattr lock ioctl }; class dir { read open getattr search }; }
allow bootupd_t boot_t:file { read open getattr lock ioctl };
allow bootupd_t boot_t:dir { read open getattr search };'

    MIOS_POLICIES[resolved_hook]='
module mios_resolved_hook 1.0;
require { type systemd_resolved_t; type init_t; class unix_stream_socket connectto; class sock_file write; }
allow systemd_resolved_t init_t:unix_stream_socket connectto;
allow systemd_resolved_t init_t:sock_file write;'

    MIOS_POLICIES[accountsd_malcontent]='
module mios_accountsd_malcontent 1.0;
require { type accountsd_t; type usr_t; class lnk_file { read getattr }; class file { read open getattr ioctl }; class dir { read open getattr search }; }
allow accountsd_t usr_t:lnk_file { read getattr };
allow accountsd_t usr_t:file { read open getattr ioctl };
allow accountsd_t usr_t:dir { read open getattr search };'

    MIOS_POLICIES[chcon_macadmin]='
module mios_chcon_macadmin 1.0;
require { type chcon_t; class capability2 mac_admin; }
allow chcon_t self:capability2 mac_admin;'

    MIOS_POLICIES[gdm_session_cache]='
module mios_gdm_session_cache 1.0;
require { type xdm_t; type cache_home_t; class dir { add_name write create read open getattr search setattr }; class file { create write read open getattr setattr }; }
allow xdm_t cache_home_t:dir { add_name write create read open getattr search setattr };
allow xdm_t cache_home_t:file { create write read open getattr setattr };'

    mkdir -p /usr/share/selinux/packages/mios

    for name in "${!MIOS_POLICIES[@]}"; do
        echo "${MIOS_POLICIES[$name]}" > "/tmp/mios_${name}.te"
        if checkmodule -M -m -o "/tmp/mios_${name}.mod" "/tmp/mios_${name}.te" 2>/dev/null && \
           semodule_package -o "/tmp/mios_${name}.pp" -m "/tmp/mios_${name}.mod" 2>/dev/null; then
            install -m 0644 "/tmp/mios_${name}.pp" "/usr/share/selinux/packages/mios/mios_${name}.pp"
            echo "[37-selinux] mios_${name}: Staged"
            SELINUX_OK=$((SELINUX_OK + 1))
        else
            echo "[37-selinux] mios_${name}: SKIPPED (type missing in current policy)"
            SELINUX_FAIL=$((SELINUX_FAIL + 1))
        fi
        rm -f "/tmp/mios_${name}".{te,mod,pp}
    done

    echo "[37-selinux] ${SELINUX_OK} policies staged in /usr/share/selinux/packages/mios/, ${SELINUX_FAIL} skipped"
fi

echo "[37-selinux] SELinux configuration complete."
