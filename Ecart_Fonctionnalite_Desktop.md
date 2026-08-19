# Écart Fonctionnalité — Desktop (Electron) vs Web

**Scope :** `desk/src` (modifiable) vs `web/frontend/src` (référence en lecture seule) + `web/backend/app/api/v1/` (read-only).  
**Date :** 2026-08-18  
**Statut :** Audit complet — Document de plan d'action technique.

---

## 1. Synthèse exécutive

| Catégorie | Web (référence) | Desktop (actuel) | Écart majeur |
|---|---|---|---|
| Pages routables | 28 | 20 (+3 importées non routées) | **10 pages publiques absentes** + **3 pages admin non routées** |
| AuthProvider | ✅ `AuthProvider` + `useAuth` | ❌ `useAuth` seulement — **AuthProvider jamais monté** | **Bug critique — Auth cassée sur Desktop** |
| Routeur | `BrowserRouter` | `HashRouter` (index.js:4) | Compatible (Electron), garder HashRouter |
| Composants desktop avancés | N/A | 9 créés, **0 importés** | **Code mort** — DataTable, FAB, FilterPanel, FormGrid, VirtualList, SplitView, ResizablePanel, DesktopTopBar, NotificationDropdown |
| Hooks desktop | N/A | 2 créés, **0 appelés** | **Code mort** — useKeyboardShortcuts, useSplitView |
| Service desktopApi | Web-only | 4 services créés, **0 importés** | **Code mort** — notificationService, favoriteService, columnConfigService, filterPresetService |
| Electron main | N/A | 60 lignes — contrôles fenêtre uniquement | **Gap majeur** — pas de menu natif, notifications, impression, drag-drop, auto-update |
| Preload IPC | N/A | 15 lignes — 5 canaux fenêtre | **Gap** — pas de canaux FS/print/notif/drag-drop |
| Landing/marketing | 7 composants + CSS | Absents | Pages publiques + landing absentes du Desktop |

---

## 2. Bug critique : AuthProvider absent

### Web (correct — `web/frontend/src/App.js:6`)
```js
import { AuthProvider, useAuth } from './contexts/AuthContext';
// …
<AuthProvider>
  <CartProvider>
    <BrowserRouter>
      <Routes>...</Routes>
    </BrowserRouter>
  </CartProvider>
</AuthProvider>
```

### Desktop (défectueux — `desk/src/App.js`)
```js
import { useAuth } from './contexts/AuthContext';   // ligne 7 — AuthProvider NON importé
// …
<DesktopProvider>      // ligne 111 — seul provider monté
  <Routes>...</Routes>
</DesktopProvider>
```

**Conséquence :** `ProtectedRoute` (App.js:44) appelle `useAuth()` → `useContext(AuthContext)` retourne `undefined` → **lève l'erreur** `'useAuth must be used within an AuthProvider'` (AuthContext.jsx:14). L'application desktop ne peut afficher **aucune** page protégée. `AuthProvider` est défini (AuthContext.jsx:20) mais **jamais importé ni utilisé** dans tout l'arbre du composant.

### Correctif (à appliquer dans `desk/src/App.js`)
```js
import { AuthProvider, useAuth } from './contexts/AuthContext';
// …
return (
  <AuthProvider>
    <DesktopProvider>
      <Routes>...</Routes>
    </DesktopProvider>
  </AuthProvider>
);
```

---

## 3. Pages manquantes ou inaccessibles

### 3.1 Pages publiques absentes du routing Desktop (10)

Ces pages existent dans `web/frontend/src/pages/` mais **n'ont aucun équivalent routé** dans `desk/src/App.js`:

| Page Web | Fonction | Présent sur Desktop |
|---|---|---|
| `Home` | Page d'accueil marketing | ❌ |
| `Catalog` | Catalogue public produits | ❌ |
| `OrderTracking` | Suivi de commande public | ❌ |
| `Contact` | Formulaire contact | ❌ |
| `About` | À propos | ❌ |
| `CGV` / `Privacy` / `Terms` | Mentions légales | ❌ |
| `Register` (public step 1) | Inscription multi-étapes | ✅ (mais `RegisterCompany`/`RegisterUser` sont partielles) |

**Composants landing associés absents** (`web/frontend/src/components/landing/`) :
`Catalog`, `Header`, `Footer`, `Hero`, `OrderTracking`, `Testimonials`, `TrustBar` + `web/frontend/src/styles/landing.css`.

> **Note :** `Register`, `RegisterUser`, `RegisterCompany`, `ForgotPassword`, `ResetPassword` sont **déjà importés et routés** sur Desktop (App.js:11-16, 116-120). Il s'agit des 4 pages d'auth. Les 10 pages ci-dessus sont les **pages publiques/marketing** absentes.

