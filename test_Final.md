# TEST FINAL — Parcours réels sur localhost (18/09/2026)

## Contexte du test

Test réalisé « comme un vrai utilisateur » sur les applications servies en local :

| Application | URL | État au moment du test |
|---|---|---|
| Backend Flask | http://localhost:5000 | En marche (`/health` → healthy) |
| Frontend web (React) | http://localhost:3000 | Démarré puis **crashé 2 fois** pendant le test, relancé |
| Super-admin (Vite) | http://localhost:3002 | Démarré pour le test |
| Desk (Electron) | :3001 | Non testé (lancement `npm run electron:dev` interactif, hors périmètre navigateur) |

Base : PostgreSQL `erp` sur `localhost:55432` (1 tenant « TOVOHERY », abonnement « gratuit » ACTIF).

Comptes de test créés pour l'occasion (les comptes démo du README ne répondaient à aucun mot de passe documenté) : `admin_test@mihaja.test`, `user_test@mihaja.test`, `sales_test@mihaja.test`, `sa_test@mihaja.test` — mot de passe `Test1234!`.

---

## 🔴 Bloquants (un parcours réel s'arrête net)

### B1. Impossible de créer une vente depuis l'interface web
- **Reproduction** : Ventes → « + Nouvelle vente » → client sélectionné, produit `Riz Makalioka 25kg` sélectionné (prix et TVA s'auto-remplissent correctement), clic sur « Créer ».
- **Résultat** : rien ne se passe. Aucune requête POST n'est envoyée au serveur. L'erreur de validation brute s'affiche dans la cellule du produit :
  > `lignes[0].produit_id must be a 'number' type, but the final value was: NaN (cast from the value "")`
- **Cause racine (trouvée)** : `web/frontend/src/pages/Sales.jsx`, ligne ~321. Le `<select>` du produit reçoit `onChange={handleProduitChange(...)}` qui **écrase** le `onChange` généré par `{...register('lignes.<i>.produit_id')}` de react-hook-form. React-hook-form n'apprend donc jamais la valeur choisie : elle reste `''` (d'où le `NaN` au cast). Le même problème existe sur le `<select>` client plus haut dans le formulaire.
- **Confirmation** : la même vente envoyée directement à l'API (`POST /api/v1/ventes`) est **acceptée** : vente créée, stock décrémenté de 50 → 48, dashboard mis à jour (CA 330 000 MGA). Le backend fonctionne ; c'est le formulaire qui est cassé.
- **Pourquoi c'est grave** : la fonctionnalité n°1 d'un ERP commercial (vendre) est inutilisable par la seule UI web.

