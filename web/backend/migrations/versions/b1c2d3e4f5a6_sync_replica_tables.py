"""Tables de replication hors-ligne (backend embarque desktop).

Cree les 5 tables du moteur de replication :
 - sync_outbox         : mutations locales en attente (cote local)
 - sync_cursors        : curseur de revision par entite (cote local)
 - sync_conflicts      : conflits LWW a revoir (cote local)
 - sync_applied_keys   : cles d'idempotence appliquees (cote central)
 - sync_state          : etat de replication, ligne unique (cote local)

Tous les modeles conservent `tenant_id` conformement aux conventions
multi-tenant du projet (cf. app/security/tenant.py).

NB : les bases de dev deja provisionnees via `db.create_all()` possedent ces
tables ; un `flask db stamp head` y est necessaire avant `db upgrade`
(meme procedure que web/backend/setup_postgresql.ps1).

Revision ID: b1c2d3e4f5a6
Revises: q1r2s3t4u5v6
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = 'q1r2s3t4u5v6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sync_outbox',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('entity', sa.String(length=64), nullable=False),
        sa.Column('entity_pk', sa.Integer(), nullable=True),
        sa.Column('local_uuid', sa.String(length=36), nullable=False),
        sa.Column('op', sa.String(length=10), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('local_uuid', name='uq_sync_outbox_local_uuid'),
        sa.UniqueConstraint('idempotency_key', name='uq_sync_outbox_idem_key'),
    )
    op.create_index('ix_sync_outbox_tenant_id', 'sync_outbox', ['tenant_id'])
    op.create_index('ix_sync_outbox_device_id', 'sync_outbox', ['device_id'])
    op.create_index('ix_sync_outbox_entity', 'sync_outbox', ['entity'])
    op.create_index('ix_sync_outbox_status', 'sync_outbox', ['status'])

    op.create_table(
        'sync_cursors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('entity', sa.String(length=64), nullable=False),
        sa.Column('last_pulled_revision', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('tenant_id', 'device_id', 'entity',
                            name='uq_sync_cursor_tenant_device_entity'),
    )
    op.create_index('ix_sync_cursors_tenant_id', 'sync_cursors', ['tenant_id'])
    op.create_index('ix_sync_cursors_device_id', 'sync_cursors', ['device_id'])
    op.create_index('ix_sync_cursors_entity', 'sync_cursors', ['entity'])

    op.create_table(
        'sync_conflicts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('entity', sa.String(length=64), nullable=False),
        sa.Column('entity_pk', sa.Integer(), nullable=True),
        sa.Column('local_payload', sa.JSON(), nullable=True),
        sa.Column('remote_payload', sa.JSON(), nullable=True),
        sa.Column('resolved_as', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_sync_conflicts_tenant_id', 'sync_conflicts', ['tenant_id'])

    op.create_table(
        'sync_applied_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('entity', sa.String(length=64), nullable=False),
        sa.Column('server_pk', sa.Integer(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('idempotency_key',
                            name='uq_sync_applied_keys_idem_key'),
    )
    op.create_index('ix_sync_applied_keys_tenant_id', 'sync_applied_keys',
                    ['tenant_id'])

    op.create_table(
        'sync_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('online', sa.Boolean(), nullable=False),
        sa.Column('pending_count', sa.Integer(), nullable=False),
        sa.Column('last_push_at', sa.DateTime(), nullable=True),
        sa.Column('last_pull_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.UniqueConstraint('tenant_id', name='uq_sync_state_tenant'),
    )
    op.create_index('ix_sync_state_tenant_id', 'sync_state', ['tenant_id'])


def downgrade():
    op.drop_index('ix_sync_state_tenant_id', table_name='sync_state')
    op.drop_table('sync_state')
    op.drop_index('ix_sync_applied_keys_tenant_id',
                  table_name='sync_applied_keys')
    op.drop_table('sync_applied_keys')
    op.drop_index('ix_sync_conflicts_tenant_id', table_name='sync_conflicts')
    op.drop_table('sync_conflicts')
    op.drop_index('ix_sync_cursors_entity', table_name='sync_cursors')
    op.drop_index('ix_sync_cursors_device_id', table_name='sync_cursors')
    op.drop_index('ix_sync_cursors_tenant_id', table_name='sync_cursors')
    op.drop_table('sync_cursors')
    op.drop_index('ix_sync_outbox_status', table_name='sync_outbox')
    op.drop_index('ix_sync_outbox_entity', table_name='sync_outbox')
    op.drop_index('ix_sync_outbox_device_id', table_name='sync_outbox')
    op.drop_index('ix_sync_outbox_tenant_id', table_name='sync_outbox')
    op.drop_table('sync_outbox')

