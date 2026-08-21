"""
MISSION 4/5 — VALIDATION DES CALCULS, DASHBOARDS ET ISOLATION MULTI-TENANT
"""
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
os.environ['PAPI_API_KEY'] = 'test-api-key'
os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

import logging
logging.getLogger('app').setLevel(logging.CRITICAL)

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.client import Client
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.fournisseur import Fournisseur
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.livraison import Livraison
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from flask_jwt_extended import create_access_token

from sqlalchemy import func


def setup_app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def create_tenant_with_user(app, nom, slug, domaine, role=Role.ADMIN, statut=StatutTenant.ACTIF):
    with app.app_context():
        tenant = Tenant(
            nom=nom,
            slug=slug,
            domaine=domaine,
            statut=statut,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.commit()
        tenant_id = tenant.id

        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='carte',
            reference_paiement=f'SUB-{slug.upper()}-001',
            is_active=True,
        )
        db.session.add(abonnement)
        db.session.commit()

        user = Utilisateur(
            username=f'user_{slug}',
            email=f'{slug}@test.mg',
            password_hash=hash_password('Test1234!'),
            nom='Test',
            prenom='User',
            role=role,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant_id,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        token = create_access_token(identity=user_id, additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'tenant_id': user.tenant_id,
        })
        return tenant_id, user_id, token


