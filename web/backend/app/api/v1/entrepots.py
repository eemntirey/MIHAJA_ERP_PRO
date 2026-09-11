from flask import request
from flask_restx import Namespace, Resource, fields
from app import db
from app.models.entrepot import Entrepot
from app.models.stock_entrepot import StockEntrepot
from app.models.produit import Produit
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required

ns = Namespace('entrepots', description='Gestion des entrepôts (multi-entrepôts)')

entrepot_model = ns.model('Entrepot', {
    'id': fields.Integer(readonly=True),
    'nom': fields.String(required=True, min_length=1, max_length=100),
    'code': fields.String(max_length=20),
    'adresse': fields.String,
    'ville': fields.String(max_length=100),
    'telephone': fields.String(max_length=20),
    'responsable': fields.String(max_length=100),
    'capacite': fields.Float,
    'principal': fields.Boolean(default=False),
    'stock_count': fields.Integer,
})

stock_entrepot_model = ns.model('StockEntrepot', {
    'id': fields.Integer(readonly=True),
    'produit_id': fields.Integer(required=True),
    'entrepot_id': fields.Integer(required=True),
    'quantite': fields.Float(default=0),
    'seuil_min': fields.Float(default=0),
    'seuil_max': fields.Float,
    'produit_nom': fields.String(readonly=True),
    'produit_reference': fields.String(readonly=True),
    'entrepot_nom': fields.String(readonly=True),
    'entrepot_code': fields.String(readonly=True),
})


@ns.route('/')
class EntrepotListResource(Resource):
    @ns.doc('list_entrepots')
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Liste tous les entrepôts"""
        entrepots = Entrepot.query.all()
        return {'entrepots': [e.to_dict() for e in entrepots], 'total': len(entrepots)}, 200

    @ns.doc('create_entrepot')
    @permission_required('stock.update')
    @tenant_required_readonly
    def post(self):
        """Crée un nouvel entrepôt"""
        data = request.get_json()
        entrepot = Entrepot(
            nom=data['nom'],
            code=data.get('code'),
            adresse=data.get('adresse'),
            ville=data.get('ville'),
            telephone=data.get('telephone'),
            responsable=data.get('responsable'),
            capacite=data.get('capacite'),
            principal=data.get('principal', False),
        )
        entrepot.save()
        return entrepot.to_dict(), 201


@ns.route('/<int:entrepot_id>')
class EntrepotResource(Resource):
    @ns.doc('get_entrepot')
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self, entrepot_id):
        """Récupère un entrepôt par son ID"""
        entrepot = Entrepot.query.get(entrepot_id)
        if not entrepot:
            return {'message': 'Entrepôt non trouvé'}, 404
        return entrepot.to_dict(), 200

    @ns.doc('update_entrepot')
    @permission_required('stock.update')
    @tenant_required_readonly
    def put(self, entrepot_id):
        """Met à jour un entrepôt"""
        entrepot = Entrepot.query.get(entrepot_id)
        if not entrepot:
            return {'message': 'Entrepôt non trouvé'}, 404
        data = request.get_json()
        for attr in ['nom', 'code', 'adresse', 'ville', 'telephone', 'responsable', 'capacite', 'principal']:
            if attr in data:
                setattr(entrepot, attr, data[attr])
        entrepot.save()
        return entrepot.to_dict(), 200

    @ns.doc('delete_entrepot')
    @permission_required('stock.delete')
    @tenant_required_readonly
    def delete(self, entrepot_id):
        """Supprime un entrepôt"""
        entrepot = Entrepot.query.get(entrepot_id)
        if not entrepot:
            return {'message': 'Entrepôt non trouvé'}, 404
        if entrepot.principal:
            return {'message': 'Impossible de supprimer l\'entrepôt principal'}, 400
        entrepot.delete()
        return {'message': 'Entrepôt supprimé'}, 200


@ns.route('/<int:entrepot_id>/stocks')
class EntrepotStockResource(Resource):
    @ns.doc('list_entrepot_stocks')
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self, entrepot_id):
        """Liste tous les stocks dans un entrepôt"""
        entrepot = Entrepot.query.get(entrepot_id)
        if not entrepot:
            return {'message': 'Entrepôt non trouvé'}, 404
        stocks = entrepot.stocks.all()
        return {'stocks': [s.to_dict() for s in stocks], 'total': len(stocks)}, 200


@ns.route('/stocks')
class StockEntrepotListResource(Resource):
    @ns.doc('list_stock_entrepots')
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        """Liste tous les stocks par entrepôt"""
        stocks = StockEntrepot.query.all()
        return {'stocks': [s.to_dict() for s in stocks], 'total': len(stocks)}, 200

    @ns.doc('create_stock_entrepot')
    @permission_required('stock.update')
    @tenant_required_readonly
    def post(self):
        """Crée ou met à jour un stock dans un entrepôt"""
        data = request.get_json()
        produit_id = data['produit_id']
        entrepot_id = data['entrepot_id']
        
        produit = Produit.query.get(produit_id)
        if not produit:
            return {'message': 'Produit non trouvé'}, 404
        
        entrepot = Entrepot.query.get(entrepot_id)
        if not entrepot:
            return {'message': 'Entrepôt non trouvé'}, 404
        
        stock = StockEntrepot.query.filter_by(
            produit_id=produit_id,
            entrepot_id=entrepot_id
        ).first()
        
        if stock:
            stock.quantite = data.get('quantite', stock.quantite)
            if 'seuil_min' in data:
                stock.seuil_min = data['seuil_min']
            if 'seuil_max' in data:
                stock.seuil_max = data['seuil_max']
        else:
            stock = StockEntrepot(
                produit_id=produit_id,
                entrepot_id=entrepot_id,
                quantite=data.get('quantite', 0),
                seuil_min=data.get('seuil_min', 0),
                seuil_max=data.get('seuil_max'),
            )
            db.session.add(stock)
        
        stock.save()
        return stock.to_dict(), 200


@ns.route('/stocks/<int:stock_id>')
@ns.route('/stocks/<int:stock_id>')
class StockEntrepotResource(Resource):
    @ns.doc('get_stock_entrepot')
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self, stock_id):
        """Récupère un stock par son ID"""
        stock = StockEntrepot.query.get(stock_id)
        if not stock:
            return {'message': 'Stock non trouvé'}, 404
        return stock.to_dict(), 200

    @ns.doc('update_stock_entrepot')
    @permission_required('stock.update')
    @tenant_required_readonly
    def put(self, stock_id):
        """Met à jour un stock"""
        stock = StockEntrepot.query.get(stock_id)
        if not stock:
            return {'message': 'Stock non trouvé'}, 404
        data = request.get_json()
        for attr in ['quantite', 'seuil_min', 'seuil_max']:
            if attr in data:
                setattr(stock, attr, data[attr])
        stock.save()
        return stock.to_dict(), 200

    @ns.doc('delete_stock_entrepot')
    @permission_required('stock.delete')
    @tenant_required_readonly
    def delete(self, stock_id):
        """Supprime un stock"""
        stock = StockEntrepot.query.get(stock_id)
        if not stock:
            return {'message': 'Stock non trouvé'}, 404
        stock.delete()
        return {'message': 'Stock supprimé'}, 200