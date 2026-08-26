# Correction de la désynchronisation Web / Desktop (Electron)

## 1. Diagnostic retenu

| # | Problème | Cause racine | Correction |
|---|----------|--------------|------------|
| 1 | Stockage isolé web/desktop | deux `localStorage` non reliés + pas de backend de préférences | namespace `/desk/*` côté Flask + `syncEngine` |
| 2 | Code dupliqué | `desktopApi.js`, `AuthContext.jsx`, `api.js` recopiés | bibliothèque `/shared` importée par les 2 builds |
| 3 | Local-first cassé desktop | `desktopApi.js` écrit dans `localStorage` sans jamais pousser | `preferences.js` backend-first + `syncEngine` (queue hors-ligne) |
| 4 | Pas de temps réel | aucun WebSocket/SSE | `websockets/socketClient.js` + Flask-SocketIO (fallback polling) |
| 5 | Auth non unifiée | 2 `AuthContext` + clés de token différentes | `shared/contexts/AuthContext.jsx` unique + `tokenStore` rétro-compatible |

## 2. Architecture cible (arborescence)

```
MIHAJA_ERP_PRO/
├── shared/                         # BIBLIOTHÈQUE UNIQUE (web + desktop)
│   ├── storage/
│   │   ├── storageAdapter.js        # getString/setString/buildKey (web=localStorage, desktop=safeStorage)
│   │   ├── tokenStore.js            # jetons unifiés (rétro-compatible clés legacy)
│   │   └── authStorage.js
│   ├── utils/
│   │   ├── syncEngine.js            # FILE D'ATTENTE + MERGE (LWW)  ★ cœur
│   │   ├── migrateLocalStorage.js   # migration one-shot desktop existant
│   │   └── localStore.js
│   ├── services/
│   │   ├── apiClient.js             # axios + intercepteurs + refresh 401 (unique)
│   │   ├── api.js                   # tous les services REST (barrel)
│   │   ├── syncApi.js               # client endpoints /desk/*
│   │   └── preferences.js           # favoris/colonnes/filtres/notifs backend-first
│   ├── contexts/AuthContext.jsx     # AuthContext UNIQUE
│   ├── hooks/{useAuth,useOnlineStatus,useRealtimeSync}.js
│   ├── websockets/socketClient.js   # Socket.IO client (temps réel)
│   ├── realtime/socketClient.js
│   └── index.js
│
├── desk/                           # build Electron (react-app-rewired)
│   ├── shared  ──(junction)──► ../shared
│   ├── src/  (importe depuis '../../shared/...')
│   └── electron/{main,preload}.js  # préload expose secureStore (safeStorage)
│
├── web/frontend/                   # build web (react-app-rewired)
│   ├── shared  ──(junction)──► ../../shared
│   └── src/  (importe depuis '../../../shared/...')
│
└── web/backend/app/
    ├── api/v1/desk.py              # NOUVEAU blueprint /api/v1/desk  ★ backend
    ├── models/desk_state.py        # NOUVEAUX modèles (favoris, filtres, colonnes, events)
    ├── realtime/socket_server.py   # Flask-SocketIO (optionnel)
    └── run_socket.py               # point d'entrée temps-réel
```

### Câblage du build (CRA 5 + react-app-rewired)
Les deux apps importent `/shared` qui est **hors de `src`**. Pour que CRA accepte :
- `config-overrides.js` (desk & web/frontend) : `removeModuleScopePlugin()` + `addBabelInclude([sharedDir])` + alias `@shared`.
- Scripts `start/build/test` → `react-app-rewired`.
- Dépendances ajoutées : `react-app-rewired`, `customize-cra`, `socket.io-client`.
- Jonctions `desk/shared` et `web/frontend/shared` → `../shared` (créées via `mklink /J`).
- `jest.moduleNameMapper` `"^@shared/(.*)$"` pour les tests.

## 3. Logique de synchronisation (extrait critique)

### 3.1 File d'attente hors-ligne — `shared/utils/syncEngine.js`
- `syncEngine.enqueue(op)` persiste chaque mutation (`localStorage` clé `erp.sync.queue`) avec `createdAt`.
- `syncEngine.flush(fetchFn)` rejoue **en FIFO** ; backoff `RETRY_DELAYS=[1000,5000,30000]`, `MAX_RETRIES=3`, `getLastSyncedAt()` horodate la dernière synchro.
- `syncEngine.isOnline()` (navigator.onLine) court-circuite l'envoi si hors-ligne.