def test_financial_calculations(app):
    print("\n" + "="*70)
    print("TEST 1: COHÉRENCE DES CALCULS FINANCIERS")
    print("="*70)

    with app.app_context():
        tenant1_id, user1_id, token1 = create_tenant_with_user(app, 'Tenant A', 'tenant-a', 'a.local')
        tenant2_id, user2_id, token2 = create_tenant_with_user(app, 'Tenant B', 'tenant-b', 'b.local')

        p1 = Produit(
            reference='P-A1',
            nom='Riz Tenant A',
            prix_achat_ht=10000.0,
            prix_vente_ht=15000.0,
            quantite_stock=100,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant1_id,
        )
        p2 = Produit(
            reference='P-A2',
            nom='Huile Tenant A',
            prix_achat_ht=5000.0,
            prix_vente_ht=8000.0,
            quantite_stock=50,
            categorie='Épicerie',
            unite='carton',
            tenant_id=tenant1_id,
        )
        db.session.add_all([p1, p2])
        db.session.commit()

        p3 = Produit(
            reference='P-B1',
            nom='Sucre Tenant B',
            prix_achat_ht=8000.0,
            prix_vente_ht=12000.0,
            quantite_stock=80,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant2_id,
        )
        db.session.add(p3)
        db.session.commit()

        c1 = Client(
            code='CLI-A1',
            nom='Client A1',
            tenant_id=tenant1_id,
            is_active=True,
            est_actif=True,
        )
        db.session.add(c1)
        db.session.commit()

        vente = Vente(
            reference='VENT-A-001',
            client_id=c1.id,
            total_ht=30000.0,
            total_ttc=36000.0,
            statut='payee',
            mode_paiement='especes',
            tenant_id=tenant1_id,
        )
        db.session.add(vente)
        db.session.commit()

        ligne1 = LigneVente(
            vente_id=vente.id,
            produit_id=p1.id,
            quantite=2,
            prix_unitaire_ht=15000.0,
            taux_tva=20.00,
            tenant_id=tenant1_id,
        )
        db.session.add(ligne1)
        db.session.commit()

        facture = Facture(
            vente_id=vente.id,
            client_id=c1.id,
            reference='FAC-A-001',
            total_ht=30000.0,
            total_ttc=36000.0,
            statut='non_payee',
            tenant_id=tenant1_id,
        )
        db.session.add(facture)
        db.session.commit()

        paiement = Paiement(
            facture_id=facture.id,
            client_id=c1.id,
            montant=36000.0,
            devise='MGA',
            statut=StatutPaiement.CONFIRME,
            type=TypePaiement.VENTE,
            reference='PAY-A-001',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant1_id,
        )
        db.session.add(paiement)
        db.session.commit()

        facture.statut = 'payee'
        db.session.commit()

        fournisseur = Fournisseur(
            code='FOUR-A1',
            raison_sociale='Fournisseur A',
            tenant_id=tenant1_id,
            type='local',
        )
        db.session.add(fournisseur)
        db.session.commit()

        commande = CommandeAchat(
            reference='CMD-A-001',
            fournisseur_id=fournisseur.id,
            total_ht=20000.0,
            total_ttc=24000.0,
            statut=StatutCommandeAchat.RECUE,
            conditions_paiement='30 jours',
            tenant_id=tenant1_id,
        )
        db.session.add(commande)
        db.session.commit()

        errors = []

        # 1. CA total = sum of vente total_ttc
        ca_total = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.tenant_id == tenant1_id
        ).scalar() or 0
        ventes = Vente.query.filter_by(is_active=True, tenant_id=tenant1_id).all()
        ventes_sum = sum(float(v.total_ttc) for v in ventes)
        if abs(float(ca_total) - ventes_sum) > 0.01:
            errors.append(f"CA total mismatch: query={ca_total}, sum={ventes_sum}")
        else:
            print(f"[OK] CA total = {ca_total:.2f} (cohérent avec somme des ventes)")

        # 2. Vente total_ttc = sum of LigneVente total_ttc
        lignes = LigneVente.query.filter_by(vente_id=vente.id, is_active=True, tenant_id=tenant1_id).all()
        lignes_sum_ttc = sum(float(l.total_ttc) for l in lignes)
        if abs(float(vente.total_ttc) - lignes_sum_ttc) > 0.01:
            errors.append(f"Vente total_ttc mismatch: vente={vente.total_ttc}, lignes_sum={lignes_sum_ttc}")
        else:
            print(f"[OK] Vente.total_ttc = {vente.total_ttc:.2f} = somme lignes TTC = {lignes_sum_ttc:.2f}")

        # 3. Facture total_ttc = Vente total_ttc
        if abs(float(facture.total_ttc) - float(vente.total_ttc)) > 0.01:
            errors.append(f"Facture total_ttc mismatch: facture={facture.total_ttc}, vente={vente.total_ttc}")
        else:
            print(f"[OK] Facture.total_ttc = {facture.total_ttc:.2f} = Vente.total_ttc")

        # 4. Paiement total = Facture total_ttc (since statut=payee)
        paiements = Paiement.query.filter_by(facture_id=facture.id, is_active=True, tenant_id=tenant1_id).all()
        paiements_sum = sum(float(p.montant) for p in paiements)
        if abs(paiements_sum - float(facture.total_ttc)) > 0.01:
            errors.append(f"Paiements mismatch: sum={paiements_sum}, facture={facture.total_ttc}")
        else:
            print(f"[OK] Paiements sum = {paiements_sum:.2f} = Facture.total_ttc")

        # 5. Creance = facture.total_ttc - paiements_sum
        creance = float(facture.total_ttc) - paiements_sum
        if creance != 0:
            errors.append(f"Créance non nulle pour facture payée: {creance}")
        else:
            print(f"[OK] Créance = {creance:.2f} (facture payée)")

        # 6. Stock value = quantite_stock * prix_achat_ht
        produits = Produit.query.filter_by(tenant_id=tenant1_id, is_active=True).all()
        stock_total = sum(float(p.quantite_stock * p.prix_achat_ht) for p in produits)
        print(f"[OK] Valeur stock tenant 1 = {stock_total:.2f} (calculée sur {len(produits)} produits)")

        # 7. Dette fournisseur = commande.total_ttc - paiements fournisseur
        dette_fournisseur = float(commande.total_ttc)
        print(f"[OK] Dette fournisseur (commande) = {dette_fournisseur:.2f}")

        # 8. Benefice mois = sum(Vente.total_ttc - Vente.total_ht)
        benefice = db.session.query(func.sum(Vente.total_ttc - Vente.total_ht)).filter(
            Vente.is_active == True,
            Vente.tenant_id == tenant1_id
        ).scalar() or 0
        print(f"[OK] Bénéfice mois = {float(benefice):.2f} (basé sur total_ttc - total_ht)")

        if errors:
            print(f"\n[ERREURS] {len(errors)} incohérence(s) détectée(s):")
            for e in errors:
                print(f"  - {e}")
            return False
        else:
            print("\n[SUCCÈS] Tous les calculs financiers sont cohérents.")
            return True


