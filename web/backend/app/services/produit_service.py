from app import db
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple

class ProduitService:
    model = Produit

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_code_barre(cls, code_barre):
        query = cls.model.query.filter_by(code_barre=code_barre, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

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
    def search(cls, query, fields):
        if not query:
            return []
        conditions = []
        for field in fields:
            if hasattr(cls.model, field):
                conditions.append(getattr(cls.model, field).ilike(f'%{query}%'))
        if conditions:
            from sqlalchemy import or_
            query_obj = cls.model.query.filter(
                cls.model.is_active == True,
                or_(*conditions)
            )
            query_obj = cls._get_tenant_filter(query_obj)
            return query_obj.limit(20).all()
        return []

    @classmethod
    def count(cls, filters=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        return query.count()

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
