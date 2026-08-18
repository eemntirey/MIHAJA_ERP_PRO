
import pandas as pd
from werkzeug.datastructures import FileStorage
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.tenant import get_current_tenant_id
from app import db
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

ACCOUNT_TYPE_MAP = {
    'actif': TypeCompte.ACTIF,
    'passif': TypeCompte.PASSIF,
    'charge': TypeCompte.CHARGE,
    'produit': TypeCompte.PRODUIT,
}

ECRITURE_STATUT_MAP = {
    'brouillon': StatutEcriture.BROUILLON,
    'valide': StatutEcriture.VALIDE,
    'annule': StatutEcriture.ANNULE,
}

TRESORERIE_TYPE_MAP = {
    'entree': TypeTresorerie.ENTREE,
    'sortie': TypeTresorerie.SORTIE,
}

PAIEMENT_MAP = {
    'espece': 'espece',
    'virement': 'virement',
    'cheque': 'cheque',
    'mobile_money': 'mobile_money',
    'mobile money': 'mobile_money',
    'carte': 'carte',
}

def _read_file(file: FileStorage):
    filename = file.filename.lower()
    try:
        if filename.endswith('.csv'):
            file.seek(0)
            return pd.read_csv(file), 'csv'
        elif filename.endswith(('.xlsx', '.xls')):
            file.seek(0)
            return pd.read_excel(file), 'excel'
        else:
            raise ValueError("Format non supporté. Utilisez CSV ou Excel (.csv, .xlsx, .xls)")
    except Exception as e:
        logger.error(f"Erreur lecture fichier comptabilité: {e}")
        raise ValueError(f"Impossible de lire le fichier: {str(e)}")


def _safe_decimal(val):
    if val is None or val == '':
        return Decimal('0')
    return Decimal(str(val))


def import_comptes_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'numero', 'nom'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier comptes: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            numero = str(row.get('numero', '')).strip()
            nom = str(row.get('nom', '')).strip()
            if not numero or not nom:
                errors.append(f"Ligne {idx + 2}: numero et nom requis")
                continue

            if CompteComptable.query.filter_by(numero=numero, is_active=True).first():
                errors.append(f"Ligne {idx + 2}: Compte {numero} existe déjà")
                continue

            type_compte_raw = str(row.get('type_compte', 'actif')).strip().lower()
            type_compte = ACCOUNT_TYPE_MAP.get(type_compte_raw)
            if type_compte is None:
                errors.append(f"Ligne {idx + 2}: type_compte invalide '{type_compte_raw}'")
                continue

            sous_compte_id = None
            if pd.notna(row.get('sous_compte_id')) and str(row.get('sous_compte_id')).strip():
                parent = CompteComptable.query.filter_by(numero=str(row['sous_compte_id']).strip(), is_active=True).first()
                if parent:
                    sous_compte_id = parent.id
                else:
                    errors.append(f"Ligne {idx + 2}: Compte parent {row['sous_compte_id']} introuvable")
                    continue

            compte = CompteComptable(
                numero=numero,
                nom=nom,
                type_compte=type_compte,
                sous_compte_id=sous_compte_id,
                solde=_safe_decimal(row.get('solde', 0)),
                is_actif=True,
                tenant_id=tenant_id,
            )
            db.session.add(compte)
            results.append({'numero': numero, 'nom': nom, 'type': type_compte.value})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }


