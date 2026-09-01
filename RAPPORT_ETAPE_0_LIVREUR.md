# ÉTAPE 0 — RAPPORT

## 1. Architecture réelle trouvée

Le projet MIHAJA_ERP_PRO utilise :
- **Flask + SQLAlchemy** avec Flask-Migrate installé mais **sans répertoire `migrations/`** ni scripts Alembic réels.
- **SQLite** comme base principale (`sqlite:///erp.db` par défaut, tests en `:memory:`).
- `db.create_all()` comme mécanisme principal de création de schéma en dev/test.
- Multi-tenant par `tenant_id` sur `BaseTenantModel`, avec filtrage global ORM via event listener (`app/security/tenant.py`).
- RBAC double : rôles système enum (`Role`) + rôles personnalisables (`RoleModel` + `Permission`).

## 2. Modèle Livreur actuel

`web/backend/app/models/livreur.py`
- Hérite de `BaseTenantModel` → `tenant_id` NOT NULL.
- Champs : `nom`, `prenom`, `telephone`, `email`, `numero_permis`, `date_embauche`, `statut`, `vehicule_id`.
- Relations : `vehicule`, `itineraires`, `livraisons`.
- **Avant cette étape** : aucune relation avec `Utilisateur`.

## 3. Modèle Utilisateur actuel

`web/backend/app/models/utilisateur.py`
- Hérite de `BaseModel` → `tenant_id` nullable.
- Champs : `username`, `email`, `password_hash`, `nom`, `prenom`, `telephone`, `mobile`, `role`, `custom_role_id`, `statut`, `admin_statut`, `device_id`, `is_principal_admin`, `employee_key_hash`, `employee_key_status`, `last_login`, `last_ip`.
- Relations : `tenant`, `clients`, `ventes`, `created_products`, `updated_products`, `custom_role`.

## 4. Relation existante ou ajoutée

**Ajoutée** dans `web/backend/app/models/livreur.py` :
```python
utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=True, index=True, unique=True)
utilisateur = db.relationship('Utilisateur', backref='livreur_profile', foreign_keys='Livreur.utilisateur_id')
```

Architecture métier :
```
Utilisateur (compte) 0..1 ↔ 1 Livreur (fiche)
```

Un livreur peut exister sans compte (`utilisateur_id` NULL). Un utilisateur ne peut être associé qu'à un seul livreur (UNIQUE).

## 5. Gestion du rôle livreur

- Ajouté `LIVREUR = 'livreur'` à l'enum `Role` dans `web/backend/app/models/utilisateur.py`.
- Ajouté `Role.LIVREUR: 30` dans `ROLE_HIERARCHY` (`web/backend/app/security/roles.py`).
- Ajouté dans les seeds :
  - `web/backend/app/__init__.py` (`_seed_roles`)
  - `web/backend/scripts/seed_roles.py`

## 6. Gestion des permissions

Ajouté dans `web/backend/app/security/permission_matrix.py` :
- `PERMISSION_DEFINITIONS` : `delivery.view`, `delivery.update`.
- `ROLE_PERMISSIONS['livreur']` : `delivery.view`, `delivery.update`, `profile.view`, `profile.update`.

Le rôle `livreur` n'a **pas** de permissions admin, manager, stock, etc.

## 7. Gestion du scope self

Le système actuel n'a pas de mécanisme générique de scope `self`. Implémenté le minimum nécessaire :

Nouveaux endpoints dans `web/backend/app/api/v1/livraisons.py` :
- `GET /livreurs/moi` — profil livreur du compte connecté.
- `GET /livreurs/moi/livraisons` — livraisons du livreur connecté uniquement.
- `GET /livreurs/moi/livraisons/<id>` — détail d'une livraison (vérification propriétaire).
- `POST /livreurs/moi/livraisons/<id>/suivi` — ajout de suivi sur ses propres livraisons.
- `POST /livreurs/moi/livraisons/<id>/statut` — changement de statut sur ses propres livraisons.

