from app import db
from app.models.employe import Employe
from app.models.presence import Presence, StatutPresence
from app.models.conge import Conge, TypeConge, StatutConge
from app.models.salaire import Salaire, StatutPaiementSalaire
from app.models.prime import Prime
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True


class CongeService:
    model = Conge
    _AUTO_PRESENCE_PREFIX = 'Auto: conge #'

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
        else:
            query = query.order_by(cls.model.date_debut.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_solde(cls, employe_id, annee=None):
        """Crédit annuel, jours pris et solde restant pour un employé."""
        from app.models.employe import Employe as _Employe
        if annee is None:
            annee = date.today().year
        employe = _Employe.query.filter_by(is_active=True, id=employe_id).first()
        if employe is None:
            return None
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and employe.tenant_id != tenant_id:
            return None
        credit = int(employe.conges_credit_annuel) if employe.conges_credit_annuel else 30
        pris = db.session.execute(
            db.select(func.coalesce(func.sum(cls.model.nb_jours), 0))
            .where(
                cls.model.is_active == True,
                cls.model.employe_id == employe_id,
                cls.model.annee == annee,
                cls.model.statut == StatutConge.APPROUVE,
            )
        ).scalar()
        pris = int(pris or 0)
        return {
            'employe_id': employe_id,
            'employe_nom': employe.nom_complet,
            'annee': annee,
            'credit_annuel': credit,
            'jours_pris': pris,
            'solde_restant': max(credit - pris, 0),
        }

    @classmethod
    def _check_overlap(cls, employe_id, date_debut, date_fin, exclude_id=None, tenant_id=None):
        """Lève ValueError si un congé actif chevauche la période donnée."""
        if date_debut is None or date_fin is None:
            return
        query = cls.model.query.filter(
            cls.model.is_active == True,
            cls.model.employe_id == employe_id,
            cls.model.date_debut <= date_fin,
            cls.model.date_fin >= date_debut,
            cls.model.statut.in_([StatutConge.EN_ATTENTE, StatutConge.APPROUVE]),
        )
        if exclude_id is not None:
            query = query.filter(cls.model.id != exclude_id)
        if tenant_id is not None:
            query = query.filter(cls.model.tenant_id == tenant_id)
        if query.first():
            raise ValueError('Un congé chevauche déjà la période demandée pour cet employé')

    @classmethod
    def _normalize_dates(cls, data):
        for key in ('date_debut', 'date_fin'):
            if key in data and isinstance(data[key], str):
                data[key] = date.fromisoformat(data[key])

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        try:
            cls._check_overlap(data.get('employe_id'), date_debut, date_fin, tenant_id=tenant_id)
        except ValueError:
            raise
        if isinstance(date_debut, str):
            date_debut = date.fromisoformat(date_debut)
        if isinstance(date_fin, str):
            date_fin = date.fromisoformat(date_fin)
        data['date_debut'] = date_debut
        data['date_fin'] = date_fin
        data['nb_jours'] = Conge.calc_jours(date_debut, date_fin)
        data['annee'] = (date_debut or date.today()).year
        instance = cls.model(**data)
        db.session.add(instance)
        try:
            db.session.flush()
            cls._sync_auto_presences(instance)
            db.session.commit()
            db.session.refresh(instance)
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        old_statut = instance.statut
        old_debut = instance.date_debut
        old_fin = instance.date_fin
        merged = {}
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at', 'nb_jours', 'annee', 'created_by', 'updated_by'):
                merged[key] = value
        date_debut = merged.get('date_debut', old_debut)
        date_fin = merged.get('date_fin', old_fin)
        try:
            cls._check_overlap(
                instance.employe_id, date_debut, date_fin,
                exclude_id=instance.id, tenant_id=instance.tenant_id,
            )
        except ValueError:
            raise
        for key, value in merged.items():
            setattr(instance, key, value)
        instance.nb_jours = Conge.calc_jours(instance.date_debut, instance.date_fin)
        instance.annee = instance.date_debut.year
        try:
            db.session.flush()
            cls._sync_auto_presences(instance, previous=(old_statut, old_debut, old_fin))
            db.session.commit()
            db.session.refresh(instance)
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        cls._remove_auto_presences(instance)
        db.session.delete(instance)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True

    @classmethod
    def _is_approved(cls, instance):
        statut = getattr(instance, 'statut', None)
        if isinstance(statut, StatutConge):
            return statut == StatutConge.APPROUVE
        return str(statut) == 'approuve'

    @classmethod
    def _auto_marker(cls, conge_id):
        return f"{cls._AUTO_PRESENCE_PREFIX}{conge_id}"

    @classmethod
    def _sync_auto_presences(cls, instance, previous=None):
        """Approuver un congé génère les présences « Congé » de la période ;
        refus/annulation ou changement de période les retire.
        """
        now_approved = cls._is_approved(instance)
        prev_approved, prev_debut, prev_fin = previous or (now_approved, instance.date_debut, instance.date_fin)
        changed_dates = (instance.date_debut, instance.date_fin) != (prev_debut, prev_fin)

        if now_approved:
            if prev_approved and changed_dates:
                cls._remove_auto_presences(instance, marker=cls._auto_marker(instance.id))
                cls._create_auto_presences(instance)
            elif not prev_approved:
                cls._create_auto_presences(instance)
        elif prev_approved:
            cls._remove_auto_presences(instance, marker=cls._auto_marker(instance.id))

    @classmethod
    def _create_auto_presences(cls, instance):
        """Crée les lignes Presence (statut conge) pour chaque jour de la période,
        sans écraser un pointage déjà saisi le jour concerné."""
        if instance.date_debut is None or instance.date_fin is None:
            return
        if instance.id is None:
            db.session.flush()
        marker = cls._auto_marker(instance.id)
        current = instance.date_debut
        while current <= instance.date_fin:
            exists = Presence.query.filter_by(
                is_active=True, employe_id=instance.employe_id, date=current,
            ).first()
            if exists is None:
                presence = Presence(
                    employe_id=instance.employe_id,
                    date=current,
                    statut=StatutPresence.CONGE,
                    remarque=marker,
                    tenant_id=instance.tenant_id,
                )
                db.session.add(presence)
            current += timedelta(days=1)

    @classmethod
    def _remove_auto_presences(cls, instance, marker=None):
        """Supprime les lignes Presence générées automatiquement par ce congé."""
        marker = marker or cls._auto_marker(instance.id)
        try:
            db.session.flush()
        except Exception:
            pass
        Presence.query.filter(
            Presence.employe_id == instance.employe_id,
            Presence.remarque.like(f"{marker}%"),
            Presence.is_active == True,
        ).delete(synchronize_session=False)

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
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
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
        from app.utils.compta_import import _sanitize_csv_cell
        for p in presences:
            writer.writerow([
                (p.get('date') or '')[:10],
                _sanitize_csv_cell(str(p.get('employe_id', '') or '')),
                _sanitize_csv_cell(str(p.get('employe_nom', '') or '')),
                _sanitize_csv_cell(str(p.get('heure_arrivee', '') or '')),
                _sanitize_csv_cell(str(p.get('heure_depart', '') or '')),
                _sanitize_csv_cell(str(p.get('heures_travaillees', '') or '')),
                _sanitize_csv_cell(str(p.get('heures_supplementaires', '') or '')),
                _sanitize_csv_cell(str(p.get('statut', '') or '')),
                _sanitize_csv_cell(str(p.get('remarque', '') or '')),
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
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
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
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
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
            total_primes = sum(Decimal(str(p.montant)) for p in primes_mois)
            salaire = Salaire(
                employe_id=employe.id,
                mois=mois,
                annee=annee,
                salaire_base=Decimal(str(employe.salaire_base or 0)),
                primes=total_primes,
                indemnites=Decimal('0'),
                deductions=Decimal('0'),
                avances=Decimal('0'),
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
        from app.utils.compta_import import _sanitize_csv_cell
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in records:
            writer.writerow([
                _sanitize_csv_cell(str(row.get(h, '')))
                for h in headers
            ])
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
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True
