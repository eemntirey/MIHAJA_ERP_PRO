from flask_restx import Namespace, Resource
from flask import current_app

ns = Namespace('test', description='Test API (development only)')

@ns.route('/')
class TestResource(Resource):
    def get(self):
        if current_app.config.get('DEBUG', False) or current_app.config.get('TESTING', False):
            return {'message': 'API fonctionne'}, 200
        return {'message': 'Endpoint non disponible en production'}, 404

