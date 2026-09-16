# P1 Finalisé / Restant

Terminé dans cette session :
- WS `pwd_v` + `TokenBlocklist` vérifiés (`socket_server.py`).
- `compare_digest` sur `PasswordResetToken.verify_token`.
- `permission_required_all` sur `user.create`, `user.delete`, `compte.delete`.
- `secure_filename` + `abspath` PDF (`documents.py`, `pdf_generator.py`).
- `CORS` prod strict (`__init__.py`).
- `Swagger` désactivé en prod (`__init__.py`).
- `FLASK_DEBUG` contrôlé (`run.py`, `.env` supprimés).
- `temporary_password` retiré de la réponse JSON et du log (`users.py`, `email_service.py`).
- CSV-injection (`_sanitize_csv_cell`) + export sécurisé (`comptabilite_service.py`).
- Headers sécurité (`CSP`, `HSTS`, `X-Frame-Options`, etc.) ajoutés (`__init__.py`).

Restant (P2 / durcissement) :
1. KMS / clé par tenant (`ENCRYPTION_KEY` unique → Vault / AWS KMS / HashiCorp Vault) — documenté dans `SECRETS_ROTATION.md`.
2. `git filter-repo` / `BFG` historique (`erp.db`, `.env`) — action manuelle nécessaire hors session.
3. Cookies `HttpOnly Secure` — pas d'usage de cookies dans le code actuel (JWT header uniquement), ajouter si un système de session cookie est introduit.
4. `pip-audit` exécution réelle (`audit_deps.py` créé, `requirements.txt` mis à jour).
5. CI `gitleaks` / `truffleHog` — à ajouter dans `.github/workflows` ou pipeline existant.

Étape suivante suggérée : valider le build (`python -m pytest` ou `docker-compose up`) et exécuter `python web/audit_deps.py`.
