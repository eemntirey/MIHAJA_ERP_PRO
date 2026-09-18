# Carte de mise en production — MIHAJA ERP PRO

> Document de référence pour le passage en production du stack complet.
> Basé sur l'état réel du dépôt (branche `V0`, commit `a070229`).
> Conventions : tous les messages utilisateur/API sont en français, devise MGA.

---

## 0. Périmètre — les 8 composables à déployer

| # | Composant | Source | Livrable prod | Hôte/port |
|---|-----------|--------|---------------|-----------|
| 1 | **API Flask + Socket.IO** | `web/backend` | Image Docker | `:5000` (interne) |
| 2 | **PostgreSQL 16** | image `postgres:16-alpine` | Conteneur + volume | `:5432` (interne) |
| 3 | **Redis 7** | image `redis:7-alpine` | Conteneur + volume | `:6379` (interne) |
| 4 | **Web React (CRA)** | `web/frontend` | Build statique `build/` | via reverse proxy |
| 5 | **Super-admin (Vite)** | `super-admin` | Build statique `dist/` | via reverse proxy |
| 6 | **Desk Electron 38** | `desk` | Installateurs NSIS/DMG/AppImage | postes clients |
| 7 | **Mobile Expo** | `mobile` | Build EAS (APK/AAB/IPA) | stores / distribution |
| 8 | **Reverse proxy TLS** | à provisionner | nginx/Caddy + certificats | `:80/:443` publics |

Architecture cible :

```
Internet ──> Reverse proxy TLS (443)
             ├── erp.exemple.mg            → statique web/frontend/build
             │     ├── /api/*              → backend:5000
             │     └── /socket.io/*  (ws)  → backend:5000
             └── admin.exemple.mg          → statique super-admin/dist
Backend ──> PostgreSQL (réseau interne) ──> Redis (réseau interne)
Backend <── worker/cron (abonnements, backups, emails, rapports)
```

---

## 1. Bloquants identifiés dans le dépôt — à lever AVANT le jour J

Ces constats proviennent de l'audit du code ; chacun empêche ou dégrade sérieusement une mise en production directe.

### B1 — Aucun serveur WSGI de production (bloquant majeur)
- `web/requirements.txt` ne contient **ni gunicorn, ni eventlet, ni gevent**.
- `run.py` appelle `socketio.run(...)` avec `allow_unsafe_werkzeug=debug` → en prod (`debug=False`), Flask-SocketIO **refuse Werkzeug** (`RuntimeError: The Werkzeug web server is not designed to run in production`).
- **Action** : ajouter `gunicorn==23.0.0` + `eventlet` (ou `gevent`) aux requirements et changer la commande de démarrage :
  ```
  gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 --timeout 120 'app:create_app()'
  ```
  ⚠️ **1 worker obligatoire** tant que Socket.IO n'utilise pas `message_queue=redis` (sinon les événements temps réel ne traversent pas les workers). Pour scaler : `-w N` + configurer `SocketIO(..., message_queue=REDIS_URL)` et des sessions sticky au proxy.

### B2 — Dockerfile frontend = serveur de développement
- `web/frontend/Dockerfile` exécute `npm start` (dev-server CRA) : lent, mémoire, non sécurisé, sans TLS.
- **Action** : remplacer par un build multi-étapes `node:20-alpine` (npm run build) → `nginx:alpine` servant `build/`, ou abandonner ce conteneur et servir le statique directement depuis le reverse proxy (recommandé).

### B3 — Celery non câblé
- `docker-compose.yml` lance `celery -A app.tasks worker`, mais `app/tasks/__init__.py` n'expose **aucune instance `Celery(...)`**, aucun `shared_task`, aucun `beat_schedule`.
- Les jobs existants sont des fonctions pures : `run_subscription_reminders()`, `run_subscription_expiration_check()` (`app/tasks/subscription_scheduler.py`), `backup_database`, `send_email`, rapports.
- **Action (au choix)** :
  - *Option minimale viable* : cron système / conteneur `ofelia` appelant une commande Flask CLI dédiée ; Celery retiré du compose.
  - *Option complète* : créer `app/tasks/celery_app.py` (instance Celery + broker Redis), décorer en `shared_task`, ajouter un `beat_schedule` (rappels + expiration quotidienne, backup nocturne).

