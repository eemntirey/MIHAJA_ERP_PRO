import sys
sys.path.insert(0, 'web/backend')
from app import create_app, db

app = create_app()
with app.app_context():
    # Create all tables
    db.create_all()
    
    # Clear existing data
    from app.models.produit import Produit
    Produit.query.delete()
    db.session.commit()
    
    # Run seed_produits_demo
    from scripts.seed_produits_demo import app as seed_app
    print("Seed produits demo completed")
    
    # Verify products
    products = Produit.query.all()
    print(f"Total products: {len(products)}")
    for p in products[:3]:
        print(f"  {p.nom} | Cat: {p.categorie} | Unite: {p.unite} | Achat: {p.prix_achat_ht} Ar | Vente: {p.prix_vente_ht} Ar | Stock: {p.quantite_stock}")
    
    # Check tenant count
    from app.models.tenant import Tenant
    tenants = Tenant.query.all()
    print(f"Total tenants: {len(tenants)}")
    for t in tenants:
        print(f"  {t.nom} - {t.ville} - {t.plan}")