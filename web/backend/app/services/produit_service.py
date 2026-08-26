from app import db
from app.models.produit import Produit
from app.services.base_service import BaseService
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple

class ProduitService(BaseService):
    model = Produit

    @classmethod
    def create(cls, data):
        return super().create(data)

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def update_stock(cls, id, quantite, type_mouvement='entree', raison='', utilisateur_id=None):
        produit = cls.get_by_id(id)
        if not produit:
            return None
        if type_mouvement == 'entree':
            produit.ajouter_stock(quantite, raison, utilisateur_id)
        elif type_mouvement == 'sortie':
            produit.retirer_stock(quantite, raison, utilisateur_id)
        else:
            produit.quantite_stock = quantite
            produit.save()
        return produit

    @classmethod
    def get_stock_alert(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        return query.filter(cls.model.quantite_stock <= cls.model.seuil_alerte).all()

    @classmethod
    def get_categories(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        categories = query.with_entities(cls.model.categorie).distinct().all()
        return [c[0] for c in categories if c[0]]

    @classmethod
    def get_statistiques(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        produits = query.all()
        total_produits = len(produits)
        total_stock = sum(float(p.quantite_stock) for p in produits)
        valeur_stock = sum(float(p.valeur_stock) for p in produits)
        return {
            'total_produits': total_produits,
            'total_stock': total_stock,
            'valeur_stock': valeur_stock,
        }