Service `LivraisonService` :
- `get_for_livreur(livreur_id)` — filtre par `livreur_id`.
- `get_for_livreur_by_id(livreur_id, livraison_id)` — vérifie la propriété.

## 8. Protection cross-tenant

- Dans l'endpoint d'association `POST /livreurs/<id>/associer-utilisateur` : vérification explicite `Livreur.tenant_id == Utilisateur.tenant_id`.
- L'association bypass le filtrage tenant global avec `_skip_tenant_filter=True` pour récupérer l'utilisateur cible.
- Les endpoints `/moi/livraisons` ne voient que les livraisons du livreur connecté, donc isolation tenant implicite.

## 9. Contraintes d'intégrité

- **DB** : `UNIQUE INDEX idx_livreur_utilisateur_id ON livreurs (utilisateur_id)`.
  - Sur SQLite, NULL ≠ NULL : plusieurs livreurs sans compte coexistent sans problème.
  - Un utilisateur ne peut être associé qu'à un seul livreur.
- **Service/API** : vérification `existing = Livreur.query.filter(Livreur.utilisateur_id == utilisateur_id, Livreur.id != livreur.id).first()` avant association.
- **Event listener** (pré-existant dans le working tree) : `_livreur_check_tenant_consistency` valide la cohérence des `tenant_id` lors des inserts/updates.

## 10. Migrations

Aucun système de migration Alembic opérationnel dans le projet. Ajouté un script dédié :

`web/backend/scripts/migrate_livreur_association.py`
- `ALTER TABLE livreurs ADD COLUMN utilisateur_id INTEGER REFERENCES utilisateurs(id)`
- `CREATE UNIQUE INDEX idx_livreur_utilisateur_id ON livreurs (utilisateur_id)`
- Testé avec succès sur `instance/erp.db` (SQLite).

Pour MySQL, la syntaxe `ALTER TABLE ... ADD COLUMN` et `CREATE UNIQUE INDEX` sont compatibles. Le caractère nullable + unique permet à plusieurs livreurs d'avoir `NULL`.

## 11. Tests ajoutés

`web/backend/tests/test_livreur_compte.py` — 7 tests :

| Test | Description |
|------|-------------|
| `test_a_livreur_sans_compte` | Livreur créé sans `utilisateur_id` → SUCCESS |
| `test_b_association_valide` | Utilisateur Tenant A + Livreur Tenant A → SUCCESS |
| `test_c_association_cross_tenant` | Utilisateur Tenant A + Livreur Tenant B → REFUS (403) |
| `test_d_compte_deja_associe` | Même utilisateur sur 2 livreurs → REFUS (409) |
| `test_e_isolation_livraisons` | Livreur A voit ses livraisons, pas celles de B |
| `test_f_isolation_tenant` | Livreur Tenant A ne peut accéder aux livraisons Tenant B |
| `test_g_regression_roles_existants` | Les rôles existants continuent de fonctionner |

## 12. Résultats des tests

```
tests/test_livreur_compte.py::TestLivreurCompte::test_a_livreur_sans_compte PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_b_association_valide PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_c_association_cross_tenant PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_d_compte_deja_associe PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_e_isolation_livraisons PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_f_isolation_tenant PASSED
tests/test_livreur_compte.py::TestLivreurCompte::test_g_regression_roles_existants PASSED
```

Tests de régression également validés :
- `tests/test_roles_presets.py` : 13 passed
- `tests/test_auth.py` : 2 passed
- `tests/test_critical_api.py` : 11 passed

## 13. Fichiers modifiés

