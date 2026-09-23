# Validation 5 questions — Démo locale MIHAJA ERP PRO

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire devenir « oui » les 5 questions (desk 1 semaine offline, web+central, modules sans bug bloquant, mobile connecté, livrable démo) sur une **démo locale**, critère **P0 + suite pytest verte**, central = **localhost**.

**Architecture:** Stabiliser le WIP offline (backend embarqué desk), corriger les P0 du registre RAPPORT, rejouer la suite backend sur PostgreSQL, smoke-tester web/desk/mobile contre `localhost:5000`, produire une checklist de démo signée.

**Tech Stack:** Flask + SQLAlchemy + pytest/Postgres, React CRA, Electron, Expo.

**Spec / sources:**
- `RAPPORT_COMPLET_MIHAJA_ERP_PRO.md` (registre bugs, top priorités)
- `docs/technical/CARTE_MISE_EN_PRODUCTION.md` (smoke tests — version démo)
- `docs/superpowers/plans/2026-09-21-backend-local-embarque-offline.md`

## Global Constraints

- Messages utilisateur/API en **français**, devise **MGA**.
- Ne **pas** toucher au filtre multi-tenant (`app/security/tenant.py`) sauf preuve de bug.
- Démo locale uniquement : pas de VPS, pas de domaine, pas de PAPI/SMTP réels.
- Central = `http://127.0.0.1:5000` ; mobile émulateur Android = `10.0.2.2:5000`.
- TDD : test qui échoue d’abord, puis code, puis commit.
- Aucun secret en clair ajouté ; les existants (scripts) partent en variables d’env.
- Ne pas supprimer de données utilisateur ; `erp.db` seulement retiré du suivi git.
- Ne jamais lancer de subagent implémenteur en parallèle (conflits de fichiers).
- Ne jamais `xfail` un P0 pour faire passer la suite.

## File Map

| Zone | Fichiers | Rôle |
|---|---|---|
| Stabilisation WIP | `desk/electron/backendHost.js`, `web/backend/run.py`, `app/services/local_bootstrap.py`, `tests/_db_utils.py`, `migrations/versions/z9y8x7w6v5u4_repair_missing_columns.py` | Offline desk non committé |
| Central démo | `desk/electron/backendHost.js` (`REPLICATION_URL`), `mobile/.env` | URL central locale |
| P0 bugs | `app/ai/previsions.py`, `app/ai/anomalies.py`, `web/backend/scripts/*.py`, `.gitignore`, `app/api/v1/ventes.py` | Registre RAPPORT |
| Hygiène | `web/backend/inspect_db.py`, `_tmp_check_version.py`, `app/ai/tmp6v20umnk` | Artifacts à nettoyer |
| Vérification | `web/backend/tests/**`, `.github/workflows/pytest.yml` | Suite verte |
| Livrable | `docs/user/DEMO_LOCALE.md` (nouveau) | Checklist boss |

## Acceptance Mapping

| # | Question | Tasks |
|---|---|---|
| 1 | Desk offline 1 semaine | 1, 2, 8 |
| 2 | Web + central | 7, 9 |
| 3 | Modules sans bug P0 | 3–7, 11 |
| 4 | Mobile central | 10 |
| 5 | Livrable boss | 12 |

---

### Task 1: Stabiliser et commiter le WIP offline (desk)

**Files:**
- Modify: `desk/electron/backendHost.js`
- Modify: `web/backend/run.py`, `web/backend/app/services/local_bootstrap.py`, `web/backend/tests/_db_utils.py`
- Create/track: `web/backend/migrations/versions/z9y8x7w6v5u4_repair_missing_columns.py`
- Test: `web/backend/tests/test_local_bootstrap.py`, `test_local_embedded_config.py`, `test_replication_full_cycle.py`

**Interfaces:**
- Produces: arbre de travail propre sur ces fichiers ; migration de réparation versionnée ; backend local démarre.

