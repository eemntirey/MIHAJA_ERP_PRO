"""Reparation des colonnes manquantes (bases provisionnees hors migration).

Certaines bases de dev (notamment provisionnees par `db.create_all()` puis
marquees `db stamp head`) sont restees sans colonnes ajoutees ensuite aux
modeles. Consequence : des SELECT sur ces tables echouent avec
`sqlite3.OperationalError: no such column` (ex. produits.stock_min,
utilisateurs.local_password_hash).

Cette migration re-synchronise uniquement les colonnes manquantes, de facon
idempotente (chaque ajout est conditionne a l'inspection du schema) :

 - produits.stock_min             (Numeric(10,2), defaut 0)
 - produits.stock_max             (Numeric(10,2), nullable)
 - produits.published             (Boolean, NOT NULL, defaut 1)
 - utilisateurs.local_password_hash (String(255), nullable)
 - commandes_client.utilisateur_id  (Integer, FK utilisateurs.id, nullable)
 - employes.conges_credit_annuel    (Integer, defaut 30)

Revision ID: z9y8x7w6v5u4
Revises: c2d3e4f5a6b7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'z9y8x7w6v5u4'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in [c['name'] for c in inspector.get_columns(table)]


def _index_exists(table: str, index: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return index in [i['name'] for i in inspector.get_indexes(table)]


def _add_column(table: str, column: sa.Column) -> None:
    # SQLite : ALTER TABLE ADD COLUMN natif (colonnes nullable / avec defaut).
    op.add_column(table, column)


def upgrade() -> None:
    # --- produits : seuils de stock et vitrine -----------------------------
    if not _column_exists('produits', 'stock_min'):
        _add_column(
            'produits',
            sa.Column('stock_min', sa.Numeric(10, 2), nullable=True,
                      server_default='0'),
        )
    if not _column_exists('produits', 'stock_max'):
        _add_column(
            'produits',
            sa.Column('stock_max', sa.Numeric(10, 2), nullable=True),
        )
    if not _column_exists('produits', 'published'):
        _add_column(
            'produits',
            sa.Column('published', sa.Boolean(), nullable=False,
                      server_default=sa.text('1')),
        )

    # --- utilisateurs : cache de mot de passe du backend embarque ----------
    if not _column_exists('utilisateurs', 'local_password_hash'):
        _add_column(
            'utilisateurs',
            sa.Column('local_password_hash', sa.String(255), nullable=True),
        )

    # --- commandes_client : client connecte (vitrine) ----------------------
    if not _column_exists('commandes_client', 'utilisateur_id'):
        bind = op.get_bind()
        if bind.dialect.name == 'sqlite':
            # SQLite n'autorise pas l'ajout de contrainte via alembic
            # (batch = copie de table), mais accepte une clause REFERENCES
            # inline dans ALTER TABLE ADD COLUMN quand la colonne est
            # nullable. On preserve ainsi la cle etrangere du modele.
            op.execute(
                'ALTER TABLE commandes_client ADD COLUMN utilisateur_id '
                'INTEGER REFERENCES utilisateurs (id)'
            )
        else:
            op.add_column(
                'commandes_client',
                sa.Column('utilisateur_id', sa.Integer(),
                          sa.ForeignKey('utilisateurs.id'), nullable=True),
            )
    if _column_exists('commandes_client', 'utilisateur_id') and \
            not _index_exists('commandes_client',
                              'ix_commandes_client_utilisateur_id'):
        op.create_index(
            'ix_commandes_client_utilisateur_id',
            'commandes_client',
            ['utilisateur_id'],
            unique=False,
        )

    # --- employes : credit de conges annuel --------------------------------
    if not _column_exists('employes', 'conges_credit_annuel'):
        _add_column(
            'employes',
            sa.Column('conges_credit_annuel', sa.Integer(), nullable=True,
                      server_default='30'),
        )


def downgrade() -> None:
    if _column_exists('employes', 'conges_credit_annuel'):
        with op.batch_alter_table('employes') as batch_op:
            batch_op.drop_column('conges_credit_annuel')
    if _index_exists('commandes_client', 'ix_commandes_client_utilisateur_id'):
        op.drop_index('ix_commandes_client_utilisateur_id',
                      table_name='commandes_client')
    if _column_exists('commandes_client', 'utilisateur_id'):
        with op.batch_alter_table('commandes_client') as batch_op:
            batch_op.drop_column('utilisateur_id')
    if _column_exists('utilisateurs', 'local_password_hash'):
        with op.batch_alter_table('utilisateurs') as batch_op:
            batch_op.drop_column('local_password_hash')
    if _column_exists('produits', 'published'):
        with op.batch_alter_table('produits') as batch_op:
            batch_op.drop_column('published')
    if _column_exists('produits', 'stock_max'):
        with op.batch_alter_table('produits') as batch_op:
            batch_op.drop_column('stock_max')
    if _column_exists('produits', 'stock_min'):
        with op.batch_alter_table('produits') as batch_op:
            batch_op.drop_column('stock_min')
