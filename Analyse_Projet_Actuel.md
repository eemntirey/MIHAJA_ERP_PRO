# Analyse du Projet MIHAJA_ERP_PRO

**Date de mise à jour** : 2026-09-05
**Statut** : Pré-production — Architecture conforme, corrections P0/P1 appliquées

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
│   ├── backend/          # API Flask (23 namespaces REST)
│   │   ├── app/
│   │   │   ├── api/v1/   # 23 namespaces REST enregistrés (admin_devices + notifications ajoutés)
│   │   │   ├── models/   # 40 modèles SQLAlchemy
│   │   │   ├── services/ # 25 services métier
│   │   │   ├── security/ # 10 modules (auth, RBAC, plans, encryption...)
│   │   │   ├── ai/       # 6 modules (prévisions, anomalies, assistant...)
│   │   │   ├── tasks/    # 3 tâches asynchrones (backups, emails, rapports)
│   │   │   ├── utils/    # 10 utilitaires (PDF, Excel, QR, barcodes...)
│   │   │   ├── config/   # 2 fichiers (settings, database)
│   │   │   ├── websockets/ # Événements temps réel
│   │   │   └── realtime/  # Socket.IO server
│   │   └── tests/        # 34 fichiers de tests
│   │
│   └── frontend/         # Application React principale (30 pages)
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
├── desk/                 # Application desktop Electron (30 pages)
│   └── src/
│       ├── pages/        # Mêmes pages que web/frontend
│       ├── components/   # Layout, auth, desktop, landing
│       ├── contexts/     # AuthContext, CartContext, DesktopContext
│       ├── services/     # api, desktopApi, draftService, publicApi
│       ├── hooks/        # useFormDraft, useAutoSaveDraft, useSplitView...
│       └── styles/       # tokens.css, landing.css
│
├── super-admin/          # Panneau d'administration plateforme (9 pages)
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

## Namespaces API Enregistrés (23)

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
| `livraisons` | `livraisons.py` | Livraisons (incluant endpoints `/livreurs/moi/*`) |
| `rh` | `rh.py` | Ressources humaines |
| `achats_devis` | `achats_devis.py` | Achats & devis |
| `comptabilite` | `comptabilite.py` | Comptabilité |
| `roles` | `roles.py` | Rôles RBAC |
| `permissions` | `permissions.py` | Permissions |
| `users` | `users.py` | Utilisateurs |
| `papi` | `papi.py` | Passerelle paiement PAPI |
| `admin_devices` | `admin_devices.py` | Gestion des appareils admin |
| `notifications` | `notifications.py` | Notifications utilisateur |

> **Note** : Les fichiers `employes.py`, `super_admin.py`, `desk.py`, `test.py` existent dans `api/v1/` mais ne sont pas enregistrés dans `__init__.py`.

---

## Modèles SQLAlchemy (40)

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

## Services Métier (25)

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

## Pages Frontend Web (30)

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

## Pages Desktop Electron (30)

Mêmes pages que le frontend web avec layout desktop optimisé (sidebar, TopBar, SplitView, CommandPalette).

---

## Pages Super Admin (9)

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

## Modules Sécurité (10)

| Module | Description |
|--------|-------------|
| `auth.py` | Authentification JWT |
| `tenant.py` | Filtrage tenant, isolation |
| `roles.py` | Gestion rôles RBAC |
| `permissions.py` | Gestion permissions |
| `permission_matrix.py` | Matrice permissions |
| `plans.py` | Plans d'abonnement |
| `plan_limits.py` | Limites par plan |
| `rate_limit.py` | Rate limiting (fail-closed) |
| `encryption.py` | Chiffrement données |
| `admin_devices.py` | Gestion des appareils admin (auto-register 1er device) |

---

## Tests

| Module | Fichier |
|--------|---------|
| Authentification | `test_auth.py` |
| Architecture admin | `test_admin_architecture.py` |
| Anti-bugs audit | `test_anti_bugs_audit.py` |
| Conformité architecture | `test_architecture_compliance.py` |
| API Utilisateurs | `test_users_api.py` |
| Multi-tenancy | `test_tenancy.py`, `test_security_multi_tenant.py` |
| Stocks | `test_stocks.py` |
| RH | `test_rh.py` |
| Produits | `test_produits.py` |
| Limites abonnement | `test_plan_limits.py`, `test_tenant_limits.py` |
| Paiements PAPI | `test_papi.py` |
| API Critiques | `test_critical_api.py` |
| Clients | `test_clients_api.py` |
| Catalogue public | `test_public_catalog.py` |
| IA | `test_ai.py` |
| Mission 5 | `test_mission_5.py` |
| Compte livreur | `test_livreur_compte.py` |
| employee_key | `test_employee_key.py` |
| Rôles presets | `test_roles_presets.py` |
| Création rôles sécurité | `test_role_creation_security.py` |
| Visibilité rôles | `test_role_visibility_fix.py` |
| Super Admin paiements | `test_super_admin_payments.py` |

