"""create_document_tables

Revision ID: 20260826181739
Revises: b2c3d4e5f6a7
Create Date: 2026-08-26 18:17:39.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260826181739'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('modeles_documents'):
        op.create_table(
            'modeles_documents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('nom', sa.String(length=100), nullable=False),
            sa.Column('type_document', sa.String(length=50), nullable=False),
            sa.Column('contenu_modele', sa.Text(), nullable=False),
            sa.Column('est_actif', sa.Boolean(), nullable=True),
            sa.Column('est_defaut', sa.Boolean(), nullable=True),
            sa.Column('logo_url', sa.String(length=500), nullable=True),
            sa.Column('mention_legales', sa.Text(), nullable=True),
            sa.Column('conditions_generales', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_modeles_documents_tenant_id'), 'modeles_documents', ['tenant_id'], unique=False)

    if not inspector.has_table('documents_generes'):
        op.create_table(
            'documents_generes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('modele_id', sa.Integer(), nullable=False),
            sa.Column('type_document', sa.String(length=50), nullable=False),
            sa.Column('reference', sa.String(length=100), nullable=False),
            sa.Column('entite_type', sa.String(length=50), nullable=True),
            sa.Column('entite_id', sa.Integer(), nullable=True),
            sa.Column('contenu_html', sa.Text(), nullable=True),
            sa.Column('contenu_pdf_path', sa.String(length=500), nullable=True),
            sa.Column('date_generation', sa.DateTime(), nullable=True),
            sa.Column('genere_par_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['genere_par_id'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['modele_id'], ['modeles_documents.id'], ),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_documents_generes_entite_id'), 'documents_generes', ['entite_id'], unique=False)
        op.create_index(op.f('ix_documents_generes_modele_id'), 'documents_generes', ['modele_id'], unique=False)
        op.create_index(op.f('ix_documents_generes_reference'), 'documents_generes', ['reference'], unique=False)
        op.create_index(op.f('ix_documents_generes_tenant_id'), 'documents_generes', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_generes_tenant_id'), table_name='documents_generes')
    op.drop_index(op.f('ix_documents_generes_reference'), table_name='documents_generes')
    op.drop_index(op.f('ix_documents_generes_modele_id'), table_name='documents_generes')
    op.drop_index(op.f('ix_documents_generes_entite_id'), table_name='documents_generes')
    op.drop_table('documents_generes')
    op.drop_index(op.f('ix_modeles_documents_tenant_id'), table_name='modeles_documents')
    op.drop_table('modeles_documents')
