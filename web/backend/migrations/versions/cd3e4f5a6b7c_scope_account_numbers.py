"""Corrige l'unicité des numéros de comptes comptables par tenant.

Revision ID: cd3e4f5a6b7c
Revises: bb2c3d4e5f6a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'cd3e4f5a6b7c'
down_revision: Union[str, None] = 'bb2c3d4e5f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table = 'comptes_comptables'
    if table not in inspector.get_table_names():
        return

    # PostgreSQL crée une contrainte UNIQUE pour unique=True.
    for constraint in inspector.get_unique_constraints(table):
        columns = constraint.get('column_names') or []
        name = constraint.get('name')
        if name and columns == ['numero']:
            op.drop_constraint(name, table, type_='unique')

    # Certains moteurs exposent la contrainte sous forme d'index unique.
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table):
        columns = index.get('column_names') or []
        name = index.get('name')
        if name and index.get('unique') and columns == ['numero']:
            try:
                op.drop_index(name, table_name=table)
            except Exception:
                pass

    inspector = sa.inspect(bind)
    existing = {
        c.get('name') for c in inspector.get_unique_constraints(table)
    }
    if 'uq_compte_tenant_numero' not in existing:
        op.create_unique_constraint(
            'uq_compte_tenant_numero',
            table,
            ['tenant_id', 'numero'],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table = 'comptes_comptables'
    if table not in inspector.get_table_names():
        return

    existing = {
        c.get('name') for c in inspector.get_unique_constraints(table)
    }
    if 'uq_compte_tenant_numero' in existing:
        op.drop_constraint('uq_compte_tenant_numero', table, type_='unique')
