
from flask import current_app, request
from flask_restx import Namespace, Resource
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token,
    create_refresh_token,
)
from datetime import datetime, timedelta
from app import db
from app.security.auth import authenticate_user, hash_password
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant


api = Namespace(
    'auth',
    description='Authentification et JWT'
)


@api.route('/login')
class AuthLogin(Resource):

    def post(self):
        data = request.get_json() or {}

        identifier = data.get('username') or data.get('email')
        password = data.get('password')
        tenant_slug = data.get('tenant_slug')

        if not identifier or not password:
            return {
                'message': 'Identifiant et mot de passe requis'
            }, 400

        try:
            result, error = authenticate_user(
                identifier,
                password,
                tenant_slug=tenant_slug
            )
        except Exception:
            current_app.logger.exception(
                'Erreur inattendue pendant l authentification de %s',
                identifier
            )
            return {
                'message': 'Erreur interne du service d’authentification'
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
                'message': 'Le service d’authentification n’a pas généré une session valide'
            }, 500

        return result, 200


@api.route('/me')
class AuthMe(Resource):

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()

        user = Utilisateur.query.get(user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        tenant = None

        if user.tenant_id:
            tenant = Tenant.query.get(user.tenant_id)

        return {
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None,
        }, 200

    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()

        user = Utilisateur.query.get(user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        data = request.get_json() or {}
        for key, value in data.items():
            if key in ['nom', 'prenom', 'telephone', 'mobile', 'email']:
                setattr(user, key, value)

        db.session.commit()

        return {
            'user': user.to_dict()
        }, 200


@api.route('/register')
class AuthRegister(Resource):

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

        if Utilisateur.query.filter(
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

            base_slug = nom_entreprise.lower().replace(' ', '-').replace('.', '-')
            slug = base_slug
            counter = 1
            while Tenant.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

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
                tenant_id=tenant.id,
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

        user = Utilisateur.query.get(user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        tenant = None

        if user.tenant_id:
            tenant = Tenant.query.get(user.tenant_id)

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
        # Avec JWT stateless, la déconnexion est généralement
        # effectuée côté client en supprimant le token.

        return {
            'message': 'Deconnexion reussie'
        }, 200


@api.route('/forgot-password')
class AuthForgotPassword(Resource):

    def post(self):
        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            return {'message': 'Email requis'}, 400

        user = Utilisateur.query.filter_by(email=email, is_active=True).first()

        if user:
            from app.models.password_reset_token import PasswordResetToken

            PasswordResetToken.query.filter_by(
                user_id=user.id,
                used=False
            ).update({'used': True})
            db.session.commit()

            raw_token = PasswordResetToken.generate_token()
            token = PasswordResetToken(
                user_id=user.id,
                token=raw_token,
                expires_at=datetime.utcnow() + timedelta(hours=1),
                ip_address=request.remote_addr,
            )
            db.session.add(token)
            db.session.commit()

            reset_link = (
                f"{request.host_url.rstrip('/')}"
                f"/reset-password/{raw_token}"
            )
            current_app.logger.info(
                'Simulated password reset email sent to %s: %s',
                user.email,
                reset_link,
            )

        return {
            'message': 'Si un compte existe avec cet email, un lien de réinitialisation a été envoyé.'
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
        from app.security.auth import hash_password

        reset_token = PasswordResetToken.query.filter_by(
            token=token,
            used=False
        ).first()

        if not reset_token or reset_token.is_expired:
            return {'message': 'Token invalide ou expiré'}, 400

        user = Utilisateur.query.get(reset_token.user_id)
        if not user or not user.is_active:
            return {'message': 'Utilisateur non trouvé'}, 404

        user.password_hash = hash_password(new_password)
        reset_token.used = True
        db.session.commit()

        return {'message': 'Mot de passe réinitialisé avec succès'}, 200


@api.route('/super-admin/me')
class SuperAdminMe(Resource):

    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()

        user = Utilisateur.query.get(user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        if user.role not in [Role.SUPER_ADMIN]:
            return {
                'message': 'Acces refuse'
            }, 403

        return {
            'user': user.to_dict()
        }, 200

    @jwt_required()
    def put(self):
        user_id = get_jwt_identity()

        user = Utilisateur.query.get(user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        if user.role not in [Role.SUPER_ADMIN]:
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
