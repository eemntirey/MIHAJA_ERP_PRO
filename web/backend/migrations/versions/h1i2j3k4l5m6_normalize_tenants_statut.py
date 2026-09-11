"""normalize tenants statut to lowercase StatutTenant values

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-09-01 14:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VALID_LOWER = {'actif', 'inactif', 'bloque', 'en_essai'}
_NAME_TO_VALUE = {
    'ACTIF': 'actif',
    'INACTIF': 'inactif',
    'BLOQUE': 'bloque',
    'EN_ESSAI': 'en_essai',
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'tenants' not in inspector.get_table_names():
        return

    rows = bind.execute(sa.text('SELECT id, statut FROM tenants')).fetchall()
    if not rows:
        return

    for tenant_id, current in rows:
        if current is None:
            continue
        normalized = str(current).strip().lower()
        if normalized in _VALID_LOWER:
            new_value = normalized
        else:
            new_value = _NAME_TO_VALUE.get(str(current).strip().upper())
            if new_value is None:
                new_value = 'en_essai'
        if new_value != current:
            bind.execute(
                sa.text('UPDATE tenants SET statut = :v WHERE id = :i'),
                {'v': new_value, 'i': tenant_id},
            )


def downgrade() -> None:
    pass