### B4 — TLS obligatoire (cookies JWT)
- En prod : `JWT_COOKIE_SECURE=True` (`app/__init__.py` L150) → le web ne pourra **pas** se connecter sans HTTPS.
- **Action** : reverse proxy avec certificat valide (Caddy automatique ou nginx + certbot) ; desk non impacté (Bearer).

### B5 — CORS vide par défaut en production
- En prod, `CORS_ORIGINS` n'a **aucun fallback** (L186) et les patterns dev (tunnels, LAN) sont ignorés.
- **Action** : lister explicitement `https://erp.exemple.mg` (+ domaine desk si servi).

### B6 — Paiements PAPI en sandbox
- `PAPI_ENVIRONMENT=sandbox` par défaut ; webhook `PAPI_CALLBACK_URL` doit être une **URL publique HTTPS**.
- **Action** : basculer `PAPI_ENVIRONMENT=production`, clé API réelle, secret webhook régénéré, URL callback `https://erp.exemple.mg/api/v1/papi/webhook`.

### B7 — E-mails désactivés
- `MAIL_ENABLED=false` par défaut (aucun envoi accidentel).
- **Action** : renseigner SMTP réel + `MAIL_ENABLED=true`, tester reset password.

### B8 — Uploads sur disque conteneur
- `uploads/` en volume bind : ok en mono-serveur, mais **à inclure dans la politique de sauvegarde** ; prévoir S3/objet si scaling.

### B9 — URL API figée au build pour desk & mobile
- Desk (Vite) et mobile (Expo) embarquent l'URL backend à la compilation.
- **Action** : définir la variable d'environnement API de prod (`VITE_*` / `EXPO_PUBLIC_*`) avant `npm run release` / `eas build`.

---

## 2. Variables d'environnement de production

Source de vérité : `web/backend/.env.example`. Générer chaque secret avec `openssl rand -hex 32`.

### Obligatoires
| Variable | Exemple / règle |
|---|---|
| `FLASK_ENV` | `production` (active tous les garde-fous) |
| `SECRET_KEY` | 64 hex — requis, sinon `ValueError` au démarrage |
| `JWT_SECRET_KEY` | 64 hex — requis, sinon `ValueError` |
| `ENCRYPTION_KEY` | 64 hex (chiffrement applicatif) |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@postgres:5432/erp_db` — **SQLite interdit en prod** (raise) |
| `REDIS_URL` | `redis://:PASS@redis:6379/0` (rate-limit fail-closed, temps réel) |
| `REDIS_PASSWORD` | 64 hex |
| `CORS_ORIGINS` | `https://erp.exemple.mg,https://admin.exemple.mg` |
| `FRONTEND_URL` / `APP_URL` | `https://erp.exemple.mg` (validé par regex en prod) |

### Paiement, mail, IA
| Variable | Règle |
|---|---|
| `PAPI_API_URL` | endpoint production PAPI |
| `PAPI_API_KEY` | clé réelle |
| `PAPI_ENVIRONMENT` | `production` |
| `PAPI_WEBHOOK_SECRET` | 64 hex, régénéré |
| `PAPI_CALLBACK_URL` | `https://erp.exemple.mg/api/v1/papi/webhook` |
| `MAIL_ENABLED` | `true` |
| `MAIL_HOST/PORT/USERNAME/PASSWORD/FROM` | SMTP réel (587, TLS) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | si modules IA utilisés |

### Recommandées
`SENTRY_DSN`, `MAX_CONTENT_LENGTH=16777216` (16 Mo, DoS pandas), `JWT_ACCESS_TOKEN_EXPIRES=3600`, `JWT_REFRESH_TOKEN_EXPIRES=7`, `PASSWORD_RESET_TTL_MINUTES=30`, `UPLOAD_FOLDER=/app/uploads`.

### Interdites en prod
`FLASK_DEBUG` (le process **refuse de démarrer**), `AUTO_MIGRATE=1` (préférer une étape de migration distincte), toute URL `localhost`/tunnel dans `CORS_ORIGINS`.

---

## 3. Infrastructure

