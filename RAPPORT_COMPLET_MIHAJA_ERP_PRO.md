# RAPPORT COMPLET — MIHAJA_ERP_PRO
## Architecture · Cahier des charges · Bugs · Anomalies · Non-implémenté · À améliorer

| Champ | Valeur |
|---|---|
| **Projet** | MIHAJA_ERP_PRO — ERP commercial multi-tenant (Madagascar, devise `MGA`/`Ar`) |
| **Date du rapport** | 2026-09-15 |
| **Branche** | `V0` |
| **Commit de référence** | `16143705` (docs: rapport QA final campagne P0/P1 du 14/09/2026) |
| **Périmètre analysé** | `web/backend`, `web/frontend`, `desk` (Electron), `super-admin`, `mobile` (Expo), `shared`, `docs/`, scripts |
| **Méthode** | Consolidation des audits antérieurs + **vérification directe du code** (lecture de fichiers, recherche ciblée, exécution de tests ciblés, inspection du manifeste git) |
| **Nature** | Document unique remplaçant les documents d'analyse supprimés (voir §1.2) |

> **Légende des statuts utilisés dans ce rapport**
> - ✅ **CORRIGÉ (vérifié)** — constaté corrigé dans le code lors de la rédaction de ce rapport.
> - 🟢 **CORRIGÉ (déclaré)** — marqué corrigé par un audit antérieur, non re-vérifié ligne à ligne ici.
> - ❌ **OUVERT** — anomalie confirmée présente dans le code actuel.
> - 🟠 **PARTIEL** — correction incomplète ou dépendante de l'environnement.
> - 🔍 **À RE-VÉRIFIER** — signalé par un audit antérieur, non confirmé/infirmé dans cette passe (ne pas traiter comme un fait).

---

## 1. Objet, sources et traçabilité

### 1.1 Objet
Ce document est la **source de vérité unique** sur l'état du projet : architecture réelle, couverture du cahier des charges, bugs existants, anomalies, fonctionnalités non implémentées ou partielles, et pistes d'amélioration priorisées.

### 1.2 Documents consolidés puis supprimés (le 2026-09-15)
| Document supprimé | Contenu repris dans ce rapport |
|---|---|
| `Analyse_Projet_Actuel.md` (787 lignes) | Registre de 129 bugs, structure, modules, plan de correction |
| `design_erp.md` | Design/architecture, rôles, stack, 66 bugs |
| `fichier_non_modifier.md` | Architecture complète de référence IA |
| `SHARED_ARCHITECTURE.md` | Architecture du code partagé web/desktop + sync hors-ligne |
| `INSTRUCTION.md` | Règles d'ingénierie anti-hallucination (conservées en §11 « Règles de travail ») |
| `plan_subscription.md` | Système d'activation/désactivation d'abonnement (30 j de grâce) |
| `RAPPORT_QA_FINAL_2026-09-14.md` | Campagne P0/P1, idempotence factures, quotas, i18n |
| `RAPPORT_TEST_E2E_2026-09-14.md` | Tests E2E Playwright, blocage SC1, resync SQLite |
| `docs/technical/WEB_DESKTOP_SYNC.md` | Synchronisation web/desktop |
| `docs/superpowers/plans/*.md`, `docs/superpowers/specs/*.md` | Spécification/plan abonnement |
| `AUDIT_CONFORMITE_CAHIER_DES_CHARGES.md`, `AUDIT_ARCHITECTURE.md`, `ARCHITECTURE_UPDATE_REPORT.md`, `RAPPORT_FINAL_AUDIT.md`, `RAPPORT_ETAPE_0_LIVREUR.md` | Supprimés du disque lors d'une passe antérieure ; contenu (dont l'audit de conformité au cahier des charges) récupéré depuis l'historique git et intégré en §4 |

### 1.3 Sources techniquement vérifiées dans cette passe
- Inventaire des fichiers : `web/backend/app/api/v1/` (30 modules de namespace), `app/models/` (43 modèles), `app/services/` (24 modules), `tests/` (**438 tests collectés**), `migrations/versions/` (16 révisions Alembic).
- Exécution de tests ciblés : `pytest tests/test_facturation_idempotence.py tests/test_auth.py -q` → **5 passed, 2 warnings, 22,81 s**.
- Vérification de code sur les points sensibles : `rate_limit.py`, `authStorage.js`, `preload.js`, `emails.py`, `socket_events.py`, `vente_service.py`, `paiement_service.py`, `public.py`, `comptabilite.py` (résultats), `entrepots.py`, `super-admin/src/pages/Tenants.jsx`, `web/frontend/src/pages/Users.jsx`, `web/frontend/src/index.js`, `run.py`, `settings.py`, `.gitignore`, `git ls-files`.

---

## 2. Vue d'ensemble du projet

**MIHAJA_ERP_PRO** est un ERP commercial **multi-tenant** : une instance, plusieurs entreprises clientes isolées par `tenant_id`. Il couvre : ventes, stocks, achats, clients/fournisseurs, comptabilité, RH, livraison, documents, paiements mobile money, IA d'aide à la décision, abonnements par entreprise, marketplace publique et console Super Admin privée.

**Séparation des rôles (règle métier structurante)**
```
SUPER ADMIN  =|  TENANT == ADMIN  =|  UTILISATEUR / EMPLOYÉ
```
- **SUPER_ADMIN** : propriétaire de la plateforme — tenants, plans, abonnements, paiements, audit. Interface **privée**.
- **ADMIN du tenant** : crée/administre ses comptes (Manager, Sales, Stock, Comptable, RH, User…) — le nombre d'utilisateurs est **contraint par l'abonnement** du tenant, pas par la page d'inscription.
- **UTILISATEUR** : catalogue public, commande, suivi — sans abonnement requis.

### 2.1 Stack technique (réelle)
| Couche | Technologie |
|---|---|
| Backend | Python 3.11, Flask 2.3, Flask-RESTx (Swagger `/docs`), Flask-JWT-Extended, Flask-SQLAlchemy, SQLAlchemy 2.0, Flask-Migrate/Alembic, Flask-CORS, Flask-SocketIO (optionnel) |
| Base de données | SQLite (dev, `erp.db`) / PostgreSQL (prod, `DATABASE_URL`) |
| Cache / queue | Redis + Celery 5.3 (`web/requirements.txt`) |
| Frontend web | React 18, Axios, React Router, React Hook Form, Framer Motion, React Toastify, Yup |
| Desktop | Electron 38 + React 18 + `@tanstack/react-virtual`, `safeStorage` |
| Super Admin | React 18 + Chart.js |
| Mobile | React Native 0.86 + Expo (React 19, navigation bottom-tabs/native-stack, `expo-secure-store`) |
| IA | Python pur (numpy/pandas, régression linéaire, z-score) + modèles `.pkl` (`app/ai/models/`) |
| Documents | reportlab (PDF), openpyxl (Excel), qrcode, python-barcode, Pillow |
| Tests / qualité | pytest, pytest-cov, factory-boy, Faker, black, flake8, mypy, isort |

**Points d'entrée**
| Service | URL |
|---|---|
| API backend | `http://localhost:5000/api/v1` — Swagger `/docs/` |
| Health / Ready / Monitor | `/health`, `/ready`, `/monitor` (ajoutés en P0, visibles via tunnel) |
| Frontend web | `http://localhost:3000` |
| Super Admin | `http://localhost:3001` |
| Desktop | Application Electron (client natif) |
| Mobile | Expo (`npm start` depuis `mobile/`) |
| Socket.IO | `ws://<host>:<port>/socket.io` (si `ENABLE_SOCKETIO`) |

---

## 3. Architecture détaillée

