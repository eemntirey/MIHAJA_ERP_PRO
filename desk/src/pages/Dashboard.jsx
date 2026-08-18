import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext';
import { authService, clientService, dashboardService, productService, saleService, subscriptionService } from '../services/api';
import {
  buildChartGeometry,
  buildPreviousPeriodTotal,
  buildPriorities,
  buildSalesEvolution,
  buildSparklinePath,
  formatCurrency,
  formatCurrencyExact,
  formatDateRange,
  formatMonthYear,
  formatNumber,
  formatPercentageChange,
  formatTrendLabel,
  getSaleDate,
  getTodayTotal,
  normalizeCriticalStockAlerts,
  normalizeReceivables,
  normalizeRecentActivity,
  normalizeTopProducts,
  serializeDashboardCsv,
  toNumber,
} from './dashboard/dashboardUtils';
import './Dashboard.css';


const createEmptyDashboardState = () => ({
  stats: {
    products: 0,
    clients: 0,
    salesToday: 0,
    revenue: 0,
    stockAlerts: 0,
    criticalStockAlerts: null,
    todayRevenue: null,
    receivablesCount: 0,
    receivablesTotal: 0,
  },
  evolution: [],
  previousPeriodTotal: null,
  topProducts: [],
  recentActivity: [],
  priorities: [],
});


const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};


const DashboardHeader = ({ periodLabel, periodCaption, onExport, onRefresh, loading }) => (
  <header className="dashboard-header">
    <div className="dashboard-header__copy">
      <p className="dashboard-eyebrow">Vue opérationnelle / {periodCaption}</p>
      <h1>Tableau de bord</h1>
      <p className="dashboard-header__description">
        Une lecture claire de votre activité, du chiffre d’affaires aux opérations à traiter.
      </p>
    </div>

    <div className="dashboard-header__actions">
      <button type="button" className="dashboard-button dashboard-button--period" disabled>
        <i className="ti ti-calendar-event" aria-hidden="true" />
        <span>{periodLabel}</span>
        <i className="ti ti-chevron-down" aria-hidden="true" />
      </button>
      <button type="button" className="dashboard-button dashboard-button--outline" onClick={onExport}>
        <i className="ti ti-download" aria-hidden="true" />
        Exporter
      </button>
      <button
        type="button"
        className="dashboard-button dashboard-button--dark"
        onClick={onRefresh}
        disabled={loading}
        aria-busy={loading}
      >
        <i className={`ti ${loading ? 'ti-loader-2 dashboard-icon-spin' : 'ti-refresh'}`} aria-hidden="true" />
        {loading ? 'Actualisation...' : 'Actualiser'}
      </button>
    </div>
  </header>
);

const RevenueHero = ({ stats, evolution, trendPercentage, shouldReduceMotion }) => {
  const sparklinePath = useMemo(
    () => buildSparklinePath(evolution.map((day) => day.total)),
    [evolution]
  );

  return (
    <motion.article
      className="dashboard-revenue-hero"
      initial={shouldReduceMotion ? false : 'hidden'}
      animate="visible"
      variants={fadeUp}
      transition={{ duration: 0.35 }}
    >
      <div className="dashboard-revenue-hero__header">
        <div>
          <p className="dashboard-overline dashboard-overline--dark">Indicateur principal</p>
          <h2>CA du mois</h2>
        </div>
        <span className="dashboard-revenue-hero__icon" aria-hidden="true">
          <i className="ti ti-chart-line" />
        </span>
      </div>

      <div className="dashboard-revenue-hero__data">
        <div>
          <p className="dashboard-revenue-hero__amount">{formatCurrency(stats.revenue)}</p>
          <p className="dashboard-revenue-hero__trend">
            {trendPercentage === null ? (
              <span className="dashboard-trend dashboard-trend--muted">Pas de comparaison</span>
            ) : (
              <span className={`dashboard-trend${trendPercentage >= 0 ? '' : ' dashboard-trend--negative'}`}>
                <i className={`ti ${trendPercentage >= 0 ? 'ti-trending-up' : 'ti-trending-down'}`} aria-hidden="true" />
                {formatTrendLabel(trendPercentage)}
              </span>
            )}
            <span>{trendPercentage === null ? 'sur la période chargée' : 'vs période précédente'}</span>
          </p>
        </div>

        <svg
          className="dashboard-revenue-hero__sparkline"
          viewBox="0 0 128 64"
          role="img"
          aria-label="Tendance du chiffre d’affaires sur la période"
        >
          <path d={sparklinePath} />
          <circle cx="126" cy={sparklinePath === 'M2 52 L126 52' ? 52 : 8} r="3.5" />
        </svg>
      </div>
    </motion.article>
  );
};

