# PLAN — Toggle Abonnement Global (Super Admin) — IMPLÉMENTATION FINALE (2026-09-15)

## Récapitulatif de la spécification appliquée (conforme au prompt utilisateur)
- **Mode INACTIF** (défaut au premier lancement) : Pro offert à l'inscription,
  quotas levés (backend), modules ouverts, page Abonnement masquée côté tenant,
  avertissement visuel (non bloquant) au seuil de 10 employés.
- **Mode ACTIF** (commercial) : choix du plan à l'inscription, cycle de grâce de
  30 jours, rappels tous les 3 jours, rétrogradation automatique vers Starter.
- **Grille mode ACTIF** : **Starter / Pro / Entreprise** — le plan **Starter
  reprend exactement les limites de l'ancien plan Gratuit**
  (1 utilisateur / 10 produits / 10 clients / 0 employé, modules `_BASIC`,
  prix 0, durée 30j). Le plan "Gratuit" disparaît **de la grille affichée**
  (`get_public_plans`) mais reste dans `PLAN_CONFIG` comme valeur legacy :
  des tenants existants peuvent avoir `plan='gratuit'` en base et le champ
  `is_free_plan` de l'API y référence `'gratuit'`. Aucune suppression, aucune
  migration destructive (critère : ne casser aucune référence en base).

## Points INCONNU — résolutions appliquées
1. **Bascule Actif → Inactif** : ne rien changer rétroactivement (les tenants
   déjà rétrogradés en Starter restent en Starter ; seules les nouvelles
   inscriptions reçoivent Pro gratuit).
2. **Verrouillage sans suppression** : réutilisation des mécanismes existants
   (`plan_limits` limites par plan + `require_module` + `subscription_required`)
   — pas de nouveau flag `is_locked`. Les données restent toujours en base.

## Implémentation finale (vérifiée + testée)

### Backend
- `models/platform_config.py` : singleton `PlatformConfig`
  (`is_subscription_active=False` par défaut) + `get_config()`.
- `migrations/versions/o1p2q3r4s5t6_add_platform_config_toggle.py` : table
  `platform_configs` (Alembic, server_default false, FK updated_by).
- `models/audit_log.py` : membre `MODIFICATION_PARAMETRE` ajouté à
  `TypeActionAudit` (ajout rétro-compatible).
- `api/v1/auth.py` :
  - `PublicPlans` (GET `/auth/plans`) : retourne `get_public_plans()` filtré
    selon le toggle + champ `subscription_active` (endpoint public).
  - `AuthRegister` : mode inactif → `plan='pro'` forcé ; mode actif → choix.
  - `AuthMe` (GET `/auth/me`) : champ `subscription_active` exposé.
- `api/v1/abonnements.py` (`MonAbonnement`) : champ `subscription_active`
  dans les 3 variantes de réponse (utilisé par Users.jsx et Subscription.jsx).
- `api/v1/super_admin.py` : endpoint `/subscription-toggle` (GET/PUT/POST) :
  audit `AuditLog(MODIFICATION_PARAMETRE)`, et à l'activation : tous les
  abonnements Pro gratuits (montant==0) reçoivent `date_fin = now + 30j`,
  `montant = get_plan_price('pro')` (prix courant, plus de hard-code),
  `SubscriptionAuditTrail(declencheur='activation_toggle')`, notification
  initiale + broadcast websocket. Réversible sans limite.
- `security/plans.py` : `get_public_plans(is_active)` (grille Starter/Pro/
  Enterprise en actif, Pro seul en inactif) ; Starter = ex-Gratuit ;
  `DEFAULT_PLAN='starter'`.
- `security/plan_limits.py` : `is_subscription_inactive()` ; `check_plan_limits`
  non bloquant en mode inactif ; `is_employee_limit_reached` → False en mode
  inactif ; `require_module` ouvert en mode inactif.
- `security/tenant.py` (`tenant_required`) : bypass abonnement en mode inactif.
- `services/abonnement_service.py` : `create_abonnement` consulte le toggle ;
  `downgrade_to_starter_plan` (cible paramétrable) + `downgrade_to_free_plan`
  (alias rétro-compatible vers starter).
- `tasks/subscription_scheduler.py` : `run_subscription_reminders()`
  (rappel si ≥3j depuis la dernière notification) ;
  `run_subscription_expiration_check()` → downgrade Starter.

### Frontend Super Admin
- `super-admin/src/pages/Subscriptions.jsx` : switch « Mode commercial »
  (ON/OFF) remplaçant l'ancien bouton « Appliquer le plan pro partout ».
- `super-admin/src/pages/Plans.jsx` : plan Starter filtré de la grille.
- `super-admin/src/services/api.js` : `getToggle` / `setToggle`.

### Frontend Tenant (web)
- `web/frontend/src/pages/Subscription.jsx` : si `subscription_active ===
  false` → page remplacée par un écran « Module Abonnement désactivé ».
- `web/frontend/src/pages/Users.jsx` : bannière non bloquante « Mode
  découverte » à partir de 8 employés (approche du seuil 10) et message
  différent au-delà de 10 ; la création reste autorisée.

### Tests
- `web/backend/tests/test_subscription_toggle.py` (NOUVEAU) : **10/10 passed**.
  Couvre : grille publique selon toggle, Starter = limites ex-Gratuit,
  inscription inactif (Pro, montant 0), inscription actif (choix conservé),
  11 employés créés en mode inactif (non bloquant), activation toggle
  (grâce 30j, montant = prix Pro courant, audit, notification), réversibilité,
  refus sans droits super admin, rappels J+0/J+1(non)/J+4(oui)/J+5(non),
  rétrogradation à J+31 avec **données (Produit) conservées en base**.
- `tests/test_plan_limits.py` + `tests/test_public_catalog.py` : fixtures
  mises à jour pour forcer le mode commercial (`is_subscription_active=True`)
  — ces tests valident les restrictions du mode ACTIF. 3 échecs corrigés.

## Points à signaler (vérifiés, hors périmètre)
1. **Échecs de tests préexistants à HEAD** : 8 échecs (super admin bypass
   permissions, messages « employés » encodés, catalogue public stock) existent
   déjà à HEAD `9cc5de22` (vérifié via worktree propre : 11 échecs à HEAD).
   Ils concernent `users.py` permissions, encodage des messages (EOL/BOM) et
   `produit_service.py` — **pas causés par le toggle**, non corrigés ici
   (périmètre).
2. **Scheduler non planifié** : `run_subscription_reminders` /
   `run_subscription_expiration_check` sont des fonctions appelables, exposées
   aussi via les endpoints manuels `/super-admin/subscriptions/notify-activation`
   et `/send-reminder-3j`, mais **aucun cron/APScheduler** ne les invoque
   automatiquement. En production, prévoir un cron (ex: systemd timer / celery
   beat) appelant ces deux fonctions toutes les 24h.
3. **L'ancien endpoint** `/super-admin/subscriptions/set-all-free` reste en
   backend (bouton frontend supprimé). Non supprimé (règle : aucune suppression
   sans besoin démontré) ; peut être retiré dans une passe de nettoyage dédiée.

