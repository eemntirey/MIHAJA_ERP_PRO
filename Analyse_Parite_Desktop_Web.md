# Audit de parité — Fonctionnalités Web → Desktop

**Date** : 18 août 2026
**Périmètre** : uniquement `desk/` (Desktop / Electron). La version Web (`web/`) a été analysée **en lecture seule**, sans aucune modification, suppression ou altération.
**Méthode** : comparaison ligne-à-ligne de `services/api.js`, des pages, des layouts (`MainLayout`/`DesktopLayout`), des `AuthContext` et de `App.js` entre `web/frontend/src` et `desk/src`.

---

## 1. VERDICT GÉNÉRAL

L'application Desktop est un **fork quasi identique du back-office Web** :

- **17 pages entreprise** présentes côté Desktop avec des tailles de fichier équivalentes à la Web (ex. `Dashboard` 715/715, `AI` 499/499, `HR` 661/661, `Clients` 463/463). Les pages Desktop sont des copies du code Web.
- **Couche de services API complète** côté Desktop (`desk/src/services/api.js`), et même **plus riche** que la Web : elle expose en plus `roleService`, `permissionService`, `userService` et `dashboardService.getPublicStats` (absents de la Web).
- `AuthContext` : gestion de session, `tenant`, `subscription` et `fetchSubscriptionStatus` **strictement identiques** entre Web et Desktop.
- Même backend Flask multi-tenant partagé (`REACT_APP_API_URL` → `/api/v1`). Aucune dépendance backend spécifique à combler.

**Conclusion** : la quasi-totalité des fonctionnalités opérationnelles sur la Web **fonctionne déjà sur le Desktop**. Les écarts réels sont peu nombreux et se répartissent en 3 catégories :
1. **Une régression fonctionnelle** (erreurs API muettes sur Desktop).
2. **Des fonctionnalités volontairement hors périmètre** (vitrine B2C, propre à la Web).
3. **Des améliorations Desktop prévues mais non câblées** (`Plan_Desktop.md`) + routes RBAC mortes.

---

## 2. LISTE COMPARATIVE — MANQUANTS / INCOMPLÈTS SUR DESKTOP

### A. Régression fonctionnelle (Web OK → Desktop cassé)

| # | Fonctionnalité | Web | Desktop | Impact |
|---|----------------|-----|---------|--------|
| A1 | **Feedback d'erreur API** | `api.js` affiche `toast.error(...)` pour toutes les erreurs non-401 (lignes 190-193) | `desk/src/services/api.js` **n'a pas** cette branche ; les erreurs 400/404/409/500 sont **silencieuses** (rejetées sans toast) | **Critique** : l'utilisateur Desktop ne voit aucun message en cas d'échec → chaque module donne l'impression d'être « bloqué ». Touche **tous les modules**. |
| A2 | **Pages RBAC dédiées accessibles** | La Web gère Rôles/Permissions/Utilisateurs dans `SuperAdmin` (fork identique présent sur Desktop) | `Roles.jsx`, `Permissions.jsx`, `Users.jsx` sont **importés dans `App.js` mais NON routés** (aucune `<Route>`, aucune entrée dans `navConfig.js`) → **injoignables**. `navConfig` Desktop ne contient que `/clients`, `/hr`, `/super-admin` | Moyen : l'UI RBAC dédiée Desktop est du code mort. Le RBAC fonctionne encore via `SuperAdmin`, mais l'entrée dédiée n'existe pas. |

### B. Fonctionnalités Web volontairement hors périmètre Desktop (B2C)

Ces pages sont propres à la **vitrine publique / e-commerce** de la Web. Le Desktop est l'application back-office entreprise (Electron) : elles n'ont **pas vocation** à y figurer.

| Fonctionnalité Web | Présence Desktop | Décision |
|--------------------|------------------|----------|
| Catalogue (`/catalogue`) | Absente | Hors périmètre (B2C) |
| Panier (`/cart`) | Absente | Hors périmètre |
| Checkout (`/checkout`) | Absente | Hors périmètre |
| Détail produit (`/produits/:id`) | Absente | Hors périmètre |
| Suivi commande (`/order-tracking`, `/suivi`) | Absente | Hors périmètre |
| Mes commandes (`/mes-commandes`) | Absente | Hors périmètre |
| Accueil (`/`) / Contact (`/contact`) | Absente | Hors périmètre |
| Page `Documentation` (`/documentation`) | Absente | **À clarifier** : page d'aide, peut être utile sur Desktop (voir Plan §2). |

> Note : les services publics (`publicApi`, `publicCatalogueService`, `public/notifications`) sont absents de `desk/src/services/api.js`, ce qui est **cohérent** (pas de vitrine sur Desktop).

### C. Composants Desktop avancés définis mais NON utilisés (`Plan_Desktop.md`)

Présents dans `desk/src/components/**` mais **0 référence dans les pages** (vérifié par grep) :

