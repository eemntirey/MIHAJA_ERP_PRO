"""move_employee_key_from_tenants_to_utilisateurs

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    if not _column_exists('utilisateurs', 'employee_key_hash'):
        op.add_column(
            'utilisateurs',
            sa.Column('employee_key_hash', sa.String(length=255), nullable=True),
        )
    if not _column_exists('utilisateurs', 'employee_key_status'):
        op.add_column(
            'utilisateurs',
            sa.Column('employee_key_status', sa.String(length=20), nullable=True, server_default='active'),
        )
    if _column_exists('tenants', 'employee_key_hash'):
        op.drop_column('tenants', 'employee_key_hash')
    if _column_exists('tenants', 'employee_key_status'):
        op.drop_column('tenants', 'employee_key_status')


def downgrade() -> None:
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
    if _column_exists('utilisateurs', 'employee_key_hash'):
        op.drop_column('utilisateurs', 'employee_key_hash')
    if _column_exists('utilisateurs', 'employee_key_status'):
        op.drop_column('utilisateurs', 'employee_key_status')
