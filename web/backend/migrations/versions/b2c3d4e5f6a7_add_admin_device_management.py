"""add_admin_device_management

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table))


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table)


def upgrade() -> None:
    if not _column_exists('utilisateurs', 'admin_statut'):
        op.add_column('utilisateurs', sa.Column('admin_statut', sa.Enum('active', 'suspended', 'revoked', name='statut_admin'), nullable=True))
    if not _column_exists('utilisateurs', 'admin_key_hash'):
        op.add_column('utilisateurs', sa.Column('admin_key_hash', sa.String(length=255), nullable=True))
    if not _column_exists('utilisateurs', 'admin_key_status'):
        op.add_column('utilisateurs', sa.Column('admin_key_status', sa.Enum('active', 'revoked', 'expired', name='statut_adminkey'), nullable=True))
    if not _column_exists('utilisateurs', 'device_id'):
        op.add_column('utilisateurs', sa.Column('device_id', sa.String(length=255), nullable=True))
    if _column_exists('utilisateurs', 'device_id') and not _index_exists('utilisateurs', 'ix_utilisateurs_device_id'):
        op.create_index(op.f('ix_utilisateurs_device_id'), 'utilisateurs', ['device_id'], unique=False)

    if not _table_exists('admin_devices'):
        op.create_table(
            'admin_devices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('device_id', sa.String(length=255), nullable=False),
            sa.Column('device_name', sa.String(length=255), nullable=True),
            sa.Column('statut', sa.Enum('active', 'revoked', name='statut_device'), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['created_by'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['updated_by'], ['utilisateurs.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['utilisateurs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_admin_devices_device_id'), 'admin_devices', ['device_id'], unique=False)
        op.create_index(op.f('ix_admin_devices_user_id'), 'admin_devices', ['user_id'], unique=False)


def downgrade() -> None:
    if _column_exists('utilisateurs', 'device_id'):
        try:
            op.drop_index(op.f('ix_utilisateurs_device_id'), table_name='utilisateurs')
        except Exception:
            pass
        op.drop_column('utilisateurs', 'device_id')
    if _column_exists('utilisateurs', 'admin_key_status'):
        op.drop_column('utilisateurs', 'admin_key_status')
    if _column_exists('utilisateurs', 'admin_key_hash'):
        op.drop_column('utilisateurs', 'admin_key_hash')
    if _column_exists('utilisateurs', 'admin_statut'):
        op.drop_column('utilisateurs', 'admin_statut')

    if _table_exists('admin_devices'):
        try:
            op.drop_index(op.f('ix_admin_devices_user_id'), table_name='admin_devices')
        except Exception:
            pass
        try:
            op.drop_index(op.f('ix_admin_devices_device_id'), table_name='admin_devices')
        except Exception:
            pass
        op.drop_table('admin_devices')
