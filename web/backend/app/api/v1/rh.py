from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.rh_service import EmployeService, PresenceService, SalaireService, PrimeService

ns_employes = Namespace('employes', description='Gestion des employes')
ns_presences = Namespace('presences', description='Gestion des presences')
ns_salaires = Namespace('salaires', description='Gestion des salaires')
ns_primes = Namespace('primes', description='Gestion des primes')

@ns_employes.route('/')
class EmployeList(Resource):
    @tenant_required
    def get(self):
        employes, total = EmployeService.get_all()
        return {'employes': [e.to_dict() for e in employes], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        employe = EmployeService.create(data)
        return employe.to_dict(), 201

@ns_employes.route('/<int:id>')
class EmployeResource(Resource):
    @tenant_required
    def get(self, id):
        employe = EmployeService.get_by_id(id)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        employe = EmployeService.update(id, data)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = EmployeService.delete(id)
        if not success:
            return {'message': 'Employe non trouve'}, 404
        return {'message': 'Employe supprime'}, 200

@ns_presences.route('/')
class PresenceList(Resource):
    @tenant_required
    def get(self):
        presences, total = PresenceService.get_all()
        return {'presences': [p.to_dict() for p in presences], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        presence = PresenceService.create(data)
        return presence.to_dict(), 201

@ns_presences.route('/<int:id>')
class PresenceResource(Resource):
    @tenant_required
    def get(self, id):
        presence = PresenceService.get_by_id(id)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        presence = PresenceService.update(id, data)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = PresenceService.delete(id)
        if not success:
            return {'message': 'Presence non trouvee'}, 404
        return {'message': 'Presence supprimee'}, 200

@ns_salaires.route('/')
class SalaireList(Resource):
    @tenant_required
    def get(self):
        salaires, total = SalaireService.get_all()
        return {'salaires': [s.to_dict() for s in salaires], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        salaire = SalaireService.create(data)
        return salaire.to_dict(), 201

@ns_salaires.route('/<int:id>')
class SalaireResource(Resource):
    @tenant_required
    def get(self, id):
        salaire = SalaireService.get_by_id(id)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        salaire = SalaireService.update(id, data)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = SalaireService.delete(id)
        if not success:
            return {'message': 'Salaire non trouve'}, 404
        return {'message': 'Salaire supprime'}, 200

@ns_primes.route('/')
class PrimeList(Resource):
    @tenant_required
    def get(self):
        primes, total = PrimeService.get_all()
        return {'primes': [p.to_dict() for p in primes], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        prime = PrimeService.create(data)
        return prime.to_dict(), 201

@ns_primes.route('/<int:id>')
class PrimeResource(Resource):
    @tenant_required
    def get(self, id):
        prime = PrimeService.get_by_id(id)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        prime = PrimeService.update(id, data)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = PrimeService.delete(id)
        if not success:
            return {'message': 'Prime non trouvee'}, 404
        return {'message': 'Prime supprimee'}, 200
