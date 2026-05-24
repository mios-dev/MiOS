# /etc/profile.d/mios-podman-ps.sh
#
# Containers run ROOTFUL on MiOS; a NON-root interactive shell -- the operator's
# SSH / Termius session, the ttyd browser terminals, any similar surface --
# running `podman ps` sees NOTHING (/run/podman is 0700 root:root). This additive
# shell function makes them VISIBLE everywhere: it shows the root-written,
# world-readable snapshot (mios-podman-ps.service -> /var/lib/mios/podman-ps.json,
# the same SSOT the dashboard + the container_status verb use) whenever the real
# rootless `podman ps` comes back empty. Operator 2026-05-23: "make sure
# containers are visible in termius and other similar surfaces".
#
# Safe + additive: only augments an EMPTY `ps` for a NON-root caller, never hides
# real output, and only affects INTERACTIVE login shells (scripts / `ssh host
# podman ...` non-login shells skip profile.d and get the real binary untouched).
case $- in
  *i*) : ;;            # interactive -- install the helper
  *)   return 2>/dev/null || true ;;
esac

podman() {
  if [ "$1" = "ps" ] && [ "$(id -u)" -ne 0 ]; then
    local _snap="${MIOS_PODMAN_PS_SNAPSHOT:-/var/lib/mios/podman-ps.json}"
    local _out; _out="$(command podman "$@" 2>/dev/null)"
    [ -n "$_out" ] && printf '%s\n' "$_out"
    if ! printf '%s\n' "$_out" | tail -n +2 | grep -q '[^[:space:]]' && [ -r "$_snap" ]; then
      echo "── rootful containers (root snapshot; your rootless podman sees none) ──"
      python3 - "$_snap" <<'PY' 2>/dev/null
import sys, json
try:
    rows = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
if not isinstance(rows, list):
    sys.exit(0)
print(f"{'NAMES':30} {'STATUS':24} IMAGE")
for c in rows:
    n = c.get('Names'); n = ','.join(n) if isinstance(n, list) else (n or '')
    st = c.get('Status') or c.get('State') or ''
    print(f"{n[:29]:30} {st[:23]:24} {c.get('Image') or ''}")
PY
    fi
  else
    command podman "$@"
  fi
}
