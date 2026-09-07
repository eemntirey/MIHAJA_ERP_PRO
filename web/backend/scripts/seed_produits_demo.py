from app import create_app, db
from app.models.produit import Produit
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant

app = create_app()

PRODUCT_NAMES_BY_CATEGORY = {
    'riz': [
        'Riz de première qualité',
        'Riz local premium',
        'Riz importé',
    ],
    'huile': [
        'Huile alimentaire 1L',
        'Huile de palme',
        'Huile végétale',
    ],
    'sucre': [
        'Sucre raffiné',
        'Sucre de canne',
        'Sucre blanc',
    ],
    'farine': [
        'Farine de blé',
        'Farine de maïs',
        'Farine de riz',
    ],
    'boissons': [
        'Eau minérale 16L',
        'Boisson gazeuse',
        'Jus de fruit',
    ],
    'biscuits': [
        'Biscuits assorted',
        'Biscuits au chocolat',
        'Biscuits beurre',
    ],
    'conserves': [
        'Conserves de poisson',
        'Conserves de légumes',
        'Conserves viande',
    ],
    'savon': [
        'Savon barre',
        'Savon liquide',
        'Savon antibactérien',
    ],
    'couches': [
        'Couches bébé taille 1',
        'Couches bébé taille 2',
        'Couches bébé taille 3',
    ],
    'entretien': [
        'Lessive poudre',
        'Détergent liquide',
        'Eau de Javel',
    ],
    'cosmetique': [
        'Crème visage',
        'Shampoing',
        'Démaquillant',
    ],
    'fournitures': [
        'Cahier scolaire',
        'Stylo plume',
        'Classeur',
    ],
}

CATEGORIES_MALAGASY = [
    'riz', 'huile', 'sucre', 'farine', 'boissons',
    'biscuits', 'conserves', 'savon', 'couches',
    'entretien', 'cosmetique', 'fournitures',
]

UNITS_MALAGASY = [
    'piece', 'bouteille', 'pack', 'carton', 'sachet',
    'paquet', 'caisse', 'sac', 'bidon', 'veau',
]

PRICE_RANGES = {
    'min': 500,
    'max': 500000,
}

def get_product_data(tenant_slug, category_idx, product_idx):
    category = CATEGORIES_MALAGASY[category_idx % len(CATEGORIES_MALAGASY)]
    product_names = PRODUCT_NAMES_BY_CATEGORY.get(category, ['Produit ' + category])
    nom = product_names[product_idx % len(product_names)]
    
    # Prix réalistes pour le marché malagasy
    base_price = 1000 + (product_idx * 3000 + tenant_slug.count('-') * 500)
    prix_achat_ht = min(base_price, PRICE_RANGES['max'])
    prix_vente_ht = round(prix_achat_ht * 1.5, 2)
    
    # Unités variées
    unite = UNITS_MALAGASY[product_idx % len(UNITS_MALAGASY)]
    
    # Stock diversifié
    quantite_stock = 10 + (product_idx * 25) + (hash(tenant_slug + category) % 40)
    seuil_alerte = max(1, 3 + (product_idx % 3))
    
    descriptions = {
        'riz': 'Riz de qualité supérieure, grain long, idéal pour la consommation quotidienne',
        'huile': 'Huile alimentaire premium, parfaite pour la cuisine',
        'sucre': 'Sucre raffiné, qualité alimentaire',
        'farine': 'Farine de première qualité, pour tous types de pâtisserie',
        'boissons': 'Eau minérale ou boissons rafraîchissantes',
        'biscuits': 'Biscuits délicieux, idéals pour le goûter',
        'conserves': 'Conserves de qualité, conserves prêtes à manger',
        'savon': 'Savon de qualité, pour l\'hygiène quotidienne',
        'couches': 'Couches bébé, confort et protection',
        'entretien': 'Produits d\'entretien ménager, efficacité garantie',
        'cosmetique': 'Produits de beauté et de soin de la peau',
        'fournitures': 'Fournitures de bureau, qualité scolaire',
    }
    
    desc = descriptions.get(category, 'Produit de qualité pour le commerce')
    
    return {
        'tenant_id': None,  # Set per tenant
        'reference': f"{tenant_slug.upper()}-{category[:3].upper()}-{product_idx+1:03d}",
        'code_barre': f"{tenant_slug}-{category[:3].upper()}-{product_idx+1:03d}",
        'nom': nom,
        'description_courte': desc,
        'categorie': category,
        'prix_achat_ht': prix_achat_ht,
        'prix_vente_ht': prix_vente_ht,
        'quantite_stock': quantite_stock,
        'seuil_alerte': seuil_alerte,
    }

with app.app_context():
    tenants = Tenant.query.all()
    count = 0
    for tenant in tenants:
        user = Utilisateur.query.filter_by(tenant_id=tenant.id, is_active=True).first()
        if not user:
            continue
        
        tenant_slug = tenant.slug or str(tenant.id)
        
        for i in range(1, 4):
            product_data = get_product_data(tenant_slug, i, i)
            product_data['tenant_id'] = tenant.id
            
            produit = Produit(
                tenant_id=tenant.id,
                reference=product_data['reference'],
                code_barre=product_data['code_barre'],
                nom=product_data['nom'],
                description_courte=product_data['description_courte'],
                categorie=product_data['categorie'],
                prix_achat_ht=product_data['prix_achat_ht'],
                prix_vente_ht=product_data['prix_vente_ht'],
                quantite_stock=product_data['quantite_stock'],
                seuil_alerte=product_data['seuil_alerte'],
                created_by=user.id,
                updated_by=user.id,
            )
            db.session.add(produit)
            count += 1
    
    db.session.commit()
    print(f'{count} produits créés pour {len(tenants)} tenants')
