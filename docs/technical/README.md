# Technical Documentation

Architecture and implementation details for the ERP project.

## Architecture

### Backend (`web/backend/`)

- **Framework**: Flask 2.3.3 + Flask-RESTx 1.1.0
- **ORM**: SQLAlchemy 2.0.22
- **Authentication**: Flask-JWT-Extended 4.5.3
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **API Documentation**: Swagger at `/docs/`

### Frontend Web (`web/frontend/`)

- **Framework**: React 18.3.1
- **Routing**: React Router DOM 7.18.2
- **State Management**: React Context (Auth, Cart)
- **Forms**: React Hook Form + Yup validation
- **UI**: Framer Motion animations, React Toastify notifications

### Desktop (`desk/`)

- **Framework**: React 18.3.1 + Electron 38
- **Packaging**: electron-builder (Windows NSIS, macOS DMG, Linux AppImage)
- **Virtualization**: @tanstack/react-virtual 3.0.0

## Multi-Tenancy

### Database Design

- Shared database with shared schema
- `tenant_id` column on all business tables
- Foreign key to `tenants` table
- Automatic filtering via `BaseService` and `@tenant_required` decorator

### Tenant Resolution

- JWT claims contain `tenant_id` and `tenant_slug`
- Header-based resolution for desktop app (`X-Tenant-Slug`)
- `SUPER_ADMIN` bypasses tenant filtering

## RBAC (Role-Based Access Control)

### Built-in Roles

| Role | Description |
|------|-------------|
| `SUPER_ADMIN` | Full access, manages all tenants |
| `ADMIN` | Tenant admin, full operational access |
| `MANAGER` | Management access |
| `SALES` | Sales module access |
| `STOCK` | Inventory module access |
| `ACCOUNTANT` | Accounting module access |
| `USER` | Public interface only |

### Custom Roles

- `RoleModel` entity with custom permissions
- `Permission` entity with code and description
- Users can have `custom_role_id` for granular access

## Models

All models inherit from `BaseModel` which provides:
- `id` (primary key)
- `tenant_id` (foreign key)
- `created_at`, `updated_at` (timestamps)
- `is_active` (soft delete)
- `created_by`, `updated_by` (audit)

### Core Models (35+)

- **Tenant**: Company/organization
- **Utilisateur**: Users with roles and permissions
- **Produit**: Products with stock, pricing, categories
- **Client**: Customers with 7 types
- **Fournisseur**: Suppliers with 6 types
- **Vente**: Sales with status workflow
- **Facture**: Invoices with payment tracking
- **Paiement**: Payments with 5 modes
- **Stock/MouvementStock**: Inventory movements
- **Abonnement**: Subscriptions with plans

### Advanced Models

- **Livraison**: Deliveries, drivers, vehicles, routes, tracking
- **RH**: Employees, attendance, salaries, bonuses
- **Comptabilite**: Chart of accounts, journal entries, treasury
- **Documents**: Document templates and generated documents
- **Achats/Devis**: Purchase orders, receipts, quotes, credit notes

## Services

All services inherit from `BaseService` providing:
- CRUD operations with automatic tenant filtering
- Pagination, filtering, and search
- Soft delete support

### Core Services

- `auth_service`: Authentication logic
- `produit_service`: Product management
- `client_service`: Client management
- `vente_service`: Sales management
- `stock_service`: Inventory management
- `facturation_service`: Invoice management
- `paiement_service`: Payment management
- `dashboard_service`: Dashboard KPIs

### Advanced Services

- `livraison_service`: Delivery management
- `rh_service`: HR management
- `comptabilite_service`: Accounting management
- `document_service`: Document generation
- `achat_service`: Purchase management
- `devis_avoir_service`: Quotes and credit notes

## Security

- JWT authentication with access/refresh tokens
- Password hashing with bcrypt
- CORS configuration
- RBAC with role-based decorators
- Multi-tenant data isolation
- Encryption for sensitive data

## API Design

- RESTful endpoints with Flask-RESTx
- Swagger documentation auto-generated
- Namespace-based organization (22 namespaces)
- Standard HTTP methods (GET, POST, PUT, DELETE)
- JSON request/response format

## Frontend Architecture

- Component-based architecture
- Context API for global state
- Service layer for API communication
- Protected routes with role-based redirection
- Responsive design with mobile-first approach

## Desktop Architecture

- Electron wrapper around React app
- Shared code with web frontend
- Desktop-specific context for native features
- IPC communication for native operations
