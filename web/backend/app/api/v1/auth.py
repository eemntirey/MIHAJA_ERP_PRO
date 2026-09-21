
import os
from flask import current_app, request
from flask_restx import Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
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
from app.services.modele_seed_service import seed_modeles_systeme
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
        from app.security.plans import get_public_plans
        return {
            'plans': get_public_plans(),
        }, 200


@api.route('/login')
class AuthLogin(Resource):

    @rate_limit(30, 300)
    def post(self):
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            current_app.logger.exception('Corps de requete invalide pour /auth/login')
            return {
                'message': 'Corps de requete invalide (JSON attendu)'
            }, 400

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
        refresh_token = result.get('refresh_token') if isinstance(result, dict) else None
        user_data = result.get('user') if isinstance(result, dict) else None
        if not isinstance(access_token, str) or not access_token.strip() or not isinstance(user_data, dict):
            current_app.logger.error(
                'Réponse d authentification incomplète pour %s',
                identifier
            )
            return {
                'message': 'Le service d\u2019authentification n\u2019a pas généré une session valide'
            }, 500

        # A1 FIX : les tokens sont envoyés en cookies HttpOnly (XSS-safe).
        # Les tokens restent aussi dans le body pour Electron (secureStore).
        resp = {'user': user_data}
        if refresh_token:
            resp['access_token'] = access_token
            resp['refresh_token'] = refresh_token
        resp_obj = current_app.response_class(
            response=__import__('json').dumps(resp),
            status=200,
            mimetype='application/json',
        )
        set_access_cookies(resp_obj, access_token)
        if refresh_token:
            set_refresh_cookies(resp_obj, refresh_token)
        return resp_obj


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

    @rate_limit(30, 300)
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
            # Règle métier : toute nouvelle entreprise/grossiste démarre toujours
            # sur le plan gratuit (30 jours inclus). Le passage aux plans payants
            # (Pro, Entreprise) nécessite un paiement validé via la page Abonnement.
            plan = 'gratuit'

            if not nom_entreprise:
                return {'message': 'Le nom de l\'entreprise est requis'}, 400

            tenant_field_limits = {
                'nom_entreprise': 200,
                'domaine': 200,
                'email_contact': 120,
                'telephone_entreprise': 20,
                'adresse': 200,
                'ville': 100,
                'code_postal': 20,
                'pays': 50,
                'plan': 50,
            }
            tenant_values = {
                'nom_entreprise': nom_entreprise,
                'domaine': domaine,
                'email_contact': email_contact,
                'telephone_entreprise': telephone_entreprise,
                'adresse': adresse,
                'ville': ville,
                'code_postal': code_postal,
                'pays': pays,
                'plan': plan,
            }
            for field, limit in tenant_field_limits.items():
                value = tenant_values.get(field)
                if value is None:
                    continue
                if isinstance(value, str) and len(value) > limit:
                    return {
                        'message': "Le champ '{0}' depasse la longueur maximale autorisee ({1} caracteres).".format(field, limit)
                    }, 400

            allowed, limit_message = check_tenant_limit(plan)
            if not allowed:
                return {'message': limit_message}, 403

            # Pré-validation UX : le domaine est soumis à une contrainte
            # d'unicité en base (ix_tenants_domaine). On contrôle avant
            # l'insertion pour renvoyer une erreur ciblée au lieu de
            # laisser échapper l'IntegrityError ; la contrainte reste le
            # garde-fou en cas d'inscriptions concurrentes.
            if domaine and Tenant.query.filter_by(domaine=domaine).first():
                return {
                    'message': 'Une entreprise existe deja avec ce domaine. Veuillez en choisir un autre.'
                }, 409

            base_slug = nom_entreprise.lower().replace(' ', '-').replace('.', '-')
            slug = base_slug
            counter = 1
            while Tenant.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            try:
                from app.security.plans import get_plan_duration_days
                duree_essai = get_plan_duration_days(plan)
                now = datetime.utcnow()
                if duree_essai > 0:
                    date_fin_essai = now + timedelta(days=duree_essai)
                else:
                    date_fin_essai = now + timedelta(days=365 * 99)

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
                    date_debut_essai=now,
                    date_fin_essai=date_fin_essai,
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

                seed_modeles_systeme(tenant.id)

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
            refresh_token = create_refresh_token(
                identity=user.id,
                additional_claims={'pwd_v': user.token_version or 0},
            )

            import json as _json
            resp_data = {
                'message': 'Compte entreprise créé avec succès',
                'user': user.to_dict(),
                'tenant': tenant.to_dict(),
                'profile_type': 'company',
                'access_token': access_token,
                'refresh_token': refresh_token,
            }
            resp_obj = current_app.response_class(
                response=_json.dumps(resp_data),
                status=201,
                mimetype='application/json',
            )
            set_access_cookies(resp_obj, access_token)
            set_refresh_cookies(resp_obj, refresh_token)
            return resp_obj

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
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims={'pwd_v': user.token_version or 0},
        )

        import json as _json
        resp_data = {
            'message': 'Compte utilisateur créé avec succès',
            'user': user.to_dict(),
            'profile_type': 'simple',
            'access_token': access_token,
            'refresh_token': refresh_token,
        }
        resp_obj = current_app.response_class(
            response=_json.dumps(resp_data),
            status=201,
            mimetype='application/json',
        )
        set_access_cookies(resp_obj, access_token)
        set_refresh_cookies(resp_obj, refresh_token)
        return resp_obj


