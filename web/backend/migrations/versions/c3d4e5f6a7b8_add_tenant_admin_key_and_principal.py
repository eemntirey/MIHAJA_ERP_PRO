"""add_tenant_admin_key_and_principal

Revision ID: c3d4e5f6a7b8
Revises: 20260826181739
Create Date: 2026-08-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = '20260826181739'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def _fk_exists(table: str, fk_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return fk_name in [fk['name'] for fk in inspector.get_foreign_keys(table)]


def upgrade() -> None:
    if not _column_exists('tenants', 'admin_principal_id'):
        op.add_column(
            'tenants',
            sa.Column('admin_principal_id', sa.Integer(), nullable=True),
        )
    if not _fk_exists('tenants', 'fk_tenants_admin_principal_id'):
        with op.batch_alter_table('tenants') as batch_op:
            batch_op.create_foreign_key(
                'fk_tenants_admin_principal_id',
                'utilisateurs',
                ['admin_principal_id'],
                ['id'],
            )


def downgrade() -> None:
    if _fk_exists('tenants', 'fk_tenants_admin_principal_id'):
        op.drop_constraint('fk_tenants_admin_principal_id', 'tenants', type_='foreignkey')
    if _column_exists('tenants', 'admin_principal_id'):
        op.drop_column('tenants', 'admin_principal_id')