| Fichier | Nature du changement |
|---------|---------------------|
| `web/backend/app/models/utilisateur.py` | Ajout `LIVREUR` dans enum `Role` |
| `web/backend/app/models/livreur.py` | Ajout `utilisateur_id`, relation, event listener (partiellement pré-existant) |
| `web/backend/app/security/roles.py` | Ajout `LIVREUR: 30` dans `ROLE_HIERARCHY` |
| `web/backend/app/security/permission_matrix.py` | Ajout permissions `delivery.view/update` + rôle `livreur` |
| `web/backend/app/__init__.py` | Ajout rôle `livreur` dans `_seed_roles` |
| `web/backend/scripts/seed_roles.py` | Ajout rôle `livreur` dans le seed |
| `web/backend/app/services/livraison_service.py` | Ajout `get_by_user`, `get_for_livreur`, `get_for_livreur_by_id` |
| `web/backend/app/api/v1/livraisons.py` | Ajout endpoints livreur-scoped + association |
| `web/backend/tests/test_livreur_compte.py` | Nouveau fichier de tests |
| `web/backend/scripts/migrate_livreur_association.py` | Nouveau script de migration |
| `web/frontend/src/pages/Delivery.jsx` | Ajout UI d'association compte |
| `shared/services/api.js` | Ajout méthodes `livreurService` (moi, livraisons, associer) |
| `shared/contexts/AuthContext.jsx` | Redirection rôle `livreur` vers `/delivery` |

## 14. Fichiers volontairement non modifiés

- `web/backend/app/models/livraison.py`
- `web/backend/app/models/suivi_livraison.py`
- `web/backend/app/models/base.py`
- `web/backend/app/services/livraison_service.py` (workflow `TRANSITIONS_AUTORISEES`)
- `web/backend/app/api/v1/livraisons.py` (endpoints existants : `POST /<id>/avancer`, `POST /<id>/suivi`, etc.)
- Tous les modules stock, facture, commande client, abonnement, RH, comptabilité, etc.

## 15. Problèmes découverts

1. **Absence de migrations Alembic** : le projet utilise `flask-migrate` mais n'a pas de répertoire `migrations/`. Les évolutions de schéma reposent sur `db.create_all()` en dev/test et sur des scripts manuels en production.
2. **Working tree pollué** : de nombreuses modifications non commitées existaient avant cette étape, rendant difficile la distinction entre changements pré-existants et nouveaux.
3. **Event listener SQLAlchemy global** : le filtrage tenant global (`do_orm_execute`) intercepte toutes les requêtes. Pour les opérations cross-tenant légitimes (ex: association), il faut utiliser `execution_options(_skip_tenant_filter=True)`.

## 16. Points nécessitant décision

1. **Abonnement pour livreurs** : le décorateur `tenant_required` applique la vérification d'abonnement à tous les rôles hors `SUPER_ADMIN`, `USER`, `ACCOUNTANT`. Un livreur sera donc bloqué si le tenant n'a pas d'abonnement actif. Décision à prendre : faut-il exempter le rôle `livreur` de cette vérification ?
2. **Scope livraisons** : les endpoints existants `GET /livraisons` et `GET /livraisons/<id>` restent accessibles aux admins/managers et voient toutes les livraisons du tenant. C'est volontaire. Si besoin, un scope "livreur uniquement" pour admin pourrait être ajouté plus tard.
3. **Permissions manquantes** : les endpoints de livraison existants ne vérifient pas les permissions via `@permission_required`. Seuls les nouveaux endpoints livreur-scoped sont protégés. Harmoniser l'ensemble des endpoints livraison avec le système de permissions pourrait être une évolution future.

## 17. Préparation recommandée pour l'ÉTAPE 1

- Mettre en place un système de migrations Alembic propre (initialiser `migrations/`, versionner le schéma).
- Définir si le rôle `livreur` nécessite un abonnement actif pour se connecter.
- Si le scope `self` doit être généralisé, concevoir un mécanisme réutilisable plutôt que des endpoints dédiés par rôle.
- Documenter les endpoints `/livreurs/moi/*` dans la spec API.
