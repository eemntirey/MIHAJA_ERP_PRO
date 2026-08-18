# Analyse des Fonctionnalités du Projet ERP
**Dernière mise à jour : 17 août 2026**

> Ce document reflète l'état réel du projet après intégration du multi-tenant, des abonnements, du Super Admin privé, de la marketplace publique et des modules avancés (Livraison, RH, Comptabilité, Documents, Achats/Devis).

---

## 1. ARCHITECTURE GÉNÉRALE

- **Backend** : Flask + Flask-RESTx + Flask-JWT-Extended + SQLAlchemy (SQLite dev / PostgreSQL prod)
- **Frontend Web** : React 18 + Axios + React Router + React Hook Form + Framer Motion + React Toastify
- **Desktop (Electron)** : React 18 + Electron 38 + @tanstack/react-virtual
- **IA** : Python pur (numpy, pandas, régression linéaire, z-score anomalies)
- **Multi-tenancy** : base partagée avec isolation par `tenant_id` + abonnement actif requis pour les tenants entreprises

### Structure du projet

```
ERP_PRO/
├── web/backend/          # API Flask (22 namespaces, 35+ modèles, 20+ services)
├── web/frontend/         # SPA React (35+ pages)
├── desk/                 # Application Electron desktop (30+ pages)
├── docs/                 # Documentation
│   ├── user/
│   ├── technical/
│   └── api/
└── [fichiers markdown de documentation]
```

---

## 2. AUTHENTIFICATION & SÉCURITÉ

### ✅ Ce qui fonctionne
- Login JWT avec access + refresh tokens
- Claims enrichis : `username`, `email`, `role`, `tenant_id`
- RBAC avec rôles : `SUPER_ADMIN`, `ADMIN`, `MANAGER`, `SALES`, `STOCK`, `ACCOUNTANT`, `USER`
- Isolation tenant via `tenant_required`
- `SUPER_ADMIN` bypass le filtrage tenant
- Hashage bcrypt des mots de passe
- Intercepteur axios avec refresh automatique
- Rôles personnalisés avec permissions granulaires (modèle `RoleModel` + `Permission`)
- Système de permissions vérifiées dans les modèles (`has_permission`, `get_permissions`)

### ⚠️ Points d'attention
- Le rôle `SUPER_ADMIN` est privé : seul le propriétaire du site doit y avoir accès.
- Les utilisateurs simples (`USER`) n'ont pas accès aux modules opérationnels ; ils sont redirigés vers la page publique.
- Les permissions granulaires sont définies mais leur vérification dans les endpoints API peut être renforcée.

---

## 3. MULTI-TENANT & ABONNEMENTS

### ✅ Ce qui fonctionne
- Modèle `Tenant` avec statut, plan, limites et abonnement
- Modèle `Abonnement` lié au tenant avec dates de début/fin, statut, montant, méthode de paiement
- Modèle `Paiement` traçant les transactions (abonnement / commande)
- Vérification de l'abonnement actif dans `tenant_required` pour protéger l'accès aux modules
- Endpoints de gestion des abonnements :
  - `POST /api/v1/abonnements/demander`
  - `GET /api/v1/abonnements/mon-abonnement`
  - `GET /api/v1/abonnements/mon-historique`
  - `POST /api/v1/abonnements/<id>/payer`
  - `POST /api/v1/abonnements/<id>/renouveler`
  - `GET /api/v1/abonnements/` (super admin)
  - `GET /api/v1/abonnements/historique/<tenant_id>` (super admin)
- Auto-seeding : création automatique de données de test au premier démarrage si aucun utilisateur n'existe

### 📌 Règles métier
- Un tenant sans abonnement actif ne peut pas publier de produits ni accéder aux modules opérationnels.
- Les produits publics ne sont retournés que pour les tenants avec abonnement actif.
- Le Super Admin voit l'historique des abonnements de chaque entreprise.
- Les limites de plan (`max_produits`, `max_clients`, `max_utilisateurs`) sont définies mais leur vérification automatique peut être renforcée.

---

## 4. MARKETPLACE PUBLIQUE

### ✅ Ce qui fonctionne
- Page d'accueil publique avec catalogue multi-entreprises
- Affichage du nom du tenant vendeur sur chaque produit
- Tunnel de commande anonyme avec coordonnées et adresse de livraison
- Validation de commande après paiement complet
- Suivi de commande par référence
- Notifications de commande
- Génération de QR code / code-barre pour scan automatique du paiement

### 📌 Règles métier
- Les commandes passées par des utilisateurs simples remontent dans l'historique du tenant entreprise.
- Une commande en ligne est valide si le paiement est complet et que la quantité demandée est disponible.

