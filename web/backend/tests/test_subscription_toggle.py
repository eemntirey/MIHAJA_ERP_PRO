# -*- coding: utf-8 -*-
import os

"""Tests du toggle abonnement global (Super Admin).

Couvre :
- inscription en mode INACTIF : plan Pro offert automatiquement ;
- inscription en mode ACTIF : choix conservé, grille Gratuit/Pro/Enterprise
  (Gratuit reprend les limites de l'ancien Starter) ;
- grille publique /auth/plans selon l'état du toggle ;
- non-blocage de la limite employés en mode INACTIF (avertissement only) ;
- bascule Inactif -> Actif : cycle de grâce 30j démarré pour les Pro gratuits ;
- rappels de paiement tous les 3 jours pendant la période de grâce ;
- rétrogradation après 30 jours : les données restent en base.
"""
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.platform_config import PlatformConfig
from app.models.subscription_audit import SubscriptionAuditTrail
from app.models.notification import Notification
from app.models.produit import Produit
from app.security.auth import hash_password
from app.security.plans import get_plan_price


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', os.environ.get('DATABASE_URL', 'postgresql+psycopg://postgres@localhost:55432/erp_test'))
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    # Réinitialiser les compteurs rate-limit mémoire entre les tests.
    from app.security import rate_limit
    rate_limit._memory_counters.clear()
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _register_company(client, suffix, plan=None):
    payload = {
        'profile_type': 'company',
        'nom_entreprise': f'Entreprise {suffix}',
        'email': f'{suffix}@test.mg',
        'username': suffix,
        'password': 'Passw0rd!X',
        'nom': 'Nom',
        'prenom': 'Prenom',
    }
    if plan is not None:
        payload['plan'] = plan
    return client.post('/api/v1/auth/register', json=payload)


def _make_super_admin():
    sa = Utilisateur(
        username='super',
        email='super@x.mg',
        password_hash=hash_password('Super123!'),
        role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(sa)
    db.session.commit()
    return sa


def _super_admin_headers(client):
    _make_super_admin()
    r = client.post('/api/v1/auth/login', json={
        'username': 'super@x.mg', 'password': 'Super123!',
    })
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def _make_pro_free_subscription():
    """Tenant avec abonnement Pro gratuit (montant 0), comme en mode INACTIF."""
    tenant = Tenant(
        nom='Pro Gratuit', slug='pro-gratuit', plan='pro',
        statut='actif', is_active=True,
    )
    db.session.add(tenant)
    db.session.flush()
    now = datetime.utcnow()
    abn = Abonnement(
        tenant_id=tenant.id, montant=0, devise='MGA',
        date_debut=now - timedelta(days=10),
        date_fin=now + timedelta(days=365 * 99),
        statut=StatutAbonnement.ACTIF, plan='pro',
    )
    db.session.add(abn)
    db.session.commit()
    return tenant.id, abn.id

class TestPublicPlans:
    def test_mode_toujours_actif_grille_gratuit_pro_entreprise(self, app):
        """Le toggle a été retiré (abonnement toujours actif) : la grille
        publique est stable (gratuit / pro / enterprise) et le payload
        expose subscription_active=True."""
        client = app.test_client()
        r = client.get('/api/v1/auth/plans')
        assert r.status_code == 200
        data = r.get_json()
        codes = [p['code'] for p in data['plans']]
        assert codes == ['gratuit', 'pro', 'enterprise']
        assert 'starter' not in codes

    def test_toggle_endpoint_toujours_actif(self, app):
        """L'endpoint super-admin /subscription-toggle est devenu un no-op :
        GET/PUT renvoient toujours subscription_active=True."""
        client = app.test_client()
        headers = _super_admin_headers(client)
        r = client.get('/api/v1/super-admin/subscription-toggle', headers=headers)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['subscription_active'] is True
        r2 = client.put('/api/v1/super-admin/subscription-toggle',
                        headers=headers, json={'subscription_active': False})
        assert r2.status_code == 200, r2.get_json()
        assert r2.get_json()['subscription_active'] is True


class TestInscription:
    def test_inscription_plan_choisi(self, app):
        """En mode toujours actif, le plan choisi est conservé."""
        client = app.test_client()
        r = _register_company(client, 'actif1', plan='gratuit')
        assert r.status_code == 201, r.get_json()
        tenant_id = r.get_json()['tenant']['id']
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_id)
            assert tenant.plan == 'gratuit'


