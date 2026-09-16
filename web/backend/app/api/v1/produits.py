from flask_restx import Namespace, Resource
from app.services.produit_service import ProduitService
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.security.plan_limits import check_plan_limits
from app.utils.qr_generator import generate_qr_code_base64

ns = Namespace('produits', description='Gestion des produits')

@ns.route('/')
class ProduitListResource(Resource):
    @ns.doc('list_produits')
    @permission_required('product.view')
    @tenant_required_readonly
    def get(self):
        """Liste tous les produits"""
        try:
            produits, total = ProduitService.get_all()
            return {'produits': [p.to_dict() for p in produits], 'total': total}, 200
        except Exception as e:
            return {'produits': [], 'total': 0, 'message': str(e)}, 500

    @ns.doc('create_produit')
    @permission_required('product.create')
    @tenant_required_readonly
    @check_plan_limits('produits')
    def post(self):
        """Cree un nouveau produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.create(data)
        return produit.to_dict(), 201

@ns.route('/<int:produit_id>')
class ProduitResource(Resource):
    @ns.doc('get_produit')
    @permission_required('product.view')
    @tenant_required_readonly
    def get(self, produit_id):
        """Recupere un produit par son ID"""
        produit = ProduitService.get_by_id(produit_id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200

    @ns.doc('update_produit')
    @permission_required('product.update')
    @tenant_required_readonly
    def put(self, produit_id):
        """Met a jour un produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.update(produit_id, data)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200
    
    @ns.doc('delete_produit')
    @permission_required('product.delete')
    @tenant_required_readonly
    def delete(self, produit_id):
        """Supprime un produit"""
        success = ProduitService.delete(produit_id)
        if not success:
            return {'message': 'Produit non trouve'}, 404
        return {'message': 'Produit supprime'}, 200

@ns.route('/<int:produit_id>/qr-code')
class ProduitQRCodeResource(Resource):
    @ns.doc('get_produit_qr_code')
    @permission_required('product.view')
    @tenant_required_readonly
    def get(self, produit_id):
        """Genere et retourne le QR code du produit en base64"""
        produit = ProduitService.get_by_id(produit_id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        
        # Use reference or code_barre for QR code data
        qr_data = produit.reference or produit.code_barre or f"PROD-{produit.id}"
        qr_base64 = generate_qr_code_base64(qr_data)
        
        return {'qr_code': qr_base64, 'data': qr_data}, 200

@ns.route('/qr-generate')
class QRCodeGenerateResource(Resource):
    @ns.doc('generate_qr_code')
    @permission_required('product.view')
    @tenant_required_readonly
    def post(self):
        """Genere un QR code pour n'importe quelle donnee"""
        from flask import request
        data = request.get_json()
        qr_data = data.get('data', '')
        if not qr_data:
            return {'message': 'Donnees requises'}, 400
        qr_base64 = generate_qr_code_base64(qr_data)
        return {'qr_code': qr_base64, 'data': qr_data}, 200
