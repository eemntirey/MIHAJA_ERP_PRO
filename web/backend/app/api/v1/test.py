from flask_restx import Namespace, Resource

ns = Namespace('test', description='Test API (development only)')

# Enregistrer uniquement en mode développement/testing
import os
_is_dev = os.environ.get('FLASK_ENV') in ('development', 'testing', '') or os.environ.get('DEBUG') == 'True'

if _is_dev:
    @ns.route('/')
    class TestResource(Resource):
        def get(self):
            return {'message': 'API fonctionne'}, 200