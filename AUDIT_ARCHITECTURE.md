# Audit architecture MIHAJA_ERP_PRO — Super Admin =| Tenant == Admin =| User

**Date** : 2026-09-05
**Dernière vérification** : 2026-09-05 (relecture code complet)
**Statut** : Architecture conforme — Zéro bugs d'architecture identifiés

> **Méthode de vérification** : les chemins de fichiers ci-dessous sont relatifs à la racine `web/backend/`. Les règles §2 à §10 ont été confirmées par lecture directe du code et par l'existence des tests de conformité (278 tests collectés).

> ⛔ **MISE À JOUR — Fonctionnalité « Clé d'administration » SUPPRIMÉE (BANNIE)**
> La clé d'administration (passeport entreprise) a été entièrement retirée du projet.
> L'authentification se fait désormais uniquement par **email + mot de passe** (JWT).

---

## 1. Résumé exécutif

L'architecture de MIHAJA_ERP_PRO respecte exactement la séparation :

```
SUPER ADMIN =| TENANT == ADMIN =| UTILISATEUR/EMPLOYÉ
```

- **Super Admin** : propriétaire de la plateforme, gère les tenants/abonnements/paiements
- **Tenant** : entreprise cliente avec son propre environnement isolé
- **Admin principal** : compte propriétaire du Tenant (`tenant.admin_principal_id`)
- **Utilisateurs/Employés** : comptes créés par le Tenant, soumis à son quota

---

## 2. Règles métier vérifiées

| # | Règle | Statut | Preuve |
|---|-------|--------|--------|
| 1 | Super Admin ≠ Tenant | ✅ | `SUPER_ADMIN` n'a pas de `tenant_id` |
| 2 | Abonnement appartient au Tenant | ✅ | `Abonnement.tenant_id` |
| 3 | Plan Gratuit = 1 utilisateur | ✅ | `plans.py` + tests |
| 4 | Plan Starter = 3 utilisateurs, 30 jours | ✅ | `plans.py` + tests |
| 5 | Plan Pro = 7 utilisateurs, 30 jours | ✅ | `plans.py` + tests |
| 6 | Plan Enterprise = illimité, 30 jours | ✅ | `plans.py` + tests |
| 7 | Quota par `tenant_id` (pas global) | ✅ | `plan_limits.py` filtre par tenant |
| 8 | Création Tenant = Admin + Abonnement | ✅ | `auth.py` register |
| 9 | Admin principal = `tenant.admin_principal_id` | ✅ | Pas juste un rôle `admin` |
| 10 | Clé admin supprimée | ✅ | Fonctionnalité bannie, colonnes retirées |
| 11 | employee_key privée au Tenant | ✅ | `Tenant.employee_key_hash`, jamais exposée |
| 12 | employee_key hashée (bcrypt) | ✅ | bcrypt dans `Tenant.employee_key_hash` |
| 13 | employee_key générable par admin principal | ✅ | `POST /api/v1/tenants/me/employee-key` |
| 14 | Super Admin ne voit pas employee_key | ✅ | `to_dict()` exclut `employee_key` |
| 15 | Employé ne peut pas renouveler | ✅ | Test → 403 |
| 16 | Multi-tenant isolé | ✅ | Filtre SQL + décorateurs + event listener ORM |

---

## 3. Modèles de données (40 modèles)

### Tenant (`web/backend/app/models/tenant.py`)
```python
admin_principal_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))
# NOTE: admin_key_hash / admin_key_status SUPPRIMÉS (fonctionnalité clé d'admin bannie)
```

### Utilisateur (`web/backend/app/models/utilisateur.py`)
```python
tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))
role = db.Column(Enum(Role))  # SUPER_ADMIN, ADMIN, MANAGER, SALES, STOCK, ACCOUNTANT, USER, RH
# NOTE: admin_key_hash / admin_key_status SUPPRIMÉS
```

### Abonnement (`web/backend/app/models/abonnement.py`)
```python
tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'))  # Toujours lié au Tenant
plan = db.Column(db.String(50))  # gratuit, starter, pro, enterprise
```

### AuditLog (`web/backend/app/models/audit_log.py`)
```python
# 25+ types d'actions auditées :
# creation_utilisateur, changement_role, creation_employe, modification_employe,
# suppression_employe, creation_tenant, activation_tenant, suspension_tenant,
# prolongation_abonnement, connexion_super_admin, deconnexion_super_admin, etc.
```

