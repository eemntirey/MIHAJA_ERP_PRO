from flask_restx import Namespace, Resource, fields
from app.services.client_service import ClientService
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits
from app.security.permissions import permission_required
from sqlalchemy.exc import IntegrityError
from flask import request
from app import db

ns = Namespace('clients', description='Gestion des clients')

client_model = ns.model('Client', {
    'code': fields.String(required=True, description='Code client unique'),
    'raison_sociale': fields.String(description='Raison sociale'),
    'nom': fields.String(description='Nom'),
    'prenom': fields.String(description='Prénom'),
    'type': fields.String(description='Type de client (boutique, epicerie, revendeur, semi_grossiste, grossiste, supermarche, restaurant, hotel, entreprise, institution, particulier)', default='particulier'),
    'secteur': fields.String(description='Secteur d\'activité', default='autre'),
    'siret': fields.String(description='SIRET'),
    'numero_tva': fields.String(description='Numéro TVA'),
    'numero_rcs': fields.String(description='Numéro RCS'),
    'email': fields.String(description='Email'),
    'email_secondaire': fields.String(description='Email secondaire'),
    'telephone': fields.String(description='Téléphone'),
    'telephone_secondaire': fields.String(description='Téléphone secondaire'),
    'mobile': fields.String(description='Mobile'),
    'fax': fields.String(description='Fax'),
    'site_web': fields.String(description='Site web'),
    'adresse_facturation': fields.String(description='Adresse de facturation'),
    'complement_facturation': fields.String(description='Complément adresse facturation'),
    'code_postal_facturation': fields.String(description='Code postal facturation'),
    'ville_facturation': fields.String(description='Ville facturation'),
    'pays_facturation': fields.String(description='Pays facturation', default='Madagascar'),
    'adresse_livraison': fields.String(description='Adresse de livraison'),
    'complement_livraison': fields.String(description='Complément adresse livraison'),
    'code_postal_livraison': fields.String(description='Code postal livraison'),
    'ville_livraison': fields.String(description='Ville livraison'),
    'pays_livraison': fields.String(description='Pays livraison', default='Madagascar'),
    'contact_nom': fields.String(description='Nom du contact principal'),
    'contact_prenom': fields.String(description='Prénom du contact principal'),
    'contact_fonction': fields.String(description='Fonction du contact'),
    'contact_email': fields.String(description='Email du contact'),
    'contact_telephone': fields.String(description='Téléphone du contact'),
    'conditions_paiement': fields.String(description='Conditions de paiement', default='30 jours'),
    'remise_standard': fields.Float(description='Remise standard', default=0),
    'plafond_credit': fields.Float(description='Plafond de crédit'),
    'echeance_credit': fields.Integer(description='Échéance crédit en jours', default=30),
    'commercial_id': fields.Integer(description='ID du commercial'),
    'est_favori': fields.Boolean(description='Client favori', default=False),
    'est_actif': fields.Boolean(description='Client actif', default=True),
    'est_bloque': fields.Boolean(description='Client bloqué', default=False),
    'note': fields.Integer(description='Note 1-5'),
})

@ns.route('/')
class ClientListResource(Resource):
    @ns.doc('list_clients')
    @tenant_required
    def get(self):
        """Liste tous les clients"""
        try:
            clients, total = ClientService.get_all()
            return {'clients': [c.to_dict() for c in clients], 'total': total}, 200
        except Exception:
            current_app.logger.exception('Erreur lors de la liste des clients')
            return {'clients': [], 'total': 0}, 500
    
    @ns.doc('create_client')
    @tenant_required
    @check_plan_limits('clients')
    @permission_required('client.create')
    @ns.expect(client_model)
    def post(self):
        """Crée un nouveau client"""
        data = request.get_json()
        if not data:
            return {'message': 'Données JSON requises'}, 400
        
        if not data.get('code'):
            return {'message': 'Le code client est requis'}, 400
        
        try:
            client = ClientService.create(data)
            return client.to_dict(), 201
        except ValueError as e:
            return {'message': str(e)}, 400
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Contrainte de base de données violée'}, 400
        except Exception:
            current_app.logger.exception('Erreur lors de la création du client')
            return {'message': 'Erreur lors de la création du client'}, 400

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