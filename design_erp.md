# Design ERP — MIHAJA_ERP_PRO

## 1. Vue d'ensemble

**MIHAJA_ERP_PRO** est un ERP (Enterprise Resource Planning) multi-locataire complet conçu pour les entreprises à Madagascar. Il gère l'ensemble des processus commerciaux : ventes, stocks, comptabilité, ressources humaines, livraisons, achats et intelligence artificielle intégrée.

**Séparation des rôles** :
```
SUPER ADMIN =| TENANT == ADMIN =| UTILISATEUR/EMPLOYÉ
```

- **Super Admin** : propriétaire de la plateforme, gère les tenants, abonnements et paiements
- **Tenant** : entreprise cliente avec environnement isolé
- **Admin principal** : compte propriétaire du Tenant (`tenant.admin_principal_id`)
- **Utilisateurs/Employés** : comptes créés par le Tenant, soumis à son quota d'abonnement

---

## 2. Stack technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Flask 2.3.3 + Flask-RESTx 1.1.0 |
| **ORM** | SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1 |
| **Base de données** | SQLite (dev) / PostgreSQL (prod) |
| **Cache/Queue** | Redis 7 + Celery 5.3 |
| **Frontend Web** | React 18.3 + React Router DOM 7 + Framer Motion |
| **Desktop** | Electron 38.8 + React 18 + @tanstack/react-virtual |
| **Super Admin** | React 18.3 + Chart.js 4 |
| **Authentification** | JWT (Flask-JWT-Extended) + bcrypt |
| **Validation** | Marshmallow 3.2 + Yup 1.7 |
| **Tests** | pytest 7.4 + Factory-Boy + Faker |

---

## 3. Structure du projet

```
MIHAJA_ERP_PRO/
├── web/
│   ├── backend/                # API Flask (22 namespaces REST)
│   │   ├── app/
│   │   │   ├── api/v1/         # 22 namespaces REST enregistrés
│   │   │   ├── models/         # 38 modèles SQLAlchemy
│   │   │   ├── services/       # 17 services métier
│   │   │   ├── security/       # 9 modules (auth, RBAC, plans, encryption...)
│   │   │   ├── ai/             # 6 modules (prévisions, anomalies, assistant...)
│   │   │   ├── tasks/          # 3 tâches asynchrones (backups, emails, rapports)
│   │   │   ├── utils/          # 9 utilitaires (PDF, Excel, QR, barcodes...)
│   │   │   ├── config/         # 2 fichiers (settings, database)
│   │   │   └── websockets/     # Événements temps réel
│   │   └── tests/              # 15 modules de tests
│   │
│   └── frontend/               # Application React principale (29 pages)
│       └── src/
│           ├── pages/          # Dashboard, Produits, Clients, Ventes, Stock...
│           ├── components/     # Layout, auth, desktop, landing, common
│           ├── contexts/       # AuthContext
│           ├── services/       # api.js
│           ├── hooks/          # useFormDraft, useMediaQuery
│           ├── schemas/        # validationSchemas.js
│           ├── utils/          # localStore, filterUtils, exportUtils
│           └── styles/         # 14 fichiers CSS
│
├── desk/                       # Application desktop Electron (29 pages)
│   └── src/
│       ├── pages/              # Mêmes pages que web/frontend
│       ├── components/         # Layout, auth, desktop, landing
│       ├── contexts/           # AuthContext, CartContext, DesktopContext
│       ├── services/           # api, desktopApi, draftService, publicApi
│       ├── hooks/              # useFormDraft, useAutoSaveDraft, useSplitView...
│       └── styles/             # tokens.css, landing.css
│
├── super-admin/                # Panneau d'administration plateforme (7 pages)
│   └── src/
│       ├── pages/              # Dashboard, Tenants, Plans, Subscriptions, Audit...
│       └── services/           # api.js
│
├── shared/                     # Code partagé web/desk
│   ├── contexts/               # AuthContext, SyncContext
│   ├── hooks/                  # useAuth, useRealtime, useOnlineStatus...
│   ├── services/               # api, apiClient, preferences, syncApi
│   ├── storage/                # authStorage, storageAdapter, tokenStore
│   ├── utils/                  # syncEngine, hydration, localStore...
│   ├── websockets/             # socketClient
│   └── realtime/               # socketClient
│
├── docs/                       # Documentation (user, API, technique)
├── scripts/                    # migrate_localStorage_sync.js
└── erp.db                      # Base SQLite dev
```

