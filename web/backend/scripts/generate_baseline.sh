#!/usr/bin/env bash
# =============================================================================
# MIHAJA_ERP_PRO — Generate real Alembic baseline on EMPTY PostgreSQL
# =============================================================================
# Prerequisites:
#   - PostgreSQL running and empty database created
#   - Virtualenv activated with requirements installed
#   - DATABASE_URL pointing to the EMPTY database
#
# Docker (recommended):
#   cd web
#   docker compose --profile db up -d postgres
#   docker compose exec postgres psql -U erp_user -d erp_db \
#     -c "CREATE DATABASE erp_empty;"
#   export DATABASE_URL=postgresql+psycopg://erp_user:erp_password@127.0.0.1:5432/erp_empty
#
# Usage:
#   cd web/backend
#   export FLASK_APP=app:create_app
#   export DATABASE_URL=postgresql+psycopg://erp_user:erp_password@127.0.0.1:5432/erp_empty
#   bash scripts/generate_baseline.sh
#
# After generation:
#   1. Inspect migrations/versions/*_baseline.py carefully
#   2. Verify CREATE TABLE / FK / UNIQUE / INDEX
#   3. Test: drop + recreate erp_empty, then flask db upgrade
#   4. Commit only after review
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== MIHAJA_ERP_PRO — Baseline generation ==="
echo "FLASK_APP=${FLASK_APP:-app:create_app}"
echo "DATABASE_URL=${DATABASE_URL:-(from .env)}"

if [[ "${DATABASE_URL:-}" == *"prod"* ]] || [[ "${DATABASE_URL:-}" == *"production"* ]]; then
  echo "ERROR: DATABASE_URL looks like production. Refusing to run."
  exit 1
fi

export FLASK_APP="${FLASK_APP:-app:create_app}"

echo ""
echo "1. Checking current Alembic head..."
flask db heads || true

echo ""
echo "2. Removing placeholder baseline if present..."
if [ -f migrations/versions/001_baseline.py ]; then
  rm -f migrations/versions/001_baseline.py
  echo "   Removed 001_baseline.py placeholder"
fi

echo ""
echo "3. Generating autogenerate revision..."
flask db migrate -m "baseline"

echo ""
echo "4. Listing generated files:"
ls -la migrations/versions/

echo ""
echo "=== NEXT STEPS (manual) ==="
echo "1. Open the newly generated file in migrations/versions/"
echo "2. Review every CREATE TABLE, FK, UNIQUE, INDEX, ENUM"
echo "3. Test on empty DB:"
echo "     docker compose exec postgres psql -U erp_user -d erp_db -c 'DROP DATABASE IF EXISTS erp_empty;'"
echo "     docker compose exec postgres psql -U erp_user -d erp_db -c 'CREATE DATABASE erp_empty;'"
echo "     flask db upgrade"
echo "4. If OK: git add migrations/versions/ && git commit"
echo "5. Push to FORD"
echo ""
echo "DONE — baseline file generated. Review before commit."
