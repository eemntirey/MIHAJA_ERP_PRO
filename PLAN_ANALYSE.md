## ANALYSE — Code lu (vérifié, non halluciné)

### 1. Modèles existants (confirmés par lecture)
- `Tenant` (`models/tenant.py`) : `plan` (String, default='gratuit'), `statut` (StatutTenant.EN_ESSAI), `date_abonnement`, `date_debut_essai`, `date_fin_essai`.
- `Abonnement` (`models/abonnement.py`) : `plan`, `statut`, `date_debut`, `date_fin`, `montant`, modules/limites (max_utilisateurs, max_employees, etc.).
- `SubscriptionAuditTrail` (`models/subscription_audit.py`) : `ancien_plan`, `nouveau_plan`, `declencheur` (automatique/manuel), `utilisateur_id`.
- `AuditLog` (`models/audit_log.py`) : `type_action` (CHANGEMENT_ABONNEMENT), `description`, `metadata_json`.
- `Notification` (`models/notification.py`) : `title`, `message`, `type` ('subscription_reminder'), `link`, `is_active`.
- **Aucun modèle `PlatformSettings`/`SystemConfig`** trouvé dans le backend.

### 2. Mécanisme de rétrogradation existant
- `AbonnementService.downgrade_to_free_plan()` (`services/abonnement_service.py` ligne 235) : crée un abonnement `plan='gratuit'`, met à jour `tenant.plan`, génère `SubscriptionAuditTrail`, et marque l'ancien abonnement `statut=EXPIRE`.
- `tasks/subscription_scheduler.py` : `run_subscription_expiration_check()` rétrograde automatiquement si `plan == 'pro'` ET `date_fin < now - 30 jours`.
- Note : le scheduler ne gère pas le rappel à J+3/J+6/.../J+30. C'est un simple check unique.

### 3. Endpoints Super Admin (confirmés par lecture `super_admin.py`)
- `/super-admin/subscriptions/set-all-free` (POST) — ligne 2118 : met `plan='pro'` sur TOUS les abonnements actifs (`update` SQL direct). C'est le bouton actuel "Appliquer le plan pro partout" dans `Subscriptions.jsx`.
- `/super-admin/subscriptions/notify-activation` (POST) — ligne 2058 : envoie notification 30j.
- `/super-admin/subscriptions/send-reminder-3j` (POST) — ligne 2088 : envoi manuel rappel -3j.
- `/super-admin/plans` (GET/PUT) — gestion des prix.

### 4. Logique d'inscription (`auth.py` ligne 169-382)
- `profile_type == 'company'` : `plan = data.get('plan', 'starter')`, crée `Tenant(plan=plan, statut=EN_ESSAI)`, puis `AbonnementService.create_abonnement({plan: plan})`.
- `plan == 'gratuit'` : `create_abonnement` appelle `activate_free_plan()` (montant=0, date_fin très lointaine).

### 5. Configuration plans (`security/plans.py`)
- `PLAN_CONFIG` : 'gratuit' (label 'Gratuit', max_employees=0, modules=_BASIC), 'starter', 'pro', 'enterprise'.
- `DEFAULT_PLAN = 'gratuit'`.
- `get_plan_config()`, `resolve_limits()`, `resolve_modules()` — pas de logique de toggle global.

### 6. Vérification des limites (`security/plan_limits.py`)
- Décorateur `check_plan_limits()` : compte actuel vs limite. Retourne 403 si atteint.
- `is_employee_limit_reached()` : compare `max_employees` au nombre d'employés actifs.
- **Pas de mécanisme de "non-blocage en mode inactif"** : le décorateur applique toujours 403 si la limite est atteinte.

### 7. Système d'audit (`audit_log.py`)
- `TypeActionAudit` inclut `CHANGEMENT_ABONNEMENT`, `MODIFICATION_PARAMETRE`, `ACTIVATION_TENANT`, etc.
- `AuditLog` est utilisé dans `_log_audit()` (super_admin.py).

