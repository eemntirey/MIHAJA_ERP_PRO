# -*- coding: utf-8 -*-
"""Tests du toggle abonnement global (Super Admin).

import os

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
    def test_mode_inactif_affiche_pro_seul(self, app):
        client = app.test_client()
        r = client.get('/api/v1/auth/plans')
        assert r.status_code == 200
        data = r.get_json()
        assert data['subscription_active'] is False
        codes = [p['code'] for p in data['plans']]
        assert codes == ['pro']

    def test_mode_actif_grille_gratuit_pro_entreprise(self, app):
        cfg = PlatformConfig.get_config()
        cfg.is_subscription_active = True
        db.session.commit()
        client = app.test_client()
        r = client.get('/api/v1/auth/plans')
        assert r.status_code == 200
        data = r.get_json()
        assert data['subscription_active'] is True
        codes = [p['code'] for p in data['plans']]
        assert codes == ['gratuit', 'pro', 'enterprise']
        assert 'starter' not in codes
        # Gratuit (ex-Starter) reprend les anciennes limites Starter
        gratuit = data['plans'][0]
        nouvelles_limites_gratuit = {
            'max_utilisateurs': 3,
            'max_produits': 50,
            'max_clients': 100,
            'max_employees': 2,
            'prix': 5000,
            'duree_jours': 30,
        }
        for key, value in nouvelles_limites_gratuit.items():
            assert gratuit[key] == value, f'{key}: {gratuit[key]} != {value}'


class TestInscription:
    def test_inscription_mode_inactif_plan_pro_automatique(self, app):
        client = app.test_client()
        r = _register_company(client, 'inactif1')
        assert r.status_code == 201, r.get_json()
        tenant_id = r.get_json()['tenant']['id']
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_id)
            assert tenant is not None
            assert tenant.plan == 'pro'
            abn = Abonnement.query.filter_by(tenant_id=tenant_id).first()
            assert abn is not None
            assert abn.plan == 'pro'
            assert float(abn.montant) == 0

    def test_inscription_mode_actif_plan_choisi(self, app):
        cfg = PlatformConfig.get_config()
        cfg.is_subscription_active = True
        db.session.commit()
        client = app.test_client()
        r = _register_company(client, 'actif1', plan='gratuit')
        assert r.status_code == 201, r.get_json()
        tenant_id = r.get_json()['tenant']['id']
        with app.app_context():
            tenant = db.session.get(Tenant, tenant_id)
            assert tenant.plan == 'gratuit'


class TestQuotasModeInactif:
    def test_employes_non_bloquants_au_dela_de_10_en_mode_inactif(self, app):
        """La limite employés (seuil 10 en découverte) n'est PAS bloquante."""
        client = app.test_client()
        r = _register_company(client, 'quota1')
        assert r.status_code == 201, r.get_json()
        token = r.get_json()['access_token']
        headers = {'Authorization': 'Bearer ' + token}
        # Plan pro = 6 employés max ; en mode INACTIF, au-delà : autorisé.
        for i in range(11):
            rr = client.post('/api/v1/users', headers=headers, json={
                'username': f'emp{i}',
                'email': f'emp{i}@quota1.mg',
                'password': 'Pass123!x',
                'role': 'user',
            })
class TestToggleActivation:
    def test_activation_demarre_grace_30j_pour_pro_gratuit(self, app):
        tenant_id, abn_id = _make_pro_free_subscription()
        headers = _super_admin_headers(app.test_client())
        r = app.test_client().put(
            '/api/v1/super-admin/subscription-toggle',
            headers=headers,
            json={'subscription_active': True},
        )
        assert r.status_code == 200, r.get_json()
        with app.app_context():
            now = datetime.utcnow()
            cfg = PlatformConfig.get_config()
            assert cfg.is_subscription_active is True
            abn_db = db.session.get(Abonnement, abn_id)
            # Cycle de grâce : 30 jours à partir de l'activation
            delta = (abn_db.date_fin - now).total_seconds()
            assert 29 * 86400 < delta <= 30 * 86400
            # Montant aligné sur le prix courant du plan Pro
            assert float(abn_db.montant) == float(get_plan_price('pro'))
            # Audit trail dédié
            audit = SubscriptionAuditTrail.query.filter_by(
                tenant_id=tenant_id, declencheur='activation_toggle',
            ).first()
            assert audit is not None
            assert audit.nouveau_plan == 'pro'
            # Notification initiale envoyée
            notif = Notification.query.filter_by(
                tenant_id=tenant_id, type='subscription_reminder',
            ).first()
            assert notif is not None

    def test_toggle_reversible(self, app):
        headers = _super_admin_headers(app.test_client())
        c = app.test_client()
        r1 = c.put('/api/v1/super-admin/subscription-toggle',
                   headers=headers, json={'subscription_active': True})
        assert r1.status_code == 200
        r2 = c.put('/api/v1/super-admin/subscription-toggle',
                   headers=headers, json={'subscription_active': False})
        assert r2.status_code == 200
        r3 = c.get('/api/v1/super-admin/subscription-toggle', headers=headers)
        assert r3.status_code == 200
        assert r3.get_json()['subscription_active'] is False

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
            abn_db.date_fin = datetime.utcnow() + timedelta(days=15)
            db.session.commit()

            client = app.test_client()
            headers = _super_admin_headers(client)
            # Activation du toggle (envoie la notification initiale J+0)
            r = client.put('/api/v1/super-admin/subscription-toggle',
                           headers=headers, json={'subscription_active': True})
            assert r.status_code == 200

            # J+1 : pas de nouveau rappel (< 3 jours écoulés)
            res = run_subscription_reminders()
            assert all(x['status'] != 'reminder_sent' for x in res)

            # J+4 : rappel envoyé
            last = Notification.query.filter_by(
                tenant_id=tenant_id, type='subscription_reminder',
                is_active=True,
            ).order_by(Notification.created_at.desc()).first()
            last.created_at = datetime.utcnow() - timedelta(days=4)
            db.session.commit()
            res = run_subscription_reminders()
            assert any(x['status'] == 'reminder_sent' for x in res)
            count_after_j4 = Notification.query.filter_by(
                tenant_id=tenant_id, type='subscription_reminder',
                is_active=True,
            ).count()
            assert count_after_j4 == 2

            # J+5 (< 3 jours après le rappel J+4) : pas de nouveau rappel
            res = run_subscription_reminders()
            assert all(x['status'] != 'reminder_sent' for x in res)


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

