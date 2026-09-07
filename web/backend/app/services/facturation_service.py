from app import db
from app.models.facture import Facture
from app.models.vente import Vente
from app.models.client import Client
from app.security.tenant import get_current_tenant_id


FACTURE_ALLOWED_KEYS = {
    'vente_id', 'client_id', 'reference', 'total_ht', 'total_ttc',
    'statut', 'tenant_id', 'is_active', 'created_by', 'updated_by',
}


def _filter_facture_payload(data):
    """Ne garde que les colonnes du modele Facture pour eviter
    TypeError avec SQLAlchemy 2.x (rejette les kwargs non-colonnes)."""
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in FACTURE_ALLOWED_KEYS}


def issue_invoice(data):
    data = _filter_facture_payload(data)
    if not data.get('vente_id') or not data.get('client_id'):
        raise ValueError('vente_id et client_id sont requis')
    tenant_id = get_current_tenant_id()
    if tenant_id:
        data['tenant_id'] = tenant_id
    reference = data.get('reference')
    if reference:
        # Unicite de la reference par tenant
        query = Facture.query.filter_by(reference=reference, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        if query.first():
            raise ValueError(f"Une facture avec la reference '{reference}' existe deja")
    else:
        # Generation d'une reference unique si absente
        import random
        import string
        from datetime import datetime
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        for _ in range(10):
            suffix = ''.join(random.choices(string.digits, k=4))
            candidate = f"FAC-{ts}-{suffix}"
            query = Facture.query.filter_by(reference=candidate, is_active=True)
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            if not query.first():
                data['reference'] = candidate
                break
        else:
            raise ValueError("Impossible de generer une reference unique de facture")
    facture = Facture(**data)
    db.session.add(facture)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return facture


def get_all():
    tenant_id = get_current_tenant_id()
    query = Facture.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Facture.query.filter_by(id=id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    facture = get_by_id(id)
    if not facture:
        return None
    PROTECTED = {'id', 'tenant_id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'}
    for key, value in data.items():
        if key in PROTECTED:
            continue
        if hasattr(facture, key):
            setattr(facture, key, value)
    db.session.commit()
    return facture


def delete(id):
    facture = get_by_id(id)
    if not facture:
        return None
    facture.delete()
    db.session.commit()
    return facture


def generate_from_vente(vente_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=vente_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    vente = query.first()
    if not vente:
        return None
    # Eviter la double facturation pour la meme vente
    existing_query = Facture.query.filter_by(vente_id=vente.id, is_active=True)
    if tenant_id:
        existing_query = existing_query.filter_by(tenant_id=tenant_id)
    if existing_query.first():
        raise ValueError("Une facture existe deja pour cette vente")
    facture = Facture(
        vente_id=vente.id,
        client_id=vente.client_id,
        tenant_id=vente.tenant_id,
        total_ht=vente.total_ht,
        total_ttc=vente.total_ttc,
        statut='non_payee',
        reference=f"FAC-{vente.reference}",
    )
    db.session.add(facture)
    db.session.commit()
    return facture