### 8. Frontend
- `super-admin/src/pages/Subscriptions.jsx` : bouton "Appliquer le plan pro partout" (ligne 86) appelant `superAdminSubscriptionService.setAllFree()`.
- `super-admin/src/pages/Plans.jsx` : affichage de la grille (Gratuit/Starter/Pro/Enterprise).
- `super-admin/src/services/api.js` : `superAdminSubscriptionService.setAllFree()` -> POST `/super-admin/subscriptions/set-all-free`.
- **Pas de composant toggle / switch global** trouvé.

---

## POINTS NON TRANCHÉS — À traiter comme INCONNU dans le PLAN

### INCONNU 1 — Bascule Actif → Inactif : comportement des tenants rétrogradés
Le prompt demande : "À clarifier/vérifier avec l'équipe si un comportement spécifique est attendu pour les tenants déjà rétrogradés en Starter au moment de cette bascule (repassent-ils en Pro ? restent-ils en Starter ?)."
Le code actuel (`downgrade_to_free_plan`) crée un nouvel abonnement `gratuit` et laisse le tenant avec `plan='gratuit'`. Il n'y a pas de logique de "repasser automatiquement en Pro" en cas de bascule.
**Proposition cohérente (à valider)** : en mode INACTIF, seul le comportement des nouvelles inscriptions change (Pro gratuit). Les tenants déjà rétrogradés en Starter (ou Gratuit) **restent dans leur plan actuel** ; on ne modifie pas rétroactivement leur statut.

### INCONNU 2 — Mécanisme de "verrouillage sans suppression" après rétrogradation à 30 jours
Le prompt demande : "vérifier s'il existe déjà un mécanisme équivalent dans le projet (ex. soft-delete, flag `is_locked`, middleware de blocage par plan) avant d'en concevoir un nouveau."
Après lecture complète :
- `soft-delete` existe (`is_active = False`) mais s'applique au tenant ou à ses données, non au "verrouillage par plan".
- Il n'y a **aucun flag `is_locked`**, aucun middleware spécifique au verrouillage par plan au-delà des décorateurs de limite (`plan_limits.py`).
- La rétrogradation actuelle (`downgrade_to_free_plan`) ne supprime rien, mais ne verrouille pas non plus : le tenant reste actif avec le nouveau plan (plus restrictif), et les données existantes sont toujours en base, mais leur accès est restreint par les décorateurs de limite (ex. max_produits=10, max_employees=0).
**Proposition cohérente (à valider)** : après rétrogradation à 30 jours, le tenant passe sur le plan Starter (avec ses limites). Les données existantes ne sont pas supprimées. Pour rendre certaines données "inaccessibles" au-delà des limites du Starter, on s'appuie sur le mécanisme existant des décorateurs (`check_plan_limits`) et du `require_module`. Aucun nouveau mécanisme de verrouillage n'est inventé ; on réutilise le pattern existant de restriction par plan.

---

## PLAN D'IMPLÉMENTATION (détaillé — à valider avant code)

### 1. Modèle de données
- **Créer `PlatformConfig`** (`models/platform_config.py` ou équivalent) — singleton (une seule ligne en base) :
  - `id` (PK), `subscription_active` (bool, default=False), `updated_at`, `updated_by`.
  - Migration : créer la table `platform_config`, insérer ligne initiale (`subscription_active=False`).
  - Vérifier qu'aucune table similaire n'existe (confirmé : aucune).

