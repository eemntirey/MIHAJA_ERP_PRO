import * as yup from 'yup';

const numericString = yup
  .mixed()
  .transform((value, original) => {
    if (original === '' || original === null || original === undefined) return null;
    const n = Number(original);
    return isNaN(n) ? undefined : n;
  });

export const livreurSchema = yup.object({
  nom: yup.string().required('Le nom est requis'),
  prenom: yup.string().required('Le prénom est requis'),
  telephone: yup.string().nullable(),
  email: yup.string().email('Email invalide').nullable(),
  numero_permis: yup.string().nullable(),
  statut: yup.string().oneOf(['actif', 'inactif', 'en_conges'], 'Statut invalide').default('actif'),
});

export const vehiculeSchema = yup.object({
  marque: yup.string().required('La marque est requise'),
  modele: yup.string().required('Le modèle est requis'),
  plaque_immatriculation: yup.string().required('La plaque est requise'),
  type: yup.string().oneOf(['camion', 'van', 'voiture', 'moto'], 'Type invalide').default('camion'),
  capacite_charge: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  capacite_volume: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  statut: yup.string().oneOf(['disponible', 'en_mission', 'en_maintenance'], 'Statut invalide').default('disponible'),
});

export const itineraireSchema = yup.object({
  nom: yup.string().required('Le nom est requis'),
  description: yup.string().nullable(),
  date_depart: yup.date().nullable(),
  date_retour: yup.date().nullable(),
  points_intermediaires: yup.string().nullable(),
  livreur_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  vehicule_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  statut: yup.string().oneOf(['planifie', 'en_cours', 'termine', 'annule'], 'Statut invalide').default('planifie'),
});

export const livraisonSchema = yup.object({
  vente_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  commande_client_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  itineraire_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  livreur_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  vehicule_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  nom_destinataire: yup.string().required('Le destinataire est requis'),
  adresse_livraison: yup.string().nullable(),
  ville_livraison: yup.string().nullable(),
  telephone_livraison: yup.string().nullable(),
  date_livraison_prevue: yup.date().nullable(),
  statut: yup.string().oneOf(['en_attente', 'chargee', 'en_route', 'livree', 'retournee', 'echec'], 'Statut invalide').default('en_attente'),
  notes: yup.string().nullable(),
});

export const suiviSchema = yup.object({
  statut: yup.string().required('Le statut est requis'),
  commentaire: yup.string().nullable(),
  localisation_lat: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  localisation_lng: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
});

export const employeSchema = yup.object({
  matricule: yup.string().required('Le matricule est requis'),
  nom: yup.string().required('Le nom est requis'),
  prenom: yup.string().nullable(),
  date_naissance: yup.date().nullable(),
  lieu_naissance: yup.string().nullable(),
  sexe: yup.string().oneOf(['M', 'F']).default('M'),
  adresse: yup.string().nullable(),
  telephone: yup.string().nullable(),
  email: yup.string().email('Email invalide').nullable(),
  poste: yup.string().nullable(),
  departement: yup.string().nullable(),
  date_embauche: yup.date().nullable(),
  date_fin_contrat: yup.date().nullable(),
  type_contrat: yup.string().oneOf(['cdi', 'cdd', 'stage', 'freelance'], 'Type invalide').default('cdi'),
  salaire_base: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  banque_nom: yup.string().nullable(),
  banque_iban: yup.string().nullable(),
  banque_bic: yup.string().nullable(),
  statut: yup.string().oneOf(['actif', 'inactif', 'en_conges', 'depart'], 'Statut invalide').default('actif'),
});

export const presenceSchema = yup.object({
  employe_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .required('L\'employé est requis'),
  date: yup.date().required('La date est requise'),
  heure_arrivee: yup.date().nullable(),
  heure_depart: yup.date().nullable(),
  heure_pause_debut: yup.date().nullable(),
  heure_pause_fin: yup.date().nullable(),
  statut: yup.string().oneOf(['present', 'absent', 'en_retard', 'conge', 'maladie'], 'Statut invalide').default('present'),
  remarque: yup.string().nullable(),
});

export const salaireSchema = yup.object({
  employe_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .required('L\'employé est requis'),
  mois: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le mois est requis')
    .min(1, 'Mois invalide (1-12)')
    .max(12, 'Mois invalide (1-12)'),
  annee: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('L\'année est requise')
    .min(1900, 'Année invalide'),
  salaire_base: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  primes: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  indemnites: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  deductions: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  avances: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  mode_paiement: yup.string().oneOf(['virement', 'especes', 'cheque'], 'Mode invalide').default('virement'),
  reference_paiement: yup.string().nullable(),
  notes: yup.string().nullable(),
  statut_paiement: yup.string().oneOf(['non_paye', 'partiel', 'paye'], 'Statut invalide').default('non_paye'),
  date_paiement: yup.date().nullable(),
});

export const primeSchema = yup.object({
  employe_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .required('L\'employé est requis'),
  type_prime: yup.string().oneOf(['performance', 'anciennete', 'objectif', 'exceptionnel'], 'Type invalide').default('performance'),
  montant: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .required('Le montant est requis')
    .min(0, 'Le montant doit être positif'),
  date_octroi: yup.date().required('La date est requise'),
  motif: yup.string().nullable(),
});

export const compteSchema = yup.object({
  numero: yup.string().required('Le numéro est requis'),
  nom: yup.string().required('Le nom est requis'),
  type_compte: yup.string().oneOf(['actif', 'passif', 'charge', 'produit'], 'Type invalide').default('actif'),
  sous_compte_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  solde: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  is_actif: yup.boolean().default(true),
});

