# Analyse comparative : Fonctionnalités Web vs Desktop
**Date : 18 août 2026**

---

## 1. Pages manquantes sur Desktop

| # | Page Web | Chemin Web | Statut Desktop | Impact |
|---|----------|-----------|----------------|--------|
| 1 | **Home** | `/` | ❌ Manquante | Page d'accueil publique avec catalogue, panier, notifications utilisateur |
| 2 | **Cart** | `/cart` | ❌ Manquante | Panier d'achat public (add/remove/update/clear) |
| 3 | **Catalogue** | `/catalogue` | ❌ Manquante | Catalogue public dédié (landing) |
| 4 | **Checkout** | `/checkout` | ❌ Manquante | Tunnel de commande anonyme avec coordonnées |
| 5 | **ProductDetail** | `/produits/:id` | ❌ Manquante | Fiche produit publique avec ajout au panier |
| 6 | **OrderTracking** | `/order-tracking/:ref` | ❌ Manquante | Suivi de commande par référence (QR + notifications) |
| 7 | **Suivi** | `/suivi` | ❌ Manquante | Wrapper landing du suivi de commande |
| 8 | **Contact** | `/contact` | ❌ Manquante | Formulaire de contact public |
| 9 | **UserOrders** | `/mes-commandes` | ❌ Manquante | Historique notifications/commandes utilisateur |
| 10 | **Documentation** | `/documentation` | ❌ Manquante | Page de documentation du site |

---

## 2. Composants manquants sur Desktop

| # | Composant | Chemin Web | Statut Desktop | Impact |
|---|-----------|-----------|----------------|--------|
| 1 | **Landing components** | `components/landing/` | ❌ Manquants | Hero, Footer, Header, Catalog, OrderTracking, Testimonials, TrustBar |
| 2 | **MainLayout** | `components/layout/MainLayout.jsx` | ❌ Manquant | Layout responsive web (DashboardRail + DesktopLayout conditionnel) |
| 3 | **DashboardRail** | `components/layout/DashboardRail.jsx` | ❌ Manquant | Sidebar rail responsive web |
| 4 | **MainLayout CSS** | `components/layout/MainLayout.css` | ❌ Manquante | Styles du layout web |
| 5 | **DashboardRail CSS** | `components/layout/DashboardRail.css` | ❌ Manquante | Styles du rail web |
| 6 | **Landing CSS** | `styles/landing.css` | ❌ Manquante | Styles des pages publiques/landing |
| 7 | **useMediaQuery hook** | `hooks/useMediaQuery.js` | ❌ Manquant | Hook de détection de taille d'écran |

---

## 3. Contextes et Services manquants

| # | Élément | Chemin Web | Statut Desktop | Impact |
|---|---------|-----------|----------------|--------|
| 1 | **CartProvider** | `contexts/CartContext.jsx` | ⚠️ Existe mais non utilisé | Contexte panier non wrappé dans App.js Desktop |
| 2 | **publicApi** | `services/api.js` | ❌ Manquant | Instance axios séparée pour API publique (sans token) |
| 3 | **publicCatalogueService** | `services/api.js` | ❌ Manquant | Services API publique (produits, commandes, tracking, notifications) |
| 4 | **dashboardService.getPublicStats()** | `services/api.js` | ❌ Manquant | Statistiques dashboard publiques |

---

## 4. Différences de routing

