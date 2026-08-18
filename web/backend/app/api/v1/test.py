from flask_restx import Namespace, Resource

ns = Namespace('test', description='Test API')

@ns.route('/')
class TestResource(Resource):
    def get(self):
        return {'message': 'API fonctionne'}, 200

