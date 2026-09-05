from flask import request, current_app
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.services.produit_service import ProduitService
from app.models.stock import MouvementStock
from app import db
from decimal import Decimal

ns = Namespace('stocks', description='Gestion des stocks')

@ns.route('/')
class StockList(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Liste les produits avec statut stock"""
        produits = ProduitService.get_stock_alert()
        return {'stocks': [p.to_dict() for p in produits]}, 200

    @permission_required('stock.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json() or {}
        produit_id = data.get('produit_id')
        quantite = data.get('quantite')
        type_mouvement = data.get('type_mouvement')
        if not produit_id or quantite is None or not type_mouvement:
            return {'message': 'produit_id, quantite et type_mouvement sont requis'}, 400
        try:
            from decimal import Decimal
            qty = Decimal(str(quantite))
        except Exception:
            return {'message': 'Quantite invalide'}, 400
        result = ProduitService.update_stock(
            produit_id,
            qty,
            type_mouvement,
            data.get('raison', '')
        )
        if not result:
            return {'message': 'Produit non trouve'}, 404
        return result.to_dict(), 201

@ns.route('/<int:id>')
class StockResource(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self, id):
        """Statut d'un produit"""
        produit = ProduitService.get_by_id(id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200

@ns.route('/mouvements')
class StockMouvementList(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Liste des mouvements de stock"""
        from app.models.stock import MouvementStock
        from app.security.tenant import get_current_tenant_id
        from app.models.utilisateur import Role
        from flask_jwt_extended import get_jwt

        claims = get_jwt() or {}
        role = claims.get('role')
        tenant_id = get_current_tenant_id()

        query = MouvementStock.query.filter_by(is_active=True).order_by(MouvementStock.created_at.desc())
        if role != Role.SUPER_ADMIN.value and tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        mouvements = query.all()
        return {'mouvements': [m.to_dict() for m in mouvements]}, 200

    @permission_required('stock.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json() or {}
        produit_id = data.get('produit_id')
        quantite = data.get('quantite')
        type_mouvement = data.get('type_mouvement')
        if not produit_id or quantite is None or not type_mouvement:
            return {'message': 'produit_id, quantite et type_mouvement sont requis'}, 400
        try:
            try:
                qty = Decimal(str(quantite))
            except Exception:
                return {'message': 'Quantite invalide'}, 400
            result = ProduitService.update_stock(
                produit_id,
                qty,
                type_mouvement,
                data.get('raison', '')
            )
            if not result:
                return {'message': 'Produit non trouve'}, 404
            return result.to_dict(), 201
        except Exception:
            current_app.logger.exception('Erreur lors de la mise a jour du stock')
            return {'message': 'Erreur lors de la mise a jour du stock'}, 400

@ns.route('/stats')
class StockStats(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Statistiques des stocks"""
        stats = ProduitService.get_statistiques()
        return stats, 200


@ns.route('/alerts')
class StockAlerts(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Alertes de stock"""
        produits = ProduitService.get_stock_alert()
        return {'alerts': [p.to_dict() for p in produits]}, 200

