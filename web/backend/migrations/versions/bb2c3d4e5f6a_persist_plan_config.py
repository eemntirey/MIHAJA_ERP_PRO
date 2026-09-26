"""Persiste les paramètres éditables des plans d'abonnement.

Revision ID: bb2c3d4e5f6a
Revises: aa1b2c3d4e5f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'bb2c3d4e5f6a'
down_revision: Union[str, None] = 'aa1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'platform_configs' not in tables:
        return

    columns = {c['name'] for c in inspector.get_columns('platform_configs')}
    if 'plans_json' not in columns:
        with op.batch_alter_table('platform_configs') as batch_op:
            batch_op.add_column(sa.Column('plans_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if 'platform_configs' not in tables:
        return

    columns = {c['name'] for c in inspector.get_columns('platform_configs')}
    if 'plans_json' in columns:
        with op.batch_alter_table('platform_configs') as batch_op:
            batch_op.drop_column('plans_json')
