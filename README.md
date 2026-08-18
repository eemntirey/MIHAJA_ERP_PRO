# ERP Commercial Multi-Tenant

Application web de gestion commerciale multi-tenant avec marketplace publique, abonnements par entreprise et rôle Super Admin privé.

## 🚀 Stack technique

- **Backend** : Flask + Flask-RESTx + Flask-JWT-Extended + SQLAlchemy (SQLite dev / PostgreSQL prod)
- **Frontend Web** : React 18 + Axios + React Router + React Hook Form + Framer Motion + React Toastify
- **Desktop (Electron)** : React 18 + Electron 38 + @tanstack/react-virtual
- **IA** : Python pur (numpy, pandas, régression linéaire, z-score)
- **Multi-tenancy** : isolation par `tenant_id` avec abonnements actifs/inactifs

## 📁 Structure du projet

```
ERP_PRO/
├── web/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/v1/          # Endpoints REST (produits, ventes, clients, stocks, abonnements, public, livraison, RH, comptabilité, documents, achats, rôles, permissions, users...)
│   │   │   ├── models/          # Modèles SQLAlchemy (35+ modèles)
│   │   │   ├── services/        # Logique métier (20+ services)
│   │   │   ├── security/        # Auth JWT, RBAC, gestion des rôles, isolation tenant
│   │   │   ├── ai/              # Prévisions, anomalies, recommandations, assistant
│   │   │   ├── utils/           # PDF, Excel, QR code, logs, validateurs
│   │   │   ├── tasks/           # Tâches Celery (backups, emails, rapports)
│   │   │   └── config/          # Configuration (settings, database)
│   │   ├── migrations/
│   │   ├── logs/
│   │   ├── requirements.txt
│   │   └── run.py
│   └── frontend/
│       ├── src/
│       │   ├── pages/           # Dashboard, Produits, Clients, Ventes, Stock, Abonnements, Livraison, RH, Comptabilité, Documents, Achats, SuperAdmin...
│       │   ├── components/      # Layout, auth, communs
│       │   ├── contexts/        # AuthContext, CartContext
│       │   ├── services/        # api.js (tous les services API)
│       │   └── styles/          # CSS global
│       └── package.json
├── desk/
│   ├── electron/                # Configuration Electron
│   ├── src/
│   │   ├── pages/               # Mêmes pages que web/frontend + layout desktop
│   │   ├── components/          # Layout, auth, communs
│   │   ├── contexts/            # AuthContext, DesktopContext
│   │   ├── services/            # api.js (tous les services API)
│   │   └── utils/               # Utilitaires desktop
│   └── package.json
├── docs/
│   ├── user/                    # Documentation utilisateur
│   ├── technical/               # Documentation technique
│   └── api/                     # Documentation API
├── Analyse_Fonctionnalite.md
├── Plan_Desktop.md
├── PROMPT_IA_AGENT_BUGS.md
├── resumer.md
└── README.md
```

## 🔐 Rôles et accès

| Rôle | Accès |
|------|-------|
| `SUPER_ADMIN` | Interface privée de gestion des tenants et abonnements, accès global |
| `ADMIN` / `MANAGER` | Modules opérationnels du tenant, gestion abonnement |
| `SALES` / `STOCK` / `ACCOUNTANT` | Modules opérationnels limités par permissions |
| `USER` | Interface publique, catalogue, commandes, suivi |

> L'interface Super Admin est privée : seul le propriétaire du site (compte `SUPER_ADMIN`) y a accès.

## 💳 Abonnements

- Chaque entreprise (tenant) doit posséder un abonnement actif pour publier des produits et accéder aux modules opérationnels.
- L'utilisateur simple peut consulter le catalogue public et passer commande sans abonnement.
- Les commandes en ligne sont validées uniquement après paiement complet.
- Chaque commande génère un QR code / code-barre pour le scan automatique.

## 🛒 E-commerce public

- Page d'accueil publique avec catalogue multi-entreprises.
- Produits filtrés selon l'abonnement actif du tenant vendeur.
- Tunnel de commande avec coordonnées, adresse de livraison et choix de quantité.
- Suivi de commande par référence avec notifications.
- QR code et code-barre pour scan automatique du paiement.

## 🖥️ Application Desktop (Electron)

- Application desktop native basée sur Electron 38.
- Partage du code React avec le frontend web.
- Layout desktop optimisé : sidebar 260px, TopBar, SplitView, CommandPalette (CMD+K).
- Virtualisation des listes longues avec @tanstack/react-virtual.
- Packaging Windows (NSIS), macOS (DMG), Linux (AppImage).

## 📊 Fonctionnalités principales

### Modules opérationnels
- **Produits** : CRUD, prix multiples, codes-barres, QR codes, stock, catégories, marques
- **Stocks** : mouvements, alertes, inventaire, emplacements, seuils critiques
- **Clients** : CRUD, historique, solde, 7 types de clients
- **Fournisseurs** : CRUD, commandes, factures, 6 types de fournisseurs
- **Ventes** : vente en gros/détail, factures, devis, bons de livraison, statuts
- **Factures & Paiements** : multi-modes, paiements partiels, créances
- **Dashboard** : chiffre d'affaires, bénéfices, top produits, alertes
- **Abonnements** : plans, demande, paiement, renouvellement, historique

### Modules avancés
- **Livraison** : livreurs, véhicules, itinéraires, livraisons, suivi temps réel
- **Ressources Humaines** : employés, présences, salaires, primes
- **Comptabilité** : plan comptable, écritures, trésorerie, import CSV
- **Documents** : modèles de documents, génération PDF/Devis/Contrats
- **Achats & Devis** : commandes fournisseurs, réceptions, devis, bons de livraison, avoirs
- **RBAC avancé** : rôles personnalisés, permissions granulaires, users management
- **IA** : prévisions, anomalies, recommandations, assistant conversationnel

### Fonctionnalités transversales
- Multi-tenancy complet avec isolation par `tenant_id`
- Authentification JWT (access + refresh tokens)
- RBAC avec rôles et permissions granulaires
- Marketplace publique multi-entreprises
- Auto-seeding de données de test au premier démarrage
- Import/Export Excel, génération PDF, QR codes, codes-barres

## 🔧 Installation

### Backend

```bash
cd web/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Le serveur démarre sur `http://localhost:5000`.
Documentation Swagger : `http://localhost:5000/docs`.

### Frontend Web

```bash
cd web/frontend
npm install
npm start
```

L'application frontend démarre sur `http://localhost:3000`.

### Desktop (Electron)

```bash
cd desk
npm install
npm run electron:dev
```

Packaging :

```bash
npm run dist
```

## 🧪 Tests

```bash
cd web/backend
pytest
```

## 📝 Documentation

- `Analyse_Fonctionnalite.md` : analyse détaillée des modules, bugs et corrections
- `Plan_Desktop.md` : plan d'évolution de l'expérience desktop
- `PROMPT_IA_AGENT_BUGS.md` : guide de debugging pour l'ERP
- `resumer.md` : résumé des travaux par session
- `http://localhost:5000/docs` : documentation API Swagger
- `docs/user/` : documentation utilisateur
- `docs/technical/` : documentation technique
- `docs/api/` : documentation API

## 📌 Notes

- Les mots de passe sont hashés avec bcrypt.
- Les tokens JWT expirent (configurable via `.env`).
- CORS configuré pour les origines frontend autorisées.
- Les données sensibles (clés, secrets) doivent être stockées dans `.env` et jamais commitées.
- Le backend supporte SQLite (dev) et PostgreSQL (prod).
- Le frontend web et desktop partagent la même API backend.
