# Plan — Version Desktop ERP Pro

> Objectif : transformer l'interface web actuelle en expérience desktop native, optimisée pour grands écrans, productivité élevée et workflows professionnels.

> **État actuel** : L'application Desktop (`desk/`) existe déjà en tant qu'application Electron 38. Elle partage le code React avec le frontend web. Ce document décrit les améliorations à apporter pour une expérience desktop complète.

---

## 1. PRINCIPES DIRECTEURS

- **Zéro perte mobile** : le responsive actuel reste intact.
- **Progressive Desktop Experience** : activée uniquement `min-width: 1280px`.
- **Performance first** : virtualisation des listes longues, lazy loading, memoization.
- **Cohérence métier** : chaque amélioration doit servir un cas d'usage ERP réel (saisie rapide, comparaison, audit).

---

## 2. LAYOUT GLOBAL

### 2.1 Barre latérale (Rail → Sidebar Desktop)

| Élément | État actuel | Version Desktop cible |
|---------|-------------|----------------------|
| Largeur | 260px (déjà implémenté dans DesktopLayout) | **260px** (icônes + labels) ✅ |
| Collapse | Oui | Oui, mémorisé dans `localStorage` |
| Recherche globale | Absente | **Input de recherche** en haut (CMD+K) |
| Favoris | Absents | **Section épinglée** (max 6 items) |
| Badges | Absents | **Badges** sur Ventes, Stocks, Factures (compteurs temps réel) |
| Profil | Footer | **En-tête** : avatar + nom + rôle + menu déroulant (profil, paramètres, logout) |

### 2.2 Header Desktop (Top Bar)

- **Titre de page** + **breadcrumb** dynamique.
- **Actions contextuelles** : créer, exporter, imprimer, filtrer.
- **Barre de recherche globale** (CMD+K) avec résultats instantanés (produits, clients, commandes, documents).
- **Notifications** : dropdown avec historique (commandes, alertes stock, paiements).
- **Indicateurs rapides** : stock critique, impayés, ventes du jour (small pills).

### 2.3 Zone principale

- **Largeur max** : `1440px` centrée avec marges latérales fluides.
- **Padding** : réduit à `16px` sur desktop (vs 24px actuel).
- **Bottom padding** : supprimé quand `ChatInput` n'est pas présent, sinon `24px`.

---

## 3. WORKSPACE MULTI-PANNEAUX (Split View)

### 3.1 Principe

Permettre l'affichage simultané de deux modules côte à côte, comme dans un desktop app.

- **Active sur** : `/products`, `/clients`, `/sales`, `/invoices`, `/stock`.
- **Trigger** : bouton "Ouvrir dans le panneau droit" sur chaque ligne de tableau.

### 3.2 Comportement

- **Gauche** : liste + filtres (scroll indépendant).
- **Droite** : détail / édition / formulaire (scroll indépendant).
- **Resizer** : barre redimensionnable (min 320px / max 60% viewport).
- **Mémorisation** : state persiste dans `localStorage` par module.

### 3.3 Cas d'usage

| Module | Panneau gauche | Panneau droit |
|--------|---------------|---------------|
| Produits | Liste + filtres | Détail produit / édition rapide |
| Clients | Liste + recherche | Fiche client + historique + créations |
| Ventes | Liste des ventes | Détail vente + paiement + livraison |
| Factures | Liste + statuts | Facture + règlement + export PDF |

---

## 4. NAVIGATION & PRODUCTIVITÉ

### 4.1 Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `CMD+K` / `CTRL+K` | Ouvrir la command palette |
| `CMD+N` | Nouvelle entrée (contexte courant) |
| `CMD+/` | Aide contextuelle |
| `CMD+E` | Exporter la vue courante (CSV/PDF) |
| `CMD+F` | Focus recherche globale |
| `CMD+B` | Toggle sidebar |
| `ALT+←/→` | Navigation historique |

### 4.2 Command Palette

