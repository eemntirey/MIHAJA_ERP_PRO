import { useEffect, useState } from 'react';
import { tenantPapiService } from '../services/api';
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
  const [status, setStatus] = useState(null);
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

  const loadStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await tenantPapiService.getStatus();
      setStatus(data);
      setVitrineEnabled(Boolean(data.vitrine_enabled));
      if (data.papi_environment) setPapiEnvironment(data.papi_environment);
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          "Impossible de charger la configuration paiement."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSave = async (e) => {
    e?.preventDefault?.();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        papi_environment: papiEnvironment,
      };
      if (papiApiKey.trim()) payload.papi_api_key = papiApiKey.trim();
      if (papiWebhookSecret.trim()) {
        payload.papi_webhook_secret = papiWebhookSecret.trim();
      }
      const { data } = await tenantPapiService.updateSettings(payload);
      setStatus(data);
      setPapiApiKey('');
      setPapiWebhookSecret('');
      setSuccess('Configuration Papi enregistrée.');
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          "Erreur lors de l'enregistrement de la configuration."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    if (
      !window.confirm(
        'Supprimer votre configuration Papi ? Vos produits ne seront plus visibles sur la vitrine.'
      )
    ) {
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const { data } = await tenantPapiService.updateSettings({
        clear: true,
      });
      setStatus(data);
      setPapiApiKey('');
      setPapiWebhookSecret('');
      setVitrineEnabled(false);
      setSuccess('Configuration Papi supprimée.');
    } catch (e) {
      setError(
        e?.response?.data?.message || 'Erreur lors de la suppression.'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setError('');
    setSuccess('');
    try {
      const { data } = await tenantPapiService.testConnection();
      if (data.ok) {
        setSuccess('Connexion Papi OK.');
      } else {
        setError('Connexion Papi refusée.');
      }
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          'Impossible de joindre Papi avec la clé configurée.'
      );
    } finally {
      setTesting(false);
    }
  };

  const handleVitrineToggle = async (next) => {
    setVitrineToggleBusy(true);
    setError('');
    setSuccess('');
    try {
      const { data } = await tenantPapiService.setVitrine(Boolean(next));
      setStatus(data);
      setVitrineEnabled(Boolean(data.vitrine_enabled));
      setSuccess(
        next
          ? 'Vitrine activée. Vos produits sont publiés.'
          : 'Vitrine désactivée.'
      );
    } catch (e) {
      setError(e?.response?.data?.message || 'Erreur lors du basculement.');
    } finally {
      setVitrineToggleBusy(false);
    }
  };

  if (loading) {
    return <div className="payment-settings loading">Chargement…</div>;
  }

  const papiConfigured = Boolean(status?.papi_configured);
  const vitrineActive = Boolean(status?.vitrine_active);

  return (
    <div className="payment-settings">
      <header className="ps-header">
        <h1>Paramètres de paiement</h1>
        <p>
          Connectez votre compte marchand Papi pour encaisser les paiements
          en ligne de vos clients sur la vitrine commune MIHAJA.
        </p>
      </header>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <section className="ps-card">
        <div className="ps-card-header">
          <h2>Compte marchand Papi</h2>
          <span
            className={`badge ${papiConfigured ? 'badge-ok' : 'badge-warn'}`}
          >
            {papiConfigured ? 'Configuré' : 'Non configuré'}
          </span>
        </div>

        <p className="ps-help">
          Vous n'avez pas encore de compte Papi marchand ? Créez-en un sur{' '}
          <a
            href="https://app.papi.mg"
            target="_blank"
            rel="noreferrer"
          >
            app.papi.mg
          </a>{' '}
          puis copiez votre clé API et votre secret webhook ci-dessous.
          <br />
          <strong>
            La configuration Papi n'est pas obligatoire : elle n'est
            requise que si vous souhaitez vendre vos produits en ligne sur
            la vitrine commune.
          </strong>
        </p>

        <form onSubmit={handleSave}>
          <div className="form-row">
            <label htmlFor="papi-api-key">Clé API Papi</label>
            <input
              id="papi-api-key"
              type="password"
              value={papiApiKey}
              onChange={(e) => setPapiApiKey(e.target.value)}
              placeholder={
                papiConfigured
                  ? 'Laisser vide pour conserver la clé actuelle'
                  : 'Coller votre clé API Papi'
              }
              autoComplete="off"
            />
          </div>

          <div className="form-row">
            <label htmlFor="papi-webhook">
              Secret webhook (optionnel mais recommandé)
            </label>
            <input
              id="papi-webhook"
              type="password"
              value={papiWebhookSecret}
              onChange={(e) => setPapiWebhookSecret(e.target.value)}
              placeholder={
                papiConfigured
                  ? 'Laisser vide pour conserver le secret actuel'
                  : 'Secret webhook fourni par Papi'
              }
              autoComplete="off"
            />
          </div>

          <div className="form-row">
            <label htmlFor="papi-env">Environnement</label>
            <select
              id="papi-env"
              value={papiEnvironment}
              onChange={(e) => setPapiEnvironment(e.target.value)}
            >
              {ENV_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="ps-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={saving || !papiApiKey.trim() && !papiWebhookSecret.trim() && !papiEnvironment}
            >
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>

            <button
              type="button"
              className="btn-secondary"
              onClick={handleTest}
              disabled={!papiConfigured || testing}
            >
              {testing ? 'Test…' : 'Tester la connexion'}
            </button>

            {papiConfigured && (
              <button
                type="button"
                className="btn-danger"
                onClick={handleClear}
                disabled={saving}
              >
                Supprimer la configuration
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="ps-card">
        <div className="ps-card-header">
          <h2>Vitrine publique MIHAJA</h2>
          <span
            className={`badge ${vitrineActive ? 'badge-ok' : 'badge-warn'}`}
          >
            {vitrineActive ? 'Active' : 'Inactive'}
          </span>
        </div>

        <p className="ps-help">
          Une fois votre compte Papi connecté, vous pouvez activer la
          vitrine commune MIHAJA : vos produits seront visibles par tous
          les visiteurs, et vos clients pourront payer en ligne via votre
          compte marchand Papi.
        </p>

        {!papiConfigured ? (
          <div className="alert alert-info">
            Configurez d'abord votre compte marchand Papi pour pouvoir
            activer la vitrine.
          </div>
        ) : (
          <div className="vitrine-toggle">
            <label className="switch">
              <input
                type="checkbox"
                checked={vitrineEnabled}
                disabled={vitrineToggleBusy}
                onChange={(e) => handleVitrineToggle(e.target.checked)}
              />
              <span className="slider" />
            </label>
            <span>
              {vitrineEnabled
                ? 'Vos produits sont publiés sur la vitrine.'
                : 'Vos produits ne sont pas publiés.'}
            </span>
          </div>
        )}
      </section>

      <section className="ps-card">
        <h2>Méthodes de paiement acceptées</h2>
        <p className="ps-help">
          Sur la vitrine, vos clients pourront choisir parmi les
          opérateurs ci-dessous (configurés par Papi pour votre compte
          marchand) :
        </p>
        <ul className="methods-list">
          {PAYMENT_METHODS.map((m) => (
            <li key={m.value}>{m.label}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}