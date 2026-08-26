from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.utilisateur import Role
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.services.abonnement_service import AbonnementService
from app import db
from datetime import datetime
from app.security.roles import is_super_admin

ns = Namespace('abonnements', description='Gestion des abonnements')


def _get_tenant_id_from_jwt():
    claims = get_jwt() or {}
    return claims.get('tenant_id')


@ns.route('/demander')
class DemanderAbonnement(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        data['tenant_id'] = tenant_id
        try:
            abonnement, paiement = AbonnementService.create_abonnement(data)
            response = {
                'abonnement': abonnement.to_dict(),
            }
            if paiement:
                response['paiement'] = paiement.to_dict()
            return response, 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400


@ns.route('/mon-abonnement')
class MonAbonnement(Resource):
    @jwt_required()
    def get(self):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        abonnement = AbonnementService.get_active_by_tenant(tenant_id)
        if not abonnement:
            return {'abonnement': None}, 200
        return {'abonnement': abonnement.to_dict()}, 200


@ns.route('/mon-historique')
class MonHistorique(Resource):
    @jwt_required()
    def get(self):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        items, total = AbonnementService.get_history_by_tenant(tenant_id, page, per_page)
        return {
            'abonnements': [a.to_dict() for a in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }, 200


@ns.route('/<int:id>/payer')
class PayerAbonnement(Resource):
    @jwt_required()
    def post(self, id):
        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        data = request.get_json() or {}

        paiement = Paiement.query.filter_by(
            tenant_id=tenant_id,
            type=TypePaiement.ABONNEMENT,
            is_active=True
        ).order_by(Paiement.created_at.desc()).first()

        if paiement:
            paiement.statut = StatutPaiement.CONFIRME
            paiement.date_paiement = datetime.utcnow()
            paiement.id_transaction_externe = data.get('id_transaction_externe')
            db.session.commit()

        abonnement.statut = StatutAbonnement.ACTIF
        abonnement.save()

        return {
            'abonnement': abonnement.to_dict(),
            'paiement': paiement.to_dict() if paiement else None
        }, 200


@ns.route('/<int:id>/renouveler')
class RenouvelerAbonnement(Resource):
    @jwt_required()
    def post(self, id):
        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        result = AbonnementService.renew_subscription(id)
        if not result:
            return {'message': 'Abonnement non trouve'}, 404
        abonnement, paiement = result
        return {
            'abonnement': abonnement.to_dict(),
            'paiement': paiement.to_dict()
        }, 200


@ns.route('/paiements/<int:paiement_id>/valider')
class ValiderPaiementHorsLigne(Resource):
    @jwt_required()
    def post(self, paiement_id):
        user_id = get_jwt_identity()
        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur or not is_super_admin(utilisateur.role):
            return {'message': 'Acces super administrateur requis'}, 403

        paiement = db.session.get(Paiement, paiement_id)
        if not paiement or not paiement.is_active:
            return {'message': 'Paiement non trouve'}, 404

        if paiement.statut == StatutPaiement.SUCCESS:
            return {'message': 'Paiement deja valide'}, 400

        paiement.statut = StatutPaiement.SUCCESS
        paiement.date_paiement = datetime.utcnow()
        db.session.commit()

        abonnement = None
        if paiement.subscription_id:
            abonnement = db.session.get(Abonnement, paiement.subscription_id)
            if abonnement and abonnement.statut != StatutAbonnement.ACTIF:
                abonnement.statut = StatutAbonnement.ACTIF
                if not abonnement.date_debut:
                    abonnement.date_debut = datetime.utcnow()
                if not abonnement.date_fin:
                    from datetime import timedelta
                    abonnement.date_fin = datetime.utcnow() + timedelta(days=30)
                db.session.add(abonnement)

        tenant = None
        if abonnement and abonnement.tenant_id:
            tenant = db.session.get(Tenant, abonnement.tenant_id)
            if tenant and tenant.statut != StatutTenant.ACTIF:
                tenant.statut = StatutTenant.ACTIF
                tenant.date_abonnement = datetime.utcnow()
                db.session.add(tenant)

        db.session.commit()

        return {
            'paiement': paiement.to_dict(),
            'abonnement': abonnement.to_dict() if abonnement else None,
            'tenant': tenant.to_dict() if tenant else None,
        }, 200


@ns.route('/')
class AbonnementList(Resource):
    @jwt_required()
    def get(self):
        from app.models.utilisateur import Utilisateur
        user_id = get_jwt_identity()
        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur or not is_super_admin(utilisateur.role):
            return {'message': 'Acces super administrateur requis'}, 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        items, total = AbonnementService.get_all_subscriptions(tenant_id=None, page=page, per_page=per_page)
        return {
            'abonnements': [a.to_dict() for a in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }, 200


@ns.route('/historique/<int:tenant_id>')
class HistoriqueTenant(Resource):
    @jwt_required()
    def get(self, tenant_id):
        from app.models.utilisateur import Utilisateur
        user_id = get_jwt_identity()
        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur or not is_super_admin(utilisateur.role):
            return {'message': 'Acces super administrateur requis'}, 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        items, total = AbonnementService.get_history_by_tenant(tenant_id, page, per_page)
        return {
            'abonnements': [a.to_dict() for a in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }, 200
