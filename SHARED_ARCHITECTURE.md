# Architecture partagée Web / Desktop

## Objectif

Éliminer la duplication entre `web/frontend/src/` et `desk/src/` et garantir la cohérence des données entre le navigateur et l'application Electron, y compris en mode hors-ligne.

## Structure des dossiers

```
├── shared/
│   ├── contexts/
│   │   └── AuthContext.jsx          # Contexte d'authentification unique
│   ├── hooks/
│   │   ├── useOnlineStatus.js       # Détection du statut en-ligne / hors-ligne
│   │   ├── useRealtimeSync.js       # Synchronisation temps-réel via Socket.IO
│   │   └── useAuth.js                # Hook useAuth partagé
│   ├── storage/
│   │   └── authStorage.js            # Accès unifié au localStorage d'authentification
│   ├── utils/
│   │   ├── localStore.js             # Wrapper localStorage tolérant aux pannes
│   │   └── syncEngine.js             # Moteur de synchronisation hors-ligne / en-ligne
│   └── websockets/
│       └── socketClient.js           # Client Socket.IO partagé
├── web/frontend/src/
│   └── contexts/AuthContext.jsx      # Réexport depuis shared/
├── desk/src/
│   ├── contexts/AuthContext.jsx      # Réexport depuis shared/
│   ├── services/desktopApi.js        # Utilise shared/syncEngine pour le mode hors-ligne
│   └── utils/localStore.js           # Réexport depuis shared/
└── web/backend/app/websockets/
    └── socket_events.py              # Serveur Socket.IO (optionnel)
```

## Composants partagés

### 1. `shared/storage/authStorage.js`

Abstraction du `localStorage` pour les données d'authentification. Utilisée par les deux intercepteurs Axios (`api.js`) et les deux `AuthContext`.

- Clés gérées: `access_token`, `refresh_token`, `user`, `tenant`, `subscription`
- Méthodes: `get*`, `set*`, `clear`

### 2. `shared/utils/syncEngine.js`

Moteur de synchronisation pour le mode hors-ligne.

**Fonctionnalités:**
- **File d'attente** (`syncQueue`): Les mutations (POST/PUT/DELETE) échouées sont enregistrées dans `localStorage` et rejouées automatiquement au retour de la connexion.
- **Hydratation**: Compare les timestamps locaux (`lastSyncedAt`) avec les données backend pour résoudre les conflits.
- **Stratégie de conflit**: Dernière écriture gagne (LWW) par défaut.

**Utilisation dans `desktopApi.js`:**
```javascript
import { syncEngine } from '../../shared/utils/syncEngine';

const syncMutation = async (method, url, payload) => {
  if (syncEngine.isOnline()) {
    try {
      return await api({ method, url, data: payload });
    } catch (error) {
      syncEngine.enqueue({ method, url, payload });
      throw error;
    }
  } else {
    syncEngine.enqueue({ method, url, payload });
    return Promise.reject(new Error('Hors-ligne: opération mise en file'));
  }
};
```

### 3. `shared/contexts/AuthContext.jsx`

Contexte React d'authentification unique, partagé entre web et desktop.

- Gestion de la session (login, register, logout)
- Rafraîchissement automatique du token via `authStorage`
- Vérification des permissions et rôles
- État `loading`, `isAuthenticated`, `user`, `tenant`, `subscription`

### 4. `shared/hooks/useOnlineStatus.js`

Hook React qui détecte le statut de connexion réseau.

```javascript
const isOnline = useOnlineStatus();
```

### 5. `shared/hooks/useRealtimeSync.js`

Hook React pour la synchronisation temps-réel via Socket.IO.

- Abonnements automatiques aux canaux de l'utilisateur connecté
- Événements personnalisés: `realtime:favorite:updated`, `realtime:column:updated`, `realtime:filter:updated`, `realtime:notification:new`

### 6. `shared/websockets/socketClient.js`

Client Socket.IO configuré avec:
- Reconnexion automatique (20 tentatives, délai exponentiel)
- Authentification par JWT lors de la connexion
- Canaux par tenant et par utilisateur

## Stratégie de migration

### Pour les utilisateurs existants

Un script de migration `scripts/migrate_localStorage_sync.js` est fourni. Il:
1. Détecte si la migration a déjà été exécutée (via `erp.migration.version`)
2. Déplace les favoris de `desk_favorites` vers le nouveau format
3. Nettoie les anciennes clés localStorage

**Exécution:**
```javascript
import { runMigration } from '../../scripts/migrate_localStorage_sync';
runMigration();
```

À appeler une seule fois au démarrage de l'application après déploiement.

## Installation des dépendances

### Web et Desktop

Aucune nouvelle dépendance pour le partage de code (les fichiers sont copiés via l'import relatif).

### Backend (optionnel, pour Socket.IO)

```bash
pip install flask-socketio python-socketio python-engineio
```

### Frontend (optionnel, pour Socket.IO)

```bash
npm install socket.io-client
```

## Activation du temps réel

Côté backend, activer avec:
```bash
export ENABLE_SOCKETIO=1
```

Côté frontend, le hook `useRealtimeSync` s'active automatiquement si `socket.io-client` est installé.

## Avantages de cette architecture

1. **Code mutualisé**: Un seul `AuthContext`, un seul `syncEngine`, un seul `localStore`
2. **Corrections uniques**: Un fix appliqué dans `shared/` bénéficie à web ET desktop
3. **Synchronisation hors-ligne**: La queue de sync garantit la cohérence des données
4. **Temps réel optionnel**: Socket.IO peut être activé/désactivé sans casser l'existant
5. **Migration progressive**: Les anciennes données sont préservées au premier démarrage

## Bundle size

L'ajout du code partagé (`shared/`) représente ~2-3 KB gzippés par client, bien dans la limite de 15%.
