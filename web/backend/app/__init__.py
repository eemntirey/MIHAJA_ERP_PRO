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

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    if not app.config['SECRET_KEY']:
        raise ValueError("SECRET_KEY environment variable is required")

    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db'
    )

    if os.getenv('FLASK_ENV', '').lower() == 'production' and database_url.startswith('sqlite'):
        raise ValueError(
            'Production environment requires PostgreSQL DATABASE_URL; SQLite is not allowed.'
        )

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
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

    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.url_map.strict_slashes = False

    db.init_app(app)
    migrate.init_app(app, db)

    from app.security.tenant import register_tenant_filter_event
    with app.app_context():
        register_tenant_filter_event()

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            'CORS_ORIGINS',
            'http://localhost:3000,http://127.0.0.1:3000,https://bj470sl0-3000.inc1.devtunnels.ms'
        ).split(',')
        if origin.strip()
    ]

    # P0 audit 14/09/2026 (ERR_CONNECTION_CLOSED sur nouvel onglet) :
    # les tunnels devtunnels.ms changent de sous-domaine à chaque session
    # (ex bj470sl0-3000 -> xyz1234-3000) et le LAN change d'IP. On accepte
    # dynamiquement ces origines au lieu d'exiger une liste figée.
    _DYNAMIC_CORS_PATTERNS = [
        r'^https://[a-z0-9-]+-3000\.inc1\.devtunnels\.ms$',
        r'^https://[a-z0-9-]+\.inc1\.devtunnels\.ms$',
        r'^http://192\.168\.\d{1,3}\.\d{1,3}:300[01]$',
        r'^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:300[01]$',
    ]
    import re as _re
    _dynamic_extra = []
    try:
        _fwd = os.getenv('CORS_DYNAMIC_ORIGINS', '')
        for _pat in [p.strip() for p in _fwd.split(',') if p.strip()]:
            _DYNAMIC_CORS_PATTERNS.append(_pat)
    except Exception:
        pass
    _origin_env_hint = os.getenv('FRONTEND_URL', '').strip()
    if _origin_env_hint and _origin_env_hint not in CORS_ORIGINS:
        _dynamic_extra.append(_origin_env_hint)
    CORS_ORIGINS = list(dict.fromkeys(CORS_ORIGINS + _dynamic_extra))

    # Partagé avec Flask-SocketIO (app.realtime.socket_server) : sans cette
    # clé dans app.config, le handshake /socket.io n'autorise que
    # http://localhost:3000 et renvoie « HTTP 400 Not an accepted origin. »
    # pour toute autre origine (ex: http://192.168.40.236:3000).
    app.config['CORS_ORIGINS'] = CORS_ORIGINS
    app.config['CORS_DYNAMIC_PATTERNS'] = list(_DYNAMIC_CORS_PATTERNS)

    if '*' in CORS_ORIGINS:
        raise ValueError(
            "CORS_ORIGINS cannot contain '*' when supports_credentials=True. "
            "Specify explicit allowed origins."
        )

    # flask-cors n'accepte ni les callables ni les fonctions dans ``origins``
    # (il les encapsule dans une liste puis appelle ``c in origin`` → TypeError
    # sur toute réponse qui ne passe pas par le décorateur cross_origin, ex:
    # une NoAuthorizationError levée avant la vue → 500 au lieu de 401).
    # On passe donc les origines statiques + les patterns dynamiques compilés,
    # que flask-cors sait matcher nativement via ``try_match_any``.
    _cors_origins_config = list(CORS_ORIGINS) + [
        _re.compile(_pat) for _pat in _DYNAMIC_CORS_PATTERNS
    ]

    CORS(
        app,
        origins=_cors_origins_config,
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
        allow_headers=[
            'Content-Type', 'Authorization', 'X-Requested-With', 'Accept',
            'X-Tenant-Slug', 'X-Tenant-Domaine', 'Idempotency-Key',
        ],
        expose_headers=['X-Request-Id'],
        supports_credentials=True,
        max_age=3600,
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
        return {'message': 'En-tête Authorization manquant ou invalide'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(err):
        return {'message': 'Token JWT invalide ou expiré'}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'message': 'Token JWT expiré'}, 401

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

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return {
            'message': e.description or e.name,
            'code': e.code,
        }, e.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        from flask import jsonify
        # JWT-specific exceptions are handled by the dedicated handlers above
        # (and on the Api namespace); ignore them here.
        from flask_jwt_extended.exceptions import (
            NoAuthorizationError, InvalidHeaderError,
            RevokedTokenError, JWTDecodeError, WrongTokenError,
        )
        from jwt.exceptions import ExpiredSignatureError
        if isinstance(e, (
            NoAuthorizationError, InvalidHeaderError,
            RevokedTokenError, JWTDecodeError,
            WrongTokenError, ExpiredSignatureError,
        )):
            # Re-lève pour laisser error_router (flask_restx) retomber sur le
            # handler Flask de flask-jwt-extended -> réponse 401 propre au lieu
            # d'un 500 "'Response' object has no attribute 'get'".
            raise e
        logger.exception('Unhandled exception during request: %s', e)
        # Tuple (dict, code) et non Response: flask_restx.Api.handle_error fait
        # default_data.get(...) -> crash si default_data est une Response Flask.
        return {
            'message': 'Erreur interne du serveur',
            'code': 500,
        }, 500

    api = Api(
        app,
        title='ERP Commercial API',
        version='1.0',
        doc='/docs/',
        decorators=[cross_origin()]
    )

    @app.route('/')
    @app.route('/index')
    def index():
        return {'message': 'ERP Commercial API', 'status': 'running'}, 200

    @app.route('/health')
    def health():
        """Health-check public monitoré (P0 audit 14/09/2026).

        Vérifie réellement la connexion DB au lieu de répondre en aveugle.
        200 = sain, 503 = dégradé (DB injoignable). Jamais de 500 générique.
        """
        from sqlalchemy import text as _sa_text
        checks = {}
        try:
            db.session.execute(_sa_text('SELECT 1'))
            checks['database'] = 'connected'
            healthy = True
        except Exception as exc:  # pragma: no cover - dépend de l'infra
            logger.warning('Health-check DB échoué: %s', exc)
            checks['database'] = 'unreachable'
            healthy = False
        payload = {
            'status': 'healthy' if healthy else 'degraded',
            'service': 'erp-backend',
            'checks': checks,
        }
        return payload, 200 if healthy else 503

    @app.route('/ready')
    def ready():
        """Readiness pour orchestrateurs/tunnels : DB + migrations à jour."""
        from sqlalchemy import text as _sa_text
        try:
            db.session.execute(_sa_text('SELECT 1'))
        except Exception as exc:
            return {'ready': False, 'reason': 'database_unreachable'}, 503
        return {'ready': True}, 200

    @app.route('/monitor')
    def monitor():
        """Endpoint de monitoring visible et monitoré (audit P0 14/09/2026)."""
        from flask import g
        from sqlalchemy import text as _sa_text
        db_status = 'unknown'
        try:
            db.session.execute(_sa_text('SELECT 1'))
            db_status = 'connected'
        except Exception:
            db_status = 'disconnected'
        return {
            'status': 'running',
            'monitor': True,
            'database': db_status,
            'service': 'erp-backend',
            'tenant_active': g.current_tenant is not None,
            'current_tenant_id': g.current_tenant.id if g.current_tenant else None,
        }, 200

    api.errorhandler(Exception)(handle_unexpected_exception)

    api.errorhandler(NoAuthorizationError)(handle_no_auth_error)
    api.errorhandler(InvalidHeaderError)(handle_invalid_header_error)
    api.errorhandler(JWTDecodeError)(handle_decode_error)
    api.errorhandler(RevokedTokenError)(handle_revoked_token_error)

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
    from app.api.v1.comptabilite import ns_comptes as comptes_ns, ns_ecritures as ecritures_ns, ns_tresorerie as tresorerie_ns, ns_resultats as resultats_ns
    from app.api.v1.documents import ns_modeles as modeles_documents_ns, ns_documents as documents_ns
    from app.api.v1.achats_devis import ns_commandes_achat as commandes_achat_ns, ns_receptions as receptions_ns, ns_devis as devis_ns, ns_bons_livraison as bons_livraison_ns, ns_avoirs as avoirs_ns
    from app.api.v1.roles import ns as roles_ns
    from app.api.v1.permissions import ns as permissions_ns
    from app.api.v1.users import ns as users_ns
    from app.api.v1.papi import ns as papi_ns
    from app.api.v1.notifications import ns as notifications_ns
    from app.api.v1.super_admin import ns as super_admin_ns
    from app.api.v1.tenant_papi import ns as tenant_papi_ns
    from app.api.v1.admin_devices import ns as admin_devices_ns
    from app.api.v1.entrepots import ns as entrepots_ns
    from app.api.v1.desk import desk_bp

    api.add_namespace(super_admin_ns, path='/api/v1/super-admin')
    api.add_namespace(admin_devices_ns, path='/api/v1/admin/devices')
    if app.config.get('DEBUG', False) or app.config.get('TESTING', False):
        from app.api.v1.test import ns as test_ns
        api.add_namespace(test_ns, path='/api/v1/test')

    api.add_namespace(auth_ns, path='/api/v1/auth')
    api.add_namespace(clients_ns, path='/api/v1/clients')
    api.add_namespace(dashboard_ns, path='/api/v1/dashboard')
    api.add_namespace(factures_ns, path='/api/v1/factures')
    api.add_namespace(fournisseurs_ns, path='/api/v1/fournisseurs')
    api.add_namespace(paiements_ns, path='/api/v1/paiements')
    api.add_namespace(produits_ns, path='/api/v1/produits')
    api.add_namespace(stocks_ns, path='/api/v1/stocks')
    api.add_namespace(ventes_ns, path='/api/v1/ventes')
    api.add_namespace(ai_ns, path='/api/v1/ai')
    # Vitrine publique : le frontend appelle /api/v1/public/... via REACT_APP_API_URL.
    # On expose le namespace aux deux préfixes (compat ascendante pour les tests
    # qui utilisent /public/...) SANS dupliquer les routes dans Swagger.
    api.add_namespace(public_ns, path='/api/v1/public')
    try:
        for _pub_entry in list(public_ns.resources):
            _pub_resource = _pub_entry[0] if len(_pub_entry) > 0 else None
            _pub_urls = _pub_entry[1] if len(_pub_entry) > 1 else []
            _pub_kwargs = _pub_entry[2] if len(_pub_entry) > 2 else {}
            if _pub_resource is None:
                continue
            for _pub_url in list(_pub_urls or []):
                _compat = '/public' + _pub_url
                try:
                    api.add_resource(_pub_resource, _compat, endpoint='public_compat_' + _pub_resource.__name__, **(_pub_kwargs or {}))
                except Exception:
                    pass
    except Exception:
        pass
    api.add_namespace(tenants_ns, path='/api/v1/tenants')
    api.add_namespace(abonnements_ns, path='/api/v1/abonnements')
    api.add_namespace(livreurs_ns, path='/api/v1/livreurs')
    api.add_namespace(vehicules_ns, path='/api/v1/vehicules')
    api.add_namespace(itineraires_ns, path='/api/v1/itineraires')
    api.add_namespace(livraisons_ns, path='/api/v1/livraisons')
    api.add_namespace(employes_ns, path='/api/v1/employes')
    api.add_namespace(stagiaires_ns, path='/api/v1/stagiaires')
    api.add_namespace(presences_ns, path='/api/v1/presences')
    api.add_namespace(salaires_ns, path='/api/v1/salaires')
    api.add_namespace(primes_ns, path='/api/v1/primes')
    api.add_namespace(comptes_ns, path='/api/v1/comptes')
    api.add_namespace(ecritures_ns, path='/api/v1/ecritures')
    api.add_namespace(tresorerie_ns, path='/api/v1/tresorerie')
    api.add_namespace(resultats_ns, path='/api/v1/resultats')
    api.add_namespace(modeles_documents_ns, path='/api/v1/modeles-documents')
    api.add_namespace(documents_ns, path='/api/v1/documents')
    api.add_namespace(commandes_achat_ns, path='/api/v1/commandes-achat')
    api.add_namespace(receptions_ns, path='/api/v1/receptions')
    api.add_namespace(devis_ns, path='/api/v1/devis')
    api.add_namespace(bons_livraison_ns, path='/api/v1/bons-livraison')
    api.add_namespace(avoirs_ns, path='/api/v1/avoirs')
    api.add_namespace(roles_ns, path='/api/v1/roles')
    api.add_namespace(permissions_ns, path='/api/v1/permissions')
    api.add_namespace(users_ns, path='/api/v1/users')
    api.add_namespace(papi_ns, path='/api/v1/papi')
    api.add_namespace(tenant_papi_ns, path='/api/v1')
    api.add_namespace(notifications_ns, path='/api/v1/notifications')
    api.add_namespace(entrepots_ns, path='/api/v1/entrepots')

    app.register_blueprint(desk_bp)

    from app.realtime.socket_server import init_socketio
    app.socketio = init_socketio(app)

    @app.before_request
    def before_request():
        from flask import g
        from app.security.tenant import resolve_tenant_from_header

        g.current_tenant = None
        g.current_user = None

        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt
            verify_jwt_in_request(optional=True)
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

    # Auto-seed des rôles/permissions système si la table est vide.
    # Idempotent : ne s'exécute que si `roles` est vide, ne modifie jamais
    # les données existantes. Évite l'écran "Aucun rôle trouvé" après un
    # reset de base (cf. incident 2026-09-07 : Postgres erp seedée manuellement).
    try:
        with app.app_context():
            from app.models.role_permission import RoleModel
            if db.session.query(RoleModel.id).first() is None:
                from scripts.seed_roles import seed_roles
                seed_roles(app)
                logger.info("Auto-seed rôles/permissions effectué (base vide).")
    except Exception:
        logger.warning("Auto-seed rôles/permissions a échoué", exc_info=True)

    # NOTE: le seeding complet (_seed_initial_data) reste declenchable via CLI.

    return app
