# Frontend

React frontend application for the ERP project.

## Features

- React 18.3.1 SPA
- React Router DOM 7.18.2 for routing
- React Hook Form + Yup for form validation
- Axios for API communication
- Framer Motion for animations
- React Toastify for notifications
- Context API for state management (Auth, Cart)
- 35+ pages covering all ERP modules

## Project Structure

```
web/frontend/
├── src/
│   ├── App.js               # Main app with routing
│   ├── index.js             # Entry point
│   ├── index.css            # Global styles
│   ├── pages/               # 35+ page components
│   │   ├── Dashboard.jsx
│   │   ├── Products.jsx
│   │   ├── Clients.jsx
│   │   ├── Sales.jsx
│   │   ├── Inventory.jsx
│   │   ├── Suppliers.jsx
│   │   ├── Purchases.jsx
│   │   ├── Delivery.jsx
│   │   ├── HR.jsx
│   │   ├── Accounting.jsx
│   │   ├── Documents.jsx
│   │   ├── AI.jsx
│   │   ├── Subscription.jsx
│   │   ├── SuperAdmin.jsx
│   │   └── ...
│   ├── components/          # Reusable components
│   │   ├── auth/            # Login, Register, etc.
│   │   └── layout/          # MainLayout
│   ├── contexts/            # React contexts
│   │   ├── AuthContext.jsx  # Authentication state
│   │   └── CartContext.jsx  # Shopping cart state
│   ├── services/            # API service layer
│   │   └── api.js           # All API services (22 namespaces)
│   ├── hooks/               # Custom hooks
│   │   └── useAuth.js       # Auth hook
│   └── styles/              # CSS modules
├── public/                  # Static assets
└── package.json             # Dependencies and scripts
```

## Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm start
   ```

The app will be available at `http://localhost:3000`.

## API Configuration

The app connects to the backend at `http://127.0.0.1:5000` by default (configured via proxy in package.json).

Environment variables:
- `REACT_APP_API_URL` - Backend API URL (default: `/api/v1`)
- `REACT_APP_PUBLIC_API_URL` - Public API URL (default: `http://127.0.0.1:5000/public`)

## Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## Services

The `services/api.js` file provides service objects for all API namespaces:

- `authService` - Authentication
- `productService` - Products
- `clientService` - Clients
- `fournisseurService` - Suppliers
- `saleService` - Sales
- `factureService` - Invoices
- `paiementService` - Payments
- `stockService` - Inventory
- `dashboardService` - Dashboard stats
- `subscriptionService` - Subscriptions
- `aiService` - AI features
- `livreurService` - Drivers
- `vehiculeService` - Vehicles
- `itineraireService` - Routes
- `livraisonService` - Deliveries
- `employeService` - Employees
- `presenceService` - Attendance
- `salaireService` - Salaries
- `primeService` - Bonuses
- `compteService` - Chart of accounts
- `ecritureService` - Journal entries
- `tresorerieService` - Treasury
- `modeleDocumentService` - Document templates
- `documentService` - Documents
- `commandeAchatService` - Purchase orders
- `receptionService` - Receptions
- `devisService` - Quotes
- `bonLivraisonService` - Delivery notes
- `avoirService` - Credit notes
- `roleService` - Roles
- `permissionService` - Permissions
- `tenantService` - Tenants (Super Admin)
- `superAdminService` - Super Admin profile
- `publicCatalogueService` - Public catalog