- Inspirée de VS Code / Linear.
- Recherche floutée sur : routes, actions, clients, produits, commandes, documents.
- Actions rapides : "Nouvelle vente", "Nouveau client", "Exporter CA", "Générer rapport".
- Affichée en overlay plein écran, fermable par `ESC`.

### 4.3 Breadcrumbs + URL sync

- Chaque vue profonde expose un breadcrumb cliquable.
- L'URL reflète le chemin (ex: `/products/42/edit`).

---

## 5. ENRICHISSEMENT DES MODULES

### 5.1 Tableaux

- **Tri multicritères** : shift+clic sur les colonnes.
- **Redimensionnement colonnes** : drag sur les bordures d'en-tête.
- **Colonnes configurables** : show/hide + ordre (sauvé par profil).
- **Filtres avancés** : panneau coulissant avec opérateurs (>, <, =, contains) et sauvegarde de filtres nommés.
- **Sélection multiple** : checkbox + actions groupées (supprimer, exporter, changer statut).
- **Virtualisation** : pour listes > 200 items (`@tanstack/react-virtual` déjà installé).

### 5.2 Formulaires

- **Layout en grille** : 2 ou 3 colonnes sur desktop (vs 1 colonne actuelle).
- **Auto-save draft** : sauvegarde automatique toutes les 5s avec indicateur "Brouillon enregistré".
- **Validation inline** : erreurs sous les champs, pas d'alertes globales.
- **Steps wizard** : pour flux longs (création entreprise, import masse, clôture mensuelle).

### 5.3 Actions rapides (FAB Desktop)

- **FAB principal** : bouton flottant en bas à droite (hors chat IA) avec actions contextuelles.
- Menu : Nouvelle vente / Nouveau client / Nouvelle facture / Demande de stock.

---

## 6. INTELLIGENCE & VISUALISATION

### 6.1 Dashboard Desktop

- **Grille responsive** avec colonnes configurables (drag & drop des widgets).
- **Widgets agrandissables** : clic pour passer en mode plein écran.
- **Comparaisons** : widget "vs période précédente" avec toggle période (7j / 30j / 90j / année).
- **Alertes inline** : bannière discrète en haut du dashboard si stock critique ou impayés > seuil.

### 6.2 Rapports & Analytics

- **Mode rapport** : vue plein écran avec sidebar réduite et filtres persistants.
- **Annotations** : permettre d'ajouter des notes sur les graphiques (pour réunions).
- **Comparateur** : sélectionner 2 périodes et afficher les deltas côte à côte.

---

## 7. GESTION DOCUMENTAIRE & IMPRESSION

### 7.1 Prévisualisation PDF inline

- Panneau droit dédié pour prévisualiser devis / facture / bon de livraison sans quitter la page.
- Bouton "Imprimer" natif avec styles dédiés `@media print`.

### 7.2 Export batch

- Sélection multiple → export groupé (ZIP de PDFs ou CSV agrégé).

---

## 8. IA & ASSISTANT

### 8.1 Assistant conversationnel Desktop

- **Panel coulissant** depuis la droite (largeur 400px) au lieu d'une page dédiée.
- **Contextuel** : il connaît la page active et les filtres en cours.
- **Actions rapides** : boutons suggestés (ex: "Générer rapport CA du mois").

---

## 9. THÈME & ACCESSIBILITÉ

### 9.1 Dark mode

- **Toggle** dans le header desktop + sidebar.
- **Respect `prefers-color-scheme`** au premier chargement.
- **Contraste WCAG AA** vérifié sur tous les textes.

### 9.2 Accessibilité

- Focus visible sur tous les éléments interactifs.
- `aria-live` pour les notifications toast.
- Navigation au clavier complète dans tableaux et modales.

---

## 10. TECHNIQUE & PERFORMANCE

### 10.1 Architecture des composants