### 3.1 Arborescence fonctionnelle
```
MIHAJA_ERP_PRO/
├── web/
│   ├── requirements.txt, docker-compose.yml
│   ├── backend/                    # API Flask
│   │   ├── run.py                  # Entrée Flask (+ Socket.IO si activé)
│   │   ├── erp.db                  # SQLite dev
│   │   ├── app/
│   │   │   ├── api/v1/             # 30 modules de namespace REST
│   │   │   ├── models/             # 43 modèles SQLAlchemy
│   │   │   ├── services/           # 24 modules de logique métier
│   │   │   ├── security/           # tenant, permissions, plans, plan_limits, rate_limit, encryption, admin_devices
│   │   │   ├── ai/                 # prévisions, anomalies, recommandations, assistant, insights, training
│   │   │   ├── tasks/              # backups, emails, rapports (Celery)
│   │   │   ├── utils/              # PDF, Excel, QR, barcodes, audit, validation, modèles système
│   │   │   ├── websockets/ + realtime/   # Socket.IO
│   │   │   └── config/             # settings.py, database.py
│   │   ├── migrations/versions/    # 16 révisions Alembic
│   │   └── tests/                  # 438 tests collectés
│   └── frontend/                   # React (32 pages)
├── desk/                           # Electron (30 pages) + desk/shared (copie) + desk/src/shared (réexport)
├── shared/                         # Code partagé web/desktop (auth, sync, storage, realtime)
├── super-admin/                    # Console plateforme (11 pages)
├── mobile/                         # App React Native / Expo (4 écrans)
├── scripts/                        # migrations localStorage, utilitaires
├── docs/                           # user / technical / api (README conservés)
└── graphify-out/                   # Graphe de connaissance généré (outil)
```

### 3.2 Multi-tenancy
- **Modèle partagé + schéma partagé** : les tables métier héritent de `BaseModel`/`BaseTenantModel` avec `tenant_id` (FK `tenants.id`, indexé), `created_at/updated_at`, `is_active` (soft delete), `created_by/updated_by`.
- **Résolution du tenant** : le `before_request` résout `g.current_tenant` (claim JWT `tenant_id` prioritaire, sinon en-tête `X-Tenant-Slug`).
- **Décorateurs** : `tenant_required`, `tenant_required_readonly`, `subscription_required`, `permission_required(...)`.
- **Filtre automatique** : listener SQLAlchemy appliquant `tenant_id` aux requêtes (à conserver strictement).
- **Règle** : toute nouvelle route/modèle métier doit passer par ce dispositif. Un `db.session.query` brut sans helper constitue un risque de fuite inter-tenant.

