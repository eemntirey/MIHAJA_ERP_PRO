from flask_restx import Namespace, Resource
from app.services.produit_service import ProduitService
from app.security.tenant import tenant_required

ns = Namespace('produits', description='Gestion des produits')

@ns.route('/')
class ProduitListResource(Resource):
    @ns.doc('list_produits')
    @tenant_required
    def get(self):
        """Liste tous les produits"""
        try:
            produits, total = ProduitService.get_all()
            return {'produits': [p.to_dict() for p in produits], 'total': total}, 200
        except Exception as e:
            return {'produits': [], 'total': 0, 'message': str(e)}, 500
    
    @ns.doc('create_produit')
    @tenant_required
    def post(self):
        """Cree un nouveau produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.create(data)
        return produit.to_dict(), 201

@ns.route('/<int:produit_id>')
class ProduitResource(Resource):
    @ns.doc('get_produit')
    @tenant_required
    def get(self, produit_id):
        """Recupere un produit par son ID"""
        produit = ProduitService.get_by_id(produit_id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200
    
    @ns.doc('update_produit')
    @tenant_required
    def put(self, produit_id):
        """Met a jour un produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.update(produit_id, data)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200
    
    @ns.doc('delete_produit')
    @tenant_required
    def delete(self, produit_id):
        """Supprime un produit"""
        success = ProduitService.delete(produit_id)
        if not success:
            return {'message': 'Produit non trouve'}, 404
        return {'message': 'Produit supprime'}, 200
