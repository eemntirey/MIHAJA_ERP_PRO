// shared/components/TempPasswordCard.jsx
import React from 'react';

const escapeHtml = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[c]);

const CARD_BG = '#ffffff';
const CARD_ACCENT = '#d4af37';
const CARD_TEXT = '#111111';
const CARD_MUTED = '#6b7280';

/**
 * Affiche une fois les identifiants de connexion d'un employe cree sans mot
 * de passe (mot de passe temporaire genere par le backend) et permet de les
 * imprimer sous forme de carte a donner a l'employe.
 *
 * Props:
 * - email: email de connexion (ou username)
 * - password: mot de passe temporaire (renvoye UNE fois par l'API)
 * - tenantName: nom de l'entreprise (optionnel, affiche sur la carte)
 * - onClose: ferme la modal
 */
const TempPasswordCard = ({ email, password, tenantName = null, onClose }) => {

  const handlePrint = () => {
    const win = window.open('', '_blank', 'width=420,height=620');
    if (!win) {
      window.alert("Veuillez autoriser les pop-ups pour imprimer la carte.");
      return;
    }
    const safeEmail = escapeHtml(email);
    const safePassword = escapeHtml(password);
    const safeTenant = escapeHtml(tenantName);
    win.document.write(`<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Identifiants de connexion</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: Arial, Helvetica, sans-serif; display: flex; justify-content: center; padding: 24px; }
  .card {
    width: 320px;
    border: 1px solid #e6e6e1;
    border-top: 6px solid ${CARD_ACCENT};
    border-radius: 8px;
    padding: 24px;
    background: ${CARD_BG};
    color: ${CARD_TEXT};
  }
  .brand { font-size: 18px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 16px; }
  .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: ${CARD_MUTED}; margin-top: 14px; }
  .value { font-size: 15px; font-weight: 600; margin-top: 4px; word-break: break-all; }
  .warn { margin-top: 18px; font-size: 11px; color: ${CARD_MUTED}; line-height: 1.5; }
</style>
</head>
<body>
  <div class="card">
    <div class="brand">${safeTenant || 'Identifiants de connexion'}</div>
    <div class="label">Identifiant (email)</div>
    <div class="value">${safeEmail}</div>
    <div class="label">Mot de passe temporaire</div>
    <div class="value">${safePassword}</div>
    <div class="warn">Ce mot de passe est temporaire : il devra etre change des la premiere connexion.</div>
  </div>
</body>
</html>`);
    win.document.close();
    win.focus();
    win.print();
  };

  const close = () => {
    if (onClose) onClose();
  };

  return (
    <div
      className="modal-overlay"
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
      onClick={close}
    >
      <div
        className="modal"
        style={{ background: CARD_BG, borderRadius: 10, width: 380, maxWidth: '92vw', padding: 24, boxShadow: '0 8px 30px rgba(0,0,0,0.25)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, margin: 0 }}>{tenantName ? 'Compte créé' : 'Identifiants de connexion'}</h2>
          <button
            type="button"
            aria-label="Fermer"
            onClick={close}
            style={{ border: 'none', background: 'none', fontSize: 22, cursor: 'pointer', lineHeight: 1 }}
          >
            ×
          </button>
        </div>

        {tenantName && <div style={{ fontSize: 13, color: CARD_MUTED, marginBottom: 8 }}>{tenantName}</div>}

        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px', color: CARD_MUTED, marginTop: 10 }}>
          Identifiant (email)
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, marginTop: 4, wordBreak: 'break-all' }}>{email}</div>

        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px', color: CARD_MUTED, marginTop: 14 }}>
          Mot de passe temporaire
        </div>
        <div
          data-testid="temporary-password"
          style={{ fontSize: 15, fontWeight: 600, marginTop: 4, background: '#f7f7f5', border: '1px solid #e6e6e1', borderRadius: 6, padding: '8px 10px', wordBreak: 'break-all' }}
        >
          {password}
        </div>

        <div style={{ fontSize: 11, color: CARD_MUTED, lineHeight: 1.5, marginTop: 14 }}>
          Ce mot de passe est temporaire : il devra être changé dès la première connexion.
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 18 }}>
          <button
            type="button"
            onClick={close}
            style={{ border: '1px solid #d1d5db', background: '#fff', borderRadius: 6, padding: '8px 14px', cursor: 'pointer', fontSize: 14 }}
          >
            Fermer
          </button>
          <button
            type="button"
            onClick={handlePrint}
            style={{ border: 'none', background: CARD_ACCENT, color: '#111', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
          >
            Imprimer la carte
          </button>
        </div>
      </div>
    </div>
  );
};

export default TempPasswordCard;