from app import db
from app.models.paiement import Paiement
from app.models.facture import Facture
from app.security.tenant import get_current_tenant_id, set_tenant_filter


def get_all():
    query = Paiement.query
    query = set_tenant_filter(query, Paiement)
    return query.all()


def get_by_id(id):
    query = Paiement.query.filter_by(id=id)
    query = set_tenant_filter(query, Paiement)
    return query.first()


def get_by_facture(facture_id):
    query = Paiement.query.filter_by(facture_id=facture_id)
    query = set_tenant_filter(query, Paiement)
    return query.all()
