from app import db
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from decimal import Decimal
from sqlalchemy import func

# Multiplicateur d'impact d'une écriture sur le solde d'un compte selon son type.
# Actif/Charge : le débit augmente le solde, le crédit le diminue  -> +1
# Passif/Produit : le crédit augmente le solde, le débit le diminue -> -1
COMPTE_SENS = {
    TypeCompte.ACTIF: Decimal('1'),
    TypeCompte.CHARGE: Decimal('1'),
    TypeCompte.PASSIF: Decimal('-1'),
    TypeCompte.PRODUIT: Decimal('-1'),
}


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

    @classmethod
    def reindex_solde(cls, id):
        """Recalcule le solde d'un compte à partir de l'ensemble de ses écritures validées."""
        compte = cls.get_by_id(id)
        if not compte:
            return None
        sens = COMPTE_SENS.get(compte.type_compte, Decimal('1'))
        total = db.session.query(
            func.sum(EcritureComptable.montant_debit - EcritureComptable.montant_credit)
        ).filter(
            EcritureComptable.compte_id == compte.id,
            EcritureComptable.statut == StatutEcriture.VALIDE,
            EcritureComptable.is_active.is_(True),
        ).scalar() or Decimal('0')
        compte.solde = (total * sens)
        db.session.commit()
        return compte


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

    @staticmethod
    def _validate_ecriture(data):
        """Valide la cohérence débit/crédit d'une écriture."""
        montant_debit = Decimal(str(data.get('montant_debit') or 0))
        montant_credit = Decimal(str(data.get('montant_credit') or 0))
        if montant_debit > 0 and montant_credit > 0:
            raise ValueError("Débit et crédit ne peuvent pas être tous deux renseignés sur une même écriture")
        if montant_debit <= 0 and montant_credit <= 0:
            raise ValueError("Au moins un de débit ou crédit doit être renseigné")
        compte_id = data.get('compte_id')
        compte = CompteComptableService.get_by_id(compte_id)
        if not compte:
            raise ValueError(f"Compte comptable id={compte_id} introuvable")
        return montant_debit, montant_credit, compte

    @staticmethod
    def _apply_solde_and_tresorerie(ecriture, sens):
        """Met à jour le solde du compte et crée l'écriture de trésorerie associée.

        Called only when an écriture passe au statut VALIDÉ.
        """
        montant_debit = Decimal(str(ecriture.montant_debit or 0))
        montant_credit = Decimal(str(ecriture.montant_credit or 0))
        delta = (montant_debit - montant_credit) * sens
        if delta != 0:
            ecriture.compte.solde = (ecriture.compte.solde or Decimal('0')) + delta
        
        # Determine tresorerie type based on account type and entry direction
        # Inferred cash flow from single-entry recording:
        # - PRODUIT (revenue): credit = money in (ENTREE)
        # - CHARGE (expense): debit = money out (SORTIE)
        # - ACTIF (asset): debit = money in (ENTREE), credit = money out (SORTIE)
        # - PASSIF (liability): credit = money in (ENTREE), debit = money out (SORTIE)
        compte_type = ecriture.compte.type_compte
        if compte_type == TypeCompte.PRODUIT:
            type_op = TypeTresorerie.ENTREE if montant_credit > 0 else TypeTresorerie.SORTIE
        elif compte_type == TypeCompte.CHARGE:
            type_op = TypeTresorerie.SORTIE if montant_debit > 0 else TypeTresorerie.ENTREE
        elif compte_type == TypeCompte.ACTIF:
            type_op = TypeTresorerie.ENTREE if montant_debit > montant_credit else TypeTresorerie.SORTIE
        else:  # PASSIF
            type_op = TypeTresorerie.ENTREE if montant_credit > montant_debit else TypeTresorerie.SORTIE
        
        tres = Tresorerie(
            date=ecriture.date,
            type_operation=type_op,
            montant=abs(montant_debit - montant_credit),
            mode_paiement='especes',
            libelle=ecriture.libelle,
            reference=ecriture.reference_externe,
            compte_id=ecriture.compte_id,
            ecriture_id=ecriture.id,
            tenant_id=ecriture.tenant_id,
        )
        db.session.add(tres)
        return delta

    @classmethod
    def create(cls, data):
        montant_debit, montant_credit, compte = cls._validate_ecriture(data)
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.flush()

        statut = getattr(instance, 'statut', None)
        if statut == StatutEcriture.VALIDE or (hasattr(data.get('statut', None), 'lower') and data.get('statut') == 'valide'):
            sens = COMPTE_SENS.get(compte.type_compte, Decimal('1'))
            cls._apply_solde_and_tresorerie(instance, sens)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        # On n'autorise pas de modifier le débit/crédit directement : passer par valider/annuler.
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by',
                                                      'montant_debit', 'montant_credit', 'compte_id'):
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
        if instance.statut != StatutEcriture.VALIDE:
            sens = COMPTE_SENS.get(instance.compte.type_compte, Decimal('1'))
            cls._apply_solde_and_tresorerie(instance, sens)
            instance.statut = StatutEcriture.VALIDE
            db.session.commit()
            db.session.refresh(instance)
        return instance

    @classmethod
    def annuler_ecriture(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        # Inverser l'effet sur le solde si l'écriture avait été validée.
        if instance.statut == StatutEcriture.VALIDE and instance.compte:
            sens = COMPTE_SENS.get(instance.compte.type_compte, Decimal('1'))
            montant_debit = Decimal(str(instance.montant_debit or 0))
            montant_credit = Decimal(str(instance.montant_credit or 0))
            delta = (montant_debit - montant_credit) * sens * Decimal('-1')
            if delta != 0:
                instance.compte.solde = (instance.compte.solde or Decimal('0')) + delta
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
        db.session.refresh(annulation)
        return annulation

    @classmethod
    def get_journal(cls, date_debut=None, date_fin=None, compte_id=None):
        """Retourne le journal des écritures avec le solde courant par compte."""
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True, statut=StatutEcriture.VALIDE)
        query = cls._get_tenant_filter(query)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        if compte_id:
            query = query.filter_by(compte_id=compte_id)
        ecritures = query.order_by(cls.model.date).all()

        # Totaux par compte (debits / credits) pour le tableau de bord du journal.
        compte_totaux = {}
        for ec in ecritures:
            sens = COMPTE_SENS.get(ec.compte.type_compte, Decimal('1')) if ec.compte else Decimal('1')
            delta = (Decimal(str(ec.montant_debit or 0)) - Decimal(str(ec.montant_credit or 0))) * sens
            c = compte_totaux.setdefault(ec.compte_id, {'debit': Decimal('0'), 'credit': Decimal('0'), 'solde': Decimal('0')})
            c['debit'] += Decimal(str(ec.montant_debit or 0))
            c['credit'] += Decimal(str(ec.montant_credit or 0))
            c['solde'] += delta

        result = []
        solde_courant = Decimal('0')
        for ec in ecritures:
            sens = COMPTE_SENS.get(ec.compte.type_compte, Decimal('1')) if ec.compte else Decimal('1')
            delta = (Decimal(str(ec.montant_debit or 0)) - Decimal(str(ec.montant_credit or 0))) * sens
            solde_courant += delta
            row = ec.to_dict()
            row['solde_courant'] = float(round(solde_courant, 2))
            result.append(row)

        comptes_resume = []
        for compte_id, t in compte_totaux.items():
            compte = CompteComptableService.get_by_id(compte_id)
            comptes_resume.append({
                'compte_id': compte_id,
                'numero': compte.numero if compte else None,
                'nom': compte.nom if compte else None,
                'debit': float(t['debit']),
                'credit': float(t['credit']),
                'solde': float(round(t['solde'], 2)),
            })
        return {
            'ecritures': result,
            'comptes_resume': sorted(comptes_resume, key=lambda x: x['numero'] or ''),
            'total_debit': float(sum(t['debit'] for t in compte_totaux.values())),
            'total_credit': float(sum(t['credit'] for t in compte_totaux.values())),
        }


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
        query = cls.model.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        entrees = query.filter(cls.model.type_operation == 'entree').with_entities(func.sum(cls.model.montant)).scalar() or 0
        sorties = query.filter(cls.model.type_operation == 'sortie').with_entities(func.sum(cls.model.montant)).scalar() or 0
        return float(entrees) - float(sorties)

    @classmethod
    def get_mouvements(cls, date_debut=None, date_fin=None):
        """Retourne les mouvements de trésorerie triés avec le solde courant cumulé."""
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        mouvements = query.order_by(cls.model.date).all()
        result = []
        solde = Decimal('0')
        for m in mouvements:
            montant = Decimal(str(m.montant or 0))
            if m.type_operation == TypeTresorerie.ENTREE or (hasattr(m.type_operation, 'value') and m.type_operation.value == 'entree'):
                solde += montant
            else:
                solde -= montant
            d = m.to_dict()
            d['solde_courant'] = float(round(solde, 2))
            result.append(d)
        return result


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

    @staticmethod
    def export_comptes():
        tenant_id = get_current_tenant_id()
        query = CompteComptable.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(CompteComptable.tenant_id == tenant_id)
        comptes = query.order_by(CompteComptable.numero).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'numero', 'nom', 'type_compte', 'sous_compte_id', 'solde', 'is_actif', 'tenant_id'])
        for c in comptes:
            writer.writerow([
                c.id, c.numero, c.nom,
                c.type_compte.value if c.type_compte else '',
                c.sous_compte_id or '', c.solde, c.is_actif, c.tenant_id,
            ])
        return buf.getvalue()

    @staticmethod
    def export_ecritures():
        tenant_id = get_current_tenant_id()
        query = EcritureComptable.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(EcritureComptable.tenant_id == tenant_id)
        ecritures = query.order_by(EcritureComptable.date).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'date', 'compte_id', 'montant_debit', 'montant_credit', 'libelle', 'piece_joint', 'reference_externe', 'entite_type', 'entite_id', 'statut', 'tenant_id'])
        for e in ecritures:
            writer.writerow([
                e.id, e.date.isoformat() if e.date else '', e.compte_id, e.montant_debit, e.montant_credit, e.libelle,
                e.piece_joint or '', e.reference_externe or '', e.entite_type or '', e.entite_id or '',
                e.statut.value if e.statut else '', e.tenant_id,
            ])
        return buf.getvalue()

    @staticmethod
    def export_tresorerie():
        tenant_id = get_current_tenant_id()
        query = Tresorerie.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(Tresorerie.tenant_id == tenant_id)
        entries = query.order_by(Tresorerie.date).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'date', 'type_operation', 'montant', 'mode_paiement', 'libelle', 'compte_bancaire', 'reference', 'is_reconcilie', 'compte_id', 'ecriture_id', 'tenant_id'])
        for t in entries:
            writer.writerow([
                t.id, t.date.isoformat() if t.date else '',
                t.type_operation.value if t.type_operation else '', t.montant, t.mode_paiement or '',
                t.libelle, t.compte_bancaire or '', t.reference or '', t.is_reconcilie, t.compte_id or '', t.ecriture_id or '', t.tenant_id,
            ])
        return buf.getvalue()