**Configuration** : Base SQLite en mémoire, Factory-Boy pour les fixtures.

**Total** : 34 fichiers de tests backend collectés (~278 tests).

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
- **40 modèles** couvrant tous les aspects d'une entreprise
- **23 namespaces API** organisés par domaine métier
- **25 services** pour la logique métier
- **4 interfaces** (Web, Desktop, Super Admin, Shared)
- **30 pages** frontend web et desktop
- **9 pages** super admin
- **Multi-tenancy** avec isolation complète des données
- **IA intégrée** (6 modules) pour l'aide à la décision
- **34 modules de tests** (~278 tests collectés) couvrant les fonctionnalités critiques
- **Sécurité renforcée** (10 modules dédiés)
- **ÉTAPE 0 (Livreur)** : relation `Livreur ↔ Utilisateur` opérationnelle avec 7 tests passent (défense en profondeur : API + service + event listener ORM)

:::ADMIN DU TENANT
       │
        └── Administration des comptes == il cree son compte E/se (connexion par email + mot de passe, sans clé d'admin — fonctionnalité supprimée). permission selon le son abonnement 
               │
               ├── Créer Manager avec leur permission / et heritier le contrainte d'abonnement de son admin 
               ├── Créer Sales .....
               ├── Créer Stock
               ├── Créer Comptable ....
               ├── Créer RH ... 
               └── Créer User .... 
	       |___ ainsi de suite ....  ###REFLECHI BIEN AVANT D'EFFECTUER UNE MODIFICATION

            tu dois savoir que si je creer un compte grossiste avec des abonnement que je choisis, un autre peut creer aussi comme ce qu'il veut mais selon l'abonnement que j'achete que je peux creer des utilisateur pas dans le pages d'inscription mais dans le listes utilisateurs dans l'app web et je peux ajoute 3 ou 5 utilisateur employe selon mon abonnement et un autre grossiste aussi peut le faire

---

## Analyse des Bugs Existants

### Résumé

| Sévérité | Backend | Frontend | Desktop/Shared | Total |
|----------|---------|----------|----------------|-------|
| **Critique** | 3 | 1 | 7 | **11** |
| **Haute** | 7 | 5 | 8 | **20** |
| **Moyenne** | 10 | 4 | 7 | **21** |
| **Basse** | 4 | 4 | 6 | **14** |
| **Total** | **24** | **14** | **28** | **66** |

---

### Bugs Critiques (Critique)

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 1 | `web/backend/app/api/v1/public.py` | 95-128 | **Endpoint public non authentifié** : `POST /api/v1/public/commandes` permet de créer des commandes sans authentification, ouvrant la porte aux fraudes et abus. |
| 2 | `web/backend/app/api/v1/papi.py` | 130-157 | **Webhook PAPI sans vérification de signature** : Un attaquant peut usurper des notifications de paiement et modifier le statut des abonnements. |
| 3 | `web/backend/app/api/v1/super_admin.py` | 1113-1150 | **Hard-delete tenant sans sauvegarde** : La fonction `_hard_delete_tenant()` et l'endpoint `POST /api/v1/super-admin/tenants/<id>/delete` effectuaient une suppression physique irréversible. **[CORRIGE]** : endpoint et fonction supprimés ; seul le soft-delete via `DELETE /api/v1/super-admin/tenants/<id>` est conservé, préservant l'historique et la traçabilité. |
| 4 | `web/frontend/src/pages/Users.jsx` | 18-22 | **ReferenceError** : `isEmployeeLimitReached()` défini au niveau du module mais référence `tenantSummary` et `formData` (state du composant) — crash à l'exécution. |
| 5 | `super-admin/src/pages/Tenants.jsx` | 260 | **Fonction indéfinie** : Le bouton "Supprimer" appelle `handleDelete()` qui n'existe pas (seul `handleDeletePermanent` est défini). |
| 6 | `shared/storage/authStorage.js` | 62-76 | **Tokens non chiffrés dans Electron** : `authStorage` écrit dans `localStorage` en clair au lieu d'utiliser `secureStore`. |
| 7 | `desk/src/services/desktopApi.js` | 1-303 | **Services dupliqués et désynchronisés** : Implémentation parallèle de notification/favorite/column/sync sans sync backend. |
| 8 | `shared/websockets/socketClient.js` | 29 | **Auth WebSocket bypass** : Lit le token depuis `localStorage` au lieu de `secureStore` — échec de connexion dans Electron. |
| 9 | `shared/realtime/socketClient.js` | 41 | **Auth WebSocket bypass** : Même problème que ci-dessus pour le module realtime. |
| 10 | `shared/contexts/SyncContext.jsx` | 75 | **Stale closure dans flushQueue** : Capture initiale de `isSyncing` dans l'event listener — race conditions possibles. |
| 11 | `desk/electron/preload.js` | 28-31 | **Décrypt fallback retourne des données corrompues** : Retourne le base64 brut au lieu de `null` quand le déchiffrement échoue. |

---

### Bugs Haute Sévérité (High)

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 12 | `web/backend/app/security/tenant.py` | 170-186 | **Commit DB dans décorateur auth** : `tenant_required` met à jour `AdminDevice.last_seen` et commit à chaque requête — charge ineffaceable et race conditions. |
| 13 | `web/backend/app/api/v1/auth.py` | 454-462 | **Scan complet des tokens de reset** : Charge TOUS les `PasswordResetToken` non utilisés en mémoire — DoS et fuite d'information. **[CORRIGE]** : recherche ciblée indexée par digest SHA-256 via `PasswordResetToken.find_by_raw_token` (aucun scan global). |
| 14 | `web/backend/app/security/rate_limit.py` | 61-62 | **Rate limiter silencieux** : `except Exception: pass` — quand Redis est down, le rate limiting est complètement désactivé. |
| 15 | `web/backend/app/ai/assistant.py` | 38 | **Total CA sous-estimé** : `.limit(200)` tronque le calcul du chiffre d'affaires pour les tenants avec >200 ventes. |
| 16 | `web/backend/app/api/v1/ventes.py` | 102-104 | **Crash ValueError non géré** : `datetime.strptime()` sans try/except — 500 error sur date invalide. |
| 17 | `web/backend/app/services/base_service.py` | 65-67 | **Mass Assignment** : `BaseService.update()` définit tous les champs fournis — un attaquant peut modifier `tenant_id`, `is_active`, etc. **[CORRIGE]** : whitelist `PROTECTED_FIELDS` appliquée à `create()` ET `update()` ; le `tenant_id` est déterminé côté serveur (contexte authentifié), les champs sensibles (`is_active`, `role`, `statut`, `created_by`, `updated_by`, etc.) sont ignorés dans le payload. |
| 18 | `web/backend/app/api/v1/super_admin.py` | 399-406 | **Soft-delete incomplet** : Seulement 9 modèles soft-delete sur ~30 — les autres (`Livreur`, `Vehicule`, `Stock`, etc.) restent orphelins. |
| 19 | `web/frontend/src/pages/Subscription.jsx` | 219-228 | **Memory leak** : `setInterval` pour polling fenêtre de paiement jamais nettoyé au unmount. |
| 20 | `web/frontend/src/pages/AI.jsx` | 266-269 | **State update on unmounted component** : `setTimeout` de 400ms peut déclencher `setMessages` après navigation. |
| 21 | `web/frontend/src/pages/Home.jsx` | 33-38 | **Stale closure** : `useEffect` avec `[]` ne réagit pas aux changements d'état auth — notifications non chargées après login. |
| 22 | `web/frontend/src/pages/Users.jsx` | 103-105 | **Race condition** : Pas d'`AbortController` pour les requêtes de recherche rapide — données obsolètes peuvent écraser les fraîches. |
| 23 | `web/frontend/src/pages/Permissions.jsx` | 45-47 | **Race condition** : Même problème d'`AbortController` manquant. |
| 24 | `desk/src/pages/Sales.jsx` | 1044 | **Modal Avoir mal placé** : Rendu conditionnel dans le mauvais tab — le modal n'apparaît que sous "Bons de livraison". |
| 25 | `desk/src/components/layout/TitleBar.jsx` | 46 | **IPC listener leak** : `window.electron.onMaximizeChanged()` jamais supprimé au cleanup. |
| 26 | `desk/src/pages/Subscription.jsx` | 220-229 | **Uncleared interval** : Même memory leak que le frontend web pour le polling de paiement. |
| 27 | `super-admin/src/hooks/useAdminRealtime.js` | 41-68 | **Socket jamais déconnecté** : Le cleanup supprime les listeners mais pas la connexion — accumulation de sockets. |
| 28 | `shared/contexts/AuthContext.jsx` | 245-260 | **Missing auth:logout dispatch** : `logout()` ne dispatch pas l'événement — les hooks realtime/sync ne réagissent pas. |
| 29 | `shared/utils/syncEngine.js` | 19 | **isOnline() defaults true** : Retourne `true` quand `navigator` est undefined — sync tenté hors ligne. |
| 30 | `super-admin/src/services/api.js` | 56,59 | **Full page reload on 401** : `window.location.href = '/login'` recharge toute l'app au lieu d'une navigation SPA. |
| 31 | `desk/src/App.js` | 165-173 | **Missing auth:logout dispatch** : Même problème que AuthContext pour le desktop. |

---

### Bugs Moyenne Sévérité (Medium)

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 32 | `web/backend/app/api/v1/users.py` | 121-126, 281-285 | **Logique changement mot de passe cassée** : Le champ `password` est utilisé pour vérification ET nouveau hash — impossible de changer le mot de passe. |
| 33 | `web/backend/app/api/v1/rh.py` | 197-198 | **ValueError non géré** : `int(mois)` crash sur chaîne non numérique. |
| 34 | `web/backend/app/api/v1/test.py` | 7 | **Endpoint test exposé** : Activé quand `FLASK_ENV` est vide (défaut) — accessible en prod. |
| 35 | `web/backend/app/models/utilisateur.py` | 74-79 | **AttributeError potentiel** : `is_admin` accède à `custom_role.permissions` sans vérifier si `custom_role` est None. |
| 36 | `web/backend/app/api/v1/stocks.py` | 78-83 | **InvalidOperation non attrapé** : `Decimal(str(quantite))` peut lever une exception non couverte. |
| 37 | `web/backend/app/api/v1/super_admin.py` | 449-458 | **Double commit** : Transaction incohérente si le second commit échoue après le premier. |
| 38 | `web/backend/app/api/v1/fournisseurs.py` | 119-120 | **Mass Assignment** : `created_by`, `updated_by`, `is_active` modifiables. |
| 39 | `web/backend/app/api/v1/factures.py` | 68-70 | **Mass Assignment** : Même problème. |
| 40 | `web/backend/app/api/v1/paiements.py` | 76-79 | **Mass Assignment** : Même problème. |
| 41 | `web/frontend/src/pages/Delivery.jsx` | 100 | **JSON sérialisation incorrecte** : Chaîne vide produit `'[""]'` au lieu de `null`. |
| 42 | `web/frontend/src/pages/Sales.jsx` | 649 | **Index comme React key** : Reconciliation incorrecte si réordonnement. |
| 43 | `web/frontend/src/pages/Home.jsx` | 346 | **Index comme React key** : Même problème pour la liste de notifications. |
| 44 | `web/frontend/src/pages/OrderTracking.jsx` | 187 | **Index comme React key** : Même problème pour le tableau de suivi. |
| 45 | `shared/services/api.js` + `apiClient.js` | 1-84 | **Instances axios dupliquées** : Logique de refresh token incohérente entre les deux. |
| 46 | `desk/src/components/layout/ResizablePanel.jsx` | 14,68 | **Unités ambiguës** : `maxWidth` utilisé comme % et pixels — comportement de resize incorrect. |
| 47 | `desk/src/pages/Inventory.jsx` | 55 | **Draft key instable** : Changement de key quand `batchTargets` change — perte du brouillon. |
| 48 | `web/backend/app/api/v1/super_admin.py` | 393, 396, 405 | **synchronize_session=False** : Objets stale dans la session SQLAlchemy après bulk update. |
| 49 | `desk/src/pages/Sales.jsx` | 328 | **Colonnes recréées inutilement** : `useMemo` dépend de `saleActionLoading` — re-renders excessifs. |
| 50 | `shared/utils/localStore.js` + `storageAdapter.js` | 15-41 | **getScopeId dupliqué** : Ignore la couche secureStore dans Electron. |
| 51 | `desk/electron/main.js` | 104-108 | **IPC handlers sans null check** : Crash si `win` est null après fermeture. |
| 52 | `desk/src/hooks/useFormDraft.js` | 134-143 | **Restore reset baseline** : `baselineRef` mis à null — re-save inutile. |

---

### Bugs Basse Sévérité (Low)

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 53 | `web/backend/app/security/tenant.py` | 111-114 | **isdigit() échoue pour négatifs** : Fallback inutile pour IDs négatifs. |
| 54 | `web/backend/app/api/v1/auth.py` | — | **Admin key en clair dans réponse** : ⛔ RÉSOLU — la clé d'administration a été supprimée (fonctionnalité bannie). |
| 55 | `web/backend/app/api/v1/super_admin.py` | 349-351 | **String literals pour rôles** : Incohérence avec `Role.ADMIN` utilisé ailleurs. |
| 56 | `web/backend/app/api/v1/super_admin.py` | 1223-1267 | **Pas de confirmation cascade** : Suppression admin = suppression silencieuse du tenant. |
| 57 | `web/frontend/src/pages/Purchases.jsx` | 171-178 | **HTML minifié fragile** : Lignes de tableau sans whitespace — parsing risqué. |
| 58 | `web/frontend/src/pages/AI.jsx` | 406 | **XSS potentiel** : URLs externes non validées avant rendu. |
| 59 | `web/frontend/src/pages/Documents.jsx` | 132 | **Filename non sanitized** : Path traversal possible via nom de fichier. |
| 60 | `web/frontend/src/pages/Dashboard.jsx` | 539-542 | **Crash potentiel** : Array `evolution` vide produit état undefined. |
| 61 | `desk/src/contexts/CartContext.jsx` | - | **Cart purement local** : Pas de sync web-desktop. |
| 62 | `desk/src/pages/Login.jsx` | 252-258 | **Quit button sur login** : Permet de quitter l'app depuis la page publique. |
| 63 | `desk/electron/main.js` | - | **Pas de single-instance lock** : Multiples instances possibles — conflits de données. |
| 64 | `desk/electron/preload.js` | 16-22 | **Sync file I/O** : `fs.writeFileSync` bloque le renderer. |
| 65 | `shared/services/api.js` | 172-191 | **Offline queue cosmétique** : Requête envoyée même hors ligne — échecs inutiles. |
| 66 | Multiple pages | - | **window.confirm** : Usage incohérent avec le ConfirmModal personnalisé du projet. |

---

### Recommandations Prioritaires

1. **Corriger les bugs critiques #1, #2** — Sécurité immédiate (auth, webhook)
2. **Corriger le bug #4 (Users.jsx)** — Crash bloquant la gestion des utilisateurs
3. **Unifier la gestion des tokens (#6, #8, #9)** — Utiliser `secureStore` partout dans Electron
4. **Corriger le Mass Assignment (#17)** — Faille de sécurité permettant l'escalade de privilèges
5. **Ajouter AbortController (#22, #23)** — Éviter les race conditions sur la recherche
6. **Nettoyer les memory leaks (#19, #20, #26)** — Intervals et timeouts non nettoyés

---

## Analyse Complémentaire — Bugs Data Integrity & Config

### Résumé des nouveaux bugs

| Sévérité | Data Integrity | Config/Sécurité | Total |
|----------|----------------|-----------------|-------|
| **Critique** | 1 | 3 | **4** |
| **Haute** | 4 | 3 | **7** |
| **Moyenne** | 6 | 5 | **11** |
| **Basse** | 1 | 1 | **2** |
| **Total** | **12** | **12** | **24** |

---

### Bugs Critiques Data Integrity & Config

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 67 | `web/backend/app/services/vente_service.py` | 102-128 | **Race condition stock** : Vérification et décrément du stock non atomiques — deux ventes concurrentes peuvent créer un stock négatif. |
| 68 | `web/backend/run.py` | 23 | **Werkzeug debugger en production** : `allow_unsafe_werkzeug=True` expose le debugger en prod. **[CORRIGE]** : `allow_unsafe_werkzeug=debug` (gated par `FLASK_DEBUG`). |
| 69 | `web/backend/run_socket.py` | 24 | **Werkzeug debugger en production** : Même problème pour le serveur WebSocket. **[CORRIGE]** : idem, gated par `FLASK_DEBUG`. |
| 70 | `web/backend/scripts/reset_enterprise_passwords.py` | 97, 19-41 | **Mots de passe en clair dans le code et logs** : Passwords hardcodés et affichés en console. |

---

### Bugs Haute Sévérité Data Integrity & Config

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 71 | `web/backend/app/services/paiement_service.py` | 55-89 | **Race condition paiement** : Deux paiements concurrents peuvent dépasser le montant de la facture (overpayment). |
| 72 | `web/backend/app/services/paiement_service.py` | 116-125 | **Statut facture stale** : Modification d'un paiement ne recalcule pas le statut de la facture. |
| 73 | `web/backend/app/services/paiement_service.py` | 55-89 | **Pas de validation montant max** : Un paiement peut dépasser le solde de la facture. |
| 74 | `web/backend/app/security/plan_limits.py` | 72-156 | **Race condition limite utilisateurs** : TOCTOU entre vérification et insertion — la limite d'abonnement peut être contournée. |
| 75 | `web/backend/.env` | 2-3 | **Secrets hardcodés** : SECRET_KEY et JWT_SECRET_KEY en clair dans le fichier .env. |
| 76 | `web/backend/.env` | 7 | **Mot de passe Redis faible** : `redispassword` est un mot de passe par défaut commun. |
| 77 | `web/backend/Dockerfile` | 1-18 | **Container en root** : Aucune directive USER — le container s'exécute en tant que root. |

---

### Bugs Moyenne Sévérité Data Integrity & Config

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 78 | `web/backend/app/models/stock.py` | 27-28 | **Audit trail stock incomplet** : Colonnes `stock_avant`/`stock_apres` jamais peuplées. |
| 79 | `web/backend/app/services/facturation_service.py` | 8-17 | **Référence facture non validée** : `issue_invoice` accepte une référence sans vérifier l'unicité. |
| 80 | `web/backend/app/services/vente_service.py` | 57-64 | **Collision référence vente** : Fenêtre de collision pour les références générées. |
| 81 | `web/backend/app/api/v1/users.py` | 147-153 | **Unicité email non atomique** : Vérification et insertion non atomiques — doublons possibles. |
| 82 | `web/backend/app/api/v1/ventes.py` | 117-134 | **Soft-delete incomplet vente** : Ne cascade pas vers Facture et Paiement. |
| 83 | `web/backend/app/services/comptabilite_service.py` | 136-148 | **Pas de validation double-entry** : Débits ≠ crédits non détectés. |
| 84 | `web/backend/app/api/v1/abonnements.py` | 184-205 | **Transaction split abonnement** : Commit paiement séparé du commit abonnement — incohérence possible. |
| 85 | `web/backend/.env` | 15 | **ENCRYPTION_KEY vide** : Le module encryption ne peut pas fonctionner sans clé. |
| 86 | `web/backend/.env` | 5 | **IP interne exposée** : `192.168.90.246` hardcodé dans CORS_ORIGINS. |
| 87 | `web/backend/Dockerfile` | 14 | **COPY . .** : Copie tout le répertoire incluant .env et logs. |
| 88 | `web/docker-compose.yml` | 13, 27 | **Ports exposés 0.0.0.0** : MySQL et Redis accessibles depuis l'extérieur. |

---

### Bugs Basse Sévérité Data Integrity & Config

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 89 | `web/backend/app/models/stock.py` | 17 | **MouvementStock orphelin** : FK sans ON DELETE — historique perdu si produit supprimé. |
| 90 | `web/backend/app/websockets/socket_events.py` | 27-52 | **Token WebSocket loggé** : Token auth potentiellement visible dans les logs engineio. |

---

## Résumé Global des Bugs

| Sévérité | Backend API | Frontend | Desktop/Shared | Data Integrity | Config | Total |
|----------|-------------|----------|----------------|----------------|--------|-------|
| **Critique** | 3 | 1 | 7 | 1 | 3 | **15** |
| **Haute** | 7 | 5 | 8 | 4 | 3 | **27** |
| **Moyenne** | 10 | 4 | 7 | 6 | 5 | **32** |
| **Basse** | 4 | 4 | 6 | 1 | 1 | **16** |
| **Total** | **24** | **14** | **28** | **12** | **12** | **90** |

---

### Plan de Correction Priorisé

#### Phase 1 — Sécurité Critique (P0)
1. Mass Assignment (#17) — Whitelist des champs modifiables **[CORRIGE]**
2. Endpoint public (#1) — Ajouter auth ou rate limiting strict
3. Webhook PAPI (#2) — Vérification signature HMAC **[CORRIGE]** (`papi/webhook.py` : `_verify_webhook_signature` avec `hmac.compare_digest`)
4. Hard-delete tenant (#3) — Soft-delete + backup + confirmation **[CORRIGE]** : endpoint hard-delete supprimé, seul soft-delete conservé
5. Werkzeug debugger (#68, #69) — Gating par `FLASK_DEBUG` **[CORRIGE]**
6. Mots de passe hardcodés (#70) — Nettoyer les scripts

#### Phase 2 — Data Integrity Critique (P0)
7. Race condition stock (#67) — Ajouter `SELECT FOR UPDATE`
8. Race condition paiement (#71) — Verrouiller la facture pendant le paiement
9. Race condition limites (#74) — Rendre la vérification atomique

#### Phase 3 — Crash & Memory (P1)
10. Users.jsx ReferenceError (#4) — Déplacer la fonction dans le composant
11. Memory leaks (#19, #20, #26) — Cleanup intervals/timeouts
12. Tokens Electron (#6, #8, #9) — Unifier vers secureStore

#### Phase 4 — Stabilité (P2)
13. Race conditions recherche (#22, #23) — AbortController
14. Stale closures (#21) — Corriger les dépendances useEffect
15. Services dupliqués (#7) — Consolidation desktop/shared

---

## Analyse Complémentaire — WebSockets, AI, Tasks, Sync

### Résumé des nouveaux bugs

| Sévérité | WebSockets | AI | Tasks | Sync/Offline | Total |
|----------|------------|-----|-------|--------------|-------|
| **Critique** | 1 | 0 | 1 | 2 | **4** |
| **Haute** | 2 | 3 | 3 | 7 | **15** |
| **Moyenne** | 3 | 4 | 3 | 7 | **17** |
| **Basse** | 1 | 1 | 0 | 1 | **3** |
| **Total** | **7** | **8** | **7** | **17** | **39** |

---

### Bugs Critiques WebSockets, AI, Tasks, Sync

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 91 | `shared/websockets/socketClient.js` | 27-31 | **Auth WebSocket mismatch** : Le client émet `authenticate` après connexion, mais le serveur attend le token dans `auth` pendant le handshake — toutes les connexions WebSocket échouent. |
| 92 | `web/backend/app/tasks/emails.py` | 24-31 | **Emails hardcodés** : `send_payment_confirmation` et `send_stock_alert` envoient à `client@example.com` / `stock@example.com` au lieu des vrais destinataires. |
| 93 | `shared/utils/syncEngine.js` | 80-88 | **Perte file sync** : Quand `localStorage` quota exceeded, la file est sauvegardée en mémoire mais `getQueue()` lit l'ancien localStorage — perte de données. |
| 94 | `shared/storage/authStorage.js` | 10-66 | **Tokens en clair** : `authStorage` écrit directement dans `localStorage` sans utiliser `storageAdapter` — tokens exposés sur desktop. |

---

### Bugs Haute Sévérité WebSockets, AI, Tasks, Sync

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 95 | `web/backend/app/websockets/socket_events.py` | 60-84 | **Validation tenant manquante** : Les handlers `subscribe:*` acceptent `tenant_id` du client sans vérifier l'appartenance — fuite inter-tenant. |
| 96 | `shared/websockets/socketClient.js` | 49-74 | **Memory leak listeners** : `disconnect()` ne nettoie pas la Map `listeners` — accumulation sur chaque reconnexion. |
| 97 | `web/backend/app/ai/previsions.py` | 131 | **Fuite inter-tenant** : Requête `MouvementStock` sans filtre `tenant_id` — données d'autres tenants dans les prévisions. |
| 98 | `web/backend/app/ai/anomalies.py` | 14-17 | **Fuite inter-tenant** : Même problème pour la détection d'anomalies. |
| 99 | `web/backend/app/ai/training.py` | 85-98 | **Modèle factice** : Le modèle stocké a des valeurs hardcodées (`avg_consumption_rate: 2.5`) sans vrai calcul. |
| 100 | `web/backend/app/tasks/backups.py` | 11 | **Backup SQLite corrompu** : `shutil.copy2` copie pendant que SQLite écrit — backup inconsistent. |
| 101 | `web/backend/app/tasks/emails.py` | 18 | **SMTP sans TLS** : Credentials et contenu envoyés en clair. |
| 102 | `web/backend/app/tasks/backups.py` | 5-12 | **Pas de gestion d'erreur backup** : Aucun try/except — échec silencieux. |
| 103 | `shared/utils/syncEngine.js` | 166-172 | **Retry count perdu** : `entry.retries` incrémenté en mémoire mais `getQueue()` relit le localStorage — compteur perdu. |
| 104 | `shared/utils/syncEngine.js` | 119-135 | **Pas d'idempotence** : Double-click crée des doublons dans la file — records dupliqués au sync. |
| 105 | `shared/storage/storageAdapter.js` | 28-41 | **getScopeId ignore secureStore** : Lit `localStorage` brut — fuite de données entre users sur desktop. |
| 106 | `shared/storage/authStorage.js` vs `tokenStore.js` | global | **Sécurité incohérente** : NEW keys chiffrées, LEGACY keys en clair — posture sécurité inconsistante. |
| 107 | `shared/utils/localStore.js` | global | **Storage split** : Duplique `storageAdapter` sans `secureStore` — deux layers non synchronisés. |
| 108 | `shared/hooks/useRealtime.js` | 105-122 | **Polling overlap** : `setInterval` n'attend pas la fin du poll précédent — events doublés ou manqués. |

---

### Bugs Moyenne Sévérité WebSockets, AI, Tasks, Sync

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 109 | `shared/realtime/socketClient.js` | 56-64 | **Listener pageshow accumulé** : Enregistré au module load sans cleanup — doublons sur navigation. |
| 110 | `shared/realtime/socketClient.js` | 72-84 | **Polling s'arrête définitivement** : Quand le token expire, pas de restart après refresh. |
| 111 | `shared/realtime/socketClient.js` | 75 | **URL malformée** : `replace('/api/v1', '')` produit double slash si trailing slash. |
| 112 | `web/backend/app/ai/previsions.py` | 98-107 | **Seuils tendance absolus** : Slope thresholds fixes — incorrect pour grandes valeurs. |
| 113 | `web/backend/app/ai/previsions.py` | 56-58 | **Crash datetime** : `v.created_at.date()` suppose datetime — crash si string. |
| 114 | `web/backend/app/ai/recommendations.py` | 23-28 | **Score négatif** : Quand `seuil_alerte == 0`, score négatif casse le tri. |
| 115 | `web/backend/app/tasks/reports.py` | 20, 33, 43 | **TypeError None** : `float(s.total_ttc)` crash si valeur NULL. |
| 116 | `web/backend/app/tasks/reports.py` | 11 | **Date invalide** : `strptime` sans try/except — crash sur date malformée. |
| 117 | `web/backend/app/tasks/emails.py` | 18-21 | **Pas de gestion erreur SMTP** : Échec sans retry ni alerte. |
| 118 | `web/backend/app/tasks/backups.py` | global | **Pas de rétention** : Backups gardés indéfiniment — exhaustion disque. |
| 119 | `shared/utils/syncEngine.js` | global | **File non bornée** : Croissance illimitée — quota exceeded. |
| 120 | `shared/utils/syncEngine.js` | 276-282 | **Merge superficiel** : Shallow merge — perte données nested. |
| 121 | `shared/contexts/SyncContext.jsx` | 75-109 | **State update after unmount** : `setIsSyncing` après await sans guard. |
| 122 | `shared/services/syncApi.js` | 31-35 | **Pas de conflit resolution** : 409 traité comme erreur générique — données écrasées. |
| 123 | `shared/storage/storageAdapter.js` | 82-96 | **memoryFallback non nettoyé** : `removeKey` ne cleanup pas si secureStore existe. |
| 124 | `shared/storage/storageAdapter.js` / `localStore.js` | 10, 5 | **memoryFallback partagé** : Map sans scoping — fuite entre comptes. |
| 125 | `shared/storage/tokenStore.js` | 31-63 | **Double write NEW/LEGACY** : Incohérence si un write échoue. |
| 126 | `shared/hooks/useRealtime.js` | 137-139 | **Stale state après reconnect** : `sinceRef` jamais reset — events manqués. |
| 127 | `shared/` + `desk/src/shared/` + `desk/shared/` | global | **Fichiers dupliqués divergents** : Copie de code qui diverge — fixes non propagées. |

---

### Bugs Basse Sévérité WebSockets, AI, Tasks, Sync

| # | Fichier | Ligne | Description |
|---|---------|-------|-------------|
| 128 | `shared/realtime/socketClient.js` | 24-28 | **Erreurs ignorées** : `emitLocal` catch vide — bugs indébuggables. |
| 129 | `web/backend/app/ai/training.py` | 71-73, 93-95 | **Pas de gestion erreur pickle** : Disk-full non géré. |
| 130 | `shared/hooks/useOnlineStatus.js` | 7-12 | **Online state conflict** : `navigator.onLine` vs `syncEngine.isOnline()` — états contradictoires. |

---

## Résumé Global Complet

| Sévérité | Backend API | Frontend | Desktop/Shared | Data Integrity | Config | WS/AI/Tasks/Sync | Total |
|----------|-------------|----------|----------------|----------------|--------|------------------|-------|
| **Critique** | 3 | 1 | 7 | 1 | 3 | 4 | **19** |
| **Haute** | 7 | 5 | 8 | 4 | 3 | 15 | **42** |
| **Moyenne** | 10 | 4 | 7 | 6 | 5 | 17 | **49** |
| **Basse** | 4 | 4 | 6 | 1 | 1 | 3 | **19** |
| **Total** | **24** | **14** | **28** | **12** | **12** | **39** | **129** |

---

### Plan de Correction Priorisé (Complet)

#### Phase 1 — Sécurité Critique (P0)
1. Mass Assignment (#17) — Whitelist des champs modifiables **[CORRIGE]**
2. Endpoint public (#1) — Ajouter auth ou rate limiting strict
3. Webhook PAPI (#2) — Vérification signature HMAC **[CORRIGE]**
4. ~~Hard-delete tenant (#3) — Soft-delete + backup + confirmation~~ **[CORRIGE]** : endpoint hard-delete supprimé, seul soft-delete conservé
5. Werkzeug debugger (#68, #69) — Supprimer `allow_unsafe_werkzeug`
6. Mots de passe hardcodés (#70) — Nettoyer les scripts
7. Fuite inter-tenant AI (#97, #98) — Ajouter filtre tenant_id
8. Fuite inter-tenant WebSocket (#95) — Valider l'appartenance tenant

#### Phase 2 — Data Integrity Critique (P0)
9. Race condition stock (#67) — Ajouter `SELECT FOR UPDATE`
10. Race condition paiement (#71) — Verrouiller la facteur pendant le paiement
11. Race condition limites (#74) — Rendre la vérification atomique
12. Perte file sync (#93) — Fixer le fallback mémoire
13. Pas d'idempotence sync (#104) — Ajouter dédoublonnage

#### Phase 3 — Crash & Memory (P1)
14. Users.jsx ReferenceError (#4) — Déplacer la fonction dans le composant **[CORRIGE]** : `isEmployeeLimitReached` définie dans le composant
15. Memory leaks (#19, #20, #26) — Cleanup intervals/timeouts
16. Tokens Electron (#6, #8, #9) — Unifier vers secureStore **[CORRIGE]** : `storageAdapter` + `tokenStore` + `authStorage` utilisent `secureStore` en Electron
17. WebSocket auth mismatch (#91) — Corriger le handshake

#### Phase 4 — Stabilité (P2)
18. Race conditions recherche (#22, #23) — AbortController
19. Stale closures (#21) — Corriger les dépendances useEffect
20. Services dupliqués (#7) — Consolidation desktop/shared
21. Polling overlap (#108) — Attendre la fin du poll précédent
22. Backup SQLite (#100) — Utiliser `sqlite3 .backup` au lieu de copy