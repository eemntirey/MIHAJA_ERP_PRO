# Backend

Backend Python Flask application for the ERP project.

## Features

- Flask 2.3.3 + Flask-RESTx for REST API
- SQLAlchemy 2.0.22 ORM
- Flask-JWT-Extended for authentication
- Flask-Migrate for database migrations
- Flask-CORS for cross-origin requests
- Multi-tenancy with automatic data isolation
- 35+ SQLAlchemy models
- 20+ business services
- 22 API namespaces with Swagger documentation
- Auto-seeding test data on first run

## Project Structure

```
web/backend/
├── app/
│   ├── __init__             # Flask app factory
│   ├── api/v1/              # 22 API namespaces
│   ├── models/              # 35+ SQLAlchemy models
│   ├── services/            # 20+ business services
│   ├── security/            # Auth, RBAC, tenant isolation
│   ├── ai/                  # AI modules (placeholders)
│   ├── utils/               # PDF, Excel, QR, logging
│   ├── tasks/               # Celery tasks (placeholders)
│   └── config/              # Settings, database config
├── migrations/              # Database migrations
├── logs/                    # Application logs
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
└── requirements.txt         # Python dependencies
```

## Installation

1. Create virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate virtual environment:
   ```bash
   # Windows
   .\venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables in `.env` (copy from `.env.example`):
   ```
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret
   DATABASE_URL=postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db
   CORS_ORIGINS=http://localhost:3000
   ```

5. Run database migrations:
   ```bash
   flask db upgrade
   ```

6. Start the application:
   ```bash
   flask run
   ```

The server will start at `http://localhost:5000`.

## API Documentation

Access Swagger documentation at:
```
http://localhost:5000/docs/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-key` |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `DATABASE_URL` | Database connection string | `postgresql+psycopg://erp_user:erp_password@localhost:5432/erp_db` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `JWT_ACCESS_TOKEN_EXPIRES` | Access token expiry (seconds) | `3600` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `UPLOAD_FOLDER` | File upload directory | `uploads` |

## Scripts

- `scripts/init_db` - Initialize database
- `scripts/seed_database` - Seed test data
- `scripts/migrate_tenant` - Migrate to multi-tenant
- `scripts/train_ai` - Train AI models

## Testing

```bash
pytest
```

## Logs

Application logs are stored in the `logs/` directory.
