from app.models.commande_client import CommandeClient
from app.services.base_service import BaseService
from app import db
from app.security.tenant import get_current_tenant_id
from datetime import datetime
import random
import string
import json

class CommandeService(BaseService):
    model = CommandeClient
    
    @classmethod
    def _generate_reference(cls):
        prefix = 'CMD'
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @classmethod
    def create_commande(cls, data):
        from app.models.produit import Produit

        reference = cls._generate_reference()
        while CommandeClient.query.filter_by(reference=reference).first():
            reference = cls._generate_reference()

        # Support both flat fields and a nested "client" object (frontend Checkout)
        client = data.get('client') or {}

        def _field(flat_key, nested_key, default=None):
            if data.get(flat_key) is not None:
                return data.get(flat_key)
            if client.get(nested_key) is not None:
                return client.get(nested_key)
            return default

        nom_client = _field('nom_client', 'nom')
        prenom_client = _field('prenom_client', 'prenom')
        email_client = _field('email_client', 'email')
        telephone_client = _field('telephone_client', 'telephone', '')
        adresse_livraison = _field('adresse_livraison', 'adresse', '')
        ville_livraison = _field('ville_livraison', 'ville', '')
        code_postal_livraison = _field('code_postal_livraison', 'code_postal', '')
        pays_livraison = data.get('pays_livraison') or client.get('pays') or 'Madagascar'

        if not nom_client or not email_client:
            raise ValueError("nom_client et email_client sont requis")

        items = data.get('items', [])
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Le panier doit contenir au moins un article")

        # Validate and collect products by produit_id
        validated_items = []
        total_ht = 0
        total_ttc = 0
        tenant_id = data.get('tenant_id')
        
        for idx, item in enumerate(items):
            produit_id = item.get('produit_id')
            if not produit_id:
                raise ValueError(f"Article {idx + 1}: produit_id requis")
            
            produit = db.session.get(Produit, produit_id)
            if not produit:
                raise ValueError(f"Article {idx + 1}: Produit avec ID {produit_id} introuvable")
            
            if not produit.is_active:
                raise ValueError(f"Article {idx + 1}: Produit '{produit.nom}' n'est pas actif")
            
            # Ensure all products belong to the same tenant
            if tenant_id is not None and produit.tenant_id != tenant_id:
                raise ValueError(f"Article {idx + 1}: Produit '{produit.nom}' n'appartient pas au tenant de la commande")
            
            # Propagate tenant from first product if not provided
            if tenant_id is None:
                tenant_id = produit.tenant_id
            
            quantite = item.get('quantite', 1)
            if not isinstance(quantite, (int, float)) or quantite <= 0:
                raise ValueError(f"Article {idx + 1}: Quantité invalide pour '{produit.nom}'")
            
            # Check stock availability
            if produit.quantite_stock is not None and produit.quantite_stock < quantite:
                raise ValueError(f"Article {idx + 1}: Stock insuffisant pour '{produit.nom}' (disponible: {produit.quantite_stock}, demandé: {quantite})")
            
            tva = float(produit.taux_tva) if produit.taux_tva else 20.0
            total_ht += float(produit.prix_vente_ht) * quantite
            total_ttc += float(produit.prix_vente_ht) * (1 + tva / 100) * quantite
            
            # Store validated item with product details
            validated_items.append({
                'produit_id': produit.id,
                'nom': produit.nom,
                'reference': produit.reference,
                'quantite': quantite,
                'prix_unitaire_ht': float(produit.prix_vente_ht),
                'taux_tva': tva,
                'total_ht': float(produit.prix_vente_ht) * quantite,
                'total_ttc': float(produit.prix_vente_ht) * (1 + tva / 100) * quantite,
            })

        commande = CommandeClient(
            reference=reference,
            nom_client=nom_client,
            prenom_client=prenom_client,
            email_client=email_client,
            telephone_client=telephone_client,
            adresse_livraison=adresse_livraison,
            ville_livraison=ville_livraison,
            code_postal_livraison=code_postal_livraison,
            pays_livraison=pays_livraison,
            items=json.dumps(validated_items),
            total_ht=total_ht,
            total_ttc=total_ttc,
            tenant_id=tenant_id,
            notes=data.get('notes')
        )
        
        db.session.add(commande)
        db.session.commit()
        return commande
    
    @classmethod
    def get_by_reference(cls, reference):
        tenant_id = get_current_tenant_id()
        query = CommandeClient.query.filter_by(reference=reference, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.first()
    
    @classmethod
    def get_by_tenant(cls, tenant_id, page=1, per_page=20):
        query = CommandeClient.query.filter_by(tenant_id=tenant_id, is_active=True)
        paginated = query.order_by(CommandeClient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total
