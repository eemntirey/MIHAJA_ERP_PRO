"""add_employee_key_to_tenants

Revision ID: e1f2g3h4i5j6
Revises: d4e5f6a7b8c9
Create Date: 2026-08-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    if not _column_exists('tenants', 'employee_key_hash'):
        op.add_column(
            'tenants',
            sa.Column('employee_key_hash', sa.String(length=255), nullable=True),
        )
    if not _column_exists('tenants', 'employee_key_status'):
        op.add_column(
            'tenants',
            sa.Column('employee_key_status', sa.String(length=20), nullable=True, server_default='active'),
        )


def downgrade() -> None:
    if _column_exists('tenants', 'employee_key_status'):
        op.drop_column('tenants', 'employee_key_status')
    if _column_exists('tenants', 'employee_key_hash'):
        op.drop_column('tenants', 'employee_key_hash')
