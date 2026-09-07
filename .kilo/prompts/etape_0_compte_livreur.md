# ÉTAPE 0 — Audit et intégration du compte Livreur dans MIHAJA_ERP_PRO

## CONTEXTE SCHÉMA (déjà connu, ne pas re-déduire)

Le MCD/MLD actuel confirme que :
- `livreurs` n'a AUCUNE colonne vers `utilisateurs` aujourd'hui. Ce n'est pas une
  relation à auditer, c'est une relation à CRÉER.
- `utilisateurs.role` est un ENUM fermé :
  ENUM(super_admin,admin,manager,sales,stock,accountant,user,rh)
- `utilisateurs` a AUSSI un `custom_role_id → roles`, avec `roles` +
  `permissions` + `role_permissions` (RBAC dynamique en parallèle de l'ENUM).
  → Il existe donc DEUX systèmes de rôles. Ne pas en ajouter un troisième.
- Aucune permission actuelle ne semble distinguer un scope "own" (mes propres
  ressources) d'un scope "all" (tout le tenant) — à vérifier dans le code réel
  des services/decorators de permission avant de conclure.
- Un précédent architectural existe déjà pour une relation 0..1 ↔ 0..1
  optionnelle entre deux fiches métier : `livreurs.vehicule_id → vehicules`
  et `vehicules.chauffeur_id → livreurs`. Réutiliser ce pattern SQLAlchemy
  (relationship/back_populates) plutôt qu'en inventer un nouveau.

## OBJECTIF

Avant toute modification du workflow Livraison, analyser et préparer correctement
la relation entre :
- la fiche métier `Livreur`
- le compte `Utilisateur`
- le futur rôle `livreur`

Le but : qu'un livreur puisse avoir un compte de connexion **sans confondre**
sa fiche métier avec son compte utilisateur.

## RÈGLE MÉTIER

Un `Livreur` est une fiche métier. Un `Utilisateur` est un compte d'authentification.

Relation souhaitée : `Utilisateur 0..1 ───── 0..1 Livreur`

Un livreur peut :
1. exister sans compte utilisateur ;
2. être lié à un compte utilisateur ;
3. utiliser ce compte pour se connecter à l'ERP.

NE PAS remplacer `Livreur` par `Utilisateur`. NE PAS fusionner les deux modèles.

## 1. AUDIT AVANT MODIFICATION (obligatoire, à faire en premier)

Inspecter et rapporter le contenu réel de :
```
web/backend/app/models/livreur.py
web/backend/app/models/utilisateur.py
web/backend/app/models/vehicule.py        (pattern de relation à imiter)
web/backend/app/models/__init__.py
web/backend/app/models/role.py / permission.py (si présents)

web/backend/app/services/
web/backend/app/api/v1/livraisons.py
web/backend/app/api/v1/utilisateurs.py (ou équivalent)

web/frontend/src/
desk/src/

migrations/
tests/
```

Déterminer précisément, et le documenter dans le rapport final :
- Comment `Role` (ENUM) et `custom_role_id`/`roles`/`role_permissions` sont
  utilisés en pratique — lequel des deux fait réellement autorité dans le
  code de vérification des permissions (decorators, middleware, `current_user`) ?
- Comment les permissions actuelles distinguent (ou non) "mes ressources" vs
  "toutes les ressources du tenant". S'il n'existe aucun mécanisme de ce type,
  le signaler explicitement plutôt que d'en improviser un.
- Comment `tenant_id` est dérivé côté backend (JWT claims / contexte
  authentifié — jamais du client HTTP), pour réutiliser exactement le même
  mécanisme pour l'isolation Livreur.
- Comment la relation `vehicule_id ↔ chauffeur_id` est déclarée en SQLAlchemy
  (nullable, backref/back_populates, contraintes) — c'est le patron à suivre
  pour `Livreur ↔ Utilisateur`.

Ne rien modifier avant d'avoir rapporté ces constats.

## 2. RÔLE LIVREUR

Le système a DEUX sources de rôles (ENUM `role` + table `roles`/RBAC dynamique).
Trancher, en te basant sur ce que le code utilise réellement pour l'autorisation
(pas sur ce qui semble "le plus propre" en théorie) :
- soit ajouter `livreur` à l'ENUM système existant,
- soit créer une ligne dans `roles` avec les permissions adéquates dans
  `role_permissions`,
- soit les deux si le code applicatif vérifie effectivement les deux champs.

Justifier le choix dans le rapport. NE PAS créer un troisième système de rôles.
NE PAS coder des permissions dispersées dans plusieurs fichiers.

## 3. RELATION LIVREUR ↔ UTILISATEUR (à créer, confirmé absente du schéma)

Ajouter sur `livreurs` :
```
utilisateur_id  FK → utilisateurs, NULLABLE, UNIQUE
```
En suivant le style de relation déjà utilisé pour `vehicule_id`/`chauffeur_id`
(nullable, relationship SQLAlchemy cohérente avec le reste du codebase).

Contraintes obligatoires :
- `utilisateur_id` nullable — un livreur sans compte reste parfaitement valide ;
- UNIQUE sur `utilisateur_id` — un utilisateur ne peut être lié qu'à un seul livreur ;
- le lien doit respecter le même `tenant_id` des deux côtés ;
- aucune possibilité de lier un livreur du Tenant A à un utilisateur du Tenant B.

NE PAS modifier `vehicules`, `itineraires`, ou tout autre modèle non concerné.

## 4. SÉCURITÉ MULTI-TENANT (obligatoire)

Vérifier explicitement `Livreur.tenant_id == Utilisateur.tenant_id` avant toute
association, au niveau service (pas seulement au niveau UI/frontend). Si possible,
ajouter aussi une garde au niveau DB (event listener SQLAlchemy `before_insert`/
`before_update`, ou contrainte si le SGBD le permet) pour ne pas dépendre
uniquement de la discipline applicative — signaler dans le rapport si ce n'est
pas faisable proprement en SQLite.

Les endpoints doivent respecter les mécanismes de sécurité existants
(`tenant_required`, permissions, JWT). NE PAS créer de contournement.

## 5. PERMISSIONS DU RÔLE LIVREUR

Ne pas donner au livreur les permissions d'un `admin`, `manager` ou `super_admin`.

Préparer au minimum la logique pour, ensuite :
- voir ses propres livraisons (uniquement les siennes — voir point d'attention
  ci-dessus sur l'absence possible de scope "own" dans le système actuel) ;
- voir les informations nécessaires à ses livraisons ;
- mettre à jour le statut de ses livraisons ;
- ajouter un événement de suivi.

Si une permission existante couvre déjà le besoin, la réutiliser. NE PAS créer
de permissions arbitraires en double. Ne pas implémenter le GPS temps réel
pour l'instant.

## 6. ISOLATION DES LIVRAISONS

Chaîne de résolution à préparer :
```
Livreur connecté → Utilisateur courant → Livreur associé → livraisons affectées
```
Un livreur connecté ne doit jamais pouvoir :
- voir/modifier les livraisons d'un autre livreur ;
- voir les livraisons d'un autre tenant.

`tenant_id` = première barrière. `livreur_id` = restriction métier ensuite.

## 7. NE PAS TOUCHER AU WORKFLOW LIVRAISON (réservé à l'ÉTAPE 1)

NE PAS modifier : les statuts (`en_attente, chargee, en_route, livree,
retournee, echec`), `TRANSITIONS_AUTORISEES`, l'endpoint `/avancer`,
`SuiviLivraison`/`suivis_livraison`.

## 8. NE PAS TOUCHER (hors périmètre de cette étape)

GPS, WebSocket, carte, notifications, PDF, stock, facturation, OrderTracking,
cascade Tenant, frontend Livraison (sauf strict nécessaire pour lier un compte
à une fiche livreur), abonnements, Super Admin, Tenant, RH, autres rôles.

## 9. TESTS OBLIGATOIRES

1. Créer un livreur sans compte utilisateur → SUCCESS
2. Associer un compte utilisateur à un livreur → SUCCESS
3. Associer un utilisateur du Tenant A à un livreur du Tenant B → REFUS
4. Livreur connecté accède à ses propres livraisons → SUCCESS
5. Livreur connecté tente d'accéder à la livraison d'un autre livreur → REFUS
6. Livreur du Tenant A tente d'accéder à une livraison du Tenant B → REFUS
7. Les rôles existants continuent de fonctionner
   (super_admin, admin, manager, sales, stock, accountant, rh, user) → SUCCESS

## 10. MIGRATION

- Créer une migration propre, ne pas utiliser `create_all()` en remplacement.
- Ne supprimer aucune donnée existante.
- `utilisateur_id` nullable.
- Si `livreur` est ajouté à l'ENUM `utilisateurs.role` : vérifier la stratégie
  de migration ENUM en SQLite (souvent recréation de table via SQLAlchemy/Alembic
  batch mode) et anticiper la portabilité vers MySQL si le projet doit y migrer.

## 11. FRONTEND

Pas de refonte UI. Si l'architecture frontend gère déjà les utilisateurs,
ne pas créer d'interface parallèle. Modification minimale seulement si
nécessaire pour lier un compte à une fiche livreur.

## 12. RÈGLE ANTI-RÉGRESSION

AUDITER → COMPRENDRE → MODIFIER LE MINIMUM → TESTER.
Ne pas réécrire un fichier entier si quelques lignes suffisent.
Ne pas créer de doublons ni de nouvelle architecture si l'existante suffit.
Ne pas inventer de fichiers, modèles, routes ou permissions sans les avoir
vérifiés dans le code. Ne pas supposer. Si une information nécessaire manque,
la signaler précisément avant d'implémenter quoi que ce soit.

## 13. RAPPORT FINAL OBLIGATOIRE

```
ÉTAPE 0 — COMPTE LIVREUR

1. Fichiers analysés
2. Architecture existante trouvée (y compris : lequel de l'ENUM role ou du
   RBAC custom_role_id fait réellement autorité dans le code)
3. Modifications effectuées
4. Relation Utilisateur ↔ Livreur
5. Rôle livreur (choix ENUM vs RBAC dynamique, et pourquoi)
6. Permissions (dont : le système actuel supporte-t-il un scope "own" ?)
7. Sécurité tenant
8. Tests ajoutés/modifiés
9. Résultat des tests
10. Fichiers non modifiés volontairement
11. Problèmes restants
12. Recommandation pour l'ÉTAPE 1
```

Ne pas passer automatiquement à l'ÉTAPE 1. ARRÊTER après cette étape et
attendre une nouvelle instruction.