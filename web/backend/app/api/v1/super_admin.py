from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement
from app.models.audit_log import AuditLog, TypeActionAudit
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.security.roles import is_super_admin
from app.security.plans import apply_plan_to_abonnement
from datetime import datetime, timedelta
from sqlalchemy import func
import json

ns = Namespace('super-admin', description='Endpoints réservés au SUPER_ADMIN')


def _ensure_super_admin():
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)
    if not user or not is_super_admin(user.role):
        return {'message': 'Acces super administrateur requis'}, 403
    return None


def _log_audit(action_type, description, tenant_id=None, metadata=None):
    try:
        user_id = get_jwt_identity()
        audit = AuditLog(
            tenant_id=tenant_id,
            utilisateur_id=user_id,
            type_action=action_type,
            description=description,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


PLANS = [
    {'code': 'gratuit', 'label': 'Gratuit', 'prix': 0, 'duree_mois': 0},
    {'code': 'starter', 'label': 'Starter', 'prix': 29, 'duree_mois': 30},
    {'code': 'pro', 'label': 'Pro', 'prix': 79, 'duree_mois': 30},
    {'code': 'enterprise', 'label': 'Enterprise', 'prix': 199, 'duree_mois': 30},
]


@ns.route('/auth/login')
class SuperAdminLogin(Resource):
    @jwt_required()
    def post(self):
        err = _ensure_super_admin()
        if err:
            return err

        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)

        _log_audit(
            TypeActionAudit.CONNEXION_SUPER_ADMIN,
            f"Connexion Super Admin: {user.username} (id={user.id})",
            metadata={'action': 'super_admin_login'},
        )

        return {
            'message': 'Session Super Admin confirmée',
            'user': user.to_dict(),
        }, 200


@ns.route('/auth/logout')
class SuperAdminLogout(Resource):
    @jwt_required()
    def post(self):
        err = _ensure_super_admin()
        if err:
            return err

        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)

        _log_audit(
            TypeActionAudit.DECONNEXION_SUPER_ADMIN,
            f"Deconnexion Super Admin: {user.username} (id={user.id})",
            metadata={'action': 'super_admin_logout'},
        )

        return {
            'message': 'Deconnexion reussie',
        }, 200


