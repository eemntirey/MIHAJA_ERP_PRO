from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required_readonly
from app.services.produit_service import ProduitService
from app.services.achat_service import CommandeAchatService, ReceptionAchatService
from app.services.devis_avoir_service import DevisService, BonLivraisonService, AvoirService

ns_commandes_achat = Namespace('commandes-achat', description='Gestion des commandes d\'achat')
ns_receptions = Namespace('receptions', description='Gestion des receptions')
ns_devis = Namespace('devis', description='Gestion des devis')
ns_bons_livraison = Namespace('bons-livraison', description='Gestion des bons de livraison')
ns_avoirs = Namespace('avoirs', description='Gestion des avoirs')

@ns_commandes_achat.route('/')
class CommandeAchatList(Resource):
    @tenant_required_readonly
    def get(self):
        commandes, total = CommandeAchatService.get_all()
        return {'commandes': [c.to_dict() for c in commandes], 'total': total}, 200

    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        commande = CommandeAchatService.create(data)
        return commande.to_dict(), 201

@ns_commandes_achat.route('/<int:id>')
class CommandeAchatResource(Resource):
    @tenant_required_readonly
    def get(self, id):
        commande = CommandeAchatService.get_by_id(id)
        if not commande:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return commande.to_dict(), 200

    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        commande = CommandeAchatService.update(id, data)
        if not commande:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return commande.to_dict(), 200

    @tenant_required_readonly
    def delete(self, id):
        success = CommandeAchatService.delete(id)
        if not success:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return {'message': 'Commande d\'achat supprimee'}, 200

@ns_receptions.route('/')
class ReceptionList(Resource):
    @tenant_required_readonly
    def get(self):
        receptions, total = ReceptionAchatService.get_all()
        return {'receptions': [r.to_dict() for r in receptions], 'total': total}, 200

    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        reception = ReceptionAchatService.create(data)
        return reception.to_dict(), 201

@ns_receptions.route('/<int:id>')
class ReceptionResource(Resource):
    @tenant_required_readonly
    def get(self, id):
        reception = ReceptionAchatService.get_by_id(id)
        if not reception:
            return {'message': 'Reception non trouvee'}, 404
        return reception.to_dict(), 200

    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        reception = ReceptionAchatService.update(id, data)
        if not reception:
            return {'message': 'Reception non trouvee'}, 404
        return reception.to_dict(), 200

    @tenant_required_readonly
    def delete(self, id):
        success = ReceptionAchatService.delete(id)
        if not success:
            return {'message': 'Reception non trouvee'}, 404
        return {'message': 'Reception supprimee'}, 200

@ns_devis.route('/')
class DevisList(Resource):
    @tenant_required_readonly
    def get(self):
        devis_list, total = DevisService.get_all()
        return {'devis': [d.to_dict() for d in devis_list], 'total': total}, 200

    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        devis = DevisService.create(data)
        return devis.to_dict(), 201

@ns_devis.route('/<int:id>')
class DevisResource(Resource):
    @tenant_required_readonly
    def get(self, id):
        devis = DevisService.get_by_id(id)
        if not devis:
            return {'message': 'Devis non trouve'}, 404
        return devis.to_dict(), 200

    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        devis = DevisService.update(id, data)
        if not devis:
            return {'message': 'Devis non trouve'}, 404
        return devis.to_dict(), 200

    @tenant_required_readonly
    def delete(self, id):
        success = DevisService.delete(id)
        if not success:
            return {'message': 'Devis non trouve'}, 404
        return {'message': 'Devis supprime'}, 200

@ns_devis.route('/<int:id>/convertir')
class DevisConvertir(Resource):
    @tenant_required_readonly
    def post(self, id):
        vente = DevisService.convertir_en_vente(id)
        if not vente:
            return {'message': 'Devis non trouve'}, 404
        return vente.to_dict(), 201

@ns_bons_livraison.route('/')
class BonLivraisonList(Resource):
    @tenant_required_readonly
    def get(self):
        bls, total = BonLivraisonService.get_all()
        return {'bons_livraison': [b.to_dict() for b in bls], 'total': total}, 200

    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        bl = BonLivraisonService.create(data)
        return bl.to_dict(), 201

@ns_bons_livraison.route('/<int:id>')
class BonLivraisonResource(Resource):
    @tenant_required_readonly
    def get(self, id):
        bl = BonLivraisonService.get_by_id(id)
        if not bl:
            return {'message': 'Bon de livraison non trouve'}, 404
        return bl.to_dict(), 200

    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        bl = BonLivraisonService.update(id, data)
        if not bl:
            return {'message': 'Bon de livraison non trouve'}, 404
        return bl.to_dict(), 200

    @tenant_required_readonly
    def delete(self, id):
        success = BonLivraisonService.delete(id)
        if not success:
            return {'message': 'Bon de livraison non trouve'}, 404
        return {'message': 'Bon de livraison supprime'}, 200

@ns_avoirs.route('/')
class AvoirList(Resource):
    @tenant_required_readonly
    def get(self):
        avoirs, total = AvoirService.get_all()
        return {'avoirs': [a.to_dict() for a in avoirs], 'total': total}, 200

    @tenant_required_readonly
    def post(self):
        from flask import request
        data = request.get_json()
        avoir = AvoirService.create(data)
        return avoir.to_dict(), 201

@ns_avoirs.route('/<int:id>')
class AvoirResource(Resource):
    @tenant_required_readonly
    def get(self, id):
        avoir = AvoirService.get_by_id(id)
        if not avoir:
            return {'message': 'Avoir non trouve'}, 404
        return avoir.to_dict(), 200

    @tenant_required_readonly
    def put(self, id):
        from flask import request
        data = request.get_json()
        avoir = AvoirService.update(id, data)
        if not avoir:
            return {'message': 'Avoir non trouve'}, 404
        return avoir.to_dict(), 200

    @tenant_required_readonly
    def delete(self, id):
        success = AvoirService.delete(id)
        if not success:
            return {'message': 'Avoir non trouve'}, 404
        return {'message': 'Avoir supprime'}, 200