### Dimensionnement initial (mono-serveur Docker)
- VPS 2–4 vCPU / 4–8 Go RAM / 40 Go SSD (Ubuntu 24.04 LTS), Docker + plugin compose.
- Firewall : **80/443 uniquement** ; Postgres/Redis **jamais exposés** (le compose actuel bind déjà `127.0.0.1`).
- DNS : `erp.exemple.mg` + `admin.exemple.mg` → IP serveur.

### Reverse proxy (Caddy recommandé — TLS automatique)
```
erp.exemple.mg {
  handle /api/*     { reverse_proxy backend:5000 }
  handle /socket.io/* { reverse_proxy backend:5000 }   # WebSocket : pas de buffering
  handle            { root * /srv/web ; try_files {path} /index.html ; file_server }
}
admin.exemple.mg { root * /srv/admin ; try_files {path} /index.html ; file_server }
```

---

## 4. Déroulé de mise en production (phases)

### Phase 0 — Corrections préalables (dans le dépôt)
1. Lever B1 (gunicorn+eventlet, commande prod), B2 (Dockerfile frontend), B3 (cron ou Celery).
2. Créer `web/docker-compose.prod.yml` (override) : images taguées, `restart: unless-stopped`, pas de mount `.`, commandes prod, healthchecks.

### Phase 1 — Provisionnement serveur
1. Installer Docker ; créer le réseau Docker ; déployer Caddy.
2. DNS + certificats (Caddy automatique).
3. Créer `deploy/.env.prod` (jamais committé — gitleaks actif en CI).

### Phase 2 — Base de données & amorçage
1. Démarrer Postgres + Redis seuls ; attendre le healthcheck.
2. Migrations Alembic :
   ```
   cd web/backend
   flask --app 'app:create_app' db upgrade
   ```
   Fallback si base vierge sans migration complète (ordre éprouvé de `setup_postgresql.ps1`) :
   `create_all` → `seed_roles` → `db stamp head` → `db upgrade`.
3. Super-admin (source de vérité unique) :
   ```
   python manage.py create-superadmin
   ```
   Les rôles/permissions système s'auto-seed de façon idempotente.
4. **Note multi-instances** : ne lancer la migration qu'**une fois** (jamais depuis N workers simultanés).

