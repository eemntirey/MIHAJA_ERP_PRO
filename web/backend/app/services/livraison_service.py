from app import db
from app.models.livreur import Livreur
from app.models.vehicule import Vehicule
from app.models.itineraire import Itineraire
from app.models.livraison import Livraison
from app.models.suivi_livraison import SuiviLivraison
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

# Workflow de suivi de statut (en_attente -> en_cours -> livree).
# La progression est unidirectionnelle : on ne recule pas d'un état terminal.
STATUTS_LIVRAISON = ['en_attente', 'chargee', 'en_cours', 'en_route', 'livree']
TERMINAUX = ['livree', 'retournee', 'echec']

# Transitions autorisées depuis chaque état (forward + états terminaux d'échec).
TRANSITIONS_AUTORISEES = {
    'en_attente': {'chargee', 'en_cours', 'en_route', 'livree', 'retournee', 'echec'},
    'chargee': {'en_cours', 'en_route', 'livree', 'retournee', 'echec'},
    'en_cours': {'en_route', 'livree', 'retournee', 'echec'},
    'en_route': {'livree', 'retournee', 'echec'},
    'livree': {'retournee'},
    'retournee': set(),
    'echec': set(),
}

class LivreurService:
    model = Livreur

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

class VehiculeService:
    model = Vehicule

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

class ItineraireService:
    model = Itineraire

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

class LivraisonService:
    model = Livraison

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
    def add_suivi(cls, livraison_id, statut, commentaire='', localisation_lat=None, localisation_lng=None):
        """Ajoute un événement de suivi et fait progresser le statut de la livraison.

        Le passage de statut est validé contre le workflow métier :
        en_attente -> chargee -> en_cours -> en_route -> livree
        (avec retour possibles vers retournee / echec).
        """
        livraison = cls.get_by_id(livraison_id)
        if not livraison:
            return None

        if statut not in TRANSITIONS_AUTORISEES:
            raise ValueError(f"Statut '{statut}' invalide")

        autorisés = TRANSITIONS_AUTORISEES.get(livraison.statut or 'en_attente', set())
        if statut not in autorisés:
            raise ValueError(
                f"Transition de statut invalide: '{livraison.statut}' -> '{statut}'. "
                f"Statuts autorisés: {sorted(autorisés) if autorisés else ['aucun']}"
            )

        suivi = SuiviLivraison(
            livraison_id=livraison_id,
            statut=statut,
            commentaire=commentaire,
            localisation_lat=localisation_lat,
            localisation_lng=localisation_lng,
            tenant_id=livraison.tenant_id,
        )
        db.session.add(suivi)
        livraison.statut = statut
        db.session.commit()
        db.session.refresh(suivi)
        return suivi

    @classmethod
    def assigner(cls, livraison_id, livreur_id, vehicule_id=None):
        """Assigne une livraison à un livreur (et éventuellement un véhicule)."""
        livraison = cls.get_by_id(livraison_id)
        if not livraison:
            return None
        livreur = LivreurService.get_by_id(livreur_id)
        if not livreur:
            raise ValueError(f"Livreur id={livreur_id} introuvable")
        if livreur.statut != 'actif':
            raise ValueError("Le livreur n'est pas actif")
        if vehicule_id:
            vehicule = VehiculeService.get_by_id(vehicule_id)
            if not vehicule:
                raise ValueError(f"Véhicule id={vehicule_id} introuvable")
        livraison.livreur_id = livreur_id
        if vehicule_id:
            livraison.vehicule_id = vehicule_id
        db.session.commit()
        db.session.refresh(livraison)
        return livraison

    @classmethod
    def passer_au_statut(cls, livraison_id, statut, commentaire='', localisation_lat=None, localisation_lng=None):
        """Alias métier pour faire progresser une livraison d'un cran (ou vers un statut cible valide)."""
        return cls.add_suivi(livraison_id, statut, commentaire, localisation_lat, localisation_lng)

    @classmethod
    def get_stats(cls):
        tenant_id = get_current_tenant_id()
        query = Livraison.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        livraisons = query.all()
        count = len(livraisons)
        by_statut = {}
        for l in livraisons:
            s = l.statut or 'en_attente'
            by_statut.setdefault(s, {'count': 0})
            by_statut[s]['count'] += 1
        return {
            'total': count,
            'by_statut': by_statut,
            'active_count': sum(1 for l in livraisons if l.statut in ('en_attente', 'chargee', 'en_cours', 'en_route')),
        }

    @classmethod
    def avancer_statut(cls, id):
        livraison = cls.get_by_id(id)
        if not livraison:
            return None
        flow = {
            'en_attente': 'chargee',
            'chargee': 'en_route',
            'en_route': 'livree',
        }
        next_status = flow.get(livraison.statut)
        if not next_status:
            return livraison
        livraison.statut = next_status
        db.session.commit()
        return livraison
