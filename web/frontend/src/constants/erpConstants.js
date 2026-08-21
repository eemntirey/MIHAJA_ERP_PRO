export const CLIENT_TYPES = [
  { value: 'boutique', label: 'Boutique' },
  { value: 'epicerie', label: 'Épicerie' },
  { value: 'revendeur', label: 'Revendeur' },
  { value: 'semi_grossiste', label: 'Semi-grossiste' },
  { value: 'grossiste', label: 'Grossiste' },
  { value: 'supermarche', label: 'Supermarché' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'hotel', label: 'Hôtel' },
  { value: 'entreprise', label: 'Entreprise' },
  { value: 'institution', label: 'Institution' },
  { value: 'particulier', label: 'Particulier' },
];

export const CLIENT_TYPE_LABELS = CLIENT_TYPES.reduce((acc, t) => ({ ...acc, [t.value]: t.label }), {});

export const SUPPLIER_TYPES = [
  { value: 'producteur_local', label: 'Producteur local' },
  { value: 'importateur', label: 'Importateur' },
  { value: 'distributeur', label: 'Distributeur' },
  { value: 'grossiste', label: 'Grossiste' },
  { value: 'fabricant', label: 'Fabricant' },
  { value: 'fournisseur_local', label: 'Fournisseur local' },
  { value: 'fournisseur_international', label: 'Fournisseur international' },
];

export const SUPPLIER_TYPE_LABELS = SUPPLIER_TYPES.reduce((acc, t) => ({ ...acc, [t.value]: t.label }), {});

export const PAYMENT_METHODS = [
  { value: 'especes', label: 'Espèces' },
  { value: 'virement', label: 'Virement bancaire' },
  { value: 'cheque', label: 'Chèque' },
  { value: 'mvola', label: 'MVola' },
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'airtel_money', label: 'Airtel Money' },
];

export const PAYMENT_METHOD_LABELS = {
  especes: 'Espèces',
  virement: 'Virement bancaire',
  cheque: 'Chèque',
  mvola: 'MVola',
  orange_money: 'Orange Money',
  airtel_money: 'Airtel Money',
};

export const UNITS = [
  { value: 'piece', label: 'Pièce' },
  { value: 'bouteille', label: 'Bouteille' },
  { value: 'sachet', label: 'Sachet' },
  { value: 'pack', label: 'Pack' },
  { value: 'carton', label: 'Carton' },
  { value: 'sac', label: 'Sac' },
  { value: 'bidon', label: 'Bidon' },
  { value: 'caisse', label: 'Caisse' },
  { value: 'palette', label: 'Palette' },
];

export const CURRENCY = {
  code: 'MGA',
  symbol: 'Ar',
  locale: 'mg-MG',
};

export const VILLES_MADAGASCAR = [
  'Antananarivo',
  'Antsirabe',
  'Fianarantsoa',
  'Antsiranana',
  'Mahajanga',
  'Toamasina',
  'Toliara',
  'Morondava',
  'Antalaha',
  'Ambovombe',
  'Farafangana',
  'Manakara',
  'Sambava',
  'Marovoay',
  'Maintirano',
  'Besalampy',
  'Moramanga',
  'Vatomandry',
  'Mahanoro',
  'Mananjary',
  'Nosy Be',
  'Andapa',
  'Bealanana',
  'Port-Bergé',
  'Mampikony',
  'Analalava',
  'Soanierana-Ivongo',
  'Fenoarivo Atsinanana',
  'Mananara Avaratra',
  'Vavatenina',
  'Marolambo',
  'Ihosy',
  'Ilakaka',
  'Betroka',
  'Ambositra',
  'Fandriana',
  'Manandriana',
  'Ambohidratrimo',
  'Andramasina',
  'Anjozorobe',
  'Manjakandriana',
  'Soavinandriana',
  'Miarinarivo',
  'Arivonimamo',
  'Tsiroanomandidy',
  'Ampanihy',
  'Betioky',
  'Sakaraha',
  'Ejeda',
  'Beloha',
  'Tsihombe',
  'Fort-Dauphin',
  'Vangaindrano',
  'Vondrozo',
  'Ikongo',
  'Nosy Varika',
  'Sahambavy',
  'Ambalavao',
];
