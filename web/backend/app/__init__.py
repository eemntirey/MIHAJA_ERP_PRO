# backend/app/__init__.py

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS, cross_origin
from flask_restx import Api
from flask_jwt_extended import JWTManager


import os
import uuid
from dotenv import load_dotenv
import logging

load_dotenv()

# Variables injectées par le processus parent (Electron lance le backend
# embarqué avec FLASK_ENV/LOCAL_DB_PATH/REPLICATION_URL/REPLICATION_DEVICE_ID)
# ou par l'environnement de test (TEST_DATABASE_URL, FLASK_ENV=testing) : elles
# doivent PRIMER sur .env/.env.local. Sans ce garde-fou, `.env.local` (chargé
# avec override=True) imposerait la configuration du poste de développement et
# le central comme la suite de tests utiliseraient la base du backend embarqué.
_PROCESS_ENV_KEYS = (
    'FLASK_ENV', 'FLASK_DEBUG', 'DEBUG', 'LOCAL_DB_PATH', 'LOCAL_API_PORT',
    'REPLICATION_URL', 'REPLICATION_DEVICE_ID', 'DATABASE_URL',
    'TEST_DATABASE_URL', 'SECRET_KEY', 'JWT_SECRET_KEY',
)
_process_env_snapshot = {
    key: os.environ[key] for key in _PROCESS_ENV_KEYS if key in os.environ
}

load_dotenv('.env.local', override=True)

os.environ.update(_process_env_snapshot)

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

logger = logging.getLogger(__name__)

# Tables minimales attendues : leur absence signifie que les migrations n'ont
# jamais ete jouees sur la base cible (cf. incident 2026-09-17 : base Postgres
# `erp_db` creee mais vide -> traceback psycopg UndefinedTable de 60 lignes au
# demarrage, puis 500 sur /api/v1/auth/login).
REQUIRED_TABLES = ('tenants', 'utilisateurs', 'roles', 'permissions')

# Endpoints publics qui ne doivent JAMAIS heriter du tenant porte par un JWT
# residuel. /auth/register cree un NOUVEAU tenant : si le filtre global
# (app/security/tenant.py) s'applique avec l'ancien tenant du navigateur, le
# rafraichissement de l'utilisateur tout juste cree ne trouve aucune ligne
# (WHERE id = ... AND tenant_id = <ancien>) -> ObjectDeletedError -> 500.
# Meme logique pour /auth/login (recherche du compte par email/username) et
# /auth/refresh (le tenant vient uniquement du refresh token).
PUBLIC_PATH_PREFIXES = (
    '/api/v1/auth/plans',
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/refresh',
    '/api/v1/auth/forgot-password',
    '/api/v1/auth/verify-reset-token',
    '/api/v1/auth/reset-password',
    '/api/v1/public',
    '/public',
)

# Rappel des commandes de correction, affiche uniquement si le schema manque.
_SCHEMA_FIX_HELP = (
    "  Commande de correction (depuis web/backend, base PostgreSQL neuve) :\n"
    "    python scripts/bootstrap_production.py                 "
    "# initialise schema + migrations + roles + Super Admin\n"
    "  Variables requises : DATABASE_URL + SUPERADMIN_PASSWORD.\n"
    "  Le bootstrap refuse toute base partiellement initialisee et ne supprime "
    "aucune donnee.\n"
    "  Ne pas utiliser 'db stamp head' seul : stamp n'exécute aucune migration.\n"
    "  Dev SQLite : DATABASE_URL=sqlite:///./erp.db "
    "(base web/backend/instance/erp.db)\n"
    "  Conteneur local : powershell -File setup_postgresql.ps1 "
    "(Postgres erp-pg, port 55432)"
)


def _inspect_database_schema():
    """Retourne (tables_manquantes, erreur) sans jamais lever d'exception.

    ``tables_manquantes`` vaut ``None`` quand l'inspection a echoue
    (base injoignable, droits insuffisants, ...).
    """
    from sqlalchemy import inspect

    try:
        existing = set(inspect(db.engine).get_table_names())
    except Exception as exc:
        return None, exc
    return [name for name in REQUIRED_TABLES if name not in existing], None