const KpiCell = ({ icon, label, value, note, critical }) => (
  <div className="dashboard-kpi-cell">
    <span className="dashboard-kpi-cell__label">
      <i className={`ti ${icon}`} aria-hidden="true" />
      {label}
    </span>
    <div>
      <p className="dashboard-kpi-cell__value">
        {critical && <span className="dashboard-kpi-cell__critical-dot" aria-hidden="true" />}
        {value}
      </p>
      <p className="dashboard-kpi-cell__note">{note}</p>
    </div>
  </div>
);

const KpiStrip = ({ stats }) => (
  <div className="dashboard-kpi-strip" aria-label="Indicateurs clés">
    <KpiCell
      icon="ti-package"
      label="Produits"
      value={formatNumber(stats.products)}
      note="Catalogue actif"
    />
    <KpiCell
      icon="ti-users"
      label="Clients"
      value={formatNumber(stats.clients)}
      note="Comptes actifs"
    />
    <KpiCell
      icon="ti-shopping-cart"
      label="Ventes aujourd’hui"
      value={formatNumber(stats.salesToday)}
      note={stats.todayRevenue === null ? 'Montant non disponible' : `${formatCurrency(stats.todayRevenue)} générés`}
    />
    <KpiCell
      icon="ti-alert-circle"
      label="Alertes stock"
      value={formatNumber(stats.stockAlerts)}
      note={stats.criticalStockAlerts === null
        ? 'Détail indisponible'
        : `${formatNumber(stats.criticalStockAlerts)} critique${stats.criticalStockAlerts > 1 ? 's' : ''}`}
      critical={stats.stockAlerts > 0}
    />
  </div>
);

