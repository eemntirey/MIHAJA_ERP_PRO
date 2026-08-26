import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.produit import Produit
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.stock import MouvementStock
from app.models.facture import Facture
from app.models.facture_fournisseur import FactureFournisseur
from app.models.paiement import Paiement, StatutPaiement, StatutPaiement
from app.models.commande_client import CommandeClient
from app.models.commande_achat import CommandeAchat
from app.models.livraison import Livraison
from app.models.employe import Employe
from app.models.compte_comptable import CompteComptable
from app.models.ecriture_comptable import EcritureComptable
from app.models.tresorerie import Tresorerie
from app.models.document_genere import DocumentGenere
from app.models.modele_document import ModeleDocument
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_context():
    ta = Tenant.query.filter_by(slug='tenant-a').first()
    tb = Tenant.query.filter_by(slug='tenant-b').first()
    if not ta:
        ta = Tenant(nom='Tenant A', slug='tenant-a', domaine='a.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(ta)
    if not tb:
        tb = Tenant(nom='Tenant B', slug='tenant-b', domaine='b.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(tb)
    db.session.flush()

    if not Abonnement.query.filter_by(tenant_id=ta.id).first():
        db.session.add(Abonnement(
            tenant_id=ta.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))
    if not Abonnement.query.filter_by(tenant_id=tb.id).first():
        db.session.add(Abonnement(
            tenant_id=tb.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))

    admin_a = Utilisateur.query.filter_by(username='admin_a').first()
    admin_b = Utilisateur.query.filter_by(username='admin_b').first()
    super_admin = Utilisateur.query.filter_by(username='super').first()
    if not admin_a:
        admin_a = Utilisateur(
            username='admin_a', email='admin@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
        )
        db.session.add(admin_a)
    if not admin_b:
        admin_b = Utilisateur(
            username='admin_b', email='admin@b.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tb.id,
        )
        db.session.add(admin_b)
    if not super_admin:
        super_admin = Utilisateur(
            username='super', email='super@x.mg',
            password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
    db.session.commit()
    return ta, tb, admin_a, admin_b, super_admin


def _login(client, identifier, password, tenant_slug=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def _get_tenant_id_from_token(client, headers):
    import jwt as pyjwt
    token = headers['Authorization'].split(' ')[1]
    decoded = pyjwt.decode(token, options={"verify_signature": False})
    return decoded.get('tenant_id')


class TestSecurityMultiTenancy:
    def test_jwt_contains_tenant_claims(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        r = client.get('/api/v1/auth/me', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['tenant_id'] is not None
        assert data['tenant']['slug'] == 'tenant-a'

    def test_super_admin_jwt_has_no_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')
        r = client.get('/api/v1/auth/me', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['tenant_id'] is None

    def test_password_reset_token_is_hashed(self, app):
        ta, _, admin_a, _, _ = _make_context()
        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/forgot-password', json={'email': 'admin@a.mg'})
            assert r.status_code == 200
            token = PasswordResetToken.query.filter_by(user_id=admin_a.id, used=False).first()
            assert token is not None
            assert token.token != 'test-token'
            assert len(token.token) > 20

    def test_cross_tenant_produits_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            p_a = Produit(nom='Produit A', reference='PA', tenant_id=ta.id, prix_achat_ht=10, prix_vente_ht=15)
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add_all([p_a, p_b])
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/produits/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/produits/{pid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/produits/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_clients_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.commit()
            cid_b = c_b.id

        r = client.get(f'/api/v1/clients/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/clients/{cid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/clients/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.commit()
            fid_b = f_b.id

        r = client.get(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a, json={'raison_sociale': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_ventes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.commit()
            vid_b = v_b.id

        r = client.get(f'/api/v1/ventes/{vid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/ventes/{vid_b}', headers=headers_a, json={'remarque': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/ventes/{vid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_factures_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.flush()
            f_b = Facture(vente_id=v_b.id, client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FB')
            db.session.add(f_b)
            db.session.commit()
            fid_b = f_b.id

        r = client.get(f'/api/v1/factures/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/factures/{fid_b}', headers=headers_a, json={'statut': 'payee'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/factures/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_paiements_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.flush()
            f_b = Facture(vente_id=v_b.id, client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FB')
            db.session.add(f_b)
            db.session.flush()
            p_b = Paiement(facture_id=f_b.id, tenant_id=tb.id, montant=50, statut=StatutPaiement.CONFIRME)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/paiements/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/paiements/{pid_b}', headers=headers_a, json={'montant': 999})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/paiements/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_employes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            e_b = Employe(nom='Employe B', prenom='B', matricule='EMP-B', tenant_id=tb.id, salaire_base=1000)
            db.session.add(e_b)
            db.session.commit()
            eid_b = e_b.id

        r = client.get(f'/api/v1/employes/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/employes/{eid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/employes/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_comptes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = CompteComptable(numero='401B', nom='Compte B', type_compte='passif', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.commit()
            cid_b = c_b.id

        r = client.get(f'/api/v1/comptes/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/comptes/{cid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/comptes/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_ecritures_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_a = CompteComptable(numero='401A', nom='Compte A', type_compte='passif', tenant_id=ta.id)
            c_b = CompteComptable(numero='401B', nom='Compte B', type_compte='passif', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            e_b = EcritureComptable(compte_id=c_b.id, tenant_id=tb.id, libelle='Ecriture B', montant_debit=100, date=datetime.utcnow())
            db.session.add(e_b)
            db.session.commit()
            eid_b = e_b.id

        r = client.get(f'/api/v1/ecritures/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/ecritures/{eid_b}', headers=headers_a, json={'libelle': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/ecritures/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_tresorerie_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            t_b = Tresorerie(tenant_id=tb.id, montant=100, libelle='Tresorerie B', type_operation='entree', date=datetime.utcnow())
            db.session.add(t_b)
            db.session.commit()
            tid_b = t_b.id

        r = client.get(f'/api/v1/tresorerie/{tid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/tresorerie/{tid_b}', headers=headers_a, json={'libelle': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/tresorerie/{tid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_commandes_achat_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            ca_b = CommandeAchat(tenant_id=tb.id, fournisseur_id=f_b.id, reference='CA-B', total_ht=100, total_ttc=120)
            db.session.add(ca_b)
            db.session.commit()
            caid_b = ca_b.id

        r = client.get(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a, json={'reference': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_livraisons_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            l_b = Livraison(tenant_id=tb.id, statut='en_attente', adresse_livraison='Addr B')
            db.session.add(l_b)
            db.session.commit()
            lid_b = l_b.id

        r = client.get(f'/api/v1/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/livraisons/{lid_b}', headers=headers_a, json={'statut': 'livree'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_documents_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            md_b = ModeleDocument(nom='Modele B', type_document='facture', contenu_modele='<html></html>', tenant_id=tb.id)
            db.session.add(md_b)
            db.session.flush()
            d_b = DocumentGenere(modele_id=md_b.id, tenant_id=tb.id, type_document='facture', reference='DOC-B')
            db.session.add(d_b)
            db.session.commit()
            did_b = d_b.id

        r = client.get(f'/api/v1/documents/{did_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/documents/{did_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_notifications_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            n_b = Notification(title='Notif B', tenant_id=tb.id)
            db.session.add(n_b)
            db.session.commit()
            nid_b = n_b.id

        r = client.get(f'/api/v1/notifications/{nid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/notifications/{nid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_list_no_leak(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            p_a = Produit(nom='Produit A', reference='PA', tenant_id=ta.id, prix_achat_ht=10, prix_vente_ht=15)
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add_all([p_a, p_b])
            db.session.commit()

        r = client.get('/api/v1/produits', headers=headers_a)
        assert r.status_code == 200
        data = r.get_json()
        names = {p['nom'] for p in data['produits']}
        assert 'Produit A' in names
        assert 'Produit B' not in names

    def test_cross_tenant_stocks_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30, quantite_stock=5, seuil_alerte=10)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/stocks/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_super_admin_can_access_cross_tenant(self, app):
        ta, tb, admin_a, admin_b, super_admin = _make_context()
        client = app.test_client()
        headers_super = _login(client, 'super', 'Super123!')

        with app.app_context():
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/produits/{pid_b}', headers=headers_super)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['nom'] == 'Produit B'

    def test_dashboard_tenant_scoped(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id, est_actif=True)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id, est_actif=True)
            db.session.add_all([c_a, c_b])
            db.session.commit()

        r_a = client.get('/api/v1/dashboard/', headers=headers_a)
        assert r_a.status_code == 200
        data_a = r_a.get_json()
        assert data_a['stats']['clients_actifs'] == 1

        r_b = client.get('/api/v1/dashboard/', headers=headers_b)
        assert r_b.status_code == 200
        data_b = r_b.get_json()
        assert data_b['stats']['clients_actifs'] == 1

    def test_secret_key_required(self, monkeypatch):
        monkeypatch.delenv('SECRET_KEY', raising=False)
        monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
        with pytest.raises(ValueError, match='SECRET_KEY'):
            create_app()

    def test_cors_wildcard_rejected(self, monkeypatch):
        monkeypatch.setenv('CORS_ORIGINS', '*')
        monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        with pytest.raises(ValueError, match='CORS_ORIGINS cannot contain'):
            create_app()

    def test_password_complexity_enforced(self, app):
        _make_context()
        client = app.test_client()

        r = client.post('/api/v1/auth/register', json={
            'email': 'new@test.com',
            'username': 'newuser',
            'password': 'weak'
        })
        assert r.status_code == 400
        assert '8 caracteres' in r.get_json()['message']

    def test_cross_tenant_ventes_list_no_leak(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            v_a = Vente(client_id=c_a.id, tenant_id=ta.id, total_ht=100, total_ttc=120, reference='VA')
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=200, total_ttc=240, reference='VB')
            db.session.add_all([v_a, v_b])
            db.session.commit()

        r = client.get('/api/v1/ventes', headers=headers_a)
        assert r.status_code == 200
        data = r.get_json()
        refs = {v['reference'] for v in data['ventes']}
        assert 'VA' in refs
        assert 'VB' not in refs

    def test_cross_tenant_commandes_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            cf_b = CommandeAchat(fournisseur_id=f_b.id, tenant_id=tb.id, reference='CF-B', total_ht=100, total_ttc=120)
            db.session.add(cf_b)
            db.session.commit()
            cfid_b = cf_b.id

        r = client.get(f'/api/v1/fournisseurs/commandes/{cfid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_factures_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            ff_b = FactureFournisseur(fournisseur_id=f_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FF-B')
            db.session.add(ff_b)
            db.session.commit()
            ffid_b = ff_b.id

        r = client.get(f'/api/v1/fournisseurs/factures/{ffid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_create_without_tenant_id_is_rejected(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            from app.services.client_service import ClientService
            with pytest.raises(ValueError, match='Aucun tenant associe'):
                ClientService.create({'code': 'CLI-NO-TENANT', 'nom': 'Orphelin'})

    def test_create_with_valid_tenant_id_succeeds(self, app):
        ta, _, admin_a, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/clients', json={
            'code': 'CLI-OK',
            'nom': 'Client OK',
            'prenom': 'Test'
        }, headers=headers)
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id

    def test_super_admin_without_tenant_id_works(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/clients', headers=headers)
        assert r.status_code == 200

    def test_tenant_resolution_failure_is_logged(self, app, monkeypatch, caplog):
        import logging
        from app.security import tenant as tenant_module

        def bad_resolve():
            raise RuntimeError('header cassé')

        monkeypatch.setattr(tenant_module, 'resolve_tenant_from_header', bad_resolve)

        with caplog.at_level(logging.WARNING, logger='app'):
            client = app.test_client()
            client.get('/api/v1/auth/login', json={'username': 'x', 'password': 'y'})

        assert any('Impossible de résoudre le tenant' in record.getMessage() for record in caplog.records)