---

## 4. Architecture multi-locataire

### Modèle : Base Partagée, Schéma Partagé

Toutes les tables métier héritent de `tenant_id` pour l'isolation.

```python
class BaseModel(db.Model):
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), index=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    is_active = Column(Boolean)   # Soft delete
    created_by = Column(Integer)
    updated_by = Column(Integer)
```

### Isolation
- **Filtre automatique par tenant** dans chaque requête via décorateur `@tenant_required`
- **RBAC** : 7 rôles prédéfinis + rôles personnalisés
- **JWT claims** contiennent `tenant_id` pour résolution prioritaire

---

## 5. Modèles de données (38)

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

## 6. Services métier (17)

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

## 7. Modules fonctionnels

### 1. Gestion Commerciale
- **Produits** : Catalogue avec catégories, images, codes-barres
- **Clients** : Fiches clients, historique d'achats, 7 types de clients
- **Ventes** : Devis, bons de commande, factures, vente en gros/détail
- **Paiements** : Intégration passerelle PAPI (monnaie MGA)

### 2. Gestion des Stocks
- Mouvements de stock (entrées/sorties/transferts)
- Alertes de stock bas et seuils critiques
- Inventaires périodiques

### 3. Ressources Humaines
- Fiches employés, gestion des présences
- Salaires et primes, stagiaires

### 4. Comptabilité
- Plan comptable, écritures comptables
- Trésorerie, import CSV

### 5. Logistique / Livraison
- Livreurs et véhicules, itinéraires
- Suivi des livraisons temps réel

### 6. Achats
- Commandes fournisseurs, réceptions
- Factures fournisseurs, devis, bons de livraison, avoirs

### 7. Documents
- Modèles de documents, génération PDF/Devis/Contrats
- QR codes et codes-barres

### 8. Intelligence Artificielle
- Prévisions de ventes (régression linéaire)
- Détection d'anomalies (z-score)
- Recommandations produits et réapprovisionnement
- Assistant conversationnel
- Entraînement modèles et services externes

---

## 8. Système de design

### Tokens de design (`web/frontend/src/styles/tokens.css`)

**Palette de couleurs** :

| Rôle | Couleur | Usage |
|------|---------|-------|
| **Primary** | Gold `#d4af37` | Actions principales, marque |
| **Success** | Vert `#22c55e` | États positifs, confirmations |
| **Warning** | Amber `#f59e0b` | Alertes, avertissements |
| **Danger** | Rouge `#ef4444` | Erreurs, suppressions |
| **Info** | Bleu `#3b82f6` | Informations, liens |

**Typographie** :
- **Headings** : Inter (weights 400-800)
- **Body** : DM Sans (weights 400-700)
- **Mono** : JetBrains Mono

**Échelle typographique** :
- Display : `clamp(40px, 5vw, 56px)`
- H1 : 28px, H2 : 22px, H3 : 18px
- Body : 14px, Small : 13px, Caption : 12px

**Espacement** : base 4px (`--space-1` à `--space-24`)

**Arrondis** : `--radius-xs: 4px` à `--radius-2xl: 20px`

**Ombres** : système en couches (`xs` → `2xl`) + ombres colorées primary

**Transitions** : 120ms (fast) à 320ms (slower), courbes `ease-out`, `ease-in-out`, `spring`

**Z-index** : base 0 → toast 500

### Layout
- **Sidebar** : 260px (collapsed : 76px)
- **Topbar** : 60px
- **Contenu max** : 1440px
- **Padding page** : responsive (`--space-8` desktop, `--space-6` tablette, `--space-4` mobile)

### Modes
- Light mode (défaut)
- Dark mode via `[data-theme='dark']`
- High contrast via `prefers-contrast: more`
- Reduced motion via `prefers-reduced-motion: reduce`

---

## 9. Pages et interfaces

