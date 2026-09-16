"""add_tenant_papi_settings_and_vitrine

Adds per-tenant Papi merchant credentials (encrypted) and a vitrine toggle
that controls whether the tenant's products are exposed on the public
storefront (and whether online payments are accepted for orders).

Revision ID: m1n2o3p4q5r6
Revises: k1l2m3n4o5p6
Create Date: 2026-09-07 16:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'm1n2o3p4q5r6'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    # Tenants: per-merchant Papi credentials + vitrine toggle
    if not _column_exists('tenants', 'papi_api_key_encrypted'):
        op.add_column(
            'tenants',
            sa.Column('papi_api_key_encrypted', sa.Text(), nullable=True),
        )
    if not _column_exists('tenants', 'papi_webhook_secret_encrypted'):
        op.add_column(
            'tenants',
            sa.Column('papi_webhook_secret_encrypted', sa.Text(), nullable=True),
        )
    if not _column_exists('tenants', 'papi_environment'):
        op.add_column(
            'tenants',
            sa.Column('papi_environment', sa.String(20), nullable=True),
        )
    if not _column_exists('tenants', 'papi_configured_at'):
        op.add_column(
            'tenants',
            sa.Column('papi_configured_at', sa.DateTime(), nullable=True),
        )
    if not _column_exists('tenants', 'vitrine_enabled'):
        op.add_column(
            'tenants',
            sa.Column(
                'vitrine_enabled',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if not _column_exists('tenants', 'vitrine_enabled_at'):
        op.add_column(
            'tenants',
            sa.Column('vitrine_enabled_at', sa.DateTime(), nullable=True),
        )

    # Paiements: link to public order (vitrine)
    if not _column_exists('paiements', 'commande_client_id'):
        op.add_column(
            'paiements',
            sa.Column(
                'commande_client_id',
                sa.Integer(),
                sa.ForeignKey('commandes_client.id'),
                nullable=True,
            ),
        )
        op.create_index(
            'ix_paiements_commande_client_id',
            'paiements',
            ['commande_client_id'],
            unique=False,
        )


def downgrade() -> None:
    if _column_exists('paiements', 'commande_client_id'):
        op.drop_index('ix_paiements_commande_client_id', table_name='paiements')
        op.drop_column('paiements', 'commande_client_id')

    for col in (
        'vitrine_enabled_at',
        'vitrine_enabled',
        'papi_configured_at',
        'papi_environment',
        'papi_webhook_secret_encrypted',
        'papi_api_key_encrypted',
    ):
        if _column_exists('tenants', col):
            op.drop_column('tenants', col)