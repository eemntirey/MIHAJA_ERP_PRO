# MIHAJA_ERP_PRO — Architecture Update Report

**Date** : 2026-08-31
**Mission** : Suppression totale de `admin_key` et mise en place de `employee_key`
**Statut** : ✅ Architecture conforme

---

## 1. Ancienne architecture supprimée

### `admin_key` — SUPPRIMÉ DÉFINITIVEMENT

| Élément | Statut |
|---------|--------|
| `admin_key_hash` (modèle Tenant) | ⛔ SUPPRIMÉ |
| `admin_key_status` (modèle Tenant) | ⛔ SUPPRIMÉ |
| `hash_admin_key()` (fonction) | ⛔ SUPPRIMÉ |
| `verify_admin_key()` (fonction) | ⛔ SUPPRIMÉ |
| `_resolve_admin_key()` (fonction) | ⛔ SUPPRIMÉ |
| `_validate_admin_key()` (fonction) | ⛔ SUPPRIMÉ |
| `StatutAdminKey` (enum) | ⛔ SUPPRIMÉ |
| Route `/api/v1/auth/admin-keys/missing` | ⛔ SUPPRIMÉ |
| `getAdminKey()` / `setAdminKey()` (frontend) | ⛔ SUPPRIMÉ |

---

## 2. Nouvelle architecture

### `employee_key` — CLÉ PRIVÉE DU TENANT

```
MIHAJA_ERP_PRO

SUPER ADMIN
    │
    ├── TENANTS
    ├── ABONNEMENTS
    ├── PAIEMENTS
    └── SUPERVISION
           │
           ▼
       TENANT == ADMIN
           │
           ├── Entreprise
           ├── Abonnement
           ├── Employés
           ├── Utilisateurs
           ├── Employee Key (privée)
           └── Modules métier
                    │
                    ▼
             ROLE + PERMISSIONS
```

### Règle de confidentialité

```
Employee Key
     │
     ├── Tenant propriétaire → ✅ peut voir / gérer sa clé
     ├── Autres Tenants → ❌ ne peuvent pas voir la clé
     └── Super Admin → ❌ ne doit JAMAIS voir la clé
```

### Règle absolue

```
ADMIN KEY = SUPPRIMÉE
EMPLOYEE KEY = PRIVÉE AU TENANT
```

---

## 3. Documentation mise à jour

| Fichier | Modification |
|---------|--------------|
| `AUDIT_ARCHITECTURE.md` | Section 13 : diagramme mis à jour avec `employee_key (privée)` |
| | Section 14 : points critiques mis à jour (confidentialité employee_key) |
| | Sections 10-15 : marquées ⛔ SUPPRIMÉ |
| `design_erp.md` | Section 10 : ajout documentation `employee_key` |
| | Section 10 : `admin_key` marquée SUPPRIMÉE (BANNIE) |
| `.kilo/skills/mihaja-erp-architecture/SKILL.md` | Section 19bis : ajout règles `employee_key` |
| | Section 19 : `admin_key` marquée SUPPRIMÉE (BANNIE) |

---

## 4. Skills mis à jour

| Skill | Modification |
|-------|--------------|
| `mihaja-erp-architecture` | Section 19bis : `EMPLOYEE KEY — CLÉ PRIVÉE DU TENANT` |
| | Règles de confidentialité ajoutées |
| | Règles strictes ajoutées (6 règles) |
| | Exemples de comportement API ajoutés |

---

## 5. Code impacté

### Backend

| Fichier | Modification |
|---------|--------------|
| `web/backend/app/models/tenant.py` | Ajout `employee_key_hash` et `employee_key_status` |
| | Ajout méthodes `set_employee_key()`, `verify_employee_key()`, `generate_employee_key()` |
| | `to_dict()` : paramètre `include_employee_key` ajouté |
| `web/backend/app/api/v1/tenants.py` | Endpoint `GET /tenants/me/employee-key` : ne retourne plus le hash |
| | Endpoint `POST /tenants/me/employee-key` : régénération sécurisée |

### Frontend (Electron)

| Fichier | Modification |
|---------|--------------|
| `desk/shared/contexts/AuthContext.jsx` | Suppression `admin_key` dans `register()` |
| | Suppression `adminKey` dans `login()` |
| | Suppression `admin_key` dans le payload de login |
| `desk/shared/storage/authStorage.js` | Suppression `getAdminKey()` / `setAdminKey()` |
| | Suppression `ADMIN_KEY_KEY` / `ADMIN_KEY` |

### Tests

