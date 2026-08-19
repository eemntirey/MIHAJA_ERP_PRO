// src/components/ClientModal.jsx
import React from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { toast } from 'react-toastify';
import { clientService } from '../services/api';

const CLIENT_TYPES = [
  { value: 'particulier', label: 'Particulier' },
  { value: 'professionnel', label: 'Professionnel' },
  { value: 'association', label: 'Association' },
  { value: 'collectivite', label: 'Collectivité' },
  { value: 'grossiste', label: 'Grossiste' },
  { value: 'distributeur', label: 'Distributeur' },
  { value: 'centrale_achat', label: 'Centrale d\'achat' },
];

const clientSchema = yup.object().shape({
  code: yup.string().required('Code client requis'),
  type: yup.string().required('Type de client requis'),
  nom: yup.string().required('Nom requis'),
  prenom: yup.string().nullable().default(''),
  email: yup.string().email('Email invalide').nullable().default(''),
  telephone: yup.string().nullable().default(''),
  adresse_facturation: yup.string().nullable().default(''),
  code_postal_facturation: yup.string().nullable().default(''),
  ville_facturation: yup.string().nullable().default(''),
  pays_facturation: yup.string().default('Madagascar'),
  raison_sociale: yup.string().nullable().default(''),
  siret: yup.string().nullable().default(''),
  numero_tva: yup.string().nullable().default(''),
});

const ClientModal = ({ client, onClose, onSuccess }) => {
  const isEdit = !!client;

  const defaultValues = {
    code: client?.code || '',
    type: client?.type || 'particulier',
    nom: client?.nom || '',
    prenom: client?.prenom || '',
    email: client?.email || '',
    telephone: client?.telephone || '',
    adresse_facturation: client?.adresse_facturation || '',
    code_postal_facturation: client?.code_postal_facturation || '',
    ville_facturation: client?.ville_facturation || '',
    pays_facturation: client?.pays_facturation || client?.pays || 'Madagascar',
    raison_sociale: client?.raison_sociale || '',
    siret: client?.siret || '',
    numero_tva: client?.numero_tva || '',
  };

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(clientSchema),
    defaultValues,
  });

  const clientType = watch('type');

  const onSubmit = async (data) => {
    try {
      if (isEdit) {
        await clientService.update(client.id, data);
        toast.success('Client mis à jour avec succès');
      } else {
        await clientService.create(data);
        toast.success('Client ajouté avec succès');
      }
      onSuccess();
    } catch (err) {
      console.error('Error saving client:', err);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isEdit ? 'Modifier le client' : 'Ajouter un nouveau client'}</h2>
          <button onClick={onClose} className="btn-close">×</button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="modal-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Code client *</label>
              <input
                type="text"
                {...register('code')}
                placeholder="Code client"
              />
              {errors.code && <span className="field-error">{errors.code.message}</span>}
            </div>
            <div className="form-group">
              <label>Type de client *</label>
              <select {...register('type')}>
                {CLIENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              {errors.type && <span className="field-error">{errors.type.message}</span>}
            </div>
            <div className="form-group">
              <label>Nom *</label>
              <input
                type="text"
                {...register('nom')}
                placeholder="Nom"
              />
              {errors.nom && <span className="field-error">{errors.nom.message}</span>}
            </div>
            <div className="form-group">
              <label>Raison sociale</label>
              <input
                type="text"
                {...register('raison_sociale')}
                placeholder="Raison sociale"
              />
              {errors.raison_sociale && <span className="field-error">{errors.raison_sociale.message}</span>}
            </div>
            <div className="form-group">
              <label>Prénom</label>
              <input
                type="text"
                {...register('prenom')}
                placeholder="Prénom"
              />
              {errors.prenom && <span className="field-error">{errors.prenom.message}</span>}
            </div>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                {...register('email')}
                placeholder="client@email.com"
              />
              {errors.email && <span className="field-error">{errors.email.message}</span>}
            </div>
            <div className="form-group">
              <label>Téléphone</label>
              <input
                type="tel"
                {...register('telephone')}
                placeholder="0612345678"
              />
              {errors.telephone && <span className="field-error">{errors.telephone.message}</span>}
            </div>
            <div className="form-group full-width">
              <label>Adresse</label>
              <input
                type="text"
                {...register('adresse_facturation')}
                placeholder="Rue, numéro"
              />
              {errors.adresse_facturation && <span className="field-error">{errors.adresse_facturation.message}</span>}
            </div>
            <div className="form-group">
              <label>Code postal</label>
              <input
                type="text"
                {...register('code_postal_facturation')}
                placeholder="101"
              />
              {errors.code_postal_facturation && <span className="field-error">{errors.code_postal_facturation.message}</span>}
            </div>
            <div className="form-group">
              <label>Ville</label>
              <input
                type="text"
                {...register('ville_facturation')}
                placeholder="Antananarivo"
              />
              {errors.ville_facturation && <span className="field-error">{errors.ville_facturation.message}</span>}
            </div>
            <div className="form-group">
              <label>Pays</label>
              <input
                type="text"
                {...register('pays_facturation')}
                placeholder="Madagascar"
              />
              {errors.pays_facturation && <span className="field-error">{errors.pays_facturation.message}</span>}
            </div>
            <div className="form-group">
              <label>SIRET</label>
              <input
                type="text"
                {...register('siret')}
                placeholder="123 456 789 00010"
              />
              {errors.siret && <span className="field-error">{errors.siret.message}</span>}
            </div>
            <div className="form-group">
              <label>TVA Intracommunautaire</label>
              <input
                type="text"
                {...register('numero_tva')}
                placeholder="FRXX 123456789"
              />
              {errors.numero_tva && <span className="field-error">{errors.numero_tva.message}</span>}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" onClick={onClose} className="btn-secondary" disabled={isSubmitting}>
              Annuler
            </button>
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isEdit ? 'Mettre à jour' : 'Ajouter'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClientModal;
