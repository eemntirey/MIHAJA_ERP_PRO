
import os
from flask import current_app, request
from flask_restx import Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token,
    create_refresh_token,
)
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app import db
from app.security.auth import (
    authenticate_user, hash_password, _validate_password, verify_password,
    invalidate_user_tokens, require_password_changed,
)
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur, StatutAdmin
from app.models.tenant import Tenant, StatutTenant
from app.security.roles import is_super_admin
from app.security.plans import check_tenant_limit
from app.services.abonnement_service import AbonnementService
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

from app.security.rate_limit import rate_limit

api = Namespace(
    'auth',
    description='Authentification et JWT'
)


@api.route('/plans')
class PublicPlans(Resource):
    def get(self):
        from app.security.plans import PLAN_CONFIG
        return {
            'plans': [
                {
                    'code': code,
                    'label': config.get('label', code.replace('_', ' ').title()),
                    'prix': config.get('prix', 0),
                    'duree_jours': config.get('duree_jours', 30),
                    'max_utilisateurs': config.get('max_utilisateurs', 1),
                    'max_employees': config.get('max_employees', 0),
                    'modules': config.get('modules', []),
                }
                for code, config in PLAN_CONFIG.items()
            ]
        }, 200


@api.route('/login')
class AuthLogin(Resource):

    @rate_limit(5, 300)
    def post(self):
        data = request.get_json() or {}

        identifier = data.get('username') or data.get('email')
        password = data.get('password')
        tenant_slug = data.get('tenant_slug')
        device_id = data.get('device_id')

        if not identifier or not password:
            return {
                'message': 'Identifiant et mot de passe requis'
            }, 400

        try:
            result, error = authenticate_user(
                identifier,
                password,
                tenant_slug=tenant_slug,
                device_id=device_id,
            )
        except Exception:
            current_app.logger.exception(
                'Erreur inattendue pendant l authentification de %s',
                identifier
            )
            return {
                'message': 'Erreur interne du service d\'authentification'
            }, 500

        if error:
            return {
                'message': error
            }, 401

        access_token = result.get('access_token') if isinstance(result, dict) else None
        user_data = result.get('user') if isinstance(result, dict) else None
        if not isinstance(access_token, str) or not access_token.strip() or not isinstance(user_data, dict):
            current_app.logger.error(
                'Réponse d authentification incomplète pour %s',
                identifier
            )
            return {
                'message': 'Le service d\u2019authentification n\u2019a pas généré une session valide'
            }, 500

        return result, 200


@api.route('/me')
class AuthMe(Resource):

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        tenant = None

        if user.tenant_id:
            tenant = db.session.get(Tenant, user.tenant_id)

        tenant_data = tenant.to_dict(include_subscription=True) if tenant else None

        return {
            'user': user.to_dict(),
            'tenant': tenant_data,
        }, 200

    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        data = request.get_json() or {}
        sensitive_fields = {'email', 'password'}
        provided_fields = set(data.keys())
        if sensitive_fields & provided_fields:
            password = data.get('password')
            if not password or not verify_password(password, user.password_hash):
                return {'message': 'Mot de passe actuel requis pour modifier les champs sensibles'}, 403

        for key, value in data.items():
            if key in ['nom', 'prenom', 'telephone', 'mobile', 'email']:
                setattr(user, key, value)

        db.session.commit()

        return {
            'user': user.to_dict()
        }, 200