| Composant | État | Fonctionnalité attendue (Plan §) |
|-----------|------|----------------------------------|
| `CommandPalette` | **Câblé** via `DesktopLayout` (CMD+K) | Palette de commandes |
| `TitleBar` | **Câblé** (uniquement `IS_ELECTRON`) | Barre de titre native |
| `SplitView` / `ResizablePanel` | Défini, **non utilisé** | Vue multi-panneaux (Plan §3) |
| `DataTable` | Défini, **non utilisé** | Tri, redimensionnement colonnes, sélection multiple, virtualisation (Plan §5.1) |
| `FilterPanel` | Défini, **non utilisé** | Filtres avancés (Plan §5.1) |
| `FAB` | Défini, **non utilisé** | Actions rapides flottantes (Plan §5.3) |
| `NotificationDropdown` | Défini, **non utilisé** | Notifications (`DesktopContext.notifications` existe mais inexploité) |
| `VirtualList` | Défini, **non utilisé** | Virtualisation listes |
| `FormGrid` | Défini, **non utilisé** | Formulaires en grille (Plan §5.2) |

### D. Fonctionnalités natives Electron (`Plan_Desktop.md` §11) — non implémentées

`desk/electron/main.js` n'importe que `app, BrowserWindow, Menu, ipcMain`. Absence de :
- Impression système (`webContents.print` / `dialog`)
- Notifications OS (`Notification`)
- Drag & drop de fichiers (import CSV)
- Menu natif complet + auto-update (`electron-updater`)

> Ces points sont des **enrichissements Desktop**, pas une parité avec la Web (la Web ne les a pas non plus). Ils rentrent dans « parfait fonctionnement sur Desktop ».

### E. Parité service-level — OK (et plus riche sur Desktop)

`desk/src/services/api.js` couvre **tous** les endpoints entreprise de la Web, plus `roleService` / `permissionService` / `userService` / `getPublicStats`. Aucun endpoint manquant côté Desktop.

---

## 3. PLAN D'ACTION TECHNIQUE (scope Desktop uniquement, architecture respectée)

**Principes** :
- Toutes les modifications ciblent `desk/` uniquement. `web/` reste en lecture seule.
- Réutiliser les composants **déjà présents** dans `desk/src/components` plutôt que réécrire.
- Backend déjà multi-tenant et partagé : aucune modification backend requise pour la parité.

### Phase 0 — Correction de régression (priorité haute, effort faible) 🔴

- **P0.1 — Toast d'erreur API** : reporter la branche `toast.error(msg)` (non-401) de `web/frontend/src/services/api.js` (lignes 190-193) dans `desk/src/services/api.js` (interceptor response). Cela rétablit le feedback utilisateur sur **tous** les modules. *Aucun changement Web.*

### Phase 1 — RBAC dédié (effort moyen) 🟠

- **P1.1 — Routage** : ajouter dans `desk/src/App.js` les `<Route>` pour `roles`, `permissions`, `users` (pages déjà codées), et les entrées correspondantes dans `desk/src/components/layout/navConfig.js` (groupe « Admin »). *Alternative si décision de conserver le RBAC dans `SuperAdmin` : supprimer les imports/pages morts (P1.2).*
- **P1.2 — Nettoyage** : retirer les imports `Roles/Permissions/Users` orphelins de `App.js` si la route n'est pas ajoutée, pour éviter le code mort.

### Phase 2 — Composants Desktop avancés (effort élevé, valeur haute) 🟡

- **P2.1 — `DataTable`** : remplacer les `<table>` bruts de `Products`, `Clients`, `Sales`, `Invoices`, `Inventory` par le `DataTable` existant (tri, resize colonnes, sélection multiple, virtualisation `@tanstack/react-virtual` déjà en dépendance).
- **P2.2 — `SplitView` + `ResizablePanel`** : envelopper liste/détail sur `Products`, `Clients`, `Sales`, `Invoices` (Plan §3).
- **P2.3 — `FilterPanel`** : brancher les filtres avancés sur les pages listes.
- **P2.4 — `FAB`** : actions rapides (Nouvelle vente / client / facture).
- **P2.5 — `NotificationDropdown`** : câbler `DesktopContext.notifications` (déjà présent) au composant déjà défini.

### Phase 3 — Fonctionnalités natives Electron (Plan §11) 🟡

- **P3.1 — Impression système** : exposer `window.electron.print` via `preload.js` (`ipcRenderer`), bouton « Imprimer » sur `Documents` / `Invoices`.
- **P3.2 — Notifications OS** : `main.js` → `Notification` sur événements commande / stock critique.
- **P3.3 — Drag & drop CSV** : exploiter `compteService/ecritureService/tresorerieService.import` déjà présents.
- **P3.4 — Menu natif + auto-update** : `Menu` + `electron-updater`.

### Phase 4 — Qualité & documentation 🟢

- **P4.1** : supprimer les imports morts dans `App.js`.
- **P4.2** : documenter explicitement le hors-périmètre B2C (§B) pour éviter de futures demandes de portage de la vitrine.
- **P4.3** (optionnel) : envisager à terme une **lib de composants commune** (`web/frontend/src` ↔ `desk/src`) pour éviter la dérive des forks (actuellement copies indépendantes).

---

## 4. RÉSUMÉ DES LIVRABLES

| Catégorie | Écart | Priorité |
|-----------|-------|----------|
| Régression | Erreurs API muettes (A1) | 🔴 Haute |
| RBAC | Pages dédiées non routées (A2) | 🟠 Moyenne |
| Hors périmètre | Vitrine B2C (B) | ⚪ Décision |
| Enhancement | Composants Desktop non câblés (C) | 🟡 Planifié |
| Enhancement | Natif Electron (D) | 🟡 Planifié |
| Parité | Services API | ✅ OK (Desktop plus riche) |

**Aucune modification n'a été apportée à la version Web.** Toutes les actions ci-dessus concernent `desk/` et le backend partagé (déjà compatible).
