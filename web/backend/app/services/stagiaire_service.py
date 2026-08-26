from app import db
from app.models.stagiaire import Stagiaire
from app.models.employe import Employe
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class StagiaireService:
    model = Stagiaire

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def _validate_tuteur(cls, tuteur_id):
        if not tuteur_id:
            return None
        tenant_id = get_current_tenant_id()
        tuteur = Employe.query.filter_by(id=tuteur_id, is_active=True)
        if tenant_id is not None:
            tuteur = tuteur.filter_by(tenant_id=tenant_id)
        return tuteur.first()

    @classmethod
    def _coerce_dates(cls, data):
        date_fields = ['date_naissance', 'date_debut', 'date_fin']
        for key in date_fields:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                try:
                    data[key] = datetime.strptime(val.strip(), '%Y-%m-%d').date()
                except ValueError:
                    data[key] = None
            elif val == '' or val is None:
                data[key] = None
        return data

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
        query = cls.model.query.filter_by(is_active=True, id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_matricule(cls, matricule):
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True, matricule=matricule)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        data = cls._coerce_dates(data)
        tuteur_id = data.get('tuteur_id')
        if tuteur_id:
            tuteur = cls._validate_tuteur(tuteur_id)
            if not tuteur:
                raise ValueError("Le tuteur selectionne n'appartient pas au tenant courant ou est introuvable.")
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        data = cls._coerce_dates(data)
        tuteur_id = data.get('tuteur_id')
        if tuteur_id is not None:
            tuteur = cls._validate_tuteur(tuteur_id)
            if not tuteur:
                raise ValueError("Le tuteur selectionne n'appartient pas au tenant courant ou est introuvable.")
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