@api.route('/register')
class AuthRegister(Resource):

    @rate_limit(5, 300)
    def post(self):
        data = request.get_json() or {}

        profile_type = data.get('profile_type', 'simple')
        email = data.get('email')
        username = data.get('username') or email
        password = data.get('password')
        nom = data.get('nom')
        prenom = data.get('prenom')
        telephone = data.get('telephone')

        if not email or not username or not password:
            return {
                'message': 'Email, username et mot de passe requis'
            }, 400

        pwd_error = _validate_password(password)
        if pwd_error:
            return {'message': pwd_error}, 400

        # Réinscription après suppression : un compte désactivé (soft-delete)
        # peut encore occuper l'email/username ; on libère ces identifiants
        # afin qu'une nouvelle inscription utilise le même email.
        Utilisateur.free_inactive_credentials(email=email, username=username)

        if Utilisateur.query.filter(
            Utilisateur.is_active == True,
            (Utilisateur.email == email) | (Utilisateur.username == username)
        ).first():
            return {
                "message": "Un compte avec cet email ou nom d'utilisateur existe déjà"
            }, 409

        hashed_password = hash_password(password)

        if profile_type == 'company':
            nom_entreprise = data.get('nom_entreprise')
            domaine = data.get('domaine')
            adresse = data.get('adresse')
            ville = data.get('ville')
            code_postal = data.get('code_postal')
            pays = data.get('pays', 'Madagascar')
            email_contact = data.get('email_contact', email)
            telephone_entreprise = data.get('telephone_entreprise')
            plan = data.get('plan', 'starter')

            if not nom_entreprise:
                return {'message': 'Le nom de l\'entreprise est requis'}, 400

            allowed, limit_message = check_tenant_limit(plan)
            if not allowed:
                return {'message': limit_message}, 403

            base_slug = nom_entreprise.lower().replace(' ', '-').replace('.', '-')
            slug = base_slug
            counter = 1
            while Tenant.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            try:
                tenant = Tenant(
                    nom=nom_entreprise,
                    slug=slug,
                    domaine=domaine,
                    email_contact=email_contact,
                    telephone=telephone_entreprise or telephone,
                    adresse=adresse,
                    ville=ville,
                    code_postal=code_postal,
                    pays=pays,
                    statut=StatutTenant.EN_ESSAI,
                    plan=plan,
                )
                db.session.add(tenant)
                db.session.flush()

                user = Utilisateur(
                    username=username,
                    email=email,
                    password_hash=hashed_password,
                    nom=nom,
                    prenom=prenom,
                    telephone=telephone,
                    role=Role.ADMIN,
                    statut=StatutUtilisateur.ACTIF,
                    admin_statut=StatutAdmin.ACTIVE,
                    tenant_id=tenant.id,
                    is_principal_admin=True,
                )
                db.session.add(user)
                db.session.flush()

                tenant.admin_principal_id = user.id
                db.session.add(tenant)
                db.session.flush()

                AbonnementService.create_abonnement({
                    'tenant_id': tenant.id,
                    'plan': plan,
                })

                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                current_app.logger.exception(
                    'Erreur d\'integrite lors de la creation du tenant pour %s',
                    email
                )
                return {
                    'message': 'Une entreprise avec ce nom ou ce domaine existe deja. Veuillez choisir un nom ou domaine different.'
                }, 409
            except Exception as exc:
                db.session.rollback()
                current_app.logger.exception(
                    'Erreur inattendue lors de la creation du tenant pour %s: %s',
                    email, exc
                )
                return {
                    'message': 'Erreur lors de la creation de l\'entreprise. Verifiez les champs (slug/domaine uniques) et reessayez.'
                }, 500

            access_token = create_access_token(
                identity=user.id,
                additional_claims={
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value if hasattr(user.role, 'value') else user.role,
                    'tenant_id': tenant.id,
                    'tenant_slug': tenant.slug,
                }
            )
            refresh_token = create_refresh_token(identity=user.id)

            return {
                'message': 'Compte entreprise créé avec succès',
                'user': user.to_dict(),
                'tenant': tenant.to_dict(),
                'profile_type': 'company',
                'access_token': access_token,
                'refresh_token': refresh_token,
            }, 201

        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hashed_password,
            nom=nom,
            prenom=prenom,
            telephone=telephone,
            role=Role.USER,
            statut=StatutUtilisateur.ACTIF,
        )

        db.session.add(user)
        db.session.flush()

        db.session.commit()

        access_token = create_access_token(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value if hasattr(user.role, 'value') else user.role,
                'tenant_id': user.tenant_id,
            }
        )
        refresh_token = create_refresh_token(identity=user.id)

        return {
            'message': 'Compte utilisateur créé avec succès',
            'user': user.to_dict(),
            'profile_type': 'simple',
            'access_token': access_token,
            'refresh_token': refresh_token,
        }, 201