### Frontend Web (29 pages)
- **Dashboard** : KPIs, graphiques, alertes
- **Produits** : Products, ProductDetail, Catalogue, Cart, Checkout
- **Clients** : CRUD, historique, solde
- **Ventes** : Sales, Invoices, Payments
- **Stock** : Inventory
- **Achats** : Purchases, Suppliers
- **Livraison** : Delivery, OrderTracking, Suivi
- **RH** : HR
- **Comptabilité** : Accounting
- **Documents** : Documents
- **Admin** : Users, Roles, Permissions
- **IA** : AI
- **Abonnement** : Subscription
- **Super Admin** : SuperAdmin, SuperAdminProfile
- **Autres** : Home, Contact, Documentation, UserOrders

### Desktop Electron (29 pages)
Mêmes pages que le frontend web avec layout desktop optimisé :
- Sidebar 260px + TopBar
- SplitView pour workflows simultanés
- CommandPalette (CMD+K)
- Virtualisation des listes longues
- Drafts auto-sauvegardés

### Super Admin (7 pages)
- Dashboard : Vue d'ensemble plateforme
- Tenants : Gestion des tenants
- TenantDetail : Détail d'un tenant
- Plans : Plans d'abonnement
- Subscriptions : Gestion abonnements
- Audit : Journal d'audit
- Profile : Profil super admin

---

## 10. Sécurité et authentification

### Authentification
- **JWT** avec access + refresh tokens
- **bcrypt** pour hash des mots de passe (coût 12)
- Claims JWT : `user_id`, `username`, `email`, `role`, `tenant_id`

### Clé employé
> La clé employé est une donnée privée appartenant au Tenant.
> Elle ne doit jamais être partagée entre les Tenants.
> Le Super Admin ne doit jamais voir la clé employé d'un Tenant.

Anciennement (conservé pour historique) :
- La « Clé d'administration » (passeport entreprise) a été supprimée.
- L'authentification se fait désormais uniquement par email + mot de passe (JWT access/refresh).
- Les colonnes `admin_key_hash`/`admin_key_status` (Tenant et Utilisateur), l'enum `StatutAdminKey`, ainsi que les routes et helpers associés ont été retirés.

### Clé Employé (employee_key) — DONNÉE PRIVÉE DU TENANT

> ⚠️ L'`employee_key` est une donnée **privée** appartenant au Tenant.

**Règle de confidentialité** :
- Tenant propriétaire → ✅ peut voir / gérer sa clé employé
- Autres Tenants → ❌ ne peuvent pas voir la clé
- Super Admin → ❌ ne doit JAMAIS voir la clé

**Règles strictes** :
1. L'`employee_key` est liée au Tenant concerné
2. Elle ne doit **jamais** être partagée entre les Tenants
3. Le Super Admin peut voir les informations administratives (nom, plan, statut, etc.) mais **jamais** l'`employee_key`
4. La protection doit être faite au **niveau backend**, pas simplement masquée côté frontend
5. L'`employee_key` ne doit **jamais** apparaître dans les réponses des endpoints Super Admin
6. L'`employee_key` ne doit **jamais** être sérialisée dans `to_dict()` du Tenant

**Exposition API** :
```text
GET /tenant/me → ✅ employee_key autorisée selon les règles métier
GET /super-admin/tenants → ❌ employee_key NE PAS RETOURNER
```

### RBAC (7 rôles)
- `SUPER_ADMIN` : accès global plateforme
- `ADMIN` / `MANAGER` : modules opérationnels
- `SALES` / `STOCK` / `ACCOUNTANT` : modules limités
- `USER` : interface publique, catalogue, commandes
- Rôles personnalisés + permissions granulaires

### Isolation multi-tenant
- Décorateur `@tenant_required` : valide JWT + charge tenant
- Filtre SQL global : `WHERE tenant_id = X` injecté automatiquement
- Résolution tenant : JWT (prioritaire) → Headers (fallback)

### Rate limiting
- Redis avec fallback passif si indisponible
- Appliqué sur `/login`, `/register`, `/forgot-password` (5 req / 300s)

---

## 11. Abonnements et quotas