### 3.2 Pages admin importées mais non routées (3)

`desk/src/App.js` importe (lignes 39-41) mais **n'ajoute pas au `<Routes>`** :

| Page | Namespace backend | Routée |
|---|---|---|
| `Roles` | `/api/v1/roles` | ❌ |
| `Permissions` | `/api/v1/permissions` | ❌ |
| `Users` | `/api/v1/users` | ❌ |

**Correctif :** ajouter 3 routes dans le `<Route element={...ProtectedRoute}>` block :
```jsx
<Route path="roles" element={<Roles />} />
<Route path="permissions" element={<Permissions />} />
<Route path="users" element={<Users />} />
```
Ces pages nécessitent le rôle `SUPER_ADMIN` (défini dans `ProtectedRoute`, App.js:64).

### 3.3 Pages Web présentes mais avec des écarts de fonctionnalité

| Page | Web | Desktop | Écart |
|---|---|---|---|
| `Dashboard` | Widgets, stats temps réel, graphiques | Présente | Vérifier données en temps réel |
| `Products` | CRUD complet + upload images + catégories | Présente | Vérifier upload images |
| `Clients` | CRUD + cartographie + historique | Présente | Vérifier cartographie |
| `Sales` | CRUD + paiement partiel + état | Présente | Vérifier paiement partiel |
| `Invoices` | PDF généré + envoi email | Présente | PDF généré côté backend, mais Desktop n'a pas d'impression native |
| `Payments` | Multi-moyens + reçu | Présente | Vérifier reçu |
| `Inventory` | Mouvements + alertes stock critique | Présente | Alertes stock critique (DesktopTopBar quickStats) |
| `Suppliers` | CRUD + conditions paiement | Présente | Vérifier |
| `Purchases` | CRUD + devis -> bon | Présente | Vérifier |
| `Delivery` | Suivi + bordereau | Présente | Vérifier bordereau |
| `HR` | RH — employés, congés, paie | Présente | Vérifier paie |
| `Accounting` | Comptabilité — écritures, grand livre | Présente | Vérifier |
| `Documents` | Gestion documents + versionnage | Présente | Vérifier |
| `AI` | Assistant IA multi-fonctions | Présente | Vérifier |
| `Subscription` | Abonnement + paiement | Présente | Vérifier |
| `SuperAdmin` | Admin tenant | Présente | Vérifier |

---

## 4. Code mort — Composants desktop créés mais jamais importés (9)

Ces composants existent dans `desk/src/components/` mais **aucune import n'existe en dehors de leur fichier source** (confirmé par grep) :