- **Alignement Starter = ancien Gratuit** :
  - `PLAN_CONFIG['starter']` doit reprendre **exactement** les anciennes valeurs du `gratuit` pour `max_employees`, `max_utilisateurs`, `modules` ?
  - Le prompt dit : "le plan Starter reprend exactement le rôle et les limites de l'ancien plan Gratuit". Actuellement `starter` a `max_employees=2`, `max_utilisateurs=3`, `modules=_EXTENDED`. `gratuit` a `max_employees=0`, `max_utilisateurs=1`, `modules=_BASIC`.
  - **Décision** : si le mode ACTIF remplace Gratuit par Starter, il faut mettre à jour `PLAN_CONFIG['starter']` pour correspondre aux anciennes valeurs du Gratuit ? Ou garder Starter tel quel et considérer que "Starter reprend le rôle" signifie que Starter devient le plan d'entrée (le seul gratuit) ?
  - **Proposition** : garder `starter` tel quel (il est déjà le plan payant le plus bas). Le prompt demande que "Gratuit" disparaisse de la grille et que Starter reprenne son rôle. Cela signifie : dans le frontend, la grille passe de 4 plans à 3 (sans Gratuit). Le `PLAN_CONFIG['gratuit']` reste en base (pour ne pas casser les FK et références), mais il n'est plus affiché ni proposé. En mode INACTIF, le plan attribué par défaut est `pro` ; en mode ACTIF, le plan par défaut est `starter` (le seul visible autre que Pro/Enterprise).
  - **Migration de données** : aucune suppression. Les tenants existants en `plan='gratuit'` gardent leur valeur en base. Le toggle ne change pas rétroactivement leur plan (sauf la règle spéciale : activation du toggle → tous les Pro gratuits basculent dans le cycle payant).

### 2. API (backend)
- **Endpoint toggle** (`/super-admin/config/subscription-toggle`) :
  - GET : retourne `{subscription_active: bool}`.
  - PUT : met à jour `PlatformConfig.subscription_active`, log audit (`MODIFICATION_PARAMETRE`), retourne le nouvel état.
  - Remplacer le bouton actuel `set-all-free` par cet endpoint.

- **Logique d'inscription (`auth.py`)** :
  - Lire `PlatformConfig` au moment de l'inscription (`register`).
  - Si `subscription_active == False` : `plan = 'pro'` (sans choix, sans paiement). Ne pas afficher de choix.
  - Si `subscription_active == True` : `plan = data.get('plan', 'starter')` (avec choix dans la grille).

- **Logique de rétrogradation (`tasks/subscription_scheduler.py`)** :
  - Modifier le scheduler pour qu'il gère le cycle de grâce de 30 jours :
    - Pour tout abonnement `plan='pro'` dont `date_fin` est dépassée de moins de 30 jours : envoyer notification rappel (tous les 3 jours) au lieu de rétrograder immédiatement.
    - Au-delà de 30 jours (`date_fin < now - 30 jours`) : rétrograder vers `starter` (et non `gratuit` si on veut que Starter remplace Gratuit). **Important** : le code actuel utilise `downgrade_to_free_plan` qui met `plan='gratuit'`. Il faut soit créer `downgrade_to_starter` soit modifier `downgrade_to_free_plan` pour accepter le plan cible.
  - **Notification tous les 3 jours** : le scheduler doit créer des `Notification` (`type='subscription_reminder'`) avec un `link` stable. On peut s'appuyer sur le couple `(type, link)` pour éviter la duplication (déjà présent dans `_existing_active_by_link` dans `notification_service.py`).

- **Bascule Inactif → Actif (transition immédiate)** :
  - Quand le toggle passe de False → True : trouver tous les tenants avec un abonnement `plan='pro'` créé pendant le mode inactif (montant=0) et démarrer leur cycle de grâce.
  - **Option la plus simple et cohérente** : au moment de l'activation, mettre à jour tous les abonnements Pro (montant=0) pour les marquer comme "en cycle de grâce" (statut reste ACTIF, mais `date_debut_essai` ou un nouveau champ `grace_start` est mis à `now`). Ensuite le scheduler existant gère la rétrogradation après 30 jours.
  - **Alternative** : créer un nouveau `SubscriptionAuditTrail` et mettre `date_fin = now + 30 jours` pour ces abonnements (comme s'ils venaient d'expirer). Mais cela modifierait leur abonnement.
  - **Proposition** : au moment de la bascule, pour chaque tenant en Pro gratuit (`plan='pro'` ET `montant == 0`), créer un nouvel abonnement Pro (payant) avec `statut=EN_ATTENTE`, `date_debut=now`, `date_fin=now + 30 jours` (grâce), et marquer l'ancien comme `EXPIRE`. Cela déclenche automatiquement le cycle de notification et de rétrogradation du scheduler existant.

