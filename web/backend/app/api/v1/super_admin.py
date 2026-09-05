from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.utilisateur import Utilisateur, Role, StatutAdmin, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.audit_log import AuditLog, TypeActionAudit
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.employe import Employe
from app.models.stagiaire import Stagiaire
from app.models.admin_device import AdminDevice
from app.models.livreur import Livreur
from app.models.vehicule import Vehicule
from app.models.itineraire import Itineraire
from app.models.stock import MouvementStock
from app.models.ligne_vente import LigneVente
from app.models.ligne_achat import LigneAchat
from app.models.commande_client import CommandeClient
from app.models.commande_fournisseur import CommandeFournisseur
from app.models.commande_achat import CommandeAchat
from app.models.facture_fournisseur import FactureFournisseur
from app.models.devis_avoir_bl import BonLivraison, Devis, Avoir
from app.models.livraison import Livraison
from app.models.suivi_livraison import SuiviLivraison
from app.models.compte_comptable import CompteComptable
from app.models.ecriture_comptable import EcritureComptable
from app.models.tresorerie import Tresorerie
from app.models.document_genere import DocumentGenere
from app.models.modele_document import ModeleDocument
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.payment_event import PaymentEvent
from app.models.presence import Presence
from app.models.salaire import Salaire
from app.models.prime import Prime
from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
from app.services.rh_service import EmployeService
from app.security.roles import is_super_admin
from app.security.plans import apply_plan_to_abonnement
from app.websockets.socket_events import broadcast_to_tenant, broadcast_to_super_admin
from datetime import datetime, timedelta
from sqlalchemy import func, text
from sqlalchemy.orm import contains_eager, joinedload
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


from app.security.plans import PLAN_CONFIG