### Web (`web/frontend/src/App.js`)
- Route publique `/` → `Home` (page d'accueil avec catalogue)
- Routes publiques sans authentification : `/cart`, `/checkout`, `/catalogue`, `/produits/:id`, `/order-tracking/:ref`, `/suivi`, `/contact`, `/mes-commandes`, `/documentation`
- Wrapper `CartProvider` autour de toute l'app
- `MainLayout` qui bascule vers `DesktopLayout` sur grands écrans

### Desktop (`desk/src/App.js`)
- Route `/` → redirection vers `/login`
- **Aucune route publique** (tout passe par `ProtectedRoute`)
- Wrapper `DesktopProvider` uniquement
- `DesktopLayout` permanent

---

## 5. Services API : comparaison détaillée

### Services présents sur Web mais absents sur Desktop

| Service | Méthodes | Usage |
|---------|----------|-------|
| `publicApi` | Instance axios | API publique sans authentification |
| `publicCatalogueService` | `getProduits`, `getProduit`, `getTenant`, `createCommande`, `getCommandeTracking`, `getNotifications` | Pages publiques (catalogue, checkout, tracking) |
| `dashboardService.getPublicStats()` | `GET /dashboard/public` | Stats dashboard publiques |

### Services présents sur Desktop mais absents sur Web

| Service | Méthodes | Usage |
|---------|----------|-------|
| `roleService` | CRUD + permissions | Gestion rôles personnalisés |
| `permissionService` | CRUD | Gestion permissions granulaires |
| `userService` | CRUD | Gestion utilisateurs (Super Admin) |
| `notificationService` (desktopApi.js) | CRUD + read-all | Notifications desktop |
| `favoriteService` (desktopApi.js) | CRUD | Favoris desktop |
| `columnConfigService` (desktopApi.js) | GET/POST | Configuration colonnes tableaux |
| `filterPresetService` (desktopApi.js) | CRUD | Filtres sauvegardés |

---

## 6. Architecture Desktop existante vs cible

### ✅ Déjà présent sur Desktop
- Electron 38 configuré avec scripts de build
- `DesktopContext` (sidebar, favoris, split view, notifications, command palette)
- `CartContext` (existe mais non intégré)
- Layout desktop complet (sidebar, top bar, title bar, command palette)
- Composants desktop : DataTable, FilterPanel, FormGrid, FAB, VirtualList, ResizablePanel, SplitView
- Tous les modules opérationnels : Dashboard, Products, Clients, Sales, Invoices, Payments, Inventory, Suppliers, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, SuperAdmin, Roles, Permissions, Users
- Hooks : `useKeyboardShortcuts`, `useSplitView`
- Services API complets pour modules authentifiés

### ❌ Manquant sur Desktop
- Pages et logique publique (catalogue, commande, suivi)
- Services API publique
- Intégration du `CartProvider` dans le flux Desktop
- Pages de contenu (Documentation, Contact)

---

## 7. Plan d'action technique

### Phase 1 — Intégration du contexte panier (1-2 jours)
1. **Wrappper `CartProvider`** dans `desk/src/App.js` (comme sur web)
2. **Ajouter `publicCatalogueService`** dans `desk/src/services/api.js`
3. **Ajouter `publicApi`** (instance axios sans authentification par défaut)
4. **Ajouter `dashboardService.getPublicStats()`**

### Phase 2 — Pages publiques Desktop (3-5 jours)
1. **Créer `Home.jsx`** adapté pour Desktop :
   - Supprimer les éléments web-only (Hero, user cartouche web)
   - Conserver le catalogue public accessible
   - Intégrer dans le layout Desktop (hors `ProtectedRoute` ou route publique dédiée)

2. **Créer `Cart.jsx`** (logique identique au web, styles adaptés Desktop)

3. **Créer `Checkout.jsx`** (tunnel de commande public)

4. **Créer `ProductDetail.jsx`** (fiche produit publique)

5. **Créer `OrderTracking.jsx`** (suivi par référence)

6. **Créer `UserOrders.jsx`** (notifications/commandes utilisateur)

7. **Créer `Documentation.jsx`** (contenu statique)

8. **Créer `Contact.jsx`** (formulaire de contact)

### Phase 3 — Routing et Layout (1-2 jours)
1. **Modifier `desk/src/App.js`** :
   - Ajouter routes publiques AVANT `ProtectedRoute`
   - Route `/` → `Home` (au lieu de redirection login)
   - Routes publiques : `/cart`, `/checkout`, `/produits/:id`, `/order-tracking/:ref`, `/mes-commandes`, `/documentation`, `/contact`

2. **Créer un `PublicLayout`** pour les pages publiques Desktop :
   - Version simplifiée de `DesktopLayout`
   - Navigation minimale (brand, login/register)
   - Intégration avec `CartContext`

### Phase 4 — Styles et composants partagés (2-3 jours)
1. **Adapter `landing.css`** pour Desktop (supprimer animations excessives, adapter spacing)
2. **Créer composants landing Desktop** si nécessaire :
   - `ProductCard` pour affichage catalogue
   - `PublicHeader` pour navigation publique
3. **Vérifier cohérence CSS** entre pages publiques et layout Desktop

### Phase 5 — Tests et validation (1-2 jours)
1. **Tester flux public complet** : Home → ProductDetail → Cart → Checkout → OrderTracking
2. **Tester authentification** : login → dashboard → logout
3. **Tester notifications** : UserOrders avec tracking
4. **Vérifier Electron** : build et packaging

---

## 8. Points d'attention architecture

### Contraintes à respecter
1. **Ne pas modifier le web** : toutes les modifications se font dans `desk/`
2. **Partager le maximum de code** : pages et services identiques au web quand possible
3. **Respecter l'architecture Desktop existante** : `DesktopProvider`, `DesktopLayout`, hooks spécifiques
4. **Maintenir la séparation public/authentifié** : pages publiques accessibles sans login

### Risques identifiés
1. **Double authentification** : le `ProtectedRoute` Desktop redirige les `user` vers `/` — il faudra adapter pour laisser accéder aux pages publiques
2. **Styles landing vs Desktop** : le CSS landing est conçu pour le web, nécessite adaptation
3. **CartContext non utilisé** : existe dans Desktop mais jamais wrappé — risque de confusion
4. **API publique** : endpoints Flask existants (`/public/*`) mais non consommés par Desktop

---

## 9. Endpoints backend concernés

Tous les endpoints suivants existent déjà dans `web/backend/app/api/v1/public.py` :

| Endpoint | Méthode | Usage Desktop |
|----------|---------|---------------|
| `/public/produits` | GET | Catalogue public, Home |
| `/public/produits/<id>` | GET | ProductDetail |
| `/public/tenants/<id>` | GET | Détail vendeur |
| `/public/commandes` | POST | Checkout (création commande) |
| `/public/commandes/tracking/<ref>` | GET | OrderTracking, UserOrders |
| `/public/notifications` | GET | UserOrders, OrderTracking |

**Aucune modification backend requise.**

---

## 10. Résumé des livrables

### Court terme (1 semaine)
- [ ] Intégration `CartProvider` dans Desktop
- [ ] Services API publique dans `desk/src/services/api.js`
- [ ] 7 pages publiques manquantes (Home, Cart, Checkout, ProductDetail, OrderTracking, UserOrders, Documentation, Contact)
- [ ] Routing public dans `desk/src/App.js`
- [ ] Styles adaptés pour pages publiques Desktop

### Moyen terme (2-3 semaines)
- [ ] Unification layout public Desktop
- [ ] Tests complets flux public
- [ ] Build Electron fonctionnel avec pages publiques

### Long terme (suivi Plan_Desktop.md)
- [ ] Landing components adaptatifs
- [ ] Améliorations UX Desktop (SplitView, CommandPalette avancée, etc.)