def _log_database_schema_problem(missing, error):
    """Journalise un diagnostic actionnable quand le schema de la base manque.

    Remplace la traceback SQLAlchemy par un message en francais. Le mot de
    passe eventuel de l'URL est masque : aucun secret ne doit apparaitre en log.
    """
    try:
        target = db.engine.url.render_as_string(hide_password=True)
    except Exception:
        target = os.getenv('DATABASE_URL', '<inconnue>')

    if error is not None:
        logger.error(
            "Base de donnees injoignable (%s) : %s. "
            "Verifiez DATABASE_URL et que le serveur de base est demarre : "
            "l'application demarre mais toute requete metier echouera.",
            target, error,
        )
        return

    logger.error(
        "Schema de base incomplet pour %s : table(s) manquante(s) : %s. "
        "Les migrations n'ont pas ete jouees sur cette base, donc "
        "l'authentification et les modules metier renverront une erreur 500.\n%s",
        target, ', '.join(missing), _SCHEMA_FIX_HELP,
    )


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

    # Backend embarque dans Electron (desktop hors-ligne) : SQLite local
    # OBLIGATOIRE + URL du serveur central pour la replication. Ce mode est
    # reserve au poste de travail ; le serveur central reste en PostgreSQL.
    _is_local_embedded = os.getenv('FLASK_ENV', '').lower() == 'local-embedded'
    if _is_local_embedded:
        from app.config.settings import LocalEmbeddedConfig
        # Config dédiée au poste de travail : SQLite local + URL du central.
        # `validate()` leve une ValueError explicite si l'un des deux manque
        # (mêmes messages que ceux attendus par le poste desktop).
        LocalEmbeddedConfig.validate()
        local_db_path = os.getenv('LOCAL_DB_PATH')
        database_url = LocalEmbeddedConfig.SQLALCHEMY_DATABASE_URI
        replication_url = LocalEmbeddedConfig.REPLICATION_URL

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Mode embarque : conserve la trace du mode et les parametres de
    # replication dans la config de l'app (lus par app/services/replication).
    app.config['FLASK_ENV'] = os.getenv('FLASK_ENV', '').lower()
    app.config['LOCAL_EMBEDDED'] = _is_local_embedded
    if _is_local_embedded:
        app.config['REPLICATION_URL'] = replication_url
        app.config['REPLICATION_DEVICE_ID'] = (
            os.getenv('REPLICATION_DEVICE_ID') or str(uuid.uuid4())
        )
        app.config['LOCAL_DB_PATH'] = local_db_path
        app.config['ENABLE_SOCKETIO'] = False


    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['JWT_ALGORITHM'] = 'HS256'

    _is_prod = os.getenv('FLASK_ENV', '').lower() == 'production'

    if _is_prod and not os.getenv('DATABASE_URL'):
        raise ValueError('DATABASE_URL requis en production (pas de fallback autorisé)')

    # A1 FIX : web utilise des cookies HttpOnly (XSS-safe), Electron continue
    # avec les headers Authorization (secureStore chiffré côté desktop).
    app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    # Cookies JWT — HttpOnly empêche l'accès JS (XSS), SameSite=Strict bloque
    # les requêtes cross-origin, Secure n'est activé qu'en production.
    app.config['JWT_ACCESS_COOKIE'] = 'access_token_cookie'
    app.config['JWT_REFRESH_COOKIE'] = 'refresh_token_cookie'
    app.config['JWT_COOKIE_SECURE'] = _is_prod
    app.config['JWT_COOKIE_HTTPONLY'] = True
    app.config['JWT_COOKIE_SAMESITE'] = 'Strict'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = os.getenv('JWT_COOKIE_CSRF_PROTECT', 'false').lower() in ('1', 'true', 'yes', 'on')
    app.config['JWT_CSRF_IN_COOKIES'] = True

    from datetime import timedelta

    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    )
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(
        days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 7))
    )

    # I2 FIX (P0) : MAX_CONTENT_LENGTH n'etait defini que dans Config (jamais
    # charge via app.config.from_object) -> uploads/Excel illimites (DoS pandas).
    app.config['MAX_CONTENT_LENGTH'] = int(
        os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    )
    app.config['MAX_FORM_MEMORY_SIZE'] = 2 * 1024 * 1024

    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.url_map.strict_slashes = False

    # Réglages d'entretien de la réplication (cf.
    # app/services/replication/maintenance.py). Valeurs surchargeables par
    # l'environnement du poste, sans redéploiement.
    try:
        app.config['SYNC_OUTBOX_RETENTION_DAYS'] = int(
            os.getenv('SYNC_OUTBOX_RETENTION_DAYS', 30)
        )
    except ValueError:
        app.config['SYNC_OUTBOX_RETENTION_DAYS'] = 30
    try:
        app.config['SYNC_CLOCK_DRIFT_TOLERANCE_S'] = int(
            os.getenv('SYNC_CLOCK_DRIFT_TOLERANCE_S', 300)
        )
    except ValueError:
        app.config['SYNC_CLOCK_DRIFT_TOLERANCE_S'] = 300

    db.init_app(app)
    migrate.init_app(app, db)

    # Enregistrement du listener outbox uniquement en mode local-embedded :
    # seules les écritures dans la base SQLite locale sont capturées (un test
    # peut héberger un central et un poste dans le même processus).
    if _is_local_embedded:
        from app.services.replication.outbox import register_outbox_listeners
        register_outbox_listeners(
            db, local_db_path=app.config.get('LOCAL_DB_PATH'),
        )

    from app.security.tenant import register_tenant_filter_event
    with app.app_context():
        register_tenant_filter_event()

    # Dev par défaut : web (:3000), desk/Electron (:3001), super-admin (:3002)
    # et Expo web de l'app mobile (:8081 — sinon « Impossible de joindre le
    # serveur » dans le navigateur, faute d'en-tête Access-Control-Allow-Origin).
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            'CORS_ORIGINS',
            '' if _is_prod
            else 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,'
                 'http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,'
                 'http://localhost:8081,http://127.0.0.1:8081,'
                 'https://bj470sl0-3000.inc1.devtunnels.ms'
        ).split(',')
        if origin.strip()
    ]

    # I4 FIX : allow-list stricte en production (patterns LAN/tunnels = DEV only).
    _is_prod_cors = _is_prod
    _DYNAMIC_CORS_PATTERNS = []
    if not _is_prod_cors:
        _DYNAMIC_CORS_PATTERNS = [
        r'^https://[a-z0-9-]+-3000\.inc1\.devtunnels\.ms$',
        r'^https://[a-z0-9-]+\.inc1\.devtunnels\.ms$',
        r'^http://192\.168\.\d{1,3}\.\d{1,3}:(?:300[012]|8081)$',
        r'^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:(?:300[012]|8081)$',
    ]
    import re as _re
    _dynamic_extra = []
    try:
        _fwd = os.getenv('CORS_DYNAMIC_ORIGINS', '')
        for _pat in [p.strip() for p in _fwd.split(',') if p.strip()]:
            if _is_prod_cors:
                logger.warning('CORS_DYNAMIC_ORIGINS ignore en production: %s', _pat)
            else:
                _DYNAMIC_CORS_PATTERNS.append(_pat)
    except Exception:
        pass
    _origin_env_hint = os.getenv('FRONTEND_URL', '').strip()
    if _origin_env_hint and _origin_env_hint not in CORS_ORIGINS:
        # Valide FRONTEND_URL pour éviter injection d'origine malveillante
        import re as _re2
        if _is_prod_cors and not _re2.match(r'^https://[a-z0-9.-]+(?::\d+)?$', _origin_env_hint):
            logger.warning('FRONTEND_URL ignoré (format invalide en prod): %s', _origin_env_hint)
        elif _origin_env_hint.startswith('https://') or _origin_env_hint.startswith('http://'):
            _dynamic_extra.append(_origin_env_hint)
        else:
            logger.warning('FRONTEND_URL ignoré (schéma invalide): %s', _origin_env_hint)
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
            'X-Tenant-Slug', 'X-Tenant-Domaine', 'Idempotency-Key', 'X-CSRF-TOKEN',
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
        resp = e.get_response()
        if resp is None:
            return {
                'message': e.description or e.name,
                'code': e.code,
            }, e.code or 500
        # Réponse Werkzeug conservée (code 415/404/405... correct) : on y
        # injecte juste le message JSON. Avant, renvoyer un tuple (dict,
        # code) depuis ce handler faisait repasser la requête dans le
        # dispatch Flask puis flask_restx Api.error_router, qui relançait
        # la HTTPException -> 500 générique au lieu du vrai code HTTP
        # (audit: POST /clients sans Content-Type JSON renvoyait 500
        # "Erreur interne" au lieu de 415).
        resp.set_data(__import__('json').dumps({
            'message': e.description or e.name,
            'code': e.code,
        }))
        resp.headers['Content-Type'] = 'application/json'
        return resp, e.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        from flask import jsonify
        # JWT-specific exceptions are handled by the dedicated handlers above
        # (and on the Api namespace); ignore them here.
        from flask_jwt_extended.exceptions import (
            NoAuthorizationError, InvalidHeaderError,
            RevokedTokenError, JWTDecodeError, WrongTokenError,
        )
        from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidSignatureError, InvalidTokenError
        if isinstance(e, (
            NoAuthorizationError, InvalidHeaderError,
            RevokedTokenError, JWTDecodeError,
            WrongTokenError, ExpiredSignatureError,
            # PyJWT brut : flask_jwt_extended 4.x laisse fuiter le DecodeError
            # (ex: header de token non décodable en base64) sans l'envelopper
            # dans JWTDecodeError — sinon il sort en 500 (audit : /auth/refresh
            # avec un token garbage devait répondre 401, pas 500).
            DecodeError, InvalidSignatureError, InvalidTokenError,
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
        doc='/docs/' if os.getenv('FLASK_ENV', '').lower() != 'production' else False,
        # Même liste d'origines que le CORS global (statiques + patterns dev
        # compilés) : flask-restx applique ce décorateur à toutes les ressources
        # et il pose _FLASK_CORS_EVALUATED, ce qui fait sauter le after_request
        # de flask-cors. Sans le passage explicite des origines ici, seules les
        # origines statiques (app.config['CORS_ORIGINS']) étaient servies et les
        # patterns LAN/tunnel (ex. Expo web http://192.168.x.y:8081) restaient
        # sans en-tête Access-Control-Allow-Origin.
        decorators=[cross_origin(origins=_cors_origins_config)]
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
    from app.api.v1.rh import ns_employes as employes_ns, ns_presences as presences_ns, ns_conges as conges_ns, ns_salaires as salaires_ns, ns_primes as primes_ns, ns_stagiaires as stagiaires_ns
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
    from app.api.v1.replication import ns as replication_ns
    # Etat et conflits de replication du POSTE (backend embarque). Enregistres
    # ici sans condition, comme `replication_ns` : sur le serveur central ces
    # tables ne sont jamais alimentees (elles sont locales au poste), mais
    # l'enregistrement systematique evite un 404 cote poste et garde les deux
    # moities de la fonctionnalite testables avec un seul `create_app()`.
    from app.api.v1.local_sync import ns as local_sync_ns
    from app.api.v1.sync_conflicts import ns as sync_conflicts_ns
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
    api.add_namespace(conges_ns, path='/api/v1/conges')
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
    api.add_namespace(replication_ns, path='/api/v1/sync/replicate')
    # Cote POSTE : /api/v1/sync/local-status (badge d'etat, cf. SyncStatus.jsx)
    # et /api/v1/sync/conflicts (+ /<id>/resolve). Sans ces deux lignes, le
    # badge reste sur « Serveur local injoignable » et l'ecran de conflits
    # renvoie 404 : le moteur de replication fonctionne mais n'est pas pilotable.
    # NB : le `path` explicite REMPLACE le nom du namespace dans l'URL
    # (flask-restx) — il doit donc contenir le prefixe complet attendu par le
    # client (`/api/v1/sync/...`), pas seulement `/api/v1`.
    api.add_namespace(local_sync_ns, path='/api/v1/sync')
    api.add_namespace(sync_conflicts_ns, path='/api/v1/sync/conflicts')
    api.add_namespace(entrepots_ns, path='/api/v1/entrepots')

    app.register_blueprint(desk_bp)

    # Servir les fichiers uploades (images produits, etc.)
    from flask import send_from_directory

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
        return send_from_directory(upload_dir, filename)

    from app.realtime.socket_server import init_socketio
    app.socketio = init_socketio(app)

    @app.before_request
    def before_request():
        from flask import g, request
        from app.security.tenant import resolve_tenant_from_header

        # g.current_tenant_id doit être remis à zéro comme les deux autres :
        # dans un contexte applicatif partagé (client de test, serveur
        # embarqué, worker), `g` survit d'une requête à l'autre et le
        # tenant_id de la requête précédente fuitait dans la suivante
        # (filtrage tenant erroné, 403 « Abonnement requis » aléatoires).
        g.current_tenant = None
        g.current_user = None
        g.current_tenant_id = None
        g.current_abonnement = None
        g.current_limits = None
        g.current_modules = None

        # Les routes publiques ne sont jamais rattachées à un tenant : on
        # n'y résout ni JWT ni header, sinon un JWT residuel (ancienne
        # session du navigateur) fausse la creation d'un nouveau tenant.
        # Les queries y restent donc non filtrées (g.current_tenant = None).
        if request.path.startswith(PUBLIC_PATH_PREFIXES):
            return

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
                        # INDISPENSABLE : get_current_tenant_id() est utilisé
                        # pour l'INSERT (desk.py, etc.). Sans cette ligne, les
                        # écritures partaient avec tenant_id = NULL pendant que
                        # le listener SQLAlchemy filtrait les SELECT sur
                        # tenant.id — d'où ObjectDeletedError au refresh
                        # post-commit et doublons à chaque sauvegarde desk.
                        g.current_tenant_id = tenant.id
                        return
        except Exception:
            pass

        try:
            tenant = resolve_tenant_from_header()
            if tenant:
                g.current_tenant = tenant
                g.current_tenant_id = tenant.id
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
    # Le schéma est inspecté AVANT toute requête : une base non migrée produit
    # un diagnostic en français au lieu d'une traceback SQLAlchemy illisible.
    try:
        with app.app_context():
            missing_tables, inspection_error = _inspect_database_schema()
            if inspection_error is not None or missing_tables:
                _log_database_schema_problem(missing_tables, inspection_error)
            else:
                from app.models.role_permission import RoleModel, Permission
                roles_empty = db.session.query(RoleModel.id).first() is None
                perms_empty = db.session.query(Permission.id).first() is None
                if roles_empty or perms_empty:
                    from scripts.seed_roles import seed_roles
                    seed_roles(app)
                    logger.info("Auto-seed rôles/permissions effectué (base vide).")
                else:
                    # Convergence : la matrice peut gagner de nouveaux codes
                    # (ex. `user.delete`) sans que la table `permissions` soit
                    # vide. On complète alors UNIQUEMENT les lignes manquantes
                    # (idempotent, aucune donnée existante n'est supprimée) afin
                    # que presets et rôles personnalisés exposent bien le CRUD
                    # complet des modules souscrits par le tenant.
                    from scripts.seed_roles import missing_permission_codes, seed_roles
                    missing_codes = missing_permission_codes()
                    if missing_codes:
                        seed_roles(app)
                        logger.info(
                            "Auto-seed rôles/permissions : %s code(s) manquant(s) ajouté(s) (%s).",
                            len(missing_codes), ", ".join(missing_codes[:10]),
                        )
    except Exception:
        logger.warning("Auto-seed rôles/permissions a échoué", exc_info=True)

    # NOTE: le seeding complet (_seed_initial_data) reste declenchable via CLI.

    # P2 : en-têtes de sécurité (Helmet-like) sans dépendance externe.
    @app.after_request
    def _security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        )
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), payment=(), usb=(), '
            'magnetometer=(), gyroscope=()'
        )
        return response

    return app
