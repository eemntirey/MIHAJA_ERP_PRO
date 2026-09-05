"""Tests du flux complet de gestion des mots de passe.

Couvre :
- creation d'un compte par le Tenant (avec must_change_password=True)
- envoie d'email de bienvenue (mocke)
- premiere connexion -> flag must_change_password
- endpoint /auth/first-login-change -> must_change_password=False
- changement volontaire /auth/change-password (ancien + nouveau + confirmation)
- mot de passe oublie (forgot-password) avec token hashé en base
- verification du token
- reset-password + invalidation token
- notification email apres changement/reset
- isolation multi-tenant
- non-revelation de l'existence du compte sur forgot-password
- politique de mot de passe (longueur, complexite)
- mot de passe non stocke en clair
- token non stocke en clair
"""

import os
import re
import secrets
from datetime import datetime, timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret')

import pytest

from app import create_app, db as _db
from app.models.utilisateur import Utilisateur, StatutUtilisateur, StatutAdmin, Role
from app.models.tenant import Tenant, StatutTenant
from app.models.password_reset_token import PasswordResetToken
from app.security.auth import hash_password, verify_password


@pytest.fixture(scope='module')
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _reset_db(app):
    """Vide les tables entre chaque test pour repartir d'un etat propre.

    La base SQLite en memoire partagee necessite un nettoyage explicite
    car le compteur de slug recommence a 1 dans chaque fixture make_tenant.
    """
    with app.app_context():
        _db.session.remove()
        # On supprime les donnees sans toucher au schema
        for table in reversed(_db.metadata.sorted_tables):
            try:
                _db.session.execute(table.delete())
            except Exception:
                pass
        _db.session.commit()
    yield


@pytest.fixture
def make_tenant(db):
    counter = {'i': 0}

    def _make(slug_prefix='t', name_prefix='T', statut=None):
        counter['i'] += 1
        slug = f"{slug_prefix}{counter['i']}"
        name = f"{name_prefix}{counter['i']}"
        t = Tenant(
            nom=name,
            slug=slug,
            statut=statut or StatutTenant.EN_ESSAI,
            plan='pro',
        )
        db.session.add(t)
        db.session.commit()
        return {'id': t.id, 'slug': slug, 'name': name}

    return _make


@pytest.fixture
def make_admin(db):
    counter = {'i': 0}

    def _make(tenant, password='Admin123!', role=Role.ADMIN, email=None):
        counter['i'] += 1
        em = email or f'admin_{counter["i"]}@{tenant["slug"]}.mg'
        u = Utilisateur(
            username=f'admin_{tenant["slug"]}_{counter["i"]}',
            email=em,
            password_hash=hash_password(password),
            nom='Admin',
            prenom='Acme',
            role=role,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant['id'],
            is_principal_admin=(role == Role.ADMIN),
            admin_statut=StatutAdmin.ACTIVE,
        )
        db.session.add(u)
        db.session.commit()
        uid = u.id
        return {'id': uid, 'email': em, 'password': password, 'tenant_id': tenant['id']}

    return _make


def _login(client, identifier, password, tenant_slug):
    return client.post('/api/v1/auth/login', json={
        'username': identifier,
        'password': password,
        'tenant_slug': tenant_slug,
    })


def _extract_reset_token(html_body):
    m = re.search(r'reset-password/([A-Za-z0-9_\-]+)', html_body)
    assert m, f'Token brut introuvable dans le mail : {html_body[:200]}'
    return m.group(1)


# ---------------------------------------------------------------------------
# Creation de compte par le Tenant
# ---------------------------------------------------------------------------

