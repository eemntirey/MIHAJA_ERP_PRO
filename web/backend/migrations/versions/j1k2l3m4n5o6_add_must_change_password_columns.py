"""add_must_change_password_columns

Revision ID: j1k2l3m4n5o6
Revises: e1f2g3h4i5j6
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in [c['name'] for c in inspector.get_columns(table)]


def upgrade() -> None:
    # must_change_password
    if not _column_exists('utilisateurs', 'must_change_password'):
        with op.batch_alter_table('utilisateurs') as batch_op:
            batch_op.add_column(
                sa.Column(
                    'must_change_password',
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        # Ajout de l'index explicite pour les requetes frequentes
        op.create_index(
            'ix_utilisateurs_must_change_password',
            'utilisateurs',
            ['must_change_password'],
            unique=False,
        )

    # password_changed_at
    if not _column_exists('utilisateurs', 'password_changed_at'):
        with op.batch_alter_table('utilisateurs') as batch_op:
            batch_op.add_column(
                sa.Column('password_changed_at', sa.DateTime(), nullable=True)
            )

    # token_version
    if not _column_exists('utilisateurs', 'token_version'):
        with op.batch_alter_table('utilisateurs') as batch_op:
            batch_op.add_column(
                sa.Column(
                    'token_version',
                    sa.Integer(),
                    nullable=False,
                    server_default='0',
                )
            )


def downgrade() -> None:
    if _column_exists('utilisateurs', 'must_change_password'):
        op.drop_index('ix_utilisateurs_must_change_password', 'utilisateurs')
        op.drop_column('utilisateurs', 'must_change_password')
    if _column_exists('utilisateurs', 'password_changed_at'):
        op.drop_column('utilisateurs', 'password_changed_at')
    if _column_exists('utilisateurs', 'token_version'):
        op.drop_column('utilisateurs', 'token_version')
