#!/bin/bash
# automation/support/bringup-pgvector.sh -- stand up mios-pgvector on a dev VM
# (WS-9 / T23 cutover step 1: the container). ADDITIVE -- runs ALONGSIDE SurrealDB;
# the agent-pipe dual-writes (db_backend=dual) once psycopg is in the venv (step 2,
# separate). Creates the data dir (uid 826), deploys schema-init + a RENDERED
# quadlet (Quadlet doesn't expand ${VAR:-def}), starts, verifies tables + the
# vector extension. Idempotent.
set -euo pipefail

SRC=/mnt/c/MiOS
DATA=/var/lib/mios/pgvector

echo "[pg] data dir (uid 826, 0700 -- postgres refuses world-readable PGDATA)"
sudo install -d -m 0700 -o 826 -g 826 "$DATA"

echo "[pg] deploy schema-init.sql"
sudo install -d -m 0755 /usr/share/mios/postgres
tr -d '\r' < "$SRC/usr/share/mios/postgres/schema-init.sql" | sudo tee /usr/share/mios/postgres/schema-init.sql >/dev/null

echo "[pg] render + deploy quadlet"
tr -d '\r' < "$SRC/usr/share/containers/systemd/mios-pgvector.container" \
    | sed -E 's/\$\{[A-Z_]+:-([^}]*)\}/\1/g' \
    | sudo tee /etc/containers/systemd/mios-pgvector.container >/dev/null

echo "[pg] daemon-reload + start"
sudo systemctl daemon-reload
sudo systemctl start mios-pgvector.service 2>&1 || true
sleep 10
echo "[pg] state=$(systemctl is-active mios-pgvector.service)"
sudo systemctl --no-pager -l status mios-pgvector.service 2>/dev/null | tail -10
echo "[pg] === recent log ==="
sudo journalctl -u mios-pgvector.service --no-pager 2>/dev/null | tail -18
echo "[pg] === verify tables (\\dt) ==="
sudo podman exec mios-pgvector psql -U mios -d mios -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1;" 2>&1 | head -30
echo "[pg] === verify vector ext ==="
sudo podman exec mios-pgvector psql -U mios -d mios -tAc "SELECT extname FROM pg_extension WHERE extname='vector';" 2>&1 | head