### B2. Le bouton de déconnexion est introuvable / sans effet
- **Reproduction** : connecté (admin, dashboard, sidebar complète), recherche du bouton « Se déconnecter » (présent dans l'accessibility tree initial) puis tentative réelle de déconnexion.
- **Résultat** : aucun élément cliquable ne correspond après interaction ; navigation forcée vers `/login` montre que la session reste active (l'utilisateur est toujours identifié). Le seul moyen « réel » de changer de compte est de vider les cookies.
- **Impact** : sur un poste partagé (contexte grossiste / comptoir), l'utilisateur suivant hérite de la session précédente.

### B3. Le serveur frontend s'arrête tout seul en cours d'utilisation
- **Reproduction** : simple navigation entre pages pendant le test.
- **Résultat** : le process CRA (port 3000) a **disparu deux fois** sans trace d'erreur dans le log (`/tmp/cra_3000.log` se termine sur « webpack compiled successfully » + un warning de dépréciation `util._extend`). Le navigateur affiche alors `chrome-error://chromewebdata`.
- **Hypothèses à instruire** : OOM du process node sous Windows, conflit de watchers, ou arrêt du terminal parent. À reproduire avec un log verbeux.

---

## 🟠 Incohérences fonctionnelles (marche réelle)

### F1. Vitrine publique : « Aucun vendeur n'est actif » alors que l'abonnement est ACTIF
- Accueil public (http://localhost:3000) : « Aucun produit disponible pour le moment. Aucun vendeur n'est actif. »
- Or le tenant TOVOHERY a un abonnement `ACTIF` jusqu'au 18/10/2026 et un produit publié.
- Cause (côté code, pas un bug en soi) : la vitrine exige **trois** conditions cumulatives — abonnement actif **+ compte marchand Papi configuré** + toggle `vitrine_enabled` (voir `_get_active_tenant_ids()` / `Tenant.is_vitrine_active()`).
- **Problème de marche réelle** : nulle part dans l'UI (dashboard admin, page abonnement, paramètres paiement) ce prérequis n'est expliqué. Un commerçant qui souscrit un abonnement et publie ses produits voit sa vitrine vide **sans jamais savoir pourquoi**. Il faut un état « vitrine : désactivée — raisons : Papi non configuré / toggle off » dans le dashboard.
- Accessoirement, le libellé « Aucun vendeur n'est actif » est trompeur : le vendeur EST actif, il n'est juste pas « exposé ».

### F2. La colonne « CODE » des produits affiche l'ID interne au lieu de la référence
- **Reproduction** : Produits → création du produit `RIZ-25` (champ « RÉFÉRENCE » rempli) → la table affiche `CODE = 1`.
- Cause : `web/frontend/src/pages/Products.jsx` ligne 190 : `accessor: (row) => row.code_barre || row.id`. Quand le code-barre est vide (mode « Manuel » sans saisie), la colonne tombe sur l'ID SQL.
- **Impact marche réelle** : l'opérateur croit que le code produit est « 1 » ; la référence métier `RIZ-25` n'apparaît **nulle part** dans la table. Dans un entrepôt, scanner/invoquer le mauvais identifiant est une erreur classique de saisie. La colonne devrait afficher la référence (`reference`) et/ou un vrai code généré.

### F3. Aucune facture générée après une vente
- Une vente existe (`VENT-20260918035615-8352`, client, montants corrects) mais la page Factures reste vide (« 0 facture »). Il faut créer la facture manuellement.
- **Impact** : double saisie, risque de ventes livrées sans facture ; le README promet pourtant « Chaque commande génère un QR code » et un lien vente→facture naturel.

### F4. Le CA du mois compte les ventes non payées
- La vente créée est au statut `en_attente` (non payée), mais le dashboard affiche « CA du mois : 330 000 MGA » et « 330 000 MGA générés ».
- **Impact** : le chiffre d'affaires présenté n'est pas un CA encaissé. Pour une marche réelle, il faut distinguer CA facturé / CA encaissé, ou au minimum étiqueter l'indicateur (« CA facturé »).

### F5. TVA incohérente entre produit et formulaire de vente
- Le produit est enregistré avec `taux_tva = 10` (valeur par défaut du backend), mais une nouvelle ligne de vente démarre à 20 %.
- L'écart se corrige dès qu'on choisit le produit (le champ TVA se met à 10), mais si l'utilisateur crée d'abord la ligne puis choisit le produit, ou supprime/re-choisit, il peut vendre avec une TVA erronée. La TVA par défaut d'une vente devrait venir du produit (ou d'un paramètre tenant), pas d'une constante 20 % dans `saleLineSchema`.

### F6. Suivi public de commande : « Commande non trouvee » pour une référence de vente
- Page `/suivi` : saisie de la référence `VENT-20260918035615-8352` (réelle, visible dans Ventes) → « Commande non trouvee » (message sans accents, au passage).
- C'est cohérent techniquement (le suivi ne concerne que les commandes e-commerce publiques), mais **incompréhensible pour un client** : deux familles de références coexistent sans explication, et l'erreur de typographie affiche le manque de soin (« trouvee »).

### F7. La page Abonnement du dashboard affiche « 0 » sans unité ni contexte
- Carte ABONNEMENT : plan « gratuit », statut ACTIF, date de fin, puis un mystérieux « **0** » isolé. Impossible de savoir s'il s'agit d'utilisateurs restants, de produits, de jours… Sur le plan gratuit (max 3 utilisateurs / 50 produits / 100 clients), afficher les compteurs réels vs limites serait le comportement attendu.

### F8. Rate-limit de login : 5 tentatives / 5 min **par IP**, réussites comprises
- Confirmé : 5 appels (échecs) puis 429 sur le 6ᵉ. Plus tôt dans le test, une connexion **réussie** a consommé le quota et bloqué les connexions suivantes (dont le user_test et le super-admin) avec le message générique « Trop de requêtes ».
- **Impact marche réelle** : tout un open space / une fatigue de proxy NAT → 5 connexions et l'entreprise entière est verrouillée 5 minutes, sans distinction par compte. Compter les succès dans le quota et ne pas distinguer par login est à revoir. L'UI web, elle, n'affiche même pas le message 429 (voir F11).

### F9. Champs de formulaire « hors sol » pour Madagascar
- Formulaire client : champs `SIRET` et « TVA INTRACOMMUNAUTAIRE » avec placeholders français (« 123 456 789 00010 », « FRXX 123456789 »), pays par défaut « Madagascar ». Ces identifiants n'existent pas à Madagascar (NIF/STAT/RCS locaux attendus).
- Type de vente : le libellé annonce « Auto-dérivé du client (grossiste, semi-grossiste, revendeur) » mais le client de test est un « Particulier » → type forcé « Détail », l'information ne se retrouve nulle part si l'on change le client après coup.

### F10. Comptes démo non fonctionnels / documentation obsolète
- Le README affiche des comptes (`distrifood@erp.com`, `grosriz@erp.com`) et une phrase incohérente : « mot de passe : défini par l'utilisateur lors du premier accès / changé au premier boot ». En base, ces comptes n'existent pas ; les seeds réels (`seed_mada_business.py`) utilisent d'autres emails. Aucun mot de passe documenté ne fonctionne sur les comptes présents (`superadmin@mihaja.mg`, `lokomada@gmail.com`).
- **Impact** : premier démarrage réel = impossible de se connecter sans aller lire les scripts de seed.

### F11. Erreurs backend invisibles dans l'UI de connexion
- Le 429 (F8) est retourné au navigateur, mais l'écran de connexion ne montre **aucun message** : l'utilisateur clique « Se connecter » et il ne se passe rien. Idem pour les erreurs de validation serveur : l'UI devrait au minimum afficher le message reçu.

### F12. Incohérence de langue des routes (et vieillesse du titre)
- Les modules ERP sont en anglais (`/products`, `/sales`, `/invoices`, `/inventory`, `/suppliers`, `/hr`) alors que la fiche produit publique est en français (`/produits/:id`) et toute l'UI est française. Un utilisateur francophone qui tente `/produits` retombe sur l'accueil publique sans explication.
- Le titre de l'onglet est codé en dur : `TIA INFO WHOLESALE / ERP PRO` (`web/frontend/public/index.html`), un nom de société tiers dans une application multi-tenant — chaque tenant devrait voir le sien.

---

## 🟡 Points positifs constatés

- Backend stable et rapide : `/health`, `/ready`, `/docs` (Swagger) OK ; authentification cookie fonctionnelle ; messages d'erreur API propres et en français.
- Isolation multi-tenant effective (filtre `tenant_id`), CRUD produits/clients OK via API et via UI (produit et client créés depuis l'UI sans accroc).
- Décrément automatique du stock après vente API (50 → 48) : la logique métier de base est saine.
- Page 403 propre et explicite pour l'accès `/super-admin` depuis un compte ADMIN (« Aucune redirection silencieuse ») — bon choix produit.
- Console super-admin : connexion, dashboard, liste des tenants et abonnements cohérents avec la base.

## 🔁 Résumé des priorités

1. **Corriger le formulaire de vente** (`Sales.jsx`, conflit `register()`/`onChange`) — B1, bloquant.
2. **Réparer la déconnexion** — B2, sécurité/UX.
3. **Diagnostiquer le crash du serveur CRA** — B3, environnement.
4. **Expliquer la vitrine publique** (état + raisons de non-exposition) — F1.
5. **Colonne CODE = référence métier**, pas l'ID SQL — F2.
6. Facturation auto à la vente (F3), CA encaissé vs facturé (F4), TVA du produit (F5), quota login par compte et non par IP (F8), message d'erreur login affiché (F11).
