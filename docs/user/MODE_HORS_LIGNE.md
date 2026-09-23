# Mode hors-ligne (bureau / desk)

## Principe

L'application bureau embarque un backend Flask local (SQLite) qui permet de
travailler sans connexion au serveur central. À la reconnexion, un moteur de
réplication push/pull synchronise les données (conflits résolus en
« last-write-wins », détection d'idempotence via clés naturelles).

## Périmètre répliqué — V1

**Répliqués automatiquement** (push et pull) :

- Produits (`produit`)
- Clients (`client`)

**NON répliqués en V1** (registre `app/services/replication/entities.py`) :

- **Ventes** : la création d'une vente en mode hors-ligne reste locale au
  poste. Elle n'est **pas** poussée automatiquement vers le central, car la
  décrémentation de stock doit passer par `vente_service` (idempotence,
  facturation, comptabilité).

## Conséquence pour l'engagement « 1 semaine offline »

Le poste peut tenir **1 semaine hors-ligne pour la consultation et la gestion
du catalogue (produits + clients)**. Les ventes saisies hors-ligne sont
conservées localement mais leur remontée vers le central nécessite soit une
saisie manuelle, soit l'extension du registre de réplication aux ventes
(l'outbox est déjà générique — voir plan offline V2).

## Bonnes pratiques

- Se connecter au moins une fois par semaine pour la réplication
  (planificateur avec backoff : 30 s → 30 min).
- En cas de conflit, l'écran « Conflits » du desk permet de résoudre
  manuellement (garder la version locale ou distante).
- L'état de synchronisation est visible via le badge `SyncStatus`.