| Composant | Chemin | Fonctionnalité | DesktopContext utilisé |
|---|---|---|---|
| `DataTable` | `components/desktop/DataTable.jsx` | Colonnes triables, redimensionnables, visibles/cachables, sélection multi-lignes, pagination | `columnConfigService` (dead) |
| `FAB` | `components/desktop/FAB.jsx` | Bouton flottant actions rapides | Aucun |
| `FilterPanel` | `components/desktop/FilterPanel.jsx` | Filtres avancés (11 opérateurs) | `filterPresetService` (dead) |
| `FormGrid` | `components/desktop/FormGrid.jsx` | Grille de formulaire responsive | Aucun |
| `VirtualList` | `components/desktop/VirtualList.jsx` | Liste virtuel (@tanstack/react-virtual) | Aucun |
| `SplitView` | `components/layout/SplitView.jsx` | Vue divisée redimensionnable | `useSplitView` (dead) |
| `ResizablePanel` | `components/layout/ResizablePanel.jsx | Panneau redimensionnable | Aucun |
| `DesktopTopBar` | `components/layout/DesktopTopBar.jsx` | Topbar avec breadcrumbs, quick-stats, notifications, CMD+K | `NotificationDropdown` (dead), `DarkModeToggle` |
| `NotificationDropdown` | `components/layout/NotificationDropdown.jsx` | Dropdown notifications | `markNotificationRead` (desktopApi dead) |

### 4.1 Code mort — Hooks (2)

| Hook | Chemin | Fonction |
|---|---|---|
| `useKeyboardShortcuts` | `hooks/useKeyboardShortcuts.js` | CMD+K (palette), CMD+N/B/F, raccourcis globaux |
| `useSplitView` | `hooks/useSplitView.js` | GestionSplitView / redimensionnement colonnes |

**Observation :** `DesktopContext.jsx` gère `splitView` (ligne 29) et `commandPaletteOpen` (ligne 72) en state, mais `useKeyboardShortcuts` et `useSplitView` ne sont **jamais appelés**. La CommandPalette est ouverte par un clic sur le bouton de recherche dans `DesktopSidebar.jsx` (ligne 136) — pas via `⌘K`.

---

## 5. Code mort — Services desktopApi (4)

`desk/src/services/desktopApi.js` définit 4 services référençant des **endpoints backend qui n'existent pas** (confirmé par absence de namespace dans `web/backend/app/api/v1/__init__.py`):

| Service | Endpoint | Namespace backend | Existe? |
|---|---|---|---|
| `notificationService` | `/notifications` | ❌ Aucun | Non |
| `favoriteService` | `/favorites` | ❌ Aucun | Non |
| `columnConfigService` | `/desk/columns/{module}` | ❌ `/desk` n'existe pas | Non |
| `filterPresetService` | `/desk/filters/{module}` | ❌ `/desk` n'existe pas | Non |

**Services backend existants** (`web/backend/app/api/v1/__init__.py`) :
`auth, clients, produits, ventes, stocks, factures, paiements, dashboard, ai, public, tenants, abonnements, documents, livraisons, rh, achats_devis, comptabilite, roles, permissions, users` (20 namespaces).

---

## 6. Écarts Electron — Processus principal (`main.js`)

### 6.1 Menu natif
```js
// main.js:50
Menu.setApplicationMenu(null);  // Menu complètement désactivé
```
**Absence :** Aucun menu système (Fichier, Édition, Affichage, Aide). Pas de `Menu.buildFromTemplate()`.

### 6.2 Notifications système
**Absence :** Aucun `ipcMain.handle('notify', ...)` ou `new Notification()`.

### 6.3 Impression
**Absence :** Aucun `ipcMain.handle('print', ...)` → `webContents.print()`.  
**Impact :** Factures, devis, bordereaux ne peuvent pas être imprimés directement depuis le Desktop. Web utilise `window.print()` (CSS media print) — Desktop devrait exposer une API d'impression native.

### 6.4 Drag & Drop
**Absence :** Aucun gestionnaire `win.on('drop')` / `webContents.on('drop')` pour l'upload de fichiers par glissement.

### 6.5 Auto-update
**Absence :** Aucune intégration `electron-updater` / `autoUpdater`.

### 6.6 IPC exposé (preload.js — 15 lignes)
**Exposé :** `minimize`, `maximize`, `unmaximize`, `close`, `quit`, `isMaximized`, `onMaximizeChanged` (7 canaux).  
**Manquant :** Channels pour: `notify`, `print`, `saveFile`, `openFile`, `readFile` (dialog), `checkForUpdates`, `setBadge`, `relaunch`.

---

## 7. Plan d'action technique — Priorisation

### Phase 0 — Bug critique (URGENT)
```
[ ] desk/src/App.js:111 — Envelopper <DesktopProvider> dans <AuthProvider>
     Importer AuthProvider depuis ./contexts/AuthContext (non useAuth seulement)
     → Restaure toute l'authentication Desktop
```

### Phase 1 — Routing incomplet
```
[ ] desk/src/App.js — Ajouter 3 routes admin manquantes:
    /roles, /permissions, /users (ProtectedRoute + SUPER_ADMIN)
[ ] desk/src/App.js — Route "/" → /dashboard (au lieu de /login) si authenticité
     (Actuellement Navigate vers /login — correct tant que AuthProvider absent)
```

### Phase 2 — Intégration composants desktop créés (code mort → fonctionnel)

**2a. TopBar + Notifications (haut priorité UX)**
```
[ ] desk/src/components/layout/DesktopLayout.jsx — Utiliser DesktopTopBar à la place de TopBar
     → Active breadcrumbs, quick-stats, notification dropdown, CMD+K bouton
```

**2b. Keyboard shortcuts**
```
[ ] desk/src/hooks/useKeyboardShortcuts.js — Activer le hook dans DesktopLayout
     → CMD+K (palette), CMD+N (nouveau), CMD+B (barre latérale), CMD+F (recherche)
```

**2c. DataTable + FilterPanel (remplacer tables simples)**
```
[ ] Migrer pages: Dashboard, Products, Clients, Sales, Invoices, Payments,
     Inventory, Suppliers, Purchases, Delivery, Documents
     → Utiliser DataTable avec colonnes persistées + FilterPanel