@api.route('/refresh')
class AuthRefresh(Resource):

    @jwt_required(refresh=True)
    def post(self):
        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        tenant = None

        if user.tenant_id:
            tenant = db.session.get(Tenant, user.tenant_id)

        access_token = create_access_token(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'email': user.email,
                'role': (
                    user.role.value
                    if hasattr(user.role, 'value')
                    else user.role
                ),
                'tenant_id': tenant.id if tenant else user.tenant_id,
                'tenant_slug': tenant.slug if tenant else None,
            }
        )

        if not isinstance(access_token, str) or not access_token.strip():
            current_app.logger.error(
                'Impossible de générer un access_token pour l utilisateur %s',
                user.id
            )
            return {
                'message': 'Impossible de renouveler la session'
            }, 500

        return {
            'access_token': access_token,
            'refresh_token': None,
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None,
        }, 200


@api.route('/logout')
class AuthLogout(Resource):

    def post(self):
        return {
            'message': 'Deconnexion reussie'
        }, 200


@api.route('/forgot-password')
class AuthForgotPassword(Resource):

    @rate_limit(5, 300)
    def post(self):
        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            return {'message': 'Email requis'}, 400

        user = Utilisateur.query.filter_by(email=email, is_active=True).first()

        if user:
            from app.models.password_reset_token import PasswordResetToken

            # Invalider les tokens précédents non utilisés
            PasswordResetToken.query.filter_by(
                user_id=user.id,
                used=False
            ).update({'used': True})
            db.session.commit()

            raw_token = PasswordResetToken.generate_token()
            hashed_token = PasswordResetToken.hash_token(raw_token)
            ttl_minutes = int(os.environ.get('PASSWORD_RESET_TTL_MINUTES', '30'))
            token = PasswordResetToken(
                user_id=user.id,
                token=hashed_token,
                expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
                ip_address=request.remote_addr,
            )
            db.session.add(token)
            db.session.commit()

            app_url = (
                os.environ.get('APP_URL')
                or os.environ.get('PUBLIC_APP_URL')
                or os.environ.get('FRONTEND_URL')
                or request.host_url.rstrip('/')
            )
            reset_link = f"{app_url.rstrip('/')}/reset-password/{raw_token}"

            # Envoi de l'e-mail de réinitialisation
            try:
                from app.services.email_service import send_password_reset_email
                tenant = db.session.get(Tenant, user.tenant_id) if user.tenant_id else None
                # Le service reconstruit lui-même le lien à partir de APP_URL
                # et du raw_token ; on lui passe donc le token brut.
                send_password_reset_email(user, tenant, raw_token, expires_in_minutes=ttl_minutes, app_url=app_url)
            except Exception:
                current_app.logger.exception(
                    'Erreur lors de l\'envoi du mail de reset pour %s', user.email
                )

            # Audit log — sans enregistrer le token brut
            try:
                log_audit(
                    TypeActionAudit.PASSWORD_RESET_REQUESTED,
                    f"Demande de réinitialisation du mot de passe pour {user.email}",
                    tenant_id=user.tenant_id,
                    utilisateur_id=user.id,
                    metadata={'ip': request.remote_addr},
                )
            except Exception:
                pass

            current_app.logger.info(
                'Password reset requested for %s from IP %s',
                user.email,
                request.remote_addr,
            )

        return {
            'message': 'Si un compte existe avec cet email, un lien de réinitialisation a été envoyé.'
        }, 200