```
desk/src/
  components/
    layout/
      DesktopLayout.jsx          # Wrapper conditionnel (>=1280px)
      TopBar.jsx                 # Header desktop
      CommandPalette.jsx         # CMD+K overlay
      SplitView.jsx              # Container multi-panneaux
      ResizablePanel.jsx         # Panneau redimensionnable
      NotificationDropdown.jsx   # Notifications
    desktop/
      DataTable.jsx              # Tableau virtuel + tri + colonnes
      FilterPanel.jsx            # Filtres avancés
      FormGrid.jsx               # Grille de formulaire
      FAB.jsx                    # Actions rapides
```

### 10.2 State management

- **URL comme source de vérité** pour la navigation et les filtres.
- **React Context** conservé pour `auth`, `cart`, `darkMode`.
- **Zustand ou Jotai** pour le state desktop spécifique (split view, colonnes tableaux, favoris).

### 10.3 Lazy loading & Code splitting

- Chaque module lourd (graphiques, tables virtualisées, éditeur PDF) chargé à la demande.
- `React.lazy` + `Suspense` sur les routes.

### 10.4 Bundle & build

- Bundle analyzer en CI.
- Target : < 300KB gzipped pour le chunk principal.

---

## 11. PACKAGING OPTIONNEL (Desktop App)

### Options

| Option | Avantages | Inconvénients |
|--------|-----------|---------------|
| **Electron** | Écosystème mature, API Node, auto-update | Lourd (~150MB) |
| **Tauri** | Léger (<10MB), Rust backend, sécurité | Courbe d'apprentissage Rust |
| **PWA + Tauri** | Meilleur des deux mondes | Complexité de config |

**Recommandation** : Electron est déjà choisi et configuré dans `desk/package.json`.

### Fonctionnalités natives à exposer

- Impression directe (dialog système).
- Notifications système (commandes, alertes stock).
- Drag & drop de fichiers vers import CSV/PDF.
- Mode kiosque pour terminaux (caisse, stock).
- Menu natif (fichier, édition, affichage, aide).
- Gestion des fenêtres (minimize, maximize, close).
- Auto-update.

---

## 12. ROADMAP DE MISE EN ŒUVRE

### Phase 1 — Fondations (Semaines 1-2)

1. Améliorer `DesktopLayout` existant (sidebar collapse, mémorisation localStorage)
2. Ajouter `TopBar` avec breadcrumbs et actions contextuelles.
3. Implémenter `CommandPalette` (CMD+K).

### Phase 2 — Productivité (Semaines 3-4)

4. Composant `DataTable` (tri, redimensionnement colonnes, sélection multiple, virtualisation).
5. `FilterPanel` avancé + sauvegarde de filtres.
6. `SplitView` avec `ResizablePanel` sur Produits et Clients.
7. Raccourcis clavier globaux.

### Phase 3 — Intelligence (Semaines 5-6)

8. Dashboard widgets configurables + mode plein écran.
9. Prévisualisation PDF inline.
10. Assistant IA en panel coulissant contextuel.

### Phase 4 — Polish (Semaines 7-8)

11. Formulaires en grille + auto-save.
12. FAB desktop + actions rapides.
13. Accessibilité complète + tests WCAG.
14. Performance : virtualisation, lazy loading, bundle audit.

### Phase 5 — Fonctionnalités natives (Semaines 9-10)

15. Impression système native.
16. Notifications système.
17. Drag & drop fichiers.
18. Auto-update.

---

## 13. CRITÈRES DE SUCCÈS

- **Performance** : First Contentful Paint < 1s sur desktop (réseau 4G).
- **Productivité** : création d'une vente en < 3 clics depuis le dashboard.
- **Adoption** : 80% des utilisateurs utilisent la command palette dans les 2 semaines.
- **Stabilité** : 0 regression sur mobile/tablette.
- **Packaging** : application desktop fonctionnelle sur Windows, macOS, Linux.

---

## 14. PROCHAINES ÉTAPES

1. Valider ce plan avec le product owner.
2. Choisir les bibliothèques (virtualisation, resizer, command palette).
3. Maquetter les écrans clés (Dashboard, Liste produits, Split view).
4. Démarrer la Phase 1.
