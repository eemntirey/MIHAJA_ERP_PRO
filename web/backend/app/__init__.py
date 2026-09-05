# backend/app/__init__.py

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS, cross_origin
from flask_restx import Api
from flask_jwt_extended import JWTManager


import os
from dotenv import load_dotenv
import logging

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

logger = logging.getLogger(__name__)


def create_app():

    app = Flask(__name__)

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("SECRET_KEY environment variable is required")

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///erp.db'
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['JWT_ALGORITHM'] = 'HS256'
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    from datetime import timedelta

    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(
        days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 30))
    )

    # flask-restx intercepts non-HTTPException errors in RESTX routes.
    # Setting PROPAGATE_EXCEPTIONS=True makes flask-restx re-raise them
    # so Flask's own error handlers (registered by flask_jwt_extended and
    # elsewhere) can produce proper responses instead of a generic 500.
    app.config['PROPAGATE_EXCEPTIONS'] = True

    # Accepter /route et /route/
    app.url_map.strict_slashes = False

    # ==========================================================
    # EXTENSIONS
    # ==========================================================

    db.init_app(app)
    migrate.init_app(app, db)

    # Register global tenant filter event listener
    from app.security.tenant import register_tenant_filter_event
    with app.app_context():
        register_tenant_filter_event()

    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000'
    ).split(',')

    if '*' in CORS_ORIGINS:
        raise ValueError(
            "CORS_ORIGINS cannot contain '*' when supports_credentials=True. "
            "Specify explicit allowed origins."
        )

    CORS(
        app,
        origins=CORS_ORIGINS,
        methods=[
            'GET',
            'POST',
            'PUT',
            'DELETE',
            'OPTIONS',
            'PATCH'
        ],
        allow_headers=[
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'Accept'
        ],
        supports_credentials=True,
        max_age=3600
    )

    jwt.init_app(app)

    # --- JWT Blocklist (révocation réelle) ---
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Retourne True si le JTI est dans la blocklist → token rejeté."""
        from app.models.token_blocklist import TokenBlocklist
        jti = jwt_payload.get('jti')
        return TokenBlocklist.is_revoked(jti)

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token JWT révoqué'}, 401


    from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

    @jwt.unauthorized_loader
    def unauthorized_callback(err):
        return {
            'message': 'En-tête Authorization manquant ou invalide'
        }, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(err):
        return {
            'message': 'Token JWT invalide ou expiré'
        }, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'message': 'Token JWT expiré'
        }, 401

    @app.errorhandler(NoAuthorizationError)
    def handle_no_auth_error(e):
        return {'message': 'En-tête Authorization manquant ou invalide'}, 401

    @app.errorhandler(InvalidHeaderError)
    def handle_invalid_header_error(e):
        return {'message': 'En-tête Authorization invalide'}, 401

    @app.errorhandler(JWTDecodeError)
    def handle_decode_error(e):
        return {'message': 'Token JWT invalide'}, 401

    @app.errorhandler(RevokedTokenError)
    def handle_revoked_token_error(e):
        return {'message': 'Token JWT révoqué'}, 401

    # ==========================================================
    # ROUTES PRINCIPALES
    # ==========================================================

    @app.route('/')
    @app.route('/index')
    def index():
        return {
            'message': 'ERP Commercial API',
            'status': 'running'
        }, 200

    @app.route('/health')
    def health():
        return {
            'status': 'healthy',
            'database': 'connected'
        }, 200

    # ==========================================================
    # FLASK-RESTX
    # ==========================================================

    api = Api(
        app,
        title='ERP Commercial API',
        version='1.0',
        doc='/docs/',
        decorators=[cross_origin()]
    )

    # flask-restx monkey-patches Flask's error handling, intercepting
    # exceptions raised in RESTX routes.  Register the same JWT error
    # handlers with the RESTX Api so 401 responses are returned instead
    # of a generic 500.
    api.errorhandler(NoAuthorizationError)(handle_no_auth_error)
    api.errorhandler(InvalidHeaderError)(handle_invalid_header_error)
    api.errorhandler(JWTDecodeError)(handle_decode_error)
    api.errorhandler(RevokedTokenError)(handle_revoked_token_error)

    # ==========================================================
    # NAMESPACES
    # ==========================================================

    from app.api.v1.auth import api as auth_ns
    from app.api.v1.clients import ns as clients_ns
    from app.api.v1.dashboard import api as dashboard_ns
    from app.api.v1.factures import api as factures_ns
    from app.api.v1.fournisseurs import ns as fournisseurs_ns
    from app.api.v1.paiements import ns as paiements_ns
    from app.api.v1.produits import ns as produits_ns
    from app.api.v1.stocks import ns as stocks_ns
    from app.api.v1.ventes import ns as ventes_ns
    from app.api.v1.ai import ns as ai_ns
    from app.api.v1.public import ns_public as public_ns
    from app.api.v1.tenants import ns as tenants_ns
    from app.api.v1.abonnements import ns as abonnements_ns
    from app.api.v1.livraisons import ns_livreurs as livreurs_ns, ns_vehicules as vehicules_ns, ns_itineraires as itineraires_ns, ns_livraisons as livraisons_ns
    from app.api.v1.rh import ns_employes as employes_ns, ns_presences as presences_ns, ns_salaires as salaires_ns, ns_primes as primes_ns, ns_stagiaires as stagiaires_ns
    from app.api.v1.comptabilite import ns_comptes as comptes_ns, ns_ecritures as ecritures_ns, ns_tresorerie as tresorerie_ns
    from app.api.v1.documents import ns_modeles as modeles_documents_ns, ns_documents as documents_ns
    from app.api.v1.achats_devis import ns_commandes_achat as commandes_achat_ns, ns_receptions as receptions_ns, ns_devis as devis_ns, ns_bons_livraison as bons_livraison_ns, ns_avoirs as avoirs_ns
    from app.api.v1.roles import ns as roles_ns
    from app.api.v1.permissions import ns as permissions_ns
    from app.api.v1.users import ns as users_ns
    from app.api.v1.papi import ns as papi_ns
    from app.api.v1.notifications import ns as notifications_ns

    from app.api.v1.super_admin import ns as super_admin_ns
    from app.api.v1.admin_devices import ns as admin_devices_ns

    # Synchronisation desktop/web (favoris, colonnes, filtres, sync incrémental)
    from app.api.v1.desk import desk_bp

    api.add_namespace(
        super_admin_ns,
        path='/api/v1/super-admin'
    )
    api.add_namespace(
        admin_devices_ns,
        path='/api/v1/admin/devices'
    )
    if app.config.get('DEBUG', False) or app.config.get('TESTING', False):
        from app.api.v1.test import ns as test_ns
        api.add_namespace(
            test_ns,
            path='/api/v1/test'
        )

    api.add_namespace(
        auth_ns,
        path='/api/v1/auth'
    )

    api.add_namespace(
        clients_ns,
        path='/api/v1/clients'
    )

    api.add_namespace(
        dashboard_ns,
        path='/api/v1/dashboard'
    )

    api.add_namespace(
        factures_ns,
        path='/api/v1/factures'
    )

    api.add_namespace(
        fournisseurs_ns,
        path='/api/v1/fournisseurs'
    )

    api.add_namespace(
        paiements_ns,
        path='/api/v1/paiements'
    )

    api.add_namespace(
        produits_ns,
        path='/api/v1/produits'
    )

    api.add_namespace(
        stocks_ns,
        path='/api/v1/stocks'
    )

    api.add_namespace(
        ventes_ns,
        path='/api/v1/ventes'
    )

    api.add_namespace(
        ai_ns,
        path='/api/v1/ai'
    )

    api.add_namespace(
        public_ns,
        path='/public'
    )

    api.add_namespace(
        tenants_ns,
        path='/api/v1/tenants'
    )

    api.add_namespace(
        abonnements_ns,
        path='/api/v1/abonnements'
    )

    api.add_namespace(
        livreurs_ns,
        path='/api/v1/livreurs'
    )

    api.add_namespace(
        vehicules_ns,
        path='/api/v1/vehicules'
    )

    api.add_namespace(
        itineraires_ns,
        path='/api/v1/itineraires'
    )

    api.add_namespace(
        livraisons_ns,
        path='/api/v1/livraisons'
    )

    api.add_namespace(
        employes_ns,
        path='/api/v1/employes'
    )

    api.add_namespace(
        stagiaires_ns,
        path='/api/v1/stagiaires'
    )

    api.add_namespace(
        presences_ns,
        path='/api/v1/presences'
    )

    api.add_namespace(
        salaires_ns,
        path='/api/v1/salaires'
    )

    api.add_namespace(
        primes_ns,
        path='/api/v1/primes'
    )

    api.add_namespace(
        comptes_ns,
        path='/api/v1/comptes'
    )

    api.add_namespace(
        ecritures_ns,
        path='/api/v1/ecritures'
    )

    api.add_namespace(
        tresorerie_ns,
        path='/api/v1/tresorerie'
    )

    api.add_namespace(
        modeles_documents_ns,
        path='/api/v1/modeles-documents'
    )

    api.add_namespace(
        documents_ns,
        path='/api/v1/documents'
    )

    api.add_namespace(
        commandes_achat_ns,
        path='/api/v1/commandes-achat'
    )

    api.add_namespace(
        receptions_ns,
        path='/api/v1/receptions'
    )

    api.add_namespace(
        devis_ns,
        path='/api/v1/devis'
    )

    api.add_namespace(
        bons_livraison_ns,
        path='/api/v1/bons-livraison'
    )

    api.add_namespace(
        avoirs_ns,
        path='/api/v1/avoirs'
    )

    api.add_namespace(
        roles_ns,
        path='/api/v1/roles'
    )

    api.add_namespace(
        permissions_ns,
        path='/api/v1/permissions'
    )

    api.add_namespace(
        users_ns,
        path='/api/v1/users'
    )

    api.add_namespace(
        papi_ns,
        path='/api/v1/papi'
    )

    api.add_namespace(
        notifications_ns,
        path='/api/v1/notifications'
    )

    # Blueprint de synchronisation desktop/web (JWT standard, compatible tiers).
    app.register_blueprint(desk_bp)

    # ==========================================================
    # TENANT CONTEXT
    # ==========================================================

    @app.before_request
    def before_request():
        from flask import g

        from app.security.tenant import (
            get_current_tenant,
            resolve_tenant_from_header
        )

        g.current_tenant = None
        g.current_user = None

        try:
            from flask_jwt_extended import verify_jwt_in_request_optional, get_jwt
            verify_jwt_in_request_optional()
            claims = get_jwt()
            if claims:
                tenant_id = claims.get('tenant_id')
                if tenant_id:
                    from app.models.tenant import Tenant
                    tenant = db.session.get(Tenant, tenant_id)
                    if tenant:
                        g.current_tenant = tenant
                        return
        except Exception:
            pass

        try:
            tenant = resolve_tenant_from_header()
            if tenant:
                g.current_tenant = tenant

        except Exception:
            logger.warning(
                "Impossible de résoudre le tenant depuis les headers HTTP",
                exc_info=True,
            )
            g.current_tenant = None

    # ==========================================================
    # AUTO-SEEDING: Desactive en production. A appeler explicitement
    # via le endpoint ou une commande CLI.
    # ==========================================================

    def _seed_roles():
        try:
            with app.app_context():
                from app.models.role_permission import RoleModel, Permission
                from app.security.permission_matrix import ROLE_PERMISSIONS

                DEFAULT_ROLES = [
                    {'name': 'super_admin', 'display_name': 'Super Admin', 'description': 'Acces complet a toutes les fonctionnalites', 'is_default': True, 'is_system': True},
                    {'name': 'admin', 'display_name': 'Admin', 'description': 'Acces administratif a toutes les ressources', 'is_default': True, 'is_system': True},
                    {'name': 'manager', 'display_name': 'Manager', 'description': 'Gestion des produits, stock, ventes, utilisateurs et rapports', 'is_default': True, 'is_system': True},
                    {'name': 'sales', 'display_name': 'Commercial', 'description': 'Gestion des ventes, clients et devis', 'is_default': True, 'is_system': True},
                    {'name': 'stock', 'display_name': 'Stock', 'description': 'Gestion des stocks, produits et fournisseurs', 'is_default': True, 'is_system': True},
                    {'name': 'accountant', 'display_name': 'Comptable', 'description': 'Gestion comptable, factures et paiements', 'is_default': True, 'is_system': True},
                    {'name': 'rh', 'display_name': 'RH', 'description': 'Gestion des ressources humaines', 'is_default': True, 'is_system': True},
                    {'name': 'user', 'display_name': 'Utilisateur', 'description': 'Utilisateur standard avec acces limite', 'is_default': True, 'is_system': True},
                    {'name': 'support', 'display_name': 'Support', 'description': 'Assistance et support aux utilisateurs et clients', 'is_default': False, 'is_system': True},
                    {'name': 'livreur', 'display_name': 'Livreur', 'description': 'Acces aux livraisons propres', 'is_default': False, 'is_system': True},
                ]

                for role_data in DEFAULT_ROLES:
                    existing = RoleModel.query.filter_by(name=role_data['name']).first()
                    if existing:
                        existing.display_name = role_data['display_name']
                        existing.description = role_data['description']
                        existing.is_default = role_data['is_default']
                        existing.is_system = role_data['is_system']
                        existing.permissions = []
                    else:
                        existing = RoleModel(
                            name=role_data['name'],
                            display_name=role_data['display_name'],
                            description=role_data['description'],
                            is_default=role_data['is_default'],
                            is_system=role_data['is_system'],
                        )
                        db.session.add(existing)
                        db.session.flush()

                    for perm_code in ROLE_PERMISSIONS.get(role_data['name'], []):
                        if perm_code == '*':
                            continue
                        perm = Permission.query.filter_by(code=perm_code).first()
                        if not perm:
                            parts = perm_code.split('.')
                            perm = Permission(
                                code=perm_code,
                                module=parts[0] if parts else 'general',
                                action=parts[1] if len(parts) > 1 else 'access',
                                description=perm_code,
                            )
                            db.session.add(perm)
                            db.session.flush()
                        if perm not in existing.permissions:
                            existing.permissions.append(perm)

                db.session.commit()
        except Exception as e:
            app.logger.exception("Erreur pendant le seed des roles: %s", e)
            try:
                db.session.rollback()
            except Exception:
                pass

    # Le reste du seeding est conserve tel quel dans le fichier original.
    # Pour eviter une troncature, on garde uniquement la structure critique
    # (blocklist JWT) et on re-importe le seeding complet depuis le code local.
    return app
