from app import db
from app.models.devis_avoir_bl import Devis, BonLivraison, Avoir
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
import datetime

def _gen_reference(prefix):
    ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    return f'{prefix}-{ts}'

class DevisService:
    model = Devis

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
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('DEV')
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
    def convertir_en_vente(cls, devis_id):
        devis = cls.get_by_id(devis_id)
        if not devis:
            return None
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        vente = Vente(
            client_id=devis.client_id,
            commercial_id=devis.commercial_id,
            total_ht=devis.total_ht,
            total_ttc=devis.total_ttc,
            mode_paiement='especes',
            statut='en_attente',
            tenant_id=devis.tenant_id,
        )
        db.session.add(vente)
        db.session.flush()
        devis.statut = 'converti'
        db.session.commit()
        return vente

class BonLivraisonService:
    model = BonLivraison

    _PROTECTED_FIELDS = ('id', 'tenant_id', 'created_at', 'updated_at', 'is_active', 'created_by', 'updated_by', 'reference')
    _INT_FK_FIELDS = ('vente_id', 'client_id', 'livreur_id', 'vehicule_id')
    _DATETIME_FIELDS = ('date_emission', 'date_livraison_prevue', 'date_livraison_reelle')

    @classmethod
    def _sanitize_payload(cls, data):
        clean = {}
        unknown = []
        for key, value in (data or {}).items():
            if not hasattr(cls.model, key):
                unknown.append(key)
                continue
            if key in cls._PROTECTED_FIELDS:
                continue
            if key in cls._INT_FK_FIELDS:
                if value in ('', None):
                    clean[key] = None
                else:
                    try:
                        clean[key] = int(value)
                    except (TypeError, ValueError):
                        raise ValueError(f"{key} doit etre un entier")
            elif key in cls._DATETIME_FIELDS:
                if value in ('', None):
                    clean[key] = None
                else:
                    try:
                        clean[key] = datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                    except ValueError:
                        raise ValueError(f"{key} doit etre une date ISO 8601 valide")
            else:
                clean[key] = value
        if unknown:
            raise ValueError(f"Champs non autorises: {', '.join(unknown)}")
        return clean

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
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        clean = cls._sanitize_payload(data)
        if not clean.get('client_id'):
            raise ValueError("client_id est obligatoire")
        clean['tenant_id'] = tenant_id
        clean['reference'] = _gen_reference('BL')
        instance = cls.model(**clean)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        clean = cls._sanitize_payload(data)
        for key, value in clean.items():
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

class AvoirService:
    model = Avoir

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
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('AV')
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
