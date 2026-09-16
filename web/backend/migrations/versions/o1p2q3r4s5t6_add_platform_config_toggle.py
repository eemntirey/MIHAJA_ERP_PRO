"""add platform_config toggle

Revision ID: o1p2q3r4s5t6
Revises: 8b2065228309
Create Date: 2026-09-15 15:38:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o1p2q3r4s5t6'
down_revision: Union[str, None] = '8b2065228309'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'platform_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('is_subscription_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], name='fk_platform_configs_updated_by'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('platform_configs')