@ns.route('/dashboard')
class SuperAdminDashboard(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        now = datetime.utcnow()
        today = now.date()
        debut_mois = today.replace(day=1)
        debut_semaine = today - timedelta(days=7)

        total_tenants = db.session.query(func.count(Tenant.id)).scalar() or 0
        tenants_actifs = db.session.query(func.count(Tenant.id)).filter(
            Tenant.statut == StatutTenant.ACTIF,
            Tenant.is_active == True,
        ).scalar() or 0
        tenants_suspendus = db.session.query(func.count(Tenant.id)).filter(
            Tenant.statut == StatutTenant.INACTIF,
        ).scalar() or 0
        tenants_essai = db.session.query(func.count(Tenant.id)).filter(
            Tenant.statut == StatutTenant.EN_ESSAI,
        ).scalar() or 0

        abonnements_actifs = db.session.query(func.count(Abonnement.id)).filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.is_active == True,
            Abonnement.date_fin > now,
        ).scalar() or 0

        abonnements_expires_bientot = db.session.query(func.count(Abonnement.id)).filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.is_active == True,
            Abonnement.date_fin > now,
            Abonnement.date_fin <= now + timedelta(days=30),
        ).scalar() or 0

        abonnements_expires = db.session.query(func.count(Abonnement.id)).filter(
            Abonnement.statut == StatutAbonnement.EXPIRE,
        ).scalar() or 0

        revenus_total = db.session.query(func.sum(Paiement.montant)).filter(
            Paiement.statut == StatutPaiement.CONFIRME,
            Paiement.is_active == True,
        ).scalar() or 0

        revenus_mois = db.session.query(func.sum(Paiement.montant)).filter(
            Paiement.statut == StatutPaiement.CONFIRME,
            Paiement.is_active == True,
            Paiement.date_paiement >= debut_mois,
        ).scalar() or 0

        nouveaux_tenants = db.session.query(func.count(Tenant.id)).filter(
            Tenant.created_at >= debut_mois,
        ).scalar() or 0

        tenants_recents = db.session.query(func.count(Tenant.id)).filter(
            Tenant.created_at >= debut_semaine,
        ).scalar() or 0

        total_utilisateurs = db.session.query(func.count(Utilisateur.id)).filter(
            Utilisateur.is_active == True,
        ).scalar() or 0

        total_produits = db.session.query(func.count(Produit.id)).filter(
            Produit.is_active == True,
        ).scalar() or 0

        total_ventes = db.session.query(func.count(Vente.id)).filter(
            Vente.is_active == True,
        ).scalar() or 0

        total_factures = db.session.query(func.count(Facture.id)).filter(
            Facture.is_active == True,
        ).scalar() or 0

        abonnements_par_plan = db.session.query(
            Abonnement.plan,
            func.count(Abonnement.id).label('count'),
        ).filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.is_active == True,
        ).group_by(Abonnement.plan).all()

        abonnements_par_plan_data = [
            {'plan': row[0] or 'inconnu', 'count': row[1]}
            for row in abonnements_par_plan
        ]

        evolution_tenants = []
        for i in range(7):
            date_jour = debut_semaine + timedelta(days=i)
            date_next = date_jour + timedelta(days=1)
            count = db.session.query(func.count(Tenant.id)).filter(
                Tenant.created_at >= date_jour,
                Tenant.created_at < date_next,
            ).scalar() or 0
            evolution_tenants.append({
                'date': date_jour.isoformat(),
                'count': count,
            })

        return {
            'total_tenants': total_tenants,
            'tenants_actifs': tenants_actifs,
            'tenants_suspendus': tenants_suspendus,
            'tenants_essai': tenants_essai,
            'abonnements_actifs': abonnements_actifs,
            'abonnements_expires_bientot': abonnements_expires_bientot,
            'abonnements_expires': abonnements_expires,
            'revenus_total': float(revenus_total),
            'revenus_mois': float(revenus_mois),
            'nouveaux_tenants': nouveaux_tenants,
            'tenants_recents': tenants_recents,
            'total_utilisateurs': total_utilisateurs,
            'total_produits': total_produits,
            'total_ventes': total_ventes,
            'total_factures': total_factures,
            'abonnements_par_plan': abonnements_par_plan_data,
            'evolution_tenants': evolution_tenants,
        }, 200


@ns.route('/tenants')
class SuperAdminTenantsList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        statut = request.args.get('statut')
        plan = request.args.get('plan')

        query = Tenant.query

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Tenant.nom.ilike(search_filter),
                    Tenant.slug.ilike(search_filter),
                    Tenant.email_contact.ilike(search_filter),
                )
            )

        if statut:
            query = query.filter(Tenant.statut == statut)

        if plan:
            query = query.filter(Tenant.plan == plan)

        query = query.order_by(Tenant.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        tenants_data = []
        for tenant in paginated.items:
            tenant_dict = tenant.to_dict()
            tenant_dict['utilisateurs_count'] = db.session.query(func.count(Utilisateur.id)).filter(
                Utilisateur.tenant_id == tenant.id,
                Utilisateur.is_active == True,
            ).scalar() or 0
            tenant_dict['last_login'] = None
            last_user = Utilisateur.query.filter(
                Utilisateur.tenant_id == tenant.id,
                Utilisateur.last_login.isnot(None),
            ).order_by(Utilisateur.last_login.desc()).first()
            if last_user:
                tenant_dict['last_login'] = last_user.last_login.isoformat()
            tenants_data.append(tenant_dict)

        return {
            'tenants': tenants_data,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages,
        }, 200


@ns.route('/tenants/<int:tenant_id>')
class SuperAdminTenantDetail(Resource):
    @jwt_required()
    def get(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        tenant_data = tenant.to_dict()

        tenant_data['utilisateurs_count'] = db.session.query(func.count(Utilisateur.id)).filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.is_active == True,
        ).scalar() or 0

        tenant_data['produits_count'] = db.session.query(func.count(Produit.id)).filter(
            Produit.tenant_id == tenant.id,
            Produit.is_active == True,
        ).scalar() or 0

        tenant_data['clients_count'] = db.session.query(func.count(Client.id)).filter(
            Client.tenant_id == tenant.id,
            Client.is_active == True,
        ).scalar() or 0

        tenant_data['fournisseurs_count'] = db.session.query(func.count(Fournisseur.id)).filter(
            Fournisseur.tenant_id == tenant.id,
            Fournisseur.is_active == True,
        ).scalar() or 0

        tenant_data['ventes_count'] = db.session.query(func.count(Vente.id)).filter(
            Vente.tenant_id == tenant.id,
            Vente.is_active == True,
        ).scalar() or 0

        tenant_data['factures_count'] = db.session.query(func.count(Facture.id)).filter(
            Facture.tenant_id == tenant.id,
            Facture.is_active == True,
        ).scalar() or 0

        abonnement_actuel = Abonnement.query.filter(
            Abonnement.tenant_id == tenant.id,
            Abonnement.is_active == True,
        ).order_by(Abonnement.date_fin.desc()).first()

        tenant_data['abonnement_actuel'] = abonnement_actuel.to_dict() if abonnement_actuel else None

        tenant_data['administrateurs'] = []
        admins = Utilisateur.query.filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.is_active == True,
        ).filter(
            Utilisateur.role.in_(['admin', 'super_admin'])
        ).all()
        for admin in admins:
            tenant_data['administrateurs'].append({
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'role': str(admin.role),
                'last_login': admin.last_login.isoformat() if admin.last_login else None,
            })

        tenant_data['last_activity'] = None
        last_login_user = Utilisateur.query.filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.last_login.isnot(None),
        ).order_by(Utilisateur.last_login.desc()).first()
        if last_login_user:
            tenant_data['last_activity'] = last_login_user.last_login.isoformat()

        tenant_data['connexions_recentes'] = db.session.query(func.count(Utilisateur.id)).filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.last_login >= datetime.utcnow() - timedelta(days=7),
        ).scalar() or 0

        return tenant_data, 200


