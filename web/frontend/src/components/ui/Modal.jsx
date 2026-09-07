import React, { useEffect, useRef } from 'react';
import './ui.css';

/**
 * Modale accessible : fermeture ESC, overlay, focus initial, responsive.
 * Structure : Header (titre + description) / Body / Footer.
 */
const Modal = ({ open, onClose, title, description, size, footer, children }) => {
  const overlayRef = useRef(null);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const t = setTimeout(() => dialogRef.current?.focus(), 30);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      clearTimeout(t);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="ui-modal__overlay"
      ref={overlayRef}
      onMouseDown={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div
        className={`ui-modal ${size === 'large' ? 'ui-modal--large' : ''} ${size === 'xlarge' ? 'ui-modal--xlarge' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={dialogRef}
      >
        <div className="ui-modal__header">
          <div className="ui-modal__heading">
            <span className="ui-modal__title">{title}</span>
            {description && <span className="ui-modal__desc">{description}</span>}
          </div>
          <button type="button" className="ui-modal__close" onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <div className="ui-modal__body">{children}</div>
        {footer && <div className="ui-modal__footer">{footer}</div>}
      </div>
    </div>
  );
};

export default Modal;
