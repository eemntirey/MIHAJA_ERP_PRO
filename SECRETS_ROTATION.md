# Rotation des secrets — P0-1 (15/09/2026)

## Actions immédiates réalisées
- `.env` racine supprimé (contenait `dev_secret_test`, `dev_jwt_secret_test`, `sqlite:///erp.db`).
- `web/backend/.env` supprimé (contenait `postgres:postgres`, `redispassword`, clés dev).
- `.env.example` mis à jour avec placeholders `<GENERATE_WITH_OPENSSL_RAND_HEX_32>` (sans valeurs réelles).
- `.gitignore` déjà couvre `.env`, `.env.*`, `*.db`, `.kilo/worktrees/*/.env`, `storage_state.json`, `login_result.json`.

## Restant (hors code — action manuelle / CI)
1. **Nettoyer l'historique git** (secrets dans commits passés) :
   - `git filter-repo --path web/backend/.env --path .kilo/worktrees/scrawny-umbrella/.env --path erp.db --invert-paths` (nécessite `git-filter-repo` installé)
   - Ou `BFG Repo-Cleaner`: `bfg --delete-files erp.db` + `--delete-files '*.env'` (attention aux `.env.example`).
2. **Rotation immédiate des secrets** (ne pas réutiliser `dev_secret_test` / `dev_jwt_secret_test` / `postgres`) :
   - `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY` : `openssl rand -hex 32`
   - `DATABASE_URL` : créer utilisateur DB dédié, changer mot de passe.
   - `REDIS_PASSWORD` : `openssl rand -hex 32`
   - `PAPI_API_KEY`, `PAPI_WEBHOOK_SECRET` : regénérer côté Papi.
3. **Ne pas commettre `.env`** : utiliser `docker-compose.yml` avec `env_file: .env` mais `.env` non versionné, ou secrets Docker (`docker secret`).
4. **CI** : ajouter `gitleaks` / `truffleHog` dans le pipeline pour bloquer tout commit avec `SECRET_KEY=` ou `PASSWORD=`.
