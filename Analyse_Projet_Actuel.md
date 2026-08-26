# Analyse du Projet MIHAJA_ERP_PRO

## Vue d'ensemble

**MIHAJA_ERP_PRO** est un système ERP (Enterprise Resource Planning) multi-locataire complet conçu pour les entreprises à Madagascar. Il gère l'ensemble des processus commerciaux : ventes, stocks, comptabilité, ressources humaines, livraisons et achats.

---

## Architecture Technique

### Stack Technologique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Flask 2.3.3 + Flask-RESTx 1.1.0 |
| **ORM** | SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1 |
| **Base de données** | SQLite (dev) / PostgreSQL (prod) |
| **Cache/Queue** | Redis 7 + Celery 5.3 |
| **Frontend Web** | React 18.3 + React Router DOM 7 |
| **Desktop** | Electron 38.8 + React 18 |
| **Super Admin** | React 18.3 + Chart.js 4 |
| **Authentification** | JWT (Flask-JWT-Extended) + bcrypt |
| **Validation** | Marshmallow 3.2 + Yup 1.7 |
| **Tests** | pytest 7.4 + Factory-Boy + Faker |

---

## Structure du Projet

```
MIHAJA_ERP_PRO/
├── web/
│   ├── backend/          # API Flask (22 namespaces REST)
│   │   ├── app/
│   │   │   ├── api/v1/   # 22 namespaces REST enregistrés
│   │   │   ├── models/   # 38 modèles SQLAlchemy
│   │   │   ├── services/ # 17 services métier
│   │   │   ├── security/ # 9 modules (auth, RBAC, plans, encryption...)
│   │   │   ├── ai/       # 6 modules (prévisions, anomalies, assistant...)
│   │   │   ├── tasks/    # 3 tâches asynchrones (backups, emails, rapports)
│   │   │   ├── utils/    # 9 utilitaires (PDF, Excel, QR, barcodes...)
│   │   │   ├── config/   # 2 fichiers (settings, database)
│   │   │   └── websockets/ # Événements temps réel
│   │   └── tests/        # 15 modules de tests
│   │
│   └── frontend/         # Application React principale (29 pages)
│       └── src/
│           ├── pages/    # Dashboard, Produits, Clients, Ventes, Stock...
│           ├── components/ # Layout, auth, desktop, landing, common
│           ├── contexts/  # AuthContext
│           ├── services/ # api.js
│           ├── hooks/    # useFormDraft, useMediaQuery
│           ├── schemas/  # validationSchemas.js
│           ├── utils/    # localStore, filterUtils, exportUtils
│           └── styles/   # 14 fichiers CSS
│
├── desk/                 # Application desktop Electron (29 pages)
│   └── src/
│       ├── pages/        # Mêmes pages que web/frontend
│       ├── components/   # Layout, auth, desktop, landing
│       ├── contexts/     # AuthContext, CartContext, DesktopContext
│       ├── services/     # api, desktopApi, draftService, publicApi
│       ├── hooks/        # useFormDraft, useAutoSaveDraft, useSplitView...
│       └── styles/       # tokens.css, landing.css
│
├── super-admin/          # Panneau d'administration plateforme (7 pages)
│   └── src/
│       ├── pages/        # Dashboard, Tenants, Plans, Subscriptions, Audit...
│       └── services/     # api.js
│
├── shared/               # Code partagé web/desk
│   ├── contexts/         # AuthContext, SyncContext
│   ├── hooks/            # useAuth, useRealtime, useOnlineStatus...
│   ├── services/         # api, apiClient, preferences, syncApi
│   ├── storage/          # authStorage, storageAdapter, tokenStore
│   ├── utils/            # syncEngine, hydration, localStore...
│   ├── websockets/       # socketClient
│   └── realtime/         # socketClient
│
├── docs/                 # Documentation (user, API, technique)
├── scripts/              # migrate_localStorage_sync.js
└── root_scripts/         # Scripts utilitaires
```

---

## Modules Fonctionnels

### 1. Gestion Commerciale
- **Produits** : Catalogue avec catégories, images, codes-barres
- **Clients** : Fiches clients, historique d'achats
- **Ventes** : Devis, bons de commande, factures
- **Paiements** : Intégration passerelle PAPI (monnaie MGA)

### 2. Gestion des Stocks
- Mouvements de stock (entrées/sorties/transferts)
- Alertes de stock bas
- Inventaires périodiques

### 3. Ressources Humaines
- Fiches employés
- Gestion des présences
- Salaires et primes
- Stagiaires

### 4. Comptabilité
- Plan comptable
- Écritures comptables
- Trésorerie

### 5. Logistique / Livraison
- Livreurs et véhicules
- Itinéraires
- Suivi des livraisons

### 6. Achats
- Commandes fournisseurs
- Réceptions
- Factures fournisseurs

