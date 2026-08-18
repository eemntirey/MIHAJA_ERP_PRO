from app import db
from app.models.compte_comptable import CompteComptable
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from sqlalchemy import func

class CompteComptableService:
    model = CompteComptable

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
        query = cls.model.query.filter_by(is_active=True, id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_numero(cls, numero):
        query = cls.model.query.filter_by(is_active=True, numero=numero)
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

class EcritureComptableService:
    model = EcritureComptable

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
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
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
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
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
    def valider_ecriture(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        instance.statut = StatutEcriture.VALIDE
        db.session.commit()
        return instance

    @classmethod
    def annuler_ecriture(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        annulation = EcritureComptable(
            date=date.today(),
            compte_id=instance.compte_id,
            montant_debit=instance.montant_credit,
            montant_credit=instance.montant_debit,
            libelle=f"Annulation de {instance.libelle}",
            reference_externe=instance.reference_externe,
            entite_type=instance.entite_type,
            entite_id=instance.entite_id,
            statut=StatutEcriture.ANNULE,
            ecriture_annulee_id=instance.id,
            tenant_id=instance.tenant_id,
        )
        db.session.add(annulation)
        instance.statut = StatutEcriture.ANNULE
        db.session.commit()
        return annulation

class TresorerieService:
    model = Tresorerie

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
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
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
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        db.session.commit()
        return True

    @classmethod
    def get_solde(cls, date_debut=None, date_fin=None):
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True).filter_by(tenant_id=tenant_id) if tenant_id else cls.model.query
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        entrees = query.filter(cls.model.type_operation == 'entree').with_entities(func.sum(cls.model.montant)).scalar() or 0
        sorties = query.filter(cls.model.type_operation == 'sortie').with_entities(func.sum(cls.model.montant)).scalar() or 0
        return float(entrees) - float(sorties)


class ComptaImportService:
    @classmethod
    def import_comptes(cls, file):
        from app.utils.compta_import import import_comptes_from_file
        return import_comptes_from_file(file)

    @classmethod
    def import_ecritures(cls, file):
        from app.utils.compta_import import import_ecritures_from_file
        return import_ecritures_from_file(file)

    @classmethod
    def import_tresorerie(cls, file):
        from app.utils.compta_import import import_tresorerie_from_file
        return import_tresorerie_from_file(file)
