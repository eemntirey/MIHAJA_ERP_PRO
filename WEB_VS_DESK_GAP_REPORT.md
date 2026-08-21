# Web vs Desk Functional Gap Report
## Objective: Identify web features missing in desk

---

## 1. APP STRUCTURE & ROUTING

### Web (`web/frontend/src/App.js`)
- Wrapped in `BrowserRouter`, `AuthProvider`, `NotificationProvider`, `CartProvider`
- Global `planLimitModal` state with `plan-limit-reached` event listener
- `ProtectedRoute` checks `isAuthenticated`, subscription status, and role-based redirects
- Routes for public pages: `/`, `/login`, `/register`, `/register/simple`, `/register/company`, `/forgot-password`, `/reset-password/:token`
- Storefront routes: `/checkout`, `/order-tracking/:ref`, `/cart`, `/produits/:id`, `/catalogue`, `/suivi`, `/contact`, `/mes-commandes`
- `ToastContainer` with fixed `theme="light"`

### Desk (`desk/src/App.js`)
- Wrapped in `AuthProvider`, `DesktopProvider`, `CartProvider` (NO `NotificationProvider`)
- Uses `React.lazy` + `Suspense` for all pages (`AuthSuspense`, `PageSuspense`)
- `ProtectedRoute` has `STOREFRONT_PREFIXES` allowing `user` role access to `/cart`, `/checkout`, `/order-tracking`, `/mes-commandes`
- Additional `RequireRole` component for `SUPER_ADMIN`/`ADMIN` protected routes (`/roles`, `/permissions`, `/users`)
- Public pages wrapped in `LandingLayout` with `darkMode` prop
- Auth pages receive `darkMode`/`onToggleDarkMode` props
- `ToastContainer` theme syncs with `darkMode`

**Gaps where web has features missing in desk:**
- Web has `NotificationProvider` at app level; desk uses `DesktopContext` for notifications instead
- Web has global `planLimitModal` with event-driven architecture; desk does not
- Desk has `React.lazy` code-splitting; web does not
- Desk has `RequireRole` route guard; web does not
- Desk auth pages receive dark mode props; web auth pages do not

---

## 2. AUTH CONTEXT

### Web (`web/frontend/src/contexts/AuthContext.jsx`)
- Extensive console.log debugging in `login` (token, user data)
- `fetchSubscriptionStatus` called after login/register
- `getRedirectPath` handles role-based redirects
- `hasPermission` and `hasRole` (case-insensitive)

### Desk (`desk/src/contexts/AuthContext.jsx`)
- Cleaner code without debug console.logs
- Same core functionality: `login`, `register`, `logout`, `fetchSubscriptionStatus`, `hasPermission`, `hasRole`, `getRedirectPath`

**Gaps:** None significant — both are functionally equivalent.

---

## 3. API SERVICES

### Web (`web/frontend/src/services/api.js`)
- `publicApi` — separate axios instance for public endpoints
- `publicCatalogueService` — `getProduits`, `getProduit`, `getTenant`, `createCommande`, `getCommandeTracking`, `getNotifications`
- `notificationService` — `getAll`, `create`, `markAsRead`, `markAllAsRead`, `delete`
- `dashboardService.getPublicStats()` — extra endpoint not in desk

### Desk (`desk/src/services/api.js`)
- No `publicApi` or `publicCatalogueService`
- No `notificationService` in api.js (moved to `desktopApi.js`)
- No `dashboardService.getPublicStats()`

**Gaps where web has features missing in desk:**
- `publicCatalogueService` — public catalogue, order creation, tracking, notifications (used by Catalogue, Suivi, Contact, ProductDetail, Checkout, OrderTracking, UserOrders)
- `dashboardService.getPublicStats()` — public dashboard stats endpoint

---

## 4. LAYOUT COMPONENTS

### Web
- `MainLayout.jsx` — responsive layout switching between `DashboardRail` (mobile) and `DesktopLayout` (desktop >=1280px)
- `DashboardRail.jsx` — sidebar navigation with groups, badges, notifications dropdown, mobile nav overlay, mobile profile menu, name editing
- `DarkModeToggle.jsx` — standalone dark mode button
- `ChatInput.jsx` — bottom chat bar for AI assistant

