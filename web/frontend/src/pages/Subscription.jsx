// src/pages/Subscription.jsx
import React, { useEffect, useState, useRef } from 'react';
import { toast } from 'react-toastify';
import { subscriptionService, papiService, plansService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Subscription.css';

const formatPlanPrice = (prix) => {
  if (prix === 0) return 'Gratuit';
  return `${Number(prix).toLocaleString('fr-FR')} Ar`;
};

const formatPlanDuration = (duree_jours) => {
  if (duree_jours === -1) return 'pour toujours';
  return `/ ${duree_jours} jours`;
};

const formatPlanLimits = (max_utilisateurs, max_employees) => {
  const fmt = (v) => (v === -1 ? 'Illimité' : v);
  if (max_utilisateurs === -1 && max_employees === -1) {
    return 'Utilisateurs et employés illimités';
  }
  if (max_employees === 0) {
    return `${fmt(max_utilisateurs)} utilisateur`;
  }
  return `${fmt(max_utilisateurs)} utilisateur${max_utilisateurs > 1 ? 's' : ''} / ${fmt(max_employees)} employé${max_employees > 1 ? 's' : ''}`;
};

const PLAN_COLORS = {
  gratuit: '#6e9b79',
  starter: '#3b82f6',
  pro: '#d4af37',
  enterprise: '#111111',
};

const PLAN_FEATURES = {
  gratuit: [
    '1 utilisateur (admin seul)',
    'Support email',
  ],
  starter: [
    '3 utilisateurs (admin + 2 employés)',
    'Support prioritaire',
    'Statistiques basiques',
  ],
  pro: [
    '7 utilisateurs (admin + 6 employés)',
    'Support dédié',
    'Modules presque complets',
    'IA incluse',
  ],
  enterprise: [
    'Utilisateurs et employés illimités',
    'Support 24/7',
    'Tous modules',
    'SLA garanti',
    'Formation',
  ],
};

const PAYMENT_METHODS = [
  { id: 'especes', value: 'ESPECES', nom: 'Espèces' },
  { id: 'virement', value: 'VIREMENT', nom: 'Virement bancaire' },
  { id: 'cheque', value: 'CHEQUE', nom: 'Chèque' },
  { id: 'mvola', value: 'MVOLA', nom: 'MVola' },
  { id: 'orange_money', value: 'ORANGE_MONEY', nom: 'Orange Money' },
  { id: 'airtel_money', value: 'AIRTEL_MONEY', nom: 'Airtel Money' },
];

const getStatusBadge = (statut) => {
  const normalized = (statut || '').toUpperCase();
  if (normalized === 'ACTIF' || normalized === 'ACTIVE') return 'success';
  if (normalized === 'EN_ATTENTE' || normalized === 'PENDING') return 'warning';
  if (normalized === 'EXPIRE' || normalized === 'EXPIRED') return 'danger';
  return 'info';
};

const getPaymentStatusBadge = (statut) => {
  const normalized = (statut || '').toLowerCase();
  if (normalized === 'succes' || normalized === 'success') return 'success';
  if (normalized === 'echec' || normalized === 'failed') return 'danger';
  if (normalized === 'en_attente' || normalized === 'pending') return 'warning';
  if (normalized === 'traitement' || normalized === 'processing') return 'info';
  if (normalized === 'annule' || normalized === 'cancelled') return 'danger';
  if (normalized === 'expiré' || normalized === 'expired') return 'danger';
  return 'info';
};

const Subscription = () => {
  const { user, tenant, fetchSubscriptionStatus } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [historique, setHistorique] = useState([]);
  const [loading, setLoading] = useState(true);
  const [historiqueLoading, setHistoriqueLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('MVOLA');
  const [papiPayments, setPapiPayments] = useState([]);
  const [showOfflineModal, setShowOfflineModal] = useState(false);
  const [offlinePayment, setOfflinePayment] = useState(null);

  const [canRenew, setCanRenew] = useState(false);
  const [tenantSummary, setTenantSummary] = useState(null);
  const [plans, setPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);

  const paymentWindowRef = useRef(null);
  const messageHandlerRef = useRef(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subRes, histRes] = await Promise.all([
        subscriptionService.getMonAbonnement().catch(() => ({ data: null })),
        subscriptionService.getMonHistorique().catch(() => ({ data: [] })),
      ]);
      setSubscription(subRes.data?.abonnement ?? null);
      setCanRenew(Boolean(subRes.data?.can_renew));
      setTenantSummary(subRes.data?.tenant || null);
      setHistorique(histRes.data?.abonnements || histRes.data || []);
      fetchSubscriptionStatus();
    } catch (err) {
      console.error('Error fetching subscription data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlans = async () => {
    try {
      setPlansLoading(true);
      const response = await plansService.getPublicPlans();
      const list = response?.data?.plans || response?.plans || [];
      setPlans(list);
    } catch (err) {
      console.error('Error fetching plans:', err);
    } finally {
      setPlansLoading(false);
    }
  };

  const fetchPapiPayments = async () => {
    try {
      const res = await papiService.getPayments();
      setPapiPayments(res.data?.payments || res.data || []);
    } catch (err) {
      console.error('Error fetching Papi payments:', err);
    }
  };

  useEffect(() => {
    fetchData();
    fetchPlans();
    fetchPapiPayments();
  }, []);

  const handleDemander = async (planId) => {
    try {
      setActionLoading(true);
      const response = await subscriptionService.demander({ plan: planId });
      toast.success('Demande d\'abonnement envoyée');
      setSubscription(response.data?.abonnement || response.data);
      fetchSubscriptionStatus();
    } catch (err) {
      console.error('Error requesting subscription:', err);
      const msg = err.response?.data?.message || 'Échec de la demande';
      toast.error(msg);
    } finally {
      setActionLoading(false);
      setSelectedPlan(null);
    }
  };

  const teardownPaymentMessageListener = () => {
    if (messageHandlerRef.current) {
      window.removeEventListener('message', messageHandlerRef.current);
      messageHandlerRef.current = null;
    }
  };

  const onPaymentSuccessMessage = () => {
    toast.success('Paiement confirmé !');
    fetchData();
    fetchSubscriptionStatus();
    fetchPapiPayments();
    teardownPaymentMessageListener();
    if (paymentWindowRef.current && !paymentWindowRef.current.closed) {
      paymentWindowRef.current.close();
    }
    paymentWindowRef.current = null;
    setShowPaymentModal(false);
  };

  const setupPaymentMessageListener = () => {
    teardownPaymentMessageListener();
    messageHandlerRef.current = function (event) {
      if (event.origin !== 'https://payment-form.papi.mg') return;
      if (event.source !== paymentWindowRef.current) return;
      if (!event.data || event.data.type !== 'PAYMENT_STATUS') return;
      onPaymentSuccessMessage();
    };
    window.addEventListener('message', messageHandlerRef.current);
  };

  const handlePayer = async (subId) => {
    if (!selectedPaymentMethod) {
      toast.error('Veuillez sélectionner un mode de paiement');
      return;
    }

    try {
      setActionLoading(true);
      const response = await papiService.createSubscriptionPayment(subId, selectedPaymentMethod, true);
      const payload = response.data || response;
      const paymentLink = payload.payment_link;
      const isOffline = payload.is_offline;

      if (isOffline) {
        setOfflinePayment(payload);
        setShowPaymentModal(false);
        setShowOfflineModal(true);
        fetchPapiPayments();
        fetchData();
        fetchSubscriptionStatus();
        return;
      }

      if (!paymentLink) {
        toast.error('Lien de paiement introuvable');
        return;
      }

      setShowPaymentModal(false);

      paymentWindowRef.current = window.open(
        paymentLink,
        'payment-form-window',
        'width=500,height=700'
      );

      if (!paymentWindowRef.current) {
        toast.error('Veuillez autoriser les pop-ups pour effectuer le paiement');
        return;
      }

      setupPaymentMessageListener();

      const checkClosed = setInterval(() => {
        if (paymentWindowRef.current && paymentWindowRef.current.closed) {
          clearInterval(checkClosed);
          teardownPaymentMessageListener();
          paymentWindowRef.current = null;
          fetchData();
          fetchSubscriptionStatus();
          fetchPapiPayments();
        }
      }, 1000);

    } catch (err) {
      console.error('Error creating Papi payment:', err);
      const msg = err.response?.data?.message || 'Échec de l\'initialisation du paiement';
      toast.error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRenouveler = async (subId) => {
    try {
      setActionLoading(true);
      await subscriptionService.renouveler(subId);
      toast.success('Abonnement renouvelé');
      fetchData();
      fetchSubscriptionStatus();
    } catch (err) {
      console.error('Error renewing subscription:', err);
      const msg = err.response?.data?.message || 'Échec du renouvellement';
      toast.error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'Indian/Antananarivo',
    });
  };

  const normalizedStatus = (subscription?.statut || '').toUpperCase();
  const isExpired = normalizedStatus === 'EXPIRE';
  const isPending = normalizedStatus === 'EN_ATTENTE';
  const isActive = normalizedStatus === 'ACTIF' || normalizedStatus === 'ACTIVE';

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement de l'abonnement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container subscription-page">
      <div className="page-header">
        <div>
          <h1>Abonnement</h1>
          <p>Gérez votre abonnement et vos facturations</p>
        </div>
      </div>

      {subscription && (
        <div className={`card subscription-status-card subscription-status-card--${subscription.statut?.toLowerCase() || 'default'}`}>
          <div className="subscription-status-card__header">
            <div>
              <h2>Abonnement actuel</h2>
              <span className={`badge ${getStatusBadge(subscription.statut)}`}>
                {subscription.statut || 'INCONNU'}
              </span>
            </div>
            {subscription.plan && <span className="subscription-plan-name">{subscription.plan}</span>}
          </div>
          <div className="subscription-status-card__details">
            <div className="stat-card">
              <div className="stat-label">Date de début</div>
              <div className="stat-value">{formatDate(subscription.date_debut)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Date de fin</div>
              <div className="stat-value">{formatDate(subscription.date_fin)}</div>
            </div>
            {subscription.montant != null && (
              <div className="stat-card">
                <div className="stat-label">Montant</div>
                <div className="stat-value">{Number(subscription.montant).toLocaleString('fr-FR')} Ar</div>
              </div>
            )}
            {subscription.max_utilisateurs != null && (
              <div className="stat-card">
                <div className="stat-label">Limite utilisateurs</div>
                <div className="stat-value">
                  {subscription.max_utilisateurs === -1 ? 'Illimité' : subscription.max_utilisateurs}
                </div>
              </div>
            )}
            {subscription.max_employees != null && (
              <div className="stat-card">
                <div className="stat-label">Limite employés</div>
                <div className="stat-value">
                  {subscription.max_employees === -1 ? 'Illimité' : subscription.max_employees}
                </div>
              </div>
            )}
            {tenantSummary && subscription.max_utilisateurs != null && (
              <div className="stat-card">
                <div className="stat-label">Utilisateurs utilisés</div>
                <div className="stat-value">
                  {tenantSummary.users_count ?? '-'} / {subscription.max_utilisateurs === -1 ? 'Illimité' : subscription.max_utilisateurs}
                </div>
              </div>
            )}
            {tenantSummary && subscription.max_employees != null && (
              <div className="stat-card">
                <div className="stat-label">Employés utilisés</div>
                <div className="stat-value">
                  {tenantSummary.employees_count ?? '-'} / {subscription.max_employees === -1 ? 'Illimité' : subscription.max_employees}
                </div>
              </div>
            )}
          </div>
          {isPending && canRenew && (
            <div className="subscription-status-card__actions">
              <button
                className="btn-primary"
                onClick={() => setShowPaymentModal(true)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Traitement...' : 'Payer maintenant'}
              </button>
            </div>
          )}
          {(isExpired || isActive) && canRenew && (
            <div className="subscription-status-card__actions">
              <button
                className="btn-secondary"
                onClick={() => handleRenouveler(subscription.id)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Traitement...' : 'Renouveler'}
              </button>
            </div>
          )}
        </div>
      )}

      {(!subscription || isExpired) && canRenew ? (
        <section className="subscription-plans-section">
          <h3 style={{ marginBottom: '18px', fontSize: '18px', fontWeight: 700 }}>
            {isExpired ? 'Choisissez un nouveau plan' : 'Choisissez votre plan'}
          </h3>
          {plansLoading ? (
            <div className="loading-screen">
              <div className="spinner-large"></div>
              <p>Chargement des plans...</p>
            </div>
          ) : (
            <div className="subscription-plans-grid">
                {plans.map((plan) => {
                  const couleur = PLAN_COLORS[plan.code] || '#6e9b79';
                  const features = PLAN_FEATURES[plan.code] || [];
                  return (
                    <div key={plan.code} className="subscription-plan-card" style={{ borderTop: `3px solid ${couleur}` }}>
                      <div className="subscription-plan-card__header">
                        <h4>{plan.label}</h4>
                        <div className="subscription-plan-card__price">
                          <span className="subscription-plan-card__amount">{formatPlanPrice(plan.prix)}</span>
                          {plan.prix > 0 && <span className="subscription-plan-card__period">{formatPlanDuration(plan.duree_jours)}</span>}
                        </div>
                      </div>
                      <p className="subscription-plan-card__limits">{formatPlanLimits(plan.max_utilisateurs, plan.max_employees)}</p>
                      <ul className="subscription-plan-card__features">
                        {features.map((feature, idx) => (
                          <li key={idx}>{feature}</li>
                        ))}
                      </ul>
                      <button
                        className="btn-primary subscription-plan-card__cta"
                        onClick={() => handleDemander(plan.code)}
                        disabled={actionLoading || selectedPlan === plan.code}
                        style={{ backgroundColor: couleur }}
                      >
                        {selectedPlan === plan.code ? 'Traitement...' : plan.prix === 0 ? 'Commencer' : 'S\'abonner'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )
      : null}

      {papiPayments.length > 0 && (
        <div className="card full-width" style={{ marginTop: '32px' }}>
          <h3 style={{ marginBottom: '18px', fontSize: '18px', fontWeight: 700 }}>
            Historique des paiements
          </h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Référence</th>
                  <th>Méthode</th>
                  <th>Montant</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {papiPayments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{payment.created_at ? formatDate(payment.created_at) : '-'}</td>
                    <td>{payment.external_reference || payment.reference || `#${payment.id}`}</td>
                    <td>{payment.payment_method || '-'}</td>
                    <td>{Number(payment.montant || 0).toLocaleString('fr-FR')} Ar</td>
                    <td>
                      <span className={`badge ${getPaymentStatusBadge(payment.statut)}`}>
                        {payment.statut || 'INCONNU'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showPaymentModal && (
        <div className="modal-overlay" onClick={() => setShowPaymentModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Payer par voie électronique</h2>
              <button onClick={() => setShowPaymentModal(false)} className="btn-close">×</button>
            </div>
            <div className="modal-body">
              {subscription && (
                <div style={{ marginBottom: '20px', padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
                  <p><strong>Plan:</strong> {subscription.plan}</p>
                  <p><strong>Montant:</strong> {Number(subscription.montant).toLocaleString('mg-MG')} Ar</p>
                </div>
              )}
              <div className="form-group">
                <label>Mode de paiement *</label>
                <div className="payment-methods-grid">
                  {PAYMENT_METHODS.map((method) => (
                    <div
                      key={method.id}
                      onClick={() => setSelectedPaymentMethod(method.value)}
                      style={{
                        padding: '12px',
                        border: `2px solid ${selectedPaymentMethod === method.value ? '#3b82f6' : '#e5e7eb'}`,
                        borderRadius: '8px',
                        cursor: 'pointer',
                        textAlign: 'center',
                        background: selectedPaymentMethod === method.value ? '#eff6ff' : '#fff',
                      }}
                    >
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>{method.nom}</div>
                    </div>
                  ))}
                </div>
              </div>
              <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '12px' }}>
                Vous serez redirigé vers la page de paiement sécurisée de Papi.
              </p>
            </div>
            <div className="modal-footer">
              <button type="button" onClick={() => setShowPaymentModal(false)} className="btn-secondary">
                Annuler
              </button>
              <button
                type="button"
                onClick={() => handlePayer(subscription.id)}
                className="btn-primary"
                disabled={actionLoading || !selectedPaymentMethod}
              >
                {actionLoading ? 'Traitement...' : 'Payer maintenant'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showOfflineModal && offlinePayment && (
        <div className="modal-overlay" onClick={() => setShowOfflineModal(false)}>
          <div className="modal modal--offline" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Bulletin de paiement hors ligne</h2>
              <button onClick={() => setShowOfflineModal(false)} className="btn-close">×</button>
            </div>
            <div className="modal-body">
              <div className="offline-bulletin">
                <div className="offline-bulletin__row">
                  <span>Référence</span>
                  <strong className="offline-bulletin__ref">{offlinePayment.reference}</strong>
                </div>
                <div className="offline-bulletin__row">
                  <span>Mode</span>
                  <strong>{offlinePayment.payment?.payment_method || selectedPaymentMethod}</strong>
                </div>
                <div className="offline-bulletin__row">
                  <span>Montant</span>
                  <strong>{Number(offlinePayment.payment?.montant || subscription?.montant || 0).toLocaleString('mg-MG')} Ar</strong>
                </div>
                <p className="offline-bulletin__instructions">
                  {offlinePayment.instructions}
                </p>
                <p className="offline-bulletin__note">
                  Votre paiement est enregistré et passe en <strong>attente de confirmation</strong>.
                  Conservez la référence ci-dessus pour le dépôt.
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" onClick={() => setShowOfflineModal(false)} className="btn-primary">
                J'ai compris
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Subscription;
