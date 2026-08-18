
# backend/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api
from flask_jwt_extended import JWTManager


import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app():

    app = Flask(__name__)

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    app.config['SECRET_KEY'] = os.getenv(
        'SECRET_KEY',
        'dev-key'
    )

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

    # Accepter /route et /route/
    app.url_map.strict_slashes = False

    # ==========================================================
    # EXTENSIONS
    # ==========================================================

    db.init_app(app)
    migrate.init_app(app, db)

    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000'
    ).split(',')

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
    # FLASK-RESTX
    # ==========================================================

    api = Api(
        app,
        title='ERP Commercial API',
        version='1.0',
        doc='/docs/'
    )

    # ==========================================================
    # NAMESPACES
    # ==========================================================

    from app.api.v1.test import ns as test_ns
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
    from app.api.v1.rh import ns_employes as employes_ns, ns_presences as presences_ns, ns_salaires as salaires_ns, ns_primes as primes_ns
    from app.api.v1.comptabilite import ns_comptes as comptes_ns, ns_ecritures as ecritures_ns, ns_tresorerie as tresorerie_ns
    from app.api.v1.documents import ns_modeles as modeles_documents_ns, ns_documents as documents_ns
    from app.api.v1.achats_devis import ns_commandes_achat as commandes_achat_ns, ns_receptions as receptions_ns, ns_devis as devis_ns, ns_bons_livraison as bons_livraison_ns, ns_avoirs as avoirs_ns
    from app.api.v1.roles import ns as roles_ns
    from app.api.v1.permissions import ns as permissions_ns
    from app.api.v1.users import ns as users_ns

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

            tenant = resolve_tenant_from_header()

            if tenant:
                g.current_tenant = tenant

        except Exception:
            pass

    # ==========================================================
    # AUTO-SEEDING: Si aucun compte n'existe, créer des données de test
    # ==========================================================

    @app.before_request
    def auto_seed_if_empty():
        from flask import request
        if request.path.startswith('/static') or request.path.startswith('/docs'):
            return

        try:
            user_count = Utilisateur.query.count()
            if user_count == 0:
                import secrets
                from app.security.auth import hash_password
                from app.models.utilisateur import Role, StatutUtilisateur
                from app.models.abonnement import Abonnement, StatutAbonnement
                from app.models.paiement import Paiement, StatutPaiement, TypePaiement
                from app.models.produit import Produit
                from datetime import datetime, timedelta

                default_password = os.getenv('DEFAULT_SEED_PASSWORD')
                if not default_password:
                    default_password = secrets.token_urlsafe(16)

                entreprises = [
                    {
                        'tenant': {
                            'nom': 'Tech Solutions SARL',
                            'slug': 'tech-solutions',
                            'domaine': 'tech.local',
                            'email_contact': 'contact@tech-solutions.com',
                            'telephone': '+261 34 12 345 67',
                            'adresse': '12 Rue de la Tech',
                            'ville': 'Antananarivo',
                            'code_postal': '101',
                            'pays': 'Madagascar',
                            'statut': StatutTenant.ACTIF,
                            'plan': 'pro',
                            'date_abonnement': datetime.utcnow(),
                        },
                        'user': {
                            'username': 'tech',
                            'email': 'tech@erp.com',
                            'password': default_password,
                            'nom': 'Ramos',
                            'prenom': 'Thomas',
                            'telephone': '+261 34 12 345 67',
                            'role': Role.ADMIN,
                            'statut': StatutUtilisateur.ACTIF,
                        },
                        'abonnement': {
                            'montant': 79.0,
                            'plan': 'pro',
                            'date_debut': datetime.utcnow(),
                            'date_fin': datetime.utcnow() + timedelta(days=30),
                            'statut': StatutAbonnement.ACTIF,
                            'methode_paiement': 'carte',
                            'reference_paiement': 'SUB-TECH-001',
                        },
                        'produits': [
                            {'nom': 'Produit Tech #1', 'prix_vente_ht': 25.0, 'quantite_stock': 50},
                            {'nom': 'Produit Tech #2', 'prix_vente_ht': 45.0, 'quantite_stock': 30},
                        ],
                    },
                    {
                        'tenant': {
                            'nom': 'Green Import',
                            'slug': 'green-import',
                            'domaine': 'green.local',
                            'email_contact': 'contact@green-import.com',
                            'telephone': '+261 34 98 765 32',
                            'adresse': '45 Avenue des Importateurs',
                            'ville': 'Toamasina',
                            'code_postal': '601',
                            'pays': 'Madagascar',
                            'statut': StatutTenant.ACTIF,
                            'plan': 'enterprise',
                            'date_abonnement': datetime.utcnow(),
                        },
                        'user': {
                            'username': 'green',
                            'email': 'green@erp.com',
                            'password': default_password,
                            'nom': 'Razafindramanana',
                            'prenom': 'Sophie',
                            'telephone': '+261 34 98 765 32',
                            'role': Role.MANAGER,
                            'statut': StatutUtilisateur.ACTIF,
                        },
                        'abonnement': {
                            'montant': 199.0,
                            'plan': 'enterprise',
                            'date_debut': datetime.utcnow(),
                            'date_fin': datetime.utcnow() + timedelta(days=30),
                            'statut': StatutAbonnement.ACTIF,
                            'methode_paiement': 'virement',
                            'reference_paiement': 'SUB-GREEN-001',
                        },
                        'produits': [
                            {'nom': 'Produit Green #1', 'prix_vente_ht': 35.0, 'quantite_stock': 40},
                            {'nom': 'Produit Green #2', 'prix_vente_ht': 55.0, 'quantite_stock': 25},
                        ],
                    },
                ]

                for item in entreprises:
                    tenant = Tenant(**item['tenant'])
                    db.session.add(tenant)
                    db.session.flush()

                    user_data = item['user']
                    user_data['tenant_id'] = tenant.id
                    password = user_data.pop('password')
                    user_data['password_hash'] = hash_password(password)
                    user = Utilisateur(**user_data)
                    db.session.add(user)
                    db.session.flush()

                    abonnement_data = item['abonnement']
                    abonnement_data['tenant_id'] = tenant.id
                    abonnement = Abonnement(**abonnement_data)
                    db.session.add(abonnement)
                    db.session.flush()

                    paiement = Paiement(
                        tenant_id=tenant.id,
                        montant=abonnement.montant,
                        devise='MGA',
                        statut=StatutPaiement.CONFIRME,
                        type=TypePaiement.ABONNEMENT,
                        reference=abonnement.reference_paiement,
                        notes=f"Paiement initial - {item['tenant']['nom']}",
                        date_paiement=datetime.utcnow(),
                    )
                    db.session.add(paiement)
                    db.session.flush()

                    for prod in item.get('produits', []):
                        produit = Produit(
                            tenant_id=tenant.id,
                            reference=f"{tenant.slug}-{prod['nom'].split('#')[1].strip()}",
                            code_barre=f"{tenant.id}-{prod['nom'].split('#')[1].strip()}",
                            nom=prod['nom'],
                            description_courte=f"Description du produit pour {tenant.nom}",
                            prix_achat_ht=float(prod['prix_vente_ht']) * 0.6,
                            prix_vente_ht=float(prod['prix_vente_ht']),
                            quantite_stock=prod['quantite_stock'],
                            seuil_alerte=5,
                            created_by=user.id,
                            updated_by=user.id,
                        )
                        db.session.add(produit)

                db.session.commit()

        except Exception:
            pass

    # ==========================================================
    # JWT IDENTITY
    # ==========================================================

    @jwt.user_identity_loader
    def user_identity_lookup(user_id):
        return user_id

    # ==========================================================
    # JWT CLAIMS
    # ==========================================================

    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):

        from app.models.utilisateur import Utilisateur

        user = db.session.get(
            Utilisateur,
            identity
        )

        if user:

            return {
                'username': user.username,
                'email': user.email,
                'role': (
                    user.role.value
                    if hasattr(user.role, 'value')
                    else user.role
                ),
                'tenant_id': user.tenant_id,
            }

        return {}

    return app
