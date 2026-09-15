"""add_utilisateur_id_to_commandes_client

Revision ID: n1o2p3q4r5s6
Revises: 07efbe5e9c15
Create Date: 2026-09-14 00:00:00.000000

Lie les commandes vitrine (commandes_client) au compte utilisateur connecté.
NULL = commande passée en invité. Permet l'endpoint GET /public/mes-commandes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'n1o2p3q4r5s6'
down_revision: Union[str, None] = '07efbe5e9c15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    if not _column_exists('commandes_client', 'utilisateur_id'):
        op.add_column(
            'commandes_client',
            sa.Column('utilisateur_id', sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            'fk_commandes_client_utilisateur_id',
            'commandes_client',
            'utilisateurs',
            ['utilisateur_id'],
            ['id'],
        )
        op.create_index(
            'ix_commandes_client_utilisateur_id',
            'commandes_client',
            ['utilisateur_id'],
        )


def downgrade() -> None:
    if _column_exists('commandes_client', 'utilisateur_id'):
        op.drop_index(
            'ix_commandes_client_utilisateur_id', table_name='commandes_client'
        )
        op.drop_constraint(
            'fk_commandes_client_utilisateur_id', 'commandes_client', type_='foreignkey'
        )
        op.drop_column('commandes_client', 'utilisateur_id')