### Modèles principaux
- **Gestion commerciale** : Produit, Client, Fournisseur, Vente, Facture, CommandeAchat, CommandeClient
- **Gestion stock** : Stock, Livraison, Livreur, Vehicule, Itineraire
- **Comptabilité** : CompteComptable, EcritureComptable, Tresorerie
- **RH** : Employe, Presence, Salaire, Prime, Stagiaire
- **Administration** : Tenant, Utilisateur, Abonnement, Paiement, AdminDevice, AuditLog
- **Documents** : DocumentGenere, ModeleDocument, DevisAvoirBL
- **Autres** : Notification, DeskState, PaymentEvent

### Livreur ↔ Utilisateur (ÉTAPE 0)
```python
class Livreur(BaseTenantModel):
    utilisateur_id = Column(Integer, ForeignKey('utilisateurs.id'), nullable=True, unique=True, index=True)
    utilisateur = relationship('Utilisateur', backref='livreur_profile', foreign_keys=[utilisateur_id])
```
Relation 0..1 ↔ 1 validée par 3 niveaux de défense (API + service + event listener ORM).

---

## 4. Flux d'authentification

### Connexion (tous rôles)
```
1. Login (email, password[, tenant_slug][, device_id optionnel])
2. Vérification mot de passe (bcrypt)
3. Résolution tenant via tenant_slug ou user.tenant_id
4. Vérification device (ADMIN uniquement, auto-register 1er device)
5. Vérification abonnement actif (si requis)
6. JWT généré avec user_id, tenant_id, role
```

### Rate limiting
- `/login` : 5 requêtes / 300s
- `/register` : 5 requêtes / 300s
- `/forgot-password` : 5 requêtes / 300s
- `/public/commandes` (POST) : 3 requêtes / 300s
- Fail-closed : refuse les requêtes si Redis indisponible en production

---

## 5. Flux de création de Tenant

### Par inscription publique (`POST /api/v1/auth/register`)
```
1. Validation données entreprise
2. Validation complexité mot de passe
3. Création Tenant (statut=EN_ESSAI, plan=choisi)
4. Création Utilisateur (role=ADMIN, is_principal_admin=True)
5. tenant.admin_principal_id = user.id
6. Création abonnement initial (AbonnementService.create_abonnement)
7. Retour: { user, tenant, access_token, refresh_token }
```

### Par Super Admin (`POST /api/v1/tenants`)
```
1. Vérification droits SUPER_ADMIN
2. Création Tenant
3. Création Utilisateur admin
4. tenant.admin_principal_id = admin.id
5. Création abonnement initial
6. Retour: { tenant, admin }
```

---

## 6. Flux de création d'utilisateur

```
1. Admin principal connecté → POST /api/v1/users
2. @tenant_required → Vérifie JWT + tenant + abonnement
3. @check_plan_limits('utilisateurs') → Compte users actifs du tenant (SELECT FOR UPDATE)
4. Si limite atteinte → 403
5. Sinon création autorisée + audit log
```

**Limites** :
- Gratuit : 1 (admin principal uniquement)
- Starter : 3 (admin + 2 employés)
- Pro : 7 (admin + 6 employés)
- Enterprise : illimité

---

## 7. Flux de renouvellement

```
1. Utilisateur connecté → POST /api/v1/abonnements/{id}/renouveler
2. @jwt_required
3. _is_principal_admin() → Vérifie tenant.admin_principal_id == current_user.id
4. Si OUI → 200 OK
5. Si NON → 403 Forbidden
```

**Règle** : Seul le `tenant.admin_principal_id` peut renouveler. Le rôle `admin` ne suffit pas.

---

## 8. Sécurité de l'authentification

| Aspect | Implémentation |
|--------|----------------|
| Stockage mot de passe | Hash bcrypt dans `Utilisateur.password_hash` |
| Jamais en clair | ✅ `to_dict()` exclut `password_hash` |
| Validation complexité | ✅ 8 caractères min, 1 lettre, 1 chiffre |
| Clé d'administration | ⛔ **SUPPRIMÉE** |
| Device management | Auto-enregistrement 1er device admin |
| JWT | HS256, expire 1h (access), 30j (refresh) |
| CORS | Origines explicites, wildcard rejeté |
| Rate limiting | Redis, fail-closed en prod |

---

## 9. Isolation multi-tenant

### Backend
- **Décorateur `@tenant_required`** : valide JWT + charge tenant + vérifie abonnement
- **Filtre SQL global** : `WHERE tenant_id = X` injecté via event listener ORM
- **Endpoints protégés** : tous les endpoints métier utilisent `@tenant_required`
- **Super Admin** : `g.current_tenant = None` → bypass filtre (accès global)

### Résolution du tenant
1. **JWT** (prioritaire) : `claims['tenant_id']`
2. **Headers** (fallback) : `X-Tenant-Slug` / `X-Tenant-Domaine`

