# web/backend/tests/test_outbox_hook.py
# Tests du hook SQLAlchemy `after_flush` qui produit des entrées SyncOutbox.
# Messages et commentaires en français conformément aux conventions.

import uuid
from decimal import Decimal

import pytest
from app import db
from app.models.produit import Produit
from app.models.client import Client
from app.models.sync_replica import SyncOutbox
from app.services.replication.outbox import register_outbox_listeners


def _create_tenant_for_tests(db):
    from app.models.tenant import Tenant, StatutTenant
    import uuid as _uuid
    tenant = Tenant(
        nom='Tenant Outbox',
        slug=f'outbox-{_uuid.uuid4().hex[:8]}',
        domaine=f'outbox-{_uuid.uuid4().hex[:8]}.local',
        statut=StatutTenant.ACTIF,
        plan='gratuit',
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


def test_insert_creates_outbox_entry(app):
    """Un INSERT sur un modèle mappé doit créer une entrée outbox."""
    register_outbox_listeners(db, {'Produit': 'produit'})
    tenant = _create_tenant_for_tests(db)
    produit = Produit(
        nom='Produit Hors-Ligne',
        reference='OFF-001',
        prix_vente_ht=Decimal('15.00'),
        tenant_id=tenant.id,
    )
    db.session.add(produit)
    db.session.commit()

    entries = SyncOutbox.query.filter_by(entity='produit', op='INSERT').all()
    assert len(entries) == 1
    assert entries[0].local_uuid is not None
    assert entries[0].payload is not None
    assert entries[0].payload.get('nom') == 'Produit Hors-Ligne'
    assert entries[0].entity_pk == produit.id
    assert entries[0].idempotency_key.startswith('default-device:')


def test_update_creates_outbox_entry(app):
    """Un UPDATE sur un modèle mappé doit créer une entrée outbox."""
    register_outbox_listeners(db, {'Produit': 'produit'})
    tenant = _create_tenant_for_tests(db)
    produit = Produit(
        nom='Avant Mise à Jour',
        reference='UPDATE-001',
        prix_vente_ht=Decimal('10.00'),
        tenant_id=tenant.id,
    )
    db.session.add(produit)
    db.session.commit()

    produit.nom = 'Après Mise à Jour'
    produit.prix_vente_ht = Decimal('20.00')
    db.session.commit()

    entries = SyncOutbox.query.filter_by(entity='produit', op='UPDATE').all()
    assert len(entries) == 1
    assert entries[0].payload.get('nom') == 'Après Mise à Jour'
    assert entries[0].entity_pk == produit.id


def test_delete_creates_outbox_entry(app):
    """Un DELETE sur un modèle mappé doit créer une entrée outbox."""
    register_outbox_listeners(db, {'Produit': 'produit'})
    tenant = _create_tenant_for_tests(db)
    produit = Produit(
        nom='À Supprimer',
        reference='DELETE-001',
        prix_vente_ht=Decimal('5.00'),
        tenant_id=tenant.id,
    )
    db.session.add(produit)
    db.session.commit()
    pk = produit.id

    db.session.delete(produit)
    db.session.commit()

    entries = SyncOutbox.query.filter_by(entity='produit', op='DELETE').all()
    assert len(entries) == 1
    assert entries[0].entity_pk == pk
