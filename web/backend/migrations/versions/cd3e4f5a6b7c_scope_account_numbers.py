"""Corrige l'unicité des numéros de comptes comptables par tenant.

Revision ID: cd3e4f5a6b7c
Revises: bb2c3d4e5f6a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cd3e4f5a6b7c'
down_revision: Union[str, None] = 'bb2c3d4e5f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = 'comptes_comptables'
_GLOBAL_COLUMNS = ('numero',)


def _is_target_unique(constraint_or_index):
    columns = tuple(
        getattr(constraint_or_index, 'column_names', None)
        or [getattr(c, 'name', None) for c in getattr(constraint_or_index, 'columns', [])]
    )
    return columns == _GLOBAL_COLUMNS


def _sqlite_rebuild(upgrade=True):
    bind = op.get_bind()
    metadata = sa.MetaData()
    table = sa.Table(_TABLE, metadata, autoload_with=bind)

    # Retirer toute unicité globale sur numero.
    for constraint in list(table.constraints):
        if isinstance(constraint, sa.UniqueConstraint) and _is_target_unique(constraint):
            table.constraints.remove(constraint)
    for index in list(table.indexes):
        if index.unique and _is_target_unique(index):
            table.indexes.remove(index)

    if upgrade:
        table.append_constraint(
            sa.UniqueConstraint(
                table.c.tenant_id,
                table.c.numero,
                name='uq_compte_tenant_numero',
            )
        )
    else:
        table.append_constraint(
            sa.UniqueConstraint(
                table.c.numero,
                name='uq_comptes_comptables_numero_legacy',
            )
        )

    with op.batch_alter_table(
        _TABLE,
        recreate='always',
        copy_from=table,
    ):
        pass


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return

    if bind.dialect.name == 'sqlite':
        # SQLite ne permet pas DROP/CREATE UNIQUE CONSTRAINT de façon portable.
        _sqlite_rebuild(upgrade=True)
        return

    # PostgreSQL : supprimer la contrainte/index global puis créer l'unicité
    # composite tenant + numero.
    for constraint in inspector.get_unique_constraints(_TABLE):
        if constraint.get('name') and tuple(constraint.get('column_names') or []) == _GLOBAL_COLUMNS:
            op.drop_constraint(constraint['name'], _TABLE, type_='unique')

    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(_TABLE):
        if index.get('name') and index.get('unique') and tuple(index.get('column_names') or []) == _GLOBAL_COLUMNS:
            try:
                op.drop_index(index['name'], table_name=_TABLE)
            except Exception:
                pass

    inspector = sa.inspect(bind)
    names = {c.get('name') for c in inspector.get_unique_constraints(_TABLE)}
    if 'uq_compte_tenant_numero' not in names:
        op.create_unique_constraint(
            'uq_compte_tenant_numero',
            _TABLE,
            ['tenant_id', 'numero'],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return

    if bind.dialect.name == 'sqlite':
        _sqlite_rebuild(upgrade=False)
        return

    if 'uq_compte_tenant_numero' in {
        c.get('name') for c in inspector.get_unique_constraints(_TABLE)
    }:
        op.drop_constraint('uq_compte_tenant_numero', _TABLE, type_='unique')
    op.create_unique_constraint(
        'uq_comptes_comptables_numero_legacy',
        _TABLE,
        ['numero'],
    )
