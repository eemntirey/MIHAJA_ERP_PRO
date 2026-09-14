"""add entrepots, stock_entrepot, and stock_min/max

Revision ID: 07efbe5e9c15
Revises: m1n2o3p4q5r6
Create Date: 2026-09-11 11:29:43.332681
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07efbe5e9c15'
down_revision: Union[str, None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(table):
        return False
    return column in [c['name'] for c in inspector.get_columns(table)]


def _index_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(table):
        return False
    return name in [i['name'] for i in inspector.get_indexes(table)]


def _unique_constraint_exists(table: str, name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(table):
        return False
    return name in [u['name'] for u in inspector.get_unique_constraints(table)]


def upgrade() -> None:
    # --- Table entrepots (multi-entrepôts) -------------------------------
    if not _table_exists('entrepots'):
        op.create_table(
            'entrepots',
            sa.Column('nom', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=20), nullable=True),
            sa.Column('adresse', sa.Text(), nullable=True),
            sa.Column('ville', sa.String(length=100), nullable=True),
            sa.Column('telephone', sa.String(length=20), nullable=True),
            sa.Column('responsable', sa.String(length=100), nullable=True),
            sa.Column('capacite', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('principal', sa.Boolean(), server_default=sa.false(), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], name='fk_basemodel_created_by', use_alter=True),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_basetenantmodel_tenant_id', use_alter=True),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], name='fk_basemodel_updated_by', use_alter=True),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('entrepots', schema=None) as batch_op:
            batch_op.create_index('idx_entrepot_nom', ['nom'], unique=False)
            batch_op.create_index(batch_op.f('ix_entrepots_code'), ['code'], unique=False)
            batch_op.create_index(batch_op.f('ix_entrepots_tenant_id'), ['tenant_id'], unique=False)

    # --- Table stocks_entrepot (stock par entrepôt) ----------------------
    if not _table_exists('stocks_entrepot'):
        op.create_table(
            'stocks_entrepot',
            sa.Column('produit_id', sa.Integer(), nullable=False),
            sa.Column('entrepot_id', sa.Integer(), nullable=False),
            sa.Column('quantite', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False),
            sa.Column('seuil_min', sa.Numeric(precision=10, scale=2), server_default='0', nullable=True),
            sa.Column('seuil_max', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], name='fk_basemodel_created_by', use_alter=True),
            sa.ForeignKeyConstraint(['entrepot_id'], ['entrepots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['produit_id'], ['produits.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_basetenantmodel_tenant_id', use_alter=True),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], name='fk_basemodel_updated_by', use_alter=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('produit_id', 'entrepot_id', name='uq_stock_entrepot_produit_entrepot'),
        )
        with op.batch_alter_table('stocks_entrepot', schema=None) as batch_op:
            batch_op.create_index('idx_stock_entrepot_entrepot', ['entrepot_id'], unique=False)
            batch_op.create_index('idx_stock_entrepot_produit', ['produit_id', 'entrepot_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_entrepot_entrepot_id'), ['entrepot_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_entrepot_produit_id'), ['produit_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_entrepot_tenant_id'), ['tenant_id'], unique=False)

    # Réparation : les bases migrées avec la première version (auto-générée)
    # de cette révision n'ont pas la contrainte d'unicité — on l'ajoute.
    if (
        _table_exists('stocks_entrepot')
        and not _unique_constraint_exists('stocks_entrepot', 'uq_stock_entrepot_produit_entrepot')
    ):
        op.create_unique_constraint(
            'uq_stock_entrepot_produit_entrepot',
            'stocks_entrepot',
            ['produit_id', 'entrepot_id'],
        )

    # --- Produits : seuils stock min / max -------------------------------
    if not _column_exists('produits', 'stock_min'):
        op.add_column(
            'produits',
            sa.Column('stock_min', sa.Numeric(precision=10, scale=2), server_default='0', nullable=True),
        )
    if not _column_exists('produits', 'stock_max'):
        op.add_column(
            'produits',
            sa.Column('stock_max', sa.Numeric(precision=10, scale=2), nullable=True),
        )


def downgrade() -> None:
    if _column_exists('produits', 'stock_max'):
        with op.batch_alter_table('produits', schema=None) as batch_op:
            batch_op.drop_column('stock_max')
    if _column_exists('produits', 'stock_min'):
        with op.batch_alter_table('produits', schema=None) as batch_op:
            batch_op.drop_column('stock_min')

    if _table_exists('stocks_entrepot'):
        if _unique_constraint_exists('stocks_entrepot', 'uq_stock_entrepot_produit_entrepot'):
            op.drop_constraint('uq_stock_entrepot_produit_entrepot', 'stocks_entrepot', type_='unique')
        for index_name in (
            'ix_stocks_entrepot_tenant_id',
            'ix_stocks_entrepot_produit_id',
            'ix_stocks_entrepot_entrepot_id',
            'idx_stock_entrepot_produit',
            'idx_stock_entrepot_entrepot',
        ):
            if _index_exists('stocks_entrepot', index_name):
                with op.batch_alter_table('stocks_entrepot', schema=None) as batch_op:
                    batch_op.drop_index(index_name)
        op.drop_table('stocks_entrepot')

    if _table_exists('entrepots'):
        for index_name in (
            'ix_entrepots_tenant_id',
            'ix_entrepots_code',
            'idx_entrepot_nom',
        ):
            if _index_exists('entrepots', index_name):
                with op.batch_alter_table('entrepots', schema=None) as batch_op:
                    batch_op.drop_index(index_name)
        op.drop_table('entrepots')
