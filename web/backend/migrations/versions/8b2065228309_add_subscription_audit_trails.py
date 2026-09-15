"""add subscription_audit_trails

Revision ID: 8b2065228309
Revises: n1o2p3q4r5s6
Create Date: 2026-09-14 19:04:37.111481
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b2065228309'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('subscription_audit_trails',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('abonnement_id', sa.Integer(), nullable=True),
    sa.Column('date_changement', sa.DateTime(), nullable=False),
    sa.Column('ancien_plan', sa.String(length=50), nullable=True),
    sa.Column('nouveau_plan', sa.String(length=50), nullable=False),
    sa.Column('declencheur', sa.String(length=20), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('utilisateur_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name='fk_subscription_audit_trails_tenant_id'),
    sa.ForeignKeyConstraint(['abonnement_id'], ['abonnements.id'], name='fk_subscription_audit_trails_abonnement_id'),
    sa.ForeignKeyConstraint(['utilisateur_id'], ['utilisateurs.id'], name='fk_subscription_audit_trails_utilisateur_id'),
    sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], name='fk_subscription_audit_trails_created_by'),
    sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], name='fk_subscription_audit_trails_updated_by'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscription_audit_trails_tenant_id', 'subscription_audit_trails', ['tenant_id'], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    with op.batch_alter_table('subscription_audit_trails', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_subscription_audit_trails_tenant_id'))
    op.drop_table('subscription_audit_trails')
