from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    # Create tables
    db.create_all()
    
    # Create default tenant (skip if auto-seed already created it)
    existing = Tenant.query.filter_by(slug='demo-seed').first()
    if existing:
        tenant = existing
    else:
        tenant = Tenant(
            nom='ERP Démonstration',
            slug='demo-seed',
            domaine='seed.local',
            statut=StatutTenant.ACTIF,
            plan='pro',
            devise='MGA',
            langue='mg',
            max_utilisateurs=20,
            max_produits=1000,
            max_clients=500,
        )
        db.session.add(tenant)
        db.session.commit()
    print(f"Tenant créé: {tenant.nom} (ID: {tenant.id})")
    
    # Create admin (skip if auto-seed already created it)
    existing_admin = Utilisateur.query.filter_by(username='admin-seed').first()
    if not existing_admin:
        admin = Utilisateur(
            username='admin-seed',
            email='admin-seed@demo.com',
            password_hash=hash_password('Test1234!'),
            nom='Administrateur',
            prenom='System',
            role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant.id,
        )
        db.session.add(admin)
        db.session.commit()
    else:
        admin = existing_admin
    print(f"Admin créé: {admin.username}")
    
    # Create sample products
    produits = [
        Produit(
            nom='Riz blanc (sac 50 kg)',
            reference='PROD-001',
            prix_achat_ht=102000.0,
            prix_vente_ht=130000.0,
            quantite_stock=120,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Huile de tournesol (carton 6 x 1 L)',
            reference='PROD-002',
            prix_achat_ht=124000.0,
            prix_vente_ht=160000.0,
            quantite_stock=35,
            categorie='Épicerie',
            unite='carton',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Eau minérale (pack 6 x 1,5 L)',
            reference='PROD-003',
            prix_achat_ht=5200.0,
            prix_vente_ht=7500.0,
            quantite_stock=500,
            categorie='Boissons',
            unite='pack',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Savon de toilette (carton 72)',
            reference='PROD-004',
            prix_achat_ht=66000.0,
            prix_vente_ht=85000.0,
            quantite_stock=25,
            categorie='Hygiène',
            unite='carton',
            tenant_id=tenant.id,
        ),
    ]
    
    for produit in produits:
        db.session.add(produit)
    db.session.commit()
    print("Produits d'exemple créés")
    
    # Create a sale with lines
    from app.models.client import Client
    client = Client(
        code='CLI-001',
        nom='Test Client',
        tenant_id=tenant.id,
        is_active=True,
        est_actif=True,
    )
    db.session.add(client)
    db.session.commit()
    
    from app.models.vente import Vente
    from app.models.ligne_vente import LigneVente
    
    # Create a sale
    vente = Vente(
        reference='TEST-001',
        client_id=client.id,
        total_ht=26000.0,
        total_ttc=28600.0,
        statut='payee',
        tenant_id=tenant.id,
    )
    db.session.add(vente)
    db.session.commit()
    
    # Create line
    ligne = LigneVente(
        vente_id=vente.id,
        produit_id=produits[0].id,
        quantite=2,
        prix_unitaire_ht=13000.0,
        taux_tva=10.00,
    )
    db.session.add(ligne)
    db.session.commit()
    
    # Update produit stock
    produit = Produit.query.filter_by(id=produits[0].id).first()
    produit.retirer_stock(2)
    db.session.commit()
    
    print("\n=== Vérification des calculs ===")
    
    # Check CA from Ventes
    from sqlalchemy import func
    ca_query = db.session.query(func.sum(Vente.total_ttc)).filter(Vente.is_active == True, Vente.tenant_id == tenant.id)
    ca_result = ca_query.scalar() or 0
    print(f"CA total (somme des ventes TTC): {ca_result}")
    
    # Check individual ventes
    ventes = Vente.query.filter_by(is_active=True, tenant_id=tenant.id).all()
    ventes_sum = sum(float(v.total_ttc) for v in ventes)
    print(f"Somme des total_ttc des ventes: {ventes_sum}")
    print(f"Écart: {abs(ca_result - ventes_sum)}")
    
    # Check stock values
    produits_db = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
    print(f"\nValeur des stocks:")
    stock_total = 0
    for p in produits_db:
        stock_val = float(p.quantite_stock * p.prix_achat_ht)
        stock_total += stock_val
        print(f"  {p.nom}: quantité={p.quantite_stock}, prix_achat_ht={float(p.prix_achat_ht)}, valeur={stock_val}")
    print(f"Total stock: {stock_total}")
    
    # Check creances calculation
    from app.models.facture import Facture
    from app.models.paiement import Paiement
    
    # Create a facture from the vente
    from app.services.facturation_service import generate_from_vente
    facture = generate_from_vente(vente.id)
    if facture:
        print(f"\nFacture créée: {facture.id}, total_ttc={facture.total_ttc}")
        
        # Create a payment
        paiement = Paiement(
            facture_id=facture.id,
            montant=facture.total_ttc,
            devise='MGA',
            statut='confirme',
            type='vente',
            reference='TEST-PAYMENT',
            notes='Payment test',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant.id,
        )
        db.session.add(paiement)
        db.session.commit()
        print(f"Paiement créé: {paiement.id}, montant={paiement.montant}")
        
        # Check remaining balance
        remaining = float(facture.total_ttc) - float(paiement.montant)
        print(f"Reste à payer: {remaining}")
    
    print("\n=== Vérification de l'isolation multi-tenant ===")
    
    # Create another tenant to verify isolation
    tenant2 = Tenant(
        nom='Autre Tenant',
        slug='other',
        domaine='other.local',
        statut=StatutTenant.ACTIF,
        plan='pro',
    )
    db.session.add(tenant2)
    db.session.commit()
    
    # Create product for second tenant
    produit2 = Produit(
        nom='Produit Autre',
        reference='PROD-005',
        prix_achat_ht=5000.0,
        prix_vente_ht=7500.0,
        quantite_stock=10,
        categorie='Test',
        unite='piece',
        tenant_id=tenant2.id,
    )
    db.session.add(produit2)
    db.session.commit()
    
    # Verify isolation
    produits_tenant1 = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
    produits_tenant2 = Produit.query.filter_by(tenant_id=tenant2.id, is_active=True).all()
    print(f"Produits tenant 1: {len(produits_tenant1)}")
    print(f"Produits tenant 2: {len(produits_tenant2)}")
    print(f"Produit 2 dans tenant 1: {produit2 in produits_tenant1}")
    
    db.session.rollback()
    print("\nTerminé!")