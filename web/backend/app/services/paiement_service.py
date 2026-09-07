from datetime import datetime

from app import db
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.facture import Facture
from app.security.tenant import get_current_tenant_id


def _normalize_payment_data(data):
    """Translate frontend field names to model column names and fill defaults."""
    normalized = dict(data)

    if 'date' in normalized and 'date_paiement' not in normalized:
        raw = normalized.pop('date')
        if raw:
            try:
                normalized['date_paiement'] = datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                try:
                    normalized['date_paiement'] = datetime.strptime(raw, '%Y-%m-%d')
                except (ValueError, TypeError):
                    pass

    if 'remarque' in normalized and 'notes' not in normalized:
        normalized['notes'] = normalized.pop('remarque')

    if normalized.get('date_paiement') and isinstance(normalized['date_paiement'], str):
        try:
            normalized['date_paiement'] = datetime.fromisoformat(normalized['date_paiement'])
        except (ValueError, TypeError):
            try:
                normalized['date_paiement'] = datetime.strptime(normalized['date_paiement'], '%Y-%m-%d')
            except (ValueError, TypeError):
                pass

    normalized.setdefault('statut', StatutPaiement.CONFIRME)
    normalized.setdefault('type', TypePaiement.VENTE)
    normalized.setdefault('mode_paiement', 'especes')

    if normalized.get('statut') and not hasattr(normalized['statut'], 'value'):
        try:
            normalized['statut'] = StatutPaiement(normalized['statut'])
        except ValueError:
            pass

    if normalized.get('type') and not hasattr(normalized['type'], 'value'):
        try:
            normalized['type'] = TypePaiement(normalized['type'])
        except ValueError:
            pass

    return normalized


def _recompute_facture_status(facture_id):
    """Recalcule le statut d'une facture en fonction du cumul des paiements actifs."""
    if not facture_id:
        return
    facture = db.session.get(Facture, facture_id)
    if not facture:
        return
    total_paye = db.session.query(
        db.func.sum(Paiement.montant)
    ).filter(
        Paiement.facture_id == facture_id,
        Paiement.tenant_id == facture.tenant_id,
        Paiement.is_active == True,
    ).scalar() or 0
    total_paye = float(total_paye or 0)
    total_ttc = float(facture.total_ttc or 0)
    if total_paye >= total_ttc and total_ttc > 0:
        facture.statut = 'payee'
    elif total_paye > 0:
        facture.statut = 'payee_partiel'
    else:
        facture.statut = 'non_payee'
    db.session.commit()


def process_payment(data):
    tenant_id = get_current_tenant_id()
    normalized = _normalize_payment_data(data)
    if tenant_id:
        normalized['tenant_id'] = tenant_id

    # Validation anti-overpayment : la somme des paiements actifs ne doit pas
    # depasser le montant TTC de la facture. On verrouille la ligne facture
    # le temps de l'operation pour eviter les races (sur SQLite, le verrou
    # est ignore, mais la transaction reste atomique cote logique).
    facture_id = normalized.get('facture_id')
    if facture_id:
        facture = Facture.query.filter_by(
            id=facture_id, is_active=True,
        )
        if tenant_id is not None:
            facture = facture.filter_by(tenant_id=tenant_id)
        facture = facture.with_for_update().first()
        if not facture:
            db.session.rollback()
            raise ValueError("Facture introuvable")
        montant = float(normalized.get('montant') or 0)
        if montant <= 0:
            db.session.rollback()
            raise ValueError("Le montant doit etre superieur a 0")
        total_paye_actuel = db.session.query(
            db.func.coalesce(db.func.sum(Paiement.montant), 0)
        ).filter(
            Paiement.facture_id == facture_id,
            Paiement.tenant_id == facture.tenant_id,
            Paiement.is_active == True,
        ).scalar() or 0
        total_paye_actuel = float(total_paye_actuel)
        total_ttc = float(facture.total_ttc or 0)
        if total_paye_actuel + montant > total_ttc + 0.01:
            db.session.rollback()
            raise ValueError(
                f"Montant trop eleve : deja paye {total_paye_actuel:.2f} "
                f"sur {total_ttc:.2f}"
            )

    paiement = Paiement(**normalized)
    db.session.add(paiement)
    db.session.commit()

    if facture_id:
        _recompute_facture_status(facture_id)

    return paiement


def get_all():
    tenant_id = get_current_tenant_id()
    query = Paiement.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Paiement.query.filter_by(id=id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def get_by_facture(facture_id):
    tenant_id = get_current_tenant_id()
    query = Paiement.query.filter_by(facture_id=facture_id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def update(id, data):
    paiement = get_by_id(id)
    if not paiement:
        return None
    normalized = _normalize_payment_data(data)
    PROTECTED = {'id', 'tenant_id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'}
    for key, value in normalized.items():
        if key in PROTECTED:
            continue
        if hasattr(paiement, key):
            setattr(paiement, key, value)
    db.session.commit()
    if paiement.facture_id:
        _recompute_facture_status(paiement.facture_id)
    return paiement


def delete(id):
    paiement = get_by_id(id)
    if not paiement:
        return None
    facture_id = paiement.facture_id
    paiement.delete()
    db.session.commit()
    if facture_id:
        _recompute_facture_status(facture_id)
    return paiement