### Desk
- `DesktopLayout.jsx` — main desktop layout with split view, FAB, command palette, title bar, keyboard shortcuts
- `DesktopSidebar.jsx` — collapsible sidebar with favorites (localStorage + API), profile dropdown, theme toggle
- `DesktopTopBar.jsx` — top bar with breadcrumbs, notification dropdown, indicators, search, theme toggle
- `TopBar.jsx` — alternative top bar with context actions, split view toggle, notification dropdown
- `Breadcrumbs.jsx` — dynamic breadcrumb navigation
- `ChatInput.jsx` — chat input for AI
- `CommandPalette.jsx` — CMD+K palette with fuzzy search, quick actions
- `DarkModeToggle.jsx` / `ThemeToggle.jsx` — theme toggles
- `LandingLayout.jsx` — public layout with cart badge, nav links
- `NotificationDropdown.jsx` — full notification dropdown with API sync, mark read/delete
- `ResizablePanel.jsx` / `SplitView.jsx` — split view panels
- `TitleBar.jsx` — Electron title bar

**Gaps where web has features missing in desk:**
- Web `MainLayout` has inline user name editing (`isEditingName`, `nameForm`, `handleSaveName` using `authService.updateMe`) — **desk does NOT have this feature in the layout**
- Web `DashboardRail` has a full mobile navigation overlay with labeled module groups — desk `DesktopSidebar` collapses to a narrow rail but lacks the full-screen mobile overlay
- Web `DashboardRail` notification dropdown uses fixed positioning with smart boundary detection — desk `NotificationDropdown` uses relative positioning
- Web `DashboardRail` has mobile profile menu with dark mode and logout — desk has profile dropdown in sidebar but structured differently

**Gaps where desk has features missing in web:**
- Desk has `CommandPalette` (CMD+K fuzzy search) — web dispatches keyboard event but has no palette component
- Desk has `SplitView` / `ResizablePanel` for master-detail views
- Desk has `FAB` (Floating Action Button)
- Desk has `TitleBar` for Electron window controls
- Desk has `TopBar` with context-aware actions per module
- Desk has favorites system in sidebar (persisted to API)
- Desk has `useFormDraft` hook for auto-saving form drafts
- Desk has `DataTable` component with bulk actions, sorting, filtering
- Desk has `FilterPanel` component with advanced field filters
- Desk has `FormGrid` / `FormField` components

---

## 5. PAGE-BY-PAGE COMPARISON

### 5.1 Dashboard
- **Both:** Nearly identical. Revenue hero, KPI strip, revenue chart, top products, activity timeline, priorities, subscription widget, export CSV, assistant IA link.
- **Web only:** Inline name editing in DashboardRail
- **Gaps:** None significant

### 5.2 Products
- **Web:** Simple HTML table, modal form, search + category filter, stats cards, stock status badges
- **Desk:** `DataTable` with bulk actions (Export CSV, bulk delete), `FilterPanel` with advanced numeric/text filters, `FormDraft` auto-save, `FormGrid` layout, computed columns (marge%, valeur_stock), selectable rows
- **Gaps:** Web lacks bulk actions, advanced filters, form drafts, computed columns

### 5.3 Clients
- **Web:** Uses `ClientModal` component, stats (total, entreprises, particuliers, panier moyen), phone formatting, type badges
- **Desk:** Inline modal with MORE fields: `code`, `prenom`, `adresse_facturation`, `ville_facturation`, `code_postal_facturation`, `siret`, `numero_tva`; conditional SIRET/TVA for non-particuliers
- **Gaps:** Web lacks `code`, `prenom`, `adresse_facturation`, `ville_facturation`, `code_postal_facturation`, `siret`, `numero_tva` fields

### 5.4 Sales
- **Web:** `react-hook-form` + `yup` validation, `SaleModal` component, view/edit modals, tabs (ventes, devis, bons-livraison, avoirs)
- **Desk:** `DataTable` with bulk actions (Export CSV, bulk delete, bulk convert devis→ventes), `FilterPanel` per tab, `FormDraft` auto-save for new and edit forms, `FormGrid` layout, edit sale modal with draft support
- **Gaps:** Web lacks bulk actions, advanced filters per tab, form drafts, edit modal with draft

### 5.5 Invoices
- **Both:** Very similar. Create invoice, detail modal, payment modal, status filter.
- **Gaps:** None significant