**Steps:**
- [ ] Lire `git status -sb` + `git diff --stat` sur les 4 fichiers WIP
- [ ] Vérifier heads Alembic : `flask --app 'app:create_app' db heads` → `z9y8x7w6v5u4` unique (sinon corriger `down_revision`)
- [ ] Run: `cd web/backend && python -m pytest tests/test_local_embedded_config.py tests/test_local_bootstrap.py tests/test_replication_full_cycle.py -q` → PASS
- [ ] Si échec : diagnostiquer et corriger (migration/bootstrap), re-run
- [ ] `git add` des 5 fichiers + commit `fix(offline): resolution Python embarque, bootstrap local + migration reparation colonnes`
- [ ] **Ne pas** committer les artifacts debug (`inspect_db.py`, `_tmp_*`, `tmp6v20umnk`) ni les autres fichiers modifiés hors Task 5

---

### Task 2: Central de démo = localhost (desk + mobile)

**Files:**
- Modify: `desk/electron/backendHost.js:106` — défaut `REPLICATION_URL`
- Modify: `mobile/.env`
- Optional: warning French si secret fallback par défaut

**Interfaces:**
- Produits: `REPLICATION_URL` démo = `http://127.0.0.1:5000` ; mobile lit `EXPO_PUBLIC_API_URL`.

**Steps:**
- [ ] Dans `backendHost.js` : `REPLICATION_URL: cfg.replicationUrl || process.env.REPLICATION_URL || 'http://127.0.0.1:5000'`
- [ ] Si secret fallback `local-embedded-secret-*` : `console.warn` French au démarrage
- [ ] `mobile/.env` : garder `EXPO_PUBLIC_API_URL=http://10.0.2.2:5000/api/v1` + commentaires physique/web
- [ ] Run: `python -m pytest tests/test_local_embedded_config.py -q` → PASS
- [ ] Commit `fix(demo): REPLICATION_URL et mobile .env pour central localhost`

---

### Task 3: P0 — isolation IA multi-tenant (#97/#98)

**Files:**
- Modify: `web/backend/app/ai/previsions.py`, `web/backend/app/ai/anomalies.py`
- Test: `web/backend/tests/test_ai.py` (étendre)

**Interfaces:**
- Produits: toute requête IA filtre `tenant_id` via `get_current_tenant_id()` ; Aucune fuite A → B.

**Steps:**
- [ ] Écrire test d'isolement 2 tenants dans `test_ai.py` (FAIL si filtre absent)
- [ ] Run: `pytest tests/test_ai.py -k isol -q` → FAIL attendu si #97 ouvert
- [ ] Implémenter filtre `tenant_id` manquant (pattern `get_current_tenant_id() or tenant_id`, `filter_by(tenant_id=tid)`)
- [ ] Run: `pytest tests/test_ai.py -q` → PASS
- [ ] Commit `fix(ai): filtre tenant_id obligatoire previsions/anomalies`

---

### Task 4: P0 — mots de passe en clair dans les scripts (#70 / A3)

**Files:**
- Modify: `web/backend/scripts/check_auth.py`, `create_sa.py`, `create_superadmin.py`, `check_superadmin_auth.py`
- Modify: `.env.example` — `DEFAULT_ADMIN_PASSWORD`
- Create: `web/backend/tests/test_no_plaintext_script_passwords.py`

**Steps:**
- [ ] Test: bannières `Super123!` / `Test1234!` absentes de `scripts/*.py` → FAIL
- [ ] Remplacer par `os.environ.get('DEFAULT_ADMIN_PASSWORD')` + SystemExit si absent
- [ ] Ajouter `DEFAULT_ADMIN_PASSWORD=` à `.env.example` (vide, pas de valeur)
- [ ] Run test → PASS
- [ ] Commit `fix(securite): mots de passe scripts via env`

---

### Task 5: P0 — hygiène dépôt (A2 + artifacts debug)

**Files:**
- Modify: `.gitignore`
- Command: `git rm --cached erp.db` (si suivi)
- Delete: `web/backend/inspect_db.py`, `_tmp_check_version.py`, `web/backend/app/ai/tmp6v20umnk`

**Steps:**
- [ ] `git ls-files | Select-String '\.db$|inspect_db|tmp6v20'`
- [ ] `git rm --cached erp.db` si présent ; supprimer artifacts untracked
- [ ] `.gitignore` += `*.db`, `*.sqlite3`, `_tmp_*`, `inspect_db.py`
- [ ] Commit `chore(repo): sortir erp.db du git + supprimer artifacts debug`
- [ ] Ne pas committer d'autres fichiers en attente

