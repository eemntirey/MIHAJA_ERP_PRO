import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-toastify';

export default function EmailConfig() {
  const [cfg, setCfg] = useState({
    MAIL_HOST: '',
    MAIL_PORT: 587,
    MAIL_USERNAME: '',
    MAIL_FROM: '',
    MAIL_FROM_NAME: '',
    MAIL_USE_TLS: true,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/super-admin/email-config')
      .then(({ data }) => setCfg(data))
      .catch(() => {});
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.put('/super-admin/email-config', cfg);
      toast.success('Configuration email mise à jour');
    } catch (err) {
      toast.error(err?.response?.data?.message || 'Erreur');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sa-page">
      <h2>Fournisseur Email (SMTP / API)</h2>
      <p className="sa-text-muted">Configuration partagée par tous les tenants.</p>
      <form onSubmit={handleSave} className="sa-form">
        <label>MAIL_HOST</label>
        <input type="text" value={cfg.MAIL_HOST || ''} onChange={e => setCfg({ ...cfg, MAIL_HOST: e.target.value })} />
        <label>MAIL_PORT</label>
        <input type="number" value={cfg.MAIL_PORT || 587} onChange={e => setCfg({ ...cfg, MAIL_PORT: parseInt(e.target.value, 10) || 587 })} />
        <label>MAIL_USERNAME</label>
        <input type="text" value={cfg.MAIL_USERNAME || ''} onChange={e => setCfg({ ...cfg, MAIL_USERNAME: e.target.value })} />
        <label>MAIL_FROM</label>
        <input type="text" value={cfg.MAIL_FROM || ''} onChange={e => setCfg({ ...cfg, MAIL_FROM: e.target.value })} />
        <label>MAIL_FROM_NAME</label>
        <input type="text" value={cfg.MAIL_FROM_NAME || ''} onChange={e => setCfg({ ...cfg, MAIL_FROM_NAME: e.target.value })} />
        <label>
          <input type="checkbox" checked={!!cfg.MAIL_USE_TLS} onChange={e => setCfg({ ...cfg, MAIL_USE_TLS: e.target.checked })} />
          MAIL_USE_TLS (TLS actif)
        </label>
        <button type="submit" disabled={loading}>{loading ? 'Enregistrement...' : 'Enregistrer'}</button>
      </form>
    </div>
  );
}
