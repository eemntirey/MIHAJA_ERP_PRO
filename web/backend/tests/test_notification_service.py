"""Tests du service de notifications (notification_service.py).

Couvre :
- create_notification (succes, pas de commit, erreur DB)
- sync_alert_notifications (stock faible, factures impayees, deduplication, desactivation stale, super admin noop)
- notify_new_sale
- _existing_active_by_link
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app import db
from app.models.notification import Notification
from app.models.tenant import Tenant, StatutTenant
from app.models.produit import Produit
from app.models.facture import Facture
from app.models.client import Client
from app.models.vente import Vente


@pytest.fixture
def tenant_data(app):
    """Cree un tenant pour les tests de notification."""
    with app.app_context():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            nom=f'Notif Tenant {suffix}',
            slug=f'notif-{suffix}',
            statut=StatutTenant.EN_ESSAI,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.commit()
        data = {'id': tenant.id, 'slug': tenant.slug}
        db.session.remove()
        yield data


class TestCreateNotification:

    def test_create_notification_success(self, app, tenant_data):
        from app.services.notification_service import create_notification
        with app.app_context():
            notif = create_notification(
                tenant_id=tenant_data['id'],
                title='Test Title',
                message='Test message',
                notif_type='info',
                link='/test',
            )
            assert notif is not None
            assert notif.title == 'Test Title'
            assert notif.message == 'Test message'
            assert notif.type == 'info'
            assert notif.link == '/test'
            assert notif.tenant_id == tenant_data['id']
            assert notif.is_active is True

    def test_create_notification_no_commit(self, app, tenant_data):
        from app.services.notification_service import create_notification
        with app.app_context():
            notif = create_notification(
                tenant_id=tenant_data['id'],
                title='No Commit',
                commit=False,
            )
            assert notif is not None
            # Pas encore en base (pas de commit)
            from flask import current_app
            result = db.session.execute(
                db.text('SELECT id FROM notifications WHERE title = :t'),
                {'t': 'No Commit'},
            )
            # Le row n'existe pas encore car pas de commit
            assert result.fetchone() is None

    def test_create_notification_db_error(self, app, tenant_data):
        from app.services.notification_service import create_notification
        with app.app_context():
            with patch('app.services.notification_service.db.session.add', side_effect=Exception('DB error')):
                notif = create_notification(
                    tenant_id=tenant_data['id'],
                    title='Will Fail',
                )
            assert notif is None


class TestSyncAlertNotifications:

    def test_sync_alert_creates_stock_alert(self, app, tenant_data):
        from app.services.notification_service import sync_alert_notifications
        with app.app_context():
            produit = Produit(
                nom='Riz Test',
                reference=f'RIZ-{uuid.uuid4().hex[:6]}',
                unite='sac',
                prix_achat_ht=30000.0,
                prix_vente_ht=40000.0,
                quantite_stock=3,
                seuil_alerte=10,
                tenant_id=tenant_data['id'],
            )
            db.session.add(produit)
            db.session.commit()

            created = sync_alert_notifications(tenant_data['id'])
            assert created >= 1

            notifs = Notification.query.filter_by(
                tenant_id=tenant_data['id'],
                type='stock_alert',
                is_active=True,
            ).all()
            assert len(notifs) >= 1
            assert any(produit.nom in n.title for n in notifs)

    def test_sync_alert_creates_unpaid_invoice(self, app, tenant_data):
        from app.services.notification_service import sync_alert_notifications
        with app.app_context():
            client = Client(
                code=f'CLI-{uuid.uuid4().hex[:8]}',
                nom='Facture Client',
                tenant_id=tenant_data['id'],
            )
            db.session.add(client)
            db.session.flush()

            vente = Vente(
                reference=f'VEN-{uuid.uuid4().hex[:8]}',
                client_id=client.id,
                total_ht=100000.0,
                total_ttc=120000.0,
                tenant_id=tenant_data['id'],
            )
            db.session.add(vente)
            db.session.flush()

            facture = Facture(
                reference=f'FAC-{uuid.uuid4().hex[:8]}',
                total_ht=100000.0,
                total_ttc=120000.0,
                statut='non_payee',
                tenant_id=tenant_data['id'],
                client_id=client.id,
                vente_id=vente.id,
            )
            db.session.add(facture)
            db.session.commit()

            created = sync_alert_notifications(tenant_data['id'])
            assert created >= 1

            notifs = Notification.query.filter_by(
                tenant_id=tenant_data['id'],
                type='facture_impayee',
                is_active=True,
            ).all()
            assert len(notifs) >= 1

    def test_sync_alert_deduplicates(self, app, tenant_data):
        from app.services.notification_service import sync_alert_notifications
        with app.app_context():
            produit = Produit(
                nom='Dedup Produit',
                reference=f'DED-{uuid.uuid4().hex[:6]}',
                unite='piece',
                prix_achat_ht=10000.0,
                prix_vente_ht=15000.0,
                quantite_stock=2,
                seuil_alerte=5,
                tenant_id=tenant_data['id'],
            )
            db.session.add(produit)
            db.session.commit()

            sync_alert_notifications(tenant_data['id'])
            count_after_first = Notification.query.filter_by(
                tenant_id=tenant_data['id'],
                type='stock_alert',
                is_active=True,
            ).count()

            sync_alert_notifications(tenant_data['id'])
            count_after_second = Notification.query.filter_by(
                tenant_id=tenant_data['id'],
                type='stock_alert',
                is_active=True,
            ).count()

            assert count_after_first == count_after_second

    def test_sync_alert_deactivates_stale(self, app, tenant_data):
        from app.services.notification_service import sync_alert_notifications, create_notification
        with app.app_context():
            produit = Produit(
                nom='Stale Produit',
                reference=f'STL-{uuid.uuid4().hex[:6]}',
                unite='piece',
                prix_achat_ht=10000.0,
                prix_vente_ht=15000.0,
                quantite_stock=2,
                seuil_alerte=5,
                tenant_id=tenant_data['id'],
            )
            db.session.add(produit)
            db.session.commit()

            link = f'/inventory?produit={produit.id}'
            create_notification(
                tenant_id=tenant_data['id'],
                title='Ancienne alerte',
                notif_type='stock_alert',
                link=link,
            )

            # Reapprovisionner le stock
            produit.quantite_stock = 20
            db.session.commit()

            sync_alert_notifications(tenant_data['id'])

            notif = Notification.query.filter_by(
                tenant_id=tenant_data['id'],
                link=link,
                type='stock_alert',
            ).first()
            assert notif.is_active is False

    def test_sync_alert_super_admin_noop(self, app):
        from app.services.notification_service import sync_alert_notifications
        with app.app_context():
            created = sync_alert_notifications(tenant_id=None)
            assert created == 0

    def test_existing_active_by_link_empty(self, app):
        from app.services.notification_service import _existing_active_by_link
        with app.app_context():
            result = _existing_active_by_link(1, 'stock_alert', [])
            assert result == {}


class TestNotifyNewSale:

    def test_notify_new_sale(self, app, tenant_data):
        from app.services.notification_service import notify_new_sale
        with app.app_context():
            vente = MagicMock()
            vente.total_ttc = 150000.0
            vente.reference = 'VTE-TEST-001'
            vente.tenant_id = tenant_data['id']

            notif = notify_new_sale(vente)
            assert notif is not None
            assert notif.type == 'sale'
            assert '150' in notif.message
            assert notif.link == '/sales'


# MagicMock pour les tests de notify_new_sale
from unittest.mock import MagicMock