class TestUserCreationByTenant:

    def test_creation_genere_mdp_temporaire_et_flag(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        login_resp = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        assert login_resp.status_code == 200
        admin_token = login_resp.get_json()['access_token']

        with patch_send_emails():
            r = client.post(
                '/api/v1/users/',
                json={
                    'username': 'emp1',
                    'email': f'emp1@{tenant["slug"]}.mg',
                    'role': 'sales',
                },
                headers={'Authorization': f'Bearer {admin_token}'},
            )
        assert r.status_code == 201, r.get_json()
        data = r.get_json()
        assert data['must_change_password'] is True
        assert data.get('temporary_password')
        assert data['temporary_password'] != f'emp1@{tenant["slug"]}.mg'

    def test_email_bienvenue_appele_lors_creation(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        login_resp = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = login_resp.get_json()['access_token']

        with patch_send_emails() as sent:
            r = client.post(
                '/api/v1/users/',
                json={
                    'username': 'emp',
                    'email': f'emp@{tenant["slug"]}.mg',
                    'role': 'sales',
                },
                headers={'Authorization': f'Bearer {token}'},
            )
        temp_pwd = r.get_json()['temporary_password']
        # L'email de bienvenue doit etre envoye avec le mdp temporaire
        assert len(sent) >= 1, f"Aucun email envoye. Sent={sent}"
        body = sent[0].html_body
        # Le mot de passe temporaire est dans le mail (et uniquement parce
        # qu'il vient d'etre genere).
        assert temp_pwd in body, f"temp_pwd={temp_pwd!r} non trouve dans body"

    def test_password_jamais_stocke_en_clair(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        login_resp = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = login_resp.get_json()['access_token']

        r = client.post(
            '/api/v1/users/',
            json={
                'username': 'emp',
                'email': f'emp@{tenant["slug"]}.mg',
                'role': 'sales',
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        temp_pwd = r.get_json()['temporary_password']

        with app.app_context():
            u = Utilisateur.query.filter_by(email=f'emp@{tenant["slug"]}.mg').first()
            assert u.password_hash != temp_pwd
            assert verify_password(temp_pwd, u.password_hash)
            d = u.to_dict()
            assert 'password_hash' not in d
            assert 'password' not in d


# ---------------------------------------------------------------------------
# Premiere connexion : obligation de changement
# ---------------------------------------------------------------------------

def _create_employe_with_temp_pwd(client, admin_token, tenant_slug):
    r = client.post(
        '/api/v1/users/',
        json={
            'username': f'emp_{secrets.token_hex(4)}',
            'email': f'emp_{secrets.token_hex(4)}@{tenant_slug}.mg',
            'role': 'sales',
        },
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert r.status_code == 201, r.get_json()
    return r.get_json()['email'], r.get_json()['temporary_password']


class TestFirstLoginChange:

    def test_login_renvoie_must_change_password_true(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']
        email, temp = _create_employe_with_temp_pwd(client, token, tenant["slug"])

        r2 = client.post(
            '/api/v1/auth/login',
            json={'username': email, 'password': temp, 'tenant_slug': tenant["slug"]},
        )
        assert r2.status_code == 200
        data = r2.get_json()
        assert data['must_change_password'] is True
        assert data['user']['must_change_password'] is True

    def test_first_change_password_force_le_changement(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']
        email, temp = _create_employe_with_temp_pwd(client, token, tenant["slug"])

        user_login = client.post(
            '/api/v1/auth/login',
            json={'username': email, 'password': temp, 'tenant_slug': tenant["slug"]},
        )
        user_token = user_login.get_json()['access_token']

        new_pwd = 'NewPass123!'
        r2 = client.post(
            '/api/v1/auth/first-login-change',
            json={'new_password': new_pwd, 'confirm_password': new_pwd},
            headers={'Authorization': f'Bearer {user_token}'},
        )
        assert r2.status_code == 200, r2.get_json()
        assert r2.get_json()['user']['must_change_password'] is False

        with app.app_context():
            u = Utilisateur.query.filter_by(email=email).first()
            assert not verify_password(temp, u.password_hash)
            assert verify_password(new_pwd, u.password_hash)

    def test_first_change_rejete_si_confirmation_differente(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']
        email, temp = _create_employe_with_temp_pwd(client, token, tenant["slug"])
        user_login = client.post(
            '/api/v1/auth/login',
            json={'username': email, 'password': temp, 'tenant_slug': tenant["slug"]},
        )
        ut = user_login.get_json()['access_token']

        r2 = client.post(
            '/api/v1/auth/first-login-change',
            json={'new_password': 'NewPass123!', 'confirm_password': 'Different1!'},
            headers={'Authorization': f'Bearer {ut}'},
        )
        assert r2.status_code == 400
        assert 'correspondent' in r2.get_json()['message']

    def test_first_change_rejete_mdp_trop_faible(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']
        email, temp = _create_employe_with_temp_pwd(client, token, tenant["slug"])
        user_login = client.post(
            '/api/v1/auth/login',
            json={'username': email, 'password': temp, 'tenant_slug': tenant["slug"]},
        )
        ut = user_login.get_json()['access_token']
        r2 = client.post(
            '/api/v1/auth/first-login-change',
            json={'new_password': 'short', 'confirm_password': 'short'},
            headers={'Authorization': f'Bearer {ut}'},
        )
        assert r2.status_code == 400


# ---------------------------------------------------------------------------
# Changement volontaire
# ---------------------------------------------------------------------------

class TestChangePassword:

    def test_change_password_avec_ancien_correct(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']

        new_pwd = 'NewAdmin456!'
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Admin123!',
                'new_password': new_pwd,
                'confirm_password': new_pwd,
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 200, r.get_json()

        r_old = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        assert r_old.status_code == 401

        r_new = _login(client, admin["email"], new_pwd, tenant["slug"])
        assert r_new.status_code == 200

    def test_change_password_ancien_incorrect(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']

        new_pwd = 'NewAdmin456!'
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Mauvais123!',
                'new_password': new_pwd,
                'confirm_password': new_pwd,
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 403

    def test_change_password_confirmation_differente(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        token = al.get_json()['access_token']

        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Admin123!',
                'new_password': 'NewAdmin456!',
                'confirm_password': 'OtherPwd789!',
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 400

    def test_change_password_invalide_jwt(self, app, client):
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'x',
                'new_password': 'NewAdmin456!',
                'confirm_password': 'NewAdmin456!',
            },
        )
        assert r.status_code in (401, 422)


# ---------------------------------------------------------------------------
# Mot de passe oublie + token
# ---------------------------------------------------------------------------

class TestForgotPassword:

    def test_reponse_generique_pour_compte_inexistant(self, app, client):
        r = client.post('/api/v1/auth/forgot-password', json={'email': 'no@one.mg'})
        assert r.status_code == 200
        assert 'Si un compte existe' in r.get_json()['message']

    def test_forgot_password_genere_token_hash_en_base(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        with patch_send_emails() as sent:
            r = client.post(
                '/api/v1/auth/forgot-password', json={'email': admin["email"]}
            )
        assert r.status_code == 200
        assert any('reset-password/' in c.html_body for c in sent)

        with app.app_context():
            tokens = PasswordResetToken.query.all()
            assert len(tokens) == 1
            stored = tokens[0].token
            raw = _extract_reset_token(sent[0].html_body)
            assert stored != raw
            assert PasswordResetToken.hash_token(raw) == stored

    def test_token_inutilisable_si_expire(self, app, client, make_tenant, make_admin):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)
            raw = 'expired-token-xyz'
            tok = PasswordResetToken(
                user_id=admin["id"],
                token=PasswordResetToken.hash_token(raw),
                expires_at=datetime.utcnow() - timedelta(minutes=1),
            )
            _db.session.add(tok)
            _db.session.commit()

        r = client.post(
            '/api/v1/auth/reset-password',
            json={'token': raw, 'new_password': 'NewPass789!'},
        )
        assert r.status_code == 400

    def test_token_inutilisable_apres_utilisation(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        raw = secrets.token_urlsafe(32)
        with app.app_context():
            t2 = PasswordResetToken(
                user_id=admin["id"],
                token=PasswordResetToken.hash_token(raw),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
            _db.session.add(t2)
            _db.session.commit()

        r1 = client.post(
            '/api/v1/auth/reset-password',
            json={'token': raw, 'new_password': 'NewPass789!'},
        )
        assert r1.status_code == 200

        r2 = client.post(
            '/api/v1/auth/reset-password',
            json={'token': raw, 'new_password': 'OtherPass456!'},
        )
        assert r2.status_code == 400

    def test_reset_password_change_hash_et_envoie_email(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        with patch_send_emails() as sent:
            client.post(
                '/api/v1/auth/forgot-password', json={'email': admin["email"]}
            )
        raw = _extract_reset_token(sent[0].html_body)

        with patch_send_emails() as sent2:
            r = client.post(
                '/api/v1/auth/reset-password',
                json={'token': raw, 'new_password': 'BrandNew789!'},
            )
        assert r.status_code == 200
        # Email "password changed" envoye apres reset
        assert len(sent2) >= 1
        assert 'modifie' in sent2[0].html_body.lower() or \
               'changed' in sent2[0].html_body.lower()

        r2 = _login(client, admin["email"], 'BrandNew789!', tenant["slug"])
        assert r2.status_code == 200
        r3 = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        assert r3.status_code == 401

    def test_verify_reset_token(self, app, client, make_tenant, make_admin):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        with patch_send_emails() as sent:
            client.post(
                '/api/v1/auth/forgot-password', json={'email': admin["email"]}
            )
        raw = _extract_reset_token(sent[0].html_body)

        r = client.post('/api/v1/auth/verify-reset-token', json={'token': raw})
        assert r.status_code == 200
        assert r.get_json()['valid'] is True

        r2 = client.post(
            '/api/v1/auth/verify-reset-token', json={'token': 'invalid-token'}
        )
        assert r2.get_json()['valid'] is False


# ---------------------------------------------------------------------------
# Isolation multi-tenant
# ---------------------------------------------------------------------------

class TestTenantIsolation:

    def test_token_genere_pour_un_user_ne_reset_qu_ce_user(
        self, app, client, make_tenant, make_admin
    ):
        with app.app_context():
            tA = make_tenant(slug_prefix='isoA', name_prefix='IsoA')
            tB = make_tenant(slug_prefix='isoB', name_prefix='IsoB')
            uA = make_admin(tA, password='AdminA1!')
            uB = make_admin(tB, password='AdminB1!')

        with patch_send_emails() as sent:
            client.post(
                '/api/v1/auth/forgot-password', json={'email': uA["email"]}
            )
        raw = _extract_reset_token(sent[0].html_body)

        r = client.post(
            '/api/v1/auth/reset-password',
            json={'token': raw, 'new_password': 'HackedPass1!'},
        )
        assert r.status_code == 200

        with app.app_context():
            assert verify_password(
                'HackedPass1!', Utilisateur.query.get(uA["id"]).password_hash
            )
            assert verify_password(
                'AdminB1!', Utilisateur.query.get(uB["id"]).password_hash
            )


# ---------------------------------------------------------------------------
# Politique de mot de passe
# ---------------------------------------------------------------------------

class TestPasswordPolicy:

    def _login_admin_token(self, client, tenant, admin):
        al = _login(client, admin["email"], 'Admin123!', tenant["slug"])
        return al.get_json()['access_token']

    def test_mdp_court_refuse(self, app, client, make_tenant, make_admin):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)
        token = self._login_admin_token(client, tenant, admin)
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Admin123!',
                'new_password': 'Ab1!',
                'confirm_password': 'Ab1!',
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 400
        assert 'caracteres' in r.get_json()['message']

    def test_mdp_sans_majuscule_refuse(self, app, client, make_tenant, make_admin):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)
        token = self._login_admin_token(client, tenant, admin)
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Admin123!',
                'new_password': 'alllower1!',
                'confirm_password': 'alllower1!',
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 400

    def test_mdp_sans_chiffre_refuse(self, app, client, make_tenant, make_admin):
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)
        token = self._login_admin_token(client, tenant, admin)
        r = client.post(
            '/api/v1/auth/change-password',
            json={
                'old_password': 'Admin123!',
                'new_password': 'AllLowerX!',
                'confirm_password': 'AllLowerX!',
            },
            headers={'Authorization': f'Bearer {token}'},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:

    def test_reset_audit_enregistre_sans_token_brut(
        self, app, client, make_tenant, make_admin
    ):
        from app.models.audit_log import AuditLog, TypeActionAudit
        with app.app_context():
            tenant = make_tenant()
            admin = make_admin(tenant)

        with patch_send_emails() as sent:
            client.post(
                '/api/v1/auth/forgot-password', json={'email': admin["email"]}
            )
        raw = _extract_reset_token(sent[0].html_body)

        with patch_send_emails():
            client.post(
                '/api/v1/auth/reset-password',
                json={'token': raw, 'new_password': 'BrandNew789!'},
            )

        with app.app_context():
            audits = AuditLog.query.filter(
                AuditLog.type_action == TypeActionAudit.PASSWORD_RESET_COMPLETED
            ).all()
            assert len(audits) >= 1
            for a in audits:
                meta = a.metadata_json or ''
                assert raw not in meta
                assert 'password' not in meta.lower() or 'changed' in meta.lower()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SentEmail:
    def __init__(self, html_body, recipient):
        self.html_body = html_body
        self.recipient = recipient


class patch_send_emails:
    """Mocke send_email pour eviter tout envoi SMTP reel pendant les tests."""

    def __enter__(self):
        from app.services import email_service
        self._sents = []
        self._orig = email_service.send_email

        def _fake(subject, html_body, recipient, *, config=None):
            self._sents.append(_SentEmail(html_body, recipient))
            return {'success': True, 'recipient': recipient, 'delivered': False}

        email_service.send_email = _fake
        return self._sents

    def __exit__(self, exc_type, exc, tb):
        from app.services import email_service
        email_service.send_email = self._orig