export const ecritureSchema = yup.object({
  date: yup.date().required('La date est requise'),
  compte_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le compte est requis'),
  montant_debit: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  montant_credit: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .default(0),
  libelle: yup.string().required('Le libellé est requis'),
  reference_externe: yup.string().nullable(),
  entite_type: yup.string().nullable(),
  entite_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  piece_joint: yup.string().nullable(),
});

export const tresorerieSchema = yup.object({
  date: yup.date().required('La date est requise'),
  type_operation: yup.string().oneOf(['entree', 'sortie'], 'Type invalide').default('entree'),
  montant: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le montant est requis')
    .min(0, 'Le montant doit être positif'),
  mode_paiement: yup.string().oneOf(['espece', 'virement', 'cheque', 'mobile_money'], 'Mode invalide').default('espece'),
  libelle: yup.string().required('Le libellé est requis'),
  compte_bancaire: yup.string().nullable(),
  reference: yup.string().nullable(),
  compte_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  ecriture_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  is_reconcilie: yup.boolean().default(false),
});

export const modeleDocumentSchema = yup.object({
  nom: yup.string().required('Le nom est requis'),
  type_document: yup.string().oneOf(['facture', 'devis', 'contrat', 'bon_livraison', 'avoir'], 'Type invalide').default('facture'),
  contenu_modele: yup.string().required('Le contenu est requis'),
  est_actif: yup.boolean().default(true),
  est_defaut: yup.boolean().default(false),
  logo_url: yup.string().nullable(),
  mention_legales: yup.string().nullable(),
  conditions_generales: yup.string().nullable(),
});

export const documentSchema = yup.object({
  modele_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le modèle est requis'),
  type_document: yup.string().oneOf(['facture', 'devis', 'contrat', 'bon_livraison', 'avoir'], 'Type invalide').default('facture'),
  reference: yup.string().required('La référence est requise'),
  entite_type: yup.string().oneOf(['vente', 'facture', 'commande', 'abonnement'], 'Entité invalide').default('vente'),
  entite_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  donnees: yup.string().required('Les données JSON sont requises'),
});

export const commandeAchatSchema = yup.object({
  fournisseur_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le fournisseur est requis'),
  total_ht: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  total_ttc: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  statut: yup.string().oneOf(['brouillon', 'envoyee', 'confirmee', 'recue', 'partiellement_recue', 'annulee'], 'Statut invalide').default('brouillon'),
  date_commande: yup.date().nullable(),
  date_livraison_prevue: yup.date().nullable(),
  date_reception: yup.date().nullable(),
  conditions_paiement: yup.string().default('30 jours'),
  remarque: yup.string().nullable(),
  lignes: yup.string().nullable(),
});

export const receptionSchema = yup.object({
  commande_achat_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('La commande est requise'),
  reference: yup.string().required('La référence est requise'),
  quantite_recue: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('La quantité reçue est requise')
    .min(0, 'La quantité doit être positive'),
  quantite_commandee: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  remarque: yup.string().nullable(),
});

export const devisSchema = yup.object({
  reference: yup.string().required('La référence est requise'),
  client_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le client est requis'),
  commercial_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  total_ht: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  total_ttc: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  date_validite: yup.date().nullable(),
  statut: yup.string().oneOf(['en_attente', 'accepte', 'refuse', 'converti', 'expire'], 'Statut invalide').default('en_attente'),
  conditions_paiement: yup.string().default('30 jours'),
  remarque: yup.string().nullable(),
});

export const bonLivraisonSchema = yup.object({
  reference: yup.string().required('La référence est requise'),
  vente_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  client_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le client est requis'),
  livreur_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  vehicule_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  adresse_livraison: yup.string().nullable(),
  date_livraison_prevue: yup.date().nullable(),
  date_livraison_reelle: yup.date().nullable(),
  statut: yup.string().oneOf(['prepare', 'expedie', 'livre'], 'Statut invalide').default('prepare'),
  signature: yup.string().nullable(),
  photo: yup.string().nullable(),
  remarque: yup.string().nullable(),
});

export const avoirSchema = yup.object({
  reference: yup.string().required('La référence est requise'),
  vente_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  facture_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return null;
      const n = Number(original);
      return isNaN(n) ? undefined : n;
    })
    .nullable(),
  client_id: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return undefined;
      return Number(original);
    })
    .required('Le client est requis'),
  montant_ht: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  montant_ttc: yup
    .mixed()
    .transform((value, original) => {
      if (original === '' || original === null || original === undefined) return 0;
      return Number(original);
    })
    .default(0),
  motif: yup.string().nullable(),
  statut: yup.string().oneOf(['en_attente', 'accepte', 'rembourse', 'annule'], 'Statut invalide').default('en_attente'),
});

export const useFormHelpers = () => {
  const toNumberOrNull = (val) => {
    if (val === '' || val === null || val === undefined) return null;
    const n = Number(val);
    return isNaN(n) ? null : n;
  };
  const toNumberOrZero = (val) => {
    if (val === '' || val === null || val === undefined) return 0;
    const n = Number(val);
    return isNaN(n) ? 0 : n;
  };
  const toNullIfEmpty = (val) => {
    if (val === '' || val === null || val === undefined) return null;
    return val;
  };
  return { toNumberOrNull, toNumberOrZero, toNullIfEmpty };
};