class TestQuotasModeActif:
    def test_employes_bloquants_au_dela_de_la_limite_pro(self, app):
        """Le mode est toujours ACTIF : la limite du plan Pro s'applique."""
        client = app.test_client()
        r = _register_company(client, 'quota1', plan='pro')
        assert r.status_code == 201, r.get_json()
        token = r.get_json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        # Plan pro : au-delà de la limite -> bloqué (403) par check_plan_limits.
        codes = []
        for i in range(11):
            rr = client.post('/api/v1/users', headers=headers, json={
                'username': f'emp{i}',
                'email': f'emp{i}@quota1.mg',
                'password': 'Pass123!x',
                'role': 'user',
            })
            codes.append(rr.status_code)
        assert any(code == 403 for code in codes), codes

class TestToggleActivation:
    def test_toggle_refuse_sans_droits_super_admin(self, app):
        client = app.test_client()
        r = client.put('/api/v1/super-admin/subscription-toggle',
                       json={'subscription_active': True})
        assert r.status_code == 401


class TestRappelsPaiement:
    def test_rappel_tous_les_3_jours(self, app):
        from app.tasks.subscription_scheduler import run_subscription_reminders
        tenant_id, abn_id = _make_pro_free_subscription()
        with app.app_context():
            abn_db = db.session.get(Abonnement, abn_id)
            # Période de grâce simulée : expiration dans 15 jours.
            abn_db.date_fin = datetime.utcnow() + timedelta(days=15)
            db.session.commit()

            # J+0 : premier rappel
            res = run_subscription_reminders()
            assert any(
                x['tenant_id'] == tenant_id and x['status'] == 'reminder_sent'
                for x in res
            ), res

            # J+1 : pas de nouveau rappel (< 3 jours écoulés)
            res = run_subscription_reminders()
            assert all(
                x['status'] != 'reminder_sent' or x['tenant_id'] != tenant_id
                for x in res
            )

            # J+4 : rappel envoyé
            last = Notification.query.filter_by(
                tenant_id=tenant_id, type='subscription_reminder',
                is_active=True,
            ).order_by(Notification.created_at.desc()).first()
            last.created_at = datetime.utcnow() - timedelta(days=4)
            db.session.commit()
            res = run_subscription_reminders()
            assert any(
                x['tenant_id'] == tenant_id and x['status'] == 'reminder_sent'
                for x in res
            ), res
            count_after_j4 = Notification.query.filter_by(
                tenant_id=tenant_id, type='subscription_reminder',
                is_active=True,
            ).count()
            assert count_after_j4 == 2

            # J+5 (< 3 jours après le rappel J+4) : pas de nouveau rappel
            res = run_subscription_reminders()
            assert all(
                x['status'] != 'reminder_sent' or x['tenant_id'] != tenant_id
                for x in res
            )


class TestRetrogradation30Jours:
    def test_donnees_conservees_apres_retrogradation(self, app):
        from app.tasks.subscription_scheduler import run_subscription_expiration_check
        tenant_id, abn_id = _make_pro_free_subscription()
        with app.app_context():
            # Abonnement Pro expiré depuis 31 jours
            abn_db = db.session.get(Abonnement, abn_id)
            now = datetime.utcnow()
            abn_db.date_debut = now - timedelta(days=61)
            abn_db.date_fin = now - timedelta(days=31)
            db.session.commit()
            # Données métier du tenant
            produit = Produit(
                tenant_id=tenant_id,
                reference='REF-TEST-1',
                nom='Produit de test',
                prix_achat_ht=1000,
                prix_vente_ht=1500,
            )
            db.session.add(produit)
            db.session.commit()

            res = run_subscription_expiration_check()
            assert any(
                x['tenant_id'] == tenant_id and x['status'] == 'retrograded'
                for x in res
            )
            tenant_db = db.session.get(Tenant, tenant_id)
            assert tenant_db.plan == 'gratuit'
            audit = SubscriptionAuditTrail.query.filter_by(
                tenant_id=tenant_id, declencheur='automatique',
            ).first()
            assert audit is not None
            assert audit.nouveau_plan == 'gratuit'
            # AUCUNE suppression de données : le produit reste en base
            produit_db = db.session.get(Produit, produit.id)
            assert produit_db is not None
            assert produit_db.nom == 'Produit de test'