### 5.6 Payments
- **Web:** Has `provider` field (Papi), `statut` field (en_attente/confirme/echec/rembourse), `operateur_mobile`, `numero_telephone` (conditional for mobile money), payment status badges, `getByFacture` endpoint
- **Desk:** Simpler — likely missing `provider`, `statut`, `operateur_mobile`, `numero_telephone`
- **Gaps:** Desk lacks `provider`, `statut`, `operateur_mobile`, `numero_telephone` fields; missing payment status badges

### 5.7 Inventory
- **Web:** Stock stats cards (total products, critical stock, total stock value, total units), low stock alert banner, view toggle (inventory/mouvements), search + "filter low stock" checkbox, stock movement modal with product selector
- **Desk:** Simpler table view
- **Gaps:** Desk lacks stock stats cards, low stock alert banner, view toggle, stock movement modal

### 5.8 Suppliers
- **Web:** `chiffre_affaires` column, products count per supplier (`getSupplierProductsCount`), fetches products for counting
- **Desk:** Basic table
- **Gaps:** Desk lacks `chiffre_affaires` display, products count per supplier

### 5.9 Purchases
- **Both:** Similar — commandes + receptions tabs, forms, tables
- **Gaps:** None significant

### 5.10 Delivery
- **Web:** Comprehensive 5-tab system (livreurs, vehicules, itineraires, livraisons, suivis), `StatusBadge` component, forms for all entities, view suivis with timeline, `avancer` statut button, lat/lng tracking in suivis
- **Desk:** Likely simpler
- **Gaps:** Desk lacks comprehensive 5-tab delivery management, suivis timeline, avancer statut, lat/lng tracking

### 5.11 HR
- **Web:** 4 tabs (employes, presences, salaires, primes), stats (total, actifs, masse salariale, total primes, presences mois), search, export CSV for presences and salaries, generate salaries (mois/annee), mark as paid
- **Desk:** Likely simpler
- **Gaps:** Desk lacks export CSV, generate salaries, mark as paid, stats summary

### 5.12 Accounting
- **Web:** 4 tabs (comptes, ecritures, tresorerie, journal), import CSV/Excel for all tabs, export CSV, validate/cancel ecritures, fetch solde, journal with solde courant and compte resume
- **Desk:** Likely simpler
- **Gaps:** Desk lacks import CSV/Excel, export CSV, validate/cancel, journal tab, solde

### 5.13 Documents
- **Web:** 2 tabs (modeles, documents), PDF preview (iframe), download, print, document generation with JSON data, modeles management
- **Desk:** Likely simpler
- **Gaps:** Desk lacks PDF preview, download, print, document generation with JSON

### 5.14 AI
- **Web:** Multi-turn conversation with context, welcome screen with 6 suggestion cards, follow-up prompts after responses, copy to clipboard, markdown rendering, sources extraction (internal + web URLs), typing indicator, clear conversation
- **Desk:** Likely simpler chat
- **Gaps:** Desk lacks multi-turn context, suggestions, follow-up prompts, copy, markdown, sources, typing indicator

### 5.15 Subscription
- **Web:** Plan selection (4 plans with colors), request subscription (`demander`), Papi payment integration (open window, message listener, success callback), offline payment modal, payment history table
- **Desk:** Likely simpler
- **Gaps:** Desk lacks Papi payment integration, offline payment modal, payment history

### 5.16 SuperAdmin
- **Web:** 3 tabs (tenants, subscriptions, historique), subscription status filter, tenant search
- **Desk:** Similar structure
- **Gaps:** None significant

### 5.17 SuperAdminProfile
- **Both:** Similar profile editing form
- **Gaps:** None

### 5.18 Users
- **Web:** `mobile` field, `custom_role_id`, search + role filter, `totalCommandes` display
- **Desk:** Likely simpler
- **Gaps:** Desk lacks `mobile`, `custom_role_id`, role filter

### 5.19 Roles
- **Both:** Similar — create/edit/delete roles, permission checkboxes
- **Gaps:** None

### 5.20 Permissions
- **Both:** Similar — create/edit/delete permissions, search + module filter
- **Gaps:** None

