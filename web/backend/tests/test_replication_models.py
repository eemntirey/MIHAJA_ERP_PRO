# web/backend/tests/test_replication_models.py
# Tests des modèles de réplication : SyncOutbox, SyncCursor, SyncState.
# Messages et commentaires en français conformément aux conventions du projet.

import uuid

import pytest

from app import db
from app.models.sync_replica import SyncOutbox, SyncCursor, SyncState


@pytest.fixture
def tenant_id(app):
    from app.models.tenant import StatutTenant, Tenant
    # Domaine unique pour éviter la collision avec des données résiduelles.
    domaine_unique = f'replication-{uuid.uuid4().hex[:8]}.local'
    slug_unique = f'tenant-repl-{uuid.uuid4().hex[:8]}',
    domaine_unique = f'replication-{uuid.uuid4().hex[:8]}.local'
    tenant = Tenant(
        nom='Tenant Réplication', slug=slug_unique,
        domaine=domaine_unique, statut=StatutTenant.ACTIF, plan='pro',
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant.id


def test_record_creates_pending(app, tenant_id):
    """L'enregistrement d'une mutation crée une entrée en statut pending."""
    entry = SyncOutbox.record(
        tenant_id=tenant_id,
        device_id='device-1',
        entity='vente',
        op='INSERT',
        payload={'client': 'Rakoto', 'total': 15000},
        local_uuid=str(uuid.uuid4()),
    )
    assert entry.status == 'pending'
    assert entry.idempotency_key == f'device-1:{entry.local_uuid}'
    assert entry.attempts == 0


def test_record_is_idempotent_per_local_uuid(app, tenant_id):
    """L'idempotence stricte : même local_uuid retourne l'entrée existante."""
    lu = str(uuid.uuid4())
    first = SyncOutbox.record(
        tenant_id=tenant_id,
        device_id='d1',
        entity='vente',
        op='INSERT',
        payload={'a': 1},
        local_uuid=lu,
    )
    again = SyncOutbox.record(
        tenant_id=tenant_id,
        device_id='d1',
        entity='vente',
        op='INSERT',
        payload={'a': 1},
        local_uuid=lu,
    )
    assert again.id == first.id
    assert SyncOutbox.query.filter_by(local_uuid=lu).count() == 1


def test_cursor_upsert(app, tenant_id):
    """Le curseur avance vers la révision la plus récente et ne recule jamais."""
    SyncCursor.upsert(
        tenant_id=tenant_id, device_id='d1', entity='produit',
        last_pulled_revision=42,
    )
    SyncCursor.upsert(
        tenant_id=tenant_id, device_id='d1', entity='produit',
        last_pulled_revision=50,
    )
    cur = SyncCursor.query.filter_by(
        tenant_id=tenant_id, device_id='d1', entity='produit',
    ).one()
    assert cur.last_pulled_revision == 50
    # Un pull plus ancien (cache) ne doit pas reculer le curseur.
    SyncCursor.upsert(
        tenant_id=tenant_id, device_id='d1', entity='produit',
        last_pulled_revision=10,
    )
    db.session.refresh(cur)
    assert cur.last_pulled_revision == 50
