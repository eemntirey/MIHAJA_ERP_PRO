import React, { useEffect, useState } from 'react';
import './PaymentSettings.css';

const ENV_OPTIONS = [
  { value: 'sandbox', label: 'Sandbox (test)' },
  { value: 'production', label: 'Production (réel)' },
];

const PAYMENT_METHODS = [
  { value: 'MVOLA', label: 'MVola' },
  { value: 'ORANGE_MONEY', label: 'Orange Money' },
  { value: 'AIRTEL_MONEY', label: 'Airtel Money' },
  { value: 'BRED', label: 'Carte bancaire (BRED/Visa)' },
];

export default function PaymentSettings() {
  const [status, setStatus] = useState({ papi_configured: false, vitrine_enabled: false, vitrine_active: false });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [papiApiKey, setPapiApiKey] = useState('');
  const [papiWebhookSecret, setPapiWebhookSecret] = useState('');
  const [papiEnvironment, setPapiEnvironment] = useState('sandbox');
  const [vitrineEnabled, setVitrineEnabled] = useState(false);
  const [vitrineToggleBusy, setVitrineToggleBusy] = useState(false);

  useEffect(() => {
    setLoading(false);
    setStatus({ papi_configured: false, vitrine_enabled: false, vitrine_active: false });
  }, []);

  const papiConfigured = Boolean(status?.papi_configured);
  const vitrineActive = Boolean(status?.vitrine_active);

  return (
    <div className="page">
      <h1>Paramètres de paiement</h1>
      <p>Configuration du compte marchand Papi et de la vitrine publique.</p>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <section className="card">
        <h2>Compte marchand Papi</h2>
        <p>Cette section est destinée au tenant. Pour le super-admin, consultez la vue Papi marchands.</p>
        <div className="form-row">
          <label>Clé API Papi</label>
          <input type="password" value={papiApiKey} onChange={(e) => setPapiApiKey(e.target.value)} placeholder="Clé API" />
        </div>
        <div className="form-row">
          <label>Secret webhook</label>
          <input type="password" value={papiWebhookSecret} onChange={(e) => setPapiWebhookSecret(e.target.value)} placeholder="Secret webhook" />
        </div>
        <div className="form-row">
          <label>Environnement</label>
          <select value={papiEnvironment} onChange={(e) => setPapiEnvironment(e.target.value)}>
            {ENV_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="actions">
          <button className="btn-primary" onClick={() => setSuccess('Configuration enregistrée (démo)')}>Enregistrer</button>
          <button className="btn-secondary" onClick={() => setSuccess('Connexion Papi OK (démo)')}>Tester</button>
        </div>
      </section>

      <section className="card">
        <h2>Vitrine publique MIHAJA</h2>
        <p>Active si le tenant a configuré Papi et activé le toggle vitrine.</p>
        <label className="switch-label">
          <input type="checkbox" checked={vitrineEnabled} onChange={(e) => setVitrineEnabled(e.target.checked)} />
          <span>Vitrine activée</span>
        </label>
      </section>

      <section className="card">
        <h2>Méthodes de paiement</h2>
        <ul>
          {PAYMENT_METHODS.map((m) => <li key={m.value}>{m.label}</li>)}
        </ul>
      </section>
    </div>
  );
}
