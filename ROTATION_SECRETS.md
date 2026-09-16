# Rotation des secrets & purge d'historique — SEC-001 (16/09/2026)

## Historique git réécrit (fait)
Purge effectuée avec `git filter-repo` (2.47.0) sur un clone-miroir propre, puis
reportée sur le dépôt principal via `git update-ref` (working tree non modifiée).

### Fichiers supprimés de TOUT l'historique
- `.env`
- `.kilo/worktrees/scrawny-umbrella/.env`
- `erp.db`

### Secrets neutralisés dans TOUT l'historique (fichiers trackés inclus)
- `postgres:eemntirey` → `postgres:<REDACTED_DB_PASSWORD>`
- `redispassword` → `<REDACTED_REDIS_PASSWORD>`
- `dev-secret-key-change-in-production` → `<REDACTED_SECRET_KEY>`
- `jwt-secret-key-change-in-production` → `<REDACTED_JWT_SECRET_KEY>`

Concerne notamment `web/backend/scripts/*.py`, `web/backend/tests/*.py`,
`web/backend/migrations/alembic.ini`, `web/backend/README.md`, rapports `.md`.

### Vérifications
- `git log --branches -S <secret>` → 0 commit pour tous les secrets listés.
- `git log --branches --name-only` → aucun `.env` / `erp.db` / `.env.local` / `.env_sqlite`.
- `git fsck --strict` → propre (plus d'objets unreachable/dangling).
- `refs/cline/*` et `refs/agents/*` → ne contenaient pas les secrets réels.
- `storage_state.json` → non tracké, gitignoré (`.gitignore:584`), SEC-002 atténué.

### Sauvegarde de secours (AVANT purge)
`C:\Users\EEMNTI~1\AppData\Local\Temp\opencode\MIHAJA_backup_20260916_095539\repo-mirror.git`
Contient l'ancien historique AVEC les secrets → à supprimer une fois la rotation validée.

## Rotation des clés (fait dans les `.env` gitignorés)
Nouvelles valeurs générées (`secrets.token_hex(32)` / Fernet) appliquées à :
- `web/backend/.env`
- `web/backend/.env.local`
- `web/.env`

Clés rotatées : `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY` (clé Fernet valide),
`REDIS_PASSWORD`, `POSTGRES_PASSWORD`/`DATABASE_URL`, `TEST_DATABASE_URL`.

> Les nouveaux mots de passe DB/Redis ne sont PAS encore appliqués aux services locaux
> (choix utilisateur : fichiers `.env` seulement). À faire :
> - `ALTER USER postgres WITH PASSWORD '<nouveau>'` (ou `erp_user`),
> - `redis-cli CONFIG SET requirepass <nouveau>` / `requirepass` dans redis.conf.

## Restant à faire (côté distant / manuel)
1. **CONFIRMATION REQUISE** avant `git push --force` vers `origin` (historique réécrit).
2. Mettre à jour les remote-tracking refs après le push : `git fetch origin --prune --force`.
3. Côté GitHub : les anciens objets restent accessibles par SHA jusqu'au GC de GitHub.
   Pour une purge totale côté serveur, ouvrir un ticket GitHub Support.
4. Regénérer `PAPI_API_KEY` / `PAPI_WEBHOOK_SECRET` côté Papi (actuellement vides).
5. `storage_state.json` et `erp.db` présents sur disque local → ne jamais committer.