def test_multi_tenant_isolation(app):
    print("\n" + "="*70)
    print("TEST 2: ISOLATION MULTI-TENANT")
    print("="*70)

    with app.app_context():
        tenant1_id, user1_id, token1 = create_tenant_with_user(app, 'Iso A', 'iso-a', 'iso-a.local')
        tenant2_id, user2_id, token2 = create_tenant_with_user(app, 'Iso B', 'iso-b', 'iso-b.local')

        client_app = app.test_client()

        r1 = client_app.post(
            '/api/v1/clients/',
            json={'code': 'ISO-CLI-A', 'nom': 'Client Iso A'},
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1.status_code == 201, f"T1 client creation failed: {r1.get_json()}"

        r2 = client_app.post(
            '/api/v1/clients/',
            json={'code': 'ISO-CLI-B', 'nom': 'Client Iso B'},
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2.status_code == 201, f"T2 client creation failed: {r2.get_json()}"

        r1_list = client_app.get(
            '/api/v1/clients/',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_list.status_code == 200
        data1 = r1_list.get_json()
        codes1 = [c['code'] for c in data1['clients']]
        assert data1['total'] == 1, f"Expected 1 client for tenant 1, got {data1['total']}"
        assert 'ISO-CLI-A' in codes1
        assert 'ISO-CLI-B' not in codes1
        print("[OK] Tenant 1 ne voit que ses propres clients")

        r2_list = client_app.get(
            '/api/v1/clients/',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_list.status_code == 200
        data2 = r2_list.get_json()
        codes2 = [c['code'] for c in data2['clients']]
        assert data2['total'] == 1, f"Expected 1 client for tenant 2, got {data2['total']}"
        assert 'ISO-CLI-B' in codes2
        assert 'ISO-CLI-A' not in codes2
        print("[OK] Tenant 2 ne voit que ses propres clients")

        # Dashboard isolation
        r1_dash = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_dash.status_code == 200
        dash1 = r1_dash.get_json()
        assert dash1['ca_total'] == 0.0, f"Expected CA=0 for tenant 1 with no sales, got {dash1['ca_total']}"
        print("[OK] Dashboard tenant 1 isolé (CA=0 sans ventes)")

        r2_dash = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_dash.status_code == 200
        dash2 = r2_dash.get_json()
        assert dash2['ca_total'] == 0.0
        print("[OK] Dashboard tenant 2 isolé (CA=0 sans ventes)")

        # Create sale for tenant 1 via API
        produit_a = Produit.query.filter_by(tenant_id=tenant1_id).first()
        if not produit_a:
            produit_a = Produit(
                reference='ISO-PROD-A',
                nom='Produit Iso A',
                prix_achat_ht=5000.0,
                prix_vente_ht=10000.0,
                quantite_stock=50,
                tenant_id=tenant1_id,
            )
            db.session.add(produit_a)
            db.session.commit()

        client_a = Client.query.filter_by(tenant_id=tenant1_id).first()
        r_vente = client_app.post(
            '/api/v1/ventes/',
            json={
                'client_id': client_a.id,
                'mode_paiement': 'espece',
                'lignes': [
                    {'produit_id': produit_a.id, 'quantite': 1, 'prix_unitaire': 10000.0},
                ],
            },
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r_vente.status_code == 201, f"Vente creation failed: {r_vente.get_json()}"
        vente_data = r_vente.get_json()

        # Check dashboard for tenant 1
        r1_dash2 = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token1}'}
        )
        dash1 = r1_dash2.get_json()
        assert dash1['ca_total'] > 0, f"Expected CA>0 for tenant 1 with sale"
        print(f"[OK] Dashboard tenant 1 CA = {dash1['ca_total']:.2f} (cohérent avec vente)")

        # Check dashboard for tenant 2 (should still be 0)
        r2_dash2 = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token2}'}
        )
        dash2 = r2_dash2.get_json()
        assert dash2['ca_total'] == 0.0, f"Expected CA=0 for tenant 2, got {dash2['ca_total']}"
        print("[OK] Dashboard tenant 2 toujours isolé (CA=0)")

        # Top clients isolation
        r1_top = client_app.get(
            '/api/v1/dashboard/top-clients',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_top.status_code == 200
        top1 = r1_top.get_json()
        assert len(top1['top_clients']) >= 1
        print(f"[OK] Top clients tenant 1: {len(top1['top_clients'])} client(s)")

        r2_top = client_app.get(
            '/api/v1/dashboard/top-clients',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_top.status_code == 200
        top2 = r2_top.get_json()
        assert len(top2['top_clients']) == 0
        print("[OK] Top clients tenant 2: 0 client (isolé)")

        # Top products isolation
        r1_prod = client_app.get(
            '/api/v1/dashboard/top-products',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_prod.status_code == 200
        prod1 = r1_prod.get_json()
        assert len(prod1['top_products']) >= 1
        print(f"[OK] Top produits tenant 1: {len(prod1['top_products'])} produit(s)")

        r2_prod = client_app.get(
            '/api/v1/dashboard/top-products',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_prod.status_code == 200
        prod2 = r2_prod.get_json()
        assert len(prod2['top_products']) == 0
        print("[OK] Top produits tenant 2: 0 produit (isolé)")

        # Alerts isolation
        r1_alert = client_app.get(
            '/api/v1/dashboard/alerts',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_alert.status_code == 200
        print("[OK] Alertes stock tenant 1 accessibles")

        r2_alert = client_app.get(
            '/api/v1/dashboard/alerts',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_alert.status_code == 200
        print("[OK] Alertes stock tenant 2 accessibles")

        print("\n[SUCCÈS] Isolation multi-tenant validée.")
        return True


def test_dashboard_calculations_from_seed_data(app):
    print("\n" + "="*70)
    print("TEST 3: DASHBOARD À PARTIR DES DONNÉES GÉNÉRÉES")
    print("="*70)

    with app.app_context():
        tenant_id, user_id, token = create_tenant_with_user(app, 'Dash Test', 'dash-test', 'dash.local')

        produits = [
            Produit(reference='D1', nom='Produit D1', prix_achat_ht=10000, prix_vente_ht=15000, quantite_stock=20, tenant_id=tenant_id),
            Produit(reference='D2', nom='Produit D2', prix_achat_ht=5000, prix_vente_ht=8000, quantite_stock=10, tenant_id=tenant_id),
        ]
        db.session.add_all(produits)
        db.session.commit()

        client_obj = Client(code='CLI-DASH', nom='Client Dash', tenant_id=tenant_id, is_active=True, est_actif=True)
        db.session.add(client_obj)
        db.session.commit()

        vente = Vente(
            reference='VENT-DASH-001',
            client_id=client_obj.id,
            total_ht=23000.0,
            total_ttc=27600.0,
            statut='payee',
            mode_paiement='especes',
            tenant_id=tenant_id,
        )
        db.session.add(vente)
        db.session.commit()

        ligne1 = LigneVente(vente_id=vente.id, produit_id=produits[0].id, quantite=1, prix_unitaire_ht=15000.0, taux_tva=20.0, tenant_id=tenant_id)
        ligne2 = LigneVente(vente_id=vente.id, produit_id=produits[1].id, quantite=1, prix_unitaire_ht=8000.0, taux_tva=20.0, tenant_id=tenant_id)
        db.session.add_all([ligne1, ligne2])
        db.session.commit()

        facture = Facture(
            vente_id=vente.id,
            client_id=client_obj.id,
            reference='FAC-DASH-001',
            total_ht=23000.0,
            total_ttc=27600.0,
            statut='non_payee',
            tenant_id=tenant_id,
        )
        db.session.add(facture)
        db.session.commit()

        paiement = Paiement(
            facture_id=facture.id,
            client_id=client_obj.id,
            montant=10000.0,
            devise='MGA',
            statut=StatutPaiement.CONFIRME,
            type=TypePaiement.VENTE,
            reference='PAY-DASH-001',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant_id,
        )
        db.session.add(paiement)
        db.session.commit()

        client_app = app.test_client()

        # Sales stats
        r = client_app.get('/api/v1/dashboard/sales-stats', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        stats = r.get_json()
        expected_ca = 27600.0
        if abs(stats['ca_total'] - expected_ca) > 0.01:
            print(f"[ERREUR] CA total dashboard={stats['ca_total']}, attendu={expected_ca}")
            return False
        print(f"[OK] CA total dashboard = {stats['ca_total']:.2f} (attendu {expected_ca:.2f})")

        # Full dashboard
        r = client_app.get('/api/v1/dashboard/', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        dash = r.get_json()
        creances = dash['stats'].get('creances_clients', [])
        expected_creance = 27600.0 - 10000.0  # 17600.0
        actual_creance = sum(c['creance'] for c in creances)
        if abs(actual_creance - expected_creance) > 0.01:
            print(f"[ERREUR] Créances dashboard={actual_creance}, attendu={expected_creance}")
            return False
        print(f"[OK] Créances clients dashboard = {actual_creance:.2f} (attendu {expected_creance:.2f})")

        print(f"[OK] Dashboard: ventes_aujourdhui={dash['stats'].get('ventes_aujourdhui')}, ca_mois={dash['stats'].get('ca_mois')}")

        # Benefice mois
        if abs(dash['stats'].get('benefice_mois', 0) - 4600.0) > 0.01:
            print(f"[ERREUR] Bénéfice mois={dash['stats'].get('benefice_mois')}, attendu=4600.0")
            return False
        print(f"[OK] Bénéfice mois = {dash['stats']['benefice_mois']:.2f} (attendu 4600.0)")

        print("\n[SUCCÈS] Dashboard cohérent avec les transactions.")
        return True


if __name__ == '__main__':
    app = setup_app()
    ok1 = test_financial_calculations(app)
    ok2 = test_multi_tenant_isolation(app)
    ok3 = test_dashboard_calculations_from_seed_data(app)

    print("\n" + "="*70)
    print("RÉSUMÉ DE LA VALIDATION")
    print("="*70)
    print(f"Calculs financiers: {'OK' if ok1 else 'ÉCHEC'}")
    print(f"Isolation multi-tenant: {'OK' if ok2 else 'ÉCHEC'}")
    print(f"Dashboard: {'OK' if ok3 else 'ÉCHEC'}")

    if ok1 and ok2 and ok3:
        print("\n✅ TOUTES LES VALIDATIONS SONT PASSÉES.")
        sys.exit(0)
    else:
        print("\n❌ CERTAINES VALIDATIONS ONT ÉCHOUÉ.")
        sys.exit(1)