const RevenueChart = ({ geometry, evolution, onViewDetails, shouldReduceMotion }) => {
  const bestPoint = geometry.bestIndex >= 0 ? geometry.points[geometry.bestIndex] : null;
  const annotationLabel = bestPoint ? formatCurrencyExact(bestPoint.total) : '';
  const annotationWidth = Math.max(92, annotationLabel.length * 7 + 22);
  const annotationX = bestPoint
    ? Math.min(
      Math.max(bestPoint.x, geometry.left + annotationWidth / 2),
      geometry.right - annotationWidth / 2
    )
    : 0;

  return (
    <section className="dashboard-panel dashboard-chart-panel" aria-labelledby="sales-chart-title">
      <div className="dashboard-panel__header">
        <div>
          <div className="dashboard-panel__title-row">
            <h2 id="sales-chart-title">Évolution du chiffre d’affaires</h2>
            <span className="dashboard-panel__period">
              <span aria-hidden="true" />
              7 derniers jours
            </span>
          </div>
          <p>Les recettes quotidiennes de la période chargée.</p>
        </div>
        <Link className="dashboard-text-link" to="/sales" onClick={onViewDetails}>
          Voir le détail
          <i className="ti ti-arrow-up-right" aria-hidden="true" />
        </Link>
      </div>

      {evolution.length === 0 ? (
        <div className="dashboard-empty-state dashboard-empty-state--chart">
          <i className="ti ti-chart-line" aria-hidden="true" />
          <p>Aucune donnée de chiffre d’affaires disponible pour cette période.</p>
        </div>
      ) : (
        <div className="dashboard-chart-wrap">
           <svg
             className="dashboard-chart"
             viewBox={`0 0 ${geometry.width} ${geometry.height}`}
             role="img"
             aria-labelledby="sales-chart-title sales-chart-description"
           >
            <title id="sales-chart-description">Courbe du chiffre d’affaires sur les sept derniers jours</title>
            {geometry.grid.map((line) => (
              <g key={line.y}>
                <line className="dashboard-chart__grid" x1="52" x2="976" y1={line.y} y2={line.y} />
                <text className="dashboard-chart__axis" x="3" y={line.y + 4}>{line.label}</text>
              </g>
            ))}
            <motion.path
              className="dashboard-chart__area"
              d={geometry.areaPath}
              initial={shouldReduceMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            />
            <motion.path
              className="dashboard-chart__line"
              d={geometry.linePath}
              initial={shouldReduceMotion ? false : { pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
            {geometry.points.map((point) => (
              <motion.circle
                key={point.dateKey}
                className="dashboard-chart__point"
                cx={point.x}
                cy={point.y}
                r={point.dateKey === bestPoint?.dateKey ? 5 : 4.5}
                tabIndex="0"
                aria-label={`${point.label} : ${formatCurrencyExact(point.total)}`}
                initial={shouldReduceMotion ? false : { scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.25, delay: shouldReduceMotion ? 0 : 0.25 }}
              >
                <title>{`${point.label} : ${formatCurrencyExact(point.total)}`}</title>
              </motion.circle>
            ))}
            {bestPoint && (
              <g className="dashboard-chart__annotation" aria-hidden="true">
                <line x1={bestPoint.x} x2={bestPoint.x} y1={bestPoint.y} y2={Math.max(bestPoint.y - 28, 8)} />
                <rect
                  x={annotationX - annotationWidth / 2}
                  y={Math.max(bestPoint.y - 64, 2)}
                  width={annotationWidth}
                  height="24"
                  rx="2"
                />
                <text x={annotationX} y={Math.max(bestPoint.y - 48, 18)}>{annotationLabel}</text>
              </g>
            )}
            {geometry.points.map((point) => (
              <text className="dashboard-chart__axis dashboard-chart__axis--date" key={`${point.dateKey}-label`} x={point.x - 12} y="254">
                {point.label}
              </text>
            ))}
          </svg>
        </div>
      )}
    </section>
  );
};

const TopProductsTable = ({ products }) => (
  <article className="dashboard-panel dashboard-products-panel">
    <div className="dashboard-panel__header">
      <div>
        <p className="dashboard-overline">Performance catalogue</p>
        <h2>Top produits</h2>
      </div>
      <Link className="dashboard-text-link" to="/products">
        Tout voir
        <i className="ti ti-arrow-up-right" aria-hidden="true" />
      </Link>
    </div>

    {products.length === 0 ? (
      <div className="dashboard-empty-state">
        <i className="ti ti-package-off" aria-hidden="true" />
        <p>Aucune donnée produit disponible.</p>
      </div>
    ) : (
      <div className="dashboard-table-wrap">
        <table className="dashboard-products-table">
          <caption className="dashboard-visually-hidden">Classement des produits par quantité vendue</caption>
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Produit</th>
              <th scope="col">Qté</th>
              <th scope="col">Valeur</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product, index) => (
              <tr key={product.id}>
                <td className="dashboard-products-table__rank">{String(index + 1).padStart(2, '0')}</td>
                <th scope="row">{product.name}</th>
                <td>{formatNumber(product.quantity)}</td>
                <td className="dashboard-products-table__value">{formatCurrencyExact(product.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </article>
);

const ActivityTimeline = ({ activity }) => (
  <article className="dashboard-panel dashboard-activity-panel">
    <div className="dashboard-panel__header">
      <div>
        <p className="dashboard-overline">Flux en direct</p>
        <h2>Activité récente</h2>
      </div>
      <span className="dashboard-live-status"><span aria-hidden="true" />Live</span>
    </div>

    {activity.length === 0 ? (
      <div className="dashboard-empty-state">
        <i className="ti ti-activity-heartbeat" aria-hidden="true" />
        <p>Aucune activité récente.</p>
      </div>
    ) : (
      <div className="dashboard-timeline">
        <span className="dashboard-timeline__line" aria-hidden="true" />
        {activity.map((item) => (
          <div className="dashboard-timeline__item" key={item.id}>
            <span className={`dashboard-timeline__dot dashboard-timeline__dot--${item.tone}`} aria-hidden="true" />
            <div className="dashboard-timeline__content">
              <div className="dashboard-timeline__heading">
                <p>{item.title}</p>
                <time>{item.timeLabel}</time>
              </div>
              <p className="dashboard-timeline__meta">{item.meta}</p>
            </div>
          </div>
        ))}
      </div>
    )}
  </article>
);

const PriorityPanel = ({ priorities }) => (
  <aside className="dashboard-panel dashboard-priority-panel" aria-labelledby="dashboard-priorities-title">
    <div className="dashboard-panel__header">
      <div>
        <p className="dashboard-overline">Priorités</p>
        <h2 id="dashboard-priorities-title">À traiter cette semaine</h2>
      </div>
      <span className="dashboard-priority-panel__count">{String(priorities.length).padStart(2, '0')}</span>
    </div>

    <div className="dashboard-priorities">
      {priorities.map((priority, index) => (
        <div className={`dashboard-priority dashboard-priority--${priority.tone}`} key={priority.id}>
          <span className="dashboard-priority__icon" aria-hidden="true">
            <i className={`ti ${priority.icon}`} />
          </span>
          <div>
            <p className="dashboard-priority__title">{priority.title}</p>
            <p className="dashboard-priority__description">{priority.description}</p>
            <Link className="dashboard-priority__action" to={priority.href}>
              {index === 0 && priority.tone === 'critical' ? 'Voir le stock' : 'Ouvrir le suivi'}
              <i className="ti ti-arrow-up-right" aria-hidden="true" />
            </Link>
          </div>
        </div>
      ))}
    </div>
  </aside>
);

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, setUser, logout, hasRole } = useAuth();
  const shouldReduceMotion = useReducedMotion();
  const isSuperAdmin = hasRole('SUPER_ADMIN');
  const [dashboardState, setDashboardState] = useState(createEmptyDashboardState);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [
        dashboardResponse,
        productsResponse,
        clientsResponse,
        recentSalesResponse,
        allSalesResponse,
        topProductsResponse,
        alertsResponse,
      ] = await Promise.all([
        dashboardService.getStats().catch(() => ({ data: {} })),
        productService.getAll({ limit: 1 }).catch(() => ({ data: {} })),
        clientService.getAll({ limit: 1 }).catch(() => ({ data: {} })),
        saleService.getAll({ limit: 10 }).catch(() => ({ data: { ventes: [] } })),
        saleService.getAll({ limit: 100 }).catch(() => ({ data: { ventes: [] } })),
        dashboardService.getTopProducts().catch(() => ({ data: {} })),
        dashboardService.getAlerts().catch(() => ({ data: null })),
      ]);

      const dashboardData = dashboardResponse.data?.stats || {};
      const recentSales = recentSalesResponse.data?.ventes || [];
      const allSales = allSalesResponse.data?.ventes || recentSales;
      const evolution = buildSalesEvolution(allSales);
      const previousPeriodTotal = buildPreviousPeriodTotal(allSales);
      const receivables = normalizeReceivables(dashboardData);
      const stats = {
        products: toNumber(productsResponse.data?.total ?? dashboardData.total_produits),
        clients: toNumber(clientsResponse.data?.total ?? dashboardData.clients_actifs),
        salesToday: toNumber(dashboardData.ventes_aujourdhui),
        revenue: toNumber(dashboardData.ca_mois),
        stockAlerts: toNumber(dashboardData.alertes_stock),
        criticalStockAlerts: normalizeCriticalStockAlerts(alertsResponse.data),
        todayRevenue: getTodayTotal(allSales),
        receivablesCount: receivables.count,
        receivablesTotal: receivables.total,
      };
      const recentActivity = normalizeRecentActivity(recentSales);
      const priorities = buildPriorities({
        criticalStockAlerts: stats.criticalStockAlerts,
        stockAlerts: stats.stockAlerts,
        receivablesCount: stats.receivablesCount,
        todaySales: stats.salesToday,
        hasSalesData: allSales.length > 0,
      });

      setDashboardState({
        stats,
        evolution,
        previousPeriodTotal,
        topProducts: normalizeTopProducts(topProductsResponse.data),
        recentActivity,
        priorities,
      });
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      const message = 'Échec du chargement des données du tableau de bord';
      setError(message);
      setDashboardState(createEmptyDashboardState());
    } finally {
      setLoading(false);
      setHasLoaded(true);
    }
  }, []);

  const fetchSubscription = useCallback(async () => {
    try {
      setSubscriptionLoading(true);
      const response = await subscriptionService.getMonAbonnement();
      setSubscription(response.data?.abonnement || response.data || null);
    } catch (err) {
      console.error('Error fetching subscription:', err);
      setSubscription(null);
    } finally {
      setSubscriptionLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const chartGeometry = useMemo(
    () => buildChartGeometry(dashboardState.evolution),
    [dashboardState.evolution]
  );
  const trendPercentage = useMemo(
    () => formatPercentageChange(
      dashboardState.evolution.reduce((sum, day) => sum + day.total, 0),
      dashboardState.previousPeriodTotal
    ),
    [dashboardState.evolution, dashboardState.previousPeriodTotal]
  );
  const periodStart = dashboardState.evolution[0]?.dateKey;
  const periodEnd = dashboardState.evolution[dashboardState.evolution.length - 1]?.dateKey;
  const periodLabel = formatDateRange(periodStart, periodEnd);
  const periodCaption = formatMonthYear(periodEnd);

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('mg-MG');
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameForm, setNameForm] = useState({ prenom: '', nom: '' });

  const handleStartEditName = () => {
    setNameForm({
      prenom: user?.prenom || '',
      nom: user?.nom || '',
    });
    setIsEditingName(true);
  };

  const handleUpdateNameField = (field, value) => {
    setNameForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveName = async () => {
    try {
      const response = await authService.updateMe({
        prenom: nameForm.prenom,
        nom: nameForm.nom,
      });
      const updatedUser = response.data?.user || response.data;
      setUser((prev) => ({ ...(prev || {}), ...updatedUser }));
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setIsEditingName(false);
      toast.success('Profil mis à jour');
    } catch (err) {
      console.error('Error updating profile:', err);
      const msg = err.response?.data?.message || 'Échec de la mise à jour';
      toast.error(msg);
    }
  };

  const handleExport = () => {
    if (!hasLoaded) return;

    const csv = serializeDashboardCsv(dashboardState);
    const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `erp-pro-dashboard-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    toast.success('Export du tableau de bord prêt');
  };

  if (loading && !hasLoaded) {
    return (
      <div className="dashboard-page dashboard-page--loading" role="status" aria-live="polite">
        <div className="dashboard-loading__spinner" aria-hidden="true" />
        <p>Chargement du tableau de bord...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      <main className="dashboard-page__main">
        <div className="dashboard-page__content">
          <DashboardHeader
            periodLabel={periodLabel}
            periodCaption={periodCaption}
            onExport={handleExport}
            onRefresh={fetchDashboardData}
            loading={loading}
          />

          {error && (
            <div className="dashboard-error" role="alert">
              <div>
                <i className="ti ti-alert-triangle" aria-hidden="true" />
                <span>{error}</span>
              </div>
              <button type="button" onClick={fetchDashboardData} disabled={loading}>
                Réessayer
              </button>
            </div>
          )}

          {!subscriptionLoading && subscription && (
            <motion.section 
              className="dashboard-panel dashboard-subscription-widget"
              initial={shouldReduceMotion ? false : 'hidden'}
              animate="visible"
              variants={fadeUp}
              transition={{ duration: 0.35 }}
              aria-label="Statut de l'abonnement"
            >
              <div className="dashboard-subscription-widget__header">
                <div>
                  <p className="dashboard-overline dashboard-overline--dark">Abonnement</p>
                  <h2>{subscription.plan || 'Votre abonnement'}</h2>
                </div>
                <span className={`badge badge-${['ACTIF', 'ACTIVE', 'actif'].includes(subscription.statut) ? 'success' : 'warning'}`}>
                  {subscription.statut || 'INCONNU'}
                </span>
              </div>
              <div className="dashboard-subscription-widget__details">
                <div>
                  <p className="dashboard-subscription-widget__label">Date de fin</p>
                  <p className="dashboard-subscription-widget__value">{formatDate(subscription.date_fin)}</p>
                </div>
                {subscription.montant && (
                  <div>
                    <p className="dashboard-subscription-widget__label">Montant</p>
                    <p className="dashboard-subscription-widget__value">{Number(subscription.montant).toFixed(2)} Ar</p>
                  </div>
                )}
              </div>
              {(subscription.statut === 'EXPIRE' || subscription.statut === 'expire' || subscription.statut === 'EN_ATTENTE' || subscription.statut === 'en_attente') && (
                <div className="dashboard-subscription-widget__actions">
                  <Link to="/subscription" className="btn-primary">
                    {subscription.statut === 'EXPIRE' || subscription.statut === 'expire' ? 'Renouveler' : 'Payer maintenant'}
                  </Link>
                </div>
              )}
            </motion.section>
          )}

          {!subscriptionLoading && !subscription && (
            <motion.section 
              className="dashboard-panel dashboard-subscription-widget dashboard-subscription-widget--alert"
              initial={shouldReduceMotion ? false : 'hidden'}
              animate="visible"
              variants={fadeUp}
              transition={{ duration: 0.35 }}
              aria-label="Alerte abonnement"
            >
              <div className="dashboard-subscription-widget__header">
                <div>
                  <p className="dashboard-overline dashboard-overline--dark">Abonnement requis</p>
                  <h2>Aucun abonnement actif</h2>
                </div>
              </div>
              <p style={{ color: 'var(--erp-muted)', marginBottom: '16px' }}>
                Souscrivez à un plan pour accéder à tous les modules opérationnels.
              </p>
              <Link to="/subscription" className="btn-primary">
                S'abonner
              </Link>
            </motion.section>
          )}

          <section className="dashboard-overview" aria-label="Vue synthétique">
            <RevenueHero
              stats={dashboardState.stats}
              evolution={dashboardState.evolution}
              trendPercentage={trendPercentage}
              shouldReduceMotion={shouldReduceMotion}
            />
            <KpiStrip stats={dashboardState.stats} />
          </section>

          <RevenueChart
            geometry={chartGeometry}
            evolution={dashboardState.evolution}
            shouldReduceMotion={shouldReduceMotion}
          />

          <section className="dashboard-workspace" aria-label="Suivi des opérations">
            <TopProductsTable products={dashboardState.topProducts} />
            <ActivityTimeline activity={dashboardState.recentActivity} />
            <PriorityPanel priorities={dashboardState.priorities} />
          </section>
        </div>
      </main>

      <Link className="dashboard-assistant" to="/ai" aria-label="Ouvrir l’assistant IA" title="Assistant IA">
        <i className="ti ti-sparkles" aria-hidden="true" />
        <span className="dashboard-assistant__label" aria-hidden="true">IA</span>
      </Link>
    </div>
  );
};

export default Dashboard;
