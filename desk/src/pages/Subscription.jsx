// src/pages/Subscription.jsx
import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { subscriptionService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Subscription.css';

const PLANS = [
  {
    id: 'gratuit',
    nom: 'Gratuit',
    prix: 0,
    periode: 'pour toujours',
    limites: '1 produit, 10 clients/mois',
    couleur: '#6e9b79',
    features: ['Catalogue limité', 'Support email', '1 utilisateur'],
  },
  {
    id: 'starter',
    nom: 'Starter',
    prix: 29,
    periode: '/ mois',
    limites: '50 produits, 100 clients/mois',
    couleur: '#3b82f6',
    features: ['Catalogue étendu', 'Support prioritaire', '3 utilisateurs', 'Statistiques basiques'],
  },
  {
    id: 'pro',
    nom: 'Pro',
    prix: 79,
    periode: '/ mois',
    limites: '200 produits, clients illimités',
    couleur: '#d4af37',
    features: ['Catalogue illimité', 'Support dédié', '10 utilisateurs', 'IA incluse', 'API access'],
  },
  {
    id: 'enterprise',
    nom: 'Enterprise',
    prix: 199,
    periode: '/ mois',
    limites: 'Catalogue illimité, tout inclus',
    couleur: '#111111',
    features: ['Tout Pro inclus', 'Support 24/7', 'Utilisateurs illimités', 'SLA garanti', 'Formation'],
  },
];

const getStatusBadge = (statut) => {
  const normalized = (statut || '').toUpperCase();
  if (normalized === 'ACTIF' || normalized === 'ACTIVE') return 'success';
  if (normalized === 'EN_ATTENTE' || normalized === 'PENDING') return 'warning';
  if (normalized === 'EXPIRE' || normalized === 'EXPIRED') return 'danger';
  return 'info';
};

const Subscription = () => {
  const { user, fetchSubscriptionStatus } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [historique, setHistorique] = useState([]);
  const [loading, setLoading] = useState(true);
  const [historiqueLoading, setHistoriqueLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subRes, histRes] = await Promise.all([
        subscriptionService.getMonAbonnement().catch(() => ({ data: null })),
        subscriptionService.getMonHistorique().catch(() => ({ data: [] })),
      ]);
      setSubscription(subRes.data?.abonnement ?? null);
      setHistorique(histRes.data?.abonnements || histRes.data || []);
    } catch (err) {
      console.error('Error fetching subscription data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
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

  const handlePayer = async (subId) => {
    try {
      setActionLoading(true);
      await subscriptionService.payer(subId, {});
      toast.success('Paiement simulé avec succès');
      fetchData();
      fetchSubscriptionStatus();
    } catch (err) {
      console.error('Error processing payment:', err);
      const msg = err.response?.data?.message || 'Échec du paiement';
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
    return new Date(dateStr).toLocaleDateString('mg-MG');
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
            {subscription.montant && (
              <div className="stat-card">
                <div className="stat-label">Montant</div>
                <div className="stat-value">{Number(subscription.montant).toFixed(2)} Ar</div>
              </div>
            )}
          </div>
          {(isPending || isExpired || isActive) && (
            <div className="subscription-status-card__actions">
              {isPending && (
                <button 
                  className="btn-primary" 
                  onClick={() => handlePayer(subscription.id)}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Traitement...' : 'Payer maintenant'}
                </button>
              )}
              {(isExpired || isActive) && (
                <button 
                  className="btn-secondary" 
                  onClick={() => handleRenouveler(subscription.id)}
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Traitement...' : 'Renouveler'}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {!subscription || isExpired ? (
        <section className="subscription-plans-section">
          <h3 style={{ marginBottom: '18px', fontSize: '18px', fontWeight: 700 }}>
            {isExpired ? 'Choisissez un nouveau plan' : 'Choisissez votre plan'}
          </h3>
          <div className="subscription-plans-grid">
            {PLANS.map((plan) => (
              <div key={plan.id} className="subscription-plan-card" style={{ borderTop: `3px solid ${plan.couleur}` }}>
                <div className="subscription-plan-card__header">
                  <h4>{plan.nom}</h4>
                  <div className="subscription-plan-card__price">
                    <span className="subscription-plan-card__amount">{plan.prix === 0 ? 'Gratuit' : `${plan.prix} Ar`}</span>
                    {plan.prix > 0 && <span className="subscription-plan-card__period">{plan.periode}</span>}
                  </div>
                </div>
                <p className="subscription-plan-card__limits">{plan.limites}</p>
                <ul className="subscription-plan-card__features">
                  {plan.features.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  ))}
                </ul>
                <button
                  className="btn-primary subscription-plan-card__cta"
                  onClick={() => handleDemander(plan.id)}
                  disabled={actionLoading || selectedPlan === plan.id}
                  style={{ backgroundColor: plan.couleur }}
                >
                  {selectedPlan === plan.id ? 'Traitement...' : plan.prix === 0 ? 'Commencer' : 'S\'abonner'}
                </button>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {historique.length > 0 && (
        <div className="card full-width" style={{ marginTop: '32px' }}>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Date début</th>
                  <th>Date fin</th>
                  <th>Montant</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {historique.map((item) => (
                  <tr key={item.id}>
                    <td>{item.plan || '-'}</td>
                    <td>{formatDate(item.date_debut)}</td>
                    <td>{formatDate(item.date_fin)}</td>
                    <td>{Number(item.montant || 0).toFixed(2)} Ar</td>
                    <td>
                      <span className={`badge ${getStatusBadge(item.statut)}`}>
                        {item.statut || 'INCONNU'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Subscription;