### 3.2 Merge des données (dernier écrit gagne + fusion manuelle)
Implémenté dans `syncEngine.js` (`mergeCollections` / `pickLatest`) :
- Indexation par `keyFn` (ex. `f.path` pour favoris, `p.id` pour filtres).
- Items présents des **deux** côtés → résolus par **LWW** sur `updatedAt`.
- Items d'un **seul** côté → conservés (fusion manuelle, pas de perte).
- Renvoie `{ merged, conflicts }` ; `preferences.hydrateAndSync()` pousse les gagnants locaux au backend (hydratation au démarrage).

### 3.3 `preferences.js` (remplace `desktopApi.js`)
- `favoriteService` / `columnConfigService` / `filterPresetService` : **backend-first**, cache local scoped (`buildKey`), et en cas d'échec réseau → `syncEngine.enqueue(...)` pour rejeu.
- `hydrateAndSync()` : (1) flush de la queue, (2) `GET /desk/sync/pull` et merge.

## 4. Backend Flask (non cassant pour mobile/tiers)
Nouveau blueprint monté sur `/api/v1/desk`, authentifié par le **même JWT Bearer** standard :
- `GET/POST/DELETE /desk/favorites`
- `GET/POST/DELETE /desk/filters/<module>`
- `GET/POST/DELETE /desk/columns/<module>`
- `POST /desk/sync/push` **et** `/desk/sync/mutations` (alias compatible desktopApi historique)
- `GET /desk/sync/pull?revision=` , `GET /desk/sync/status`
- `GET /desk/events?since=` (fallback polling temps-réel)
- Modèles `DeskFavorite`, `DeskFilterPreset`, `DeskColumnConfig`, `SyncEvent` (tenant + user scoped).
- Migration BDD : `python web/backend/scripts/create_desk_tables.py` (dev) ou `flask db migrate` + `flask db upgrade` (prod).
- Temps réel : `web/backend/run_socket.py` (`ENABLE_SOCKETIO=1`) ; désactivé proprement si `flask-socketio` absent → le client bascule sur le polling.

## 5. Auth unifiée
- `shared/contexts/AuthContext.jsx` unique ; `tokenStore` lit/écrit **aussi** les clés legacy (`access_token`, `user`...) → sessions existantes préservées.
- Desktop : tokens dans `window.electron.secureStore` (chiffrés via `safeStorage` Electron, voir `electron/preload.js`), avec repli `localStorage`.
- Même logique de refresh 401 dans `apiClient.js` (interceptor unique).

## 6. Stratégie de migration (zéro perte)
`shared/utils/migrateLocalStorage.js` (`migrateLegacyDesktopData()`), appelé **une fois** après la 1re connexion post-déploiement :
1. `desk_favorites` (legacy non-scoped) → `favoriteService.add` (push backend).
2. `erp.desk.columns.<module>` → `columnConfigService.save`.
3. `erp.desk.filters.<module>` → `filterPresetService.save`.
4. Pose le marqueur `erp.migrated` (idempotent).
Les données web (qui n'avaient pas de local-first) sont récupérées via `hydrateAndSync()` au login.

## 7. Plan d'action chiffré (étapes + effort)

| Étape | Action | Fichiers | Risque | Gain |
|------|--------|----------|--------|------|
| 1 | Bibliothèque `/shared` (déjà présente) reconciliée | syncEngine (mergeCollections ajouté), index | Faible | Unifiée |
| 2 | Backend `/desk/*` + modèles | `app/api/v1/desk.py`, `models/desk_state.py` | Moyen | Source de vérité |
| 3 | Socket.IO + polling fallback | `realtime/socket_server.py`, `run_socket.py`, `requirements.txt` | Faible | Temps réel |
| 4 | Câblage build (junctions + rewired) | `config-overrides.js` ×2, `package.json` ×2 | Moyen | Imports `/shared` OK |
| 5 | Auth unifiée + secureStore | `AuthContext.jsx`, `preload.js`, `tokenStore.js` | Faible | Sessions cohérentes |
| 6 | Migration one-shot | `migrateLocalStorage.js` | Faible | Aucune perte |
| 7 | Tests + bundle budget | `npm test` (desk/web), `npm run build` | Moyen | < +15% bundle |

**Vérifications** : `cd web/backend && flask db upgrade && ENABLE_SOCKETIO=1 python run_socket.py` ; `cd desk && npm i && npm run electron:dev` ; `cd web/frontend && npm i && npm start`. Le bundle web doit rester sous le budget (+15%) car le code mutualisé **remplace** des doublons au lieu de s'ajouter.

## 8. Contraintes respectées
- API REST mobile/tiers inchangée (nouveaux endpoints dans un blueprint séparé, même auth JWT).
- Fonctionne dev / staging / prod (Socket.IO optionnel, polling sinon).
- Taille bundle : mutualisation par remplacement (pas d'addition de code).
