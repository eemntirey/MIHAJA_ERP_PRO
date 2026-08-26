from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.livraison_service import LivreurService, VehiculeService, ItineraireService, LivraisonService

ns_livreurs = Namespace('livreurs', description='Gestion des livreurs')
ns_vehicules = Namespace('vehicules', description='Gestion des vehicules')
ns_itineraires = Namespace('itineraires', description='Gestion des itineraires')
ns_livraisons = Namespace('livraisons', description='Gestion des livraisons')

@ns_livreurs.route('/')
class LivreurList(Resource):
    @tenant_required
    def get(self):
        livreurs, total = LivreurService.get_all()
        return {'livreurs': [l.to_dict() for l in livreurs], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.create(data)
        return livreur.to_dict(), 201

@ns_livreurs.route('/<int:id>')
class LivreurResource(Resource):
    @tenant_required
    def get(self, id):
        livreur = LivreurService.get_by_id(id)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.update(id, data)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = LivreurService.delete(id)
        if not success:
            return {'message': 'Livreur non trouve'}, 404
        return {'message': 'Livreur supprime'}, 200

@ns_vehicules.route('/')
class VehiculeList(Resource):
    @tenant_required
    def get(self):
        vehicules, total = VehiculeService.get_all()
        return {'vehicules': [v.to_dict() for v in vehicules], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.create(data)
        return vehicule.to_dict(), 201

@ns_vehicules.route('/<int:id>')
class VehiculeResource(Resource):
    @tenant_required
    def get(self, id):
        vehicule = VehiculeService.get_by_id(id)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.update(id, data)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = VehiculeService.delete(id)
        if not success:
            return {'message': 'Vehicule non trouve'}, 404
        return {'message': 'Vehicule supprime'}, 200

@ns_itineraires.route('/')
class ItineraireList(Resource):
    @tenant_required
    def get(self):
        itineraires, total = ItineraireService.get_all()
        return {'itineraires': [i.to_dict() for i in itineraires], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.create(data)
        return itineraire.to_dict(), 201

@ns_itineraires.route('/<int:id>')
class ItineraireResource(Resource):
    @tenant_required
    def get(self, id):
        itineraire = ItineraireService.get_by_id(id)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.update(id, data)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = ItineraireService.delete(id)
        if not success:
            return {'message': 'Itineraire non trouve'}, 404
        return {'message': 'Itineraire supprime'}, 200

@ns_livraisons.route('/')
class LivraisonList(Resource):
    @tenant_required
    def get(self):
        livraisons, total = LivraisonService.get_all()
        return {'livraisons': [l.to_dict() for l in livraisons], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        livraison = LivraisonService.create(data)
        return livraison.to_dict(), 201

@ns_livraisons.route('/<int:id>')
class LivraisonResource(Resource):
    @tenant_required
    def get(self, id):
        livraison = LivraisonService.get_by_id(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        livraison = LivraisonService.update(id, data)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = LivraisonService.delete(id)
        if not success:
            return {'message': 'Livraison non trouvee'}, 404
        return {'message': 'Livraison supprimee'}, 200

@ns_livraisons.route('/<int:id>/suivi')
class LivraisonSuivi(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json()
        try:
            suivi = LivraisonService.add_suivi(
                id,
                data.get('statut'),
                data.get('commentaire', ''),
                data.get('localisation_lat'),
                data.get('localisation_lng'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not suivi:
            return {'message': 'Livraison non trouvee'}, 404
        return suivi.to_dict(), 201

@ns_livraisons.route('/<int:id>/suivis')
class LivraisonSuivis(Resource):
    @tenant_required
    def get(self, id):
        from app.models.suivi_livraison import SuiviLivraison
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = SuiviLivraison.query.filter_by(livraison_id=id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        suivis = query.order_by(SuiviLivraison.date_mise_a_jour.desc()).all()
        return {'suivis': [s.to_dict() for s in suivis]}, 200


@ns_livraisons.route('/<int:id>/assigner')
class LivraisonAssigner(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json() or {}
        try:
            livraison = LivraisonService.assigner(
                id,
                data.get('livreur_id'),
                data.get('vehicule_id'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200


@ns_livraisons.route('/<int:id>/statut')
class LivraisonStatut(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json() or {}
        try:
            suivi = LivraisonService.passer_au_statut(
                id,
                data.get('statut'),
                data.get('commentaire', ''),
                data.get('localisation_lat'),
                data.get('localisation_lng'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not suivi:
            return {'message': 'Livraison non trouvee'}, 404
        return suivi.to_dict(), 201


@ns_livraisons.route('/stats')
class LivraisonStats(Resource):
    @tenant_required
    def get(self):
        stats = LivraisonService.get_stats()
        return stats, 200


@ns_livraisons.route('/<int:id>/avancer')
class LivraisonAvancer(Resource):
    @tenant_required
    def post(self, id):
        livraison = LivraisonService.avancer_statut(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200
