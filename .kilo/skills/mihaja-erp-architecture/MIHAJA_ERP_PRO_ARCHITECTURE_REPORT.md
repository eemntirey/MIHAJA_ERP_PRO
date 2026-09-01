# SOURCE DE RÉFÉRENCE OBLIGATOIRE — RAPPORT ARCHITECTURAL

Le skill `MIHAJA_ERP_PRO Architecture Guard V2` possède un document de référence :

```text
.kilocode/skills/mihaja-erp-architecture/MIHAJA_ERP_PRO_ARCHITECTURE_REPORT.md
```

Ce document représente l'état architectural documenté du projet au moment de son analyse.

## RÈGLE

Avant toute modification importante du projet, consulter ce rapport afin de comprendre :

* l'architecture générale ;
* la structure du projet ;
* les modèles ;
* les services ;
* les modules fonctionnels ;
* le multi-tenancy ;
* les règles Admin Tenant ;
* les abonnements ;
* les quotas ;
* les rôles ;
* les permissions ;
* l'authentification ;
* Web / Desktop / Shared ;
* la synchronisation ;
* les tests ;
* les bugs connus ;
* la priorité des corrections.

Le rapport ne doit PAS être considéré comme une autorisation de modifier le code.

Il est une source de contexte et de référence.

---

# UTILISATION DU RAPPORT

Avant toute modification :

```text
SKILL
  ↓
RAPPORT ARCHITECTURAL
  ↓
CODE ACTUEL
  ↓
COMPARAISON
  ↓
ANALYSE
```

Le code actuel reste la source de vérité pour déterminer l'état réel du projet.

Le rapport sert à :

1. comprendre l'architecture prévue ;
2. identifier les règles métier ;
3. identifier les contraintes existantes ;
4. repérer les écarts entre documentation et code ;
5. orienter l'audit ;
6. éviter les modifications qui contredisent l'architecture.

---

# RÈGLE DE CONFLIT

Si le rapport et le code actuel sont différents :

NE PAS choisir automatiquement le contenu du rapport.

Identifier explicitement :

```text
DOCUMENTATION
vs
CODE ACTUEL
```

Puis déterminer :

* si le code est une évolution volontaire ;
* si le rapport est obsolète ;
* si le code constitue une régression ;
* si une décision métier manque ;
* si une correction est nécessaire.

Ne jamais écraser automatiquement le code pour le faire correspondre au rapport.

---

# RÈGLE DE MISE À JOUR

Après une modification architecturale importante, le rapport peut devenir obsolète.

Dans ce cas :

1. signaler la divergence ;
2. ne pas modifier silencieusement le rapport ;
3. proposer la mise à jour documentaire ;
4. attendre l'autorisation ;
5. mettre à jour le rapport seulement après validation.

---

# BUG BACKLOG DE RÉFÉRENCE

Le rapport contient un backlog de bugs connus.

Ils doivent être utilisés comme contexte d'audit.

Ne pas supposer qu'un bug est encore présent uniquement parce qu'il apparaît dans le rapport.

Avant de le corriger :

```text
Rapport
   ↓
Recherche dans le code actuel
   ↓
Vérification
   ↓
Cause racine réelle
   ↓
Correction
```

Un bug déjà corrigé ne doit pas être corrigé une deuxième fois.

---

# PRIORITÉ DE CORRECTION

Le rapport identifie plusieurs problèmes critiques.

Pour toute intervention basée sur ce backlog, appliquer :

```text
P0 — Sécurité critique
C1
C2
C3
C4
C5
C7
C8
C9

P1 — Stabilité critique
C6

P2 — Haute sévérité
H*

P3 — Moyenne
M*

P4 — Basse
L*
```

Cette priorité doit toutefois être confirmée par l'état réel du code avant correction.

---

# RÈGLE SPÉCIALE MULTI-TENANT

Le rapport confirme l'architecture :

```text
Tenant
  ↓
Abonnement
  ↓
Limites
  ↓
Admin principal
  ↓
Utilisateurs
  ↓
Rôles
  ↓
Permissions
```

Cette chaîne constitue une architecture critique.

Toute modification touchant l'un de ces éléments doit obligatoirement vérifier les autres.

---

# RÈGLE SPÉCIALE QUOTAS

Les quotas sont calculés par :

```text
tenant_id
```

et non globalement.

Exemple :

```text
Tenant A → Plan 5 → 5 utilisateurs
Tenant B → Plan 3 → 3 utilisateurs
```

Le quota d'un Tenant ne doit jamais affecter celui d'un autre.

---

# RÈGLE SPÉCIALE TESTS

Le rapport indique :

```text
119 tests backend
```

Ne jamais supposer que ce résultat est encore valable sans exécution réelle des tests.

Le nombre indiqué dans le rapport est historique.

Toujours vérifier l'état réel avant de déclarer :

```text
PASS
```

---

# RÈGLE DE FIABILITÉ

Le rapport est une documentation de référence.

Il ne remplace jamais :

```text
le code actuel
les tests actuels
la base actuelle
la configuration actuelle
```

Utiliser les trois niveaux :

```text
DOCUMENTATION
+
CODE
+
TESTS
```

pour déterminer l'état réel du système.

---

# RÈGLE FINALE

Avant toute modification architecturale :

```text
CONSULTER LE SKILL
        ↓
CONSULTER LE RAPPORT
        ↓
INSPECTER LE CODE
        ↓
VÉRIFIER LES TESTS
        ↓
ANALYSER LES ÉCARTS
        ↓
PROPOSER
        ↓
STOP
        ↓
ATTENDRE AUTORISATION
        ↓
MODIFIER
        ↓
TESTER
        ↓
AUDITER
```

Aucune modification importante ne doit être réalisée uniquement sur la base du rapport.
