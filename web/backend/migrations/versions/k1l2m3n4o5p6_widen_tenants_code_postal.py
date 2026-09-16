"""widen_tenants_code_postal

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-09-07 18:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tenants') as batch_op:
        batch_op.alter_column(
            'code_postal',
            existing_type=sa.String(length=10),
            type_=sa.String(length=20),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('tenants') as batch_op:
        batch_op.alter_column(
            'code_postal',
            existing_type=sa.String(length=20),
            type_=sa.String(length=10),
            existing_nullable=True,
        )