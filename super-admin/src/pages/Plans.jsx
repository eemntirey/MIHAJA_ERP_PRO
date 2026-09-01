import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { superAdminPlanService } from '../services/api';

const Plans = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingPlan, setEditingPlan] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    prix: '',
    duree_jours: '',
  });

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await superAdminPlanService.getAll();
      setPlans(response.data?.plans || response.data || []);
    } catch {
      toast.error('Échec du chargement des plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  useEffect(() => {
    const handlePlanUpdated = (e) => {
      const updated = e.detail;
      if (updated && updated.code) {
        setPlans(prev => prev.map(p => p.code === updated.code ? { ...p, ...updated } : p));
      } else {
        fetchPlans();
      }
    };
    window.addEventListener('realtime:plan:updated', handlePlanUpdated);
    return () => window.removeEventListener('realtime:plan:updated', handlePlanUpdated);
  }, []);

  const openEditModal = (plan) => {
    setEditingPlan(plan);
    setFormData({
      prix: plan.prix,
      duree_jours: plan.duree_jours,
    });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingPlan(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!editingPlan) return;

    try {
      setSaving(true);
      await superAdminPlanService.update(editingPlan.code, {
        prix: parseInt(formData.prix, 10),
        duree_jours: parseInt(formData.duree_jours, 10),
      });
      toast.success('Plan mis à jour');
      closeModal();
      fetchPlans();
    } catch (err) {
      const msg = err.response?.data?.message || 'Échec de la mise à jour';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Plans</h1>
          <p>Architecture des abonnements</p>
        </div>
        <button onClick={fetchPlans} className="btn-secondary" disabled={loading}>
          Rafraîchir
        </button>
      </div>

      {loading ? (
        <div className="loading-screen">
          <div className="spinner-large"></div>
          <p>Chargement des plans...</p>
        </div>
      ) : (
        <div className="stats-grid">
          {plans.map((plan) => (
            <div className="stat-card" key={plan.code}>
              <div className="stat-label">{plan.label}</div>
              <div className="stat-value">{plan.prix === 0 ? 'Gratuit' : `${plan.prix} Ar`}</div>
              <div style={{ marginTop: '8px', color: 'var(--color-text-muted)', fontSize: '14px' }}>
                {plan.tenants_count} tenant{plan.tenants_count !== 1 ? 's' : ''}
              </div>
              <div style={{ marginTop: '4px', color: 'var(--color-text-dim)', fontSize: '12px' }}>
                Durée: {plan.duree_jours > 0 ? `${plan.duree_jours} jours` : 'Illimité'}
              </div>
              <div style={{ marginTop: '12px' }}>
                <button onClick={() => openEditModal(plan)} className="btn-small btn-edit" title="Modifier">
                  <i className="ti ti-edit" aria-hidden="true" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Modifier le plan: {editingPlan?.label}</h2>
              <button type="button" className="btn-close" onClick={closeModal}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="prix">Prix (Ar)</label>
                  <input
                    id="prix"
                    name="prix"
                    type="number"
                    min="0"
                    value={formData.prix}
                    onChange={handleChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="duree_jours">Durée (jours)</label>
                  <input
                    id="duree_jours"
                    name="duree_jours"
                    type="number"
                    value={formData.duree_jours}
                    onChange={handleChange}
                    required
                  />
                  <small style={{ color: 'var(--color-text-dim)' }}>-1 pour illimité</small>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal}>Annuler</button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Enregistrement...' : 'Enregistrer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Plans;
