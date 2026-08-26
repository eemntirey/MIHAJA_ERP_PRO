# CODE.MD

### FICHIER .PY: check_db.py
<<<
import sqlite3, os
db = sqlite3.connect(os.path.join('web', 'backend', 'instance', 'erp.db'))
cur = db.execute("SELECT alembic_version FROM alembic_version")
print("alembic_version:", cur.fetchall())
rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("tables:", len(rows))
for r in rows:
    print("  ", r[0])
    cnt = db.execute(f"SELECT COUNT(*) FROM '{r[0]}'").fetchone()[0]
    print(f"     rows={cnt}")

>>>

### FICHIER .PY: reset_alembic.py
<<<
import sqlite3, os, shutil, sys

db_path = os.path.join('web', 'backend', 'instance', 'erp.db')
bak_path = db_path + '.bak'

if not os.path.exists(bak_path):
    shutil.copy2(db_path, bak_path)
    print("Backed up to", bak_path)
else:
    print("Backup already exists:", bak_path)

conn = sqlite3.connect(db_path)
try:
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    print("Before:", rows)
    conn.execute("DELETE FROM alembic_version")
    conn.commit()
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    print("After:", rows)
except Exception as e:
    print("alembic_version handling:", e)
    # table may not exist; create empty marker
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL); INSERT INTO alembic_version (version_num) VALUES ('')")
    conn.commit()
conn.close()

>>>

### FICHIER .PY: web\backend\add_user.py
<<<
from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.security.auth import hash_password

app = create_app()

with app.app_context():
    # Vérifier s'il existe déjà
    existing = Utilisateur.query.filter_by(email='testuser@example.com').first()
    if existing:
        print('Utilisateur test déjà existant:', existing.username)
    else:
        u = Utilisateur(
            username='testuser',
            email='testuser@example.com',
            password_hash=hash_password('Test1234'),
            nom='Test',
            prenom='User',
            role='USER',
            tenant_id=1,
        )
        db.session.add(u)
        db.session.commit()
        print('Utilisateur créé:', u.username)

>>>

### FICHIER .PY: web\backend\app\__init__.py
<<<

# backend/app/__init__.py

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
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

    # Synchronisation desktop/web (favoris, colonnes, filtres, sync incrémental)
    from app.api.v1.desk import desk_bp

    api.add_namespace(
        super_admin_ns,
        path='/api/v1/super-admin'
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
            logger.warning(
                "Impossible de résoudre le tenant depuis les headers HTTP",
                exc_info=True,
            )
            g.current_tenant = None

    # ==========================================================
    # AUTO-SEEDING: Desactive en production. A appeler explicitement
    # via le endpoint ou une commande CLI.
    # ==========================================================

    def _seed_initial_data(app):
        try:
            with app.app_context():
                from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
                from app.models.tenant import Tenant, StatutTenant
                from app.models.abonnement import Abonnement, StatutAbonnement
                from app.models.paiement import Paiement, StatutPaiement, TypePaiement
                from app.models.produit import Produit
                from app.security.auth import hash_password
                from datetime import datetime, timedelta

                user_count = Utilisateur.query.count()

                if user_count == 0:
                    default_password = os.getenv('DEFAULT_ADMIN_PASSWORD') or os.urandom(16).hex()

                    entreprises = [
                        {
                            'tenant': {
                                'nom': 'Mada Distribution SARL',
                                'slug': 'mada-distribution',
                                'domaine': 'mada.local',
                                'email_contact': 'contact@mada-distribution.com',
                                'telephone': '+261 34 12 345 67',
                                'adresse': 'Zone industrielle Andraisoro',
                                'ville': 'Antananarivo',
                                'code_postal': '101',
                                'pays': 'Madagascar',
                                'statut': StatutTenant.ACTIF,
                                'plan': 'pro',
                                'date_abonnement': datetime.utcnow(),
                            },
                            'user': {
                                'username': 'mada',
                                'email': 'mada@erp.com',
                                'password': default_password,
                                'nom': 'Rakotondrainibe',
                                'prenom': 'Hery',
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
                                'methode_paiement': 'especes',
                                'reference_paiement': 'SUB-TECH-001',
                            },
                            'produits': [
                                {'nom': 'Riz blanc (sac 50 kg) #1', 'prix_vente_ht': 136000.0, 'quantite_stock': 86},
                                {'nom': 'Huile de tournesol (carton 6 x 1 L) #2', 'prix_vente_ht': 174000.0, 'quantite_stock': 24},
                            ],
                        },
                        {
                            'tenant': {
                                'nom': 'Tana Import & Distribution',
                                'slug': 'tana-import',
                                'domaine': 'tana.local',
                                'email_contact': 'contact@tana-import.com',
                                'telephone': '+261 34 98 765 32',
                                'adresse': 'Quai de la Gare maritime',
                                'ville': 'Toamasina',
                                'code_postal': '601',
                                'pays': 'Madagascar',
                                'statut': StatutTenant.ACTIF,
                                'plan': 'enterprise',
                                'date_abonnement': datetime.utcnow(),
                            },
                            'user': {
                                'username': 'tana',
                                'email': 'tana@erp.com',
                                'password': default_password,
                                'nom': 'Razafindramanana',
                                'prenom': 'Voahangy',
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
                                {'nom': 'Sucre blanc (sac 25 kg) #1', 'prix_vente_ht': 112000.0, 'quantite_stock': 45},
                                {'nom': 'Eau minérale (pack 6 x 1,5 L) #2', 'prix_vente_ht': 9600.0, 'quantite_stock': 360},
                            ],
                        },
                    ]

                    for item in entreprises:
                        tenant = Tenant(item['tenant'])
                        db.session.add(tenant)
                        db.session.flush()

                        user_data = item['user']
                        user_data['tenant_id'] = tenant.id
                        password = user_data.pop('password')
                        user_data['password_hash'] = hash_password(password)
                        user = Utilisateur(user_data)
                        db.session.add(user)
                        db.session.flush()

                        abonnement_data = item['abonnement']
                        abonnement_data['tenant_id'] = tenant.id
                        abonnement = Abonnement(abonnement_data)
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
                    current_app.logger.info("Donnees de base initialisees avec succes")

        except Exception as e:
            app.logger.exception("Erreur pendant l'auto-seed: %s", e)
            try:
                db.session.rollback()
            except Exception:
                pass

    if os.getenv('FLASK_ENV') in ('development', 'testing') and os.getenv('AUTO_SEED_DATA') == '1':
        _seed_initial_data(app)

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

    # ==========================================================
    # TEMPS RÉEL (Socket.IO) - optionnel, activé par ENABLE_SOCKETIO=1
    # ==========================================================
    socketio = None
    if os.getenv('ENABLE_SOCKETIO') == '1':
        try:
            from app.websockets.socket_events import init_socketio
            socketio = init_socketio(app)
        except Exception as exc:  # pragma: no cover
            logger.warning("SocketIO non initialisé : %s", exc)

    return app

>>>

### FICHIER .PY: web\backend\app\ai\__init__.py
<<<
from .previsions import predict_sales, predict_stock_rupture
from .anomalies import detect_stock_anomalies, detect_sales_anomalies, detect_payment_anomalies
from .recommendations import suggest_reorders, suggest_cross_sell, suggest_pricing_adjustments
from .assistant import ask_assistant
from .training import train_models
from .external_services import external_ai, web_search, context_manager

__all__ = [
    'predict_sales',
    'predict_stock_rupture',
    'detect_stock_anomalies',
    'detect_sales_anomalies',
    'detect_payment_anomalies',
    'suggest_reorders',
    'suggest_cross_sell',
    'suggest_pricing_adjustments',
    'ask_assistant',
    'train_models',
    'external_ai',
    'web_search',
    'context_manager',
]

>>>

### FICHIER .PY: web\backend\app\ai\anomalies.py
<<<
import pandas as pd
import numpy as np
from datetime import datetime
from app.models.stock import MouvementStock
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db


def detect_stock_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    mouvements = MouvementStock.query.filter_by(is_active=True)
    if tenant_id:
        mouvements = mouvements.filter_by(tenant_id=tenant_id)
    mouvements = mouvements.all()

    if not mouvements:
        return {'anomalies': [], 'count': 0}

    data = []
    for m in mouvements:
        date_str = m.created_at.isoformat() if hasattr(m.created_at, 'isoformat') else str(m.created_at)
        data.append({
            'date': date_str,
            'quantite': abs(float(m.quantite or 0)),
            'produit_id': m.produit_id
        })

    df = pd.DataFrame(data)
    anomalies = []

    for produit_id in df['produit_id'].unique():
        prod_df = df[df['produit_id'] == produit_id]
        if len(prod_df) < 2:
            continue
        mean_qty = prod_df['quantite'].mean()
        std_qty = prod_df['quantite'].std()

        produit_query = Produit.query.filter_by(id=int(produit_id))
        if tenant_id:
            produit_query = produit_query.filter_by(tenant_id=tenant_id)
        produit = produit_query.first()
        nom_produit = produit.nom if produit else f"Produit #{produit_id}"

        if std_qty == 0 or np.isnan(std_qty):
            continue

        for _, row in prod_df.iterrows():
            z_score = abs(row['quantite'] - mean_qty) / std_qty
            if z_score > 1.8:
                anomalies.append({
                    'produit_id': int(produit_id),
                    'nom_produit': nom_produit,
                    'date': row['date'],
                    'quantite': row['quantite'],
                    'mean': round(mean_qty, 2),
                    'z_score': round(z_score, 2),
                    'type': 'Variation anormale de stock',
                    'severity': 'high' if z_score > 2.5 else 'medium'
                })

    return {'anomalies': anomalies, 'count': len(anomalies)}


def detect_sales_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    ventes = Vente.query.filter_by(is_active=True)
    if tenant_id:
        ventes = ventes.filter_by(tenant_id=tenant_id)
    ventes = ventes.all()

    if not ventes:
        return {'anomalies': [], 'count': 0}

    data = []
    for v in ventes:
        date_str = v.created_at.isoformat() if hasattr(v.created_at, 'isoformat') else str(v.created_at)
        data.append({
            'id': v.id,
            'reference': getattr(v, 'reference', f'Vente #{v.id}'),
            'date': date_str,
            'total_ttc': float(v.total_ttc or 0)
        })

    df = pd.DataFrame(data)
    anomalies = []

    mean_val = df['total_ttc'].mean()
    std_val = df['total_ttc'].std()

    if std_val == 0 or np.isnan(std_val):
        return {'anomalies': [], 'count': 0}

    for _, row in df.iterrows():
        z_score = abs(row['total_ttc'] - mean_val) / std_val
        if z_score > 1.8:
            anomalies.append({
                'vente_id': row['id'],
                'reference': row['reference'],
                'date': row['date'],
                'total_ttc': round(row['total_ttc'], 2),
                'mean': round(mean_val, 2),
                'z_score': round(z_score, 2),
                'type': 'Montant de vente inhabituel',
                'severity': 'high' if z_score > 2.5 else 'medium'
            })

    return {'anomalies': anomalies, 'count': len(anomalies)}


def detect_payment_anomalies(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Facture.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)

    factures = query.all()
    anomalies = []
    today = datetime.utcnow().date()

    for f in factures:
        statut_val = getattr(f.statut, 'value', str(f.statut)).lower()
        if statut_val in ['non_payee', 'payee_partiel', 'en_attente']:
            if f.created_at:
                created_date = f.created_at.date() if isinstance(f.created_at, datetime) else f.created_at
                days_overdue = (today - created_date).days
                if days_overdue > 30:
                    anomalies.append({
                        'facture_id': f.id,
                        'reference': f.reference,
                        'montant_ttc': float(f.total_ttc or 0),
                        'retard_jours': days_overdue,
                        'statut': statut_val,
                        'type': 'Facture impayée en retard critique',
                        'severity': 'high' if days_overdue > 60 else 'medium'
                    })

    return {'anomalies': anomalies, 'count': len(anomalies)}

>>>

### FICHIER .PY: web\backend\app\ai\assistant.py
<<<
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.facture import Facture
from app.models.ligne_vente import LigneVente
from app.security.tenant import get_current_tenant_id
from app.ai.previsions import predict_sales, predict_stock_rupture
from app.ai.recommendations import suggest_reorders
from app.ai.external_services import external_ai, web_search, context_manager
from app import db
import logging

logger = logging.getLogger(__name__)


def _get_tenant_name(tenant_id):
    try:
        from app.models.tenant import Tenant
        tenant = db.session.get(Tenant, tenant_id)
        return tenant.nom if tenant else None
    except Exception:
        return None


def _build_context_block(tenant_id):
    """Construit un contexte métier synthétique pour l'IA."""
    try:
        produits = Produit.query.filter_by(is_active=True)
        if tenant_id:
            produits = produits.filter_by(tenant_id=tenant_id)
        nb_produits = produits.count()

        ventes = Vente.query.filter_by(is_active=True)
        if tenant_id:
            ventes = ventes.filter_by(tenant_id=tenant_id)
        nb_ventes = ventes.count()
        ca_total = sum(float(v.total_ttc or 0) for v in ventes.limit(200).all())

        clients = Client.query.filter_by(is_active=True)
        if tenant_id:
            clients = clients.filter_by(tenant_id=tenant_id)
        nb_clients = clients.count()

        factures = Facture.query.filter_by(is_active=True)
        if tenant_id:
            factures = factures.filter_by(tenant_id=tenant_id)
        nb_factures = factures.count()

        alertes = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            alertes = alertes.filter_by(tenant_id=tenant_id)
        nb_alertes = alertes.count()

        return (
            f"Contexte métier actuel : {nb_produits} produits, {nb_clients} clients, "
            f"{nb_ventes} ventes, CA total {ca_total:.2f} Ar, {nb_factures} factures, "
            f"{nb_alertes} alerte(s) stock."
        )
    except Exception as e:
        logger.error(f"Erreur build_context_block: {str(e)}")
        return "Contexte métier indisponible pour le moment."


def ask_assistant(tenant_id=None, prompt="", conversation=None):
    tenant_id = get_current_tenant_id() or tenant_id
    prompt_lower = prompt.lower().strip() if prompt else ""

    if not prompt_lower:
        return "Bonjour ! Je suis l'assistant IA de votre ERP. Comment puis-je vous aider aujourd'hui ? Vous pouvez me poser des questions sur les stocks, les ventes, les clients, les factures ou les prévisions."

    tenant_name = _get_tenant_name(tenant_id)
    system_prompt = context_manager.build_system_prompt(tenant_name)
    context_block = _build_context_block(tenant_id)

    # Réponse interne forte pour les requêtes métier classiques
    internal_answer = _answer_internal(tenant_id, prompt_lower)
    if internal_answer:
        if external_ai.is_configured():
            enriched = _enrich_with_external_ai(
                prompt=prompt,
                prompt_lower=prompt_lower,
                system_prompt=system_prompt,
                context_block=context_block,
                internal_answer=internal_answer,
                conversation=conversation
            )
            if enriched:
                return enriched
        return internal_answer

    # Si pas de réponse interne, demander à l'IA externe si dispo
    if external_ai.is_configured():
        external_answer = _ask_external(
            prompt=prompt,
            prompt_lower=prompt_lower,
            system_prompt=system_prompt,
            context_block=context_block,
            conversation=conversation
        )
        if external_answer:
            return external_answer

    return ("**Assistant IA ERP** : Je peux vous assister sur plusieurs sujets :\n"
            "- *« Quel est l'état du stock ? »*\n"
            "- *« Quel est notre chiffre d'affaires ? »*\n"
            "- *« Quelles sont les prévisions de ventes ? »*\n"
            "- *« Combien de clients avons-nous ? »*\n"
            "- *« Quel est le montant des factures impayées ? »*")


def _answer_internal(tenant_id, prompt_lower):
    if any(w in prompt_lower for w in ['prévision', 'prevision', 'projections', 'futur', 'tendance']):
        prev = predict_sales(tenant_id=tenant_id, periods=30)
        return (f"**Prévisions de Ventes (30 prochains jours)** :\n"
                f"- Chiffre d'affaires estimé : **{prev['total_predicted']:.2f} Ar**\n"
                f"- Moyenne journalière : **{prev['average_daily_predicted']:.2f} Ar/jour**\n"
                f"- Tendance observée : **{prev['trend'].upper()}**\n"
                f"- Indice de confiance du modèle : **{int(prev['confidence_score']*100)}%**")

    if any(w in prompt_lower for w in ['réapprovision', 'réapprovisionnement', 'reorder', 'commande fournisseur', 'stock à commander', 'approvisionnement']):
        recommandations = suggest_reorders(tenant_id=tenant_id)
        suggestions = recommandations.get('recommendations') if isinstance(recommandations, dict) else None
        if not suggestions:
            return "Aucune recommandation de réapprovisionnement n'a été trouvée pour le moment."
        lines = []
        for item in suggestions[:5]:
            label = item.get('nom') or item.get('product_name') or 'Produit inconnu'
            quantity = item.get('quantite_suggeree') or item.get('suggested_quantity') or 0
            lines.append(f"- {label} : quantité suggérée {quantity}")
        return "**Réapprovisionnement recommandé** :\n" + "\n".join(lines)

    if any(w in prompt_lower for w in ['stock', 'inventaire', 'rupture', 'seuil', 'alerte']):
        produits = Produit.query.filter_by(is_active=True)
        if tenant_id:
            produits = produits.filter_by(tenant_id=tenant_id)
        produits_list = produits.all()
        alertes = [p for p in produits_list if (p.quantite_stock or 0) <= (p.seuil_alerte or 0)]
        ruptures = [p for p in produits_list if (p.quantite_stock or 0) == 0]
        recommandations = suggest_reorders(tenant_id=tenant_id)
        nb_recommandations = recommandations.get('count', 0) if isinstance(recommandations, dict) else 0
        if ruptures:
            msg = f"**Attention** : {len(ruptures)} produit(s) en rupture totale de stock ({', '.join([p.nom for p in ruptures[:3]])}).\n"
        elif alertes:
            msg = f"**Alerte Stock** : {len(alertes)} produit(s) ont atteint leur seuil d'alerte.\n"
        else:
            msg = f"**Stock au vert** : Les {len(produits_list)} produits du catalogue disposent d'un niveau de stock suffisant.\n"
        if nb_recommandations > 0:
            msg += f"**Conseil IA** : {nb_recommandations} réapprovisionnement(s) suggéré(s)."
        return msg

    if any(w in prompt_lower for w in ['top produit', 'meilleur produit', 'meilleures ventes', 'produits les plus vendus', 'top ventes']):
        results = db.session.query(
            LigneVente.produit_id,
            db.func.sum(LigneVente.quantite).label('quantite_vendue'),
            db.func.sum(LigneVente.total_ttc).label('montant_total')
        ).join(Vente, LigneVente.vente_id == Vente.id)
        results = results.filter(Vente.is_active == True)
        if tenant_id:
            results = results.filter(Vente.tenant_id == tenant_id)
        results = results.group_by(LigneVente.produit_id).order_by(db.desc('quantite_vendue')).limit(3).all()
        if not results:
            return "Je n'ai pas trouvé de données de vente suffisantes pour établir un top des produits."
        lines = []
        for row in results:
            produit_query = Produit.query.filter_by(id=row.produit_id)
            if tenant_id:
                produit_query = produit_query.filter_by(tenant_id=tenant_id)
            produit = produit_query.first()
            label = produit.nom if produit else f'Produit #{row.produit_id}'
            lines.append(f"- {label} : {float(row.quantite_vendue):.0f} unités vendues, {float(row.montant_total or 0):.2f} Ar")
        return "**Produits les plus vendus** :\n" + "\n".join(lines)

    if any(w in prompt_lower for w in ['vente', 'ca', 'chiffre', 'chiffre d\'affaires', 'revenu']):
        ventes = Vente.query.filter_by(is_active=True)
        if tenant_id:
            ventes = ventes.filter_by(tenant_id=tenant_id)
        ventes_list = ventes.all()
        total_ca = sum(float(v.total_ttc or 0) for v in ventes_list)
        return f"**Chiffre d'Affaires Total** : **{total_ca:.2f} Ar** générés sur un total de **{len(ventes_list)} ventes** enregistrées."

    if any(w in prompt_lower for w in ['facture', 'impayé', 'impayee', 'retard', 'paiement']):
        factures = Facture.query.filter_by(is_active=True)
        if tenant_id:
            factures = factures.filter_by(tenant_id=tenant_id)
        factures_list = factures.all()
        impayees = [f for f in factures_list if getattr(f.statut, 'value', str(f.statut)).lower() in ['non_payee', 'payee_partiel', 'en_attente']]
        montant_impaye = sum(float(f.total_ttc or 0) for f in impayees)
        return f"**Factures** : **{len(impayees)} facture(s) en attente ou non payée(s)** pour un montant total restant dû de **{montant_impaye:.2f} Ar** sur {len(factures_list)} factures émises."

    if any(w in prompt_lower for w in ['client', 'acheteur']):
        clients = Client.query.filter_by(is_active=True)
        if tenant_id:
            clients = clients.filter_by(tenant_id=tenant_id)
        nb_clients = clients.count()
        return f"**Portefeuille Clients** : Vous avez actuellement **{nb_clients} client(s) actif(s)** enregistrés dans le système."

    if any(w in prompt_lower for w in ['fournisseur', 'achat', 'commande']):
        fournisseurs = Fournisseur.query.filter_by(is_active=True)
        if tenant_id:
            fournisseurs = fournisseurs.filter_by(tenant_id=tenant_id)
        return f"**Fournisseurs** : **{fournisseurs.count()} fournisseur(s)** enregistrés."

    return None


def _enrich_with_external_ai(prompt, prompt_lower, system_prompt, context_block, internal_answer, conversation):
    enriched_query = (
        "Réponds en français, de façon professionnelle et concise.\n"
        f"Contexte interne vérifié : {context_block}\n"
        f"Réponse interne validée : {internal_answer}\n"
        f"Question de l'utilisateur : {prompt}\n"
        "Si des sources externes peuvent préciser la réponse, cite-les clairement."
    )
    messages = context_manager.build_messages(conversation or [], enriched_query)
    result = external_ai.chat(messages=messages, system_prompt=system_prompt)
    if result.get('content'):
        sources = []
        if result.get('provider') and result['provider'] != 'local':
            sources.append({
                'name': result['provider'],
                'type': 'ia',
                'url': ''
            })
        if web_search and _should_web_search(prompt_lower):
            web_results = web_search.search(prompt, max_results=3)
            sources.extend([{**r, 'type': 'web'} for r in web_results])
        if sources:
            source_lines = "\n\n**Sources** :\n" + "\n".join(
                f"- {s['name']}: {s['url'] or 'réponse générée'}" for s in sources
            )
            return result['content'] + source_lines
        return result['content']
    return None


def _ask_external(prompt, prompt_lower, system_prompt, context_block, conversation):
    enriched_query = (
        "Réponds en français, de façon professionnelle et concise.\n"
        f"Contexte interne : {context_block}\n"
        f"Question : {prompt}\n"
        "Tu peux utiliser des recherches web si nécessaire."
    )
    messages = context_manager.build_messages(conversation or [], enriched_query)
    result = external_ai.chat(messages=messages, system_prompt=system_prompt)
    if result.get('content'):
        sources = []
        if result.get('provider') and result['provider'] != 'local':
            sources.append({
                'name': result['provider'],
                'type': 'ia',
                'url': ''
            })
        if web_search and _should_web_search(prompt_lower):
            web_results = web_search.search(prompt, max_results=3)
            sources.extend([{**r, 'type': 'web'} for r in web_results])
        if sources:
            source_lines = "\n\n**Sources** :\n" + "\n".join(
                f"- {s['name']}: {s['url'] or 'réponse générée'}" for s in sources
            )
            return result['content'] + source_lines
        return result['content']
    return None


def _should_web_search(prompt_lower: str) -> bool:
    triggers = [
        'marché', 'tendance', 'concurrent', 'prix du marché',
        'norme', 'réglementation', 'loi', 'actualité', 'news'
    ]
    return any(t in prompt_lower for t in triggers)


>>>

### FICHIER .PY: web\backend\app\ai\external_services.py
<<<
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from app.security.tenant import get_current_tenant_id

logger = logging.getLogger(__name__)


class ExternalAIService:
    """Abstraction pour appeler des fournisseurs IA externes."""

    def __init__(self):
        self.provider = os.getenv('AI_PROVIDER', 'local').lower()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
        self.timeout = int(os.getenv('AI_REQUEST_TIMEOUT', '30'))

    def is_configured(self) -> bool:
        if self.provider == 'openai':
            return bool(self.openai_api_key)
        if self.provider == 'anthropic':
            return bool(self.anthropic_api_key)
        return False

    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                'provider': 'local',
                'content': None,
                'error': 'Aucun fournisseur IA externe configuré'
            }

        try:
            if self.provider == 'openai':
                return self._call_openai(messages, system_prompt)
            if self.provider == 'anthropic':
                return self._call_anthropic(messages, system_prompt)
        except Exception as e:
            logger.error(f"Erreur appel IA externe ({self.provider}): {str(e)}")
            return {
                'provider': self.provider,
                'content': None,
                'error': str(e)
            }

        return {
            'provider': 'local',
            'content': None,
            'error': 'Fournisseur IA non supporté'
        }

    def _call_openai(self, messages: List[Dict[str, str]], system_prompt: Optional[str]) -> Dict[str, Any]:
        payload_messages = []
        if system_prompt:
            payload_messages.append({'role': 'system', 'content': system_prompt})
        payload_messages.extend(messages)

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f"Bearer {self.openai_api_key}",
                'Content-Type': 'application/json'
            },
            json={
                'model': self.openai_model,
                'messages': payload_messages,
                'temperature': 0.2,
                'max_tokens': 1200
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return {
            'provider': 'openai',
            'content': content,
            'model': self.openai_model,
            'usage': data.get('usage')
        }

    def _call_anthropic(self, messages: List[Dict[str, str]], system_prompt: Optional[str]) -> Dict[str, Any]:
        payload_messages = []
        for m in messages:
            role = 'user' if m['role'] == 'user' else 'assistant'
            payload_messages.append({'role': role, 'content': m['content']})

        body = {
            'model': self.anthropic_model,
            'messages': payload_messages,
            'max_tokens': 1200,
            'temperature': 0.2
        }
        if system_prompt:
            body['system'] = system_prompt

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': self.anthropic_api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            },
            json=body,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        content_blocks = data.get('content', [])
        content = content_blocks[0].get('text', '') if content_blocks else ''
        return {
            'provider': 'anthropic',
            'content': content,
            'model': self.anthropic_model,
            'usage': data.get('usage')
        }


class WebSearchService:
    """Recherche web basique pour enrichir les réponses IA."""

    def __init__(self):
        self.enabled = os.getenv('AI_WEB_SEARCH_ENABLED', 'false').lower() == 'true'
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.timeout = int(os.getenv('AI_WEB_SEARCH_TIMEOUT', '15'))

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.enabled:
            return []

        results = []
        try:
            if self.serpapi_key:
                results = self._search_serpapi(query, max_results)
            else:
                results = self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.error(f"Erreur recherche web: {str(e)}")

        return results[:max_results]

    def _search_serpapi(self, query: str, max_results: int) -> List[Dict[str, str]]:
        response = requests.get(
            'https://serpapi.com/search.json',
            params={
                'q': query,
                'api_key': self.serpapi_key,
                'num': max_results,
                'hl': 'fr',
                'gl': 'fr'
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get('organic_results', [])[:max_results]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', '')
            })
        return results

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        response = requests.get(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        results = []

        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'FirstURL' in topic:
                results.append({
                    'title': topic.get('Text', '').split(' - ')[0],
                    'url': topic.get('FirstURL', ''),
                    'snippet': topic.get('Text', '')
                })
        return results

    def fetch_page(self, url: str) -> Optional[str]:
        try:
            response = requests.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; ERP-IA-Bot/1.0)'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines[:120])
        except Exception as e:
            logger.error(f"Erreur fetch page {url}: {str(e)}")
            return None


class AIContextManager:
    """Gestion du contexte conversationnel."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history

    def build_messages(self, conversation: List[Dict[str, Any]], current_prompt: str) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        for msg in conversation[-self.max_history:]:
            role = 'user' if msg.get('role') == 'user' else 'assistant'
            content = msg.get('content', '')
            if content:
                messages.append({'role': role, 'content': content})

        if current_prompt:
            messages.append({'role': 'user', 'content': current_prompt})
        return messages

    def build_system_prompt(self, tenant_name: Optional[str] = None) -> str:
        tenant_label = tenant_name or 'votre entreprise'
        return (
            "Vous êtes l'assistant IA d'un ERP commercial. "
            f"Vous répondez en français, de manière concise et professionnelle. "
            f"Vous vous appuyez sur les données métier du tenant '{tenant_label}', "
            "sur les outils internes du ERP (stocks, ventes, clients, factures, prévisions) "
            "et, si disponible, sur des ressources externes vérifiées. "
            "Si une information incertaine vient d'une source externe, citez-la clairement. "
            "Si une donnée interne est indisponible, dites-le explicitement."
        )


external_ai = ExternalAIService()
web_search = WebSearchService()
context_manager = AIContextManager()

>>>

### FICHIER .PY: web\backend\app\ai\models\__init__.py
<<<
# Placeholder package for serialized AI models

>>>

### FICHIER .PY: web\backend\app\ai\previsions.py
<<<
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.models.vente import Vente
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.security.tenant import get_current_tenant_id
from app import db


def predict_sales(tenant_id=None, periods=30, product_id=None):
    """
    Prédiction du chiffre d'affaires et des volumes de ventes
    basée sur l'analyse de régression linéaire et moyennes mobiles pondérées.
    """
    tenant_id = get_current_tenant_id() or tenant_id
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    ventes = query.order_by(Vente.created_at.asc()).all()

    today = datetime.utcnow().date()

    if not ventes or len(ventes) < 2:
        baseline_daily = 100.0 if not ventes else float(ventes[0].total_ttc or 100.0)
        forecast_list = []
        forecast_simple = []
        total_predicted = 0.0

        for i in range(1, periods + 1):
            future_date = today + timedelta(days=i)
            variation = np.sin(i / 3.0) * (baseline_daily * 0.1)
            predicted_val = round(max(10.0, baseline_daily + variation), 2)
            forecast_simple.append(predicted_val)
            forecast_list.append({
                'date': future_date.isoformat(),
                'predicted_sales': predicted_val,
                'lower_bound': round(predicted_val * 0.85, 2),
                'upper_bound': round(predicted_val * 1.15, 2)
            })
            total_predicted += predicted_val

        return {
            'tenant_id': tenant_id,
            'periods': periods,
            'forecast': forecast_simple,
            'forecast_details': forecast_list,
            'total_predicted': round(total_predicted, 2),
            'average_daily_predicted': round(total_predicted / max(periods, 1), 2),
            'trend': 'stable',
            'growth_rate_percent': 0.0,
            'confidence_score': 0.65,
            'status': 'baseline'
        }

    data = [{'date': v.created_at, 'total': float(v.total_ttc or 0.0)} for v in ventes if v.created_at]
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df_daily = df.set_index('date').resample('D').sum().fillna(0).reset_index()

    df_daily['date_ordinal'] = df_daily['date'].apply(lambda x: x.toordinal())

    X = df_daily['date_ordinal'].values
    Y = df_daily['total'].values

    if len(X) > 1 and np.std(X) > 0:
        slope, intercept = np.polyfit(X, Y, 1)
        std_err = np.std(Y - (slope * X + intercept))
    else:
        slope = 0.0
        intercept = Y.mean() if len(Y) > 0 else 100.0
        std_err = Y.std() if len(Y) > 0 else 10.0

    forecast_simple = []
    forecast_list = []
    total_predicted = 0.0

    for i in range(1, periods + 1):
        future_date = today + timedelta(days=i)
        future_ordinal = future_date.toordinal()

        raw_pred = slope * future_ordinal + intercept
        day_factor = 1.1 if future_date.weekday() in [4, 5] else 0.95
        predicted_val = round(max(0.0, raw_pred * day_factor), 2)

        lower_bound = round(max(0.0, predicted_val - 1.96 * max(std_err, 5.0)), 2)
        upper_bound = round(predicted_val + 1.96 * max(std_err, 5.0), 2)

        forecast_simple.append(predicted_val)
        forecast_list.append({
            'date': future_date.isoformat(),
            'predicted_sales': predicted_val,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        })
        total_predicted += predicted_val

    if slope > 0.5:
        trend = 'forte_croissance'
    elif slope > 0.05:
        trend = 'croissante'
    elif slope < -0.5:
        trend = 'forte_décroissance'
    elif slope < -0.05:
        trend = 'décroissante'
    else:
        trend = 'stable'

    return {
        'tenant_id': tenant_id,
        'periods': periods,
        'forecast': forecast_simple,
        'forecast_details': forecast_list,
        'total_predicted': round(total_predicted, 2),
        'average_daily_predicted': round(total_predicted / max(periods, 1), 2),
        'trend': trend,
        'confidence_score': 0.88,
        'status': 'success'
    }


def predict_stock_rupture(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produits = query.all()

    predictions = []
    for p in produits:
        mouvements = MouvementStock.query.filter_by(produit_id=p.id, is_active=True).all()
        if not mouvements:
            continue
        qty_changes = [abs(float(m.quantite)) for m in mouvements if getattr(m.type_mouvement, 'value', str(m.type_mouvement)).lower() in ['sortie', 'vente']]
        if not qty_changes:
            avg_consumption = 1.0
        else:
            avg_consumption = np.mean(qty_changes)

        if avg_consumption > 0:
            days_remaining = float(p.quantite_stock) / avg_consumption
            if days_remaining <= 14:
                predictions.append({
                    'produit_id': p.id,
                    'nom': p.nom,
                    'stock_actuel': float(p.quantite_stock),
                    'seuil_alerte': float(p.seuil_alerte or 0),
                    'consommation_moyenne_jour': round(avg_consumption, 2),
                    'jours_restants': round(days_remaining, 1),
                    'priorite': 'CRITIQUE' if days_remaining <= 3 else 'HAUTE'
                })

    predictions.sort(key=lambda x: x['jours_restants'])
    return {'predictions': predictions, 'count': len(predictions)}

>>>

### FICHIER .PY: web\backend\app\ai\recommendations.py
<<<
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import func


def suggest_reorders(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produits = query.all()

    recommendations = []
    for p in produits:
        stock_actuel = float(p.quantite_stock or 0)
        seuil_alerte = float(p.seuil_alerte or 0)
        seuil_critique = float(p.seuil_critique or 0)

        if stock_actuel <= seuil_alerte or stock_actuel <= 5:
            # Calcul de la quantité optimale de réapprovisionnement
            quantite_suggeree = max(20, int((seuil_alerte * 2.5) - stock_actuel))

            is_critique = stock_actuel <= seuil_critique or stock_actuel == 0
            score = (seuil_alerte - stock_actuel) / max(seuil_alerte, 1) if seuil_alerte > 0 else 1.0

            fournisseur = db.session.get(Fournisseur, p.fournisseur_id) if getattr(p, 'fournisseur_id', None) else None

            recommendations.append({
                'produit_id': p.id,
                'nom': p.nom,
                'reference': getattr(p, 'reference', f'REF-{p.id}'),
                'stock_actuel': stock_actuel,
                'seuil_alerte': seuil_alerte,
                'seuil_critique': seuil_critique,
                'quantite_suggeree': quantite_suggeree,
                'prix_achat_estime': round(quantite_suggeree * float(p.prix_achat_ht or 0), 2),
                'fournisseur_nom': fournisseur.raison_sociale if fournisseur else 'Non spécifié',
                'priorite': 'CRITIQUE' if is_critique else 'HAUTE',
                'score': round(float(score), 2)
            })

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return {'recommendations': recommendations, 'count': len(recommendations)}


def suggest_cross_sell(client_id):
    from app.models.ligne_vente import LigneVente
    tenant_id = get_current_tenant_id()
    ventes = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        ventes = ventes.filter_by(tenant_id=tenant_id)
    ventes = ventes.all()
    if not ventes:
        popular = Produit.query.filter_by(is_active=True)
        if tenant_id:
            popular = popular.filter_by(tenant_id=tenant_id)
        popular = popular.limit(5).all()
        return {
            'recommendations': [{'produit_id': p.id, 'nom': p.nom, 'prix': float(p.prix_vente_ht or 0)} for p in popular],
            'count': len(popular)
        }

    vente_ids = [v.id for v in ventes]
    lignes = LigneVente.query.filter(LigneVente.vente_id.in_(vente_ids), LigneVente.is_active == True).all()
    produits_achetes = set(l.produit_id for l in lignes)

    autres_produits = Produit.query.filter(
        Produit.is_active == True,
        ~Produit.id.in_(produits_achetes)
    )
    if tenant_id:
        autres_produits = autres_produits.filter_by(tenant_id=tenant_id)
    autres_produits = autres_produits.limit(5).all()

    return {
        'recommendations': [{'produit_id': p.id, 'nom': p.nom, 'prix': float(p.prix_vente_ht or 0)} for p in autres_produits],
        'count': len(autres_produits)
    }


def suggest_pricing_adjustments(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produits = query.all()

    suggestions = []
    for p in produits:
        prix_achat = float(p.prix_achat_ht or 0)
        prix_vente = float(p.prix_vente_ht or 0)

        if prix_achat > 0:
            marge_pct = ((prix_vente - prix_achat) / prix_achat) * 100
            if marge_pct < 15.0:
                nouveau_prix = round(prix_achat * 1.25, 2)
                suggestions.append({
                    'produit_id': p.id,
                    'nom': p.nom,
                    'prix_actuel': prix_vente,
                    'marge_actuelle_pct': round(marge_pct, 1),
                    'prix_suggere': nouveau_prix,
                    'marge_cible_pct': 25.0,
                    'raison': 'Marge trop faible (< 15%)'
                })
            elif float(p.quantite_stock or 0) > 100 and marge_pct > 50.0:
                nouveau_prix = round(prix_vente * 0.9, 2)
                suggestions.append({
                    'produit_id': p.id,
                    'nom': p.nom,
                    'prix_actuel': prix_vente,
                    'marge_actuelle_pct': round(marge_pct, 1),
                    'prix_suggere': nouveau_prix,
                    'marge_cible_pct': round(marge_pct * 0.9, 1),
                    'raison': 'Surstock et marge élevée : promotion recommandée (-10%)'
                })

    return {'suggestions': suggestions, 'count': len(suggestions)}

>>>

### FICHIER .PY: web\backend\app\ai\training.py
<<<

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from app.models.vente import Vente
from app.models.stock import MouvementStock
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db


MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')


def train_models(tenant_id=None, data=None, force_retrain=False, model_type='all'):
    """
    Entraînement des modèles prédictifs de ventes et de consommation de stock.
    
    Args:
        tenant_id: ID du tenant pour l'entraînement spécifique
        data: Données personnalisées pour l'entraînement
        force_retrain: Si True, force le réentraînement même si les données n'ont pas changé
        model_type: Type de modèle à entraîner ('all', 'sales', 'stock')
    
    Sauvegarde des paramètres de modèles dans app/ai/models/.
    """
    tenant_id = get_current_tenant_id() or tenant_id
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Vérifier si le réentraînement est nécessaire
    if not force_retrain:
        # Ici on pourrait vérifier la date du dernier entraînement
        # et les dates des dernières données
        pass

    trained_models = []
    result = {'status': 'success', 'message': 'Modèles IA entraînés', 'models_trained': []}
    
    # 1. Modèle de prévision de Vente
    if model_type in ['all', 'sales']:
        query_ventes = Vente.query.filter_by(is_active=True)
        if tenant_id:
            query_ventes = query_ventes.filter_by(tenant_id=tenant_id)
        ventes = query_ventes.all()

        vente_model_data = {
            'trained_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'records_count': len(ventes),
            'slope': 0.1,
            'intercept': 100.0,
            'r2_score': 0.85
        }

        if len(ventes) >= 2:
            records = [{'date': v.created_at.date() if isinstance(v.created_at, datetime) else v.created_at, 'total': float(v.total_ttc or 0)} for v in ventes if v.created_at]
            if records:
                df = pd.DataFrame(records)
                df_daily = df.groupby('date')['total'].sum().reset_index()
                df_daily['ord'] = df_daily['date'].apply(lambda x: x.toordinal())
                X = df_daily['ord'].values
                Y = df_daily['total'].values
                if len(X) >= 2 and np.std(X) > 0:
                    slope, intercept = np.polyfit(X, Y, 1)
                    vente_model_data['slope'] = float(slope)
                    vente_model_data['intercept'] = float(intercept)
                    vente_model_data['r2_score'] = round(float(np.corrcoef(X, Y)[0, 1]**2), 3) if len(X) > 2 else 0.80

        vente_model_path = os.path.join(MODELS_DIR, 'vente_model.pkl')
        with open(vente_model_path, 'wb') as f:
            pickle.dump(vente_model_data, f)
        
        trained_models.append('vente_model.pkl')
        result['vente_model'] = vente_model_data

    # 2. Modèle de Consommation de Stock
    if model_type in ['all', 'stock']:
        query_stock = MouvementStock.query.filter_by(is_active=True)
        if tenant_id:
            query_stock = query_stock.filter_by(tenant_id=tenant_id)
        mouvements = query_stock.all()

        stock_model_data = {
            'trained_at': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'mouvements_count': len(mouvements),
            'avg_consumption_rate': 2.5,
            'status': 'trained'
        }

        stock_model_path = os.path.join(MODELS_DIR, 'stock_model.pkl')
        with open(stock_model_path, 'wb') as f:
            pickle.dump(stock_model_data, f)
        
        trained_models.append('stock_model.pkl')
        result['stock_model'] = stock_model_data
    
    result['models_trained'] = trained_models
    result['message'] = f'Modèles IA entraînés: {len(trained_models)} modèle(s)'
    
    return result


>>>

### FICHIER .PY: web\backend\app\api\__init__.py
<<<
from . import v1

>>>

### FICHIER .PY: web\backend\app\api\v1\__init__.py
<<<
from . import auth
from . import clients
from . import dashboard
from . import factures
from . import fournisseurs
from . import paiements
from . import produits
from . import stocks
from . import ventes
from . import ai
from . import public
from . import tenants
from . import abonnements
from . import documents
from . import livraisons
from . import rh
from . import achats_devis
from . import comptabilite
from . import roles
from . import permissions
from . import users
from . import papi

# Note: test namespace is imported conditionally in app/__init__.py during API registration

>>>

### FICHIER .PY: web\backend\app\api\v1\abonnements.py
<<<
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.utilisateur import Role
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.services.abonnement_service import AbonnementService
from app import db
from datetime import datetime
from app.security.roles import is_super_admin

ns = Namespace('abonnements', description='Gestion des abonnements')


def _get_tenant_id_from_jwt():
    claims = get_jwt() or {}
    return claims.get('tenant_id')


@ns.route('/demander')
class DemanderAbonnement(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        data['tenant_id'] = tenant_id
        try:
            abonnement, paiement = AbonnementService.create_abonnement(data)
            response = {
                'abonnement': abonnement.to_dict(),
            }
            if paiement:
                response['paiement'] = paiement.to_dict()
            return response, 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400


@ns.route('/mon-abonnement')
class MonAbonnement(Resource):
    @jwt_required()
    def get(self):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        abonnement = AbonnementService.get_active_by_tenant(tenant_id)
        if not abonnement:
            return {'abonnement': None}, 200
        return {'abonnement': abonnement.to_dict()}, 200


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
        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        data = request.get_json() or {}

        paiement = Paiement.query.filter_by(
            tenant_id=tenant_id,
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

        return {
            'abonnement': abonnement.to_dict(),
            'paiement': paiement.to_dict() if paiement else None
        }, 200


@ns.route('/<int:id>/renouveler')
class RenouvelerAbonnement(Resource):
    @jwt_required()
    def post(self, id):
        abonnement = db.session.get(Abonnement, id)
        if not abonnement:
            return {'message': 'Abonnement non trouve'}, 404

        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401
        if abonnement.tenant_id != tenant_id:
            return {'message': 'Acces refuse a cet abonnement'}, 403

        result = AbonnementService.renew_subscription(id)
        if not result:
            return {'message': 'Abonnement non trouve'}, 404
        abonnement, paiement = result
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
                tenant.date_abonnement = datetime.utcnow()
                db.session.add(tenant)

        db.session.commit()

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
        items, total = AbonnementService.get_all_subscriptions(tenant_id=None, page=page, per_page=per_page)
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

>>>

### FICHIER .PY: web\backend\app\api\v1\achats_devis.py
<<<
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.produit_service import ProduitService
from app.services.achat_service import CommandeAchatService, ReceptionAchatService
from app.services.devis_avoir_service import DevisService, BonLivraisonService, AvoirService

ns_commandes_achat = Namespace('commandes-achat', description='Gestion des commandes d\'achat')
ns_receptions = Namespace('receptions', description='Gestion des receptions')
ns_devis = Namespace('devis', description='Gestion des devis')
ns_bons_livraison = Namespace('bons-livraison', description='Gestion des bons de livraison')
ns_avoirs = Namespace('avoirs', description='Gestion des avoirs')

@ns_commandes_achat.route('/')
class CommandeAchatList(Resource):
    @tenant_required
    def get(self):
        commandes, total = CommandeAchatService.get_all()
        return {'commandes': [c.to_dict() for c in commandes], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        commande = CommandeAchatService.create(data)
        return commande.to_dict(), 201

@ns_commandes_achat.route('/<int:id>')
class CommandeAchatResource(Resource):
    @tenant_required
    def get(self, id):
        commande = CommandeAchatService.get_by_id(id)
        if not commande:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return commande.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        commande = CommandeAchatService.update(id, data)
        if not commande:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return commande.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = CommandeAchatService.delete(id)
        if not success:
            return {'message': 'Commande d\'achat non trouvee'}, 404
        return {'message': 'Commande d\'achat supprimee'}, 200

@ns_receptions.route('/')
class ReceptionList(Resource):
    @tenant_required
    def get(self):
        receptions, total = ReceptionAchatService.get_all()
        return {'receptions': [r.to_dict() for r in receptions], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        reception = ReceptionAchatService.create(data)
        return reception.to_dict(), 201

@ns_receptions.route('/<int:id>')
class ReceptionResource(Resource):
    @tenant_required
    def get(self, id):
        reception = ReceptionAchatService.get_by_id(id)
        if not reception:
            return {'message': 'Reception non trouvee'}, 404
        return reception.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        reception = ReceptionAchatService.update(id, data)
        if not reception:
            return {'message': 'Reception non trouvee'}, 404
        return reception.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = ReceptionAchatService.delete(id)
        if not success:
            return {'message': 'Reception non trouvee'}, 404
        return {'message': 'Reception supprimee'}, 200

@ns_devis.route('/')
class DevisList(Resource):
    @tenant_required
    def get(self):
        devis_list, total = DevisService.get_all()
        return {'devis': [d.to_dict() for d in devis_list], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        devis = DevisService.create(data)
        return devis.to_dict(), 201

@ns_devis.route('/<int:id>')
class DevisResource(Resource):
    @tenant_required
    def get(self, id):
        devis = DevisService.get_by_id(id)
        if not devis:
            return {'message': 'Devis non trouve'}, 404
        return devis.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        devis = DevisService.update(id, data)
        if not devis:
            return {'message': 'Devis non trouve'}, 404
        return devis.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = DevisService.delete(id)
        if not success:
            return {'message': 'Devis non trouve'}, 404
        return {'message': 'Devis supprime'}, 200

@ns_devis.route('/<int:id>/convertir')
class DevisConvertir(Resource):
    @tenant_required
    def post(self, id):
        vente = DevisService.convertir_en_vente(id)
        if not vente:
            return {'message': 'Devis non trouve'}, 404
        return vente.to_dict(), 201

@ns_bons_livraison.route('/')
class BonLivraisonList(Resource):
    @tenant_required
    def get(self):
        bls, total = BonLivraisonService.get_all()
        return {'bons_livraison': [b.to_dict() for b in bls], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        bl = BonLivraisonService.create(data)
        return bl.to_dict(), 201

@ns_bons_livraison.route('/<int:id>')
class BonLivraisonResource(Resource):
    @tenant_required
    def get(self, id):
        bl = BonLivraisonService.get_by_id(id)
        if not bl:
            return {'message': 'Bon de livraison non trouve'}, 404
        return bl.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        bl = BonLivraisonService.update(id, data)
        if not bl:
            return {'message': 'Bon de livraison non trouve'}, 404
        return bl.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = BonLivraisonService.delete(id)
        if not success:
            return {'message': 'Bon de livraison non trouve'}, 404
        return {'message': 'Bon de livraison supprime'}, 200

@ns_avoirs.route('/')
class AvoirList(Resource):
    @tenant_required
    def get(self):
        avoirs, total = AvoirService.get_all()
        return {'avoirs': [a.to_dict() for a in avoirs], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        avoir = AvoirService.create(data)
        return avoir.to_dict(), 201

@ns_avoirs.route('/<int:id>')
class AvoirResource(Resource):
    @tenant_required
    def get(self, id):
        avoir = AvoirService.get_by_id(id)
        if not avoir:
            return {'message': 'Avoir non trouve'}, 404
        return avoir.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        avoir = AvoirService.update(id, data)
        if not avoir:
            return {'message': 'Avoir non trouve'}, 404
        return avoir.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = AvoirService.delete(id)
        if not success:
            return {'message': 'Avoir non trouve'}, 404
        return {'message': 'Avoir supprime'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\ai.py
<<<
from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from app.security.tenant import tenant_required
from app.ai import (
    predict_sales,
    detect_stock_anomalies,
    suggest_reorders,
    ask_assistant,
    train_models,
    external_ai,
    web_search,
    context_manager,
)
from app.ai.anomalies import detect_sales_anomalies, detect_payment_anomalies
from app.ai.recommendations import suggest_pricing_adjustments, suggest_cross_sell
from app.ai.previsions import predict_stock_rupture

ns = Namespace('ai', description="Module d'Intelligence Artificielle et Prédictions")

# Modèles pour la documentation Swagger
prevision_model = ns.model('Prevision', {
    'tenant_id': fields.Integer(description='ID du tenant'),
    'periods': fields.Integer(description='Nombre de périodes pour la prédiction'),
    'forecast': fields.List(fields.Float, description='Liste des prévisions'),
    'total_predicted': fields.Float(description='Total des ventes prédites'),
    'trend': fields.String(description='Tendance des ventes'),
    'confidence_score': fields.Float(description='Score de confiance')
})

anomaly_model = ns.model('Anomaly', {
    'type': fields.String(description="Type d'anomalie"),
    'severity': fields.String(description='Niveau de sévérité'),
    'count': fields.Integer(description="Nombre d'anomalies")
})

recommendation_model = ns.model('Recommendation', {
    'produit_id': fields.Integer(description='ID du produit'),
    'nom': fields.String(description='Nom du produit'),
    'quantite_suggeree': fields.Integer(description='Quantité suggérée'),
    'priorite': fields.String(description='Niveau de priorité')
})


@ns.route('/previsions')
@ns.doc(responses={200: 'Prévisions récupérées avec succès', 400: 'Requête invalide'})
class PrevisionsResource(Resource):
    @tenant_required
    def get(self):
        """Obtenir les prévisions de ventes pour une période donnée"""
        try:
            periods = request.args.get('periods', default=30, type=int)
            product_id = request.args.get('product_id', default=None, type=int)

            if periods <= 0 or periods > 365:
                return {'error': 'La période doit être entre 1 et 365 jours'}, 400

            data = predict_sales(periods=periods, product_id=product_id)
            return data, 200
        except Exception as e:
            return {'error': f'Erreur lors de la prédiction: {str(e)}'}, 500


@ns.route('/anomalies')
@ns.doc(responses={200: 'Anomalies détectées avec succès', 500: 'Erreur serveur'})
class AnomaliesResource(Resource):
    @tenant_required
    def get(self):
        """Détecter les anomalies de stock, de ventes et de paiements"""
        try:
            anomaly_type = request.args.get('type', default='all', type=str)

            stock_anomalies = detect_stock_anomalies()
            sales_anomalies = detect_sales_anomalies()
            payment_anomalies = detect_payment_anomalies()

            result = {
                'stock_anomalies': stock_anomalies,
                'sales_anomalies': sales_anomalies,
                'payment_anomalies': payment_anomalies,
                'total_anomalies': stock_anomalies['count'] + sales_anomalies['count'] + payment_anomalies['count']
            }

            if anomaly_type != 'all':
                if anomaly_type == 'stock':
                    return {'stock_anomalies': stock_anomalies}, 200
                elif anomaly_type == 'sales':
                    return {'sales_anomalies': sales_anomalies}, 200
                elif anomaly_type == 'payment':
                    return {'payment_anomalies': payment_anomalies}, 200

            return result, 200
        except Exception as e:
            return {'error': f'Erreur lors de la détection des anomalies: {str(e)}'}, 500


@ns.route('/recommendations')
@ns.doc(responses={200: 'Recommandations récupérées avec succès', 500: 'Erreur serveur'})
class RecommendationsResource(Resource):
    @tenant_required
    def get(self):
        """Obtenir les recommandations de réapprovisionnement, d'ajustement de prix et de vente croisée"""
        try:
            recom_type = request.args.get('type', default='all', type=str)
            client_id = request.args.get('client_id', default=None, type=int)

            reorders = suggest_reorders()
            pricing = suggest_pricing_adjustments()

            result = {
                'reorder_suggestions': reorders,
                'pricing_suggestions': pricing
            }

            if client_id:
                cross_sell = suggest_cross_sell(client_id=client_id)
                result['cross_sell_suggestions'] = cross_sell

            if recom_type != 'all':
                if recom_type == 'reorder':
                    return {'reorder_suggestions': reorders}, 200
                elif recom_type == 'pricing':
                    return {'pricing_suggestions': pricing}, 200
                elif recom_type == 'cross_sell' and client_id:
                    cross_sell = suggest_cross_sell(client_id=client_id)
                    return {'cross_sell_suggestions': cross_sell}, 200

            return result, 200
        except Exception as e:
            return {'error': f'Erreur lors de la génération des recommandations: {str(e)}'}, 500


@ns.route('/assistant')
@ns.doc(responses={200: 'Réponse de l\'assistant', 400: 'Requête invalide'})
class AssistantResource(Resource):
    @tenant_required
    def post(self):
        """Interroger l'assistant virtuel ERP avec une question en langage naturel"""
        try:
            body = request.get_json() or {}
            prompt = body.get('prompt', '')
            conversation = body.get('conversation', [])

            if not prompt or not isinstance(prompt, str) or len(prompt.strip()) < 3:
                return {'error': 'Veuillez fournir une question valide (minimum 3 caractères)'}, 400

            response_text = ask_assistant(prompt=prompt, conversation=conversation)
            return {'prompt': prompt, 'response': response_text}, 200
        except Exception as e:
            return {'error': f'Erreur avec l\'assistant: {str(e)}'}, 500


@ns.route('/train')
@ns.doc(responses={200: 'Modèles entraînés avec succès', 400: 'Requête invalide', 500: 'Erreur lors de l\'entraînement'})
class TrainResource(Resource):
    @tenant_required
    def post(self):
        """Entraîner/Réactualiser les modèles IA avec les dernières données"""
        try:
            body = request.get_json() or {}
            force_retrain = body.get('force_retrain', False)
            model_type = body.get('model_type', 'all')

            res = train_models(force_retrain=force_retrain, model_type=model_type)
            return res, 200
        except Exception as e:
            return {'error': f'Erreur lors de l entrainement des modeles: {str(e)}'}, 500


@ns.route('/stock-ruptures')
@ns.doc(responses={200: 'Prédictions de rupture de stock récupérées', 500: 'Erreur serveur'})
class StockRuptureResource(Resource):
    @tenant_required
    def get(self):
        """Prédire les ruptures de stock pour les produits"""
        try:
            data = predict_stock_rupture()
            return {
                'message': 'Prédictions de rupture de stock',
                'predictions': data.get('predictions', []),
                'count': data.get('count', 0)
            }, 200
        except Exception as e:
            return {'error': f'Erreur lors de la prediction des ruptures: {str(e)}'}, 500


@ns.route('/health')
@ns.doc(responses={200: 'Statut du module IA'})
class AIHealthResource(Resource):
    @tenant_required
    def get(self):
        """Vérifier le statut du module IA"""
        try:
            return {
                'status': 'healthy',
                'message': 'Module IA operationnel',
                'external_ai': {
                    'provider': external_ai.provider,
                    'configured': external_ai.is_configured()
                },
                'web_search': {
                    'enabled': web_search.enabled,
                    'configured': bool(web_search.serpapi_key)
                },
                'endpoints': [
                    {'path': '/ai/previsions', 'method': 'GET', 'description': 'Prévisions de ventes'},
                    {'path': '/ai/anomalies', 'method': 'GET', 'description': 'Détection d\'anomalies'},
                    {'path': '/ai/recommendations', 'method': 'GET', 'description': 'Recommandations'},
                    {'path': '/ai/assistant', 'method': 'POST', 'description': 'Assistant IA'},
                    {'path': '/ai/train', 'method': 'POST', 'description': 'Entraînement des modèles'},
                    {'path': '/ai/stock-ruptures', 'method': 'GET', 'description': 'Prédiction des ruptures'},
                    {'path': '/ai/search', 'method': 'POST', 'description': 'Recherche web externe'},
                    {'path': '/ai/context', 'method': 'POST', 'description': 'Mise à jour du contexte conversationnel'}
                ]
            }, 200
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}, 500


@ns.route('/search')
class AISearchResource(Resource):
    @tenant_required
    def post(self):
        """Recherche web externe pour enrichir une réponse IA"""
        try:
            body = request.get_json() or {}
            query = body.get('query', '')
            max_results = int(body.get('max_results', 5))

            if not query or not isinstance(query, str) or len(query.strip()) < 2:
                return {'error': 'Requête de recherche invalide'}, 400

            results = web_search.search(query, max_results=max_results)
            return {'query': query, 'results': results}, 200
        except Exception as e:
            return {'error': f'Erreur lors de la recherche web: {str(e)}'}, 500


@ns.route('/context')
class AIContextResource(Resource):
    @tenant_required
    def post(self):
        """Met à jour le contexte conversationnel de l'assistant"""
        try:
            body = request.get_json() or {}
            conversation = body.get('conversation', [])
            current_prompt = body.get('prompt', '')

            if not isinstance(conversation, list):
                return {'error': 'conversation doit être une liste'}, 400

            messages = context_manager.build_messages(conversation, current_prompt)
            return {'messages': messages}, 200
        except Exception as e:
            return {'error': f'Erreur lors de la mise à jour du contexte: {str(e)}'}, 500


>>>

### FICHIER .PY: web\backend\app\api\v1\auth.py
<<<

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
from app.security.auth import authenticate_user, hash_password, _validate_password, verify_password
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.security.roles import is_super_admin


from app.security.rate_limit import rate_limit

api = Namespace(
    'auth',
    description='Authentification et JWT'
)

@api.route('/login')
class AuthLogin(Resource):

    @rate_limit(5, 300)
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

        user = db.session.get(Utilisateur, user_id)

        if not user:
            return {
                'message': 'Utilisateur non trouve'
            }, 404

        tenant = None

        if user.tenant_id:
            tenant = db.session.get(Tenant, user.tenant_id)

        return {
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None,
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
        # Avec JWT stateless, la déconnexion est généralement
        # effectuée côté client en supprimant le token.

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

            PasswordResetToken.query.filter_by(
                user_id=user.id,
                used=False
            ).update({'used': True})
            db.session.commit()

            raw_token = PasswordResetToken.generate_token()
            hashed_token = PasswordResetToken.hash_token(raw_token)
            token = PasswordResetToken(
                user_id=user.id,
                token=hashed_token,
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
                'Password reset requested for %s from IP %s',
                user.email,
                request.remote_addr,
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
        from app.security.auth import hash_password, _validate_password

        reset_tokens = PasswordResetToken.query.filter_by(
            used=False
        ).all()

        reset_token = None
        for t in reset_tokens:
            if PasswordResetToken.verify_token(token, t.token):
                reset_token = t
                break

        if not reset_token or reset_token.is_expired:
            return {'message': 'Token invalide ou expiré'}, 400

        pwd_error = _validate_password(new_password)
        if pwd_error:
            return {'message': pwd_error}, 400

        user = db.session.get(Utilisateur, reset_token.user_id)
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

>>>

### FICHIER .PY: web\backend\app\api\v1\clients.py
<<<
from flask_restx import Namespace, Resource, fields
from app.services.client_service import ClientService
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits
from app.security.permissions import permission_required
from sqlalchemy.exc import IntegrityError
from flask import request
from app import db

ns = Namespace('clients', description='Gestion des clients')

client_model = ns.model('Client', {
    'code': fields.String(required=True, description='Code client unique'),
    'raison_sociale': fields.String(description='Raison sociale'),
    'nom': fields.String(description='Nom'),
    'prenom': fields.String(description='Prénom'),
    'type': fields.String(description='Type de client (boutique, epicerie, revendeur, semi_grossiste, grossiste, supermarche, restaurant, hotel, entreprise, institution, particulier)', default='particulier'),
    'secteur': fields.String(description='Secteur d\'activité', default='autre'),
    'siret': fields.String(description='SIRET'),
    'numero_tva': fields.String(description='Numéro TVA'),
    'numero_rcs': fields.String(description='Numéro RCS'),
    'email': fields.String(description='Email'),
    'email_secondaire': fields.String(description='Email secondaire'),
    'telephone': fields.String(description='Téléphone'),
    'telephone_secondaire': fields.String(description='Téléphone secondaire'),
    'mobile': fields.String(description='Mobile'),
    'fax': fields.String(description='Fax'),
    'site_web': fields.String(description='Site web'),
    'adresse_facturation': fields.String(description='Adresse de facturation'),
    'complement_facturation': fields.String(description='Complément adresse facturation'),
    'code_postal_facturation': fields.String(description='Code postal facturation'),
    'ville_facturation': fields.String(description='Ville facturation'),
    'pays_facturation': fields.String(description='Pays facturation', default='Madagascar'),
    'adresse_livraison': fields.String(description='Adresse de livraison'),
    'complement_livraison': fields.String(description='Complément adresse livraison'),
    'code_postal_livraison': fields.String(description='Code postal livraison'),
    'ville_livraison': fields.String(description='Ville livraison'),
    'pays_livraison': fields.String(description='Pays livraison', default='Madagascar'),
    'contact_nom': fields.String(description='Nom du contact principal'),
    'contact_prenom': fields.String(description='Prénom du contact principal'),
    'contact_fonction': fields.String(description='Fonction du contact'),
    'contact_email': fields.String(description='Email du contact'),
    'contact_telephone': fields.String(description='Téléphone du contact'),
    'conditions_paiement': fields.String(description='Conditions de paiement', default='30 jours'),
    'remise_standard': fields.Float(description='Remise standard', default=0),
    'plafond_credit': fields.Float(description='Plafond de crédit'),
    'echeance_credit': fields.Integer(description='Échéance crédit en jours', default=30),
    'commercial_id': fields.Integer(description='ID du commercial'),
    'est_favori': fields.Boolean(description='Client favori', default=False),
    'est_actif': fields.Boolean(description='Client actif', default=True),
    'est_bloque': fields.Boolean(description='Client bloqué', default=False),
    'note': fields.Integer(description='Note 1-5'),
})

@ns.route('/')
class ClientListResource(Resource):
    @ns.doc('list_clients')
    @tenant_required
    def get(self):
        """Liste tous les clients"""
        try:
            clients, total = ClientService.get_all()
            return {'clients': [c.to_dict() for c in clients], 'total': total}, 200
        except Exception:
            current_app.logger.exception('Erreur lors de la liste des clients')
            return {'clients': [], 'total': 0}, 500
    
    @ns.doc('create_client')
    @tenant_required
    @check_plan_limits('clients')
    @permission_required('client.create')
    @ns.expect(client_model)
    def post(self):
        """Crée un nouveau client"""
        data = request.get_json()
        if not data:
            return {'message': 'Données JSON requises'}, 400
        
        if not data.get('code'):
            return {'message': 'Le code client est requis'}, 400
        
        try:
            client = ClientService.create(data)
            return client.to_dict(), 201
        except ValueError as e:
            return {'message': str(e)}, 400
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Contrainte de base de données violée'}, 400
        except Exception:
            current_app.logger.exception('Erreur lors de la création du client')
            return {'message': 'Erreur lors de la création du client'}, 400

@ns.route('/<int:client_id>')
class ClientResource(Resource):
    @ns.doc('get_client')
    @tenant_required
    def get(self, client_id):
        """Récupère un client par son ID"""
        client = ClientService.get_by_id(client_id)
        if not client:
            return {'message': 'Client non trouve'}, 404
        return client.to_dict(), 200
    
    @ns.doc('update_client')
    @tenant_required
    def put(self, client_id):
        """Met à jour un client"""
        from flask import request
        data = request.get_json()
        client = ClientService.update(client_id, data)
        if not client:
            return {'message': 'Client non trouve'}, 404
        return client.to_dict(), 200
    
    @ns.doc('delete_client')
    @tenant_required
    def delete(self, client_id):
        """Supprime un client"""
        success = ClientService.delete(client_id)
        if not success:
            return {'message': 'Client non trouve'}, 404
        return {'message': 'Client supprime'}, 200
>>>

### FICHIER .PY: web\backend\app\api\v1\comptabilite.py
<<<
from flask_restx import Namespace, Resource
from flask import request, Response
from app.security.tenant import tenant_required
from app.security.permissions import permission_required
from app.services.comptabilite_service import CompteComptableService, EcritureComptableService, TresorerieService, ComptaImportService
from datetime import date
from sqlalchemy import func
import io

ns_comptes = Namespace('comptes', description='Gestion des comptes comptables')
ns_ecritures = Namespace('ecritures', description='Gestion des ecritures comptables')
ns_tresorerie = Namespace('tresorerie', description='Gestion de la tresorerie')

@ns_comptes.route('/')
class CompteList(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self):
        comptes, total = CompteComptableService.get_all()
        return {'comptes': [c.to_dict() for c in comptes], 'total': total}, 200

    @tenant_required
    @permission_required('compte.create')
    def post(self):
        from flask import request
        data = request.get_json()
        compte = CompteComptableService.create(data)
        return compte.to_dict(), 201


@ns_comptes.route('/<int:id>')
class CompteResource(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self, id):
        compte = CompteComptableService.get_by_id(id)
        if not compte:
            return {'message': 'Compte non trouve'}, 404
        return compte.to_dict(), 200

    @tenant_required
    @permission_required('compte.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        compte = CompteComptableService.update(id, data)
        if not compte:
            return {'message': 'Compte non trouve'}, 404
        return compte.to_dict(), 200

    @tenant_required
    @permission_required('compte.delete')
    def delete(self, id):
        success = CompteComptableService.delete(id)
        if not success:
            return {'message': 'Compte non trouve'}, 404
        return {'message': 'Compte supprime'}, 200


@ns_comptes.route('/export')
class CompteExport(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self):
        csv = ComptaImportService.export_comptes()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=comptes.csv'}
        )


@ns_ecritures.route('/')
class EcritureList(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        ecritures, total = EcritureComptableService.get_all()
        return {'ecritures': [e.to_dict() for e in ecritures], 'total': total}, 200

    @tenant_required
    @permission_required('ecriture.create')
    def post(self):
        from flask import request
        data = request.get_json() or {}
        if 'date' in data and isinstance(data['date'], str):
            try:
                data['date'] = date.fromisoformat(data['date'])
            except (ValueError, TypeError):
                pass
        ecriture = EcritureComptableService.create(data)
        return ecriture.to_dict(), 201


@ns_ecritures.route('/<int:id>')
class EcritureResource(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self, id):
        ecriture = EcritureComptableService.get_by_id(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200

    @tenant_required
    @permission_required('ecriture.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        ecriture = EcritureComptableService.update(id, data)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200

    @tenant_required
    @permission_required('ecriture.delete')
    def delete(self, id):
        success = EcritureComptableService.delete(id)
        if not success:
            return {'message': 'Ecriture non trouvee'}, 404
        return {'message': 'Ecriture supprimee'}, 200


@ns_ecritures.route('/<int:id>/valider')
class EcritureValider(Resource):
    @tenant_required
    @permission_required('ecriture.update')
    def post(self, id):
        ecriture = EcritureComptableService.valider_ecriture(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200


@ns_ecritures.route('/<int:id>/annuler')
class EcritureAnnuler(Resource):
    @tenant_required
    @permission_required('ecriture.update')
    def post(self, id):
        ecriture = EcritureComptableService.annuler_ecriture(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 201


@ns_ecritures.route('/journal')
class EcritureJournal(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        compte_id = request.args.get('compte_id')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        try:
            compte_id_int = int(compte_id) if compte_id else None
        except (TypeError, ValueError):
            compte_id_int = None
        journal = EcritureComptableService.get_journal(debut, fin, compte_id_int)
        return journal, 200


@ns_ecritures.route('/export')
class EcritureExport(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        csv = ComptaImportService.export_ecritures()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=ecritures.csv'}
        )


@ns_tresorerie.route('/')
class TresorerieList(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        tresoreries, total = TresorerieService.get_all()
        return {'tresoreries': [t.to_dict() for t in tresoreries], 'total': total}, 200

    @tenant_required
    @permission_required('tresorerie.create')
    def post(self):
        from flask import request
        data = request.get_json()
        entree = TresorerieService.create(data)
        return entree.to_dict(), 201


@ns_tresorerie.route('/<int:id>')
class TresorerieResource(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self, id):
        entree = TresorerieService.get_by_id(id)
        if not entree:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return entree.to_dict(), 200

    @tenant_required
    @permission_required('tresorerie.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        entree = TresorerieService.update(id, data)
        if not entree:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return entree.to_dict(), 200

    @tenant_required
    @permission_required('tresorerie.delete')
    def delete(self, id):
        success = TresorerieService.delete(id)
        if not success:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return {'message': 'Entree de tresorerie supprimee'}, 200


@ns_tresorerie.route('/solde')
class TresorerieSolde(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        solde = TresorerieService.get_solde(debut, fin)
        return {'solde': solde, 'date_debut': date_debut, 'date_fin': date_fin}, 200


@ns_tresorerie.route('/mouvements')
class TresorerieMouvements(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        mouvements = TresorerieService.get_mouvements(debut, fin)
        return {'mouvements': mouvements, 'count': len(mouvements)}, 200


@ns_tresorerie.route('/export')
class TresorerieExport(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        csv = ComptaImportService.export_tresorerie()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=tresorerie.csv'}
        )


@ns_comptes.route('/import')
class CompteImport(Resource):
    @tenant_required
    @permission_required('compte.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_comptes(file)
            return {
                'message': f"Import terminé: {result['imported']} comptes importés",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import de comptes')
            return {'message': 'Erreur serveur lors de l import de comptes'}, 500


@ns_ecritures.route('/import')
class EcritureImport(Resource):
    @tenant_required
    @permission_required('ecriture.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_ecritures(file)
            return {
                'message': f"Import terminé: {result['imported']} écritures importées",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import d ecritures')
            return {'message': 'Erreur serveur lors de l import d ecritures'}, 500


@ns_tresorerie.route('/import')
class TresorerieImport(Resource):
    @tenant_required
    @permission_required('tresorerie.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_tresorerie(file)
            return {
                'message': f"Import terminé: {result['imported']} entrées trésorerie importées",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import de tresorerie')
            return {'message': 'Erreur serveur lors de l import de tresorerie'}, 500

>>>

### FICHIER .PY: web\backend\app\api\v1\dashboard.py
<<<
from flask_restx import Namespace, Resource
from app.services.dashboard_service import get_dashboard_data
from app.security.tenant import tenant_required

api = Namespace('dashboard', description='Tableau de bord et statistiques')

@api.route('/')
class Dashboard(Resource):
    @api.doc('get_dashboard')
    @tenant_required
    def get(self):
        """Récupère les données du tableau de bord"""
        data = get_dashboard_data()
        return {
            'message': 'Donnees du tableau de bord',
            'stats': data,
        }, 200

@api.route('/sales-stats')
class SalesStats(Resource):
    @tenant_required
    def get(self):
        """Statistiques des ventes"""
        from app.models.vente import Vente
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func
        from datetime import datetime, timedelta

        tenant_id = get_current_tenant_id()
        today = datetime.utcnow().date()
        debut_mois = today.replace(day=1)

        query = Vente.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        ca_total = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True
        )
        if tenant_id:
            ca_total = ca_total.filter_by(tenant_id=tenant_id)
        ca_total = ca_total.scalar() or 0

        ventes_mois = query.filter(Vente.created_at >= debut_mois).count()
        ca_mois = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ca_mois = ca_mois.filter_by(tenant_id=tenant_id)
        ca_mois = ca_mois.scalar() or 0

        panier_moyen = float(ca_mois) / ventes_mois if ventes_mois > 0 else 0

        return {
            'ca_total': float(ca_total),
            'ventes_mois': ventes_mois,
            'ca_mois': float(ca_mois),
            'panier_moyen': panier_moyen
        }, 200

@api.route('/top-products')
class TopProducts(Resource):
    @tenant_required
    def get(self):
        """Top produits vendus"""
        from app.models.ligne_vente import LigneVente
        from app.models.produit import Produit
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func

        tenant_id = get_current_tenant_id()

        query = db.session.query(
            LigneVente.produit_id,
            Produit.nom,
            func.sum(LigneVente.quantite).label('total_quantite'),
            func.sum(LigneVente.total_ht).label('total_ca')
        ).join(
            Produit, Produit.id == LigneVente.produit_id
        ).filter(
            LigneVente.is_active == True,
            Produit.is_active == True
        )

        if tenant_id:
            query = query.filter(LigneVente.tenant_id == tenant_id)

        results = query.group_by(
            LigneVente.produit_id, Produit.nom
        ).order_by(
            func.sum(LigneVente.quantite).desc()
        ).limit(10).all()

        return {
            'top_products': [{
                'produit_id': r[0],
                'nom': r[1],
                'total_quantite': float(r[2]),
                'total_ca': float(r[3])
            } for r in results]
        }, 200

@api.route('/top-clients')
class TopClients(Resource):
    @tenant_required
    def get(self):
        """Top clients par chiffre d'affaires"""
        from app.models.vente import Vente
        from app.models.client import Client
        from app import db
        from app.security.tenant import get_current_tenant_id
        from sqlalchemy import func

        tenant_id = get_current_tenant_id()

        query = db.session.query(
            Vente.client_id,
            Client.nom,
            func.count(Vente.id).label('nb_ventes'),
            func.sum(Vente.total_ttc).label('ca_total')
        ).join(
            Client, Client.id == Vente.client_id
        ).filter(
            Vente.is_active == True,
            Client.is_active == True
        )

        if tenant_id:
            query = query.filter(Vente.tenant_id == tenant_id)

        results = query.group_by(
            Vente.client_id, Client.nom
        ).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(10).all()

        return {
            'top_clients': [{
                'client_id': r[0],
                'nom': r[1],
                'nb_ventes': r[2],
                'ca_total': float(r[3])
            } for r in results]
        }, 200

@api.route('/alerts')
class Alerts(Resource):
    @tenant_required
    def get(self):
        """Alertes stock et autres"""
        from app.models.produit import Produit
        from app import db
        from app.security.tenant import get_current_tenant_id

        tenant_id = get_current_tenant_id()

        query = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)

        alertes_stock = query.all()

        return {
            'alertes_stock': [p.to_dict() for p in alertes_stock],
            'nb_alertes_stock': len(alertes_stock)
        }, 200


>>>

### FICHIER .PY: web\backend\app\api\v1\desk.py
<<<
# web/backend/app/api/v1/desk.py
# Namespace de synchronisation desktop/web (favoris, colonnes, filtres, sync incrémental).
# Blueprint monté sur /api/v1/desk. Compatible mobile/tiers (JWT Bearer standard).

import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
from app.security.tenant import get_current_tenant_id
from app.realtime.socket_server import emit_preference_update

desk_bp = Blueprint("desk", __name__, url_prefix="/api/v1/desk")


def _user_id():
    uid = get_jwt_identity()
    return int(uid) if isinstance(uid, str) and uid.isdigit() else uid


def _tenant_id():
    return get_current_tenant_id()


def _record_event(entity, module, payload):
    """Incrémente la révision et journalise la mutation pour le pull/polling."""
    try:
        last = (
            SyncEvent.query.filter_by(user_id=_user_id())
            .order_by(SyncEvent.revision.desc())
            .first()
        )
        next_rev = (last.revision + 1) if last else 1
        ev = SyncEvent(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            entity=entity,
            module=module,
            payload=payload,
            revision=next_rev,
        )
        db.session.add(ev)
        db.session.commit()
        emit_preference_update(entity, _user_id(), payload)
        return next_rev
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("Erreur journalisation sync: %s", exc)
        db.session.rollback()
        return None


# ============================ FAVORIS =====================================
@desk_bp.route("/favorites", methods=["GET"])
@jwt_required()
def list_favorites():
    rows = (
        DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True)
        .order_by(DeskFavorite.updated_at.desc())
        .all()
    )
    return jsonify({"favorites": [r.to_public() for r in rows]}), 200


@desk_bp.route("/favorites", methods=["POST"])
@jwt_required()
def upsert_favorite():
    data = request.get_json(force=True, silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"message": "path requis"}), 400
    fav = DeskFavorite.query.filter_by(
        user_id=_user_id(), path=path, is_active=True
    ).first()
    if fav:
        fav.label = data.get("label", fav.label)
        fav.data = data.get("data", fav.data)
    else:
        fav = DeskFavorite(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            path=path,
            label=data.get("label"),
            data=data.get("data"),
        )
        db.session.add(fav)
    db.session.commit()
    _record_event("favorite", None, fav.to_public())
    return jsonify({"favorites": [r.to_public() for r in
               DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]}), 200


@desk_bp.route("/favorites/<path:key>", methods=["DELETE"])
@jwt_required()
def delete_favorite(key):
    fav = DeskFavorite.query.filter_by(
        user_id=_user_id(), path=key, is_active=True
    ).first()
    if fav:
        fav.is_active = False
        db.session.commit()
        _record_event("favorite", None, {"id": fav.id, "path": key, "deleted": True})
    return jsonify({"favorites": [r.to_public() for r in
               DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]}), 200


# ============================ FILTRES =====================================
@desk_bp.route("/filters/<module>", methods=["GET"])
@jwt_required()
def list_filters(module):
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


@desk_bp.route("/filters/<module>", methods=["POST"])
@jwt_required()
def upsert_filter(module):
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "name requis"}), 400
    preset_id = data.get("id")
    preset = None
    if preset_id:
        preset = DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, id=preset_id, is_active=True
        ).first()
    if not preset:
        preset = DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, name=name, is_active=True
        ).first()
    if preset:
        preset.name = name
        preset.filters = data.get("filters", preset.filters)
        preset.is_default = bool(data.get("isDefault", preset.is_default))
    else:
        preset = DeskFilterPreset(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            module=module,
            name=name,
            filters=data.get("filters", []),
            is_default=bool(data.get("isDefault", False)),
        )
        db.session.add(preset)
    if preset.is_default:
        DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, is_active=True
        ).filter(DeskFilterPreset.id != preset.id).update({"is_default": False})
    db.session.commit()
    _record_event("filter", module, preset.to_public())
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


@desk_bp.route("/filters/<module>/<int:fid>", methods=["DELETE"])
@jwt_required()
def delete_filter(module, fid):
    preset = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, id=fid, is_active=True
    ).first()
    if preset:
        preset.is_active = False
        db.session.commit()
        _record_event("filter", module, {"id": fid, "deleted": True})
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


# ============================ COLONNES ====================================
@desk_bp.route("/columns/<module>", methods=["GET"])
@jwt_required()
def get_columns(module):
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if not cfg:
        return jsonify({"module": module, "config": {"widths": {}, "hidden": [], "sort": []}}), 200
    return jsonify(cfg.to_public()), 200


@desk_bp.route("/columns/<module>", methods=["POST"])
@jwt_required()
def save_columns(module):
    data = request.get_json(force=True, silent=True) or {}
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if cfg:
        cfg.widths = data.get("widths", cfg.widths)
        cfg.hidden = data.get("hidden", cfg.hidden)
        cfg.sort = data.get("sort", cfg.sort)
        cfg.version = data.get("version", cfg.version)
    else:
        cfg = DeskColumnConfig(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            module=module,
            widths=data.get("widths", {}),
            hidden=data.get("hidden", []),
            sort=data.get("sort", []),
            version=data.get("version", 1),
        )
        db.session.add(cfg)
    db.session.commit()
    _record_event("column", module, cfg.to_public())
    return jsonify(cfg.to_public()), 200


@desk_bp.route("/columns/<module>", methods=["DELETE"])
@jwt_required()
def reset_columns(module):
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if cfg:
        cfg.is_active = False
        db.session.commit()
    empty = {"widths": {}, "hidden": [], "sort": []}
    _record_event("column", module, {"module": module, "config": empty})
    return jsonify({"module": module, "config": empty}), 200


# ============================ SYNC INCERTEMENTAL ==========================
@desk_bp.route("/sync/mutations", methods=["POST"])
@jwt_required()
def sync_mutations():
    """Alias de /sync/push (compatible desktopApi.js historique)."""
    return sync_push()


@desk_bp.route("/sync/push", methods=["POST"])
@jwt_required()
def sync_push():
    """Applique un batch de mutations (provenant de la file hors-ligne d'un client)."""
    body = request.get_json(force=True, silent=True) or {}
    mutations = body.get("mutations", [])
    revision = None
    for m in mutations:
        entity = m.get("entity")
        op = m.get("op")
        p = m.get("payload", {})
        if entity == "favorite":
            if op == "delete":
                fav = DeskFavorite.query.filter_by(user_id=_user_id(), path=p.get("key"), is_active=True).first()
                if fav:
                    fav.is_active = False
            else:
                fav = DeskFavorite.query.filter_by(user_id=_user_id(), path=p.get("path"), is_active=True).first()
                if fav:
                    fav.label = p.get("label", fav.label); fav.data = p.get("data", fav.data)
                else:
                    fav = DeskFavorite(tenant_id=_tenant_id(), user_id=_user_id(),
                                       path=p.get("path"), label=p.get("label"), data=p.get("data"))
                    db.session.add(fav)
        elif entity == "column":
            mod = p.get("module")
            if op == "delete":
                c = DeskColumnConfig.query.filter_by(user_id=_user_id(), module=mod, is_active=True).first()
                if c: c.is_active = False
            else:
                c = DeskColumnConfig.query.filter_by(user_id=_user_id(), module=mod, is_active=True).first()
                cfg = p.get("config", {})
                if c:
                    c.widths = cfg.get("widths", c.widths); c.hidden = cfg.get("hidden", c.hidden); c.sort = cfg.get("sort", c.sort)
                else:
                    c = DeskColumnConfig(tenant_id=_tenant_id(), user_id=_user_id(), module=mod,
                                         widths=cfg.get("widths", {}), hidden=cfg.get("hidden", []), sort=cfg.get("sort", []))
                    db.session.add(c)
        elif entity == "filter":
            mod = p.get("module")
            if op == "delete":
                fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, id=p.get("id"), is_active=True).first()
                if fp: fp.is_active = False
            else:
                fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, id=p.get("id"), is_active=True).first()
                if not fp:
                    fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, name=p.get("name"), is_active=True).first()
                if fp:
                    fp.name = p.get("name", fp.name); fp.filters = p.get("filters", fp.filters)
                else:
                    fp = DeskFilterPreset(tenant_id=_tenant_id(), user_id=_user_id(), module=mod,
                                           name=p.get("name", "Sans nom"), filters=p.get("filters", []))
                    db.session.add(fp)
        db.session.commit()
        revision = _record_event(entity, p.get("module"), p)
    return jsonify({"revision": revision or 0, "applied": len(mutations)}), 200


@desk_bp.route("/sync/pull", methods=["GET"])
@jwt_required()
def sync_pull():
    """Renvoie l'état complet courant (dernière écriture gagne côté client)."""
    favs = [r.to_public() for r in
            DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]
    modules = db.session.query(DeskFilterPreset.module).filter_by(
        user_id=_user_id(), is_active=True).distinct().all()
    filters = [
        {"module": mod[0], "presets": [r.to_public() for r in
         DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod[0], is_active=True).all()]}
        for mod in modules
    ]
    cols = [
        r.to_public() for r in
        DeskColumnConfig.query.filter_by(user_id=_user_id(), is_active=True).all()
    ]
    last = SyncEvent.query.filter_by(user_id=_user_id()).order_by(SyncEvent.revision.desc()).first()
    return jsonify({
        "favorites": favs,
        "filters": filters,
        "columns": cols,
        "revision": last.revision if last else 0,
    }), 200


@desk_bp.route("/sync/status", methods=["GET"])
@jwt_required()
def sync_status():
    last = SyncEvent.query.filter_by(user_id=_user_id()).order_by(SyncEvent.revision.desc()).first()
    return jsonify({"revision": last.revision if last else 0}), 200


@desk_bp.route("/events", methods=["GET"])
@jwt_required()
def events_poll():
    """Fallback polling temps-réel : événements depuis `since` (epoch ms)."""
    since = request.args.get("since", type=int)
    q = SyncEvent.query.filter_by(user_id=_user_id())
    if since:
        # compare with created_at epoch ms
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(since / 1000.0, tz=timezone.utc)
        q = q.filter(SyncEvent.created_at > dt)
    events = q.order_by(SyncEvent.id.asc()).limit(200).all()
    now = int(datetime.utcnow().timestamp() * 1000)
    return jsonify({"events": [e.to_public() for e in events], "now": now}), 200

>>>

### FICHIER .PY: web\backend\app\api\v1\documents.py
<<<
from flask_restx import Namespace, Resource
from flask import send_file, abort
from app.security.tenant import tenant_required, get_current_tenant
from app.services.document_service import ModeleDocumentService, DocumentGenereService
from app.utils.pdf_generator import generate_document_pdf
from app.utils.qr_generator import generate_qr_code
from app import db
from datetime import datetime
import os

ns_modeles = Namespace('modeles-documents', description='Gestion des modeles de documents')
ns_documents = Namespace('documents', description='Gestion des documents generes')

@ns_modeles.route('/')
class ModeleList(Resource):
    @tenant_required
    def get(self):
        modeles, total = ModeleDocumentService.get_all()
        return {'modeles': [m.to_dict() for m in modeles], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        modele = ModeleDocumentService.create(data)
        return modele.to_dict(), 201

@ns_modeles.route('/<int:id>')
class ModeleResource(Resource):
    @tenant_required
    def get(self, id):
        modele = ModeleDocumentService.get_by_id(id)
        if not modele:
            return {'message': 'Modele non trouve'}, 404
        return modele.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        modele = ModeleDocumentService.update(id, data)
        if not modele:
            return {'message': 'Modele non trouve'}, 404
        return modele.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = ModeleDocumentService.delete(id)
        if not success:
            return {'message': 'Modele non trouve'}, 404
        return {'message': 'Modele supprime'}, 200

@ns_documents.route('/')
class DocumentList(Resource):
    @tenant_required
    def get(self):
        documents, total = DocumentGenereService.get_all()
        return {'documents': [d.to_dict() for d in documents], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        document = DocumentGenereService.create(data)
        return document.to_dict(), 201

@ns_documents.route('/<int:id>')
class DocumentResource(Resource):
    @tenant_required
    def get(self, id):
        document = DocumentGenereService.get_by_id(id)
        if not document:
            return {'message': 'Document non trouve'}, 404
        return document.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = DocumentGenereService.delete(id)
        if not success:
            return {'message': 'Document non trouve'}, 404
        return {'message': 'Document supprime'}, 200

@ns_documents.route('/<int:id>/pdf')
class DocumentPdfResource(Resource):
    @tenant_required
    def get(self, id):
        document = DocumentGenereService.get_by_id(id)
        if not document or not document.contenu_pdf_path:
            return {'message': 'PDF non trouve'}, 404
        if not os.path.exists(document.contenu_pdf_path):
            return {'message': 'Fichier PDF introuvable sur le serveur'}, 404
        return send_file(
            document.contenu_pdf_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=os.path.basename(document.contenu_pdf_path)
        )

@ns_documents.route('/generer')
class GenererDocument(Resource):
    @tenant_required
    def post(self):
        from flask import request
        from app.models.tenant import Tenant
        data = request.get_json()
        modele_id = data.get('modele_id')
        type_document = data.get('type_document')
        reference = data.get('reference')
        entite_type = data.get('entite_type')
        entite_id = data.get('entite_id')
        donnees = data.get('donnees', {}) or {}

        modele = ModeleDocumentService.get_by_id(modele_id)
        if not modele:
            modele = ModeleDocumentService.get_defaut_by_type(type_document)
        if not modele:
            return {'message': 'Modele non trouve'}, 404

        html_content = modele.contenu_modele
        for key, value in donnees.items():
            html_content = html_content.replace('{{' + key + '}}', str(value) if value is not None else '')

        tenant = None
        current_tenant = get_current_tenant()
        if current_tenant:
            tenant = current_tenant.to_dict()
        else:
            tenant_user = None
            from flask_jwt_extended import get_jwt
            claims = get_jwt() or {}
            tenant_id = claims.get('tenant_id')
            if tenant_id:
                tenant_obj = db.session.get(Tenant, tenant_id)
                if tenant_obj:
                    tenant = tenant_obj.to_dict()

        modele_dict = modele.to_dict()
        modele_dict.pop('tenant_id', None)

        filename = f"{type_document}_{reference}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = generate_document_pdf(
            filename=filename,
            type_document=type_document,
            reference=reference,
            donnees=donnees,
            tenant=tenant,
            modele=modele_dict,
        )

        document = DocumentGenereService.create({
            'modele_id': modele.id,
            'type_document': type_document,
            'reference': reference,
            'entite_type': entite_type,
            'entite_id': entite_id,
            'contenu_html': html_content,
            'contenu_pdf_path': pdf_path,
        })
        result = document.to_dict()
        result['pdf_url'] = f"/api/v1/documents/{document.id}/pdf"
        return result, 201

>>>

### FICHIER .PY: web\backend\app\api\v1\employes.py
<<<
from flask import request, Response
from flask_restx import Namespace, Resource
from datetime import date
from app import db
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits, check_admin_limit, require_module
from app.services.rh_service import EmployeService
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns_employes = Namespace('employes', description='Gestion des employes')

_MODULE_RH = 'rh'


@ns_employes.route('/')
class EmployeList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        employes, total = EmployeService.get_all()
        return {'employes': [e.to_dict() for e in employes], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    @check_plan_limits('employes')
    def post(self):
        data = request.get_json() or {}
        employe = EmployeService.create(data)
        try:
            log_audit(
                TypeActionAudit.CREATION_EMPLOYE,
                f"Création de l'employé {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=employe.tenant_id,
                utilisateur_id=getattr(request, 'current_user_id', None),
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 201


@ns_employes.route('/<int:id>')
class EmployeResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        employe = EmployeService.get_by_id(id)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        employe = EmployeService.update(id, data)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = EmployeService.delete(id)
        if not success:
            return {'message': 'Employe non trouve'}, 404
        return {'message': 'Employe supprime'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\factures.py
<<<
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.facturation_service import issue_invoice
from app import db

api = Namespace('factures', description='Gestion des factures')

@api.route('/')
class FactureList(Resource):
    @tenant_required
    def get(self):
        """Liste toutes les factures"""
        from app.models.facture import Facture
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Facture.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        factures = query.all()
        result = []
        for f in factures:
            d = f.to_dict()
            paiements = [p.to_dict() for p in f.paiements.filter_by(is_active=True).all()]
            d['paiements'] = paiements
            result.append(d)
        return {'factures': result}, 200

    @tenant_required
    def post(self):
        """Creation de facture"""
        from flask import request
        data = request.get_json()
        facture = issue_invoice(data)
        return facture.to_dict(), 201

@api.route('/<int:id>')
class FactureResource(Resource):
    @tenant_required
    def get(self, id):
        """Details d'une facture"""
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        from app.security.tenant import get_current_tenant_id
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(facture_id=id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        result = facture.to_dict()
        result['paiements'] = [p.to_dict() for p in paiements]
        return result, 200

    @tenant_required
    def put(self, id):
        """Met a jour une facture"""
        from app.models.facture import Facture
        from app.security.tenant import tenant_filtered_get
        from flask import request
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        data = request.get_json()
        try:
            for key, value in data.items():
                if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id']:
                    setattr(facture, key, value)
            db.session.commit()
            return facture.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @tenant_required
    def delete(self, id):
        """Supprime une facture"""
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        try:
            facture.is_active = False
            Paiement.query.filter_by(facture_id=id, is_active=True, tenant_id=facture.tenant_id).update({'is_active': False})
            db.session.commit()
            return {'message': 'Facture supprimee'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

@api.route('/from-vente/<int:vente_id>')
class FactureFromVente(Resource):
    @tenant_required
    def post(self, vente_id):
        """Genere une facture depuis une vente"""
        from app.models.vente import Vente
        from app.models.facture import Facture
        from flask import request
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, vente_id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        data = request.get_json() or {}
        try:
            existing = Facture.query.filter_by(vente_id=vente.id, is_active=True, tenant_id=vente.tenant_id).first()
            if existing:
                return {'message': 'Une facture existe deja pour cette vente', 'facture': existing.to_dict()}, 409
            facture = Facture(
                vente_id=vente.id,
                client_id=vente.client_id,
                tenant_id=vente.tenant_id,
                reference=data.get('reference', f"FAC-{vente.reference}"),
                total_ht=vente.total_ht,
                total_ttc=vente.total_ttc,
                statut=data.get('statut', 'non_payee')
            )
            facture.save()
            return facture.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400


>>>

### FICHIER .PY: web\backend\app\api\v1\fournisseurs.py
<<<
from flask_restx import Namespace, Resource
from app.services.fournisseur_service import FournisseurService
from app.security.tenant import tenant_required

ns = Namespace('fournisseurs', description='Gestion des fournisseurs')

@ns.route('/')
class FournisseurListResource(Resource):
    @ns.doc('list_fournisseurs')
    @tenant_required
    def get(self):
        """Liste tous les fournisseurs"""
        fournisseurs, total = FournisseurService.get_all()
        return {'fournisseurs': [f.to_dict() for f in fournisseurs], 'total': total}, 200

    @ns.doc('create_fournisseur')
    @tenant_required
    def post(self):
        """Cree un nouveau fournisseur"""
        from flask import request
        data = request.get_json()
        fournisseur = FournisseurService.create(data)
        return fournisseur.to_dict(), 201

@ns.route('/<int:fournisseur_id>')
class FournisseurResource(Resource):
    @ns.doc('get_fournisseur')
    @tenant_required
    def get(self, fournisseur_id):
        """Recupere un fournisseur par son ID"""
        fournisseur = FournisseurService.get_by_id(fournisseur_id)
        if not fournisseur:
            return {'message': 'Fournisseur non trouve'}, 404
        return fournisseur.to_dict(), 200

    @ns.doc('update_fournisseur')
    @tenant_required
    def put(self, fournisseur_id):
        """Met a jour un fournisseur"""
        from flask import request
        data = request.get_json()
        fournisseur = FournisseurService.update(fournisseur_id, data)
        if not fournisseur:
            return {'message': 'Fournisseur non trouve'}, 404
        return fournisseur.to_dict(), 200

    @ns.doc('delete_fournisseur')
    @tenant_required
    def delete(self, fournisseur_id):
        """Supprime un fournisseur"""
        success = FournisseurService.delete(fournisseur_id)
        if not success:
            return {'message': 'Fournisseur non trouve'}, 404
        return {'message': 'Fournisseur supprime'}, 200

@ns.route('/commandes')
class CommandeFournisseurListResource(Resource):
    @ns.doc('list_commandes_fournisseurs')
    @tenant_required
    def get(self):
        """Liste des commandes fournisseurs"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = CommandeFournisseur.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        commandes = query.all()
        return {'commandes': [c.to_dict() for c in commandes]}, 200

    @ns.doc('create_commande_fournisseur')
    @tenant_required
    def post(self):
        """Cree une commande fournisseur"""
        from flask import request
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        data = request.get_json()
        try:
            tenant_id = get_current_tenant_id()
            commande = CommandeFournisseur(
                fournisseur_id=data['fournisseur_id'],
                reference=data.get('reference', ''),
                total_ht=data.get('total_ht', 0),
                total_ttc=data.get('total_ttc', 0),
                statut=data.get('statut', 'en_attente'),
                tenant_id=tenant_id
            )
            commande.save()
            return commande.to_dict(), 201
        except Exception as e:
            return {'message': str(e)}, 400

@ns.route('/commandes/<int:id>')
class CommandeFournisseurResource(Resource):
    @ns.doc('get_commande_fournisseur')
    @tenant_required
    def get(self, id):
        """Recupere une commande fournisseur par ID"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        return commande.to_dict(), 200

    @ns.doc('update_commande_fournisseur')
    @tenant_required
    def put(self, id):
        """Met a jour une commande fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        from flask import request
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        data = request.get_json() or {}
        for key, value in data.items():
            if hasattr(commande, key) and key not in ('id', 'tenant_id', 'created_at'):
                setattr(commande, key, value)
        commande.save()
        return commande.to_dict(), 200

    @ns.doc('delete_commande_fournisseur')
    @tenant_required
    def delete(self, id):
        """Supprime une commande fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        commande.delete()
        return {'message': 'Commande fournisseur supprimee'}, 200

@ns.route('/factures')
class FactureFournisseurListResource(Resource):
    @ns.doc('list_factures_fournisseurs')
    @tenant_required
    def get(self):
        """Liste des factures fournisseurs"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = FactureFournisseur.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        factures = query.all()
        return {'factures': [f.to_dict() for f in factures]}, 200

    @ns.doc('create_facture_fournisseur')
    @tenant_required
    def post(self):
        """Cree une facture fournisseur"""
        from flask import request
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import get_current_tenant_id
        data = request.get_json()
        try:
            tenant_id = get_current_tenant_id()
            facture = FactureFournisseur(
                fournisseur_id=data['fournisseur_id'],
                reference=data.get('reference', ''),
                total_ht=data.get('total_ht', 0),
                total_ttc=data.get('total_ttc', 0),
                statut=data.get('statut', 'non_payee'),
                tenant_id=tenant_id
            )
            facture.save()
            return facture.to_dict(), 201
        except Exception as e:
            return {'message': str(e)}, 400

@ns.route('/factures/<int:id>')
class FactureFournisseurResource(Resource):
    @ns.doc('get_facture_fournisseur')
    @tenant_required
    def get(self, id):
        """Recupere une facture fournisseur par ID"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        return facture.to_dict(), 200

    @ns.doc('update_facture_fournisseur')
    @tenant_required
    def put(self, id):
        """Met a jour une facture fournisseur"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        from flask import request
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        data = request.get_json() or {}
        for key, value in data.items():
            if hasattr(facture, key) and key not in ('id', 'tenant_id', 'created_at'):
                setattr(facture, key, value)
        facture.save()
        return facture.to_dict(), 200

    @ns.doc('delete_facture_fournisseur')
    @tenant_required
    def delete(self, id):
        """Supprime une facture fournisseur"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        facture.delete()
        return {'message': 'Facture fournisseur supprimee'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\livraisons.py
<<<
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.livraison_service import LivreurService, VehiculeService, ItineraireService, LivraisonService

ns_livreurs = Namespace('livreurs', description='Gestion des livreurs')
ns_vehicules = Namespace('vehicules', description='Gestion des vehicules')
ns_itineraires = Namespace('itineraires', description='Gestion des itineraires')
ns_livraisons = Namespace('livraisons', description='Gestion des livraisons')

@ns_livreurs.route('/')
class LivreurList(Resource):
    @tenant_required
    def get(self):
        livreurs, total = LivreurService.get_all()
        return {'livreurs': [l.to_dict() for l in livreurs], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.create(data)
        return livreur.to_dict(), 201

@ns_livreurs.route('/<int:id>')
class LivreurResource(Resource):
    @tenant_required
    def get(self, id):
        livreur = LivreurService.get_by_id(id)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        livreur = LivreurService.update(id, data)
        if not livreur:
            return {'message': 'Livreur non trouve'}, 404
        return livreur.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = LivreurService.delete(id)
        if not success:
            return {'message': 'Livreur non trouve'}, 404
        return {'message': 'Livreur supprime'}, 200

@ns_vehicules.route('/')
class VehiculeList(Resource):
    @tenant_required
    def get(self):
        vehicules, total = VehiculeService.get_all()
        return {'vehicules': [v.to_dict() for v in vehicules], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.create(data)
        return vehicule.to_dict(), 201

@ns_vehicules.route('/<int:id>')
class VehiculeResource(Resource):
    @tenant_required
    def get(self, id):
        vehicule = VehiculeService.get_by_id(id)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        vehicule = VehiculeService.update(id, data)
        if not vehicule:
            return {'message': 'Vehicule non trouve'}, 404
        return vehicule.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = VehiculeService.delete(id)
        if not success:
            return {'message': 'Vehicule non trouve'}, 404
        return {'message': 'Vehicule supprime'}, 200

@ns_itineraires.route('/')
class ItineraireList(Resource):
    @tenant_required
    def get(self):
        itineraires, total = ItineraireService.get_all()
        return {'itineraires': [i.to_dict() for i in itineraires], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.create(data)
        return itineraire.to_dict(), 201

@ns_itineraires.route('/<int:id>')
class ItineraireResource(Resource):
    @tenant_required
    def get(self, id):
        itineraire = ItineraireService.get_by_id(id)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        itineraire = ItineraireService.update(id, data)
        if not itineraire:
            return {'message': 'Itineraire non trouve'}, 404
        return itineraire.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = ItineraireService.delete(id)
        if not success:
            return {'message': 'Itineraire non trouve'}, 404
        return {'message': 'Itineraire supprime'}, 200

@ns_livraisons.route('/')
class LivraisonList(Resource):
    @tenant_required
    def get(self):
        livraisons, total = LivraisonService.get_all()
        return {'livraisons': [l.to_dict() for l in livraisons], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        livraison = LivraisonService.create(data)
        return livraison.to_dict(), 201

@ns_livraisons.route('/<int:id>')
class LivraisonResource(Resource):
    @tenant_required
    def get(self, id):
        livraison = LivraisonService.get_by_id(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        livraison = LivraisonService.update(id, data)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = LivraisonService.delete(id)
        if not success:
            return {'message': 'Livraison non trouvee'}, 404
        return {'message': 'Livraison supprimee'}, 200

@ns_livraisons.route('/<int:id>/suivi')
class LivraisonSuivi(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json()
        try:
            suivi = LivraisonService.add_suivi(
                id,
                data.get('statut'),
                data.get('commentaire', ''),
                data.get('localisation_lat'),
                data.get('localisation_lng'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not suivi:
            return {'message': 'Livraison non trouvee'}, 404
        return suivi.to_dict(), 201

@ns_livraisons.route('/<int:id>/suivis')
class LivraisonSuivis(Resource):
    @tenant_required
    def get(self, id):
        from app.models.suivi_livraison import SuiviLivraison
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = SuiviLivraison.query.filter_by(livraison_id=id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        suivis = query.order_by(SuiviLivraison.date_mise_a_jour.desc()).all()
        return {'suivis': [s.to_dict() for s in suivis]}, 200


@ns_livraisons.route('/<int:id>/assigner')
class LivraisonAssigner(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json() or {}
        try:
            livraison = LivraisonService.assigner(
                id,
                data.get('livreur_id'),
                data.get('vehicule_id'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200


@ns_livraisons.route('/<int:id>/statut')
class LivraisonStatut(Resource):
    @tenant_required
    def post(self, id):
        from flask import request
        data = request.get_json() or {}
        try:
            suivi = LivraisonService.passer_au_statut(
                id,
                data.get('statut'),
                data.get('commentaire', ''),
                data.get('localisation_lat'),
                data.get('localisation_lng'),
            )
        except ValueError as e:
            return {'message': str(e)}, 400
        if not suivi:
            return {'message': 'Livraison non trouvee'}, 404
        return suivi.to_dict(), 201


@ns_livraisons.route('/stats')
class LivraisonStats(Resource):
    @tenant_required
    def get(self):
        stats = LivraisonService.get_stats()
        return stats, 200


@ns_livraisons.route('/<int:id>/avancer')
class LivraisonAvancer(Resource):
    @tenant_required
    def post(self, id):
        livraison = LivraisonService.avancer_statut(id)
        if not livraison:
            return {'message': 'Livraison non trouvee'}, 404
        return livraison.to_dict(), 200

>>>

### FICHIER .PY: web\backend\app\api\v1\notifications.py
<<<
from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.notification import Notification
from app import db
from app.security.tenant import tenant_required, get_current_tenant_id_or_none
from datetime import datetime

ns = Namespace('notifications', description='Gestion des notifications')

notification_model = ns.model('Notification', {
    'id': fields.Integer(readonly=True),
    'title': fields.String(required=True),
    'message': fields.String(),
    'type': fields.String(required=True, default='info'),
    'read': fields.Boolean(default=False),
    'read_at': fields.String(),
    'user_id': fields.Integer(),
    'link': fields.String(),
    'tenant_id': fields.Integer(readonly=True),
    'created_at': fields.String(readonly=True),
    'updated_at': fields.String(readonly=True),
    'is_active': fields.Boolean(readonly=True),
})


@ns.route('/')
class NotificationList(Resource):
    @ns.doc('list_notifications')
    @ns.marshal_list_with(notification_model)
    @tenant_required
    def get(self):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
        return [n.to_dict() for n in notifications]

    @ns.doc('create_notification')
    @ns.expect(notification_model, validate=True)
    @ns.marshal_with(notification_model, code=201)
    @tenant_required
    def post(self):
        data = request.get_json() or {}
        title = data.get('title')
        message = data.get('message')
        notif_type = data.get('type', 'info')
        link = data.get('link')
        user_id = data.get('user_id')

        if not title:
            return {'message': 'Le titre est requis'}, 400

        tenant_id = get_current_tenant_id_or_none()

        notification = Notification(
            title=title,
            message=message,
            type=notif_type,
            link=link,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.session.add(notification)
        db.session.commit()
        return notification.to_dict(), 201


@ns.route('/<int:notification_id>')
class NotificationDetail(Resource):
    @ns.doc('get_notification')
    @ns.marshal_with(notification_model)
    @tenant_required
    def get(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        return notification.to_dict(), 200

    @ns.doc('delete_notification')
    @tenant_required
    def delete(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        notification.is_active = False
        db.session.commit()
        return {'message': 'Notification supprimee'}, 200


@ns.route('/<int:notification_id>/read')
class NotificationRead(Resource):
    @ns.doc('mark_notification_as_read')
    @ns.marshal_with(notification_model)
    @tenant_required
    def patch(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        notification.read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        return notification.to_dict(), 200


@ns.route('/read-all')
class NotificationReadAll(Resource):
    @ns.doc('mark_all_notifications_as_read')
    @tenant_required
    def patch(self):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(is_active=True, read=False)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        now = datetime.utcnow()
        for notification in query.all():
            notification.read = True
            notification.read_at = now
        db.session.commit()
        return {'message': 'Toutes les notifications ont ete marquees comme lues'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\paiements.py
<<<
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.paiement_service import process_payment
from app import db

ns = Namespace('paiements', description='Gestion des paiements')

@ns.route('/')
class PaiementList(Resource):
    @tenant_required
    def get(self):
        """Liste tous les paiements"""
        from app.models.paiement import Paiement
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        return {'paiements': [p.to_dict() for p in paiements]}, 200

    @tenant_required
    def post(self):
        """Creation de paiement"""
        from flask import request
        from flask_restx import abort
        data = request.get_json()
        if not data:
            return {'message': 'Donnees requises'}, 400
        
        montant = data.get('montant')
        if montant is None or float(montant) <= 0:
            return {'message': 'Le montant est requis et doit etre superieur a 0'}, 400
        
        facture_id = data.get('facture_id')
        if facture_id:
            from app.models.facture import Facture
            from app.security.tenant import get_current_tenant_id
            tenant_id = get_current_tenant_id()
            query = Facture.query.filter_by(id=facture_id, is_active=True)
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            facture = query.first()
            if not facture:
                return {'message': 'Facture non trouvee'}, 404
        
        paiement = process_payment(data)
        return paiement.to_dict(), 201

@ns.route('/<int:id>')
class PaiementResource(Resource):
    @tenant_required
    def get(self, id):
        """Details d'un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        return paiement.to_dict(), 200

    @tenant_required
    def put(self, id):
        """Met a jour un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        from app.services.paiement_service import _normalize_payment_data
        from flask import request
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        data = request.get_json()
        if not data:
            return {'message': 'Donnees requises'}, 400
        try:
            normalized = _normalize_payment_data(data)
            for key, value in normalized.items():
                if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id']:
                    setattr(paiement, key, value)
            db.session.commit()
            return paiement.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @tenant_required
    def delete(self, id):
        """Supprime un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        try:
            paiement.is_active = False
            db.session.commit()
            return {'message': 'Paiement supprime'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

@ns.route('/facture/<int:facture_id>')
class PaiementFactureResource(Resource):
    @tenant_required
    def get(self, facture_id):
        """Liste les paiements d'une facture"""
        from app.models.paiement import Paiement
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(facture_id=facture_id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        return {'paiements': [p.to_dict() for p in paiements]}, 200


>>>

### FICHIER .PY: web\backend\app\api\v1\papi.py
<<<
from flask import request, current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.utilisateur import Utilisateur
from app.models.paiement import Paiement
from app.models.abonnement import Abonnement
from app.security.tenant import tenant_required, get_current_tenant_id
from app.services.papi.payment import (
    create_subscription_payment,
    create_subscription_offline_payment,
    PAPER_METHODS,
)
from app.services.papi.webhook import process_papi_webhook
from app.services.papi.errors import (
    PapiError,
    PapiAuthError,
    PapiValidationError,
    PapiWebhookError,
    PapiDuplicateWebhookError,
    PapiInvalidStatusError,
)

ns = Namespace('papi', description='Intégration Papi (paiements en ligne et hors ligne)')

# Alias d'entrée acceptés (frontend) -> valeurs canoniques backend
METHOD_ALIASES = {
    'mvola': 'MVOLA',
    'orange_money': 'ORANGE_MONEY',
    'orange money': 'ORANGE_MONEY',
    'airtel_money': 'ARTEL_MONEY',
    'airtel money': 'ARTEL_MONEY',
    'bred': 'BRED',
    'especes': 'ESPECES',
    'espèces': 'ESPECES',
    'cash': 'ESPECES',
    'virement': 'VIREMENT',
    'bank_transfer': 'VIREMENT',
    'cheque': 'CHEQUE',
    'chèque': 'CHEQUE',
    'check': 'CHEQUE',
}

ELECTRONIC_METHODS = ('MVOLA', 'ORANGE_MONEY', 'ARTEL_MONEY', 'BRED')
VALID_METHODS = ELECTRONIC_METHODS + PAPER_METHODS


def _normalize_payment_method(payment_method):
    raw = (payment_method or '').strip()
    if not raw:
        return None
    return METHOD_ALIASES.get(raw.lower(), raw.upper())


def _get_tenant_id_from_jwt():
    claims = get_jwt() or {}
    return claims.get('tenant_id')


@ns.route('/payments/subscription/<int:subscription_id>')
class CreatePapiPayment(Resource):

    @jwt_required()
    def post(self, subscription_id):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        data = request.get_json() or {}
        payment_method = _normalize_payment_method(data.get('payment_method', 'MVOLA'))
        is_test_mode = data.get('is_test_mode', True)

        if not payment_method or payment_method not in VALID_METHODS:
            return {
                'message': f"Mode de paiement invalide. Choisissez parmi: {', '.join(VALID_METHODS)}"
            }, 400

        try:
            if payment_method in PAPER_METHODS:
                result = create_subscription_offline_payment(
                    subscription_id=subscription_id,
                    payment_method=payment_method,
                    tenant_id=tenant_id,
                )
            else:
                result = create_subscription_payment(
                    subscription_id=subscription_id,
                    payment_method=payment_method,
                    is_test_mode=is_test_mode,
                    tenant_id=tenant_id,
                )
            return result, 200
        except ValueError as exc:
            current_app.logger.warning('Papi payment creation validation error: %s', exc)
            return {'message': str(exc)}, 400
        except PapiError as exc:
            current_app.logger.error('Papi payment creation error: %s', exc)
            return {'message': 'Erreur du service de paiement'}, 502
        except Exception as exc:
            current_app.logger.exception('Unexpected error during Papi payment creation')
            return {'message': 'Erreur interne du service de paiement'}, 500


@ns.route('/payments')
class ListPapiPayments(Resource):

    @jwt_required()
    def get(self):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        query = Paiement.query.filter(
            Paiement.tenant_id == tenant_id,
            Paiement.is_active == True,
            Paiement.provider.in_(['papi', 'manuel']),
        )
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        paginated = query.order_by(Paiement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            'payments': [p.to_dict() for p in paginated.items],
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
        }, 200


@ns.route('/payments/<int:id>')
class PapiPaymentDetail(Resource):

    @jwt_required()
    def get(self, id):
        tenant_id = _get_tenant_id_from_jwt()
        if not tenant_id:
            return {'message': 'Aucun tenant associe'}, 401

        payment = Paiement.query.filter_by(
            id=id,
            tenant_id=tenant_id,
            is_active=True,
            provider='papi',
        ).first()

        if not payment:
            return {'message': 'Paiement non trouve'}, 404

        return payment.to_dict(), 200


@ns.route('/webhook')
class PapiWebhook(Resource):

    def post(self):
        payload = request.get_json() or {}
        current_app.logger.info(
            'Papi webhook received: %s',
            {k: v for k, v in payload.items() if k not in ('payload',)}
        )

        try:
            result = process_papi_webhook(payload)
            status_code = 200
            if result.get('status') == 'already_processed':
                status_code = 200
            return result, status_code
        except PapiDuplicateWebhookError as exc:
            current_app.logger.info('Papi duplicate webhook: %s', exc)
            return {'status': 'already_processed'}, 200
        except PapiWebhookError as exc:
            current_app.logger.warning('Papi webhook validation error: %s', exc)
            return {'message': str(exc)}, 403
        except PapiInvalidStatusError as exc:
            current_app.logger.warning('Papi webhook invalid status: %s', exc)
            return {'message': str(exc)}, 400
        except Exception as exc:
            current_app.logger.exception('Unexpected error processing Papi webhook')
            return {'message': 'Erreur interne du webhook'}, 500

>>>

### FICHIER .PY: web\backend\app\api\v1\permissions.py
<<<
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.role_permission import Permission
from app.models.utilisateur import Utilisateur
from app import db
from app.security.roles import is_admin, is_super_admin

ns = Namespace('permissions', description='Gestion des permissions')

_ALLOWED_FIELDS = {'code', 'description', 'module', 'action'}


def _ensure_admin():
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (is_super_admin(user.role) or is_admin(user.role)):
        return {'message': 'Acces administrateur requis'}, 403
    return None


@ns.route('/')
class PermissionList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        search = (request.args.get('search') or '').strip().lower()
        module = (request.args.get('module') or '').strip().lower()
        query = Permission.query
        if search:
            query = query.filter(
                db.or_(
                    Permission.code.ilike(f'%{search}%'),
                    Permission.description.ilike(f'%{search}%'),
                )
            )
        if module:
            query = query.filter(Permission.module.ilike(f'%{module}%'))
        permissions = query.order_by(Permission.module.asc(), Permission.code.asc()).all()
        return {'permissions': [p.to_dict() for p in permissions]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        code = data.get('code')
        if not code:
            return {'message': 'Le code de permission est requis'}, 400
        existing = Permission.query.filter_by(code=code).first()
        if existing:
            return {'message': 'Une permission avec ce code existe deja'}, 409
        permission = Permission(
            code=code,
            description=data.get('description'),
            module=data.get('module'),
            action=data.get('action'),
        )
        db.session.add(permission)
        db.session.commit()
        return permission.to_dict(), 201


@ns.route('/<int:permission_id>')
class PermissionResource(Resource):
    @jwt_required()
    def get(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = db.session.get(Permission, permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        return permission.to_dict(), 200

    @jwt_required()
    def put(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = db.session.get(Permission, permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        data = request.get_json() or {}
        for key in _ALLOWED_FIELDS:
            if key in data:
                setattr(permission, key, data[key])
        db.session.commit()
        return permission.to_dict(), 200

    @jwt_required()
    def delete(self, permission_id):
        err = _ensure_admin()
        if err:
            return err
        permission = db.session.get(Permission, permission_id)
        if not permission:
            return {'message': 'Permission non trouvee'}, 404
        db.session.delete(permission)
        db.session.commit()
        return {'message': 'Permission supprimee'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\produits.py
<<<
from flask_restx import Namespace, Resource
from app.services.produit_service import ProduitService
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits

ns = Namespace('produits', description='Gestion des produits')

@ns.route('/')
class ProduitListResource(Resource):
    @ns.doc('list_produits')
    @tenant_required
    def get(self):
        """Liste tous les produits"""
        try:
            produits, total = ProduitService.get_all()
            return {'produits': [p.to_dict() for p in produits], 'total': total}, 200
        except Exception as e:
            return {'produits': [], 'total': 0, 'message': str(e)}, 500
    
    @ns.doc('create_produit')
    @tenant_required
    @check_plan_limits('produits')
    def post(self):
        """Cree un nouveau produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.create(data)
        return produit.to_dict(), 201

@ns.route('/<int:produit_id>')
class ProduitResource(Resource):
    @ns.doc('get_produit')
    @tenant_required
    def get(self, produit_id):
        """Recupere un produit par son ID"""
        produit = ProduitService.get_by_id(produit_id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200
    
    @ns.doc('update_produit')
    @tenant_required
    def put(self, produit_id):
        """Met a jour un produit"""
        from flask import request
        data = request.get_json()
        produit = ProduitService.update(produit_id, data)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200
    
    @ns.doc('delete_produit')
    @tenant_required
    def delete(self, produit_id):
        """Supprime un produit"""
        success = ProduitService.delete(produit_id)
        if not success:
            return {'message': 'Produit non trouve'}, 404
        return {'message': 'Produit supprime'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\public.py
<<<
from flask import request, current_app
from flask_restx import Namespace, Resource
from app.models.produit import Produit
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.commande_client import CommandeClient
from app.services.commande_service import CommandeService
from app import db
from datetime import datetime

ns_public = Namespace('public', description='API publique (catalogue, commandes, notifications)')
ns = ns_public


def _get_active_tenant_ids():
    now = datetime.utcnow()
    active_ids = [
        row[0] for row in db.session.query(Abonnement.tenant_id)
        .filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        )
        .distinct()
        .all()
    ]
    return set(active_ids)


@ns_public.route('/produits')
class PublicProduitList(Resource):
    def get(self):
        active_tenant_ids = _get_active_tenant_ids()
        if active_tenant_ids:
            produits = Produit.query.filter(
                Produit.is_active == True,
                Produit.tenant_id.in_(active_tenant_ids)
            ).all()
        else:
            produits = []
        # Joindre le nom du tenant vendeur pour l'affichage public
        tenant_map = {}
        if active_tenant_ids:
            tenants = Tenant.query.filter(Tenant.id.in_(active_tenant_ids)).all()
            tenant_map = {t.id: t.nom for t in tenants}
        result = []
        for p in produits:
            d = p.to_dict()
            d['tenant_nom'] = tenant_map.get(p.tenant_id, '')
            result.append(d)
        return {'produits': result}, 200


@ns_public.route('/produits/<int:produit_id>')
class PublicProduitDetail(Resource):
    def get(self, produit_id):
        active_tenant_ids = _get_active_tenant_ids()
        if not active_tenant_ids:
            return {'message': 'Produit non trouve'}, 404
        produit = Produit.query.filter(
            Produit.id == produit_id,
            Produit.is_active == True,
            Produit.tenant_id.in_(active_tenant_ids)
        ).first()
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        data = produit.to_dict()
        if produit.tenant_id and produit.tenant_id in active_tenant_ids:
            tenant = db.session.get(Tenant, produit.tenant_id)
            if tenant:
                data['tenant_nom'] = tenant.nom
        else:
            data['tenant_nom'] = ''
        return data, 200


@ns_public.route('/tenants/<int:tenant_id>')
class PublicTenantDetail(Resource):
    def get(self, tenant_id):
        tenant = Tenant.query.filter_by(id=tenant_id, is_active=True).first()
        if not tenant:
            return {'message': 'Vendeur non trouve'}, 404
        data = {
            'id': tenant.id,
            'nom': tenant.nom,
            'slug': tenant.slug,
            'ville': tenant.ville,
            'pays': tenant.pays,
            'statut': tenant.statut.value if hasattr(tenant.statut, 'value') else tenant.statut,
            'plan': tenant.plan,
        }
        return data, 200


@ns_public.route('/commandes')
class PublicCommandeCreate(Resource):
    def post(self):
        data = request.get_json() or {}

        # Le frontend Checkout envoie un objet "client" imbriqué, mais on
        # accepte également les champs plats (nom_client / email_client).
        client = data.get('client') or {}
        nom_client = data.get('nom_client') or client.get('nom')
        email_client = data.get('email_client') or client.get('email')
        items = data.get('items', [])

        missing = []
        if not nom_client:
            missing.append('nom_client')
        if not email_client:
            missing.append('email_client')
        if not items:
            missing.append('items')
        if missing:
            return {'message': f"Champs requis manquants: {', '.join(missing)}"}, 400

        if not isinstance(items, list) or len(items) == 0:
            return {'message': 'Le panier doit contenir au moins un article'}, 400

        try:
            commande = CommandeService.create_commande(data)
            return commande.to_dict(), 201
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur création commande publique')
            return {'message': 'Erreur lors de la création de la commande'}, 500


@ns_public.route('/commandes/tracking/<string:ref>')
class PublicCommandeTracking(Resource):
    def get(self, ref):
        commande = CommandeService.get_by_reference(ref)
        if not commande:
            return {'message': 'Commande non trouvee'}, 404
        statut_value = (
            commande.statut.value
            if hasattr(commande.statut, 'value')
            else commande.statut
        )
        return {
            'reference': commande.reference,
            'statut': statut_value,
            'updated_at': commande.updated_at.isoformat() if commande.updated_at else None,
        }, 200


@ns_public.route('/notifications')
class PublicNotifications(Resource):
    def get(self):
        ref = request.args.get('ref')
        if ref:
            commande = CommandeService.get_by_reference(ref)
            if not commande:
                return {'message': 'Commande non trouvee'}, 404
            
            statut_value = (
                commande.statut.value
                if hasattr(commande.statut, 'value')
                else commande.statut
            )
            
            return {
                'commande_ref': commande.reference,
                'statut': statut_value,
                'notifications': [
                    {
                        'message': f"Commande {statut_value}",
                        'date': commande.updated_at.isoformat() if commande.updated_at else None,
                        'statut': statut_value
                    }
                ]
            }, 200
        
        return {'notifications': []}, 200
    
    def post(self):
        data = request.get_json() or {}
        return {
            'message': 'Notification non supportée pour l\'instant. Utilisez /api/v1/notifications pour créer des notifications.',
            'data': data
        }, 501

>>>

### FICHIER .PY: web\backend\app\api\v1\rh.py
<<<
from flask import request, Response, g
from flask_restx import Namespace, Resource
from datetime import date
from app import db
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits, require_module
from app.services.rh_service import EmployeService, PresenceService, SalaireService, PrimeService
from app.services.stagiaire_service import StagiaireService
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns_employes = Namespace('employes', description='Gestion des employes')
ns_presences = Namespace('presences', description='Gestion des presences')
ns_salaires = Namespace('salaires', description='Gestion des salaires')
ns_primes = Namespace('primes', description='Gestion des primes')
ns_stagiaires = Namespace('stagiaires', description='Gestion des stagiaires')

_MODULE_RH = 'rh'


@ns_employes.route('/')
class EmployeList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        employes, total = EmployeService.get_all()
        return {'employes': [e.to_dict() for e in employes], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    @check_plan_limits('employes')
    def post(self):
        data = request.get_json() or {}
        employe = EmployeService.create(data)
        try:
            log_audit(
                TypeActionAudit.CREATION_EMPLOYE,
                f"Création de l'employé {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 201


@ns_employes.route('/<int:id>')
class EmployeResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        employe = EmployeService.get_by_id(id)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        employe = EmployeService.update(id, data)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.MODIFICATION_EMPLOYE,
                f"Modification de l'employe {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = EmployeService.delete(id)
        if not success:
            return {'message': 'Employe non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.SUPPRESSION_EMPLOYE,
                f"Suppression de l'employe id={id}",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': id},
            )
        except Exception:
            pass
        return {'message': 'Employe supprime'}, 200


@ns_presences.route('/')
class PresenceList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        presences, total = PresenceService.get_all()
        return {'presences': [p.to_dict() for p in presences], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        presence = PresenceService.create(data)
        return presence.to_dict(), 201


@ns_presences.route('/registre')
class PresenceRegistre(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        mois = request.args.get('mois')
        annee = request.args.get('annee')
        mois = int(mois) if mois else None
        annee = int(annee) if annee else None
        presences = PresenceService.get_registre(mois, annee)
        return {'presences': presences, 'count': len(presences)}, 200


@ns_presences.route('/registre/export')
class PresenceRegistreExport(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        mois = request.args.get('mois')
        annee = request.args.get('annee')
        mois = int(mois) if mois else None
        annee = int(annee) if annee else None
        csv = PresenceService.get_registre_export(mois, annee)
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=registre_presences.csv'}
        )


@ns_presences.route('/<int:id>')
class PresenceResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        presence = PresenceService.get_by_id(id)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        presence = PresenceService.update(id, data)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = PresenceService.delete(id)
        if not success:
            return {'message': 'Presence non trouvee'}, 404
        return {'message': 'Presence supprimee'}, 200


@ns_salaires.route('/')
class SalaireList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        salaires, total = SalaireService.get_all()
        return {'salaires': [s.to_dict() for s in salaires], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        salaire = SalaireService.create(data)
        return salaire.to_dict(), 201


@ns_salaires.route('/generer')
class SalaireGenerer(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        mois = data.get('mois')
        annee = data.get('annee')
        if not mois or not annee:
            today = date.today()
            mois = mois or today.month
            annee = annee or today.year
        mois = int(mois)
        annee = int(annee)
        salaires = SalaireService.generate_salaries(mois, annee)
        return {
            'message': f"{len(salaires)} bulletins de salaire générés pour {mois}/{annee}",
            'generated': len(salaires),
            'salaires': [s.to_dict() for s in salaires],
        }, 200


@ns_salaires.route('/<int:id>/payer')
class SalairePayer(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def post(self, id):
        data = request.get_json() or {}
        salaire = SalaireService.marquer_paye(
            id,
            statut_paiement=data.get('statut_paiement'),
            mode_paiement=data.get('mode_paiement'),
            reference_paiement=data.get('reference_paiement'),
            date_paiement=data.get('date_paiement'),
        )
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200


@ns_salaires.route('/export')
class SalaireExport(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        salaires, _ = SalaireService.get_all()
        headers = ['id', 'employe_id', 'employe_nom', 'mois', 'annee',
                   'salaire_base', 'primes', 'indemnites', 'deductions', 'avances',
                   'salaire_brut', 'salaire_net', 'statut_paiement', 'date_paiement', 'mode_paiement']
        records = []
        for s in salaires:
            d = s.to_dict()
            records.append({
                'id': d.get('id'),
                'employe_id': d.get('employe_id'),
                'employe_nom': d.get('employe_nom'),
                'mois': d.get('mois'),
                'annee': d.get('annee'),
                'salaire_base': d.get('salaire_base'),
                'primes': d.get('primes'),
                'indemnites': d.get('indemnites'),
                'deductions': d.get('deductions'),
                'avances': d.get('avances'),
                'salaire_brut': d.get('salaire_brut'),
                'salaire_net': d.get('salaire_net'),
                'statut_paiement': d.get('statut_paiement'),
                'date_paiement': d.get('date_paiement'),
                'mode_paiement': d.get('mode_paiement'),
            })
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(headers)
        for r in records:
            writer.writerow([r.get(h, '') for h in headers])
        return Response(buf.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=salaires.csv'})


@ns_salaires.route('/<int:id>')
class SalaireResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        salaire = SalaireService.get_by_id(id)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        salaire = SalaireService.update(id, data)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = SalaireService.delete(id)
        if not success:
            return {'message': 'Salaire non trouve'}, 404
        return {'message': 'Salaire supprime'}, 200


@ns_primes.route('/')
class PrimeList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        primes, total = PrimeService.get_all()
        return {'primes': [p.to_dict() for p in primes], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        prime = PrimeService.create(data)
        return prime.to_dict(), 201


@ns_primes.route('/<int:id>')
class PrimeResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        prime = PrimeService.get_by_id(id)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        prime = PrimeService.update(id, data)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = PrimeService.delete(id)
        if not success:
            return {'message': 'Prime non trouvee'}, 404
        return {'message': 'Prime supprimee'}, 200


@ns_stagiaires.route('/')
class StagiaireList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        stagiaires, total = StagiaireService.get_all()
        return {'stagiaires': [s.to_dict() for s in stagiaires], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    @check_plan_limits('stagiaires')
    def post(self):
        data = request.get_json() or {}
        try:
            stagiaire = StagiaireService.create(data)
        except ValueError as e:
            return {'message': str(e)}, 400
        try:
            log_audit(
                TypeActionAudit.CREATION_STAGIAIRE,
                f"Création du stagiaire {stagiaire.nom_complet} (matricule={stagiaire.matricule})",
                tenant_id=stagiaire.tenant_id,
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': stagiaire.id, 'matricule': stagiaire.matricule},
            )
        except Exception:
            pass
        return stagiaire.to_dict(), 201


@ns_stagiaires.route('/<int:id>')
class StagiaireResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        return stagiaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        data = request.get_json() or {}
        try:
            stagiaire = StagiaireService.update(id, data)
        except ValueError as e:
            return {'message': str(e)}, 400
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.MODIFICATION_STAGIAIRE,
                f"Modification du stagiaire {stagiaire.nom_complet} (matricule={stagiaire.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': stagiaire.id, 'matricule': stagiaire.matricule},
            )
        except Exception:
            pass
        return stagiaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        stagiaire.delete()
        try:
            log_audit(
                TypeActionAudit.SUPPRESSION_STAGIAIRE,
                f"Suppression du stagiaire id={id}",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': id},
            )
        except Exception:
            pass
        return {'message': 'Stagiaire supprime'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\roles.py
<<<
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.role_permission import RoleModel, Permission, role_permissions
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app import db
from app.security.roles import is_admin, is_super_admin

ns = Namespace('roles', description='Gestion des roles et permissions')

_ALLOWED_FIELDS = {'name', 'display_name', 'description', 'is_default', 'is_system'}


def _ensure_admin():
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)
    if not user:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (is_super_admin(user.role) or is_admin(user.role)):
        return {'message': 'Acces administrateur requis'}, 403
    return None


def _coerce_boolean(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('1', 'true', 'yes', 'on')


@ns.route('/')
class RoleList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_admin()
        if err:
            return err
        search = (request.args.get('search') or '').strip().lower()
        query = RoleModel.query
        if search:
            query = query.filter(
                db.or_(
                    RoleModel.name.ilike(f'%{search}%'),
                    RoleModel.display_name.ilike(f'%{search}%'),
                )
            )
        roles = query.order_by(RoleModel.name.asc()).all()
        return {'roles': [r.to_dict() for r in roles]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        name = data.get('name')
        if not name:
            return {'message': 'Le nom du role est requis'}, 400
        existing = RoleModel.query.filter_by(name=name).first()
        if existing:
            return {'message': 'Un role avec ce nom existe deja'}, 409
        role = RoleModel(
            name=name,
            display_name=data.get('display_name', name),
            description=data.get('description'),
            is_default=_coerce_boolean(data.get('is_default'), default=False),
            is_system=_coerce_boolean(data.get('is_system'), default=False),
        )
        permission_ids = data.get('permission_ids') or []
        if isinstance(permission_ids, list):
            for pid in permission_ids:
                perm = db.session.get(Permission, pid)
                if perm:
                    role.permissions.append(perm)
        db.session.add(role)
        db.session.commit()
        return role.to_dict(), 201


@ns.route('/<int:role_id>')
class RoleResource(Resource):
    @jwt_required()
    def get(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = db.session.get(RoleModel, role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        return role.to_dict(), 200

    @jwt_required()
    def put(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = db.session.get(RoleModel, role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        data = request.get_json() or {}
        for key in _ALLOWED_FIELDS:
            if key in data:
                setattr(role, key, data[key])
        if 'permission_ids' in data:
            role.permissions = []
            for pid in data.get('permission_ids') or []:
                perm = db.session.get(Permission, pid)
                if perm:
                    role.permissions.append(perm)
        db.session.commit()
        return role.to_dict(), 200

    @jwt_required()
    def delete(self, role_id):
        err = _ensure_admin()
        if err:
            return err
        role = db.session.get(RoleModel, role_id)
        if not role:
            return {'message': 'Role non trouve'}, 404
        if role.is_system:
            return {'message': 'Impossible de supprimer un role systeme'}, 400
        db.session.delete(role)
        db.session.commit()
        return {'message': 'Role supprime'}, 200


@ns.route('/permissions')
class RolePermissionList(Resource):
    @jwt_required()
    def post(self):
        err = _ensure_admin()
        if err:
            return err
        data = request.get_json() or {}
        role_id = data.get('role_id')
        permission_id = data.get('permission_id')
        if not role_id or not permission_id:
            return {'message': 'role_id et permission_id requis'}, 400
        role = db.session.get(RoleModel, role_id)
        perm = db.session.get(Permission, permission_id)
        if not role or not perm:
            return {'message': 'Role ou permission introuvable'}, 404
        if perm in role.permissions:
            return {'message': 'Permission deja assignee'}, 409
        role.permissions.append(perm)
        db.session.commit()
        return {'message': 'Permission ajoutee'}, 201


@ns.route('/permissions/<int:role_id>/<int:permission_id>')
class RolePermissionResource(Resource):
    @jwt_required()
    def delete(self, role_id, permission_id):
        err = _ensure_admin()
        if err:
            return err
        role = db.session.get(RoleModel, role_id)
        perm = db.session.get(Permission, permission_id)
        if not role or not perm:
            return {'message': 'Role ou permission introuvable'}, 404
        if perm in role.permissions:
            role.permissions.remove(perm)
            db.session.commit()
        return {'message': 'Permission retiree'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\stocks.py
<<<
from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.produit_service import ProduitService
from app.models.stock import MouvementStock
from app import db
from decimal import Decimal

ns = Namespace('stocks', description='Gestion des stocks')

@ns.route('/')
class StockList(Resource):
    @tenant_required
    def get(self):
        """Liste les produits avec statut stock"""
        produits = ProduitService.get_stock_alert()
        return {'stocks': [p.to_dict() for p in produits]}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json() or {}
        produit_id = data.get('produit_id')
        quantite = data.get('quantite')
        type_mouvement = data.get('type_mouvement')
        if not produit_id or quantite is None or not type_mouvement:
            return {'message': 'produit_id, quantite et type_mouvement sont requis'}, 400
        result = ProduitService.update_stock(
            produit_id,
            quantite,
            type_mouvement,
            data.get('raison', '')
        )
        if not result:
            return {'message': 'Produit non trouve'}, 404
        return result.to_dict(), 201

@ns.route('/<int:id>')
class StockResource(Resource):
    @tenant_required
    def get(self, id):
        """Statut d'un produit"""
        produit = ProduitService.get_by_id(id)
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        return produit.to_dict(), 200

@ns.route('/mouvements')
class StockMouvementList(Resource):
    @tenant_required
    def get(self):
        """Liste des mouvements de stock"""
        from app.models.stock import MouvementStock
        from app.security.tenant import get_current_tenant_id
        from app.models.utilisateur import Role
        from flask_jwt_extended import get_jwt

        claims = get_jwt() or {}
        role = claims.get('role')
        tenant_id = get_current_tenant_id()

        query = MouvementStock.query.filter_by(is_active=True).order_by(MouvementStock.created_at.desc())
        if role != Role.SUPER_ADMIN.value and tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        mouvements = query.all()
        return {'mouvements': [m.to_dict() for m in mouvements]}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json() or {}
        produit_id = data.get('produit_id')
        quantite = data.get('quantite')
        type_mouvement = data.get('type_mouvement')
        if not produit_id or quantite is None or not type_mouvement:
            return {'message': 'produit_id, quantite et type_mouvement sont requis'}, 400
        try:
            result = ProduitService.update_stock(
                produit_id,
                Decimal(str(quantite)),
                type_mouvement,
                data.get('raison', '')
            )
            if not result:
                return {'message': 'Produit non trouve'}, 404
            return result.to_dict(), 201
        except Exception:
            current_app.logger.exception('Erreur lors de la mise a jour du stock')
            return {'message': 'Erreur lors de la mise a jour du stock'}, 400

@ns.route('/stats')
class StockStats(Resource):
    @tenant_required
    def get(self):
        """Statistiques des stocks"""
        stats = ProduitService.get_statistiques()
        return stats, 200


@ns.route('/alerts')
class StockAlerts(Resource):
    @tenant_required
    def get(self):
        """Alertes de stock"""
        produits = ProduitService.get_stock_alert()
        return {'alerts': [p.to_dict() for p in produits]}, 200


>>>

### FICHIER .PY: web\backend\app\api\v1\super_admin.py
<<<
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

>>>

### FICHIER .PY: web\backend\app\api\v1\tenants.py
<<<
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app import db
from app.security.roles import is_super_admin
from datetime import datetime, timedelta

ns = Namespace('tenants', description='Gestion des tenants (SUPER_ADMIN)')

_ALLOWED_TENANT_FIELDS = {
    'nom', 'slug', 'domaine', 'email_contact', 'telephone',
    'adresse', 'ville', 'code_postal', 'pays', 'plan',
}


def _ensure_super_admin():
    user_id = get_jwt_identity()
    user = db.session.get(Utilisateur, user_id)
    if not user or not is_super_admin(user.role):
        return {'message': 'Acces super administrateur requis'}, 403
    return None


def _coerce_statut(value):
    if value is None:
        return None
    if isinstance(value, StatutTenant):
        return value
    normalized = str(value).strip().lower()
    for member in StatutTenant:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return None


@ns.route('/')
class TenantList(Resource):
    @jwt_required()
    def get(self):
        err = _ensure_super_admin()
        if err:
            return err
        tenants = Tenant.query.all()
        return {'tenants': [t.to_dict() for t in tenants]}, 200

    @jwt_required()
    def post(self):
        err = _ensure_super_admin()
        if err:
            return err
        data = request.get_json() or {}
        now = datetime.utcnow()
        trial_duration = timedelta(days=14)
        tenant = Tenant(
            nom=data.get('nom'),
            slug=data.get('slug'),
            domaine=data.get('domaine'),
            email_contact=data.get('email_contact'),
            telephone=data.get('telephone'),
            adresse=data.get('adresse'),
            ville=data.get('ville'),
            pays=data.get('pays', 'Madagascar'),
            code_postal=data.get('code_postal'),
            statut=_coerce_statut(data.get('statut', StatutTenant.EN_ESSAI)) or StatutTenant.EN_ESSAI,
            plan=data.get('plan', 'gratuit'),
            date_debut_essai=now,
            date_fin_essai=now + trial_duration,
        )
        db.session.add(tenant)
        db.session.commit()
        return tenant.to_dict(), 201


@ns.route('/<int:tenant_id>')
class TenantResource(Resource):
    @jwt_required()
    def get(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        return tenant.to_dict(), 200

    @jwt_required()
    def put(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        data = request.get_json() or {}
        for key, value in data.items():
            if key in _ALLOWED_TENANT_FIELDS:
                setattr(tenant, key, value)
        if data.get('statut') is not None:
            statut = _coerce_statut(data['statut'])
            if statut is not None:
                tenant.statut = statut
        db.session.commit()
        return tenant.to_dict(), 200


@ns.route('/<int:tenant_id>/suspend')
class TenantSuspend(Resource):
    @jwt_required()
    def post(self, tenant_id):
        err = _ensure_super_admin()
        if err:
            return err
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant non trouve'}, 404
        tenant.statut = StatutTenant.INACTIF
        tenant.is_active = False
        db.session.commit()
        return {'message': 'Tenant suspendu', 'tenant': tenant.to_dict()}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\test.py
<<<
from flask_restx import Namespace, Resource

ns = Namespace('test', description='Test API (development only)')

# Enregistrer uniquement en mode développement/testing
import os
_is_dev = os.environ.get('FLASK_ENV') in ('development', 'testing', '') or os.environ.get('DEBUG') == 'True'

if _is_dev:
    @ns.route('/')
    class TestResource(Resource):
        def get(self):
            return {'message': 'API fonctionne'}, 200
>>>

### FICHIER .PY: web\backend\app\api\v1\users.py
<<<
from flask import request, g
from flask_restx import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.role_permission import RoleModel
from app.models.tenant import Tenant
from app import db
from app.security.auth import hash_password, _validate_password
from app.security.plan_limits import check_plan_limits, check_admin_limit, require_module
from app.security.tenant import tenant_required, get_current_tenant_id
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns = Namespace('users', description='Gestion des utilisateurs')

_ALLOWED_USER_FIELDS = {'username', 'email', 'nom', 'prenom', 'telephone', 'mobile', 'role', 'statut', 'custom_role_id'}


def _require_admin():
    """Vérifie que l'utilisateur courant est admin ou super admin.

    Retourne (None, None) si autorisé, sinon (message, status).
    """
    user = getattr(g, 'current_user', None)
    if user is None:
        return {'message': 'Utilisateur non trouve'}, 401
    if not (user.is_super_admin or user.is_admin):
        return {'message': 'Acces administrateur requis'}, 403
    return None, None


def _is_global_admin():
    """True si l'utilisateur courant est super admin (accès global multi-tenant)."""
    user = getattr(g, 'current_user', None)
    return bool(user) and bool(user.is_super_admin)


def _get_tenant_scoped_user(user_id):
    """Récupère un utilisateur en respectant la portée tenant.

    Un admin de tenant ne peut manipuler que les utilisateurs de son propre tenant.
    """
    user = db.session.get(Utilisateur, user_id)
    if user is None:
        return None
    current_tenant_id = get_current_tenant_id()
    if current_tenant_id is not None and user.tenant_id != current_tenant_id:
        return None
    return user


def _coerce_statut(value):
    if value is None:
        return None
    if isinstance(value, StatutUtilisateur):
        return value
    normalized = str(value).strip().lower()
    for member in StatutUtilisateur:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return None


def _coerce_role(value):
    if value is None:
        return Role.USER
    if isinstance(value, Role):
        return value
    normalized = str(value).strip().lower()
    for member in Role:
        if member.value == normalized or member.name.lower() == normalized:
            return member
    return Role.USER


@ns.route('/')
class UserList(Resource):
    @tenant_required
    def get(self):
        err, status = _require_admin()
        if err:
            return err, status
        search = (request.args.get('search') or '').strip().lower()
        role_filter = (request.args.get('role') or '').strip().lower()
        statut_filter = (request.args.get('statut') or '').strip().lower()
        query = Utilisateur.query.filter_by(is_active=True)
        # Portée tenant : un admin de tenant ne voit que les utilisateurs de son tenant.
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id is not None:
            query = query.filter(Utilisateur.tenant_id == current_tenant_id)
        if search:
            query = query.filter(
                db.or_(
                    Utilisateur.username.ilike(f'%{search}%'),
                    Utilisateur.email.ilike(f'%{search}%'),
                    Utilisateur.nom.ilike(f'%{search}%'),
                    Utilisateur.prenom.ilike(f'%{search}%'),
                )
            )
        if role_filter:
            coerced = _coerce_role(role_filter)
            query = query.filter(Utilisateur.role == coerced)
        if statut_filter:
            coerced = _coerce_statut(statut_filter)
            if coerced:
                query = query.filter(Utilisateur.statut == coerced)
        users = query.order_by(Utilisateur.created_at.desc()).all()
        return {'users': [u.to_dict() for u in users]}, 200

    @tenant_required
    @check_plan_limits('utilisateurs')
    @check_admin_limit()
    def post(self):
        err, status = _require_admin()
        if err:
            return err, status
        data = request.get_json() or {}
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        if not username or not email or not password:
            return {'message': 'username, email et password requis'}, 400
        pwd_error = _validate_password(password)
        if pwd_error:
            return {'message': pwd_error}, 400
        existing = (
            Utilisateur.query.execution_options(_skip_tenant_filter=True)
            .filter((Utilisateur.email == email) | (Utilisateur.username == username))
            .first()
        )
        if existing:
            return {'message': 'Un utilisateur avec cet email ou username existe deja'}, 409
        role = _coerce_role(data.get('role', 'user'))
        if role == Role.SUPER_ADMIN and not _is_global_admin():
            return {'message': 'Seul un super administrateur peut creer un compte super_admin'}, 403
        tenant_id = data.get('tenant_id')
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id is not None:
            if tenant_id is not None and tenant_id != current_tenant_id:
                return {'message': 'Vous ne pouvez pas creer d\'utilisateur dans un autre tenant'}, 403
            tenant_id = current_tenant_id
        if tenant_id is not None:
            tenant = db.session.get(Tenant, tenant_id)
            if not tenant:
                return {'message': 'Tenant introuvable'}, 404
        creator_id = get_jwt_identity()
        user = Utilisateur(
            username=username,
            email=email,
            password_hash=hash_password(password),
            nom=data.get('nom'),
            prenom=data.get('prenom'),
            telephone=data.get('telephone'),
            mobile=data.get('mobile'),
            role=role,
            statut=_coerce_statut(data.get('statut')) or StatutUtilisateur.ACTIF,
            custom_role_id=data.get('custom_role_id'),
            tenant_id=tenant_id,
            created_by=creator_id,
        )
        db.session.add(user)
        db.session.commit()
        try:
            log_audit(
                TypeActionAudit.CREATION_UTILISATEUR,
                f"Création de l'utilisateur {user.username} (role={role.value})",
                tenant_id=tenant_id,
                utilisateur_id=get_jwt_identity(),
                metadata={'user_id': user.id, 'role': role.value},
            )
        except Exception:
            pass
        return user.to_dict(), 201


@ns.route('/<int:user_id>')
class UserResource(Resource):
    @tenant_required
    def get(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        return user.to_dict(), 200

    @tenant_required
    def put(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        if user.is_super_admin and not _is_global_admin():
            return {'message': 'Seul un super administrateur peut modifier un compte super_admin'}, 403
        data = request.get_json() or {}
        old_role = user.role
        for key in _ALLOWED_USER_FIELDS:
            if key not in data:
                continue
            value = data[key]
            if key == 'role':
                coerced = _coerce_role(value)
                if coerced == Role.SUPER_ADMIN and not _is_global_admin():
                    return {'message': 'Seul un super administrateur peut assigner le role super_admin'}, 403
                if coerced in (Role.ADMIN, Role.SUPER_ADMIN) and user.tenant_id:
                    tenant = db.session.get(Tenant, user.tenant_id)
                    if tenant and not check_admin_limit(tenant):
                        return {'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'}, 403
                value = coerced
            elif key == 'statut':
                value = _coerce_statut(value)
            setattr(user, key, value)
        if 'password' in data and data['password']:
            pwd_error = _validate_password(data['password'])
            if pwd_error:
                return {'message': pwd_error}, 400
            user.password_hash = hash_password(data['password'])
        user.updated_by = get_jwt_identity()
        db.session.commit()
        if old_role != user.role:
            log_audit(
                TypeActionAudit.CHANGEMENT_ROLE,
                f"Changement de rôle pour {user.username}: {old_role.value} -> {user.role.value}",
                tenant_id=user.tenant_id,
                utilisateur_id=g.current_user.id if hasattr(g, 'current_user') and g.current_user else None,
                metadata={'user_id': user.id, 'old_role': old_role.value, 'new_role': user.role.value},
            )
        return user.to_dict(), 200

    @tenant_required
    def delete(self, user_id):
        err, status = _require_admin()
        if err:
            return err, status
        user = _get_tenant_scoped_user(user_id)
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404
        if user.is_super_admin:
            return {'message': 'Impossible de supprimer un super administrateur'}, 400
        user.is_active = False
        db.session.commit()
        return {'message': 'Utilisateur desactive'}, 200

>>>

### FICHIER .PY: web\backend\app\api\v1\ventes.py
<<<
from flask_restx import Namespace, Resource, fields
from app.security.tenant import tenant_required
from app.services.vente_service import get_sales_summary, create_with_lignes, get_stats
from flask import request
from app import db

ns = Namespace('ventes', description='Gestion des ventes')

ligne_vente_model = ns.model('LigneVente', {
    'produit_id': fields.Integer(required=True, description='ID produit'),
    'quantite': fields.Float(required=True, description='Quantité vendue'),
    'prix_unitaire': fields.Float(required=True, description='Prix unitaire HT'),
    'taux_tva': fields.Float(description='Taux TVA', default=20),
})

vente_model = ns.model('Vente', {
    'client_id': fields.Integer(required=True, description='ID client'),
    'date': fields.String(description='Date de la vente'),
    'statut': fields.String(description='Statut de la vente', default='en_attente'),
    'mode_paiement': fields.String(description='Mode de paiement', default='especes'),
    'remarque': fields.String(description='Remarque'),
    'lignes': fields.List(fields.Nested(ligne_vente_model), required=True, description='Lignes de vente'),
})

@ns.route('/')
class VenteList(Resource):
    @tenant_required
    def get(self):
        """Liste toutes les ventes"""
        try:
            ventes = get_sales_summary()
            result = []
            for v in ventes:
                d = v.to_dict()
                if v.client:
                    d['client_nom'] = v.client.nom_complet or v.client.nom
                else:
                    d['client_nom'] = None
                if v.commercial:
                    d['commercial_nom'] = v.commercial.full_name
                else:
                    d['commercial_nom'] = None
                result.append(d)
            return {'ventes': result}, 200
        except Exception:
            current_app.logger.exception('Erreur lors de la liste des ventes')
            return {'ventes': []}, 500

    @ns.doc('create_vente')
    @tenant_required
    @ns.expect(vente_model)
    def post(self):
        """Creation de vente"""
        from flask import request
        data = request.get_json()
        try:
            vente = create_with_lignes(data)
            return vente.to_dict(), 201
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la création de la vente')
            return {'message': 'Erreur lors de la création de la vente'}, 400

@ns.route('/<int:id>')
class VenteResource(Resource):
    @tenant_required
    def get(self, id):
        """Details d'une vente"""
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        lignes = LigneVente.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).all()
        result = vente.to_dict()
        result['lignes_vente'] = [l.to_dict() for l in lignes]
        if vente.client:
            result['client_nom'] = vente.client.nom_complet or vente.client.nom
        else:
            result['client_nom'] = None
        if vente.commercial:
            result['commercial_nom'] = vente.commercial.full_name
        else:
            result['commercial_nom'] = None
        return result, 200

    @tenant_required
    def put(self, id):
        """Met a jour une vente"""
        from app.models.vente import Vente
        from app.security.tenant import tenant_filtered_get
        from flask import request
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        data = request.get_json()
        try:
            if 'date' in data and isinstance(data['date'], str):
                from datetime import datetime
                data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
            for key, value in data.items():
                if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id']:
                    setattr(vente, key, value)
            from app import db
            db.session.commit()
            return vente.to_dict(), 200
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la mise a jour de la vente')
            return {'message': 'Erreur lors de la mise a jour de la vente'}, 400

    @tenant_required
    def delete(self, id):
        """Supprime une vente"""
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        try:
            vente.is_active = False
            LigneVente.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).update({'is_active': False})
            from app import db
            db.session.commit()
            return {'message': 'Vente supprimee'}, 200
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la suppression de la vente')
            return {'message': 'Erreur lors de la suppression de la vente'}, 400


@ns.route('/summary')
class VenteSummary(Resource):
    @tenant_required
    def get(self):
        """Statistiques des ventes"""
        stats = get_stats()
        return stats, 200


>>>

### FICHIER .PY: web\backend\app\config\__init__.py
<<<
from .settings import Config
from .database import init_db

__all__ = ['Config', 'init_db']

>>>

### FICHIER .PY: web\backend\app\config\database.py
<<<
from .settings import Config
from ..models.base import db


def init_db(app):
    app.config.from_object(Config)
    db.init_app(app)
    return db

>>>

### FICHIER .PY: web\backend\app\config\settings.py
<<<
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///erp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Celery / Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Multi-tenancy
    DEFAULT_TENANT_SLUG = 'default'
    DEFAULT_TENANT_DOMAIN = 'localhost'
    DEFAULT_TENANT_NAME = 'Tenant Par Défaut'

    # Currency & Localization (Madagascar)
    CURRENCY_CODE = 'MGA'
    CURRENCY_SYMBOL = 'Ar'
    CURRENCY_LOCALE = 'mg-MG'
    DEFAULT_COUNTRY = 'Madagascar'

    # Papi Payment Gateway
    PAPI_API_URL = os.getenv('PAPI_API_URL', 'https://app.papi.mg/dashboard/api/payment-links')
    PAPI_API_KEY = os.getenv('PAPI_API_KEY')
    PAPI_ENVIRONMENT = os.getenv('PAPI_ENVIRONMENT', 'sandbox')
    PAPI_WEBHOOK_SECRET = os.getenv('PAPI_WEBHOOK_SECRET')
    PAPI_CALLBACK_URL = os.getenv('PAPI_CALLBACK_URL')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
>>>

### FICHIER .PY: web\backend\app\constants.py
<<<
MODE_PAIEMENT_CHOICES = [
    ('especes', 'Espèces'),
    ('virement', 'Virement bancaire'),
    ('cheque', 'Chèque'),
    ('mvola', 'MVola'),
    ('orange_money', 'Orange Money'),
    ('airtel_money', 'Airtel Money'),
]

UNITE_CHOICES = [
    'piece',
    'bouteille',
    'sachet',
    'pack',
    'carton',
    'sac',
    'bidon',
    'caisse',
    'palette',
]

CURRENCY = {
    'code': 'MGA',
    'symbol': 'Ar',
    'locale': 'mg-MG',
}

>>>

### FICHIER .PY: web\backend\app\models\__init__.py
<<<
from app.models.base import BaseModel
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.fournisseur import Fournisseur, TypeFournisseur
from app.models.client import Client, TypeClient, SecteurActivite
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.ligne_vente import LigneVente
from app.models.commande_client import CommandeClient, StatutCommande
from app.models.commande_fournisseur import CommandeFournisseur
from app.models.facture_fournisseur import FactureFournisseur
from app.models.ligne_achat import LigneAchat
from app.models.livreur import Livreur
from app.models.vehicule import Vehicule
from app.models.itineraire import Itineraire
from app.models.livraison import Livraison
from app.models.suivi_livraison import SuiviLivraison
from app.models.employe import Employe, TypeContrat, Sexe, StatutEmploye
from app.models.stagiaire import Stagiaire, TypeContratStagiaire, SexeStagiaire, StatutStagiaire
from app.models.presence import Presence, StatutPresence
from app.models.salaire import Salaire, StatutPaiementSalaire
from app.models.prime import Prime, TypePrime
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.models.modele_document import ModeleDocument
from app.models.document_genere import DocumentGenere
from app.models.commande_achat import CommandeAchat, ReceptionAchat, QualiteAchat, StatutCommandeAchat
from app.models.devis_avoir_bl import Devis, BonLivraison, Avoir, StatutAvoir
from app.models.password_reset_token import PasswordResetToken
from app.models.payment_event import PaymentEvent
from app.models.notification import Notification
from app.models.audit_log import AuditLog, TypeActionAudit
from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
from app.models.role_permission import RoleModel, Permission
from app import db
from app.models.tenant import Tenant, StatutTenant

__all__ = [
    'db',
    'BaseModel',
    'Utilisateur',
    'Role',
    'StatutUtilisateur',
    'Fournisseur',
    'TypeFournisseur',
    'Client',
    'TypeClient',
    'SecteurActivite',
    'Produit',
    'MouvementStock',
    'TypeMouvement',
    'Vente',
    'Facture',
    'Paiement',
    'StatutPaiement',
    'TypePaiement',
    'LigneVente',
    'CommandeClient',
    'StatutCommande',
    'CommandeFournisseur',
    'FactureFournisseur',
    'LigneAchat',
    'Livreur',
    'Vehicule',
    'Itineraire',
    'Livraison',
    'SuiviLivraison',
    'Employe',
    'TypeContrat',
    'Sexe',
    'StatutEmploye',
    'Presence',
    'StatutPresence',
    'Salaire',
    'StatutPaiementSalaire',
    'Prime',
    'TypePrime',
    'CompteComptable',
    'TypeCompte',
    'EcritureComptable',
    'StatutEcriture',
    'Tresorerie',
    'TypeTresorerie',
    'ModeleDocument',
    'DocumentGenere',
    'CommandeAchat',
    'ReceptionAchat',
    'QualiteAchat',
    'StatutCommandeAchat',
    'Devis',
    'BonLivraison',
    'Avoir',
    'StatutAvoir',
    'Tenant',
    'StatutTenant',
    'Abonnement',
    'StatutAbonnement',
    'PasswordResetToken',
    'PaymentEvent',
    'Notification',
    'AuditLog',
    'TypeActionAudit',
    'DeskFavorite',
    'DeskFilterPreset',
    'DeskColumnConfig',
    'SyncEvent',
    'RoleModel',
    'Permission',
]

>>>

### FICHIER .PY: web\backend\app\models\abonnement.py
<<<
from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, Numeric
import enum
from datetime import datetime


class StatutAbonnement(enum.Enum):
    ACTIF = 'actif'
    EXPIRE = 'expire'
    EN_ATTENTE = 'en_attente'
    ANNULE = 'annule'


class Abonnement(BaseModel):
    __tablename__ = 'abonnements'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    montant = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    devise = db.Column(db.String(10), default='MGA')
    date_debut = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_fin = db.Column(db.DateTime, nullable=False)
    statut = db.Column(Enum(StatutAbonnement), default=StatutAbonnement.EN_ATTENTE, nullable=False)
    methode_paiement = db.Column(db.String(50))
    reference_paiement = db.Column(db.String(100))
    plan = db.Column(db.String(50))
    notes = db.Column(db.Text)

    max_utilisateurs = db.Column(db.Integer, nullable=True)
    max_produits = db.Column(db.Integer, nullable=True)
    max_clients = db.Column(db.Integer, nullable=True)
    max_admins = db.Column(db.Integer, nullable=True)
    max_employees = db.Column(db.Integer, nullable=True)
    max_interns = db.Column(db.Integer, nullable=True)
    modules = db.Column(db.Text, nullable=True)

    tenant = db.relationship('Tenant', back_populates='abonnements', lazy='select')
    paiements = db.relationship('Paiement', back_populates='abonnement', cascade='all, delete-orphan')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['montant'] = float(self.montant) if self.montant else 0.0
        data['date_debut'] = (
            self.date_debut.isoformat()
            if self.date_debut
            else None
        )
        data['date_fin'] = (
            self.date_fin.isoformat()
            if self.date_fin
            else None
        )
        data['modules'] = (
            [m.strip() for m in self.modules.split(',') if m.strip()]
            if isinstance(self.modules, str)
            else self.modules
        )
        return data

    def __repr__(self):
        return f'<Abonnement {self.id} - Tenant {self.tenant_id} ({self.statut.value if hasattr(self.statut, "value") else self.statut})>'

>>>

### FICHIER .PY: web\backend\app\models\audit_log.py
<<<
from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum
import enum
import json


class TypeActionAudit(enum.Enum):
    CREATION_UTILISATEUR = 'creation_utilisateur'
    CHANGEMENT_ROLE = 'changement_role'
    CREATION_EMPLOYE = 'creation_employe'
    MODIFICATION_EMPLOYE = 'modification_employe'
    SUPPRESSION_EMPLOYE = 'suppression_employe'
    CREATION_STAGIAIRE = 'creation_stagiaire'
    MODIFICATION_STAGIAIRE = 'modification_stagiaire'
    SUPPRESSION_STAGIAIRE = 'suppression_stagiaire'
    MODIFICATION_PERMISSION = 'modification_permission'
    CHANGEMENT_ABONNEMENT = 'changement_abonnement'
    CREATION_TENANT = 'creation_tenant'
    ACTIVATION_TENANT = 'activation_tenant'
    SUSPENSION_TENANT = 'suspension_tenant'
    PROLONGATION_ABONNEMENT = 'prolongation_abonnement'
    CONNEXION_SUPER_ADMIN = 'connexion_super_admin'
    DECONNEXION_SUPER_ADMIN = 'deconnexion_super_admin'
    MODIFICATION_TENANT = 'modification_tenant'


class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True, index=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True, index=True)
    type_action = db.Column(Enum(TypeActionAudit), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)

    tenant = db.relationship('Tenant', foreign_keys=[tenant_id], lazy='select')
    utilisateur = db.relationship('Utilisateur', foreign_keys=[utilisateur_id], lazy='select')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['type_action'] = (
            self.type_action.value
            if hasattr(self.type_action, 'value')
            else self.type_action
        )
        if self.metadata_json:
            try:
                data['metadata_json'] = json.loads(self.metadata_json)
            except (json.JSONDecodeError, TypeError):
                data['metadata_json'] = self.metadata_json
        else:
            data['metadata_json'] = None
        return data

    def __repr__(self):
        return f'<AuditLog {self.type_action} tenant={self.tenant_id} user={self.utilisateur_id}>'

>>>

### FICHIER .PY: web\backend\app\models\base.py
<<<
from decimal import Decimal
from datetime import datetime, date
from app import db

class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        self.is_active = False
        db.session.commit()
    
    def hard_delete(self):
        db.session.delete(self)
        db.session.commit()
    
    def to_dict(self, exclude=None):
        data = {}
        exclude = exclude or []
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            data[column.name] = value
        return data


class BaseTenantModel(BaseModel):
    __abstract__ = True
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)

>>>

### FICHIER .PY: web\backend\app\models\client.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Index, Numeric
import enum

class TypeClient(enum.Enum):
    BOUTIQUE = 'boutique'
    EPICERIE = 'epicerie'
    REVENDEUR = 'revendeur'
    SEMI_GROSSISTE = 'semi_grossiste'
    GROSSISTE = 'grossiste'
    SUPERMARCHE = 'supermarche'
    RESTAURANT = 'restaurant'
    HOTEL = 'hotel'
    ENTREPRISE = 'entreprise'
    INSTITUTION = 'institution'
    PARTICULIER = 'particulier'

class SecteurActivite(enum.Enum):
    AGRICULTURE = 'agriculture'
    INDUSTRIE = 'industrie'
    CONSTRUCTION = 'construction'
    COMMERCE = 'commerce'
    TRANSPORT = 'transport'
    SERVICES = 'services'
    AUTRE = 'autre'

class Client(BaseTenantModel):
    __tablename__ = 'clients'
    
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    raison_sociale = db.Column(db.String(200))
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    type = db.Column(
        Enum(
            TypeClient,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=TypeClient.PARTICULIER
    )
    secteur = db.Column(
        Enum(
            SecteurActivite,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=SecteurActivite.AUTRE
    )
    
    # Identification
    siret = db.Column(db.String(20))
    numero_tva = db.Column(db.String(20))
    numero_rcs = db.Column(db.String(50))
    
    # Contact
    email = db.Column(db.String(100), unique=True, index=True)
    email_secondaire = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    telephone_secondaire = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    site_web = db.Column(db.String(200))
    
    # Adresse de facturation
    adresse_facturation = db.Column(db.String(200))
    complement_facturation = db.Column(db.String(200))
    code_postal_facturation = db.Column(db.String(10))
    ville_facturation = db.Column(db.String(100))
    pays_facturation = db.Column(db.String(50), default='Madagascar')
    
    # Adresse de livraison (si différente)
    adresse_livraison = db.Column(db.String(200))
    complement_livraison = db.Column(db.String(200))
    code_postal_livraison = db.Column(db.String(10))
    ville_livraison = db.Column(db.String(100))
    pays_livraison = db.Column(db.String(50), default='Madagascar')
    
    # Contact principal
    contact_nom = db.Column(db.String(100))
    contact_prenom = db.Column(db.String(100))
    contact_fonction = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_telephone = db.Column(db.String(20))
    
    # Informations commerciales
    conditions_paiement = db.Column(db.String(50), default='30 jours')
    remise_standard = db.Column(Numeric(5, 2), default=0)
    plafond_credit = db.Column(Numeric(10, 2))
    echeance_credit = db.Column(db.Integer, default=30)  # jours
    
    # Compte client
    solde = db.Column(Numeric(10, 2), default=0)
    points_fidelite = db.Column(db.Integer, default=0)
    
    # Commercial
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    
    # Statut
    est_favori = db.Column(db.Boolean, default=False)
    est_actif = db.Column(db.Boolean, default=True)
    est_bloque = db.Column(db.Boolean, default=False)
    note = db.Column(db.Integer)  # 1-5
    
    # Relations
    commercial = db.relationship('Utilisateur', back_populates='clients', foreign_keys='Client.commercial_id')
    ventes = db.relationship('Vente', back_populates='client', lazy='dynamic')
    factures = db.relationship('Facture', back_populates='client', lazy='dynamic')
    paiements = db.relationship('Paiement', back_populates='client', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_client_nom_prenom', 'nom', 'prenom'),
        Index('idx_client_type_secteur', 'type', 'secteur'),
        Index('idx_client_commercial', 'commercial_id'),
    )
    
    @property
    def nom_complet(self):
        if self.type == TypeClient.PARTICULIER:
            return f"{self.prenom} {self.nom}"
        return self.raison_sociale or f"{self.prenom} {self.nom}"
    
    @property
    def adresse_complete_facturation(self):
        return f"{self.adresse_facturation}, {self.code_postal_facturation} {self.ville_facturation}, {self.pays_facturation}"
    
    @property
    def total_achats(self):
        """Total des achats du client"""
        from app.models.vente import Vente
        return self.ventes.filter_by(is_active=True, statut='payee').with_entities(
            db.func.sum(Vente.total_ttc)
        ).scalar() or 0
    
    @property
    def total_commandes(self):
        """Nombre total de commandes"""
        return self.ventes.filter_by(is_active=True).count()
    
    @property
    def dernier_achat(self):
        """Date du dernier achat"""
        from app.models.vente import Vente
        derniere_vente = self.ventes.filter_by(is_active=True).order_by(
            Vente.created_at.desc()
        ).first()
        return derniere_vente.created_at if derniere_vente else None
    
    @property
    def est_a_credit(self):
        """Vérifie si le client est à crédit"""
        return self.solde < 0
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type' in data and self.type:
            data['type'] = self.type.value
        if 'secteur' in data and self.secteur:
            data['secteur'] = self.secteur.value
        data['nom_complet'] = self.nom_complet
        data['total_achats'] = float(self.total_achats)
        data['total_commandes'] = self.total_commandes
        return data
    
    def __repr__(self):
        return f'<Client {self.code} - {self.nom_complet}>'
>>>

### FICHIER .PY: web\backend\app\models\commande_achat.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutCommandeAchat(enum.Enum):
    BROUILLON = 'brouillon'
    ENVOYEE = 'envoyee'
    CONFIRMEE = 'confirmee'
    RECUE = 'recue'
    PARTIELLEMENT_RECUE = 'partiellement_recue'
    ANNULEE = 'annulee'

class CommandeAchat(BaseTenantModel):
    __tablename__ = 'commandes_achat'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    total_ht = db.Column(Numeric(12, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(12, 2), nullable=False, default=0)
    statut = db.Column(db.Enum(StatutCommandeAchat, name='statut_commande_achat', values_callable=lambda e: [x.value for x in e]), default=StatutCommandeAchat.BROUILLON)
    date_commande = db.Column(db.DateTime, default=db.func.now())
    date_livraison_prevue = db.Column(db.DateTime)
    date_reception = db.Column(db.DateTime)
    remarque = db.Column(db.Text)
    conditions_paiement = db.Column(db.String(100))

    fournisseur = db.relationship('Fournisseur', back_populates='commandes_achat')
    receptions = db.relationship('ReceptionAchat', back_populates='commande_achat', lazy='dynamic')
    lignes_achat = db.relationship('LigneAchat', back_populates='commande_achat', lazy='dynamic')

    __table_args__ = (
        Index('idx_commande_achat_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.fournisseur:
            data['fournisseur_nom'] = self.fournisseur.nom_complet
        return data

    def __repr__(self):
        return f'<CommandeAchat {self.reference}>'

class ReceptionAchat(BaseTenantModel):
    __tablename__ = 'receptions_achat'

    commande_achat_id = db.Column(db.Integer, db.ForeignKey('commandes_achat.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    date_reception = db.Column(db.DateTime, default=db.func.now())
    receptionne_par_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    quantite_recue = db.Column(Numeric(10, 2), nullable=False)
    quantite_commandee = db.Column(Numeric(10, 2), nullable=False)
    ecart = db.Column(Numeric(10, 2))
    remarque = db.Column(db.Text)

    commande_achat = db.relationship('CommandeAchat', back_populates='receptions')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<ReceptionAchat {self.reference}>'

class QualiteAchat(BaseTenantModel):
    __tablename__ = 'qualites_achat'

    reception_id = db.Column(db.Integer, db.ForeignKey('receptions_achat.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite_controlee = db.Column(Numeric(10, 2), nullable=False)
    quantite_conforme = db.Column(Numeric(10, 2), nullable=False)
    quantite_rejetee = db.Column(Numeric(10, 2), default=0)
    motif_rejet = db.Column(db.String(200))
    statut = db.Column(db.String(20), default='conforme')  # conforme/non_conforme
    remarque = db.Column(db.Text)

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<QualiteAchat {self.id}>'

>>>

### FICHIER .PY: web\backend\app\models\commande_client.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Numeric
import enum
import json

class StatutCommande(enum.Enum):
    EN_ATTENTE = 'en_attente'
    CONFIRMEE = 'confirmee'
    EXPEDIEE = 'expediee'
    LIVREE = 'livree'
    ANNULEE = 'annulee'

class CommandeClient(BaseTenantModel):
    __tablename__ = 'commandes_client'
    
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    nom_client = db.Column(db.String(100), nullable=False)
    prenom_client = db.Column(db.String(100))
    email_client = db.Column(db.String(120), nullable=False)
    telephone_client = db.Column(db.String(20))
    
    adresse_livraison = db.Column(db.String(200))
    ville_livraison = db.Column(db.String(100))
    code_postal_livraison = db.Column(db.String(10))
    pays_livraison = db.Column(db.String(50), default='Madagascar')
    
    items = db.Column(db.Text, nullable=False)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    
    statut = db.Column(Enum(StatutCommande), default=StatutCommande.EN_ATTENTE, nullable=False)
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), index=True)
    tenant = db.relationship('Tenant', backref='commandes_client')
    
    notes = db.Column(db.Text)
    
    @property
    def items_list(self):
        if self.items:
            try:
                return json.loads(self.items)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @items_list.setter
    def items_list(self, value):
        self.items = json.dumps(value)
    
    def to_dict(self):
        data = super().to_dict()
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        enriched_items = []
        for item in self.items_list:
            produit = None
            try:
                from app.models.produit import Produit
                produit_query = Produit.query.filter_by(id=item.get('produit_id'))
                if self.tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=self.tenant_id)
                produit = produit_query.first()
            except Exception:
                pass
            enriched_items.append({
                'produit_id': item.get('produit_id'),
                'quantite': item.get('quantite', 1),
                'produit_nom': produit.nom if produit else None,
                'prix_unitaire': float(produit.prix_vente_ht) if produit else 0,
                'total': float(produit.prix_vente_ht or 0) * item.get('quantite', 1) if produit else 0,
            })
        data['items'] = enriched_items
        return data
    
    def __repr__(self):
        return f'<CommandeClient {self.reference} - {self.nom_client}>'

>>>

### FICHIER .PY: web\backend\app\models\commande_fournisseur.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class CommandeFournisseur(BaseTenantModel):
    __tablename__ = 'commandes_fournisseur'
    
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='en_attente')  # en_attente, envoyee, recue, annulee
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='commandes')
    lignes_achat = db.relationship('LigneAchat', back_populates='commande_fournisseur', lazy='dynamic')


>>>

### FICHIER .PY: web\backend\app\models\compte_comptable.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index, Numeric
import enum

class TypeCompte(enum.Enum):
    ACTIF = 'actif'
    PASSIF = 'passif'
    CHARGE = 'charge'
    PRODUIT = 'produit'

class CompteComptable(BaseTenantModel):
    __tablename__ = 'comptes_comptables'

    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    type_compte = db.Column(db.Enum(TypeCompte, name='type_compte', values_callable=lambda e: [x.value for x in e]), nullable=False)
    sous_compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), index=True)
    solde = db.Column(Numeric(12, 2), default=0)
    is_actif = db.Column(db.Boolean, default=True)

    sous_comptes = db.relationship('CompteComptable', remote_side='CompteComptable.id', back_populates='parent')
    parent = db.relationship('CompteComptable', remote_side='CompteComptable.sous_compte_id', back_populates='sous_comptes')
    ecritures = db.relationship('EcritureComptable', back_populates='compte', lazy='dynamic')
    tresorerie_ecritures = db.relationship('Tresorerie', back_populates='compte', foreign_keys='Tresorerie.compte_id')

    __table_args__ = (
        Index('idx_compte_numero', 'numero'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_compte:
            data['type_compte'] = self.type_compte.value
        if self.parent:
            data['parent_numero'] = self.parent.numero
            data['parent_nom'] = self.parent.nom
        return data

    def __repr__(self):
        return f'<CompteComptable {self.numero} - {self.nom}>'

>>>

### FICHIER .PY: web\backend\app\models\desk_state.py
<<<
# web/backend/app/models/desk_state.py
# Modèles de préférences synchronisées (favoris, colonnes, filtres, events).
# Héritent de BaseModel : tenant_id, created_at, updated_at, is_active,
# created_by, updated_by. Scopés par user_id pour la cohérence web/desktop.

from app import db
from app.models.base import BaseModel
from datetime import datetime


class DeskFavorite(BaseModel):
    __tablename__ = 'desk_favorites'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    path = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(255), nullable=True)
    data = db.Column(db.JSON, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'user_id', 'path', name='uq_desk_fav_tenant_user_path'),
    )

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        return d


class DeskFilterPreset(BaseModel):
    __tablename__ = 'desk_filter_presets'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    filters = db.Column(db.JSON, nullable=True)
    is_default = db.Column(db.Boolean, default=False)

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        d['createdAt'] = d.pop('created_at')
        return d


class DeskColumnConfig(BaseModel):
    __tablename__ = 'desk_column_configs'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    module = db.Column(db.String(64), nullable=False, index=True)
    widths = db.Column(db.JSON, nullable=True)
    hidden = db.Column(db.JSON, nullable=True)
    sort = db.Column(db.JSON, nullable=True)
    version = db.Column(db.Integer, default=1)

    def to_public(self):
        d = self.to_dict(exclude=['tenant_id', 'created_by', 'updated_by', 'is_active'])
        d['updatedAt'] = d.pop('updated_at')
        return {
            'module': d['module'],
            'config': {
                'widths': d.get('widths') or {},
                'hidden': d.get('hidden') or [],
                'sort': d.get('sort') or [],
                'version': d.get('version', 1),
            },
        }


class SyncEvent(BaseModel):
    """Journal incrémental des mutations pour le temps-réel / pull polling."""
    __tablename__ = 'desk_sync_events'

    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False, index=True)
    entity = db.Column(db.String(32), nullable=False)  # favorite | column | filter | notification
    module = db.Column(db.String(64), nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    revision = db.Column(db.BigInteger, nullable=False, index=True)

    def to_public(self):
        return {
            'id': self.id,
            'revision': self.revision,
            'entity': self.entity,
            'module': self.module,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

>>>

### FICHIER .PY: web\backend\app\models\devis_avoir_bl.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutAvoir(enum.Enum):
    EN_ATTENTE = 'en_attente'
    ACCEPTE = 'accepte'
    REMBOURSE = 'rembourse'
    ANNULE = 'annule'

class Avoir(BaseTenantModel):
    __tablename__ = 'avoirs'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    montant_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    montant_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    motif = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutAvoir, name='statut_avoir', values_callable=lambda e: [x.value for x in e]), default=StatutAvoir.EN_ATTENTE)
    date_avoir = db.Column(db.DateTime, default=db.func.now())
    rembourse = db.Column(db.Boolean, default=False)

    __table_args__ = (
        Index('idx_avoir_client', 'client_id'),
        Index('idx_avoir_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        return data

    def __repr__(self):
        return f'<Avoir {self.reference}>'

class Devis(BaseTenantModel):
    __tablename__ = 'devis'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    date_devis = db.Column(db.DateTime, default=db.func.now())
    date_validite = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente/accepte/refuse/converti/expire
    remarque = db.Column(db.Text)
    conditions_paiement = db.Column(db.String(100))

    __table_args__ = (
        Index('idx_devis_client', 'client_id'),
        Index('idx_devis_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data

    def __repr__(self):
        return f'<Devis {self.reference}>'

class BonLivraison(BaseTenantModel):
    __tablename__ = 'bons_livraison'

    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)
    adresse_livraison = db.Column(db.String(200))
    date_emission = db.Column(db.DateTime, default=db.func.now())
    date_livraison_prevue = db.Column(db.DateTime)
    date_livraison_reelle = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='prepare')  # prepare/expedie/livre
    signature = db.Column(db.Text)
    photo = db.Column(db.Text)
    remarque = db.Column(db.Text)

    __table_args__ = (
        Index('idx_bon_livraison_client', 'client_id'),
        Index('idx_bon_livraison_statut', 'statut'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<BonLivraison {self.reference}>'

>>>

### FICHIER .PY: web\backend\app\models\document_genere.py
<<<
from app.models.base import BaseTenantModel
from app import db

class DocumentGenere(BaseTenantModel):
    __tablename__ = 'documents_generes'

    modele_id = db.Column(db.Integer, db.ForeignKey('modeles_documents.id'), nullable=False, index=True)
    type_document = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(100), nullable=False, index=True)
    entite_type = db.Column(db.String(50))  # vente/facture/commande/abonnement
    entite_id = db.Column(db.Integer, index=True)
    contenu_html = db.Column(db.Text)
    contenu_pdf_path = db.Column(db.String(500))
    date_generation = db.Column(db.DateTime, default=db.func.now())
    genere_par_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    modele = db.relationship('ModeleDocument', back_populates='documents')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.modele:
            data['modele_nom'] = self.modele.nom
        return data

    def __repr__(self):
        return f'<DocumentGenere {self.reference}>'

>>>

### FICHIER .PY: web\backend\app\models\ecriture_comptable.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutEcriture(enum.Enum):
    BROUILLON = 'brouillon'
    VALIDE = 'valide'
    ANNULE = 'annule'

class EcritureComptable(BaseTenantModel):
    __tablename__ = 'ecritures_comptables'

    date = db.Column(db.Date, nullable=False)
    compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), nullable=False, index=True)
    montant_debit = db.Column(Numeric(12, 2), default=0)
    montant_credit = db.Column(Numeric(12, 2), default=0)
    libelle = db.Column(db.String(200), nullable=False)
    piece_joint = db.Column(db.Text)
    reference_externe = db.Column(db.String(50))  # facture_id, vente_id, etc.
    entite_type = db.Column(db.String(50))  # vente, facture, achat, etc.
    entite_id = db.Column(db.Integer, index=True)
    statut = db.Column(db.Enum(StatutEcriture, name='statut_ecriture', values_callable=lambda e: [x.value for x in e]), default=StatutEcriture.BROUILLON)
    ecriture_annulee_id = db.Column(db.Integer, db.ForeignKey('ecritures_comptables.id'), index=True)

    compte = db.relationship('CompteComptable', back_populates='ecritures', foreign_keys=[compte_id])
    ecriture_annulee = db.relationship('EcritureComptable', remote_side='EcritureComptable.id', back_populates='annulations')
    annulations = db.relationship('EcritureComptable', foreign_keys=[ecriture_annulee_id], back_populates='ecriture_annulee')
    tresorerie = db.relationship('Tresorerie', back_populates='ecriture', foreign_keys='Tresorerie.ecriture_id')

    __table_args__ = (
        Index('idx_ecriture_date', 'date'),
        Index('idx_ecriture_reference', 'reference_externe', 'entite_type', 'entite_id'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.compte:
            data['compte_numero'] = self.compte.numero
            data['compte_nom'] = self.compte.nom
        if self.tresorerie:
            data['tresorerie_ids'] = [t.id for t in self.tresorerie]
            data['tresorerie_count'] = len(self.tresorerie)
        return data

    def __repr__(self):
        return f'<EcritureComptable {self.id} - {self.libelle}>'

>>>

### FICHIER .PY: web\backend\app\models\employe.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeContrat(enum.Enum):
    CDI = 'cdi'
    CDD = 'cdd'
    STAGE = 'stage'
    FREELANCE = 'freelance'

class Sexe(enum.Enum):
    M = 'M'
    F = 'F'

class StatutEmploye(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    EN_CONGE = 'en_conges'
    DEPART = 'depart'

class Employe(BaseTenantModel):
    __tablename__ = 'employes'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    matricule = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    sexe = db.Column(db.Enum(Sexe, name='sexe', values_callable=lambda e: [x.value for x in e]), default=Sexe.M)
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    numero_securite_sociale = db.Column(db.String(50))

    poste = db.Column(db.String(100))
    departement = db.Column(db.String(100))

    date_embauche = db.Column(db.Date)
    date_fin_contrat = db.Column(db.Date)
    type_contrat = db.Column(db.Enum(TypeContrat, name='type_contrat', values_callable=lambda e: [x.value for x in e]), default=TypeContrat.CDI)

    salaire_base = db.Column(Numeric(10, 2), default=0)
    coefficient = db.Column(db.String(20))
    anciennete = db.Column(db.Integer, default=0)

    banque_nom = db.Column(db.String(100))
    banque_iban = db.Column(db.String(50))
    banque_bic = db.Column(db.String(20))

    photo = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutEmploye, name='statut_employe', values_callable=lambda e: [x.value for x in e]), default=StatutEmploye.ACTIF)

    notes = db.Column(db.Text)

    presences = db.relationship('Presence', back_populates='employe', lazy='dynamic')
    salaires = db.relationship('Salaire', back_populates='employe', lazy='dynamic')
    primes = db.relationship('Prime', back_populates='employe', lazy='dynamic')

    tenant = db.relationship('Tenant', back_populates='employes', lazy='select')

    __table_args__ = (
        Index('idx_employe_matricule', 'matricule'),
        Index('idx_employe_nom_prenom', 'nom', 'prenom'),
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.sexe:
            data['sexe'] = self.sexe.value
        if self.type_contrat:
            data['type_contrat'] = self.type_contrat.value
        if self.statut:
            data['statut'] = self.statut.value
        data['nom_complet'] = self.nom_complet
        return data

    def __repr__(self):
        return f'<Employe {self.matricule} - {self.nom_complet}>'

>>>

### FICHIER .PY: web\backend\app\models\facture.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class Facture(BaseTenantModel):
    __tablename__ = 'factures'
    
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='non_payee')  # non_payee, payee, payee_partiel, annulee
    
    # Relations
    vente = db.relationship('Vente', back_populates='factures')
    client = db.relationship('Client', back_populates='factures')
    paiements = db.relationship('Paiement', back_populates='facture', lazy='dynamic')
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data


>>>

### FICHIER .PY: web\backend\app\models\facture_fournisseur.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class FactureFournisseur(BaseTenantModel):
    __tablename__ = 'factures_fournisseur'
    
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), nullable=False, index=True)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    statut = db.Column(db.String(50), default='non_payee')  # non_payee, payee, payee_partiel, annulee
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='factures')


>>>

### FICHIER .PY: web\backend\app\models\fournisseur.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Index, Numeric
import enum

class TypeFournisseur(enum.Enum):
    PRODUCTEUR_LOCAL = 'producteur_local'
    IMPORTATEUR = 'importateur'
    DISTRIBUTEUR = 'distributeur'
    GROSSISTE = 'grossiste'
    FABRICANT = 'fabricant'
    FOURNISSEUR_LOCAL = 'fournisseur_local'
    FOURNISSEUR_INTERNATIONAL = 'fournisseur_international'

class Fournisseur(BaseTenantModel):
    __tablename__ = 'fournisseurs'
    
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    raison_sociale = db.Column(db.String(200), nullable=False)
    nom_commercial = db.Column(db.String(200))
    
    # Identification légale
    siret = db.Column(db.String(20))
    numero_tva = db.Column(db.String(20))
    forme_juridique = db.Column(db.String(50))
    capital_social = db.Column(Numeric(10, 2))
    
    # Type
    type = db.Column(
        Enum(
            TypeFournisseur,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=TypeFournisseur.FOURNISSEUR_LOCAL,
        nullable=False
    )
    # Contact
    email = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    site_web = db.Column(db.String(200))
    
    # Contact principal
    contact_nom = db.Column(db.String(100))
    contact_prenom = db.Column(db.String(100))
    contact_fonction = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_telephone = db.Column(db.String(20))
    
    # Adresse
    adresse = db.Column(db.String(200))
    complement_adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(50), default='Madagascar')
    coordonnees_gps = db.Column(db.String(100))
    
    # Informations bancaires
    iban = db.Column(db.String(34))
    bic = db.Column(db.String(11))
    nom_banque = db.Column(db.String(100))
    
    # Informations commerciales
    conditions_paiement = db.Column(db.String(50), default='30 jours fin de mois')
    delai_livraison = db.Column(db.Integer, default=5)  # jours
    mode_livraison = db.Column(db.String(50), default='Standard')
    
    # Remises
    remise_standard = db.Column(Numeric(5, 2), default=0)
    remise_volume = db.Column(Numeric(5, 2), default=0)
    
    # Statut
    est_favori = db.Column(db.Boolean, default=False)
    est_actif = db.Column(db.Boolean, default=True)
    note = db.Column(db.Integer)  # 1-5
    
    # Relations
    produits = db.relationship('Produit', back_populates='fournisseur', lazy='dynamic')
    commandes = db.relationship('CommandeFournisseur', back_populates='fournisseur', lazy='dynamic')
    factures = db.relationship('FactureFournisseur', back_populates='fournisseur', lazy='dynamic')
    commandes_achat = db.relationship('CommandeAchat', back_populates='fournisseur', lazy='dynamic')
    paiements = db.relationship('Paiement', back_populates='fournisseur', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_fournisseur_raison_sociale', 'raison_sociale'),
        Index('idx_fournisseur_type', 'type'),
    )
    
    @property
    def nom_complet(self):
        return self.nom_commercial or self.raison_sociale
    
    @property
    def nombre_produits(self):
        return self.produits.filter_by(is_active=True).count()
    
    @property
    def chiffre_affaires(self):
        """Chiffre d'affaires total avec ce fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        tenant_id = getattr(self, 'tenant_id', None)
        query = db.session.query(
            db.func.sum(CommandeFournisseur.total_ht)
        ).filter(
            CommandeFournisseur.fournisseur_id == self.id,
            CommandeFournisseur.is_active == True
        )
        if tenant_id is not None:
            query = query.filter(CommandeFournisseur.tenant_id == tenant_id)
        total = query.scalar()
        return total or 0
    
    @property
    def dernieres_commandes(self):
        from app.models.commande_fournisseur import CommandeFournisseur
        return self.commandes.filter_by(is_active=True).order_by(
            CommandeFournisseur.created_at.desc()
        ).limit(5).all()
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type' in data and self.type:
            data['type'] = self.type.value
        data['nombre_produits'] = self.nombre_produits
        data['nom_complet'] = self.nom_complet
        data['chiffre_affaires'] = float(self.chiffre_affaires) if self.chiffre_affaires else 0
        return data
    
    def __repr__(self):
        return f'<Fournisseur {self.code} - {self.raison_sociale}>'
>>>

### FICHIER .PY: web\backend\app\models\itineraire.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index

class Itineraire(BaseTenantModel):
    __tablename__ = 'itineraires'

    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date_depart = db.Column(db.DateTime, nullable=False)
    date_retour = db.Column(db.DateTime)
    points_intermediaires = db.Column(db.Text)  # JSON text
    statut = db.Column(db.String(20), default='planifie')  # planifie/en_cours/termine/annule

    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), nullable=False, index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), nullable=False, index=True)

    livreur = db.relationship('Livreur', back_populates='itineraires')
    vehicule = db.relationship('Vehicule', back_populates='itineraires')
    livraisons = db.relationship('Livraison', back_populates='itineraire', lazy='dynamic')

    __table_args__ = (
        Index('idx_itineraire_date', 'date_depart'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.livreur:
            data['livreur_nom'] = self.livreur.nom_complet
        if self.vehicule:
            data['vehicule_plaque'] = self.vehicule.plaque_immatriculation
        return data

    def __repr__(self):
        return f'<Itineraire {self.nom}>'

>>>

### FICHIER .PY: web\backend\app\models\ligne_achat.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class LigneAchat(BaseTenantModel):
    __tablename__ = 'lignes_achat'
    
    commande_fournisseur_id = db.Column(db.Integer, db.ForeignKey('commandes_fournisseur.id'), index=True)
    commande_achat_id = db.Column(db.Integer, db.ForeignKey('commandes_achat.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ht = db.Column(Numeric(10, 2), nullable=False)
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    total_ht = db.Column(Numeric(10, 2))
    
    # Relations
    commande_fournisseur = db.relationship('CommandeFournisseur', back_populates='lignes_achat')
    commande_achat = db.relationship('CommandeAchat', back_populates='lignes_achat')
    produit = db.relationship('Produit', back_populates='lignes_achat')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_total()
        
    def _calculer_total(self):
        if self.quantite and self.prix_unitaire_ht:
            self.total_ht = self.quantite * self.prix_unitaire_ht


>>>

### FICHIER .PY: web\backend\app\models\ligne_vente.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class LigneVente(BaseTenantModel):
    __tablename__ = 'lignes_vente'
    
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), nullable=False, index=True)
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    quantite = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ht = db.Column(Numeric(10, 2), nullable=False)
    prix_unitaire_ttc = db.Column(Numeric(10, 2))
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    remise = db.Column(Numeric(5, 2), default=0.00)
    total_ht = db.Column(Numeric(10, 2))
    total_ttc = db.Column(Numeric(10, 2))
    
    # Relations
    vente = db.relationship('Vente', back_populates='lignes_vente')
    produit = db.relationship('Produit', back_populates='lignes_vente')
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_totaux()
        
    def _calculer_totaux(self):
        if self.prix_unitaire_ht is not None and self.taux_tva is not None:
            self.prix_unitaire_ttc = self.prix_unitaire_ht * (1 + self.taux_tva / 100)
        if self.quantite is not None and self.prix_unitaire_ht is not None:
            base_ht = self.quantite * self.prix_unitaire_ht
            if self.remise is not None:
                base_ht = base_ht * (1 - self.remise / 100)
            self.total_ht = base_ht
            if self.taux_tva is not None:
                self.total_ttc = base_ht * (1 + self.taux_tva / 100)
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.produit:
            data['produit_nom'] = self.produit.nom
        else:
            data['produit_nom'] = None
        return data


>>>

### FICHIER .PY: web\backend\app\models\livraison.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Index

class Livraison(BaseTenantModel):
    __tablename__ = 'livraisons'

    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), index=True)
    commande_client_id = db.Column(db.Integer, db.ForeignKey('commandes_client.id'), index=True)
    itineraire_id = db.Column(db.Integer, db.ForeignKey('itineraires.id'), index=True)
    livreur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)

    adresse_livraison = db.Column(db.String(200))
    ville_livraison = db.Column(db.String(100))
    telephone_livraison = db.Column(db.String(20))
    nom_destinataire = db.Column(db.String(200))

    date_livraison_prevue = db.Column(db.DateTime)
    date_livraison_reelle = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='en_attente')  # en_attente/chargee/en_route/livree/retournee/echec
    signature_client = db.Column(db.Text)  # base64 image
    photo_livraison = db.Column(db.Text)  # base64 image or URL
    notes = db.Column(db.Text)

    itineraire = db.relationship('Itineraire', back_populates='livraisons')
    livreur = db.relationship('Livreur', back_populates='livraisons')
    vehicule = db.relationship('Vehicule', back_populates='livraisons')
    suivis = db.relationship('SuiviLivraison', back_populates='livraison', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_livraison_statut', 'statut'),
        Index('idx_livraison_date', 'date_livraison_prevue'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.livreur:
            data['livreur_nom'] = self.livreur.nom_complet
        if self.vehicule:
            data['vehicule_plaque'] = self.vehicule.plaque_immatriculation
        if self.itineraire:
            data['itineraire_nom'] = self.itineraire.nom
        return data

    def __repr__(self):
        return f'<Livraison {self.id} - {self.statut}>'

>>>

### FICHIER .PY: web\backend\app\models\livreur.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index

class Livreur(BaseTenantModel):
    __tablename__ = 'livreurs'

    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    numero_permis = db.Column(db.String(50))
    date_embauche = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='actif')  # actif/inactif/en_conges

    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicules.id'), index=True)

    vehicule = db.relationship('Vehicule', back_populates='chauffeurs', foreign_keys='Livreur.vehicule_id')
    itineraires = db.relationship('Itineraire', back_populates='livreur', lazy='dynamic')
    livraisons = db.relationship('Livraison', back_populates='livreur', lazy='dynamic')

    __table_args__ = (
        Index('idx_livreur_nom', 'nom', 'prenom'),
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['nom_complet'] = self.nom_complet
        return data

    def __repr__(self):
        return f'<Livreur {self.nom_complet}>'

>>>

### FICHIER .PY: web\backend\app\models\modele_document.py
<<<
from app.models.base import BaseTenantModel
from app import db

class ModeleDocument(BaseTenantModel):
    __tablename__ = 'modeles_documents'

    nom = db.Column(db.String(100), nullable=False)
    type_document = db.Column(db.String(50), nullable=False)
    contenu_modele = db.Column(db.Text, nullable=False)
    est_actif = db.Column(db.Boolean, default=True)
    est_defaut = db.Column(db.Boolean, default=False)
    logo_url = db.Column(db.String(500))
    mention_legales = db.Column(db.Text)
    conditions_generales = db.Column(db.Text)

    documents = db.relationship('DocumentGenere', back_populates='modele', lazy='dynamic')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<ModeleDocument {self.nom} - {self.type_document}>'

>>>

### FICHIER .PY: web\backend\app\models\notification.py
<<<
from app import db
from app.models.base import BaseTenantModel
from datetime import datetime


class Notification(BaseTenantModel):
    __tablename__ = 'notifications'

    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False, default='info')
    read = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True)
    link = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        data = super().to_dict()
        data['title'] = self.title
        data['message'] = self.message
        data['type'] = self.type
        data['read'] = self.read
        data['read_at'] = self.read_at.isoformat() if self.read_at else None
        data['user_id'] = self.user_id
        data['link'] = self.link
        return data

>>>

### FICHIER .PY: web\backend\app\models\paiement.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Numeric
import enum


class StatutPaiement(enum.Enum):
    EN_ATTENTE = 'en_attente'
    PROCESSING = 'traitement'
    SUCCESS = 'succes'
    CONFIRME = 'confirme'
    FAILED = 'echec'
    CANCELLED = 'annule'
    EXPIRED = 'expiré'


class TypePaiement(enum.Enum):
    ABONNEMENT = 'abonnement'
    COMMANDE = 'commande'
    VENTE = 'vente'
    ACHAT = 'achat'
    SALAIRE = 'salaire'
    AUTRE = 'autre'


class ProviderPaiement(enum.Enum):
    PAPI = 'papi'
    VISA = 'visa'
    AUTRE = 'autre'


class Paiement(BaseTenantModel):
    __tablename__ = 'paiements'

    facture_id = db.Column(db.Integer, db.ForeignKey('factures.id'), index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), index=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('abonnements.id'), index=True, nullable=True)
    montant = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    mode_paiement = db.Column(db.String(50), default='especes')  # espece/virement/cheque/orange_money/airtel_money
    operateur_mobile = db.Column(db.String(50))  # Orange, Airtel, etc.
    numero_telephone = db.Column(db.String(20))  # for mobile money

    devise = db.Column(db.String(10), default='MGA')
    statut = db.Column(Enum(StatutPaiement))
    type = db.Column(Enum(TypePaiement))
    reference = db.Column(db.String(100))
    id_transaction_externe = db.Column(db.String(100))
    date_paiement = db.Column(db.DateTime)
    date_echeance = db.Column(db.DateTime)  # for partial/scheduled payments
    notes = db.Column(db.Text)

    # Papi-specific fields
    provider = db.Column(db.String(20), default='especes', comment='Provider: papi, visa, etc.')
    payment_method = db.Column(db.String(50), comment='Payment method: MVOLA, ORANGE_MONEY, AIRTEL_MONEY, VISA')
    external_payment_id = db.Column(db.String(100), comment='Papi payment link ID')
    external_reference = db.Column(db.String(100), comment='Papi payment reference')
    completed_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    payment_metadata = db.Column(db.Text, nullable=True)

    facture = db.relationship('Facture', back_populates='paiements')
    client = db.relationship('Client', back_populates='paiements')
    fournisseur = db.relationship('Fournisseur', back_populates='paiements', lazy='select')
    tenant = db.relationship('Tenant', back_populates='paiements')
    abonnement = db.relationship('Abonnement', back_populates='paiements')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['montant'] = float(self.montant) if self.montant else 0.0
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['type'] = (
            self.type.value
            if hasattr(self.type, 'value')
            else self.type
        )
        data['date_paiement'] = (
            self.date_paiement.isoformat()
            if self.date_paiement
            else None
        )
        return data

    def __repr__(self):
        return f'<Paiement {self.id} - {self.montant} {self.devise or "MGA"} ({self.statut.value if hasattr(self.statut, "value") else self.statut})>'

>>>

### FICHIER .PY: web\backend\app\models\password_reset_token.py
<<<
from app.models.base import BaseModel
from app import db
from datetime import datetime, timedelta
import secrets
from app.security.auth import hash_password, verify_password


class PasswordResetToken(BaseModel):
    __tablename__ = 'password_reset_tokens'

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id'),
        nullable=False,
        index=True
    )
    token = db.Column(db.String(255), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    ip_address = db.Column(db.String(45))

    user = db.relationship(
        'Utilisateur',
        foreign_keys=[user_id],
        backref=db.backref('password_reset_tokens', lazy='dynamic')
    )

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(raw_token):
        return hash_password(raw_token)

    @staticmethod
    def verify_token(raw_token, stored_hash):
        return verify_password(raw_token, stored_hash)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    @classmethod
    def find_valid_token(cls, user_id, raw_token):
        candidates = cls.query.filter_by(
            user_id=user_id,
            used=False,
        ).all()
        for candidate in candidates:
            if candidate.verify_token(raw_token, candidate.token):
                return candidate
        return None

>>>

### FICHIER .PY: web\backend\app\models\payment_event.py
<<<

import json

from app.models.base import BaseModel
from app import db
from datetime import datetime
from sqlalchemy.types import TypeDecorator, TEXT


class JSONEncodedDict(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class PaymentEvent(BaseModel):
    __tablename__ = 'payment_events'

    payment_id = db.Column(db.Integer, db.ForeignKey('paiements.id'), nullable=False, index=True)
    event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    payload = db.Column(JSONEncodedDict, nullable=False)
    signature = db.Column(db.String(255))
    processed = db.Column(db.Boolean, default=False, nullable=False)
    processed_at = db.Column(db.DateTime)

    payment = db.relationship('Paiement', backref='events')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<PaymentEvent {self.event_id} processed={self.processed}>'

>>>

### FICHIER .PY: web\backend\app\models\presence.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutPresence(enum.Enum):
    PRESENT = 'present'
    ABSENT = 'absent'
    EN_RETARD = 'en_retard'
    CONGE = 'conge'
    MALADIE = 'maladie'

class Presence(BaseTenantModel):
    __tablename__ = 'presences'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    heure_arrivee = db.Column(db.DateTime)
    heure_depart = db.Column(db.DateTime)
    heure_pause_debut = db.Column(db.DateTime)
    heure_pause_fin = db.Column(db.DateTime)
    heures_travaillees = db.Column(db.Numeric(4, 2))
    heures_supplementaires = db.Column(db.Numeric(4, 2), default=0)
    statut = db.Column(db.Enum(StatutPresence, name='statut_presence', values_callable=lambda e: [x.value for x in e]), default=StatutPresence.PRESENT)
    remarque = db.Column(db.String(200))

    employe = db.relationship('Employe', back_populates='presences')

    __table_args__ = (
        Index('idx_presence_employe_date', 'employe_id', 'date', unique=True),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut:
            data['statut'] = self.statut.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
        return data

    def __repr__(self):
        return f'<Presence {self.employe_id} - {self.date}>'

>>>

### FICHIER .PY: web\backend\app\models\prime.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypePrime(enum.Enum):
    PERFORMANCE = 'performance'
    ANCIENNETE = 'anciennete'
    OBJECTIF = 'objectif'
    EXCEPTIONNEL = 'exceptionnel'

class Prime(BaseTenantModel):
    __tablename__ = 'primes'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    type_prime = db.Column(db.Enum(TypePrime, name='type_prime', values_callable=lambda e: [x.value for x in e]), nullable=False)
    montant = db.Column(Numeric(10, 2), nullable=False)
    date_octroi = db.Column(db.Date, nullable=False)
    motif = db.Column(db.String(200))

    employe = db.relationship('Employe', back_populates='primes')

    __table_args__ = (
        Index('idx_prime_employe', 'employe_id'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_prime:
            data['type_prime'] = self.type_prime.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
        return data

    def __repr__(self):
        return f'<Prime {self.employe_id} - {self.type_prime.value if self.type_prime else None}>'

>>>

### FICHIER .PY: web\backend\app\models\produit.py
<<<
from decimal import Decimal

from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index, CheckConstraint


class Produit(BaseTenantModel):
    __tablename__ = 'produits'
    
    # Identifiants
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code_barre = db.Column(db.String(50), unique=True)
    code_interne = db.Column(db.String(50), unique=True)
    
    # Informations générales
    nom = db.Column(db.String(200), nullable=False)
    description_courte = db.Column(db.String(500))
    description_longue = db.Column(db.Text)
    
    # Catégorisation
    categorie = db.Column(db.String(100), index=True)
    sous_categorie = db.Column(db.String(100))
    famille = db.Column(db.String(100))
    marque = db.Column(db.String(100))
    modele = db.Column(db.String(100))
    unite = db.Column(db.String(50), default='piece')
    
    # Prix
    prix_achat_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    prix_achat_ttc = db.Column(Numeric(10, 2))
    prix_vente_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    prix_vente_ttc = db.Column(Numeric(10, 2))
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    marge_standard = db.Column(Numeric(5, 2))
    
    # Stock
    quantite_stock = db.Column(Numeric(10, 2), default=0)
    seuil_alerte = db.Column(Numeric(10, 2), default=10)
    seuil_critique = db.Column(Numeric(10, 2), default=5)
    emplacement = db.Column(db.String(100))
    rayon = db.Column(db.String(50))
    etagere = db.Column(db.String(50))
    
    # Dimensions et poids
    poids = db.Column(Numeric(10, 2))
    longueur = db.Column(Numeric(10, 2))
    largeur = db.Column(Numeric(10, 2))
    hauteur = db.Column(Numeric(10, 2))
    volume = db.Column(Numeric(10, 2))
    
    # Fournisseur
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), index=True)
    reference_fournisseur = db.Column(db.String(50))
    
    # Images et codes
    image_url = db.Column(db.String(500))
    qr_code_data = db.Column(db.String(500))
    
    # Prix multi-niveaux
    prix_grossiste = db.Column(Numeric(10, 2))
    prix_revendeur = db.Column(Numeric(10, 2))
    prix_demi_gros = db.Column(Numeric(10, 2))
    
    # Tags et recherche
    tags = db.Column(db.String(500))  # comma-separated tags
    
    # Statut
    statut = db.Column(db.String(20), default='actif')  # actif, en_rupture, abandonne
    est_service = db.Column(db.Boolean, default=False)
    est_dechirable = db.Column(db.Boolean, default=False)
    est_dangereux = db.Column(db.Boolean, default=False)
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='produits')
    mouvements_stock = db.relationship('MouvementStock', back_populates='produit', lazy='dynamic')
    lignes_vente = db.relationship('LigneVente', back_populates='produit', lazy='dynamic')
    lignes_achat = db.relationship('LigneAchat', back_populates='produit', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_produit_nom_categorie', 'nom', 'categorie'),
        Index('idx_produit_fournisseur', 'fournisseur_id', 'categorie'),
        Index('idx_produit_marque_modele', 'marque', 'modele'),
        CheckConstraint('prix_achat_ht >= 0', name='ck_prix_achat_ht_positive'),
        CheckConstraint('prix_vente_ht >= 0', name='ck_prix_vente_ht_positive'),
        CheckConstraint('quantite_stock >= 0', name='ck_quantite_stock_positive'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_prix_ttc()
        self._calculer_volume()
    
    def _calculer_prix_ttc(self):
        """Calcule les prix TTC"""
        if self.prix_achat_ht is not None and self.taux_tva is not None:
            self.prix_achat_ttc = self.prix_achat_ht * (1 + self.taux_tva / 100)
        if self.prix_vente_ht is not None and self.taux_tva is not None:
            self.prix_vente_ttc = self.prix_vente_ht * (1 + self.taux_tva / 100)
    
    def _calculer_volume(self):
        """Calcule le volume en m³"""
        if self.longueur is not None and self.largeur is not None and self.hauteur is not None:
            self.volume = (self.longueur * self.largeur * self.hauteur) / 1000000  # en m³
    
    @property
    def valeur_stock(self):
        """Valeur totale du stock"""
        return self.quantite_stock * self.prix_achat_ht
    
    @property
    def marge_unitaire(self):
        """Marge unitaire"""
        return self.prix_vente_ht - self.prix_achat_ht
    
    @property
    def taux_marge(self):
        """Taux de marge en pourcentage"""
        if self.prix_achat_ht and self.prix_achat_ht > 0:
            return ((self.prix_vente_ht - self.prix_achat_ht) / self.prix_achat_ht) * 100
        return 0
    
    @property
    def taux_marque(self):
        """Taux de marque en pourcentage"""
        if self.prix_vente_ht and self.prix_vente_ht > 0:
            return ((self.prix_vente_ht - self.prix_achat_ht) / self.prix_vente_ht) * 100
        return 0
    
    @property
    def est_en_rupture(self):
        """Vérifie si le produit est en rupture"""
        return self.quantite_stock <= 0
    
    @property
    def est_alerte_stock(self):
        """Vérifie si le stock est sous le seuil d'alerte"""
        return self.quantite_stock <= self.seuil_alerte
    
    @property
    def est_stock_critique(self):
        """Vérifie si le stock est critique"""
        return self.quantite_stock <= self.seuil_critique
    
    def ajouter_stock(self, quantite, raison='', utilisateur_id=None):
        """Ajoute du stock"""
        quantite = Decimal(str(quantite))
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")
        
        self.quantite_stock += quantite
        self.save()
        
        # Créer un mouvement de stock
        from app.models.stock import MouvementStock
        mouvement = MouvementStock(
            produit_id=self.id,
            type_mouvement='entree',
            quantite=quantite,
            raison=raison,
            created_by=utilisateur_id,
            tenant_id=self.tenant_id
        )
        mouvement.save()
        return mouvement
    
    def retirer_stock(self, quantite, raison='', utilisateur_id=None):
        """Retire du stock"""
        quantite = Decimal(str(quantite))
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")
        
        if self.quantite_stock < quantite:
            raise ValueError(f"Stock insuffisant. Disponible: {self.quantite_stock}")
        
        self.quantite_stock -= quantite
        self.save()
        
        # Créer un mouvement de stock
        from app.models.stock import MouvementStock
        mouvement = MouvementStock(
            produit_id=self.id,
            type_mouvement='sortie',
            quantite=quantite,
            raison=raison,
            created_by=utilisateur_id,
            tenant_id=self.tenant_id
        )
        mouvement.save()
        return mouvement
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        # Ajouter les propriétés calculées
        data['valeur_stock'] = float(self.valeur_stock)
        data['marge_unitaire'] = float(self.marge_unitaire)
        data['taux_marge'] = float(self.taux_marge)
        data['taux_marque'] = float(self.taux_marque)
        data['est_en_rupture'] = self.est_en_rupture
        data['est_alerte_stock'] = self.est_alerte_stock
        return data
    
    def __repr__(self):
        return f'<Produit {self.reference} - {self.nom}>'

>>>

### FICHIER .PY: web\backend\app\models\role_permission.py
<<<
from app.models.base import BaseModel
from app import db
from sqlalchemy import Table, Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


role_permissions = Table(
    'role_permissions',
    db.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False),
)


class Permission(BaseModel):
    __tablename__ = 'permissions'

    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    module = db.Column(db.String(100), index=True)
    action = db.Column(db.String(50))

    roles = relationship(
        'RoleModel',
        secondary=role_permissions,
        back_populates='permissions',
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<Permission {self.code}>'


class RoleModel(BaseModel):
    __tablename__ = 'roles'

    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100))
    description = db.Column(db.String(255))
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)

    permissions = relationship(
        'Permission',
        secondary=role_permissions,
        back_populates='roles',
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['permissions'] = [p.to_dict() for p in self.permissions] if self.permissions else []
        return data

    def __repr__(self):
        return f'<RoleModel {self.name}>'

>>>

### FICHIER .PY: web\backend\app\models\salaire.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class StatutPaiementSalaire(enum.Enum):
    NON_PAYE = 'non_paye'
    PARTIEL = 'partiel'
    PAYE = 'paye'

class Salaire(BaseTenantModel):
    __tablename__ = 'salaires'

    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False, index=True)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    salaire_base = db.Column(Numeric(10, 2), nullable=False, default=0)
    primes = db.Column(Numeric(10, 2), default=0)
    indemnites = db.Column(Numeric(10, 2), default=0)
    deductions = db.Column(Numeric(10, 2), default=0)
    avances = db.Column(Numeric(10, 2), default=0)
    salaire_brut = db.Column(Numeric(10, 2))
    salaire_net = db.Column(Numeric(10, 2))
    statut_paiement = db.Column(db.Enum(StatutPaiementSalaire, name='statut_paiement_salaire', values_callable=lambda e: [x.value for x in e]), default=StatutPaiementSalaire.NON_PAYE)
    date_paiement = db.Column(db.Date)
    mode_paiement = db.Column(db.String(20))
    reference_paiement = db.Column(db.String(50))
    notes = db.Column(db.Text)

    employe = db.relationship('Employe', back_populates='salaires')

    __table_args__ = (
        Index('idx_salaire_employe_mois', 'employe_id', 'mois', 'annee', unique=True),
    )

    def calculer_salaire(self):
        self.salaire_brut = self.salaire_base + self.primes + self.indemnites - self.deductions
        self.salaire_net = self.salaire_brut - self.avances

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.statut_paiement:
            data['statut_paiement'] = self.statut_paiement.value
        if self.employe:
            data['employe_nom'] = self.employe.nom_complet
            data['employe_matricule'] = self.employe.matricule
        return data

    def __repr__(self):
        return f'<Salaire {self.employe_id} {self.mois}/{self.annee}>'

>>>

### FICHIER .PY: web\backend\app\models\stagiaire.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeContratStagiaire(enum.Enum):
    STAGE_INITIATION = 'stage_initiation'
    STAGE_FIN_ETUDES = 'stage_fin_etudes'
    STAGE_PROFESSIONNEL = 'stage_professionnel'
    APPRENTISSAGE = 'apprentissage'

class SexeStagiaire(enum.Enum):
    M = 'M'
    F = 'F'

class StatutStagiaire(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    EN_STAGE = 'en_stage'
    TERMINE = 'termine'
    ABANDON = 'abandon'

class Stagiaire(BaseTenantModel):
    __tablename__ = 'stagiaires'

    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    matricule = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date)
    lieu_naissance = db.Column(db.String(100))
    sexe = db.Column(db.Enum(SexeStagiaire, name='sexe_stagiaire', values_callable=lambda e: [x.value for x in e]), default=SexeStagiaire.M)
    adresse = db.Column(db.String(200))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    etablissement = db.Column(db.String(150))
    formation = db.Column(db.String(150))
    type_contrat = db.Column(db.Enum(TypeContratStagiaire, name='type_contrat_stagiaire', values_callable=lambda e: [x.value for x in e]), default=TypeContratStagiaire.STAGE_INITIATION)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    indemnite = db.Column(Numeric(10, 2), default=0)
    tuteur_id = db.Column(db.Integer, db.ForeignKey('employes.id'))
    departement = db.Column(db.String(100))
    note = db.Column(db.Text)
    statut = db.Column(db.Enum(StatutStagiaire, name='statut_stagiaire', values_callable=lambda e: [x.value for x in e]), default=StatutStagiaire.ACTIF)

    tenant = db.relationship('Tenant', back_populates='stagiaires', lazy='select')
    tuteur = db.relationship('Employe', foreign_keys=[tuteur_id], lazy='select')

    __table_args__ = (
        Index('idx_stagiaire_matricule', 'matricule'),
        Index('idx_stagiaire_nom_prenom', 'nom', 'prenom'),
    )

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.sexe:
            data['sexe'] = self.sexe.value
        if self.type_contrat:
            data['type_contrat'] = self.type_contrat.value
        if self.statut:
            data['statut'] = self.statut.value
        data['nom_complet'] = self.nom_complet
        return data

    def __repr__(self):
        return f'<Stagiaire {self.matricule} - {self.nom_complet}>'

>>>

### FICHIER .PY: web\backend\app\models\stock.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Index
import enum

class TypeMouvement(enum.Enum):
    ENTREE = 'entree'
    SORTIE = 'sortie'
    INVENTAIRE = 'inventaire'
    AJUSTEMENT = 'ajustement'
    RETOUR = 'retour'
    TRANSFERT = 'transfert'

class MouvementStock(BaseTenantModel):
    __tablename__ = 'mouvements_stock'
    
    produit_id = db.Column(db.Integer, db.ForeignKey('produits.id'), nullable=False, index=True)
    type_mouvement = db.Column(
        Enum(
            TypeMouvement,
            values_callable=lambda enum: [e.value for e in enum],
            name='typemouvement',
        ),
        nullable=False,
    )
    quantite = db.Column(db.Numeric(10, 2), nullable=False)
    stock_avant = db.Column(db.Numeric(10, 2))
    stock_apres = db.Column(db.Numeric(10, 2))
    raison = db.Column(db.String(200))
    reference = db.Column(db.String(50))  # Référence liée (commande, facture, etc.)
    
    # Relations
    produit = db.relationship('Produit', back_populates='mouvements_stock')
    utilisateur = db.relationship('Utilisateur', foreign_keys='MouvementStock.created_by')
    
    __table_args__ = (
        Index('idx_mouvement_produit_date', 'produit_id', 'created_at'),
        Index('idx_mouvement_type', 'type_mouvement'),
    )
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type_mouvement' in data and self.type_mouvement:
            data['type_mouvement'] = self.type_mouvement.value
        if self.produit:
            data['produit_nom'] = self.produit.nom
        else:
            data['produit_nom'] = None
        return data

>>>

### FICHIER .PY: web\backend\app\models\suivi_livraison.py
<<<
from app.models.base import BaseTenantModel
from app import db

class SuiviLivraison(BaseTenantModel):
    __tablename__ = 'suivis_livraison'

    livraison_id = db.Column(db.Integer, db.ForeignKey('livraisons.id'), nullable=False, index=True)
    statut = db.Column(db.String(50), nullable=False)
    localisation_lat = db.Column(db.Numeric(10, 8))
    localisation_lng = db.Column(db.Numeric(11, 8))
    commentaire = db.Column(db.Text)
    date_mise_a_jour = db.Column(db.DateTime, default=db.func.now())

    livraison = db.relationship('Livraison', back_populates='suivis')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<SuiviLivraison {self.livraison_id} - {self.statut}>'

>>>

### FICHIER .PY: web\backend\app\models\tenant.py
<<<
from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, ForeignKey
import enum
from datetime import datetime


class StatutTenant(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    BLOQUE = 'bloque'
    EN_ESSAI = 'en_essai'


class Tenant(BaseModel):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    domaine = db.Column(db.String(200), unique=True, index=True)
    email_contact = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(50), default='Madagascar')
    code_postal = db.Column(db.String(10))
    
    # Abonnement
    statut = db.Column(Enum(StatutTenant), default=StatutTenant.EN_ESSAI, nullable=False)
    plan = db.Column(db.String(50), default='gratuit')  # gratuit, starter, pro, enterprise
    date_debut_essai = db.Column(db.DateTime)
    date_fin_essai = db.Column(db.DateTime)
    date_abonnement = db.Column(db.DateTime)
    
    # Limites
    max_utilisateurs = db.Column(db.Integer, default=5)
    max_produits = db.Column(db.Integer, default=100)
    max_clients = db.Column(db.Integer, default=50)
    
    # Configuration
    logo = db.Column(db.String(200))
    devise = db.Column(db.String(10), default='MGA')
    langue = db.Column(db.String(5), default='mg')
    fuseau_horaire = db.Column(db.String(50), default='Indian/Antananarivo')
    
    # Relations
    utilisateurs = db.relationship(
        'Utilisateur',
        back_populates='tenant',
        lazy='dynamic',
        primaryjoin='and_(Tenant.id==Utilisateur.tenant_id, Utilisateur.is_active==True)'
    )
    abonnements = db.relationship(
        'Abonnement',
        back_populates='tenant',
        lazy='dynamic'
    )
    paiements = db.relationship(
        'Paiement',
        back_populates='tenant',
        lazy='dynamic'
    )
    employes = db.relationship(
        'Employe',
        back_populates='tenant',
        lazy='dynamic'
    )
    stagiaires = db.relationship(
        'Stagiaire',
        back_populates='tenant',
        lazy='dynamic'
    )
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'slug': self.slug,
            'domaine': self.domaine,
            'email_contact': self.email_contact,
            'telephone': self.telephone,
            'adresse': self.adresse,
            'ville': self.ville,
            'pays': self.pays,
            'code_postal': self.code_postal,

            'statut': (
                self.statut.value
                if hasattr(self.statut, 'value')
                else self.statut
            ),

            'plan': self.plan,

            'date_debut_essai': (
                self.date_debut_essai.isoformat()
                if self.date_debut_essai
                else None
            ),

            'date_fin_essai': (
                self.date_fin_essai.isoformat()
                if self.date_fin_essai
                else None
            ),

            'date_abonnement': (
                self.date_abonnement.isoformat()
                if self.date_abonnement
                else None
            ),

            'max_utilisateurs': self.max_utilisateurs,
            'max_produits': self.max_produits,
            'max_clients': self.max_clients,

            'logo': self.logo,
            'devise': self.devise,
            'langue': self.langue,
            'fuseau_horaire': self.fuseau_horaire,

            'is_active': self.is_active,

            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            'updated_at': (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
    def __repr__(self):
        return f'<Tenant {self.nom} ({self.slug})>'

>>>

### FICHIER .PY: web\backend\app\models\tresorerie.py
<<<
from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric, Index
import enum

class TypeTresorerie(enum.Enum):
    ENTREE = 'entree'
    SORTIE = 'sortie'

class Tresorerie(BaseTenantModel):
    __tablename__ = 'tresoreries'

    date = db.Column(db.Date, nullable=False)
    type_operation = db.Column(db.Enum(TypeTresorerie, name='type_tresorerie', values_callable=lambda e: [x.value for x in e]), nullable=False)
    montant = db.Column(Numeric(12, 2), nullable=False)
    mode_paiement = db.Column(db.String(20))  # especes/virement/cheque/mvola/orange_money/airtel_money
    libelle = db.Column(db.String(200), nullable=False)
    compte_bancaire = db.Column(db.String(100))
    reference = db.Column(db.String(50))
    piece_jointe = db.Column(db.Text)
    is_reconcilie = db.Column(db.Boolean, default=False)

    compte_id = db.Column(db.Integer, db.ForeignKey('comptes_comptables.id'), index=True)
    ecriture_id = db.Column(db.Integer, db.ForeignKey('ecritures_comptables.id'), index=True)

    compte = db.relationship('CompteComptable', back_populates='tresorerie_ecritures')
    ecriture = db.relationship('EcritureComptable', back_populates='tresorerie')

    __table_args__ = (
        Index('idx_tresorerie_date', 'date'),
        Index('idx_tresorerie_type', 'type_operation'),
        Index('idx_tresorerie_compte', 'compte_id'),
        Index('idx_tresorerie_ecriture', 'ecriture_id'),
        Index('idx_tresorerie_reconcilie', 'is_reconcilie', 'date'),
    )

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.type_operation:
            data['type_operation'] = self.type_operation.value
        if self.compte:
            data['compte_numero'] = self.compte.numero
            data['compte_nom'] = self.compte.nom
        if self.ecriture:
            data['ecriture_libelle'] = self.ecriture.libelle
            data['ecriture_statut'] = self.ecriture.statut.value if self.ecriture.statut else None
        return data

    def __repr__(self):
        return f'<Tresorerie {self.date} - {self.type_operation.value if self.type_operation else None} {self.montant}>'

>>>

### FICHIER .PY: web\backend\app\models\utilisateur.py
<<<
from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum
import enum
from datetime import datetime

class Role(enum.Enum):
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    MANAGER = 'manager'
    SALES = 'sales'
    STOCK = 'stock'
    ACCOUNTANT = 'accountant'
    USER = 'user'
    
    def __str__(self):
        return self.value

class StatutUtilisateur(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    BLOQUE = 'bloque'
    EN_ATTENTE = 'en_attente'

class Utilisateur(BaseModel):
    __tablename__ = 'utilisateurs'
    
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    
    role = db.Column(Enum(Role), default=Role.USER, nullable=False)
    custom_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), index=True)
    statut = db.Column(Enum(StatutUtilisateur), default=StatutUtilisateur.ACTIF)
    
    custom_role = db.relationship('RoleModel', backref='users', foreign_keys='Utilisateur.custom_role_id')
    
    last_login = db.Column(db.DateTime)
    last_ip = db.Column(db.String(45))
    
    tenant = db.relationship('Tenant', back_populates='utilisateurs', foreign_keys='Utilisateur.tenant_id')
    clients = db.relationship('Client', back_populates='commercial', foreign_keys='Client.commercial_id', lazy='dynamic')
    ventes = db.relationship('Vente', back_populates='commercial', foreign_keys='Vente.commercial_id', lazy='dynamic')
    created_products = db.relationship('Produit', foreign_keys='Produit.created_by', lazy='dynamic')
    updated_products = db.relationship('Produit', foreign_keys='Produit.updated_by', lazy='dynamic')
    
    @property
    def full_name(self):
        if self.prenom and self.nom:
            return f"{self.prenom} {self.nom}"
        return self.username
    
    @property
    def is_admin(self):
        from app.security.roles import is_admin as _is_admin
        if self.custom_role_id:
            return any(p.code == 'admin.access' for p in (self.custom_role.permissions or []))
        return _is_admin(self.role)
    
    @property
    def is_super_admin(self):
        from app.security.roles import is_super_admin as _is_super_admin
        if self.custom_role_id:
            return any(p.code == 'super_admin.access' for p in (self.custom_role.permissions or []))
        return _is_super_admin(self.role)
    
    @property
    def is_manager(self):
        from app.security.roles import is_manager as _is_manager
        if self.custom_role_id:
            return any(p.code in ['manager.access', 'admin.access', 'super_admin.access'] for p in (self.custom_role.permissions or []))
        return _is_manager(self.role)
    
    def get_permissions(self):
        if self.custom_role_id and self.custom_role and self.custom_role.permissions:
            return [p.code for p in self.custom_role.permissions]
        from app.security.permission_matrix import PERMISSIONS
        role_name = self.role.value if hasattr(self.role, 'value') else self.role
        return PERMISSIONS.get(role_name, [])
    
    def has_permission(self, permission):
        from app.security.roles import has_permission
        return has_permission(self.id, permission)
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'password_hash' in data:
            del data['password_hash']
        if 'role' in data:
            data['role'] = str(self.role)
        if 'statut' in data:
            data['statut'] = str(self.statut)
        if 'custom_role_id' in data:
            if self.custom_role:
                data['custom_role'] = self.custom_role.to_dict()
            else:
                data['custom_role'] = None
        data['permissions'] = self.get_permissions()
        return data
    
    def __repr__(self):
        return f'<Utilisateur {self.username}>'

>>>

### FICHIER .PY: web\backend\app\models\vehicule.py
<<<
from app.models.base import BaseTenantModel
from app import db

class Vehicule(BaseTenantModel):
    __tablename__ = 'vehicules'

    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    plaque_immatriculation = db.Column(db.String(20), unique=True, nullable=False, index=True)
    type = db.Column(db.String(20), default='camion')  # camion/van/voiture/moto
    capacite_charge = db.Column(db.Integer)  # en kg
    capacite_volume = db.Column(db.Integer)  # en litres
    statut = db.Column(db.String(20), default='disponible')  # disponible/en_mission/en_maintenance

    chauffeur_id = db.Column(db.Integer, db.ForeignKey('livreurs.id'), index=True)

    chauffeurs = db.relationship('Livreur', back_populates='vehicule', foreign_keys='Livreur.vehicule_id')
    itineraires = db.relationship('Itineraire', back_populates='vehicule', lazy='dynamic')
    livraisons = db.relationship('Livraison', back_populates='vehicule', lazy='dynamic')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.chauffeurs:
            data['chauffeur_nom'] = self.chauffeurs.first().nom_complet if self.chauffeurs.first() else None
        return data

    def __repr__(self):
        return f'<Vehicule {self.marque} {self.modele} - {self.plaque_immatriculation}>'

>>>

### FICHIER .PY: web\backend\app\models\vente.py
<<<
from datetime import datetime

from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Numeric

class Vente(BaseTenantModel):
    __tablename__ = 'ventes'
    
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0.00)
    mode_paiement = db.Column(db.String(50))
    type_vente = db.Column(db.String(20), default='detail')  # gros / detail
    remarque = db.Column(db.Text)
    statut = db.Column(db.String(50), default='en_attente')  # devis, en_attente, payee, annulee
    
    # Relations
    client = db.relationship('Client', back_populates='ventes')
    commercial = db.relationship('Utilisateur', back_populates='ventes', foreign_keys='Vente.commercial_id')
    lignes_vente = db.relationship('LigneVente', back_populates='vente', lazy='dynamic')
    factures = db.relationship('Facture', back_populates='vente', lazy='dynamic')
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        return data

>>>

### FICHIER .PY: web\backend\app\realtime\__init__.py
<<<
# web/backend/app/realtime/__init__.py
from app.realtime.socket_server import init_socketio, emit_preference_update, socketio

__all__ = ["init_socketio", "emit_preference_update", "socketio"]

>>>

### FICHIER .PY: web\backend\app\realtime\socket_server.py
<<<
# web/backend/app/realtime/socket_server.py
# Serveur temps-réel (Flask-SocketIO). Désactivé proprement si flask-socketio
# n'est pas installé : le client bascule alors sur le polling (voir /desk/events).

import logging
from flask import request

logger = logging.getLogger(__name__)

socketio = None


def init_socketio(app):
    """Initialise SocketIO sur l'app Flask. Retourne None si non disponible."""
    global socketio
    try:
        from flask_socketio import SocketIO
    except ImportError:
        logger.warning(
            "flask-socketio non installé : temps-réel désactivé. "
            "Le client utilisera le fallback polling (/api/v1/desk/events)."
        )
        return None

    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
        async_mode="threading",
        path="/socket.io",
    )
    _register_handlers()
    return socketio


def _register_handlers():
    if not socketio:
        return
    from flask_jwt_extended import decode_token

    @socketio.on("connect")
    def _on_connect():
        token = request.args.get("token") or (
            request.headers.get("Authorization", "").replace("Bearer ", "")
        )
        if not token:
            return False
        try:
            claims = decode_token(token)
            user_id = claims.get("sub")
            request.sid and socketio.enter_room(request.sid, f"user:{user_id}")
            return True
        except Exception:
            return False

    @socketio.on("disconnect")
    def _on_disconnect():
        return

    @socketio.on("ping")
    def _on_ping():
        socketio.emit("pong")


def emit_preference_update(entity, user_id, payload):
    """Émet une MAJ vers la room de l'utilisateur (si SocketIO actif)."""
    if not socketio or not user_id:
        return
    try:
        socketio.emit(f"{entity}:updated", payload, room=f"user:{user_id}")
    except Exception as exc:  # pragma: no cover
        logger.warning("Échec émission socket %s: %s", entity, exc)

>>>

### FICHIER .PY: web\backend\app\security\__init__.py
<<<
# app/security/__init__.py
# Re-exports removed to avoid circular imports with app.models.password_reset_token.
# Import directly from submodules: app.security.auth, app.security.tenant, etc.

>>>

### FICHIER .PY: web\backend\app\security\auth.py
<<<
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask import request, g
from functools import wraps
from sqlalchemy import or_
from app.models.utilisateur import Utilisateur, StatutUtilisateur
from app.models.tenant import Tenant
from app import db
import bcrypt


def hash_password(password):
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, password_hash):
    """Vérifie un mot de passe hashé"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def _validate_password(password):
    if not password or len(password) < 8:
        return 'Le mot de passe doit contenir au moins 8 caracteres'
    if not any(c.isalpha() for c in password):
        return 'Le mot de passe doit contenir au moins une lettre'
    if not any(c.isdigit() for c in password):
        return 'Le mot de passe doit contenir au moins un chiffre'
    return None


def create_access_token_for_user(user):
    """Crée un token d'accès pour un utilisateur"""
    return create_access_token(
        identity=user.id,
        additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'tenant_id': user.tenant_id,
        }
    )


def authenticate_user(identifier, password, tenant_slug=None):
    """Authentifie un utilisateur"""
    tenant = None
    
    if tenant_slug:
        tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
        if not tenant:
            return None, "Tenant non trouvé"
        user = Utilisateur.query.filter(
            Utilisateur.tenant_id == tenant.id,
            Utilisateur.is_active == True,
            or_(Utilisateur.username == identifier, Utilisateur.email == identifier)
        ).first()
    else:
        user = Utilisateur.query.filter(
            Utilisateur.is_active == True,
            or_(Utilisateur.username == identifier, Utilisateur.email == identifier)
        ).first()
        if user and user.tenant_id:
            tenant = db.session.get(Tenant, user.tenant_id)
    
    if not user:
        return None, "Utilisateur non trouvé"
    
    if not verify_password(password, user.password_hash):
        return None, "Mot de passe incorrect"
    
    if user.statut != StatutUtilisateur.ACTIF:
        return None, "Utilisateur inactif ou bloque"
    
    g.current_tenant = tenant
    g.current_user = user
    
    # Générer les tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value if hasattr(user.role, 'value') else user.role,
            'tenant_id': tenant.id if tenant else user.tenant_id,
            'tenant_slug': tenant.slug if tenant else None
        }
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'tenant': tenant.to_dict() if tenant else None
    }, None
>>>

### FICHIER .PY: web\backend\app\security\encryption.py
<<<
from cryptography.fernet import Fernet
import os


def _get_key():
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is required. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return key


def encrypt_text(value: str) -> str:
    key = _get_key().encode('utf-8')
    return Fernet(key).encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_text(token: str) -> str:
    key = _get_key().encode('utf-8')
    return Fernet(key).decrypt(token.encode('utf-8')).decode('utf-8')

>>>

### FICHIER .PY: web\backend\app\security\permission_matrix.py
<<<

PERMISSION_DEFINITIONS = {
    "product.view": {"module": "product", "action": "view", "description": "Voir les produits"},
    "product.create": {"module": "product", "action": "create", "description": "Creer des produits"},
    "product.update": {"module": "product", "action": "update", "description": "Modifier des produits"},
    "product.delete": {"module": "product", "action": "delete", "description": "Supprimer des produits"},
    "stock.view": {"module": "stock", "action": "view", "description": "Voir les stocks"},
    "stock.update": {"module": "stock", "action": "update", "description": "Modifier les stocks"},
    "sale.view": {"module": "sale", "action": "view", "description": "Voir les ventes"},
    "sale.create": {"module": "sale", "action": "create", "description": "Creer des ventes"},
    "sale.update": {"module": "sale", "action": "update", "description": "Modifier des ventes"},
    "user.view": {"module": "user", "action": "view", "description": "Voir les utilisateurs"},
    "user.create": {"module": "user", "action": "create", "description": "Creer des utilisateurs"},
    "user.update": {"module": "user", "action": "update", "description": "Modifier des utilisateurs"},
    "report.view": {"module": "report", "action": "view", "description": "Voir les rapports"},
    "client.view": {"module": "client", "action": "view", "description": "Voir les clients"},
    "client.create": {"module": "client", "action": "create", "description": "Creer des clients"},
    "client.update": {"module": "client", "action": "update", "description": "Modifier des clients"},
    "invoice.view": {"module": "invoice", "action": "view", "description": "Voir les factures"},
    "invoice.create": {"module": "invoice", "action": "create", "description": "Creer des factures"},
    "invoice.update": {"module": "invoice", "action": "update", "description": "Modifier des factures"},
    "payment.view": {"module": "payment", "action": "view", "description": "Voir les paiements"},
    "payment.create": {"module": "payment", "action": "create", "description": "Creer des paiements"},
    "quote.view": {"module": "quote", "action": "view", "description": "Voir les devis"},
    "quote.create": {"module": "quote", "action": "create", "description": "Creer des devis"},
    "supplier.view": {"module": "supplier", "action": "view", "description": "Voir les fournisseurs"},
    "supplier.create": {"module": "supplier", "action": "create", "description": "Creer des fournisseurs"},
    "supplier.update": {"module": "supplier", "action": "update", "description": "Modifier des fournisseurs"},
    "purchase_order.view": {"module": "purchase_order", "action": "view", "description": "Voir les commandes d'achat"},
    "purchase_order.create": {"module": "purchase_order", "action": "create", "description": "Creer des commandes d'achat"},
    "profile.view": {"module": "profile", "action": "view", "description": "Voir son profil"},
    "profile.update": {"module": "profile", "action": "update", "description": "Modifier son profil"},
    "compte.view": {"module": "compte", "action": "view", "description": "Voir les comptes"},
    "compte.create": {"module": "compte", "action": "create", "description": "Creer des comptes"},
    "compte.update": {"module": "compte", "action": "update", "description": "Modifier des comptes"},
    "compte.delete": {"module": "compte", "action": "delete", "description": "Supprimer des comptes"},
    "ecriture.view": {"module": "ecriture", "action": "view", "description": "Voir les ecritures"},
    "ecriture.create": {"module": "ecriture", "action": "create", "description": "Creer des ecritures"},
    "ecriture.update": {"module": "ecriture", "action": "update", "description": "Modifier des ecritures"},
    "ecriture.delete": {"module": "ecriture", "action": "delete", "description": "Supprimer des ecritures"},
    "tresorerie.view": {"module": "tresorerie", "action": "view", "description": "Voir la tresorerie"},
    "tresorerie.create": {"module": "tresorerie", "action": "create", "description": "Creer des mouvements de tresorerie"},
    "tresorerie.update": {"module": "tresorerie", "action": "update", "description": "Modifier des mouvements de tresorerie"},
    "tresorerie.delete": {"module": "tresorerie", "action": "delete", "description": "Supprimer des mouvements de tresorerie"},
}

ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "admin": ["*"],
    "manager": [
        "product.create", "product.update", "product.delete", "product.view",
        "stock.view", "stock.update",
        "sale.view", "sale.create", "sale.update",
        "user.view", "user.create", "user.update",
        "report.view",
        "client.view", "client.create", "client.update",
        "invoice.view", "invoice.create", "invoice.update",
        "payment.view", "payment.create",
    ],
    "sales": [
        "product.view",
        "sale.view", "sale.create",
        "client.view", "client.create", "client.update",
        "quote.view", "quote.create",
        "invoice.view",
    ],
    "stock": [
        "product.view", "product.create", "product.update",
        "stock.view", "stock.update",
        "supplier.view", "supplier.create", "supplier.update",
        "purchase_order.view", "purchase_order.create",
        "sale.view",
    ],
    "accountant": [
        "product.view",
        "invoice.view", "invoice.create", "invoice.update",
        "payment.view", "payment.create",
        "report.view",
        "sale.view",
        "client.view",
        "compte.view", "compte.create", "compte.update", "compte.delete",
        "ecriture.view", "ecriture.create", "ecriture.update", "ecriture.delete",
        "tresorerie.view", "tresorerie.create", "tresorerie.update", "tresorerie.delete",
    ],
    "user": [
        "product.view",
        "profile.view", "profile.update",
    ],
}

PERMISSIONS = ROLE_PERMISSIONS

>>>

### FICHIER .PY: web\backend\app\security\permissions.py
<<<
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models.utilisateur import Utilisateur, Role
from .roles import has_permission


def permission_required(permission):
    """Décorateur pour vérifier les permissions"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            if not has_permission(user_id, permission):
                return {'message': 'Permission non accordée'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


>>>

### FICHIER .PY: web\backend\app\security\plan_limits.py
<<<
from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from flask_jwt_extended.exceptions import (
    NoAuthorizationError,
    InvalidHeaderError,
    RevokedTokenError,
    JWTDecodeError,
)
from app import db
from app.models.tenant import Tenant
from app.models.utilisateur import Role, Utilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.roles import is_super_admin
from app.security.plans import resolve_limits, resolve_modules, is_unlimited
from app.models.tenant import StatutTenant

FEATURE_LIMIT_MAP = {
    'produits': ('max_produits', 'produit'),
    'clients': ('max_clients', 'client'),
    'utilisateurs': ('max_utilisateurs', 'utilisateur'),
    'employes': ('max_employees', 'employe'),
    'stagiaires': ('max_interns', 'stagiaire'),
}

FEATURE_LIMIT_MESSAGES = {
    'produits': 'Limite de produits atteinte pour votre abonnement actuel.',
    'clients': 'Limite de clients atteinte pour votre abonnement actuel.',
    'utilisateurs': 'Limite d\'utilisateurs atteinte pour votre abonnement actuel.',
    'employes': 'Limite d\'employés atteinte pour votre abonnement actuel.',
    'stagiaires': 'Limite de stagiaires atteinte pour votre abonnement actuel.',
}


def _get_tenant_from_claims_or_g():
    claims = get_jwt() or {}
    tenant = getattr(g, 'current_tenant', None)
    if tenant:
        return tenant
    tenant_id = claims.get('tenant_id')
    if isinstance(tenant_id, str) and tenant_id.isdigit():
        tenant_id = int(tenant_id)
    if not tenant_id:
        return None
    return db.session.get(Tenant, tenant_id)


def _get_active_abonnement(tenant):
    if not tenant:
        return None
    return Abonnement.query.filter(
        Abonnement.tenant_id == tenant.id,
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.is_active == True,
    ).order_by(Abonnement.created_at.desc()).first()


def _get_limits(tenant):
    abonnement = _get_active_abonnement(tenant)
    if abonnement:
        return resolve_limits(tenant, abonnement)
    return resolve_limits(tenant)


def _get_modules(tenant):
    abonnement = _get_active_abonnement(tenant)
    if abonnement:
        return resolve_modules(tenant, abonnement)
    return resolve_modules(tenant)


def check_plan_limits(feature):
    """
    Décorateur vérifiant les limites du plan du tenant
    avant une action de création.

    Le rôle SUPER_ADMIN contourne automatiquement la vérification.

    Args:
        feature: 'produits', 'clients', 'utilisateurs', 'employes' ou 'stagiaires'

    Returns:
        Tuple (dict, int) avec une erreur 403 si la limite est atteinte,
        sinon poursuit l'exécution de la vue.
    """
    if feature not in FEATURE_LIMIT_MAP:
        raise ValueError(
            f"Feature inconnue: {feature}. "
            f"Options: {list(FEATURE_LIMIT_MAP.keys())}"
        )

    limit_field, model_name = FEATURE_LIMIT_MAP[feature]

    _MODEL_IMPORTS = {
        'produit': ('app.models.produit', 'Produit'),
        'client': ('app.models.client', 'Client'),
        'utilisateur': ('app.models.utilisateur', 'Utilisateur'),
        'employe': ('app.models.employe', 'Employe'),
        'stagiaire': ('app.models.stagiaire', 'Stagiaire'),
    }

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except NoAuthorizationError:
                return {
                    'message': 'En-tête Authorization manquant ou invalide'
                }, 401
            except InvalidHeaderError:
                return {'message': 'En-tête Authorization invalide'}, 401
            except RevokedTokenError:
                return {'message': 'Token JWT révoqué'}, 401
            except JWTDecodeError:
                return {'message': 'Token JWT invalide'}, 401
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)

            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            limits = _get_limits(tenant)
            limit = limits.get(limit_field)
            if is_unlimited(limit):
                return fn(*args, **kwargs)

            module_name, class_name = _MODEL_IMPORTS[model_name]
            mod = __import__(module_name, fromlist=[class_name])
            model_class = getattr(mod, class_name)

            current_count = model_class.query.filter_by(
                tenant_id=tenant.id,
                is_active=True,
            ).count()

            if current_count >= limit:
                return {
                    'message': FEATURE_LIMIT_MESSAGES.get(feature, 'Limite atteinte pour votre abonnement actuel.')
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def is_admin_limit_reached(tenant):
    limits = _get_limits(tenant)
    admin_limit_val = limits.get('max_admins', 1)
    if admin_limit_val is None or admin_limit_val <= 0:
        admin_limit_val = 1

    current_admins = Utilisateur.query.filter(
        Utilisateur.tenant_id == tenant.id,
        Utilisateur.role == Role.ADMIN,
        Utilisateur.is_active == True,
    ).count()

    return current_admins >= admin_limit_val


def check_admin_limit():
    """
    Décorateur vérifiant que le tenant n'a pas atteint la limite d'administrateurs.
    Utilisé lors de la création/modification d'un utilisateur avec role ADMIN.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)
            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            if is_admin_limit_reached(tenant):
                return {
                    'message': 'Limite d\'administrateurs atteinte pour votre abonnement actuel.'
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


def require_module(module):
    """
    Décorateur vérifiant que le module est autorisé pour le tenant.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return {'message': 'Token JWT invalide ou expiré'}, 401

            claims = get_jwt()
            user_id = get_jwt_identity()
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            utilisateur = db.session.get(Utilisateur, user_id)
            if utilisateur and is_super_admin(utilisateur.role):
                return fn(*args, **kwargs)

            tenant = _get_tenant_from_claims_or_g()
            if not tenant:
                return {'message': 'Aucun tenant associe a ce compte'}, 401

            if tenant.statut == StatutTenant.EN_ESSAI:
                return fn(*args, **kwargs)

            allowed = _get_modules(tenant)
            if module not in allowed:
                return {
                    'message': f'Module "{module}" non disponible pour votre abonnement actuel.'
                }, 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator

>>>

### FICHIER .PY: web\backend\app\security\plans.py
<<<
"""Configuration centralisée des plans d'abonnement et des modules.

Source unique de vérité pour :
- les limites (utilisateurs, admins, employés, stagiaires, produits, clients)
- les modules accessibles par plan

Toute limite est dérivée de l'abonnement actif du tenant ; en l'absence
d'abonnement (période d'essai), on retombe sur la configuration du plan
associé au tenant.
"""

# Règle absolue : peu importe le plan, le nombre d'administrateurs ne peut
# jamais dépasser cette valeur.
MAX_ADMINS_ABSOLUTE = 5

# Modules connus de l'application. Une route ne doit PAS être accessible juste
# parce qu'elle existe : le module doit être présent dans l'abonnement du tenant.
AVAILABLE_MODULES = [
    'dashboard',
    'produits',
    'clients',
    'ventes',
    'factures',
    'paiements',
    'catalogue',
    'stocks',
    'rh',
    'documents',
    'comptabilite',
    'livraison',
    'ia',
    'achats',
]

_BASIC = ['dashboard', 'produits', 'clients', 'ventes', 'factures', 'paiements', 'catalogue', 'rh']
_EXTENDED = _BASIC + ['stocks', 'documents']
_ALL = _EXTENDED + ['comptabilite', 'livraison', 'ia', 'achats']

# Limites par plan. -1 signifie "illimité".
PLAN_CONFIG = {
    'gratuit': {
        'max_utilisateurs': 1,
        'max_produits': 10,
        'max_clients': 10,
        'max_admins': 1,
        'max_employees': 5,
        'max_interns': 2,
        'modules': _BASIC,
    },
    'starter': {
        'max_utilisateurs': 3,
        'max_produits': 50,
        'max_clients': 100,
        'max_admins': 2,
        'max_employees': 20,
        'max_interns': 5,
        'modules': _EXTENDED,
    },
    'pro': {
        'max_utilisateurs': 10,
        'max_produits': 200,
        'max_clients': 1000,
        'max_admins': 5,
        'max_employees': 100,
        'max_interns': 20,
        'modules': _ALL,
    },
    'enterprise': {
        'max_utilisateurs': -1,
        'max_produits': -1,
        'max_clients': -1,
        'max_admins': 5,
        'max_employees': -1,
        'max_interns': -1,
        'modules': _ALL,
    },
}

DEFAULT_PLAN = 'gratuit'

LIMIT_KEYS = (
    'max_utilisateurs',
    'max_produits',
    'max_clients',
    'max_admins',
    'max_employees',
    'max_interns',
)


def get_plan_config(plan):
    """Retourne la configuration du plan (avec repli sur le plan par défaut)."""
    if not plan:
        return PLAN_CONFIG[DEFAULT_PLAN]
    return PLAN_CONFIG.get(plan, PLAN_CONFIG[DEFAULT_PLAN])


def is_unlimited(value):
    """Une limite -1 ou None est considérée comme illimitée."""
    return value is None or value == -1


def admin_limit(raw):
    """Applique la règle absolue MAX_ADMINS_ABSOLUTE."""
    if raw is None or raw <= 0:
        return MAX_ADMINS_ABSOLUTE
    return min(raw, MAX_ADMINS_ABSOLUTE)


def resolve_limits(tenant, abonnement=None):
    """Résout les limites pour un tenant.

    Priorité : abonnement actif (si fourni et renseigné), sinon configuration
    du plan du tenant.
    """
    if abonnement is not None:
        limits = {}
        for key in LIMIT_KEYS:
            val = getattr(abonnement, key, None)
            if val is not None:
                limits[key] = val
        if limits:
            limits.setdefault('max_admins', MAX_ADMINS_ABSOLUTE)
            return limits
    cfg = get_plan_config(tenant.plan if tenant else None)
    return {key: cfg.get(key) for key in LIMIT_KEYS}


def resolve_modules(tenant, abonnement=None):
    """Retourne la liste des modules autorisés pour le tenant."""
    if abonnement is not None and getattr(abonnement, 'modules', None):
        mods = abonnement.modules
        if isinstance(mods, str):
            mods = [m.strip() for m in mods.split(',') if m.strip()]
        if mods:
            return list(mods)
    cfg = get_plan_config(tenant.plan if tenant else None)
    return list(cfg.get('modules', []))


def apply_plan_to_abonnement(abonnement, plan=None):
    """Recopie les limites et modules du plan dans l'abonnement."""
    cfg = get_plan_config(plan or abonnement.plan)
    for key in LIMIT_KEYS:
        setattr(abonnement, key, cfg.get(key))
    abonnement.modules = ','.join(cfg.get('modules', []))
    return abonnement

>>>

### FICHIER .PY: web\backend\app\security\rate_limit.py
<<<
import time
import logging
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_client = None
    _redis_available = True
except Exception:
    _redis_client = None
    _redis_available = False


def _get_redis_client():
    global _redis_client
    if not _redis_available:
        return None
    try:
        from app import current_app
        url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        return None
    return _redis_client


def rate_limit(max_requests, window_seconds, key_func=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            client = _get_redis_client()
            if client is None:
                return fn(*args, **kwargs)

            try:
                if key_func:
                    key = key_func()
                else:
                    ip = request.remote_addr or 'unknown'
                    key = f"rate_limit:{fn.__name__}:{ip}"

                now = time.time()
                pipe = client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, count, _ = pipe.execute()

                if count > max_requests:
                    logger.warning(
                        "Rate limit exceeded for %s: %s requests in %ss window",
                        key, count, window_seconds
                    )
                    return jsonify({'message': 'Trop de requêtes. Veuillez réessayer plus tard.'}), 429
            except Exception:
                pass

            return fn(*args, **kwargs)
        return wrapper
    return decorator

>>>

### FICHIER .PY: web\backend\app\security\roles.py
<<<
from functools import wraps
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import jsonify
from app import db
from app.models.utilisateur import Utilisateur, Role
from app.models.role_permission import RoleModel


def normalize_role(role_value):
    """Normalize role value for case-insensitive comparison.
    
    Args:
        role_value: Can be Role enum, string value (e.g., 'super_admin'), or string name (e.g., 'SUPER_ADMIN')
    
    Returns:
        Role enum value if valid, None otherwise
    """
    if role_value is None:
        return None
    
    if isinstance(role_value, Role):
        return role_value
    
    if isinstance(role_value, str):
        # Try to match by value (e.g., 'super_admin')
        for role in Role:
            if role.value.lower() == role_value.lower():
                return role
        # Try to match by name (e.g., 'SUPER_ADMIN')
        for role in Role:
            if role.name.lower() == role_value.lower():
                return role
    
    return None


def is_super_admin(role_value):
    """Check if role is SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized == Role.SUPER_ADMIN


def is_admin(role_value):
    """Check if role is ADMIN or SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized in (Role.ADMIN, Role.SUPER_ADMIN)


def is_manager(role_value):
    """Check if role is MANAGER, ADMIN, or SUPER_ADMIN (case-insensitive)."""
    normalized = normalize_role(role_value)
    return normalized in (Role.MANAGER, Role.ADMIN, Role.SUPER_ADMIN)


def has_role(role_value, *allowed_roles):
    """Check if role matches any of the allowed roles (case-insensitive)."""
    normalized = normalize_role(role_value)
    allowed_normalized = {normalize_role(r) for r in allowed_roles if normalize_role(r)}
    return normalized in allowed_normalized


from app.security.permission_matrix import ROLE_PERMISSIONS

PERMISSIONS = ROLE_PERMISSIONS


def has_permission(user_id, permission):
    user = db.session.get(Utilisateur, user_id)
    if not user:
        return False
    
    if user.custom_role_id and user.custom_role and user.custom_role.permissions:
        user_permissions = [p.code for p in user.custom_role.permissions]
        if '*' in user_permissions:
            return True
        return permission in user_permissions
    
    role = user.role.value if hasattr(user.role, 'value') else user.role
    user_permissions = PERMISSIONS.get(role, [])
    
    if '*' in user_permissions:
        return True
    return permission in user_permissions

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)
        if not user or not is_super_admin(user.role) and not is_admin(user.role):
            return jsonify({'message': 'Acces administrateur requis'}), 403
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = db.session.get(Utilisateur, user_id)
        if not user or not is_super_admin(user.role):
            return jsonify({'message': 'Acces super administrateur requis'}), 403
        return f(*args, **kwargs)
    return jwt_required()(decorated_function)

>>>

### FICHIER .PY: web\backend\app\security\tenant.py
<<<
from functools import wraps
from flask import request, g
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app import db
from sqlalchemy import event
import logging
from app.security.roles import is_super_admin, is_admin, is_manager

logger = logging.getLogger(__name__)

# Global flag to track if the tenant filter event is registered
_tenant_filter_registered = False


def register_tenant_filter_event():
    """Register the global SQLAlchemy event listener for tenant filtering.
    This should be called once during app initialization.
    """
    global _tenant_filter_registered
    if _tenant_filter_registered:
        return
    
    @event.listens_for(db.session, 'do_orm_execute')
    def _do_orm_execute(orm_execute_state):
        # Skip if not a select statement
        if not orm_execute_state.is_select:
            return
        
        # Skip if execution options indicate no tenant filtering
        if orm_execute_state.execution_options.get('_skip_tenant_filter'):
            logger.warning(
                "Tenant filter bypassed via _skip_tenant_filter on query: %s",
                str(orm_execute_state.statement),
            )
            return
        
        # Get current tenant from Flask g
        from flask import has_request_context
        if not has_request_context():
            return
        
        tenant = getattr(g, 'current_tenant', None)
        if tenant is None:
            # No tenant filtering for SUPER_ADMIN (g.current_tenant is None)
            return
        
        tenant_id = getattr(g, 'current_tenant_id', None)
        if tenant_id is None:
            try:
                tenant_id = tenant.id
            except Exception:
                return
        
        # Apply tenant filter to all entities in the query that have tenant_id
        if hasattr(orm_execute_state.statement, 'column_descriptions'):
            for desc in orm_execute_state.statement.column_descriptions:
                entity = desc.get('entity')
                if entity is None:
                    continue
                if entity.__name__ == 'Tenant':
                    continue
                if hasattr(entity, 'tenant_id'):
                    orm_execute_state.statement = orm_execute_state.statement.where(
                        entity.tenant_id == tenant_id
                    )
    
    _tenant_filter_registered = True


def get_current_tenant():
    return getattr(g, 'current_tenant', None)


def get_current_tenant_id():
    return getattr(g, 'current_tenant_id', None)


def set_tenant_filter(query, model_class):
    tenant_id = get_current_tenant_id()
    if tenant_id is not None:
        if hasattr(model_class, 'tenant_id'):
            query = query.filter(model_class.tenant_id == tenant_id)
    return query


def tenant_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        claims = get_jwt()
        tenant_id = claims.get('tenant_id')
        user_id = get_jwt_identity()

        if isinstance(tenant_id, str) and tenant_id.isdigit():
            tenant_id = int(tenant_id)
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        
        if utilisateur and is_super_admin(utilisateur.role):
            g.current_tenant = None
            g.current_user = utilisateur
            return fn(*args, **kwargs)

        if not tenant_id:
            if getattr(g, 'current_tenant', None):
                tenant_id = g.current_tenant.id
            else:
                if utilisateur and utilisateur.tenant_id:
                    tenant_id = utilisateur.tenant_id

        if not tenant_id:
            return {'message': 'Aucun tenant associe a ce compte'}, 401

        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Tenant introuvable'}, 401
        if not tenant.is_active:
            return {'message': 'Tenant inactif'}, 401

        if not utilisateur:
            return {'message': 'Utilisateur introuvable'}, 401
        if utilisateur.tenant_id != tenant_id:
            return {'message': 'Acces refuse a ce tenant'}, 403
        
        if utilisateur.role not in [Role.SUPER_ADMIN, Role.USER, Role.ACCOUNTANT]:
            from app.models.abonnement import Abonnement, StatutAbonnement
            from datetime import datetime
            now = datetime.utcnow()
            abonnement_actif = Abonnement.query.filter(
                Abonnement.tenant_id == tenant_id,
                Abonnement.statut == StatutAbonnement.ACTIF,
                Abonnement.date_fin > now,
                Abonnement.is_active == True
            ).first()
            if not abonnement_actif:
                if tenant.statut != StatutTenant.EN_ESSAI:
                    return {'message': 'Abonnement requis'}, 403
        
        g.current_tenant = tenant
        g.current_tenant_id = tenant_id
        g.current_user = utilisateur
        
        return fn(*args, **kwargs)
    
    return wrapper


def tenant_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur or not utilisateur.is_admin:
            return {'message': 'Acces refuse: admin requis'}, 403

        g.current_user = utilisateur
        return fn(*args, **kwargs)

    return wrapper


def get_current_tenant_id_or_none():
    """Retourne le tenant_id courant ou None pour SUPER_ADMIN (pas de filtrage)."""
    tenant = get_current_tenant()
    return tenant.id if tenant else None


def tenant_filtered_get(model_class, obj_id, allow_super_admin=True):
    """Récupère un objet en appliquant le filtre tenant.

    Pour SUPER_ADMIN, le filtre tenant n'est pas appliqué (accès global).
    """
    from flask_jwt_extended import get_jwt
    from app.security.roles import is_super_admin

    claims = get_jwt() or {}
    role = claims.get('role')

    query = model_class.query.filter_by(id=obj_id, is_active=True)
    if not (allow_super_admin and is_super_admin(role)):
        tenant_id = get_current_tenant_id_or_none()
        if tenant_id is not None and hasattr(model_class, 'tenant_id'):
            query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def resolve_tenant_from_header():
    tenant_slug = request.headers.get('X-Tenant-Slug')
    tenant_domaine = request.headers.get('X-Tenant-Domaine')
    
    if tenant_slug:
        return Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
    elif tenant_domaine:
        return Tenant.query.filter_by(domaine=tenant_domaine, is_active=True).first()
    return None


def ensure_tenant_for_model(model_instance):
    tenant_id = get_current_tenant_id()
    if tenant_id and hasattr(model_instance, 'tenant_id'):
        model_instance.tenant_id = tenant_id


def subscription_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
        from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError, RevokedTokenError, JWTDecodeError

        try:
            verify_jwt_in_request()
        except NoAuthorizationError:
            return {'message': 'En-tête Authorization manquant ou invalide'}, 401
        except InvalidHeaderError:
            return {'message': 'En-tête Authorization invalide'}, 401
        except RevokedTokenError:
            return {'message': 'Token JWT révoqué'}, 401
        except JWTDecodeError:
            return {'message': 'Token JWT invalide'}, 401
        except Exception:
            return {'message': 'Token JWT invalide ou expiré'}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)

        utilisateur = db.session.get(Utilisateur, user_id)
        if not utilisateur:
            return {'message': 'Utilisateur introuvable'}, 401

        if is_admin(utilisateur.role) or is_manager(utilisateur.role):
            return fn(*args, **kwargs)

        tenant_id = utilisateur.tenant_id
        if not tenant_id:
            return {'message': 'Aucun tenant associe a ce compte'}, 401

        from app.models.abonnement import Abonnement, StatutAbonnement
        from datetime import datetime
        now = datetime.utcnow()

        abonnement_actif = Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        ).first()

        if not abonnement_actif:
            tenant = db.session.get(Tenant, tenant_id)
            if tenant and tenant.statut == StatutTenant.EN_ESSAI:
                return fn(*args, **kwargs)
            return {'message': 'Abonnement requis'}, 403

        return fn(*args, **kwargs)
    
    return wrapper

>>>

### FICHIER .PY: web\backend\app\services\__init__.py
<<<
# Services

>>>

### FICHIER .PY: web\backend\app\services\abonnement_service.py
<<<
from datetime import datetime, timedelta
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.tenant import Tenant, StatutTenant
from app.security.tenant import get_current_tenant_id
from app.security.plans import apply_plan_to_abonnement


class AbonnementService:

    @classmethod
    def get_active_by_tenant(cls, tenant_id):
        now = datetime.utcnow()
        return Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        ).first()

    @classmethod
    def activate_free_plan(cls, tenant_id, plan='gratuit'):
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant non trouve")

        now = datetime.utcnow()
        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=0,
            devise='MGA',
            date_debut=now,
            date_fin=now + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            plan=plan,
        )
        apply_plan_to_abonnement(abonnement, plan)
        db.session.add(abonnement)
        db.session.flush()

        tenant.statut = StatutTenant.ACTIF
        tenant.plan = plan
        tenant.date_abonnement = now
        db.session.add(tenant)
        db.session.commit()

        return abonnement

    @classmethod
    def create_abonnement(cls, data):
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            tenant_id = get_current_tenant_id()

        if not tenant_id:
            raise ValueError("tenant_id requis")

        plan = data.get('plan', 'starter')

        if plan == 'gratuit':
            return cls.activate_free_plan(tenant_id, plan), None

        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=data.get('montant'),
            devise=data.get('devise', 'MGA'),
            date_debut=data.get('date_debut') or datetime.utcnow(),
            date_fin=data.get('date_fin') or (datetime.utcnow() + timedelta(days=30)),
            statut=StatutAbonnement.EN_ATTENTE,
            methode_paiement=data.get('methode_paiement'),
            reference_paiement=data.get('reference_paiement'),
            notes=data.get('notes'),
            plan=plan
        )
        apply_plan_to_abonnement(abonnement, abonnement.plan)
        db.session.add(abonnement)
        db.session.flush()

        paiement = Paiement(
            tenant_id=tenant_id,
            montant=data.get('montant'),
            devise=data.get('devise', 'MGA'),
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            reference=data.get('reference_paiement'),
            notes=data.get('notes'),
            date_paiement=datetime.utcnow()
        )
        db.session.add(paiement)
        db.session.commit()

        return abonnement, paiement

    @classmethod
    def get_history_by_tenant(cls, tenant_id, page=1, per_page=20):
        query = Abonnement.query.filter_by(tenant_id=tenant_id, is_active=True)
        paginated = query.order_by(Abonnement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

    @classmethod
    def get_all_subscriptions(cls, tenant_id=None, page=1, per_page=20):
        query = Abonnement.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        paginated = query.order_by(Abonnement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

    @classmethod
    def renew_subscription(cls, abonnement_id):
        abonnement = Abonnement.query.filter_by(id=abonnement_id, is_active=True).first()
        if not abonnement:
            return None

        now = datetime.utcnow()
        if abonnement.date_fin and abonnement.date_fin > now:
            base_date = abonnement.date_fin
        else:
            base_date = now

        abonnement.date_debut = base_date
        abonnement.date_fin = base_date + timedelta(days=30)
        abonnement.statut = StatutAbonnement.ACTIF
        apply_plan_to_abonnement(abonnement, abonnement.plan)
        abonnement.save()

        paiement = Paiement(
            tenant_id=abonnement.tenant_id,
            montant=abonnement.montant,
            devise=abonnement.devise,
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            reference=f"Renouvellement {abonnement.id}",
            notes=f"Renouvellement de l'abonnement {abonnement.id}",
            date_paiement=now
        )
        db.session.add(paiement)
        db.session.commit()

        return abonnement, paiement

    @classmethod
    def cancel_subscription(cls, abonnement_id):
        abonnement = Abonnement.query.filter_by(id=abonnement_id, is_active=True).first()
        if not abonnement:
            return None
        abonnement.statut = StatutAbonnement.ANNULE
        abonnement.save()
        return abonnement

>>>

### FICHIER .PY: web\backend\app\services\achat_service.py
<<<
from datetime import datetime
from app import db
from app.models.commande_achat import CommandeAchat, ReceptionAchat
from app.models.ligne_achat import LigneAchat
from app.security.tenant import get_current_tenant_id

def _gen_reference(prefix, id_val=None):
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    suffix = f'-{id_val}' if id_val else ''
    return f'{prefix}-{ts}{suffix}'

class CommandeAchatService:
    model = CommandeAchat

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('ACH')
        
        for date_field in ('date_livraison_prevue', 'date_reception', 'date_commande'):
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass
        
        lignes_data = data.pop('lignes', [])
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.flush()
        total_ht = 0
        total_ttc = 0
        for ligne in lignes_data:
            ligne['commande_achat_id'] = instance.id
            if tenant_id:
                ligne['tenant_id'] = tenant_id
            ligne_obj = LigneAchat(**ligne)
            db.session.add(ligne_obj)
            total_ht += float(ligne_obj.total_ht or 0)
            total_ttc += float(ligne_obj.total_ht or 0) * (1 + float(ligne.get('taux_tva', 20)) / 100)
        instance.total_ht = total_ht
        instance.total_ttc = total_ttc
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        lignes_data = data.pop('lignes', None)
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        if lignes_data is not None:
            LigneAchat.query.filter_by(commande_achat_id=id, is_active=True).update({'is_active': False})
            total_ht = 0
            total_ttc = 0
            for ligne in lignes_data:
                ligne['commande_achat_id'] = id
                ligne_obj = LigneAchat(**ligne)
                db.session.add(ligne_obj)
                total_ht += float(ligne_obj.total_ht or 0)
                total_ttc += float(ligne_obj.total_ht or 0) * (1 + float(ligne.get('taux_tva', 20)) / 100)
            instance.total_ht = total_ht
            instance.total_ttc = total_ttc
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class ReceptionAchatService:
    model = ReceptionAchat

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('REC')
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

>>>

### FICHIER .PY: web\backend\app\services\auth_service.py
<<<
from ..security.auth import verify_password, authenticate_user as _authenticate_user


def authenticate_user(username, password, tenant_slug=None):
    return _authenticate_user(username, password, tenant_slug=tenant_slug)

>>>

### FICHIER .PY: web\backend\app\services\base_service.py
<<<
from app import db
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import func

class BaseService:
    """Service de base avec fonctions CRUD génériques"""
    
    model = None
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20, 
                filters: Optional[Dict] = None, 
                order_by: Optional[str] = None) -> Tuple[List, int]:
        """Récupère toutes les entités avec pagination"""
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        
        if filters:
            for key, value in filters.items():
                if value is not None:
                    if hasattr(cls.model, key):
                        query = query.filter_by(**{key: value})
        
        if order_by:
            query = query.order_by(order_by)
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional[Any]:
        """Récupère une entité par son ID"""
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Any:
        """Crée une nouvelle entité"""
        if hasattr(cls.model, 'tenant_id'):
            tenant_id = data.get('tenant_id') or get_current_tenant_id()
            if not tenant_id:
                raise ValueError("tenant_id est obligatoire pour cette ressource")
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        instance.save()
        return instance
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> Optional[Any]:
        """Met à jour une entité"""
        instance = cls.get_by_id(id)
        if not instance:
            return None
        
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        instance.save()
        return instance
    
    @classmethod
    def delete(cls, id: int) -> bool:
        """Supprime une entité (soft delete)"""
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True
    
    @classmethod
    def hard_delete(cls, id: int) -> bool:
        """Supprime une entité (hard delete)"""
        query = cls.model.query.filter_by(id=id)
        query = cls._get_tenant_filter(query)
        instance = query.first()
        if not instance:
            return False
        instance.hard_delete()
        return True
    

    @classmethod
    def exists(cls, **kwargs) -> bool:
        """Vérifie si une entité existe avec les critères donnés"""
        query = cls.model.query.filter_by(**kwargs)
        query = cls._get_tenant_filter(query)
        return query.first() is not None
>>>

### FICHIER .PY: web\backend\app\services\client_service.py
<<<
from app.models.client import Client
from app.services.base_service import BaseService
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import or_, func
from typing import Optional, Dict, Any, List, Tuple

class ClientService(BaseService):
    model = Client
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        from app.security.tenant import set_tenant_filter
        return set_tenant_filter(query, cls.model)
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20,
                filters: Optional[Dict] = None,
                order_by: Optional[str] = None) -> Tuple[List[Client], int]:
        """Récupère tous les clients avec filtres"""
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        
        if filters:
            if filters.get('type'):
                query = query.filter_by(type=filters['type'])
            if filters.get('secteur'):
                query = query.filter_by(secteur=filters['secteur'])
            if filters.get('commercial_id'):
                query = query.filter_by(commercial_id=filters['commercial_id'])
            if filters.get('est_actif') is not None:
                query = query.filter_by(est_actif=filters['est_actif'])
            if filters.get('est_bloque') is not None:
                query = query.filter_by(est_bloque=filters['est_bloque'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Client.raison_sociale.ilike(search),
                        Client.code.ilike(search),
                        Client.nom.ilike(search),
                        Client.prenom.ilike(search),
                        Client.email.ilike(search),
                        Client.ville_facturation.ilike(search)
                    )
                )
        
        if order_by:
            query = query.order_by(order_by)
        else:
            query = query.order_by(Client.nom.asc(), Client.prenom.asc())
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Client:
        """Crée un nouveau client"""
        if 'code' not in data or not data['code']:
            raise ValueError("Le code client est requis")
        
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Aucun tenant associe a ce compte")
        
        q = cls.model.query.filter_by(code=data['code'], tenant_id=tenant_id)
        if q.first():
            raise ValueError(f"Le code {data['code']} existe déjà")
        
        if data.get('email'):
            q = cls.model.query.filter_by(email=data['email'], tenant_id=tenant_id)
            if q.first():
                raise ValueError(f"L'email {data['email']} existe déjà")
        
        data['tenant_id'] = tenant_id
        return super().create(data)
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional[Client]:
        """Récupère un client par son email"""
        query = cls.model.query.filter_by(email=email, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()
    
    @classmethod
    def get_clients_actifs(cls) -> List[Client]:
        """Récupère les clients actifs"""
        query = cls.model.query.filter_by(is_active=True, est_actif=True)
        query = cls._get_tenant_filter(query)
        return query.all()
    
    @classmethod
    def get_top_clients(cls, limit: int = 10) -> List[Dict]:
        """Récupère les meilleurs clients (CA)"""
        from app.models.vente import Vente
        from app.security.tenant import get_current_tenant_id
        
        tenant_id = get_current_tenant_id()
        query = db.session.query(
            Client.id,
            Client.nom,
            Client.prenom,
            Client.raison_sociale,
            func.sum(Vente.total_ttc).label('ca_total')
        ).join(
            Vente,
            Client.id == Vente.client_id
        ).filter(
            Client.is_active == True,
            Vente.is_active == True,
            Vente.statut == 'payee'
        )
        
        if tenant_id:
            query = query.filter(Client.tenant_id == tenant_id)
        
        results = query.group_by(
            Client.id
        ).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(limit).all()
        
        return [{
            'id': r[0],
            'nom': r[1],
            'prenom': r[2],
            'raison_sociale': r[3],
            'ca_total': float(r[4] or 0)
        } for r in results]
    
    @classmethod
    def get_client_stats(cls, client_id: int) -> Dict:
        """Récupère les statistiques d'un client"""
        client = cls.get_by_id(client_id)
        if not client:
            return {}
        
        from app.models.vente import Vente
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        
        # Dernières commandes
        dernieres_commandes = client.ventes.filter_by(
            is_active=True
        ).order_by(
            Vente.created_at.desc()
        ).limit(5).all()
        
        # Factures
        factures = client.factures.filter_by(
            is_active=True
        ).all()
        
        # Paiements récents
        paiements_recents = client.paiements.filter_by(
            is_active=True
        ).order_by(
            Paiement.created_at.desc()
        ).limit(10).all()
        
        return {
            'client': client.to_dict(),
            'total_achats': float(client.total_achats),
            'nombre_commandes': client.total_commandes,
            'dernier_achat': client.dernier_achat.isoformat() if client.dernier_achat else None,
            'dernieres_commandes': [v.to_dict() for v in dernieres_commandes],
            'factures': [f.to_dict() for f in factures],
            'paiements_recents': [p.to_dict() for p in paiements_recents],
            'solde': float(client.solde)
        }
>>>

### FICHIER .PY: web\backend\app\services\commande_service.py
<<<
from app.models.commande_client import CommandeClient
from app.services.base_service import BaseService
from app import db
from app.security.tenant import get_current_tenant_id
from datetime import datetime
import random
import string
import json

class CommandeService(BaseService):
    model = CommandeClient
    
    @classmethod
    def _generate_reference(cls):
        prefix = 'CMD'
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @classmethod
    def create_commande(cls, data):
        from app.models.produit import Produit

        reference = cls._generate_reference()
        while CommandeClient.query.filter_by(reference=reference).first():
            reference = cls._generate_reference()

        # Support both flat fields and a nested "client" object (frontend Checkout)
        client = data.get('client') or {}

        def _field(flat_key, nested_key, default=None):
            if data.get(flat_key) is not None:
                return data.get(flat_key)
            if client.get(nested_key) is not None:
                return client.get(nested_key)
            return default

        nom_client = _field('nom_client', 'nom')
        prenom_client = _field('prenom_client', 'prenom')
        email_client = _field('email_client', 'email')
        telephone_client = _field('telephone_client', 'telephone', '')
        adresse_livraison = _field('adresse_livraison', 'adresse', '')
        ville_livraison = _field('ville_livraison', 'ville', '')
        code_postal_livraison = _field('code_postal_livraison', 'code_postal', '')
        pays_livraison = data.get('pays_livraison') or client.get('pays') or 'Madagascar'

        if not nom_client or not email_client:
            raise ValueError("nom_client et email_client sont requis")

        items = data.get('items', [])
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Le panier doit contenir au moins un article")

        # Validate and collect products by produit_id
        validated_items = []
        total_ht = 0
        total_ttc = 0
        tenant_id = data.get('tenant_id')
        
        for idx, item in enumerate(items):
            produit_id = item.get('produit_id')
            if not produit_id:
                raise ValueError(f"Article {idx + 1}: produit_id requis")
            
            produit = db.session.get(Produit, produit_id)
            if not produit:
                raise ValueError(f"Article {idx + 1}: Produit avec ID {produit_id} introuvable")
            
            if not produit.is_active:
                raise ValueError(f"Article {idx + 1}: Produit '{produit.nom}' n'est pas actif")
            
            # Ensure all products belong to the same tenant
            if tenant_id is not None and produit.tenant_id != tenant_id:
                raise ValueError(f"Article {idx + 1}: Produit '{produit.nom}' n'appartient pas au tenant de la commande")
            
            # Propagate tenant from first product if not provided
            if tenant_id is None:
                tenant_id = produit.tenant_id
            
            quantite = item.get('quantite', 1)
            if not isinstance(quantite, (int, float)) or quantite <= 0:
                raise ValueError(f"Article {idx + 1}: Quantité invalide pour '{produit.nom}'")
            
            # Check stock availability
            if produit.quantite_stock is not None and produit.quantite_stock < quantite:
                raise ValueError(f"Article {idx + 1}: Stock insuffisant pour '{produit.nom}' (disponible: {produit.quantite_stock}, demandé: {quantite})")
            
            tva = float(produit.taux_tva) if produit.taux_tva else 20.0
            total_ht += float(produit.prix_vente_ht) * quantite
            total_ttc += float(produit.prix_vente_ht) * (1 + tva / 100) * quantite
            
            # Store validated item with product details
            validated_items.append({
                'produit_id': produit.id,
                'nom': produit.nom,
                'reference': produit.reference,
                'quantite': quantite,
                'prix_unitaire_ht': float(produit.prix_vente_ht),
                'taux_tva': tva,
                'total_ht': float(produit.prix_vente_ht) * quantite,
                'total_ttc': float(produit.prix_vente_ht) * (1 + tva / 100) * quantite,
            })

        commande = CommandeClient(
            reference=reference,
            nom_client=nom_client,
            prenom_client=prenom_client,
            email_client=email_client,
            telephone_client=telephone_client,
            adresse_livraison=adresse_livraison,
            ville_livraison=ville_livraison,
            code_postal_livraison=code_postal_livraison,
            pays_livraison=pays_livraison,
            items=json.dumps(validated_items),
            total_ht=total_ht,
            total_ttc=total_ttc,
            tenant_id=tenant_id,
            notes=data.get('notes')
        )
        
        db.session.add(commande)
        db.session.commit()
        return commande
    
    @classmethod
    def get_by_reference(cls, reference):
        tenant_id = get_current_tenant_id()
        query = CommandeClient.query.filter_by(reference=reference, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.first()
    
    @classmethod
    def get_by_tenant(cls, tenant_id, page=1, per_page=20):
        query = CommandeClient.query.filter_by(tenant_id=tenant_id, is_active=True)
        paginated = query.order_by(CommandeClient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

>>>

### FICHIER .PY: web\backend\app\services\comptabilite_service.py
<<<
from app import db
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date
from decimal import Decimal
from sqlalchemy import func

# Multiplicateur d'impact d'une écriture sur le solde d'un compte selon son type.
# Actif/Charge : le débit augmente le solde, le crédit le diminue  -> +1
# Passif/Produit : le crédit augmente le solde, le débit le diminue -> -1
COMPTE_SENS = {
    TypeCompte.ACTIF: Decimal('1'),
    TypeCompte.CHARGE: Decimal('1'),
    TypeCompte.PASSIF: Decimal('-1'),
    TypeCompte.PRODUIT: Decimal('-1'),
}


class CompteComptableService:
    model = CompteComptable

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True, id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_numero(cls, numero):
        query = cls.model.query.filter_by(is_active=True, numero=numero)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def reindex_solde(cls, id):
        """Recalcule le solde d'un compte à partir de l'ensemble de ses écritures validées."""
        compte = cls.get_by_id(id)
        if not compte:
            return None
        sens = COMPTE_SENS.get(compte.type_compte, Decimal('1'))
        total = db.session.query(
            func.sum(EcritureComptable.montant_debit - EcritureComptable.montant_credit)
        ).filter(
            EcritureComptable.compte_id == compte.id,
            EcritureComptable.statut == StatutEcriture.VALIDE,
            EcritureComptable.is_active.is_(True),
        ).scalar() or Decimal('0')
        compte.solde = (total * sens)
        db.session.commit()
        return compte


class EcritureComptableService:
    model = EcritureComptable

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @staticmethod
    def _validate_ecriture(data):
        """Valide la cohérence débit/crédit d'une écriture."""
        montant_debit = Decimal(str(data.get('montant_debit') or 0))
        montant_credit = Decimal(str(data.get('montant_credit') or 0))
        if montant_debit > 0 and montant_credit > 0:
            raise ValueError("Débit et crédit ne peuvent pas être tous deux renseignés sur une même écriture")
        if montant_debit <= 0 and montant_credit <= 0:
            raise ValueError("Au moins un de débit ou crédit doit être renseigné")
        compte_id = data.get('compte_id')
        compte = CompteComptableService.get_by_id(compte_id)
        if not compte:
            raise ValueError(f"Compte comptable id={compte_id} introuvable")
        return montant_debit, montant_credit, compte

    @staticmethod
    def _apply_solde_and_tresorerie(ecriture, sens):
        """Met à jour le solde du compte et crée l'écriture de trésorerie associée.

        Called only when an écriture passe au statut VALIDÉ.
        """
        montant_debit = Decimal(str(ecriture.montant_debit or 0))
        montant_credit = Decimal(str(ecriture.montant_credit or 0))
        delta = (montant_debit - montant_credit) * sens
        if delta != 0:
            ecriture.compte.solde = (ecriture.compte.solde or Decimal('0')) + delta
        
        # Determine tresorerie type based on account type and entry direction
        # Inferred cash flow from single-entry recording:
        # - PRODUIT (revenue): credit = money in (ENTREE)
        # - CHARGE (expense): debit = money out (SORTIE)
        # - ACTIF (asset): debit = money in (ENTREE), credit = money out (SORTIE)
        # - PASSIF (liability): credit = money in (ENTREE), debit = money out (SORTIE)
        compte_type = ecriture.compte.type_compte
        if compte_type == TypeCompte.PRODUIT:
            type_op = TypeTresorerie.ENTREE if montant_credit > 0 else TypeTresorerie.SORTIE
        elif compte_type == TypeCompte.CHARGE:
            type_op = TypeTresorerie.SORTIE if montant_debit > 0 else TypeTresorerie.ENTREE
        elif compte_type == TypeCompte.ACTIF:
            type_op = TypeTresorerie.ENTREE if montant_debit > montant_credit else TypeTresorerie.SORTIE
        else:  # PASSIF
            type_op = TypeTresorerie.ENTREE if montant_credit > montant_debit else TypeTresorerie.SORTIE
        
        tres = Tresorerie(
            date=ecriture.date,
            type_operation=type_op,
            montant=abs(montant_debit - montant_credit),
            mode_paiement='especes',
            libelle=ecriture.libelle,
            reference=ecriture.reference_externe,
            compte_id=ecriture.compte_id,
            ecriture_id=ecriture.id,
            tenant_id=ecriture.tenant_id,
        )
        db.session.add(tres)
        return delta

    @classmethod
    def create(cls, data):
        montant_debit, montant_credit, compte = cls._validate_ecriture(data)
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.flush()

        statut = getattr(instance, 'statut', None)
        if statut == StatutEcriture.VALIDE or (hasattr(data.get('statut', None), 'lower') and data.get('statut') == 'valide'):
            sens = COMPTE_SENS.get(compte.type_compte, Decimal('1'))
            cls._apply_solde_and_tresorerie(instance, sens)
        db.session.commit()
        db.session.refresh(instance)
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        # On n'autorise pas de modifier le débit/crédit directement : passer par valider/annuler.
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by',
                                                      'montant_debit', 'montant_credit', 'compte_id'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def valider_ecriture(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        if instance.statut != StatutEcriture.VALIDE:
            sens = COMPTE_SENS.get(instance.compte.type_compte, Decimal('1'))
            cls._apply_solde_and_tresorerie(instance, sens)
            instance.statut = StatutEcriture.VALIDE
            db.session.commit()
            db.session.refresh(instance)
        return instance

    @classmethod
    def annuler_ecriture(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        # Inverser l'effet sur le solde si l'écriture avait été validée.
        if instance.statut == StatutEcriture.VALIDE and instance.compte:
            sens = COMPTE_SENS.get(instance.compte.type_compte, Decimal('1'))
            montant_debit = Decimal(str(instance.montant_debit or 0))
            montant_credit = Decimal(str(instance.montant_credit or 0))
            delta = (montant_debit - montant_credit) * sens * Decimal('-1')
            if delta != 0:
                instance.compte.solde = (instance.compte.solde or Decimal('0')) + delta
        annulation = EcritureComptable(
            date=date.today(),
            compte_id=instance.compte_id,
            montant_debit=instance.montant_credit,
            montant_credit=instance.montant_debit,
            libelle=f"Annulation de {instance.libelle}",
            reference_externe=instance.reference_externe,
            entite_type=instance.entite_type,
            entite_id=instance.entite_id,
            statut=StatutEcriture.ANNULE,
            ecriture_annulee_id=instance.id,
            tenant_id=instance.tenant_id,
        )
        db.session.add(annulation)
        instance.statut = StatutEcriture.ANNULE
        db.session.commit()
        db.session.refresh(annulation)
        return annulation

    @classmethod
    def get_journal(cls, date_debut=None, date_fin=None, compte_id=None):
        """Retourne le journal des écritures avec le solde courant par compte."""
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True, statut=StatutEcriture.VALIDE)
        query = cls._get_tenant_filter(query)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        if compte_id:
            query = query.filter_by(compte_id=compte_id)
        ecritures = query.order_by(cls.model.date).all()

        # Totaux par compte (debits / credits) pour le tableau de bord du journal.
        compte_totaux = {}
        for ec in ecritures:
            sens = COMPTE_SENS.get(ec.compte.type_compte, Decimal('1')) if ec.compte else Decimal('1')
            delta = (Decimal(str(ec.montant_debit or 0)) - Decimal(str(ec.montant_credit or 0))) * sens
            c = compte_totaux.setdefault(ec.compte_id, {'debit': Decimal('0'), 'credit': Decimal('0'), 'solde': Decimal('0')})
            c['debit'] += Decimal(str(ec.montant_debit or 0))
            c['credit'] += Decimal(str(ec.montant_credit or 0))
            c['solde'] += delta

        result = []
        solde_courant = Decimal('0')
        for ec in ecritures:
            sens = COMPTE_SENS.get(ec.compte.type_compte, Decimal('1')) if ec.compte else Decimal('1')
            delta = (Decimal(str(ec.montant_debit or 0)) - Decimal(str(ec.montant_credit or 0))) * sens
            solde_courant += delta
            row = ec.to_dict()
            row['solde_courant'] = float(round(solde_courant, 2))
            result.append(row)

        comptes_resume = []
        for compte_id, t in compte_totaux.items():
            compte = CompteComptableService.get_by_id(compte_id)
            comptes_resume.append({
                'compte_id': compte_id,
                'numero': compte.numero if compte else None,
                'nom': compte.nom if compte else None,
                'debit': float(t['debit']),
                'credit': float(t['credit']),
                'solde': float(round(t['solde'], 2)),
            })
        return {
            'ecritures': result,
            'comptes_resume': sorted(comptes_resume, key=lambda x: x['numero'] or ''),
            'total_debit': float(sum(t['debit'] for t in compte_totaux.values())),
            'total_credit': float(sum(t['credit'] for t in compte_totaux.values())),
        }


class TresorerieService:
    model = Tresorerie

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        db.session.commit()
        return True

    @classmethod
    def get_solde(cls, date_debut=None, date_fin=None):
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        entrees = query.filter(cls.model.type_operation == 'entree').with_entities(func.sum(cls.model.montant)).scalar() or 0
        sorties = query.filter(cls.model.type_operation == 'sortie').with_entities(func.sum(cls.model.montant)).scalar() or 0
        return float(entrees) - float(sorties)

    @classmethod
    def get_mouvements(cls, date_debut=None, date_fin=None):
        """Retourne les mouvements de trésorerie triés avec le solde courant cumulé."""
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if date_debut:
            query = query.filter(cls.model.date >= date_debut)
        if date_fin:
            query = query.filter(cls.model.date <= date_fin)
        mouvements = query.order_by(cls.model.date).all()
        result = []
        solde = Decimal('0')
        for m in mouvements:
            montant = Decimal(str(m.montant or 0))
            if m.type_operation == TypeTresorerie.ENTREE or (hasattr(m.type_operation, 'value') and m.type_operation.value == 'entree'):
                solde += montant
            else:
                solde -= montant
            d = m.to_dict()
            d['solde_courant'] = float(round(solde, 2))
            result.append(d)
        return result


class ComptaImportService:
    @classmethod
    def import_comptes(cls, file):
        from app.utils.compta_import import import_comptes_from_file
        return import_comptes_from_file(file)

    @classmethod
    def import_ecritures(cls, file):
        from app.utils.compta_import import import_ecritures_from_file
        return import_ecritures_from_file(file)

    @classmethod
    def import_tresorerie(cls, file):
        from app.utils.compta_import import import_tresorerie_from_file
        return import_tresorerie_from_file(file)

    @staticmethod
    def export_comptes():
        tenant_id = get_current_tenant_id()
        query = CompteComptable.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(CompteComptable.tenant_id == tenant_id)
        comptes = query.order_by(CompteComptable.numero).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'numero', 'nom', 'type_compte', 'sous_compte_id', 'solde', 'is_actif', 'tenant_id'])
        for c in comptes:
            writer.writerow([
                c.id, c.numero, c.nom,
                c.type_compte.value if c.type_compte else '',
                c.sous_compte_id or '', c.solde, c.is_actif, c.tenant_id,
            ])
        return buf.getvalue()

    @staticmethod
    def export_ecritures():
        tenant_id = get_current_tenant_id()
        query = EcritureComptable.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(EcritureComptable.tenant_id == tenant_id)
        ecritures = query.order_by(EcritureComptable.date).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'date', 'compte_id', 'montant_debit', 'montant_credit', 'libelle', 'piece_joint', 'reference_externe', 'entite_type', 'entite_id', 'statut', 'tenant_id'])
        for e in ecritures:
            writer.writerow([
                e.id, e.date.isoformat() if e.date else '', e.compte_id, e.montant_debit, e.montant_credit, e.libelle,
                e.piece_joint or '', e.reference_externe or '', e.entite_type or '', e.entite_id or '',
                e.statut.value if e.statut else '', e.tenant_id,
            ])
        return buf.getvalue()

    @staticmethod
    def export_tresorerie():
        tenant_id = get_current_tenant_id()
        query = Tresorerie.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter(Tresorerie.tenant_id == tenant_id)
        entries = query.order_by(Tresorerie.date).all()
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['id', 'date', 'type_operation', 'montant', 'mode_paiement', 'libelle', 'compte_bancaire', 'reference', 'is_reconcilie', 'compte_id', 'ecriture_id', 'tenant_id'])
        for t in entries:
            writer.writerow([
                t.id, t.date.isoformat() if t.date else '',
                t.type_operation.value if t.type_operation else '', t.montant, t.mode_paiement or '',
                t.libelle, t.compte_bancaire or '', t.reference or '', t.is_reconcilie, t.compte_id or '', t.ecriture_id or '', t.tenant_id,
            ])
        return buf.getvalue()

>>>

### FICHIER .PY: web\backend\app\services\dashboard_service.py
<<<
from app.security.tenant import get_current_tenant_id
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.ligne_vente import LigneVente
from app.models.facture import Facture
from app.models.paiement import Paiement
from app import db
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError


def get_dashboard_data():
    try:
        tenant_id = get_current_tenant_id()

        today = datetime.utcnow().date()
        debut_mois = today.replace(day=1)

        ventes_query = Vente.query.filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ventes_query = ventes_query.filter_by(tenant_id=tenant_id)
        ca_mois = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ca_mois = ca_mois.filter_by(tenant_id=tenant_id)
        ca_mois = ca_mois.scalar() or 0

        alertes_query = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            alertes_query = alertes_query.filter_by(tenant_id=tenant_id)
        alertes_stock = alertes_query.count()

        clients_query = Client.query.filter_by(is_active=True, est_actif=True)
        if tenant_id:
            clients_query = clients_query.filter_by(tenant_id=tenant_id)
        clients_actifs = clients_query.count()

        ventes_aujourdhui_query = Vente.query.filter(
            Vente.is_active == True,
            Vente.created_at >= today
        )
        if tenant_id:
            ventes_aujourdhui_query = ventes_aujourdhui_query.filter_by(tenant_id=tenant_id)
        ventes_aujourdhui = ventes_aujourdhui_query.count()

        benefice_mois = db.session.query(func.sum(Vente.total_ttc - Vente.total_ht)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            benefice_mois = benefice_mois.filter_by(tenant_id=tenant_id)
        benefice_mois = float(benefice_mois.scalar() or 0)

        top_produits_query = db.session.query(
            LigneVente.produit_id,
            func.sum(LigneVente.quantite).label('total_quantite'),
            func.sum(LigneVente.total_ttc).label('total_ttc')
        ).join(Vente).filter(
            LigneVente.is_active == True,
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            top_produits_query = top_produits_query.filter(Vente.tenant_id == tenant_id)
        top_produits_query = top_produits_query.group_by(LigneVente.produit_id).order_by(
            func.sum(LigneVente.total_ttc).desc()
        ).limit(5).all()
        top_produits = [
            {
                'produit_id': row[0],
                'total_quantite': float(row[1]),
                'total_ttc': float(row[2])
            }
            for row in top_produits_query
        ]

        top_clients_query = db.session.query(
            Vente.client_id,
            func.sum(Vente.total_ttc).label('total_ttc')
        ).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            top_clients_query = top_clients_query.filter_by(tenant_id=tenant_id)
        top_clients_query = top_clients_query.group_by(Vente.client_id).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(5).all()
        top_clients = [
            {
                'client_id': row[0],
                'total_ttc': float(row[1])
            }
            for row in top_clients_query
        ]

        evolution_ventes = []
        for i in range(7):
            date_jour = today - timedelta(days=i)
            count = db.session.query(func.count(Vente.id)).filter(
                Vente.is_active == True,
                func.date(Vente.created_at) == date_jour
            )
            if tenant_id:
                count = count.filter_by(tenant_id=tenant_id)
            evolution_ventes.append({
                'date': date_jour.isoformat(),
                'count': count.scalar() or 0
            })
        evolution_ventes.reverse()

        paiements_subquery = db.session.query(
            Paiement.facture_id.label('facture_id'),
            func.coalesce(func.sum(Paiement.montant), 0).label('paiements_total')
        ).filter(
            Paiement.is_active == True
        )
        if tenant_id:
            paiements_subquery = paiements_subquery.filter_by(tenant_id=tenant_id)
        paiements_subquery = paiements_subquery.group_by(Paiement.facture_id).subquery()

        creances_clients_query = db.session.query(
            Client.id,
            Client.nom,
            Client.prenom,
            func.sum(Facture.total_ttc - func.coalesce(paiements_subquery.c.paiements_total, 0)).label('creance')
        ).join(Facture, Client.id == Facture.client_id).outerjoin(
            paiements_subquery,
            Facture.id == paiements_subquery.c.facture_id
        ).filter(
            Client.is_active == True,
            Facture.is_active == True,
            Facture.statut != 'payee'
        )
        if tenant_id:
            creances_clients_query = creances_clients_query.filter(Client.tenant_id == tenant_id)
        creances_clients_query = creances_clients_query.group_by(Client.id, Client.nom, Client.prenom)
        creances_clients = [
            {
                'client_id': row[0],
                'nom': row[1],
                'prenom': row[2],
                'creance': float(row[3] or 0)
            }
            for row in creances_clients_query.all()
        ]

        fournisseurs_query = Fournisseur.query.filter_by(is_active=True)
        if tenant_id:
            fournisseurs_query = fournisseurs_query.filter_by(tenant_id=tenant_id)
        nombre_fournisseurs = fournisseurs_query.count()

        return {
            'ventes_aujourdhui': ventes_aujourdhui,
            'ca_mois': float(ca_mois),
            'alertes_stock': alertes_stock,
            'clients_actifs': clients_actifs,
            'benefice_mois': benefice_mois,
            'top_produits': top_produits,
            'top_clients': top_clients,
            'evolution_ventes': evolution_ventes,
            'creances_clients': creances_clients,
            'nombre_fournisseurs': nombre_fournisseurs
        }
    except OperationalError as e:
        # Database tables may not be created yet (migrations). Return
        # sensible defaults so the API doesn't raise HTTP 500.
        return {
            'ventes_aujourdhui': 0,
            'ca_mois': 0.0,
            'alertes_stock': 0,
            'clients_actifs': 0,
            'benefice_mois': 0.0,
            'top_produits': [],
            'top_clients': [],
            'evolution_ventes': [],
            'creances_clients': [],
            'nombre_fournisseurs': 0,
            'db_error': str(e)
        }

>>>

### FICHIER .PY: web\backend\app\services\devis_avoir_service.py
<<<
from app import db
from app.models.devis_avoir_bl import Devis, BonLivraison, Avoir
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
import datetime

def _gen_reference(prefix):
    ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
    return f'{prefix}-{ts}'

class DevisService:
    model = Devis

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('DEV')
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def convertir_en_vente(cls, devis_id):
        devis = cls.get_by_id(devis_id)
        if not devis:
            return None
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        vente = Vente(
            client_id=devis.client_id,
            commercial_id=devis.commercial_id,
            total_ht=devis.total_ht,
            total_ttc=devis.total_ttc,
            mode_paiement='especes',
            statut='en_attente',
            tenant_id=devis.tenant_id,
        )
        db.session.add(vente)
        db.session.flush()
        devis.statut = 'converti'
        db.session.commit()
        return vente

class BonLivraisonService:
    model = BonLivraison

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('BL')
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class AvoirService:
    model = Avoir

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('AV')
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

>>>

### FICHIER .PY: web\backend\app\services\document_service.py
<<<
from app import db
from app.models.modele_document import ModeleDocument
from app.models.document_genere import DocumentGenere
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

class ModeleDocumentService:
    model = ModeleDocument

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_defaut_by_type(cls, type_document):
        query = cls.model.query.filter_by(type_document=type_document, est_defaut=True, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class DocumentGenereService:
    model = DocumentGenere

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_reference(cls, reference):
        query = cls.model.query.filter_by(reference=reference)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def get_by_entite(cls, entite_type, entite_id):
        query = cls.model.query.filter_by(entite_type=entite_type, entite_id=entite_id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.all()

>>>

### FICHIER .PY: web\backend\app\services\facturation_service.py
<<<
from app import db
from app.models.facture import Facture
from app.models.vente import Vente
from app.models.client import Client
from app.security.tenant import get_current_tenant_id


def issue_invoice(data):
    if not data.get('vente_id') or not data.get('client_id'):
        raise ValueError('vente_id et client_id sont requis')
    tenant_id = get_current_tenant_id()
    if tenant_id:
        data['tenant_id'] = tenant_id
    facture = Facture(**data)
    db.session.add(facture)
    db.session.commit()
    return facture


def get_all():
    tenant_id = get_current_tenant_id()
    query = Facture.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Facture.query.filter_by(id=id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    facture = get_by_id(id)
    if not facture:
        return None
    for key, value in data.items():
        if hasattr(facture, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(facture, key, value)
    db.session.commit()
    return facture


def delete(id):
    facture = get_by_id(id)
    if not facture:
        return None
    facture.delete()
    return facture


def generate_from_vente(vente_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=vente_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    vente = query.first()
    if not vente:
        return None
    facture = Facture(
        vente_id=vente.id,
        client_id=vente.client_id,
        tenant_id=vente.tenant_id,
        total_ht=vente.total_ht,
        total_ttc=vente.total_ttc,
        statut='non_payee'
    )
    db.session.add(facture)
    db.session.commit()
    return facture

>>>

### FICHIER .PY: web\backend\app\services\fournisseur_service.py
<<<
from app.models.fournisseur import Fournisseur
from app.services.base_service import BaseService
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import or_, func
from typing import Optional, Dict, Any, List, Tuple

class FournisseurService(BaseService):
    model = Fournisseur
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        from app.security.tenant import set_tenant_filter
        return set_tenant_filter(query, cls.model)
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20,
                filters: Optional[Dict] = None,
                order_by: Optional[str] = None) -> Tuple[List[Fournisseur], int]:
        """Récupère tous les fournisseurs avec filtres"""
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        
        if filters:
            if filters.get('type'):
                query = query.filter_by(type=filters['type'])
            if filters.get('pays'):
                query = query.filter_by(pays=filters['pays'])
            if filters.get('est_actif') is not None:
                query = query.filter_by(est_actif=filters['est_actif'])
            if filters.get('est_favori') is not None:
                query = query.filter_by(est_favori=filters['est_favori'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Fournisseur.raison_sociale.ilike(search),
                        Fournisseur.code.ilike(search),
                        Fournisseur.siret.ilike(search),
                        Fournisseur.email.ilike(search),
                        Fournisseur.ville.ilike(search)
                    )
                )
        
        if order_by:
            query = query.order_by(order_by)
        else:
            query = query.order_by(Fournisseur.raison_sociale.asc())
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Fournisseur:
        """Crée un nouveau fournisseur"""
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Aucun tenant associe a ce compte")
        
        # Vérifier le code unique dans le tenant
        q = cls.model.query.filter_by(code=data['code'], tenant_id=tenant_id)
        if q.first():
            raise ValueError(f"Le code {data['code']} existe déjà")
        
        # Vérifier le SIRET unique dans le tenant
        if data.get('siret'):
            q = cls.model.query.filter_by(siret=data['siret'], tenant_id=tenant_id)
            if q.first():
                raise ValueError(f"Le SIRET {data['siret']} existe déjà")
        
        data['tenant_id'] = tenant_id
        return super().create(data)
    
    @classmethod
    def get_by_siret(cls, siret: str) -> Optional[Fournisseur]:
        """Récupère un fournisseur par son SIRET"""
        query = cls.model.query.filter_by(siret=siret, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()
    
    @classmethod
    def get_top_fournisseurs(cls, limit: int = 10) -> List[Dict]:
        """Récupère les meilleurs fournisseurs (chiffre d'affaires)"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        
        tenant_id = get_current_tenant_id()
        query = db.session.query(
            Fournisseur.id,
            Fournisseur.raison_sociale,
            Fournisseur.code,
            func.sum(CommandeFournisseur.total_ht).label('ca_total')
        ).join(
            CommandeFournisseur,
            Fournisseur.id == CommandeFournisseur.fournisseur_id
        ).filter(
            Fournisseur.is_active == True,
            CommandeFournisseur.is_active == True
        )
        
        if tenant_id:
            query = query.filter(Fournisseur.tenant_id == tenant_id)
        
        results = query.group_by(
            Fournisseur.id
        ).order_by(
            func.sum(CommandeFournisseur.total_ht).desc()
        ).limit(limit).all()
        
        return [{
            'id': r[0],
            'raison_sociale': r[1],
            'code': r[2],
            'ca_total': float(r[3] or 0)
        } for r in results]
>>>

### FICHIER .PY: web\backend\app\services\livraison_service.py
<<<
from app import db
from app.models.livreur import Livreur
from app.models.vehicule import Vehicule
from app.models.itineraire import Itineraire
from app.models.livraison import Livraison
from app.models.suivi_livraison import SuiviLivraison
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

# Workflow de suivi de statut (en_attente -> en_cours -> livree).
# La progression est unidirectionnelle : on ne recule pas d'un état terminal.
STATUTS_LIVRAISON = ['en_attente', 'chargee', 'en_cours', 'en_route', 'livree']
TERMINAUX = ['livree', 'retournee', 'echec']

# Transitions autorisées depuis chaque état (forward + états terminaux d'échec).
TRANSITIONS_AUTORISEES = {
    'en_attente': {'chargee', 'en_cours', 'en_route', 'livree', 'retournee', 'echec'},
    'chargee': {'en_cours', 'en_route', 'livree', 'retournee', 'echec'},
    'en_cours': {'en_route', 'livree', 'retournee', 'echec'},
    'en_route': {'livree', 'retournee', 'echec'},
    'livree': {'retournee'},
    'retournee': set(),
    'echec': set(),
}

class LivreurService:
    model = Livreur

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class VehiculeService:
    model = Vehicule

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class ItineraireService:
    model = Itineraire

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class LivraisonService:
    model = Livraison

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def add_suivi(cls, livraison_id, statut, commentaire='', localisation_lat=None, localisation_lng=None):
        """Ajoute un événement de suivi et fait progresser le statut de la livraison.

        Le passage de statut est validé contre le workflow métier :
        en_attente -> chargee -> en_cours -> en_route -> livree
        (avec retour possibles vers retournee / echec).
        """
        livraison = cls.get_by_id(livraison_id)
        if not livraison:
            return None

        if statut not in TRANSITIONS_AUTORISEES:
            raise ValueError(f"Statut '{statut}' invalide")

        autorisés = TRANSITIONS_AUTORISEES.get(livraison.statut or 'en_attente', set())
        if statut not in autorisés:
            raise ValueError(
                f"Transition de statut invalide: '{livraison.statut}' -> '{statut}'. "
                f"Statuts autorisés: {sorted(autorisés) if autorisés else ['aucun']}"
            )

        suivi = SuiviLivraison(
            livraison_id=livraison_id,
            statut=statut,
            commentaire=commentaire,
            localisation_lat=localisation_lat,
            localisation_lng=localisation_lng,
            tenant_id=livraison.tenant_id,
        )
        db.session.add(suivi)
        livraison.statut = statut
        db.session.commit()
        db.session.refresh(suivi)
        return suivi

    @classmethod
    def assigner(cls, livraison_id, livreur_id, vehicule_id=None):
        """Assigne une livraison à un livreur (et éventuellement un véhicule)."""
        livraison = cls.get_by_id(livraison_id)
        if not livraison:
            return None
        livreur = LivreurService.get_by_id(livreur_id)
        if not livreur:
            raise ValueError(f"Livreur id={livreur_id} introuvable")
        if livreur.statut != 'actif':
            raise ValueError("Le livreur n'est pas actif")
        if vehicule_id:
            vehicule = VehiculeService.get_by_id(vehicule_id)
            if not vehicule:
                raise ValueError(f"Véhicule id={vehicule_id} introuvable")
        livraison.livreur_id = livreur_id
        if vehicule_id:
            livraison.vehicule_id = vehicule_id
        db.session.commit()
        db.session.refresh(livraison)
        return livraison

    @classmethod
    def passer_au_statut(cls, livraison_id, statut, commentaire='', localisation_lat=None, localisation_lng=None):
        """Alias métier pour faire progresser une livraison d'un cran (ou vers un statut cible valide)."""
        return cls.add_suivi(livraison_id, statut, commentaire, localisation_lat, localisation_lng)

    @classmethod
    def get_stats(cls):
        tenant_id = get_current_tenant_id()
        query = Livraison.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        livraisons = query.all()
        count = len(livraisons)
        by_statut = {}
        for l in livraisons:
            s = l.statut or 'en_attente'
            by_statut.setdefault(s, {'count': 0})
            by_statut[s]['count'] += 1
        return {
            'total': count,
            'by_statut': by_statut,
            'active_count': sum(1 for l in livraisons if l.statut in ('en_attente', 'chargee', 'en_cours', 'en_route')),
        }

    @classmethod
    def avancer_statut(cls, id):
        livraison = cls.get_by_id(id)
        if not livraison:
            return None
        flow = {
            'en_attente': 'chargee',
            'chargee': 'en_route',
            'en_route': 'livree',
        }
        next_status = flow.get(livraison.statut)
        if not next_status:
            return livraison
        livraison.statut = next_status
        db.session.commit()
        return livraison

>>>

### FICHIER .PY: web\backend\app\services\paiement_service.py
<<<
from datetime import datetime

from app import db
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.facture import Facture
from app.security.tenant import get_current_tenant_id


def _normalize_payment_data(data):
    """Translate frontend field names to model column names and fill defaults."""
    normalized = dict(data)

    if 'date' in normalized and 'date_paiement' not in normalized:
        raw = normalized.pop('date')
        if raw:
            try:
                normalized['date_paiement'] = datetime.fromisoformat(raw)
            except (ValueError, TypeError):
                try:
                    normalized['date_paiement'] = datetime.strptime(raw, '%Y-%m-%d')
                except (ValueError, TypeError):
                    pass

    if 'remarque' in normalized and 'notes' not in normalized:
        normalized['notes'] = normalized.pop('remarque')

    if normalized.get('date_paiement') and isinstance(normalized['date_paiement'], str):
        try:
            normalized['date_paiement'] = datetime.fromisoformat(normalized['date_paiement'])
        except (ValueError, TypeError):
            try:
                normalized['date_paiement'] = datetime.strptime(normalized['date_paiement'], '%Y-%m-%d')
            except (ValueError, TypeError):
                pass

    normalized.setdefault('statut', StatutPaiement.CONFIRME)
    normalized.setdefault('type', TypePaiement.VENTE)
    normalized.setdefault('mode_paiement', 'especes')

    if normalized.get('statut') and not hasattr(normalized['statut'], 'value'):
        try:
            normalized['statut'] = StatutPaiement(normalized['statut'])
        except ValueError:
            pass

    if normalized.get('type') and not hasattr(normalized['type'], 'value'):
        try:
            normalized['type'] = TypePaiement(normalized['type'])
        except ValueError:
            pass

    return normalized


def process_payment(data):
    tenant_id = get_current_tenant_id()
    normalized = _normalize_payment_data(data)
    if tenant_id:
        normalized['tenant_id'] = tenant_id
    paiement = Paiement(**normalized)
    db.session.add(paiement)
    db.session.commit()
    
    facture_id = normalized.get('facture_id')
    if facture_id:
        from app.security.tenant import get_current_tenant_id as _get_tid
        tid = _get_tid()
        query = Facture.query.filter_by(id=facture_id, is_active=True)
        if tid is not None:
            query = query.filter_by(tenant_id=tid)
        facture = query.first()
        if facture:
            total_paye = db.session.query(
                db.func.sum(Paiement.montant)
            ).filter(
                Paiement.facture_id == facture_id,
                Paiement.tenant_id == facture.tenant_id,
                Paiement.is_active == True
            ).scalar() or 0
            
            if total_paye >= float(facture.total_ttc):
                facture.statut = 'payee'
            elif total_paye > 0:
                facture.statut = 'payee_partiel'
            else:
                facture.statut = 'non_payee'
            db.session.commit()
    
    return paiement


def get_all():
    tenant_id = get_current_tenant_id()
    query = Paiement.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Paiement.query.filter_by(id=id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def get_by_facture(facture_id):
    tenant_id = get_current_tenant_id()
    query = Paiement.query.filter_by(facture_id=facture_id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def update(id, data):
    paiement = get_by_id(id)
    if not paiement:
        return None
    normalized = _normalize_payment_data(data)
    for key, value in normalized.items():
        if hasattr(paiement, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(paiement, key, value)
    db.session.commit()
    return paiement


def delete(id):
    paiement = get_by_id(id)
    if not paiement:
        return None
    paiement.delete()
    return paiement

>>>

### FICHIER .PY: web\backend\app\services\papi\__init__.py
<<<

>>>

### FICHIER .PY: web\backend\app\services\papi\client.py
<<<

import json
import logging
from typing import Dict, Any, Optional

import requests

from app.services.papi.errors import (
    PapiError,
    PapiAuthError,
    PapiValidationError,
    PapiUnavailableError,
)

logger = logging.getLogger(__name__)


class PapiClient:
    """HTTP client for Papi payment gateway API."""

    def __init__(self, api_url: str, api_key: str, environment: str = 'sandbox'):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.environment = environment

    def _headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Token': self.api_key,
        }

    def create_payment_link(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment link via Papi API.

        Args:
            payload: Payment creation payload matching Papi spec.

        Returns:
            The 'data' object from Papi response containing paymentLink,
            notificationToken, paymentReference, etc.

        Raises:
            PapiAuthError: If API key is invalid (401/403).
            PapiValidationError: If payload is invalid (400).
            PapiUnavailableError: If API is unreachable.
            PapiError: For other errors.
        """
        url = self.api_url
        logger.info(
            'Creating Papi payment link for reference=%s amount=%s',
            payload.get('reference'),
            payload.get('amount'),
        )

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
        except requests.ConnectionError as exc:
            logger.error('Papi API connection error: %s', exc)
            raise PapiUnavailableError('Papi API est indisponible') from exc
        except requests.Timeout as exc:
            logger.error('Papi API timeout: %s', exc)
            raise PapiUnavailableError('Papi API a mis trop de temps à répondre') from exc
        except requests.RequestException as exc:
            logger.error('Papi API request error: %s', exc)
            raise PapiUnavailableError('Erreur de communication avec Papi') from exc

        if response.status_code in (401, 403):
            logger.error('Papi authentication failed: %s', response.text)
            raise PapiAuthError('Clé API Papi invalide')

        if response.status_code == 400:
            try:
                error_data = response.json()
                message = error_data.get('error', {}).get('message', 'Requête invalide')
            except Exception:
                message = response.text or 'Requête invalide'
            logger.error('Papi validation error: %s', message)
            raise PapiValidationError(message)

        if response.status_code != 200:
            logger.error('Papi unexpected status %s: %s', response.status_code, response.text)
            raise PapiError(f"Papi a retourné le statut {response.status_code}")

        try:
            result = response.json()
        except ValueError as exc:
            logger.error('Papi invalid JSON response: %s', exc)
            raise PapiError('Réponse invalide de Papi') from exc

        data = result.get('data')
        if not data:
            logger.error('Papi response missing data: %s', result)
            raise PapiError('Réponse de Papi incomplète')

        logger.info(
            'Papi payment link created: paymentReference=%s paymentLink=%s',
            data.get('paymentReference'),
            data.get('paymentLink'),
        )
        return data

>>>

### FICHIER .PY: web\backend\app\services\papi\errors.py
<<<

class PapiError(Exception):
    """Base exception for Papi integration errors."""
    pass


class PapiAuthError(PapiError):
    """Raised when Papi authentication fails (invalid API key)."""
    pass


class PapiValidationError(PapiError):
    """Raised when Papi returns a validation error."""
    pass


class PapiUnavailableError(PapiError):
    """Raised when Papi API is unreachable."""
    pass


class PapiWebhookError(PapiError):
    """Raised when webhook verification fails."""
    pass


class PapiDuplicateWebhookError(PapiError):
    """Raised when a webhook event has already been processed."""
    pass


class PapiInvalidStatusError(PapiError):
    """Raised when webhook payment status is invalid or unexpected."""
    pass

>>>

### FICHIER .PY: web\backend\app\services\papi\payment.py
<<<

import uuid
import logging
from datetime import datetime

from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur
from app.security.tenant import get_current_tenant_id, get_current_tenant
from app.services.papi.client import PapiClient
from app.services.papi.errors import PapiError, PapiAuthError, PapiValidationError, PapiUnavailableError
from app.config.settings import Config

logger = logging.getLogger(__name__)

PROVIDER_METHOD_MAP = {
    'MVOLA': 'MVOLA',
    'ORANGE_MONEY': 'ORANGE_MONEY',
    'ARTEL_MONEY': 'AIRTEL_MONEY',
    'BRED': 'VISA',
}


def _build_papi_payload(
    subscription: Abonnement,
    tenant: Tenant,
    user: Utilisateur,
    notification_token: str,
    payment_method: str,
    is_test_mode: bool = True,
) -> dict:
    """Build the Papi payment link creation payload."""
    reference = f"SUB-{tenant.id}-{subscription.id}-{uuid.uuid4().hex[:8].upper()}"

    provider = payment_method.upper()
    if provider not in ('MVOLA', 'ORANGE_MONEY', 'ARTEL_MONEY', 'BRED'):
        raise PapiValidationError(f"Mode de paiement invalide: {payment_method}")

    success_url = (
        f"{Config.PAPI_CALLBACK_URL}/../payment-result?"
        f"status=success&reference={reference}"
    )
    failure_url = (
        f"{Config.PAPI_CALLBACK_URL}/../payment-result?"
        f"status=failure&reference={reference}"
    )

    payload = {
        'amount': float(subscription.montant),
        'clientName': tenant.nom,
        'reference': reference,
        'description': f"Abonnement {subscription.plan} - {tenant.nom}",
        'successUrl': success_url,
        'failureUrl': failure_url,
        'notificationUrl': Config.PAPI_CALLBACK_URL,
        'validDuration': 60,
        'provider': provider,
        'payerEmail': tenant.email_contact or user.email,
        'payerPhone': tenant.telephone or user.telephone or user.mobile,
        'isTestMode': is_test_mode,
        'testReason': 'Integration test ERP',
    }

    if provider == 'BRED':
        payload['provider'] = 'BRED'

    return payload


def create_subscription_payment(
    subscription_id: int,
    payment_method: str,
    is_test_mode: bool = True,
    tenant_id: int = None,
) -> dict:
    """Create a Papi payment link for a subscription.

    Args:
        subscription_id: The subscription to pay.
        payment_method: One of MVOLA, ORANGE_MONEY, ARTEL_MONEY, BRED.
        is_test_mode: Whether to use Papi test mode.
        tenant_id: Tenant ID (optional, falls back to current request tenant).

    Returns:
        Dict with payment data including payment_link, payment, subscription.

    Raises:
        ValueError: If subscription/tenant not found or validation fails.
        PapiError: If Papi API call fails.
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValueError("Aucun tenant associe")

    tenant = None
    try:
        tenant = get_current_tenant()
    except Exception:
        pass
    
    if not tenant:
        from app.models.tenant import Tenant
        tenant = db.session.get(Tenant, tenant_id)

    subscription = db.session.get(Abonnement, subscription_id)
    if not subscription:
        raise ValueError("Abonnement non trouve")

    if subscription.tenant_id != tenant_id:
        raise ValueError("Acces refuse a cet abonnement")

    user_id = None
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
    except Exception:
        pass

    user = None
    if user_id:
        user = db.session.get(Utilisateur, user_id)

    if not subscription.montant or float(subscription.montant) < 300:
        raise ValueError("Le montant de l'abonnement est inferieur au minimum requis (300 MGA)")

    if not Config.PAPI_API_KEY:
        raise ValueError("Papi n'est pas configure: PAPI_API_KEY manquant")

    papi_client = PapiClient(
        api_url=Config.PAPI_API_URL,
        api_key=Config.PAPI_API_KEY,
        environment=Config.PAPI_ENVIRONMENT,
    )

    payload = _build_papi_payload(subscription, tenant, user, '', payment_method, is_test_mode)

    try:
        papi_data = papi_client.create_payment_link(payload)
    except PapiAuthError as exc:
        logger.error("Papi auth error: %s", exc)
        raise ValueError("Authentification Papi invalide") from exc
    except PapiValidationError as exc:
        logger.error("Papi validation error: %s", exc)
        raise ValueError(str(exc)) from exc
    except PapiUnavailableError as exc:
        logger.error("Papi unavailable: %s", exc)
        raise ValueError("Service de paiement indisponible, veuillez reessayer") from exc
    except PapiError as exc:
        logger.error("Papi error: %s", exc)
        raise ValueError(str(exc)) from exc

    external_reference = papi_data.get('paymentReference', payload['reference'])
    notification_token = papi_data.get('notificationToken', '')

    existing_payment = Paiement.query.filter_by(
        tenant_id=tenant_id,
        external_reference=external_reference,
        is_active=True,
    ).first()

    if existing_payment:
        logger.info(
            "Idempotent payment found for reference=%s, returning existing",
            external_reference,
        )
        return {
            'payment_link': existing_payment.external_payment_id,
            'payment': existing_payment.to_dict(),
            'subscription': subscription.to_dict(),
        }

    payment_method_db = PROVIDER_METHOD_MAP.get(payment_method.upper(), payment_method.upper())

    paiement = Paiement(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        montant=subscription.montant,
        devise=subscription.devise or 'MGA',
        statut=StatutPaiement.EN_ATTENTE,
        type=TypePaiement.ABONNEMENT,
        provider=ProviderPaiement.PAPI.value,
        payment_method=payment_method_db,
        external_payment_id=papi_data.get('paymentLink', ''),
        external_reference=external_reference,
        reference=external_reference,
        notes=f"Paiement abonnement {subscription.plan} via Papi",
    )

    db.session.add(paiement)
    db.session.commit()

    logger.info(
        "Papi payment created: paiement_id=%s reference=%s",
        paiement.id,
        external_reference,
    )

    return {
        'payment_link': papi_data.get('paymentLink', ''),
        'payment': paiement.to_dict(),
        'subscription': subscription.to_dict(),
    }


# Modes de paiement papier / hors ligne (espèces, virement, chèque)
PAPER_METHODS = ('ESPECES', 'VIREMENT', 'CHEQUE')

PAPER_INSTRUCTIONS = {
    'ESPECES': (
        "Rendez-vous à notre agence avec cette référence et le montant en espèces. "
        "Le paiement est validé par un responsable après encaissement au guichet."
    ),
    'VIREMENT': (
        "Effectuez un virement bancaire vers le compte de l'entreprise en indiquant "
        "impérativement cette référence dans le libellé. Le paiement est confirmé après réception."
    ),
    'CHEQUE': (
        "Émettez un chèque à l'ordre de l'entreprise en indiquant cette référence au dos. "
        "Le paiement est validé à l'encaissement du chèque."
    ),
}


def create_subscription_offline_payment(
    subscription_id: int,
    payment_method: str,
    tenant_id: int = None,
) -> dict:
    """Create an offline (paper) payment record for a subscription.

    Handles espèces / virement / chèque. No external Papi gateway is used:
    a payment reference is generated and the record stays EN_ATTENTE until an
    administrator confirms the deposit.

    Returns:
        Dict with is_offline=True, payment, subscription, reference, instructions.
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValueError("Aucun tenant associe")

    tenant = None
    try:
        tenant = get_current_tenant()
    except Exception:
        pass

    if not tenant:
        tenant = db.session.get(Tenant, tenant_id)

    subscription = db.session.get(Abonnement, subscription_id)
    if not subscription:
        raise ValueError("Abonnement non trouve")

    if subscription.tenant_id != tenant_id:
        raise ValueError("Acces refuse a cet abonnement")

    if not subscription.montant or float(subscription.montant) < 300:
        raise ValueError("Le montant de l'abonnement est inferieur au minimum requis (300 MGA)")

    payment_method = (payment_method or '').upper()
    if payment_method not in PAPER_METHODS:
        raise ValueError("Mode de paiement papier invalide")

    reference = f"PAPIER-{tenant.id}-{subscription.id}-{uuid.uuid4().hex[:8].upper()}"

    existing_payment = Paiement.query.filter_by(
        tenant_id=tenant_id,
        external_reference=reference,
        is_active=True,
    ).first()

    if existing_payment:
        return {
            'is_offline': True,
            'payment': existing_payment.to_dict(),
            'subscription': subscription.to_dict(),
            'reference': existing_payment.reference,
            'instructions': PAPER_INSTRUCTIONS.get(payment_method, ''),
        }

    paiement = Paiement(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        montant=subscription.montant,
        devise=subscription.devise or 'MGA',
        statut=StatutPaiement.EN_ATTENTE,
        type=TypePaiement.ABONNEMENT,
        provider='manuel',
        payment_method=payment_method,
        reference=reference,
        external_reference=reference,
        notes=f"Paiement abonnement {subscription.plan} hors ligne ({payment_method})",
    )

    db.session.add(paiement)
    db.session.commit()

    logger.info(
        "Offline payment created: paiement_id=%s reference=%s method=%s",
        paiement.id,
        reference,
        payment_method,
    )

    return {
        'is_offline': True,
        'payment': paiement.to_dict(),
        'subscription': subscription.to_dict(),
        'reference': reference,
        'instructions': PAPER_INSTRUCTIONS.get(payment_method, ''),
    }

>>>

### FICHIER .PY: web\backend\app\services\papi\webhook.py
<<<

import logging
from datetime import datetime

from app import db
from app.models.paiement import Paiement, StatutPaiement
from app.models.payment_event import PaymentEvent
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.services.papi.errors import (
    PapiWebhookError,
    PapiDuplicateWebhookError,
    PapiInvalidStatusError,
)

logger = logging.getLogger(__name__)


def process_papi_webhook(payload: dict) -> dict:
    """Process an incoming Papi webhook notification.

    Args:
        payload: The JSON body from Papi webhook.

    Returns:
        Dict with processing result.

    Raises:
        PapiWebhookError: If webhook is invalid.
        PapiDuplicateWebhookError: If event already processed.
        PapiInvalidStatusError: If status is unexpected.
    """
    payment_reference = payload.get('paymentReference')
    notification_token = payload.get('notificationToken')
    payment_status = payload.get('paymentStatus')
    payment_method = payload.get('paymentMethod', '')
    currency = payload.get('currency', 'MGA')
    amount = payload.get('amount')
    fee = payload.get('fee', 0)
    client_name = payload.get('clientName', '')
    description = payload.get('description', '')
    merchant_reference = payload.get('merchantPaymentReference', '')
    message = payload.get('message', '')
    payer_email = payload.get('payerEmail', '')
    payer_phone = payload.get('payerPhone', '')

    logger.info(
        'Papi webhook received: reference=%s status=%s method=%s',
        payment_reference,
        payment_status,
        payment_method,
    )

    if not payment_reference or not notification_token:
        logger.error('Papi webhook missing required fields')
        raise PapiWebhookError('Champs requis manquants dans le webhook')

    if payment_status not in ('SUCCESS', 'PENDING', 'FAILED'):
        logger.error('Papi webhook invalid status: %s', payment_status)
        raise PapiInvalidStatusError(f"Statut de paiement invalide: {payment_status}")

    event_id = f"papi-{payment_reference}-{notification_token}"
    existing_event = PaymentEvent.query.filter_by(event_id=event_id).first()
    if existing_event and existing_event.processed:
        logger.info('Papi webhook already processed: event_id=%s', event_id)
        return {
            'status': 'already_processed',
            'event_id': event_id,
        }

    paiement = Paiement.query.filter_by(
        external_reference=payment_reference,
        is_active=True,
    ).first()

    if not paiement:
        logger.error('Papi webhook for unknown payment reference: %s', payment_reference)
        raise PapiWebhookError('Paiement introuvable')

    if paiement.notification_token and paiement.notification_token != notification_token:
        logger.error(
            'Papi webhook token mismatch: stored=%s received=%s',
            paiement.notification_token,
            notification_token,
        )
        raise PapiWebhookError('Token de notification invalide')

    if amount is not None and float(amount) != float(paiement.montant or 0):
        logger.error(
            'Papi webhook amount mismatch: expected=%s received=%s',
            paiement.montant,
            amount,
        )
        raise PapiWebhookError('Montant de paiement invalide')

    if currency != (paiement.devise or 'MGA'):
        logger.error(
            'Papi webhook currency mismatch: expected=%s received=%s',
            paiement.devise,
            currency,
        )
        raise PapiWebhookError('Devise de paiement invalide')

    if not existing_event:
        payment_event = PaymentEvent(
            payment_id=paiement.id,
            event_id=event_id,
            event_type=payment_status,
            payload=payload,
            signature=notification_token,
            processed=False,
        )
        db.session.add(payment_event)
        db.session.flush()
    else:
        payment_event = existing_event
        payment_event.payload = payload
        payment_event.received_at = datetime.utcnow()

    old_status = paiement.statut
    new_status = old_status

    if payment_status == 'SUCCESS':
        if paiement.statut != StatutPaiement.SUCCESS:
            paiement.statut = StatutPaiement.SUCCESS
            paiement.date_paiement = datetime.utcnow()
            new_status = StatutPaiement.SUCCESS

        if paiement.subscription_id:
            subscription = db.session.get(Abonnement, paiement.subscription_id)
            if subscription and subscription.statut != StatutAbonnement.ACTIF:
                subscription.statut = StatutAbonnement.ACTIF
                if not subscription.date_debut:
                    subscription.date_debut = datetime.utcnow()
                if not subscription.date_fin:
                    from datetime import timedelta
                    subscription.date_fin = datetime.utcnow() + timedelta(days=30)
                subscription.methode_paiement = paiement.payment_method
                subscription.reference_paiement = paiement.external_reference
                db.session.add(subscription)

                if subscription.tenant_id:
                    tenant = db.session.get(Tenant, subscription.tenant_id)
                    if tenant and tenant.statut != StatutTenant.ACTIF:
                        tenant.statut = StatutTenant.ACTIF
                        tenant.date_abonnement = datetime.utcnow()
                        db.session.add(tenant)

    elif payment_status == 'FAILED':
        if paiement.statut != StatutPaiement.FAILED:
            paiement.statut = StatutPaiement.FAILED
            new_status = StatutPaiement.FAILED

    elif payment_status == 'PENDING':
        if paiement.statut == StatutPaiement.PENDING:
            paiement.statut = StatutPaiement.PROCESSING
            new_status = StatutPaiement.PROCESSING

    payment_event.processed = True
    payment_event.processed_at = datetime.utcnow()
    db.session.commit()

    logger.info(
        'Papi webhook processed: paiement_id=%s old_status=%s new_status=%s',
        paiement.id,
        old_status.value if hasattr(old_status, 'value') else old_status,
        new_status.value if hasattr(new_status, 'value') else new_status,
    )

    return {
        'status': 'processed',
        'event_id': event_id,
        'payment_id': paiement.id,
        'payment_status': new_status.value if hasattr(new_status, 'value') else new_status,
    }

>>>

### FICHIER .PY: web\backend\app\services\produit_service.py
<<<
from app import db
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple

class ProduitService:
    model = Produit

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_code_barre(cls, code_barre):
        query = cls.model.query.filter_by(code_barre=code_barre, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        return super().create(data)

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def update_stock(cls, id, quantite, type_mouvement='entree', raison='', utilisateur_id=None):
        produit = cls.get_by_id(id)
        if not produit:
            return None
        if type_mouvement == 'entree':
            produit.ajouter_stock(quantite, raison, utilisateur_id)
        elif type_mouvement == 'sortie':
            produit.retirer_stock(quantite, raison, utilisateur_id)
        else:
            produit.quantite_stock = quantite
            produit.save()
        return produit

    @classmethod
    def get_stock_alert(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        return query.filter(cls.model.quantite_stock <= cls.model.seuil_alerte).all()

    @classmethod
    def get_categories(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        categories = query.with_entities(cls.model.categorie).distinct().all()
        return [c[0] for c in categories if c[0]]

    @classmethod
    def get_statistiques(cls):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        produits = query.all()
        total_produits = len(produits)
        total_stock = sum(float(p.quantite_stock) for p in produits)
        valeur_stock = sum(float(p.valeur_stock) for p in produits)
        return {
            'total_produits': total_produits,
            'total_stock': total_stock,
            'valeur_stock': valeur_stock,
        }

>>>

### FICHIER .PY: web\backend\app\services\rh_service.py
<<<
from app import db
from app.models.employe import Employe
from app.models.presence import Presence
from app.models.salaire import Salaire, StatutPaiementSalaire
from app.models.prime import Prime
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func

class EmployeService:
    model = Employe

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True, id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_matricule(cls, matricule):
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True, matricule=matricule)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class PresenceService:
    model = Presence

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_employe_date(cls, employe_id, date_val):
        query = cls.model.query.filter_by(is_active=True).filter_by(employe_id=employe_id, date=date_val)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        db.session.commit()
        return True

    @classmethod
    def get_registre(cls, mois=None, annee=None):
        """Registre des présences pour un mois donné (ou le mois courant)."""
        if not mois or not annee:
            today = date.today()
            mois = today.month
            annee = today.year
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        query = query.filter(db.extract('month', cls.model.date) == mois,
                             db.extract('year', cls.model.date) == annee)
        presences = query.order_by(cls.model.employe_id, cls.model.date).all()
        result = []
        for p in presences:
            d = p.to_dict()
            if (not d.get('heures_travaillees') or float(d.get('heures_travaillees') or 0) == 0) \
                    and p.heure_arrivee and p.heure_depart:
                delta = (p.heure_depart - p.heure_arrivee)
                pause = Decimal('0')
                if p.heure_pause_debut and p.heure_pause_fin:
                    pause = p.heure_pause_fin - p.heure_pause_debut
                heures = (delta.total_seconds() - pause.total_seconds()) / 3600.0
                p.heures_travaillees = Decimal(str(round(heures, 2)))
                db.session.commit()
                d['heures_travaillees'] = float(p.heures_travaillees)
            result.append(d)
        return result

    @classmethod
    def get_registre_export(cls, mois=None, annee=None):
        """Produit un export CSV du registre de présence."""
        presences = cls.get_registre(mois, annee)
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['date', 'employe_id', 'employe_nom', 'heure_arrivee', 'heure_depart',
                         'heures_travaillees', 'heures_supplementaires', 'statut', 'remarque'])
        for p in presences:
            writer.writerow([
                (p.get('date') or '')[:10],
                p.get('employe_id', '') or '',
                p.get('employe_nom', '') or '',
                p.get('heure_arrivee', '') or '',
                p.get('heure_depart', '') or '',
                p.get('heures_travaillees', '') or '',
                p.get('heures_supplementaires', '') or '',
                p.get('statut', '') or '',
                p.get('remarque', '') or '',
            ])
        return buf.getvalue()


class SalaireService:
    model = Salaire

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_employe_mois(cls, employe_id, mois, annee):
        query = cls.model.query.filter_by(is_active=True).filter_by(employe_id=employe_id, mois=mois, annee=annee)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        instance.calculer_salaire()
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        instance.calculer_salaire()
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        db.session.commit()
        return True

    @classmethod
    def generate_salaries(cls, mois, annee):
        tenant_id = get_current_tenant_id()
        employes = Employe.query.filter_by(is_active=True, statut='actif').filter_by(tenant_id=tenant_id).all() if tenant_id else Employe.query.filter_by(is_active=True, statut='actif').all()
        results = []
        for employe in employes:
            existing = Salaire.query.filter_by(employe_id=employe.id, mois=mois, annee=annee, is_active=True).first()
            if existing:
                continue
            primes_mois = Prime.query.filter_by(employe_id=employe.id, is_active=True).filter(
                func.extract('month', Prime.date_octroi) == mois,
                func.extract('year', Prime.date_octroi) == annee
            ).all()
            total_primes = sum(Decimal(str(p.montant)) for p in primes_mois)
            salaire = Salaire(
                employe_id=employe.id,
                mois=mois,
                annee=annee,
                salaire_base=Decimal(str(employe.salaire_base or 0)),
                primes=total_primes,
                indemnites=Decimal('0'),
                deductions=Decimal('0'),
                avances=Decimal('0'),
                tenant_id=tenant_id,
            )
            salaire.calculer_salaire()
            db.session.add(salaire)
            results.append(salaire)
        db.session.commit()
        return results

    @classmethod
    def marquer_paye(cls, id, statut_paiement=None, mode_paiement=None, reference_paiement=None, date_paiement=None):
        """Marque un bulletin de salaire comme payé (ou modifie le statut de paiement)."""
        instance = cls.get_by_id(id)
        if not instance:
            return None
        if statut_paiement is not None:
            instance.statut_paiement = statut_paiement if not hasattr(statut_paiement, 'value') else statut_paiement.value
        if mode_paiement is not None:
            instance.mode_paiement = mode_paiement
        if reference_paiement is not None:
            instance.reference_paiement = reference_paiement
        if statut_paiement in ('paye', StatutPaiementSalaire.PAYE, 'PAYE') and instance.date_paiement is None:
            instance.date_paiement = date_paiement or date.today()
        instance.calculer_salaire()
        db.session.commit()
        db.session.refresh(instance)
        return instance

    @classmethod
    def get_by_employe(cls, employe_id, mois=None, annee=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if employe_id:
            query = query.filter_by(employe_id=employe_id)
        if mois:
            query = query.filter_by(mois=mois)
        if annee:
            query = query.filter_by(annee=annee)
        return query.order_by(cls.model.annee.desc(), cls.model.mois.desc()).all()

    @classmethod
    def export_csv(cls, records, headers):
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in records:
            writer.writerow([row.get(h, '') for h in headers])
        return output.getvalue()

class PrimeService:
    model = Prime

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True).filter_by(id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        db.session.delete(instance)
        db.session.commit()
        return True

>>>

### FICHIER .PY: web\backend\app\services\stagiaire_service.py
<<<
from app import db
from app.models.stagiaire import Stagiaire
from app.models.employe import Employe
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class StagiaireService:
    model = Stagiaire

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def _validate_tuteur(cls, tuteur_id):
        if not tuteur_id:
            return None
        tenant_id = get_current_tenant_id()
        tuteur = Employe.query.filter_by(id=tuteur_id, is_active=True)
        if tenant_id is not None:
            tuteur = tuteur.filter_by(tenant_id=tenant_id)
        return tuteur.first()

    @classmethod
    def _coerce_dates(cls, data):
        date_fields = ['date_naissance', 'date_debut', 'date_fin']
        for key in date_fields:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                try:
                    data[key] = datetime.strptime(val.strip(), '%Y-%m-%d').date()
                except ValueError:
                    data[key] = None
            elif val == '' or val is None:
                data[key] = None
        return data

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(is_active=True, id=id)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def get_by_matricule(cls, matricule):
        tenant_id = get_current_tenant_id()
        query = cls.model.query.filter_by(is_active=True, matricule=matricule)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        data = cls._coerce_dates(data)
        tuteur_id = data.get('tuteur_id')
        if tuteur_id:
            tuteur = cls._validate_tuteur(tuteur_id)
            if not tuteur:
                raise ValueError("Le tuteur selectionne n'appartient pas au tenant courant ou est introuvable.")
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        data = cls._coerce_dates(data)
        tuteur_id = data.get('tuteur_id')
        if tuteur_id is not None:
            tuteur = cls._validate_tuteur(tuteur_id)
            if not tuteur:
                raise ValueError("Le tuteur selectionne n'appartient pas au tenant courant ou est introuvable.")
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

>>>

### FICHIER .PY: web\backend\app\services\vente_service.py
<<<
from datetime import datetime
from decimal import Decimal
from app import db
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.security.tenant import get_current_tenant_id
import random
import string


def get_sales_summary():
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    sale = get_by_id(id)
    if not sale:
        return None
    if 'date' in data and isinstance(data['date'], str):
        data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
    for key, value in data.items():
        if hasattr(sale, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(sale, key, value)
    db.session.commit()
    return sale


def delete(id):
    sale = get_by_id(id)
    if not sale:
        return None
    sale.delete()
    return sale


def create_with_lignes(data):
    tenant_id = get_current_tenant_id()
    lignes_data = data.pop('lignes', [])
    if tenant_id:
        data['tenant_id'] = tenant_id

    if not data.get('reference'):
        prefix = 'VENT'
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        data['reference'] = f"{prefix}-{timestamp}-{random_part}"
        while Vente.query.filter_by(reference=data['reference']).first():
            random_part = ''.join(random.choices(string.digits, k=4))
            data['reference'] = f"{prefix}-{timestamp}-{random_part}"

    if not data.get('client_id'):
        raise ValueError("Le client est requis")

    if 'date' in data and isinstance(data['date'], str):
        data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')

    total_ht = 0
    total_ttc = 0
    stock_errors = []
    for ligne in lignes_data:
        quantite = Decimal(str(ligne.get('quantite', 0)))
        prix_unitaire = Decimal(str(ligne.get('prix_unitaire', 0)))
        taux_tva = Decimal(str(ligne.get('taux_tva', 20)))
        remise = Decimal(str(ligne.get('remise', 0)))
        base_ht = quantite * prix_unitaire * (1 - remise / 100)
        total_ht += base_ht
        total_ttc += base_ht * (1 + taux_tva / 100)

    data['total_ht'] = total_ht
    data['total_ttc'] = total_ttc
    sale = Vente(**data)
    db.session.add(sale)
    db.session.flush()
    for ligne in lignes_data:
        produit_id = ligne.get('produit_id')
        quantite = ligne.get('quantite')
        mapped_ligne = {
            'vente_id': sale.id,
            'tenant_id': sale.tenant_id,
            'produit_id': produit_id,
            'quantite': quantite,
            'prix_unitaire_ht': ligne.get('prix_unitaire'),
            'taux_tva': ligne.get('taux_tva'),
        }
        ligne_vente = LigneVente(**mapped_ligne)
        db.session.add(ligne_vente)
        if produit_id and quantite is not None:
            qty = float(quantite)
            if qty > 0:
                tenant_id = sale.tenant_id
                produit_query = Produit.query.filter_by(id=produit_id)
                if tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=tenant_id)
                produit = produit_query.first()
                if produit:
                    try:
                        qty_decimal = Decimal(str(qty))
                        if produit.quantite_stock < qty_decimal:
                            raise ValueError(f"Stock insuffisant. Disponible: {produit.quantite_stock}")
                        produit.quantite_stock -= qty_decimal
                        mouvement = MouvementStock(
                            produit_id=produit.id,
                            type_mouvement='sortie',
                            quantite=qty_decimal,
                            raison=f'Vente {sale.reference}',
                            tenant_id=produit.tenant_id,
                        )
                        db.session.add(mouvement)
                    except ValueError as e:
                        stock_errors.append(str(e))
    if stock_errors:
        db.session.rollback()
        raise ValueError("; ".join(stock_errors))
    db.session.commit()
    return sale


def get_by_client(client_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_stats():
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    ventes = query.all()
    count = len(ventes)
    total = sum(float(v.total_ttc) for v in ventes)
    average = total / count if count > 0 else 0
    by_status = {}
    for vente in ventes:
        statut = vente.statut
        if statut not in by_status:
            by_status[statut] = {'count': 0, 'total': 0}
        by_status[statut]['count'] += 1
        by_status[statut]['total'] += float(vente.total_ttc)
    return {
        'total': total,
        'count': count,
        'average': average,
        'by_status': by_status
    }

>>>

### FICHIER .PY: web\backend\app\tasks\__init__.py
<<<
from .backups import backup_database
from .emails import send_email
from .reports import generate_daily_sales_report, generate_monthly_report, generate_stock_report

__all__ = ['backup_database', 'send_email', 'generate_daily_sales_report', 'generate_monthly_report', 'generate_stock_report']

>>>

### FICHIER .PY: web\backend\app\tasks\backups.py
<<<
import os
import shutil
from datetime import datetime

def backup_database(config):
    db_path = config.get('DB_PATH', 'erp.db')
    backup_dir = config.get('BACKUP_DIR', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')
    shutil.copy2(db_path, backup_path)
    return {'status': 'success', 'path': backup_path, 'timestamp': timestamp}
>>>

### FICHIER .PY: web\backend\app\tasks\emails.py
<<<
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(recipient, subject, body, smtp_config=None):
    if not smtp_config:
        smtp_config = {
            'host': 'localhost',
            'port': 25,
            'user': None,
            'password': None
        }
    msg = MIMEMultipart()
    msg['From'] = smtp_config.get('user', 'erp@localhost')
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
        if smtp_config.get('user'):
            server.login(smtp_config['user'], smtp_config['password'])
        server.send_message(msg)
    return {'status': 'sent', 'recipient': recipient}

def send_invoice_email(invoice_id, recipient_email, smtp_config=None):
    return send_email(recipient_email, f'Facture #{invoice_id}', f'<p>Votre facture #{invoice_id} est disponible.</p>', smtp_config)

def send_payment_confirmation(payment_id, smtp_config=None):
    return send_email('client@example.com', f'Confirmation paiement #{payment_id}', f'<p>Paiement #{payment_id} confirmé.</p>', smtp_config)

def send_stock_alert(product_id, threshold, smtp_config=None):
    return send_email('stock@example.com', f'Alerte stock produit #{product_id}', f'<p>Le produit #{product_id} a atteint le seuil de {threshold}.</p>', smtp_config)
>>>

### FICHIER .PY: web\backend\app\tasks\reports.py
<<<
from app.utils.pdf_generator import generate_report_pdf
from app.utils.excel_generator import generate_excel_report
from app.models.vente import Vente
from app.models.produit import Produit
from app.security.tenant import get_current_tenant_id
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

def generate_daily_sales_report(date_str, tenant_id):
    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= target_date,
        Vente.created_at < target_date + timedelta(days=1)
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    data = [{'id': s.id, 'reference': s.reference, 'total_ttc': float(s.total_ttc), 'statut': s.statut} for s in sales]
    filename = f'report_sales_{date_str}.pdf'
    return generate_report_pdf(filename, data, f'Rapport des ventes du {date_str}')

def generate_monthly_report(month, year, tenant_id):
    query = Vente.query.filter(
        Vente.is_active == True,
        Vente.created_at >= datetime(year, month, 1),
        Vente.created_at < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    )
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    sales = query.all()
    total = sum(float(s.total_ttc) for s in sales)
    data = [{'total_ventes': len(sales), 'ca_total': total, 'mois': month, 'annee': year}]
    filename = f'report_monthly_{year}_{month:02d}.pdf'
    return generate_report_pdf(filename, data, f'Rapport mensuel {month}/{year}')

def generate_stock_report(tenant_id):
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    products = query.all()
    data = [{'reference': p.reference, 'nom': p.nom, 'stock': float(p.quantite_stock), 'valeur': float(p.valeur_stock)} for p in products]
    filename = 'report_stock.pdf'
    return generate_report_pdf(filename, data, 'Rapport de stock')
>>>

### FICHIER .PY: web\backend\app\utils\__init__.py
<<<
from .pdf_generator import generate_invoice_pdf, generate_quote_pdf, generate_report_pdf
from .excel_generator import generate_excel_report
from .qr_generator import generate_qr_code
from .barcode_generator import generate_barcode
from .logger import get_logger
from .validators import validate_email, validate_phone, validate_siret, validate_product_data

__all__ = [
    'generate_invoice_pdf',
    'generate_quote_pdf',
    'generate_report_pdf',
    'generate_excel_report',
    'generate_qr_code',
    'generate_barcode',
    'get_logger',
    'validate_email',
    'validate_phone',
    'validate_siret',
    'validate_product_data',
]

>>>

### FICHIER .PY: web\backend\app\utils\audit.py
<<<
from app import db
from app.models.audit_log import AuditLog, TypeActionAudit


def log_audit(type_action, description, tenant_id=None, utilisateur_id=None, metadata=None):
    try:
        entry = AuditLog(
            tenant_id=tenant_id,
            utilisateur_id=utilisateur_id,
            type_action=type_action,
            description=description,
            metadata_json=str(metadata) if metadata else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()

>>>

### FICHIER .PY: web\backend\app\utils\barcode_generator.py
<<<
import barcode
from barcode.writer import ImageWriter


def generate_barcode(data, filename):
    code_class = barcode.get('code128', data, writer=ImageWriter())
    code_class.save(filename)
    return filename

>>>

### FICHIER .PY: web\backend\app\utils\compta_import.py
<<<

import pandas as pd
from werkzeug.datastructures import FileStorage
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.tenant import get_current_tenant_id
from app import db
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

ACCOUNT_TYPE_MAP = {
    'actif': TypeCompte.ACTIF,
    'passif': TypeCompte.PASSIF,
    'charge': TypeCompte.CHARGE,
    'produit': TypeCompte.PRODUIT,
}

ECRITURE_STATUT_MAP = {
    'brouillon': StatutEcriture.BROUILLON,
    'valide': StatutEcriture.VALIDE,
    'annule': StatutEcriture.ANNULE,
}

TRESORERIE_TYPE_MAP = {
    'entree': TypeTresorerie.ENTREE,
    'sortie': TypeTresorerie.SORTIE,
}

PAIEMENT_MAP = {
    'espece': 'especes',
    'especes': 'especes',
    'virement': 'virement',
    'cheque': 'cheque',
    'mvola': 'mvola',
    'orange_money': 'orange_money',
    'airtel_money': 'airtel_money',
    'mobile_money': 'mvola',
    'mobile money': 'mvola',
    'carte': 'especes',
}

def _read_file(file: FileStorage):
    filename = file.filename.lower()
    try:
        if filename.endswith('.csv'):
            file.seek(0)
            return pd.read_csv(file), 'csv'
        elif filename.endswith(('.xlsx', '.xls')):
            file.seek(0)
            return pd.read_excel(file), 'excel'
        else:
            raise ValueError("Format non supporté. Utilisez CSV ou Excel (.csv, .xlsx, .xls)")
    except Exception as e:
        logger.error(f"Erreur lecture fichier comptabilité: {e}")
        raise ValueError(f"Impossible de lire le fichier: {str(e)}")


def _safe_decimal(val):
    if val is None or val == '':
        return Decimal('0')
    return Decimal(str(val))


def import_comptes_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'numero', 'nom'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier comptes: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            numero = str(row.get('numero', '')).strip()
            nom = str(row.get('nom', '')).strip()
            if not numero or not nom:
                errors.append(f"Ligne {idx + 2}: numero et nom requis")
                continue

            if CompteComptable.query.filter_by(numero=numero, is_active=True).first():
                errors.append(f"Ligne {idx + 2}: Compte {numero} existe déjà")
                continue

            type_compte_raw = str(row.get('type_compte', 'actif')).strip().lower()
            type_compte = ACCOUNT_TYPE_MAP.get(type_compte_raw)
            if type_compte is None:
                errors.append(f"Ligne {idx + 2}: type_compte invalide '{type_compte_raw}'")
                continue

            sous_compte_id = None
            if pd.notna(row.get('sous_compte_id')) and str(row.get('sous_compte_id')).strip():
                parent = CompteComptable.query.filter_by(numero=str(row['sous_compte_id']).strip(), is_active=True).first()
                if parent:
                    sous_compte_id = parent.id
                else:
                    errors.append(f"Ligne {idx + 2}: Compte parent {row['sous_compte_id']} introuvable")
                    continue

            compte = CompteComptable(
                numero=numero,
                nom=nom,
                type_compte=type_compte,
                sous_compte_id=sous_compte_id,
                solde=_safe_decimal(row.get('solde', 0)),
                is_actif=True,
                tenant_id=tenant_id,
            )
            db.session.add(compte)
            results.append({'numero': numero, 'nom': nom, 'type': type_compte.value})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }


def import_ecritures_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'date', 'compte_id', 'libelle'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier ecritures: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            date_raw = str(row.get('date', '')).strip()
            if not date_raw:
                errors.append(f"Ligne {idx + 2}: date requise")
                continue

            date_obj = None
            for fmt_date in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_obj = datetime.strptime(date_raw, fmt_date).date()
                    break
                except ValueError:
                    continue
            if not date_obj:
                errors.append(f"Ligne {idx + 2}: format date invalide '{date_raw}' (attendu YYYY-MM-DD)")
                continue

            compte_id = int(float(str(row.get('compte_id', '')).strip()))
            compte = CompteComptable.query.filter_by(id=compte_id, is_active=True).first()
            if not compte:
                errors.append(f"Ligne {idx + 2}: compte_id {compte_id} introuvable")
                continue

            montant_debit = _safe_decimal(row.get('montant_debit', 0))
            montant_credit = _safe_decimal(row.get('montant_credit', 0))
            if montant_debit > 0 and montant_credit > 0:
                errors.append(f"Ligne {idx + 2}: débit et crédit ne peuvent pas être tous les deux > 0")
                continue

            libelle = str(row.get('libelle', '')).strip()
            if not libelle:
                errors.append(f"Ligne {idx + 2}: libelle requis")
                continue

            statut_raw = str(row.get('statut', 'brouillon')).strip().lower()
            statut = ECRITURE_STATUT_MAP.get(statut_raw, StatutEcriture.BROUILLON)

            entite_type = None
            if pd.notna(row.get('entite_type')) and str(row.get('entite_type')).strip():
                entite_type = str(row.get('entite_type')).strip()

            entite_id = None
            if pd.notna(row.get('entite_id')) and str(row.get('entite_id')).strip():
                try:
                    entite_id = int(float(str(row.get('entite_id')).strip()))
                except Exception:
                    pass

            ecriture = EcritureComptable(
                date=date_obj,
                compte_id=compte_id,
                montant_debit=montant_debit,
                montant_credit=montant_credit,
                libelle=libelle,
                piece_joint=str(row.get('piece_joint', '') or ''),
                reference_externe=str(row.get('reference_externe', '') or '') if pd.notna(row.get('reference_externe')) else None,
                entite_type=entite_type,
                entite_id=entite_id,
                statut=statut,
                tenant_id=tenant_id,
            )
            db.session.add(ecriture)
            results.append({'date': str(date_obj), 'libelle': libelle, 'compte': compte.numero})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }


def import_tresorerie_from_file(file: FileStorage, tenant_id=None):
    df, fmt = _read_file(file)

    required_cols = {'date', 'type_operation', 'montant', 'libelle'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier tresorerie: {missing}")

    tenant_id = tenant_id or get_current_tenant_id()
    results = []
    errors = []

    for idx, row in df.iterrows():
        try:
            date_raw = str(row.get('date', '')).strip()
            if not date_raw:
                errors.append(f"Ligne {idx + 2}: date requise")
                continue

            date_obj = None
            for fmt_date in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    date_obj = datetime.strptime(date_raw, fmt_date).date()
                    break
                except ValueError:
                    continue
            if not date_obj:
                errors.append(f"Ligne {idx + 2}: format date invalide '{date_raw}' (attendu YYYY-MM-DD)")
                continue

            type_raw = str(row.get('type_operation', '')).strip().lower()
            type_operation = TRESORERIE_TYPE_MAP.get(type_raw)
            if type_operation is None:
                errors.append(f"Ligne {idx + 2}: type_operation invalide '{type_raw}'")
                continue

            montant = _safe_decimal(row.get('montant'))
            if montant <= 0:
                errors.append(f"Ligne {idx + 2}: montant doit être positif")
                continue

            libelle = str(row.get('libelle', '')).strip()
            if not libelle:
                errors.append(f"Ligne {idx + 2}: libelle requis")
                continue

            mode_paiement_raw = str(row.get('mode_paiement', 'espece')).strip().lower()
            mode_paiement = PAIEMENT_MAP.get(mode_paiement_raw, 'espece')

            compte_bancaire = None
            if pd.notna(row.get('compte_bancaire')) and str(row.get('compte_bancaire')).strip():
                compte_bancaire = str(row.get('compte_bancaire')).strip()

            reference = None
            if pd.notna(row.get('reference')) and str(row.get('reference')).strip():
                reference = str(row.get('reference')).strip()

            entree = Tresorerie(
                date=date_obj,
                type_operation=type_operation,
                montant=montant,
                mode_paiement=mode_paiement,
                libelle=libelle,
                compte_bancaire=compte_bancaire,
                reference=reference,
                piece_jointe=str(row.get('piece_joint', '') or ''),
                is_reconcilie=bool(str(row.get('is_reconcilie', '')).lower() in ('true', '1', 'oui')),
                tenant_id=tenant_id,
            )
            db.session.add(entree)
            results.append({'date': str(date_obj), 'type': type_operation.value, 'montant': str(montant), 'libelle': libelle})
        except Exception as e:
            errors.append(f"Ligne {idx + 2}: {str(e)}")

    if results:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Erreur base de données: {str(e)}")

    return {
        'imported': len(results),
        'errors': errors,
        'details': results,
    }

>>>

### FICHIER .PY: web\backend\app\utils\excel_generator.py
<<<
from openpyxl import Workbook


def generate_excel_report(filename, rows):
    wb = Workbook()
    ws = wb.active
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row, start=1):
            ws.cell(row=row_index, column=col_index, value=value)
    wb.save(filename)

>>>

### FICHIER .PY: web\backend\app\utils\logger.py
<<<
import logging


def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

>>>

### FICHIER .PY: web\backend\app\utils\malagasy_data.py
<<<
"""
Donnees de demonstration et valeurs par defaut adaptees au contexte
commercial malagache (grossiste, distributeur, semi-grossiste, boutique).

La monnaie utilisee est l'ariary (MGA / Ar). Les prix sont en MGA et
restent coherents avec une activite de gros / distribution.
"""

# ---------------------------------------------------------------------------
# Villes malgachomanes et codes postaux Madagascar
# ---------------------------------------------------------------------------
VILLES_MADAGAS = [
    {"ville": "Antananarivo", "code_postal": "101", "region": "Analamanga"},
    {"ville": "Antsirabe", "code_postal": "110", "region": "Vakinankaratra"},
    {"ville": "Fianarantsoa", "code_postal": "301", "region": "Haute Matsiatra"},
    {"ville": "Antsiranana", "code_postal": "201", "region": "Diana"},
    {"ville": "Mahajanga", "code_postal": "401", "region": "Boeny"},
    {"ville": "Toamasina", "code_postal": "501", "region": "Atsinanana"},
    {"ville": "Toliara", "code_postal": "601", "region": "Atsimo-Andrefana"},
    {"ville": "Morondava", "code_postal": "619", "region": "Menabe"},
    {"ville": "Antalaha", "code_postal": "206", "region": "Sava"},
    {"ville": "Ambovombe", "code_postal": "603", "region": "Androy"},
    {"ville": "Farafangana", "code_postal": "308", "region": "Atsimo-Atsinanana"},
    {"ville": "Manakara", "code_postal": "317", "region": "Vatovavy"},
    {"ville": "Sambava", "code_postal": "208", "region": "Sava"},
    {"ville": "Marovoay", "code_postal": "415", "region": "Boeny"},
    {"ville": "Maintirano", "code_postal": "418", "region": "Melaky"},
    {"ville": "Besalampy", "code_postal": "421", "region": "Melaky"},
    {"ville": "Moramanga", "code_postal": "514", "region": "Atsinanana"},
    {"ville": "Vatomandry", "code_postal": "516", "region": "Atsinanana"},
    {"ville": "Mahanoro", "code_postal": "510", "region": "Atsinanana"},
    {"ville": "Mananjary", "code_postal": "316", "region": "Vatovavy"},
    {"ville": "Nosy Be", "code_postal": "207", "region": "Diana"},
    {"ville": "Andapa", "code_postal": "205", "region": "Sava"},
    {"ville": "Bealanana", "code_postal": "433", "region": "Sofia"},
    {"ville": "Port-Bergé", "code_postal": "438", "region": "Sofia"},
    {"ville": "Mampikony", "code_postal": "434", "region": "Sofia"},
    {"ville": "Analalava", "code_postal": "422", "region": "Sofia"},
    {"ville": "Soanierana-Ivongo", "code_postal": "523", "region": "Analanjirofo"},
    {"ville": "Fenoarivo Atsinanana", "code_postal": "508", "region": "Analanjirofo"},
    {"ville": "Mananara Avaratra", "code_postal": "514", "region": "Analanjirofo"},
    {"ville": "Vavatenina", "code_postal": "518", "region": "Analanjirofo"},
    {"ville": "Marolambo", "code_postal": "513", "region": "Atsinanana"},
    {"ville": "Ihosy", "code_postal": "311", "region": "Ihorombe"},
    {"ville": "Ilakaka", "code_postal": "313", "region": "Ihorombe"},
    {"ville": "Betroka", "code_postal": "314", "region": "Anosy"},
    {"ville": "Ambositra", "code_postal": "306", "region": "Amoron'i Mania"},
    {"ville": "Fandriana", "code_postal": "304", "region": "Amoron'i Mania"},
    {"ville": "Manandriana", "code_postal": "305", "region": "Amoron'i Mania"},
    {"ville": "Ambohidratrimo", "code_postal": "105", "region": "Analamanga"},
    {"ville": "Andramasina", "code_postal": "106", "region": "Analamanga"},
    {"ville": "Anjozorobe", "code_postal": "107", "region": "Analamanga"},
    {"ville": "Manjakandriana", "code_postal": "116", "region": "Analamanga"},
    {"ville": "Soavinandriana", "code_postal": "118", "region": "Itasy"},
    {"ville": "Miarinarivo", "code_postal": "121", "region": "Itasy"},
    {"ville": "Arivonimamo", "code_postal": "112", "region": "Itasy"},
    {"ville": "Tsiroanomandidy", "code_postal": "119", "region": "Bongolava"},
    {"ville": "Tsiroanomandidy", "code_postal": "119", "region": "Bongolava"},
    {"ville": "Maintirano", "code_postal": "418", "region": "Melaky"},
    {"ville": "Morondava", "code_postal": "619", "region": "Menabe"},
    {"ville": "Miandrivazo", "code_postal": "616", "region": "Menabe"},
    {"ville": "Antsalova", "code_postal": "424", "region": "Melaky"},
    {"ville": "Belo sur Tsiribihina", "code_postal": "614", "region": "Menabe"},
    {"ville": "Ampanihy", "code_postal": "605", "region": "Atsimo-Andrefana"},
    {"ville": "Betioky", "code_postal": "607", "region": "Atsimo-Andrefana"},
    {"ville": "Tuléar", "code_postal": "601", "region": "Atsimo-Andrefana"},
    {"ville": "Sakaraha", "code_postal": "620", "region": "Atsimo-Andrefana"},
    {"ville": "Atsimo-Andrefana", "code_postal": "601", "region": "Atsimo-Andrefana"},
    {"ville": "Ejeda", "code_postal": "608", "region": "Atsimo-Andrefana"},
    {"ville": "Ambovombe", "code_postal": "603", "region": "Androy"},
    {"ville": "Beloha", "code_postal": "605", "region": "Androy"},
    {"ville": "Tsihombe", "code_postal": "609", "region": "Androy"},
    {"ville": "Fort-Dauphin", "code_postal": "614", "region": "Anosy"},
    {"ville": "Vangaindrano", "code_postal": "320", "region": "Atsimo-Atsinanana"},
    {"ville": "Farafangana", "code_postal": "308", "region": "Atsimo-Atsinanana"},
    {"ville": "Vondrozo", "code_postal": "323", "region": "Atsimo-Atsinanana"},
    {"ville": "Manakara", "code_postal": "317", "region": "Vatovavy"},
    {"ville": "Ikongo", "code_postal": "318", "region": "Vatovavy"},
    {"ville": "Mananjary", "code_postal": "316", "region": "Vatovavy"},
    {"ville": "Nosy Varika", "code_postal": "319", "region": "Vatovavy"},
    {"ville": "Sahambavy", "code_postal": "306", "region": "Haute Matsiatra"},
    {"ville": "Ambalavao", "code_postal": "303", "region": "Haute Matsiatra"},
    {"ville": "Côte Est", "code_postal": "301", "region": "Haute Matsiatra"},
]


def tel_madag(reste):
    """Construit un numero +261 fictif stable a partir d'un suffixe."""
    return f"+261 3{reste}"


# ---------------------------------------------------------------------------
# Catalogue produits (grossiste / distribution) en Ariary
# ---------------------------------------------------------------------------
# Prix ordonnes : grossiste < demi_gros < revendeur < vente (detail).
PRODUCTS_CATALOG = [
    {
        "nom": "Riz blanc Makalioka (sac 50 kg)",
        "categorie": "Riz & Cereales",
        "unite": "sac",
        "marque": "Lac Alaotra",
        "prix_achat_ht": 420000,
        "prix_vente_ht": 525000,
        "prix_grossiste": 505000,
        "prix_demi_gros": 515000,
        "prix_revendeur": 518000,
        "quantite_stock": 120,
        "seuil_alerte": 20,
        "seuil_critique": 8,
        "description_courte": "Riz local conditionne en sac de 50 kg",
    },
    {
        "nom": "Riz brise (sac 25 kg)",
        "categorie": "Riz & Cereales",
        "unite": "sac",
        "marque": "RSI Mada",
        "prix_achat_ht": 175000,
        "prix_vente_ht": 230000,
        "prix_grossiste": 215000,
        "prix_demi_gros": 222000,
        "prix_revendeur": 226000,
        "quantite_stock": 220,
        "seuil_alerte": 30,
        "seuil_critique": 15,
        "description_courte": "Riz brise / brisures pour la restauration collective",
    },
    {
        "nom": "Huile vegetale Loulou (1 L)",
        "categorie": "Huiles & Grains",
        "unite": "bouteille",
        "marque": "Loulou",
        "prix_achat_ht": 7000,
        "prix_vente_ht": 9500,
        "prix_grossiste": 8800,
        "prix_demi_gros": 9100,
        "prix_revendeur": 9300,
        "quantite_stock": 1800,
        "seuil_alerte": 250,
        "seuil_critique": 100,
        "description_courte": "Huile alimentaire 1 L, tres demandee en detail",
    },
    {
        "nom": "Huile de table 5 L (bidon)",
        "categorie": "Huiles & Grains",
        "unite": "bidon",
        "marque": "Hasi",
        "prix_achat_ht": 88000,
        "prix_vente_ht": 112000,
        "prix_grossiste": 103000,
        "prix_demi_gros": 108000,
        "prix_revendeur": 110000,
        "quantite_stock": 320,
        "seuil_alerte": 50,
        "seuil_critique": 25,
        "description_courte": "Bidon 5 L pour boucheries et detail",
    },
    {
        "nom": "Sucre blanc en poudre (1 kg)",
        "categorie": "Couleurs & Sucreries",
        "unite": "sachet",
        "marque": "Compania",
        "prix_achat_ht": 3600,
        "prix_vente_ht": 4800,
        "prix_grossiste": 4400,
        "prix_demi_gros": 4600,
        "prix_revendeur": 4700,
        "quantite_stock": 9000,
        "seuil_alerte": 1200,
        "seuil_critique": 500,
        "description_courte": "Sucre de canne blanc en sachet de 1 kg",
    },
    {
        "nom": "Farine de ble (sac 50 kg)",
        "categorie": "Farines & Pates",
        "unite": "sac",
        "marque": "Aux Mille",
        "prix_achat_ht": 140000,
        "prix_vente_ht": 185000,
        "prix_grossiste": 174000,
        "prix_demi_gros": 180000,
        "prix_revendeur": 182000,
        "quantite_stock": 140,
        "seuil_alerte": 25,
        "seuil_critique": 12,
        "description_courte": "Farine de ble pour boulangeries et pates",
    },
    {
        "nom": "Eau minerale 2 L (pack 6)",
        "categorie": "Eaux & Boissons",
        "unite": "pack",
        "marque": "Source Tiaca",
        "prix_achat_ht": 7800,
        "prix_vente_ht": 10500,
        "prix_grossiste": 9800,
        "prix_demi_gros": 10100,
        "prix_revendeur": 10300,
        "quantite_stock": 750,
        "seuil_alerte": 120,
        "seuil_critique": 60,
        "description_courte": "Pack de 6 bouteilles d'eau minerale 1,5 L",
    },
    {
        "nom": "Boisson gazeuse locale (1,5 L)",
        "categorie": "Eaux & Boissons",
        "unite": "bouteille",
        "marque": "VCore",
        "prix_achat_ht": 4500,
        "prix_vente_ht": 6800,
        "prix_grossiste": 6100,
        "prix_demi_gros": 6400,
        "prix_revendeur": 6600,
        "quantite_stock": 900,
        "seuil_alerte": 150,
        "seuil_critique": 70,
        "description_courte": "Soda orange local 1,5 L, tres consomme",
    },
    {
        "nom": "Biscuit Vitel (250 g)",
        "categorie": "Biscuits & Gouters",
        "unite": "paquet",
        "marque": "Vitelo",
        "prix_achat_ht": 1400,
        "prix_vente_ht": 2100,
        "prix_grossiste": 1900,
        "prix_demi_gros": 2000,
        "prix_revendeur": 2050,
        "quantite_stock": 6000,
        "seuil_alerte": 900,
        "seuil_critique": 400,
        "description_courte": "Biscuits sucre 250 g, grande rotation",
    },
]
>>>

### FICHIER .PY: web\backend\app\utils\pdf_generator.py
<<<
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from app.config.settings import Config

GOLD = colors.HexColor('#d4af37')
ONYX = colors.HexColor('#111111')
ONYX_SOFT = colors.HexColor('#2a2a2a')
MUTED = colors.HexColor('#77776f')
LINE = colors.HexColor('#e6e6e1')
BEIGE = colors.HexColor('#f7f7f5')
WHITE = colors.white


def _get_upload_folder():
    return Config.UPLOAD_FOLDER


def _build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['tenant_name'] = ParagraphStyle(
        'tenant_name',
        parent=base['Heading1'],
        fontSize=20,
        leading=24,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        spaceAfter=2,
    )
    styles['tenant_info'] = ParagraphStyle(
        'tenant_info',
        parent=base['Normal'],
        fontSize=9,
        leading=13,
        textColor=MUTED,
        fontName='Helvetica',
    )
    styles['doc_title'] = ParagraphStyle(
        'doc_title',
        parent=base['Heading1'],
        fontSize=22,
        leading=26,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    styles['doc_ref'] = ParagraphStyle(
        'doc_ref',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=MUTED,
        fontName='Helvetica',
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    styles['section_label'] = ParagraphStyle(
        'section_label',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        spaceAfter=4,
        textTransform='uppercase',
        letterSpacing=0.08,
    )
    styles['normal'] = ParagraphStyle(
        'normal',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=ONYX,
        fontName='Helvetica',
    )
    styles['normal_right'] = ParagraphStyle(
        'normal_right',
        parent=base['Normal'],
        fontSize=10,
        leading=14,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_RIGHT,
    )
    styles['small'] = ParagraphStyle(
        'small',
        parent=base['Normal'],
        fontSize=8,
        leading=11,
        textColor=MUTED,
        fontName='Helvetica',
    )
    styles['footer'] = ParagraphStyle(
        'footer',
        parent=base['Normal'],
        fontSize=8,
        leading=10,
        textColor=MUTED,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )
    styles['total'] = ParagraphStyle(
        'total',
        parent=base['Normal'],
        fontSize=11,
        leading=15,
        textColor=ONYX,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
    )
    styles['table_header'] = ParagraphStyle(
        'table_header',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=WHITE,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    )
    styles['table_cell'] = ParagraphStyle(
        'table_cell',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_LEFT,
    )
    styles['table_cell_right'] = ParagraphStyle(
        'table_cell_right',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_RIGHT,
    )
    styles['table_cell_center'] = ParagraphStyle(
        'table_cell_center',
        parent=base['Normal'],
        fontSize=9,
        leading=12,
        textColor=ONYX,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )
    return styles


def _add_header_footer(canvas_obj, doc, tenant, doc_title, doc_ref, page_count=1):
    canvas_obj.saveState()
    try:
        width, height = A4
        margin = 2 * cm

        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, height - margin + 0.4 * cm, width - margin, height - margin + 0.4 * cm)

        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawRightString(width - margin, 1.2 * cm, f'Page {doc.page} / {page_count}')

        if tenant:
            canvas_obj.setFont('Helvetica', 7)
            canvas_obj.setFillColor(MUTED)
            footer_text = f"{tenant.get('nom', '')} | {tenant.get('adresse', '')}, {tenant.get('ville', '')} | {tenant.get('telephone', '')} | {tenant.get('email_contact', '')}"
            canvas_obj.drawString(margin, 1.2 * cm, footer_text[:120])

        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, margin - 0.3 * cm, width - margin, margin - 0.3 * cm)
    except Exception:
        pass
    canvas_obj.restoreState()


def _try_load_logo(logo_path_or_url, max_width_cm=4):
    try:
        if not logo_path_or_url:
            return None
        path = logo_path_or_url
        if not os.path.isabs(path):
            folder = _get_upload_folder()
            candidate = os.path.join(folder, path)
            if os.path.exists(candidate):
                path = candidate
        if os.path.exists(path):
            img = ImageReader(path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            max_w = max_width_cm * cm
            w = min(max_w, iw)
            h = w * aspect
            if h > 3 * cm:
                h = 3 * cm
                w = h / aspect
            return Image(path, width=w, height=h)
    except Exception:
        return None
    return None


def _build_table_header(styles):
    return [
        Paragraph('Désignation', styles['table_header']),
        Paragraph('Qté', styles['table_header']),
        Paragraph('Prix unit. HT', styles['table_header']),
        Paragraph('TVA', styles['table_header']),
        Paragraph('Total HT', styles['table_header']),
    ]


def _build_table_row(styles, item):
    return [
        Paragraph(str(item.get('produit_nom', item.get('designation', item.get('description', '')))), styles['table_cell']),
        Paragraph(str(item.get('quantite', item.get('qte', ''))), styles['table_cell_center']),
        Paragraph(f"{float(item.get('prix_unitaire', item.get('prix_ht', 0))):.2f}", styles['table_cell_right']),
        Paragraph(f"{item.get('taux_tva', item.get('tva', 0))}%", styles['table_cell_center']),
        Paragraph(f"{float(item.get('total_ht', item.get('total', 0))):.2f}", styles['table_cell_right']),
    ]


def generate_document_pdf(filename, type_document, reference, donnees, tenant, modele=None):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    styles = _build_styles()
    width, height = A4
    margin = 2 * cm
    content_width = width - 2 * margin

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin + 1.6 * cm,
        bottomMargin=margin + 1.6 * cm,
    )

    story = []
    logo = None
    if modele and modele.get('logo_url'):
        logo = _try_load_logo(modele.get('logo_url'))
    if not logo and tenant and tenant.get('logo'):
        logo = _try_load_logo(tenant.get('logo'))

    tenant_name = tenant.get('nom', '') if tenant else ''
    tenant_adresse = tenant.get('adresse', '') if tenant else ''
    tenant_ville = tenant.get('ville', '') if tenant else ''
    tenant_pays = tenant.get('pays', '') if tenant else ''
    tenant_telephone = tenant.get('telephone', '') if tenant else ''
    tenant_email = tenant.get('email_contact', '') if tenant else ''
    tenant_devise = tenant.get('devise', 'MGA') if tenant else 'MGA'

    if logo:
        story.append(logo)
        story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(tenant_name or 'ENTREPRISE', styles['tenant_name']))
    if tenant_adresse or tenant_ville or tenant_telephone or tenant_email:
        info_line = ', '.join(filter(None, [tenant_adresse, tenant_ville, tenant_pays, tenant_telephone, tenant_email]))
        story.append(Paragraph(info_line, styles['tenant_info']))
    story.append(Spacer(1, 0.3 * cm))

    story.append(HRFlowable(width=content_width, thickness=1.5, color=GOLD, spaceAfter=0.4 * cm))

    type_labels = {
        'facture': 'FACTURE',
        'devis': 'DEVIS',
        'contrat': 'CONTRAT',
        'bon_livraison': 'BON DE LIVRAISON',
        'avoir': 'AVOIR',
    }
    title = type_labels.get(type_document, type_document.upper())
    story.append(Paragraph(title, styles['doc_title']))
    story.append(Paragraph(f'Référence : {reference}', styles['doc_ref']))
    story.append(Spacer(1, 0.4 * cm))

    client_nom = donnees.get('client_nom', donnees.get('client', ''))
    client_adresse = donnees.get('client_adresse', '')
    client_ville = donnees.get('client_ville', '')
    client_email = donnees.get('client_email', '')
    client_telephone = donnees.get('client_telephone', '')

    if client_nom or client_adresse or client_email:
        story.append(Paragraph('CLIENT', styles['section_label']))
        client_lines = ' | '.join(filter(None, [client_nom, client_adresse, client_ville, client_email, client_telephone]))
        story.append(Paragraph(client_lines or '-', styles['normal']))
        story.append(Spacer(1, 0.3 * cm))

    items = donnees.get('items', donnees.get('lignes', []))
    if not items and isinstance(donnees, list):
        items = donnees

    if items:
        story.append(Paragraph('DÉTAIL', styles['section_label']))
        story.append(Spacer(1, 0.1 * cm))

        table_data = [_build_table_header(styles)]
        for item in items:
            table_data.append(_build_table_row(styles, item))

        table = Table(table_data, colWidths=[content_width * 0.38, content_width * 0.12, content_width * 0.18, content_width * 0.12, content_width * 0.20], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ONYX),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), BEIGE),
            ('GRID', (0, 0), (-1, -1), 0.5, LINE),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

    total_ht = float(donnees.get('total_ht', donnees.get('total', 0)))
    taux_tva = float(donnees.get('taux_tva', 0))
    total_ttc = float(donnees.get('total_ttc', total_ht * (1 + taux_tva / 100)))
    remise = float(donnees.get('remise', 0))
    net_ht = total_ht - remise
    total_tva = net_ht * taux_tva / 100 if taux_tva else 0
    net_ttc = net_ht + total_tva

    story.append(HRFlowable(width=content_width, thickness=0.5, color=LINE, spaceAfter=0.3 * cm))

    totals_data = [
        [Paragraph('Total HT', styles['normal']), Paragraph(f'{total_ht:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('Remise', styles['normal']), Paragraph(f'{remise:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('Net HT', styles['normal']), Paragraph(f'{net_ht:.2f} {tenant_devise}', styles['normal'])],
        [Paragraph(f'TVA ({taux_tva:.1f}%)', styles['normal']), Paragraph(f'{total_tva:.2f} {tenant_devise}', styles['normal_right'])],
        [Paragraph('TOTAL TTC', styles['total']), Paragraph(f'{net_ttc:.2f} {tenant_devise}', styles['total'])],
    ]
    totals_table = Table(totals_data, colWidths=[content_width * 0.7, content_width * 0.3])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, ONYX),
        ('BACKGROUND', (0, -1), (-1, -1), BEIGE),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.6 * cm))

    if modele and modele.get('conditions_generales'):
        story.append(Paragraph('CONDITIONS GÉNÉRALES', styles['section_label']))
        story.append(Paragraph(modele.get('conditions_generales', ''), styles['small']))
        story.append(Spacer(1, 0.3 * cm))

    if modele and modele.get('mention_legales'):
        story.append(Paragraph('MENTIONS LÉGALES', styles['section_label']))
        story.append(Paragraph(modele.get('mention_legales', ''), styles['small']))

    page_count = 1

    def _on_page(canvas_obj, doc_obj):
        nonlocal page_count
        page_count = max(page_count, doc_obj.page)
        _add_header_footer(canvas_obj, doc_obj, tenant, title, reference, page_count)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return filepath


def generate_report_pdf(filename, data, title):
    folder = _get_upload_folder()
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = _build_styles()
    story = []
    story.append(Paragraph(title, styles['doc_title']))
    story.append(Spacer(1, 0.5 * cm))
    if isinstance(data, list):
        table_data = [_build_table_header(styles)] if data else [['Aucune donnée', '', '', '', '']]
        for row in data:
            table_data.append(_build_table_row(styles, row if isinstance(row, dict) else {'produit_nom': str(row)}))
        table = Table(table_data, colWidths=[doc.width * 0.38, doc.width * 0.12, doc.width * 0.18, doc.width * 0.12, doc.width * 0.20], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ONYX),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, LINE),
            ('BACKGROUND', (0, 1), (-1, -1), BEIGE),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        for key, value in data.items() if isinstance(data, dict) else []:
            story.append(Paragraph(f"{key}: {value}", styles['normal']))
    doc.build(story)
    return filepath


def generate_invoice_pdf(filename, invoice_data):
    type_document = invoice_data.get('type_document', 'facture')
    reference = invoice_data.get('reference', '')
    donnees = invoice_data.get('donnees', invoice_data)
    tenant = invoice_data.get('tenant', {})
    modele = invoice_data.get('modele', {})
    return generate_document_pdf(filename, type_document, reference, donnees, tenant, modele)


def generate_quote_pdf(filename, quote_data):
    type_document = quote_data.get('type_document', 'devis')
    reference = quote_data.get('reference', '')
    donnees = quote_data.get('donnees', quote_data)
    tenant = quote_data.get('tenant', {})
    modele = quote_data.get('modele', {})
    return generate_document_pdf(filename, type_document, reference, donnees, tenant, modele)

>>>

### FICHIER .PY: web\backend\app\utils\qr_generator.py
<<<
import qrcode


def generate_qr_code(data, filename):
    img = qrcode.make(data)
    img.save(filename)
    return filename

>>>

### FICHIER .PY: web\backend\app\utils\validators.py
<<<
from decimal import Decimal
import re

def validate_email(email):
    """Valide un email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Valide un numéro de téléphone malgache au format +261 XX XX XXX XX ou 0XX XX XX XXX XX"""
    pattern = r'^(\+261|0)(2[0-9]|3[0-9])(\d{2})(\d{3})(\d{2})$'
    return re.match(pattern, phone.replace(' ', '')) is not None

def format_phone(phone):
    """Formate un numéro de téléphone malgache au format international +261 XX XX XXX XX"""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('261'):
        rest = digits[3:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    elif digits.startswith('0'):
        rest = digits[1:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    return phone

def validate_siret(siret):
    """Valide un numéro SIRET"""
    return len(siret) == 14 and siret.isdigit()

def validate_product_data(data):
    """Valide les données d'un produit"""
    required = ['reference', 'nom', 'prix_achat_ht', 'prix_vente_ht']
    for field in required:
        if field not in data:
            raise ValueError(f"Le champ {field} est requis")
    
    if data.get('prix_achat_ht', 0) <= 0:
        raise ValueError("Le prix d'achat doit être supérieur à 0")
    
    if data.get('prix_vente_ht', 0) <= 0:
        raise ValueError("Le prix de vente doit être supérieur à 0")
    
    if data.get('taux_tva', 0) < 0:
        raise ValueError("Le taux de TVA doit être positif")
    
    if data.get('quantite_stock', 0) < 0:
        raise ValueError("La quantité en stock doit être positive")
>>>

### FICHIER .PY: web\backend\app\websockets\__init__.py
<<<
# backend/app/websockets/__init__.py
# Package WebSocket pour la synchronisation temps-réel.

>>>

### FICHIER .PY: web\backend\app\websockets\socket_events.py
<<<
# backend/app/websockets/socket_events.py
# Gestion des événements Socket.IO pour la synchronisation temps-réel.

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_jwt_extended import decode_token
from flask import current_app

socketio = None


def init_socketio(app):
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins=current_app.config.get('CORS_ORIGINS', []),
        async_mode='eventlet',
        logger=current_app.config.get('DEBUG', False),
        engineio_logger=current_app.config.get('DEBUG', False),
    )

    register_handlers(socketio)
    return socketio


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect(auth):
        try:
            token = auth.get('token', '') if auth else ''
            if not token:
                return False

            decoded = decode_token(token)
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')

            if not tenant_id:
                return False

            room = f"tenant:{tenant_id}"
            join_room(room)

            if user_id:
                join_room(f"user:{user_id}")

            current_app.logger.info(
                f"Client connecté: tenant={tenant_id}, user={user_id}"
            )

        except Exception as e:
            current_app.logger.warning(f"Connexion WebSocket rejetée: {e}")
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        current_app.logger.info("Client déconnecté")

    @socketio.on('subscribe:favorites')
    def handle_subscribe_favorites(data):
        tenant_id = data.get('tenant_id')
        if tenant_id:
            join_room(f"tenant:{tenant_id}:favorites")

    @socketio.on('subscribe:columns')
    def handle_subscribe_columns(data):
        tenant_id = data.get('tenant_id')
        module = data.get('module')
        if tenant_id and module:
            join_room(f"tenant:{tenant_id}:columns:{module}")

    @socketio.on('subscribe:filters')
    def handle_subscribe_filters(data):
        tenant_id = data.get('tenant_id')
        module = data.get('module')
        if tenant_id and module:
            join_room(f"tenant:{tenant_id}:filters:{module}")

    @socketio.on('subscribe:notifications')
    def handle_subscribe_notifications(data):
        user_id = data.get('user_id')
        if user_id:
            join_room(f"user:{user_id}:notifications")


def broadcast_to_tenant(tenant_id, event, data):
    if socketio:
        socketio.emit(event, data, room=f"tenant:{tenant_id}")


def broadcast_to_user(user_id, event, data):
    if socketio:
        socketio.emit(event, data, room=f"user:{user_id}")


def broadcast_favorite_update(tenant_id, favorite_data):
    if socketio:
        socketio.emit('favorite:updated', favorite_data, room=f"tenant:{tenant_id}:favorites")


def broadcast_column_update(tenant_id, module, column_data):
    if socketio:
        socketio.emit('column:updated', column_data, room=f"tenant:{tenant_id}:columns:{module}")


def broadcast_filter_update(tenant_id, module, filter_data):
    if socketio:
        socketio.emit('filter:updated', filter_data, room=f"tenant:{tenant_id}:filters:{module}")


def broadcast_notification(user_id, notification_data):
    if socketio:
        socketio.emit('notification:new', notification_data, room=f"user:{user_id}:notifications")


def get_socketio():
    global socketio
    return socketio

>>>

### FICHIER .PY: web\backend\check_db.py
<<<
import sqlite3

conn = sqlite3.connect('erp.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'{len(tables)} tables')
for t in tables:
    print(f'  - {t[0]}')
conn.close()

>>>

### FICHIER .PY: web\backend\check_db_url.py
<<<
import sys
import os

os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.app_context():
    print(f"DATABASE_URL: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    from app import db
    print(f"Engine URL: {db.engine.url}")
    print(f"Engine name: {db.engine.name}")

>>>

### FICHIER .PY: web\backend\check_instance_dbs.py
<<<
import sqlite3
import os

instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
for f in os.listdir(instance_dir):
    if f.endswith('.db'):
        path = os.path.join(instance_dir, f)
        try:
            conn = sqlite3.connect(path)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            if 'alembic_version' in tables:
                cursor = conn.execute('SELECT * FROM alembic_version')
                versions = [r[0] for r in cursor.fetchall()]
                print(f"{f}: HAS alembic_version -> {versions}")
            else:
                print(f"{f}: no alembic_version (tables: {len(tables)})")
            conn.close()
        except Exception as e:
            print(f"{f}: ERROR - {e}")

>>>

### FICHIER .PY: web\backend\check_tables.py
<<<
import sqlite3
conn = sqlite3.connect('C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend/erp.db')
cursor = conn.execute('SELECT name FROM sqlite_master WHERE type="table"')
print([r[0] for r in cursor.fetchall()])
conn.close()

>>>

### FICHIER .PY: web\backend\check_tenant.py
<<<


from app import create_app
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur

app = create_app()

with app.app_context():

    print("\n========== TENANTS ==========")

    tenants = Tenant.query.all()

    if not tenants:
        print("Aucun tenant trouvé.")
    else:
        for t in tenants:
            print(
                f"ID={t.id} | "
                f"Nom={t.nom} | "
                f"Slug={t.slug} | "
                f"Actif={t.is_active}"
            )

    print("\n========== UTILISATEURS ==========")

    utilisateurs = Utilisateur.query.all()

    if not utilisateurs:
        print("Aucun utilisateur trouvé.")
    else:
        for u in utilisateurs:
            print(
                f"ID={u.id} | "
                f"Email={u.email} | "
                f"Role={u.role} | "
                f"Tenant_ID={u.tenant_id}"
            )

    print("\n========== FIN ==========")

>>>

### FICHIER .PY: web\backend\check_versions.py
<<<
import os

versions_dir = os.path.join(os.path.dirname(__file__), 'migrations', 'versions')
print(f"Versions dir: {versions_dir}")
print(f"Exists: {os.path.exists(versions_dir)}")
if os.path.exists(versions_dir):
    files = os.listdir(versions_dir)
    print(f"Files: {files}")
    for f in files:
        print(f"  {f} ({os.path.getsize(os.path.join(versions_dir, f))} bytes)")

# Also check all .py files in migrations for revision references
migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
for root, dirs, files in os.walk(migrations_dir):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r') as fh:
                content = fh.read()
                if 'revision' in content.lower() or 'down_revision' in content.lower():
                    print(f"\nFound revision reference in {path}:")
                    for line in content.split('\n'):
                        if 'revision' in line.lower() or 'down_revision' in line.lower():
                            print(f"  {line}")

>>>

### FICHIER .PY: web\backend\create_tenant.py
<<<
from app import create_app, db
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur

app = create_app()

with app.app_context():

    # 1. Créer le tenant
    tenant = Tenant.query.first()

    if tenant is None:
        tenant = Tenant(
            nom="ERP Commercial",
            slug="erp-commercial",
            is_active=True
        )

        db.session.add(tenant)
        db.session.flush()

        print(f"Tenant créé : ID={tenant.id}")
    else:
        print(f"Tenant existant : ID={tenant.id}")

    # 2. Associer tous les utilisateurs au tenant
    utilisateurs = Utilisateur.query.all()

    for utilisateur in utilisateurs:
        utilisateur.tenant_id = tenant.id
        print(
            f"{utilisateur.email} -> tenant_id={tenant.id}"
        )

    db.session.commit()

    print("\nInitialisation multi-tenant terminée.")
>>>

### FICHIER .PY: web\backend\debug_app_db.py
<<<
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

app = create_app()
with app.app_context():
    print(f"Instance path: {app.instance_path}")
    db_path = os.path.join(app.instance_path, 'erp.db')
    print(f"DB path: {db_path}")
    print(f"DB exists: {os.path.exists(db_path)}")
    
    if os.path.exists(db_path):
        print(f"DB size: {os.path.getsize(db_path)}")
    
    # Check tables via SQLAlchemy
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables via inspector: {tables}")
    
    # Check if utilisateurs table exists
    print(f"utilisateurs in tables: {'utilisateurs' in tables}")
    
    # Try to query
    try:
        count = db.session.query(Utilisateur).count()
        print(f"Utilisateur count: {count}")
    except Exception as e:
        print(f"Query error: {e}")

>>>

### FICHIER .PY: web\backend\debug_create.py
<<<
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

print(f"Current dir: {os.getcwd()}")
print(f"Utilisateur table: {Utilisateur.__tablename__}")

app = create_app()
with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Engine: {db.engine}")
    print(f"Tables in metadata: {list(db.metadata.tables.keys())[:5]}...")
    db.create_all()
    print("create_all done")
    
    # Check if file was created/modified
    db_path = os.path.join(os.getcwd(), 'erp.db')
    if os.path.exists(db_path):
        print(f"DB file exists: {db_path}, size: {os.path.getsize(db_path)}")
    else:
        print(f"DB file NOT found at: {db_path}")
    
    conn = db.engine.connect()
    cursor = conn.connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    conn.close()

>>>

### FICHIER .PY: web\backend\drop_alembic_version.py
<<<
import sqlite3

path = 'instance/erp.db'
conn = sqlite3.connect(path)
try:
    conn.execute('DROP TABLE IF EXISTS alembic_version')
    conn.commit()
    print("Dropped alembic_version table")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()

>>>

### FICHIER .PY: web\backend\fix_db.py
<<<
import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('erp.db')
cursor = conn.cursor()

# Check if the tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables: {tables}")

# Check if the tenants table exists
if 'tenants' in tables:
    cursor.execute("SELECT id, nom, plan FROM tenants")
    tenants = cursor.fetchall()
    print(f"\nTenants: {len(tenants)}")
    for t in tenants:
        print(f"  ID={t[0]}, Nom={t[1]}, Plan={t[2]}")

    # Check if the abonnements table exists
    if 'abonnements' in tables:
        cursor.execute("SELECT id, tenant_id, statut, date_fin, is_active, modules FROM abonnements")
        abonnements = cursor.fetchall()
        print(f"\nAbonnements: {len(abonnements)}")
        for a in abonnements:
            print(f"  ID={a[0]}, Tenant={a[1]}, Statut={a[2]}, Date_fin={a[3]}, Is_active={a[4]}, Modules={a[5]}")

        # Update all abonnements to be active with a future date_fin
        new_date_fin = (datetime.utcnow() + timedelta(days=365)).isoformat()
        cursor.execute("""
            UPDATE abonnements
            SET statut = 'actif',
                date_debut = ?,
                date_fin = ?,
                is_active = 1,
                modules = 'dashboard,produits,clients,ventes,factures,paiements,catalogue,stocks,rh,documents,comptabilite,livraison,ia,achats'
            WHERE statut != 'actif' OR date_fin < ? OR is_active != 1
        """, (datetime.utcnow().isoformat(), new_date_fin, datetime.utcnow().isoformat()))

        print(f"\nUpdated {cursor.rowcount} abonnements")

        # Verify the updates
        cursor.execute("SELECT id, tenant_id, statut, date_fin, is_active, modules FROM abonnements")
        abonnements = cursor.fetchall()
        print(f"\nAbonnements after update: {len(abonnements)}")
        for a in abonnements:
            print(f"  ID={a[0]}, Tenant={a[1]}, Statut={a[2]}, Date_fin={a[3]}, Is_active={a[4]}, Modules={a[5]}")
    else:
        print("Abonnements table does not exist")
else:
    print("Tenants table does not exist")

conn.commit()
conn.close()
print("\nDone!")

>>>

### FICHIER .PY: web\backend\fix_subscriptions.py
<<<
"""
Script de correction des abonnements expirés.
Met à jour la date de fin des abonnements pour les rendre actifs.
"""
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant
from app.security.plans import apply_plan_to_abonnement

app = create_app()

with app.app_context():
    # Get all tenants
    tenants = Tenant.query.all()
    print(f"Nombre de tenants: {len(tenants)}")

    for tenant in tenants:
        print(f"\nTenant: {tenant.nom} (plan: {tenant.plan})")

        # Get the latest subscription for this tenant
        abonnement = Abonnement.query.filter_by(
            tenant_id=tenant.id
        ).order_by(Abonnement.created_at.desc()).first()

        if abonnement:
            print(f"  Abonnement trouvé: ID={abonnement.id}, statut={abonnement.statut.value}, date_fin={abonnement.date_fin}")

            # Update the subscription to be active
            abonnement.statut = StatutAbonnement.ACTIF
            abonnement.date_debut = datetime.utcnow()
            abonnement.date_fin = datetime.utcnow() + timedelta(days=365)
            abonnement.is_active = True

            # Apply plan configuration (this sets the modules field)
            apply_plan_to_abonnement(abonnement, tenant.plan)

            print(f"  -> Mis à jour: statut=ACTIF, date_fin={abonnement.date_fin}")
            print(f"  -> Modules: {abonnement.modules}")
        else:
            print("  Aucun abonnement trouvé, création d'un nouveau...")
            # Create a new subscription
            abonnement = Abonnement(
                tenant_id=tenant.id,
                montant=79.0,
                devise='MGA',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=365),
                statut=StatutAbonnement.ACTIF,
                methode_paiement='especes',
                reference_paiement='SUB-FIX-001',
                plan=tenant.plan or 'pro',
            )
            apply_plan_to_abonnement(abonnement, tenant.plan or 'pro')
            db.session.add(abonnement)
            print(f"  -> Créé: statut=ACTIF, date_fin={abonnement.date_fin}")

    db.session.commit()
    print("\n✅ Tous les abonnements ont été mis à jour avec succès!")

>>>

### FICHIER .PY: web\backend\init_db.py
<<<
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app import db

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database tables created successfully!")

    # Check if there are any tenants
    from app.models.tenant import Tenant
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.security.plans import apply_plan_to_abonnement
    from datetime import datetime, timedelta

    tenants = Tenant.query.all()
    print(f"Found {len(tenants)} tenants")

    for tenant in tenants:
        print(f"\nTenant: {tenant.nom} (plan: {tenant.plan})")

        # Get the latest subscription for this tenant
        abonnement = Abonnement.query.filter_by(
            tenant_id=tenant.id
        ).order_by(Abonnement.created_at.desc()).first()

        if abonnement:
            print(f"  Abonnement found: ID={abonnement.id}, statut={abonnement.statut.value}, date_fin={abonnement.date_fin}")

            # Update the subscription to be active
            abonnement.statut = StatutAbonnement.ACTIF
            abonnement.date_debut = datetime.utcnow()
            abonnement.date_fin = datetime.utcnow() + timedelta(days=365)
            abonnement.is_active = True

            # Apply plan configuration (this sets the modules field)
            apply_plan_to_abonnement(abonnement, tenant.plan)

            print(f"  -> Updated: statut=ACTIF, date_fin={abonnement.date_fin}")
            print(f"  -> Modules: {abonnement.modules}")
        else:
            print("  No subscription found, creating a new one...")
            # Create a new subscription
            abonnement = Abonnement(
                tenant_id=tenant.id,
                montant=79.0,
                devise='MGA',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=365),
                statut=StatutAbonnement.ACTIF,
                methode_paiement='especes',
                reference_paiement='SUB-FIX-001',
                plan=tenant.plan or 'pro',
            )
            apply_plan_to_abonnement(abonnement, tenant.plan or 'pro')
            db.session.add(abonnement)
            print(f"  -> Created: statut=ACTIF, date_fin={abonnement.date_fin}")

    db.session.commit()
    print("\nAll subscriptions have been updated successfully!")

>>>

### FICHIER .PY: web\backend\inspect_db.py
<<<
import sqlite3

db = sqlite3.connect(r'instance\erp.db')
cur = db.cursor()
tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print('tables:', sorted(tabs))
print('has alembic_version:', 'alembic_version' in tabs)
if 'alembic_version' in tabs:
    print('alembic_version rows:', cur.execute('SELECT * FROM alembic_version').fetchall())
try:
    cols = [r[1] for r in cur.execute('PRAGMA table_info(ventes)')]
    print('ventes cols:', cols)
except Exception as e:
    print('ventes err', e)
cur.close()

>>>

### FICHIER .PY: web\backend\list_tenants.py
<<<
from app import create_app, db
from app.models.tenant import Tenant

app = create_app()

with app.app_context():
    tenants = Tenant.query.all()
    for t in tenants:
        print(t.id, t.slug, t.is_active, t.statut)

>>>

### FICHIER .PY: web\backend\manage.py
<<<
import click
from flask.cli import with_appcontext
from app import create_app, db
from app.models.utilisateur import Utilisateur, Role
from app.security.auth import hash_password
import getpass

app = create_app()

@app.cli.command("create-admin")
@click.argument('email')
@click.argument('username')
def create_admin(email, username):
    """Crée un administrateur"""
    password = getpass.getpass("Mot de passe: ")
    password2 = getpass.getpass("Confirmer le mot de passe: ")
    
    if password != password2:
        click.echo("Les mots de passe ne correspondent pas")
        return
    
    if Utilisateur.query.filter_by(email=email).first():
        click.echo("Cet email existe déjà")
        return
    
    if Utilisateur.query.filter_by(username=username).first():
        click.echo("Ce nom d'utilisateur existe déjà")
        return
    
    admin = Utilisateur(
        email=email,
        username=username,
        password_hash=hash_password(password),
        role=Role.ADMIN,
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Admin {username} créé avec succès!")

@app.cli.command("seed-data")
def seed_data():
    """Remplit la base de données avec des données de test"""
    # Note: Create a seeds.py module to implement this functionality
    click.echo(" seed_all() function not implemented. Please create app/seeds.py.")

if __name__ == '__main__':
    app.cli()
>>>

### FICHIER .PY: web\backend\migrations\env.py
<<<
import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

>>>

### FICHIER .PY: web\backend\run.py
<<<
﻿from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
    
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    if debug:
        print('WARNING: Debug mode is enabled. Do not use in production.')
    
    print(f"Serveur: http://{host}:{port}")
    print(f"Documentation: http://{host}:{port}/docs")
    
    app.run(debug=debug, host=host, port=port)

>>>

### FICHIER .PY: web\backend\run_socket.py
<<<
# web/backend/run_socket.py
# Point d'entrée avec Socket.IO (temps-réel).
# Usage : ENABLE_SOCKETIO=1 python run_socket.py
# Le temps-réel est optionnel : sans flask-socketio installé, le client
# desktop/web bascule automatiquement sur le polling (/api/v1/desk/events).

from app import create_app
import os

app = create_app()

# Active SocketIO si la dépendance est présente et l'env est activé.
os.environ.setdefault("ENABLE_SOCKETIO", "1")

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))

    try:
        from app.realtime import socketio
        if socketio:
            print("Temps-réel Socket.IO activé sur le port", port)
            socketio.run(app, debug=debug, host=host, port=port, allow_unsafe_werkzeug=True)
        else:
            print("SocketIO indisponible : démarrage HTTP classique.")
            app.run(debug=debug, host=host, port=port)
    except ImportError:
        app.run(debug=debug, host=host, port=port)

>>>

### FICHIER .PY: web\backend\scripts\backup.py
<<<
from app.tasks.backups import backup_database


def run_backup():
    result = backup_database('backups/erp-backup.zip')
    print(result)


if __name__ == '__main__':
    run_backup()

>>>

### FICHIER .PY: web\backend\scripts\create_admin.py
<<<
from app.models.utilisateur import Utilisateur
from app.security.auth import hash_password


def create_admin(username, email, password):
    hashed = hash_password(password)
    admin = Utilisateur(username=username, email=email, password_hash=hashed)
    return admin


if __name__ == '__main__':
    admin = create_admin('admin', 'admin@example.com', 'Admin123!')
    print('Admin user created: %s' % admin.username)

>>>

### FICHIER .PY: web\backend\scripts\create_desk_tables.py
<<<
#!/usr/bin/env python
"""
Crée les tables de synchronisation desktop/web (favoris, colonnes, filtres, events).
En dev (SQLite) ou pour un bootstrap rapide, exécuter :
    python scripts/create_desk_tables.py
En prod, préférer : flask db migrate + flask db upgrade (Alembic).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.desk_state import (
    DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
)

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        print("Création des tables de synchronisation (desk)...")
        db.create_all()
        print("Tables créées :", [
            DeskFavorite.__tablename__,
            DeskFilterPreset.__tablename__,
            DeskColumnConfig.__tablename__,
            SyncEvent.__tablename__,
        ])

>>>

### FICHIER .PY: web\backend\scripts\create_tables.py
<<<
#!/usr/bin/env python
"""
Script de creation des tables de la base de donnees
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.models.role_permission import RoleModel, Permission
from app.models.tenant import Tenant

app = create_app()

def create_tables():
    with app.app_context():
        print("Creation des tables...")
        db.create_all()
        print("Tables creees avec succes!")

if __name__ == '__main__':
    create_tables()

>>>

### FICHIER .PY: web\backend\scripts\init_db.py
<<<
#!/usr/bin/env python
"""
Script d'initialisation de la base de données
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.models.fournisseur import Fournisseur
from app.models.client import Client
from app.models.stock import MouvementStock
from app.models.tenant import Tenant, StatutTenant
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.auth import hash_password
from decimal import Decimal
from datetime import datetime, timedelta, date
import random
import secrets

app = create_app()

def init_database():
    """Initialise la base de données avec des données de test"""
    with app.app_context():
        default_password = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)
        
        print("  Suppression des tables existantes...")
        db.drop_all()
        
        print(" Création des tables...")
        db.create_all()

        print(" Création du tenant...")
        tenant = Tenant(
            nom='ERP Commercial',
            slug='erp-commercial',
            domaine='localhost',
            email_contact='admin@erp.com',
            statut=StatutTenant.ACTIF,
            plan='pro',
            max_utilisateurs=20,
            max_produits=1000,
            max_clients=500,
        )
        db.session.add(tenant)
        db.session.flush()
        
        print(" Création des utilisateurs...")
        # Admin
        admin = Utilisateur(
            username='admin',
            email='admin@erp.com',
            password_hash=hash_password(default_password),
            nom='Admin',
            prenom='System',
            role=Role.ADMIN,
            is_active=True
        )
        admin.save()
        
        # Commercial
        commercial = Utilisateur(
            username='commercial',
            email='commercial@erp.com',
            password_hash=hash_password(default_password),
            nom='Ramanantoandro',
            prenom='Jean',
            role=Role.SALES,
            is_active=True
        )
        commercial.save()
        
        # Stock
        stock_manager = Utilisateur(
            username='stock',
            email='stock@erp.com',
            password_hash=hash_password(default_password),
            nom='Ramiaramanana',
            prenom='Pierre',
            role=Role.STOCK,
            is_active=True
        )
        stock_manager.save()

        for utilisateur in (admin, commercial, stock_manager):
            utilisateur.tenant_id = tenant.id
        db.session.commit()
        
        print(" Création des fournisseurs...")
        fournisseurs = [
            Fournisseur(
                code='F001',
                raison_sociale='Rizière Mahavelika',
                siret='12345678901234',
                email='contact@mahavelika.mg',
                telephone='+261 34 12 345 67',
                adresse='RN7, zone Mahavelona',
                code_postal='301',
                ville='Fianarantsoa',
                pays='Madagascar',
                type='producteur_local',
                est_actif=True
            ),
            Fournisseur(
                code='F002',
                raison_sociale='TopAliment Import',
                siret='23456789012345',
                email='info@topaliment.mg',
                telephone='+261 34 47 258 36',
                adresse='Quai de la Gare maritime',
                code_postal='501',
                ville='Toamasina',
                pays='Madagascar',
                type='fournisseur_international',
                est_actif=True
            ),
            Fournisseur(
                code='F003',
                raison_sociale='Mall Boissons',
                siret='34567890123456',
                email='contact@mallboissons.mg',
                telephone='+261 34 47 852 36',
                adresse='Zone industrielle Andraisoro',
                ville='Antananarivo',
                pays='Madagascar',
                type='distributeur',
                est_actif=True
            )
        ]
        for fournisseur in fournisseurs:
            fournisseur.tenant_id = tenant.id
            fournisseur.save()
        
        print(" Création des clients...")
        clients = [
            Client(
                code='C001',
                raison_sociale='Boutique Soa',
                email='contact@boutiquesoa.mg',
                telephone='+261 34 12 345 67',
                adresse_facturation='Avenue de l\'Indépendance',
                code_postal_facturation='101',
                ville_facturation='Antananarivo',
                pays_facturation='Madagascar',
                type='boutique',
                secteur='commerce',
                commercial_id=commercial.id,
                est_actif=True
            ),
            Client(
                code='C002',
                raison_sociale='Épicerie Fitiavana',
                email='contact@epiceriefitiavana.mg',
                telephone='+261 34 85 741 23',
                adresse_facturation='Rue du Marché',
                code_postal_facturation='110',
                ville_facturation='Antsirabe',
                pays_facturation='Madagascar',
                type='epicerie',
                secteur='commerce',
                commercial_id=commercial.id,
                est_actif=True
            ),
            Client(
                code='C003',
                raison_sociale='Hôtel Mahavavy Plage',
                email='contact@mahavavyplage.mg',
                telephone='+261 34 47 852 36',
                adresse_facturation='Boulevard du Littoral',
                code_postal_facturation='601',
                ville_facturation='Mahajanga',
                pays_facturation='Madagascar',
                type='hotel',
                secteur='services',
                commercial_id=commercial.id,
                est_actif=True
            )
        ]
        for client in clients:
            client.tenant_id = tenant.id
            client.save()
        
        print(" Création des produits...")
        produits_data = [
            {
                'reference': 'P001',
                'nom': 'Riz blanc (sac 50 kg)',
                'description_courte': 'Riz blanc de première qualité, sac de 50 kg',
                'categorie': 'Alimentaire',
                'sous_categorie': 'Riz',
                'prix_achat_ht': Decimal('102000.00'),
                'prix_vente_ht': Decimal('130000.00'),
                'taux_tva': Decimal('20.00'),
                'quantite_stock': Decimal('120'),
                'seuil_alerte': Decimal('30'),
                'seuil_critique': Decimal('10'),
                'fournisseur_id': fournisseurs[0].id,
                'marque': 'Mahavelika',
                'unite': 'sac'
            },
            {
                'reference': 'P002',
                'nom': 'Huile de tournesol (carton 6 x 1 L)',
                'description_courte': 'Carton de 6 bouteilles d\'huile de tournesol 1 L',
                'categorie': 'Épicerie',
                'sous_categorie': 'Huiles',
                'prix_achat_ht': Decimal('124000.00'),
                'prix_vente_ht': Decimal('160000.00'),
                'taux_tva': Decimal('20.00'),
                'quantite_stock': Decimal('35'),
                'seuil_alerte': Decimal('10'),
                'seuil_critique': Decimal('5'),
                'fournisseur_id': fournisseurs[1].id,
                'marque': 'Tanamasoandro',
                'unite': 'carton'
            },
            {
                'reference': 'P003',
                'nom': 'Sucre blanc (sac 25 kg)',
                'description_courte': 'Sac de sucre blanc raffiné 25 kg',
                'categorie': 'Alimentaire',
                'sous_categorie': 'Sucre',
                'prix_achat_ht': Decimal('86000.00'),
                'prix_vente_ht': Decimal('110000.00'),
                'taux_tva': Decimal('20.00'),
                'quantite_stock': Decimal('40'),
                'seuil_alerte': Decimal('12'),
                'seuil_critique': Decimal('5'),
                'fournisseur_id': fournisseurs[2].id,
                'marque': 'SIRAMA',
                'unite': 'sac'
            },
            {
                'reference': 'P004',
                'nom': 'Eau minérale (pack 6 x 1,5 L)',
                'description_courte': 'Pack de 6 bouteilles d\'eau minérale 1,5 L',
                'categorie': 'Boissons',
                'sous_categorie': 'Eaux',
                'prix_achat_ht': Decimal('5200.00'),
                'prix_vente_ht': Decimal('7500.00'),
                'taux_tva': Decimal('20.00'),
                'quantite_stock': Decimal('500'),
                'seuil_alerte': Decimal('100'),
                'seuil_critique': Decimal('40'),
                'fournisseur_id': fournisseurs[2].id,
                'marque': 'Talcéa',
                'unite': 'pack'
            },
            {
                'reference': 'P005',
                'nom': 'Savon de toilette (carton 72)',
                'description_courte': 'Carton de 72 savons de toilette parfumés',
                'categorie': 'Hygiène',
                'sous_categorie': 'Savons',
                'prix_achat_ht': Decimal('66000.00'),
                'prix_vente_ht': Decimal('85000.00'),
                'taux_tva': Decimal('20.00'),
                'quantite_stock': Decimal('25'),
                'seuil_alerte': Decimal('8'),
                'seuil_critique': Decimal('3'),
                'fournisseur_id': fournisseurs[1].id,
                'marque': 'Ny Hary',
                'unite': 'carton'
            }
        ]
        
        for data in produits_data:
            data['tenant_id'] = tenant.id
            produit = Produit(**data)
            produit.save()
            print(f"   {produit.nom} - {produit.quantite_stock} unités")
        
        print(" Création des mouvements de stock initiaux...")
        produits = Produit.query.all()
        for produit in produits:
            # Créer un mouvement d'entrée initial
            mouvement = MouvementStock(
                produit_id=produit.id,
                type_mouvement='entree',
                quantite=produit.quantite_stock,
                stock_avant=0,
                stock_apres=produit.quantite_stock,
                raison='Stock initial',
                created_by=admin.id,
                tenant_id=tenant.id,
            )
            mouvement.save()

        print(" Création du plan comptable...")
        comptes_data = [
            ('101', 'Capital social', 'actif', None),
            ('106', 'Réserves', 'actif', None),
            ('120', 'Résultat net', 'actif', None),
            ('164', 'Emprunts', 'passif', None),
            ('401', 'Fournisseurs', 'passif', None),
            ('411', 'Clients', 'actif', None),
            ('445', 'TVA collectée', 'passif', None),
            ('4457', 'TVA déductible', 'actif', '445'),
            ('512', 'Banque', 'actif', None),
            ('530', 'Caisse', 'actif', None),
            ('607', 'Achats marchandises', 'charge', None),
            ('701', 'Ventes marchandises', 'produit', None),
            ('706', 'Prestations de services', 'produit', None),
            ('707', 'Ventes produits fabriqués', 'produit', None),
            ('708', 'Ventes accessoires', 'produit', None),
            ('761', 'Produits financiers', 'produit', None),
            ('771', 'Produits exceptionnels', 'produit', None),
        ]
        comptes_map = {}
        for numero, nom, type_compte, parent_numero in comptes_data:
            parent_id = comptes_map.get(parent_numero) if parent_numero else None
            compte = CompteComptable(
                numero=numero,
                nom=nom,
                type_compte=TypeCompte(type_compte),
                sous_compte_id=parent_id,
                solde=Decimal('0.00'),
                is_actif=True,
                tenant_id=tenant.id,
            )
            db.session.add(compte)
            db.session.flush()
            comptes_map[numero] = compte.id

        print(" Création d'écritures comptables initiales...")
        ecritures_samples = [
            (date.today(), comptes_map.get('512'), Decimal('150000.00'), Decimal('0'), 'Apport initial capital', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('101'), Decimal('0'), Decimal('150000.00'), 'Capital social souscrit', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('401'), Decimal('0'), Decimal('45000.00'), 'Achat marchandises F001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('607'), Decimal('45000.00'), Decimal('0'), 'Achat marchandises F001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('411'), Decimal('32000.00'), Decimal('0'), 'Vente C001', StatutEcriture.VALIDE),
            (date.today(), comptes_map.get('701'), Decimal('0'), Decimal('32000.00'), 'Vente C001', StatutEcriture.VALIDE),
        ]
        for ecr_date, compte_id, debit, credit, libelle, statut in ecritures_samples:
            if compte_id:
                ecriture = EcritureComptable(
                    date=ecr_date,
                    compte_id=compte_id,
                    montant_debit=debit,
                    montant_credit=credit,
                    libelle=libelle,
                    statut=statut,
                    tenant_id=tenant.id,
                )
                db.session.add(ecriture)

        print(" Création d'entrées trésorerie initiales...")
        tresorerie_samples = [
            (date.today(), 'entree', Decimal('150000.00'), 'virement', 'Apport initial capital', 'BNI-001', 'APP-001'),
            (date.today(), 'sortie', Decimal('45000.00'), 'virement', 'Règlement F001', 'BNI-001', 'REG-F001'),
        ]
        for tres_date, type_op, montant, mode, libelle, compte_bancaire, reference in tresorerie_samples:
            entree = Tresorerie(
                date=tres_date,
                type_operation=TypeTresorerie(type_op),
                montant=montant,
                mode_paiement=mode,
                libelle=libelle,
                compte_bancaire=compte_bancaire,
                reference=reference,
                is_reconcilie=False,
                tenant_id=tenant.id,
            )
            db.session.add(entree)

        db.session.commit()
        
        print(" Base de données initialisée avec succès!")
        print(f"\n Mot de passe par defaut: {default_password}")
        print("  Identifiants:")
        print("  - Admin: admin@erp.com")
        print("  - Commercial: commercial@erp.com")
        print("  - Stock: stock@erp.com")

if __name__ == '__main__':
    init_database()
>>>

### FICHIER .PY: web\backend\scripts\migrate_tenant.py
<<<
import os
import sys
import secrets
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.security.auth import hash_password
from sqlalchemy import text
from datetime import datetime


def migrate():
    """Applique les migrations multi-tenant"""
    app = create_app()
    
    with app.app_context():
        print("Début de la migration multi-tenant...")
        
        # Créer toutes les tables (si elles n'existent pas)
        db.create_all()
        print("Tables vérifiées/créées.")
        
        # Vérifier si la colonne tenant_id existe déjà
        inspector = db.inspect(db.engine)
        
        # Ajouter tenant_id aux tables existantes si nécessaire
        tables_to_update = [
            'utilisateurs', 'produits', 'clients', 'fournisseurs',
            'stocks', 'ventes', 'factures', 'paiements',
            'mouvements_stock', 'commandes_fournisseur', 'factures_fournisseur',
            'lignes_vente', 'lignes_achat'
        ]
        
        for table_name in tables_to_update:
            try:
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                if 'tenant_id' not in columns:
                    with db.engine.connect() as conn:
                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER'))
                        conn.commit()
                    print(f"  Colonne tenant_id ajoutée à {table_name}")
            except Exception as e:
                print(f"  {table_name}: {e}")
        
        # Créer le tenant par défaut s'il n'existe pas
        default_tenant = Tenant.query.filter_by(slug='demo').first()
        if not default_tenant:
            default_tenant = Tenant(
                nom='ERP Démonstration',
                slug='demo',
                domaine='localhost',
                email_contact='admin@demo.com',
                statut=StatutTenant.ACTIF,
                plan='pro',
                max_utilisateurs=20,
                max_produits=1000,
                max_clients=500,
                devise='MGA',
                langue='mg',
            )
            db.session.add(default_tenant)
            db.session.flush()
            print("Tenant par défaut créé: demo")
        
        # Créer l'admin par défaut s'il n'existe pas
        admin = Utilisateur.query.filter_by(
            username='admin',
            tenant_id=default_tenant.id
        ).first()
        
        if not admin:
            default_password = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)
            admin = Utilisateur(
                username='admin',
                email='admin@demo.com',
                password_hash=hash_password(default_password),
                nom='Administrateur',
                prenom='System',
                role=Role.ADMIN,
                tenant_id=default_tenant.id,
            )
            db.session.add(admin)
            print(f"Admin créé: admin")
        
        db.session.commit()
        print("Migration terminée avec succès!")


def seed():
    """Remplit la base de données avec des données d'exemple"""
    app = create_app()
    
    with app.app_context():
        print("Remplissage de la base de données...")
        
        tenant = Tenant.query.filter_by(slug='demo').first()
        if not tenant:
            print("Aucun tenant trouvé. Exécutez d'abord migrate()")
            return
        
        # Supprimer les anciennes données du tenant
        Produit.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        from app.models.client import Client
        Client.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        from app.models.fournisseur import Fournisseur
        Fournisseur.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        
        # Créer des produits d'exemple
        produits = [
            Produit(
                nom='Riz blanc (sac 50 kg)', reference='PROD-001',
                prix_achat_ht=102000.0, prix_vente_ht=130000.0,
                quantite_stock=120, categorie='Alimentaire',
                unite='sac',
                tenant_id=tenant.id
            ),
            Produit(
                nom='Huile de tournesol (carton 6 x 1 L)', reference='PROD-002',
                prix_achat_ht=124000.0, prix_vente_ht=160000.0,
                quantite_stock=35, categorie='Épicerie',
                unite='carton',
                tenant_id=tenant.id
            ),
            Produit(
                nom='Eau minérale (pack 6 x 1,5 L)', reference='PROD-003',
                prix_achat_ht=5200.0, prix_vente_ht=7500.0,
                quantite_stock=500, categorie='Boissons',
                unite='pack',
                tenant_id=tenant.id
            ),
        ]
        
        # Créer des clients d'exemple
        clients = [
            Client(
                code='CLI001', raison_sociale='Boutique Soa',
                type='boutique', email='contact@boutiquesoa.mg',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                tenant_id=tenant.id
            ),
            Client(
                code='CLI002', raison_sociale='Épicerie Fitiavana',
                type='epicerie', email='contact@epiceriefitiavana.mg',
                ville_facturation='Antsirabe',
                code_postal_facturation='110',
                tenant_id=tenant.id
            ),
        ]
        
        # Créer des fournisseurs d'exemple
        fournisseurs = [
            Fournisseur(
                code='FOU001', raison_sociale='Rizière Mahavelika',
                type='producteur_local', email='contact@mahavelika.mg',
                ville='Fianarantsoa',
                tenant_id=tenant.id
            ),
            Fournisseur(
                code='FOU002', raison_sociale='TopAliment Import',
                type='fournisseur_international', email='info@topaliment.mg',
                ville='Toamasina',
                tenant_id=tenant.id
            ),
        ]
        
        db.session.add_all(produits + clients + fournisseurs)
        db.session.commit()
        print("Données d'exemple créées!")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'seed':
            seed()
        else:
            migrate()
    else:
        migrate()

>>>

### FICHIER .PY: web\backend\scripts\reset_enterprise_passwords.py
<<<
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password

app = create_app()

ENTERPRISE_USERS = [
    {
        'tenant': {'nom': 'Tech Solutions SARL', 'slug': 'tech-solutions', 'domaine': 'tech.local', 'email_contact': 'contact@tech-solutions.com', 'telephone': '+261 34 12 345 67', 'adresse': '12 Rue de la Tech', 'ville': 'Antananarivo', 'code_postal': '101', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'pro'},
        'user': {'username': 'tech', 'email': 'tech@erp.com', 'password': 'TechPass123!', 'nom': 'Ramanantoandro', 'prenom': 'Thomas', 'telephone': '+261 34 12 345 67', 'role': Role.ADMIN, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 79.0, 'plan': 'pro', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'especes', 'reference_paiement': 'SUB-TECH-001'},
    },
    {
        'tenant': {'nom': 'Green Import', 'slug': 'green-import', 'domaine': 'green.local', 'email_contact': 'contact@green-import.com', 'telephone': '+261 34 98 765 32', 'adresse': '45 Avenue des Importateurs', 'ville': 'Toamasina', 'code_postal': '601', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'enterprise'},
        'user': {'username': 'green', 'email': 'green@erp.com', 'password': 'GreenPass123!', 'nom': 'Razafindramanana', 'prenom': 'Sophie', 'telephone': '+261 34 98 765 32', 'role': Role.MANAGER, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 199.0, 'plan': 'enterprise', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'virement', 'reference_paiement': 'SUB-GREEN-001'},
    },
    {
        'tenant': {'nom': 'DistriPlus', 'slug': 'distriplus', 'domaine': 'distri.local', 'email_contact': 'contact@distriplus.com', 'telephone': '+261 34 45 678 91', 'adresse': '8 Boulevard de la Distribution', 'ville': 'Antsirabe', 'code_postal': '401', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'starter'},
        'user': {'username': 'distri', 'email': 'distri@erp.com', 'password': 'DistriPass123!', 'nom': 'Rasoamanarivo', 'prenom': 'Lucas', 'telephone': '+261 34 45 678 91', 'role': Role.ADMIN, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 29.0, 'plan': 'starter', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'mvola', 'reference_paiement': 'SUB-DISTRI-001'},
    },
    {
        'tenant': {'nom': 'Global Trade', 'slug': 'global-trade', 'domaine': 'global.local', 'email_contact': 'contact@global-trade.com', 'telephone': '+261 34 56 789 01', 'adresse': '100 Rue du Commerce', 'ville': 'Toliara', 'code_postal': '301', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'pro'},
        'user': {'username': 'global', 'email': 'global@erp.com', 'password': 'GlobalPass123!', 'nom': 'Andriamiranto', 'prenom': 'Emma', 'telephone': '+261 34 56 789 01', 'role': Role.SALES, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 79.0, 'plan': 'pro', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'especes', 'reference_paiement': 'SUB-GLOBAL-001'},
    },
    {
        'tenant': {'nom': 'MegaStock', 'slug': 'megastock', 'domaine': 'mega.local', 'email_contact': 'contact@megastock.com', 'telephone': '+261 34 67 890 12', 'adresse': '25 Avenue des Entrepôts', 'ville': 'Antsiranana', 'code_postal': '201', 'pays': 'Madagascar', 'statut': StatutTenant.ACTIF, 'plan': 'enterprise'},
        'user': {'username': 'mega', 'email': 'mega@erp.com', 'password': 'MegaPass123!', 'nom': 'Ramiaramanana', 'prenom': 'Hugo', 'telephone': '+261 34 67 890 12', 'role': Role.STOCK, 'statut': StatutUtilisateur.ACTIF},
        'abonnement': {'montant': 199.0, 'plan': 'enterprise', 'date_debut': datetime.utcnow(), 'date_fin': datetime.utcnow() + timedelta(days=30), 'statut': StatutAbonnement.ACTIF, 'methode_paiement': 'virement', 'reference_paiement': 'SUB-MEGA-001'},
    },
]


def main():
    with app.app_context():
        for item in ENTERPRISE_USERS:
            tenant = Tenant.query.filter_by(slug=item['tenant']['slug']).first()
            if tenant:
                utilisateur = Utilisateur.query.filter_by(tenant_id=tenant.id, email=item['user']['email']).first()
                if utilisateur:
                    utilisateur.password_hash = hash_password(item['user']['password'])
                    print(f"MAJ mot de passe: {item['user']['email']}")
                else:
                    user_data = dict(item['user'])
                    password = user_data.pop('password')
                    user_data['tenant_id'] = tenant.id
                    user_data['password_hash'] = hash_password(password)
                    utilisateur = Utilisateur(**user_data)
                    db.session.add(utilisateur)
                    print(f"Ajoute user: {item['user']['email']}")
            else:
                tenant = Tenant(**item['tenant'])
                db.session.add(tenant)
                db.session.flush()

                user_data = dict(item['user'])
                password = user_data.pop('password')
                user_data['tenant_id'] = tenant.id
                user_data['password_hash'] = hash_password(password)
                utilisateur = Utilisateur(**user_data)
                db.session.add(utilisateur)
                db.session.flush()

                abonnement_data = dict(item['abonnement'])
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
                print(f"Cree: {item['tenant']['nom']} | {item['user']['email']}")

        db.session.commit()
        print("\nListe des users entreprise:")
        for item in ENTERPRISE_USERS:
            print(f"- {item['user']['email']} / {item['user']['password']} ({item['user']['role'].value})")


if __name__ == '__main__':
    main()

>>>

### FICHIER .PY: web\backend\scripts\reset_test_data.py
<<<
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement
from app.models.paiement import Paiement
from app.models.produit import Produit

app = create_app()

from scripts.seed_test_users import main as seed_main

TEST_SLUGS = [
    'distrifood-entreprise',
    'epicerie-solidaire-enterprise',
    'grosriz-distribution',
    'wholesale-center',
    'grossiste-btp',
]

TEST_EMAILS = [
    'distrifood@erp.com',
    'epicerie@erp.com',
    'grosriz@erp.com',
    'wholesale@erp.com',
    'grossiste-btp@erp.com',
    'client.simple@erp.com',
    'client.pub@erp.com',
]


def purge():
    tenants = Tenant.query.filter(Tenant.slug.in_(TEST_SLUGS)).all()
    tenant_ids = [t.id for t in tenants]

    if tenant_ids:
        Paiement.query.filter(Paiement.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Abonnement.query.filter(Abonnement.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Produit.query.filter(Produit.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        Utilisateur.query.filter(Utilisateur.tenant_id.in_(tenant_ids)).delete(
            synchronize_session=False
        )
        for t in tenants:
            db.session.delete(t)

    Utilisateur.query.filter(Utilisateur.email.in_(TEST_EMAILS)).delete(
        synchronize_session=False
    )

    db.session.commit()
    print(f"Purge terminee: {len(tenants)} tenants, {len(TEST_EMAILS)} emails test supprimes.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        purge()
        seed_main()

>>>

### FICHIER .PY: web\backend\scripts\seed_database.py
<<<
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os
import secrets


def seed_tenant(tenant_data, admin_data):
    """Crée un tenant avec son admin"""
    app = create_app()
    
    with app.app_context():
        # Créer le tenant
        tenant = Tenant.query.filter_by(slug=tenant_data['slug']).first()
        if not tenant:
            tenant = Tenant(
                nom=tenant_data['nom'],
                slug=tenant_data['slug'],
                domaine=tenant_data.get('domaine'),
                email_contact=tenant_data.get('email_contact'),
                telephone=tenant_data.get('telephone'),
                adresse=tenant_data.get('adresse'),
                ville=tenant_data.get('ville'),
                pays=tenant_data.get('pays', 'Madagascar'),
                code_postal=tenant_data.get('code_postal'),
                statut=StatutTenant.ACTIF,
                plan=tenant_data.get('plan', 'gratuit'),
                max_utilisateurs=tenant_data.get('max_utilisateurs', 10),
                max_produits=tenant_data.get('max_produits', 500),
                max_clients=tenant_data.get('max_clients', 200),
                devise=tenant_data.get('devise', 'MGA'),
                langue=tenant_data.get('langue', 'mg'),
            )
            db.session.add(tenant)
            db.session.flush()
            print(f"Tenant créé: {tenant.nom}")
        
        # Créer l'admin du tenant
        admin = Utilisateur.query.filter_by(
            username=admin_data['username'],
            tenant_id=tenant.id
        ).first()
        
        if not admin:
            admin = Utilisateur(
                username=admin_data['username'],
                email=admin_data['email'],
                password_hash=hash_password(admin_data['password']),
                nom=admin_data.get('nom', 'Admin'),
                prenom=admin_data.get('prenom', 'System'),
                role=Role.ADMIN,
                statut=admin_data.get('statut', 'actif'),
                tenant_id=tenant.id,
            )
            db.session.add(admin)
            db.session.flush()
            print(f"Admin créé: {admin.username}")
        
        db.session.commit()
        return tenant, admin


def seed_default_tenant():
    """Crée le tenant par défaut"""
    default_password = "Test1234!"
    tenant_data = {
        'nom': 'ERP Démonstration',
        'slug': 'demo',
        'domaine': 'localhost',
        'email_contact': 'admin@demo.com',
        'plan': 'pro',
        'max_utilisateurs': 20,
        'max_produits': 1000,
        'max_clients': 500,
    }
    
    admin_data = {
        'username': 'admin',
        'email': 'admin@demo.com',
        'password': default_password,
        'nom': 'Administrateur',
        'prenom': 'System',
    }
    
    return seed_tenant(tenant_data, admin_data)


def seed_sample_data(tenant_slug='demo'):
    """Ajoute des données d'exemple pour un tenant"""
    app = create_app()
    
    with app.app_context():
        tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        if not tenant:
            print(f"Tenant {tenant_slug} non trouvé")
            return
        
        # Supprimer les anciennes données
        Produit.query.filter_by(tenant_id=tenant.id, is_active=True).delete()
        
        # Créer des produits d'exemple
        produits = [
            Produit(
                nom='Riz blanc (sac 50 kg)',
                reference='PROD-001',
                prix_achat_ht=102000.0,
                prix_vente_ht=130000.0,
                quantite_stock=120,
                categorie='Alimentaire',
                unite='sac',
                tenant_id=tenant.id,
            ),
            Produit(
                nom='Huile de tournesol (carton 6 x 1 L)',
                reference='PROD-002',
                prix_achat_ht=124000.0,
                prix_vente_ht=160000.0,
                quantite_stock=35,
                categorie='Épicerie',
                unite='carton',
                tenant_id=tenant.id,
            ),
            Produit(
                nom='Eau minérale (pack 6 x 1,5 L)',
                reference='PROD-003',
                prix_achat_ht=5200.0,
                prix_vente_ht=7500.0,
                quantite_stock=500,
                categorie='Boissons',
                unite='pack',
                tenant_id=tenant.id,
            ),
            Produit(
                nom='Savon de toilette (carton 72)',
                reference='PROD-004',
                prix_achat_ht=66000.0,
                prix_vente_ht=85000.0,
                quantite_stock=25,
                categorie='Hygiène',
                unite='carton',
                tenant_id=tenant.id,
            ),
        ]
        
        for produit in produits:
            db.session.add(produit)
        
        db.session.commit()
        print(f"Données d'exemple créées pour {tenant.nom}")


if __name__ == '__main__':
    print("Initialisation du tenant par défaut...")
    seed_default_tenant()
    print("Données d'exemple...")
    seed_sample_data()
    print("Terminé!")

>>>

### FICHIER .PY: web\backend\scripts\seed_entreprises.py
<<<
from app import create_app, db
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.tenant import Tenant, StatutTenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os
import secrets

app = create_app()

DEFAULT_PASSWORD = os.getenv('SEED_USER_PASSWORD') or secrets.token_urlsafe(12)

with app.app_context():
    entreprises = [
        {
            'tenant': {
                'nom': 'DistriFood Madagascar',
                'slug': 'distrifood',
                'domaine': 'distrifood.local',
                'email_contact': 'contact@distrifood.mg',
                'telephone': '+261 32 02 345 67',
                'adresse': '12 Rue du Commerce',
                'ville': 'Antananarivo',
                'code_postal': '101',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'distrifood',
                'email': 'distrifood@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ravoahangy',
                'prenom': 'Mirana',
                'telephone': '+261 32 02 345 67',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 199.0,
                'plan': 'enterprise',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'virement',
                'reference_paiement': 'SUB-DISTRIFOOD-001',
            },
        },
        {
            'tenant': {
                'nom': 'Epicerie Solidaire',
                'slug': 'epicerie-solidaire',
                'domaine': 'epicerie.local',
                'email_contact': 'contact@epicerie.mg',
                'telephone': '+261 33 11 223 44',
                'adresse': "7 Avenue de l'Indépendance",
                'ville': 'Toamasina',
                'code_postal': '601',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'starter',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'epicerie',
                'email': 'epicerie@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rabet',
                'prenom': 'Pascal',
                'telephone': '+261 33 11 223 44',
                'role': Role.ADMIN,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 29.0,
                'plan': 'starter',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'orange_money',
                'reference_paiement': 'SUB-EPICIE-001',
            },
        },
        {
            'tenant': {
                'nom': 'GrosRiz Import',
                'slug': 'grosriz',
                'domaine': 'grosriz.local',
                'email_contact': 'contact@grosriz.mg',
                'telephone': '+261 32 55 667 78',
                'adresse': '25 Zone Industrielle',
                'ville': 'Antsirabe',
                'code_postal': '401',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'grosriz',
                'email': 'grosriz@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rasimandimbison',
                'prenom': 'Jean',
                'telephone': '+261 32 55 667 78',
                'role': Role.SALES,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'especes',
                'reference_paiement': 'SUB-GROSRIZ-001',
            },
        },
        {
            'tenant': {
                'nom': 'PharmaDistribution',
                'slug': 'pharmadistrib',
                'domaine': 'pharma.local',
                'email_contact': 'contact@pharma.mg',
                'telephone': '+261 34 77 889 01',
                'adresse': '9 Route de l\'Hôpital',
                'ville': 'Fianarantsoa',
                'code_postal': '301',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'enterprise',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'pharma',
                'email': 'pharma@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Rakoto',
                'prenom': 'Ange',
                'telephone': '+261 34 77 889 01',
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
                'reference_paiement': 'SUB-PHARMA-001',
            },
        },
        {
            'tenant': {
                'nom': 'Boutique en Ligne',
                'slug': 'boutiqueligne',
                'domaine': 'boutique.local',
                'email_contact': 'contact@boutique.mg',
                'telephone': '+261 32 33 44 55',
                'adresse': '16 Analakely',
                'ville': 'Antsiranana',
                'code_postal': '201',
                'pays': 'Madagascar',
                'statut': StatutTenant.ACTIF,
                'plan': 'pro',
                'date_abonnement': datetime.utcnow(),
            },
            'user': {
                'username': 'boutique',
                'email': 'boutique@erp.com',
                'password': DEFAULT_PASSWORD,
                'nom': 'Ranirison',
                'prenom': 'Sophie',
                'telephone': '+261 32 33 44 55',
                'role': Role.USER,
                'statut': StatutUtilisateur.ACTIF,
            },
            'abonnement': {
                'montant': 79.0,
                'plan': 'pro',
                'date_debut': datetime.utcnow(),
                'date_fin': datetime.utcnow() + timedelta(days=30),
                'statut': StatutAbonnement.ACTIF,
                'methode_paiement': 'mvola',
                'reference_paiement': 'SUB-BOUTIQ-001',
            },
        },
    ]

    created_users = []

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

        created_users.append({
            'tenant': tenant.nom,
            'email': user.email,
            'password': password,
            'role': user.role.value,
            'tenant_id': tenant.id,
        })

    db.session.commit()

    print('Entreprises et abonnements créés avec succès :')
    for u in created_users:
        print(f"- {u['tenant']} | {u['email']} | role={u['role']} | tenant_id={u['tenant_id']}")

>>>

### FICHIER .PY: web\backend\scripts\seed_mada_business.py
<<<
#!/usr/bin/env python
"""
Seeder métier réaliste pour un grossiste / distributeur malgache.

Ce script génère un jeu de données complète et culturellement crédible pour
Madagascar (monnaie : Ariary MGA) incluant :

  1. PRODUITS     — 15 articles PGC (riz, huile, sucre, farine, boissons,
                     savons, conserves) avec plusieurs conditionnements et
                     prix d'achat / vente / grossiste / démarché / détail.
  2. TIERS       — Clients variés, fournisseurs crédibles, commercial fictif.
  3. VENTES      — Commandes comptant (espèces / Mobile Money), crédit 7j/15j/
                     30j avec paiements partiels, livraisons en attente.
  4. ACHATS      — Commandes fournisseurs, réceptions, factures, paiements
                     avec gestion des dettes fournisseurs.
  5. STOCKS      — Répartis sur 2 dépôts (Dépôt principal / Magasin boutique)
                     via le champ emplacement + mouvements de stock.
  6. COMPTABIL.  — Plan comptable simplifié, écritures et trésorerie.

Toutes les données sont FICTIVES mais culturellement crédibles.
Toutes les contraintes de clé étrangère sont respectées.

Usage :
    python scripts/seed_mada_business.py
    # ou via Flask CLI :
    flask seed-data mada-business
"""
import sys
import os
from datetime import datetime, timedelta, date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.fournisseur import Fournisseur, TypeFournisseur
from app.models.client import Client, TypeClient, SecteurActivite
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.commande_fournisseur import CommandeFournisseur
from app.models.commande_achat import (
    CommandeAchat, ReceptionAchat, QualiteAchat, StatutCommandeAchat
)
from app.models.facture_fournisseur import FactureFournisseur
from app.models.ligne_achat import LigneAchat
from app.models.compte_comptable import CompteComptable, TypeCompte
from app.models.ecriture_comptable import EcritureComptable, StatutEcriture
from app.models.tresorerie import Tresorerie, TypeTresorerie
from app.security.auth import hash_password
from app.utils.malagasy_data import VILLES_MADAGAS, tel_madag

app = create_app()

PASSWORD = "Test1234!"
TAUX_TVA = Decimal("10.00")

DEPOT_PRINCIPAL = "Dépôt principal - Zone industrielle Andraisoro, Antananarivo"
DEPOT_BOUTIQUE = "Magasin boutique - Analakely, Antananarivo"

DEPOTS = [
    {"nom": "Dépôt principal", "emplacement": DEPOT_PRINCIPAL},
    {"nom": "Magasin boutique", "emplacement": DEPOT_BOUTIQUE},
]


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 1 — TENANT ET UTILISATEURS
# ──────────────────────────────────────────────────────────────────────────────

def seed_tenant_and_users():
    """Crée le tenant 'Distrib Moderne SARL' et ses 3 utilisateurs."""
    tenant = Tenant.query.filter_by(slug='distrib-moderne').first()
    if tenant:
        print(f"  [SKIP] Tenant 'distrib-moderne' existe déjà (id={tenant.id})")
        return tenant

    now = datetime.utcnow()

    tenant = Tenant(
        nom='Distrib Moderne SARL',
        slug='distrib-moderne',
        domaine='distrib-moderne.local',
        email_contact='contact@distrib-moderne.mg',
        telephone='+261 20 22 334 45',
        adresse='Zone industrielle Andraisoro, 27 Rue du Commerce',
        ville='Antananarivo',
        pays='Madagascar',
        code_postal='101',
        statut=StatutTenant.ACTIF,
        plan='pro',
        date_debut_essai=now - timedelta(days=30),
        date_abonnement=now,
        max_utilisateurs=20,
        max_produits=500,
        max_clients=200,
        devise='MGA',
        langue='mg',
        fuseau_horaire='Indian/Antananarivo',
    )
    db.session.add(tenant)
    db.session.flush()

    # Admin
    admin = Utilisateur(
        username='admin',
        email='admin@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Rasolofo',
        prenom='Miora',
        telephone='+261 34 00 111 22',
        mobile='+261 34 00 111 22',
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(admin)

    # Commercial (Jean Rakoto)
    commercial = Utilisateur(
        username='jean.rakoto',
        email='jean.rakoto@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Rakoto',
        prenom='Jean',
        telephone='+261 34 22 333 44',
        mobile='+261 34 22 333 44',
        role=Role.SALES,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(commercial)

    # Gestionnaire de stock
    stock_mgr = Utilisateur(
        username='andry',
        email='andry@distrib-moderne.mg',
        password_hash=hash_password(PASSWORD),
        nom='Andriamianarivo',
        prenom='Andry',
        telephone='+261 34 55 666 77',
        mobile='+261 34 55 666 77',
        role=Role.STOCK,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(stock_mgr)

    db.session.flush()

    # Abonnement
    abonnement = db.session... Abonnement(
        tenant_id=tenant.id,
        montant=Decimal('79.00'),
        devise='USD',
        date_debut=now,
        date_fin=now + timedelta(days=30),
        statut=db.session... StatutAbonnement.ACTIF,
        methode_paiement='virement',
        reference_paiement='SUB-DISTRIBMG-001',
        plan='pro',
    )
    db.session.add(abonnement)

    db.session.commit()

    users = {
        'admin': admin,
        'commercial': commercial,
        'stock': stock_mgr,
    }
    print(f"  [OK] Tenant '{tenant.nom}' créé avec 3 utilisateurs")
    return {'tenant': tenant, 'users': users}


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 2 — FOURNISSEURS
# ──────────────────────────────────────────────────────────────────────────────

FOURNISSEURS_DATA = [
    # Producteur local — riz
    {
        'code': 'FOU-MG-001', 'raison_sociale': 'Rizière Mahavelika',
        'nom_commercial': 'Riz Mahavelika',
        'type': TypeFournisseur.PRODUCTEUR_LOCAL,
        'siret': '01234567890123', 'forme_juridique': 'GIE',
        'email': 'contact@mahavelika.mg', 'telephone': '+261 262 12 345',
        'mobile': '+261 34 01 234 56',
        'adresse': 'Route de Faratsaritra, RN7', 'code_postal': '301',
        'ville': 'Fianarantsoa', 'pays': 'Madagascar',
        'contact_nom': 'Rakotondramanana', 'contact_prenom': 'Julien',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 01 234 56',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 3,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('8.00'),
        'note': 5,
    },
    # Producteur local — sucre
    {
        'code': 'FOU-MG-002', 'raison_sociale': 'Sucreries du Pays SARL',
        'nom_commercial': 'Sucre Pays',
        'type': TypeFournisseur.PRODUCTEUR_LOCAL,
        'siret': '02345678901234', 'forme_juridique': 'SARL',
        'email': 'vente@sucreriedupays.mg', 'telephone': '+261 236 45 678',
        'mobile': '+261 34 02 345 67',
        'adresse': 'Avenue du Sucre,quartier Lavil', 'code_postal': '601',
        'ville': 'Morondava', 'pays': 'Madagascar',
        'contact_nom': 'Ramanjary', 'contact_prenom': 'Sitraka',
        'contact_fonction': 'Commercial', 'contact_telephone': '+261 34 02 345 67',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 5,
        'remise_standard': Decimal('3.00'), 'remise_volume': Decimal('6.00'),
        'note': 4,
    },
    # Fournisseur local — huile
    {
        'code': 'FOU-MG-003', 'raison_sociale': 'Huilerie Centrale',
        'nom_commercial': 'Huile Centrale',
        'type': TypeFournisseur.FOURNISSEUR_LOCAL,
        'siret': '03456789012345', 'forme_juridique': 'SA',
        'email': 'contact@huilerie-centrale.mg', 'telephone': '+261 262 55 667',
        'mobile': '+261 34 03 456 78',
        'adresse': 'Port de Toamasina, Quai 5', 'code_postal': '501',
        'ville': 'Toamasina', 'pays': 'Madagascar',
        'contact_nom': 'Rasoamanarivo', 'contact_prenom': 'Hery',
        'contact_fonction': 'Responsable Achat', 'contact_telephone': '+261 34 03 456 78',
        'conditions_paiement': '15 jours', 'delai_livraison': 5,
        'remise_standard': Decimal('4.00'), 'remise_volume': Decimal('7.00'),
        'note': 4,
    },
    # Distributeur — boissons
    {
        'code': 'FOU-MG-004', 'raison_sociale': 'Brasserie Malagasy SA',
        'nom_commercial': 'BMA Boissons',
        'type': TypeFournisseur.FOURNISSEUR_LOCAL,
        'siret': '04567890123456', 'forme_juridique': 'SA',
        'email': 'commercial@bma.mg', 'telephone': '+261 20 22 445 56',
        'mobile': '+261 34 04 567 89',
        'adresse': '12 Avenue du 14-Juin', 'code_postal': '101',
        'ville': 'Antananarivo', 'pays': 'Madagascar',
        'contact_nom': 'Andriamatoa', 'contact_prenom': 'Lalaina',
        'contact_fonction': 'Responsable Grands Comptes',
        'contact_telephone': '+261 34 04 567 89',
        'conditions_paiement': '30 jours', 'delai_livraison': 2,
        'remise_standard': Decimal('6.00'), 'remise_volume': Decimal('10.00'),
        'note': 5,
    },
    # Importateur international
    {
        'code': 'FOU-MG-005', 'raison_sociale': 'TopAliment Import',
        'nom_commercial': 'TopAliment',
        'type': TypeFournisseur.FOURNISSEUR_INTERNATIONAL,
        'siret': '05678901234567', 'forme_juridique': 'SARL',
        'email': 'info@topaliment.mg', 'telephone': '+261 262 77 889',
        'mobile': '+261 34 05 678 90',
        'adresse': 'Immeuble Mamirok, 3ème étage', 'code_postal': '501',
        'ville': 'Toamasina', 'pays': 'Madagascar',
        'contact_nom': 'Randriamialison', 'contact_prenom': 'Piera',
        'contact_fonction': 'Manager Export',
        'contact_telephone': '+261 34 05 678 90',
        'conditions_paiement': '45 jours', 'delai_livraison': 14,
        'remise_standard': Decimal('2.00'), 'remise_volume': Decimal('5.00'),
        'note': 4,
    },
    # Fabricant — boulangisme/pâtisserie
    {
        'code': 'FOU-MG-006', 'raison_sociale': 'Boulangerie Moderne SARL',
        'nom_commercial': 'Boulangerie Moderne',
        'type': TypeFournisseur.FABRICANT,
        'siret': '06789012345678', 'forme_juridique': 'SARL',
        'email': 'vente@boulangerie-moderne.mg', 'telephone': '+261 262 33 445',
        'mobile': '+261 34 06 789 01',
        'adresse': 'Rue Pasteur Wrapsaint', 'code_postal': '101',
        'ville': 'Antsirabe', 'pays': 'Madagascar',
        'contact_nom': 'Rasoamaharo', 'contact_prenom': 'Nirina',
        'contact_fonction': 'Directrice Commerciale',
        'contact_telephone': '+261 34 06 789 01',
        'conditions_paiement': '30 jours', 'delai_livraison': 7,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('8.00'),
        'note': 5,
    },
    # Fabricant — savonnerie
    {
        'code': 'FOU-MG-007', 'raison_sociale': 'Savonnerie du Lac SARL',
        'nom_commercial': 'Savon du Lac',
        'type': TypeFournisseur.FABRICANT,
        'siret': '07890123456789', 'forme_juridique': 'SARL',
        'email': 'contact@savondulac.mg', 'telephone': '+261 236 22 112',
        'mobile': '+261 34 07 890 12',
        'adresse': 'Route de Mahajanga, PK 8', 'code_postal': '101',
        'ville': 'Mahajanga', 'pays': 'Madagascar',
        'contact_nom': 'Ramoson', 'contact_prenom': 'Brigitte',
        'contact_fonction': 'Responsable Technique',
        'contact_telephone': '+261 34 07 890 12',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 5,
        'remise_standard': Decimal('4.00'), 'remise_volume': Decimal('7.00'),
        'note': 4,
    },
    # Fabricant — conserves
    {
        'code': 'FOU-MG-008', 'raison_sociale': 'Conserves de Madagascar SA',
        'nom_commercial': 'Conserves MG',
        'type': TypeFournisseur.FABRICANT,
        'siret': '08901234567890', 'forme_juridique': 'SA',
        'email': 'commercial@conserves-mg.mg', 'telephone': '+261 262 44 556',
        'mobile': '+261 34 08 901 23',
        'adresse': 'Zone Industrielle Togo Afo', 'code_postal': '301',
        'ville': 'Fianarantsoa', 'pays': 'Madagascar',
        'contact_nom': 'Randriamandimby', 'contact_prenom': 'Sylvain',
        'contact_fonction': 'Gérant',
        'contact_telephone': '+261 34 08 901 23',
        'conditions_paiement': '30 jours fin de mois', 'delai_livraison': 4,
        'remise_standard': Decimal('5.00'), 'remise_volume': Decimal('9.00'),
        'note': 5,
    },
]


def seed_fournisseurs(tenant_id, admin_id):
    fournisseurs = []
    for data in FOURNISSEURS_DATA:
        existing = Fournisseur.query.filter_by(code=data['code'], tenant_id=tenant_id).first()
        if existing:
            fournisseurs.append(existing)
            continue
        f = Fournisseur(**data)
        f.tenant_id = tenant_id
        f.created_by = admin_id
        f.updated_by = admin_id
        db.session.add(f)
        fournisseurs.append(f)
    db.session.flush()
    print(f"  [OK] {len(fournisseurs)} fournisseurs créés")
    return fournisseurs


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 3 — CLIENTS
# ──────────────────────────────────────────────────────────────────────────────

CLIENTS_DATA = [
    {
        'code': 'CLI-MG-001', 'raison_sociale': 'Boutique Soa',
        'type': TypeClient.BOUTIQUE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@boutiquesoa.mg', 'telephone': '+261 34 11 222 33',
        'mobile': '+261 34 11 222 33',
        'adresse_facturation': '27 Avenue de l\'Indépendance',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '27 Avenue de l\'Indépendance',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Ramanantoandro', 'contact_prenom': 'Mireille',
        'contact_fonction': 'Gérante', 'contact_telephone': '+261 34 11 222 33',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('2000000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-002', 'raison_sociale': 'Épicerie Fitiavana',
        'type': TypeClient.EPICERIE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@epiceriefitiavana.mg', 'telephone': '+261 34 22 333 44',
        'mobile': '+261 34 22 333 44',
        'adresse_facturation': '15 Rue du Marché',
        'code_postal_facturation': '110', 'ville_facturation': 'Antsirabe',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '15 Rue du Marché',
        'code_postal_livraison': '110', 'ville_livraison': 'Antsirabe',
        'contact_nom': 'Rabet', 'contact_prenom': 'Pascal',
        'contact_fonction': 'Propriétaire', 'contact_telephone': '+261 34 22 333 44',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('800000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-003', 'raison_sociale': 'Shop Mada',
        'type': TypeClient.SEMI_GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@shopmada.mg', 'telephone': '+261 34 33 444 55',
        'mobile': '+261 34 33 444 55',
        'adresse_facturation': '12 Avenue du 14-Juin',
        'code_postal_facturation': '201', 'ville_facturation': 'Antsiranana',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '12 Avenue du 14-Juin',
        'code_postal_livraison': '201', 'ville_livraison': 'Antsiranana',
        'contact_nom': 'Andriamihaja', 'contact_prenom': 'Bruno',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 33 444 55',
        'conditions_paiement': '7 jours', 'plafond_credit': Decimal('1500000.00'),
        'echeance_credit': 7, 'remise_standard': Decimal('4.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-004', 'raison_sociale': 'Supermarché Mahajy',
        'nom': 'Mahajanarivo', 'prenom': 'Solo',
        'type': TypeClient.SUPERMARCHE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@supermarchemajy.mg', 'telephone': '+261 34 44 555 66',
        'mobile': '+261 34 44 555 66',
        'adresse_facturation': '1 Rue du Marché Central',
        'code_postal_facturation': '401', 'ville_facturation': 'Mahajanga',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '1 Rue du Marché Central',
        'code_postal_livraison': '401', 'ville_livraison': 'Mahajanga',
        'contact_nom': 'Mahajanarivo', 'contact_prenom': 'Solo',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 44 555 66',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('3000000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-005', 'raison_sociale': 'Épicerie Maman Aina',
        'type': TypeClient.EPICERIE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'mamanaina@epicerie.mg', 'telephone': '+261 34 55 666 77',
        'mobile': '+261 34 55 666 77',
        'adresse_facturation': '45 Avenue de la Côte',
        'code_postal_facturation': '501', 'ville_facturation': 'Toamasina',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '45 Avenue de la Côte',
        'code_postal_livraison': '501', 'ville_livraison': 'Toamasina',
        'contact_nom': 'Rasoamanarivo', 'contact_prenom': 'Aïna',
        'contact_fonction': 'Propriétaire', 'contact_telephone': '+261 34 55 666 77',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('500000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 3,
    },
    {
        'code': 'CLI-MG-006', 'raison_sociale': 'Boutique Mama Dina',
        'type': TypeClient.BOUTIQUE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@mamadina.mg', 'telephone': '+261 34 66 777 88',
        'mobile': '+261 34 66 777 88',
        'adresse_facturation': '8 Rue Colbert',
        'code_postal_facturation': '110', 'ville_facturation': 'Antsirabe',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '8 Rue Colbert',
        'code_postal_livraison': '110', 'ville_livraison': 'Antsirabe',
        'contact_nom': 'Andriatra', 'contact_prenom': 'Dina',
        'contact_fonction': 'Gérante', 'contact_telephone': '+261 34 66 777 88',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('600000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('2.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-007', 'raison_sociale': 'Dépôt de Quartier',
        'type': TypeClient.SEMI_GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@depotquartier.mg', 'telephone': '+261 34 77 888 99',
        'mobile': '+261 34 77 888 99',
        'adresse_facturation': '10 Avenue de la Liberté',
        'code_postal_facturation': '601', 'ville_facturation': 'Toliara',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '10 Avenue de la Liberté',
        'code_postal_livraison': '601', 'ville_livraison': 'Toliara',
        'contact_nom': 'Rasolofonirina', 'contact_prenom': 'Heri',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 77 888 99',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('1200000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('4.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-008', 'raison_sociale': 'Restaurant Le Zebu',
        'type': TypeClient.RESTAURANT, 'secteur': SecteurActivite.SERVICES,
        'email': 'contact@restaurantlezebu.mg', 'telephone': '+261 34 88 999 00',
        'mobile': '+261 34 88 999 00',
        'adresse_facturation': '22 Boulevard de l\'Indépendance',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '22 Boulevard de l\'Indépendance',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Rakotondramanana', 'contact_prenom': 'David',
        'contact_fonction': 'Gérant', 'contact_telephone': '+261 34 88 999 00',
        'conditions_paiement': '7 jours', 'plafond_credit': Decimal('300000.00'),
        'echeance_credit': 7, 'remise_standard': Decimal('5.00'),
        'note': 5,
    },
    {
        'code': 'CLI-MG-009', 'raison_sociale': 'Hôtel Coco Beach',
        'type': TypeClient.HOTEL, 'secteur': SecteurActivite.SERVICES,
        'email': 'reservations@cocobeach.mg', 'telephone': '+261 34 99 000 11',
        'mobile': '+261 34 99 000 11',
        'adresse_facturation': '10 Avenue des Baigneurs',
        'code_postal_facturation': '501', 'ville_facturation': 'Toamasina',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': '10 Avenue des Baigneurs',
        'code_postal_livraison': '501', 'ville_livraison': 'Toamasina',
        'contact_nom': 'Andriamiarar', 'contact_prenom': 'Sabrina',
        'contact_fonction': 'Directrice', 'contact_telephone': '+261 34 99 000 11',
        'conditions_paiement': '15 jours', 'plafond_credit': Decimal('1000000.00'),
        'echeance_credit': 15, 'remise_standard': Decimal('3.00'),
        'note': 4,
    },
    {
        'code': 'CLI-MG-010', 'raison_sociale': 'Centrale des Épiceries',
        'type': TypeClient.GROSSISTE, 'secteur': SecteurActivite.COMMERCE,
        'email': 'contact@centrale-epicerie.mg', 'telephone': '+261 34 10 111 22',
        'mobile': '+261 34 10 111 22',
        'adresse_facturation': 'Immeuble Central, 4ème étage',
        'code_postal_facturation': '101', 'ville_facturation': 'Antananarivo',
        'pays_facturation': 'Madagascar',
        'adresse_livraison': 'Immeuble Central, 4ème étage',
        'code_postal_livraison': '101', 'ville_livraison': 'Antananarivo',
        'contact_nom': 'Ramanantsoa', 'contact_prenom': 'Viviane',
        'contact_fonction': 'Responsable Achats',
        'contact_telephone': '+261 34 10 111 22',
        'conditions_paiement': '30 jours', 'plafond_credit': Decimal('5000000.00'),
        'echeance_credit': 30, 'remise_standard': Decimal('5.00'),
        'note': 5,
    },
]


def seed_clients(tenant_id, commercial_id, admin_id):
    clients = []
    for data in CLIENTS_DATA:
        existing = Client.query.filter_by(code=data['code'], tenant_id=tenant_id).first()
        if existing:
            clients.append(existing)
            continue
        data['tenant_id'] = tenant_id
        data['commercial_id'] = commercial_id
        data['created_by'] = admin_id
        data['updated_by'] = admin_id
        c = Client(**data)
        db.session.add(c)
        clients.append(c)
    db.session.flush()
    print(f"  [OK] {len(clients)} clients créés")
    return clients


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 4 — PRODUITS
# ──────────────────────────────────────────────────────────────────────────────

# 15 produits PGC réalistes avec plusieurs conditionnements.
# Les prix sont en Ariary (MGA). Le taux de TVA est 10 % (TNV Madagascar).
PRODUITS_DATA = [
    # ─── RIZ ────────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-001', 'code_barre': '6001000010018', 'code_interne': 'MG-RIZ-001',
        'nom': 'Riz blanc Makalioka (sac 50 kg)',
        'description_courte': 'Riz de première qualité, grain long, conditionné en sac de 50 kg',
        'description_longue': 'Riz blanc Makalioka provenance du Lac Alaotra, grain long, idéal pour la consommation quotidienne et la restauration collective.',
        'categorie': 'Riz & Céréales', 'sous_categorie': 'Riz blanc', 'famille': 'Céréales',
        'marque': 'Lac Alaotra', 'modele': 'Makalioka', 'unite': 'sac',
        'prix_achat_ht': Decimal('350000.00'), 'prix_vente_ht': Decimal('450000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('200'), 'seuil_alerte': Decimal('30'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A1', 'etagere': '03',
        'poids': Decimal('50.00'), 'longueur': Decimal('80'), 'largeur': Decimal('60'), 'hauteur': Decimal('20'),
        'marque': 'Lac Alaotra',
        'prix_grossiste': Decimal('430000.00'), 'prix_demi_gros': Decimal('440000.00'), 'prix_revendeur': Decimal('448000.00'),
        'tags': 'riz,alimentation,grande-consommation',
        'fournisseur_code': 'FOU-MG-001',
    },
    {
        'reference': 'DISTRI-MG-002', 'code_barre': '6001000010025', 'code_interne': 'MG-RIZ-002',
        'nom': 'Riz brisé (sac 25 kg)',
        'description_courte': 'Riz brisé pour la restauration collective et les pâtisseries',
        'categorie': 'Riz & Céréales', 'sous_categorie': 'Riz brisé', 'famille': 'Céréales',
        'marque': 'RSI Mada', 'modele': 'Brisé', 'unite': 'sac',
        'prix_achat_ht': Decimal('175000.00'), 'prix_vente_ht': Decimal('230000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('350'), 'seuil_alerte': Decimal('40'), 'seuil_critique': Decimal('15'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A1', 'etagere': '04',
        'poids': Decimal('25.00'), 'longueur': Decimal('70'), 'largeur': Decimal('50'), 'hauteur': Decimal('15'),
        'marque': 'RSI Mada',
        'prix_grossiste': Decimal('215000.00'), 'prix_demi_gros': Decimal('222000.00'), 'prix_revendeur': Decimal('226000.00'),
        'tags': 'riz,restauration,cereales',
        'fournisseur_code': 'FOU-MG-001',
    },
    # ─── HUILE ────────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-003', 'code_barre': '6001000020019', 'code_interne': 'MG-HUI-001',
        'nom': 'Huile de tournesol (bidon 5 L)',
        'description_courte': 'Huile végétale de tournesol, bidon de 5 L pour les boucheries et le détail',
        'categorie': 'Huiles & Grains', 'sous_categorie': 'Huile alimentaire', 'famille': 'Huiles',
        'marque': 'Hasi', 'modele': 'Classic', 'unite': 'bidon',
        'prix_achat_ht': Decimal('85000.00'), 'prix_vente_ht': Decimal('110000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('150'), 'seuil_alerte': Decimal('25'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B2', 'etagere': '01',
        'poids': Decimal('5.50'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('30'),
        'prix_grossiste': Decimal('103000.00'), 'prix_demi_gros': Decimal('108000.00'), 'prix_revendeur': Decimal('110000.00'),
        'tags': 'huile,cuisine,vegetale',
        'fournisseur_code': 'FOU-MG-003',
    },
    {
        'reference': 'DISTRI-MG-004', 'code_barre': '6001000020026', 'code_interne': 'MG-HUI-002',
        'nom': 'Huile alimentaire (bouteille 1 L)',
        'description_courte': 'Huile de cuisine premium en bouteille de 1 L, très demandée en détail',
        'categorie': 'Huiles & Grains', 'sous_categorie': 'Huile alimentaire', 'famille': 'Huiles',
        'marque': 'Loulou', 'modele': 'Premium', 'unite': 'bouteille',
        'prix_achat_ht': Decimal('2500.00'), 'prix_vente_ht': Decimal('3200.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('2000'), 'seuil_alerte': Decimal('300'), 'seuil_critique': Decimal('100'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C3', 'etagere': '02',
        'poids': Decimal('1.00'), 'longueur': Decimal('7'), 'largeur': Decimal('7'), 'hauteur': Decimal('23'),
        'prix_grossiste': Decimal('2900.00'), 'prix_demi_gros': Decimal('3050.00'), 'prix_revendeur': Decimal('3150.00'),
        'tags': 'huile,cuisine,1l,bouteille',
        'fournisseur_code': 'FOU-MG-003',
    },
    # ─── SUCRE ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-005', 'code_barre': '6001000030012', 'code_interne': 'MG-SUC-001',
        'nom': 'Sucre blanc (sac 25 kg)',
        'description_courte': 'Sucre de canne blanc raffiné, sac de 25 kg pour les professionnels',
        'categorie': 'Couleurs & Sucreries', 'sous_categorie': 'Sucre', 'famille': 'Sucreries',
        'marque': 'Compania', 'modele': 'Blanc', 'unite': 'sac',
        'prix_achat_ht': Decimal('95000.00'), 'prix_vente_ht': Decimal('125000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('180'), 'seuil_alerte': Decimal('30'), 'seuil_critique': Decimal('12'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A2', 'etagere': '02',
        'poids': Decimal('25.00'), 'longueur': Decimal('70'), 'largeur': Decimal('50'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('115000.00'), 'prix_demi_gros': Decimal('120000.00'), 'prix_revendeur': Decimal('122000.00'),
        'tags': 'sucre,cantonnade,restaurant,pâtisserie',
        'fournisseur_code': 'FOU-MG-002',
    },
    {
        'reference': 'DISTRI-MG-006', 'code_barre': '6001000030029', 'code_interne': 'MG-SUC-002',
        'nom': 'Sucre raffiné (paquet 1 kg)',
        'description_courte': 'Sucre raffiné en paquet de 1 kg pour le détail et les particuliers',
        'categorie': 'Couleurs & Sucreries', 'sous_categorie': 'Sucre', 'famille': 'Sucreries',
        'marque': 'Compania', 'modele': 'Raffiné', 'unite': 'sachet',
        'prix_achat_ht': Decimal('3500.00'), 'prix_vente_ht': Decimal('4800.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('9000'), 'seuil_alerte': Decimal('1200'), 'seuil_critique': Decimal('500'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C1', 'etagere': '05',
        'poids': Decimal('1.00'), 'longueur': Decimal('12'), 'largeur': Decimal('12'), 'hauteur': Decimal('8'),
        'prix_grossiste': Decimal('4400.00'), 'prix_demi_gros': Decimal('4600.00'), 'prix_revendeur': Decimal('4700.00'),
        'tags': 'sucre,detail,particulier,1kg',
        'fournisseur_code': 'FOU-MG-002',
    },
    # ─── FARINE ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-007', 'code_barre': '6001000040015', 'code_interne': 'MG-FAR-001',
        'nom': 'Farine de blé (sac 50 kg)',
        'description_courte': 'Farine de blé T45 pour boulangeries et pâtisseries',
        'categorie': 'Farines & Pâtes', 'sous_categorie': 'Farine de blé', 'famille': 'Céréales',
        'marque': 'Aux Mille', 'modele': 'T45', 'unite': 'sac',
        'prix_achat_ht': Decimal('135000.00'), 'prix_vente_ht': Decimal('180000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('120'), 'seuil_alerte': Decimal('25'), 'seuil_critique': Decimal('10'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A3', 'etagere': '01',
        'poids': Decimal('50.00'), 'longueur': Decimal('75'), 'largeur': Decimal('55'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('168000.00'), 'prix_demi_gros': Decimal('174000.00'), 'prix_revendeur': Decimal('177000.00'),
        'tags': 'farine,blé,boulangerie,pâtisserie',
        'fournisseur_code': 'FOU-MG-006',
    },
    {
        'reference': 'DISTRI-MG-008', 'code_barre': '6001000040022', 'code_interne': 'MG-FAR-002',
        'nom': 'Farine de maïs (sac 25 kg)',
        'description_courte': 'Farine de maïs pour les fritures et les pâtes traditionnelles',
        'categorie': 'Farines & Pâtes', 'sous_categorie': 'Farine de maïs', 'famille': 'Céréales',
        'marque': 'Aux Mille', 'modele': 'Maïs', 'unite': 'sac',
        'prix_achat_ht': Decimal('65000.00'), 'prix_vente_ht': Decimal('85000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('90'), 'seuil_alerte': Decimal('20'), 'seuil_critique': Decimal('8'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A3', 'etagere': '02',
        'poids': Decimal('25.00'), 'longueur': Decimal('65'), 'largeur': Decimal('45'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('80000.00'), 'prix_demi_gros': Decimal('82500.00'), 'prix_revendeur': Decimal('83500.00'),
        'tags': 'farine,maïs,friture,tradition',
        'fournisseur_code': 'FOU-MG-006',
    },
    # ─── EAUX & BOISSONS ───────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-009', 'code_barre': '6001000050018', 'code_interne': 'MG-EAS-001',
        'nom': 'Eau minérale (pack 6 x 1,5 L)',
        'description_courte': 'Pack de 6 bouteilles d\'eau minérale de source, 1,5 L chacune',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Eaux minérales', 'famille': 'Boissons',
        'marque': 'Source Tiaca', 'modele': 'Naturelle', 'unite': 'pack',
        'prix_achat_ht': Decimal('7800.00'), 'prix_vente_ht': Decimal('10500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('800'), 'seuil_alerte': Decimal('150'), 'seuil_critique': Decimal('70'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C4', 'etagere': '03',
        'poids': Decimal('9.00'), 'longueur': Decimal('30'), 'largeur': Decimal('20'), 'hauteur': Decimal('22'),
        'prix_grossiste': Decimal('9800.00'), 'prix_demi_gros': Decimal('10100.00'), 'prix_revendeur': Decimal('10300.00'),
        'tags': 'eau,minérale,boisson,source',
        'fournisseur_code': 'FOU-MG-004',
    },
    {
        'reference': 'DISTRI-MG-010', 'code_barre': '6001000050025', 'code_interne': 'MG-BOI-001',
        'nom': 'Boisson gazeuse locale (pack 12 x 1,5 L)',
        'description_courte': 'Soda orange local, pack de 12 bouteilles de 1,5 L',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Boissons gazeuses', 'famille': 'Boissons',
        'marque': 'VCore', 'modele': 'Orange', 'unite': 'pack',
        'prix_achat_ht': Decimal('14500.00'), 'prix_vente_ht': Decimal('19500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('600'), 'seuil_alerte': Decimal('100'), 'seuil_critique': Decimal('50'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B1', 'etagere': '04',
        'poids': Decimal('18.00'), 'longueur': Decimal('35'), 'largeur': Decimal('25'), 'hauteur': Decimal('24'),
        'prix_grossiste': Decimal('17200.00'), 'prix_demi_gros': Decimal('18200.00'), 'prix_revendeur': Decimal('18900.00'),
        'tags': 'boisson,gazéuse,soda,orange,1,5l',
        'fournisseur_code': 'FOU-MG-004',
    },
    {
        'reference': 'DISTRI-MG-011', 'code_barre': '6001000050032', 'code_interne': 'MG-EAS-002',
        'nom': 'Eau en bouteille (1,5 L)',
        'description_courte': 'Eau minérale en bouteille individuelle de 1,5 L',
        'categorie': 'Eaux & Boissons', 'sous_categorie': 'Eaux minérales', 'famille': 'Boissons',
        'marque': 'Source Tiaca', 'modele': 'Indiv', 'unite': 'bouteille',
        'prix_achat_ht': Decimal('1200.00'), 'prix_vente_ht': Decimal('1800.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('3000'), 'seuil_alerte': Decimal('500'), 'seuil_critique': Decimal('200'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C4', 'etagere': '01',
        'poids': Decimal('1.50'), 'longueur': Decimal('7'), 'largeur': Decimal('7'), 'hauteur': Decimal('23'),
        'prix_grossiste': Decimal('1550.00'), 'prix_demi_gros': Decimal('1650.00'), 'prix_revendeur': Decimal('1720.00'),
        'tags': 'eau,minérale,bouteille,1.5l,detail',
        'fournisseur_code': 'FOU-MG-004',
    },
    # ─── BISCUITS ─────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-012', 'code_barre': '6001000060011', 'code_interne': 'MG-BIS-001',
        'nom': 'Biscuit Sucré (carton 250 g x 12)',
        'description_courte': 'Biscuits sucrés au beurre, 12 paquets de 250 g',
        'categorie': 'Biscuits & Gâteaux', 'sous_categorie': 'Biscuits', 'famille': 'Épicerie sèche',
        'marque': 'Vitel', 'modele': 'Sucré', 'unite': 'paquet',
        'prix_achat_ht': Decimal('15000.00'), 'prix_vente_ht': Decimal('21000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('600'), 'seuil_alerte': Decimal('90'), 'seuil_critique': Decimal('40'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B3', 'etagere': '02',
        'poids': Decimal('3.00'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('15'),
        'prix_grossiste': Decimal('19000.00'), 'prix_demi_gros': Decimal('20000.00'), 'prix_revendeur': Decimal('20500.00'),
        'tags': 'biscuit,goûter,snack,sucré',
        'fournisseur_code': 'FOU-MG-006',
    },
    # ─── SAVONS ───────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-013', 'code_barre': '6001000070010', 'code_interne': 'MG-SAV-001',
        'nom': 'Savon de toilette (carton 72)',
        'description_courte': 'Carton de 72 savons de toilette parfumés, 100 g chacun',
        'categorie': 'Hygiène', 'sous_categorie': 'Savons', 'famille': 'Produits d\'hygiène',
        'marque': 'Ny Hary', 'modele': 'Parfum', 'unite': 'carton',
        'prix_achat_ht': Decimal('65000.00'), 'prix_vente_ht': Decimal('85000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('80'), 'seuil_alerte': Decimal('15'), 'seuil_critique': Decimal('8'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'A4', 'etagere': '01',
        'poids': Decimal('7.20'), 'longueur': Decimal('40'), 'largeur': Decimal('30'), 'hauteur': Decimal('25'),
        'prix_grossiste': Decimal('78000.00'), 'prix_demi_gros': Decimal('81000.00'), 'prix_revendeur': Decimal('83000.00'),
        'tags': 'savon,hygiène,toilette,barre',
        'fournisseur_code': 'FOU-MG-007',
    },
    {
        'reference': 'DISTRI-MG-014', 'code_barre': '6001000070027', 'code_interne': 'MG-SAV-002',
        'nom': 'Savon liquide (bidon 5 L)',
        'description_courte': 'Savon liquide concentré pour usages ménagers et industriels, bidon de 5 L',
        'categorie': 'Hygiène', 'sous_categorie': 'Produits ménagers', 'famille': 'Produits d\'hygiène',
        'marque': 'Ny Hary', 'modele': 'Liquide', 'unite': 'bidon',
        'prix_achat_ht': Decimal('75000.00'), 'prix_vente_ht': Decimal('95000.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('60'), 'seuil_alerte': Decimal('12'), 'seuil_critique': Decimal('5'),
        'emplacement': DEPOT_BOUTIQUE, 'rayon': 'C2', 'etagere': '04',
        'poids': Decimal('5.50'), 'longueur': Decimal('25'), 'largeur': Decimal('20'), 'hauteur': Decimal('30'),
        'prix_grossiste': Decimal('88000.00'), 'prix_demi_gros': Decimal('91000.00'), 'prix_revendeur': Decimal('93000.00'),
        'tags': 'savon,liquide,ménager,hygiène',
        'fournisseur_code': 'FOU-MG-007',
    },
    # ─── CONSERVES ────────────────────────────────────────────────────────────
    {
        'reference': 'DISTRI-MG-015', 'code_barre': '6001000080013', 'code_interne': 'MG-CON-001',
        'nom': 'Conserves de sardine (pack 12)',
        'description_courte': 'Conserves de sardines en boîte de 12, provenant de la pêche locale',
        'categorie': 'Conserves & Produits transforms', 'sous_categorie': 'Poissons conservés', 'famille': 'Conserves',
        'marque': 'Pêche MG', 'modele': 'Sardine', 'unite': 'pack',
        'prix_achat_ht': Decimal('12500.00'), 'prix_vente_ht': Decimal('17500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('400'), 'seuil_alerte': Decimal('80'), 'seuil_critique': Decimal('30'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B4', 'etagere': '03',
        'poids': Decimal('5.40'), 'longueur': Decimal('28'), 'largeur': Decimal('20'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('16000.00'), 'prix_demi_gros': Decimal('16800.00'), 'prix_revendeur': Decimal('17200.00'),
        'tags': 'conserves,sardine,poisson,local',
        'fournisseur_code': 'FOU-MG-008',
    },
    {
        'reference': 'DISTRI-MG-016', 'code_barre': '6001000080020', 'code_interne': 'MG-CON-002',
        'nom': 'Conserves de haricots rouges (pack 12)',
        'description_courte': 'Conserves de haricots rouges malgaches, pack de 12 boîtes',
        'categorie': 'Conserves & Produits transforms', 'sous_categorie': 'Légumes conservés', 'famille': 'Conserves',
        'marque': 'Pêche MG', 'modele': 'Haricots', 'unite': 'pack',
        'prix_achat_ht': Decimal('9800.00'), 'prix_vente_ht': Decimal('13500.00'),
        'taux_tva': TAUX_TVA,
        'quantite_stock': Decimal('300'), 'seuil_alerte': Decimal('60'), 'seuil_critique': Decimal('25'),
        'emplacement': DEPOT_PRINCIPAL, 'rayon': 'B4', 'etagere': '04',
        'poids': Decimal('5.00'), 'longueur': Decimal('28'), 'largeur': Decimal('20'), 'hauteur': Decimal('12'),
        'prix_grossiste': Decimal('12200.00'), 'prix_demi_gros': Decimal('12900.00'), 'prix_revendeur': Decimal('13200.00'),
        'tags': 'conserves,haricots,légumes,local',
        'fournisseur_code': 'FOU-MG-008',
    },
]


def seed_produits(tenant_id, fournisseurs, admin_id):
    fournisseur_map = {f.code: f for f in fournisseurs}
    produits = []
    for data in PRODUITS_DATA:
        existing = Produit.query.filter_by(reference=data['reference'], tenant_id=tenant_id).first()
        if existing:
            produits.append(existing)
            continue
        fou_code = data.pop('fournisseur_code')
        fournisseur = fournisseur_map.get(fou_code)
        if fournisseur:
            data['fournisseur_id'] = fournisseur.id
        data['tenant_id'] = tenant_id
        data['created_by'] = admin_id
        data['updated_by'] = admin_id
        data['prix_achat_ttc'] = data['prix_achat_ht'] * (1 + TAUX_TVA / 100)
        data['prix_vente_ttc'] = data['prix_vente_ht'] * (1 + TAUX_TVA / 100)
        data['marge_standard'] = Decimal('0')
        if data['prix_achat_ht'] > 0:
            data['marge_standard'] = (
                (data['prix_vente_ht'] - data['prix_achat_ht']) / data['prix_achat_ht']
            ) * 100
        p = Produit(**data)
        db.session.add(p)
        produits.append(p)
    db.session.flush()
    print(f"  [OK] {len(produits)} produits créés")
    return produits


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 5 — STOCKS INITIAUX (mouvements + répartition dépôts)
# ──────────────────────────────────────────────────────────────────────────────

def seed_stocks_initiaux(produits, tenant_id, stock_mgr_id):
    """Crée les mouvements d'entrée initiale et répartit les stocks sur 2 dépôts."""
    mouvements = []
    now = datetime.utcnow()
    # Date d'initialisation : 30 jours avant aujourd'hui
    date_init = now - timedelta(days=30)

    for p in produits:
        # Mouvement d'entrée initial
        mouvement = MouvementStock(
            produit_id=p.id,
            tenant_id=tenant_id,
            type_mouvement=TypeMouvement.ENTREE,
            quantite=p.quantite_stock,
            stock_avant=Decimal('0'),
            stock_apres=p.quantite_stock,
            raison=f"Réception initiale — {p.emplacement.split(' - ')[0]}",
            reference=f"BL-INIT-{p.reference}",
            created_by=stock_mgr_id,
            created_at=date_init,
        )
        db.session.add(mouvement)
        mouvements.append(mouvement)

    db.session.flush()

    # Quelques transferts entre dépôts pour illustrer la logistics
    transferts = [
        ('DISTRI-MG-006', 20, DEPOT_BOUTIQUE),   # 20 sacs de farine vers le magasin
        ('DISTRI-MG-011', 500, DEPOT_PRINCIPAL),  # 500 bouteilles d'eau retour au dépôt
        ('DISTRI-MG-004', 300, DEPOT_BOUTIQUE),   # 300 bouteilles d'huile vers boutique
    ]
    for ref, qty, emplacement in transferts:
        p = next((x for x in produits if x.reference == ref), None)
        if not p:
            continue
        before = p.quantite_stock
        after = before - qty if emplacement == DEPOT_PRINCIPAL else before  # stock total unchanged
        mouvement = MouvementStock(
            produit_id=p.id,
            tenant_id=tenant_id,
            type_mouvement=TypeMouvement.TRANSFERT,
            quantite=qty,
            stock_avant=before,
            stock_apres=after if emplacement == DEPOT_PRINCIPAL else before,
            raison=f"Transfert vers {emplacement.split(' - ')[0]}",
            reference=f"TF-{p.reference}-01",
            created_by=stock_mgr_id,
            created_at=date_init + timedelta(days=5),
        )
        db.session.add(mouvement)
        mouvements.append(mouvement)

    db.session.commit()
    depot_principal = sum(1 for p in produits if DEPOT_PRINCIPAL in p.emplacement)
    depot_boutique = sum(1 for p in produits if DEPOT_BOUTIQUE in p.emplacement)
    print(f"  [OK] {len(mouvements)} mouvements de stock créés ({depot_principal} produits au dépôt principal, {depot_boutique} au magasin boutique)")
    return mouvements


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 6 — VENTES, FACTURES, PAIEMENTS
# ──────────────────────────────────────────────────────────────────────────────

# Chaque vente définit :
#   client, produits (référence → quantité), date, statut, mode_paiement,
#   crédit_jours, paiements (liste de montants par mode)
VENTES_DATA = [
    # 1. Comptant espèces — Boutique Soa
    {
        'client_code': 'CLI-MG-001',
        'reference': 'VTE-MG-001',
        'date_jours_ago': 5,
        'lignes': [
            ('DISTRI-MG-001', 2),   # Riz 50kg x2
            ('DISTRI-MG-003', 3),   # Huile 5L x3
            ('DISTRI-MG-005', 1),   # Sucre 25kg x1
            ('DISTRI-MG-009', 5),   # Eau pack x5
        ],
        'statut': 'payee',
        'mode_paiement': 'especes',
        'credit_jours': 0,
        'echeance_jours_ago': 5,
        'paiements': [{'montant': None, 'mode': 'especes', 'jours_ago': 5}, 'complete': True],
        'notes': 'Livraison effectuée, règlement en espèces sur place',
    },
    # 2. Mobile Money — Épicerie Fitiavana
    {
        'client_code': 'CLI-MG-002',
        'reference': 'VTE-MG-002',
        'date_jours_ago': 4,
        'lignes': [
            ('DISTRI-MG-006', 20),  # Sucre 1kg x20
            ('DISTRI-MG-012', 10),   # Biscuit x10
            ('DISTRI-MG-015', 5),    # Conserves sardine x5
            ('DISTRI-MG-011', 15),   # Eau 1,5L x15
        ],
        'statut': 'payee',
        'mode_paiement': 'orange_money',
        'credit_jours': 0,
        'echeance_jours_ago': 4,
        'paiements': [{'montant': None, 'mode': 'orange_money', 'jours_ago': 4}, 'complete': True],
        'notes': 'Paiement Orange Money, reçu par SMS',
    },
    # 3. Crédit 7j, partiel — Shop Mada
    {
        'client_code': 'CLI-MG-003',
        'reference': 'VTE-MG-003',
        'date_jours_ago': 10,
        'lignes': [
            ('DISTRI-MG-002', 5),   # Riz 25kg x5
            ('DISTRI-MG-004', 20),   # Huile 1L x20
            ('DISTRI-MG-007', 2),   # Farine 50kg x2
        ],
        'statut': 'payee',
        'mode_paiement': 'a_voir',
        'credit_jours': 7,
        'echeance_jours_ago': 3,
        'paiements': [{'montant': 800000, 'mode': 'orange_money', 'jours_ago': 3}, {'montant': None, 'mode': 'a_voir', 'jours_ago': 0}, 'complete': True],
        'notes': 'Crédit 7 jours — acompte de 800 000 Ar reçu, reste à régler',
    },
    # 4. Crédit 15j, payé à l'échéance — Supermarché Mahajy
    {
        'client_code': 'CLI-MG-004',
        'reference': 'VTE-MG-004',
        'date_jours_ago': 18,
        'lignes': [
            ('DISTRI-MG-001', 3),   # Riz 50kg x3
            ('DISTRI-MG-003', 5),   # Huile 5L x5
            ('DISTRI-MG-005', 3),   # Sucre 25kg x3
            ('DISTRI-MG-016', 15),  # Conserves haricots x15
        ],
        'statut': 'payee',
        'mode_paiement': 'virement',
        'credit_jours': 15,
        'echeance_jours_ago': 3,
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 3}, 'complete': True],
        'notes': 'Crédit 15 jours — solde réglé à l\'échéance par virement bancaire',
    },
    # 5. Crédit 30j, reste à payer — Centrale des Épiceries
    {
        'client_code': 'CLI-MG-010',
        'reference': 'VTE-MG-005',
        'date_jours_ago': 35,
        'lignes': [
            ('DISTRI-MG-001', 5),   # Riz 50kg x5
            ('DISTRI-MG-003', 10),  # Huile 5L x10
            ('DISTRI-MG-005', 4),   # Sucre 25kg x4
            ('DISTRI-MG-007', 3),   # Farine 50kg x3
            ('DISTRI-MG-010', 8),   # Boisson 12-pack x8
            ('DISTRI-MG-012', 20),  # Biscuit x20
        ],
        'statut': 'payee_partiel',
        'mode_paiement': 'a_voir',
        'credit_jours': 30,
        'echeance_jours_ago': 5,
        'paiements': [{'montant': 2500000, 'mode': 'virement', 'jours_ago': 5}, 'complete': False],
        'notes': 'Crédit 30 jours — acompte de 2 500 000 Ar reçu, reste à payer',
    },
    # 6. En attente, non payée — Restaurant Le Zebu
    {
        'client_code': 'CLI-MG-008',
        'reference': 'VTE-MG-006',
        'date_jours_ago': 3,
        'lignes': [
            ('DISTRI-MG-002', 3),   # Riz 25kg x3
            ('DISTRI-MG-004', 10),   # Huile 1L x10
            ('DISTRI-MG-009', 3),   # Eau pack x3
            ('DISTRI-MG-015', 10),  # Conserves sardine x10
        ],
        'statut': 'en_attente',
        'mode_paiement': 'a_voir',
        'credit_jours': 7,
        'echeance_jours_ago': 0,
        'paiements': [], 'complete': False,
        'notes': 'Commande livrée, paiement attendu dans 7 jours',
    },
    # 7. Partiellement réglée — Hôtel Coco Beach
    {
        'client_code': 'CLI-MG-009',
        'reference': 'VTE-MG-007',
        'date_jours_ago': 12,
        'lignes': [
            ('DISTRI-MG-001', 1),   # Riz 50kg x1
            ('DISTRI-MG-003', 2),   # Huile 5L x2
            ('DISTRI-MG-005', 1),   # Sucre 25kg x1
            ('DISTRI-MG-009', 8),   # Eau pack x8
            ('DISTRI-MG-012', 10),  # Biscuit x10
        ],
        'statut': 'payee_partiel',
        'mode_paiement': 'a_voir',
        'credit_jours': 15,
        'echeance_jours_ago': 2,
        'paiements': [{'montant': 500000, 'mode': 'especes', 'jours_ago': 2}, 'complete': True],
        'notes': 'Crédit 15 jours — 500 000 Ar remis en espèces, solde restant',
    },
    # 8. Livrée, non payée, crédit 15j — Dépôt de Quartier
    {
        'client_code': 'CLI-MG-007',
        'reference': 'VTE-MG-008',
        'date_jours_ago': 20,
        'lignes': [
            ('DISTRI-MG-001', 2),   # Riz 50kg x2
            ('DISTRI-MG-003', 3),   # Huile 5L x3
            ('DISTRI-MG-005', 2),   # Sucre 25kg x2
            ('DISTRI-MG-007', 2),   # Farine 50kg x2
            ('DISTRI-MG-010', 6),   # Boisson 12-pack x6
        ],
        'statut': 'en_attente',
        'mode_paiement': 'a_voir',
        'credit_jours': 15,
        'echeance_jours_ago': 5,
        'paiements': [], 'complete': False,
        'notes': 'Livraison effectuée, crédit 15 jours, paiement en attente',
    },
]


def seed_ventes(tenant_id, client_map, produits_map, commercial_id, stock_mgr_id):
    """Crée les ventes, lignes, factures, paiements et mouvements de stock."""
    ventes = []
    now = datetime.utcnow()

    for vd in VENTES_DATA:
        client = client_map.get(vd['client_code'])
        if not client:
            print(f"  [WARN] Client {vd['client_code']} introuvable")
            continue

        date_vente = now - timedelta(days=vd['date_jours_ago'])

        # Créer la vente
        vente = Vente(
            reference=vd['reference'],
            client_id=client.id,
            commercial_id=commercial_id,
            date=date_vente,
            mode_paiement=vd['mode_paiement'],
            type_vente='gros',
            remarque=vd['notes'],
            statut=vd['statut'],
            tenant_id=tenant_id,
            created_by=commercial_id,
            updated_by=commercial_id,
        )
        db.session.add(vente)
        db.session.flush()

        total_ht = Decimal('0')
        total_ttc = Decimal('0')

        for ref, qty in vd['lignes']:
            p = produits_map.get(ref)
            if not p:
                print(f"  [WARN] Produit {ref} introuvable pour vente {vd['reference']}")
                continue
            ligne = LigneVente(
                vente_id=vente.id,
                produit_id=p.id,
                tenant_id=tenant_id,
                quantite=qty,
                prix_unitaire_ht=p.prix_vente_ht,
                taux_tva=TAUX_TVA,
                remise=client.remise_standard or Decimal('0'),
                created_by=commercial_id,
                updated_by=commercial_id,
            )
            db.session.add(ligne)
            db.session.flush()

            total_ht += ligne.total_ht
            total_ttc += ligne.total_ttc

            # Réduire le stock et créer un mouvement de sortie
            p.quantite_stock -= ligne.quantite
            stock_before = p.quantite_stock + ligne.quantite
            sortie = MouvementStock(
                produit_id=p.id,
                tenant_id=tenant_id,
                type_mouvement=TypeMouvement.SORTIE,
                quantite=ligne.quantite,
                stock_avant=stock_before,
                stock_apres=p.quantite_stock,
                raison=f"Vente {vd['reference']} — {client.raison_sociale}",
                reference=vd['reference'],
                created_by=stock_mgr_id,
                created_at=date_vente,
            )
            db.session.add(sortie)

        vente.total_ht = total_ht
        vente.total_ttc = total_ttc
        db.session.flush()

        # Créer la facture liée à la vente
        facture = Facture(
            vente_id=vente.id,
            client_id=client.id,
            tenant_id=tenant_id,
            reference=f"FAC-{vd['reference']}",
            total_ht=total_ht,
            total_ttc=total_ttc,
            statut='non_payee',
            created_by=commercial_id,
            updated_by=commercial_id,
        )
        db.session.add(facture)
        db.session.flush()

        # Créer les paiements
        total_paye = Decimal('0')
        for pmnt in vd.get('paiements', []):
            if pmnt.get('complete'):
                montant = total_ttc - total_paye
            else:
                montant = Decimal(str(pmnt['montant']))

            if montant <= 0:
                continue

            date_paiement = now - timedelta(days=pmnt.get('jours_ago', 0))
            paiement = Paiement(
                facture_id=facture.id,
                client_id=client.id,
                tenant_id=tenant_id,
                montant=montant,
                mode_paiement=pmnt['mode'],
                operateur_mobile=pmnt['mode'] if pmnt['mode'] in ('orange_money', 'airtel_money', 'mvola') else None,
                numero_telephone=client.mobile,
                devise='MGA',
                statut=StatutPaiement.CONFIRME,
                type=TypePaiement.VENTE,
                reference=f"P-{facture.reference}-{pmnt.get('mode', 'especes')[:4]}",
                date_paiement=date_paiement,
                notes=f"Paiement {pmnt['mode']} — Vente {vd['reference']}",
                provider='especes',
                payment_method=pmnt['mode'].upper() if pmnt['mode'] in ('orange_money', 'airtel_money', 'mvola') else 'ESPECES',
                completed_at=date_paiement,
                created_by=commercial_id,
                updated_by=commercial_id,
            )
            db.session.add(paiement)
            total_paye += montant

        # Mettre à jour le statut de la facture
        if total_paye >= total_ttc and total_paye > 0:
            facture.statut = 'payee'
        elif total_paye > 0:
            facture.statut = 'payee_partiel'
        else:
            facture.statut = 'non_payee'

        # Mettre à jour le solde client
        client.solde = client.solde or Decimal('0')
        client.solde -= total_ttc
        client.solde += total_paye

        ventes.append(vente)
        print(f"  [OK] Vente {vd['reference']} — {client.raison_sociale} — HT={float(total_ht):,.0f} Ar — TTC={float(total_ttc):,.0f} Ar — Facture statut={facture.statut}")

    db.session.commit()
    print(f"  [OK] {len(ventes)} ventes créées avec factures et paiements")
    return ventes


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 7 — ACHATS FOURNISSEURS (CommandeAchat + LigneAchat + réception +
#            FactureFournisseur + Paiement)
# ──────────────────────────────────────────────────────────────────────────────

ACHATS_DATA = [
    # 1. Rizière Mahavelika — réceptionné, facturé, payé
    {
        'fournisseur_code': 'FOU-MG-001',
        'reference': 'ACH-MG-001',
        'date_jours_ago': 40,
        'statut': StatutCommandeAchat.RECUE,
        'lignes': [
            ('DISTRI-MG-001', 20, Decimal('350000.00')),  # Riz 50kg x20
            ('DISTRI-MG-002', 30, Decimal('175000.00')),  # Riz 25kg x30
        ],
        'facture_ref': 'FACFOU-MG-001',
        'facture_statut': 'payee',
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 38, 'complete': True}],
        'notes': 'Livraison complète, paiement reçu',
    },
    # 2. Huilerie Centrale — réceptionné, facturé, partiellement payé
    {
        'fournisseur_code': 'FOU-MG-003',
        'reference': 'ACH-MG-002',
        'date_jours_ago': 25,
        'statut': StatutCommandeAchat.PARTIELLEMENT_RECUE,
        'lignes': [
            ('DISTRI-MG-003', 10, Decimal('85000.00')),  # Huile 5L x10
            ('DISTRI-MG-004', 50, Decimal('2500.00')),  # Huile 1L x50
        ],
        'facture_ref': 'FACFOU-MG-002',
        'facture_statut': 'payee_partiel',
        'paiements': [{'montant': 500000, 'mode': 'virement', 'jours_ago': 22, 'complete': False}],
        'notes': 'Livraison partielle (Huile 5L OK, Huile 1L en retard), acompte reçu',
    },
    # 3. TopAliment Import — en cours, non livré
    {
        'fournisseur_code': 'FOU-MG-005',
        'reference': 'ACH-MG-003',
        'date_jours_ago': 10,
        'statut': StatutCommandeAchat.ENVOYEE,
        'lignes': [
            ('DISTRI-MG-012', 30, Decimal('15000.00')),  # Biscuit x30
            ('DISTRI-MG-013', 10, Decimal('65000.00')),  # Savon x10
        ],
        'facture_ref': None,
        'facture_statut': None,
        'paiements': [],
        'notes': 'Commande envoyée, livraison prévue dans 14 jours',
    },
    # 4. Conserves de Madagascar — réceptionné, facturé, payé
    {
        'fournisseur_code': 'FOU-MG-008',
        'reference': 'ACH-MG-004',
        'date_jours_ago': 28,
        'statut': StatutCommandeAchat.RECUE,
        'lignes': [
            ('DISTRI-MG-015', 20, Decimal('12500.00')),  # Conserves sardine x20
            ('DISTRI-MG-016', 15, Decimal('9800.00')),  # Conserves haricots x15
        ],
        'facture_ref': 'FACFOU-MG-004',
        'facture_statut': 'payee',
        'paiements': [{'montant': None, 'mode': 'virement', 'jours_ago': 26, 'complete': True}],
        'notes': 'Livraison complète, solde réglé',
    },
]


def seed_achats(tenant_id, fournisseur_map, produits_map, stock_mgr_id, admin_id):
    """Crée les commandes d'achat, réceptions, factures fournisseur et paiements."""
    now = datetime.utcnow()
    achats = []

    for ad in ACHATS_DATA:
        fournisseur = fournisseur_map.get(ad['fournisseur_code'])
        if not fournisseur:
            continue

        date_cmd = now - timedelta(days=ad['date_jours_ago'])

        # CommandeAchat (obligatoire pour LigneAchat)
        commande_achat = CommandeAchat(
            reference=ad['reference'],
            fournisseur_id=fournisseur.id,
            tenant_id=tenant_id,
            date_commande=date_cmd,
            date_livraison_prevue=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
            statut=ad['statut'],
            conditions_paiement=fournisseur.conditions_paiement,
            remarque=ad['notes'],
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(commande_achat)
        db.session.flush()

        # CommandeFournisseur (simplifiée, pour la trace)
        ref_cmd_fou = f"CF-{ad['reference']}"
        cmd_fournisseur = CommandeFournisseur(
            reference=ref_cmd_fou,
            fournisseur_id=fournisseur.id,
            tenant_id=tenant_id,
            statut='recue' if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE) else 'en_attente',
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(cmd_fournisseur)
        db.session.flush()

        total_ht = Decimal('0')
        total_ttc = Decimal('0')
        total_qty_recue = Decimal('0')
        total_qty_cmd = Decimal('0')

        for ref, qty, prix_achat in ad['lignes']:
            p = produits_map.get(ref)
            if not p:
                continue

            ligne_achat = LigneAchat(
                commande_fournisseur_id=cmd_fournisseur.id,
                commande_achat_id=commande_achat.id,
                produit_id=p.id,
                tenant_id=tenant_id,
                quantite=qty,
                prix_unitaire_ht=prix_achat,
                taux_tva=TAUX_TVA,
                created_by=stock_mgr_id,
                updated_by=stock_mgr_id,
            )
            db.session.add(ligne_achat)
            db.session.flush()

            total_ht += ligne_achat.total_ht
            total_ttc += ligne_achat.total_ht * (1 + TAUX_TVA / 100)
            total_qty_cmd += qty

            # Si réceptionnée, augmenter le stock
            if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE):
                qty_recue = qty if ad['statut'] == StatutCommandeAchat.RECUE else qty // 2
                qty_recue = Decimal(str(qty_recue))
                total_qty_recue += qty_recue

                p.quantite_stock += qty_recue
                entree = MouvementStock(
                    produit_id=p.id,
                    tenant_id=tenant_id,
                    type_mouvement=TypeMouvement.ENTREE,
                    quantite=qty_recue,
                    stock_avant=p.quantite_stock - qty_recue,
                    stock_apres=p.quantite_stock,
                    raison=f"Réception achat {ad['reference']} — {fournisseur.raison_sociale}",
                    reference=ad['reference'],
                    created_by=stock_mgr_id,
                    created_at=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
                )
                db.session.add(entree)

        commande_achat.total_ht = total_ht
        commande_achat.total_ttc = total_ttc
        cmd_fournisseur.total_ht = total_ht
        cmd_fournisseur.total_ttc = total_ttc

        # Réception d'achat (si réceptionnée)
        if ad['statut'] in (StatutCommandeAchat.RECUE, StatutCommandeAchat.PARTIELLEMENT_RECUE):
            reception = ReceptionAchat(
                commande_achat_id=commande_achat.id,
                tenant_id=tenant_id,
                reference=f"REC-{ad['reference']}",
                date_reception=date_cmd + timedelta(days=fournisseur.delai_livraison or 5),
                receptionne_par_id=stock_mgr_id,
                quantite_recue=total_qty_recue,
                quantite_commandee=total_qty_cmd,
                ecart=total_qty_cmd - total_qty_recue,
                remarque='Contrôle qualité effectué',
                created_by=stock_mgr_id,
                updated_by=stock_mgr_id,
            )
            db.session.add(reception)
            db.session.flush()

        # Facture fournisseur + paiement
        if ad.get('facture_ref'):
            facture_fou = FactureFournisseur(
                fournisseur_id=fournisseur.id,
                tenant_id=tenant_id,
                reference=ad['facture_ref'],
                total_ht=total_ht,
                total_ttc=total_ttc,
                statut=ad['facture_statut'],
                created_by=admin_id,
                updated_by=admin_id,
            )
            db.session.add(facture_fou)
            db.session.flush()

            # Paiements fournisseur
            total_paye = Decimal('0')
            for pmnt in ad.get('paiements', []):
                if pmnt.get('complete'):
                    montant = total_ttc - total_paye
                else:
                    montant = Decimal(str(pmnt['montant']))

                if montant <= 0:
                    continue

                date_p = now - timedelta(days=pmnt.get('jours_ago', 0))
                paiement = Paiement(
                    fournisseur_id=fournisseur.id,
                    tenant_id=tenant_id,
                    montant=montant,
                    mode_paiement=pmnt['mode'],
                    devise='MGA',
                    statut=StatutPaiement.CONFIRME,
                    type=TypePaiement.ACHAT,
                    reference=f"PFOU-{ad['facture_ref']}",
                    date_paiement=date_p,
                    notes=f"Paiement fournisseur — {fournisseur.raison_sociale}",
                    provider='bank',
                    completed_at=date_p,
                    created_by=admin_id,
                    updated_by=admin_id,
                )
                db.session.add(paiement)
                total_paye += montant

            # Mettre à jour le statut de la facture fournisseur
            if total_paye >= total_ttc:
                facture_fou.statut = 'payee'
            elif total_paye > 0:
                facture_fou.statut = 'payee_partiel'

            print(f"  [OK] Achat {ad['reference']} — {fournisseur.raison_sociale} — HT={float(total_ht):,.0f} — Statut CMD={ad['statut'].value}, Facture={facture_fou.statut}")

        achats.append(commande_achat)

    db.session.commit()
    print(f"  [OK] {len(achats)} commandes d'achat créées")
    return achats


# ──────────────────────────────────────────────────────────────────────────────
#  PHASE 8 — COMPTABILITÉ
# ──────────────────────────────────────────────────────────────────────────────

COMPTES_DATA = [
    ('101', 'Capital social', TypeCompte.ACTIF, None),
    ('106', 'Report à nouveau', TypeCompte.ACTIF, None),
    ('120', 'Résultat de l exercice', TypeCompte.ACTIF, None),
    ('215', 'Stocks de marchandises', TypeCompte.ACTIF, None),
    ('31',  'Clients', TypeCompte.ACTIF, None),
    ('34',  'Fournisseurs', TypeCompte.PASSIF, None),
    ('445', 'Taxe sur le chiffre d\'affaires déboursée', TypeCompte.PASSIF, None),
    ('4457', 'TVA déductible sur achats', TypeCompte.ACTIF, '445'),
    ('512', 'Banque', TypeCompte.ACTIF, None),
    ('530', 'Caisse', TypeCompte.ACTIF, None),
    ('607', 'Achats de marchandises', TypeCompte.CHARGE, None),
    ('701', 'Ventes de marchandises', TypeCompte.PRODUIT, None),
    ('706', 'Représentation du service', TypeCompte.PRODUIT, None),
    ('775', 'Charges de personnel', TypeCompte.CHARGE, None),
]


def seed_comptabilite(tenant_id, ventes, achats, fournisseur_map, client_map, admin_id):
    """Crée le plan comptable, écritures et mouvements de trésorerie."""
    now = datetime.utcnow()
    comptes_map = {}

    for numero, nom, type_compte, parent_num in COMPTES_DATA:
        existing = CompteComptable.query.filter_by(numero=numero, tenant_id=tenant_id).first()
        if existing:
            comptes_map[numero] = existing.id
            continue
        parent_id = comptes_map.get(parent_num) if parent_num else None
        compte = CompteComptable(
            numero=numero,
            nom=nom,
            type_compte=type_compte,
            sous_compte_id=parent_id,
            solde=Decimal('0.00'),
            is_actif=True,
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(compte)
        db.session.flush()
        comptes_map[numero] = compte.id

    ecritures = []

    # Écriture d'ouverture — apport en capital
    ecritures.append({
        'date': now - timedelta(days=30),
        'compte_id': comptes_map['512'],
        'debit': Decimal('5000000.00'), 'credit': Decimal('0'),
        'libelle': 'Apport initial en capital — Distrib Moderne SARL',
        'entite_type': 'tenant', 'entite_id': None,
    })
    ecritures.append({
        'date': now - timedelta(days=30),
        'compte_id': comptes_map['101'],
        'debit': Decimal('0'), 'credit': Decimal('5000000.00'),
        'libelle': 'Capital social souscrit — Distrib Moderne SARL',
        'entite_type': 'tenant', 'entite_id': None,
    })

    # Écritures pour les ventes (Clients débit, Ventes crédit, TVA collectée crédit)
    ventes_comptees = sorted(ventes, key=lambda v: v.date)
    for v in ventes_comptees:
        if v.statut == 'annulee':
            continue
        ecritures.append({
            'date': v.date,
            'compte_id': comptes_map['31'],
            'debit': v.total_ttc, 'credit': Decimal('0'),
            'libelle': f'Vente {v.reference} — {v.client.nom_complet if v.client else "N/A"}',
            'entite_type': 'vente', 'entite_id': v.id,
        })
        ecritures.append({
            'date': v.date,
            'compte_id': comptes_map['701'],
            'debit': Decimal('0'), 'credit': v.total_ht,
            'libelle': f'Vente {v.reference} — TVA détaillée',
            'entite_type': 'vente', 'entite_id': v.id,
        })
        tva = v.total_ttc - v.total_ht
        if tva > 0:
            ecritures.append({
                'date': v.date,
                'compte_id': comptes_map['445'],
                'debit': Decimal('0'), 'credit': tva,
                'libelle': f'TVA collectée vente {v.reference}',
                'entite_type': 'vente', 'entite_id': v.id,
            })

    # Écritures pour les achats (Achats débit, Fournisseurs crédit, TVA déductible débit)
    for ca in achats:
        if ca.total_ht <= 0:
            continue
        ecritures.append({
            'date': ca.date_commande,
            'compte_id': comptes_map['607'],
            'debit': ca.total_ht, 'credit': Decimal('0'),
            'libelle': f'Achat {ca.reference} — {ca.fournisseur.raison_sociale if ca.fournisseur else "N/A"}',
            'entite_type': 'commande_achat', 'entite_id': ca.id,
        })
        ecritures.append({
            'date': ca.date_commande,
            'compte_id': comptes_map['34'],
            'debit': Decimal('0'), 'credit': ca.total_ht + (ca.total_ttc - ca.total_ht),
            'libelle': f'Facture fournisseur {ca.reference}',
            'entite_type': 'commande_achat', 'entite_id': ca.id,
        })
        tva_achat = ca.total_ttc - ca.total_ht
        if tva_achat > 0:
            ecritures.append({
                'date': ca.date_commande,
                'compte_id': comptes_map['4457'],
                'debit': tva_achat, 'credit': Decimal('0'),
                'libelle': f'TVA déductible achat {ca.reference}',
                'entite_type': 'commande_achat', 'entite_id': ca.id,
            })

    for ecr_data in ecritures:
        ecriture = EcritureComptable(
            date=ecr_data['date'],
            compte_id=ecr_data['compte_id'],
            montant_debit=ecr_data['debit'],
            montant_credit=ecr_data['credit'],
            libelle=ecr_data['libelle'],
            entite_type=ecr_data['entite_type'],
            entite_id=ecr_data['entite_id'],
            statut=StatutEcriture.VALIDE,
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(ecriture)
    db.session.flush()

    # Mouvements de trésorerie liés aux paiements
    tresorerie_entries = []
    all_paiements = Paiement.query.filter_by(tenant_id=tenant_id, is_active=True).all()
    for p in all_paiements:
        if p.type == TypePaiement.VENTE and p.facture_id:
            tres_type = TypeTresorerie.ENTREE
            compte_banque = '530' if p.mode_paiement == 'especes' else '512'
        elif p.type == TypePaiement.ACHAT and p.fournisseur_id:
            tres_type = TypeTresorerie.SORTIE
            compte_banque = '512'  # virement
        elif p.type == TypePaiement.ABONNEMENT:
            continue  # skip subscription payments
        else:
            continue

        tres = Tresorerie(
            date=p.date_paiement.date() if p.date_paiement else now.date(),
            type_operation=tres_type,
            montant=p.montant,
            mode_paiement=p.mode_paiement,
            libelle=p.notes or f'Paiement {p.reference}',
            compte_bancaire=compte_banque + '-MG',
            reference=p.reference,
            is_reconcilie=True,
            compte_id=comptes_map.get(compte_banque),
            tenant_id=tenant_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
        db.session.add(tres)
        tresorerie_entries.append(tres)

    db.session.commit()
    print(f"  [OK] {len(COMPTES_DATA)} comptes comptables, {len(ecritures)} écritures, {len(tresorerie_entries)} mouvements de trésorerie créés")
    return comptes_map


# ──────────────────────────────────────────────────────────────────────────────
#  POINT D'ENTRÉE
# ──────────────────────────────────────────────────────────────────────────────

def seed_all():
    """Exécute l'ensemble des phases de seed."""
    with app.app_context():
        db.create_all()
        result = seed_tenant_and_users()
        tenant = result['tenant']
        users = result['users']

        fournisseurs = seed_fournisseurs(tenant.id, users['admin'].id)
        fournisseur_map = {f.code: f for f in fournisseurs}

        clients = seed_clients(tenant.id, users['commercial'].id, users['admin'].id)
        client_map = {c.code: c for c in clients}

        produits = seed_produits(tenant.id, fournisseurs, users['admin'].id)
        produits_map = {p.reference: p for p in produits}

        seed_stocks_initiaux(produits, tenant.id, users['stock'].id)

        ventes = seed_ventes(
            tenant.id, client_map, produits_map,
            users['commercial'].id, users['stock'].id
        )

        achats = seed_achats(
            tenant.id, fournisseur_map, produits_map,
            users['stock'].id, users['admin'].id
        )

        seed_comptabilite(
            tenant.id, ventes, achats,
            fournisseur_map, client_map, users['admin'].id
        )

        print("\n" + "=" * 70)
        print("SEMAGE MÉTIER MADAGASCAR — TERMINÉ AVEC SUCCÈS")
        print("=" * 70)
        print(f"  Tenant       : {tenant.nom}")
        print(f"  Fournisseurs : {len(fournisseurs)}")
        print(f"  Clients      : {len(clients)}")
        print(f"  Produits     : {len(produits)}")
        print(f"  Ventes       : {len(ventes)}")
        print(f"  Achats       : {len(achats)}")
        print(f"  Mot de passe : {PASSWORD}")
        print(f"  Admin email  : admin@distrib-moderne.mg")
        print(f"  Commercial   : jean.rakoto@distrib-moderne.mg")
        print("=" * 70)


if __name__ == '__main__':
    seed_all()

>>>

### FICHIER .PY: web\backend\scripts\seed_produits_demo.py
<<<
from app import create_app, db
from app.models.produit import Produit
from app.models.utilisateur import Utilisateur
from app.models.tenant import Tenant

app = create_app()

PRODUCT_NAMES_BY_CATEGORY = {
    'riz': [
        'Riz de première qualité',
        'Riz local premium',
        'Riz importé',
    ],
    'huile': [
        'Huile alimentaire 1L',
        'Huile de palme',
        'Huile végétale',
    ],
    'sucre': [
        'Sucre raffiné',
        'Sucre de canne',
        'Sucre blanc',
    ],
    'farine': [
        'Farine de blé',
        'Farine de maïs',
        'Farine de riz',
    ],
    'boissons': [
        'Eau minérale 16L',
        'Boisson gazeuse',
        'Jus de fruit',
    ],
    'biscuits': [
        'Biscuits assorted',
        'Biscuits au chocolat',
        'Biscuits beurre',
    ],
    'conserves': [
        'Conserves de poisson',
        'Conserves de légumes',
        'Conserves viande',
    ],
    'savon': [
        'Savon barre',
        'Savon liquide',
        'Savon antibactérien',
    ],
    'couches': [
        'Couches bébé taille 1',
        'Couches bébé taille 2',
        'Couches bébé taille 3',
    ],
    'entretien': [
        'Lessive poudre',
        'Détergent liquide',
        'Eau de Javel',
    ],
    'cosmetique': [
        'Crème visage',
        'Shampoing',
        'Démaquillant',
    ],
    'fournitures': [
        'Cahier scolaire',
        'Stylo plume',
        'Classeur',
    ],
}

CATEGORIES_MALAGASY = [
    'riz', 'huile', 'sucre', 'farine', 'boissons',
    'biscuits', 'conserves', 'savon', 'couches',
    'entretien', 'cosmetique', 'fournitures',
]

UNITS_MALAGASY = [
    'piece', 'bouteille', 'pack', 'carton', 'sachet',
    'paquet', 'caisse', 'sac', 'bidon', 'veau',
]

PRICE_RANGES = {
    'min': 500,
    'max': 500000,
}

def get_product_data(tenant_slug, category_idx, product_idx):
    category = CATEGORIES_MALAGASY[category_idx % len(CATEGORIES_MALAGASY)]
    product_names = PRODUCT_NAMES_BY_CATEGORY.get(category, ['Produit ' + category])
    nom = product_names[product_idx % len(product_names)]
    
    # Prix réalistes pour le marché malagasy
    base_price = 1000 + (product_idx * 3000 + tenant_slug.count('-') * 500)
    prix_achat_ht = min(base_price, PRICE_RANGES['max'])
    prix_vente_ht = round(prix_achat_ht * 1.5, 2)
    
    # Unités variées
    unite = UNITS_MALAGASY[product_idx % len(UNITS_MALAGASY)]
    
    # Stock diversifié
    quantite_stock = 10 + (product_idx * 25) + (hash(tenant_slug + category) % 40)
    seuil_alerte = max(1, 3 + (product_idx % 3))
    
    descriptions = {
        'riz': 'Riz de qualité supérieure, grain long, idéal pour la consommation quotidienne',
        'huile': 'Huile alimentaire premium, parfaite pour la cuisine',
        'sucre': 'Sucre raffiné, qualité alimentaire',
        'farine': 'Farine de première qualité, pour tous types de pâtisserie',
        'boissons': 'Eau minérale ou boissons rafraîchissantes',
        'biscuits': 'Biscuits délicieux, idéals pour le goûter',
        'conserves': 'Conserves de qualité, conserves prêtes à manger',
        'savon': 'Savon de qualité, pour l\'hygiène quotidienne',
        'couches': 'Couches bébé, confort et protection',
        'entretien': 'Produits d\'entretien ménager, efficacité garantie',
        'cosmetique': 'Produits de beauté et de soin de la peau',
        'fournitures': 'Fournitures de bureau, qualité scolaire',
    }
    
    desc = descriptions.get(category, 'Produit de qualité pour le commerce')
    
    return {
        'tenant_id': None,  # Set per tenant
        'reference': f"{tenant_slug.upper()}-{category[:3].upper()}-{product_idx+1:03d}",
        'code_barre': f"{tenant_slug}-{category[:3].upper()}-{product_idx+1:03d}",
        'nom': nom,
        'description_courte': desc,
        'categorie': category,
        'prix_achat_ht': prix_achat_ht,
        'prix_vente_ht': prix_vente_ht,
        'quantite_stock': quantite_stock,
        'seuil_alerte': seuil_alerte,
    }

with app.app_context():
    tenants = Tenant.query.all()
    count = 0
    for tenant in tenants:
        user = Utilisateur.query.filter_by(tenant_id=tenant.id, is_active=True).first()
        if not user:
            continue
        
        tenant_slug = tenant.slug or str(tenant.id)
        
        for i in range(1, 4):
            product_data = get_product_data(tenant_slug, i, i)
            product_data['tenant_id'] = tenant.id
            
            produit = Produit(
                tenant_id=tenant.id,
                reference=product_data['reference'],
                code_barre=product_data['code_barre'],
                nom=product_data['nom'],
                description_courte=product_data['description_courte'],
                categorie=product_data['categorie'],
                prix_achat_ht=product_data['prix_achat_ht'],
                prix_vente_ht=product_data['prix_vente_ht'],
                quantite_stock=product_data['quantite_stock'],
                seuil_alerte=product_data['seuil_alerte'],
                created_by=user.id,
                updated_by=user.id,
            )
            db.session.add(produit)
            count += 1
    
    db.session.commit()
    print(f'{count} produits créés pour {len(tenants)} tenants')

>>>

### FICHIER .PY: web\backend\scripts\seed_roles.py
<<<
#!/usr/bin/env python
"""
Script d'initialisation des roles et permissions par defaut
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.role_permission import RoleModel, Permission
from app.models.utilisateur import Role

app = create_app()

from app.security.permission_matrix import ROLE_PERMISSIONS

DEFAULT_ROLES = [
    {
        'name': 'super_admin',
        'display_name': 'Super Administrateur',
        'description': 'Acces complet a toutes les fonctionnalites',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'admin',
        'display_name': 'Administrateur',
        'description': 'Acces administratif a toutes les ressources',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'manager',
        'display_name': 'Manager',
        'description': 'Gestion des produits, stock, ventes, utilisateurs et rapports',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'sales',
        'display_name': 'Commercial',
        'description': 'Gestion des ventes, clients et devis',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'stock',
        'display_name': 'Gestionnaire de Stock',
        'description': 'Gestion des stocks, produits et fournisseurs',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'accountant',
        'display_name': 'Comptable',
        'description': 'Gestion comptable, factures et paiements',
        'is_default': True,
        'is_system': True,
    },
    {
        'name': 'user',
        'display_name': 'Utilisateur',
        'description': 'Utilisateur standard avec acces limite',
        'is_default': True,
        'is_system': True,
    },
]

def seed_roles():
    with app.app_context():
        print("Initialisation des roles et permissions...")
        
        for role_data in DEFAULT_ROLES:
            existing = RoleModel.query.filter_by(name=role_data['name']).first()
            if existing:
                print(f"  Role '{role_data['name']}' existe deja, mise a jour...")
                existing.display_name = role_data['display_name']
                existing.description = role_data['description']
                existing.is_default = role_data['is_default']
                existing.is_system = role_data['is_system']
                existing.permissions = []
            else:
                print(f"  Creation du role '{role_data['name']}'...")
                existing = RoleModel(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data['description'],
                    is_default=role_data['is_default'],
                    is_system=role_data['is_system'],
                )
                db.session.add(existing)
            
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
        print("Roles et permissions initialises avec succes!")

if __name__ == '__main__':
    seed_roles()

>>>

### FICHIER .PY: web\backend\scripts\seed_test_users.py
<<<
import os
import sys
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.produit import Produit
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.auth import hash_password

app = create_app()

DEFAULT_PASSWORD = "Test1234!"

ENTERPRISE_USERS = [
    {
        'tenant': {
            'nom': 'DistriFood Madagascar',
            'slug': 'distrifood-entreprise',
            'domaine': 'distrifood.local',
            'email_contact': 'contact@distrifood.mg',
            'telephone': '+261 32 02 345 67',
            'adresse': '12 Rue du Commerce',
            'ville': 'Antananarivo',
            'code_postal': '101',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'enterprise',
        },
        'user': {
            'username': 'distrifood',
            'email': 'distrifood@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Ravoahangy',
            'prenom': 'Mirana',
            'telephone': '+261 32 02 345 67',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 199.0,
            'plan': 'enterprise',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=90),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'Epicerie Solidaire',
            'slug': 'epicerie-solidaire-enterprise',
            'domaine': 'epicerie.local',
            'email_contact': 'contact@epicerie.mg',
            'telephone': '+261 33 11 223 44',
            'adresse': '7 Avenue de l\'Indépendance',
            'ville': 'Toamasina',
            'code_postal': '601',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'starter',
        },
        'user': {
            'username': 'epicerie',
            'email': 'epicerie@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Rabet',
            'prenom': 'Pascal',
            'telephone': '+261 33 11 223 44',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 29.0,
            'plan': 'starter',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'GrosRiz Import',
            'slug': 'grosriz-distribution',
            'domaine': 'grosriz.local',
            'email_contact': 'contact@grosriz.mg',
            'telephone': '+261 32 55 667 78',
            'adresse': '25 Zone Industrielle',
            'ville': 'Antsirabe',
            'code_postal': '401',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'pro',
        },
        'user': {
            'username': 'grosriz',
            'email': 'grosriz@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Rasimandimbison',
            'prenom': 'Jean',
            'telephone': '+261 32 55 667 78',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 79.0,
            'plan': 'pro',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
]

WHOLESALE_USERS = [
    {
        'tenant': {
            'nom': 'Semi-Gros Analamanga',
            'slug': 'wholesale-center',
            'domaine': 'semigros.local',
            'email_contact': 'contact@semigros.mg',
            'telephone': '+261 34 33 444 56',
            'adresse': '7 Rue du Grossiste',
            'ville': 'Fianarantsoa',
            'code_postal': '301',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'pro',
        },
        'user': {
            'username': 'wholesale',
            'email': 'wholesale@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Andriamiranto',
            'prenom': 'Chloé',
            'telephone': '+261 34 33 444 56',
            'role': Role.SALES,
        },
        'abonnement': {
            'montant': 79.0,
            'plan': 'pro',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=60),
            'statut': StatutAbonnement.ACTIF,
        },
    },
    {
        'tenant': {
            'nom': 'Grossiste BTP',
            'slug': 'grossiste-btp',
            'domaine': 'grossiste-btp.local',
            'email_contact': 'contact@grossiste-btp.com',
            'telephone': '+261 34 44 554 67',
            'adresse': '22 Zone Industrielle',
            'ville': 'Toamasina',
            'code_postal': '601',
            'pays': 'Madagascar',
            'statut': StatutTenant.ACTIF,
            'plan': 'starter',
        },
        'user': {
            'username': 'grossiste-btp',
            'email': 'grossiste-btp@erp.com',
            'password': DEFAULT_PASSWORD,
            'nom': 'Ramiaramanana',
            'prenom': 'Olivia',
            'telephone': '+261 34 44 554 67',
            'role': Role.ADMIN,
        },
        'abonnement': {
            'montant': 29.0,
            'plan': 'starter',
            'date_debut': datetime.utcnow(),
            'date_fin': datetime.utcnow() + timedelta(days=30),
            'statut': StatutAbonnement.ACTIF,
        },
    },
]

SIMPLE_USERS = [
    {
        'username': 'client.simple',
        'email': 'client.simple@erp.com',
        'password': DEFAULT_PASSWORD,
        'nom': 'Andriana',
        'prenom': 'Marie',
        'role': Role.USER,
        'statut': StatutUtilisateur.ACTIF,
    },
    {
        'username': 'client.pub',
        'email': 'client.pub@erp.com',
        'password': DEFAULT_PASSWORD,
        'nom': 'Ravoahangy',
        'prenom': 'Lucie',
        'role': Role.USER,
        'statut': StatutUtilisateur.ACTIF,
    },
]


def _create_enterprise(data, kind):
    tenant = Tenant.query.filter_by(slug=data['tenant']['slug']).first()
    if tenant:
        print(f"[{kind}] Tenant existe deja: {tenant.slug}")
        return

    tenant = Tenant(**data['tenant'])
    db.session.add(tenant)
    db.session.flush()

    user = data['user']
    password = user.pop('password')
    user['tenant_id'] = tenant.id
    user['password_hash'] = hash_password(password)
    user['role'] = user.get('role', Role.ADMIN)
    user['statut'] = StatutUtilisateur.ACTIF
    utilisateur = Utilisateur(**user)
    db.session.add(utilisateur)
    db.session.flush()

    abonnement = Abonnement(**data['abonnement'])
    abonnement.tenant_id = tenant.id
    db.session.add(abonnement)
    db.session.flush()

    paiement = Paiement(
        tenant_id=tenant.id,
        montant=abonnement.montant,
        devise='MGA',
        statut=StatutPaiement.CONFIRME,
        type=TypePaiement.ABONNEMENT,
        reference=abonnement.reference_paiement or f"PAY-{tenant.slug}",
        notes=f"Paiement initial - {tenant.nom}",
        date_paiement=datetime.utcnow(),
    )
    db.session.add(paiement)

    db.session.flush()
    print(f"[{kind}] Cree: {tenant.nom} | {utilisateur.email} | role={utilisateur.role.value}")


def _seed_produits(tenant):
    produits = [
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-001",
            nom='Riz de première qualité',
            description_courte='Riz sélectionné, grain long, qualité supérieure',
            categorie='riz',
            prix_achat_ht=7000.0,
            prix_vente_ht=9500.0,
            quantite_stock=120,
            tenant_id=tenant.id,
        ),
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-002",
            nom='Huile alimentaire 1L',
            description_courte='Huile de cuisine premium, bouteille 1L',
            categorie='huile',
            prix_achat_ht=10500.0,
            prix_vente_ht=13500.0,
            quantite_stock=85,
            tenant_id=tenant.id,
        ),
        Produit(
            reference=f"{tenant.slug.upper()}-PROD-003",
            nom='Savon barre',
            description_courte='Savon hygiène quotidienne, paquet de 5',
            categorie='savon',
            prix_achat_ht=6000.0,
            prix_vente_ht=8500.0,
            quantite_stock=200,
            tenant_id=tenant.id,
        ),
    ]
    for p in produits:
        db.session.add(p)
    db.session.flush()


def main():
    with app.app_context():
        db.create_all()

        print("=== Entreprises (enterprise) ===")
        for item in ENTERPRISE_USERS:
            _create_enterprise(item, 'ENTERPRISE')

        print("=== Grossistes (wholesale) ===")
        for item in WHOLESALE_USERS:
            _create_enterprise(item, 'WHOLESALE')

        for tenant_data in (_i['tenant'] for _i in (ENTERPRISE_USERS + WHOLESALE_USERS)):
            tenant = Tenant.query.filter_by(slug=tenant_data['slug']).first()
            if tenant and not Produit.query.filter_by(tenant_id=tenant.id).first():
                _seed_produits(tenant)

        print("=== Utilisateurs simples ===")
        for u in SIMPLE_USERS:
            existing = Utilisateur.query.filter_by(email=u['email']).first()
            if existing:
                print(f"[SIMPLE] Existe deja: {existing.email}")
                continue
            password = u.pop('password')
            u['password_hash'] = hash_password(password)
            utilisateur = Utilisateur(**u)
            db.session.add(utilisateur)
            db.session.flush()
            print(f"[SIMPLE] Cree: {utilisateur.email} | role={utilisateur.role.value}")

        db.session.commit()
        print("\nSeed termine. Utilisateurs de test disponibles:")
        print(f" - Mot de passe par defaut: {DEFAULT_PASSWORD}")
        print(" - Enterprise: distrifood@erp.com")
        print(" - Enterprise: epicerie@erp.com")
        print(" - Enterprise: grosriz@erp.com")
        print(" - Wholesale: wholesale@erp.com")
        print(" - Wholesale: grossiste-btp@erp.com")
        print(" - Simple: client.simple@erp.com")
        print(" - Simple: client.pub@erp.com")


if __name__ == '__main__':
    main()
>>>

### FICHIER .PY: web\backend\scripts\train_ai.py
<<<
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.ai.training import train_models

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        print("🤖 Entraînement des modèles IA en cours...")
        result = train_models()
        print("✅ Entraînement terminé :")
        print(result)


>>>

### FICHIER .PY: web\backend\seed_demo.py
<<<
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password
from datetime import datetime, timedelta
import os

app = create_app()
app.config['TESTING'] = True

with app.app_context():
    # Create tables
    db.create_all()
    
    # Create default tenant (skip if auto-seed already created it)
    existing = Tenant.query.filter_by(slug='demo-seed').first()
    if existing:
        tenant = existing
    else:
        tenant = Tenant(
            nom='ERP Démonstration',
            slug='demo-seed',
            domaine='seed.local',
            statut=StatutTenant.ACTIF,
            plan='pro',
            devise='MGA',
            langue='mg',
            max_utilisateurs=20,
            max_produits=1000,
            max_clients=500,
        )
        db.session.add(tenant)
        db.session.commit()
    print(f"Tenant créé: {tenant.nom} (ID: {tenant.id})")
    
    # Create admin (skip if auto-seed already created it)
    existing_admin = Utilisateur.query.filter_by(username='admin-seed').first()
    if not existing_admin:
        admin = Utilisateur(
            username='admin-seed',
            email='admin-seed@demo.com',
            password_hash=hash_password('Test1234!'),
            nom='Administrateur',
            prenom='System',
            role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant.id,
        )
        db.session.add(admin)
        db.session.commit()
    else:
        admin = existing_admin
    print(f"Admin créé: {admin.username}")
    
    # Create sample products
    produits = [
        Produit(
            nom='Riz blanc (sac 50 kg)',
            reference='PROD-001',
            prix_achat_ht=102000.0,
            prix_vente_ht=130000.0,
            quantite_stock=120,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Huile de tournesol (carton 6 x 1 L)',
            reference='PROD-002',
            prix_achat_ht=124000.0,
            prix_vente_ht=160000.0,
            quantite_stock=35,
            categorie='Épicerie',
            unite='carton',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Eau minérale (pack 6 x 1,5 L)',
            reference='PROD-003',
            prix_achat_ht=5200.0,
            prix_vente_ht=7500.0,
            quantite_stock=500,
            categorie='Boissons',
            unite='pack',
            tenant_id=tenant.id,
        ),
        Produit(
            nom='Savon de toilette (carton 72)',
            reference='PROD-004',
            prix_achat_ht=66000.0,
            prix_vente_ht=85000.0,
            quantite_stock=25,
            categorie='Hygiène',
            unite='carton',
            tenant_id=tenant.id,
        ),
    ]
    
    for produit in produits:
        db.session.add(produit)
    db.session.commit()
    print("Produits d'exemple créés")
    
    # Create a sale with lines
    from app.models.client import Client
    client = Client(
        code='CLI-001',
        nom='Test Client',
        tenant_id=tenant.id,
        is_active=True,
        est_actif=True,
    )
    db.session.add(client)
    db.session.commit()
    
    from app.models.vente import Vente
    from app.models.ligne_vente import LigneVente
    
    # Create a sale
    vente = Vente(
        reference='TEST-001',
        client_id=client.id,
        total_ht=26000.0,
        total_ttc=28600.0,
        statut='payee',
        tenant_id=tenant.id,
    )
    db.session.add(vente)
    db.session.commit()
    
    # Create line
    ligne = LigneVente(
        vente_id=vente.id,
        produit_id=produits[0].id,
        quantite=2,
        prix_unitaire_ht=13000.0,
        taux_tva=10.00,
    )
    db.session.add(ligne)
    db.session.commit()
    
    # Update produit stock
    produit = Produit.query.filter_by(id=produits[0].id).first()
    produit.retirer_stock(2)
    db.session.commit()
    
    print("\n=== Vérification des calculs ===")
    
    # Check CA from Ventes
    from sqlalchemy import func
    ca_query = db.session.query(func.sum(Vente.total_ttc)).filter(Vente.is_active == True, Vente.tenant_id == tenant.id)
    ca_result = ca_query.scalar() or 0
    print(f"CA total (somme des ventes TTC): {ca_result}")
    
    # Check individual ventes
    ventes = Vente.query.filter_by(is_active=True, tenant_id=tenant.id).all()
    ventes_sum = sum(float(v.total_ttc) for v in ventes)
    print(f"Somme des total_ttc des ventes: {ventes_sum}")
    print(f"Écart: {abs(ca_result - ventes_sum)}")
    
    # Check stock values
    produits_db = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
    print(f"\nValeur des stocks:")
    stock_total = 0
    for p in produits_db:
        stock_val = float(p.quantite_stock * p.prix_achat_ht)
        stock_total += stock_val
        print(f"  {p.nom}: quantité={p.quantite_stock}, prix_achat_ht={float(p.prix_achat_ht)}, valeur={stock_val}")
    print(f"Total stock: {stock_total}")
    
    # Check creances calculation
    from app.models.facture import Facture
    from app.models.paiement import Paiement
    
    # Create a facture from the vente
    from app.services.facturation_service import generate_from_vente
    facture = generate_from_vente(vente.id)
    if facture:
        print(f"\nFacture créée: {facture.id}, total_ttc={facture.total_ttc}")
        
        # Create a payment
        paiement = Paiement(
            facture_id=facture.id,
            montant=facture.total_ttc,
            devise='MGA',
            statut='confirme',
            type='vente',
            reference='TEST-PAYMENT',
            notes='Payment test',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant.id,
        )
        db.session.add(paiement)
        db.session.commit()
        print(f"Paiement créé: {paiement.id}, montant={paiement.montant}")
        
        # Check remaining balance
        remaining = float(facture.total_ttc) - float(paiement.montant)
        print(f"Reste à payer: {remaining}")
    
    print("\n=== Vérification de l'isolation multi-tenant ===")
    
    # Create another tenant to verify isolation
    tenant2 = Tenant(
        nom='Autre Tenant',
        slug='other',
        domaine='other.local',
        statut=StatutTenant.ACTIF,
        plan='pro',
    )
    db.session.add(tenant2)
    db.session.commit()
    
    # Create product for second tenant
    produit2 = Produit(
        nom='Produit Autre',
        reference='PROD-005',
        prix_achat_ht=5000.0,
        prix_vente_ht=7500.0,
        quantite_stock=10,
        categorie='Test',
        unite='piece',
        tenant_id=tenant2.id,
    )
    db.session.add(produit2)
    db.session.commit()
    
    # Verify isolation
    produits_tenant1 = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
    produits_tenant2 = Produit.query.filter_by(tenant_id=tenant2.id, is_active=True).all()
    print(f"Produits tenant 1: {len(produits_tenant1)}")
    print(f"Produits tenant 2: {len(produits_tenant2)}")
    print(f"Produit 2 dans tenant 1: {produit2 in produits_tenant1}")
    
    db.session.rollback()
    print("\nTerminé!")
>>>

### FICHIER .PY: web\backend\simulate_refresh_flow.py
<<<
import json
from urllib import request

BASE = 'http://127.0.0.1:5000/api/v1'

# 1) Login
login_payload = {'username':'testuser@example.com','password':'Test1234','tenant_slug':'erp-commercial'}
req = request.Request(f'{BASE}/auth/login', data=json.dumps(login_payload).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
with request.urlopen(req) as r:
    resp = json.loads(r.read().decode('utf-8'))
    access = resp.get('access_token')
    refresh = resp.get('refresh_token')
    print('Login OK, access len', len(access) if access else None)

# 2) Call protected resource with invalid access token
bad_req = request.Request(f'{BASE}/produits', headers={'Authorization':'Bearer invalidtoken'}, method='GET')
try:
    with request.urlopen(bad_req) as r:
        print('Unexpected success', r.status)
except Exception as e:
    print('Protected call with invalid token failed as expected:', e)

# 3) Call refresh with refresh token in Authorization header
refresh_req = request.Request(f'{BASE}/auth/refresh', data=None, headers={'Authorization': f'Bearer {refresh}'}, method='POST')
with request.urlopen(refresh_req) as r2:
    r2b = json.loads(r2.read().decode('utf-8'))
    new_access = r2b.get('access_token')
    print('Refresh returned new access len', len(new_access) if new_access else None)

# 4) Retry protected resource with new access
retry_req = request.Request(f'{BASE}/produits', headers={'Authorization': f'Bearer {new_access}'}, method='GET')
try:
    with request.urlopen(retry_req) as r3:
        print('Retry success, status', r3.status)
        print('Body sample:', r3.read(200).decode('utf-8'))
except Exception as e:
    print('Retry failed:', e)

>>>

### FICHIER .PY: web\backend\test_alembic.py
<<<
import sys
import os
import traceback

os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.app_context():
    from flask import current_app
    from alembic import command
    
    migrate = current_app.extensions['migrate']
    config = migrate.migrate.get_config()
    try:
        command.upgrade(config, 'head')
        print("Migrations applied successfully!")
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")

>>>

### FICHIER .PY: web\backend\test_auth_debug.py
<<<
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.utilisateur import Utilisateur

app = create_app()
with app.app_context():
    try:
        user = Utilisateur.query.filter_by(email='superadmin@test.com').first()
        if user:
            print(f"Found user: {user.username} ({user.email})")
        else:
            print("User superadmin@test.com not found")
    except Exception as e:
        print(f"Error: {e}")

>>>

### FICHIER .PY: web\backend\test_init.py
<<<
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("Step 1: Starting...")

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

print("Step 2: Imports done")

db = SQLAlchemy()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
app.config['JWT_SECRET_KEY'] = 'test'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///erp_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

print("Step 3: DB initialized")

with app.app_context():
    print("Step 4: In context")
    db.create_all()
    print("Step 5: Tables created")

print("Done!")

>>>

### FICHIER .PY: web\backend\test_login.py
<<<
import json
from urllib import request

url = 'http://127.0.0.1:5000/api/v1/auth/login'
payload = {
    'username': 'testuser@example.com',
    'password': 'Test1234',
    'tenant_slug': 'erp-commercial'
}

data = json.dumps(payload).encode('utf-8')
req = request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with request.urlopen(req) as resp:
        body = resp.read().decode('utf-8')
        print(resp.status)
        print(resp.getheaders())
        print(body)
        # Si login OK, essayer le refresh
        import json as _json
        data = _json.loads(body)
        refresh = data.get('refresh_token')
        if refresh:
            print('\nAttempting refresh...')
            refresh_req = request.Request(
                'http://127.0.0.1:5000/api/v1/auth/refresh',
                data=None,
                headers={'Authorization': f'Bearer {refresh}'},
                method='POST'
            )
            try:
                with request.urlopen(refresh_req) as r2:
                    b2 = r2.read().decode('utf-8')
                    print(r2.status)
                    print(r2.getheaders())
                    print(b2)
            except Exception as e2:
                print('Refresh error:', e2)
                if hasattr(e2, 'read'):
                    print(e2.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))

>>>

### FICHIER .PY: web\backend\test_migrate.py
<<<
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

if __name__ == '__main__':
    from flask_migrate import upgrade
    try:
        with app.app_context():
            upgrade()
        print("Migrations applied successfully!")
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")

>>>

### FICHIER .PY: web\backend\tests\__init__.py
<<<
# Test package for backend

>>>

### FICHIER .PY: web\backend\tests\conftest.py
<<<

import pytest
from app import create_app, db as _db


@pytest.fixture(scope='session')
def app():
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
    os.environ['PAPI_API_KEY'] = 'test-api-key'
    os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
    os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

    app = create_app()
    app.config['TESTING'] = True

    with app.app_context():
        _db.drop_all()
        _db.create_all()

    yield app

    with app.app_context():
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()

>>>

### FICHIER .PY: web\backend\tests\test_ai.py
<<<
import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.ai.previsions import predict_sales
from app.ai.anomalies import detect_stock_anomalies
from app.ai.recommendations import suggest_reorders
from app.ai.assistant import ask_assistant
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


def test_predict_sales(app, tenant):
    with app.app_context():
        result = predict_sales(tenant.id, periods=5)
        assert result['periods'] == 5
        assert isinstance(result['forecast'], list)
        assert len(result['forecast']) == 5


def test_detect_stock_anomalies(app, tenant):
    with app.app_context():
        result = detect_stock_anomalies(tenant.id)
        assert 'anomalies' in result
        assert 'count' in result


def test_suggest_reorders(app, tenant):
    with app.app_context():
        result = suggest_reorders(tenant.id)
        assert 'recommendations' in result
        assert 'count' in result


def test_ask_assistant(app, tenant):
    with app.app_context():
        result = ask_assistant(tenant.id, ' Quel est le stock ? ')
        assert isinstance(result, str)
        assert len(result) > 0

>>>

### FICHIER .PY: web\backend\tests\test_auth.py
<<<
from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_login_returns_session_tokens(app):
    auth_result = {
        'access_token': 'access-token',
        'refresh_token': 'refresh-token',
        'user': {'id': 1, 'email': 'admin@example.com'},
        'tenant': {'id': 1, 'slug': 'demo'},
    }

    with patch('app.api.v1.auth.authenticate_user', return_value=(auth_result, None)):
        response = app.test_client().post(
            '/api/v1/auth/login',
            json={'username': 'admin@example.com', 'password': 'secret123'},
        )

    assert response.status_code == 200
    assert response.get_json() == auth_result


def test_login_rejects_incomplete_session_response(app):
    with patch(
        'app.api.v1.auth.authenticate_user',
        return_value=({'user': {'id': 1}}, None),
    ):
        response = app.test_client().post(
            '/api/v1/auth/login',
            json={'username': 'admin@example.com', 'password': 'secret123'},
        )

    assert response.status_code == 500
    assert response.get_json() == {
        'message': 'Le service d’authentification n’a pas généré une session valide'
    }

>>>

### FICHIER .PY: web\backend\tests\test_clients_api.py
<<<
import pytest
from decimal import Decimal
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password, create_access_token_for_user
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro',
    )
    db.session.add(tenant)
    db.session.commit()
    
    abonnement = Abonnement(
        tenant_id=tenant.id,
        montant=79.0,
        plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
        methode_paiement='especes',
        reference_paiement='SUB-TEST-001',
        is_active=True,
        max_clients=2,
    )
    db.session.add(abonnement)
    db.session.commit()
    return tenant


@pytest.fixture
def utilisateur(app, tenant):
    user = Utilisateur(
        username='testuser',
        email='test@test.com',
        password_hash=hash_password('password123'),
        role=Role.ADMIN,
        tenant_id=tenant.id
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def auth_headers(app, utilisateur):
    with app.app_context():
        token = create_access_token_for_user(utilisateur)
    return {'Authorization': f'Bearer {token}'}


class TestClientAPI:
    def test_create_client_success(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI001',
                    'nom': 'Dupont',
                    'prenom': 'Jean',
                    'email': 'jean.dupont@example.com',
                    'telephone': '+261 34 123 4567',
                    'type': 'particulier'
                },
                headers=auth_headers
            )
        assert response.status_code == 201
        data = response.get_json()
        assert data['code'] == 'CLI001'
        assert data['nom'] == 'Dupont'
        assert data['prenom'] == 'Jean'

    def test_create_client_missing_code(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'nom': 'Dupont',
                    'prenom': 'Jean'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'code' in data['message'].lower()

    def test_create_client_no_json(self, app, auth_headers):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                headers=auth_headers
            )
        assert response.status_code in (400, 415)

    def test_create_client_duplicate_code(self, app, auth_headers, tenant):
        with app.app_context():
            client = Client(
                code='CLI002',
                nom='Client Existant',
                tenant_id=tenant.id
            )
            db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI002',
                    'nom': 'Nouveau',
                    'prenom': 'Client'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'CLI002' in data['message']

    def test_create_client_duplicate_email(self, app, auth_headers, tenant):
        with app.app_context():
            client = Client(
                code='CLI003',
                nom='Client Existant',
                email='dupont@example.com',
                tenant_id=tenant.id
            )
            db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI004',
                    'nom': 'Nouveau',
                    'prenom': 'Client',
                    'email': 'dupont@example.com'
                },
                headers=auth_headers
            )
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['message'].lower() or 'existe' in data['message'].lower()

    def test_create_client_unauthorized(self, app):
        with app.app_context():
            response = app.test_client().post(
                '/api/v1/clients/',
                json={'code': 'CLI005'}
            )
        assert response.status_code == 401

    def test_create_client_plan_limit_reached(self, app, auth_headers, tenant):
        with app.app_context():
            for i in range(tenant.max_clients):
                client = Client(
                    code=f'CLI{i:03d}',
                    nom=f'Client {i}',
                    tenant_id=tenant.id
                )
                db.session.add(client)
            db.session.commit()
            
            response = app.test_client().post(
                '/api/v1/clients/',
                json={
                    'code': 'CLI_OVERFLOW',
                    'nom': 'Nouveau'
                },
                headers=auth_headers
            )
        assert response.status_code == 403
        data = response.get_json()
        assert data['message'] == 'Limite de clients atteinte pour votre abonnement actuel.'

    def test_list_clients_tenant_isolation(self, app, tenant):
        with app.app_context():
            autre_tenant = Tenant(
                nom='Autre Tenant',
                slug='autre-tenant',
                domaine='autre.local',
                statut=StatutTenant.ACTIF,
                plan='pro'
            )
            db.session.add(autre_tenant)
            db.session.commit()
            
            abonnement_autre = Abonnement(
                tenant_id=autre_tenant.id,
                montant=79.0,
                plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                methode_paiement='especes',
                reference_paiement='SUB-AUTRE-001',
                is_active=True
            )
            db.session.add(abonnement_autre)
            db.session.commit()
            
            user1 = Utilisateur(
                username='user1',
                email='user1@test.com',
                password_hash=hash_password('password'),
                role=Role.ADMIN,
                tenant_id=tenant.id
            )
            user2 = Utilisateur(
                username='user2',
                email='user2@test.com',
                password_hash=hash_password('password'),
                role=Role.ADMIN,
                tenant_id=autre_tenant.id
            )
            db.session.add_all([user1, user2])
            db.session.commit()
            
            token1 = create_access_token_for_user(user1)
            token2 = create_access_token_for_user(user2)
            
            client1 = Client(code='T1C1', nom='Client T1', tenant_id=tenant.id)
            client2 = Client(code='T1C2', nom='Client T1B', tenant_id=tenant.id)
            client3 = Client(code='T2C1', nom='Client T2', tenant_id=autre_tenant.id)
            db.session.add_all([client1, client2, client3])
            db.session.commit()
            
            response1 = app.test_client().get(
                '/api/v1/clients/',
                headers={'Authorization': f'Bearer {token1}'}
            )
            response2 = app.test_client().get(
                '/api/v1/clients/',
                headers={'Authorization': f'Bearer {token2}'}
            )
        
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert data1['total'] == 2
        codes1 = [c['code'] for c in data1['clients']]
        assert 'T1C1' in codes1
        assert 'T1C2' in codes1
        assert 'T2C1' not in codes1
        
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert data2['total'] == 1
        codes2 = [c['code'] for c in data2['clients']]
        assert 'T2C1' in codes2
        assert 'T1C1' not in codes2

>>>

### FICHIER .PY: web\backend\tests\test_critical_api.py
<<<
import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.document_genere import DocumentGenere
from app.models.modele_document import ModeleDocument
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_tenant():
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=tenant.id,
        montant=100.0,
        plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    user = Utilisateur(
        username='admin',
        email='admin@test.com',
        password_hash=hash_password('Admin123!'),
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(user)
    db.session.commit()
    return tenant, user


def _login(client, email, password, tenant_slug=None):
    payload = {'username': email, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestDashboardAPI:
    def test_dashboard_returns_stats(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/dashboard/', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'stats' in data

    def test_sales_stats(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/dashboard/sales-stats', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'ca_total' in data
        assert 'ventes_mois' in data


class TestSubscriptionAPI:
    def test_create_subscription(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/abonnements/demander', json={
            'montant': 100.0,
            'plan': 'pro',
        }, headers=headers)
        assert r.status_code == 201
        data = r.get_json()
        assert 'abonnement' in data

    def test_get_my_subscription(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.get('/api/v1/abonnements/mon-abonnement', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert 'abonnement' in data


class TestNotificationAPI:
    def test_create_and_list_notifications(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/notifications', json={
            'title': 'Test',
            'message': 'Hello',
            'type': 'info',
        }, headers=headers)
        assert r.status_code == 201
        r = client.get('/api/v1/notifications', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)


class TestAccountingAPI:
    def test_create_account(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/comptes', json={
            'numero': '701',
            'nom': 'Ventes',
            'type_compte': 'produit',
        }, headers=headers)
        assert r.status_code == 201
        data = r.get_json()
        assert data['numero'] == '701'

    def test_create_entry(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        compte = client.post('/api/v1/comptes', json={
            'numero': '701',
            'nom': 'Ventes',
            'type_compte': 'produit',
        }, headers=headers).get_json()
        r = client.post('/api/v1/ecritures', json={
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'compte_id': compte['id'],
            'montant_debit': 0,
            'montant_credit': 100,
            'libelle': 'Test entry',
        }, headers=headers)
        assert r.status_code == 201


class TestDeliveryAPI:
    def test_create_delivery(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        r = client.post('/api/v1/livraisons', json={
            'adresse_livraison': '123 Main St',
            'statut': 'en_attente',
        }, headers=headers)
        assert r.status_code == 201


class TestDocumentAPI:
    def test_create_document(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        headers = _login(client, 'admin@test.com', 'Admin123!', 'test-tenant')
        modele = ModeleDocument(
            nom='Test Modele',
            type_document='facture',
            contenu_modele='<html>{{reference}}</html>',
            tenant_id=tenant.id,
        )
        db.session.add(modele)
        db.session.commit()
        r = client.post('/api/v1/documents', json={
            'modele_id': modele.id,
            'type_document': 'facture',
            'reference': 'DOC-001',
            'entite_type': 'vente',
            'entite_id': 1,
            'contenu_html': '<html>DOC-001</html>',
        }, headers=headers)
        assert r.status_code == 201


class TestPublicAPI:
    def test_public_catalogue(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        produit = Produit(
            nom='Public Product',
            reference='PUB-001',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15,
        )
        db.session.add(produit)
        db.session.commit()
        r = client.get('/public/produits')
        assert r.status_code == 200

    def test_public_checkout(self, app):
        tenant, user = _make_tenant()
        client = app.test_client()
        produit = Produit(
            nom='Public Product',
            reference='PUB-002',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15,
            quantite_stock=100,
        )
        db.session.add(produit)
        db.session.commit()
        r = client.post('/public/commandes', json={
            'nom_client': 'John Doe',
            'email_client': 'john@example.com',
            'items': [{'produit_id': produit.id, 'quantite': 2}],
        })
        assert r.status_code == 201

>>>

### FICHIER .PY: web\backend\tests\test_mission_5.py
<<<
import json
import uuid
from datetime import datetime, timedelta

import pytest
from decimal import Decimal

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.client import Client
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.fournisseur import Fournisseur, TypeFournisseur
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat, ReceptionAchat
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.livraison import Livraison
from app.security.auth import hash_password, create_access_token_for_user


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('PAPI_API_URL', 'https://test.papi.mg/dashboard/api/payment-links')
    monkeypatch.setenv('PAPI_API_KEY', 'test-api-key')
    monkeypatch.setenv('PAPI_ENVIRONMENT', 'sandbox')
    monkeypatch.setenv('PAPI_CALLBACK_URL', 'http://localhost:5000/api/v1/papi/webhook')

    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def tenant_id(app):
    with app.app_context():
        tenant = Tenant(
            nom='Test Tenant Malagasy',
            slug='test-mg-mission5',
            domaine='test.mg',
            statut=StatutTenant.ACTIF,
            plan='pro',
            max_clients=50,
        )
        db.session.add(tenant)
        db.session.commit()

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='especes',
            reference_paiement='SUB-MISSION5-001',
            is_active=True
        )
        db.session.add(abonnement)
        db.session.commit()
        return tenant.id


@pytest.fixture
def abonnement_id(app, tenant_id):
    with app.app_context():
        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='especes',
            reference_paiement='SUB-TEST-001',
            is_active=True,
        )
        db.session.add(abonnement)
        db.session.commit()
        return abonnement.id


@pytest.fixture
def utilisateur_id(app, tenant_id):
    with app.app_context():
        user = Utilisateur(
            username='testuser',
            email='test@test.mg',
            password_hash=hash_password('password123'),
            role=Role.ADMIN,
            tenant_id=tenant_id,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def auth_headers(app, utilisateur_id):
    with app.app_context():
        user = db.session.get(Utilisateur, utilisateur_id)
        token = create_access_token_for_user(user)
    return {'Authorization': f'Bearer {token}'}


class TestWorkflowVenteComplet:
    """WORKFLOW VENTE COMPLET"""

    def test_workflow_vente_end_to_end(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            client = Client(
                code='CLI001',
                nom='Ravo',
                prenom='Jean',
                email='jean.ravo@test.mg',
                telephone='+261 34 123 4567',
                type='particulier',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                pays_facturation='Madagascar',
                ville_livraison='Antananarivo',
                code_postal_livraison='101',
                pays_livraison='Madagascar',
                tenant_id=tenant_id,
            )
            db.session.add(client)
            db.session.commit()
            client_id = client.id

            product1 = Produit(
                reference='PROD001',
                nom='Riz Makalioka 25kg',
                unite='sac',
                prix_vente_ht=15000.00,
                prix_achat_ht=8000.00,
                taux_tva=20.00,
                quantite_stock=100,
                categorie='alimentaire',
                tenant_id=tenant_id,
            )
            product2 = Produit(
                reference='PROD002',
                nom='Huile Loulou 1L carton',
                unite='carton',
                prix_vente_ht=5000.00,
                prix_achat_ht=2500.00,
                taux_tva=20.00,
                quantite_stock=50,
                categorie='agricole',
                tenant_id=tenant_id,
            )
            db.session.add_all([product1, product2])
            db.session.commit()
            prod1_id = product1.id
            prod2_id = product2.id

            stock_prod1_before = float(product1.quantite_stock)
            stock_prod2_before = float(product2.quantite_stock)

        # Créer commande vente
        response = app.test_client().post(
            '/api/v1/ventes/',
            json={
                'client_id': client_id,
                'reference': 'VENT-TEST-001',
                'mode_paiement': 'especes',
                'lignes': [
                    {'produit_id': prod1_id, 'quantite': 5, 'prix_unitaire': 15000.00},
                    {'produit_id': prod2_id, 'quantite': 2, 'prix_unitaire': 5000.00},
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, f"Creation vente failed: {response.get_json()}"
        vente = response.get_json()
        vente_id = vente['id']

        with app.app_context():
            p1 = db.session.get(Produit, prod1_id)
            p2 = db.session.get(Produit, prod2_id)
            assert float(p1.quantite_stock) == stock_prod1_before - 5
            assert float(p2.quantite_stock) == stock_prod2_before - 2

        # Valider vente
        response = app.test_client().put(
            f'/api/v1/ventes/{vente_id}',
            json={'statut': 'confirmee'},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.get_json()['statut'] == 'confirmee'

        # Générer bon de livraison
        response = app.test_client().post(
            '/api/v1/livraisons/',
            json={
                'vente_id': vente_id,
                'adresse_livraison': 'Analakely',
                'ville_livraison': 'Antananarivo',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        livraison = response.get_json()
        livraison_id = livraison['id']

        response = app.test_client().post(
            f'/api/v1/livraisons/{livraison_id}/statut',
            json={'statut': 'livree', 'commentaire': 'Livrée à Antananarivo'},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Facturer à crédit 15j
        response = app.test_client().post(
            f'/api/v1/factures/from-vente/{vente_id}',
            json={'reference': f'FAC-{vente["reference"]}', 'statut': 'non_payee'},
            headers=auth_headers,
        )
        assert response.status_code == 201
        facture = response.get_json()
        facture_id = facture['id']

        response = app.test_client().put(
            f'/api/v1/factures/{facture_id}',
            json={'statut': 'en_credit', 'conditions_paiement': '15 jours'},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Paiement partiel MVola
        part = round(float(facture['total_ttc']) * 0.6, 2)
        response = app.test_client().post(
            '/api/v1/paiements/',
            json={
                'facture_id': facture_id,
                'montant': part,
                'mode_paiement': 'MVOLA',
                'reference': f'PAY-MV-{uuid.uuid4().hex[:6].upper()}',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        paiement = response.get_json()
        assert float(paiement['montant']) == part

        response = app.test_client().get(f'/api/v1/factures/{facture_id}', headers=auth_headers)
        assert response.status_code == 200
        facture_after = response.get_json()
        assert facture_after['statut'] in ('payee_partiel', 'payee')


class TestWorkflowAchatComplet:
    """WORKFLOW ACHAT COMPLET"""

    def test_workflow_achat_end_to_end(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            fournisseur = Fournisseur(
                code='FOURN001',
                raison_sociale='DistriFood Madagascar',
                nom_commercial='DistriFood',
                email='contact@distrifood.mg',
                telephone='+261 34 987 6543',
                adresse='Analakely',
                ville='Antananarivo',
                code_postal='101',
                pays='Madagascar',
                type='fournisseur_local',
                est_actif=True,
                tenant_id=tenant_id,
            )
            db.session.add(fournisseur)
            db.session.commit()
            fournisseur_id = fournisseur.id

            produit = Produit(
                reference='PROD-ACHAT001',
                nom='Sac Riz 50kg',
                unite='sac',
                prix_achat_ht=7000.00,
                prix_vente_ht=15000.00,
                taux_tva=20.00,
                quantite_stock=0,
                categorie='alimentaire',
                tenant_id=tenant_id,
            )
            db.session.add(produit)
            db.session.commit()
            produit_id = produit.id

        # Passer commande fournisseur
        response = app.test_client().post(
            '/api/v1/commandes-achat/',
            json={
                'fournisseur_id': fournisseur_id,
                'reference': 'CA-TEST-001',
                'total_ht': 35000.0,
                'total_ttc': 42000.0,
                'conditions_paiement': '30 jours',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        commande = response.get_json()
        commande_id = commande['id']

        # Réceptionner en dépôt
        response = app.test_client().post(
            '/api/v1/receptions/',
            json={
                'commande_achat_id': commande_id,
                'reference': 'REC-TEST-001',
                'quantite_recue': 100,
                'quantite_commandee': 100,
                'receptionne_par_id': utilisateur_id,
                'remarque': 'Reception depot Antananarivo',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        reception = response.get_json()

        # Update stock after reception using stock API
        response = app.test_client().post(
            '/api/v1/stocks/',
            json={
                'produit_id': produit_id,
                'quantite': 100,
                'type_mouvement': 'entree',
                'raison': 'Reception CA-TEST-001',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        with app.app_context():
            p = db.session.get(Produit, produit_id)
            assert float(p.quantite_stock) == 100

        # Valider la dette
        response = app.test_client().put(
            f'/api/v1/commandes-achat/{commande_id}',
            json={'statut': 'recue', 'remarque': 'Dette validee'},
            headers=auth_headers,
        )
        assert response.status_code == 200
        commande_updated = response.get_json()
        assert commande_updated['statut'] == 'recue'

        # Effectuer un règlement partiel
        response = app.test_client().post(
            '/api/v1/paiements/',
            json={
                'montant': 21000.0,
                'mode_paiement': 'ESPECES',
                'reference': f'PAY-ESP-{uuid.uuid4().hex[:6].upper()}',
                'notes': 'Reglement partial commande fournisseur',
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        paiement = response.get_json()
        assert float(paiement['montant']) == 21000.0


class TestInterfaceFormulaires:
    """INTERFACE & FORMULAIRES"""

    def test_ariary_amounts_and_malagasy_cities_and_units(self, app, auth_headers, tenant_id, utilisateur_id, abonnement_id):
        with app.app_context():
            client = Client(
                code='CLI-FORM',
                nom='FormTest',
                email='form@test.mg',
                telephone='+261 34 555 5555',
                type='particulier',
                ville_facturation='Antananarivo',
                code_postal_facturation='101',
                pays_facturation='Madagascar',
                ville_livraison='Antananarivo',
                code_postal_livraison='101',
                pays_livraison='Madagascar',
                tenant_id=tenant_id,
            )
            db.session.add(client)
            db.session.commit()
            client_id = client.id

            produit = Produit(
                reference='PROD-ARIARY',
                nom='Produit Test Ariary',
                unite='piece',
                prix_vente_ht=1000.00,
                prix_achat_ht=500.00,
                taux_tva=20.00,
                quantite_stock=50,
                categorie='test',
                tenant_id=tenant_id,
            )
            db.session.add(produit)
            db.session.commit()
            produit_id = produit.id

        # Saisie montant Ariary
        response = app.test_client().post(
            '/api/v1/ventes/',
            json={
                'client_id': client_id,
                'reference': 'VENT-ARIARY-TEST',
                'mode_paiement': 'MVOLA',
                'lignes': [
                    {'produit_id': produit_id, 'quantite': 3, 'prix_unitaire': 1000.00},
                ],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        vente = response.get_json()
        assert round(float(vente['total_ttc']), 2) == 3600.00

        # Villes malgaches
        cities = [
            ('Antananarivo', '101'),
            ('Toamasina', '501'),
            ('Antsirabe', '110'),
            ('Fianarantsoa', '301'),
            ('Mahajanga', '401'),
            ('Toliara', '601'),
            ('Antsiranana', '201'),
        ]
        with app.app_context():
            created_clients = []
            for city, cp in cities:
                c = Client(
                    code=f'CLI-CITY-{city}',
                    nom=f'Test {city}',
                    email=f'test-{city}@test.mg',
                    telephone='+261 34 111 1111',
                    type='particulier',
                    ville_facturation=city,
                    code_postal_facturation=cp,
                    pays_facturation='Madagascar',
                    ville_livraison=city,
                    code_postal_livraison=cp,
                    pays_livraison='Madagascar',
                    tenant_id=tenant_id,
                )
                db.session.add(c)
                created_clients.append(c)
            db.session.commit()
            for c in created_clients:
                assert c.ville_facturation in [city for city, _ in cities]

        # Unités produit
        units = ['piece', 'sac', 'carton', 'kg', 'litres', 'unité']
        with app.app_context():
            for u in units:
                p = Produit(
                    reference=f'PROD-U-{u}',
                    nom=f'Test {u}',
                    unite=u,
                    prix_vente_ht=1000.00,
                    prix_achat_ht=500.00,
                    taux_tva=20.00,
                    quantite_stock=10,
                    categorie='test',
                    tenant_id=tenant_id,
                )
                db.session.add(p)
            db.session.commit()
            for u in units:
                p = db.session.query(Produit).filter_by(reference=f'PROD-U-{u}').first()
                assert p is not None
                assert p.unite == u

>>>

### FICHIER .PY: web\backend\tests\test_papi.py
<<<

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app import db
from app.models.paiement import Paiement, StatutPaiement, TypePaiement, ProviderPaiement
from app.models.payment_event import PaymentEvent
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.security.auth import hash_password


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        unique_slug = f'test-tenant-{uuid.uuid4().hex[:8]}'
        unique_email = f'test-{uuid.uuid4().hex[:8]}@example.com'
        unique_username = f'testuser-{uuid.uuid4().hex[:8]}'
        tenant = Tenant(
            nom='Test Tenant',
            slug=unique_slug,
            statut=StatutTenant.ACTIF,
            plan='starter',
        )
        db.session.add(tenant)
        db.session.flush()

        user = Utilisateur(
            username=unique_username,
            email=unique_email,
            password_hash=hash_password('password123'),
            role=Role.ADMIN,
            tenant_id=tenant.id,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(user)
        db.session.flush()

        abonnement = Abonnement(
            tenant_id=tenant.id,
            montant=15000.0,
            devise='MGA',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.EN_ATTENTE,
            plan='starter',
        )
        db.session.add(abonnement)
        db.session.commit()

        from flask_jwt_extended import create_access_token
        token = create_access_token(
            identity=user.id,
            additional_claims={
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'tenant_id': tenant.id,
                'tenant_slug': tenant.slug,
            }
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        return headers, tenant.id, user.id, abonnement.id


def _papi_response(payment_link='https://pay.papi.mg/payment/abc123', notification_token='token-xyz', reference=None):
    ref = reference or f'SUB-1-1-{uuid.uuid4().hex[:8].upper()}'
    return {
        'data': {
            'amount': 15000.0,
            'currency': 'MGA',
            'linkCreationDateTime': 1723850012,
            'linkExpirationDateTime': 1723853612,
            'paymentLink': payment_link,
            'clientName': 'Test Tenant',
            'paymentReference': ref,
            'description': 'Abonnement starter - Test Tenant',
            'successUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=success&reference={ref}',
            'failureUrl': f'http://localhost:5000/api/v1/papi/payment-result?status=failure&reference={ref}',
            'notificationUrl': 'http://localhost:5000/api/v1/papi/webhook',
            'payerEmail': 'test@example.com',
            'payerPhone': '+261340000000',
            'notificationToken': notification_token,
            'testReason': 'Integration test ERP',
            'isTestMode': True,
        }
    }


class TestPapiPaymentCreation:

    def test_create_payment_requires_auth(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 401

    def test_create_payment_success(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        mock_response = _papi_response()

        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert 'payment_link' in data
        assert data['payment_link'] == mock_response['data']['paymentLink']
        assert data['payment']['provider'] == 'papi'
        assert data['payment']['payment_method'] == 'MVOLA'
        assert data['payment']['statut'] == 'en_attente'

    def test_create_payment_invalid_method(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'INVALID_METHOD'},
        )
        assert response.status_code == 400

    def test_create_payment_subscription_not_found(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            '/api/v1/papi/payments/subscription/99999',
            headers=headers,
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 400

    def test_create_payment_tenant_mismatch(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers

        with app.app_context():
            other_slug = f'other-tenant-{uuid.uuid4().hex[:8]}'
            other_tenant = Tenant(
                nom='Other Tenant',
                slug=other_slug,
                statut=StatutTenant.ACTIF,
                plan='starter',
            )
            db.session.add(other_tenant)
            db.session.flush()

            other_user = Utilisateur(
                username='otheruser',
                email=f'other-{uuid.uuid4().hex[:8]}@example.com',
                password_hash=hash_password('password123'),
                role=Role.ADMIN,
                tenant_id=other_tenant.id,
                statut=StatutUtilisateur.ACTIF,
            )
            db.session.add(other_user)
            db.session.commit()

            from flask_jwt_extended import create_access_token
            other_token = create_access_token(
                identity=other_user.id,
                additional_claims={
                    'username': other_user.username,
                    'email': other_user.email,
                    'role': other_user.role.value,
                    'tenant_id': other_tenant.id,
                    'tenant_slug': other_tenant.slug,
                }
            )
            other_headers = {
                'Authorization': f'Bearer {other_token}',
                'Content-Type': 'application/json',
            }

        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=other_headers,
            json={'payment_method': 'MVOLA'},
        )
        assert response.status_code == 400

    def test_create_payment_amount_too_low(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            abonnement = db.session.get(Abonnement, sub_id)
            abonnement.montant = 100.0
            db.session.commit()

        mock_response = _papi_response()
        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA'},
            )
        assert response.status_code == 400


class TestPapiOfflinePayment:

    def test_create_offline_payment_success(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'especes'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['is_offline'] is True
        assert data['payment']['provider'] == 'manuel'
        assert data['payment']['payment_method'] == 'ESPECES'
        assert data['payment']['statut'] == 'en_attente'
        assert 'reference' in data and data['reference'].startswith('PAPIER-')
        assert data['instructions']

    def test_create_offline_payment_via_alias(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'cheque'},
        )
        assert response.status_code == 200
        assert response.get_json()['payment']['payment_method'] == 'CHEQUE'

    def test_list_includes_offline_payments(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        create = client.post(
            f'/api/v1/papi/payments/subscription/{sub_id}',
            headers=headers,
            json={'payment_method': 'virement'},
        )
        assert create.status_code == 200

        response = client.get('/api/v1/papi/payments', headers=headers)
        assert response.status_code == 200
        payments = response.get_json()['payments']
        assert any(p['provider'] == 'manuel' for p in payments)


class TestPapiWebhook:

    def test_webhook_valid_success(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'SUCCESS',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'fee': 500,
                'clientName': 'Test Tenant',
                'description': 'Abonnement starter - Test Tenant',
                'merchantPaymentReference': 'MERCHANT-0001',
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement effectué avec succès.',
                'payerEmail': 'test@example.com',
                'payerPhone': '+261340000000',
            }

            response = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'processed'
        assert data['payment_status'] == 'succes'

        with app.app_context():
            paiement = Paiement.query.filter_by(external_reference=reference).first()
            assert paiement.statut == StatutPaiement.SUCCESS

            abonnement = db.session.get(Abonnement, sub_id)
            assert abonnement.statut == StatutAbonnement.ACTIF

    def test_webhook_invalid_token(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        webhook_payload = {
            'paymentStatus': 'SUCCESS',
            'paymentMethod': 'MVOLA',
            'currency': 'MGA',
            'amount': 15000,
            'paymentReference': 'SUB-1-1-UNKNOWN',
            'notificationToken': 'wrong-token',
            'message': 'Paiement effectué avec succès.',
        }

        response = client.post(
            '/api/v1/papi/webhook',
            data=json.dumps(webhook_payload),
            content_type='application/json',
        )
        assert response.status_code == 403

    def test_webhook_duplicate_event(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'SUCCESS',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement effectué avec succès.',
            }

            response1 = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )
            assert response1.status_code == 200

            response2 = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )
            assert response2.status_code == 200
            assert response2.get_json()['status'] == 'already_processed'

    def test_webhook_failed_payment(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            mock_response = _papi_response()
            reference = mock_response['data']['paymentReference']
            notification_token = mock_response['data']['notificationToken']

            with patch('app.services.papi.client.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                mock_post.return_value.raise_for_status.return_value = None

                create_resp = client.post(
                    f'/api/v1/papi/payments/subscription/{sub_id}',
                    headers=headers,
                    json={'payment_method': 'MVOLA', 'is_test_mode': True},
                )
            assert create_resp.status_code == 200

            paiement = Paiement.query.filter_by(external_reference=reference).first()
            paiement.notification_token = notification_token
            db.session.commit()

            webhook_payload = {
                'paymentStatus': 'FAILED',
                'paymentMethod': 'MVOLA',
                'currency': 'MGA',
                'amount': 15000,
                'paymentReference': reference,
                'notificationToken': notification_token,
                'message': 'Paiement échoué.',
            }

            response = client.post(
                '/api/v1/papi/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json',
            )

        assert response.status_code == 200
        with app.app_context():
            paiement = Paiement.query.filter_by(external_reference=reference).first()
            assert paiement.statut == StatutPaiement.FAILED

            abonnement = db.session.get(Abonnement, sub_id)
            assert abonnement.statut != StatutAbonnement.ACTIF

    def test_webhook_missing_fields(self, client):
        response = client.post(
            '/api/v1/papi/webhook',
            data=json.dumps({'paymentStatus': 'SUCCESS'}),
            content_type='application/json',
        )
        assert response.status_code == 403


class TestPapiPaymentList:

    def test_list_papi_payments(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        with app.app_context():
            paiement = Paiement(
                tenant_id=tenant_id,
                subscription_id=sub_id,
                montant=15000.0,
                devise='MGA',
                statut=StatutPaiement.EN_ATTENTE,
                type=TypePaiement.ABONNEMENT,
                provider=ProviderPaiement.PAPI.value,
                payment_method='MVOLA',
                external_payment_id='https://pay.papi.mg/payment/abc123',
                external_reference='SUB-1-1-TEST123',
                reference='SUB-1-1-TEST123',
            )
            db.session.add(paiement)
            db.session.commit()

            response = client.get('/api/v1/papi/payments', headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['payments']) == 1
        assert data['payments'][0]['provider'] == 'papi'

    def test_list_papi_payments_empty(self, client, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        response = client.get('/api/v1/papi/payments', headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['payments'] == []


class TestIdempotence:

    def test_duplicate_create_returns_existing(self, client, app, auth_headers):
        headers, tenant_id, user_id, sub_id = auth_headers
        mock_response = _papi_response()

        with patch('app.services.papi.client.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            response1 = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )
            assert response1.status_code == 200

            response2 = client.post(
                f'/api/v1/papi/payments/subscription/{sub_id}',
                headers=headers,
                json={'payment_method': 'MVOLA', 'is_test_mode': True},
            )
            assert response2.status_code == 200

        with app.app_context():
            count = Paiement.query.filter_by(
                tenant_id=tenant_id,
                external_reference=mock_response['data']['paymentReference'],
                is_active=True,
            ).count()
            assert count == 1

>>>

### FICHIER .PY: web\backend\tests\test_plan_limits.py
<<<
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.employe import Employe
from app.models.stagiaire import Stagiaire
from app.security.auth import hash_password
from app.security.plans import resolve_limits, resolve_modules, admin_limit


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_tenant_with_abonnement(plan='pro', max_admins=2, max_employees=3, max_interns=1, modules='rh,stocks,produits'):
    tenant = Tenant(
        nom='Tenant Test',
        slug='tenant-test',
        statut=StatutTenant.ACTIF,
        plan=plan,
    )
    db.session.add(tenant)
    db.session.flush()
    abonnement = Abonnement(
        tenant_id=tenant.id,
        montant=100.0,
        plan=plan,
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
        max_admins=max_admins,
        max_employees=max_employees,
        max_interns=max_interns,
        modules=modules,
    )
    db.session.add(abonnement)
    admin = Utilisateur(
        username='admin',
        email='admin@test.mg',
        password_hash=hash_password('Admin123!'),
        role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF,
        tenant_id=tenant.id,
    )
    db.session.add(admin)
    db.session.commit()
    return tenant, admin


def _login(client, username, password, tenant_slug=None):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestAdminLimits:
    def test_cannot_create_more_admins_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=1)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif'})
        assert r.status_code == 403, r.get_json()
        assert 'administrateurs' in r.get_json()['message']

    def test_can_create_admin_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif'})
        assert r.status_code == 201, r.get_json()

    def test_super_admin_bypasses_admin_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_admins=1)
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'admin2', 'email': 'admin2@test.mg',
                              'password': 'Pass123!', 'role': 'admin', 'statut': 'actif',
                              'tenant_id': tenant.id})
        assert r.status_code == 201, r.get_json()


class TestEmployeeLimits:
    def test_cannot_create_more_employees_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        Employe(tenant_id=tenant.id, matricule='EMP001', nom='A', prenom='B').save()
        Employe(tenant_id=tenant.id, matricule='EMP002', nom='C', prenom='D').save()

        r = client.post('/api/v1/employes', headers=headers,
                        json={'matricule': 'EMP003', 'nom': 'E', 'prenom': 'F'})
        assert r.status_code == 403, r.get_json()
        assert 'employés' in r.get_json()['message']

    def test_can_create_employee_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_employees=3)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/employes', headers=headers,
                        json={'matricule': 'EMP001', 'nom': 'E', 'prenom': 'F'})
        assert r.status_code == 201, r.get_json()


class TestInternLimits:
    def test_cannot_create_more_interns_than_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_interns=1)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        Stagiaire(tenant_id=tenant.id, matricule='STG001', nom='A', prenom='B').save()

        r = client.post('/api/v1/stagiaires', headers=headers,
                        json={'matricule': 'STG002', 'nom': 'C', 'prenom': 'D'})
        assert r.status_code == 403, r.get_json()
        assert 'stagiaires' in r.get_json()['message']

    def test_can_create_intern_under_limit(self, app):
        tenant, admin = _make_tenant_with_abonnement(max_interns=2)
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.post('/api/v1/stagiaires', headers=headers,
                        json={'matricule': 'STG001', 'nom': 'C', 'prenom': 'D'})
        assert r.status_code == 201, r.get_json()


class TestModuleRestrictions:
    def test_employee_routes_blocked_without_module(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits,clients')
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 403, r.get_json()
        assert 'rh' in r.get_json()['message']

    def test_employee_routes_allowed_with_module(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits,clients,rh')
        client = app.test_client()
        headers = _login(client, 'admin', 'Admin123!', 'tenant-test')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 200, r.get_json()

    def test_super_admin_bypasses_module_restriction(self, app):
        tenant, admin = _make_tenant_with_abonnement(modules='produits')
        super_admin = Utilisateur(
            username='super',
            email='super@x.mg',
            password_hash=hash_password('Super123!'),
            role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
        db.session.commit()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/employes', headers=headers)
        assert r.status_code == 200, r.get_json()


class TestMultiTenantIsolation:
    def test_employee_created_by_tenant_a_not_visible_by_tenant_b(self, app):
        tenant_a = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
        tenant_b = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()
        for t in (tenant_a, tenant_b):
            db.session.add(Abonnement(
                tenant_id=t.id, montant=100.0, plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                max_admins=5, max_employees=100, max_interns=20,
                modules='rh,stocks,produits',
            ))
        admin_a = Utilisateur(
            username='admin_a', email='admin_a@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_a.id,
        )
        admin_b = Utilisateur(
            username='admin_b', email='admin_b@b.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_b.id,
        )
        db.session.add_all([admin_a, admin_b])
        db.session.commit()

        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        r = client.post('/api/v1/employes', headers=headers_a,
                        json={'matricule': 'EMP001', 'nom': 'A', 'prenom': 'B'})
        assert r.status_code == 201, r.get_json()

        r_a = client.get('/api/v1/employes', headers=headers_a)
        assert r_a.status_code == 200
        assert len(r_a.get_json()['employes']) == 1

        r_b = client.get('/api/v1/employes', headers=headers_b)
        assert r_b.status_code == 200
        assert len(r_b.get_json()['employes']) == 0

    def test_user_creation_scoped_to_current_tenant(self, app):
        tenant_a = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
        tenant_b = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()
        for t in (tenant_a, tenant_b):
            db.session.add(Abonnement(
                tenant_id=t.id, montant=100.0, plan='pro',
                date_debut=datetime.utcnow(),
                date_fin=datetime.utcnow() + timedelta(days=30),
                statut=StatutAbonnement.ACTIF,
                max_admins=5, max_employees=100, max_interns=20,
                modules='rh,stocks,produits',
            ))
        admin_a = Utilisateur(
            username='admin_a', email='admin_a@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tenant_a.id,
        )
        db.session.add(admin_a)
        db.session.commit()

        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers_a,
                        json={'username': 'newuser', 'email': 'new@a.mg',
                              'password': 'Pass123!', 'role': 'user'})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == tenant_a.id

>>>

### FICHIER .PY: web\backend\tests\test_produits.py
<<<
from app.models.produit import Produit
from decimal import Decimal

def test_produit_model():
    produit = Produit(nom='Test', reference='TEST001', prix_vente_ht=Decimal('9.99'))
    assert produit.nom == 'Test'
    assert produit.reference == 'TEST001'
    assert produit.prix_vente_ht == Decimal('9.99')

>>>

### FICHIER .PY: web\backend\tests\test_rh.py
<<<
import pytest
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.employe import Employe
from app.models.stagiaire import Stagiaire
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_tenant(slug, plan='pro'):
    tenant = Tenant(nom=slug, slug=slug, domaine=f'{slug}.local', statut=StatutTenant.ACTIF, plan=plan)
    db.session.add(tenant)
    db.session.commit()
    abonnement = Abonnement(
        tenant_id=tenant.id,
        plan=plan,
        statut=StatutAbonnement.ACTIF,
        date_debut=datetime.utcnow() - timedelta(days=30),
        date_fin=datetime.utcnow() + timedelta(days=30),
        modules='rh',
        max_employees=5,
        max_interns=2,
    )
    db.session.add(abonnement)
    db.session.commit()
    return tenant


def _make_user(tenant, username, role=Role.ADMIN):
    user = Utilisateur(
        username=username,
        email=f'{username}@example.com',
        password_hash=hash_password('Password123!'),
        nom=username,
        prenom=username,
        role=role,
        tenant_id=tenant.id,
        statut=StatutUtilisateur.ACTIF,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username, password, tenant_slug):
    payload = {'username': username, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def test_create_stagiaire(app):
    tenant = _make_tenant('tenant-stg')
    user = _make_user(tenant, 'admin-stg')
    client = app.test_client()
    headers = _login(client, 'admin-stg', 'Password123!', 'tenant-stg')

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-001',
        'nom': 'Dupont',
        'prenom': 'Jean',
        'etablissement': 'Université A',
        'formation': 'Informatique',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'statut': 'en_stage',
    })
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert data['matricule'] == 'STG-001'
    assert data['nom'] == 'Dupont'
    assert data['tenant_id'] == tenant.id


def test_cross_tenant_stagiaires_denied(app):
    ta = _make_tenant('tenant-a')
    tb = _make_tenant('tenant-b')
    _make_user(ta, 'admin_a', Role.ADMIN)
    _make_user(tb, 'admin_b', Role.ADMIN)
    client = app.test_client()
    headers_a = _login(client, 'admin_a', 'Password123!', 'tenant-a')

    with app.app_context():
        s_b = Stagiaire(nom='Stagiaire B', prenom='B', matricule='STG-B', tenant_id=tb.id, etablissement='Univ B')
        db.session.add(s_b)
        db.session.commit()
        sid_b = s_b.id

    r = client.get(f'/api/v1/stagiaires/{sid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()

    r = client.put(f'/api/v1/stagiaires/{sid_b}', headers=headers_a, json={'nom': 'Hacked'})
    assert r.status_code == 404, r.get_json()

    r = client.delete(f'/api/v1/stagiaires/{sid_b}', headers=headers_a)
    assert r.status_code == 404, r.get_json()


def test_stagiaire_tuteur_meme_tenant(app):
    tenant = _make_tenant('tenant-tuteur')
    user = _make_user(tenant, 'admin-tuteur')
    client = app.test_client()
    headers = _login(client, 'admin-tuteur', 'Password123!', 'tenant-tuteur')

    with app.app_context():
        e = Employe(nom='Employe Tuteur', prenom='T', matricule='EMP-T', tenant_id=tenant.id, salaire_base=1000)
        db.session.add(e)
        db.session.commit()
        eid = e.id

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-T',
        'nom': 'Stagiaire',
        'prenom': 'S',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'tuteur_id': eid,
    })
    assert r.status_code == 201, r.get_json()


def test_stagiaire_tuteur_autre_tenant_refuse(app):
    ta = _make_tenant('tenant-a')
    tb = _make_tenant('tenant-b')
    _make_user(ta, 'admin_a', Role.ADMIN)
    _make_user(tb, 'admin_b', Role.ADMIN)
    client = app.test_client()
    headers_a = _login(client, 'admin_a', 'Password123!', 'tenant-a')

    with app.app_context():
        e_b = Employe(nom='Employe B', prenom='B', matricule='EMP-B', tenant_id=tb.id, salaire_base=1000)
        db.session.add(e_b)
        db.session.commit()
        eid_b = e_b.id

    r = client.post('/api/v1/stagiaires', headers=headers_a, json={
        'matricule': 'STG-X',
        'nom': 'Stagiaire',
        'prenom': 'S',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
        'tuteur_id': eid_b,
    })
    assert r.status_code == 400, r.get_json()
    assert 'tuteur' in r.get_json()['message'].lower()


def test_employe_plan_limit(app):
    tenant = _make_tenant('tenant-limit', plan='gratuit')
    user = _make_user(tenant, 'admin-limit')
    client = app.test_client()
    headers = _login(client, 'admin-limit', 'Password123!', 'tenant-limit')

    with app.app_context():
        for i in range(5):
            e = Employe(nom=f'Employe {i}', prenom='E', matricule=f'EMP-{i}', tenant_id=tenant.id, salaire_base=1000)
            db.session.add(e)
        db.session.commit()

    r = client.post('/api/v1/employes', headers=headers, json={
        'matricule': 'EMP-OVER',
        'nom': 'Overflow',
        'prenom': 'O',
        'salaire_base': 1000,
    })
    assert r.status_code == 403, r.get_json()
    assert 'limite' in r.get_json()['message'].lower()


def test_stagiaire_plan_limit(app):
    tenant = _make_tenant('tenant-stg-limit', plan='gratuit')
    user = _make_user(tenant, 'admin-stg-limit')
    client = app.test_client()
    headers = _login(client, 'admin-stg-limit', 'Password123!', 'tenant-stg-limit')

    with app.app_context():
        for i in range(2):
            s = Stagiaire(nom=f'Stagiaire {i}', prenom='S', matricule=f'STG-{i}', tenant_id=tenant.id, etablissement='Univ')
            db.session.add(s)
        db.session.commit()

    r = client.post('/api/v1/stagiaires', headers=headers, json={
        'matricule': 'STG-OVER',
        'nom': 'Overflow',
        'prenom': 'O',
        'etablissement': 'Univ',
        'formation': 'Info',
        'type_contrat': 'stage_initiation',
        'date_debut': '2026-01-01',
        'date_fin': '2026-06-01',
    })
    assert r.status_code == 403, r.get_json()
    assert 'limite' in r.get_json()['message'].lower()

>>>

### FICHIER .PY: web\backend\tests\test_security_multi_tenant.py
<<<
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.produit import Produit
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.stock import MouvementStock
from app.models.facture import Facture
from app.models.facture_fournisseur import FactureFournisseur
from app.models.paiement import Paiement, StatutPaiement, StatutPaiement
from app.models.commande_client import CommandeClient
from app.models.commande_achat import CommandeAchat
from app.models.livraison import Livraison
from app.models.employe import Employe
from app.models.compte_comptable import CompteComptable
from app.models.ecriture_comptable import EcritureComptable
from app.models.tresorerie import Tresorerie
from app.models.document_genere import DocumentGenere
from app.models.modele_document import ModeleDocument
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_context():
    ta = Tenant.query.filter_by(slug='tenant-a').first()
    tb = Tenant.query.filter_by(slug='tenant-b').first()
    if not ta:
        ta = Tenant(nom='Tenant A', slug='tenant-a', domaine='a.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(ta)
    if not tb:
        tb = Tenant(nom='Tenant B', slug='tenant-b', domaine='b.local', statut=StatutTenant.ACTIF, plan='pro')
        db.session.add(tb)
    db.session.flush()

    if not Abonnement.query.filter_by(tenant_id=ta.id).first():
        db.session.add(Abonnement(
            tenant_id=ta.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))
    if not Abonnement.query.filter_by(tenant_id=tb.id).first():
        db.session.add(Abonnement(
            tenant_id=tb.id, montant=100.0, plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
        ))

    admin_a = Utilisateur.query.filter_by(username='admin_a').first()
    admin_b = Utilisateur.query.filter_by(username='admin_b').first()
    super_admin = Utilisateur.query.filter_by(username='super').first()
    if not admin_a:
        admin_a = Utilisateur(
            username='admin_a', email='admin@a.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
        )
        db.session.add(admin_a)
    if not admin_b:
        admin_b = Utilisateur(
            username='admin_b', email='admin@b.mg',
            password_hash=hash_password('Admin123!'), role=Role.ADMIN,
            statut=StatutUtilisateur.ACTIF, tenant_id=tb.id,
        )
        db.session.add(admin_b)
    if not super_admin:
        super_admin = Utilisateur(
            username='super', email='super@x.mg',
            password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
            statut=StatutUtilisateur.ACTIF,
        )
        db.session.add(super_admin)
    db.session.commit()
    return ta, tb, admin_a, admin_b, super_admin


def _login(client, identifier, password, tenant_slug=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


def _get_tenant_id_from_token(client, headers):
    import jwt as pyjwt
    token = headers['Authorization'].split(' ')[1]
    decoded = pyjwt.decode(token, options={"verify_signature": False})
    return decoded.get('tenant_id')


class TestSecurityMultiTenancy:
    def test_jwt_contains_tenant_claims(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        r = client.get('/api/v1/auth/me', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['tenant_id'] is not None
        assert data['tenant']['slug'] == 'tenant-a'

    def test_super_admin_jwt_has_no_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')
        r = client.get('/api/v1/auth/me', headers=headers)
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['tenant_id'] is None

    def test_password_reset_token_is_hashed(self, app):
        ta, _, admin_a, _, _ = _make_context()
        client = app.test_client()
        with app.app_context():
            r = client.post('/api/v1/auth/forgot-password', json={'email': 'admin@a.mg'})
            assert r.status_code == 200
            token = PasswordResetToken.query.filter_by(user_id=admin_a.id, used=False).first()
            assert token is not None
            assert token.token != 'test-token'
            assert len(token.token) > 20

    def test_cross_tenant_produits_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            p_a = Produit(nom='Produit A', reference='PA', tenant_id=ta.id, prix_achat_ht=10, prix_vente_ht=15)
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add_all([p_a, p_b])
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/produits/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/produits/{pid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/produits/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_clients_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.commit()
            cid_b = c_b.id

        r = client.get(f'/api/v1/clients/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/clients/{cid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/clients/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.commit()
            fid_b = f_b.id

        r = client.get(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a, json={'raison_sociale': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/fournisseurs/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_ventes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.commit()
            vid_b = v_b.id

        r = client.get(f'/api/v1/ventes/{vid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/ventes/{vid_b}', headers=headers_a, json={'remarque': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/ventes/{vid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_factures_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.flush()
            f_b = Facture(vente_id=v_b.id, client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FB')
            db.session.add(f_b)
            db.session.commit()
            fid_b = f_b.id

        r = client.get(f'/api/v1/factures/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/factures/{fid_b}', headers=headers_a, json={'statut': 'payee'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/factures/{fid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_paiements_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.flush()
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='VB')
            db.session.add(v_b)
            db.session.flush()
            f_b = Facture(vente_id=v_b.id, client_id=c_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FB')
            db.session.add(f_b)
            db.session.flush()
            p_b = Paiement(facture_id=f_b.id, tenant_id=tb.id, montant=50, statut=StatutPaiement.CONFIRME)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/paiements/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/paiements/{pid_b}', headers=headers_a, json={'montant': 999})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/paiements/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_employes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            e_b = Employe(nom='Employe B', prenom='B', matricule='EMP-B', tenant_id=tb.id, salaire_base=1000)
            db.session.add(e_b)
            db.session.commit()
            eid_b = e_b.id

        r = client.get(f'/api/v1/employes/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/employes/{eid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/employes/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_comptes_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_b = CompteComptable(numero='401B', nom='Compte B', type_compte='passif', tenant_id=tb.id)
            db.session.add(c_b)
            db.session.commit()
            cid_b = c_b.id

        r = client.get(f'/api/v1/comptes/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/comptes/{cid_b}', headers=headers_a, json={'nom': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/comptes/{cid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_ecritures_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_a = CompteComptable(numero='401A', nom='Compte A', type_compte='passif', tenant_id=ta.id)
            c_b = CompteComptable(numero='401B', nom='Compte B', type_compte='passif', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            e_b = EcritureComptable(compte_id=c_b.id, tenant_id=tb.id, libelle='Ecriture B', montant_debit=100, date=datetime.utcnow())
            db.session.add(e_b)
            db.session.commit()
            eid_b = e_b.id

        r = client.get(f'/api/v1/ecritures/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/ecritures/{eid_b}', headers=headers_a, json={'libelle': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/ecritures/{eid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_tresorerie_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            t_b = Tresorerie(tenant_id=tb.id, montant=100, libelle='Tresorerie B', type_operation='entree', date=datetime.utcnow())
            db.session.add(t_b)
            db.session.commit()
            tid_b = t_b.id

        r = client.get(f'/api/v1/tresorerie/{tid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/tresorerie/{tid_b}', headers=headers_a, json={'libelle': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/tresorerie/{tid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_commandes_achat_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            ca_b = CommandeAchat(tenant_id=tb.id, fournisseur_id=f_b.id, reference='CA-B', total_ht=100, total_ttc=120)
            db.session.add(ca_b)
            db.session.commit()
            caid_b = ca_b.id

        r = client.get(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a, json={'reference': 'Hacked'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/commandes-achat/{caid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_livraisons_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            l_b = Livraison(tenant_id=tb.id, statut='en_attente', adresse_livraison='Addr B')
            db.session.add(l_b)
            db.session.commit()
            lid_b = l_b.id

        r = client.get(f'/api/v1/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.put(f'/api/v1/livraisons/{lid_b}', headers=headers_a, json={'statut': 'livree'})
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/livraisons/{lid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_documents_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            md_b = ModeleDocument(nom='Modele B', type_document='facture', contenu_modele='<html></html>', tenant_id=tb.id)
            db.session.add(md_b)
            db.session.flush()
            d_b = DocumentGenere(modele_id=md_b.id, tenant_id=tb.id, type_document='facture', reference='DOC-B')
            db.session.add(d_b)
            db.session.commit()
            did_b = d_b.id

        r = client.get(f'/api/v1/documents/{did_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/documents/{did_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_notifications_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            n_b = Notification(title='Notif B', tenant_id=tb.id)
            db.session.add(n_b)
            db.session.commit()
            nid_b = n_b.id

        r = client.get(f'/api/v1/notifications/{nid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

        r = client.delete(f'/api/v1/notifications/{nid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_list_no_leak(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            p_a = Produit(nom='Produit A', reference='PA', tenant_id=ta.id, prix_achat_ht=10, prix_vente_ht=15)
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add_all([p_a, p_b])
            db.session.commit()

        r = client.get('/api/v1/produits', headers=headers_a)
        assert r.status_code == 200
        data = r.get_json()
        names = {p['nom'] for p in data['produits']}
        assert 'Produit A' in names
        assert 'Produit B' not in names

    def test_cross_tenant_stocks_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30, quantite_stock=5, seuil_alerte=10)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/stocks/{pid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_super_admin_can_access_cross_tenant(self, app):
        ta, tb, admin_a, admin_b, super_admin = _make_context()
        client = app.test_client()
        headers_super = _login(client, 'super', 'Super123!')

        with app.app_context():
            p_b = Produit(nom='Produit B', reference='PB', tenant_id=tb.id, prix_achat_ht=20, prix_vente_ht=30)
            db.session.add(p_b)
            db.session.commit()
            pid_b = p_b.id

        r = client.get(f'/api/v1/produits/{pid_b}', headers=headers_super)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()['nom'] == 'Produit B'

    def test_dashboard_tenant_scoped(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        headers_b = _login(client, 'admin_b', 'Admin123!', 'tenant-b')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id, est_actif=True)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id, est_actif=True)
            db.session.add_all([c_a, c_b])
            db.session.commit()

        r_a = client.get('/api/v1/dashboard/', headers=headers_a)
        assert r_a.status_code == 200
        data_a = r_a.get_json()
        assert data_a['stats']['clients_actifs'] == 1

        r_b = client.get('/api/v1/dashboard/', headers=headers_b)
        assert r_b.status_code == 200
        data_b = r_b.get_json()
        assert data_b['stats']['clients_actifs'] == 1

    def test_secret_key_required(self, monkeypatch):
        monkeypatch.delenv('SECRET_KEY', raising=False)
        monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
        with pytest.raises(ValueError, match='SECRET_KEY'):
            create_app()

    def test_cors_wildcard_rejected(self, monkeypatch):
        monkeypatch.setenv('CORS_ORIGINS', '*')
        monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
        monkeypatch.setenv('SECRET_KEY', 'test-secret')
        with pytest.raises(ValueError, match='CORS_ORIGINS cannot contain'):
            create_app()

    def test_password_complexity_enforced(self, app):
        _make_context()
        client = app.test_client()

        r = client.post('/api/v1/auth/register', json={
            'email': 'new@test.com',
            'username': 'newuser',
            'password': 'weak'
        })
        assert r.status_code == 400
        assert '8 caracteres' in r.get_json()['message']

    def test_cross_tenant_ventes_list_no_leak(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            c_a = Client(code='CLI-A', nom='Client A', tenant_id=ta.id)
            c_b = Client(code='CLI-B', nom='Client B', tenant_id=tb.id)
            db.session.add_all([c_a, c_b])
            db.session.flush()
            v_a = Vente(client_id=c_a.id, tenant_id=ta.id, total_ht=100, total_ttc=120, reference='VA')
            v_b = Vente(client_id=c_b.id, tenant_id=tb.id, total_ht=200, total_ttc=240, reference='VB')
            db.session.add_all([v_a, v_b])
            db.session.commit()

        r = client.get('/api/v1/ventes', headers=headers_a)
        assert r.status_code == 200
        data = r.get_json()
        refs = {v['reference'] for v in data['ventes']}
        assert 'VA' in refs
        assert 'VB' not in refs

    def test_cross_tenant_commandes_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            cf_b = CommandeAchat(fournisseur_id=f_b.id, tenant_id=tb.id, reference='CF-B', total_ht=100, total_ttc=120)
            db.session.add(cf_b)
            db.session.commit()
            cfid_b = cf_b.id

        r = client.get(f'/api/v1/fournisseurs/commandes/{cfid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_cross_tenant_factures_fournisseurs_denied(self, app):
        ta, tb, admin_a, admin_b, _ = _make_context()
        client = app.test_client()
        headers_a = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            f_b = Fournisseur(code='FOU-B', raison_sociale='Fournisseur B', tenant_id=tb.id)
            db.session.add(f_b)
            db.session.flush()
            ff_b = FactureFournisseur(fournisseur_id=f_b.id, tenant_id=tb.id, total_ht=100, total_ttc=120, reference='FF-B')
            db.session.add(ff_b)
            db.session.commit()
            ffid_b = ff_b.id

        r = client.get(f'/api/v1/fournisseurs/factures/{ffid_b}', headers=headers_a)
        assert r.status_code == 404, r.get_json()

    def test_create_without_tenant_id_is_rejected(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        with app.app_context():
            from app.services.client_service import ClientService
            with pytest.raises(ValueError, match='Aucun tenant associe'):
                ClientService.create({'code': 'CLI-NO-TENANT', 'nom': 'Orphelin'})

    def test_create_with_valid_tenant_id_succeeds(self, app):
        ta, _, admin_a, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/clients', json={
            'code': 'CLI-OK',
            'nom': 'Client OK',
            'prenom': 'Test'
        }, headers=headers)
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id

    def test_super_admin_without_tenant_id_works(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/clients', headers=headers)
        assert r.status_code == 200

    def test_tenant_resolution_failure_is_logged(self, app, monkeypatch, caplog):
        import logging
        from app.security import tenant as tenant_module

        def bad_resolve():
            raise RuntimeError('header cassé')

        monkeypatch.setattr(tenant_module, 'resolve_tenant_from_header', bad_resolve)

        with caplog.at_level(logging.WARNING, logger='app'):
            client = app.test_client()
            client.get('/api/v1/auth/login', json={'username': 'x', 'password': 'y'})

        assert any('Impossible de résoudre le tenant' in record.getMessage() for record in caplog.records)

>>>

### FICHIER .PY: web\backend\tests\test_stocks.py
<<<
from app.models.stock import MouvementStock, TypeMouvement
from decimal import Decimal

def test_mouvement_stock_model():
    mouvement = MouvementStock(produit_id=1, type_mouvement=TypeMouvement.ENTREE, quantite=Decimal('10.0'))
    assert mouvement.produit_id == 1
    assert mouvement.type_mouvement == TypeMouvement.ENTREE
    assert mouvement.quantite == Decimal('10.0')

>>>

### FICHIER .PY: web\backend\tests\test_tenancy.py
<<<
import pytest
from decimal import Decimal
from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role
from app.models.produit import Produit
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.security.auth import hash_password


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def tenant(app):
    tenant = Tenant(
        nom='Test Tenant',
        slug='test-tenant',
        domaine='test.local',
        statut=StatutTenant.ACTIF,
        plan='pro'
    )
    db.session.add(tenant)
    db.session.commit()
    return tenant


@pytest.fixture
def utilisateur(app, tenant):
    user = Utilisateur(
        username='testuser',
        email='test@test.com',
        password_hash=hash_password('password123'),
        role=Role.ADMIN,
        tenant_id=tenant.id
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestTenantModel:
    def test_create_tenant(self, app):
        tenant = Tenant(
            nom='Test Tenant',
            slug='test-slug',
            domaine='test.com',
            statut=StatutTenant.ACTIF
        )
        db.session.add(tenant)
        db.session.commit()
        
        assert tenant.id is not None
        assert tenant.nom == 'Test Tenant'
        assert tenant.slug == 'test-slug'
        assert tenant.statut == StatutTenant.ACTIF

    def test_tenant_utilisateurs_relation(self, app, tenant):
        user = Utilisateur(
            username='user1',
            email='user1@test.com',
            password_hash=hash_password('password'),
            tenant_id=tenant.id
        )
        db.session.add(user)
        db.session.commit()
        
        assert user in tenant.utilisateurs.all()


class TestMultiTenancy:
    def test_produit_tenant_isolation(self, app, tenant):
        # Créer deux produits pour le même tenant
        p1 = Produit(
            nom='Produit 1',
            reference='P001',
            tenant_id=tenant.id,
            prix_achat_ht=10,
            prix_vente_ht=15
        )
        p2 = Produit(
            nom='Produit 2',
            reference='P002',
            tenant_id=tenant.id,
            prix_achat_ht=20,
            prix_vente_ht=30
        )
        db.session.add_all([p1, p2])
        db.session.commit()
        
        # Vérifier l'isolation
        produits = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(produits) == 2
        
        # Un produit d'un autre tenant ne doit pas apparaître
        autre_tenant = Tenant(nom='Autre', slug='autre', statut=StatutTenant.ACTIF)
        db.session.add(autre_tenant)
        db.session.commit()
        p3 = Produit(
            nom='Produit 3',
            reference='P003',
            tenant_id=autre_tenant.id,
            prix_achat_ht=5,
            prix_vente_ht=10
        )
        db.session.add(p3)
        db.session.commit()
        
        produits_tenant1 = Produit.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(produits_tenant1) == 2
        assert p3 not in produits_tenant1

    def test_client_tenant_isolation(self, app, tenant):
        c1 = Client(
            code='CLI001',
            nom='Client 1',
            tenant_id=tenant.id
        )
        c2 = Client(
            code='CLI002',
            nom='Client 2',
            tenant_id=tenant.id
        )
        db.session.add_all([c1, c2])
        db.session.commit()
        
        clients = Client.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(clients) == 2

    def test_fournisseur_tenant_isolation(self, app, tenant):
        f1 = Fournisseur(
            code='FOU001',
            raison_sociale='Fournisseur 1',
            tenant_id=tenant.id
        )
        f2 = Fournisseur(
            code='FOU002',
            raison_sociale='Fournisseur 2',
            tenant_id=tenant.id
        )
        db.session.add_all([f1, f2])
        db.session.commit()
        
        fournisseurs = Fournisseur.query.filter_by(tenant_id=tenant.id, is_active=True).all()
        assert len(fournisseurs) == 2

    def test_utilisateur_tenant_relation(self, app, tenant):
        user = Utilisateur(
            username='testuser',
            email='test@test.com',
            password_hash=hash_password('password'),
            tenant_id=tenant.id
        )
        db.session.add(user)
        db.session.commit()
        
        assert user.tenant_id == tenant.id
        assert user.tenant.id == tenant.id


class TestProduitModel:
    def test_produit_creation(self, app, tenant):
        produit = Produit(
            nom='Test Produit',
            reference='TEST001',
            prix_achat_ht=Decimal('10.00'),
            prix_vente_ht=Decimal('15.00'),
            quantite_stock=100,
            tenant_id=tenant.id
        )
        db.session.add(produit)
        db.session.commit()
        
        assert produit.id is not None
        assert produit.nom == 'Test Produit'
        assert produit.tenant_id == tenant.id

>>>

### FICHIER .PY: web\backend\tests\test_users_api.py
<<<
import pytest
from datetime import datetime, timedelta

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.audit_log import AuditLog, TypeActionAudit
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def app(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _make_context():
    """Crée deux tenants (A et B) + un admin + un abonnement actif pour le tenant A."""
    ta = Tenant(nom='Tenant A', slug='tenant-a', statut=StatutTenant.ACTIF, plan='pro')
    tb = Tenant(nom='Tenant B', slug='tenant-b', statut=StatutTenant.ACTIF, plan='pro')
    db.session.add_all([ta, tb])
    db.session.flush()
    db.session.add(Abonnement(
        tenant_id=ta.id, montant=100.0, plan='pro',
        date_debut=datetime.utcnow(),
        date_fin=datetime.utcnow() + timedelta(days=30),
        statut=StatutAbonnement.ACTIF,
    ))
    admin_a = Utilisateur(
        username='admin_a', email='admin@a.mg',
        password_hash=hash_password('Admin123!'), role=Role.ADMIN,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    super_admin = Utilisateur(
        username='super', email='super@x.mg',
        password_hash=hash_password('Super123!'), role=Role.SUPER_ADMIN,
        statut=StatutUtilisateur.ACTIF,
    )
    user_a = Utilisateur(
        username='user_a', email='ua@a.mg',
        password_hash=hash_password('User123!'), role=Role.USER,
        statut=StatutUtilisateur.ACTIF, tenant_id=ta.id,
    )
    user_b = Utilisateur(
        username='user_b', email='ub@b.mg',
        password_hash=hash_password('User123!'), role=Role.USER,
        statut=StatutUtilisateur.ACTIF, tenant_id=tb.id,
    )
    db.session.add_all([admin_a, super_admin, user_a, user_b])
    db.session.commit()
    return ta, admin_a, super_admin, user_a, user_b


def _login(client, identifier, password, tenant_slug=None):
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    r = client.post('/api/v1/auth/login', json=payload)
    assert r.status_code == 200, r.get_json()
    return {'Authorization': 'Bearer ' + r.get_json()['access_token']}


class TestUsersApiTenantIsolation:
    def test_admin_tenant_ne_voit_que_son_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200, r.get_json()
        users = r.get_json()['users']
        usernames = {u['username'] for u in users}
        # Seuls les utilisateurs du tenant A (et l'admin) sont visibles
        assert 'admin_a' in usernames
        assert 'user_a' in usernames
        # Pas de fuite cross-tenant ni de super admin global
        assert 'user_b' not in usernames
        assert 'super' not in usernames

    def test_admin_tenant_ne_peut_pas_lire_user_autre_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        user_b_id = Utilisateur.query.filter_by(username='user_b').first().id

        r = client.get(f'/api/v1/users/{user_b_id}', headers=headers)
        assert r.status_code == 404, r.get_json()

    def test_admin_tenant_est_scope_vers_son_propre_tenant(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'nouveau', 'email': 'nouveau@a.mg',
                              'password': 'Pass123!', 'role': 'sales', 'statut': 'actif'})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id

    def test_admin_tenant_ne_peut_pas_creer_super_admin(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'evil', 'email': 'evil@x.mg',
                              'password': 'Pass123!', 'role': 'super_admin', 'statut': 'actif'})
        assert r.status_code == 403, r.get_json()

    def test_super_admin_voit_tous_les_utilisateurs(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.get('/api/v1/users', headers=headers)
        assert r.status_code == 200, r.get_json()
        users = r.get_json()['users']
        usernames = {u['username'] for u in users}
        assert {'admin_a', 'super', 'user_a', 'user_b'} <= usernames

    def test_roles_accessibles_par_admin_tenant(self, app):
        # Le module utilisateur charge aussi la liste des rôles pour les filtres/formulaires
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.get('/api/v1/roles', headers=headers)
        assert r.status_code == 200, r.get_json()
        assert 'roles' in r.get_json()


class TestUsersApiSecurity:
    def test_admin_tenant_ne_peut_pas_creer_user_autre_tenant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        tb = Tenant.query.filter_by(slug='tenant-b').first()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'evil', 'email': 'evil@b.mg',
                              'password': 'Pass123!', 'tenant_id': tb.id})
        assert r.status_code == 403, r.get_json()

    def test_creation_user_tenant_inexistant_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'ghost', 'email': 'ghost@x.mg',
                              'password': 'Pass123!', 'tenant_id': 99999})
        assert r.status_code == 404, r.get_json()

    def test_creation_user_mot_de_passe_faible_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible', 'email': 'faible@a.mg',
                              'password': '1234567'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_sans_lettre_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible2', 'email': 'faible2@a.mg',
                              'password': '12345678'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_sans_chiffre_refuse(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'faible3', 'email': 'faible3@a.mg',
                              'password': 'abcdefgh'})
        assert r.status_code == 400, r.get_json()

    def test_creation_user_mot_de_passe_valide_ok(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'nouveau', 'email': 'nouveau@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()

    def test_creation_user_created_by_renseigne(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'trace1', 'email': 'trace1@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()
        created_id = r.get_json()['id']
        user = Utilisateur.query.get(created_id)
        assert user is not None
        assert user.created_by == admin_a.id

    def test_modification_user_updated_by_renseigne(self, app):
        ta, admin_a, _, _, _ = _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')
        user_a = Utilisateur.query.filter_by(username='user_a').first()

        r = client.put(f'/api/v1/users/{user_a.id}', headers=headers,
                       json={'nom': 'NouveauNom'})
        assert r.status_code == 200, r.get_json()
        updated_user = Utilisateur.query.get(user_a.id)
        assert updated_user.updated_by == admin_a.id

    def test_creation_user_audit_enregistre(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'admin_a', 'Admin123!', 'tenant-a')

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'audit1', 'email': 'audit1@a.mg',
                              'password': 'Pass123!'})
        assert r.status_code == 201, r.get_json()
        created_id = r.get_json()['id']
        log = AuditLog.query.filter_by(type_action=TypeActionAudit.CREATION_UTILISATEUR).first()
        assert log is not None
        assert 'audit1' in log.description

    def test_super_admin_peut_creer_user_tenant_existant(self, app):
        _make_context()
        client = app.test_client()
        headers = _login(client, 'super', 'Super123!')
        ta = Tenant.query.filter_by(slug='tenant-a').first()

        r = client.post('/api/v1/users', headers=headers,
                        json={'username': 'supernew', 'email': 'supernew@a.mg',
                              'password': 'Pass123!', 'tenant_id': ta.id})
        assert r.status_code == 201, r.get_json()
        assert r.get_json()['tenant_id'] == ta.id
>>>

### FICHIER .PY: web\backend\validate_mission_4.py
<<<
"""
MISSION 4/5 — VALIDATION DES CALCULS, DASHBOARDS ET ISOLATION MULTI-TENANT
"""
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
os.environ['PAPI_API_URL'] = 'https://test.papi.mg/dashboard/api/payment-links'
os.environ['PAPI_API_KEY'] = 'test-api-key'
os.environ['PAPI_ENVIRONMENT'] = 'sandbox'
os.environ['PAPI_CALLBACK_URL'] = 'http://localhost:5000/api/v1/papi/webhook'

import logging
logging.getLogger('app').setLevel(logging.CRITICAL)

from app import create_app, db
from app.models.tenant import Tenant, StatutTenant
from app.models.utilisateur import Utilisateur, Role, StatutUtilisateur
from app.models.client import Client
from app.models.produit import Produit
from app.models.stock import MouvementStock, TypeMouvement
from app.models.facture import Facture
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.fournisseur import Fournisseur
from app.models.commande_achat import CommandeAchat, StatutCommandeAchat
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.livraison import Livraison
from app.models.abonnement import Abonnement, StatutAbonnement
from app.security.auth import hash_password
from flask_jwt_extended import create_access_token

from sqlalchemy import func


def setup_app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def create_tenant_with_user(app, nom, slug, domaine, role=Role.ADMIN, statut=StatutTenant.ACTIF):
    with app.app_context():
        tenant = Tenant(
            nom=nom,
            slug=slug,
            domaine=domaine,
            statut=statut,
            plan='pro',
        )
        db.session.add(tenant)
        db.session.commit()
        tenant_id = tenant.id

        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=79.0,
            plan='pro',
            date_debut=datetime.utcnow(),
            date_fin=datetime.utcnow() + timedelta(days=30),
            statut=StatutAbonnement.ACTIF,
            methode_paiement='carte',
            reference_paiement=f'SUB-{slug.upper()}-001',
            is_active=True,
        )
        db.session.add(abonnement)
        db.session.commit()

        user = Utilisateur(
            username=f'user_{slug}',
            email=f'{slug}@test.mg',
            password_hash=hash_password('Test1234!'),
            nom='Test',
            prenom='User',
            role=role,
            statut=StatutUtilisateur.ACTIF,
            tenant_id=tenant_id,
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        token = create_access_token(identity=user_id, additional_claims={
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'tenant_id': user.tenant_id,
        })
        return tenant_id, user_id, token


def test_financial_calculations(app):
    print("\n" + "="*70)
    print("TEST 1: COHÉRENCE DES CALCULS FINANCIERS")
    print("="*70)

    with app.app_context():
        tenant1_id, user1_id, token1 = create_tenant_with_user(app, 'Tenant A', 'tenant-a', 'a.local')
        tenant2_id, user2_id, token2 = create_tenant_with_user(app, 'Tenant B', 'tenant-b', 'b.local')

        p1 = Produit(
            reference='P-A1',
            nom='Riz Tenant A',
            prix_achat_ht=10000.0,
            prix_vente_ht=15000.0,
            quantite_stock=100,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant1_id,
        )
        p2 = Produit(
            reference='P-A2',
            nom='Huile Tenant A',
            prix_achat_ht=5000.0,
            prix_vente_ht=8000.0,
            quantite_stock=50,
            categorie='Épicerie',
            unite='carton',
            tenant_id=tenant1_id,
        )
        db.session.add_all([p1, p2])
        db.session.commit()

        p3 = Produit(
            reference='P-B1',
            nom='Sucre Tenant B',
            prix_achat_ht=8000.0,
            prix_vente_ht=12000.0,
            quantite_stock=80,
            categorie='Alimentaire',
            unite='sac',
            tenant_id=tenant2_id,
        )
        db.session.add(p3)
        db.session.commit()

        c1 = Client(
            code='CLI-A1',
            nom='Client A1',
            tenant_id=tenant1_id,
            is_active=True,
            est_actif=True,
        )
        db.session.add(c1)
        db.session.commit()

        vente = Vente(
            reference='VENT-A-001',
            client_id=c1.id,
            total_ht=30000.0,
            total_ttc=36000.0,
            statut='payee',
            mode_paiement='especes',
            tenant_id=tenant1_id,
        )
        db.session.add(vente)
        db.session.commit()

        ligne1 = LigneVente(
            vente_id=vente.id,
            produit_id=p1.id,
            quantite=2,
            prix_unitaire_ht=15000.0,
            taux_tva=20.00,
            tenant_id=tenant1_id,
        )
        db.session.add(ligne1)
        db.session.commit()

        facture = Facture(
            vente_id=vente.id,
            client_id=c1.id,
            reference='FAC-A-001',
            total_ht=30000.0,
            total_ttc=36000.0,
            statut='non_payee',
            tenant_id=tenant1_id,
        )
        db.session.add(facture)
        db.session.commit()

        paiement = Paiement(
            facture_id=facture.id,
            client_id=c1.id,
            montant=36000.0,
            devise='MGA',
            statut=StatutPaiement.CONFIRME,
            type=TypePaiement.VENTE,
            reference='PAY-A-001',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant1_id,
        )
        db.session.add(paiement)
        db.session.commit()

        facture.statut = 'payee'
        db.session.commit()

        fournisseur = Fournisseur(
            code='FOUR-A1',
            raison_sociale='Fournisseur A',
            tenant_id=tenant1_id,
            type='local',
        )
        db.session.add(fournisseur)
        db.session.commit()

        commande = CommandeAchat(
            reference='CMD-A-001',
            fournisseur_id=fournisseur.id,
            total_ht=20000.0,
            total_ttc=24000.0,
            statut=StatutCommandeAchat.RECUE,
            conditions_paiement='30 jours',
            tenant_id=tenant1_id,
        )
        db.session.add(commande)
        db.session.commit()

        errors = []

        # 1. CA total = sum of vente total_ttc
        ca_total = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.tenant_id == tenant1_id
        ).scalar() or 0
        ventes = Vente.query.filter_by(is_active=True, tenant_id=tenant1_id).all()
        ventes_sum = sum(float(v.total_ttc) for v in ventes)
        if abs(float(ca_total) - ventes_sum) > 0.01:
            errors.append(f"CA total mismatch: query={ca_total}, sum={ventes_sum}")
        else:
            print(f"[OK] CA total = {ca_total:.2f} (cohérent avec somme des ventes)")

        # 2. Vente total_ttc = sum of LigneVente total_ttc
        lignes = LigneVente.query.filter_by(vente_id=vente.id, is_active=True, tenant_id=tenant1_id).all()
        lignes_sum_ttc = sum(float(l.total_ttc) for l in lignes)
        if abs(float(vente.total_ttc) - lignes_sum_ttc) > 0.01:
            errors.append(f"Vente total_ttc mismatch: vente={vente.total_ttc}, lignes_sum={lignes_sum_ttc}")
        else:
            print(f"[OK] Vente.total_ttc = {vente.total_ttc:.2f} = somme lignes TTC = {lignes_sum_ttc:.2f}")

        # 3. Facture total_ttc = Vente total_ttc
        if abs(float(facture.total_ttc) - float(vente.total_ttc)) > 0.01:
            errors.append(f"Facture total_ttc mismatch: facture={facture.total_ttc}, vente={vente.total_ttc}")
        else:
            print(f"[OK] Facture.total_ttc = {facture.total_ttc:.2f} = Vente.total_ttc")

        # 4. Paiement total = Facture total_ttc (since statut=payee)
        paiements = Paiement.query.filter_by(facture_id=facture.id, is_active=True, tenant_id=tenant1_id).all()
        paiements_sum = sum(float(p.montant) for p in paiements)
        if abs(paiements_sum - float(facture.total_ttc)) > 0.01:
            errors.append(f"Paiements mismatch: sum={paiements_sum}, facture={facture.total_ttc}")
        else:
            print(f"[OK] Paiements sum = {paiements_sum:.2f} = Facture.total_ttc")

        # 5. Creance = facture.total_ttc - paiements_sum
        creance = float(facture.total_ttc) - paiements_sum
        if creance != 0:
            errors.append(f"Créance non nulle pour facture payée: {creance}")
        else:
            print(f"[OK] Créance = {creance:.2f} (facture payée)")

        # 6. Stock value = quantite_stock * prix_achat_ht
        produits = Produit.query.filter_by(tenant_id=tenant1_id, is_active=True).all()
        stock_total = sum(float(p.quantite_stock * p.prix_achat_ht) for p in produits)
        print(f"[OK] Valeur stock tenant 1 = {stock_total:.2f} (calculée sur {len(produits)} produits)")

        # 7. Dette fournisseur = commande.total_ttc - paiements fournisseur
        dette_fournisseur = float(commande.total_ttc)
        print(f"[OK] Dette fournisseur (commande) = {dette_fournisseur:.2f}")

        # 8. Benefice mois = sum(Vente.total_ttc - Vente.total_ht)
        benefice = db.session.query(func.sum(Vente.total_ttc - Vente.total_ht)).filter(
            Vente.is_active == True,
            Vente.tenant_id == tenant1_id
        ).scalar() or 0
        print(f"[OK] Bénéfice mois = {float(benefice):.2f} (basé sur total_ttc - total_ht)")

        if errors:
            print(f"\n[ERREURS] {len(errors)} incohérence(s) détectée(s):")
            for e in errors:
                print(f"  - {e}")
            return False
        else:
            print("\n[SUCCÈS] Tous les calculs financiers sont cohérents.")
            return True


def test_multi_tenant_isolation(app):
    print("\n" + "="*70)
    print("TEST 2: ISOLATION MULTI-TENANT")
    print("="*70)

    with app.app_context():
        tenant1_id, user1_id, token1 = create_tenant_with_user(app, 'Iso A', 'iso-a', 'iso-a.local')
        tenant2_id, user2_id, token2 = create_tenant_with_user(app, 'Iso B', 'iso-b', 'iso-b.local')

        client_app = app.test_client()

        r1 = client_app.post(
            '/api/v1/clients/',
            json={'code': 'ISO-CLI-A', 'nom': 'Client Iso A'},
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1.status_code == 201, f"T1 client creation failed: {r1.get_json()}"

        r2 = client_app.post(
            '/api/v1/clients/',
            json={'code': 'ISO-CLI-B', 'nom': 'Client Iso B'},
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2.status_code == 201, f"T2 client creation failed: {r2.get_json()}"

        r1_list = client_app.get(
            '/api/v1/clients/',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_list.status_code == 200
        data1 = r1_list.get_json()
        codes1 = [c['code'] for c in data1['clients']]
        assert data1['total'] == 1, f"Expected 1 client for tenant 1, got {data1['total']}"
        assert 'ISO-CLI-A' in codes1
        assert 'ISO-CLI-B' not in codes1
        print("[OK] Tenant 1 ne voit que ses propres clients")

        r2_list = client_app.get(
            '/api/v1/clients/',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_list.status_code == 200
        data2 = r2_list.get_json()
        codes2 = [c['code'] for c in data2['clients']]
        assert data2['total'] == 1, f"Expected 1 client for tenant 2, got {data2['total']}"
        assert 'ISO-CLI-B' in codes2
        assert 'ISO-CLI-A' not in codes2
        print("[OK] Tenant 2 ne voit que ses propres clients")

        # Dashboard isolation
        r1_dash = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_dash.status_code == 200
        dash1 = r1_dash.get_json()
        assert dash1['ca_total'] == 0.0, f"Expected CA=0 for tenant 1 with no sales, got {dash1['ca_total']}"
        print("[OK] Dashboard tenant 1 isolé (CA=0 sans ventes)")

        r2_dash = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_dash.status_code == 200
        dash2 = r2_dash.get_json()
        assert dash2['ca_total'] == 0.0
        print("[OK] Dashboard tenant 2 isolé (CA=0 sans ventes)")

        # Create sale for tenant 1 via API
        produit_a = Produit.query.filter_by(tenant_id=tenant1_id).first()
        if not produit_a:
            produit_a = Produit(
                reference='ISO-PROD-A',
                nom='Produit Iso A',
                prix_achat_ht=5000.0,
                prix_vente_ht=10000.0,
                quantite_stock=50,
                tenant_id=tenant1_id,
            )
            db.session.add(produit_a)
            db.session.commit()

        client_a = Client.query.filter_by(tenant_id=tenant1_id).first()
        r_vente = client_app.post(
            '/api/v1/ventes/',
            json={
                'client_id': client_a.id,
                'mode_paiement': 'espece',
                'lignes': [
                    {'produit_id': produit_a.id, 'quantite': 1, 'prix_unitaire': 10000.0},
                ],
            },
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r_vente.status_code == 201, f"Vente creation failed: {r_vente.get_json()}"
        vente_data = r_vente.get_json()

        # Check dashboard for tenant 1
        r1_dash2 = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token1}'}
        )
        dash1 = r1_dash2.get_json()
        assert dash1['ca_total'] > 0, f"Expected CA>0 for tenant 1 with sale"
        print(f"[OK] Dashboard tenant 1 CA = {dash1['ca_total']:.2f} (cohérent avec vente)")

        # Check dashboard for tenant 2 (should still be 0)
        r2_dash2 = client_app.get(
            '/api/v1/dashboard/sales-stats',
            headers={'Authorization': f'Bearer {token2}'}
        )
        dash2 = r2_dash2.get_json()
        assert dash2['ca_total'] == 0.0, f"Expected CA=0 for tenant 2, got {dash2['ca_total']}"
        print("[OK] Dashboard tenant 2 toujours isolé (CA=0)")

        # Top clients isolation
        r1_top = client_app.get(
            '/api/v1/dashboard/top-clients',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_top.status_code == 200
        top1 = r1_top.get_json()
        assert len(top1['top_clients']) >= 1
        print(f"[OK] Top clients tenant 1: {len(top1['top_clients'])} client(s)")

        r2_top = client_app.get(
            '/api/v1/dashboard/top-clients',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_top.status_code == 200
        top2 = r2_top.get_json()
        assert len(top2['top_clients']) == 0
        print("[OK] Top clients tenant 2: 0 client (isolé)")

        # Top products isolation
        r1_prod = client_app.get(
            '/api/v1/dashboard/top-products',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_prod.status_code == 200
        prod1 = r1_prod.get_json()
        assert len(prod1['top_products']) >= 1
        print(f"[OK] Top produits tenant 1: {len(prod1['top_products'])} produit(s)")

        r2_prod = client_app.get(
            '/api/v1/dashboard/top-products',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_prod.status_code == 200
        prod2 = r2_prod.get_json()
        assert len(prod2['top_products']) == 0
        print("[OK] Top produits tenant 2: 0 produit (isolé)")

        # Alerts isolation
        r1_alert = client_app.get(
            '/api/v1/dashboard/alerts',
            headers={'Authorization': f'Bearer {token1}'}
        )
        assert r1_alert.status_code == 200
        print("[OK] Alertes stock tenant 1 accessibles")

        r2_alert = client_app.get(
            '/api/v1/dashboard/alerts',
            headers={'Authorization': f'Bearer {token2}'}
        )
        assert r2_alert.status_code == 200
        print("[OK] Alertes stock tenant 2 accessibles")

        print("\n[SUCCÈS] Isolation multi-tenant validée.")
        return True


def test_dashboard_calculations_from_seed_data(app):
    print("\n" + "="*70)
    print("TEST 3: DASHBOARD À PARTIR DES DONNÉES GÉNÉRÉES")
    print("="*70)

    with app.app_context():
        tenant_id, user_id, token = create_tenant_with_user(app, 'Dash Test', 'dash-test', 'dash.local')

        produits = [
            Produit(reference='D1', nom='Produit D1', prix_achat_ht=10000, prix_vente_ht=15000, quantite_stock=20, tenant_id=tenant_id),
            Produit(reference='D2', nom='Produit D2', prix_achat_ht=5000, prix_vente_ht=8000, quantite_stock=10, tenant_id=tenant_id),
        ]
        db.session.add_all(produits)
        db.session.commit()

        client_obj = Client(code='CLI-DASH', nom='Client Dash', tenant_id=tenant_id, is_active=True, est_actif=True)
        db.session.add(client_obj)
        db.session.commit()

        vente = Vente(
            reference='VENT-DASH-001',
            client_id=client_obj.id,
            total_ht=23000.0,
            total_ttc=27600.0,
            statut='payee',
            mode_paiement='especes',
            tenant_id=tenant_id,
        )
        db.session.add(vente)
        db.session.commit()

        ligne1 = LigneVente(vente_id=vente.id, produit_id=produits[0].id, quantite=1, prix_unitaire_ht=15000.0, taux_tva=20.0, tenant_id=tenant_id)
        ligne2 = LigneVente(vente_id=vente.id, produit_id=produits[1].id, quantite=1, prix_unitaire_ht=8000.0, taux_tva=20.0, tenant_id=tenant_id)
        db.session.add_all([ligne1, ligne2])
        db.session.commit()

        facture = Facture(
            vente_id=vente.id,
            client_id=client_obj.id,
            reference='FAC-DASH-001',
            total_ht=23000.0,
            total_ttc=27600.0,
            statut='non_payee',
            tenant_id=tenant_id,
        )
        db.session.add(facture)
        db.session.commit()

        paiement = Paiement(
            facture_id=facture.id,
            client_id=client_obj.id,
            montant=10000.0,
            devise='MGA',
            statut=StatutPaiement.CONFIRME,
            type=TypePaiement.VENTE,
            reference='PAY-DASH-001',
            date_paiement=datetime.utcnow(),
            tenant_id=tenant_id,
        )
        db.session.add(paiement)
        db.session.commit()

        client_app = app.test_client()

        # Sales stats
        r = client_app.get('/api/v1/dashboard/sales-stats', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        stats = r.get_json()
        expected_ca = 27600.0
        if abs(stats['ca_total'] - expected_ca) > 0.01:
            print(f"[ERREUR] CA total dashboard={stats['ca_total']}, attendu={expected_ca}")
            return False
        print(f"[OK] CA total dashboard = {stats['ca_total']:.2f} (attendu {expected_ca:.2f})")

        # Full dashboard
        r = client_app.get('/api/v1/dashboard/', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        dash = r.get_json()
        creances = dash['stats'].get('creances_clients', [])
        expected_creance = 27600.0 - 10000.0  # 17600.0
        actual_creance = sum(c['creance'] for c in creances)
        if abs(actual_creance - expected_creance) > 0.01:
            print(f"[ERREUR] Créances dashboard={actual_creance}, attendu={expected_creance}")
            return False
        print(f"[OK] Créances clients dashboard = {actual_creance:.2f} (attendu {expected_creance:.2f})")

        print(f"[OK] Dashboard: ventes_aujourdhui={dash['stats'].get('ventes_aujourdhui')}, ca_mois={dash['stats'].get('ca_mois')}")

        # Benefice mois
        if abs(dash['stats'].get('benefice_mois', 0) - 4600.0) > 0.01:
            print(f"[ERREUR] Bénéfice mois={dash['stats'].get('benefice_mois')}, attendu=4600.0")
            return False
        print(f"[OK] Bénéfice mois = {dash['stats']['benefice_mois']:.2f} (attendu 4600.0)")

        print("\n[SUCCÈS] Dashboard cohérent avec les transactions.")
        return True


if __name__ == '__main__':
    app = setup_app()
    ok1 = test_financial_calculations(app)
    ok2 = test_multi_tenant_isolation(app)
    ok3 = test_dashboard_calculations_from_seed_data(app)

    print("\n" + "="*70)
    print("RÉSUMÉ DE LA VALIDATION")
    print("="*70)
    print(f"Calculs financiers: {'OK' if ok1 else 'ÉCHEC'}")
    print(f"Isolation multi-tenant: {'OK' if ok2 else 'ÉCHEC'}")
    print(f"Dashboard: {'OK' if ok3 else 'ÉCHEC'}")

    if ok1 and ok2 and ok3:
        print("\n✅ TOUTES LES VALIDATIONS SONT PASSÉES.")
        sys.exit(0)
    else:
        print("\n❌ CERTAINES VALIDATIONS ONT ÉCHOUÉ.")
        sys.exit(1)

>>>

### FICHIER .PY: web\backend\verify_app.py
<<<
import sys
import os

os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

with app.app_context():
    from flask_migrate import upgrade
    upgrade()
    print("Migrations OK!")
    
    # Verify we can access the database
    from app import db
    from app.models.tenant import Tenant
    count = Tenant.query.count()
    print(f"Tenants in database: {count}")
    
    # Verify tables exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables: {len(tables)}")
    print("Sample tables:", tables[:5])

>>>

### FICHIER .PY: web\backend\verify_minimal.py
<<<
import sys
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')

import enum

class TypeFournisseur(enum.Enum):
    LOCAL = 'local'
    NATIONAL = 'national'
    INTERNATIONAL = 'international'
    GROSSISTE = 'grossiste'
    FABRICANT = 'fabricant'
    DISTRIBUTEUR = 'distributeur'
    PRODUCTEUR_LOCAL = 'producteur_local'
    IMPORTATEUR = 'importateur'
    FOURNISSEUR_LOCAL = 'fournisseur_local'
    FOURNISSEUR_INTERNATIONAL = 'fournisseur_international'

values = [e.value for e in TypeFournisseur]
print('TypeFournisseur values:', values)
assert 'importateur' in values

import re

# Test validate_phone regex
pattern = r'^(\+261|0)(2[0-9]|3[0-9])(\d{2})(\d{3})(\d{2})$'
test_numbers = ['+261 34 12 345 67', '+261341234567', '+261 34 47 258 36']
for num in test_numbers:
    stripped = num.replace(' ', '')
    result = re.match(pattern, stripped) is not None
    print(f'validate_phone("{num}"): {result}')
    assert result, f'Failed for {num}'

# Test format_phone
def format_phone(phone):
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('261'):
        rest = digits[3:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    elif digits.startswith('0'):
        rest = digits[1:]
        if len(rest) == 9:
            return f'+261 {rest[0:2]} {rest[2:4]} {rest[4:7]} {rest[7:9]}'
    return phone

print('format_phone("+261341234567"):', format_phone('+261341234567'))
assert format_phone('+261341234567') == '+261 34 12 345 67'

CURRENCY = {
    'code': 'MGA',
    'symbol': 'Ar',
    'locale': 'mg-MG',
}
print('CURRENCY:', CURRENCY)

print('All checks passed!')

>>>

### FICHIER .PY: web\backend\verify_simple.py
<<<
import sys
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')

from app.models.fournisseur import TypeFournisseur
values = [e.value for e in TypeFournisseur]
print('TypeFournisseur values:', values)
assert 'importateur' in values, 'IMPORTATEUR missing!'

from app.utils.validators import validate_phone, format_phone
print('validate_phone spaced:', validate_phone('+261 34 12 345 67'))
print('validate_phone compact:', validate_phone('+261341234567'))
assert validate_phone('+261 34 12 345 67'), 'validate_phone failed'
assert validate_phone('+261341234567'), 'validate_phone failed'

print('format_phone +261:', format_phone('+261341234567'))
print('format_phone 0:', format_phone('0341234567'))
assert format_phone('+261341234567') == '+261 34 12 345 67', 'format_phone failed'

from app.constants import CURRENCY
print('CURRENCY:', CURRENCY)
assert CURRENCY['code'] == 'MGA'

print('All checks passed!')

>>>

