"""add conges table and employe conges credit

Revision ID: p1q2r3s4t5u6
Revises: o1p2q3r4s5t6
Create Date: 2026-09-16 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p1q2r3s4t5u6'
down_revision: Union[str, None] = 'o1p2q3r4s5t6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('conges'):
        op.create_table(
            'conges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('employe_id', sa.Integer(), nullable=False),
            sa.Column('type_conge', sa.String(length=20), nullable=True),
            sa.Column('date_debut', sa.Date(), nullable=False),
            sa.Column('date_fin', sa.Date(), nullable=False),
            sa.Column('nb_jours', sa.Integer(), nullable=False),
            sa.Column('annee', sa.Integer(), nullable=False),
            sa.Column('motif', sa.String(length=200), nullable=True),
            sa.Column('statut', sa.String(length=20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['employe_id'], ['employes.id'], ),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_conges_annee'), 'conges', ['annee'], unique=False)
        op.create_index(op.f('ix_conges_employe_id'), 'conges', ['employe_id'], unique=False)
        op.create_index(op.f('ix_conges_tenant_id'), 'conges', ['tenant_id'], unique=False)
        op.create_index('idx_conge_employe_dates', 'conges', ['employe_id', 'date_debut', 'date_fin'], unique=False)

    if 'conges_credit_annuel' not in [c['name'] for c in inspector.get_columns('employes')]:
        op.add_column('employes', sa.Column('conges_credit_annuel', sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'conges_credit_annuel' in [c['name'] for c in inspector.get_columns('employes')]:
        op.drop_column('employes', 'conges_credit_annuel')
    if inspector.has_table('conges'):
        op.drop_index('idx_conge_employe_dates', table_name='conges')
        op.drop_index(op.f('ix_conges_tenant_id'), table_name='conges')
        op.drop_index(op.f('ix_conges_employe_id'), table_name='conges')
        op.drop_index(op.f('ix_conges_annee'), table_name='conges')
        op.drop_table('conges')