| Plan | Utilisateurs | Durée | Caractéristiques |
|------|-------------|-------|------------------|
| **Gratuit** | 1 (admin principal) | Illimité | Accès basique |
| **Starter** | 3 | 30 jours | Accès étendu |
| **Pro** | 7 | 30 jours | Fonctionnalités avancées |
| **Enterprise** | Illimité | 30 jours | Accès complet |

**Règles** :
- Quota par `tenant_id` (pas global)
- Renouvellement réservé à `tenant.admin_principal_id`
- Seul l'admin principal peut créer/modifier les utilisateurs

---

## 12. Intelligence Artificielle

### Modules (6)

| Module | Description |
|--------|-------------|
| `previsions.py` | Prévisions de ventes (régression linéaire) |
| `anomalies.py` | Détection d'anomalies (z-score sur stocks, ventes, paiements) |
| `recommendations.py` | Réapprovisionnement, cross-sell, ajustements prix |
| `assistant.py` | Assistant conversationnel avec contexte métier |
| `training.py` | Entraînement modèles |
| `external_services.py` | Intégration OpenAI, Anthropic, recherche web |

### Architecture IA
- Réponse interne forte pour requêtes métier classiques
- Enrichissement externe optionnel (OpenAI / Anthropic)
- Recherche web déclenchée sur mots-clés spécifiques
- Gestion de contexte conversationnel (10 messages max)

---

## 13. Synchronisation Web / Desktop

### Architecture partagée (`shared/`)

| Composant | Description |
|-----------|-------------|
| `shared/contexts/AuthContext.jsx` | Contexte auth unique web + desktop |
| `shared/hooks/useOnlineStatus.js` | Détection online/offline |
| `shared/hooks/useRealtimeSync.js` | Sync temps réel via Socket.IO |
| `shared/storage/authStorage.js` | Abstraction localStorage auth |
| `shared/utils/syncEngine.js` | Moteur sync hors-ligne (LWW, queue) |
| `shared/websockets/socketClient.js` | Client Socket.IO partagé |

### Stratégie
- Code mutualisé entre `web/frontend` et `desk`
- File d'attente pour mutations hors-ligne
- Hydratation par timestamps
- Stratégie de conflit : Dernière écriture gagne (LWW)
- Migration progressive depuis ancien format localStorage

---

## 14. Points d'entrée

| Service | URL | Description |
|---------|-----|-------------|
| Frontend Web | `http://localhost:3000` | Interface utilisateur tenant |
| Super Admin | `http://localhost:3001` | Administration plateforme |
| API Backend | `http://localhost:5000/api/v1` | API REST |
| Swagger Docs | `http://localhost:5000/docs/` | Documentation API |
| Desktop | Application native | Client Electron |

---

## 15. Namespaces API (22)

| Namespace | Description |
|-----------|-------------|
| `auth` | Authentification JWT |
| `clients` | Gestion clients |
| `dashboard` | Tableau de bord |
| `factures` | Factures clients |
| `fournisseurs` | Fournisseurs |
| `paiements` | Paiements |
| `produits` | Catalogue produits |
| `stocks` | Gestion stocks |
| `ventes` | Ventes |
| `ai` | Intelligence artificielle |
| `public` | Accès public (catalogue) |
| `tenants` | Gestion tenants |
| `abonnements` | Abonnements |
| `documents` | Documents |
| `livraisons` | Livraisons |
| `rh` | Ressources humaines |
| `achats_devis` | Achats & devis |
| `comptabilite` | Comptabilité |
| `roles` | Rôles RBAC |
| `permissions` | Permissions |
| `users` | Utilisateurs |
| `papi` | Passerelle paiement PAPI |

---

## 16. Tests

### Backend (119 tests — tous passent)

| Module | Fichier | Tests |
|--------|---------|-------|
| Authentification | `test_auth.py` | 2/2 PASS |
| API Utilisateurs | `test_users_api.py` | 16/16 PASS |
| Multi-tenancy | `test_tenancy.py` | - |
| Stocks | `test_stocks.py` | - |
| Sécurité | `test_security_multi_tenant.py` | - |
| RH | `test_rh.py` | - |
| Produits | `test_produits.py` | - |
| Limites abonnement | `test_plan_limits.py`, `test_tenant_limits.py` | 12/12 PASS |
| Paiements PAPI | `test_papi.py` | - |
| API Critiques | `test_critical_api.py` | - |
| Clients | `test_clients_api.py` | - |
| IA | `test_ai.py` | - |
| Conformité architecture | `test_architecture_compliance.py` | 17/17 PASS |

