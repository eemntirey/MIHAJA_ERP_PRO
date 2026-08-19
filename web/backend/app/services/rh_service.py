from app import db
from app.models.employe import Employe
from app.models.presence import Presence
from app.models.salaire import Salaire, StatutPaiementSalaire
from app.models.prime import Prime
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func

class EmployeService:
    model = Employe

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

class PresenceService:
    model = Presence

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
    def get_by_employe_date(cls, employe_id, date_val):
        query = cls.model.query.filter_by(is_active=True).filter_by(employe_id=employe_id, date=date_val)
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
        db.session.delete(instance)
        db.session.commit()
        return True

    @classmethod
    def get_registre(cls, mois=None, annee=None):
        """Registre des présences pour un mois donné (ou le mois courant)."""
        if not mois or not annee:
            today = date.today()
            mois = today.month
            annee = today.year
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        query = query.filter(db.extract('month', cls.model.date) == mois,
                             db.extract('year', cls.model.date) == annee)
        presences = query.order_by(cls.model.employe_id, cls.model.date).all()
        result = []
        for p in presences:
            d = p.to_dict()
            if (not d.get('heures_travaillees') or float(d.get('heures_travaillees') or 0) == 0) \
                    and p.heure_arrivee and p.heure_depart:
                delta = (p.heure_depart - p.heure_arrivee)
                pause = Decimal('0')
                if p.heure_pause_debut and p.heure_pause_fin:
                    pause = p.heure_pause_fin - p.heure_pause_debut
                heures = (delta.total_seconds() - pause.total_seconds()) / 3600.0
                p.heures_travaillees = Decimal(str(round(heures, 2)))
                db.session.commit()
                d['heures_travaillees'] = float(p.heures_travaillees)
            result.append(d)
        return result

    @classmethod
    def get_registre_export(cls, mois=None, annee=None):
        """Produit un export CSV du registre de présence."""
        presences = cls.get_registre(mois, annee)
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['date', 'employe_id', 'employe_nom', 'heure_arrivee', 'heure_depart',
                         'heures_travaillees', 'heures_supplementaires', 'statut', 'remarque'])
        for p in presences:
            writer.writerow([
                (p.get('date') or '')[:10],
                p.get('employe_id', '') or '',
                p.get('employe_nom', '') or '',
                p.get('heure_arrivee', '') or '',
                p.get('heure_depart', '') or '',
                p.get('heures_travaillees', '') or '',
                p.get('heures_supplementaires', '') or '',
                p.get('statut', '') or '',
                p.get('remarque', '') or '',
            ])
        return buf.getvalue()


class SalaireService:
    model = Salaire

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
    def get_by_employe_mois(cls, employe_id, mois, annee):
        query = cls.model.query.filter_by(is_active=True).filter_by(employe_id=employe_id, mois=mois, annee=annee)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        instance.calculer_salaire()
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
        instance.calculer_salaire()
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
    def generate_salaries(cls, mois, annee):
        tenant_id = get_current_tenant_id()
        employes = Employe.query.filter_by(is_active=True, statut='actif').filter_by(tenant_id=tenant_id).all() if tenant_id else Employe.query.filter_by(is_active=True, statut='actif').all()
        results = []
        for employe in employes:
            existing = Salaire.query.filter_by(employe_id=employe.id, mois=mois, annee=annee, is_active=True).first()
            if existing:
                continue
            primes_mois = Prime.query.filter_by(employe_id=employe.id, is_active=True).filter(
                func.extract('month', Prime.date_octroi) == mois,
                func.extract('year', Prime.date_octroi) == annee
            ).all()
            total_primes = sum(float(p.montant) for p in primes_mois)
            salaire = Salaire(
                employe_id=employe.id,
                mois=mois,
                annee=annee,
                salaire_base=employe.salaire_base or 0,
                primes=total_primes,
                indemnites=0,
                deductions=0,
                avances=0,
                tenant_id=tenant_id,
            )
            salaire.calculer_salaire()
            db.session.add(salaire)
            results.append(salaire)
        db.session.commit()
        return results

    @classmethod
    def marquer_paye(cls, id, statut_paiement=None, mode_paiement=None, reference_paiement=None, date_paiement=None):
        """Marque un bulletin de salaire comme payé (ou modifie le statut de paiement)."""
        instance = cls.get_by_id(id)
        if not instance:
            return None
        if statut_paiement is not None:
            instance.statut_paiement = statut_paiement if not hasattr(statut_paiement, 'value') else statut_paiement.value
        if mode_paiement is not None:
            instance.mode_paiement = mode_paiement
        if reference_paiement is not None:
            instance.reference_paiement = reference_paiement
        if statut_paiement in ('paye', StatutPaiementSalaire.PAYE, 'PAYE') and instance.date_paiement is None:
            instance.date_paiement = date_paiement or date.today()
        instance.calculer_salaire()
        db.session.commit()
        db.session.refresh(instance)
        return instance

    @classmethod
    def get_by_employe(cls, employe_id, mois=None, annee=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if employe_id:
            query = query.filter_by(employe_id=employe_id)
        if mois:
            query = query.filter_by(mois=mois)
        if annee:
            query = query.filter_by(annee=annee)
        return query.order_by(cls.model.annee.desc(), cls.model.mois.desc()).all()

    @classmethod
    def export_csv(cls, records, headers):
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in records:
            writer.writerow([row.get(h, '') for h in headers])
        return output.getvalue()

class PrimeService:
    model = Prime

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
