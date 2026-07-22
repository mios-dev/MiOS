# /etc/profile.d/00-mios-pre-bootc.sh
# Pre-bootc-switch MiOS terminal-experience bridge.
# Sources mios.git's profile.d scripts from /mnt/m/ until the OCI
# image's bootc-switch lands them at the canonical /etc/profile.d/.
# Auto-disables once /etc/profile.d/mios-prompt.sh exists at root.
# Normalize any quoted or uppercase C.UTF-8 locale passed by WSL/clients to glibc's C.utf8 / en_US.UTF-8
case "${LANG:-}" in
    "C.UTF-8"|'"C.UTF-8"') export LANG="C.utf8" ;;
esac
case "${LC_CTYPE:-}" in
    "C.UTF-8"|'"C.UTF-8"') export LC_CTYPE="C.utf8" ;;
esac
case "${LC_COLLATE:-}" in
    "C.UTF-8"|'"C.UTF-8"') export LC_COLLATE="C.utf8" ;;
esac
case "${LC_ALL:-}" in
    "C.UTF-8"|'"C.UTF-8"') export LC_ALL="C.utf8" ;;
esac

if [ ! -e /etc/profile.d/mios-prompt.sh ] && [ -d /mnt/m/etc/profile.d ]; then
    for _miosf in /mnt/m/etc/profile.d/mios-*.sh /mnt/m/etc/profile.d/zz-mios-*.sh; do
        [ -r "$_miosf" ] && . "$_miosf"
    done
    unset _miosf
fi