@ns.route('/tenants/<int:tenant_id>/suspend')
class SuperAdminSuspendTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        tenant.statut = StatutTenant.INACTIF
        tenant.is_active = False
        db.session.commit()

        _log_audit(
            TypeActionAudit.SUSPENSION_TENANT,
            f"Suspension du tenant {tenant.nom} (id={tenant.id})",
            tenant_id=tenant.id,
            metadata={'action': 'suspend_tenant'},
        )

        return {
            'message': 'Tenant suspendu',
            'tenant': tenant.to_dict(),
        }, 200


@ns.route('/tenants/<int:tenant_id>/activate')
class ActivateTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        tenant.statut = StatutTenant.ACTIF
        tenant.is_active = True
        db.session.commit()

        _log_audit(
            TypeActionAudit.ACTIVATION_TENANT,
            f"Activation du tenant {tenant.nom} (id={tenant.id})",
            tenant_id=tenant.id,
            metadata={'action': 'activate_tenant'},
        )

        return {
            'message': 'Tenant activé',
            'tenant': tenant.to_dict(),
        }, 200


@ns.route('/tenants/<int:tenant_id>/reactivate')
class ReactivateTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        tenant.statut = StatutTenant.ACTIF
        tenant.is_active = True
        db.session.commit()

        _log_audit(
            TypeActionAudit.ACTIVATION_TENANT,
            f"Réactivation du tenant {tenant.nom} (id={tenant.id})",
            tenant_id=tenant.id,
            metadata={'action': 'reactivate_tenant'},
        )

        return {
            'message': 'Tenant réactivé',
            'tenant': tenant.to_dict(),
        }, 200


@ns.route('/tenants/<int:tenant_id>/subscription/change')
class ChangeSubscription(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        data = request.get_json() or {}
        new_plan = data.get('plan')
        days = data.get('days', 30)

        if not new_plan:
            return {'message': 'Plan requis'}, 400

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        old_plan = tenant.plan
        tenant.plan = new_plan

        abonnement = Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.is_active == True,
        ).order_by(Abonnement.date_fin.desc()).first()

        if abonnement:
            abonnement.plan = new_plan
            abonnement.date_debut = datetime.utcnow()
            abonnement.date_fin = datetime.utcnow() + timedelta(days=days)
            abonnement.statut = StatutAbonnement.ACTIF
            apply_plan_to_abonnement(abonnement, new_plan)

        db.session.commit()

        _log_audit(
            TypeActionAudit.CHANGEMENT_ABONNEMENT,
            f"Changement d'abonnement du tenant {tenant.nom} (id={tenant.id}): {old_plan} -> {new_plan}",
            tenant_id=tenant.id,
            metadata={'action': 'change_subscription', 'old_plan': old_plan, 'new_plan': new_plan, 'days': days},
        )

        return {
            'message': 'Abonnement modifié',
            'tenant': tenant.to_dict(),
            'abonnement': abonnement.to_dict() if abonnement else None,
        }, 200


