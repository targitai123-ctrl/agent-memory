#!/bin/bash
# One-command environment setup. Idempotent — safe to re-run after a VM reset.
set -e

echo "==> Installing Postgres + pgvector (if missing)"
if ! dpkg -l | grep -q postgresql-16-pgvector; then
  sudo -n apt-get update -qq
  sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-16-pgvector
fi

echo "==> Starting Postgres"
sudo -n service postgresql start || true
sleep 2

echo "==> Creating role and database (if missing)"
sudo -n -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='hatch'" | grep -q 1 \
  || sudo -n -u postgres psql -c "CREATE USER hatch WITH SUPERUSER PASSWORD 'hatch';"
sudo -n -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='agent_memory'" | grep -q 1 \
  || sudo -n -u postgres psql -c "CREATE DATABASE agent_memory OWNER hatch;"

echo "==> Done. Start the API with:"
echo "    cd ~/workspace/agent-memory && ./scripts/run.sh"