### Phase 3 — Build & déploiement services
1. `docker compose -f docker-compose.yml -f docker-compose.prod.yml build`
2. `docker compose ... up -d postgres redis` puis `up -d backend` (+ worker/cron selon B3).
3. Vérifier les logs : absence de `ValueError`, tables `tenants/utilisateurs/roles/permissions` présentes (sinon l'app logge le diagnostic `_SCHEMA_FIX_HELP`).

### Phase 4 — Frontends
1. **Web** : `npm run build` (web/frontend) → publier `build/` dans `/srv/web`. ⚠️Après toute modification de `config-overrides.js`, **vider le cache webpack** (risque "Invalid hook call").
2. **Super-admin** : `npm run build` → `/srv/admin`.
3. **Desk** : `npm run release` (vite build && electron-builder) → `dist/` NSIS/DMG/AppImage ; versionner les installateurs (GitHub Releases) ; signature de code optionnelle mais recommandée (SmartScreen).
4. **Mobile** : `eas build` avec l'URL API de production.

### Phase 5 — Observabilité
- Sentry (`SENTRY_DSN`), `docker logs` avec rotation, alertes sur `/health` et `/ready` (JSON, vérifient réellement la DB : 200 sain / 503 dégradé).
- Métriques : `/monitor` (racine backend, port 5000) est un **statut JSON** — le faire scraper par Prometheus **depuis le réseau Docker interne** (`http://backend:5000/monitor`), ou l'exposer au proxy avec restriction IP ; `prometheus-flask-exporter` est présent dans les requirements mais **non encore branché** sur l'app : à ajouter si l'on veut de vraies métriques Prometheus.

### Phase 6 — Sauvegardes & reprise
- `pg_dump` quotidien (cron) + retention 30 jours, hors serveur applicatif (S3/OSS).
- Sauvegarde `uploads/` (B8).
- `celery`/cron `backup_database` (app/tasks/backups.py) selon B3.
- **Tester une restauration complète** avant le go-live (sinon ce n'est pas une sauvegarde).

---

## 5. Smoke tests post-déploiement (dans l'ordre)

| # | Test | Attendu |
|---|------|---------|
| 1 | `GET /health` puis `GET /ready` | `200` (ready vérifie la DB) |
| 2 | `GET /docs` | **404/bloqué** (Swagger désactivé en prod) |
| 3 | Login web (`https://erp.exemple.mg`) | cookie `access_token_cookie` **Secure + HttpOnly + SameSite=Strict** |
| 4 | Login desk (Bearer) | 200 + rafraîchissement OK |
| 5 | Inscription tenant (domaine + essai) | 201, dates d'essai positionnées ; domaine dupliqué → **409** |
| 6 | Socket.IO | `upgrade: true` négocie `websocket` derrière le proxy |
| 7 | Rate limiting | 429 après dépassement (Redis fail-closed en prod) |
| 8 | Webhook PAPI | requête signée acceptée ; signature invalide rejetée |
| 9 | Reset password | e-mail reçu (SMTP réel) |
| 10 | Upload Excel 16,5 Mo | rejeté 413 (`MAX_CONTENT_LENGTH`) |

---

## 6. Checklist Go / No-Go

- [ ] B1–B9 levés et testés sur un environnement de staging
- [ ] `.env.prod` complet, secrets 64 hex, **jamais** commités (gitleaks vert)
- [ ] HTTPS valide sur les 2 domaines ; HSTS activé
- [ ] Migrations appliquées **une seule fois** ; `stamp head` cohérent
- [ ] Super-admin créé, mot de passe fort, MFA si disponible
- [ ] `FLASK_DEBUG` absent, `/docs` inaccessible, SQLite impossible
- [ ] `CORS_ORIGINS` = domaines de prod uniquement
- [ ] PAPI en `production` + webhook vérifié de bout en bout
- [ ] SMTP actif, reset password testé
- [ ] CI verte : `playwright.yml`, `secret-scan.yml`, `security-audit.yml` (pip-audit, npm audit, bandit)
- [ ] Tests backend `pytest` verts contre PostgreSQL (`erp_test`)
- [ ] Sauvegarde **+ restauration** testées ; retention définie
- [ ] Sentry + alertes `/health` configurés
- [ ] Installateurs desk + build mobile versionnés avec l'URL API de prod
- [ ] Procédure de rollback relue par une 2e personne

---

## 7. Rollback

| Scénario | Procédure |
|---|---|
| Régression applicative | `docker compose ... down backend` → redémarrer sur le **tag d'image N-1** (toujours tagguer : `erp-backend:YYYYMMDD-HHMM`) |
| Migration cassée | Ne jamais `db downgrade` à l'aveugle en prod : restaurer le `pg_dump` pré-migration |
| Fuite de secret | Suivre `ROTATION_SECRETS.md` (SECRET/JWT/ENCRYPTION/REDIS) |
| Frontend défectueux | Re-publier le build N-1 conservé dans `/srv/releases/` |
| Clients desk | Les installateurs sont versionnés : rediffuser la release N-1 |

---

## 8. Annexes — commandes de référence

```bash
# Secrets
openssl rand -hex 32

# Migrations (depuis web/backend)
flask --app 'app:create_app' db upgrade
flask --app 'app:create_app' db stamp head   # rattrapage schema existant

# Amorçage
python manage.py create-superadmin           # délègue à scripts/create_superadmin.py
python scripts/seed_roles.py                 # idempotent

# Backend prod (après B1)
gunicorn -k eventlet -w 1 -b 0.0.0.0:5000 --timeout 120 --access-logfile - 'app:create_app()'

# Builds clients
cd web/frontend && npm run build
cd super-admin  && npm run build
cd desk         && npm run release           # vite build && electron-builder

# Docker
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Sauvegarde / restauration
docker exec erp_postgres pg_dump -U erp_user erp_db | gzip > backup_$(date +%F).sql.gz
gunzip -c backup_YYYY-MM-DD.sql.gz | docker exec -i erp_postgres psql -U erp_user erp_db
```

---

*Document généré le 18/09/2026 — à mettre à jour après levée des bloquants B1–B3.*


