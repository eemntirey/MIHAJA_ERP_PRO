import React, { useId } from 'react';
import './ui.css';

/**
 * Field — conteneur sémantique pour un champ de formulaire.
 * Lie visuellement et pour l'accessibilité :
 *   - le label (htmlFor + id)
 *   - le contrôle (children)
 *   - le texte d'aide (helperText)
 *   - le message d'erreur (error)
 *
 * Usage :
 *   <Field id="x" label="Email" required helperText="Nous ne partagerons jamais votre email.">
 *     <input id="x" className="field__input" ... />
 *   </Field>
 *
 * Pour aller plus vite, voir <TextField>, <SelectField>, <ToggleField>.
 */
const Field = ({
  id,
  label,
  required = false,
  optional = false,
  helperText,
  error,
  children,
  className = '',
}) => {
  const reactId = useId();
  const fieldId = id || `field-${reactId}`;
  const helperId = helperText ? `${fieldId}-help` : undefined;
  const errorId = error ? `${fieldId}-err` : undefined;
  const describedBy = [helperId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={`field ${error ? 'field--error' : ''} ${className}`}>
      {label && (
        <label htmlFor={fieldId} className="field__label">
          <span>{label}</span>
          {required && <span className="field__required" aria-hidden="true">*</span>}
          {optional && !required && <span className="field__optional">facultatif</span>}
        </label>
      )}
      <div className="field__control" aria-describedby={describedBy}>
        {children}
      </div>
      {helperText && !error && (
        <p id={helperId} className="field__help">{helperText}</p>
      )}
      {error && (
        <p id={errorId} className="field__error" role="alert">
          <span className="field__error-icon" aria-hidden="true">!</span>
          {error}
        </p>
      )}
    </div>
  );
};

export default Field;