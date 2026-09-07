from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.services.livraison_service import LivreurService, VehiculeService, ItineraireService, LivraisonService
from app.models.livreur import Livreur
from app.models.utilisateur import Utilisateur, Role
from app import db

ns_livreurs = Namespace('livreurs', description='Gestion des livreurs')
ns_vehicules = Namespace('vehicules', description='Gestion des vehicules')
ns_itineraires = Namespace('itineraires', description='Gestion des itineraires')
ns_livraisons = Namespace('livraisons', description='Gestion des livraisons')


def _get_current_livreur():
    from flask_jwt_extended import get_jwt_identity
    from app.security.roles import has_permission
    user_id = get_jwt_identity()
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    user = db.session.get(Utilisateur, user_id)
    if not user:
        return None
    if user.role != Role.LIVREUR:
        return None
    return LivreurService.get_by_user(user_id)


def _require_livreur():
    livreur = _get_current_livreur()
    if not livreur:
        return {'message': 'Acces refuse : profil livreur requis'}, 403
    return None, livreur

@ns_livreurs.route('/')
class LivreurList(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        livreurs, total = LivreurService.get_all()
        return {'livreurs': [l.to_dict() for l in livreurs], 'total': total}, 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.create(data)
        return livreur.to_dict(), 201

@ns_livreurs.route('/<int:id>')
class LivreurResource(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self, id):
        livreur = LivreurService.get_by_id(id)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.update(id, data)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def delete(self, id):
        success = LivreurService.delete(id)
        if not success:
            return {'message': 'Livreur non trouve'}, 404
        return {'message': 'Livreur supprime'}, 200

@ns_vehicules.route('/')
class VehiculeList(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        vehicules, total = VehiculeService.get_all()
        return {'vehicules': [v.to_dict() for v in vehicules], 'total': total}, 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.create(data)
        return vehicule.to_dict(), 201

@ns_vehicules.route('/<int:id>')
class VehiculeResource(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self, id):
        vehicule = VehiculeService.get_by_id(id)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.update(id, data)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def delete(self, id):
        success = VehiculeService.delete(id)
        if not success:
            return {'message': 'Vehicule non trouve'}, 404
        return {'message': 'Vehicule supprime'}, 200

@ns_itineraires.route('/')
class ItineraireList(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        itineraires, total = ItineraireService.get_all()
        return {'itineraires': [i.to_dict() for i in itineraires], 'total': total}, 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.create(data)
        return itineraire.to_dict(), 201

@ns_itineraires.route('/<int:id>')
class ItineraireResource(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self, id):
        itineraire = ItineraireService.get_by_id(id)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.update(id, data)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def delete(self, id):
        success = ItineraireService.delete(id)
        if not success:
            return {'message': 'Itineraire non trouve'}, 404
        return {'message': 'Itineraire supprime'}, 200

@ns_livraisons.route('/')
class LivraisonList(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        livraisons, total = LivraisonService.get_all()
        return {'livraisons': [l.to_dict() for l in livraisons], 'total': total}, 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        try:
            livraison = LivraisonService.create(data)
        except ValueError as e:
            return {'message': str(e)}, 400
        return livraison.to_dict(), 201

@ns_livraisons.route('/<int:id>')
class LivraisonResource(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self, id):
        livraison = LivraisonService.get_by_id(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        try:
            livraison = LivraisonService.update(id, data)
        except ValueError as e:
            return {'message': str(e)}, 400
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def delete(self, id):
        success = LivraisonService.delete(id)
        if not success:
            return {'message': 'Livraison non trouvee'}, 404
        return {'message': 'Livraison supprimee'}, 200

@ns_livraisons.route('/<int:id>/suivi')
class LivraisonSuivi(Resource):
    @permission_required('delivery.update')
    @tenant_required_readonly
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
    @permission_required('delivery.view')
    @tenant_required_readonly
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
    @permission_required('delivery.update')
    @tenant_required_readonly
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
    @permission_required('delivery.update')
    @tenant_required_readonly
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
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        stats = LivraisonService.get_stats()
        return stats, 200


@ns_livraisons.route('/<int:id>/avancer')
class LivraisonAvancer(Resource):
    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self, id):
        livraison = LivraisonService.avancer_statut(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200


@ns_livreurs.route('/moi')
class LivreurMoi(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        err, livreur = _require_livreur()
        if err:
            return err, 403
        return livreur.to_dict(), 200


@ns_livreurs.route('/moi/livraisons')
class LivreurMoiLivraisons(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self):
        err, livreur = _require_livreur()
        if err:
            return err, 403
        livraisons, total = LivraisonService.get_for_livreur(livreur.id)
        return {'livraisons': [l.to_dict() for l in livraisons], 'total': total}, 200


@ns_livreurs.route('/moi/livraisons/<int:id>')
class LivreurMoiLivraisonResource(Resource):
    @permission_required('delivery.view')
    @tenant_required_readonly
    def get(self, id):
        err, livreur = _require_livreur()
        if err:
            return err, 403
        livraison = LivraisonService.get_for_livreur_by_id(livreur.id, id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self, id):
        err, livreur = _require_livreur()
        if err:
            return err, 403
        livraison = LivraisonService.get_for_livreur_by_id(livreur.id, id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        from flask import request
        data = request.get_json() or {}
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


@ns_livreurs.route('/moi/livraisons/<int:id>/statut')
class LivreurMoiLivraisonStatut(Resource):
    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self, id):
        err, livreur = _require_livreur()
        if err:
            return err, 403
        livraison = LivraisonService.get_for_livreur_by_id(livreur.id, id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
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


@ns_livreurs.route('/<int:id>/associer-utilisateur')
class LivreurAssocierUtilisateur(Resource):
    @permission_required('delivery.update')
    @tenant_required_readonly
    def post(self, id):
        from flask import request
        from app.security.roles import is_admin, is_super_admin
        from flask_jwt_extended import get_jwt_identity

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        current_user = db.session.get(Utilisateur, user_id)
        if not current_user or not (is_super_admin(current_user.role) or is_admin(current_user.role)):
            return {'message': 'Acces administrateur requis'}, 403

        livreur = LivreurService.get_by_id(id)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404

        data = request.get_json() or {}
        utilisateur_id = data.get('utilisateur_id')
        if not utilisateur_id:
            return {'message': 'utilisateur_id requis'}, 400
        if isinstance(utilisateur_id, str) and utilisateur_id.isdigit():
            utilisateur_id = int(utilisateur_id)

        utilisateur = Utilisateur.query.execution_options(_skip_tenant_filter=True).get(utilisateur_id)
        if not utilisateur:
            return {'message': 'Utilisateur non trouve'}, 404

        if utilisateur.tenant_id != livreur.tenant_id:
            return {'message': 'Cross-tenant interdit : le livreur et l\'utilisateur doivent appartenir au meme tenant'}, 403

        existing = Livreur.query.filter(
            Livreur.utilisateur_id == utilisateur_id,
            Livreur.is_active == True,
            Livreur.id != livreur.id,
        ).first()
        if existing:
            return {'message': 'Cet utilisateur est deja associe a un autre livreur'}, 409

        livreur.utilisateur_id = utilisateur_id
        db.session.commit()
        return livreur.to_dict(), 200
