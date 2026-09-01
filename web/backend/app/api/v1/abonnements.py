from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.utilisateur import Role, Utilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.services.abonnement_service import AbonnementService
from app import db
from datetime import datetime
from app.security.roles import is_super_admin, is_admin
from app.websockets.socket_events import broadcast_to_tenant

ns = Namespace('abonnements', description='Gestion des abonnements')


def _get_tenant_id_from_jwt():
    claims = get_jwt() or {}
    return claims.get('tenant_id')


def _is_principal_admin(utilisateur, tenant):
    """§10/§11 : seul l'Admin principal du Tenant peut gérer l'abonnement.

    Le droit est lié à l'identité (admin_principal_id du Tenant) et non
    seulement au rôle 'admin'. Repli (legacy) sur le rôle admin si le Tenant
    n'a pas encore d'admin principal enregistré.
    """
    if not utilisateur or not tenant:
        return False
    if tenant.admin_principal_id is not None:
        return tenant.admin_principal_id == utilisateur.id
    return bool(utilisateur.is_admin)


@ns.route('/demander')
class DemanderAbonnement(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        user_id = get_jwt_identity()
        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur:
            return {'message': 'Utilisateur non trouve'}, 401

        if not is_super_admin(utilisateur.role):
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant or not _is_principal_admin(utilisateur, tenant):
                return {'message': 'Seul l\'administrateur principal du tenant peut demander un abonnement'}, 403

        data['tenant_id'] = tenant_id
        try:
            abonnement, paiement = AbonnementService.create_abonnement(data)
            response = {
                'abonnement': abonnement.to_dict(),
            }
            if paiement:
                response['paiement'] = paiement.to_dict()
            try:
                broadcast_to_tenant(tenant_id, 'subscription:updated', abonnement.to_dict())
            except Exception:
                pass
            return response, 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400


@ns.route('/mon-abonnement')
class MonAbonnement(Resource):
    @jwt_required()
    def get(self):
        claims = get_jwt() or {}
        user_id = get_jwt_identity()
        utilisateur = db.session.get(Utilisateur, user_id)

        if utilisateur and is_super_admin(utilisateur.role):
            return {'abonnement': None, 'can_renew': True, 'tenant': None}, 200

        tenant_id = claims.get('tenant_id')
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        try:
            tenant = db.session.get(Tenant, tenant_id)
        except Exception:
            current_app.logger.exception(
                "Lecture du tenant %s impossible (donnees invalides)", tenant_id
            )
            tenant = None
        abonnement = AbonnementService.get_active_by_tenant(tenant_id)
        can_renew = _is_principal_admin(utilisateur, tenant)

        if not abonnement:
            tenant_summary = None
            if tenant:
                users_count = Utilisateur.query.filter_by(
                    tenant_id=tenant.id, is_active=True
                ).count()
                employees_count = Utilisateur.query.filter(
                    Utilisateur.tenant_id == tenant.id,
                    Utilisateur.role.in_([Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER]),
                    Utilisateur.is_active == True,
                ).count()
                from app.security.plans import get_plan_config
                plan_cfg = get_plan_config(tenant.plan)
                tenant_summary = {
                    'id': tenant.id,
                    'nom': tenant.nom,
                    'plan': tenant.plan,
                    'statut': (
                        tenant.statut.value
                        if hasattr(tenant.statut, 'value')
                        else tenant.statut
                    ),
                    'max_utilisateurs': plan_cfg.get('max_utilisateurs'),
                    'max_employees': plan_cfg.get('max_employees'),
                    'users_count': users_count,
                    'employees_count': employees_count,
                }
            return {'abonnement': None, 'can_renew': can_renew, 'tenant': tenant_summary}, 200

        else:
            if tenant is None:
                return {'abonnement': abonnement.to_dict(), 'can_renew': can_renew, 'tenant': None}, 200
            users_count = Utilisateur.query.filter_by(
                tenant_id=tenant.id, is_active=True
            ).count()
            employees_count = Utilisateur.query.filter(
                Utilisateur.tenant_id == tenant.id,
                Utilisateur.role.in_([Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER]),
                Utilisateur.is_active == True,
            ).count()
            from app.security.plans import resolve_limits
            resolved = resolve_limits(tenant, abonnement) if tenant else {}
            tenant_summary = {
                'id': tenant.id,
                'nom': tenant.nom,
                'plan': tenant.plan,
                'statut': (
                    tenant.statut.value
                    if hasattr(tenant.statut, 'value')
                    else tenant.statut
                ),
                'max_utilisateurs': resolved.get('max_utilisateurs'),
                'max_employees': resolved.get('max_employees'),
                'users_count': users_count,
                'employees_count': employees_count,
            }
            return {'abonnement': abonnement.to_dict(), 'can_renew': can_renew, 'tenant': tenant_summary}, 200


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
        utilisateur = db.session.get(Utilisateur, get_jwt_identity())

        # §12 : le Super Admin gère la plateforme et peut effectuer le paiement.
        if utilisateur and utilisateur.is_super_admin:
            abonnement = db.session.get(Abonnement, id)
            if not abonnement:
                return {'message': 'Abonnement non trouve'}, 404
            return self._effectuer_paiement(abonnement)

        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        tenant = db.session.get(Tenant, tenant_id)
        # §10/§11 : droit lié à l'identité (admin principal), pas seulement au rôle.
        if not _is_principal_admin(utilisateur, tenant):
            return {'message': 'Seul l\'administrateur principal du tenant peut effectuer ce paiement'}, 403

        return self._effectuer_paiement(abonnement)

    @staticmethod
    def _effectuer_paiement(abonnement):
        data = request.get_json() or {}

        paiement = Paiement.query.filter_by(
            tenant_id=abonnement.tenant_id,
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

        try:
            broadcast_to_tenant(abonnement.tenant_id, 'subscription:updated', abonnement.to_dict())
        except Exception:
            pass

        return {
            'abonnement': abonnement.to_dict(),
            'paiement': paiement.to_dict() if paiement else None
        }, 200


@ns.route('/<int:id>/renouveler')
class RenouvelerAbonnement(Resource):
    @jwt_required()
    def post(self, id):
        utilisateur = db.session.get(Utilisateur, get_jwt_identity())

        # §12 : le Super Admin gère la plateforme et peut renouveler.
        if utilisateur and utilisateur.is_super_admin:
            result = AbonnementService.renew_subscription(id)
            if not result:
                return {'message': 'Abonnement non trouve'}, 404
            abonnement, paiement = result
            return {
                'abonnement': abonnement.to_dict(),
                'paiement': paiement.to_dict()
            }, 200

        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        tenant = db.session.get(Tenant, tenant_id)
        # §10/§11 : droit lié à l'identité (admin principal), pas seulement au rôle.
        if not _is_principal_admin(utilisateur, tenant):
            return {'message': 'Seul l\'administrateur principal du tenant peut renouveler l\'abonnement'}, 403

        result = AbonnementService.renew_subscription(id)
        if not result:
            return {'message': 'Abonnement non trouve'}, 404
        abonnement, paiement = result
        try:
            broadcast_to_tenant(abonnement.tenant_id, 'subscription:updated', abonnement.to_dict())
        except Exception:
            pass
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
                tenant.is_active = True
                tenant.date_abonnement = datetime.utcnow()
                db.session.add(tenant)

        db.session.commit()

        try:
            if abonnement:
                broadcast_to_tenant(abonnement.tenant_id, 'subscription:updated', abonnement.to_dict())
            if tenant:
                broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
        except Exception:
            pass

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
        statut = request.args.get('statut')
        plan = request.args.get('plan')
        items, total = AbonnementService.get_all_subscriptions(
            tenant_id=None, page=page, per_page=per_page,
            statut=statut, plan=plan,
        )
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
