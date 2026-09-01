# MIHAJA ERP - Super Admin

Console d'administration indépendante pour la gestion de la plateforme MIHAJA ERP.

## Architecture

Le Super Admin est une application frontend **complètement indépendante** du Web et du Desk.

```
web          → localhost:3000 (application web pour les tenants)
super-admin  → localhost:3001 (console d'administration plateforme)
backend      → localhost:5000 (API centrale)
desk         → application Electron indépendante
```

## Prérequis

- Node.js 16+
- npm ou yarn
- Backend MIHAJA ERP en cours d'exécution sur le port 5000

## Installation

```bash
cd super-admin
npm install
```

## Configuration

Créez un fichier `.env` à la racine du dossier `super-admin/` :

```env
REACT_APP_API_URL=http://localhost:5000/api/v1
PORT=3001
```

## Démarrage

```bash
npm start
```

L'application sera accessible sur `http://localhost:3001`.

## Build de production

```bash
npm run build
```

## Authentification

Le Super Admin utilise une authentification **séparée** avec :

- Token JWT stocké dans `super_admin_access_token`
- Refresh token dans `super_admin_refresh_token`
- Données utilisateur dans `super_admin_user`

Seuls les utilisateurs avec le rôle `SUPER_ADMIN` peuvent accéder à cette interface.

## Fonctionnalités

### Dashboard (`/`)
- Statistiques globales de la plateforme
- Graphiques d'évolution des inscriptions
- Répartition des tenants par statut
- Abonnements par plan
- Tenants récents

### Gestion des tenants (`/tenants`)
- Liste paginée de tous les tenants
- Recherche par nom, slug, email
- Filtrage par statut et plan
- Actions : activer, suspendre, réactiver

### Fiche détaillée (`/tenants/:id`)
- Informations générales du tenant
- Statistiques d'utilisation (utilisateurs, produits, clients, etc.)
- Abonnement actuel et historique
- Liste des administrateurs
- Activité récente

### Abonnements (`/subscriptions`)
- Liste de tous les abonnements
- Filtrage par statut et plan
- Informations du tenant associé

### Plans (`/plans`)
- Architecture des abonnements
- Nombre de tenants par plan

### Audit (`/audit`)
- Journal des actions sensibles
- Filtrage par type d'action
- Traçabilité complète (acteur, action, cible, date)

## API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/auth/login` | Authentification |
| POST | `/auth/refresh` | Rafraîchir le token |
| GET | `/super-admin/dashboard` | Statistiques dashboard |
| GET | `/super-admin/tenants` | Liste des tenants |
| GET | `/super-admin/tenants/:id` | Détail d'un tenant |
| POST | `/super-admin/tenants/:id/suspend` | Suspendre un tenant |
| POST | `/super-admin/tenants/:id/activate` | Activer un tenant |
| POST | `/super-admin/tenants/:id/reactivate` | Réactiver un tenant |
| POST | `/super-admin/tenants/:id/subscription/extend` | Prolonger abonnement |
| POST | `/super-admin/tenants/:id/subscription/change` | Modifier abonnement |
| GET | `/super-admin/subscriptions` | Liste des abonnements |
| GET | `/super-admin/plans` | Liste des plans |
| GET | `/super-admin/audit` | Logs d'audit |

## Sécurité

- Vérification du rôle `SUPER_ADMIN` côté backend
- JWT avec expiration
- Refresh token automatique
- Protection des routes côté frontend ET backend
- Audit logging des actions sensibles
- Isolation multi-tenant respectée

## Structure du projet

```
super-admin/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   └── ConfirmModal.jsx
│   │   └── layout/
│   │       ├── SuperAdminLayout.jsx
│   │       └── SuperAdminLayout.css
│   ├── contexts/
│   │   └── SuperAdminAuthContext.jsx
│   ├── pages/
│   │   ├── LoginPage.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Tenants.jsx
│   │   ├── TenantDetail.jsx
│   │   ├── Subscriptions.jsx
│   │   ├── Plans.jsx
│   │   ├── Audit.jsx
│   │   └── Profile.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.js
│   ├── index.js
│   └── index.css
├── public/
├── package.json
├── .env
├── .env.example
└── README.md
```

## Technologies

- React 18
- React Router DOM 7
- Axios
- Chart.js + react-chartjs-2
- React Toastify
- Framer Motion