def import_ecritures_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'date', 'compte_id', 'libelle'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier ecritures: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            date_raw = str(row.get('date', '')).strip()
            if not date_raw:
                errors.append(f"Ligne {idx + 2}: date requise")
                continue

            date_obj = None
            for fmt_date in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_obj = datetime.strptime(date_raw, fmt_date).date()
                    break
                except ValueError:
                    continue
            if not date_obj:
                errors.append(f"Ligne {idx + 2}: format date invalide '{date_raw}' (attendu YYYY-MM-DD)")
                continue

            compte_id = int(float(str(row.get('compte_id', '')).strip()))
            compte = CompteComptable.query.filter_by(id=compte_id, is_active=True).first()
            if not compte:
                errors.append(f"Ligne {idx + 2}: compte_id {compte_id} introuvable")
                continue

            montant_debit = _safe_decimal(row.get('montant_debit', 0))
            montant_credit = _safe_decimal(row.get('montant_credit', 0))
            if montant_debit > 0 and montant_credit > 0:
                errors.append(f"Ligne {idx + 2}: débit et crédit ne peuvent pas être tous les deux > 0")
                continue

            libelle = str(row.get('libelle', '')).strip()
            if not libelle:
                errors.append(f"Ligne {idx + 2}: libelle requis")
                continue

            statut_raw = str(row.get('statut', 'brouillon')).strip().lower()
            statut = ECRITURE_STATUT_MAP.get(statut_raw, StatutEcriture.BROUILLON)

            entite_type = None
            if pd.notna(row.get('entite_type')) and str(row.get('entite_type')).strip():
                entite_type = str(row.get('entite_type')).strip()

            entite_id = None
            if pd.notna(row.get('entite_id')) and str(row.get('entite_id')).strip():
                try:
                    entite_id = int(float(str(row.get('entite_id')).strip()))
                except Exception:
                    pass

            ecriture = EcritureComptable(
                date=date_obj,
                compte_id=compte_id,
                montant_debit=montant_debit,
                montant_credit=montant_credit,
                libelle=libelle,
                piece_joint=str(row.get('piece_joint', '') or ''),
                reference_externe=str(row.get('reference_externe', '') or '') if pd.notna(row.get('reference_externe')) else None,
                entite_type=entite_type,
                entite_id=entite_id,
                statut=statut,
                tenant_id=tenant_id,
            )
            db.session.add(ecriture)
            results.append({'date': str(date_obj), 'libelle': libelle, 'compte': compte.numero})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }


def import_tresorerie_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'date', 'type_operation', 'montant', 'libelle'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier tresorerie: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            date_raw = str(row.get('date', '')).strip()
            if not date_raw:
                errors.append(f"Ligne {idx + 2}: date requise")
                continue

            date_obj = None
            for fmt_date in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_obj = datetime.strptime(date_raw, fmt_date).date()
                    break
                except ValueError:
                    continue
            if not date_obj:
                errors.append(f"Ligne {idx + 2}: format date invalide '{date_raw}' (attendu YYYY-MM-DD)")
                continue

            type_raw = str(row.get('type_operation', '')).strip().lower()
            type_operation = TRESORERIE_TYPE_MAP.get(type_raw)
            if type_operation is None:
                errors.append(f"Ligne {idx + 2}: type_operation invalide '{type_raw}'")
                continue

            montant = _safe_decimal(row.get('montant'))
            if montant <= 0:
                errors.append(f"Ligne {idx + 2}: montant doit être positif")
                continue

            libelle = str(row.get('libelle', '')).strip()
            if not libelle:
                errors.append(f"Ligne {idx + 2}: libelle requis")
                continue

            mode_paiement_raw = str(row.get('mode_paiement', 'espece')).strip().lower()
            mode_paiement = PAIEMENT_MAP.get(mode_paiement_raw, 'espece')

            compte_bancaire = None
            if pd.notna(row.get('compte_bancaire')) and str(row.get('compte_bancaire')).strip():
                compte_bancaire = str(row.get('compte_bancaire')).strip()

            reference = None
            if pd.notna(row.get('reference')) and str(row.get('reference')).strip():
                reference = str(row.get('reference')).strip()

            entree = Tresorerie(
                date=date_obj,
                type_operation=type_operation,
                montant=montant,
                mode_paiement=mode_paiement,
                libelle=libelle,
                compte_bancaire=compte_bancaire,
                reference=reference,
                piece_jointe=str(row.get('piece_joint', '') or ''),
                is_reconcilie=bool(str(row.get('is_reconcilie', '')).lower() in ('true', '1', 'oui')),
                tenant_id=tenant_id,
            )
            db.session.add(entree)
            results.append({'date': str(date_obj), 'type': type_operation.value, 'montant': str(montant), 'libelle': libelle})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }
