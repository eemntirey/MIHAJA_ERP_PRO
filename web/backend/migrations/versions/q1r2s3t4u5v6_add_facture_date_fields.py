"""add date_echeance and date_facture to factures

Revision ID: q1r2s3t4u5v6
Revises: p1q2r3s4t5u6
Create Date: 2026-09-21 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'q1r2s3t4u5v6'
down_revision: Union[str, None] = 'p1q2r3s4t5u6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('factures'):
        columns = {col['name'] for col in inspector.get_columns('factures')}

        if 'date_facture' not in columns:
            op.add_column('factures', sa.Column('date_facture', sa.Date(), nullable=True))
        if 'date_echeance' not in columns:
            op.add_column('factures', sa.Column('date_echeance', sa.Date(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('factures'):
        columns = {col['name'] for col in inspector.get_columns('factures')}

        if 'date_echeance' in columns:
            op.drop_column('factures', 'date_echeance')
        if 'date_facture' in columns:
            op.drop_column('factures', 'date_facture')