```

**2d. VirtualList (performance)**
```
[ ] Activer sur pages à grande liste (Products, Clients, Invoices, Documents)
```

**2e. SplitView / ResizablePanel**
```
[ ] Activer sur Sales (détails facture) ou Inventory (mouvements) via useSplitView
```

**2f. FAB + FormGrid**
```
[ ] FAB sur Sales (nouvelle vente), Purchases (nouveau devis)
     → FormGrid pour formulaires de création/édition
```

### Phase 3 — Services desktopApi + Backend

**3a. Notification service → backend**
```
[ ] web/backend/app/api/v1/notifications.py — Créer namespace /notifications
     (GET liste, POST marquer lue, DELETE)
[ ] Registrer dans __init__.py (ligne 18)
```

**3b. Favorites → localStorage (front-only)**
```
[ ] desktopApi.js favoriteService — Utiliser localStorage au lieu de API
     (DesktopSidebar.jsx gère déjà les favoris en localStorage — unifier)
```

**3c. Column config + Filter presets → localStorage**
```
[ ] desktopApi.js columnConfigService — Persister dans localStorage
[ ] desktopApi.js filterPresetService — Persister dans localStorage
```

### Phase 4 — Pages publiques/marketing (10 pages)

```
[ ] Créer desk/src/pages/Catalog.jsx (public catalogue produits)
[ ] Créer desk/src/pages/OrderTracking.jsx (suivi public commande)
[ ] Créer desk/src/pages/Home.jsx (page d'accueil)
[ ] Créer desk/src/pages/Contact.jsx
[ ] Créer desk/src/pages/About.jsx
[ ] Créer desk/src/pages/CGV.jsx, Privacy.jsx, Terms.jsx
[ ] Importer desk/src/components/landing/* (7 composants) depuis web/
     → OU créer versions desktop du landing
[ ] Importer web/frontend/src/styles/landing.css
[ ] Ajouter routes publiques (sans auth) dans desk/src/App.js
     → Catalog, OrderTracking accessibles sans login
```

### Phase 5 — APIs Electron manquantes

```
5a. main.js — Menu natif
    [ ] Menu.buildFromTemplate() avec Fichier/Édition/Affichage/Aide
    [ ] Raccourcis clavier natifs (Cmd+Q, Cmd+W, etc.)

5b. main.js — Notifications système
    [ ] ipcMain.handle('notify', (_, {title, body}) => new Notification({title, body}).show())

5c. main.js — Impression
    [ ] ipcMain.handle('print', () => win.webContents.print())

5d. main.js — Dialog file picker
    [ ] ipcMain.handle('open-file-dialog', () => dialog.showOpenDialog(...))
    [ ] ipcMain.handle('save-file-dialog', () => dialog.showSaveDialog(...))

5e. preload.js — Exposer nouveaux canaux
    [ ] contextBridge.exposeInMainWorld('electronAPI', {
        notify, print, openFile, saveFile, checkForUpdates, setBadge, relaunch
      })

5f. main.js — Drag & Drop
    [ ] win.webContents.on('will-finish-launching') + drop handlers

5g. Auto-update
    [ ] Intégrer electron-updater (package.json + main.js)
```

### Phase 6 — Tests & validation

```
[ ] AuthProvider wrapper — vérifier useAuth ne throw plus
[ ] 3 routes admin — vérifier SUPER_ADMIN peut accéder
[ ] CMD+K — ouvre CommandPalette via clavier
[ ] Notifications — affichées dans DesktopTopBar + dropdown
[ ] Impression facture — test print via bouton
[ ] Drag-drop upload — test fichier sur zone cible
```

---

## 8. Matrice de traçabilité backend ↔ Desktop

| Namespace backend | Pages web | Pages desktop | Desktop route? | Implémenté? |
|---|---|---|---|---|
| `auth` | Login, Register, Forgot, Reset | ✅ Toutes | ✅ | ✅ (sans AuthProvider) |
| `produits` | Products | Products | ✅ | ✅ |
| `clients` | Clients | Clients | ✅ | ✅ |
| `ventes` | Sales | Sales | ✅ | ✅ |
| `stocks` | Inventory | Inventory | ✅ | ✅ |
| `factures` | Invoices | Invoices | ✅ | ✅ |
| `paiements` | Payments | Payments | ✅ | ✅ |
| `achats_devis` | Purchases | Purchases | ✅ | ✅ |
| `livraisons` | Delivery | Delivery | ✅ | ✅ |
| `rh` | HR | HR | ✅ | ✅ |
| `comptabilite` | Accounting | Accounting | ✅ | ✅ |
| `documents` | Documents | Documents | ✅ | ✅ |
| `ai` | AI | AI | ✅ | ✅ |
| `abonnements` | Subscription | Subscription | ✅ | ✅ |
| `dashboard` | Dashboard | Dashboard | ✅ | ✅ |
| `public` | Catalog, OrderTracking, Home, Contact, About, CGV, Privacy, Terms | ❌ **Absent** | ❌ | ❌ |
| `tenants` | SuperAdmin (tenant mgmt) | SuperAdmin | ✅ | ✅ |
| `roles` | Roles | Roles | ❌ **Importée non routée** | ❌ |
| `permissions` | Permissions | Permissions | ❌ **Importée non routée** | ❌ |
| `users` | Users | Users | ❌ **Importée non routée** | ❌ |

**Conclusion :** Toutes les pages existantes sont couplées à des namespaces backend existants. Le seul namespace **non exploité** côté Desktop est `public` (pages marketing). Les 3 pages admin (`roles`, `permissions`, `users`) sont fonctionnellement prêtes — il manque seulement le routing.

---

## 9. Priorisation des actions (matrice RICE simplifiée)

| # | Action | Reach | Impact | Conf. | Effort | Priorité |
|---|---|---|---|---|---|---|
| 1 | AuthProvider wrapper | Tous utilisateurs Desktop | Critique (app cassée) | Élevée | 1 ligne | **URGENT** |
| 2 | Routes /roles, /permissions, /users | Admin | Élevé (3 pages bloquées) | Élevée | 3 routes | **Haut** |
| 3 | DesktopTopBar + DesktopLayout swap | Tous utilisateurs | Élevé (UX complète) | Élevée | 1 fichier | **Haut** |
| 4 | useKeyboardShortcuts activé | Tous utilisateurs | Élevé (accessibilité) | Élevée | 2 fichiers | **Haut** |
| 5 | Menu natif Electron | Tous utilisateurs | Moyen | Élevée | 30 lignes | **Haut** |
| 6 | Notifications système | Tous utilisateurs | Moyen | Élevée | 15 lignes | **Moyen** |
| 7 | Impression native | Factures/Fiches | Moyen | Élevée | 15 lignes | **Moyen** |
| 8 | DataTable + FilterPanel | Power users | Élevé | Moyenne | Multiple pages | **Moyen** |
| 9 | Pages publiques (Catalog, Home, etc.) | Public/Marketing | Moyen | Élevée | Nouveau | **Bas** |
| 10 | Auto-update | Tous | Moyen | Moyenne | Package externe | **Bas** |
| 11 | Drag & Drop | Uploads | Moyen | Moyenne | 20 lignes | **Bas** |
| 12 | SplitView / ResizablePanel | Power users | Faible | Moyenne | Pages selectionnées | **Bas** |
| 13 | VirtualList | Grandes listes | Moyen (perf) | Élevée | Pages spécifiques | **Bas** |

---

## 10. Annexe — Fichiers de référence

### Desktop (à modifier)
| Fichier | Ligne clé | Action |
|---|---|---|
| `desk/src/App.js` | 7, 111 | Importer + monter AuthProvider |
| `desk/src/App.js` | 151 | Ajouter routes /roles, /permissions, /users |
| `desk/src/index.js` | 4 | Garder HashRouter ✅ |
| `desk/src/components/layout/DesktopLayout.jsx` | — | Swap TopBar → DesktopTopBar |
| `desk/src/services/desktopApi.js` | 5-27 | Réimplanter (localStorage / backend) |
| `desk/electron/main.js` | 3, 50 | Ajouter Menu, Notifications, Print, Dialog |
| `desk/electron/preload.js` | 5 | Étendre exposeInMainWorld |
| `desk/src/hooks/useKeyboardShortcuts.js` | 6 | Appeler dans DesktopLayout |
| `desk/src/hooks/useSplitView.js` | 6 | Appeler dans SplitView/DataTable |

### Web (lecture seule — référence)
| Fichier | Usage |
|---|---|
| `web/frontend/src/App.js` | AuthProvider pattern, BrowserRouter, routing |
| `web/frontend/src/index.js` | Provider hierarchy (AuthProvider → CartProvider) |
| `web/frontend/src/components/landing/` | Catalog, Header, Footer, Hero, OrderTracking, Testimonials, TrustBar |
| `web/frontend/src/styles/landing.css` | Styles marketing |
| `web/frontend/src/services/api.js` | API patterns (publicCatalogueService, etc.) |
| `web/backend/app/api/v1/__init__.py` | Namespace registration (ligne 1-22) |
| `web/backend/app/api/v1/notifications.py` | **À créer** (n'existe pas) |

---

*Rapport généré par audit structuré — voir conversation pour détails de chaque fichier lu.*
