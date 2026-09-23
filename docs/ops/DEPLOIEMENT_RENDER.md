# Déploiement staging sur Render (offre gratuite)

> **Périmètre : staging/démo uniquement.** L'offre gratuite Render dort
> après inactivité (première requête lente), la RAM est limitée (512 Mo) et
> la base gratuite est à durée limitée : jamais de données clients réelles
> sans sauvegardes. Pour la production réelle, voir la carte
> `docs/technical/CARTE_MISE_EN_PRODUCTION.md` (VPS : Hetzner ≈ 4,51 €/mois,
> ou Oracle Always Free si vous acceptez la carte bancaire + le risque de
> récupération des instances inactives).
>
> **Pourquoi pas de SSH :** Render est du PaaS, on déploie via GitHub, pas
> en SSH. Le `render.yaml` à la racine décrit toute l'infra (backend Flask
> + frontend statique + Postgres 16).

## 0. Prérequis (5 min, à faire par vous)

1. **Compte Render gratuit** : https://dashboard.render.com → Sign Up with GitHub.
2. **Code sur GitHub** : poussez ce dépôt (branche `V0`) sur GitHub.
   Le Blueprint pointera dessus.
3. **Accès DNS `sekoliko.com`** : pouvoir ajouter 2 enregistrements CNAME.

## 1. Créer les services via Blueprint

1. Render → **New → Blueprint** → connectez le dépôt → branche `V0`.
2. Render détecte `render.yaml` et propose 4 ressources :
   `mihaja-erp-backend` (Docker), `mihaja-erp-frontend` (statique),
   `mihaja-erp-super-admin` (statique), `mihaja-erp-db` (Postgres).
   **Apply**.
3. Le premier build dure 5 à 10 min (image Python + `npm ci`).

## 2. Corriger `DATABASE_URL` (obligatoire)

Render fournit `postgres://…`, mais SQLAlchemy + psycopg3 exige le schéma
`postgresql+psycopg://…`, sinon le backend crash au démarrage.

1. Backend → **Environment** → `DATABASE_URL` :
   remplacez le préfixe `postgres://` par `postgresql+psycopg://`
   (le reste de l'URL est inchangé). **Save** (redéploie).

## 3. Poser `ENCRYPTION_KEY` (obligatoire)

`render.yaml` la déclare `sync: false` exprès : une valeur générée au
hasard par Render serait **invalide** (il faut une clé Fernet).

1. Backend → **Environment** → `ENCRYPTION_KEY`, valeur staging :
   `aNBUmUZqYSGvHChpsUWkvUhCSw31cW7A4c2qXuPGRxs=`
2. **Save**. (Clé de staging uniquement — jamais en production réelle.)

`SECRET_KEY` / `JWT_SECRET_KEY` sont déjà générées automatiquement.

## 4. Vérifier migrations + créer le SUPER_ADMIN

**Free tier** : `preDeployCommand` n'est pas supporté → les migrations
Alembic se lancent **à la main** via Shell après chaque déploiement :

1. Backend → **Shell** :
   ```sh
   flask --app "app:create_app" db upgrade
   ```
   Contrôle ensuite : Logs → `Running upgrade` sans erreur, puis
   `GET /health 200`.
2. Toujours dans le Shell, créer le SUPER_ADMIN :
   ```sh
   $env:SUPERADMIN_PASSWORD = 'UnMotDePasseSolide123!'
   python scripts/create_superadmin.py
   ```
   (Sans cette étape, pas d'accès super-admin.)

## 5. Rewrites `/api` + `/socket.io` (obligatoire pour le web)

Les cookies JWT sont `SameSite=Strict` : le navigateur doit voir **une
seule origine**. Le frontend statique doit donc relayer l'API :

1. `mihaja-erp-frontend` → **Redirects/Rewrites → Add Rule → Rewrite** :
   - Source `/api/*` → Destination
     `https://mihaja-erp-backend.onrender.com/api/:splat`
   - Source `/socket.io/*` → Destination
     `https://mihaja-erp-backend.onrender.com/socket.io/:splat`
2. Test : `https://mihaja-erp-frontend.onrender.com/api/v1/plans`
   doit répondre (pas de 404 Render).
3. `mihaja-erp-super-admin` → **Redirects/Rewrites → Add Rule → Rewrite**
   ( mêmes règles que le frontend ) :
   - Source `/api/*` → Destination
     `https://mihaja-erp-backend.onrender.com/api/:splat`
   - Source `/socket.io/*` → Destination
     `https://mihaja-erp-backend.onrender.com/socket.io/:splat`

## 6. Domaines `sekoliko.com` + DNS

1. Backend → **Settings → Custom Domain** → `api.sekoliko.com`.
   Frontend → **Custom Domain** → `erp.sekoliko.com`.
2. Chez votre registrar DNS :
   | Hôte | Type  | Cible |
   |------|-------|-------|
   | `api` | CNAME | `mihaja-erp-backend.onrender.com` |
   | `erp` | CNAME | `mihaja-erp-frontend.onrender.com` |
3. Attendez la propagation (5 min à 24 h) : Render émet le TLS
   automatiquement. Contrôle : `https://api.sekoliko.com/health` → 200.
4. Une fois les domaines actifs, mettez à jour dans le backend
   (`Environment`) : `CORS_ORIGINS` et `FRONTEND_URL` contiennent déjà
   `https://erp.sekoliko.com` et `https://api.sekoliko.com` — rien à
   changer sauf si vous avez choisi d'autres noms.

## 7. Rebrancher mobile + desk sur le staging

- **Mobile (Expo)** : reconstruisez avec
  `EXPO_PUBLIC_API_URL=https://api.sekoliko.com/api/v1`
  (les apps mobiles utilisent `Authorization: Bearer`, pas de cookies :
  l'appel direct à `api.sekoliko.com` fonctionne).
- **Desk (Electron, mode en ligne)** : réplication vers
  `https://api.sekoliko.com` — variable `REPLICATION_URL` ou champ
  `replicationUrl` de `%APPDATA%/…/local-backend.json`.

## 8. Sauvegardes (staging = base jetable)

Base gratuite = pas de garantie de conservation. Dump hebdo depuis
n'importe quel poste avec `psql` :

```sh
pg_dump "postgresql+psycopg://erp_user:<mot-de-passe>@<hote-externe>:5432/erp_db" -Fc -f erp-staging.dump
```

(Hôte externe + mot de passe : page **Info** de `mihaja-erp-db`.)

## 9. Limites connues du staging gratuit

- **Sleep** : après inactivité, ~30 à 60 s de réveil sur la 1ʳᵉ requête.
- **Pas de Celery** (worker/beat non déployés) : e-mails, relances et
  tâches planifiées inactifs — normal en staging (`MAIL_ENABLED=false`
  par défaut).
- **512 Mo RAM** : 1 worker gunicorn, usage démo uniquement.

## 10. Alternative base pérenne gratuite : Aiven

Si Render supprime la base gratuite : créez un Postgres gratuit sur
https://aiven.io/free-postgresql-database (sans carte, 1 Go, persistant),
puis remplacez `DATABASE_URL` du backend par l'URL Aiven (en
`postgresql+psycopg://…`). Aucun changement de code.
