from app import create_app, db
from app.models.produit import Produit
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant

app = create_app()

with app.app_context():
    tenants = Tenant.query.all()
    count = 0
    for tenant in tenants:
        user = Utilisateur.query.filter_by(tenant_id=tenant.id, is_active=True).first()
        if not user:
            continue
        for i in range(1, 4):
            produit = Produit(
                tenant_id=tenant.id,
                reference=f"{tenant.slug or tenant.id}-{i}",
                code_barre=f"{tenant.id}-{i}",
                nom=f"Produit {tenant.nom} #{i}",
                description_courte=f"Description du produit {i} pour {tenant.nom}",
                prix_achat_ht=10 + i * 2,
                prix_vente_ht=20 + i * 5,
                quantite_stock=50,
                seuil_alerte=5,
                created_by=user.id,
                updated_by=user.id,
            )
            db.session.add(produit)
            count += 1
    db.session.commit()
    print(f'{count} produits créés pour {len(tenants)} tenants')
