"""baseline — PLACEHOLDER — replace with real autogenerate

Revision ID: 001_baseline
Revises:
Create Date: 2026-09-07

=============================================================================
THIS IS A STRUCTURAL PLACEHOLDER ONLY.
=============================================================================

It intentionally contains no CREATE TABLE operations.

To generate the REAL baseline against an EMPTY PostgreSQL database:

    cd web/backend
    export FLASK_APP=app:create_app
    export DATABASE_URL=postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_empty

    # Option A — helper script
    bash scripts/generate_baseline.sh

    # Option B — manual
    rm -f migrations/versions/001_baseline.py
    flask db migrate -m "baseline"

Then:
  1. Inspect the generated file (CREATE TABLE, FK, UNIQUE, INDEX, ENUM)
  2. Drop and recreate empty DB
  3. flask db upgrade
  4. Verify schema
  5. Commit only after successful test

Do NOT use db.create_all() in production.
Do NOT stamp a non-empty database to hide missing migrations.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Intentionally empty.
    # Replace this file by running flask db migrate on an empty PostgreSQL.
    pass


def downgrade():
    pass