---

## 5. INTERFACE SUPER ADMIN

### ✅ Ce qui fonctionne
- Accès restreint au rôle `SUPER_ADMIN`
- Gestion des tenants (création, modification, suspension)
- Gestion des abonnements (vue globale, filtres par statut)
- Historique des abonnements par entreprise
- Modification du profil Super Admin (`GET/PUT /api/v1/auth/super-admin/me`)
- Gestion des rôles personnalisés et permissions
- Gestion des utilisateurs (CRUD)
- Interface sobre et privée, non exposée aux autres rôles

---

## 6. INTERFACE ENTREPRISE

### ✅ Ce qui fonctionne
- Accès aux modules opérationnels uniquement si abonnement actif
- Page de gestion d'abonnement avec plans (Gratuit, Starter, Pro, Enterprise)
- Demande, paiement (simulation) et renouvellement d'abonnement
- Publication de produits sur la marketplace publique
- Réception des commandes dans l'historique des ventes

---

## 7. MODULES OPÉRATIONNELS

### ✅ Modules core
- **Produits** : CRUD, prix multiples, codes-barres, QR codes, stock, catégories, marques, tags, statuts
- **Stocks** : mouvements, alertes, inventaire, emplacements, seuils critiques
- **Clients** : CRUD, historique, solde, 7 types de clients, adresses multiples
- **Fournisseurs** : CRUD, commandes, factures, 6 types de fournisseurs
- **Ventes** : vente en gros/détail, factures, devis, bons de livraison, statuts (devis → en_attente → payée → annulée)
- **Factures & Paiements** : multi-modes, paiements partiels, créances
- **Dashboard** : chiffre d'affaires, bénéfices, top produits, alertes

### ✅ Modules avancés
- **Livraison** : livreurs, véhicules, itinéraires, livraisons, suivi temps réel
- **Ressources Humaines** : employés, présences, salaires, primes
- **Comptabilité** : plan comptable, écritures, trésorerie, import CSV
- **Documents** : modèles de documents, génération PDF/Devis/Contrats
- **Achats & Devis** : commandes fournisseurs, réceptions, devis, bons de livraison, avoirs
- **RBAC avancé** : rôles personnalisés, permissions granulaires, users management

### ⚠️ Points d'attention connus
- Certains endpoints ou champs frontend/backend peuvent encore présenter des incohérences mineures.
- Les limites de plan (`max_produits`, `max_clients`, `max_utilisateurs`) sont définies mais leur vérification automatique peut être renforcée.
- Le module IA est entièrement en mode placeholder.

---

## 8. FRONTEND WEB — ÉTAT DES LIEUX

### ✅ Ce qui fonctionne
- Routing avec `ProtectedRoute` et redirection par rôle
- `AuthContext` avec login, logout, subscription status, redirection post-login
- `CartContext` pour le panier d'achat public
- Pages publiques : Catalogue, Checkout, OrderTracking avec styles à bordures captivantes
- Pages opérationnelles : Dashboard, Products, Clients, Sales, Inventory, Suppliers, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, Invoices, Payments
- Super Admin : gestion tenants + abonnements + rôles + permissions + users
- Subscription : plans, demande, paiement, renouvellement
- QR code de commande généré via API publique
- Services API complets pour tous les modules (22 namespaces)

### ⚠️ Points d'attention
- `ForgotPassword`/`ResetPassword` : endpoints backend à implémenter
- Certains modules avancés (Livraison, RH, Comptabilité, Documents) sont présents dans le frontend mais la logique métier backend est basique
- Le module Documents (génération PDF) est partiellement implémenté
- Certaines pages utilisent des données simulées au lieu des APIs réelles

---

## 9. APPLICATION DESKTOP (ELECTRON) — ÉTAT DES LIEUX

### ✅ Ce qui fonctionne
- Structure Electron complète avec configuration
- Partage du code React avec le frontend web
- `DesktopContext` pour les fonctionnalités spécifiques desktop
- Layout desktop avec DesktopLayout, protection des routes
- Toutes les pages opérationnelles présentes (Products, Clients, Sales, Inventory, Suppliers, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, SuperAdmin, Roles, Permissions, Users)
- Services API identiques au web
- Scripts de packaging (Windows NSIS, macOS DMG, Linux AppImage)

### ⚠️ Points d'attention
- `Plan_Desktop.md` décrit des fonctionnalités à implémenter (SplitView, ResizablePanel, CommandPalette, virtualization)
- Le layout desktop est basique, les améliorations décrites dans `Plan_Desktop.md` sont à implémenter
- Les fonctionnalités natives (impression, notifications système, drag & drop) sont à implémenter
- La virtualisation des tableaux est installée mais pas encore utilisée