PLANS = [
    {
        'code': code,
        'label': config.get('label', code.replace('_', ' ').title()),
        'prix': config.get('prix', 0),
        'duree_jours': config.get('duree_jours', 30),
    }
    for code, config in PLAN_CONFIG.items()
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
            Tenant.statut == StatutTenant.BLOQUE,
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

        query = Tenant.query.filter(Tenant.is_active == True)

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

    @jwt_required()
    def delete(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        try:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant non trouve'}, 404

            if not tenant.is_active or tenant.statut == StatutTenant.INACTIF:
                return {'message': 'Tenant deja desactive'}, 400

            tenant_nom = tenant.nom
            tenant_id_log = tenant.id
            _hard_delete_tenant_data(tenant_id)
            db.session.commit()

            _log_audit(
                TypeActionAudit.SUPPRESSION_TENANT,
                f"Suppression definitive du tenant {tenant_nom} (id={tenant_id_log})",
                tenant_id=tenant_id_log,
                metadata={'action': 'delete_tenant'},
            )

            return {
                'message': 'Tenant supprime definitivement',
                'tenant': {'id': tenant_id_log, 'nom': tenant_nom},
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erreur lors de la suppression: {str(e)}'}, 500


@ns.route('/tenants/<int:tenant_id>/suspend')
class SuperAdminSuspendTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        try:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant non trouvé'}, 404

            if tenant.statut == StatutTenant.BLOQUE:
                return {'message': 'Tenant déjà suspendu'}, 200

            tenant.statut = StatutTenant.BLOQUE
            db.session.commit()

            admins = Utilisateur.query.filter_by(tenant_id=tenant_id, role=Role.ADMIN, is_active=True).all()
            for admin in admins:
                admin.admin_statut = StatutAdmin.SUSPENDED
                db.session.add(admin)

            db.session.commit()

            _log_audit(
                TypeActionAudit.SUSPENSION_TENANT,
                f"Suspension du tenant {tenant.nom} (id={tenant.id})",
                tenant_id=tenant.id,
                metadata={'action': 'suspend_tenant'},
            )
            try:
                broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
            except Exception:
                pass

            return {
                'message': 'Tenant suspendu',
                'tenant': tenant.to_dict(),
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erreur lors de la suspension: {str(e)}'}, 500


@ns.route('/tenants/<int:tenant_id>/activate')
class ActivateTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        try:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant non trouvé'}, 404

            if tenant.statut == StatutTenant.ACTIF and tenant.is_active:
                return {'message': 'Tenant déjà activé'}, 200

            tenant.statut = StatutTenant.ACTIF
            tenant.is_active = True
            db.session.commit()

            admins = Utilisateur.query.filter_by(tenant_id=tenant_id, role=Role.ADMIN).all()
            for admin in admins:
                admin.admin_statut = StatutAdmin.ACTIVE
                db.session.add(admin)

            db.session.commit()

            _log_audit(
                TypeActionAudit.ACTIVATION_TENANT,
                f"Activation du tenant {tenant.nom} (id={tenant.id})",
                tenant_id=tenant.id,
                metadata={'action': 'activate_tenant'},
            )
            try:
                broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
            except Exception:
                pass

            return {
                'message': 'Tenant activé',
                'tenant': tenant.to_dict(),
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erreur lors de l\'activation: {str(e)}'}, 500


@ns.route('/tenants/<int:tenant_id>/reactivate')
class ReactivateTenant(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err

        try:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant non trouvé'}, 404

            if tenant.statut == StatutTenant.ACTIF and tenant.is_active:
                return {'message': 'Tenant déjà activé'}, 200

            tenant.statut = StatutTenant.ACTIF
            tenant.is_active = True
            db.session.commit()

            admins = Utilisateur.query.filter_by(tenant_id=tenant_id, role=Role.ADMIN).all()
            for admin in admins:
                admin.admin_statut = StatutAdmin.ACTIVE
                db.session.add(admin)

            db.session.commit()

            _log_audit(
                TypeActionAudit.ACTIVATION_TENANT,
                f"Réactivation du tenant {tenant.nom} (id={tenant.id})",
                tenant_id=tenant.id,
                metadata={'action': 'reactivate_tenant'},
            )
            try:
                broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
            except Exception:
                pass

            return {
                'message': 'Tenant réactivé',
                'tenant': tenant.to_dict(),
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erreur lors de la réactivation: {str(e)}'}, 500


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
        try:
            broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
            if abonnement:
                broadcast_to_tenant(tenant.id, 'subscription:updated', abonnement.to_dict())
        except Exception:
            pass

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
        try:
            broadcast_to_tenant(tenant.id, 'subscription:updated', abonnement.to_dict())
        except Exception:
            pass

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

        from app.services.abonnement_service import AbonnementService
        items, total = AbonnementService.get_all_subscriptions(
            tenant_id=None, page=page, per_page=per_page,
            statut=statut, plan=plan,
        )

        subs_data = []
        for sub in items:
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
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
        }, 200


# ==========================================================
# 💰 PAIEMENTS & REVENUS (lecture seule, SUPER_ADMIN uniquement)
#
# Portée : transactions d'abonnement de la plateforme
# (Paiement.type == 'abonnement', provider 'papi' ou 'manuel').
# Les paiements métier des tenants (factures, ventes, achats...)
# ne font pas partie des revenus de la plateforme.
#
# Settlement Papi : l'intégration Papi actuelle ne fournit aucune
# donnée de versement (settlement). Aucun montant de settlement ni
# de "net à recevoir" n'est donc calculé ici : on n'affiche que ce
# qui existe réellement en base (paiement + évènements webhook).
# ==========================================================

_SETTLEMENT_UNAVAILABLE = (
    "Informations de settlement non disponibles via l'intégration actuelle"
)

_PAPI_FEES_UNAVAILABLE = (
    "Frais Papi non disponibles via l'intégration actuelle"
)

# Groupes de statuts (valeurs réelles de StatutPaiement) :
# - confirmé/encaissé : 'succes' (Papi SUCCESS / validation hors ligne)
#   et 'confirme'
# - en attente : 'en_attente', 'traitement'
# - échoué : 'echec', 'annule', 'expiré'
_CONFIRMED_STATUTS = (StatutPaiement.SUCCESS, StatutPaiement.CONFIRME)
_PENDING_STATUTS = (StatutPaiement.EN_ATTENTE, StatutPaiement.PROCESSING)
_FAILED_STATUTS = (StatutPaiement.FAILED, StatutPaiement.CANCELLED, StatutPaiement.EXPIRED)

_STATUT_LABELS = {
    StatutPaiement.EN_ATTENTE: 'EN_ATTENTE',
    StatutPaiement.PROCESSING: 'PROCESSING',
    StatutPaiement.SUCCESS: 'SUCCESS',
    StatutPaiement.CONFIRME: 'CONFIRME',
    StatutPaiement.FAILED: 'FAILED',
    StatutPaiement.CANCELLED: 'CANCELLED',
    StatutPaiement.EXPIRED: 'EXPIRE',
}

# Accepte à la fois le nom de l'enum (ex: 'SUCCESS') et sa valeur
# en base (ex: 'succes') comme filtre.
_STATUT_FILTER_MAP = {}
for _st in StatutPaiement:
    _STATUT_FILTER_MAP[str(_st.name).upper()] = _st
    _STATUT_FILTER_MAP[str(_st.value).upper()] = _st


def _payment_status_value(payment):
    return payment.statut.value if hasattr(payment.statut, 'value') else payment.statut


def _payment_status_label(statut):
    return _STATUT_LABELS.get(statut, str(statut).upper() if statut else None)


def _resolve_statut_filter(raw):
    if not raw:
        return None
    return _STATUT_FILTER_MAP.get(str(raw).strip().upper())


def _parse_payment_date(raw, inclusive_end=False):
    """Parse un filtre de date ISO (YYYY-MM-DD). Retourne None si invalide."""
    if not raw:
        return None
    try:
        dt = datetime.strptime(str(raw).strip()[:10], '%Y-%m-%d')
    except (TypeError, ValueError):
        return None
    if inclusive_end:
        dt = dt + timedelta(days=1)  # borne haute exclusive (fin de journée)
    return dt


def _apply_payment_filters(query, args):
    """Applique les filtres communs aux endpoints liste/statistiques.

    Tous les filtres sont optionnels ; les valeurs invalides sont ignorées.
    Les requêtes passent exclusivement par l'ORM SQLAlchemy (pas de SQL
    brut => pas d'injection SQL).
    """
    tenant_id = args.get('tenant_id', type=int)
    if tenant_id:
        query = query.filter(Paiement.tenant_id == tenant_id)

    statut = _resolve_statut_filter(args.get('status'))
    if statut is not None:
        query = query.filter(Paiement.statut == statut)

    provider = (args.get('provider') or '').strip()
    if provider:
        query = query.filter(Paiement.provider == provider)

    payment_method = (args.get('payment_method') or '').strip()
    if payment_method:
        query = query.filter(Paiement.payment_method == payment_method)

    plan = (args.get('plan') or '').strip()
    if plan:
        query = query.filter(Paiement.abonnement.has(Abonnement.plan == plan))

    date_from = _parse_payment_date(args.get('date_from'))
    if date_from:
        query = query.filter(Paiement.created_at >= date_from)

    date_to = _parse_payment_date(args.get('date_to'), inclusive_end=True)
    if date_to:
        query = query.filter(Paiement.created_at < date_to)

    return query


def _payments_base_query():
    """Query de base : paiements d'abonnement actifs, avec tenant + abonnement.

    Les tenants désactivés (soft-delete) restent visibles : l'historique
    financier doit être conservé.
    """
    return (
        Paiement.query
        .join(Tenant, Paiement.tenant_id == Tenant.id)
        .filter(
            Paiement.is_active == True,
            Paiement.type == TypePaiement.ABONNEMENT,
        )
        .options(
            contains_eager(Paiement.tenant),
            joinedload(Paiement.abonnement),
        )
    )


def _payment_list_item(payment):
    """Sérialise un paiement pour la liste (aucune donnée sensible)."""
    tenant = payment.tenant
    abonnement = payment.abonnement
    return {
        'id': payment.id,
        'tenant_id': payment.tenant_id,
        'tenant_name': tenant.nom if tenant else None,
        'subscription_id': payment.subscription_id,
        'plan': abonnement.plan if abonnement else None,
        'montant': float(payment.montant or 0),
        'devise': payment.devise or 'MGA',
        'provider': payment.provider,
        'payment_method': payment.payment_method,
        'statut': _payment_status_value(payment),
        'statut_label': _payment_status_label(payment.statut),
        'reference': payment.reference,
        'external_reference': payment.external_reference,
        'date_paiement': payment.date_paiement.isoformat() if payment.date_paiement else None,
        'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
        'created_at': payment.created_at.isoformat() if payment.created_at else None,
        'updated_at': payment.updated_at.isoformat() if payment.updated_at else None,
    }


def _payment_events_info(payment_id):
    """Charge les PaymentEvent d'un paiement (sans payload ni signature).

    Retourne (events_data, papi_fee) : les évènements incluent uniquement
    event_id/event_type/statut de traitement/dates. Le `fee` est extrait du
    payload du webhook Papi UNIQUEMENT s'il a réellement été renvoyé par
    Papi (aucun calcul, aucun pourcentage inventé).
    """
    events = (
        PaymentEvent.query
        .filter_by(payment_id=payment_id)
        .order_by(PaymentEvent.created_at.asc())
        .all()
    )
    events_data = []
    papi_fee = None
    for event in events:
        events_data.append({
            'event_id': event.event_id,
            'event_type': event.event_type,
            'processed': bool(event.processed),
            'processed_at': event.processed_at.isoformat() if event.processed_at else None,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        })
        if event.processed and papi_fee is None:
            payload = event.payload if isinstance(event.payload, dict) else {}
            raw_fee = payload.get('fee')
            try:
                if raw_fee is not None:
                    papi_fee = float(raw_fee)
            except (TypeError, ValueError):
                continue
    return events_data, papi_fee


def _payment_stats_by_method(base_query, statuts):
    """Repartition par methode de paiement (donnees reelles uniquement)."""
    rows = (
        base_query
        .with_entities(
            Paiement.payment_method,
            func.count(Paiement.id).label('count'),
            func.coalesce(func.sum(Paiement.montant), 0).label('total'),
        )
        .filter(Paiement.statut.in_(statuts))
        .group_by(Paiement.payment_method)
        .all()
    )
    return [
        {
            'payment_method': row[0] or 'INCONNU',
            'count': row[1],
            'montant': float(row[2] or 0),
        }
        for row in rows
    ]


def _payment_stats_by_plan(base_query, statuts):
    """Repartition par plan (jointure reelle via Abonnement)."""
    rows = (
        base_query
        .with_entities(
            Abonnement.plan,
            func.count(Paiement.id).label('count'),
            func.coalesce(func.sum(Paiement.montant), 0).label('total'),
        )
        .join(Abonnement, Paiement.subscription_id == Abonnement.id)
        .filter(Paiement.statut.in_(statuts))
        .group_by(Abonnement.plan)
        .all()
    )
    return [
        {
            'plan': row[0] or 'INCONNU',
            'count': row[1],
            'montant': float(row[2] or 0),
        }
        for row in rows
    ]


@ns.route('/payments')
class SuperAdminPaymentsList(Resource):
    @jwt_required()
    def get(self):
        """Liste paginee des paiements d'abonnement de la plateforme.

        Acces reserve au SUPER_ADMIN. Les paiements metiers des tenants
        (factures/ventes/achats) ne sont PAS inclus : ils ne constituent
        pas des revenus de la plateforme.
        """
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = max(1, min(per_page, 200))

        query = _payments_base_query()
        query = _apply_payment_filters(query, request.args)

        search = (request.args.get('search') or '').strip()
        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Tenant.nom.ilike(like),
                    Paiement.reference.ilike(like),
                    Paiement.external_reference.ilike(like),
                )
            )

        query = query.order_by(Paiement.created_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        items = [_payment_list_item(p) for p in paginated.items]

        return {
            'items': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
            },
        }, 200


@ns.route('/payments/<int:payment_id>')
class SuperAdminPaymentDetail(Resource):
    @jwt_required()
    def get(self, payment_id):
        err = _ensure_super_admin()
        if err:
            return err

        paiement = (
            Paiement.query
            .filter_by(id=payment_id, is_active=True)
            .options(joinedload(Paiement.abonnement))
            .first()
        )
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404

        data = _payment_list_item(paiement)
        if paiement.abonnement:
            data['subscription'] = paiement.abonnement.to_dict()

        events_data, papi_fee = _payment_events_info(paiement.id)
        data['payment_events'] = events_data

        # Settlement : l'API Papi actuelle ne fournit aucun champ
        # settlement_id / settlement_status / settlement_amount /
        # settlement_date. Le webhook ne stocke pas non plus ces champs.
        # On expose donc une mention explicite "non disponible" pour ne
        # PAS inventer un montant de versement.
        data['settlement'] = {
            'available': False,
            'message': _SETTLEMENT_UNAVAILABLE,
            'settlement_id': None,
            'settlement_status': None,
            'settlement_amount': None,
            'settlement_date': None,
            'settlement_reference': None,
            'net_amount': None,
        }

        # Frais Papi : uniquement si le champ `fee` a ete reellement
        # transmis par Papi dans le payload du webhook et stocke dans
        # PaymentEvent.payload. Aucun pourcentage/frais invente.
        if papi_fee is not None:
            data['papi_fees'] = {
                'available': True,
                'fee': papi_fee,
                'message': None,
            }
        else:
            data['papi_fees'] = {
                'available': False,
                'message': _PAPI_FEES_UNAVAILABLE,
                'fee': None,
            }

        # Net a recevoir : seulement si frais + statut SUCCESS/CONFIRME.
        net_amount_block = {
            'available': False,
            'montant': None,
            'devise': paiement.devise or 'MGA',
            'message': 'Net à recevoir non disponible (frais Papi ou settlement bancaire reel non connus)',
        }
        if (
            papi_fee is not None
            and float(paiement.montant or 0) > 0
            and _payment_status_value(paiement) in ('succes', 'confirme')
        ):
            net = float(paiement.montant or 0) - papi_fee
            net_amount_block = {
                'available': True,
                'montant': max(net, 0.0),
                'devise': paiement.devise or 'MGA',
                'note': 'Net = montant confirme - frais reels Papi (settlement bancaire non confirme)',
            }
        data['settlement']['net_amount'] = net_amount_block
        # Expose egalement net_amount au top level pour faciliter l'UI.
        data['net_amount'] = net_amount_block

        return data, 200


@ns.route('/payments/stats')
class SuperAdminPaymentsStats(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        # Agrégations SQL : requête sans eager-load (les options joinedload
        # ne sont pas pertinentes pour des requêtes GROUP BY).
        base_query = Paiement.query.filter(
            Paiement.is_active == True,
            Paiement.type == TypePaiement.ABONNEMENT,
        )
        base_query = _apply_payment_filters(base_query, request.args)

        total_success = float(
            base_query.with_entities(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut.in_(_CONFIRMED_STATUTS))
            .scalar() or 0
        )
        total_pending = float(
            base_query.with_entities(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut.in_(_PENDING_STATUTS))
            .scalar() or 0
        )
        total_failed = float(
            base_query.with_entities(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut.in_(_FAILED_STATUTS))
            .scalar() or 0
        )

        success_count = (
            base_query.with_entities(func.count(Paiement.id))
            .filter(Paiement.statut.in_(_CONFIRMED_STATUTS))
            .scalar() or 0
        )
        pending_count = (
            base_query.with_entities(func.count(Paiement.id))
            .filter(Paiement.statut.in_(_PENDING_STATUTS))
            .scalar() or 0
        )
        failed_count = (
            base_query.with_entities(func.count(Paiement.id))
            .filter(Paiement.statut.in_(_FAILED_STATUTS))
            .scalar() or 0
        )

        online_confirmed = float(
            base_query.with_entities(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut.in_(_CONFIRMED_STATUTS))
            .filter(Paiement.provider == 'papi')
            .scalar() or 0
        )
        offline_confirmed = float(
            base_query.with_entities(func.coalesce(func.sum(Paiement.montant), 0))
            .filter(Paiement.statut.in_(_CONFIRMED_STATUTS))
            .filter(Paiement.provider.in_(['manuel', 'especes']))
            .scalar() or 0
        )

        by_method_confirmed = _payment_stats_by_method(base_query, _CONFIRMED_STATUTS)
        by_plan_confirmed = _payment_stats_by_plan(base_query, _CONFIRMED_STATUTS)

        return {
            'currency': 'MGA',
            'total_count': (success_count or 0) + (pending_count or 0) + (failed_count or 0),
            'success_count': success_count,
            'pending_count': pending_count,
            'failed_count': failed_count,
            'total_success': total_success,
            'total_pending': total_pending,
            'total_failed': total_failed,
            'online_confirmed': online_confirmed,
            'offline_confirmed': offline_confirmed,
            'by_method_confirmed': by_method_confirmed,
            'by_plan_confirmed': by_plan_confirmed,
            'settlement': {
                'available': False,
                'message': _SETTLEMENT_UNAVAILABLE,
            },
            'papi_fees': {
                'available': False,
                'message': _PAPI_FEES_UNAVAILABLE,
            },
            'note': (
                "total_success = somme des paiements MIHAJA confirmes "
                "(SUCCESS/CONFIRME). Cela n'implique PAS un versement "
                "effectif sur le compte bancaire MIHAJA."
            ),
        }, 200


# ==========================================================
# Options de filtrage réelles (tenants, plans, providers,
# méthodes, statuts) — issues de la base, pas de valeurs inventées.
# ==========================================================


@ns.route('/payments/filters')
class SuperAdminPaymentFilters(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        tenants = (
            Tenant.query.filter(Tenant.is_active == True)
            .order_by(Tenant.nom.asc()).all()
        )

        plans = [
            row[0] for row in db.session.query(Abonnement.plan)
            .filter(Abonnement.plan.isnot(None))
            .distinct().order_by(Abonnement.plan.asc()).all()
        ]

        scope = [
            Paiement.is_active == True,
            Paiement.type == TypePaiement.ABONNEMENT,
        ]
        providers = [
            row[0] for row in db.session.query(Paiement.provider)
            .filter(*scope, Paiement.provider.isnot(None)).distinct().all()
        ]
        for known in ('papi', 'manuel'):
            if known not in providers:
                providers.append(known)

        payment_methods = [
            row[0] for row in db.session.query(Paiement.payment_method)
            .filter(*scope, Paiement.payment_method.isnot(None)).distinct().all()
        ]
        for known in ('MVOLA', 'ORANGE_MONEY', 'AIRTEL_MONEY', 'VISA',
                      'ESPECES', 'VIREMENT', 'CHEQUE'):
            if known not in payment_methods:
                payment_methods.append(known)

        statuses = [
            {
                'value': st.value,
                'name': st.name,
                'label': _STATUT_LABELS[st],
            }
            for st in StatutPaiement
        ]

        return {
            'tenants': [{'id': t.id, 'nom': t.nom} for t in tenants],
            'plans': plans,
            'providers': sorted(providers),
            'payment_methods': sorted(payment_methods),
            'statuses': statuses,
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

        from app.security.plans import PLAN_CONFIG
        plans_data = []
        for plan in PLANS:
            count = 0
            if plan['code'] != 'gratuit':
                count = db.session.query(func.count(Abonnement.id)).filter(
                    Abonnement.plan == plan['code'],
                    Abonnement.is_active == True,
                ).scalar() or 0
            cfg = PLAN_CONFIG.get(plan['code'], {})
            plans_data.append({
                'code': plan['code'],
                'label': plan['label'],
                'prix': plan['prix'],
                'duree_jours': plan['duree_jours'],
                'max_utilisateurs': cfg.get('max_utilisateurs', 1),
                'max_employees': cfg.get('max_employees', 0),
                'modules': cfg.get('modules', []),
                'tenants_count': count,
            })

        return {
            'plans': plans_data,
        }, 200

    @jwt_required()
    def put(self):
        from app.security.plans import PLAN_CONFIG
        err = _ensure_super_admin()
        if err:
            return err

        data = request.get_json()
        if not data:
            return {'message': 'Données requises'}, 400

        code = data.get('code')
        if not code:
            return {'message': 'Code du plan requis'}, 400

        plan = next((p for p in PLANS if p['code'] == code), None)
        if not plan:
            return {'message': 'Plan non trouvé'}, 404

        if 'prix' in data:
            try:
                prix = int(data['prix'])
                if prix < 0:
                    return {'message': 'Le prix doit être positif'}, 400
                plan['prix'] = prix
                if code in PLAN_CONFIG:
                    PLAN_CONFIG[code]['prix'] = prix
            except (ValueError, TypeError):
                return {'message': 'Prix invalide'}, 400

        if 'duree_jours' in data:
            try:
                duree = int(data['duree_jours'])
                if duree != -1 and duree <= 0:
                    return {'message': 'La durée doit être positive ou -1 pour illimité'}, 400
                plan['duree_jours'] = duree
                if code in PLAN_CONFIG:
                    PLAN_CONFIG[code]['duree_jours'] = duree
            except (ValueError, TypeError):
                return {'message': 'Durée invalide'}, 400

        _log_audit(
            TypeActionAudit.MODIFICATION_PARAMETRE,
            f"Modification plan {code}: prix={plan['prix']}, durée={plan['duree_jours']}j",
            metadata={'plan_code': code, 'prix': plan['prix'], 'duree_jours': plan['duree_jours']},
        )

        try:
            broadcast_to_super_admin('plan:updated', {
                'code': plan['code'],
                'label': plan['label'],
                'prix': plan['prix'],
                'duree_jours': plan['duree_jours'],
            })
        except Exception:
            pass

        return {
            'message': 'Plan mis à jour',
            'plan': {
                'code': plan['code'],
                'label': plan['label'],
                'prix': plan['prix'],
                'duree_jours': plan['duree_jours'],
            }
        }, 200


@ns.route('/employes')
class SuperAdminEmployesList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        tenant_id = request.args.get('tenant_id', type=int)
        statut = request.args.get('statut')

        query = Employe.query.filter_by(is_active=True)

        if tenant_id:
            query = query.filter(Employe.tenant_id == tenant_id)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Employe.nom.ilike(search_filter),
                    Employe.prenom.ilike(search_filter),
                    Employe.matricule.ilike(search_filter),
                )
            )

        if statut:
            query = query.filter(Employe.statut == statut)

        query = query.order_by(Employe.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        employes_data = []
        for employe in paginated.items:
            emp_dict = employe.to_dict()
            tenant = db.session.get(Tenant, employe.tenant_id)
            emp_dict['tenant_nom'] = tenant.nom if tenant else None
            emp_dict['tenant_slug'] = tenant.slug if tenant else None
            employes_data.append(emp_dict)

        return {
            'employes': employes_data,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages,
        }, 200


@ns.route('/employes/<int:employe_id>')
class SuperAdminEmployeDetail(Resource):
    @jwt_required()
    def get(self, employe_id):
        err = _ensure_super_admin()
        if err:
            return err

        employe = Employe.query.filter_by(id=employe_id, is_active=True).first()
        if not employe:
            return {'message': 'Employe non trouve'}, 404

        data = employe.to_dict()
        tenant = db.session.get(Tenant, employe.tenant_id)
        data['tenant_nom'] = tenant.nom if tenant else None
        data['tenant_slug'] = tenant.slug if tenant else None
        return data, 200

    @jwt_required()
    def put(self, employe_id):
        err = _ensure_super_admin()
        if err:
            return err

        employe = Employe.query.filter_by(id=employe_id, is_active=True).first()
        if not employe:
            return {'message': 'Employe non trouve'}, 404

        data = request.get_json() or {}
        allowed_fields = {
            'nom', 'prenom', 'matricule', 'date_naissance', 'lieu_naissance',
            'sexe', 'adresse', 'date_embauche', 'date_fin_contrat', 'type_contrat',
            'salaire_base', 'coefficient', 'anciennete', 'banque_nom', 'banque_iban',
            'banque_bic', 'photo', 'statut', 'notes', 'departement', 'poste',
        }

        for key, value in data.items():
            if key in allowed_fields and hasattr(employe, key):
                if key in ('sexe', 'type_contrat', 'statut') and isinstance(value, str):
                    enum_map = {
                        'sexe': {'M': 'M', 'F': 'F'},
                        'type_contrat': {'cdi': 'cdi', 'cdd': 'cdd', 'stage': 'stage', 'freelance': 'freelance'},
                        'statut': {'actif': 'actif', 'inactif': 'inactif', 'en_conges': 'en_conges', 'depart': 'depart'},
                    }
                    mapped = enum_map.get(key, {}).get(value.lower())
                    if mapped:
                        setattr(employe, key, mapped)
                else:
                    setattr(employe, key, value)

        db.session.commit()
        db.session.refresh(employe)

        result = employe.to_dict()
        tenant = db.session.get(Tenant, employe.tenant_id)
        result['tenant_nom'] = tenant.nom if tenant else None
        result['tenant_slug'] = tenant.slug if tenant else None

        _log_audit(
            TypeActionAudit.MODIFICATION_EMPLOYE,
            f"Modification de l'employe {employe.nom_complet} (id={employe.id}) par le super admin",
            tenant_id=employe.tenant_id,
            metadata={'employe_id': employe.id, 'matricule': employe.matricule},
        )

        return result, 200

    @jwt_required()
    def delete(self, employe_id):
        err = _ensure_super_admin()
        if err:
            return err

        employe = Employe.query.filter_by(id=employe_id, is_active=True).first()
        if not employe:
            return {'message': 'Employe non trouve'}, 404

        employe.delete()

        _log_audit(
            TypeActionAudit.SUPPRESSION_EMPLOYE,
            f"Suppression de l'employe {employe.nom_complet} (id={employe.id}, matricule={employe.matricule}) par le super admin",
            tenant_id=employe.tenant_id,
            metadata={'employe_id': employe.id, 'matricule': employe.matricule},
        )

        return {'message': 'Employe supprime'}, 200


def _cascade_delete_tenant_data(tenant_id):
    """Desactive en cascade toutes les données d'un tenant (soft-delete).

    Cette fonction effectue une suppression logique de toutes les données
    associees au tenant : utilisateurs, employes, produits, clients, fournisseurs,
    ventes, factures, abonnements, paiements, etc. Aucune donnee n'est
    physiquement supprimee afin de preserver l'historique et la tracabilite.
    """
    from app.models.stagiaire import Stagiaire
    from app.models.presence import Presence
    from app.models.salaire import Salaire
    from app.models.prime import Prime
    from app.models.commande_achat import CommandeAchat, ReceptionAchat, QualiteAchat
    from app.models.devis_avoir_bl import Devis, BonLivraison, Avoir
    from app.models.livraison import Livraison
    from app.models.stock import MouvementStock
    from app.models.compte_comptable import CompteComptable
    from app.models.ecriture_comptable import EcritureComptable
    from app.models.audit_log import AuditLog
    from app.models.document_genere import DocumentGenere
    from app.models.notification import Notification
    from app.models.admin_device import AdminDevice
    from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
    from app.models.password_reset_token import PasswordResetToken
    from app.models.ligne_vente import LigneVente
    from app.models.ligne_achat import LigneAchat
    from app.models.commande_client import CommandeClient
    from app.models.suivi_livraison import SuiviLivraison
    from app.models.payment_event import PaymentEvent
    from app.models.facture_fournisseur import FactureFournisseur
    from app.models.livreur import Livreur
    from app.models.vehicule import Vehicule
    from app.models.itineraire import Itineraire

    tenant_models = [
        PaymentEvent, LigneVente, LigneAchat, QualiteAchat,
        ReceptionAchat, SuiviLivraison, DocumentGenere,
        Presence, Salaire, Prime, MouvementStock,
        Notification, AdminDevice,
        DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent,
        PasswordResetToken, FactureFournisseur,
        Tresorerie, EcritureComptable, BonLivraison, Avoir,
        Devis, Livraison, Vente, CommandeClient,
        CommandeFournisseur, CommandeAchat, Facture,
        Client, Fournisseur, Stagiaire,
        Employe, Produit, ModeleDocument, CompteComptable,
        Livreur, Vehicule, Itineraire, AuditLog,
    ]
    for model in tenant_models:
        try:
            model.query.filter_by(tenant_id=tenant_id, is_active=True).update(
                {model.is_active: False}, synchronize_session=False
            )
        except Exception:
            pass

    abonnements = Abonnement.query.filter_by(tenant_id=tenant_id, is_active=True).all()
    for abonnement in abonnements:
        db.session.delete(abonnement)

    users = Utilisateur.query.filter_by(tenant_id=tenant_id, is_active=True).all()
    for user in users:
        user.mark_deleted()


def _hard_delete_tenant_data(tenant_id):
    """Supprime physiquement toutes les donnees d'un tenant.

    Cette fonction effectue une suppression reelle de toutes les donnees
    associees au tenant dans l'ordre des dependances FK pour eviter
    les violations de contrainte.
    """
    from app.models.stagiaire import Stagiaire
    from app.models.presence import Presence
    from app.models.salaire import Salaire
    from app.models.prime import Prime
    from app.models.commande_achat import CommandeAchat, ReceptionAchat, QualiteAchat
    from app.models.devis_avoir_bl import Devis, BonLivraison, Avoir
    from app.models.livraison import Livraison
    from app.models.stock import MouvementStock
    from app.models.compte_comptable import CompteComptable
    from app.models.ecriture_comptable import EcritureComptable
    from app.models.audit_log import AuditLog
    from app.models.document_genere import DocumentGenere
    from app.models.notification import Notification
    from app.models.admin_device import AdminDevice
    from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
    from app.models.password_reset_token import PasswordResetToken
    from app.models.ligne_vente import LigneVente
    from app.models.ligne_achat import LigneAchat
    from app.models.commande_client import CommandeClient
    from app.models.suivi_livraison import SuiviLivraison
    from app.models.payment_event import PaymentEvent
    from app.models.facture_fournisseur import FactureFournisseur
    from app.models.livreur import Livreur
    from app.models.vehicule import Vehicule
    from app.models.itineraire import Itineraire

    hard_delete_order = [
        SyncEvent,
        PasswordResetToken,
        Notification,
        DeskFavorite,
        DeskFilterPreset,
        DeskColumnConfig,
        AdminDevice,
        Presence,
        Salaire,
        Prime,
        Stagiaire,
        PaymentEvent,
        LigneVente,
        LigneAchat,
        SuiviLivraison,
        EcritureComptable,
        DocumentGenere,
        Paiement,
        Avoir,
        BonLivraison,
        Facture,
        Vente,
        Devis,
        Livraison,
        CommandeClient,
        CommandeFournisseur,
        QualiteAchat,
        ReceptionAchat,
        CommandeAchat,
        FactureFournisseur,
        MouvementStock,
        Produit,
        Client,
        Fournisseur,
        Employe,
        Livreur,
        Vehicule,
        Itineraire,
        Abonnement,
        CompteComptable,
        Tresorerie,
        ModeleDocument,
        Utilisateur,
    ]

    for user in Utilisateur.query.filter_by(tenant_id=tenant_id):
        AdminDevice.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    for model in hard_delete_order:
        try:
            model.query.filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        except Exception:
            pass

    Tenant.query.filter_by(id=tenant_id).delete(synchronize_session=False)


@ns.route('/users')
class SuperAdminUsersList(Resource):
    @jwt_required()
    def get(self):
        """Liste tous les utilisateurs de la plateforme (super admin seulement).
        
        Filtrage par rôle : par défaut, montre seulement les admins (ADMIN et SUPER_ADMIN).
        Utiliser ?role=all pour voir tous les utilisateurs.
        """
        err = _ensure_super_admin()
        if err:
            return err

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', 'admins')
        tenant_id = request.args.get('tenant_id', type=int)
        statut = request.args.get('statut')

        query = Utilisateur.query.filter_by(is_active=True)
        query = query.filter(Utilisateur.statut == StatutUtilisateur.ACTIF)

        if tenant_id:
            query = query.filter(Utilisateur.tenant_id == tenant_id)

        if role_filter == 'admins':
            query = query.filter(
                Utilisateur.role.in_([Role.ADMIN, Role.SUPER_ADMIN])
            )
        elif role_filter == 'tenant_admins':
            query = query.filter(Utilisateur.role == Role.ADMIN)
        elif role_filter == 'super_admins':
            query = query.filter(Utilisateur.role == Role.SUPER_ADMIN)
        elif role_filter == 'employees':
            query = query.filter(
                Utilisateur.role.in_([Role.USER, Role.SALES, Role.STOCK, Role.ACCOUNTANT, Role.RH, Role.MANAGER])
            )
        elif role_filter and role_filter != 'all':
            try:
                role_enum = Role(role_filter)
                query = query.filter(Utilisateur.role == role_enum)
            except ValueError:
                pass

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Utilisateur.username.ilike(search_filter),
                    Utilisateur.email.ilike(search_filter),
                    Utilisateur.nom.ilike(search_filter),
                    Utilisateur.prenom.ilike(search_filter),
                )
            )

        if statut:
            try:
                statut_enum = StatutUtilisateur(statut)
                query = query.filter(Utilisateur.statut == statut_enum)
            except ValueError:
                pass

        query = query.order_by(Utilisateur.created_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        users_data = []
        for user in paginated.items:
            user_dict = user.to_dict()
            tenant = (
                db.session.get(Tenant, user.tenant_id)
                if user.tenant_id is not None
                else None
            )
            user_dict['tenant_nom'] = tenant.nom if tenant else None
            user_dict['tenant_slug'] = tenant.slug if tenant else None
            users_data.append(user_dict)

        return {
            'users': users_data,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages,
        }, 200


@ns.route('/users/<int:user_id>')
class SuperAdminUserDetail(Resource):
    @jwt_required()
    def get(self, user_id):
        err = _ensure_super_admin()
        if err:
            return err

        user = db.session.get(Utilisateur, user_id)
        if not user:
            return {'message': 'Utilisateur non trouvé'}, 404

        user_dict = user.to_dict()
        tenant = (
            db.session.get(Tenant, user.tenant_id)
            if user.tenant_id is not None
            else None
        )
        user_dict['tenant_nom'] = tenant.nom if tenant else None
        user_dict['tenant_slug'] = tenant.slug if tenant else None
        return user_dict, 200

    @jwt_required()
    def delete(self, user_id):
        """Suppression d'un utilisateur par le super admin.
        
        Si c'est un admin de tenant, supprime aussi le tenant et toutes ses données.
        """
        err = _ensure_super_admin()
        if err:
            return err

        try:
            user = db.session.get(Utilisateur, user_id)
            if not user:
                return {'message': 'Utilisateur non trouvé'}, 404

            if user.is_super_admin:
                return {'message': 'Impossible de supprimer un super administrateur'}, 400

            user_username = user.username
            tenant_id = user.tenant_id
            is_admin = user.role == Role.ADMIN

            if is_admin and tenant_id:
                tenant = db.session.get(Tenant, tenant_id)
                tenant_nom = tenant.nom if tenant else "inconnu"
                _hard_delete_tenant_data(tenant_id)
                message = f"Admin {user_username}, tenant {tenant_nom} et toutes ses données ont été supprimés"
            else:
                user.mark_deleted()
                message = f"Utilisateur {user_username} désactivé"

            db.session.commit()

            _log_audit(
                TypeActionAudit.SUPPRESSION_UTILISATEUR,
                f"Suppression de l'utilisateur {user_username} (id={user_id}) par le super admin",
                tenant_id=tenant_id,
                metadata={'user_id': user_id, 'is_admin': is_admin},
            )

            if is_admin and tenant:
                try:
                    broadcast_to_tenant(tenant.id, 'tenant:updated', tenant.to_dict())
                except Exception:
                    pass

            return {'message': message}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'Erreur lors de la suppression: {str(e)}'}, 500
