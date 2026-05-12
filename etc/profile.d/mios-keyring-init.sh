# /etc/profile.d/mios-keyring-init.sh
#
# Stub. Auto-unlock has moved to mios-keyring-autounlock.service
# (systemd user unit) which fires at WSL distro boot, before any app
# could trigger a libsecret prompt. The previous interactive prompt
# at first shell open is intentionally removed -- operator should
# never see a keyring dialog during normal use.
#
# Edit the password via mios.toml [identity].default_password
# (or mios.html). The service reads it on every boot.
return 0