---

## 10. SÉCURITÉ

- Authentification JWT sécurisée (access + refresh)
- RBAC par rôle avec permissions granulaires
- Isolation multi-tenant stricte
- `SUPER_ADMIN` hors filtrage tenant
- Accès à l'interface Super Admin restreint par vérification de rôle
- Rôles personnalisés avec permissions granulaires (modèle RoleModel + Permission)
- Hashage bcrypt des mots de passe
- CORS configuré pour les origines frontend autorisées

---

## 11. ROADMAP COURT TERME

1. Fiabiliser la synchronisation des champs frontend ↔ backend sur tous les modules
2. Ajouter la vérification des limites de plan dans les services métier
3. Implémenter les endpoints de réinitialisation de mot de passe
4. Finaliser le module Documents (PDF, Devis, Contrats)
5. Ajouter le module Livraison complet (chauffeurs, véhicules, itinéraires, suivi)
6. Développer les modules RH (employés, présences, salaires, primes)
7. Développer le module Comptabilité (plan comptable, écritures, trésorerie)
8. Implémenter les modules IA (prévisions, anomalies, recommandations, assistant)
9. Implémenter les tâches planifiées (backups, emails, rapports)
10. Finaliser l'application Desktop selon le `Plan_Desktop.md`

---

## 12. DÉMARRAGE RAPIDE

### Backend

```bash
cd web/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Frontend Web

```bash
cd web/frontend
npm install
npm start
```

### Desktop (Electron)

```bash
cd desk
npm install
npm run electron:dev
```

### Tests

```bash
cd web/backend
pytest
```

- Backend : `http://localhost:5000`
- Frontend Web : `http://localhost:3000`
- Desktop : `http://localhost:3001` (avec Electron)
- Swagger : `http://localhost:5000/docs`

---

## 13. MODULES & ENDPOINTS API

### API Core
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/register` - Inscription
- `POST /api/v1/auth/refresh` - Renouvellement token
- `POST /api/v1/auth/logout` - Déconnexion
- `GET /api/v1/auth/me` - Utilisateur connecté
- `GET /api/v1/dashboard` - Statistiques dashboard

### Modules opérationnels
- `GET|POST /api/v1/produits` - Produits
- `GET|POST /api/v1/clients` - Clients
- `GET|POST /api/v1/fournisseurs` - Fournisseurs
- `GET|POST /api/v1/ventes` - Ventes
- `GET|POST /api/v1/factures` - Factures
- `GET|POST /api/v1/paiements` - Paiements
- `GET|POST /api/v1/stocks` - Stocks et mouvements

### Modules avancés
- `GET|POST /api/v1/livreurs` - Livreurs
- `GET|POST /api/v1/vehicules` - Véhicules
- `GET|POST /api/v1/itineraires` - Itinéraires
- `GET|POST /api/v1/livraisons` - Livraisons
- `GET|POST /api/v1/employes` - Employés (RH)
- `GET|POST /api/v1/presences` - Présences (RH)
- `GET|POST /api/v1/salaires` - Salaires (RH)
- `GET|POST /api/v1/primes` - Primes (RH)
- `GET|POST /api/v1/comptes` - Plan comptable
- `GET|POST /api/v1/ecritures` - Écritures comptables
- `GET|POST /api/v1/tresorerie` - Trésorerie
- `GET|POST /api/v1/modeles-documents` - Modèles de documents
- `GET|POST /api/v1/documents` - Documents générés
- `GET|POST /api/v1/commandes-achat` - Commandes d'achat
- `GET|POST /api/v1/receptions` - Réceptions
- `GET|POST /api/v1/devis` - Devis
- `GET|POST /api/v1/bons-livraison` - Bons de livraison
- `GET|POST /api/v1/avoirs` - Avoirs

### Administration
- `GET|POST /api/v1/tenants` - Tenants (Super Admin)
- `GET|POST /api/v1/abonnements` - Abonnements
- `GET|POST /api/v1/roles` - Rôles personnalisés
- `GET|POST /api/v1/permissions` - Permissions
- `GET|POST /api/v1/users` - Utilisateurs

### IA & Public
- `GET /api/v1/ai/health` - Santé du service IA
- `GET /api/v1/ai/previsions` - Prévisions
- `GET /api/v1/ai/anomalies` - Détection anomalies
- `GET /api/v1/ai/recommendations` - Recommandations
- `POST /api/v1/ai/assistant` - Assistant conversationnel
- `GET /public/produits` - Catalogue public
- `POST /public/commandes` - Commandes publiques
- `GET /public/commandes/tracking/<ref>` - Suivi commande