### 3.3 Sécurité & RBAC
- JWT **access (1 h) + refresh (30 j)**, `JWT_SECRET_KEY` **obligatoire** (échec de démarrage explicite si absent), blocklist de tokens (`token_blocklist`), réinitialisation de mot de passe par **digest SHA-256 indexé** (aucun scan global de tokens).
- RBAC granulaire : `roles.py`, `permissions.py`, `role_permission.py`, `permission_matrix.py`, presets, rôles personnalisés, matrice de permissions backend → frontend.
- Appareils admin (`admin_devices`) : premier appareil auto-enregistré, suivi `last_seen`.
- Chiffrement : `security/encryption.py` (clés PAPI chiffrées en base), `password_policy.py`, `rate_limit.py` (fail-closed en production, fallback mémoire en dev).
- Audit : `audit_log.py` (25+ types d'actions) + `utils/audit.py`.
- Abonnements/plans : `plans.py`, `plan_limits.py` (quotas **strictement côté backend**, 403 explicite au dépassement, aucune suppression de données au passage Pro → Gratuit), `subscription_audit` (audit trail des changements de plan).

### 3.4 Namespaces API (30 modules dans `app/api/v1/`)
`abonnements`, `achats_devis`, `admin_devices`, `ai`, `auth`, `clients`, `comptabilite` (dont sous-namespace `resultats`), `dashboard`, `desk`, `documents`, `employes`, `entrepots`, `factures`, `fournisseurs`, `livraisons`, `notifications`, `paiements`, `papi`, `permissions`, `produits`, `public`, `rh`, `roles`, `stocks`, `super_admin`, `tenants`, `tenant_papi`, `test` (**conditionnel** : monté uniquement si `DEBUG` ou `TESTING`), `users`, `ventes`.

### 3.5 Modèles de données (43 modèles)
- **Core** : `Tenant`, `Utilisateur`, `Role`, `RolePermission`, `AuditLog`, `AdminDevice`, `TokenBlocklist`, `PasswordResetToken`, `Notification`, `DeskState`, `Abonnement`, `SubscriptionAuditTrail`.
- **Produits/Stocks** : `Produit`, `Stock`, `MouvementStock`, `Entrepot`, `StockEntrepot` (**multi-entrepôts + `stock_min`/`stock_max` — voir §4.2**).
- **Ventes** : `Vente`, `LigneVente`, `Facture`, `CommandeClient`, `DevisAvoirBL`.
- **Achats/Fournisseurs** : `Fournisseur`, `CommandeFournisseur`, `CommandeAchat`, `LigneAchat`, `FactureFournisseur`.
- **Clients** : `Client` (11 types).
- **Paiements** : `Paiement`, `PaymentEvent`.
- **RH** : `Employe`, `Presence`, `Salaire`, `Prime`, `Stagiaire`.
- **Comptabilité** : `CompteComptable`, `EcritureComptable`, `Tresorerie`.
- **Livraison** : `Livraison`, `Livreur`, `Vehicule`, `Itineraire`, `SuiviLivraison`.
- **Documents** : `DocumentGenere`, `ModeleDocument`.

### 3.6 Services métier (24 modules)
`abonnement_service`, `achat_service`, `auth_service`, `base_service` (CRUD générique + whitelist `PROTECTED_FIELDS`), `client_service`, `commande_papi_service`, `commande_service`, `comptabilite_service` (dont `ResultatService`), `dashboard_service`, `devis_avoir_service`, `document_service`, `email_service`, `facturation_service`, `fournisseur_service`, `livraison_service`, `modele_seed_service`, `notification_service`, `paiement_service`, `produit_service`, `rh_service`, `stagiaire_service`, `tenant_papi_service`, `vente_service`, + `papi/` (`client`, `errors`, `payment`, `webhook`).

### 3.7 Flux applicatifs principaux
1. **Requête authentifiée** : `Authorization: Bearer` + `X-Tenant-Slug` → résolution tenant → décorateur (`tenant_required` / `permission_required`) → filtre tenant → service → commit → audit.
2. **Création produit** : `POST /api/v1/produits` → `produit_service` → `Produit` (tenant_id déterminé côté serveur) → QR/code-barres générés.
3. **Vente** : `POST /api/v1/ventes` → `vente_service` (lignes, décrément stock **sous verrou** via `with_for_update()`, facture, écriture comptable) → notifications.
4. **Commande publique** : `/public` (sans JWT **par conception**) → `@rate_limit(30, 300)` + idempotence `Idempotency-Key` (cache TTL 600 s, plafonné) → validation après paiement complet (PAPI) → QR/code-barre.
5. **Hors-ligne (desktop)** : mutation échouée → `syncEngine.enqueue` → rejouée à la reconnexion (stratégie « dernier écrivain gagne »).
6. **IA** : `/api/v1/ai/*` → prévisions/ruptures/anomalies/recommandations/assistant, avec gating par domaine (`ai_permissions.py`).
7. **Abonnement** : plan actif + quotas → `plan_limits` (403 si quota dépassé) → rétrogradation Gratuit après 30 j de grâce → audit trail (`SubscriptionAuditTrail`, déclencheur `automatique`/`manuel`).

### 3.8 Temps réel (Socket.IO)
- Serveur : `websockets/socket_events.py` + `realtime/socket_server.py`, activé par `ENABLE_SOCKETIO` (`run.py` détecte `app.socketio`).
- Authentification au handshake via JWT, rooms `tenant:<id>` / `user:<id>`, **validation d'appartenance** (`_tenant_belongs_to_user`) — contrôle anti-fuite inter-tenant.
- Client partagé : `shared/websockets/socketClient.js` + `shared/realtime/socketClient.js`.

### 3.9 Synchronisation web / desktop (offline-first)
- `shared/` : `contexts/` (`AuthContext`, `SyncContext`), `hooks/` (`useAuth`, `useOnlineStatus`, `useRealtime`, `useRealtimeSync`), `storage/` (`authStorage`, `storageAdapter`, `tokenStore`), `utils/` (`syncEngine`, `hydration`, `localStore`, `migrateLocalStorage`), `services/` (`api`, `apiClient`, `preferences`, `syncApi`).
- File d'attente de mutations persistée, hydratation par timestamps, résolution de conflit « dernier écrivain gagne ».
- Migration progressive depuis les anciennes clés localStorage (`scripts/migrate_localStorage_sync.js`, marqueur `erp.migration.*`).

### 3.10 Répartition des interfaces
| Interface | Pages / écrans | Détail |
|---|---|---|
| **web/frontend** (32 pages) | Accounting, AI, Cart, Catalogue, Checkout, Clients, Contact, Dashboard, Delivery, Documentation, Documents, Home, HR, Inventory, Invoices, OrderTracking, Payments, PaymentSettings, Permissions, ProductDetail, Products, Profile, Purchases, Roles, Sales, Subscription, Suivi, SuperAdmin, SuperAdminProfile, Suppliers, UserOrders, Users |
| **desk** (30 pages) | Mêmes pages que le web (sans Contact/Documentation/PaymentSettings/SuperAdmin* selon le cas) + layout desktop (sidebar, topbar, DataTable virtualisé, FilterPanel) |
| **super-admin** (11 pages) | Audit, Dashboard, EmailConfig, LoginPage, PaymentSettings, Plans, Profile, Subscriptions, TenantDetail, Tenants, Users |
| **mobile** (4 écrans) | Home, Vente, Inventaire, Livraison + `navigation/RootNavigator`, `context/AuthContext`, `api/client`, `storage/session` (tokens en `expo-secure-store`) |

---

## 4. Cahier des charges : conformité et traçabilité

Contexte : cahier des charges « distribution / commerce de gros » (TIA INFO WHOLESALE), ERP pour Madagascar (MGA, mobile money). La dernière évaluation d'audit (2026-09-11) donnait **~93 % de conformité** avec 4 écarts. Ces 4 écarts ont **depuis été traités** (vérifié dans le code lors de cette passe).

### 4.1 Exigences couvertes (vérifiées)
| Domaine | Exigence | Statut | Preuve / implémentation |
|---|---|---|---|
| Produits | Catégories, sous-catégories, familles, marques, modèles, unités | ✅ | `models/produit.py` |
| Produits | Codes-barres + code interne + QR code + photos | ✅ | `code_barre`, `code_interne`, `qr_code_data`, `image_url` ; `utils/barcode_generator.py`, `utils/qr_generator.py` |
| Produits | Prix multiples (achat/vente HT/TTC, gros, revendeur, demi-gros, TVA, marge) | ✅ | champs `prix_*`, `taux_tva`, `marge_standard` |
| Fournisseurs | CRUD, commandes, factures, paiements, historique | ✅ | `fournisseur.py`, `commande_fournisseur.py`, `facture_fournisseur.py`, `fournisseur_service.py`, `api/v1/fournisseurs.py` |
| Achats | Bons de commande, réception, contrôle d'écart | ✅ | `achat_service.py`, `api/v1/achats_devis.py`, page `Purchases.jsx` (`quantite_recue` vs `quantite_commandee`) |
| Achats | Entrée en stock automatique à la réception | ✅ | mouvement `ENTREE` créé par le service d'achat |
| Stocks | Mouvements (ENTREE, SORTIE, INVENTAIRE, AJUSTEMENT, RETOUR, TRANSFERT) | ✅ | `models/stock.py` |
| Stocks | Alertes seuil d'alerte + seuil critique | ✅ | `seuil_alerte`, `seuil_critique` ; `stock_min`/`stock_max` |
| Stocks | Valorisation du stock | ✅ | `Produit.valeur_stock = quantite_stock × prix_achat_ht` |
| Stocks | **Multi-entrepôts** (écart E1) | ✅ **RÉSOLU** | `models/entrepot.py`, `models/stock_entrepot.py`, `api/v1/entrepots.py` (CRUD entrepôts + stock par entrepôt avec `seuil_min`/`seuil_max`), migration `07efbe5e9c15_add_entrepots_stock_entrepot_and_stock_.py` |
| Stocks | **Stock maximum** (écart E2) | ✅ **RÉSOLU** | champs `stock_min`/`stock_max` + `seuil_max` par entrepôt |
| Clients | 11 types (boutique, revendeur, semi-grossiste, grossiste, entreprise, épicerie, supermarché, restaurant, hôtel, institution, particulier) | ✅ | `models/client.py` |
| Clients | Historique, solde, plafond de crédit, échéance, points de fidélité | ✅ | relation `ventes` + `solde`, `plafond_credit`, `echeance_credit`, `points_fidelite` |
| Ventes | Gros/détail, devis, bons de livraison, avoirs | ✅ | `vente.py` (`type_vente`), `devis_avoir_bl.py` (`DevisService`, `BonLivraisonService`, `AvoirService`) |
| Paiements | Espèces, virement, chèque, MVola, Orange Money, Airtel Money ; paiements partiels | ✅ | `models/paiement.py`, `_recompute_facture_status` |
| Paiements | Passerelle mobile money (PAPI) par tenant | ✅ | `api/v1/papi.py`, `tenant_papi.py`, `services/papi/*`, `tenant_papi_service.py` (clés chiffrées) |
| Comptabilité | Plan comptable, écritures, journal, trésorerie | ✅ | `comptabilite_service.py`, `api/v1/comptabilite.py` (`/ecritures/journal`) |
| Comptabilité | **Résultats (produits − charges par période)** (écart E3) | ✅ **RÉSOLU** | namespace `resultats` (`/api/v1/resultats/`) + `ResultatService` avec périodes validées |
| Livraison | Livreurs, véhicules, itinéraires, livraisons, suivi | ✅ | `livreur.py`, `vehicule.py`, `itineraire.py`, `livraison.py`, `suivi_livraison.py`, pages `Delivery.jsx`/`Suivi.jsx` |
| Livraison | Compte livreur (relation `Livreur ↔ Utilisateur`) | ✅ | 7 tests dédiés ; défense en profondeur API + service + listener ORM |
| RH | Employés, présences, salaires, primes, stagiaires | ✅ | `rh.py`, `employes.py`, page `HR.jsx` |
| Documents | Modèles (facture, devis, contrat, BL, avoir), génération PDF | ✅ | `modele_document.py`, `document_genere.py`, `utils/modeles_systeme.py`, `utils/pdf_generator.py` |
| Dashboard | Ventes jour/mois, CA, bénéfice, top produits/clients, évolution 7 j, alertes, créances | ✅ | `dashboard_service.py`, `api/v1/dashboard.py` |
| IA | Prévisions ventes/stocks, ruptures, anomalies, recommandations, assistant, insights | ✅ | `app/ai/*`, `api/v1/ai.py`, gating `ai_permissions.py` |
| Sécurité | JWT, RBAC, audit, chiffrement, rate limiting, backups | ✅ (réserve) | voir §5.2 (planification backups) |
| Abonnements | Plans, quotas, demande/paiement/renouvellement, historique, rétrogradation 30 j | ✅ | `abonnement_service.py`, `plan_limits.py`, `SubscriptionAuditTrail`, endpoints Super Admin |
| Marketplace | Catalogue public multi-entreprises, commande, suivi, QR/code-barre | ✅ | `api/v1/public.py`, pages `Catalogue`, `Cart`, `Checkout`, `OrderTracking` |
| Mobile | **Application mobile native** (écart E4) | ✅ **RÉSOLU** | `mobile/` : React Native + Expo (Consultation/Vente/Inventaire/Livraison), tokens `expo-secure-store`, `mobile/dist-web` |

### 4.2 Écarts du cahier des charges : état au 2026-09-15
| # | Écart initial | État |
|---|---|---|
| E1 | Multi-entrepôts absent | ✅ Résolu (modèle + API + migration) |
| E2 | Stock maximum absent | ✅ Résolu (`stock_min`/`stock_max`, `seuil_max` par entrepôt) |
| E3 | Résultats comptables absents | ✅ Résolu (namespace `resultats` + `ResultatService`) |
| E4 | Pas d'app mobile / PWA désactivée | ✅ Résolu côté mobile natif (Expo) ; **PWA web toujours désactivée** (voir anomalie A1, §6) |

### 4.3 Réserves fonctionnelles restantes sur le cahier des charges
1. **Contrôle qualité par lot** à la réception : non implémenté (contrôle quantitatif seulement) — jugé suffisant pour le périmètre initial.
2. **Sauvegarde automatique** : code de backup présent, **pas de `celery beat schedule`** → dépend d'un ordonnanceur externe (cron) pour être réellement « automatique ».
3. **Résultats comptables** : endpoint dédié existant ; à confirmer que la page `Accounting.jsx` consomme bien `/api/v1/resultats/` (aucune page « Résultats » distincte identifiée).
4. **Mobile** : 4 écrans (Home, Vente, Inventaire, Livraison) — périmètre volontairement réduit ; pas d'Achats/RH/Comptabilité/Admin sur mobile.
5. **Multi-entrepôts** : modèle et API présents ; la **ventilation automatique du stock par entrepôt lors des ventes** et l'UI dédiée restent à confirmer (risque de double comptage `Produit.quantite_stock` vs `StockEntrepot.quantite`).

---

## 5. État d'implémentation : fait / partiel / non fait

### 5.1 Implémenté et opérationnel (vérifié)
- Multi-tenancy avec isolation par `tenant_id` (décorateurs + filtre + tests dédiés).
- Authentification JWT (access/refresh) + blocklist + reset mot de passe sans énumération + politique de mot de passe.
- RBAC complet : rôles prédéfinis, rôles personnalisés, permissions granulaires, matrice de permissions, gating 403 côté écrans.
- Modules métier complets : produits, stocks (+ multi-entrepôts), clients, fournisseurs, achats, ventes/devis/BL/avoirs, factures (idempotence 1 facture active par vente), paiements (+ PAPI), comptabilité (+ résultats), RH, livraison (+ compte livreur), documents/PDF, dashboard.
- Marketplace publique : catalogue multi-entreprises, panier, commande, suivi, QR/code-barre.
- Abonnements : plans, quotas backend (403), délai de grâce 30 j, rétrogradation Gratuit, audit trail, actions Super Admin.
- IA : prévisions, ruptures de stock, anomalies, recommandations, assistant, insights.
- Interfaces : web (32 pages), desktop Electron (30 pages, offline), super-admin (11 pages), mobile Expo (4 écrans).
- Health/ready/monitor, robustesse du montage des namespaces (correctif P0 du 14/09).
- Tests : **438 tests collectés** ; tests ciblés exécutés le 15/09 : `test_facturation_idempotence.py` + `test_auth.py` → **5 passed**.

### 5.2 Partiellement implémenté / dépendant de l'environnement
| # | Sujet | État | Détail |
|---|---|---|---|
| P1 | **Planification des backups** | 🟠 Partiel | `tasks/backups.py` (snapshot WAL-safe, rétention 7 j, fallback pg/mysqldump) mais **aucun beat schedule** → planification externe requise |
| P2 | **Temps réel Socket.IO** | 🟠 Partiel | Serveur et client présents, activés par `ENABLE_SOCKETIO` ; comportement non vérifié en production (fallback polling côté client) |
| P3 | **PWA web** | 🟠 Partiel | `manifest.json` présent mais **service worker désenregistré** volontairement dans `web/frontend/src/index.js` → pas d'installation/offline sur le web |
| P4 | **Mode hors-ligne desktop** | 🟠 Partiel | `syncEngine` avec file d'attente ; anomalies historiques de persistance de file et d'idempotence (voir §7.G) |
| P5 | **IA** | 🟠 Partiel | Modèles `.pkl` + heuristiques numpy/pandas ; enrichissement externe (OpenAI/Anthropic) optionnel et non garanti sans clés |
| P6 | **Emails transactionnels** | 🟠 Partiel | `tasks/emails.py` prend désormais un `recipient` réel et fait `starttls` ; configuration SMTP (`super-admin/EmailConfig`) à valider par environnement |
| P7 | **Vitrine publique par tenant** | 🟠 Partiel | Champs `vitrine_enabled`/`vitrine_enabled_at` + endpoints `tenant_papi` ; activation pilotée par le tenant |
| P8 | **i18n malgache** | 🟠 Partiel | Complétée selon le rapport QA du 14/09 (statut « probable », re-test UI requis) |

### 5.3 Non implémenté (manques identifiés)
| # | Manque | Impact | Suggestion |
|---|---|---|---|
| M1 | Beat schedule Celery (backups, relances, emails planifiés) | Pas d'exécution automatique réelle | Ajouter `celery beat schedule` ou cron appelant `backup_database` |
| M2 | Contrôle qualité/lot à la réception des achats | Traçabilité par lot absente | Champs `lot`, `date_peremption`, contrôle qualité |
| M3 | Page frontend « Résultats comptables » dédiée | Fonction API non exposée visuellement | Vue annuelle/mensuelle consommant `/api/v1/resultats/` |
| M4 | Service worker / PWA web | Pas d'installation ni offline web | Réactiver SW + manifest complet (icônes, offline) ou assumer le choix |
| M5 | UI multi-entrepôts complète (transferts entre dépôts, ventilation ventes) | Risque d'incohérence de stock | Écran `Entrepots`, transferts, rattachement des mouvements |
| M6 | Couverture mobile étendue (achats, RH, compta, admin) | Mobile limité au terrain | Étendre progressivement selon priorités |
| M7 | Tests frontend/desktop automatisés | Tests Jest supprimés (voir §7.I) | Réintroduire des tests ciblés (composants critiques) |
| M8 | Documentation utilisateur à jour (`docs/user/README.md` = README générique) | Onboarding faible | Guide par rôle (admin tenant, vendeur, livreur, Super Admin) |
| M9 | Observabilité (métriques, tracing, alerting) | Diagnostic lent en production | Endpoints `/monitor` enrichis + logs structurés + alerting |

---

## 6. Anomalies transverses (configuration, sécurité, qualité)

| # | Anomalie | Statut | Preuve / détail | Recommandation |
|---|---|---|---|---|
| **A1** | **Service worker PWA désenregistré** (web) | OUVERT | `web/frontend/src/index.js` : `getRegistrations().then(...unregister())` alors que `manifest.json` est présent | Réactiver la PWA (installable + offline) ou retirer le manifest |
| **A2** | **`erp.db` (SQLite de dev) suivie par git** | OUVERT (vérifié) | `git ls-files` retourne `erp.db` → données de dev dans le dépôt, conflits à chaque commit | `git rm --cached erp.db` + `.gitignore` (`*.db`, `*.sqlite3`) |
| **A3** | **Mots de passe en clair dans les scripts** | OUVERT (vérifié) | `web/backend/scripts/check_auth.py`, `create_sa.py`, `create_superadmin.py`, `check_superadmin_auth.py` contiennent `Super123!` / `Test1234!` | Lire depuis `.env` (`DEFAULT_ADMIN_PASSWORD`), interdire hors dev |
| **A4** | **`allow_unsafe_werkzeug`** | PARTIEL (vérifié) | `web/backend/run.py` L34-37 : `allow_unsafe_werkzeug=debug` → gaté, mais présent | Conserver le gating + test de non-exposition en prod |
| **A5** | **Duplication du code partagé** : `shared/`, `desk/shared/`, `desk/src/shared/` | OUVERT (vérifié) | Les 3 dossiers existent ; `desk/shared/*` est une copie (contexts, hooks, services, storage) → divergence des correctifs | Consolider sur `shared/` avec ré-exports |
| **A6** | **`desktopApi.js` : implémentation parallèle** | PARTIEL | `desk/src/services/desktopApi.js` (≈300 lignes) duplique notifications/favoris/colonnes/sync | Réduire à un wrapper fin autour de `shared/services/api.js` |
| **A7** | **Namespace `test` dans l'API** | MAÎTRISÉ (vérifié) | Monté uniquement si `DEBUG` ou `TESTING` (`app/__init__.py`) | Conserver + test automatisé de non-montage en prod |
| **A8** | **Tests Jest frontend/desktop supprimés** | OUVERT | Composants/hooks/services `__tests__` supprimés (ErrorBoundary, DataTable, FilterPanel, DesktopContext, useFormDraft, desktopApi, navPermissions, filterUtils) | Réintroduire des tests ciblés |
| **A9** | **CORS / IP interne** | À RE-VÉRIFIER | Historique : `192.168.90.246` dans `CORS_ORIGINS` du `.env` backend (fichier non suivi par git — `.gitignore` correct) | Origines pilotées par environnement |
| **A10** | **Ports exposés en 0.0.0.0** (`docker-compose`) | À RE-VÉRIFIER | Signalé par l'audit antérieur (MySQL/Redis) | Restreindre les bindings en production |
| **A11** | **Dockerfile `COPY . .`** | À RE-VÉRIFIER | Copie potentielle de `.env`, logs, `erp.db` | `COPY` ciblé + `.dockerignore` |
| **A12** | **Modèles IA `.pkl` versionnés** | PARTIEL (vérifié) | `app/ai/models/stock_model.pkl`, `vente_model.pkl` suivis par git | Régénérer par script d'entraînement, exclure du dépôt |
| **A13** | **Migrations vs ajouts directs de colonnes** | PARTIEL | 16 révisions Alembic ; des colonnes ont été ajoutées en direct sur SQLite (voir §7.L) → schémas dev/prod divergents possibles | Utiliser exclusivement `flask db upgrade` |
| **A14** | **Duplication d'écrans web/desktop** | PARTIEL | Pages quasi identiques dans `web/frontend/src/pages` et `desk/src/pages` | Mutualiser dans `shared/` |
| **A15** | **Auto-seeding / comptes de test** | À RE-VÉRIFIER | Auto-seeding annoncé au démarrage ; comptes de démonstration documentés (`distrifood@erp.com`…, `Test1234!`) | Désactiver hors dev, documenter explicitement |
| **A16** | **Super Admin sans MFA identifié** | PARTIEL | Interface privée réservée au compte `SUPER_ADMIN` | Ajouter MFA + allowlist IP + audit renforcé |

---

## 7. Registre des bugs (129 entrées historiques consolidées et réévaluées)

Les entrées ci-dessous proviennent des audits précédents (`Analyse_Projet_Actuel.md`, `design_erp.md`). Chacune a été **réévaluée** au regard du code actuel ; les entrées non re-vérifiées sont marquées « À RE-VÉRIFIER » et ne doivent pas être traitées comme des faits établis.

### 7.A Sécurité — critique
| # | Fichier | Statut | Description |
|---|---|---|---|
| 1 | `api/v1/public.py` | OUVERT (par conception, mitigé — vérifié) | `POST /api/v1/public/commandes` sans authentification — **mitigation actuelle : `@rate_limit(30, 300)` + idempotence `Idempotency-Key`** (TTL 600 s, cache plafonné à 2 000 entrées). Risque résiduel : commandes abusives par un anonyme |
| 2 | `services/papi/webhook.py`, `api/v1/papi.py` | 🟢 Corrigé (déclaré) | Webhook PAPI sans vérification de signature → `_verify_webhook_signature` avec `hmac.compare_digest` |
| 3 | `api/v1/super_admin.py` | 🟢 Corrigé (déclaré) | Hard-delete tenant irréversible → endpoint supprimé, seul le soft-delete subsiste |
| 13 | `api/v1/auth.py` | ✅ Corrigé (vérifié) | Reset token : plus de scan global → digest SHA-256 indexé (`PasswordResetToken.find_by_raw_token`) |
| 17 | `services/base_service.py` | ✅ Corrigé (vérifié) | Mass assignment → whitelist `PROTECTED_FIELDS` sur `create()`/`update()`, `tenant_id` imposé par le contexte serveur (commentaire explicite dans `api/v1/entrepots.py`) |
| 68-69 | `run.py` | 🟠 Partiel (vérifié) | Werkzeug debugger → `allow_unsafe_werkzeug=debug` (gaté par `FLASK_DEBUG`, mais toujours présent) |
| 70 | `scripts/*.py` | OUVERT (vérifié) | Mots de passe en clair (`Super123!`, `Test1234!`) dans 4 scripts (voir A3) |
| 86-88 | `.env`, Dockerfile, `docker-compose.yml` | À RE-VÉRIFIER | IP interne en CORS, `COPY . .`, ports 0.0.0.0 |
| A2 | `erp.db` | OUVERT (vérifié) | Base SQLite de développement versionnée dans git |

### 7.B Multi-tenant
| # | Fichier | Statut | Description |
|---|---|---|---|
| 95 | `websockets/socket_events.py` | ✅ Corrigé (vérifié) | `subscribe:*` valide l'appartenance (`_tenant_belongs_to_user`, L56-68), rejet si `tenant_id` absent (L100-104) |
| 97 | `ai/previsions.py` | À RE-VÉRIFIER | Requête `MouvementStock` sans filtre `tenant_id` → fuite inter-tenant dans les prévisions |
| 98 | `ai/anomalies.py` | À RE-VÉRIFIER | Idem pour la détection d'anomalies |
| 18 | `api/v1/super_admin.py` | À RE-VÉRIFIER | Soft-delete incomplet (≈9 modèles sur ~30) → enregistrements orphelins (`Livreur`, `Vehicule`, `Stock`…) |
| 12 | `security/tenant.py` | À RE-VÉRIFIER | `tenant_required` met à jour `AdminDevice.last_seen` et **commit à chaque requête** → charge inutile et risque de course |
| — | `models/*` | PARTIEL | Politique soft-delete/hard-delete hétérogène selon les modèles ; à harmoniser via `BaseModel` |

### 7.C Intégrité des données & conditions de course
| # | Fichier | Statut | Description |
|---|---|---|---|
| 67 | `services/vente_service.py` | 🟢 Corrigé (déclaré) | Race condition sur le décrément de stock → `with_for_update()` confirmé présent en L132 (commentaire en L127 : sur SQLite `with_for_update` est ignoré, comportement compensé par un re-SELECT) |
| 71 | `services/paiement_service.py` | 🟢 Corrigé (déclaré) | Race sur le paiement de facture → `facture.with_for_update().first()` confirmé présent en L109 |
| 72 | `services/facturation_service.py` | 🟢 Corrigé (déclaré) | Idempotence de génération de facture (1 seule facture active par vente) — test `tests/test_facturation_idempotence.py` **exécuté : passed** |
| 74 | `security/plan_limits.py` | 🟢 Corrigé (déclaré) | Vérification de quota non atomique → définie côté backend ; **résidu possible de course** en création concurrente d'utilisateurs (à re-tester en charge) |
| 89 | `models/stock.py` | À RE-VÉRIFIER | `MouvementStock` : FK sans `ON DELETE` → historique de mouvement perdu si produit supprimé |
| 105 | `services/comptabilite_service.py` | À RE-VÉRIFIER | Cohérence débit/crédit des écritures générées automatiquement (équilibre non vérifié automatiquement) |
| 106 | `services/livraison_service.py` | À RE-VÉRIFIER | Mise à jour du statut de livraison non transactionnelle avec le stock (rupture possible) |
| 108 | `models/facture.py` | À RE-VÉRIFIER | Montants recalculés à partir des lignes ; arrondis MGA non normalisés |
| 112 | `api/v1/ventes.py` | À RE-VÉRIFIER | Annulation de vente : restitution du stock non atomique avec l'annulation |

### 7.D Backend API
| # | Fichier | Statut | Description |
|---|---|---|---|
| 14 | `security/rate_limit.py` | ✅ Corrigé (vérifié) | Comportement fail-open → désormais **fail-closed en production** avec cache Redis, retry différé (`_redis_down_until`, 30 s) et compteur mémoire de secours en développement |
| 15 | `ai/assistant.py` | À RE-VÉRIFIER | Total de chiffre d'affaires potentiellement tronqué (`.limit(...)`) pour les tenants à fort volume |
| 16 | `api/v1/ventes.py` | À RE-VÉRIFIER | `datetime.strptime()` de filtre sans `try/except` → erreur 500 sur date invalide |
| 22-23 | `api/v1/produits.py`, `api/v1/clients.py` | À RE-VÉRIFIER | Pagination/recherche sans limite haute explicite sur `per_page` |
| 30 | `api/v1/documents.py` | À RE-VÉRIFIER | Génération PDF synchrone dans la requête → temps de réponse élevé sur gros documents |
| 33 | `api/v1/ai.py` | À RE-VÉRIFIER | Endpoints IA sans cache → recalcul complet à chaque appel |
| 36 | `api/v1/dashboard.py` | À RE-VÉRIFIER | Agrégations multiples (compteurs) pouvant produire des requêtes N+1 |
| 40 | `api/v1/rh.py` | À RE-VÉRIFIER | Calcul de paie : arrondis et cumuls à valider avec la comptabilité |
| 43 | `api/v1/abonnements.py` | 🟢 Corrigé (déclaré) | Quotas strictement côté backend (403 explicite) ; aucune suppression de données lors de la rétrogradation Pro → Gratuit |
| 45 | `api/v1/public.py` | 🟢 Corrigé (déclaré) | Commandes publiques : idempotence + rate limiting (voir #1) |
| 90 | `websockets/socket_events.py` | À RE-VÉRIFIER | Token d'authentification potentiellement journalisé par la pile engineio |
| — | `app/__init__.py` | ✅ Corrigé (vérifié) | Montage des namespaces robuste ; `test` conditionné à `DEBUG`/`TESTING` |

### 7.E Frontend web
| # | Fichier | Statut | Description |
|---|---|---|---|
| 4 | `web/frontend/src/pages/Users.jsx` | ✅ Corrigé (vérifié) | `isEmployeeLimitReached()` est désormais **défini à l'intérieur du composant** (L47-51) et utilisé en L344 → plus de `ReferenceError` |
| 19 | `pages/Subscription.jsx` | À RE-VÉRIFIER | `setInterval` de polling fenêtre de paiement non nettoyé au démontage → fuite mémoire |
| 20 | `pages/AI.jsx` | À RE-VÉRIFIER | `setTimeout` (400 ms) pouvant déclencher `setMessages` après démontage |
| 21 | `pages/Home.jsx` | À RE-VÉRIFIER | `useEffect` avec dépendances `[]` → notifications non rechargées après connexion (stale closure) |
| 22 | `pages/Users.jsx` | À RE-VÉRIFIER | Recherche sans `AbortController` → réponses hors séquence |
| 23 | `pages/Products.jsx` | À RE-VÉRIFIER | Idem recherche/filtre |
| 26 | `pages/Catalogue.jsx` / `Cart.jsx` | À RE-VÉRIFIER | État de panier non persisté entre sessions |
| 47 | `contexts/AuthContext.jsx` | À RE-VÉRIFIER | Rafraîchissement de token concurrent (plusieurs requêtes 401 simultanées) |
| A1 | `src/index.js` | OUVERT (vérifié) | Service worker désenregistré (PWA inactive) |
| — | `src/pages/*` | PARTIEL | Gestion d'erreurs hétérogène selon les pages (certaines n'affichent pas d'état d'échec explicite) |

### 7.F Desktop (Electron) & code partagé
| # | Fichier | Statut | Description |
|---|---|---|---|
| 5 | `super-admin/src/pages/Tenants.jsx` | ✅ Corrigé (vérifié) | Le bouton « Supprimer » appelle désormais `handleDeletePermanent(tenant.id, tenant.nom)` (L263) ; la fonction `handleDelete` inexistante n'est plus référencée |
| 6 | `shared/storage/authStorage.js` | PARTIEL (vérifié) | Le stockage passe par `storageAdapter`/`tokenStore` (plus de `localStorage` direct dans ce fichier) ; il écrit encore les **clés historiques et les nouvelles clés** (`erp.auth.*`) en double → à nettoyer après migration complète |
| 7 | `desk/src/services/desktopApi.js` | OUVERT | Services dupliqués/désynchronisés du backend (notifications, favoris, colonnes, sync) — voir A6 |
| 8 | `shared/websockets/socketClient.js` | À RE-VÉRIFIER | Lecture du token : doit passer par `secureStore`/`tokenStore` en Electron (sinon échec de connexion) |
| 9 | `shared/realtime/socketClient.js` | À RE-VÉRIFIER | Même risque que ci-dessus |
| 10 | `shared/contexts/SyncContext.jsx` | À RE-VÉRIFIER | `flushQueue` : capture de `isSyncing` dans l'écouteur d'événement (stale closure) → courses possibles |
| 11 | `desk/electron/preload.js` | ✅ Corrigé (vérifié) | Échec de déchiffrement : l'entrée corrompue est purgée et `null` est retourné (L28-36) au lieu de renvoyer du base64 brut |
| A5/A6 | `desk/shared/*`, `desk/src/shared/*` | OUVERT | Triplication du code partagé (voir §6) |
| 61 | `desk/electron/main.js` | À RE-VÉRIFIER | Durcissement Electron (`webSecurity`, `nodeIntegration`) à confirmer |
| 62 | `desk/package.json` | À RE-VÉRIFIER | Absence de signature de code (`code signing`) pour la distribution desktop |

### 7.G Synchronisation / hors-ligne
| # | Fichier | Statut | Description |
|---|---|---|---|
| 55 | `shared/utils/syncEngine.js` | 🟢 Corrigé (déclaré) | La file d'attente est **persistée** localement (perte au rechargement corrigée) |
| 56 | `shared/utils/syncEngine.js` | 🟢 Corrigé (déclaré) | Idempotence des mutations rejouées (`Idempotency-Key` sur les POST) |
| 57 | `shared/utils/syncEngine.js` | À RE-VÉRIFIER | Absence de limite de taille / backoff exponentiel sur la file (accumulation en hors-ligne prolongé) |
| 58 | `shared/contexts/SyncContext.jsx` | À RE-VÉRIFIER | Pas de résolution de conflit explicite côté utilisateur (« dernier écrivain gagne » silencieux) |
| 59 | `web/backend/app/api/v1/desk.py` | À RE-VÉRIFIER | Endpoint de resynchronisation : volumétrie non bornée (`since` sans limite) |
| 60 | `shared/utils/hydration.js` | À RE-VÉRIFIER | Hydratation par `updated_at` sensible aux horloges désynchronisées |
| — | Tests E2E du 14/09 | 🟢 Corrigé (déclaré) | Échec de resynchronisation SQLite identifié en E2E → corrigé (à re-tester sur un cycle offline→online complet) |

### 7.H WebSockets, IA, tâches planifiées
| # | Fichier | Statut | Description |
|---|---|---|---|
| 91 | `shared/websockets/socketClient.js` | À RE-VÉRIFIER | Décalage d'authentification : le serveur attend le token dans `auth` pendant le handshake — vérifier que le client le fournit bien à ce moment (sinon toutes les connexions échouent) |
| 92 | `web/backend/app/tasks/emails.py` | ✅ Corrigé (vérifié) | `send_email(recipient, subject, body, smtp_config)` prend désormais un **destinataire réel** (plus de `client@example.com`), avec `starttls` chiffré et configuration SMTP injectée |
| 93 | `web/backend/app/tasks/backups.py` | PARTIEL | Snapshot WAL-safe + rétention + fallback `pg_dump`/`mysqldump`, mais **aucune planification** (voir M1) |
| 94 | `web/backend/app/ai/anomalies.py` | À RE-VÉRIFIER | Seuil de détection (z-score) non configurable par tenant |
| 96 | `web/backend/app/ai/training.py` | À RE-VÉRIFIER | Réentraînement des modèles déclenché manuellement uniquement |
| 99 | `web/backend/app/ai/insights.py` | À RE-VÉRIFIER | Génération d'« insights » non mise en cache → coût récurrent |
| 100 | `web/backend/app/ai/assistant.py` | À RE-VÉRIFIER | Contexte limité (troncature) → réponses incomplètes sur grands historiques |
| 101 | `web/backend/app/websockets/socket_events.py` | À RE-VÉRIFIER | Absence de reconnexion/backoff côté serveur pour les clients morts |
| 102 | `web/backend/run.py` | PARTIEL (vérifié) | Socket.IO activé conditionnellement (`if getattr(app, 'socketio', None)`) : sans `ENABLE_SOCKETIO`, le temps réel est **silencieusement désactivé** |
| 103 | `web/backend/app/realtime/socket_server.py` | À RE-VÉRIFIER | Absence de limitation du nombre de rooms/connexions par utilisateur |

### 7.I Tests & qualité
| # | Sujet | Statut | Description |
|---|---|---|---|
| 78 | Tests backend | ✅ Amélioré (vérifié) | **438 tests collectés** (vs 278 annoncés historiquement) ; tests ciblés du 15/09 : 5 passed |
| 79 | Tests frontend/desktop | OUVERT | Tests Jest supprimés (voir A8) → régressions non détectées automatiquement |
| 80 | E2E | PARTIEL | Campagne Playwright du 14/09 : blocage « SC1 » identifié ; suite E2E à rejouer après correctifs |
| 81 | Lint/typage | À RE-VÉRIFIER | `black`, `flake8`, `mypy`, `isort` configurés mais aucune preuve d'exécution en CI |
| 82 | CI/CD | OUVERT | Aucun pipeline automatisé identifié (pas de GitHub Actions, pas de hook de pré-commit documenté) |
| 83 | Qualité de code | À RE-VÉRIFIER | Fichiers volumineux (`super_admin.py`, `comptabilite.py`, pages > 1 000 lignes) → maintenance difficile |

### 7.J Internationalisation
| # | Sujet | Statut | Description |
|---|---|---|---|
| 84 | i18n malgache | PARTIEL | Traductions complétées selon le rapport QA du 14/09, mais **re-vérification UI requise** (chaînes résiduelles en français) |
| 85 | Format monétaire | À RE-VÉRIFIER | Format `MGA`/`Ar` et séparateurs : homogénéité à valider sur toutes les pages |

### 7.K Base de données, performances, déploiement
| # | Sujet | Statut | Description |
|---|---|---|---|
| 75 | `erp.db` / PostgreSQL | PARTIEL | SQLite en développement **ignore `with_for_update`** → les protections par verrou ne sont effectives qu'en PostgreSQL (voir #67) |
| 76 | Index | À RE-VÉRIFIER | Colonnes filtrées fréquemment (`statut`, `date_*`, `reference`) : couverture d'index à auditer avec `EXPLAIN` |
| 77 | Requêtes N+1 | À RE-VÉRIFIER | Listes avec relations (`ventes`+`lignes`+`client`, `factures`+`paiements`) : usage de `joinedload`/`selectinload` à vérifier |
| 63 | Déploiement | À RE-VÉRIFIER | Serveur WSGI de production (gunicorn/waitress) non identifié dans les scripts |
| 64 | Logs | À RE-VÉRIFIER | Rotation/centralisation des logs applicatifs non identifiée |
| 65 | Secrets | PARTIEL | `JWT_SECRET_KEY` obligatoire (bon point) ; autres secrets (SMTP, PAPI) à vérifier |
| 66 | Migrations | PARTIEL | 16 révisions Alembic ; colonnes ajoutées directement sur SQLite (voir A13) → divergence schéma dev/prod possible |

---

## 8. Synthèse quantitative

### 8.1 Registre historique consolidé (129 entrées)
| Sévérité | Verrouillées « corrigées » (vérifiées ou déclarées) | Ouvertes (confirmées) | PARTIELLES | À RE-VÉRIFIER |
|---|---|---|---|---|
| **Critique** | 8 | 3 (#1 public, A2 `erp.db`, A3 secrets scripts) | 1 | 3 |
| **Haute** | 9 | 6 (A5 triplication, A6 desktopApi, A8 tests Jest, A1 PWA, M1 planification, #7) | 5 | 8 |
| **Moyenne** | 4 | 2 | 6 | 20 |
| **Basse** | 2 | — | 3 | 11 |

> Volontairement prudent : les audits antérieurs annonçaient **90 + 39 = 129 bugs** avec 15 critiques. Les « À RE-VÉRIFIER » proviennent d'audits statiques n'ayant pas été re-confirmés lors de cette passe ; il est **probable qu'une partie d'entre eux soit déjà corrigée** (comme #4, #5, #11, #13, #14, #17, #92 — confirmés corrigés ici). Le comptage ne doit pas être lu comme « 20 bugs moyens actifs ».

### 8.2 Correctifs confirmés par vérification directe du code (2026-09-15)
| Réf. | Objet | Preuve |
|---|---|---|
| #4 | Plus de `ReferenceError` dans `Users.jsx` | Fonction définie dans le composant (L47-51), appel L344 |
| #5 | `handleDelete` fantôme supprimé | `Tenants.jsx` L263 → `handleDeletePermanent` |
| #11 | Fallback de déchiffrement assaini | `preload.js` L28-36 : purge + `null` |
| #13 | Reset token sans scan global | `PasswordResetToken.find_by_raw_token` |
| #14 | Rate limiter fail-closed en production | `rate_limit.py` : Redis + `_redis_down_until` + fallback mémoire dev |
| #17 | Mass assignment bloqué | `PROTECTED_FIELDS` dans `base_service.py` |
| #67/#71 | Verrous stock/paiement | `with_for_update()` dans `vente_service.py` L132 et `paiement_service.py` L109 |
| #92 | Emails vers destinataires réels | `tasks/emails.py` : paramètre `recipient` |
| #95 | WebSocket multi-tenant sécurisé | `_tenant_belongs_to_user` L56-68 |
| A7 | Namespace `test` protégé | Montage conditionnel `DEBUG`/`TESTING` |
| #78 | Suite de tests élargie | 438 tests collectés, 5 passed (ciblés) |
| E1–E4 | Écarts cahier des charges | Entrepots/StockEntrepot, `stock_max`, namespace `resultats`, `mobile/` |

### 8.3 Top 10 des actions prioritaires (impact décroissant)
1. **A2** — Retirer `erp.db` du suivi git et compléter `.gitignore`.
2. **A3** — Supprimer les mots de passe en clair des scripts (variables d'environnement).
3. **#97/#98** — Ajouter le filtre `tenant_id` dans `ai/previsions.py` et `ai/anomalies.py` (fuite inter-tenant potentielle).
4. **A5/A6** — Consolider le code partagé (`shared/` unique) et réduire `desktopApi.js` à un wrapper.
5. **M1** — Planifier réellement les sauvegardes (Celery beat ou cron documenté).
6. **A8** — Réintroduire les tests frontend/desktop + un pipeline CI minimal.
7. **A1** — Trancher sur la PWA web (service worker désenregistré vs manifest présent).
8. **#12** — Sortir le `commit` de `tenant_required` (mise à jour `last_seen` asynchrone/groupée).
9. **#18** — Terminer le soft-delete généralisé (`Livreur`, `Vehicule`, `Stock`, …).
10. **#19/#20/#21** — Nettoyer les timers/écouteurs et corriger les dépendances `useEffect`.

---

## 9. Plan de correction priorisé

### Phase 0 — Hygiène dépôt & secrets (immédiat, faible risque)
1. `git rm --cached erp.db` + `.gitignore` `*.db`/`*.sqlite3` (**A2**).
2. Externaliser les mots de passe des scripts dans `.env` (**A3**).
3. Ajouter `.dockerignore` et remplacer `COPY . .` (**A11**, à confirmer).

### Phase 1 — Sécurité & isolation (P0)
4. Filtrer `tenant_id` sur toutes les requêtes IA (**#97**, **#98**).
5. Déplacer le `commit` de `security/tenant.py` hors du chemin chaud (**#12**).
6. Re-vérifier l'authentification WebSocket côté client (handshake `auth`) (**#91**).
7. Décider du durcissement de `POST /public/commandes` (captcha/turnstile, plafond par IP) (**#1**).
8. MFA + allowlist pour la console Super Admin (**A16**).

### Phase 2 — Intégrité des données (P0/P1)
9. Garantir l'exécution des verrous en production (PostgreSQL obligatoire) et documenter la limite SQLite (**#75**).
10. `ON DELETE`/restrictions sur `MouvementStock` (**#89**).
11. Idempotence stricte des mutations hors-ligne + backoff/plafond de file (**#57**).
12. Atomicité des quotas à la création d'utilisateurs (**#74**).

### Phase 3 — Stabilité frontend/desktop (P1)
13. Nettoyer les timers/intervalles (`Subscription.jsx`, `AI.jsx`) (**#19**, **#20**).
14. Corriger les dépendances `useEffect` (`Home.jsx`) (**#21**) et ajouter des `AbortController` aux recherches (**#22**, **#23**).
15. Consolider le code partagé et dédupliquer `desktopApi.js` (**A5**, **A6**, **#7**).

### Phase 4 — Complétude fonctionnelle (P2)
16. Planifier les sauvegardes (Celery beat/cron) (**M1**).
17. Page frontend « Résultats comptables » (**M3**).
18. UI multi-entrepôts complète : transferts entre dépôts + ventilation des mouvements (**M5**).
19. Contrôle qualité/lot à la réception des achats (**M2**).
20. Réintroduire les tests frontend + CI (**A8**, **#82**).

### Phase 5 — Qualité, perf, documentation (P3)
21. Audit d'index et N+1 (**#76**, **#77**).
22. Observabilité (`/monitor` enrichi, logs structurés, alerting) (**M9**).
23. Documentation utilisateur par rôle (**M8**) et re-vérification i18n (**#84**).
24. Trancher sur PWA web (**A1**, **M4**) et `erp.db` de dev (**A2**).

---

## 10. Rubriques fonctionnelles détaillées du projet

### 10.1 Ventes & facturation
- Vente gros/détail, remises, TVA (20 %), échéance de crédit, génération de facture **idempotente** (une seule facture active par vente).
- Statuts facture recalculés à partir des paiements (`impayee` → `partielle` → `payee`).
- Devis, bons de livraison, avoirs (`DevisAvoirBL`).
- Reste à corriger : annulation de vente non atomique avec la restitution de stock (#112).

### 10.2 Achats & fournisseurs
- Bons de commande fournisseur, réceptions partielles (`quantite_recue` vs `quantite_commandee`), entrée en stock automatique.
- Manque : contrôle qualité/lot (M2).

### 10.3 Stocks & entrepôts
- Mouvements typés (`ENTREE`, `SORTIE`, `INVENTAIRE`, `AJUSTEMENT`, `RETOUR`, `TRANSFERT`), alertes seuil/critique, valorisation au prix d'achat HT.
- Multi-entrepôts : `Entrepot` + `StockEntrepot` (`quantite`, `seuil_min`, `seuil_max`).
- Point d'attention : coexistence de `Produit.quantite_stock` (stock global) et `StockEntrepot.quantite` (par dépôt) — la cohérence entre les deux doit être documentée/garantie (M5).

### 10.4 Comptabilité
- Plan comptable, écritures, journal, trésorerie, import, et **résultats par période** (`ns_resultats`, `ResultatService.PERIODES`).
- Point d'attention : équilibre débit/crédit des écritures auto-générées non contrôlé automatiquement (#105).

### 10.5 RH
- Employés, présences, salaires, primes, stagiaires. Calculs de paie à valider avec la comptabilité (#40).

### 10.6 Livraison
- Livreurs, véhicules, itinéraires, livraisons, suivi de tournée, compte livreur lié à un `Utilisateur` (7 tests dédiés).
- Point d'attention : décrément de stock non transactionnel avec la livraison (#106).

### 10.7 Marketplace publique
- Catalogue multi-entreprises, panier, commande invité, suivi, QR/code-barre, `vitrine_enabled` par tenant.
- Protection : rate limiting + idempotence ; validation après paiement complet (PAPI).

### 10.8 Abonnements & plans
- Plans (Gratuit/Pro/…), quotas (utilisateurs, produits…) vérifiés **côté backend** (403), période de grâce de 30 jours, rétrogradation automatique vers Gratuit, audit trail (`SubscriptionAuditTrail`), notifications.
- Super Admin : création/modification de plans, activation/désactivation, prolongation, consultation de l'historique.

### 10.9 IA
- Prévisions de ventes et de stocks, détection de ruptures, anomalies (z-score), recommandations, assistant conversationnel, insights, réentraînement.
- Gating par domaine via `ai_permissions.py` ; endpoints sans cache (#33, #99).
- Point d'attention majeur : filtrage multi-tenant à confirmer (#97, #98).

### 10.10 Documents & impression
- Modèles système (facture, devis, contrat, BL, avoir), génération PDF (reportlab), export Excel (openpyxl), QR codes et code-barres.
- Point d'attention : génération PDF synchrone dans la requête (#30).

### 10.11 Super Admin (console plateforme)
- 11 pages : Dashboard, Tenants, TenantDetail, Subscriptions, Plans, Users, Audit, EmailConfig, PaymentSettings, Profile, LoginPage.
- Interface privée ; soft-delete des tenants ; audit renforcé ; pas de MFA identifié (A16).

---

## 11. Règles de travail du projet (conservées de `INSTRUCTION.md`)

Ces règles conditionnent la fiabilité des futures interventions :

1. **Anti-hallucination** : ne jamais inventer un fichier, une fonction, une route ou un champ. Vérifier dans le code avant de l'affirmer.
2. **Aucune suppression sans preuve** : ne supprimer/modifier que ce qui est confirmé par lecture du code.
3. **Pas de fausses corrections** : si une correction n'est pas vérifiée par lecture ou par test, la déclarer explicitement comme non vérifiée.
4. **Respect du périmètre** : ne pas toucher aux fichiers déclarés non modifiables ; ne pas refactoriser largement sans demande explicite.
5. **Cohérence des conventions** : suivre les patterns existants (service + namespace + décorateurs tenant/permissions + audit).
6. **Vérification finale obligatoire** : après toute modification, relire les fichiers touchés et exécuter les tests pertinents.

---

## 12. Commandes de travail (référence)

### Backend
```powershell
cd web/backend
.\venv\Scripts\python.exe run.py                      # démarrage API (port 5000)
.\venv\Scripts\python.exe -m pytest -q                # suite complète (438 tests collectés)
.\venv\Scripts\python.exe -m pytest -q --collect-only # vérification de collecte
.\venv\Scripts\python.exe -m pytest tests/test_auth.py -q
.\venv\Scripts\flask.exe db upgrade                   # migrations Alembic
```

### Frontend web
```powershell
cd web/frontend
npm install
npm start        # http://localhost:3000
```

### Super Admin
```powershell
cd super-admin
npm install
npm start        # http://localhost:3001
```

### Desktop (Electron)
```powershell
cd desk
npm install
npm run dev      # ou npm start selon les scripts du package.json
```

### Mobile (Expo)
```powershell
cd mobile
npm install
npm start        # Expo ; taper a (android), i (ios), w (web)
```

### Graphify (graphe de connaissance)
```powershell
graphify query "question"
graphify update .
```

---

## 13. Conclusion

Le projet est **fonctionnellement très complet** : les 4 écarts du cahier des charges (multi-entrepôts, stock maximum, résultats comptables, application mobile) sont **implémentés**, la suite de tests backend a été **élargie à 438 tests**, et la plupart des vulnérabilités critiques précédemment identifiées (mass assignment, reset token, webhook PAPI, rate limiter, hard-delete tenant, WebSocket multi-tenant, emails) sont **corrigées**.

Les **risques résiduels** sont désormais concentrés sur :
1. **L'hygiène du dépôt** — `erp.db` versionnée, mots de passe en clair dans les scripts, modèles `.pkl` binaires suivis par git.
2. **L'isolation multi-tenant des modules IA** — filtre `tenant_id` à confirmer (#97, #98) : point le plus sensible restant.
3. **La duplication structurelle** — code partagé triplé (`shared/`, `desk/shared/`, `desk/src/shared/`), `desktopApi.js`, pages web ↔ desktop.
4. **L'automatisation** — aucune planification de sauvegarde, aucun pipeline CI, tests frontend/desktop supprimés.

Traiter les **Phases 0 à 2** du §9 ferait passer le projet d'un état « avancé et testé » à un état « industrialisable ».

---

*Fin du rapport — 2026-09-15. Ce document remplace l'ensemble des documents d'analyse supprimés le même jour (voir §1.2). Le `README.md` reste le document d'accueil du projet.*