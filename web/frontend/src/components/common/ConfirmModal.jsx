import React from 'react';

const ConfirmModal = ({
  title,
  message,
  warning,
  confirmText = 'Confirmer',
  cancelText = 'Annuler',
  confirmClass = 'btn-danger',
  onConfirm,
  onCancel,
}) => {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-modal-header">
          <h3>{title}</h3>
          <button type="button" className="btn-close" onClick={onCancel}>&times;</button>
        </div>
        <div className="confirm-modal-body">
          <p>{message}</p>
          {warning && (
            <div className="confirm-modal-warning">
              <i className="ti ti-alert-triangle" aria-hidden="true" />
              {warning}
            </div>
          )}
        </div>
        <div className="confirm-modal-footer">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button type="button" className={confirmClass} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
