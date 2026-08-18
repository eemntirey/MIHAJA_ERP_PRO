# API Documentation

The ERP API is documented using Swagger/OpenAPI.

## Accessing API Documentation

Start the backend server and navigate to:
```
http://localhost:5000/docs/
```

## Authentication

All protected endpoints require a Bearer token:
```
Authorization: Bearer <access_token>
```

### Obtaining a Token

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "tech",
  "password": "your_password"
}
```

### Refreshing a Token

```bash
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

## Base URL

```
http://localhost:5000/api/v1
```

## Public Endpoints

```
GET  /public/produits
GET  /public/produits/{id}
GET  /public/tenants/{id}
POST /public/commandes
GET  /public/commandes/tracking/{ref}
GET  /public/notifications
```

## Core Endpoints

### Authentication
- `POST /auth/login` - Login
- `POST /auth/register` - Register
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Logout
- `GET /auth/me` - Current user

### Products
- `GET /produits` - List products
- `GET /produits/{id}` - Get product
- `POST /produits` - Create product
- `PUT /produits/{id}` - Update product
- `DELETE /produits/{id}` - Delete product

### Clients
- `GET /clients` - List clients
- `GET /clients/{id}` - Get client
- `POST /clients` - Create client
- `PUT /clients/{id}` - Update client
- `DELETE /clients/{id}` - Delete client

### Sales
- `GET /ventes` - List sales
- `GET /ventes/{id}` - Get sale
- `POST /ventes` - Create sale
- `PUT /ventes/{id}` - Update sale
- `DELETE /ventes/{id}` - Delete sale

### Inventory
- `GET /stocks` - List stock movements
- `POST /stocks/mouvements` - Create movement
- `GET /stocks/alerts` - Get stock alerts

### Invoices
- `GET /factures` - List invoices
- `GET /factures/{id}` - Get invoice
- `POST /factures` - Create invoice
- `PUT /factures/{id}` - Update invoice
- `DELETE /factures/{id}` - Delete invoice

### Payments
- `GET /paiements` - List payments
- `GET /paiements/{id}` - Get payment
- `POST /paiements` - Create payment
- `PUT /paiements/{id}` - Update payment
- `DELETE /paiements/{id}` - Delete payment

## Advanced Endpoints

### Delivery
- `GET /livreurs` - List drivers
- `GET /vehicules` - List vehicles
- `GET /itineraires` - List routes
- `GET /livraisons` - List deliveries
- `POST /livraisons/{id}/suivi` - Add tracking

### HR
- `GET /employes` - List employees
- `GET /presences` - List attendances
- `GET /salaires` - List salaries
- `GET /primes` - List bonuses

### Accounting
- `GET /comptes` - List accounts
- `GET /ecritures` - List journal entries
- `GET /tresorerie` - List treasury entries

### Documents
- `GET /modeles-documents` - List document templates
- `POST /documents/generer` - Generate document

### Purchases
- `GET /commandes-achat` - List purchase orders
- `GET /receptions` - List receptions
- `GET /devis` - List quotes
- `GET /bons-livraison` - List delivery notes
- `GET /avoirs` - List credit notes

## Admin Endpoints

### Tenants (Super Admin)
- `GET /tenants` - List tenants
- `GET /tenants/{id}` - Get tenant
- `POST /tenants` - Create tenant
- `PUT /tenants/{id}` - Update tenant
- `POST /tenants/{id}/suspend` - Suspend tenant

### Subscriptions
- `GET /abonnements` - List subscriptions
- `POST /abonnements/demander` - Request subscription
- `GET /abonnements/mon-abonnement` - My subscription
- `POST /abonnements/{id}/payer` - Pay subscription
- `POST /abonnements/{id}/renouveler` - Renew subscription

### Roles & Permissions
- `GET /roles` - List roles
- `GET /permissions` - List permissions
- `GET /users` - List users

## Dashboard Endpoints

- `GET /dashboard` - Global statistics
- `GET /dashboard/sales-stats` - Sales statistics
- `GET /dashboard/top-products` - Top products
- `GET /dashboard/top-clients` - Top clients
- `GET /dashboard/alerts` - Active alerts

## AI Endpoints

- `GET /ai/health` - AI service health
- `GET /ai/previsions` - Sales/stock forecasts
- `GET /ai/anomalies` - Anomaly detection
- `GET /ai/recommendations` - Recommendations
- `POST /ai/assistant` - AI assistant chat

## Response Formats

### Success Response
```json
{
  "data": { ... },
  "message": "Success"
}
```

### Error Response
```json
{
  "message": "Error description",
  "error": "Detailed error"
}
```

### Pagination
```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```
