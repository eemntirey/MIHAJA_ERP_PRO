import React, { useId } from 'react';
import Field from './Field';

/**
 * ToggleField — Case à option "switch" senior :
 *   - vraie switch visuelle (track + thumb animé)
 *   - label cliquable (le label entier toggle la switch)
 *   - accessible (role, aria-checked, focus ring)
 *   - état on/off clairement différent
 *   - helper text + error
 *
 * Compatible react-hook-form : passer {...register('name')} au composant.
 * Important : le contrôle caché doit rester premier enfant du <label>
 * pour que react-hook-form capture la value.
 */
const ToggleField = ({
  id,
  label,
  description,
  required = false,
  helperText,
  error,
  checked,
  defaultChecked,
  disabled = false,
  onChange,
  name,
  register,
  registerOptions,
  className = '',
  ...rest
}) => {
  const reactId = useId();
  const fieldId = id || `toggle-${reactId}`;
  const reg = register && name ? register(name, registerOptions) : null;

  return (
    <Field
      id={fieldId}
      label={undefined}
      required={required}
      helperText={helperText}
      error={error}
      className={`toggle-field ${className}`}
    >
      <label
        htmlFor={fieldId}
        className={`toggle ${disabled ? 'toggle--disabled' : ''} ${checked || defaultChecked ? 'toggle--on' : ''}`}
      >
        <input
          id={fieldId}
          type="checkbox"
          role="switch"
          className="toggle__input"
          disabled={disabled}
          checked={checked}
          defaultChecked={defaultChecked}
          onChange={onChange}
          aria-invalid={!!error}
          {...(reg || {})}
          {...rest}
        />
        <span className="toggle__track" aria-hidden="true">
          <span className="toggle__thumb" />
        </span>
        {(description || label) && (
          <span className="toggle__body">
            {label && <span className="toggle__title">{label}</span>}
            {description && <span className="toggle__desc">{description}</span>}
          </span>
        )}
      </label>
    </Field>
  );
};

export default ToggleField;