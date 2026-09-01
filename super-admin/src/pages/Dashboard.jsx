import React, { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useSuperAdminAuth } from '../contexts/SuperAdminAuthContext';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { superAdminDashboardService, superAdminTenantService } from '../services/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const Dashboard = () => {
  const { user } = useSuperAdminAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recentTenants, setRecentTenants] = useState([]);

  const fetchAll = async () => {
    if (!user) return;

    try {
      setLoading(true);
      const [statsRes, tenantsRes] = await Promise.all([
        superAdminDashboardService.getStats(),
        superAdminTenantService.getAll({ per_page: 5 }),
      ]);
      setStats(statsRes.data || statsRes);
      setRecentTenants(tenantsRes.data?.tenants || []);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      toast.error('Échec du chargement du tableau de bord');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  useEffect(() => {
    const handleTenantUpdated = () => {
      fetchAll();
    };
    const handleUserUpdated = () => {
      fetchAll();
    };
    const handleSubscriptionUpdated = () => {
      fetchAll();
    };
    window.addEventListener('realtime:tenant:updated', handleTenantUpdated);
    window.addEventListener('realtime:user:updated', handleUserUpdated);
    window.addEventListener('realtime:subscription:updated', handleSubscriptionUpdated);
    return () => {
      window.removeEventListener('realtime:tenant:updated', handleTenantUpdated);
      window.removeEventListener('realtime:user:updated', handleUserUpdated);
      window.removeEventListener('realtime:subscription:updated', handleSubscriptionUpdated);
    };
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner-large"></div>
        <p>Chargement du tableau de bord...</p>
      </div>
    );
  }

  const tenantsChartData = {
    labels: ['Actifs', 'Suspendus', 'En essai'],
    datasets: [
      {
        data: [stats?.tenants_actifs || 0, stats?.tenants_suspendus || 0, stats?.tenants_essai || 0],
        backgroundColor: ['rgba(34, 197, 94, 0.7)', 'rgba(239, 68, 68, 0.7)', 'rgba(245, 158, 11, 0.7)'],
        borderColor: ['#22c55e', '#ef4444', '#f59e0b'],
        borderWidth: 1,
      },
    ],
  };

  const evolutionChartData = {
    labels: stats?.evolution_tenants?.map((e) => new Date(e.date).toLocaleDateString('fr-FR', { weekday: 'short' })) || [],
    datasets: [
      {
        label: 'Nouveaux tenants',
        data: stats?.evolution_tenants?.map((e) => e.count) || [],
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const plansChartData = {
    labels: stats?.abonnements_par_plan?.map((p) => p.plan) || [],
    datasets: [
      {
        data: stats?.abonnements_par_plan?.map((p) => p.count) || [],
        backgroundColor: [
          'rgba(59, 130, 246, 0.7)',
          'rgba(34, 197, 94, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(168, 85, 247, 0.7)',
        ],
        borderColor: ['#3b82f6', '#22c55e', '#f59e0b', '#a855f7'],
        borderWidth: 1,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#94a3b8' },
      },
      y: {
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#94a3b8' },
      },
    },
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#94a3b8', padding: 16 },
      },
    },
  };

  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#94a3b8' },
      },
      y: {
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#94a3b8', beginAtZero: true },
      },
    },
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Tableau de bord</h1>
          <p>Vue d'ensemble de la plateforme MIHAJA ERP</p>
        </div>
        <button onClick={fetchAll} className="btn-secondary" disabled={loading}>
          Rafraîchir
        </button>
      </div>

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total tenants</div>
              <div className="stat-value">{stats.total_tenants}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Tenants actifs</div>
              <div className="stat-value" style={{ color: 'var(--color-success)' }}>{stats.tenants_actifs}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Tenants suspendus</div>
              <div className="stat-value" style={{ color: 'var(--color-danger)' }}>{stats.tenants_suspendus}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">En essai</div>
              <div className="stat-value" style={{ color: 'var(--color-warning)' }}>{stats.tenants_essai}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Abonnements actifs</div>
              <div className="stat-value" style={{ color: 'var(--color-success)' }}>{stats.abonnements_actifs}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Expire bientôt (30j)</div>
              <div className="stat-value" style={{ color: 'var(--color-warning)' }}>{stats.abonnements_expires_bientot}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Revenus totaux</div>
              <div className="stat-value">{stats.revenus_total?.toLocaleString('fr-FR')} Ar</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Revenus ce mois</div>
              <div className="stat-value" style={{ color: 'var(--color-info)' }}>{stats.revenus_mois?.toLocaleString('fr-FR')} Ar</div>
            </div>
          </div>

          <div className="dashboard-charts">
            <div className="chart-card">
              <h3 className="chart-title">Évolution des inscriptions (7 jours)</h3>
              <div className="chart-container">
                <Line data={evolutionChartData} options={lineOptions} />
              </div>
            </div>

            <div className="chart-card">
              <h3 className="chart-title">Répartition des tenants</h3>
              <div className="chart-container">
                <Doughnut data={tenantsChartData} options={doughnutOptions} />
              </div>
            </div>

            <div className="chart-card">
              <h3 className="chart-title">Abonnements par plan</h3>
              <div className="chart-container">
                <Bar data={plansChartData} options={chartOptions} />
              </div>
            </div>
          </div>

          <div className="dashboard-secondary">
            <div className="card">
              <h3 className="section-title">Plateforme</h3>
              <div className="platform-stats">
                <div className="platform-stat">
                  <span className="platform-stat-value">{stats.total_utilisateurs}</span>
                  <span className="platform-stat-label">Utilisateurs</span>
                </div>
                <div className="platform-stat">
                  <span className="platform-stat-value">{stats.total_produits}</span>
                  <span className="platform-stat-label">Produits</span>
                </div>
                <div className="platform-stat">
                  <span className="platform-stat-value">{stats.total_ventes}</span>
                  <span className="platform-stat-label">Ventes</span>
                </div>
                <div className="platform-stat">
                  <span className="platform-stat-value">{stats.total_factures}</span>
                  <span className="platform-stat-label">Factures</span>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 className="section-title">Tenants récents</h3>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nom</th>
                      <th>Statut</th>
                      <th>Plan</th>
                      <th>Créé le</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTenants.length === 0 ? (
                      <tr><td colSpan="4" className="text-center text-muted">Aucun tenant</td></tr>
                    ) : recentTenants.map((t) => (
                      <tr key={t.id}>
                        <td>{t.nom}</td>
                        <td><span className={`badge ${t.statut === 'actif' ? 'badge-success' : 'badge-warning'}`}>{t.statut}</span></td>
                        <td>{t.plan}</td>
                        <td>{t.created_at ? new Date(t.created_at).toLocaleDateString('fr-FR') : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