@api.route('/verify-reset-token')
class AuthVerifyResetToken(Resource):
    """Vérifie la validité d'un token de réinitialisation sans l'utiliser."""

    def post(self):
        data = request.get_json() or {}
        token = data.get('token')
        if not token:
            return {'message': 'Token requis'}, 400

        from app.models.password_reset_token import PasswordResetToken
        reset_token = PasswordResetToken.find_by_raw_token(token)

        if not reset_token:
            return {'valid': False, 'message': 'Token invalide ou expiré'}, 400

        if reset_token.used:
            return {'valid': False, 'message': 'Token déjà utilisé'}, 400

        user = db.session.get(Utilisateur, reset_token.user_id)
        if not user or not user.is_active:
            return {'valid': False, 'message': 'Utilisateur introuvable'}, 404

        remaining = None
        if reset_token.expires_at:
            remaining = max(0, int((reset_token.expires_at - datetime.utcnow()).total_seconds()))

        return {
            'valid': True,
            'message': 'Token valide',
            'remaining_seconds': remaining,
            'email': user.email,
        }, 200


@api.route('/reset-password')
class AuthResetPassword(Resource):

    def post(self):
        data = request.get_json() or {}
        token = data.get('token')
        new_password = data.get('new_password')
        if not token or not new_password:
            return {'message': 'Token et nouveau mot de passe requis'}, 400

        from app.models.password_reset_token import PasswordResetToken

        reset_token = PasswordResetToken.find_by_raw_token(token)
        if not reset_token:
            # Audit — token invalide ou expiré
            try:
                log_audit(
                    TypeActionAudit.PASSWORD_RESET_FAILED,
                    'Tentative de reset avec token invalide ou expiré',
                    metadata={'ip': request.remote_addr},
                )
            except Exception:
                pass
            return {'message': 'Token invalide ou expiré'}, 400

        pwd_error = _validate_password(new_password)
        if pwd_error:
            return {'message': pwd_error}, 400

        user = db.session.get(Utilisateur, reset_token.user_id)
        if not user or not user.is_active:
            return {'message': 'Utilisateur non trouvé'}, 404

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.utcnow()
        reset_token.used = True
        # Invalide toutes les sessions precedentes
        invalidate_user_tokens(user)
        db.session.commit()

        # Notification e-mail après reset
        try:
            from app.services.email_service import send_password_changed_email
            tenant = db.session.get(Tenant, user.tenant_id) if user.tenant_id else None
            send_password_changed_email(user, tenant=tenant)
        except Exception:
            current_app.logger.exception(
                'Erreur lors de l\'envoi de l\'email de confirmation reset pour %s',
                user.email
            )

        # Audit
        try:
            log_audit(
                TypeActionAudit.PASSWORD_RESET_COMPLETED,
                f"Réinitialisation du mot de passe complétée pour {user.email}",
                tenant_id=user.tenant_id,
                utilisateur_id=user.id,
                metadata={'ip': request.remote_addr},
            )
        except Exception:
            pass

        return {'message': 'Mot de passe réinitialisé avec succès'}, 200


def _first_change_password_post():
    """Implémentation partagée entre /auth/first-change-password et
    /auth/first-login-change. Cette dernière URL est celle attendue
    par le frontend (Login.jsx, FirstLoginChange.jsx) pour rester
    compatible avec les deux frontends (web et desktop)."""
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)

    if not user or not user.is_active:
        return {'message': 'Utilisateur non trouvé'}, 404

    if not user.must_change_password:
        return {
            'message': 'Aucun changement obligatoire de mot de passe en attente'
        }, 400

    data = request.get_json() or {}
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not new_password or not confirm_password:
        return {'message': 'Nouveau mot de passe et confirmation requis'}, 400

    if new_password != confirm_password:
        return {'message': 'Les mots de passe ne correspondent pas'}, 400

    pwd_error = _validate_password(new_password)
    if pwd_error:
        return {'message': pwd_error}, 400

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.utcnow()
    invalidate_user_tokens(user)
    db.session.commit()

    # Notification e-mail
    try:
        from app.services.email_service import send_password_changed_email
        tenant = db.session.get(Tenant, user.tenant_id) if user.tenant_id else None
        send_password_changed_email(user, tenant=tenant)
    except Exception:
        current_app.logger.exception(
            'Erreur lors de l\'envoi email first-change pour %s', user.email
        )

    # Audit
    try:
        log_audit(
            TypeActionAudit.PASSWORD_FIRST_CHANGE,
            f"Premiere modification du mot de passe pour {user.email}",
            tenant_id=user.tenant_id,
            utilisateur_id=user.id,
            metadata={'ip': request.remote_addr},
        )
    except Exception:
        pass

    return {
        'message': 'Mot de passe modifié avec succès',
        'user': user.to_dict(),
    }, 200


