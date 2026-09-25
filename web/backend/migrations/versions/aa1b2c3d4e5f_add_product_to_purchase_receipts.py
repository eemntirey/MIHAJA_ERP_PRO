"""Ajoute le produit rattache a une reception d'achat.

Permet d'integrer chaque reception au stock sans inventer une
repartition lorsqu'une commande comporte plusieurs produits.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'aa1b2c3d4e5f'
down_revision: Union[str, None] = 'z9y8x7w6v5u4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c['name'] for c in inspector.get_columns('receptions_achat')}

    if 'produit_id' not in columns:
        with op.batch_alter_table('receptions_achat') as batch_op:
            batch_op.add_column(sa.Column('produit_id', sa.Integer(), nullable=True))
            batch_op.create_index(
                'ix_receptions_achat_produit_id',
                ['produit_id'],
                unique=False,
            )
            batch_op.create_foreign_key(
                'fk_receptions_achat_produit_id',
                'produits',
                ['produit_id'],
                ['id'],
            )

    # Les anciennes lignes ne peuvent pas etre rattachees automatiquement
    # si elles correspondent a plusieurs produits. On les laisse NULL pour
    # permettre une migration progressive des historiques.


def downgrade() -> None:
    with op.batch_alter_table('receptions_achat') as batch_op:
        batch_op.drop_constraint('fk_receptions_achat_produit_id', type_='foreignkey')
        batch_op.drop_index('ix_receptions_achat_produit_id')
        batch_op.drop_column('produit_id')