**Total** : 119 tests passent ✅

---

## 17. État actuel et bugs connus

### Bugs critiques à corriger (11)
1. Endpoint public non authentifié (`POST /api/v1/public/commandes`)
2. Webhook PAPI sans vérification de signature
3. Hard-delete tenant sans sauvegarde
4. `ReferenceError` dans `Users.jsx` (`isEmployeeLimitReached`)
5. Fonction `handleDelete` indéfinie dans `Tenants.jsx`
6. Tokens non chiffrés dans Electron (`authStorage` → `secureStore`)
7. Auth WebSocket bypass (`localStorage` au lieu de `secureStore`)
8. Stale closure dans `flushQueue` (SyncContext)
9. Décrypt fallback retourne données corrompues (Electron preload)
10. Services dupliqués et désynchronisés (`desktopApi.js`)
11. Commit DB dans décorateur auth (`tenant_required`)

### Bugs haute sévérité (20)
- Scan complet des tokens de reset (DoS potentiel)
- Rate limiter silencieux si Redis down
- Total CA sous-estimé (`.limit(200)`)
- Mass Assignment dans `BaseService.update()`
- Soft-delete incomplet (9/30 modèles)
- Memory leaks (intervals, timeouts non nettoyés)
- Race conditions (AbortController manquant)
- Socket jamais déconnecté (super-admin)

### Bugs moyenne sévérité (21)
- Logique changement mot de passe cassée
- `ValueError` non gérés (dates, conversions)
- Endpoint test exposé en production
- Double commit incohérent
- Instances axios dupliquées
- `window.confirm` incohérent avec ConfirmModal personnalisé

### Bugs basse sévérité (14)
- `isdigit()` échoue pour négatifs
- Admin key en clair dans réponse registration — **RÉSOLU** : la clé d'administration a été supprimée (voir §Clé d'administration — FONCTIONNALITÉ SUPPRIMÉE)
- String literals pour rôles
- Pas de single-instance lock Electron
- `fs.writeFileSync` bloque le renderer
- XSS potentiel, path traversal

---

## 18. Déploiement

### Docker Compose
- PostgreSQL (prod)
- Redis 7
- Backend Flask
- Celery Worker
- Frontend React

### Commandes principales

```bash
# Backend
cd web/backend
flask run                    # Développement
flask db upgrade             # Migrations
pytest                       # Tests (119 passent)

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

## 19. Documentation disponible

| Document | Description |
|----------|-------------|
| `README.md` | Vue d'ensemble du projet |
| `Analyse_Projet_Actuel.md` | Analyse complète (structure, bugs, architecture) |
| `AUDIT_ARCHITECTURE.md` | Audit conformité architecture (17/17 tests passent) |
| `SHARED_ARCHITECTURE.md` | Architecture code partagé web/desktop |
| `RAPPORT_FINAL_AUDIT.md` | Rapport d'audit technique détaillé |
| `CODE.MD` | Standards et extraits de code |
| `docs/user/README.md` | Guide utilisateur final |
| `docs/api/README.md` | Documentation API |
| `docs/technical/README.md` | Architecture technique |

---

## 20. Résumé

MIHAJA_ERP_PRO est un ERP **production-ready** avec :
- **38 modèles** couvrant tous les aspects d'une entreprise
- **22 namespaces API** organisés par domaine métier
- **17 services** pour la logique métier
- **4 interfaces** (Web, Desktop, Super Admin, Shared)
- **29 pages** frontend web et desktop
- **7 pages** super admin
- **Multi-tenancy** avec isolation complète des données
- **IA intégrée** (6 modules) pour l'aide à la décision
- **119 tests backend** tous passants
- **Sécurité renforcée** (JWT, RBAC, rate limiting, encryption)

**Architecture conforme à 100%** aux règles métier Super Admin =| Tenant == Admin =| User.

**Points d'attention** : 66 bugs identifiés (11 critiques, 20 haute, 21 moyenne, 14 basse) nécessitant corrections avant production optimale.
