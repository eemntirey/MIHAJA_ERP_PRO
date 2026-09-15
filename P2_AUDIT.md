# P2 - Audit et durcissement (15/09/2026)

## Bump manuel (pas de réseau externe)
- web/backend/requirements.txt : déjà à jour (`Flask==3.0.0`, `cryptography==42.0.5`, `Pillow==10.4.0`, `numpy==1.26.4`, `requests==2.32.3`)
- web/frontend/package.json : `axios` `^1.19.0` → `^1.7.0`
- package.json (racine) : `axios` `^1.19.0` → `^1.7.0`

## En-têtes de sécurité ajoutées
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security`
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`

## Actions différées (à faire en CI / avec réseau)
- `pip-audit` (PyPI)
- `npm audit` (npm registry)
- `pip install --upgrade -r requirements.txt` (vérifier compatibilité)
- `npm ci` / `npm audit fix`
- Rotation `ENCRYPTION_KEY` (KMS / clé par tenant) — P2 avancé