@api.route('/first-change-password')
class AuthFirstChangePassword(Resource):
    """Endpoint historique pour le changement obligatoire du mot de passe."""

    @jwt_required()
    def post(self):
        return _first_change_password_post()


@api.route('/first-login-change')
class AuthFirstLoginChange(Resource):
    """Alias moderne de /auth/first-change-password utilisé par le frontend."""

    @jwt_required()
    def post(self):
        return _first_change_password_post()


@api.route('/change-password')
class AuthChangePassword(Resource):
    """Changement volontaire du mot de passe pour un utilisateur connecté.

    Requiert l'ancien mot de passe. Envoie une notification e-mail après
    modification réussie et enregistre l'événement dans l'audit log.
    """

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)

        if not user or not user.is_active:
            return {'message': 'Utilisateur non trouvé'}, 404

        data = request.get_json() or {}
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return {'message': 'Ancien mot de passe, nouveau mot de passe et confirmation requis'}, 400

        # Vérifier l'ancien mot de passe
        if not verify_password(old_password, user.password_hash):
            try:
                log_audit(
                    TypeActionAudit.PASSWORD_RESET_FAILED,
                    f"Tentative de changement de mot de passe avec ancien mot de passe incorrect pour {user.email}",
                    tenant_id=user.tenant_id,
                    utilisateur_id=user.id,
                )
            except Exception:
                pass
            return {'message': 'Ancien mot de passe incorrect'}, 403

        if new_password != confirm_password:
            return {'message': 'Les mots de passe ne correspondent pas'}, 400

        pwd_error = _validate_password(new_password)
        if pwd_error:
            return {'message': pwd_error}, 400

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.utcnow()
        invalidate_user_tokens(user)
        db.session.commit()

        # Notification e-mail
        try:
            from app.services.email_service import send_password_changed_email
            tenant = db.session.get(Tenant, user.tenant_id) if user.tenant_id else None
            send_password_changed_email(user, tenant=tenant)
        except Exception:
            current_app.logger.exception(
                'Erreur lors de l\'envoi email change-password pour %s', user.email
            )

        # Audit
        try:
            log_audit(
                TypeActionAudit.PASSWORD_CHANGED,
                f"Modification du mot de passe par l'utilisateur {user.email}",
                tenant_id=user.tenant_id,
                utilisateur_id=user.id,
                metadata={'ip': request.remote_addr},
            )
        except Exception:
            pass

        return {
            'message': 'Mot de passe modifié avec succès',
            'user': user.to_dict(),
        }, 200


@api.route('/super-admin/me')
class SuperAdminMe(Resource):

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        if not is_super_admin(user.role):
            return {
                'message': 'Acces refuse'
            }, 403

        return {
            'user': user.to_dict()
        }, 200

    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        if not is_super_admin(user.role):
            return {
                'message': 'Acces refuse'
            }, 403

        data = request.get_json() or {}
        for key, value in data.items():
            if key in ['nom', 'prenom', 'telephone', 'mobile', 'email']:
                setattr(user, key, value)

        db.session.commit()

        return {
            'user': user.to_dict()
        }, 200
