from flask import current_app
from datetime import datetime
from decimal import Decimal
from app import db
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.security.tenant import get_current_tenant_id, set_tenant_filter
import random
import string


def get_sales_summary():
    query = Vente.query.filter_by(is_active=True)
    query = set_tenant_filter(query, Vente)
    return query.all()


def get_by_id(id):
    query = Vente.query.filter_by(id=id, is_active=True)
    query = set_tenant_filter(query, Vente)
    return query.first()


def update(id, data):
    sale = get_by_id(id)
    if not sale:
        return None
    if 'date' in data and isinstance(data['date'], str):
        data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
    for key, value in data.items():
        if hasattr(sale, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(sale, key, value)
    db.session.commit()
    return sale


def delete(id):
    sale = get_by_id(id)
    if not sale:
        return None
    sale.delete()
    return sale


def create_with_lignes(data):
    tenant_id = get_current_tenant_id()
    lignes_data = data.pop('lignes', [])
    if tenant_id is None:
        raise ValueError('Aucun tenant associe a ce compte')
    data['tenant_id'] = tenant_id

    if not data.get('reference'):
        prefix = 'VENT'
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        data['reference'] = f'{prefix}-{timestamp}-{random_part}'

    vente = Vente(**{k: v for k, v in data.items() if hasattr(Vente, k)})
    db.session.add(vente)
    db.session.flush()

    for ligne in lignes_data:
        ligne['vente_id'] = vente.id
        ligne['tenant_id'] = tenant_id
        db.session.add(LigneVente(**{k: v for k, v in ligne.items() if hasattr(LigneVente, k)}))

    db.session.commit()
    return vente
