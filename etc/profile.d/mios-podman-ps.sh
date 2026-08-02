# AI-hint: Provides a shell function to intercept `podman ps` for non-root users, falling back to a JSON snapshot of rootful containers if the local rootless podman view is empty.
# AI-related: mios-podman-ps, mios-podman-ps.service
# AI-functions: podman
if [ -z "${CONTAINER_HOST:-}" ] && [ -S /run/podman/podman.sock ] && [ -r /run/podman/podman.sock ]; then
    export CONTAINER_HOST="unix:///run/podman/podman.sock"
fi

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
      echo "── rootful containers ──"
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
