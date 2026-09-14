// web/frontend/src/i18n/translations.js
// Dictionnaires de traduction FR / MG (malagasy).
// Source unique pour l'i18n léger de l'application (LanguageContext).
// Convention : clés hiérarchiques 'section.nom', interpolation {variable}.
// Les libellés de navigation sont traduits par chemin (nav.<path>) afin de ne
// PAS modifier shared/navConfig.js (source unique partagée avec l'app desk).

export const FR_CODE = 'fr';
export const MG_CODE = 'mg';
export const DEFAULT_LANGUAGE = FR_CODE;

export const LANGUAGES = [
  { code: FR_CODE, label: 'Français', short: 'FR', flag: '🇫🇷' },
  { code: MG_CODE, label: 'Malagasy', short: 'MG', flag: '🇲🇬' },
];

export const SUPPORTED_LANGUAGES = LANGUAGES.map((l) => l.code);

export const translations = {
  fr: {
    // --- Accès refusé explicite (P1-3 : jamais de redirection silencieuse) ---
    'accessDenied.title': 'Module non accessible',
    'accessDenied.body': 'La page {path} nécessite {module} et la permission ({permissions}). Contactez votre administrateur ou changez d\u2019abonnement. Aucune redirection silencieuse n\u2019a eu lieu.',
    // --- Commun ---
    'common.language': 'Langue',
    'common.home': 'Accueil',
    'common.profile': 'Profil',
    'common.userProfile': 'Profil utilisateur',
    'common.subscription': 'Abonnement',
    'common.paymentSettings': 'Paramètres de paiement',
    'common.lightMode': 'Mode clair',
    'common.darkMode': 'Mode sombre',
    'common.logout': 'Se déconnecter',
    'common.notifications': 'Notifications',
    'common.markAllRead': 'Tout marquer comme lu',
    'common.noNotifications': 'Aucune notification',
    'common.justNow': "à l'instant",
    'common.minutesAgo': 'il y a {n} min',
    'common.hoursAgo': 'il y a {n} h',
    'common.modules': 'Modules',
    'common.modulesMenu': 'Menu des modules',
    'common.closeMenu': 'Fermer le menu',
    'common.favorites': 'Favoris',
    'common.search': 'Recherche',
    'common.searchPlaceholder': 'Rechercher pages, actions, clients, produits…',
    'common.globalSearch': 'Recherche globale',
    'common.noResults': 'Aucun résultat',
    'common.action': 'Action',
    'common.page': 'Page',
    'common.palette': 'Palette de commandes',
    'common.loading': 'Chargement...',

    // --- Groupes de navigation (navConfig::NAV_GROUPS) ---
    'navGroup.Piloter': 'Piloter',
    'navGroup.Opérations': 'Opérations',
    'navGroup.Gestion': 'Gestion',
    'navGroup.Admin': 'Admin',

    // --- Navigation (par chemin — navConfig::NAV_ITEMS) ---
    'nav./dashboard': 'Tableau de bord',
    'nav./products': 'Produits',
    'nav./clients': 'Clients',
    'nav./sales': 'Ventes',
    'nav./invoices': 'Factures',
    'nav./payments': 'Paiements',
    'nav./inventory': 'Stock',
    'nav./suppliers': 'Fournisseurs',
    'nav./purchases': 'Achats',
    'nav./delivery': 'Livraisons',
    'nav./hr': 'Ressources humaines',
    'nav./accounting': 'Comptabilité',
    'nav./documents': 'Documents',
    'nav./ai': 'Assistant IA',
    'nav./super-admin': 'Administration',
    'nav./users': 'Utilisateurs',
    'nav./roles': 'Rôles',
    'nav./permissions': 'Permissions',

    // --- Actions contextuelles (TopBar / CommandPalette) ---
    'action./products': 'Nouveau produit',
    'action./clients': 'Nouveau client',
    'action./sales': 'Nouvelle vente',
    'action./invoices': 'Nouvelle facture',
    'action./inventory': 'Entrée de stock',
    'action./suppliers': 'Nouveau fournisseur',
    'action./purchases': 'Nouvel achat',
    'action./accounting': 'Nouvelle écriture',
    'action./documents': 'Nouveau document',
    'action./hr': 'Nouvel employé',
    'action./delivery': 'Nouvelle livraison',
    'action.qa-ca': 'Exporter le chiffre d’affaires',

    // --- Indicateurs TopBar ---
    'indicator.stock': 'Stock critique',
    'indicator.invoices': 'Impayés',
    'indicator.sales': 'Ventes du jour',

    // --- TopBar ---
    'topbar.expand': 'Déplier la barre',
    'topbar.collapse': 'Réduire la barre',
    'topbar.toggleSidebar': 'Basculer la barre latérale',
    'topbar.breadcrumb': "Fil d'Ariane",
    'topbar.logout': 'Déconnexion',

    // --- Rail / divers ---
    'rail.mainNav': 'Navigation principale',
    'common.clickToOpen': 'Cliquer pour ouvrir',
    'common.user': 'Utilisateur',

    // --- Sidebar desktop ---
    'sidebar.pin': 'Épingler aux favoris',
    'sidebar.unpin': 'Retirer des favoris',
    'sidebar.searchPlaceholder': 'Rechercher…',

    // --- Modale limite de plan (App.js) ---
    'planLimit.title': 'Limite du plan atteinte',
    'planLimit.close': 'Fermer',
    'planLimit.change': "Modifier mon abonnement",
    // --- Abonnement ---
    'subscription.upgradePlan': 'Passer à un plan payant',
  },

  mg: {
    // --- Accès refusé explicite (P1-3 : jamais de redirection silencieuse) ---
    'accessDenied.title': 'Tsy afaka miditra',
    'accessDenied.body': 'Ny pejy {path} dia mitaky {module} sy ny alalana ({permissions}). Mifandraisa amin\u2019ny mpitantana na ovay ny abonema. Tsy nisy famerenana mangina.',
    // --- Commun ---
    'common.language': 'Fiteny',
    'common.home': 'Fandraisana',
    'common.profile': 'Profila',
    'common.userProfile': 'Profila mpampiasa',
    'common.subscription': 'Abonema',
    'common.paymentSettings': 'Fandrindrana ny fandoavana',
    'common.lightMode': 'Endrika mazava',
    'common.darkMode': 'Endrika maizina',
    'common.logout': 'Hivoaka',
    'common.notifications': 'Fampandrenesana',
    'common.markAllRead': 'Mariho ho vakiana rehetra',
    'common.noNotifications': 'Tsy misy fampandrenesana',
    'common.justNow': 'izao avy hatrany',
    'common.minutesAgo': '{n} min lasa izay',
    'common.hoursAgo': '{n} ora lasa izay',
    'common.modules': 'Fizarana',
    'common.modulesMenu': 'Menio fizarana',
    'common.closeMenu': 'Hidiana ny menio',
    'common.favorites': 'Favorits',
    'common.search': 'Fikarohana',
    'common.searchPlaceholder': 'Karohy pejy, hetsika, mpanjifa, vokatra…',
    'common.globalSearch': 'Fikarohana manerana',
    'common.noResults': 'Tsy misy valiny',
    'common.action': 'Hetsika',
    'common.page': 'Pejy',
    'common.palette': 'Lisitry ny baiko',
    'common.loading': 'Eo am-pamakiana...',

    // --- Groupes de navigation (navConfig::NAV_GROUPS) ---
    'navGroup.Piloter': 'Fanaraha-maso',
    'navGroup.Opérations': 'Hetsika',
    'navGroup.Gestion': 'Fandrindrana',
    'navGroup.Admin': 'Admin',

    // --- Navigation (par chemin — navConfig::NAV_ITEMS) ---
    'nav./dashboard': 'Tabilao fanaraha-maso',
    'nav./products': 'Vokatra',
    'nav./clients': 'Mpanjifa',
    'nav./sales': 'Varotra',
    'nav./invoices': 'Faktora',
    'nav./payments': 'Fandoavana',
    'nav./inventory': 'Tahiry',
    'nav./suppliers': 'Mpamatsy',
    'nav./purchases': 'Fividianana',
    'nav./delivery': 'Fanaterana',
    'nav./hr': 'Mpiasa',
    'nav./accounting': 'Kaontabilita',
    'nav./documents': 'Antontan-taratasy',
    'nav./ai': 'Mpanampy IA',
    'nav./super-admin': 'Fitantanana',
    'nav./users': 'Mpampiasa',
    'nav./roles': 'Anjara asa',
    'nav./permissions': 'Alalana',

    // --- Actions contextuelles (TopBar / CommandPalette) ---
    'action./products': 'Vokatra vaovao',
    'action./clients': 'Mpanjifa vaovao',
    'action./sales': 'Varotra vaovao',
    'action./invoices': 'Faktora vaovao',
    'action./inventory': 'Fampidirana tahiry',
    'action./suppliers': 'Mpamatsy vaovao',
    'action./purchases': 'Fividianana vaovao',
    'action./accounting': 'Soratra vaovao',
    'action./documents': 'Antontan-taratasy vaovao',
    'action./hr': 'Mpiasa vaovao',
    'action./delivery': 'Fanaterana vaovao',
    'action.qa-ca': 'Havoaka ny vola miditra',

    // --- Indicateurs TopBar ---
    'indicator.stock': 'Tahiry tena ambany',
    'indicator.invoices': 'Tsy voaloa',
    'indicator.sales': 'Varotra androany',

    // --- TopBar ---
    'topbar.expand': 'Hanitarana ny bara',
    'topbar.collapse': 'Hanalefahana ny bara',
    'topbar.toggleSidebar': 'Hamandrika ny bara anila',
    'topbar.breadcrumb': 'Lalana',
    'topbar.logout': 'Fivoahana',

    // --- Rail / divers ---
    'rail.mainNav': 'Fitetezana voalohany',
    'common.clickToOpen': 'Tsindrio hanokafana',
    'common.user': 'Mpampiasa',

    // --- Sidebar desktop ---
    'sidebar.pin': 'Apetraho amin’ny favorits',
    'sidebar.unpin': 'Esory amin’ny favorits',
    'sidebar.searchPlaceholder': 'Hikaroka…',

    // --- Modale limite de plan (App.js) ---
    'planLimit.title': "Fetra tratra amin'ny abonema",
    'planLimit.close': 'Hidiana',
    'planLimit.change': 'Hanova ny abonema',
    // --- Abonnement ---
    'subscription.upgradePlan': 'Miakatra ho drafitra mandoa vola',
  },
};