@ns.route('/tenants/<int:tenant_id>/subscription/extend')
class ExtendSubscription(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        data = request.get_json() or {}
        days = data.get('days', 30)

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouvé'}, 404

        abonnement = Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.is_active == True,
        ).order_by(Abonnement.date_fin.desc()).first()

        if not abonnement:
            return {'message': 'Aucun abonnement trouvé pour ce tenant'}, 404

        base_date = abonnement.date_fin if abonnement.date_fin and abonnement.date_fin > datetime.utcnow() else datetime.utcnow()
        abonnement.date_debut = base_date
        abonnement.date_fin = base_date + timedelta(days=days)
        abonnement.statut = StatutAbonnement.ACTIF
        db.session.commit()

        _log_audit(
            TypeActionAudit.PROLONGATION_ABONNEMENT,
            f"Prolongation de l'abonnement du tenant {tenant.nom} (id={tenant.id}) de {days} jours",
            tenant_id=tenant.id,
            metadata={'action': 'extend_subscription', 'days': days, 'abonnement_id': abonnement.id},
        )

        return {
            'message': 'Abonnement prolongé',
            'abonnement': abonnement.to_dict(),
        }, 200


@ns.route('/subscriptions')
class SuperAdminSubscriptions(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        statut = request.args.get('statut')
        plan = request.args.get('plan')

        query = Abonnement.query

        if statut:
            query = query.filter(Abonnement.statut == statut)

        if plan:
            query = query.filter(Abonnement.plan == plan)

        query = query.order_by(Abonnement.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        subs_data = []
        for sub in paginated.items:
            sub_dict = sub.to_dict()
            tenant = db.session.get(Tenant, sub.tenant_id)
            sub_dict['tenant'] = {
                'id': tenant.id,
                'nom': tenant.nom,
                'slug': tenant.slug,
            } if tenant else None
            subs_data.append(sub_dict)

        return {
            'abonnements': subs_data,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages,
        }, 200


@ns.route('/audit')
class SuperAdminAudit(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        action_type = request.args.get('action_type')
        tenant_id = request.args.get('tenant_id', type=int)
        user_id = request.args.get('user_id', type=int)

        query = AuditLog.query.filter_by(is_active=True)

        if action_type:
            query = query.filter_by(type_action=action_type)

        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        if user_id:
            query = query.filter_by(utilisateur_id=user_id)

        paginated = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        logs = []
        for log in paginated.items:
            log_dict = log.to_dict()
            log_dict['utilisateur'] = None
            log_dict['tenant'] = None
            if log.utilisateur_id:
                user = db.session.get(Utilisateur, log.utilisateur_id)
                if user:
                    log_dict['utilisateur'] = {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role.value if hasattr(user.role, 'value') else user.role,
                    }
            if log.tenant_id:
                tenant = db.session.get(Tenant, log.tenant_id)
                if tenant:
                    log_dict['tenant'] = {
                        'id': tenant.id,
                        'nom': tenant.nom,
                        'slug': tenant.slug,
                    }
            logs.append(log_dict)

        return {
            'logs': logs,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages,
        }, 200


@ns.route('/plans')
class SuperAdminPlans(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        plans_data = []
        for plan in PLANS:
            count = 0
            if plan['code'] != 'gratuit':
                count = db.session.query(func.count(Abonnement.id)).filter(
                    Abonnement.plan == plan['code'],
                    Abonnement.is_active == True,
                ).scalar() or 0
            plans_data.append({
                'code': plan['code'],
                'label': plan['label'],
                'prix': plan['prix'],
                'duree_mois': plan['duree_mois'],
                'tenants_count': count,
            })

        return {
            'plans': plans_data,
        }, 200
