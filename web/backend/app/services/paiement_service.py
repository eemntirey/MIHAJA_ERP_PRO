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


def process_payment(data):
    tenant_id = get_current_tenant_id()
    normalized = _normalize_payment_data(data)
    if tenant_id:
        normalized['tenant_id'] = tenant_id
    paiement = Paiement(**normalized)
    db.session.add(paiement)
    db.session.commit()
    
    facture_id = normalized.get('facture_id')
    if facture_id:
        from app.security.tenant import get_current_tenant_id as _get_tid
        tid = _get_tid()
        query = Facture.query.filter_by(id=facture_id, is_active=True)
        if tid is not None:
            query = query.filter_by(tenant_id=tid)
        facture = query.first()
        if facture:
            total_paye = db.session.query(
                db.func.sum(Paiement.montant)
            ).filter(
                Paiement.facture_id == facture_id,
                Paiement.tenant_id == facture.tenant_id,
                Paiement.is_active == True
            ).scalar() or 0
            
            if total_paye >= float(facture.total_ttc):
                facture.statut = 'payee'
            elif total_paye > 0:
                facture.statut = 'payee_partiel'
            else:
                facture.statut = 'non_payee'
            db.session.commit()
    
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
    for key, value in normalized.items():
        if hasattr(paiement, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(paiement, key, value)
    db.session.commit()
    return paiement


def delete(id):
    paiement = get_by_id(id)
    if not paiement:
        return None
    paiement.delete()
    return paiement