### 7. Intelligence Artificielle
- Prévisions de ventes
- Détection d'anomalies
- Recommandations
- Assistant conversationnel

---

## Architecture Multi-Locataire

### Modèle : Base Partagée, Schéma Partagé

```python
class BaseModel(db.Model):
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), index=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    is_active = Column(Boolean)  # Soft delete
    created_by = Column(Integer)
    updated_by = Column(Integer)
```

- **Isolation** : Toutes les tables métier héritent de `tenant_id`
- **Sécurité** : Filtre automatique par tenant dans chaque requête
- **RBAC** : 7 rôles prédéfinis + rôles personnalisés

---

## Points d'Entrée

| Service | URL | Description |
|---------|-----|-------------|
| Frontend Web | `http://localhost:3000` | Interface utilisateur tenant |
| Super Admin | `http://localhost:3001` | Administration plateforme |
| API Backend | `http://localhost:5000/api/v1` | API REST |
| Swagger Docs | `http://localhost:5000/docs/` | Documentation API |
| Desktop | Application native | Client Electron |

---

## Sécurité

- **Authentification** : JWT avec claims tenant_id
- **Autorisation** : RBAC granulaire (rôles + permissions)
- **Isolation** : Validation systématique du tenant_id
- **Audit** : Journalisation des actions (AuditLog)
- **Mots de passe** : Hashage bcrypt
- **Chiffrement** : Module encryption dédié

---

## Namespaces API Enregistrés (22)

| Namespace | Fichier | Description |
|-----------|---------|-------------|
| `auth` | `auth.py` | Authentification JWT |
| `clients` | `clients.py` | Gestion clients |
| `dashboard` | `dashboard.py` | Tableau de bord |
| `factures` | `factures.py` | Factures clients |
| `fournisseurs` | `fournisseurs.py` | Fournisseurs |
| `paiements` | `paiements.py` | Paiements |
| `produits` | `produits.py` | Catalogue produits |
| `stocks` | `stocks.py` | Gestion stocks |
| `ventes` | `ventes.py` | Ventes |
| `ai` | `ai.py` | Intelligence artificielle |
| `public` | `public.py` | Accès public (catalogue) |
| `tenants` | `tenants.py` | Gestion tenants |
| `abonnements` | `abonnements.py` | Abonnements |
| `documents` | `documents.py` | Documents |
| `livraisons` | `livraisons.py` | Livraisons |
| `rh` | `rh.py` | Ressources humaines |
| `achats_devis` | `achats_devis.py` | Achats & devis |
| `comptabilite` | `comptabilite.py` | Comptabilité |
| `roles` | `roles.py` | Rôles RBAC |
| `permissions` | `permissions.py` | Permissions |
| `users` | `users.py` | Utilisateurs |
| `papi` | `papi.py` | Passerelle paiement PAPI |

> **Note** : Les fichiers `employes.py`, `notifications.py`, `super_admin.py`, `desk.py`, `test.py` existent dans `api/v1/` mais ne sont pas enregistrés dans `__init__.py`.

---

## Modèles SQLAlchemy (38)

| Catégorie | Modèles |
|-----------|---------|
| **Core** | Tenant, Utilisateur, RolePermission, AuditLog |
| **Produits** | Produit, Stock |
| **Ventes** | Vente, LigneVente, Facture, FactureFournisseur, CommandeClient |
| **Clients** | Client |
| **Fournisseurs** | Fournisseur, CommandeFournisseur, CommandeAchat, LigneAchat |
| **Paiements** | Paiement, PaymentEvent |
| **RH** | Employe, Presence, Salaire, Prime, Stagiaire |
| **Comptabilité** | CompteComptable, EcritureComptable, Tresorerie |
| **Livraison** | Livraison, Livreur, Vehicule, Itineraire, SuiviLivraison |
| **Achats** | DevisAvoirBL |
| **Documents** | DocumentGenere, ModeleDocument |
| **Abonnements** | Abonnement |
| **Config** | Notification, PasswordResetToken, DeskState |

---

## Services Métier (17)

| Service | Description |
|---------|-------------|
| `BaseService` | Service de base avec CRUD générique |
| `AuthService` | Authentification et tokens |
| `ClientService` | Gestion clients |
| `ProduitService` | Catalogue produits |
| `VenteService` | Ventes et facturation |
| `CommandeService` | Commandes |
| `AchatService` | Achats fournisseurs |
| `StockService` | Mouvements de stock |
| `PaiementService` | Enregistrement paiements |
| `LivraisonService` | Livraisons |
| `FournisseurService` | Fournisseurs |
| `FacturationService` | Factures |
| `ComptabiliteService` | Écritures comptables |
| `DashboardService` | Statistiques dashboard |
| `RHService` | Ressources humaines |
| `StagiaireService` | Stagiaires |
| `AbonnementService` | Abonnements |

---

## Pages Frontend Web (29)