### 3. Logique des quotas (`security/plan_limits.py`)
- Modifier `check_plan_limits()` et `is_employee_limit_reached()` pour consulter le toggle global (`PlatformConfig.subscription_active`).
- **Si `subscription_active == False`** :
  - Pour `employes` (`max_employees`) : ne pas bloquer (ne pas retourner 403). Au lieu de cela, retourner un avertissement (ou simplement autoriser sans erreur, mais le frontend doit afficher la bannière d'avertissement à 10 employés).
  - Pour `produits`, `clients`, `utilisateurs` : illimité (`is_unlimited` doit retourner True pour ces limites).
  - Pour les modules (`require_module`) : autoriser `_ALL` (tous modules accessibles, y compris `stocks`, `achats`, etc.).
- **Si `subscription_active == True`** : comportement normal (déjà en place).

### 4. Frontend
- **Super Admin (`Subscriptions.jsx`)** :
  - Remplacer le bouton "Appliquer le plan pro partout" par un **switch ON/OFF** (toggle) affichant l'état actuel (`subscription_active`).
  - Remplacer le bouton "Activer plans (notification 30j)" par le bouton du toggle.
  - Ajouter un appel GET au chargement pour récupérer l'état du toggle.
- **Super Admin (`Plans.jsx`)** :
  - Conditionnellement masquer le plan "Gratuit" de la grille si `subscription_active == True` (ou toujours le masquer si le toggle est actif). Actuellement, le frontend reçoit `PLAN_CONFIG` via `/super-admin/plans` et affiche tous les plans. Il faut filtrer côté frontend (ou modifier le backend `/super-admin/plans` pour ne pas inclure `gratuit` en mode actif).
- **Tenant (`Subscription.jsx` / inscription)** :
  - Si `subscription_active == False` : masquer la page Abonnement (ou la rendre inaccessible), et lors de l'inscription, ne pas afficher le choix de plan (assigner automatiquement `pro`).
  - Afficher une bannière d'avertissement non bloquante si le nombre d'employés approche 10 en mode inactif.

### 5. Tests (à ajouter)
- `test_subscription_toggle_inactif_actif` : bascule toggle → tous les Pro gratuits reçoivent un cycle de grâce de 30 jours.
- `test_inscription_inactif` : plan Pro assigné automatiquement, pas de choix.
- `test_inscription_actif` : choix de plan affiché, Starter présent, Gratuit absent.
- `test_employes_inactif` : création du 11ème employé autorisée (pas de 403), avertissement affiché.
- `test_cycle_notifications` : notifications créées à J+3, J+6, ... (simuler avec des dates).
- `test_retrogradation_30j` : après 30 jours sans paiement, rétrogradation vers Starter ; données non supprimées (vérifier que `is_active` des données reste True, mais accès restreint par limites).

---

## CRITÈRES D'ACCEPTATION (avant tout commit)
- [ ] Toggle réversible sans erreur, sans perte de données.
- [ ] Aucune suppression physique de données dans le cycle (confirmer via lecture du code `downgrade_to_free_plan` et de la migration).
- [ ] Isolation multi-tenant respectée : le toggle est global, mais son application reste calculée par tenant (audit trail avec `tenant_id`).
- [ ] Le changement Gratuit → Starter ne casse aucune FK existante (`plan='gratuit'` reste valide en base, mais masqué dans la grille).
- [ ] Vérifier via lecture du code que `PLAN_CONFIG['gratuit']` n'est pas supprimé du backend (pour éviter les erreurs de référence).

---

## ACTION REQUISE : VALIDATION AVANT CODE
Avant d'écrire une ligne :
1. Confirmer ou corriger la **proposition INCONNU 1** (bascule Actif → Inactif : les rétrogradés restent Starter ?).
2. Confirmer ou corriger la **proposition INCONNU 2** (verrouillage : réutiliser le mécanisme de limite existant, sans inventer `is_locked`).
3. Valider la décision sur `PLAN_CONFIG['starter']` (garder tel quel, mais masquer `gratuit` dans la grille en mode actif).
4. Valider la création du modèle singleton `PlatformConfig`.

Dès validation, j'implémente dans cet ordre : modèle → API (toggle + inscription + scheduler) → service quotas → frontend → tests.
