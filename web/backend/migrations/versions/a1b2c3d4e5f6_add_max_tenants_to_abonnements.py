"""add_max_tenants_to_abonnements

Revision ID: a1b2c3d4e5f6
Revises: 9d32b5c43ad9
Create Date: 2026-08-25 15:23:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d32b5c43ad9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    if not _column_exists('abonnements', 'max_tenants'):
        op.add_column('abonnements', sa.Column('max_tenants', sa.Integer(), nullable=True))


def downgrade() -> None:
    if _column_exists('abonnements', 'max_tenants'):
        op.drop_column('abonnements', 'max_tenants')