| Module | Pages |
|--------|-------|
| **Dashboard** | Dashboard |
| **Produits** | Products, ProductDetail, Catalogue, Cart, Checkout |
| **Clients** | Clients |
| **Ventes** | Sales, Invoices, Payments |
| **Stock** | Inventory |
| **Achats** | Purchases, Suppliers |
| **Livraison** | Delivery, OrderTracking, Suivi |
| **RH** | HR |
| **Comptabilité** | Accounting |
| **Documents** | Documents |
| **Admin** | Users, Roles, Permissions |
| **IA** | AI |
| **Abonnement** | Subscription |
| **Super Admin** | SuperAdmin, SuperAdminProfile |
| **Autres** | Home, Contact, Documentation, UserOrders |

---

## Pages Desktop Electron (29)

Mêmes pages que le frontend web avec layout desktop optimisé (sidebar, TopBar, SplitView, CommandPalette).

---

## Pages Super Admin (7)

| Page | Description |
|------|-------------|
| `Dashboard` | Vue d'ensemble plateforme |
| `Tenants` | Gestion des tenants |
| `TenantDetail` | Détail d'un tenant |
| `Plans` | Plans d'abonnement |
| `Subscriptions` | Gestion abonnements |
| `Audit` | Journal d'audit |
| `Profile` | Profil super admin |

---

## Modules IA (6)

| Module | Description |
|--------|-------------|
| `previsions.py` | Prévisions de ventes (régression linéaire) |
| `anomalies.py` | Détection d'anomalies (z-score) |
| `recommendations.py` | Recommandations produits |
| `assistant.py` | Assistant conversationnel |
| `training.py` | Entraînement modèles |
| `external_services.py` | Intégration services externes |

---

## Modules Sécurité (9)

| Module | Description |
|--------|-------------|
| `auth.py` | Authentification JWT |
| `tenant.py` | Filtrage tenant, isolation |
| `roles.py` | Gestion rôles RBAC |
| `permissions.py` | Gestion permissions |
| `permission_matrix.py` | Matrice permissions |
| `plans.py` | Plans d'abonnement |
| `plan_limits.py` | Limites par plan |
| `rate_limit.py` | Rate limiting |
| `encryption.py` | Chiffrement données |

---

## Tests

| Module | Fichier |
|--------|---------|
| Authentification | `test_auth.py` |
| API Utilisateurs | `test_users_api.py` |
| Multi-tenancy | `test_tenancy.py` |
| Stocks | `test_stocks.py` |
| Sécurité | `test_security_multi_tenant.py` |
| RH | `test_rh.py` |
| Produits | `test_produits.py` |
| Limites abonnement | `test_plan_limits.py`, `test_tenant_limits.py` |
| Paiements PAPI | `test_papi.py` |
| API Critiques | `test_critical_api.py` |
| Clients | `test_clients_api.py` |
| IA | `test_ai.py` |
| Mission 5 | `test_mission_5.py` |

**Configuration** : Base SQLite en mémoire, Factory-Boy pour les fixtures.

---

## Déploiement

### Docker Compose
- PostgreSQL (prod)
- Redis 7
- Backend Flask
- Celery Worker
- Frontend React

### Commandes Principales

```bash
# Backend
cd web/backend
flask run                    # Développement
flask db upgrade             # Migrations
pytest                       # Tests

# Frontend
cd web/frontend
npm start                    # Développement
npm run build                # Production

# Desktop
cd desk
npm run electron:dev         # Développement
npm run dist                 # Packaging
```

---

## Documentation Disponible

| Document | Description |
|----------|-------------|
| `README.md` | Vue d'ensemble du projet |
| `docs/user/README.md` | Guide utilisateur final |
| `docs/api/README.md` | Documentation API |
| `docs/technical/README.md` | Architecture technique |
| `docs/technical/WEB_DESKTOP_SYNC.md` | Sync web-desktop |
| `MLD_ERP_Multi_Tenant.pdf` | Schéma base de données |
| `Analyse_Fonctionnalite.md` | Analyse des fonctionnalités |
| `Plan_Desktop.md` | Plan évolution desktop |
| `SHARED_ARCHITECTURE.md` | Architecture code partagé |
| `RAPPORT_FINAL_AUDIT.md` | Rapport d'audit |
| `CODE.MD`, `CODE_REACT.MD` | Standards de code |

---

## Résumé

MIHAJA_ERP_PRO est un ERP production-ready avec :
- **38 modèles** couvrant tous les aspects d'une entreprise
- **22 namespaces API** organisés par domaine métier
- **17 services** pour la logique métier
- **4 interfaces** (Web, Desktop, Super Admin, Shared)
- **29 pages** frontend web et desktop
- **7 pages** super admin
- **Multi-tenancy** avec isolation complète des données
- **IA intégrée** (6 modules) pour l'aide à la décision
- **15 modules de tests** couvrant les fonctionnalités critiques
- **Sécurité renforcée** (9 modules dédiés)