---

### Task 6: P0 — #16 strptime sans garde (500 date invalide)

**Files:**
- Modify: `web/backend/app/api/v1/ventes.py`
- Test: étendre test existant ventes ou `test_critical_api.py`

**Steps:**
- [ ] Test: `GET /ventes?date_debut=not-a-date` → 200 ou 400, **jamais 500** → FAIL si 500
- [ ] try/except `datetime.strptime` → 400 message French `Format de date invalide (AAAA-MM-JJ).`
- [ ] Run → PASS
- [ ] Commit `fix(ventes): validation date filtre -> 400`

---

### Task 7: Suite backend 100 % verte

**Files:**
- Tous `web/backend/tests/**`
- Infra: Docker `erp-pg` + `web/backend/setup_postgresql.ps1` si absent

**Steps:**
- [ ] Vérifier/monter Postgres : `docker ps --filter name=erp-pg` sinon `setup_postgresql.ps1`
- [ ] `cd web/backend; $env:TEST_DATABASE_URL='postgresql+psycopg://postgres@localhost:55432/erp_test'; python -m pytest tests/ -q --tb=line`
- [ ] Chaque échec → systematic-debugging → fix + test local → re-run
- [ ] Deux passes consécutives 0 failed
- [ ] Commits `fix(tests): …` par lot de correctifs
- [ ] **Interdiction:** xfail/skip un P0

---

### Task 8: Validation desk offline « ≥ 1 semaine »

**Files:**
- Create: `docs/user/DEMO_LOCALE.md` (section offline)
- Vérif: `test_replication_full_cycle.py`, `test_local_bootstrap.py`

**Steps:**
- [ ] `pytest tests/test_replication_full_cycle.py tests/test_local_bootstrap.py -q` → PASS
- [ ] Documenter + exécuter le scénario manuel (login online → couper réseau/central → restart desk → login offline → ventes → reconnect → push visible web)
- [ ] Preuve refresh JWT local (access expiry court ou step documenté)
- [ ] Résultats ✅/❌ dans `DEMO_LOCALE.md`
- [ ] Si échec login offline / push → fix + tests, re-Step 1

---

### Task 9: Web + central localhost — smoke bout en bout

**Steps:**
- [ ] Backend `python run.py` → `/api/v1/health` 200
- [ ] Frontend `npm start` :3000 → proxy 5000
- [ ] Parcours: Login → Dashboard → Clients CRUD → Produits CRUD → Vente → Stock (pas de 500, messages FR)
- [ ] Logger dans `DEMO_LOCALE.md`
- [ ] Si bug bloquant découvert → fix + tests dans le même task

---

### Task 10: Mobile connecté au central local

**Steps:**
- [ ] Backend up ; CORS inclut `localhost:8081` (déjà)
- [ ] `cd mobile && npm start`
- [ ] Login → Home stats → Vente liste → Inventaire recherche → Livraison `avancer`
- [ ] Fix si échec API (routes/extractList)
- [ ] Logger dans `DEMO_LOCALE.md`

---

### Task 11: Balayage P0 final registre

**Steps:**
- [ ] Re-vérifier top RAPPORT §8.3 : A2 (T5), A3 (T4), #97/98 (T3), #16 (T6) → statuts
- [ ] Balayer `À RE-VÉRIFIER` **utilisés en démo** (ventes, stocks, auth, livraisons) : si 500/403 en test → fix
- [ ] A5/A6, M1 : noter « hors démo locale » dans checklist
- [ ] Commit si fixes supplémentaires

---

### Task 12: Livrable boss — checklist démo locale

**Files:**
- Create: `docs/user/DEMO_LOCALE.md` (compléter)

**Steps:**
- [ ] Prérequis + ordre de démarrage (backend, web, desk, mobile)
- [ ] Tableau 5 questions avec preuve + date + ☐/☑
- [ ] Script démo 10 min
- [ ] Commit `docs(demo): checklist validation 5 questions`

## Hors périmètre assumé

Prod VPS/HTTPS, PAPI réel, SMTP, stores, PWA, soft-delete 100 %, déduplication `shared/` — pas requis pour la démo locale.
