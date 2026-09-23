"""Replication hors-ligne : complement (journal central, mappings, cache).

Ajoute ce que la premiere migration de replication (b1c2d3e4f5a6) n'avait pas
prevu :
 - sync_central_log     : journal des revisions cote CENTRAL (table du pull) ;
 - sync_local_mappings  : correspondance PK locale <-> PK centrale (risque 6) ;
 - sync_central_log.source_device_id : origine d'une mutation (un poste ne
   rejoue pas ses propres mutations) ;
 - sync_state.service_token : jeton JWT du central utilise par push/pull ;
 - utilisateurs.local_password_hash : cache scrypt du login hors-ligne.

Correction : la table locale `sync_state` ne doit PAS porter `tenant_id`
(modele SyncState = ligne unique par poste, hors filtrage tenant). La colonne
est supprimee si elle existe (elle est NOT NULL, ce qui faisait echouer tout
INSERT sur une base creee par migration).

Chaque operation est conditionnelle (`inspect`) : les bases de dev
provisionnees par `db.create_all()` contiennent deja tout ou partie de ces
objets.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_names():
    return set(_inspector().get_table_names())


def _column_names(table):
    inspector = _inspector()
    if table not in inspector.get_table_names():
        return set()
    return {col['name'] for col in inspector.get_columns(table)}


def upgrade():
    tables = _table_names()

    if 'sync_central_log' not in tables:
        op.create_table(
            'sync_central_log',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('entity', sa.String(length=64), nullable=False),
            sa.Column('entity_pk', sa.Integer(), nullable=False),
            sa.Column('op', sa.String(length=10), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('revision', sa.BigInteger(), nullable=False),
            sa.Column('source_device_id', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_sync_central_log_tenant_id', 'sync_central_log',
                        ['tenant_id'])
        op.create_index('ix_sync_central_log_entity', 'sync_central_log',
                        ['entity'])
        op.create_index('ix_sync_central_log_revision', 'sync_central_log',
                        ['revision'])
        op.create_index('ix_sync_central_log_source_device_id',
                        'sync_central_log', ['source_device_id'])

    if 'sync_local_mappings' not in tables:
        op.create_table(
            'sync_local_mappings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('entity', sa.String(length=64), nullable=False),
            sa.Column('local_pk', sa.Integer(), nullable=False),
            sa.Column('remote_pk', sa.Integer(), nullable=False),
            sa.Column('local_uuid', sa.String(length=36), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('tenant_id', 'entity', 'local_pk',
                                name='uq_sync_mapping_tenant_entity_local'),
            sa.UniqueConstraint('tenant_id', 'entity', 'remote_pk',
                                name='uq_sync_mapping_tenant_entity_remote'),
        )
        op.create_index('ix_sync_local_mappings_tenant_id',
                        'sync_local_mappings', ['tenant_id'])
        op.create_index('ix_sync_local_mappings_entity',
                        'sync_local_mappings', ['entity'])
        op.create_index('ix_sync_local_mappings_local_pk',
                        'sync_local_mappings', ['local_pk'])
        op.create_index('ix_sync_local_mappings_remote_pk',
                        'sync_local_mappings', ['remote_pk'])

    central_columns = _column_names('sync_central_log')
    if central_columns and 'source_device_id' not in central_columns:
        op.add_column('sync_central_log', sa.Column(
            'source_device_id', sa.String(length=64), nullable=True,
        ))

    state_columns = _column_names('sync_state')
    if state_columns:
        if 'service_token' not in state_columns:
            op.add_column('sync_state', sa.Column(
                'service_token', sa.Text(), nullable=True,
            ))
        if 'tenant_id' in state_columns:
            # Ligne unique par poste : plus de tenant_id (ni de contrainte
            # d'unicite par tenant heritee de la 1re migration).
            inspector = _inspector()
            for constraint in inspector.get_unique_constraints('sync_state'):
                if constraint.get('column_names') == ['tenant_id']:
                    op.drop_constraint(
                        constraint['name'], 'sync_state', type_='unique',
                    )
            for index in inspector.get_indexes('sync_state'):
                if index.get('column_names') == ['tenant_id']:
                    op.drop_index(index['name'], table_name='sync_state')
            op.drop_column('sync_state', 'tenant_id')

    user_columns = _column_names('utilisateurs')
    if user_columns and 'local_password_hash' not in user_columns:
        op.add_column('utilisateurs', sa.Column(
            'local_password_hash', sa.String(length=255), nullable=True,
        ))


def downgrade():
    user_columns = _column_names('utilisateurs')
    if 'local_password_hash' in user_columns:
        op.drop_column('utilisateurs', 'local_password_hash')

    state_columns = _column_names('sync_state')
    if state_columns:
        if 'service_token' in state_columns:
            op.drop_column('sync_state', 'service_token')
        if 'tenant_id' not in state_columns:
            op.add_column('sync_state', sa.Column(
                'tenant_id', sa.Integer(), nullable=True,
            ))

    if 'sync_local_mappings' in _table_names():
        op.drop_table('sync_local_mappings')

    if 'sync_central_log' in _table_names():
        op.drop_table('sync_central_log')
