// src/components/desktop/FormGrid.jsx
//
// Layout de formulaire Desktop : grille multi-colonnes (2 à 3 colonnes) qui
// retombe automatiquement sur une colonne unique en dessous de 1280px.
//
// Exemple :
//   <FormGrid columns={3}>
//     <FormField label="Nom" required error={errors.nom}>
//       <input name="nom" value={form.nom} onChange={onChange} />
//     </FormField>
//     <FormField label="Description" span="full">
//       <textarea name="description" ... />
//     </FormField>
//   </FormGrid>
//
// Brouillons : `FormDraftBanner` (restauration) et `FormDraftStatus` (état de
// l'auto-save) consomment l'objet retourné par le hook `useFormDraft`.

import React from 'react';
import './FormGrid.css';

const clampColumns = (columns) => {
  const value = Number(columns) || 2;
  return Math.min(3, Math.max(1, Math.round(value)));
};

const spanClass = (span) => {
  if (span === 'full' || span === true) return 'form-field--full';
  if (Number(span) >= 3) return 'form-field--span-3';
  if (Number(span) === 2) return 'form-field--span-2';
  return '';
};

const FormGrid = ({ columns = 2, gap, children, className, dense = false }) => {
  const cols = clampColumns(columns);
  return (
    <div
      className={['form-grid-desktop', dense ? 'form-grid-desktop--dense' : '', className || '']
        .filter(Boolean)
        .join(' ')}
      data-columns={cols}
      style={{
        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
        gap: gap !== undefined ? gap : undefined,
      }}
    >
      {children}
    </div>
  );
};

/** Champ de formulaire : label + contrôle + aide/erreur, avec gestion du span. */
export const FormField = ({
  label,
  htmlFor,
  required = false,
  error,
  hint,
  span,
  className,
  children,
}) => (
  <div
    className={['form-field', spanClass(span), error ? 'has-error' : '', className || '']
      .filter(Boolean)
      .join(' ')}
  >
    {label && (
      <label className="form-field-label" htmlFor={htmlFor}>
        {label}
        {required && (
          <span className="form-field-required" aria-hidden="true">
            *
          </span>
        )}
      </label>
    )}
    <div className="form-field-control">{children}</div>
    {error ? (
      <span className="form-field-error" role="alert">
        {error}
      </span>
    ) : (
      hint && <span className="form-field-hint">{hint}</span>
    )}
  </div>
);

/** Bloc thématique à l'intérieur d'un formulaire (titre + grille imbriquée). */
export const FormSection = ({ title, description, columns = 2, actions, children, className }) => (
  <section className={['form-grid-section', className || ''].filter(Boolean).join(' ')}>
    {(title || actions) && (
      <header className="form-grid-section-head">
        <div>
          {title && <h4 className="form-grid-section-title">{title}</h4>}
          {description && <p className="form-grid-section-desc">{description}</p>}
        </div>
        {actions && <div className="form-grid-section-actions">{actions}</div>}
      </header>
    )}
    <FormGrid columns={columns}>{children}</FormGrid>
  </section>
);

const formatDraftTime = (savedAt) => {
  if (!savedAt) return '';
  const date = new Date(savedAt);
  if (Number.isNaN(date.getTime())) return '';
  const isToday = date.toDateString() === new Date().toDateString();
  const time = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  return isToday ? time : `${date.toLocaleDateString('fr-FR')} à ${time}`;
};

/**
 * Bandeau proposant de restaurer un brouillon trouvé en local.
 * @param {Object} draft objet retourné par `useFormDraft`
 * @param {(data:Object) => void} onRestore
 */
export const FormDraftBanner = ({ draft, onRestore, className }) => {
  if (!draft?.hasStoredDraft) return null;
  const savedLabel = formatDraftTime(draft.storedDraft?.savedAt);
  return (
    <div className={['form-draft-banner', className || ''].filter(Boolean).join(' ')} role="status">
      <span className="form-draft-banner-text">
        <i className="ti ti-history" aria-hidden="true" />
        Un brouillon {savedLabel ? `enregistré à ${savedLabel} ` : ''}est disponible pour ce formulaire.
      </span>
      <span className="form-draft-banner-actions">
        <button
          type="button"
          className="form-draft-btn is-primary"
          onClick={() => {
            const data = draft.restore();
            if (data && onRestore) onRestore(data);
          }}
        >
          Restaurer
        </button>
        <button type="button" className="form-draft-btn" onClick={draft.discard}>
          Ignorer
        </button>
      </span>
    </div>
  );
};

/** Indicateur discret de l'auto-save (toutes les 5 secondes par défaut). */
export const FormDraftStatus = ({ draft, className }) => {
  if (!draft) return null;
  const { status, savedAt, interval } = draft;
  const seconds = Math.round((interval || 5000) / 1000);

  let icon = 'ti-cloud';
  let text = `Brouillon automatique toutes les ${seconds} s`;
  if (status === 'saved') {
    icon = 'ti-cloud-check';
    text = `Brouillon enregistré à ${formatDraftTime(savedAt)}`;
  } else if (status === 'restored') {
    icon = 'ti-history';
    text = 'Brouillon restauré';
  } else if (status === 'error') {
    icon = 'ti-cloud-off';
    text = 'Brouillon non persisté (stockage local indisponible)';
  }

  return (
    <span
      className={['form-draft-status', status === 'error' ? 'is-error' : '', className || '']
        .filter(Boolean)
        .join(' ')}
      aria-live="polite"
    >
      <i className={`ti ${icon}`} aria-hidden="true" />
      {text}
    </span>
  );
};

export default FormGrid;
