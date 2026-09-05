"""Tests Paiements & Revenus (Super Admin).

Couverture :
  - RBAC      : SUPER_ADMIN autorise / Tenant Admin refuse / anonyme refuse
  - Isolation : le Super Admin voit tous les tenants ; un Tenant Admin
    ne peut PAS consulter les paiements globaux
  - Statistiques : SUCCESS/CONFIRME comptes comme revenus confirmes,
    EN_ATTENTE et FAILED exclus
  - Filtres : status, provider, payment_method, tenant, plan, dates, search
  - Pagination : page / per_page / total / pages
  - Securite : aucune fuite de PAPI_API_KEY / PAPI_WEBHOOK_SECRET /
    notification_token dans les reponses
"""
import os
import uuid
from datetime import datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('PAPI_API_URL', 'https://test.papi.mg/dashboard/api/payment-links')
os.environ.setdefault('PAPI_API_KEY', 'test-api-key')
os.environ.setdefault('PAPI_ENVIRONMENT', 'sandbox')
os.environ.setdefault('PAPI_CALLBACK_URL', 'http://localhost:5000/api/v1/papi/webhook')

import pytest
from flask_jwt_extended import create_access_token

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.payment_event import PaymentEvent
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password

SECRET_MARKERS = ('test-api-key', 'PAPI_API_KEY', 'PAPI_WEBHOOK_SECRET',
                  'notification_token', 'notificationToken')


def _uid():
    return uuid.uuid4().hex[:8]


def _make_abonnement(tenant, plan, montant):
    return Abonnement(
        tenant_id=tenant.id,
        montant=montant,
        devise='MGA',
        date_debut=datetime.utcnow() - timedelta(days=1),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
        plan=plan,
    )


def _make_payment(tenant, abonnement, statut, montant, provider='papi',
                  payment_method='MVOLA'):
    suffix = _uid()
    paiement = Paiement(
        tenant_id=tenant.id,
        subscription_id=abonnement.id,
        montant=montant,
        devise='MGA',
        statut=statut,
        type=TypePaiement.ABONNEMENT,
        provider=provider,
        payment_method=payment_method,
        reference=f'REF-{suffix}',
        external_reference=f'SUB-{tenant.id}-{abonnement.id}-{suffix}',
        notes='Paiement abonnement (test)',
    )
    db.session.add(paiement)
    return paiement


