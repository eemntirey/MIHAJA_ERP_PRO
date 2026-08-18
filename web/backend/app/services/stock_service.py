from app import db
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.security.tenant import get_current_tenant_id


def get_mouvements(produit_id=None, type_mouvement=None):
    tenant_id = get_current_tenant_id()
    query = MouvementStock.query
    if produit_id is not None:
        query = query.filter_by(produit_id=produit_id)
    if type_mouvement is not None:
        query = query.filter_by(type_mouvement=type_mouvement)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def update_stock(produit_id, quantity):
    tenant_id = get_current_tenant_id()
    query = Produit.query.filter_by(id=produit_id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produit = query.first()
    if not produit:
        return None
    produit.quantite_stock = quantity
    db.session.commit()
    return produit