| Fichier | Modification |
|---------|--------------|
| `test_architecture_compliance.py` | Réécriture complète sans `admin_key` |
| | Tests de connexion par email + mot de passe uniquement |
| `test_security_multi_tenant.py` | Suppression `admin_key` dans `_login()` |
| | Suppression `admin_key` dans tous les appels |
| `test_anti_bugs_audit.py` | Suppression import `hash_admin_key` |
| | Suppression `admin_key` dans `_login()` et `_auth()` |
| | Remplacement Test11 (cle admin) par Test11 (employee_key) |
| | Remplacement Test12 (password != cle) par Test12 (password securise) |
| | Suppression `admin_key` dans tous les appels |
| `test_admin_architecture.py` | Suppression `admin_key` dans `_make_admin_tenant()` |
| | Suppression `admin_key` dans `_login()` |
| | Suppression `admin_key` dans tous les appels |
| | Test 21 : vérifie que `admin_key` n'est PLUS retournée |
| | Test 27 : vérifie que `admin_key` n'est PAS dans la réponse |
| `test_employee_key.py` | **NOUVEAU** : Tests complets pour `employee_key` |

---

## 6. Sécurité

### Tenant isolation

- ✅ Toutes les données métier isolées par `tenant_id`
- ✅ `employee_key` isolée par Tenant
- ✅ Tenant A ne peut pas voir l'`employee_key` de Tenant B

### employee_key protection

- ✅ `employee_key` jamais exposée dans les endpoints Super Admin
- ✅ `employee_key_hash` jamais sérialisée dans `to_dict()` par défaut
- ✅ `employee_key` retournée UNE SEULE FOIS après génération
- ✅ Hash bcrypt pour le stockage
- ✅ Backend = autorité de sécurité (pas de masquage frontend)

### API exposure

```
GET /tenant/me → ✅ employee_key autorisée selon les règles métier
GET /super-admin/tenants → ❌ employee_key NE PAS RETOURNER
GET /super-admin/users → ❌ employee_key NE PAS RETOURNER
GET /tenants/<id> (Super Admin) → ❌ employee_key NE PAS RETOURNER
```

---

## 7. Tests

### Tests exécutés

| Test | Description | Statut |
|------|-------------|--------|
| Test 1 | Tenant A crée sa clé employé | ✅ PASS |
| Test 1b | Tenant A régénère sa clé employé | ✅ PASS |
| Test 2 | Tenant A consulte sa clé | ✅ PASS |
| Test 2b | Non-admin principal ne peut pas accéder | ✅ PASS |
| Test 3 | Tenant B ne peut pas voir la clé de A | ✅ PASS |
| Test 4 | Super Admin liste tenants sans employee_key | ✅ PASS |
| Test 5 | Super Admin liste users sans employee_key | ✅ PASS |
| Test 6 | Super Admin ne peut pas récupérer la clé | ✅ PASS |
| Test 7 | Aucune référence fonctionnelle à admin_key | ✅ PASS |
| Test 7b | Aucune admin_key dans les réponses API | ✅ PASS |

### Recherche globale

| Terme | Résultat |
|-------|----------|
| `admin_key` | ❌ Aucune référence fonctionnelle active |
| `hash_admin_key` | ❌ Aucune référence fonctionnelle active |
| `verify_admin_key` | ❌ Aucune référence fonctionnelle active |
| `_resolve_admin_key` | ❌ Aucune référence fonctionnelle active |
| `_validate_admin_key` | ❌ Aucune référence fonctionnelle active |

---

## 8. Problèmes restants

Aucun problème critique identifié.

**Notes** :
- Les fichiers de migration (`c3d4e5f6a7b8_add_tenant_admin_key_and_principal.py`) sont conservés pour l'historique mais ne sont plus utilisés
- Les références dans la documentation sont clairement marquées comme "SUPPRIMÉE (BANNIE)" pour éviter toute confusion

---

## 9. Conclusion

### ✅ Architecture conforme

L'architecture MIHAJA_ERP_PRO est désormais conforme à 100% aux règles métier spécifiées :

1. ✅ `admin_key` = SUPPRIMÉE (aucune référence fonctionnelle active)
2. ✅ `employee_key` = propriété privée du Tenant
3. ✅ Super Admin = aucune visibilité sur `employee_key`
4. ✅ Tenant = peut gérer sa `employee_key`
5. ✅ Tenant A ≠ Tenant B (isolation stricte)
6. ✅ TENANT == ADMIN
7. ✅ Fiche employé ≠ compte utilisateur
8. ✅ Fiche stagiaire ≠ compte utilisateur
9. ✅ Backend = autorité de sécurité
10. ✅ Toute donnée sensible respecte l'isolation tenant

### Source de vérité

```
ADMIN KEY = SUPPRIMÉE
EMPLOYEE KEY = PRIVÉE AU TENANT
```

**Ne jamais réintroduire `admin_key` dans une future fonctionnalité, migration, API, interface, skill ou documentation.**
