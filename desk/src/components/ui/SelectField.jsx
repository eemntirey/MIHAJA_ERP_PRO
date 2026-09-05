import React, { useId } from 'react';
import Field from './Field';

const SelectField = ({
  id,
  label,
  required = false,
  optional = false,
  helperText,
  error,
  disabled = false,
  placeholder,
  options = [],
  value,
  onChange,
  name,
  register,
  registerOptions,
  className = '',
  ...rest
}) => {
  const reactId = useId();
  const fieldId = id || `select-${reactId}`;

  const reg = register && name ? register(name, registerOptions) : null;
  const selectValue = reg ? undefined : value;
  const selectOnChange = reg ? undefined : onChange;

  return (
    <Field
      id={fieldId}
      label={label}
      required={required}
      optional={optional}
      helperText={helperText}
      error={error}
      className={className}
    >
      <div className={`select-field ${disabled ? 'select-field--disabled' : ''}`}>
        <select
          id={fieldId}
          className="select-field__native"
          disabled={disabled}
          required={required}
          aria-invalid={!!error}
          value={selectValue}
          onChange={selectOnChange}
          {...(reg || {})}
          {...rest}
        >
          {placeholder !== undefined && (
            <option value="" disabled={required}>{placeholder}</option>
          )}
          {options.map((opt) => {
            if (opt && typeof opt === 'object') {
              return <option key={opt.value} value={opt.value}>{opt.label}</option>;
            }
            return <option key={opt} value={opt}>{opt}</option>;
          })}
        </select>
        <span className="select-field__chevron" aria-hidden="true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </div>
    </Field>
  );
};

export default SelectField;