from app import db
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id


def get_sales_summary():
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    sale = get_by_id(id)
    if not sale:
        return None
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
    if tenant_id:
        data['tenant_id'] = tenant_id

    total_ht = 0
    total_ttc = 0
    for ligne in lignes_data:
        quantite = float(ligne.get('quantite', 0))
        prix_unitaire_ht = float(ligne.get('prix_unitaire', 0))
        taux_tva = float(ligne.get('taux_tva', 20))
        total_ht += quantite * prix_unitaire_ht
        total_ttc += quantite * prix_unitaire_ht * (1 + taux_tva / 100)

    data['total_ht'] = total_ht
    data['total_ttc'] = total_ttc
    sale = Vente(**data)
    db.session.add(sale)
    db.session.flush()
    for ligne in lignes_data:
        produit_id = ligne.get('produit_id')
        quantite = ligne.get('quantite')
        ligne['vente_id'] = sale.id
        ligne['tenant_id'] = sale.tenant_id
        ligne_vente = LigneVente(**ligne)
        db.session.add(ligne_vente)
        if produit_id and quantite is not None:
            qty = float(quantite)
            if qty > 0:
                tenant_id = sale.tenant_id
                produit_query = Produit.query.filter_by(id=produit_id)
                if tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=tenant_id)
                produit = produit_query.first()
                if produit:
                    produit.retirer_stock(qty)
    db.session.commit()
    return sale


def get_by_client(client_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_stats():
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    ventes = query.all()
    count = len(ventes)
    total = sum(float(v.total_ttc) for v in ventes)
    average = total / count if count > 0 else 0
    by_status = {}
    for vente in ventes:
        statut = vente.statut
        if statut not in by_status:
            by_status[statut] = {'count': 0, 'total': 0}
        by_status[statut]['count'] += 1
        by_status[statut]['total'] += float(v.total_ttc)
    return {
        'total': total,
        'count': count,
        'average': average,
        'by_status': by_status
    }