@api.route('/refresh')
class AuthRefresh(Resource):

    @jwt_required(refresh=True)
    def post(self):
        from flask_jwt_extended import get_jwt

        user_id = get_jwt_identity()

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        # V2/V3 : un refresh émis avant un changement de mot de passe ne
        # doit plus pouvoir forger de nouveaux access tokens. Les refresh
        # antérieurs à pwd_v (sans claim) portent 0 par défaut : ils restent
        # valides uniquement si l'utilisateur n'a jamais changé de mot de
        # passe (token_version == 0).
        refresh_claims = get_jwt() or {}
        refresh_pwd_v = refresh_claims.get('pwd_v', 0)
        if refresh_pwd_v < (user.token_version or 0):
            return {
                'message': 'Votre session a expire. Veuillez vous reconnecter.',
                'code': 'TOKEN_VERSION_EXPIRED',
            }, 401

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
                'pwd_v': user.token_version or 0,
            }
        )

        # Refresh token rotation : un nouveau refresh est émis à chaque
        # renouvellement d'access_token et il porte le pwd_v courant. Le
        # frontend doit stocker le refresh renvoyé (les intercepteurs
        # partagés le font déjà via tokenStore.setSession). Un refresh
        # antérieur à un changement de mot de passe est rejeté ci-dessus.
        new_refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims={'pwd_v': user.token_version or 0},
        )

        if not isinstance(access_token, str) or not access_token.strip():
            current_app.logger.error(
                'Impossible de générer un access_token pour l utilisateur %s',
                user.id
            )
            return {
                'message': 'Impossible de renouveler la session'
            }, 500

        # Audit P2-5 : détection de réutilisation du refresh token. Le
        # refresh présenté est immédiatement révoqué côte serveur après
        # avoir servi — un token volé ne peut pas être rejoué.
        from app.models.token_blocklist import TokenBlocklist
        used_claims = get_jwt() or {}
        used_jti = used_claims.get('jti')
        used_exp = used_claims.get('exp')
        if used_jti and used_exp:
            used_expires_at = datetime.utcfromtimestamp(used_exp)
            TokenBlocklist.revoke(
                used_jti,
                expires_at=used_expires_at,
                token_type='refresh',
                user_id=user.id,
            )
            db.session.commit()

        import json as _json
        resp_data = {
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None,
        }
        resp_obj = current_app.response_class(
            response=_json.dumps(resp_data),
            status=200,
            mimetype='application/json',
        )
        set_access_cookies(resp_obj, access_token)
        set_refresh_cookies(resp_obj, new_refresh_token)
        return resp_obj


@api.route('/logout')
class AuthLogout(Resource):

    @jwt_required()
    def post(self):
        from flask_jwt_extended import get_jwt, decode_token, get_jwt_identity
        from app.models.token_blocklist import TokenBlocklist
        from datetime import datetime

        claims = get_jwt()
        jti = claims.get('jti')
        exp_ts = claims.get('exp')
        user_id = get_jwt_identity()

        if jti and exp_ts:
            expires_at = datetime.utcfromtimestamp(exp_ts)
            TokenBlocklist.revoke(jti, expires_at=expires_at, token_type='access', user_id=user_id)

        # Révoque le refresh token s'il est fourni dans le body (Electron)
        # ou s'il est présent en cookie (web — lu depuis le cookie via decode_token).
        # Meilleur effort : absent/invalide/expiré = ignoré silencieusement.
        try:
            data = request.get_json(silent=True) or {}
            raw_refresh = data.get('refresh_token')

            # Si pas de refresh dans le body, tenter de le lire depuis le cookie
            if not raw_refresh:
                from flask import make_response
                raw_refresh = request.cookies.get('refresh_token_cookie')

            if raw_refresh and isinstance(raw_refresh, str):
                decoded = decode_token(raw_refresh)
                if decoded.get('type') == 'refresh' and str(decoded.get('sub')) == str(user_id):
                    r_jti = decoded.get('jti')
                    r_exp = decoded.get('exp')
                    if r_jti and r_exp:
                        TokenBlocklist.revoke(
                            r_jti,
                            expires_at=datetime.utcfromtimestamp(r_exp),
                            token_type='refresh',
                            user_id=user_id,
                        )
        except Exception:
            current_app.logger.debug(
                'Logout : refresh_token non révoqué (absent/invalide/expiré)',
                exc_info=True,
            )

        db.session.commit()

        # A1 FIX : effacer les cookies JWT HttpOnly
        import json as _json
        resp_obj = current_app.response_class(
            response=_json.dumps({'message': 'Deconnexion reussie'}),
            status=200,
            mimetype='application/json',
        )
        unset_jwt_cookies(resp_obj)
        return resp_obj


@api.route('/forgot-password')
class AuthForgotPassword(Resource):

    @rate_limit(30, 300)
    def post(self):
        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            return {'message': 'Email requis'}, 400

        # M6 : en production, exiger un SMTP réellement configuré. Sans lui,
        # un token de reset serait créé mais jamais délivré. On coupe net avec
        # un 501 explicite pour tout le monde (même message, pas d'énumération).
        if os.getenv('FLASK_ENV', '').lower() == 'production':
            from app.config.settings import Config
            mail_ready = bool(getattr(Config, 'MAIL_ENABLED', False)) and bool(getattr(Config, 'MAIL_HOST', None))
            if not mail_ready:
                return {
                    'message': 'La réinitialisation par email n\'est pas disponible. Contactez un administrateur.'
                }, 501

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

    @rate_limit(60, 300)
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

    @rate_limit(60, 300)
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
        sensitive_fields = {'email'}
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
        },