@pytest.fixture(scope='module')
def pay_data(app):
    """Jeu de donnees : 2 tenants, paiements Papi + hors ligne."""
    with app.app_context():
        suffix = _uid()

        tenant_a = Tenant(
            nom=f'Entreprise Alpha {suffix}',
            slug=f'pay-a-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='pro',
        )
        tenant_b = Tenant(
            nom=f'Entreprise Beta {suffix}',
            slug=f'pay-b-{suffix}',
            statut=StatutTenant.ACTIF,
            plan='starter',
        )
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()

        admin_a = Utilisateur(
            username=f'admin-a-{suffix}',
            email=f'admin-a-{suffix}@example.com',
            password_hash=hash_password('Password123!'),
            role=Role.ADMIN,
            tenant_id=tenant_a.id,
            statut=StatutUtilisateur.ACTIF,
        )
        sa = Utilisateur(
            username=f'sa-pay-{suffix}',
            email=f'sa-pay-{suffix}@example.com',
            password_hash=hash_password('Password123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add_all([admin_a, sa])
        db.session.flush()

        abo_a = _make_abonnement(tenant_a, 'pro', 15000)
        abo_b = _make_abonnement(tenant_b, 'starter', 5000)
        db.session.add_all([abo_a, abo_b])
        db.session.flush()

        # Tenant A : 1 SUCCESS papi (15000), 1 EN_ATTENTE manuel (5000),
        # 1 FAILED papi (15000).
        p_success = _make_payment(
            tenant_a, abo_a, StatutPaiement.SUCCESS, 15000,
            provider='papi', payment_method='MVOLA',
        )
        p_pending = _make_payment(
            tenant_a, abo_a, StatutPaiement.EN_ATTENTE, 5000,
            provider='manuel', payment_method='VIREMENT',
        )
        p_failed = _make_payment(
            tenant_a, abo_a, StatutPaiement.FAILED, 15000,
            provider='papi', payment_method='MVOLA',
        )
        # Tenant B : 1 CONFIRME manuel (5000) = revenu confirme hors ligne.
        p_confirmed_offline = _make_payment(
            tenant_b, abo_b, StatutPaiement.CONFIRME, 5000,
            provider='manuel', payment_method='ESPECES',
        )
        db.session.flush()

        # Event webhook Papi reel (frais reellement retournes par Papi).
        event = PaymentEvent(
            payment_id=p_success.id,
            event_id=f'papi-{p_success.external_reference}-{_uid()}',
            event_type='SUCCESS',
            payload={
                'paymentStatus': 'SUCCESS',
                'fee': 300,
                'paymentReference': p_success.external_reference,
            },
            signature='tok-test',
            processed=True,
            processed_at=datetime.utcnow(),
        )
        db.session.add(event)
        db.session.commit()

        sa_token = create_access_token(
            identity=sa.id, additional_claims={'role': 'super_admin'})
        admin_a_token = create_access_token(
            identity=admin_a.id,
            additional_claims={
                'role': 'admin',
                'tenant_id': tenant_a.id,
                'tenant_slug': tenant_a.slug,
            })

        return {
            'sa_headers': {'Authorization': f'Bearer {sa_token}'},
            'admin_a_headers': {'Authorization': f'Bearer {admin_a_token}'},
            # Valeurs simples (les objets ORM seraient detaches hors contexte).
            'tenant_a_id': tenant_a.id,
            'tenant_a_nom': tenant_a.nom,
            'tenant_b_id': tenant_b.id,
            'tenant_b_nom': tenant_b.nom,
            'admin_a_id': admin_a.id,
            'p_success_id': p_success.id,
            'p_success_ref': p_success.external_reference,
            'n_payments_a': 3,
            'n_payments_b': 1,
        }


def _assert_no_secrets(payload_text):
    for marker in SECRET_MARKERS:
        assert marker not in payload_text, (
            f'Fuite potentielle de secret: "{marker}" present dans la reponse'
        )


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #
class TestRBAC:
    def test_super_admin_autorise(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments', headers=pay_data['sa_headers'])
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert 'items' in body and 'pagination' in body

    def test_tenant_admin_refuse(self, app, client, pay_data):
        for url in (
            '/api/v1/super-admin/payments',
            '/api/v1/super-admin/payments/stats',
            '/api/v1/super-admin/payments/filters',
            f"/api/v1/super-admin/payments/{pay_data['p_success_id']}",
        ):
            r = client.get(url, headers=pay_data['admin_a_headers'])
            assert r.status_code == 403, (url, r.status_code, r.get_json())

    def test_anonyme_refuse(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments')
        assert r.status_code == 401

    def test_faux_super_admin_refuse(self, app, client, pay_data):
        # Un tenant admin qui prétendrait le rôle super_admin dans ses claims
        # doit être refusé : la vérification passe par l'utilisateur en base.
        forged = create_access_token(
            identity=pay_data['admin_a_id'],
            additional_claims={'role': 'super_admin'})
        r = client.get(
            '/api/v1/super-admin/payments',
            headers={'Authorization': f'Bearer {forged}'},
        )
        assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Isolation
# --------------------------------------------------------------------------- #
class TestIsolation:
    def test_super_admin_voit_tous_les_tenants(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments', headers=pay_data['sa_headers'])
        assert r.status_code == 200
        names = {item['tenant_name'] for item in r.get_json()['items']}
        assert pay_data['tenant_a_nom'] in names
        assert pay_data['tenant_b_nom'] in names

    def test_tenant_admin_ne_voit_pas_les_paiements_globaux(self, app, client, pay_data):
        # Les routes globales sont interdites au tenant admin.
        r = client.get('/api/v1/super-admin/payments/stats',
                       headers=pay_data['admin_a_headers'])
        assert r.status_code == 403
        # Le tenant admin garde sa vue limitee a SON tenant via /papi/payments.
        r2 = client.get('/api/v1/papi/payments',
                        headers=pay_data['admin_a_headers'])
        assert r2.status_code == 200
        for payment in r2.get_json()['payments']:
            assert payment['tenant_id'] == pay_data['tenant_a_id']


# --------------------------------------------------------------------------- #
# Statistiques
# --------------------------------------------------------------------------- #
class TestStats:
    def test_revenus_confirmes_excluent_attente_et_echec(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments/stats?tenant_id={pay_data['tenant_a_id']}",
            headers=pay_data['sa_headers'],
        )
        assert r.status_code == 200, r.get_json()
        stats = r.get_json()
        # Tenant A : SUCCESS 15000 (confirme), EN_ATTENTE 5000, FAILED 15000.
        assert stats['total_success'] == 15000
        assert stats['success_count'] == 1
        assert stats['total_pending'] == 5000
        assert stats['pending_count'] == 1
        assert stats['total_failed'] == 15000
        assert stats['failed_count'] == 1
        assert stats['currency'] == 'MGA'

    def test_statut_confirme_compte_comme_confirme(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments/stats?tenant_id={pay_data['tenant_b_id']}",
            headers=pay_data['sa_headers'],
        )
        assert r.status_code == 200
        stats = r.get_json()
        assert stats['total_success'] == 5000
        assert stats['success_count'] == 1
        assert stats['total_pending'] == 0

    def test_repartition_par_methode_et_plan(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments/stats?tenant_id={pay_data['tenant_a_id']}",
            headers=pay_data['sa_headers'],
        )
        stats = r.get_json()
        by_method = {m['payment_method']: m for m in stats['by_method_confirmed']}
        assert by_method['MVOLA']['montant'] == 15000
        by_plan = {p['plan']: p for p in stats['by_plan_confirmed']}
        assert by_plan['pro']['montant'] == 15000
        # Online / offline separees.
        assert stats['online_confirmed'] == 15000
        assert stats['offline_confirmed'] == 0

    def test_settlement_toujours_non_disponible(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments/stats',
                       headers=pay_data['sa_headers'])
        stats = r.get_json()
        assert stats['settlement']['available'] is False
        assert 'non disponibles' in stats['settlement']['message'].lower()


# --------------------------------------------------------------------------- #
# Filtres
# --------------------------------------------------------------------------- #
class TestFilters:
    def _list(self, client, pay_data, **params):
        r = client.get(
            '/api/v1/super-admin/payments',
            headers=pay_data['sa_headers'],
            query_string=params,
        )
        assert r.status_code == 200, r.get_json()
        return r.get_json()

    def test_filtre_statut_valeur_db(self, app, client, pay_data):
        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          status='succes')
        assert body['pagination']['total'] == 1
        assert body['items'][0]['statut'] == 'succes'

    def test_filtre_statut_nom_enum(self, app, client, pay_data):
        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          status='SUCCESS')
        assert body['pagination']['total'] == 1
        assert body['items'][0]['statut'] == 'succes'

    def test_filtre_provider(self, app, client, pay_data):
        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          provider='manuel')
        assert body['pagination']['total'] == 1
        assert body['items'][0]['provider'] == 'manuel'

    def test_filtre_payment_method(self, app, client, pay_data):
        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          payment_method='MVOLA')
        assert body['pagination']['total'] == 2
        for item in body['items']:
            assert item['payment_method'] == 'MVOLA'

    def test_filtre_tenant(self, app, client, pay_data):
        body = self._list(client, pay_data, tenant_id=pay_data['tenant_b_id'])
        assert body['pagination']['total'] == pay_data['n_payments_b']
        assert body['items'][0]['tenant_name'] == pay_data['tenant_b_nom']

    def test_filtre_plan(self, app, client, pay_data):
        body = self._list(client, pay_data, plan='starter')
        assert body['pagination']['total'] == pay_data['n_payments_b']
        assert body['items'][0]['plan'] == 'starter'

    def test_filtre_dates(self, app, client, pay_data):
        today = datetime.utcnow().strftime('%Y-%m-%d')
        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          date_from=today)
        assert body['pagination']['total'] == pay_data['n_payments_a']

        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          date_from=tomorrow)
        assert body['pagination']['total'] == 0

        body = self._list(client, pay_data, tenant_id=pay_data['tenant_a_id'],
                          date_to=yesterday)
        assert body['pagination']['total'] == 0

    def test_recherche_par_reference(self, app, client, pay_data):
        body = self._list(client, pay_data, search=pay_data['p_success_ref'])
        assert body['pagination']['total'] == 1
        assert body['items'][0]['id'] == pay_data['p_success_id']

    def test_filtres_combines(self, app, client, pay_data):
        body = self._list(
            client, pay_data,
            tenant_id=pay_data['tenant_a_id'],
            provider='papi',
            payment_method='MVOLA',
            status='succes',
        )
        assert body['pagination']['total'] == 1
        assert body['items'][0]['id'] == pay_data['p_success_id']


# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #
class TestPagination:
    def test_pagination_basique(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments?tenant_id={pay_data['tenant_a_id']}"
            '&page=1&per_page=1',
            headers=pay_data['sa_headers'],
        )
        body = r.get_json()
        assert body['pagination']['total'] == pay_data['n_payments_a']
        assert body['pagination']['per_page'] == 1
        assert body['pagination']['pages'] == pay_data['n_payments_a']
        assert len(body['items']) == 1

    def test_pagination_page_2_different(self, app, client, pay_data):
        base = (f"/api/v1/super-admin/payments"
                f"?tenant_id={pay_data['tenant_a_id']}&per_page=1")
        r1 = client.get(base + '&page=1', headers=pay_data['sa_headers'])
        r2 = client.get(base + '&page=2', headers=pay_data['sa_headers'])
        id1 = r1.get_json()['items'][0]['id']
        id2 = r2.get_json()['items'][0]['id']
        assert id1 != id2

    def test_pagination_page_hors_limites(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments?tenant_id={pay_data['tenant_a_id']}"
            '&page=99&per_page=20',
            headers=pay_data['sa_headers'],
        )
        body = r.get_json()
        assert body['items'] == []
        assert body['pagination']['total'] == pay_data['n_payments_a']


# --------------------------------------------------------------------------- #
# Détail + options de filtres
# --------------------------------------------------------------------------- #
class TestDetail:
    def test_detail_complet(self, app, client, pay_data):
        r = client.get(
            f"/api/v1/super-admin/payments/{pay_data['p_success_id']}",
            headers=pay_data['sa_headers'],
        )
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data['tenant_name'] == pay_data['tenant_a_nom']
        assert data['plan'] == 'pro'
        assert data['montant'] == 15000
        assert data['devise'] == 'MGA'
        assert data['provider'] == 'papi'
        assert data['payment_method'] == 'MVOLA'
        assert data['statut'] == 'succes'
        assert data['statut_label'] == 'SUCCESS'
        assert data['external_reference'] == pay_data['p_success_ref']
        # Settlement : jamais disponible via l'integration actuelle.
        assert data['settlement']['available'] is False
        assert data['settlement']['settlement_status'] is None
        assert 'non disponibles' in data['settlement']['message'].lower()
        # Net = montant confirme - frais reels Papi (300) = 14700.
        assert data['net_amount']['available'] is True
        assert data['net_amount']['montant'] == 14700
        # Frais Papi reels issus du webhook : 300.
        assert data['papi_fees']['available'] is True
        assert data['papi_fees']['fee'] == 300.0
        # Evenements webhook presents.
        assert len(data['payment_events']) == 1
        assert data['payment_events'][0]['event_type'] == 'SUCCESS'

    def test_detail_404(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments/99999999',
                       headers=pay_data['sa_headers'])
        assert r.status_code == 404

    def test_filters_options_reelles(self, app, client, pay_data):
        r = client.get('/api/v1/super-admin/payments/filters',
                       headers=pay_data['sa_headers'])
        assert r.status_code == 200
        options = r.get_json()
        assert any(t['id'] == pay_data['tenant_a_id'] for t in options['tenants'])
        assert 'pro' in options['plans']
        assert 'papi' in options['providers']
        assert 'manuel' in options['providers']
        assert 'MVOLA' in options['payment_methods']
        values = {s['value'] for s in options['statuses']}
        assert {'succes', 'en_attente', 'echec'} <= values


# --------------------------------------------------------------------------- #
# Securite : absence de secrets
# --------------------------------------------------------------------------- #
class TestNoSecretLeak:
    def test_aucun_secret_dans_les_reponses(self, app, client, pay_data):
        urls = [
            '/api/v1/super-admin/payments?per_page=50',
            '/api/v1/super-admin/payments/stats',
            '/api/v1/super-admin/payments/filters',
            f"/api/v1/super-admin/payments/{pay_data['p_success_id']}",
        ]
        for url in urls:
            r = client.get(url, headers=pay_data['sa_headers'])
            assert r.status_code == 200, url
            _assert_no_secrets(str(r.get_json()))
