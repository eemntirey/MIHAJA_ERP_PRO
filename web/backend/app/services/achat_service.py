from app import db
from app.models.commande_achat import CommandeAchat, ReceptionAchat, QualiteAchat
from app.models.ligne_achat import LigneAchat
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple

class CommandeAchatService:
    model = CommandeAchat

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
        lignes_data = data.pop('lignes', [])
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.flush()
        total_ht = 0
        total_ttc = 0
        for ligne in lignes_data:
            ligne['commande_achat_id'] = instance.id
            if tenant_id:
                ligne['tenant_id'] = tenant_id
            ligne_obj = LigneAchat(**ligne)
            db.session.add(ligne_obj)
            total_ht += float(ligne_obj.total_ht or 0)
            total_ttc += float(ligne_obj.total_ht or 0) * (1 + float(ligne.get('taux_tva', 20)) / 100)
        instance.total_ht = total_ht
        instance.total_ttc = total_ttc
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        lignes_data = data.pop('lignes', None)
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        if lignes_data is not None:
            LigneAchat.query.filter_by(commande_achat_id=id, is_active=True).update({'is_active': False})
            total_ht = 0
            total_ttc = 0
            for ligne in lignes_data:
                ligne['commande_achat_id'] = id
                ligne_obj = LigneAchat(**ligne)
                db.session.add(ligne_obj)
                total_ht += float(ligne_obj.total_ht or 0)
                total_ttc += float(ligne_obj.total_ht or 0) * (1 + float(ligne.get('taux_tva', 20)) / 100)
            instance.total_ht = total_ht
            instance.total_ttc = total_ttc
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class ReceptionAchatService:
    model = ReceptionAchat

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