### 5.21 Cart
- **Web:** Quantity update, remove item, clear cart, total price calculation, checkout navigation
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.22 Checkout
- **Web:** QR code generation, order confirmation with QR, public catalogue service
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.23 OrderTracking
- **Web:** QR code, barcode text, notifications list, refresh notifications
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.24 UserOrders
- **Web:** Track by reference, notifications list with status badges
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.25 Catalogue
- **Web:** Uses `Catalog` component from `components/landing/Catalog`
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.26 Suivi
- **Web:** Uses `OrderTracking` component from `components/landing/OrderTracking`
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.27 Contact
- **Web:** Contact form with name, email, message
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.28 Documentation
- **Web:** Static documentation page
- **Desk:** Likely similar
- **Gaps:** None significant

### 5.29 ProductDetail
- **Web:** Product image, category, price, stock, description, marque, reference, add to cart with quantity selector, buy button for users
- **Desk:** Likely similar
- **Gaps:** None significant

---

## 6. SUMMARY OF CRITICAL GAPS (Web features missing in Desk)

### High Priority
1. **publicCatalogueService** — public endpoints for catalogue, orders, tracking, notifications (affects Catalogue, Suivi, Contact, ProductDetail, Checkout, OrderTracking, UserOrders)
2. **Payments page** — missing `provider` (Papi), `statut`, `operateur_mobile`, `numero_telephone` fields
3. **Inventory page** — missing stock stats cards, low stock alert banner, view toggle, stock movement modal
4. **HR page** — missing export CSV, generate salaries, mark as paid
5. **Accounting page** — missing import CSV/Excel, export CSV, journal tab, validate/cancel ecritures
6. **Documents page** — missing PDF preview, download, print
7. **AI page** — missing multi-turn conversation, suggestions, follow-up prompts, copy, markdown, sources
8. **Subscription page** — missing Papi payment integration, offline payment modal, payment history
9. **Delivery page** — missing comprehensive 5-tab management, suivis timeline, avancer statut
10. **Clients page** — missing `code`, `prenom`, `adresse_facturation`, `ville_facturation`, `code_postal_facturation`, `siret`, `numero_tva` fields
11. **Suppliers page** — missing `chiffre_affaires`, products count per supplier
12. **Users page** — missing `mobile`, `custom_role_id`, role filter

### Medium Priority
13. **Layout name editing** — Web `MainLayout`/`DashboardRail` has inline name editing; desk does not
14. **Mobile nav overlay** — Web `DashboardRail` has full-screen mobile nav; desk lacks this
15. **Notification context** — Web uses `NotificationContext`; desk uses `DesktopContext`
16. **Dashboard** — Web has name editing in rail; desk does not

### Low Priority / Infrastructure
17. **Plan limit modal** — Web has global plan limit modal; desk does not
18. **React.lazy** — Desk has code-splitting; web does not
19. **RequireRole** — Desk has role-based route guard; web does not
20. **FormDraft / DataTable / FilterPanel / FormGrid** — Desk has reusable desktop components; web uses simpler HTML tables and modals

---

## 7. FILES READ

### Web Pages (29)
Dashboard, Products, Clients, Sales, Invoices, Payments, Inventory, Suppliers, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, SuperAdmin, SuperAdminProfile, Users, Roles, Permissions, Cart, Checkout, OrderTracking, UserOrders, Catalogue, Suivi, Contact, Documentation, ProductDetail

### Desk Pages (29 read)
Dashboard, Products, Clients, Sales, Invoices, Payments, Inventory, Suppliers, Purchases, Delivery, HR, Accounting, Documents, AI, Subscription, SuperAdmin, SuperAdminProfile, Users, Roles, Permissions, Cart, Checkout, OrderTracking, UserOrders, Catalogue, Suivi, Contact, Documentation, ProductDetail

### Layout / Core Files
- Web: MainLayout.jsx, DashboardRail.jsx, App.js, AuthContext.jsx, api.js
- Desk: DesktopLayout.jsx, DesktopSidebar.jsx, DesktopTopBar.jsx, TopBar.jsx, Breadcrumbs.jsx, ChatInput.jsx, CommandPalette.jsx, DarkModeToggle.jsx, LandingLayout.jsx, NotificationDropdown.jsx, ResizablePanel.jsx, SplitView.jsx, ThemeToggle.jsx, TitleBar.jsx, App.js, AuthContext.jsx, api.js