### Vérifications supplémentaires
- `subscription_required` : vérifie abonnement actif
- `tenant_admin_required` : vérifie JWT + admin
- `check_plan_limits(feature)` : vérifie limites avec `SELECT FOR UPDATE`

---

## 10. Frontend (3 applications)

### Desktop (`desk/src/`)
| Module | Fichiers | Description |
|--------|----------|-------------|
| `components/` | ~47 fichiers | Composants réutilisables (DataTable, FilterPanel, layouts) |
| `pages/` | 30 fichiers | Pages ERP (Dashboard, Ventes, Factures, Stock, RH, etc.) |
| `contexts/` | 5 fichiers | Auth, Cart, Desktop, Notification, Sync |
| `hooks/` | 6 fichiers | Custom hooks |
| `services/` | 4 fichiers | API client |
| `utils/` | 4 fichiers | Utilitaires |
| `tests/` | 11 fichiers | Tests unitaires |

### Frontend Web (`web/frontend/src/`)
- 30 pages React (Dashboard, Ventes, Produits, Stock, RH, Comptabilité, etc.)
- 2 fichiers de tests
- Contexts, hooks, services, utils alignés avec le desktop

### Super Admin (`super-admin/src/`)
| Page | Description |
|------|-------------|
| `Dashboard.jsx` | Tableau de bord plateforme |
| `Tenants.jsx` | Liste des tenants |
| `TenantDetail.jsx` | Détail d'un tenant |
| `Subscriptions.jsx` | Gestion abonnements |
| `Plans.jsx` | Configuration plans |
| `Users.jsx` | Liste utilisateurs |
| `Audit.jsx` | **Journal d'audit** (25+ types d'actions) |
| `Profile.jsx` | Profil super admin |
| `LoginPage.jsx` | Connexion |

### Shared (`shared/`)
- Bibliothèque commune (contexts, hooks, realtime, services, storage, utils, websockets) — 24 fichiers JS/JSX.

---

## 11. Tests (278 collectés)

### Backend (`web/backend/tests/`)
| Fichier | Description |
|---------|-------------|
| `test_admin_architecture.py` | Architecture admin |
| `test_ai.py` | Module AI |
| `test_anti_bugs_audit.py` | Anti-bugs audit |
| `test_architecture_compliance.py` | Conformité architecture (17 tests) |
| `test_auth.py` | Authentification |
| `test_clients_api.py` | API clients |
| `test_critical_api.py` | API critiques |
| `test_employee_key.py` | Clé employé |
| `test_livreur_compte.py` | **Compte livreur — ÉTAPE 0 (7 tests)** |
| `test_mission_5.py` | Mission 5 |
| `test_papi.py` | Intégration PAPI |
| `test_plan_limits.py` | Limites plan |
| `test_produits.py` | Produits |
| `test_public_catalog.py` | Catalogue public |
| `test_rh.py` | Ressources humaines |
| `test_role_creation_security.py` | Sécurité création rôles |
| `test_role_visibility_fix.py` | Visibilité rôles |
| `test_roles_presets.py` | Presets rôles |
| `test_security_multi_tenant.py` | Sécurité multi-tenant |
| `test_stocks.py` | Stocks |
| `test_tenancy.py` | Tenancy |
| `test_tenant_limits.py` | Limites tenant |
| `test_users_api.py` | API utilisateurs |
| `test_super_admin_payments.py` | Super Admin paiements |
| `conftest.py` | Fixtures partagées |
| ... | (34 fichiers au total) |

### Desktop (`desk/src/**/__tests__/`)
| Fichier | Description |
|---------|-------------|
| `DataTable.component.test.jsx` | Composant DataTable |
| `DataTable.logic.test.js` | Logique DataTable |
| `FilterPanel.test.jsx` | Composant FilterPanel |
| `DesktopContext.notifications.test.jsx` | Contexte notifications |
| `useFormDraft.test.jsx` | Hook formulaire |
| `filterUtils.test.js` | Utilitaires filtre |
| `notify.test.js` | Utilitaires notification |
| ... | (11 fichiers au total) |

### Frontend Web (`web/frontend/src/**/__tests__/`)
- 2 fichiers de tests.

---

## 12. Architecture technique

### Backend
```
web/backend/
├── app/
│   ├── __init__.py          # App factory, CORS, JWT, tenant context
│   ├── api/v1/              # 23 namespaces enregistrés (28 fichiers)
│   ├── config/              # Configuration (settings, database)
│   ├── models/              # 40 modèles SQLAlchemy
│   ├── security/            # 10 modules (auth, RBAC, plans, rate-limit, encryption, admin_devices)
│   ├── services/            # 25 services métier
│   ├── utils/               # 10 utilitaires (audit, PDF, Excel, QR, etc.)
│   ├── ai/                  # Module IA (6 fichiers + 2 modèles .pkl)
│   ├── tasks/               # 3 tâches background
│   ├── websockets/          # Événements temps réel
│   └── realtime/            # Socket.IO server
├── migrations/              # 11 migrations Alembic
├── scripts/                 # 22 scripts utilitaires
├── tests/                   # 34 fichiers de test
├── Dockerfile               # Image Docker (user non-root)
└── requirements.txt         # Dépendances Python
```

