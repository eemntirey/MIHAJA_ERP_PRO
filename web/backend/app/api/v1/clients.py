from flask_restx import Namespace, Resource
from app.services.client_service import ClientService
from app.security.tenant import tenant_required

ns = Namespace('clients', description='Gestion des clients')

@ns.route('/')
class ClientListResource(Resource):
    @ns.doc('list_clients')
    @tenant_required
    def get(self):
        """Liste tous les clients"""
        try:
            clients, total = ClientService.get_all()
            return {'clients': [c.to_dict() for c in clients], 'total': total}, 200
        except Exception as e:
            return {'clients': [], 'total': 0, 'message': str(e)}, 500
    
    @ns.doc('create_client')
    @tenant_required
    def post(self):
        """Crée un nouveau client"""
        from flask import request
        data = request.get_json()
        client = ClientService.create(data)
        return client.to_dict(), 201

@ns.route('/<int:client_id>')
class ClientResource(Resource):
    @ns.doc('get_client')
    @tenant_required
    def get(self, client_id):
        """Récupère un client par son ID"""
        client = ClientService.get_by_id(client_id)
        if not client:
            return {'message': 'Client non trouve'}, 404
        return client.to_dict(), 200
    
    @ns.doc('update_client')
    @tenant_required
    def put(self, client_id):
        """Met à jour un client"""
        from flask import request
        data = request.get_json()
        client = ClientService.update(client_id, data)
        if not client:
            return {'message': 'Client non trouve'}, 404
        return client.to_dict(), 200
    
    @ns.doc('delete_client')
    @tenant_required
    def delete(self, client_id):
        """Supprime un client"""
        success = ClientService.delete(client_id)
        if not success:
            return {'message': 'Client non trouve'}, 404
        return {'message': 'Client supprime'}, 200