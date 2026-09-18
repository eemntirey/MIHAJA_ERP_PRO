# web/frontend/Dockerfile
# Build de production du frontend CRA (B2) — remplace l'ancien `npm start`
# (serveur de développement react-scripts, inutilisable en production).
#
# IMPORTANT — contexte de build = RACINE du monorepo :
# le build CRA importe la bibliothèque partagée `shared/` via l'alias
# `@shared` -> path.resolve(__dirname, '../../shared') (config-overrides.js)
# ET via des chemins relatifs `../../../../shared/...` (src/services/api.js).
# D'où la topologie attendue dans l'image : frontend dans /app, shared dans
# /shared (depuis /app, `../../shared` = /shared ; depuis /app/src/services,
# quatre niveaux remontent à /shared).

# ---------------------------------------------------------------------------
# Étape 1 : compilation du bundle statique
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

COPY web/frontend/package.json web/frontend/package-lock.json ./
# Lock resynchronisé avec package.json (l'ancien lock déclarait axios ^1.19.0
# alors que package.json déclare ^1.7.0, ce qui faisait échouer npm ci) :
# `npm ci` garantit un build reproductible à l'identique du lock.
RUN npm ci --no-audit --no-fund

# Bibliothèque partagée — doit être présente AVANT le build.
COPY shared /shared

# Code du frontend — copie ciblée (et non `COPY web/frontend/ ./`) pour que
# la modification d'un fichier annexe (nginx.conf, Dockerfile, doc) ne
# réinvalide pas la couche du build CRA.
COPY web/frontend/config-overrides.js ./
COPY web/frontend/public ./public
COPY web/frontend/src ./src

# DISABLE_ESLINT_PLUGIN : web/frontend/.env n'est pas copié (secrets exclus
# par .dockerignore) et CRA transforme les warnings ESLint en échec quand
# CI=true. CI=false : le build ne casse jamais sur du lint.
# GENERATE_SOURCEMAP=false : pas de sourcemaps exposées en production.
ENV DISABLE_ESLINT_PLUGIN=true \
    CI=false \
    GENERATE_SOURCEMAP=false \
    NODE_OPTIONS=--max-old-space-size=2048

RUN npm run build

# ---------------------------------------------------------------------------
# Étape 2 : service statique nginx (SPA + relais API/temps réel)
# ---------------------------------------------------------------------------
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY web/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Entrypoint vidé volontairement : le /docker-entrypoint.sh officiel exécute
# 10-listen-on-ipv6-by-default.sh qui appelle `apk manifest nginx` — cet appel
# peut rester bloqué (constaté sur Docker Desktop : conteneur « Up » mais
# nginx jamais lancé, port fermé). Aucun de ces scripts ne nous est utile :
# la configuration est statique (pas d'envsubst) et déjà en place.
ENTRYPOINT []

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

