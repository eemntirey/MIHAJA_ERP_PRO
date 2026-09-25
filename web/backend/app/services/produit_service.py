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
            cls._set_stock_absolu(produit, quantite, type_mouvement, raison, utilisateur_id)
        return produit

    @classmethod
    def _set_stock_absolu(cls, produit, quantite, type_mouvement, raison='', utilisateur_id=None):
        """Fixe le stock à une valeur absolue en traçant le mouvement.

        Utilisé pour les types ``inventaire``, ``ajustement``, ``retour`` et
        ``transfert`` : contrairement aux entrées/sorties, la quantité fournie
        est la nouvelle quantité en stock. Le mouvement est historisé comme
        pour les entrées/sorties afin que l'écran « Mouvements » et l'audit
        restent exploitables (avant correctif, le stock changeait sans trace).
        """
        from decimal import Decimal
        from app.models.stock import MouvementStock, TypeMouvement

        type_value = (
            type_mouvement.value if hasattr(type_mouvement, 'value') else str(type_mouvement)
        )
        types_valides = {t.value for t in TypeMouvement}
        if type_value not in types_valides:
            raise ValueError(
                'Type de mouvement invalide: {0}. Attendu: {1}'.format(
                    type_mouvement, ', '.join(sorted(types_valides))
                )
            )

        try:
            nouvelle_quantite = Decimal(str(quantite))
        except Exception:
            raise ValueError('Quantite invalide')
        if nouvelle_quantite < 0:
            raise ValueError('La quantite ne peut pas etre negative')

        stock_avant = Decimal(str(produit.quantite_stock or 0))
        produit.quantite_stock = nouvelle_quantite
        produit.save()

        mouvement = MouvementStock(
            produit_id=produit.id,
            type_mouvement=type_value,
            quantite=nouvelle_quantite,
            stock_avant=stock_avant,
            stock_apres=nouvelle_quantite,
            raison=raison,
            created_by=utilisateur_id,
            tenant_id=produit.tenant_id,
        )
        mouvement.save()
        return mouvement

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
        from sqlalchemy import func
        stats = query.with_entities(
            func.count(cls.model.id),
            func.coalesce(func.sum(cls.model.quantite_stock), 0),
            func.coalesce(
                func.sum(cls.model.quantite_stock * cls.model.prix_achat_ht), 0
            ),
        ).one()
        return {
            'total_produits': int(stats[0] or 0),
            'total_stock': float(stats[1] or 0),
            'valeur_stock': float(stats[2] or 0),
        }
