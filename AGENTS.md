# AGENTS.md — MIHAJA ERP PRO

Multi-tenant commercial ERP for Madagascar (currency MGA, UI/API messages in French).
Flask monolith backend + four separate frontends that share a root JS library.

## Layout & ports

- `web/backend` — Flask app (Flask-RESTx namespaces, SQLAlchemy, Celery, Socket.IO). Dev server on `:5000`.
- `web/frontend` — React 18, CRA via `react-app-rewired`, `:3000`. Proxies `/api` → `:5000`.
- `desk` — Electron 38 + Vite, `:3001`; `npm run electron:dev` runs Vite + Electron together.
- `super-admin` — independent Vite console, `:3002`.
- `mobile` — React Native + Expo.
- `shared/` — root JS library (auth, storage, sync/realtime, RBAC nav) imported by **both** web and desk. `shared/navConfig.js` + `shared/utils/navPermissions.js` are the single source of truth for navigation/RBAC — never fork them per app.

## Backend

- Entrypoint: `web/backend/run.py` (`create_app()` lives in `web/backend/app/__init__.py`). Swagger at `:5000/docs`, disabled when `FLASK_ENV=production`.
- Dependencies: `pip install -r web/requirements.txt` (note: `web/`, not `web/backend/`).
- `create_app()` raises `ValueError` if `SECRET_KEY` or `JWT_SECRET_KEY` is missing — a `.env` must exist.
- DB: dev uses SQLite (`DATABASE_URL=sqlite:///./erp.db`, see `.env_sqlite`); when `DATABASE_URL` is unset the default is local Postgres. `FLASK_ENV=production` rejects SQLite, debug mode, and `/docs`.
- Local Postgres (used by prod config and tests): Docker container `erp-pg` on port `55432`; provision it with `web/backend/setup_postgresql.ps1` (`create_all` → `seed_roles` → `db stamp head` → `db upgrade`).
- Migrations: Alembic in `web/backend/migrations`; drive with `flask --app 'app:create_app' db ...`.
- SUPER_ADMIN is created with `python manage.py create-superadmin`, which delegates to `scripts/create_superadmin.py` (single source of truth). System roles/permissions auto-seed when their tables are empty (idempotent).

## Multi-tenancy (critical)

- Nearly every model is tenant-scoped and **must** define a `tenant_id` column.
- `web/backend/app/security/tenant.py` registers a global SQLAlchemy `do_orm_execute` listener that appends `tenant_id = <current>` to every SELECT during a request. Bypass only with `query.execution_options(_skip_tenant_filter=True)`. SUPER_ADMIN has `tenant_id = NULL` and skips filtering.
- Reuse the decorators/helpers in `app/security/tenant.py` and `app/security/roles.py` instead of re-implementing tenant or RBAC checks.

## Tests

- `cd web/backend && pytest`. Requires a running **PostgreSQL** — the default URL is `postgresql+psycopg://postgres@localhost:55432/erp_test`, and the DB name is rewritten to `erp_test` from `TEST_DATABASE_URL`/`DATABASE_URL`.
- Isolation is per-test via PG SAVEPOINT; `db.drop_all` is monkeypatched to `reset_schema` in `tests/conftest.py` because the schema has FK cycles. Never hardcode DB credentials in tests (a past secret-scan redacted one and broke the suite).
- CI: `.github/workflows/playwright.yml` (root Playwright), `secret-scan.yml` (gitleaks), `security-audit.yml` (pip-audit, npm audit, bandit).

## Conventions

- All user-facing strings, API error messages, and most comments are in French; keep new ones French too.
- Web authenticates via HttpOnly cookies, Electron/desk via `Authorization: Bearer`; the backend accepts both (`JWT_TOKEN_LOCATION = ['cookies', 'headers']`).
- `web/frontend/config-overrides.js` aliases `@shared` → root `shared/` and pins a single `react`/`react-dom` copy. Editing it without clearing webpack's filesystem cache can leave a stale bundle (and cause "Invalid hook call").

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
