from app import db
from app.models.facture import Facture
from app.models.vente import Vente
from app.models.client import Client
from app.security.tenant import get_current_tenant_id


def issue_invoice(data):
    if not data.get('vente_id') or not data.get('client_id'):
        raise ValueError('vente_id et client_id sont requis')
    tenant_id = get_current_tenant_id()
    if tenant_id:
        data['tenant_id'] = tenant_id
    facture = Facture(**data)
    db.session.add(facture)
    db.session.commit()
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
    for key, value in data.items():
        if hasattr(facture, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(facture, key, value)
    db.session.commit()
    return facture


def delete(id):
    facture = get_by_id(id)
    if not facture:
        return None
    facture.delete()
    return facture


def generate_from_vente(vente_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=vente_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    vente = query.first()
    if not vente:
        return None
    facture = Facture(
        vente_id=vente.id,
        client_id=vente.client_id,
        tenant_id=vente.tenant_id,
        total_ht=vente.total_ht,
        total_ttc=vente.total_ttc,
        statut='non_payee'
    )
    db.session.add(facture)
    db.session.commit()
    return facture
