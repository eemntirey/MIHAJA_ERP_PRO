from flask_restx import Namespace, Resource
from app.services.dashboard_service import get_dashboard_data
from app.security.tenant import tenant_required

api = Namespace('dashboard', description='Tableau de bord et statistiques')

@api.route('/')
class Dashboard(Resource):
    @api.doc('get_dashboard')
    @tenant_required
    def get(self):
        """Récupère les données du tableau de bord"""
        data = get_dashboard_data()
        return {
            'message': 'Donnees du tableau de bord',
            'stats': data,
        }, 200

@api.route('/sales-stats')
class SalesStats(Resource):
    @tenant_required
    def get(self):
        """Statistiques des ventes"""
        from app.models.vente import Vente
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func
        from datetime import datetime, timedelta

        tenant_id = get_current_tenant_id()
        today = datetime.utcnow().date()
        debut_mois = today.replace(day=1)

        query = Vente.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        ca_total = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True
        )
        if tenant_id:
            ca_total = ca_total.filter_by(tenant_id=tenant_id)
        ca_total = ca_total.scalar() or 0

        ventes_mois = query.filter(Vente.created_at >= debut_mois).count()
        ca_mois = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ca_mois = ca_mois.filter_by(tenant_id=tenant_id)
        ca_mois = ca_mois.scalar() or 0

        panier_moyen = float(ca_mois) / ventes_mois if ventes_mois > 0 else 0

        return {
            'ca_total': float(ca_total),
            'ventes_mois': ventes_mois,
            'ca_mois': float(ca_mois),
            'panier_moyen': panier_moyen
        }, 200

@api.route('/top-products')
class TopProducts(Resource):
    @tenant_required
    def get(self):
        """Top produits vendus"""
        from app.models.ligne_vente import LigneVente
        from app.models.produit import Produit
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func

        tenant_id = get_current_tenant_id()

        query = db.session.query(
            LigneVente.produit_id,
            Produit.nom,
            func.sum(LigneVente.quantite).label('total_quantite'),
            func.sum(LigneVente.total_ht).label('total_ca')
        ).join(
            Produit, Produit.id == LigneVente.produit_id
        ).filter(
            LigneVente.is_active == True,
            Produit.is_active == True
        )

        if tenant_id:
            query = query.filter(LigneVente.tenant_id == tenant_id)

        results = query.group_by(
            LigneVente.produit_id, Produit.nom
        ).order_by(
            func.sum(LigneVente.quantite).desc()
        ).limit(10).all()

        return {
            'top_products': [{
                'produit_id': r[0],
                'nom': r[1],
                'total_quantite': float(r[2]),
                'total_ca': float(r[3])
            } for r in results]
        }, 200

@api.route('/top-clients')
class TopClients(Resource):
    @tenant_required
    def get(self):
        """Top clients par chiffre d'affaires"""
        from app.models.vente import Vente
        from app.models.client import Client
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func

        tenant_id = get_current_tenant_id()

        query = db.session.query(
            Vente.client_id,
            Client.nom,
            func.count(Vente.id).label('nb_ventes'),
            func.sum(Vente.total_ttc).label('ca_total')
        ).join(
            Client, Client.id == Vente.client_id
        ).filter(
            Vente.is_active == True,
            Client.is_active == True
        )

        if tenant_id:
            query = query.filter(Vente.tenant_id == tenant_id)

        results = query.group_by(
            Vente.client_id, Client.nom
        ).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(10).all()

        return {
            'top_clients': [{
                'client_id': r[0],
                'nom': r[1],
                'nb_ventes': r[2],
                'ca_total': float(r[3])
            } for r in results]
        }, 200

@api.route('/alerts')
class Alerts(Resource):
    @tenant_required
    def get(self):
        """Alertes stock et autres"""
        from app.models.produit import Produit
        from app import db
        from app.security.tenant import get_current_tenant_id

        tenant_id = get_current_tenant_id()

        query = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        alertes_stock = query.all()

        return {
            'alertes_stock': [p.to_dict() for p in alertes_stock],
            'nb_alertes_stock': len(alertes_stock)
        }, 200