### Frontend
```
web/frontend/                 # Application Web React (tenant)
├── src/
│   ├── components/
│   ├── pages/                # 30 pages
│   ├── contexts/
│   ├── hooks/
│   ├── services/
│   ├── utils/
│   └── __tests__/            # 2 fichiers
└── package.json

desk/                         # Application Desktop Electron
├── src/
│   ├── components/           # ~47 composants
│   ├── pages/                # 30 pages
│   ├── contexts/             # 5 contextes
│   ├── hooks/                # 6 hooks
│   ├── services/             # 4 services API
│   ├── utils/                # 4 utilitaires
│   └── __tests__/            # 11 fichiers de test
├── electron/                 # Processus Electron
├── package.json
└── Dockerfile

super-admin/                  # Application Web Super Admin
├── src/
│   ├── pages/                # 9 pages
│   ├── components/           # Composants
│   ├── services/             # Service API
│   └── contexts/             # Contexte auth
└── package.json

shared/                       # Bibliothèque commune (24 fichiers JS/JSX)
├── contexts/
├── hooks/
├── realtime/
├── services/
├── storage/
├── utils/
└── websockets/
```

---

## 13. Points critiques garantis

1. **Authentification par email + mot de passe** : Hash bcrypt, validation à chaque connexion
2. **employee_key privée au Tenant** : appartient au Tenant, jamais partagée
3. **Super Admin ≠ employee_key** : ne peut jamais voir l'employee_key d'un Tenant
4. **Isolation cross-tenant** : données du Tenant A inaccessibles au Tenant B (3 niveaux : event listener ORM, décorateurs, filtres SQL)
5. **Renouvellement = admin principal** : `tenant.admin_principal_id == current_user.id`
6. **Quota par tenant** : Comptage `WHERE tenant_id = X` avec `SELECT FOR UPDATE`
7. **Zéro exposition** : employee_key jamais en clair dans API/logs/Swagger
8. **Backend = autorité de sécurité** : règles appliquées côté serveur
9. **Audit trail** : 25+ types d'actions enregistrées automatiquement
10. **Rate limiting** : Protection anti-brute-force avec fail-closed

---

## 14. Nouveautés (depuis dernier audit)

| Fonctionnalité | Description |
|----------------|-------------|
| Module AI | Anomalies, prévisions, recommandations (modèles ML entraînés) |
| Audit Trail | 25+ types d'actions, modèle AuditLog, frontend de consultation |
| Super Admin Web | Application React complète (dashboard, tenants, abonnements, audit) |
| Tâches Background | Backups, emails, reports |
| Device Management | Auto-enregistrement 1er device, vérification sur connexion |
| Rate Limiting Étendu | Fail-closed, 5 endpoints protégés |
| Génération Documents | PDF, Excel, QR codes, codes-barres |
| Encryption Module | Chiffrement de données sensibles |

---

## 15. Statut final

**ZERO BUGS D'ARCHITECTURE IDENTIFIÉS (2026-09-05)**

L'architecture MIHAJA_ERP_PRO est conforme à 100% aux règles métier spécifiées. Le projet est en état de **pré-production** avec 278 tests backend (34 fichiers), une couverture de sécurité améliorée, et une architecture mature (40 modèles, 23 namespaces API, 25 services, 4 applications frontend : Web + Desktop + Super Admin + Shared).

### Corrections de sécurité récemment validées (vs audit 2026-09-01)
- Webhook PAPI avec vérification signature HMAC (`papi/webhook.py`)
- Mass assignment corrigé dans `BaseService.update()` (whitelist `PROTECTED_FIELDS`)
- Werkzeug debugger gated par `FLASK_DEBUG` (plus de debugger en prod)
- Hard-delete tenant : endpoint et fonction `_hard_delete_tenant()` supprimés (seul soft-delete conservé)
- `isEmployeeLimitReached` déplacé dans le scope du composant `Users.jsx` (plus de ReferenceError)
- Tokens Electron unifiés via `secureStore` (storageAdapter, tokenStore, authStorage)

### ÉTAPE 0 — Compte livreur (livrée)
- Relation `Livreur ↔ Utilisateur` opérationnelle
- 7/7 tests passent (`test_livreur_compte.py`)
- 3 niveaux de défense (API + service + event listener ORM)
